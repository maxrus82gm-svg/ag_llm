import tempfile
import unittest
from pathlib import Path

from web_alarm.models import MicrotaskStatus
from web_alarm.state_machine import ServerStateMachine, TransitionRejected
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


class ServerStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()

        registry = WorkspaceRegistry(self.storage)
        workspace = registry.register("Project", self.project)
        tasks = TaskStore(self.storage)
        self.task = tasks.create_task(
            workspace.workspace_id,
            "Task",
            "RAW TASK",
            "Test server-owned state machine",
            task_id="task_sm",
        )
        self.micro = tasks.create_microtask(
            self.task.task_id,
            "M1",
            "First",
            microtask_id="m1",
        )
        self.machine = ServerStateMachine(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def _prepare_m1(self):
        target = self.project / "file.txt"
        target.write_text("before", encoding="utf-8")
        return self.machine.prepare_microtask(
            self.task.task_id,
            "m1",
            [("file.txt", "edit")],
            operation_id="op_prepare",
        )

    def test_planned_to_active_is_physically_rejected(self):
        with self.assertRaises(TransitionRejected) as caught:
            self.machine.transition(
                self.task.task_id,
                "m1",
                MicrotaskStatus.ACTIVE,
                operation_id="op_bad",
            )

        self.assertEqual(caught.exception.current_status, MicrotaskStatus.PLANNED)
        self.assertIn("not allowed", caught.exception.reason)
        self.assertIn("prepare restore point", caught.exception.next_safe_action)
        self.assertEqual(
            self.machine.tasks.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.PLANNED,
        )
        checkpoint = self.machine.state.read_checkpoint(self.task.task_id)
        self.assertEqual(checkpoint.current_status, MicrotaskStatus.PLANNED)
        # RC-5: the caller's label is history, never checkpoint content
        self.assertIsNone(checkpoint.last_operation_id)
        rejected = self.machine.state.read_events(self.task.task_id)[-1]
        self.assertEqual((rejected.event_type, rejected.operation_id), ("MICROTASK_TRANSITION_REJECTED", "op_bad"))

    def test_prepare_creates_backup_verified_checkpoint_and_event(self):
        result = self._prepare_m1()

        self.assertEqual(
            result["microtask"].status,
            MicrotaskStatus.BACKUP_VERIFIED,
        )
        self.assertEqual(result["checkpoint"].snapshot_status, "VERIFIED")
        self.assertIn("READY", result["checkpoint"].next_safe_action)
        events = self.machine.state.read_events(self.task.task_id)
        self.assertEqual(events[-1].event_type, "MICROTASK_PREPARED")

    def test_valid_lifecycle_requires_verification_evidence(self):
        self._prepare_m1()
        ready = self.machine.transition(
            self.task.task_id,
            "m1",
            "READY",
            operation_id="op_ready",
        )
        self.assertEqual(ready["microtask"].status, MicrotaskStatus.READY)

        active = self.machine.transition(
            self.task.task_id,
            "m1",
            "ACTIVE",
            operation_id="op_active",
        )
        self.assertEqual(active["microtask"].status, MicrotaskStatus.ACTIVE)
        self.assertEqual(
            self.machine.tasks.open_plan(self.task.task_id).current_microtask_id,
            "m1",
        )

        done = self.machine.transition(
            self.task.task_id,
            "m1",
            "DONE",
            operation_id="op_done",
        )
        self.assertEqual(done["microtask"].status, MicrotaskStatus.DONE)

        with self.assertRaises(TransitionRejected) as caught:
            self.machine.transition(
                self.task.task_id,
                "m1",
                "VERIFIED",
                operation_id="op_verify_missing",
            )
        self.assertIn("verification_evidence", caught.exception.reason)
        self.assertEqual(
            self.machine.tasks.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.DONE,
        )

        verified = self.machine.transition(
            self.task.task_id,
            "m1",
            "VERIFIED",
            verification_evidence="57/57 tests PASS",
            operation_id="op_verified",
        )
        self.assertEqual(verified["microtask"].status, MicrotaskStatus.VERIFIED)
        checkpoint = self.machine.state.read_checkpoint(self.task.task_id)
        self.assertEqual(checkpoint.last_verified_microtask_id, "m1")
        self.assertEqual(checkpoint.current_status, MicrotaskStatus.VERIFIED)
        self.assertIsNone(checkpoint.last_operation_id)  # RC-5: no tracked operation exists
        self.assertEqual(self.machine.state.read_events(self.task.task_id)[-1].operation_id, "op_verified")

    def test_second_microtask_cannot_prepare_before_previous_verified(self):
        tasks = TaskStore(self.storage)
        tasks.create_microtask(
            self.task.task_id,
            "M2",
            "Second",
            microtask_id="m2",
        )
        (self.project / "second.txt").write_text("before", encoding="utf-8")

        with self.assertRaises(TransitionRejected) as caught:
            self.machine.prepare_microtask(
                self.task.task_id,
                "m2",
                [("second.txt", "edit")],
                operation_id="op_m2",
            )

        self.assertIn("previous microtask m1", caught.exception.reason)
        self.assertEqual(
            tasks.open_microtask(self.task.task_id, "m2").status,
            MicrotaskStatus.PLANNED,
        )

    def test_corrupted_snapshot_blocks_ready_transition(self):
        result = self._prepare_m1()
        manifest = result["manifest"]
        snapshot = self.machine.manifests.list_snapshots(
            self.task.task_id,
            "m1",
        )[0]
        work_dir = self.machine.tasks.microtask_directory(
            self.task.task_id,
            "m1",
            active_only=True,
        )
        binary = work_dir / "restore_point" / str(snapshot.snapshot_path)
        binary.write_bytes(b"corrupted")

        with self.assertRaises(TransitionRejected) as caught:
            self.machine.transition(
                self.task.task_id,
                "m1",
                "READY",
                operation_id="op_ready_bad",
            )

        self.assertIn("verified restore point required", caught.exception.reason)
        self.assertEqual(
            self.machine.tasks.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BLOCKED_PREPARE,
        )
        checkpoint = self.machine.state.read_checkpoint(self.task.task_id)
        self.assertEqual(checkpoint.current_status, MicrotaskStatus.BLOCKED_PREPARE)
        self.assertEqual(checkpoint.snapshot_status, "NOT_VERIFIED")

    def test_failed_verification_can_reenter_active_only_with_snapshot(self):
        self._prepare_m1()
        self.machine.transition(self.task.task_id, "m1", "READY")
        self.machine.transition(self.task.task_id, "m1", "ACTIVE")
        self.machine.transition(self.task.task_id, "m1", "DONE")
        failed = self.machine.transition(
            self.task.task_id,
            "m1",
            "FAILED_VERIFICATION",
            verification_evidence="test failure",
        )
        self.assertEqual(
            failed["microtask"].status,
            MicrotaskStatus.FAILED_VERIFICATION,
        )
        active = self.machine.transition(
            self.task.task_id,
            "m1",
            "ACTIVE",
        )
        self.assertEqual(active["microtask"].status, MicrotaskStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
