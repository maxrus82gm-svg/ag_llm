"""Compact read-only Entry Context Pack for Web Alarm Workspace WA-2.4.

RC-5: every current fact (CURRENT_MICROTASK / CURRENT_STATUS / NEXT_SAFE_ACTION
and the rest) comes from the canonical projection over the authoritative stores.
The persisted checkpoint is shown only as a validated diagnostic and is never
read as truth. The pack stays bounded and never reads the event history.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .projection import ProjectionService
from .recovery_report_store import RecoveryReportStore
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
        self.projection = ProjectionService(self.tasks.storage_root)
        self.reconciliation = self.projection.reconciliation
        self.recovery_reports = RecoveryReportStore(self.tasks.storage_root)

    def build(self, task_id: str) -> dict[str, Any]:
        task = self.tasks.open_task(task_id)
        workspace = self.registry.get(task.workspace_id)
        projection = self.projection.build(task_id)
        validation = self.projection.validate_checkpoint(task_id, projection)
        position = projection["position"]
        recovery = projection["recovery"]

        snapshot = projection["restore_point"]["status"]
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
            "PLAN_SUMMARY": [
                {
                    "sequence": item["sequence"],
                    "microtask_id": item["microtask_id"],
                    "title": item["title"],
                    "status": item["status"],
                }
                for item in position["microtasks"]
            ],
            "LAST_VERIFIED": position["last_verified"],
            "CURRENT_MICROTASK": position["current_microtask_id"],
            "CURRENT_STATUS": position["current_status"],
            "SNAPSHOT_STATUS": snapshot if snapshot in ("VERIFIED", "NOT_APPLICABLE") else "NOT_VERIFIED",
            "LAST_OPERATION": projection["last_operation_id"],
            "NEXT_SAFE_ACTION": projection["next_safe_action"],
            "AUTHORITY_SOURCE": projection["authority_source"],
            "RECOVERY": {
                key: recovery.get(key)
                for key in ("state", "source", "operation_id", "resolution_id", "rollback_id", "decision", "attention")
            },
            "BLOCKERS": [{"code": item["code"], "reason": item["reason"]} for item in projection["blockers"]],
            "CHECKPOINT": {
                "status": validation["status"],
                "authoritative": False,
                "reasons": validation["reasons"],
            },
            "PROJECTION": {
                "projection_version": projection["projection_version"],
                "source_fingerprint": projection["source_fingerprint"],
                "projection_fingerprint": projection["projection_fingerprint"],
            },
            "PROTOCOL_RULES": list(PROTOCOL_RULES),
        }
        reports = self.recovery_reports.list_reports(task_id)
        pack["LATEST_RECOVERY_REPORT"] = (
            reports[-1].to_dict() if reports else None
        )
        reconciliation = None
        if projection["authority_source"] == "reconciliation" and recovery["operation_id"] is not None:
            # the very calculation behind NEXT (no second, possibly diverging read)
            reconciliation = projection["advisory_reconciliation"].get(recovery["operation_id"])
        pack["RECONCILIATION"] = reconciliation
        if reconciliation is not None:
            # diagnostic only: what the persisted (never authoritative) checkpoint said
            pack["CHECKPOINT_NEXT_SAFE_ACTION"] = (validation["persisted"] or {}).get("next_safe_action")
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
        blocker_lines = [f"BLOCKER: {item['code']} — {item['reason']}" for item in pack.get("BLOCKERS", [])]
        recovery = pack.get("RECOVERY") or {}
        recovery_lines = (
            [f"RECOVERY: {recovery.get('state')} (operation {recovery.get('operation_id') or '-'})"]
            if recovery.get("state") not in (None, "NORMAL")
            else []
        )
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
                *recovery_lines,
                *reconciliation_lines,
                *blocker_lines,
                f"NEXT SAFE ACTION: {pack['NEXT_SAFE_ACTION']}",
                f"NEXT SOURCE: {pack.get('AUTHORITY_SOURCE', '-')} (projection from authoritative state)",
                f"CHECKPOINT: {(pack.get('CHECKPOINT') or {}).get('status', '-')} (never authority)",
                "PROTOCOL RULES:",
                *rules,
                "RAW TASK:",
                task["raw_task"],
            ]
        )
