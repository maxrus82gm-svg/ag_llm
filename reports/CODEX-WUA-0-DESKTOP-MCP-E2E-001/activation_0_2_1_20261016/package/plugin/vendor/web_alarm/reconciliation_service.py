"""Read-only integration service for Web Alarm Workspace WA-3.3.3."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .models import MicrotaskStatus, OperationStatus
from .operation_store import OperationStore, OperationStoreError
from .reconciliation import (
    ReconciliationEvidenceCollector,
    ReconciliationEvidenceError,
)
from .reconciliation_decision import ReconciliationDecisionEngine


SERVICE_VERSION = 1

_RECOVERY_MICROTASK_STATUSES = {
    MicrotaskStatus.BLOCKED_PREPARE.value,
    MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT.value,
    MicrotaskStatus.RECOVERY_REQUIRED.value,
    MicrotaskStatus.FAILED_VERIFICATION.value,
}

_RECONCILE_OPERATION_STATUSES = {
    OperationStatus.STARTED.value,
    OperationStatus.UNKNOWN_AFTER_DISCONNECT.value,
}


class ReconciliationService:
    """Coordinate evidence + decision without executing any recovery mutation."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.evidence = ReconciliationEvidenceCollector(storage_root)
        self.decisions = ReconciliationDecisionEngine()
        self.operations = OperationStore(self.evidence.tasks.storage_root)

    def reconcile(
        self,
        task_id: str,
        microtask_id: str,
        operation_id: str,
        *,
        expected_post_state: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        evidence = self.evidence.collect(
            task_id,
            microtask_id,
            operation_id=operation_id,
            expected_post_state=expected_post_state,
        )
        decision = self.decisions.decide(evidence)
        return {
            "SERVICE_VERSION": SERVICE_VERSION,
            "MODE": "READ_ONLY_RECONCILIATION",
            "MUTATION_PERFORMED": False,
            "TASK_ID": task_id,
            "MICROTASK_ID": microtask_id,
            "OPERATION_ID": operation_id,
            "EVIDENCE": evidence.to_dict(),
            "DECISION": decision.to_dict(),
            "NEXT_SAFE_ACTION": decision.next_safe_action,
        }

    def needs_reconciliation(
        self,
        task_id: str,
        operation_id: str | None,
        current_status: str | None,
    ) -> bool:
        if current_status in _RECOVERY_MICROTASK_STATUSES:
            return True
        if operation_id is None:
            return False
        try:
            operation = self.operations.get(task_id, operation_id)
        except OperationStoreError:
            # Missing/corrupt operation evidence must be surfaced by reconciliation
            # when the surrounding microtask itself already says recovery.
            return False
        return operation.status.value in _RECONCILE_OPERATION_STATUSES

    def reconcile_if_needed(
        self,
        task_id: str,
        microtask_id: str | None,
        operation_id: str | None,
        current_status: str | None,
    ) -> dict[str, Any] | None:
        if microtask_id is None or operation_id is None:
            return None
        if not self.needs_reconciliation(task_id, operation_id, current_status):
            return None
        return self.reconcile(task_id, microtask_id, operation_id)
