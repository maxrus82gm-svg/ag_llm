import hashlib
import tempfile
import unittest
from pathlib import Path

from web_alarm.server import WebAlarmApi


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class TransportAuthorityNegativeTests(unittest.TestCase):
    EVENT_TYPES = (
        "REMOTE_ONLINE",
        "REMOTE_OFFLINE",
        "REMOTE_RECOVERED",
        "RESULT_DELIVERY_FAILED",
        "MESSAGE_DELIVERY_TIMEOUT",
        "PROCESS_RESTARTED",
    )

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.api = WebAlarmApi(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def create_prepared_task(self, targets=None):
        targets = targets or [("target.txt", b"before")]
        self.api.dispatch(
            "POST",
            "/workspaces",
            {
                "display_name": "Project",
                "workspace_root": str(self.project),
                "workspace_id": "ws_authority",
            },
        )
        self.api.dispatch(
            "POST",
            "/tasks",
            {
                "workspace_id": "ws_authority",
                "title": "Authority",
                "raw_task": "RAW",
                "goal": "Transport must remain evidence-only",
                "task_id": "task_authority",
            },
        )
        self.api.dispatch(
            "POST",
            "/tasks/task_authority/microtasks",
            {
                "title": "M1",
                "goal": "Guard authority",
                "microtask_id": "m1",
            },
        )
        for name, content in targets:
            (self.project / name).write_bytes(content)
        self.api.dispatch(
            "POST",
            "/microtasks/m1/prepare",
            {
                "task_id": "task_authority",
                "targets": [
                    {"path": name, "expected_change": "edit"}
                    for name, _ in targets
                ],
                "operation_id": "prepare_authority",
            },
        )
        return "task_authority", "m1"
    def begin_unknown_operation(self, target="target.txt", operation_id="op_unknown"):
        before = (self.project / target).read_bytes()
        self.api.operations.begin(
            "task_authority",
            "m1",
            "write",
            target,
            operation_id=operation_id,
            expected_precondition_sha256=sha256(before),
            request_payload={"content": "after"},
        )
        self.api.operations.transition(
            "task_authority",
            operation_id,
            "STARTED",
        )
        self.api.operations.transition(
            "task_authority",
            operation_id,
            "UNKNOWN_AFTER_DISCONNECT",
        )

    def workflow_snapshot(self, operation_id=None):
        task_dir = self.api.tasks.task_directory("task_authority")
        checkpoint = self.api.state.read_checkpoint("task_authority")
        operation = (
            self.api.operations.get("task_authority", operation_id)
            if operation_id is not None
            else None
        )
        return {
            "task_tree": tree_snapshot(task_dir),
            "workspace": tree_snapshot(self.project),
            "checkpoint": checkpoint,
            "operation": operation,
        }

    def post_transport(self, event_type, event_id, operation_id=None):
        body = {
            "event_type": event_type,
            "event_id": event_id,
            "task_id": "task_authority",
            "microtask_id": "m1",
            "operation_id": operation_id,
            "remote_call_kind": "write_file",
            "error_class": event_type.lower(),
        }
        if event_type == "PROCESS_RESTARTED":
            body.update(
                process_id=9999,
                process_start_time="2026-10-02T18:00:00+05:00",
                payload={"previous_process_id": 8888},
            )
        status, payload = self.api.dispatch("POST", "/transport/events", body)
        self.assertEqual(status, 201)
        self.assertEqual(payload["authority"], "evidence_only")
        self.assertFalse(payload["workflow_mutation_performed"])

    def test_every_transport_event_leaves_workflow_workspace_and_unknown_operation_unchanged(self):
        self.create_prepared_task()
        self.begin_unknown_operation()
        baseline = self.workflow_snapshot("op_unknown")

        for index, event_type in enumerate(self.EVENT_TYPES):
            with self.subTest(event_type=event_type):
                self.post_transport(
                    event_type,
                    f"event_{index}",
                    operation_id="op_unknown",
                )
                self.assertEqual(
                    self.workflow_snapshot("op_unknown"),
                    baseline,
                )

        _, listed = self.api.dispatch(
            "GET",
            "/transport/events?operation_id=op_unknown",
        )
        self.assertEqual(len(listed["events"]), len(self.EVENT_TYPES))
        self.assertEqual(listed["authority"], "evidence_only")
        self.assertFalse(listed["workflow_mutation_performed"])

    def test_remote_recovered_does_not_resolve_unknown_or_change_reconciliation_decision(self):
        self.create_prepared_task()
        self.begin_unknown_operation()
        expected_post = {
            "target.txt": {
                "exists": True,
                "sha256": sha256(b"after"),
            }
        }
        before = self.api.reconciliation.reconcile(
            "task_authority",
            "m1",
            "op_unknown",
            expected_post_state=expected_post,
        )

        self.post_transport(
            "REMOTE_RECOVERED",
            "event_recovered_unknown",
            operation_id="op_unknown",
        )

        after = self.api.reconciliation.reconcile(
            "task_authority",
            "m1",
            "op_unknown",
            expected_post_state=expected_post,
        )
        operation = self.api.operations.get("task_authority", "op_unknown")

        self.assertEqual(operation.status.value, "UNKNOWN_AFTER_DISCONNECT")
        self.assertEqual(after["DECISION"], before["DECISION"])
        self.assertFalse(after["MUTATION_PERFORMED"])

    def test_message_delivery_timeout_after_real_post_state_does_not_adopt_or_transition(self):
        self.create_prepared_task()
        before_bytes = (self.project / "target.txt").read_bytes()
        self.api.operations.begin(
            "task_authority",
            "m1",
            "write",
            "target.txt",
            operation_id="op_done_but_reply_lost",
            expected_precondition_sha256=sha256(before_bytes),
            request_payload={"content": "after"},
        )
        self.api.operations.transition(
            "task_authority",
            "op_done_but_reply_lost",
            "STARTED",
        )
        (self.project / "target.txt").write_bytes(b"after")
        expected_post = {
            "target.txt": {
                "exists": True,
                "sha256": sha256(b"after"),
            }
        }
        decision_before = self.api.reconciliation.reconcile(
            "task_authority",
            "m1",
            "op_done_but_reply_lost",
            expected_post_state=expected_post,
        )
        operation_before = self.api.operations.get(
            "task_authority",
            "op_done_but_reply_lost",
        )

        self.post_transport(
            "MESSAGE_DELIVERY_TIMEOUT",
            "event_message_timeout",
            operation_id="op_done_but_reply_lost",
        )

        decision_after = self.api.reconciliation.reconcile(
            "task_authority",
            "m1",
            "op_done_but_reply_lost",
            expected_post_state=expected_post,
        )
        operation_after = self.api.operations.get(
            "task_authority",
            "op_done_but_reply_lost",
        )

        self.assertEqual(decision_before["DECISION"], decision_after["DECISION"])
        self.assertEqual(operation_before, operation_after)
        self.assertEqual(operation_after.status.value, "STARTED")
        self.assertEqual((self.project / "target.txt").read_bytes(), b"after")

    def test_result_delivery_failed_in_partial_state_does_not_rollback(self):
        self.create_prepared_task(
            [("a.txt", b"before-a"), ("b.txt", b"before-b")]
        )
        self.api.operations.begin(
            "task_authority",
            "m1",
            "write",
            "a.txt",
            operation_id="op_partial",
            expected_precondition_sha256=sha256(b"before-a"),
            request_payload={"content": "after-a"},
        )
        self.api.operations.transition(
            "task_authority",
            "op_partial",
            "STARTED",
        )
        (self.project / "a.txt").write_bytes(b"after-a")
        workspace_before = tree_snapshot(self.project)
        expected_post = {
            "a.txt": {"exists": True, "sha256": sha256(b"after-a")},
            "b.txt": {"exists": True, "sha256": sha256(b"after-b")},
        }
        decision_before = self.api.reconciliation.reconcile(
            "task_authority",
            "m1",
            "op_partial",
            expected_post_state=expected_post,
        )

        self.post_transport(
            "RESULT_DELIVERY_FAILED",
            "event_partial_result",
            operation_id="op_partial",
        )

        decision_after = self.api.reconciliation.reconcile(
            "task_authority",
            "m1",
            "op_partial",
            expected_post_state=expected_post,
        )
        self.assertEqual(decision_before["DECISION"], decision_after["DECISION"])
        self.assertEqual(tree_snapshot(self.project), workspace_before)
        self.assertEqual(
            self.api.operations.get("task_authority", "op_partial").status.value,
            "STARTED",
        )

    def test_process_restarted_does_not_finish_unfinished_operation_or_advance_microtask(self):
        self.create_prepared_task()
        before_micro = self.api.tasks.open_microtask("task_authority", "m1")
        self.api.operations.begin(
            "task_authority",
            "m1",
            "write",
            "target.txt",
            operation_id="op_restart",
            request_payload={"content": "after"},
        )
        self.api.operations.transition(
            "task_authority",
            "op_restart",
            "STARTED",
        )
        checkpoint_before = self.api.state.read_checkpoint("task_authority")

        self.post_transport(
            "PROCESS_RESTARTED",
            "event_process_restart",
            operation_id="op_restart",
        )

        after_micro = self.api.tasks.open_microtask("task_authority", "m1")
        after_op = self.api.operations.get("task_authority", "op_restart")
        checkpoint_after = self.api.state.read_checkpoint("task_authority")
        self.assertEqual(after_micro, before_micro)
        self.assertEqual(after_op.status.value, "STARTED")
        self.assertEqual(checkpoint_after, checkpoint_before)

    def test_duplicate_and_out_of_order_events_do_not_gain_authority(self):
        self.create_prepared_task()
        self.begin_unknown_operation()
        baseline = self.workflow_snapshot("op_unknown")

        order = [
            ("REMOTE_RECOVERED", "event_out_1"),
            ("REMOTE_OFFLINE", "event_out_2"),
            ("REMOTE_ONLINE", "event_out_3"),
            ("REMOTE_RECOVERED", "event_out_4"),
        ]
        for event_type, event_id in order:
            self.post_transport(event_type, event_id, operation_id="op_unknown")

        duplicate = {
            "event_type": "REMOTE_RECOVERED",
            "event_id": "event_out_4",
            "task_id": "task_authority",
            "microtask_id": "m1",
            "operation_id": "op_unknown",
            "remote_call_kind": "write_file",
            "error_class": "remote_recovered",
        }
        status, payload = self.api.dispatch("POST", "/transport/events", duplicate)
        self.assertEqual(status, 201)
        self.assertEqual(payload["authority"], "evidence_only")
        self.assertFalse(payload["workflow_mutation_performed"])
        self.assertEqual(self.workflow_snapshot("op_unknown"), baseline)

    def test_unbound_transport_events_cannot_create_or_activate_workflow(self):
        empty_tasks_before = tree_snapshot(self.storage / "tasks")
        status, payload = self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "REMOTE_ONLINE",
                "event_id": "event_unbound",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["authority"], "evidence_only")
        self.assertFalse(payload["workflow_mutation_performed"])
        self.assertEqual(tree_snapshot(self.storage / "tasks"), empty_tasks_before)
        self.assertFalse((self.storage / "checkpoint.json").exists())


if __name__ == "__main__":
    unittest.main()
