import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from web_alarm.context_pack import EntryContextPackBuilder
from web_alarm.operation_store import OperationStore
from web_alarm.remote_entry import RemoteEntry
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ReconciliationIntegrationTests(unittest.TestCase):
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
            workspace_id="ws_integration",
        )
        tasks = TaskStore(self.storage)
        self.task = tasks.create_task(
            workspace.workspace_id,
            "Integration Task",
            "RAW TASK",
            "Exercise reconciliation integration.",
            task_id="task_integration",
        )
        self.micro = tasks.create_microtask(
            self.task.task_id,
            "M1",
            "Integration recovery",
            microtask_id="m1",
        )
        ServerStateMachine(self.storage).prepare_microtask(
            self.task.task_id,
            self.micro.microtask_id,
            [("file.txt", "edit")],
            operation_id="prepare_m1",
        )
        operations = OperationStore(self.storage)
        operations.begin(
            self.task.task_id,
            self.micro.microtask_id,
            "write",
            "file.txt",
            operation_id="op_write",
            expected_precondition_sha256=sha256(self.before),
            request_payload={"content": "after"},
        )
        operations.transition(
            self.task.task_id,
            "op_write",
            "STARTED",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def expected_post(self):
        return {
            "file.txt": {
                "exists": True,
                "sha256": sha256(self.after),
            }
        }

    def test_context_pack_surfaces_reconciliation_and_authoritative_next_action(self):
        original = self.target.read_bytes()

        pack = EntryContextPackBuilder(self.storage).build(
            self.task.task_id
        )

        self.assertIsNotNone(pack["RECONCILIATION"])
        self.assertEqual(
            pack["RECONCILIATION"]["DECISION"]["decision"],
            "MANUAL_REVIEW_REQUIRED",
        )
        self.assertEqual(
            pack["NEXT_SAFE_ACTION"],
            pack["RECONCILIATION"]["NEXT_SAFE_ACTION"],
        )
        self.assertIn(
            "RECONCILIATION DECISION: MANUAL_REVIEW_REQUIRED",
            pack["CONTEXT_TEXT"],
        )
        self.assertIn("CHECKPOINT_NEXT_SAFE_ACTION", pack)
        self.assertEqual(self.target.read_bytes(), original)

    def test_remote_entry_returns_reconciliation_ready_without_mutation(self):
        original = self.target.read_bytes()

        entry = RemoteEntry(self.storage).enter(self.task.task_id)

        self.assertEqual(entry["ENTRY_STATE"], "RECONCILIATION_READY")
        self.assertEqual(
            entry["RECOVERY_DECISION"],
            "MANUAL_REVIEW_REQUIRED",
        )
        self.assertTrue(entry["RECOVERY_REVIEW_REQUIRED"])
        self.assertEqual(
            entry["MUTATION_DECISION"],
            "FOLLOW_RECONCILIATION_NEXT_SAFE_ACTION",
        )
        self.assertIsNotNone(entry["RECONCILIATION"])
        self.assertTrue(entry["READ_ONLY"])
        self.assertEqual(self.target.read_bytes(), original)

    def test_server_reconcile_with_exact_post_proves_retry_safe_at_pre_state(self):
        api = WebAlarmApi(self.storage)
        original = self.target.read_bytes()

        status, payload = api.dispatch(
            "POST",
            "/tasks/task_integration/reconcile",
            {
                "microtask_id": "m1",
                "operation_id": "op_write",
                "expected_post_state": self.expected_post(),
            },
        )

        self.assertEqual(status, 200)
        self.assertFalse(payload["MUTATION_PERFORMED"])
        self.assertEqual(
            payload["DECISION"]["decision"],
            "RETRY_SAFE",
        )
        self.assertEqual(
            payload["DECISION"]["reason_code"],
            "PRE_STATE_AND_POST_NOT_REACHED",
        )
        self.assertEqual(self.target.read_bytes(), original)

    def test_server_reconcile_adopts_exact_post_without_reexecuting_mutation(self):
        self.target.write_bytes(self.after)
        api = WebAlarmApi(self.storage)
        current = self.target.read_bytes()

        status, payload = api.dispatch(
            "POST",
            "/tasks/task_integration/reconcile",
            {
                "microtask_id": "m1",
                "operation_id": "op_write",
                "expected_post_state": self.expected_post(),
            },
        )

        self.assertEqual(status, 200)
        self.assertFalse(payload["MUTATION_PERFORMED"])
        self.assertEqual(
            payload["DECISION"]["decision"],
            "ADOPT_CURRENT_STATE",
        )
        self.assertEqual(self.target.read_bytes(), current)

    def test_real_http_reconcile_endpoint_is_read_only(self):
        api = WebAlarmApi(self.storage)
        server = create_server(api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        original = self.target.read_bytes()
        body = json.dumps(
            {
                "microtask_id": "m1",
                "operation_id": "op_write",
                "expected_post_state": self.expected_post(),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://{host}:{port}/tasks/task_integration/reconcile",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

        self.assertFalse(payload["MUTATION_PERFORMED"])
        self.assertEqual(payload["DECISION"]["decision"], "RETRY_SAFE")
        self.assertEqual(self.target.read_bytes(), original)

    def test_reconciliation_result_survives_new_server_instance(self):
        body = {
            "microtask_id": "m1",
            "operation_id": "op_write",
            "expected_post_state": self.expected_post(),
        }

        first = WebAlarmApi(self.storage).dispatch(
            "POST",
            "/tasks/task_integration/reconcile",
            body,
        )[1]
        second = WebAlarmApi(self.storage).dispatch(
            "POST",
            "/tasks/task_integration/reconcile",
            body,
        )[1]

        self.assertEqual(first["DECISION"], second["DECISION"])
        self.assertEqual(first["EVIDENCE"], second["EVIDENCE"])

    def test_normal_task_without_inflight_operation_has_no_reconciliation(self):
        other_project = self.root / "other_project"
        other_project.mkdir()
        workspace = WorkspaceRegistry(self.storage).register(
            "Other",
            other_project,
            workspace_id="ws_other",
        )
        tasks = TaskStore(self.storage)
        task = tasks.create_task(
            workspace.workspace_id,
            "Normal Task",
            "RAW",
            "No recovery.",
            task_id="task_normal",
        )
        tasks.create_microtask(
            task.task_id,
            "M1",
            "Normal",
            microtask_id="normal_m1",
        )

        pack = EntryContextPackBuilder(self.storage).build(task.task_id)

        self.assertIsNone(pack["RECONCILIATION"])
        self.assertNotIn("CHECKPOINT_NEXT_SAFE_ACTION", pack)


if __name__ == "__main__":
    unittest.main()
