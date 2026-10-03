"""Persistent Recovery Report orchestration for WA-3.6 M003."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from .models import record_to_dict
from .reconciliation_service import ReconciliationService
from .recovery_report_builder import RecoveryReportBuilder
from .recovery_report_store import RecoveryReportRecord, RecoveryReportStore
from .transport_event_store import TransportEventRecord, TransportEventStore


class RecoveryReportService:
    """Create/read Recovery Reports without executing workflow recovery actions."""

    def __init__(self, storage_root: str | Path | None = None) -> None:
        self.reconciliation = ReconciliationService(storage_root)
        self.state = EventCheckpointStore(self.reconciliation.evidence.tasks.storage_root)
        self.transport = TransportEventStore(self.reconciliation.evidence.tasks.storage_root)
        self.builder = RecoveryReportBuilder()
        self.store = RecoveryReportStore(self.reconciliation.evidence.tasks.storage_root)

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
            accepted_as_already_done=accepted_as_already_done,
            actually_retried=actually_retried,
            actually_rolled_back=actually_rolled_back,
            untouched_or_unresolved=untouched_or_unresolved,
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
