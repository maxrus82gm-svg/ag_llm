import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from web_alarm.operation_store import OperationStore
from web_alarm.recovery_report_service import RecoveryReportService
from web_alarm.recovery_report_store import RecoveryReportStore
from web_alarm.server import WebAlarmApi
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RecoveryReportAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_acceptance",
        )
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task(
            "ws_acceptance",
            "Acceptance",
            "RAW TASK",
            "Recovery Report acceptance matrix",
            task_id="task_acceptance",
        )
        self.tasks.create_microtask(
            "task_acceptance",
            "M1",
            "Recovery acceptance",
            microtask_id="m1",
        )
        self.machine = ServerStateMachine(self.storage)
        self.operations = OperationStore(self.storage)
        self.api = WebAlarmApi(self.storage)
        self.service = RecoveryReportService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def prepare(self, targets):
        specs = []
        for name, before in targets.items():
            (self.project / name).write_bytes(before)
            specs.append((name, "edit"))
        self.machine.prepare_microtask(
            "task_acceptance",
            "m1",
            specs,
            operation_id="prepare_m1",
        )

    def begin(self, target, before, operation_id, status="INTENT"):
        self.operations.begin(
            "task_acceptance",
            "m1",
            "write",
            target,
            operation_id=operation_id,
            expected_precondition_sha256=sha256(before),
            request_payload={"case": operation_id},
        )
        if status != "INTENT":
            self.operations.transition(
                "task_acceptance",
                operation_id,
                status,
            )

    def post_transport(self, event_type, event_id, operation_id, **extra):
        body = {
            "event_type": event_type,
            "event_id": event_id,
            "task_id": "task_acceptance",
            "microtask_id": "m1",
            "operation_id": operation_id,
            "error_class": event_type.lower(),
        }
        body.update(extra)
        status, payload = self.api.dispatch(
            "POST",
            "/transport/events",
            body,
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["authority"], "evidence_only")
        self.assertFalse(payload["workflow_mutation_performed"])

    def expected(self, **values):
        return {
            name: {"exists": True, "sha256": sha256(content)}
            for name, content in values.items()
        }

    def test_disconnect_before_mutation_is_none_and_not_retried(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_none", status="INTENT")

        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_none",
            incident_id="incident_none",
            expected_post_state=self.expected(**{"file.txt": after}),
        )

        self.assertEqual(report.side_effect_scope.value, "none")
        self.assertEqual(report.reconciliation_decision, "RETRY_SAFE")
        self.assertEqual(report.actually_retried, [])
        self.assertEqual(
            self.operations.get("task_acceptance", "op_none").status.value,
            "INTENT",
        )

    def test_partial_execution_is_partial_without_automatic_rollback(self):
        before_a, before_b = b"before-a", b"before-b"
        after_a, after_b = b"after-a", b"after-b"
        self.prepare({"a.txt": before_a, "b.txt": before_b})
        self.begin("a.txt", before_a, "op_partial", status="STARTED")
        (self.project / "a.txt").write_bytes(after_a)
        workspace_before = {
            "a.txt": (self.project / "a.txt").read_bytes(),
            "b.txt": (self.project / "b.txt").read_bytes(),
        }

        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_partial",
            incident_id="incident_partial",
            expected_post_state=self.expected(
                **{"a.txt": after_a, "b.txt": after_b}
            ),
        )

        self.assertEqual(report.side_effect_scope.value, "partial")
        self.assertEqual(
            report.reconciliation_decision,
            "ROLLBACK_CURRENT_MICROTASK",
        )
        self.assertEqual(report.actually_rolled_back, [])
        self.assertEqual(
            {
                "a.txt": (self.project / "a.txt").read_bytes(),
                "b.txt": (self.project / "b.txt").read_bytes(),
            },
            workspace_before,
        )

    def test_full_lost_result_is_full_and_accepted_without_replay(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_full", status="STARTED")
        (self.project / "file.txt").write_bytes(after)
        self.post_transport(
            "MESSAGE_DELIVERY_TIMEOUT",
            "event_timeout",
            "op_full",
        )
        operation_before = self.operations.get(
            "task_acceptance",
            "op_full",
        )

        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_full",
            incident_id="incident_full",
            caller_error_class="message_delivery_timeout",
            expected_post_state=self.expected(**{"file.txt": after}),
            accepted_as_already_done=["file.txt"],
        )

        self.assertEqual(report.side_effect_scope.value, "full")
        self.assertEqual(report.reconciliation_decision, "ADOPT_CURRENT_STATE")
        self.assertEqual(report.accepted_as_already_done, ["file.txt"])
        self.assertEqual(report.actually_retried, [])
        self.assertEqual(
            self.operations.get("task_acceptance", "op_full"),
            operation_before,
        )
        self.assertEqual((self.project / "file.txt").read_bytes(), after)

    def test_unknown_then_remote_recovered_remains_unknown_until_reconciliation(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_unknown", status="STARTED")
        self.operations.transition(
            "task_acceptance",
            "op_unknown",
            "UNKNOWN_AFTER_DISCONNECT",
        )
        self.post_transport(
            "REMOTE_OFFLINE",
            "event_offline",
            "op_unknown",
        )
        self.post_transport(
            "REMOTE_RECOVERED",
            "event_recovered",
            "op_unknown",
        )

        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_unknown",
            incident_id="incident_unknown",
            expected_post_state=self.expected(**{"file.txt": after}),
        )

        self.assertEqual(report.side_effect_scope.value, "none")
        self.assertEqual(report.reconciliation_decision, "RETRY_SAFE")
        self.assertEqual(
            self.operations.get(
                "task_acceptance",
                "op_unknown",
            ).status.value,
            "UNKNOWN_AFTER_DISCONNECT",
        )
        self.assertEqual(
            [item["event_type"] for item in report.transport_evidence],
            ["REMOTE_OFFLINE", "REMOTE_RECOVERED"],
        )

    def test_process_restart_is_evidence_only(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_restart", status="STARTED")
        operation_before = self.operations.get(
            "task_acceptance",
            "op_restart",
        )
        checkpoint_before = self.api.state.read_checkpoint("task_acceptance")
        self.post_transport(
            "PROCESS_RESTARTED",
            "event_restart",
            "op_restart",
            process_id=2222,
            process_start_time="2026-10-02T21:00:00+05:00",
        )

        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_restart",
            incident_id="incident_restart",
            expected_post_state=self.expected(**{"file.txt": after}),
            process_restarted=True,
            process_evidence=[{"process_id": 2222}],
        )

        self.assertFalse(report.automatic_mutation_authorized)
        self.assertTrue(report.process_restarted)
        self.assertEqual(
            self.operations.get("task_acceptance", "op_restart"),
            operation_before,
        )
        self.assertEqual(
            self.api.state.read_checkpoint("task_acceptance"),
            checkpoint_before,
        )

    def test_result_delivery_failed_partial_state_is_reported_not_rolled_back(self):
        before_a, before_b = b"before-a", b"before-b"
        after_a, after_b = b"after-a", b"after-b"
        self.prepare({"a.txt": before_a, "b.txt": before_b})
        self.begin("a.txt", before_a, "op_result_partial", status="STARTED")
        (self.project / "a.txt").write_bytes(after_a)
        self.post_transport(
            "RESULT_DELIVERY_FAILED",
            "event_result_failed",
            "op_result_partial",
        )
        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_result_partial",
            incident_id="incident_result_partial",
            expected_post_state=self.expected(
                **{"a.txt": after_a, "b.txt": after_b}
            ),
        )

        self.assertEqual(report.side_effect_scope.value, "partial")
        self.assertEqual(report.actually_rolled_back, [])
        self.assertEqual((self.project / "a.txt").read_bytes(), after_a)
        self.assertEqual((self.project / "b.txt").read_bytes(), before_b)

    def test_drift_is_ambiguous_and_fail_closed(self):
        before, expected, drift = b"before", b"expected", b"third-party"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_drift", status="STARTED")
        (self.project / "file.txt").write_bytes(drift)

        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_drift",
            incident_id="incident_drift",
            expected_post_state=self.expected(**{"file.txt": expected}),
        )
        self.assertEqual(report.side_effect_scope.value, "ambiguous")
        self.assertEqual(
            report.reconciliation_decision,
            "MANUAL_REVIEW_REQUIRED",
        )
        self.assertEqual(report.actually_retried, [])
        self.assertEqual(report.actually_rolled_back, [])
        self.assertEqual((self.project / "file.txt").read_bytes(), drift)

    def test_duplicate_operation_and_report_are_idempotent(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_duplicate", status="STARTED")
        replay = self.operations.begin(
            "task_acceptance",
            "m1",
            "write",
            "file.txt",
            operation_id="op_duplicate",
            expected_precondition_sha256=sha256(before),
            request_payload={"case": "op_duplicate"},
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["replay_decision"], "RECONCILE_REQUIRED")
        self.assertEqual(len(self.operations.list("task_acceptance")), 1)

        first = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_duplicate",
            incident_id="incident_duplicate",
            expected_post_state=self.expected(**{"file.txt": after}),
            report_id="report_duplicate",
        )
        second = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_duplicate",
            incident_id="incident_duplicate",
            expected_post_state=self.expected(**{"file.txt": after}),
            report_id="report_duplicate",
        )

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(
            len(RecoveryReportStore(self.storage).list_reports("task_acceptance")),
            1,
        )

    def test_out_of_order_transport_is_preserved_as_evidence_not_authority(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_order", status="STARTED")
        for event_type, event_id in (
            ("REMOTE_RECOVERED", "event_1"),
            ("REMOTE_OFFLINE", "event_2"),
            ("REMOTE_ONLINE", "event_3"),
        ):
            self.post_transport(event_type, event_id, "op_order")
        operation_before = self.operations.get("task_acceptance", "op_order")
        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_order",
            incident_id="incident_order",
            expected_post_state=self.expected(**{"file.txt": after}),
        )

        self.assertEqual(
            [item["event_type"] for item in report.transport_evidence],
            ["REMOTE_RECOVERED", "REMOTE_OFFLINE", "REMOTE_ONLINE"],
        )
        self.assertFalse(report.automatic_mutation_authorized)
        self.assertEqual(
            self.operations.get("task_acceptance", "op_order"),
            operation_before,
        )

    def test_fresh_process_reads_same_decision_scope_and_next_action(self):
        before, after = b"before", b"after"
        self.prepare({"file.txt": before})
        self.begin("file.txt", before, "op_process", status="STARTED")
        (self.project / "file.txt").write_bytes(after)
        report = self.service.create_report(
            task_id="task_acceptance",
            microtask_id="m1",
            operation_id="op_process",
            incident_id="incident_process",
            expected_post_state=self.expected(**{"file.txt": after}),
            accepted_as_already_done=["file.txt"],
            fresh_process_reopen_result="PASS",
        )
        code = (
            "import json; "
            "from web_alarm.recovery_report_store import RecoveryReportStore; "
            f"r=RecoveryReportStore(r'{self.storage}').get('task_acceptance','{report.report_id}'); "
            "print(json.dumps(r.to_dict(), ensure_ascii=False))"
        )
        output = subprocess.check_output(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parent,
            text=True,
            encoding="utf-8",
        )
        reopened = json.loads(output)

        self.assertEqual(
            reopened["reconciliation_decision"],
            report.reconciliation_decision,
        )
        self.assertEqual(
            reopened["side_effect_scope"],
            report.side_effect_scope.value,
        )
        self.assertEqual(
            reopened["next_safe_action"],
            report.next_safe_action,
        )
        self.assertEqual(
            reopened["fresh_process_reopen_result"],
            "PASS",
        )


if __name__ == "__main__":
    unittest.main()
