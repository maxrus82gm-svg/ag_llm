"""Pure authoritative evidence -> Recovery Report builder for WA-3.6 M002."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .reconciliation import ReconciliationEvidence, TargetEvidence
from .reconciliation_decision import (
    ReconciliationDecision,
    ReconciliationDecisionEngine,
)
from .recovery_report_store import (
    RecoveryReportRecord,
    RecoveryTargetSummary,
    SideEffectScope,
)


class RecoveryReportBuilderError(RuntimeError):
    """Raised when authoritative inputs are inconsistent or incomplete."""


class RecoveryReportBuilder:
    """Build Recovery Reports without reading storage or executing recovery."""

    _KNOWN = {"PRE_STATE", "EXPECTED_POST_STATE"}

    @staticmethod
    def _side_effect_scope(evidence: ReconciliationEvidence) -> SideEffectScope:
        if (
            not evidence.targets
            or evidence.errors
            or not evidence.evidence_complete
        ):
            return SideEffectScope.AMBIGUOUS

        classifications = [item.classification for item in evidence.targets]
        if any(value not in RecoveryReportBuilder._KNOWN for value in classifications):
            return SideEffectScope.AMBIGUOUS
        if all(value == "PRE_STATE" for value in classifications):
            return SideEffectScope.NONE
        if all(value == "EXPECTED_POST_STATE" for value in classifications):
            if evidence.expected_post_complete:
                return SideEffectScope.FULL
            return SideEffectScope.AMBIGUOUS
        if set(classifications) == RecoveryReportBuilder._KNOWN:
            return SideEffectScope.PARTIAL
        return SideEffectScope.AMBIGUOUS

    @staticmethod
    def _target_summary(target: TargetEvidence) -> RecoveryTargetSummary:
        pre_state = {
            "exists": target.exists_before,
            "size": target.size_before,
            "sha256": target.sha256_before,
            "snapshot_valid": target.snapshot_valid,
        }
        current_state = {
            "exists": target.current_exists,
            "is_file": target.current_is_file,
            "size": target.current_size,
            "sha256": target.current_sha256,
        }
        expected_post_state = {
            "exists": target.expected_post_exists,
            "sha256": target.expected_post_sha256,
            "source": target.expected_post_source,
        }
        evidence_identity = {
            "classification": target.classification,
            "snapshot_path": target.snapshot_path,
            "snapshot_error": target.snapshot_error,
            "path_error": target.path_error,
            "missing_evidence": list(target.missing_evidence),
            "operation_target": target.operation_target,
            "operation_precondition_matches_manifest": (
                target.operation_precondition_matches_manifest
            ),
        }
        return RecoveryTargetSummary(
            source_path=target.source_path,
            pre_state=pre_state,
            current_state=current_state,
            expected_post_state=expected_post_state,
            classification=target.classification,
            evidence_identity=evidence_identity,
        )

    @staticmethod
    def _evidence_list(
        name: str,
        values: Iterable[Mapping[str, Any] | Any],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for value in values:
            if isinstance(value, Mapping):
                result.append(dict(value))
                continue
            to_dict = getattr(value, "to_dict", None)
            if callable(to_dict):
                payload = to_dict()
                if isinstance(payload, dict):
                    result.append(payload)
                    continue
            raise RecoveryReportBuilderError(
                f"{name} items must be mappings or provide to_dict()"
            )
        return result

    @staticmethod
    def _validate_decision(
        evidence: ReconciliationEvidence,
        decision: ReconciliationDecision,
    ) -> str:
        fingerprint = ReconciliationDecisionEngine.evidence_fingerprint(evidence)
        identity_matches = (
            decision.task_id == evidence.task_id
            and decision.microtask_id == evidence.microtask_id
            and decision.operation_id == evidence.operation_id
        )
        if not identity_matches or decision.evidence_fingerprint != fingerprint:
            raise RecoveryReportBuilderError(
                "reconciliation decision is not bound to supplied evidence"
            )
        return fingerprint

    def build(
        self,
        *,
        incident_id: str,
        evidence: ReconciliationEvidence,
        decision: ReconciliationDecision | None,
        caller_error_class: str | None = None,
        transport_evidence: Iterable[Mapping[str, Any] | Any] = (),
        process_evidence: Iterable[Mapping[str, Any] | Any] = (),
        process_restarted: bool = False,
        checkpoint_identity: Mapping[str, Any] | None = None,
        accepted_as_already_done: Iterable[str] = (),
        actually_retried: Iterable[str] = (),
        actually_rolled_back: Iterable[str] = (),
        untouched_or_unresolved: Iterable[str] = (),
        resolver_actions: Iterable[Mapping[str, Any]] = (),
        resolver_next_safe_action: Mapping[str, Any] | None = None,
        rollback_receipts: Iterable[Mapping[str, Any]] = (),
        next_safe_action: str | None = None,
        fresh_process_reopen_result: str | None = None,
        report_id: str | None = None,
        created_at: str | None = None,
    ) -> RecoveryReportRecord:
        if not isinstance(evidence, ReconciliationEvidence):
            raise RecoveryReportBuilderError(
                "evidence must be ReconciliationEvidence"
            )

        fingerprint = ReconciliationDecisionEngine.evidence_fingerprint(evidence)
        authoritative_next: str | None = None
        if decision is not None:
            if not isinstance(decision, ReconciliationDecision):
                raise RecoveryReportBuilderError(
                    "decision must be ReconciliationDecision or None"
                )
            fingerprint = self._validate_decision(evidence, decision)
            authoritative_next = decision.next_safe_action
        if resolver_next_safe_action is not None:
            # RC-2: persisted Resolver outcome outranks advisory reconciliation.
            authoritative_next = resolver_next_safe_action["next_safe_action"]
        if authoritative_next is not None:
            if next_safe_action is not None and (
                next_safe_action.strip() != authoritative_next
            ):
                raise RecoveryReportBuilderError(
                    "next_safe_action conflicts with authoritative decision"
                )
            resolved_next_safe_action = authoritative_next
        else:
            if not isinstance(next_safe_action, str) or not next_safe_action.strip():
                raise RecoveryReportBuilderError(
                    "next_safe_action is required when decision is unavailable"
                )
            resolved_next_safe_action = next_safe_action.strip()

        evidence_identity: dict[str, Any] = {
            "evidence_version": evidence.evidence_version,
            "evidence_fingerprint": fingerprint,
        }
        if decision is not None:
            evidence_identity.update(
                {
                    "decision_version": decision.decision_version,
                    "reason_code": decision.reason_code,
                }
            )
        if resolver_next_safe_action is not None:
            evidence_identity.update(
                {
                    "next_safe_action_source": resolver_next_safe_action.get("source", "resolver"),
                    "next_safe_action_resolution_id": resolver_next_safe_action[
                        "resolution_id"
                    ],
                }
            )

        kwargs: dict[str, Any] = {
            "incident_id": incident_id,
            "task_id": evidence.task_id,
            "microtask_id": evidence.microtask_id,
            "operation_id": evidence.operation_id,
            "caller_error_class": caller_error_class,
            "transport_evidence": self._evidence_list(
                "transport_evidence",
                transport_evidence,
            ),
            "process_evidence": self._evidence_list(
                "process_evidence",
                process_evidence,
            ),
            "process_restarted": process_restarted,
            "last_persistent_operation_state": evidence.operation_status,
            "checkpoint_identity": (
                dict(checkpoint_identity)
                if checkpoint_identity is not None
                else None
            ),
            "affected_targets": [
                self._target_summary(target) for target in evidence.targets
            ],
            "evidence_identity": evidence_identity,
            "side_effect_scope": self._side_effect_scope(evidence),
            "reconciliation_decision": (
                decision.decision if decision is not None else None
            ),
            "reconciliation_reason": (
                decision.reason if decision is not None else None
            ),
            "accepted_as_already_done": list(accepted_as_already_done),
            "actually_retried": list(actually_retried),
            "actually_rolled_back": list(actually_rolled_back),
            "untouched_or_unresolved": list(untouched_or_unresolved),
            "resolver_actions": self._evidence_list(
                "resolver_actions",
                resolver_actions,
            ),
            "rollback_receipts": self._evidence_list(
                "rollback_receipts",
                rollback_receipts,
            ),
            "next_safe_action": resolved_next_safe_action,
            "fresh_process_reopen_result": fresh_process_reopen_result,
        }
        if report_id is not None:
            kwargs["report_id"] = report_id
        if created_at is not None:
            kwargs["created_at"] = created_at

        try:
            return RecoveryReportRecord(**kwargs)
        except (TypeError, ValueError) as exc:
            raise RecoveryReportBuilderError(
                "invalid Recovery Report inputs"
            ) from exc
