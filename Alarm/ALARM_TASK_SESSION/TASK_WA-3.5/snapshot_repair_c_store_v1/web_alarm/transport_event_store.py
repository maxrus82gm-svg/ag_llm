"""Persistent append-only transport evidence for Web Alarm WA-3.5.A."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, new_id, utc_now_iso
from .workspace_registry import default_storage_root


class TransportEventStoreError(RuntimeError):
    """Raised when transport evidence cannot be validated or persisted."""


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


def _record_to_dict(record: TransportEventRecord) -> dict[str, Any]:
    data = asdict(record)
    data["event_type"] = record.event_type.value
    return data


class TransportEventStore:
    """Global append-only transport evidence; never mutates workflow state."""

    RELATIVE_PATH = Path("transport") / "transport_events.jsonl"

    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        root = Path(storage_root) if storage_root is not None else default_storage_root()
        self.storage_root = root.expanduser().resolve(strict=False)
        self.events_path = self.storage_root / self.RELATIVE_PATH
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
        line = json.dumps(
            _record_to_dict(record),
            ensure_ascii=False,
            separators=(",", ":"),
        ) + "\n"
        try:
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise TransportEventStoreError(
                f"cannot append transport event: {self.events_path}"
            ) from exc
        return record

    def read_events(self) -> list[TransportEventRecord]:
        if not self.events_path.exists():
            return []
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise TransportEventStoreError(
                f"cannot read transport events: {self.events_path}"
            ) from exc

        records: list[TransportEventRecord] = []
        for index, line in enumerate(lines, start=1):
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
