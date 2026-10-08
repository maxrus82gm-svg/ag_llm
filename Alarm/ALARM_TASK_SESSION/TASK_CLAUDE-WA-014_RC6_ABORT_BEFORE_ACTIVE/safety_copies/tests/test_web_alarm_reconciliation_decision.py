import unittest

from web_alarm.reconciliation import ReconciliationEvidence, TargetEvidence
from web_alarm.reconciliation_decision import (
    ADOPT_CURRENT_STATE,
    MANUAL_REVIEW_REQUIRED,
    RETRY_SAFE,
    ROLLBACK_CURRENT_MICROTASK,
    ReconciliationDecisionEngine,
)


def target(
    path: str,
    classification: str,
    *,
    matches_pre: bool | None,
    matches_post: bool | None,
    drift: bool | None = False,
    missing: list[str] | None = None,
) -> TargetEvidence:
    return TargetEvidence(
        source_path=path,
        expected_change="edit",
        exists_before=True,
        size_before=6,
        sha256_before="prehash",
        snapshot_path="snapshots/s1.bin",
        snapshot_valid=True,
        snapshot_error=None,
        current_exists=True,
        current_is_file=True,
        current_size=5,
        current_sha256="currenthash",
        path_error=None,
        expected_post_exists=True,
        expected_post_sha256="posthash",
        expected_post_source="supplied",
        operation_target=True,
        operation_precondition_matches_manifest=True,
        matches_pre_state=matches_pre,
        matches_expected_post_state=matches_post,
        drift_detected=drift,
        classification=classification,
        missing_evidence=list(missing or []),
    )


def evidence(
    *targets: TargetEvidence,
    status: str | None = "UNKNOWN_AFTER_DISCONNECT",
    operation_id: str | None = "op_1",
    complete: bool = True,
    post_complete: bool = True,
    errors: list[str] | None = None,
) -> ReconciliationEvidence:
    return ReconciliationEvidence(
        evidence_version=1,
        task_id="task_decision",
        microtask_id="m1",
        workspace_id="ws_1",
        workspace_root="M:/workspace",
        operation_id=operation_id,
        operation_status=status,
        operation_action="write" if operation_id else None,
        operation_target="a.txt" if operation_id else None,
        operation_request_fingerprint="fingerprint" if operation_id else None,
        operation_expected_precondition_sha256="prehash" if operation_id else None,
        operation_result_summary=None,
        verification_evidence=None,
        manifest_status="VERIFIED",
        snapshot_status="VERIFIED",
        evidence_complete=complete,
        expected_post_complete=post_complete,
        errors=list(errors or []),
        targets=list(targets),
    )


class ReconciliationDecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ReconciliationDecisionEngine()

    def test_exact_post_state_is_adopted_without_authorizing_mutation(self):
        ev = evidence(
            target(
                "a.txt",
                "EXPECTED_POST_STATE",
                matches_pre=False,
                matches_post=True,
            ),
            status="UNKNOWN_AFTER_DISCONNECT",
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, ADOPT_CURRENT_STATE)
        self.assertEqual(result.reason_code, "EXACT_POST_STATE_PROVEN")
        self.assertFalse(result.automatic_mutation_authorized)
        self.assertIn("do not rerun", result.next_safe_action)

    def test_intent_and_all_pre_state_is_retry_safe(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            status="INTENT",
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, RETRY_SAFE)
        self.assertEqual(result.reason_code, "INTENT_AND_PRE_STATE")
        self.assertIn("same operation_id", result.next_safe_action)

    def test_started_all_pre_with_exact_post_disproven_is_retry_safe(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            status="STARTED",
            post_complete=True,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, RETRY_SAFE)
        self.assertEqual(result.reason_code, "PRE_STATE_AND_POST_NOT_REACHED")

    def test_started_all_pre_without_exact_post_is_manual(self):
        ev = evidence(
            target(
                "a.txt",
                "PRE_STATE",
                matches_pre=True,
                matches_post=None,
                missing=["expected_post_state"],
            ),
            status="STARTED",
            post_complete=False,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(
            result.reason_code,
            "PRE_STATE_BUT_POST_EVIDENCE_INCOMPLETE",
        )

    def test_partial_known_state_is_rollback_candidate_not_execution(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            target(
                "b.txt",
                "EXPECTED_POST_STATE",
                matches_pre=False,
                matches_post=True,
            ),
            status="UNKNOWN_AFTER_DISCONNECT",
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, ROLLBACK_CURRENT_MICROTASK)
        self.assertEqual(result.reason_code, "PARTIAL_KNOWN_STATE")
        self.assertFalse(result.automatic_mutation_authorized)
        self.assertIn("later explicit recovery executor", result.next_safe_action)

    def test_verified_operation_with_partial_workspace_is_manual(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            target(
                "b.txt",
                "EXPECTED_POST_STATE",
                matches_pre=False,
                matches_post=True,
            ),
            status="VERIFIED",
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "VERIFIED_OPERATION_NOW_PARTIAL")

    def test_intent_with_partial_workspace_is_manual(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            target(
                "b.txt",
                "EXPECTED_POST_STATE",
                matches_pre=False,
                matches_post=True,
            ),
            status="INTENT",
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "INTENT_OPERATION_HAS_PARTIAL_CHANGES")

    def test_drift_is_manual(self):
        ev = evidence(
            target(
                "a.txt",
                "DRIFT",
                matches_pre=False,
                matches_post=False,
                drift=True,
            )
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "UNSAFE_TARGET_CLASSIFICATION")
        self.assertIn("a.txt", result.affected_targets)

    def test_changed_unclassified_is_manual(self):
        ev = evidence(
            target(
                "a.txt",
                "CHANGED_UNCLASSIFIED",
                matches_pre=False,
                matches_post=None,
                drift=None,
                missing=["expected_post_state"],
            ),
            post_complete=False,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "UNSAFE_TARGET_CLASSIFICATION")

    def test_missing_core_evidence_is_manual(self):
        ev = evidence(
            target(
                "a.txt",
                "MISSING_EVIDENCE",
                matches_pre=None,
                matches_post=None,
                drift=None,
                missing=["valid_snapshot"],
            ),
            complete=False,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "CORE_EVIDENCE_INCOMPLETE")

    def test_missing_operation_identity_is_manual(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            status=None,
            operation_id=None,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "OPERATION_EVIDENCE_MISSING")

    def test_pre_state_that_also_satisfies_post_is_not_retry_safe(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=True),
            status="UNKNOWN_AFTER_DISCONNECT",
            post_complete=True,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(
            result.reason_code,
            "PRE_STATE_ALSO_MATCHES_EXPECTED_POST",
        )

    def test_done_but_workspace_is_pre_state_is_manual(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            status="DONE",
            post_complete=True,
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "LIFECYCLE_CONTRADICTS_PRE_STATE")

    def test_intent_with_exact_post_state_is_lifecycle_conflict(self):
        ev = evidence(
            target(
                "a.txt",
                "EXPECTED_POST_STATE",
                matches_pre=False,
                matches_post=True,
            ),
            status="INTENT",
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(
            result.reason_code,
            "LIFECYCLE_CONTRADICTS_POST_STATE",
        )

    def test_same_evidence_gives_identical_decision_and_fingerprint(self):
        ev = evidence(
            target("a.txt", "PRE_STATE", matches_pre=True, matches_post=False),
            status="INTENT",
        )

        first = self.engine.decide(ev).to_dict()
        second = self.engine.decide(ev).to_dict()

        self.assertEqual(first, second)
        self.assertEqual(len(first["evidence_fingerprint"]), 64)

    def test_evidence_errors_fail_closed_before_target_rules(self):
        ev = evidence(
            target(
                "a.txt",
                "EXPECTED_POST_STATE",
                matches_pre=False,
                matches_post=True,
            ),
            errors=["operation target is not declared in manifest"],
        )

        result = self.engine.decide(ev)

        self.assertEqual(result.decision, MANUAL_REVIEW_REQUIRED)
        self.assertEqual(result.reason_code, "EVIDENCE_ERRORS")


if __name__ == "__main__":
    unittest.main()
