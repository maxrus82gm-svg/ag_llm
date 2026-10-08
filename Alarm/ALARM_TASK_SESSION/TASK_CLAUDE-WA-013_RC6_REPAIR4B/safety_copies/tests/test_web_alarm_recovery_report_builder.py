import unittest

from web_alarm.reconciliation import ReconciliationEvidence, TargetEvidence
from web_alarm.reconciliation_decision import (
    ADOPT_CURRENT_STATE,
    ReconciliationDecisionEngine,
)
from web_alarm.recovery_report_builder import (
    RecoveryReportBuilder,
    RecoveryReportBuilderError,
)
from web_alarm.recovery_report_store import SideEffectScope


class RecoveryReportBuilderTests(unittest.TestCase):
    def make_target(self, classification, source_path="file.py"):
        pre = classification == "PRE_STATE"
        post = classification == "EXPECTED_POST_STATE"
        return TargetEvidence(
            source_path=source_path,
            expected_change="edit",
            exists_before=True,
            size_before=3,
            sha256_before="pre",
            snapshot_path="snapshots/s1.bin",
            snapshot_valid=True,
            snapshot_error=None,
            current_exists=True,
            current_is_file=True,
            current_size=4,
            current_sha256="pre" if pre else ("post" if post else "other"),
            path_error=None,
            expected_post_exists=True,
            expected_post_sha256="post",
            expected_post_source="supplied",
            operation_target=True,
            operation_precondition_matches_manifest=True,
            matches_pre_state=True if pre else False,
            matches_expected_post_state=True if post else False,
            drift_detected=True if classification == "DRIFT" else False,
            classification=classification,
            missing_evidence=[],
        )

    def make_evidence(self, classifications, **overrides):
        values = {
            "evidence_version": 1,
            "task_id": "task_a",
            "microtask_id": "micro_a",
            "workspace_id": "ws_a",
            "workspace_root": "M:/workspace",
            "operation_id": "op_a",
            "operation_status": "STARTED",
            "operation_action": "edit",
            "operation_target": "file.py",
            "operation_request_fingerprint": "request_fp",
            "operation_expected_precondition_sha256": "pre",
            "operation_result_summary": None,
            "verification_evidence": None,
            "manifest_status": "VERIFIED",
            "snapshot_status": "VERIFIED",
            "evidence_complete": True,
            "expected_post_complete": True,
            "errors": [],
            "targets": [
                self.make_target(value, f"file_{index}.py")
                for index, value in enumerate(classifications)
            ],
        }
        values.update(overrides)
        return ReconciliationEvidence(**values)

    def test_exact_post_state_builds_full_report_without_replay(self):
        evidence = self.make_evidence(["EXPECTED_POST_STATE"])
        decision = ReconciliationDecisionEngine().decide(evidence)

        report = RecoveryReportBuilder().build(
            incident_id="incident_full",
            evidence=evidence,
            decision=decision,
            caller_error_class="result_delivery_failed",
            transport_evidence=[{"event_type": "RESULT_DELIVERY_FAILED"}],
            process_evidence=[{"process_id": 123}],
            process_restarted=False,
            checkpoint_identity={"checkpoint_id": "cp1"},
            accepted_as_already_done=["file_0.py"],
        )

        self.assertEqual(report.side_effect_scope, SideEffectScope.FULL)
        self.assertEqual(report.reconciliation_decision, ADOPT_CURRENT_STATE)
        self.assertEqual(report.accepted_as_already_done, ["file_0.py"])
        self.assertEqual(report.actually_retried, [])
        self.assertEqual(report.actually_rolled_back, [])
        self.assertEqual(report.next_safe_action, decision.next_safe_action)
        self.assertFalse(report.automatic_mutation_authorized)

    def test_all_pre_state_is_none(self):
        evidence = self.make_evidence(["PRE_STATE"])
        report = RecoveryReportBuilder().build(
            incident_id="incident_none",
            evidence=evidence,
            decision=None,
            next_safe_action="await authoritative reconciliation",
        )
        self.assertEqual(report.side_effect_scope, SideEffectScope.NONE)
        self.assertIsNone(report.reconciliation_decision)

    def test_mixed_known_state_is_partial(self):
        evidence = self.make_evidence(
            ["PRE_STATE", "EXPECTED_POST_STATE"]
        )
        decision = ReconciliationDecisionEngine().decide(evidence)
        report = RecoveryReportBuilder().build(
            incident_id="incident_partial",
            evidence=evidence,
            decision=decision,
        )
        self.assertEqual(report.side_effect_scope, SideEffectScope.PARTIAL)

    def test_drift_or_incomplete_evidence_is_ambiguous(self):
        drift = self.make_evidence(["DRIFT"])
        incomplete = self.make_evidence(
            ["PRE_STATE"],
            evidence_complete=False,
            errors=["snapshot missing"],
        )
        first = RecoveryReportBuilder().build(
            incident_id="incident_drift",
            evidence=drift,
            decision=None,
            next_safe_action="manual review",
        )
        second = RecoveryReportBuilder().build(
            incident_id="incident_incomplete",
            evidence=incomplete,
            decision=None,
            next_safe_action="manual review",
        )
        self.assertEqual(first.side_effect_scope, SideEffectScope.AMBIGUOUS)
        self.assertEqual(second.side_effect_scope, SideEffectScope.AMBIGUOUS)

    def test_missing_decision_requires_explicit_next_safe_action(self):
        evidence = self.make_evidence(["PRE_STATE"])
        with self.assertRaises(RecoveryReportBuilderError):
            RecoveryReportBuilder().build(
                incident_id="incident_missing_decision",
                evidence=evidence,
                decision=None,
            )

    def test_mismatched_decision_is_rejected_fail_closed(self):
        evidence = self.make_evidence(["EXPECTED_POST_STATE"])
        decision = ReconciliationDecisionEngine().decide(evidence)
        changed = self.make_evidence(
            ["PRE_STATE"],
            operation_status="INTENT",
        )
        with self.assertRaises(RecoveryReportBuilderError):
            RecoveryReportBuilder().build(
                incident_id="incident_mismatch",
                evidence=changed,
                decision=decision,
            )

    def test_action_facts_are_never_inferred_from_decision(self):
        evidence = self.make_evidence(["EXPECTED_POST_STATE"])
        decision = ReconciliationDecisionEngine().decide(evidence)
        report = RecoveryReportBuilder().build(
            incident_id="incident_actions",
            evidence=evidence,
            decision=decision,
        )

        self.assertEqual(report.accepted_as_already_done, [])
        self.assertEqual(report.actually_retried, [])
        self.assertEqual(report.actually_rolled_back, [])

    def test_target_summary_preserves_pre_current_and_expected_evidence(self):
        evidence = self.make_evidence(["EXPECTED_POST_STATE"])
        decision = ReconciliationDecisionEngine().decide(evidence)
        report = RecoveryReportBuilder().build(
            incident_id="incident_target",
            evidence=evidence,
            decision=decision,
        )
        target = report.affected_targets[0]
        self.assertEqual(target.pre_state["sha256"], "pre")
        self.assertEqual(target.current_state["sha256"], "post")
        self.assertEqual(target.expected_post_state["sha256"], "post")
        self.assertEqual(
            target.evidence_identity["classification"],
            "EXPECTED_POST_STATE",
        )


if __name__ == "__main__":
    unittest.main()
