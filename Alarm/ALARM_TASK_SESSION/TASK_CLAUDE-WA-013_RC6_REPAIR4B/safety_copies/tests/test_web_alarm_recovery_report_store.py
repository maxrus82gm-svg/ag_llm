import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.models import SCHEMA_VERSION
from web_alarm.recovery_report_store import (
    RecoveryReportConflictError,
    RecoveryReportRecord,
    RecoveryReportStore,
    RecoveryReportStoreError,
    RecoveryTargetSummary,
    SideEffectScope,
)
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


class RecoveryReportStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        WorkspaceRegistry(self.storage).register(
            "fixture",
            self.workspace,
            workspace_id="ws_fixture",
        )
        TaskStore(self.storage).create_task(
            "ws_fixture",
            "Recovery fixture",
            "fixture raw task",
            "fixture goal",
            task_id="task_recovery",
        )
        self.store = RecoveryReportStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_report(self, **overrides):
        values = {
            "report_id": "report_001",
            "incident_id": "incident_001",
            "task_id": "task_recovery",
            "microtask_id": "micro_001",
            "operation_id": "op_001",
            "caller_error_class": "message_delivery_timeout",
            "transport_evidence": [
                {"event_id": "transport_001", "event_type": "MESSAGE_DELIVERY_TIMEOUT"}
            ],
            "process_evidence": [{"process_id": 1234, "alive": True}],
            "process_restarted": False,
            "last_persistent_operation_state": "DONE",
            "checkpoint_identity": {"checkpoint_id": "checkpoint_001"},
            "affected_targets": [
                RecoveryTargetSummary(
                    source_path="web_alarm/example.py",
                    pre_state={"sha256": "pre"},
                    current_state={"sha256": "post"},
                    expected_post_state={"sha256": "post"},
                    classification="EXPECTED_POST_STATE",
                    evidence_identity={"snapshot_id": "snapshot_001"},
                )
            ],
            "evidence_identity": {"evidence_fingerprint": "abc123"},
            "side_effect_scope": SideEffectScope.FULL,
            "reconciliation_decision": "ADOPT_CURRENT_STATE",
            "reconciliation_reason": "exact post-state proven",
            "accepted_as_already_done": ["web_alarm/example.py"],
            "actually_retried": [],
            "actually_rolled_back": [],
            "untouched_or_unresolved": [],
            "next_safe_action": "continue without replay",
            "fresh_process_reopen_result": None,
        }
        values.update(overrides)
        return RecoveryReportRecord(**values)

    def test_full_contract_round_trip_is_restart_safe(self):
        report = self.make_report()
        stored = self.store.append(report)

        reopened = RecoveryReportStore(self.storage)
        loaded = reopened.get("task_recovery", stored.report_id)
        self.assertEqual(loaded.to_dict(), report.to_dict())
        self.assertEqual(loaded.side_effect_scope, SideEffectScope.FULL)
        self.assertEqual(loaded.authority, "evidence_only")
        self.assertFalse(loaded.automatic_mutation_authorized)
        self.assertEqual(
            loaded.affected_targets[0].classification,
            "EXPECTED_POST_STATE",
        )

    def test_all_side_effect_scopes_are_supported(self):
        for index, scope in enumerate(SideEffectScope):
            report = self.make_report(
                report_id=f"report_{index}",
                incident_id=f"incident_{index}",
                side_effect_scope=scope,
            )
            self.store.append(report)

        loaded = self.store.list_reports("task_recovery")
        self.assertEqual(
            {item.side_effect_scope for item in loaded},
            set(SideEffectScope),
        )

    def test_invalid_scope_and_authority_are_rejected(self):
        with self.assertRaises(ValueError):
            self.make_report(side_effect_scope="unknown")
        with self.assertRaises(ValueError):
            self.make_report(authority="workflow_authority")
        with self.assertRaises(ValueError):
            self.make_report(automatic_mutation_authorized=True)
    def test_same_report_id_is_idempotent_but_conflict_fails_closed(self):
        report = self.make_report()
        first = self.store.append(report)
        second = self.store.append(self.make_report())

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(len(self.store.list_reports("task_recovery")), 1)

        with self.assertRaises(RecoveryReportConflictError):
            self.store.append(
                self.make_report(next_safe_action="different continuation")
            )

    def test_corrupted_report_fails_closed(self):
        report = self.store.append(self.make_report())
        path = self.store.report_path("task_recovery", report.report_id)
        path.write_text("not-json", encoding="utf-8")

        with self.assertRaises(RecoveryReportStoreError):
            RecoveryReportStore(self.storage).get(
                "task_recovery",
                report.report_id,
            )

    def test_unknown_schema_fails_closed(self):
        report = self.store.append(self.make_report())
        path = self.store.report_path("task_recovery", report.report_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["schema_version"] = SCHEMA_VERSION + 999
        path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(RecoveryReportStoreError):
            self.store.get("task_recovery", report.report_id)

    def test_store_does_not_mutate_task_plan_or_checkpoint(self):
        task_dir = TaskStore(self.storage).task_directory("task_recovery")
        task_before = (task_dir / "task.json").read_bytes()
        plan_before = (task_dir / "plan.json").read_bytes()

        self.store.append(self.make_report())

        self.assertEqual((task_dir / "task.json").read_bytes(), task_before)
        self.assertEqual((task_dir / "plan.json").read_bytes(), plan_before)
        self.assertFalse((self.storage / "checkpoints" / "task_recovery.json").exists())

    def test_unknown_task_is_rejected_without_persistence(self):
        report = self.make_report(task_id="missing_task")

        with self.assertRaises(RecoveryReportStoreError):
            self.store.append(report)

        self.assertFalse(
            (self.storage / "recovery_reports" / "missing_task").exists()
        )

    def test_blank_identity_and_non_json_evidence_are_rejected(self):
        with self.assertRaises(ValueError):
            self.make_report(incident_id=" ")
        with self.assertRaises(ValueError):
            self.make_report(transport_evidence=[{"bad": object()}])


if __name__ == "__main__":
    unittest.main()
