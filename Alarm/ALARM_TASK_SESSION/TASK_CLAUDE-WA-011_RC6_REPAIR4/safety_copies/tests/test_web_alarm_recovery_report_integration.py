import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from web_alarm.context_pack import EntryContextPackBuilder
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.remote_entry import RemoteEntry
from web_alarm.recovery_report_service import RecoveryReportService
from web_alarm.resolver_service import ResolverService
from web_alarm.server import WebAlarmApi
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.transport_event_store import TransportEventStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RecoveryReportIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.target = self.project / "file.txt"
        self.before = b"before"
        self.after = b"after"
        self.target.write_bytes(self.before)

        workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_report",
        )
        tasks = TaskStore(self.storage)
        tasks.create_task(
            workspace.workspace_id,
            "Recovery report integration",
            "RAW TASK",
            "Persist recovery report.",
            task_id="task_report",
        )
        tasks.create_microtask(
            "task_report",
            "M1",
            "Recovery integration",
            microtask_id="m1",
        )
        ServerStateMachine(self.storage).prepare_microtask(
            "task_report",
            "m1",
            [("file.txt", "edit")],
            operation_id="prepare_m1",
        )
        operations = OperationStore(self.storage)
        operations.begin(
            "task_report",
            "m1",
            "write",
            "file.txt",
            operation_id="op_write",
            expected_precondition_sha256=sha256(self.before),
            request_payload={"content": "after"},
            payload=self.after,
        )
        operations.transition("task_report", "op_write", "STARTED")
        TransportEventStore(self.storage).append(
            "RESULT_DELIVERY_FAILED",
            task_id="task_report",
            microtask_id="m1",
            operation_id="op_write",
            error_class="result_delivery_failed",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def adopt(self):
        # RC-2: accepted_as_already_done must come from a tracked ADOPT.
        decision = ReconciliationService(self.storage).reconcile(
            "task_report", "m1", "op_write"
        )["DECISION"]
        result = ResolverService(self.storage).apply(
            "task_report",
            "m1",
            "op_write",
            "ADOPT",
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=OperationStore(self.storage).get("task_report", "op_write").revision,
        )
        self.assertTrue(result["accepted"])

    def expected_post(self):
        return {
            "file.txt": {
                "exists": True,
                "sha256": sha256(self.after),
            }
        }
    def test_service_persists_full_report_without_workflow_mutation(self):
        self.target.write_bytes(self.after)
        self.adopt()
        before = self.target.read_bytes()
        operation_before = OperationStore(self.storage).get(
            "task_report",
            "op_write",
        ).status

        report = RecoveryReportService(self.storage).create_report(
            task_id="task_report",
            microtask_id="m1",
            operation_id="op_write",
            incident_id="incident_service",
            caller_error_class="result_delivery_failed",
            expected_post_state=self.expected_post(),
            accepted_as_already_done=["file.txt"],
        )

        self.assertEqual(report.side_effect_scope.value, "full")
        self.assertEqual(report.reconciliation_decision, "ADOPT_CURRENT_STATE")
        self.assertEqual(report.accepted_as_already_done, ["file.txt"])
        self.assertEqual(report.actually_retried, [])
        self.assertTrue(report.transport_evidence)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(
            OperationStore(self.storage).get("task_report", "op_write").status,
            operation_before,
        )
    def test_server_post_and_get_survive_new_api_instance(self):
        self.target.write_bytes(self.after)
        self.adopt()
        body = {
            "incident_id": "incident_http",
            "microtask_id": "m1",
            "operation_id": "op_write",
            "caller_error_class": "result_delivery_failed",
            "expected_post_state": self.expected_post(),
            "accepted_as_already_done": ["file.txt"],
        }
        status, created = WebAlarmApi(self.storage).dispatch(
            "POST",
            "/tasks/task_report/recovery-reports",
            body,
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["authority"], "evidence_only")
        self.assertFalse(created["workflow_mutation_performed"])
        report_id = created["report"]["report_id"]

        status, loaded = WebAlarmApi(self.storage).dispatch(
            "GET",
            f"/tasks/task_report/recovery-reports?report_id={report_id}",
        )
        self.assertEqual(status, 200)
        self.assertEqual(loaded["report"]["report_id"], report_id)
        self.assertEqual(loaded["report"]["side_effect_scope"], "full")

    def test_context_pack_and_remote_entry_surface_latest_report(self):
        self.target.write_bytes(self.after)
        report = RecoveryReportService(self.storage).create_report(
            task_id="task_report",
            microtask_id="m1",
            operation_id="op_write",
            incident_id="incident_context",
            expected_post_state=self.expected_post(),
        )

        pack = EntryContextPackBuilder(self.storage).build("task_report")
        entry = RemoteEntry(self.storage).enter("task_report")

        self.assertEqual(
            pack["LATEST_RECOVERY_REPORT"]["report_id"],
            report.report_id,
        )
        self.assertEqual(
            entry["CONTEXT_PACK"]["LATEST_RECOVERY_REPORT"]["report_id"],
            report.report_id,
        )

    def test_status_advertises_recovery_reports(self):
        status, payload = WebAlarmApi(self.storage).dispatch("GET", "/status")
        self.assertEqual(status, 200)
        self.assertIn("recovery_reports", payload["capabilities"])

    def test_invalid_server_payload_fails_closed(self):
        with self.assertRaises(Exception):
            WebAlarmApi(self.storage).dispatch(
                "POST",
                "/tasks/task_report/recovery-reports",
                {
                    "incident_id": "incident_bad",
                    "microtask_id": "m1",
                    "operation_id": "op_write",
                    "process_restarted": "yes",
                },
            )

    def test_fresh_python_process_reads_same_persisted_report(self):
        self.target.write_bytes(self.after)
        report = RecoveryReportService(self.storage).create_report(
            task_id="task_report",
            microtask_id="m1",
            operation_id="op_write",
            incident_id="incident_process",
            expected_post_state=self.expected_post(),
        )
        code = (
            "import json; "
            "from web_alarm.recovery_report_store import RecoveryReportStore; "
            f"r=RecoveryReportStore(r'{self.storage}').get('task_report','{report.report_id}'); "
            "print(json.dumps(r.to_dict(), ensure_ascii=False))"
        )
        output = subprocess.check_output(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parent,
            text=True,
            encoding="utf-8",
        )
        loaded = json.loads(output)
        self.assertEqual(loaded["report_id"], report.report_id)
        self.assertEqual(
            loaded["reconciliation_decision"],
            report.reconciliation_decision,
        )
        self.assertEqual(
            loaded["next_safe_action"],
            report.next_safe_action,
        )


if __name__ == "__main__":
    unittest.main()
