"""Deterministic reconciliation decision policy for WA-3.3.2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from .reconciliation import ReconciliationEvidence


DECISION_VERSION = 1

ADOPT_CURRENT_STATE = "ADOPT_CURRENT_STATE"
RETRY_SAFE = "RETRY_SAFE"
ROLLBACK_CURRENT_MICROTASK = "ROLLBACK_CURRENT_MICROTASK"
MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

_ALLOWED_DECISIONS = {
    ADOPT_CURRENT_STATE,
    RETRY_SAFE,
    ROLLBACK_CURRENT_MICROTASK,
    MANUAL_REVIEW_REQUIRED,
}


@dataclass(slots=True)
class ReconciliationDecision:
    decision_version: int
    decision: str
    reason_code: str
    reason: str
    evidence_fingerprint: str
    task_id: str
    microtask_id: str
    operation_id: str | None
    operation_status: str | None
    target_counts: dict[str, int]
    affected_targets: list[str]
    next_safe_action: str
    automatic_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if self.decision not in _ALLOWED_DECISIONS:
            raise ValueError(f"unsupported reconciliation decision: {self.decision}")
        if self.automatic_mutation_authorized:
            raise ValueError(
                "WA-3.3.2 decisions must never authorize automatic mutation"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReconciliationDecisionEngine:
    """Pure evidence -> decision mapping. No storage reads and no side effects."""

    @staticmethod
    def evidence_fingerprint(evidence: ReconciliationEvidence) -> str:
        raw = json.dumps(
            evidence.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _counts(evidence: ReconciliationEvidence) -> dict[str, int]:
        counts = {
            "PRE_STATE": 0,
            "EXPECTED_POST_STATE": 0,
            "DRIFT": 0,
            "CHANGED_UNCLASSIFIED": 0,
            "MISSING_EVIDENCE": 0,
        }
        for target in evidence.targets:
            counts[target.classification] = counts.get(
                target.classification, 0
            ) + 1
        return counts

    @staticmethod
    def _affected(
        evidence: ReconciliationEvidence,
        *,
        manual: bool = False,
    ) -> list[str]:
        if manual:
            selected = [
                item.source_path
                for item in evidence.targets
                if item.classification != "PRE_STATE"
                or item.missing_evidence
            ]
            return selected or [item.source_path for item in evidence.targets]
        return [item.source_path for item in evidence.targets]

    def _decision(
        self,
        evidence: ReconciliationEvidence,
        decision: str,
        reason_code: str,
        reason: str,
        next_safe_action: str,
        *,
        manual_targets: bool = False,
    ) -> ReconciliationDecision:
        return ReconciliationDecision(
            decision_version=DECISION_VERSION,
            decision=decision,
            reason_code=reason_code,
            reason=reason,
            evidence_fingerprint=self.evidence_fingerprint(evidence),
            task_id=evidence.task_id,
            microtask_id=evidence.microtask_id,
            operation_id=evidence.operation_id,
            operation_status=evidence.operation_status,
            target_counts=self._counts(evidence),
            affected_targets=self._affected(
                evidence,
                manual=manual_targets,
            ),
            next_safe_action=next_safe_action,
            automatic_mutation_authorized=False,
        )

    def manual(
        self,
        evidence: ReconciliationEvidence,
        reason_code: str,
        reason: str,
    ) -> ReconciliationDecision:
        return self._decision(
            evidence,
            MANUAL_REVIEW_REQUIRED,
            reason_code,
            reason,
            (
                "inspect conflicting or missing evidence; do not retry, adopt, "
                "or rollback automatically"
            ),
            manual_targets=True,
        )

    def decide(self, evidence: ReconciliationEvidence) -> ReconciliationDecision:
        if not evidence.targets:
            return self.manual(
                evidence,
                "NO_TARGET_EVIDENCE",
                "reconciliation has no target evidence",
            )

        if evidence.operation_id is None or evidence.operation_status is None:
            return self.manual(
                evidence,
                "OPERATION_EVIDENCE_MISSING",
                "persistent operation identity/status is required",
            )

        if evidence.errors:
            return self.manual(
                evidence,
                "EVIDENCE_ERRORS",
                "; ".join(evidence.errors),
            )

        if not evidence.evidence_complete:
            return self.manual(
                evidence,
                "CORE_EVIDENCE_INCOMPLETE",
                "manifest/snapshot/current-state evidence is incomplete",
            )

        classifications = [item.classification for item in evidence.targets]
        unsafe = {
            "DRIFT",
            "CHANGED_UNCLASSIFIED",
            "MISSING_EVIDENCE",
        }
        present_unsafe = sorted(set(classifications) & unsafe)
        if present_unsafe:
            return self.manual(
                evidence,
                "UNSAFE_TARGET_CLASSIFICATION",
                "unsafe target classifications: " + ", ".join(present_unsafe),
            )

        all_post = all(
            value == "EXPECTED_POST_STATE" for value in classifications
        )
        all_pre = all(value == "PRE_STATE" for value in classifications)
        mixed_known = (
            set(classifications) == {"PRE_STATE", "EXPECTED_POST_STATE"}
        )

        if all_post:
            if not evidence.expected_post_complete:
                return self.manual(
                    evidence,
                    "POST_EVIDENCE_NOT_EXACT",
                    "expected post-state is not exact for every target",
                )
            if evidence.operation_status == "INTENT":
                return self.manual(
                    evidence,
                    "LIFECYCLE_CONTRADICTS_POST_STATE",
                    (
                        "Workspace exactly matches expected post-state while "
                        "operation lifecycle never left INTENT"
                    ),
                )
            return self._decision(
                evidence,
                ADOPT_CURRENT_STATE,
                "EXACT_POST_STATE_PROVEN",
                "all targets exactly match the recorded expected post-state",
                (
                    "adopt the existing Workspace state through the later "
                    "recovery integration; do not rerun the mutation"
                ),
            )

        if mixed_known:
            if evidence.operation_status == "VERIFIED":
                return self.manual(
                    evidence,
                    "VERIFIED_OPERATION_NOW_PARTIAL",
                    (
                        "operation is VERIFIED but Workspace now mixes pre-state "
                        "and expected post-state"
                    ),
                )
            if evidence.operation_status == "INTENT":
                return self.manual(
                    evidence,
                    "INTENT_OPERATION_HAS_PARTIAL_CHANGES",
                    (
                        "operation never left INTENT but Workspace contains "
                        "known post-state changes"
                    ),
                )
            return self._decision(
                evidence,
                ROLLBACK_CURRENT_MICROTASK,
                "PARTIAL_KNOWN_STATE",
                (
                    "targets are a mixture of exact pre-state and exact "
                    "expected post-state with a valid restore point"
                ),
                (
                    "rollback only the current microtask through the later "
                    "explicit recovery executor; do not retry first"
                ),
            )

        if all_pre:
            status = evidence.operation_status
            if status == "INTENT":
                return self._decision(
                    evidence,
                    RETRY_SAFE,
                    "INTENT_AND_PRE_STATE",
                    (
                        "operation remained INTENT and all declared targets "
                        "exactly match pre-state"
                    ),
                    (
                        "retry only through the replay-safe execution path using "
                        "the same operation_id"
                    ),
                )

            retryable_ambiguous = {
                "STARTED",
                "UNKNOWN_AFTER_DISCONNECT",
                "FAILED",
            }
            if status in retryable_ambiguous:
                if not evidence.expected_post_complete:
                    return self.manual(
                        evidence,
                        "PRE_STATE_BUT_POST_EVIDENCE_INCOMPLETE",
                        (
                            "targets match pre-state but exact post-state evidence "
                            "is missing, so completion cannot be disproved"
                        ),
                    )
                if any(
                    item.matches_expected_post_state is True
                    for item in evidence.targets
                ):
                    return self.manual(
                        evidence,
                        "PRE_STATE_ALSO_MATCHES_EXPECTED_POST",
                        (
                            "current pre-state is also a valid expected post-state "
                            "for at least one target"
                        ),
                    )
                return self._decision(
                    evidence,
                    RETRY_SAFE,
                    "PRE_STATE_AND_POST_NOT_REACHED",
                    (
                        "all targets exactly match pre-state and exact expected "
                        "post-state is proven not to have been reached"
                    ),
                    (
                        "retry only through the replay-safe execution path using "
                        "the same operation_id"
                    ),
                )

            return self.manual(
                evidence,
                "LIFECYCLE_CONTRADICTS_PRE_STATE",
                (
                    f"operation status {status!r} is incompatible with "
                    "automatic retry from proven pre-state"
                ),
            )

        return self.manual(
            evidence,
            "UNHANDLED_EVIDENCE_SHAPE",
            "evidence shape is not covered by a safe deterministic rule",
        )
