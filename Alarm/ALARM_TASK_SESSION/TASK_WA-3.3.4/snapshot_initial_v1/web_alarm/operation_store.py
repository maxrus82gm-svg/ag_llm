"""Persistent replay-safe operation identity for Web Alarm Workspace WA-3.2."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .models import (
    SCHEMA_VERSION,
    OperationRecord,
    OperationStatus,
    new_id,
    record_to_dict,
    utc_now_iso,
)
from .task_store import TaskStore, TaskStoreError


class OperationStoreError(RuntimeError):
    """Raised when operation state is missing, invalid, or unsafe."""


class OperationConflictError(OperationStoreError):
    """Same operation_id was replayed with a different immutable request."""


class OperationTransitionError(OperationStoreError):
    """Requested operation lifecycle transition is not allowed."""


def _safe_component(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationStoreError(f"{name} must be a non-empty string")
    value = value.strip()
    if Path(value).name != value or "/" in value or "\\" in value:
        raise OperationStoreError(f"{name} must not contain path separators")
    return value


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{new_id('tmp')}.tmp"
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise OperationStoreError(f"cannot persist operation record: {path}") from exc


def _canonical_fingerprint(
    *,
    task_id: str,
    microtask_id: str,
    action: str,
    target: str,
    expected_precondition_sha256: str | None,
    request_payload: Any,
) -> str:
    material = {
        "task_id": task_id,
        "microtask_id": microtask_id,
        "action": action,
        "target": target,
        "expected_precondition_sha256": expected_precondition_sha256,
        "request": request_payload,
    }
    try:
        raw = json.dumps(
            material,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OperationStoreError("operation request is not JSON-serializable") from exc
    return hashlib.sha256(raw).hexdigest()


class OperationStore:
    """Disk-backed operation identity and lifecycle; it never executes mutations."""

    _ALLOWED: dict[OperationStatus, set[OperationStatus]] = {
        OperationStatus.INTENT: {
            OperationStatus.STARTED,
            OperationStatus.FAILED,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        },
        OperationStatus.STARTED: {
            OperationStatus.DONE,
            OperationStatus.FAILED,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        },
        OperationStatus.DONE: {
            OperationStatus.VERIFIED,
            OperationStatus.FAILED,
        },
        OperationStatus.VERIFIED: set(),
        OperationStatus.FAILED: set(),
        OperationStatus.UNKNOWN_AFTER_DISCONNECT: set(),
    }

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.tasks = TaskStore(storage_root)
        self.events = EventCheckpointStore(self.tasks.storage_root)
        self._lock = threading.RLock()

    def _operations_dir(
        self,
        task_id: str,
        *,
        active_only: bool = False,
        create: bool = False,
    ) -> Path:
        task_dir = self.tasks.task_directory(task_id, active_only=active_only)
        path = task_dir / "operations"
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(
        self,
        task_id: str,
        operation_id: str,
        *,
        active_only: bool = False,
        create_dir: bool = False,
    ) -> Path:
        operation_id = _safe_component("operation_id", operation_id)
        return self._operations_dir(
            task_id,
            active_only=active_only,
            create=create_dir,
        ) / f"{operation_id}.json"

    def _load_path(self, path: Path, task_id: str, operation_id: str) -> OperationRecord:
        if not path.is_file():
            raise OperationStoreError(f"unknown operation_id: {operation_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OperationStoreError(f"cannot read operation record: {path}") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            raise OperationStoreError(f"unsupported or invalid operation schema: {path}")
        try:
            raw["status"] = OperationStatus(raw["status"])
            record = OperationRecord(**raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise OperationStoreError(f"invalid operation record: {path}") from exc
        if record.task_id != task_id or record.operation_id != operation_id:
            raise OperationStoreError("operation identity does not match requested record")
        return record

    def get(self, task_id: str, operation_id: str) -> OperationRecord:
        operation_id = _safe_component("operation_id", operation_id)
        path = self._path(task_id, operation_id)
        return self._load_path(path, task_id, operation_id)

    def list(self, task_id: str) -> list[OperationRecord]:
        directory = self._operations_dir(task_id)
        if not directory.is_dir():
            return []
        records: list[OperationRecord] = []
        for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
            operation_id = path.stem
            records.append(self._load_path(path, task_id, operation_id))
        return records

    @staticmethod
    def replay_decision(status: OperationStatus) -> str:
        if status in {
            OperationStatus.STARTED,
            OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        }:
            return "RECONCILE_REQUIRED"
        if status in {
            OperationStatus.DONE,
            OperationStatus.VERIFIED,
            OperationStatus.FAILED,
        }:
            return "RETURN_KNOWN_STATE"
        return "RETURN_EXISTING_INTENT"

    def _touch_checkpoint(self, task_id: str, operation_id: str) -> None:
        try:
            checkpoint = self.events.read_checkpoint(task_id)
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" in str(exc):
                return
            raise OperationStoreError(str(exc)) from exc
        checkpoint.last_operation_id = operation_id
        try:
            self.events.write_checkpoint(checkpoint)
        except EventCheckpointStoreError as exc:
            raise OperationStoreError(str(exc)) from exc

    def begin(
        self,
        task_id: str,
        microtask_id: str,
        action: str,
        target: str,
        *,
        operation_id: str | None = None,
        expected_precondition_sha256: str | None = None,
        request_payload: Any = None,
    ) -> dict[str, Any]:
        task_id = _safe_component("task_id", task_id)
        microtask_id = _safe_component("microtask_id", microtask_id)
        action = action.strip() if isinstance(action, str) else ""
        target = target.strip() if isinstance(target, str) else ""
        if not action:
            raise OperationStoreError("action must be a non-empty string")
        if not target:
            raise OperationStoreError("target must be a non-empty string")
        self.tasks.open_microtask(task_id, microtask_id)
        self.tasks.task_directory(task_id, active_only=True)
        chosen_id = _safe_component(
            "operation_id",
            operation_id or new_id("op"),
        )
        fingerprint = _canonical_fingerprint(
            task_id=task_id,
            microtask_id=microtask_id,
            action=action,
            target=target,
            expected_precondition_sha256=expected_precondition_sha256,
            request_payload=request_payload,
        )

        with self._lock:
            path = self._path(task_id, chosen_id, active_only=True)
            if path.exists():
                existing = self._load_path(path, task_id, chosen_id)
                immutable_match = (
                    existing.microtask_id == microtask_id
                    and existing.action == action
                    and existing.target == target
                    and existing.request_fingerprint == fingerprint
                    and existing.expected_precondition_sha256
                    == expected_precondition_sha256
                )
                if not immutable_match:
                    self.events.append_event(
                        task_id,
                        "OPERATION_REPLAY_CONFLICT",
                        microtask_id=microtask_id,
                        operation_id=chosen_id,
                        payload={"existing_status": existing.status.value},
                    )
                    raise OperationConflictError(
                        "operation_id already exists with a different request fingerprint"
                    )
                self.events.append_event(
                    task_id,
                    "OPERATION_REPLAY",
                    microtask_id=microtask_id,
                    operation_id=chosen_id,
                    payload={
                        "status": existing.status.value,
                        "decision": self.replay_decision(existing.status),
                    },
                )
                self._touch_checkpoint(task_id, chosen_id)
                return {
                    "operation": existing,
                    "created": False,
                    "replayed": True,
                    "replay_decision": self.replay_decision(existing.status),
                }

            record = OperationRecord(
                operation_id=chosen_id,
                task_id=task_id,
                microtask_id=microtask_id,
                action=action,
                target=target,
                status=OperationStatus.INTENT,
                request_fingerprint=fingerprint,
                expected_precondition_sha256=expected_precondition_sha256,
            )
            _atomic_write_json(path, record_to_dict(record))
            self.events.append_event(
                task_id,
                "OPERATION_INTENT",
                microtask_id=microtask_id,
                operation_id=chosen_id,
                payload={
                    "action": action,
                    "target": target,
                    "request_fingerprint": fingerprint,
                },
            )
            self._touch_checkpoint(task_id, chosen_id)
            return {
                "operation": record,
                "created": True,
                "replayed": False,
                "replay_decision": self.replay_decision(record.status),
            }

    def transition(
        self,
        task_id: str,
        operation_id: str,
        requested_status: OperationStatus | str,
        *,
        result_summary: str | None = None,
    ) -> dict[str, Any]:
        requested = OperationStatus(requested_status)
        operation_id = _safe_component("operation_id", operation_id)
        with self._lock:
            path = self._path(task_id, operation_id, active_only=True)
            record = self._load_path(path, task_id, operation_id)
            current = record.status

            if requested == current:
                self.events.append_event(
                    task_id,
                    "OPERATION_TRANSITION_REPLAY",
                    microtask_id=record.microtask_id,
                    operation_id=operation_id,
                    payload={"status": current.value},
                )
                self._touch_checkpoint(task_id, operation_id)
                return {
                    "operation": record,
                    "changed": False,
                    "replayed": True,
                    "replay_decision": self.replay_decision(record.status),
                }

            if requested not in self._ALLOWED.get(current, set()):
                raise OperationTransitionError(
                    f"{current.value} -> {requested.value} is not allowed"
                )

            record.status = requested
            if result_summary is not None:
                if not isinstance(result_summary, str) or not result_summary.strip():
                    raise OperationStoreError(
                        "result_summary must be a non-empty string when provided"
                    )
                record.result_summary = result_summary.strip()
            record.updated_at = utc_now_iso()
            _atomic_write_json(path, record_to_dict(record))
            self.events.append_event(
                task_id,
                "OPERATION_TRANSITION",
                microtask_id=record.microtask_id,
                operation_id=operation_id,
                payload={
                    "from": current.value,
                    "to": requested.value,
                    "result_summary": record.result_summary,
                },
            )
            self._touch_checkpoint(task_id, operation_id)
            return {
                "operation": record,
                "changed": True,
                "replayed": False,
                "replay_decision": self.replay_decision(record.status),
            }
