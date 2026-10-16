"""Persistent Recovery Report orchestration for WA-3.6 M003."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .models import record_to_dict
from .reconciliation_service import ReconciliationService
from .recovery_report_builder import RecoveryReportBuilder, RecoveryReportBuilderError
from .recovery_report_store import RecoveryReportRecord, RecoveryReportStore
from .resolver_service import ResolverService
from .rollback_service import RollbackService
from .transport_event_store import TransportEventRecord, TransportEventStore


class RecoveryReportClaimError(RecoveryReportBuilderError):
    """A caller claimed a recovery action that no tracked resolution backs."""


class RecoveryReportService:
    """Create/read Recovery Reports without executing workflow recovery actions.

    RC-2: recovery action facts (accepted / retried / rolled back) come only
    from persisted Resolver records. Caller-supplied action lists are kept for
    API compatibility but may only repeat those facts; anything else fails closed.
    """

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.reconciliation = ReconciliationService(storage_root)
        self.state = EventCheckpointStore(self.reconciliation.evidence.tasks.storage_root)
        self.transport = TransportEventStore(self.reconciliation.evidence.tasks.storage_root)
        self.builder = RecoveryReportBuilder()
        self.store = RecoveryReportStore(self.reconciliation.evidence.tasks.storage_root)
        self.resolver = ResolverService(self.reconciliation.evidence.tasks.storage_root)
        self.rollbacks = RollbackService(self.reconciliation.evidence.tasks.storage_root)

    @staticmethod
    def _check_claims(name: str, claimed: Sequence[str], backed: list[str]) -> None:
        unbacked = [item for item in claimed if item not in backed]
        if unbacked:
            raise RecoveryReportClaimError(
                f"{name} is not backed by a fresh tracked resolution: {unbacked}"
            )

    @staticmethod
    def _transport_to_dict(record: TransportEventRecord) -> dict[str, Any]:
        data = asdict(record)
        data["event_type"] = record.event_type.value
        return data

    def _checkpoint_identity(self, task_id: str) -> dict[str, Any] | None:
        try:
            checkpoint = self.state.read_checkpoint(task_id)
        except EventCheckpointStoreError as exc:
            if "checkpoint is missing" in str(exc):
                return None
            raise
        return record_to_dict(checkpoint)

    def create_report(
        self,
        *,
        task_id: str,
        microtask_id: str,
        operation_id: str,
        incident_id: str,
        caller_error_class: str | None = None,
        expected_post_state: Mapping[str, Mapping[str, Any]] | None = None,
        process_evidence: Sequence[Mapping[str, Any]] = (),
        process_restarted: bool = False,
        accepted_as_already_done: Sequence[str] = (),
        actually_retried: Sequence[str] = (),
        actually_rolled_back: Sequence[str] = (),
        untouched_or_unresolved: Sequence[str] = (),
        fresh_process_reopen_result: str | None = None,
        report_id: str | None = None,
    ) -> RecoveryReportRecord:
        evidence = self.reconciliation.evidence.collect(
            task_id,
            microtask_id,
            operation_id=operation_id,
            expected_post_state=expected_post_state,
        )
        decision = self.reconciliation.decisions.decide(evidence)
        facts = self.resolver.report_facts(task_id, microtask_id, operation_id)
        # RC-4: "actually rolled back" only from persisted verified rollback
        # receipts; an accepted ROLLBACK resolution alone is still a request.
        rollback = self.rollbacks.report_facts(task_id, microtask_id, operation_id)
        facts["actually_rolled_back"] = rollback["actually_rolled_back"]
        authoritative = facts["next_safe_action"]
        if authoritative is not None and (
            authoritative["resolution_id"] in rollback["next_safe_action_by_resolution"]
        ):
            facts["next_safe_action"] = {
                "resolution_id": authoritative["resolution_id"],
                "next_safe_action": rollback["next_safe_action_by_resolution"][
                    authoritative["resolution_id"]
                ],
                "source": "rollback",
            }
        for name, claimed in (
            ("accepted_as_already_done", accepted_as_already_done),
            ("actually_retried", actually_retried),
            ("actually_rolled_back", actually_rolled_back),
        ):
            self._check_claims(name, claimed, facts[name])
        transport = [
            self._transport_to_dict(item)
            for item in self.transport.list_events(
                task_id=task_id,
                microtask_id=microtask_id,
                operation_id=operation_id,
            )
        ]
        report = self.builder.build(
            incident_id=incident_id,
            evidence=evidence,
            decision=decision,
            caller_error_class=caller_error_class,
            transport_evidence=transport,
            process_evidence=process_evidence,
            process_restarted=process_restarted,
            checkpoint_identity=self._checkpoint_identity(task_id),
            accepted_as_already_done=facts["accepted_as_already_done"],
            actually_retried=facts["actually_retried"],
            actually_rolled_back=facts["actually_rolled_back"],
            untouched_or_unresolved=untouched_or_unresolved,
            resolver_actions=facts["resolver_actions"],
            resolver_next_safe_action=facts["next_safe_action"],
            rollback_receipts=rollback["rollback_receipts"],
            fresh_process_reopen_result=fresh_process_reopen_result,
            report_id=report_id,
        )
        return self.store.append(report)

    def get_report(
        self,
        task_id: str,
        report_id: str,
    ) -> RecoveryReportRecord:
        return self.store.get(task_id, report_id)

    def list_reports(self, task_id: str) -> list[RecoveryReportRecord]:
        return self.store.list_reports(task_id)
