import hashlib
import tempfile
import unittest
from pathlib import Path

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore, OperationTransitionError
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

TASK = "task_rc6"
MICRO = "m1"
OP = "op_1"
BEFORE = b"before\n"
AFTER = b"after\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RecoverySettlementPrimitiveTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.target = self.project / "target.txt"
        self.target.write_bytes(BEFORE)
        WorkspaceRegistry(self.storage).register("RC6", self.project, workspace_id="ws_rc6")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_rc6", "RC6", "RAW TASK", "Recovery", task_id=TASK)
        self.tasks.create_microtask(TASK, "M1", "Recovery step", microtask_id=MICRO)
        self.ops = OperationStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def begin_started(self):
        self.ops.begin(
            TASK, MICRO, "write", "target.txt",
            operation_id=OP,
            payload=AFTER,
            request_payload={"case": OP},
        )
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        return self.ops.get(TASK, OP)

    def events(self):
        return EventCheckpointStore(self.storage).read_events(TASK)

    def test_adopt_settlement_proves_post_state_and_persists_receipt(self):
        started = self.begin_started()
        self.target.write_bytes(AFTER)
        before_bytes = self.target.read_bytes()

        with self.ops.task_lock(TASK):
            result = self.ops._settle_recovery_locked(
                TASK, OP, "ADOPT",
                resolution_id="res_adopt",
                expected_revision=started.revision,
            )

        record = self.ops.get(TASK, OP)
        self.assertTrue(result["changed"])
        self.assertEqual(record.status, OperationStatus.VERIFIED)
        self.assertEqual(record.result_summary, "recovery ADOPT via res_adopt")
        self.assertIsNotNone(record.receipt)
        self.assertTrue(record.receipt["matches_expected_post"])
        self.assertEqual(record.receipt["sha256"], sha(AFTER))
        self.assertEqual(record.recovery_settlement["action"], "ADOPT")
        self.assertEqual(record.recovery_settlement["resolution_id"], "res_adopt")
        self.assertEqual(self.target.read_bytes(), before_bytes)
        settled = [e for e in self.events() if e.event_type == "OPERATION_RECOVERY_SETTLED"]
        self.assertEqual(len(settled), 1)
        self.assertEqual(settled[0].payload["settlement"], "ADOPT")

    def test_adopt_settlement_is_idempotent_for_same_resolution(self):
        started = self.begin_started()
        self.target.write_bytes(AFTER)
        with self.ops.task_lock(TASK):
            first = self.ops._settle_recovery_locked(
                TASK, OP, "ADOPT", resolution_id="res_adopt", expected_revision=started.revision
            )
            second = self.ops._settle_recovery_locked(
                TASK, OP, "ADOPT", resolution_id="res_adopt",
                expected_revision=first["operation"].revision,
            )
        self.assertTrue(first["changed"])
        self.assertTrue(second["replayed"])
        self.assertFalse(second["changed"])

    def test_adopt_refuses_when_current_bytes_are_not_expected_post(self):
        started = self.begin_started()
        self.target.write_bytes(b"other\n")
        with self.ops.task_lock(TASK):
            with self.assertRaises(OperationTransitionError):
                self.ops._settle_recovery_locked(
                    TASK, OP, "ADOPT", resolution_id="res_adopt", expected_revision=started.revision
                )
        self.assertEqual(self.ops.get(TASK, OP).status, OperationStatus.STARTED)

    def test_abort_settlement_fails_operation_without_workspace_write(self):
        started = self.begin_started()
        self.target.write_bytes(b"drift\n")
        before_bytes = self.target.read_bytes()
        with self.ops.task_lock(TASK):
            result = self.ops._settle_recovery_locked(
                TASK, OP, "ABORT", resolution_id="res_abort", expected_revision=started.revision
            )
        record = self.ops.get(TASK, OP)
        self.assertTrue(result["changed"])
        self.assertEqual(record.status, OperationStatus.STARTED)
        self.assertEqual(record.result_summary, "recovery ABORT via res_abort")
        self.assertEqual(record.recovery_settlement["action"], "ABORT")
        self.assertEqual(record.recovery_settlement["resolution_id"], "res_abort")
        self.assertEqual(self.target.read_bytes(), before_bytes)

    def test_rollback_settlement_fails_original_operation_without_workspace_write(self):
        started = self.begin_started()
        before_bytes = self.target.read_bytes()
        with self.ops.task_lock(TASK):
            result = self.ops._settle_recovery_locked(
                TASK, OP, "ROLLBACK", resolution_id="res_rb", expected_revision=started.revision
            )
        self.assertTrue(result["changed"])
        record = self.ops.get(TASK, OP)
        self.assertEqual(record.status, OperationStatus.STARTED)
        self.assertEqual(record.recovery_settlement["action"], "ROLLBACK")
        self.assertEqual(record.recovery_settlement["resolution_id"], "res_rb")
        self.assertEqual(self.target.read_bytes(), before_bytes)

    def test_settlement_revision_cas_fails_closed(self):
        started = self.begin_started()
        with self.ops.task_lock(TASK):
            with self.assertRaises(OperationTransitionError):
                self.ops._settle_recovery_locked(
                    TASK, OP, "ABORT", resolution_id="res_abort",
                    expected_revision=(started.revision or 0) + 1,
                )
        self.assertEqual(self.ops.get(TASK, OP).status, OperationStatus.STARTED)

    def test_generic_transition_still_cannot_manufacture_recovery_verified(self):
        self.begin_started()
        self.ops.transition(TASK, OP, OperationStatus.UNKNOWN_AFTER_DISCONNECT)
        with self.assertRaises(OperationTransitionError):
            self.ops.transition(TASK, OP, OperationStatus.VERIFIED)

    def test_lock_held_microtask_status_write_does_not_reacquire_lock(self):
        with self.tasks.mutation_lock(TASK):
            record = self.tasks.set_microtask_status_locked(
                TASK, MICRO, MicrotaskStatus.RECOVERY_REQUIRED
            )
        self.assertEqual(record.status, MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.RECOVERY_REQUIRED)


if __name__ == "__main__":
    unittest.main()
