"""Append-only event log and compact checkpoint storage for WA-1.5."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import (
    SCHEMA_VERSION,
    CheckpointRecord,
    EventRecord,
    MicrotaskStatus,
    new_id,
    record_to_dict,
    utc_now_iso,
)
from .store_lock import InterProcessLock, StoreLockTimeout
from .task_store import TaskStore, TaskStoreError


class EventCheckpointStoreError(RuntimeError):
    """Raised when event/checkpoint state is invalid or cannot be persisted."""


class MicrotaskHistoryConflict(EventCheckpointStoreError):
    """R-MT: journal and persisted status cannot be reconciled automatically (operator required)."""


# R-MT (AUD-02b-R): a microtask lifecycle step is journaled as a write-ahead intent
# (durable before the status compare-and-set, carrying the verification evidence),
# then the status write, then a commit MICROTASK_TRANSITION with the same intent_id.
MICROTASK_INTENT = "MICROTASK_TRANSITION_INTENT"
MICROTASK_COMMIT = "MICROTASK_TRANSITION"
MICROTASK_ABANDONED = "MICROTASK_TRANSITION_ABANDONED"
MICROTASK_REAFFIRMED = "MICROTASK_VERIFICATION_REAFFIRMED"
_VERIFIED = MicrotaskStatus.VERIFIED.value


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def microtask_journal(events: list[EventRecord], statuses: dict[str, tuple[str, str]]) -> dict[str, list]:
    """Pure R-MT reading of one TASK history (no lock, no write).

    ``statuses`` maps microtask_id -> (persisted status value, record updated_at).
    Returns ``pending`` (one open intent per microtask with its deterministic
    resolution), ``contradictions`` (operator required) and ``unproven_verified``
    (VERIFIED with no recorded evidence: neither an evidence-bearing commit, nor
    a reaffirmation, nor an open intent that will commit one).

    Deterministic resolution of an open intent, decided by the authoritative
    record only: status == intent.to -> COMMIT (rebuilt from the durable intent);
    status == intent.from and the record untouched since the intent -> ABANDON
    (the compare-and-set never happened); anything else -> contradiction.
    """
    intents: dict[str, dict[str, EventRecord]] = {}
    closures: dict[str, dict[str, list[tuple[str, EventRecord]]]] = {}
    proven: set[str] = set()
    contradictions: list[dict[str, Any]] = []
    for event in events:
        mid = event.microtask_id
        payload = event.payload if isinstance(event.payload, dict) else {}
        if mid is None:
            continue
        if event.event_type == MICROTASK_INTENT:
            intents.setdefault(mid, {})[event.event_id] = event
        elif event.event_type in (MICROTASK_COMMIT, MICROTASK_ABANDONED):
            intent_id = payload.get("intent_id")
            if event.event_type == MICROTASK_COMMIT and payload.get("to") == _VERIFIED \
                    and _text(payload.get("verification_evidence")):
                proven.add(mid)
            if intent_id is not None:
                closures.setdefault(mid, {}).setdefault(intent_id, []).append((event.event_type, event))
        elif event.event_type == MICROTASK_REAFFIRMED and _text(payload.get("verification_evidence")):
            proven.add(mid)
    pending: list[dict[str, Any]] = []
    for mid in sorted(set(intents) | set(closures)):
        own = intents.get(mid, {})
        open_intents = []
        for intent_id, items in closures.get(mid, {}).items():
            intent = own.get(intent_id)
            if intent is None:
                contradictions.append({"microtask_id": mid, "intent_id": intent_id,
                                       "reason": "a commit/abandon names an intent that is not recorded"})
                continue
            kinds = {kind for kind, _ in items}
            if len(kinds) > 1:
                contradictions.append({"microtask_id": mid, "intent_id": intent_id,
                                       "reason": "the intent is both committed and abandoned"})
            for kind, event in items:
                if kind == MICROTASK_COMMIT and any(
                    event.payload.get(key) != intent.payload.get(key)
                    for key in ("from", "to", "verification_evidence")
                ):
                    contradictions.append({"microtask_id": mid, "intent_id": intent_id,
                                           "reason": "the commit contradicts its durable intent"})
        for intent_id, intent in own.items():
            if intent_id not in closures.get(mid, {}):
                open_intents.append(intent)
        if not open_intents:
            continue
        if len(open_intents) > 1:
            contradictions.append({"microtask_id": mid, "intent_id": None,
                                   "reason": f"{len(open_intents)} open intents for one microtask"})
            continue
        intent = open_intents[0]
        state = statuses.get(mid)
        frm, to = intent.payload.get("from"), intent.payload.get("to")
        if state is None:
            contradictions.append({"microtask_id": mid, "intent_id": intent.event_id,
                                   "reason": "the microtask record is not readable"})
        elif to == _VERIFIED and not _text(intent.payload.get("verification_evidence")):
            contradictions.append({"microtask_id": mid, "intent_id": intent.event_id,
                                   "reason": "a VERIFIED intent without verification evidence"})
        elif state[0] == to:
            pending.append({"microtask_id": mid, "intent": intent, "resolution": "COMMIT"})
        elif state[0] == frm and state[1] == intent.payload.get("basis_updated_at"):
            pending.append({"microtask_id": mid, "intent": intent, "resolution": "ABANDON"})
        else:
            contradictions.append({"microtask_id": mid, "intent_id": intent.event_id,
                                   "reason": f"the record changed since the intent ({frm} -> {to}): it is "
                                             f"{state[0]}; the outcome is not provable"})
    committing_verified = {p["microtask_id"] for p in pending
                           if p["resolution"] == "COMMIT" and p["intent"].payload.get("to") == _VERIFIED}
    unproven = sorted(mid for mid, state in statuses.items()
                      if state[0] == _VERIFIED and mid not in proven and mid not in committing_verified)
    return {"pending": pending, "contradictions": contradictions, "unproven_verified": unproven}


# AUD-01: json.dumps(ensure_ascii=False) leaves U+0085/U+2028/U+2029 raw inside
# strings, while str.splitlines() readers (older code, tools) cut lines at them.
# Writing them escaped keeps one record per physical LF for every reader.
_ESCAPED_LINE_BOUNDARIES = str.maketrans({"\u0085": "\\u0085", "\u2028": "\\u2028", "\u2029": "\\u2029"})


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise EventCheckpointStoreError(f"cannot persist file: {path}") from exc


class EventCheckpointStore:
    """Store append-only chronology separately from current compact state."""

    def __init__(self, storage_root: str | os.PathLike[str] | None = None) -> None:
        self.task_store = TaskStore(storage_root)

    def _task_dir(self, task_id: str) -> Path:
        try:
            return self.task_store.task_directory(task_id)
        except TaskStoreError as exc:
            raise EventCheckpointStoreError(str(exc)) from exc

    def _events_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "events.jsonl"

    def _checkpoint_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "checkpoint.json"

    def _checkpoint_md_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "checkpoint.md"

    def append_event(
        self,
        task_id: str,
        event_type: str,
        *,
        microtask_id: str | None = None,
        operation_id: str | None = None,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> EventRecord:
        record = EventRecord(
            event_id=event_id or new_id("event"),
            task_id=task_id,
            event_type=event_type,
            microtask_id=microtask_id,
            operation_id=operation_id,
            payload=dict(payload or {}),
        )
        path = self._events_path(task_id)
        line = json.dumps(record_to_dict(record), ensure_ascii=False, separators=(",", ":"))
        data = (line.translate(_ESCAPED_LINE_BOUNDARIES) + "\n").encode("utf-8")  # before any lock or open
        # AUD-02b: O_APPEND is not atomic between processes on Windows, and the
        # writers of one TASK history hold different locks (or none), so racing
        # appends could overwrite each other: a persisted status would silently
        # lose its event. This leaf lock (no other lock is taken under it)
        # serializes the appends of one TASK; readers stay lock-free.
        lock = InterProcessLock(
            self.task_store.storage_root / "locks" / "events" / f"{task_id}.lock",
            timeout=self.task_store.lock_timeout,
        )
        try:
            lock.acquire()
        except (StoreLockTimeout, OSError) as exc:
            raise EventCheckpointStoreError(f"cannot lock event log: {path}: {exc}") from exc
        try:
            # A crash may leave a complete JSON object without its delimiter.
            # Never join the next record onto it or silently repair history.
            with path.open("a+b") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell():
                    handle.seek(-1, os.SEEK_END)
                    if handle.read(1) != b"\n":
                        raise EventCheckpointStoreError(f"unterminated event log: {path}")
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise EventCheckpointStoreError(f"cannot append event: {path}") from exc
        finally:
            lock.release()
        return record

    def read_events(self, task_id: str) -> list[EventRecord]:
        path = self._events_path(task_id)
        if not path.exists():
            return []
        records: list[EventRecord] = []
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise EventCheckpointStoreError(f"cannot read event log: {path}") from exc
        if data and not data.endswith(b"\n"):
            raise EventCheckpointStoreError(f"unterminated event log: {path}")
        # AUD-01: one physical LF ends one record (a CRLF record drops its CR).
        # Unicode line boundaries inside a JSON string are data, not delimiters.
        for index, chunk in enumerate(data.split(b"\n")[:-1], start=1):
            try:
                line = chunk.removesuffix(b"\r").decode("utf-8")
            except UnicodeDecodeError as exc:
                raise EventCheckpointStoreError(f"cannot read event log: {path}") from exc
            if not line.strip():
                raise EventCheckpointStoreError(f"blank event line at {index}")
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EventCheckpointStoreError(f"invalid event JSON at line {index}") from exc
            if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
                raise EventCheckpointStoreError(f"invalid event schema at line {index}")
            try:
                record = EventRecord(**raw)
            except (TypeError, ValueError) as exc:
                raise EventCheckpointStoreError(f"invalid event record at line {index}") from exc
            if record.task_id != task_id:
                raise EventCheckpointStoreError(f"event task mismatch at line {index}")
            records.append(record)
        return records

    def microtask_statuses(self, task_id: str) -> dict[str, tuple[str, str]]:
        try:
            return {m.microtask_id: (m.status.value, m.updated_at) for m in self.task_store.list_microtasks(task_id)}
        except TaskStoreError as exc:
            raise EventCheckpointStoreError(f"microtask records are unreadable: {exc}") from exc

    def resolve_microtask_intents_locked(self, task_id: str, microtask_id: str | None = None) -> list[dict[str, Any]]:
        """R-MT reconciliation; the caller holds the TASK mutation lock.

        Every status writer holds that lock, so the persisted status cannot move
        while an open intent is classified here. Only the deterministic outcomes
        of ``microtask_journal`` are written (a commit rebuilt from the durable
        intent, marked ``recovered_from_intent``; or an audited abandon); any
        contradiction raises MicrotaskHistoryConflict and nothing is written.
        """
        events = self.read_events(task_id)
        facts = microtask_journal(events, self.microtask_statuses(task_id))
        conflicts = [c for c in facts["contradictions"] if microtask_id in (None, c["microtask_id"])]
        if conflicts:
            raise MicrotaskHistoryConflict(
                "microtask history cannot be reconciled automatically: "
                + "; ".join(f"{c['microtask_id']}: {c['reason']}" for c in conflicts)
            )
        outcomes: list[dict[str, Any]] = []
        for item in facts["pending"]:
            if microtask_id not in (None, item["microtask_id"]):
                continue
            intent = item["intent"]
            frm, to = intent.payload.get("from"), intent.payload.get("to")
            if item["resolution"] == "COMMIT":
                self.append_event(
                    task_id, MICROTASK_COMMIT, microtask_id=item["microtask_id"], operation_id=intent.operation_id,
                    payload={"from": frm, "to": to,
                             "verification_evidence": intent.payload.get("verification_evidence"),
                             "intent_id": intent.event_id, "recovered_from_intent": True},
                )
            else:
                self.append_event(
                    task_id, MICROTASK_ABANDONED, microtask_id=item["microtask_id"], operation_id=intent.operation_id,
                    payload={"intent_id": intent.event_id, "from": frm, "to": to, "recovered": True,
                             "reason": "the record is unchanged since the intent: the compare-and-set never happened"},
                )
            outcomes.append({"microtask_id": item["microtask_id"], "intent_id": intent.event_id,
                             "resolution": item["resolution"], "from": frm, "to": to})
        return outcomes

    def write_checkpoint(self, record: CheckpointRecord) -> CheckpointRecord:
        task = self.task_store.open_task(record.task_id)
        if record.workspace_id != task.workspace_id:
            raise EventCheckpointStoreError("checkpoint workspace_id does not match TASK")
        if record.current_microtask_id is not None:
            micro = self.task_store.open_microtask(record.task_id, record.current_microtask_id)
            if micro.task_id != record.task_id:
                raise EventCheckpointStoreError("current microtask does not belong to TASK")
        if record.last_verified_microtask_id is not None:
            micro = self.task_store.open_microtask(record.task_id, record.last_verified_microtask_id)
            if micro.task_id != record.task_id:
                raise EventCheckpointStoreError("last verified microtask does not belong to TASK")
        record.updated_at = utc_now_iso()
        payload = json.dumps(record_to_dict(record), ensure_ascii=False, indent=2) + "\n"
        _atomic_write_text(self._checkpoint_path(record.task_id), payload)
        _atomic_write_text(self._checkpoint_md_path(record.task_id), self.render_checkpoint_md(record))
        return record

    def read_checkpoint(self, task_id: str) -> CheckpointRecord:
        path = self._checkpoint_path(task_id)
        if not path.is_file():
            raise EventCheckpointStoreError(f"checkpoint is missing: {task_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EventCheckpointStoreError(f"cannot read checkpoint: {path}") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            raise EventCheckpointStoreError("unsupported or invalid checkpoint schema")
        try:
            raw["current_status"] = MicrotaskStatus(raw["current_status"])
            record = CheckpointRecord(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise EventCheckpointStoreError("invalid checkpoint record") from exc
        if record.task_id != task_id:
            raise EventCheckpointStoreError("checkpoint task_id mismatch")
        task = self.task_store.open_task(task_id)
        if record.workspace_id != task.workspace_id:
            raise EventCheckpointStoreError("checkpoint workspace_id mismatch")
        return record

    def checkpoint_markdown(self, task_id: str) -> str | None:
        """Read checkpoint.md as written (None when absent); pure."""
        path = self._checkpoint_md_path(task_id)
        if not path.is_file():
            return None
        try:
            return path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise EventCheckpointStoreError(f"cannot read checkpoint markdown: {path}") from exc

    @staticmethod
    def render_checkpoint_md(record: CheckpointRecord) -> str:
        projection = ""
        if record.projection is not None:
            meta = record.projection
            projection = (
                f"- PROJECTION: v{meta.get('projection_version')} rebuilt from authoritative state "
                f"(source {meta.get('source_fingerprint')}, projection {meta.get('projection_fingerprint')})\n"
                f"- NEXT SOURCE: {meta.get('authority_source')}\n"
            )
        return (
            f"# Web Alarm Checkpoint\n\n"
            f"- TASK: {record.task_id}\n"
            f"- WORKSPACE: {record.workspace_id}\n"
            f"- LAST VERIFIED MICROTASK: {record.last_verified_microtask_id or '-'}\n"
            f"- CURRENT MICROTASK: {record.current_microtask_id or '-'}\n"
            f"- CURRENT STATUS: {record.current_status.value}\n"
            f"- SNAPSHOT STATUS: {record.snapshot_status}\n"
            f"- LAST OPERATION: {record.last_operation_id or '-'}\n"
            f"- UPDATED AT: {record.updated_at}\n"
            f"{projection}\n"
            f"## NEXT SAFE ACTION\n\n{record.next_safe_action}\n"
        )
