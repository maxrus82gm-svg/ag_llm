import tempfile
import unittest
from pathlib import Path

from web_alarm.operation_store import (
    OperationConflictError,
    OperationStore,
    OperationTransitionError,
)
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.workspace_registry import WorkspaceRegistry
from web_alarm.task_store import TaskStore


class OperationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.marker = self.project / "marker.txt"
        self.marker.write_text("before", encoding="utf-8")

        workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_ops",
        )
        tasks = TaskStore(self.storage)
        self.task = tasks.create_task(
            workspace.workspace_id,
            "Operation Task",
            "RAW TASK",
            "Exercise replay identity",
            task_id="task_ops",
        )
        self.micro = tasks.create_microtask(
            self.task.task_id,
            "M1",
            "Operation step",
            microtask_id="m1",
        )
        self.store = OperationStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def begin(self, **overrides):
        values = {
            "task_id": self.task.task_id,
            "microtask_id": self.micro.microtask_id,
            "action": "write",
            "target": "marker.txt",
            "operation_id": "op_stable",
            "expected_precondition_sha256": "abc123",
            "request_payload": {"content": "after", "mode": "rewrite"},
        }
        values.update(overrides)
        return self.store.begin(**values)

    def test_new_intent_is_persistent_and_does_not_touch_real_workspace(self):
        before = self.marker.read_bytes()

        result = self.begin()

        self.assertTrue(result["created"])
        self.assertFalse(result["replayed"])
        self.assertEqual(result["operation"].status.value, "INTENT")
        self.assertEqual(result["replay_decision"], "RETURN_EXISTING_INTENT")
        self.assertEqual(self.marker.read_bytes(), before)

        reopened = OperationStore(self.storage).get("task_ops", "op_stable")
        self.assertEqual(reopened.operation_id, "op_stable")
        self.assertEqual(
            reopened.request_fingerprint,
            result["operation"].request_fingerprint,
        )

    def test_same_operation_id_and_request_is_idempotent_replay(self):
        first = self.begin(
            request_payload={"mode": "rewrite", "content": "after"},
        )
        second = OperationStore(self.storage).begin(
            "task_ops",
            "m1",
            "write",
            "marker.txt",
            operation_id="op_stable",
            expected_precondition_sha256="abc123",
            request_payload={"content": "after", "mode": "rewrite"},
        )

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertTrue(second["replayed"])
        self.assertEqual(second["operation"].status.value, "INTENT")
        operation_files = list(
            (self.storage / "tasks" / "active" / "task_ops" / "operations").glob("*.json")
        )
        self.assertEqual(len(operation_files), 1)

    def test_same_operation_id_with_different_request_fails_closed(self):
        self.begin()

        with self.assertRaises(OperationConflictError):
            self.begin(request_payload={"content": "DIFFERENT", "mode": "rewrite"})

        current = self.store.get("task_ops", "op_stable")
        self.assertEqual(current.status.value, "INTENT")
        self.assertEqual(self.marker.read_text(encoding="utf-8"), "before")

    def test_lifecycle_is_forward_only_and_terminal_replay_is_idempotent(self):
        self.begin()

        started = self.store.transition("task_ops", "op_stable", "STARTED")
        self.assertEqual(started["operation"].status.value, "STARTED")
        done = self.store.transition(
            "task_ops",
            "op_stable",
            "DONE",
            result_summary="mutation reported complete",
        )
        self.assertEqual(done["operation"].status.value, "DONE")
        verified = self.store.transition(
            "task_ops",
            "op_stable",
            "VERIFIED",
            result_summary="post-state verified",
        )
        self.assertEqual(verified["operation"].status.value, "VERIFIED")

        replay = self.store.transition("task_ops", "op_stable", "VERIFIED")
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["changed"])
        self.assertEqual(replay["replay_decision"], "RETURN_KNOWN_STATE")

        with self.assertRaises(OperationTransitionError):
            self.store.transition("task_ops", "op_stable", "STARTED")

    def test_started_and_unknown_replay_require_reconciliation(self):
        self.begin()
        self.store.transition("task_ops", "op_stable", "STARTED")

        replay = self.begin()
        self.assertEqual(replay["replay_decision"], "RECONCILE_REQUIRED")

        self.store.transition(
            "task_ops",
            "op_stable",
            "UNKNOWN_AFTER_DISCONNECT",
        )
        unknown = self.begin()
        self.assertEqual(
            unknown["operation"].status.value,
            "UNKNOWN_AFTER_DISCONNECT",
        )
        self.assertEqual(unknown["replay_decision"], "RECONCILE_REQUIRED")

        with self.assertRaises(OperationTransitionError):
            self.store.transition("task_ops", "op_stable", "DONE")

    def test_read_only_list_does_not_create_operations_directory(self):
        operations_dir = (
            self.storage / "tasks" / "active" / "task_ops" / "operations"
        )
        self.assertFalse(operations_dir.exists())

        self.assertEqual(self.store.list("task_ops"), [])

        self.assertFalse(operations_dir.exists())

    def test_server_operation_endpoints_preserve_replay_identity(self):
        api = WebAlarmApi(self.storage)
        before = self.marker.read_bytes()
        body = {
            "microtask_id": "m1",
            "action": "write",
            "target": "marker.txt",
            "operation_id": "op_api",
            "expected_precondition_sha256": "abc123",
            "request": {"content": "after"},
        }

        status, first = api.dispatch("POST", "/tasks/task_ops/operations", body)
        self.assertEqual(status, 201)
        self.assertTrue(first["created"])

        status, replay = api.dispatch("POST", "/tasks/task_ops/operations", body)
        self.assertEqual(status, 200)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["operation"]["operation_id"], "op_api")

        status, started = api.dispatch(
            "POST",
            "/tasks/task_ops/operations/op_api/transition",
            {"target_status": "STARTED"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(started["replay_decision"], "RECONCILE_REQUIRED")

        status, inspected = api.dispatch(
            "GET",
            "/tasks/task_ops/operations/op_api",
        )
        self.assertEqual(status, 200)
        self.assertEqual(inspected["operation"]["status"], "STARTED")
        self.assertEqual(inspected["replay_decision"], "RECONCILE_REQUIRED")
        self.assertEqual(self.marker.read_bytes(), before)

    def test_server_conflicting_replay_returns_409(self):
        api = WebAlarmApi(self.storage)
        base = {
            "microtask_id": "m1",
            "action": "write",
            "target": "marker.txt",
            "operation_id": "op_conflict",
            "request": {"content": "one"},
        }
        api.dispatch("POST", "/tasks/task_ops/operations", base)

        conflicting = dict(base)
        conflicting["request"] = {"content": "two"}
        with self.assertRaises(ApiError) as caught:
            api.dispatch("POST", "/tasks/task_ops/operations", conflicting)

        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(caught.exception.code, "operation_replay_conflict")


if __name__ == "__main__":
    unittest.main()
