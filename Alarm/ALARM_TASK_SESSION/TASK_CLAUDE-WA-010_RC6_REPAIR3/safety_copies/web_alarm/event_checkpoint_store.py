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
from .task_store import TaskStore, TaskStoreError


class EventCheckpointStoreError(RuntimeError):
    """Raised when event/checkpoint state is invalid or cannot be persisted."""


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
        line = json.dumps(record_to_dict(record), ensure_ascii=False, separators=(",", ":")) + "\n"
        try:
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise EventCheckpointStoreError(f"cannot append event: {path}") from exc
        return record

    def read_events(self, task_id: str) -> list[EventRecord]:
        path = self._events_path(task_id)
        if not path.exists():
            return []
        records: list[EventRecord] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise EventCheckpointStoreError(f"cannot read event log: {path}") from exc
        for index, line in enumerate(lines, start=1):
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
