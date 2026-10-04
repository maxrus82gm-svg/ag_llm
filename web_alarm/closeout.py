"""RC-5 TASK closeout gate: pure inspection + gated completion.

``inspect`` is pure (no lock, no write). ``complete`` takes the operations TASK
lock (serializes with operation begin/transition, Resolver, RC-3 claims and
RC-4 rollback) and then the TaskStore mutation lock (serializes with
microtask/plan writes), re-proves eligibility from a fresh projection under
both locks and only then moves the TASK to completed. Lock order is always
operations TASK lock -> TaskStore lock; no path takes them the other way round.
A rejected completion writes nothing: the TASK stays active.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .event_checkpoint_store import EventCheckpointStoreError
from .operation_store import OperationStoreError
from .projection import ProjectionService
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS
from .task_store import TaskStore, TaskStoreError


class CloseoutError(RuntimeError):
    """The closeout gate could not run safely (lock or storage failure)."""


class CloseoutService:
    def __init__(self, storage_root: str | Path | None = None, *, lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS) -> None:
        self.projection = ProjectionService(storage_root, lock_timeout=lock_timeout)
        self.tasks = TaskStore(self.projection.tasks.storage_root, lock_timeout=lock_timeout)
        self.operations = self.projection.operations
        self.events = self.projection.state

    @staticmethod
    def verdict(projection: dict[str, Any]) -> dict[str, Any]:
        blockers = projection["closeout"]
        return {
            "task_id": projection["task"]["task_id"],
            "eligible": not blockers,
            "blockers": blockers,
            "facts": {
                "task_status": projection["task"]["status"],
                "location": projection["task"]["location"],
                "microtasks": projection["position"]["microtasks"],
                "operations": [
                    {
                        "operation_id": view["operation_id"],
                        "status": view["status"],
                        "recovery_state": (view["recovery"] or {}).get("state"),
                    }
                    for view in projection["operations"]
                ],
                "rollbacks": [
                    {"rollback_id": s["rollback_id"], "status": s["status"], "claims_released": s["claims_released"]}
                    for s in projection["rollbacks"]
                ],
                "active_claims": len(projection["ownership"]["active_claims"]),
            },
            "next_safe_action": (
                blockers[0]["next"]
                if blockers
                else "the closeout gate is clean: complete the TASK through the gated `task complete`"
            ),
            "source_fingerprint": projection["source_fingerprint"],
            "projection_fingerprint": projection["projection_fingerprint"],
            "workflow_mutation_performed": False,
        }

    def inspect(self, task_id: str) -> dict[str, Any]:
        """Pure closeout inspection: eligibility, blockers, facts and NEXT."""
        return self.verdict(self.projection.build(task_id))

    def complete(self, task_id: str) -> dict[str, Any]:
        """Complete the TASK only if a fresh inspection under the TASK locks is clean."""
        try:
            with self.operations.task_lock(task_id):
                with self.tasks.mutation_lock(task_id):
                    verdict = self.verdict(self.projection.build(task_id))
                    if not verdict["eligible"]:
                        return {"result": "REJECTED", "completed": False, "task": None, "closeout": verdict}
                    task = self.tasks.complete_task_locked(task_id)
        except (OperationStoreError, TaskStoreError) as exc:
            raise CloseoutError(str(exc)) from exc
        recorded = True
        try:  # history only: the completion itself is already authoritative
            self.events.append_event(
                task_id,
                "TASK_COMPLETED",
                payload={"gate": "RC5_CLOSEOUT", "source_fingerprint": verdict["source_fingerprint"]},
            )
        except EventCheckpointStoreError:
            recorded = False
        return {
            "result": "COMPLETED",
            "completed": True,
            "task": task,
            "closeout": dict(verdict, workflow_mutation_performed=True),
            "event_recorded": recorded,
        }
