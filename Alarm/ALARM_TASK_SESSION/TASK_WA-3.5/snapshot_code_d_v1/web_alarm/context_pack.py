"""Compact read-only Entry Context Pack for Web Alarm Workspace WA-2.4."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .manifest_store import ManifestSnapshotStore, ManifestStoreError
from .models import MicrotaskStatus
from .reconciliation_service import ReconciliationService
from .state_machine import ServerStateMachine
from .task_store import TaskStore
from .workspace_registry import WorkspaceRegistry


PACK_VERSION = 1

PROTOCOL_RULES = [
    "Read current persistent state before changing the real Workspace.",
    "No real-Workspace mutation without a verified restore point for the current microtask.",
    "DONE is not VERIFIED; verification evidence is required before VERIFIED.",
    "Do not start the next microtask before the previous microtask is VERIFIED.",
    "After an ambiguous disconnect, reconcile disk state before retry or rollback.",
    "Do not blindly replay the last mutation operation.",
    "Do not automatically rollback on disconnect; rollback only after reconciliation.",
]


class EntryContextPackBuilder:
    """Build one compact restart-safe Chat handoff without reading full history."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.tasks = TaskStore(storage_root)
        self.registry = WorkspaceRegistry(self.tasks.storage_root)
        self.state = EventCheckpointStore(self.tasks.storage_root)
        self.manifests = ManifestSnapshotStore(self.tasks.storage_root)
        self.machine = ServerStateMachine(self.tasks.storage_root)
        self.reconciliation = ReconciliationService(self.tasks.storage_root)

    def _last_verified(self, task_id: str) -> str | None:
        last: str | None = None
        for micro in self.tasks.list_microtasks(task_id):
            if micro.status == MicrotaskStatus.VERIFIED:
                last = micro.microtask_id
            else:
                break
        return last

    def _current_microtask(self, task_id: str) -> str | None:
        plan = self.tasks.open_plan(task_id)
        if plan.current_microtask_id is not None:
            return plan.current_microtask_id
        microtasks = self.tasks.list_microtasks(task_id)
        for micro in microtasks:
            if micro.status != MicrotaskStatus.VERIFIED:
                return micro.microtask_id
        return microtasks[-1].microtask_id if microtasks else None

    def _snapshot_status(self, task_id: str, microtask_id: str | None) -> str:
        if microtask_id is None:
            return "NOT_APPLICABLE"
        try:
            self.manifests.verify_restore_point(task_id, microtask_id)
        except ManifestStoreError:
            return "NOT_VERIFIED"
        return "VERIFIED"

    def build(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.open_task(task_id)
        workspace = self.registry.get(task.workspace_id)
        plan = self.tasks.open_plan(task_id)
        microtasks = self.tasks.list_microtasks(task_id)

        checkpoint = None
        try:
            checkpoint = self.state.read_checkpoint(task_id)
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" not in str(exc):
                raise

        current_id = (
            checkpoint.current_microtask_id
            if checkpoint is not None and checkpoint.current_microtask_id is not None
            else self._current_microtask(task_id)
        )
        current = (
            self.tasks.open_microtask(task_id, current_id)
            if current_id is not None
            else None
        )

        last_verified = (
            checkpoint.last_verified_microtask_id
            if checkpoint is not None
            else self._last_verified(task_id)
        )
        current_status = (
            checkpoint.current_status.value
            if checkpoint is not None
            else (current.status.value if current is not None else "NO_MICROTASK")
        )
        snapshot_status = (
            checkpoint.snapshot_status
            if checkpoint is not None
            else self._snapshot_status(task_id, current_id)
        )
        last_operation = (
            checkpoint.last_operation_id if checkpoint is not None else None
        )
        if checkpoint is not None:
            next_safe_action = checkpoint.next_safe_action
        elif current_id is not None:
            next_safe_action = self.machine.next_safe_action(task_id, current_id)
        else:
            next_safe_action = "create a microtask and define the TASK plan"

        plan_summary = [
            {
                "sequence": item.sequence,
                "microtask_id": item.microtask_id,
                "title": item.title,
                "status": item.status.value,
            }
            for item in microtasks
        ]

        pack: dict[str, Any] = {
            "PACK_VERSION": PACK_VERSION,
            "TASK": {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status.value,
                "raw_task": task.raw_task,
            },
            "WORKSPACE": {
                "workspace_id": workspace.workspace_id,
                "display_name": workspace.display_name,
                "workspace_root": workspace.workspace_root,
            },
            "GOAL": task.goal,
            "PLAN_SUMMARY": plan_summary,
            "LAST_VERIFIED": last_verified,
            "CURRENT_MICROTASK": current_id,
            "CURRENT_STATUS": current_status,
            "SNAPSHOT_STATUS": snapshot_status,
            "LAST_OPERATION": last_operation,
            "NEXT_SAFE_ACTION": next_safe_action,
            "PROTOCOL_RULES": list(PROTOCOL_RULES),
        }
        reconciliation = self.reconciliation.reconcile_if_needed(
            task_id,
            current_id,
            last_operation,
            current_status,
        )
        pack["RECONCILIATION"] = reconciliation
        if reconciliation is not None:
            pack["CHECKPOINT_NEXT_SAFE_ACTION"] = next_safe_action
            pack["NEXT_SAFE_ACTION"] = reconciliation["NEXT_SAFE_ACTION"]
        pack["CONTEXT_TEXT"] = self.render_text(pack)
        return pack

    @staticmethod
    def render_text(pack: dict[str, Any]) -> str:
        task = pack["TASK"]
        workspace = pack["WORKSPACE"]
        plan_lines = [
            f"{item['sequence']}. {item['microtask_id']} [{item['status']}] — {item['title']}"
            for item in pack["PLAN_SUMMARY"]
        ]
        rules = [f"- {rule}" for rule in pack["PROTOCOL_RULES"]]
        reconciliation = pack.get("RECONCILIATION")
        reconciliation_lines: list[str] = []
        if reconciliation is not None:
            decision = reconciliation["DECISION"]
            reconciliation_lines = [
                f"RECONCILIATION DECISION: {decision['decision']}",
                f"RECONCILIATION REASON: {decision['reason_code']} — {decision['reason']}",
            ]
        return "\n".join(
            [
                "WEB ALARM ENTRY CONTEXT PACK",
                f"TASK: {task['task_id']} — {task['title']}",
                f"TASK STATUS: {task['status']}",
                f"WORKSPACE: {workspace['display_name']} — {workspace['workspace_root']}",
                f"GOAL: {pack['GOAL']}",
                "PLAN SUMMARY:",
                *(plan_lines or ["(no microtasks)"]),
                f"LAST VERIFIED: {pack['LAST_VERIFIED'] or '-'}",
                f"CURRENT MICROTASK: {pack['CURRENT_MICROTASK'] or '-'}",
                f"CURRENT STATUS: {pack['CURRENT_STATUS']}",
                f"SNAPSHOT STATUS: {pack['SNAPSHOT_STATUS']}",
                f"LAST OPERATION: {pack['LAST_OPERATION'] or '-'}",
                *reconciliation_lines,
                f"NEXT SAFE ACTION: {pack['NEXT_SAFE_ACTION']}",
                "PROTOCOL RULES:",
                *rules,
                "RAW TASK:",
                task["raw_task"],
            ]
        )
