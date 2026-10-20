"""Persistent append-only transport evidence for Web Alarm WA-3.5.A."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, new_id, utc_now_iso
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .workspace_registry import default_storage_root


class TransportEventStoreError(RuntimeError):
    """Raised when transport evidence cannot be validated or persisted."""


class TransportEventConflictError(TransportEventStoreError):
    """Raised when one event_id is reused for different transport evidence."""


class TransportEventType(str, Enum):
    REMOTE_ONLINE = "REMOTE_ONLINE"
    REMOTE_OFFLINE = "REMOTE_OFFLINE"
    REMOTE_RECOVERED = "REMOTE_RECOVERED"
    RESULT_DELIVERY_FAILED = "RESULT_DELIVERY_FAILED"
    MESSAGE_DELIVERY_TIMEOUT = "MESSAGE_DELIVERY_TIMEOUT"
    PROCESS_RESTARTED = "PROCESS_RESTARTED"

@dataclass(slots=True)
class TransportEventRecord:
    event_id: str = field(default_factory=lambda: new_id("transport"))
    event_type: TransportEventType = TransportEventType.REMOTE_ONLINE
    task_id: str | None = None
    microtask_id: str | None = None
    operation_id: str | None = None
    remote_call_kind: str | None = None
    error_class: str | None = None
    process_id: int | None = None
    process_start_time: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=utc_now_iso)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        if not isinstance(self.event_type, TransportEventType):
            self.event_type = TransportEventType(self.event_type)
        for name in ("task_id", "microtask_id", "operation_id", "remote_call_kind",
                     "error_class", "process_start_time"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be null or a non-empty string")
        if self.process_id is not None and (
            not isinstance(self.process_id, int) or isinstance(self.process_id, bool)
            or self.process_id <= 0
        ):
            raise ValueError("process_id must be null or a positive integer")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be an object")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")


# AUD-01T: the per-TASK history framing contract (AUD-01) for the global log too.
# json.dumps(ensure_ascii=False) leaves U+0085/U+2028/U+2029 raw inside strings,
# and str.splitlines() readers (older code, tools) cut a record at them; written
# escaped they are the same JSON string and one physical LF stays one record.
_ESCAPED_LINE_BOUNDARIES = str.maketrans(
    {chr(code): chr(92) + "u" + format(code, "04x") for code in (0x85, 0x2028, 0x2029)}
)


def _record_to_dict(record: TransportEventRecord) -> dict[str, Any]:
    data = asdict(record)
    data["event_type"] = record.event_type.value
    return data


def _request_identity(record: TransportEventRecord) -> dict[str, Any]:
    data = _record_to_dict(record)
    data.pop("recorded_at", None)
    return data


def _encode_record(record: TransportEventRecord) -> bytes:
    line = json.dumps(_record_to_dict(record), ensure_ascii=False, separators=(",", ":"))
    try:
        return (line.translate(_ESCAPED_LINE_BOUNDARIES) + "\n").encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("transport event text is not valid Unicode (unpaired surrogate)") from exc


class TransportEventStore:
    """Global append-only transport evidence; never mutates workflow state.

    AUD-01T: one store lock serializes read-check-append across processes and
    threads, so replay/conflict detection sees every committed record and
    concurrent appends cannot overwrite each other (O_APPEND is not atomic
    between processes on Windows). Readers stay lock-free: a record is a single
    write call. A torn or unparsable log fails closed and is never repaired.
    """

    RELATIVE_PATH = Path("transport") / "transport_events.jsonl"
    LOCK_RELATIVE_PATH = Path("locks") / "transport" / "transport_events.lock"

    def __init__(
        self,
        storage_root: str | os.PathLike[str] | None = None,
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        root = Path(storage_root) if storage_root is not None else default_storage_root()
        self.storage_root = root.expanduser().resolve(strict=False)
        self.events_path = self.storage_root / self.RELATIVE_PATH
        self.lock_path = self.storage_root / self.LOCK_RELATIVE_PATH
        self.lock_timeout = lock_timeout
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: TransportEventType | str,
        *,
        task_id: str | None = None,
        microtask_id: str | None = None,
        operation_id: str | None = None,
        remote_call_kind: str | None = None,
        error_class: str | None = None,
        process_id: int | None = None,
        process_start_time: str | None = None,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> TransportEventRecord:
        record = TransportEventRecord(
            event_id=event_id or new_id("transport"),
            event_type=TransportEventType(event_type),
            task_id=task_id,
            microtask_id=microtask_id,
            operation_id=operation_id,
            remote_call_kind=remote_call_kind,
            error_class=error_class,
            process_id=process_id,
            process_start_time=process_start_time,
            payload=dict(payload or {}),
        )
        data = _encode_record(record)  # invalid text is refused before any lock or write
        lock = InterProcessLock(self.lock_path, timeout=self.lock_timeout)
        try:
            lock.acquire()
        except (StoreLockTimeout, OSError) as exc:
            raise TransportEventStoreError(f"cannot lock transport events: {exc}") from exc
        try:
            for existing in self.read_events():
                if existing.event_id != record.event_id:
                    continue
                if _request_identity(existing) == _request_identity(record):
                    return existing
                raise TransportEventConflictError(
                    f"event_id replay conflict: {record.event_id}"
                )
            self._append_locked(data)
        finally:
            lock.release()
        return record

    def _append_locked(self, data: bytes) -> None:
        """Append one record while holding the store lock.

        A crash may leave a complete JSON object without its delimiter: never
        join the next record onto it. A failed write/fsync is rolled back to the
        previous end before the lock is released, so one failed append does not
        leave a torn tail that would block all transport evidence.
        """
        try:
            with self.events_path.open("a+b", buffering=0) as handle:
                size = handle.seek(0, os.SEEK_END)
                if size:
                    handle.seek(-1, os.SEEK_END)
                    if handle.read(1) != b"\n":
                        raise TransportEventStoreError(
                            f"unterminated transport event log: {self.events_path}"
                        )
                try:
                    view = memoryview(data)
                    while view:
                        view = view[handle.write(view):]
                    os.fsync(handle.fileno())
                except OSError as exc:
                    try:
                        handle.truncate(size)
                        os.fsync(handle.fileno())
                        outcome = f"rolled back to {size} bytes"
                    except OSError as undo:
                        outcome = (
                            f"rollback to {size} bytes failed ({undo}); a torn tail keeps "
                            "transport evidence fail-closed until manual repair"
                        )
                    raise TransportEventStoreError(
                        f"cannot append transport event: {self.events_path}; {outcome}"
                    ) from exc
        except OSError as exc:
            raise TransportEventStoreError(
                f"cannot append transport event: {self.events_path}"
            ) from exc

    def read_events(self) -> list[TransportEventRecord]:
        try:
            data = self.events_path.read_bytes()
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise TransportEventStoreError(
                f"cannot read transport events: {self.events_path}"
            ) from exc
        if data and not data.endswith(b"\n"):
            raise TransportEventStoreError(
                f"unterminated transport event log: {self.events_path}"
            )

        records: list[TransportEventRecord] = []
        # AUD-01T: one physical LF ends one record (a CRLF record drops its CR);
        # Unicode line boundaries inside a JSON string are data, not delimiters.
        for index, chunk in enumerate(data.split(b"\n")[:-1], start=1):
            try:
                line = chunk.removesuffix(b"\r").decode("utf-8")
            except UnicodeDecodeError as exc:
                raise TransportEventStoreError(
                    f"invalid transport event UTF-8 at line {index}"
                ) from exc
            if not line.strip():
                raise TransportEventStoreError(
                    f"blank transport event line at {index}"
                )
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TransportEventStoreError(
                    f"invalid transport event JSON at line {index}"
                ) from exc
            if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
                raise TransportEventStoreError(
                    f"invalid transport event schema at line {index}"
                )
            try:
                raw["event_type"] = TransportEventType(raw["event_type"])
                record = TransportEventRecord(**raw)
            except (KeyError, TypeError, ValueError) as exc:
                raise TransportEventStoreError(
                    f"invalid transport event record at line {index}"
                ) from exc
            records.append(record)
        return records

    def list_events(
        self,
        *,
        task_id: str | None = None,
        microtask_id: str | None = None,
        operation_id: str | None = None,
        event_type: TransportEventType | str | None = None,
    ) -> list[TransportEventRecord]:
        event_type_value = (
            TransportEventType(event_type) if event_type is not None else None
        )
        return [
            record
            for record in self.read_events()
            if (task_id is None or record.task_id == task_id)
            and (microtask_id is None or record.microtask_id == microtask_id)
            and (operation_id is None or record.operation_id == operation_id)
            and (event_type_value is None or record.event_type == event_type_value)
        ]
