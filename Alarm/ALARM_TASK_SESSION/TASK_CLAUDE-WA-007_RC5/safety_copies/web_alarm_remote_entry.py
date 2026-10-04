"""Canonical read-only Remote entry for Web Alarm Workspace WA-3.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .context_pack import EntryContextPackBuilder
from .models import MicrotaskStatus
from .task_store import TaskStore, TaskStoreError


ENTRY_VERSION = 1

_RECOVERY_STATUSES = {
    MicrotaskStatus.BLOCKED_PREPARE.value,
    MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT.value,
    MicrotaskStatus.RECOVERY_REQUIRED.value,
    MicrotaskStatus.FAILED_VERIFICATION.value,
}


class RemoteEntryError(RuntimeError):
    """Raised when the canonical Remote entry cannot resolve safely."""


class RemoteEntry:
    """Resolve exactly one active TASK and return its read-only handoff pack."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.tasks = TaskStore(storage_root)
        self.context = EntryContextPackBuilder(self.tasks.storage_root)

    def active_task_ids(self) -> list[str]:
        task_ids: list[str] = []
        for path in sorted(self.tasks.active_dir.iterdir(), key=lambda p: p.name):
            if not path.is_dir():
                continue
            task = self.tasks.open_task(path.name)
            self.tasks.task_directory(task.task_id, active_only=True)
            task_ids.append(task.task_id)
        return task_ids

    def resolve_task_id(self, task_id: str | None = None) -> str:
        if task_id is not None:
            self.tasks.task_directory(task_id, active_only=True)
            return task_id

        active = self.active_task_ids()
        if not active:
            raise RemoteEntryError(
                "no active TASK is available; create/activate a TASK or pass --task-id"
            )
        if len(active) != 1:
            joined = ", ".join(active)
            raise RemoteEntryError(
                "active TASK is ambiguous; pass --task-id explicitly "
                f"(candidates: {joined})"
            )
        return active[0]

    def enter(self, task_id: str | None = None) -> dict[str, Any]:
        resolved = self.resolve_task_id(task_id)
        pack = self.context.build(resolved)
        current_status = str(pack["CURRENT_STATUS"])
        reconciliation = pack.get("RECONCILIATION")
        if reconciliation is not None:
            recovery_decision = reconciliation["DECISION"]["decision"]
            entry_state = "RECONCILIATION_READY"
            recovery_required = recovery_decision == "MANUAL_REVIEW_REQUIRED"
            mutation_decision = "FOLLOW_RECONCILIATION_NEXT_SAFE_ACTION"
        else:
            recovery_decision = None
            recovery_required = current_status in _RECOVERY_STATUSES
            entry_state = (
                "RECOVERY_REVIEW_REQUIRED"
                if recovery_required
                else "CONTEXT_READY"
            )
            mutation_decision = (
                "RECONCILE_BEFORE_MUTATION"
                if recovery_required
                else "FOLLOW_NEXT_SAFE_ACTION_AFTER_CONTEXT_REVIEW"
            )
        return {
            "ENTRY_VERSION": ENTRY_VERSION,
            "ENTRY_MODE": "CANONICAL_REMOTE_ENTRY",
            "RESOLVED_TASK_ID": resolved,
            "ENTRY_STATE": entry_state,
            "RECOVERY_REVIEW_REQUIRED": recovery_required,
            "RECOVERY_DECISION": recovery_decision,
            "MUTATION_DECISION": mutation_decision,
            "READ_ONLY": True,
            "RECONCILIATION": reconciliation,
            "CONTEXT_PACK": pack,
        }
