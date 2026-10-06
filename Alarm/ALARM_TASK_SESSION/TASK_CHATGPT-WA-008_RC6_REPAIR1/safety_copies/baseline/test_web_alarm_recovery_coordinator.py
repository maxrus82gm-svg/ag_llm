import hashlib
import tempfile
import unittest
from pathlib import Path

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore, OperationTransitionError
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import (
    FAIL_CLOSED, MANUAL_DECISION_REQUIRED, READY_FOR_EXECUTION,
    READY_FOR_VERIFICATION, RecoveryCoordinator,
)
from web_alarm.resolver_service import ResolverService
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


class RecoveryCoordinatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.target = self.project / "target.txt"
        self.extra = self.project / "extra.txt"
        self.target.write_bytes(BEFORE)
        WorkspaceRegistry(self.storage).register("RC6", self.project, workspace_id="ws_rc6")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_rc6", "RC6", "RAW TASK", "Recovery", task_id=TASK)
        self.tasks.create_microtask(TASK, "M1", "Recovery step", microtask_id=MICRO)
        self.ops = OperationStore(self.storage)
        self.resolver = ResolverService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def prepare(self, specs=(("target.txt", "edit"),)):
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, MICRO, list(specs))

    def set_micro(self, status):
        self.tasks.set_microtask_status(TASK, MICRO, status)

    def begin_started(self):
        self.ops.begin(
            TASK, MICRO, "write", "target.txt",
            operation_id=OP,
            payload=AFTER,
            request_payload={"case": OP},
        )
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        return self.ops.get(TASK, OP)

    def resolve(self, action):
        decision = ReconciliationService(self.storage).reconcile(TASK, MICRO, OP)["DECISION"]
        record = self.ops.get(TASK, OP)
        return self.resolver.apply(
            TASK,
            MICRO,
            OP,
            action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=record.revision,
            agent="rc6-test",
            channel="test",
        )

    def test_clean_active_task_is_ready_without_writes(self):
        self.set_micro(MicrotaskStatus.ACTIVE)
        before = self.target.read_bytes()

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertTrue(result["ready_for_execution"])
        self.assertEqual(result["performed_steps"], [])
        self.assertEqual(self.target.read_bytes(), before)

    def test_unresolved_operation_requires_manual_decision(self):
        self.prepare()
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        before = self.target.read_bytes()

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertTrue(result["requires_human"])
        self.assertEqual(result["performed_steps"], [])
        self.assertEqual(self.target.read_bytes(), before)

    def test_retry_rearms_microtask_but_performs_no_physical_write(self):
        self.prepare()
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        accepted = self.resolve("RETRY")
        self.assertTrue(accepted["accepted"])
        before = self.target.read_bytes()

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.ACTIVE)
        self.assertEqual(self.ops.get(TASK, OP).status, OperationStatus.STARTED)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual([s["action"] for s in result["performed_steps"]], ["REARM_RETRY"])

    def test_adopt_settles_durably_and_stops_at_verification_boundary(self):
        self.prepare()
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        self.target.write_bytes(AFTER)
        accepted = self.resolve("ADOPT")
        self.assertTrue(accepted["accepted"])

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], READY_FOR_VERIFICATION)
        op = self.ops.get(TASK, OP)
        self.assertEqual(op.status, OperationStatus.VERIFIED)
        self.assertEqual(op.recovery_settlement["action"], "ADOPT")
        self.assertTrue(op.receipt["matches_expected_post"])
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.DONE)
        self.assertEqual(self.target.read_bytes(), AFTER)

        replay = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(replay["state"], READY_FOR_VERIFICATION)
        self.assertEqual(replay["performed_steps"], [])

    def test_abort_settles_without_erasing_forensic_operation_status(self):
        self.prepare()
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        self.target.write_bytes(b"drift\n")
        accepted = self.resolve("ABORT")
        self.assertTrue(accepted["accepted"])
        before = self.target.read_bytes()

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        op = self.ops.get(TASK, OP)
        self.assertEqual(op.status, OperationStatus.STARTED)
        self.assertEqual(op.recovery_settlement["action"], "ABORT")
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.target.read_bytes(), before)

    def _rollback_case(self):
        self.extra.write_bytes(b"keep\n")
        self.prepare((("target.txt", "edit"), ("extra.txt", "delete")))
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        self.target.write_bytes(AFTER)
        accepted = self.resolve("ROLLBACK")
        self.assertTrue(accepted["accepted"])
        return accepted

    def test_one_command_rollback_uses_rc4_then_stops_for_new_decision(self):
        self._rollback_case()

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.target.read_bytes(), BEFORE)
        self.assertEqual(self.extra.read_bytes(), b"keep\n")
        op = self.ops.get(TASK, OP)
        self.assertEqual(op.status, OperationStatus.STARTED)
        self.assertEqual(op.recovery_settlement["action"], "ROLLBACK")
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.RECOVERY_REQUIRED)
        actions = [step["action"] for step in result["performed_steps"]]
        self.assertIn("PREPARE_ROLLBACK", actions)
        self.assertIn("APPLY_ROLLBACK", actions)
        self.assertIn("SETTLE_ROLLBACK", actions)

    def test_step_budget_fails_closed_without_infinite_loop_and_resume_is_safe(self):
        self._rollback_case()

        first = RecoveryCoordinator(self.storage).recover(TASK, max_recovery_steps=1)

        self.assertEqual(first["state"], FAIL_CLOSED)
        self.assertEqual(first["error"], "RECOVERY_STEP_BUDGET_EXHAUSTED")
        self.assertEqual(len(first["performed_steps"]), 1)

        resumed = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(resumed["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.target.read_bytes(), BEFORE)
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ROLLBACK")


if __name__ == "__main__":
    unittest.main()
