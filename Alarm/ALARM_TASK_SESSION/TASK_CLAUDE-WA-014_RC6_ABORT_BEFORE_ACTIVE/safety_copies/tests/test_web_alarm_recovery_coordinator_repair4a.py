"""RC-6 Repair #4A regressions: an accepted recovery action of an operation whose
microtask is PREPARING (interrupted preparation) or has never been ACTIVE always
has a completion path or an explicit manual boundary, never an endless
FAIL_CLOSED."""

import unittest
import unittest.mock

from test_web_alarm_recovery_coordinator_repair2 import AFTER, BEFORE, TASK
from test_web_alarm_recovery_coordinator_repair4 import PREPARE_CRASH, Repair4Fixture

from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.recovery_coordinator import (
    _ABORT_FROM_PRE_EXECUTION,
    MANUAL_DECISION_REQUIRED,
    READY_FOR_EXECUTION,
    READY_FOR_VERIFICATION,
    RECOVERY_BLOCKED,
    RECOVERY_IN_PROGRESS,
    RecoveryCoordinator,
)
from web_alarm.resolution_store import ResolutionResult
from web_alarm.rollback_service import RollbackService
from web_alarm.target_claim_service import TargetClaimService

STEP_CRASH = """
    import os
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    from web_alarm.models import MicrotaskStatus
    where = {where!r}
    if where == "before_settlement":
        def die(self, *a, **k):
            os._exit(41)  # the preparation is reconciled, the ABORT not yet settled
        RecoveryCoordinator._settle_resolution = die
    else:
        real = RecoveryCoordinator._set_micro_locked
        def die(self, task_id, microtask_id, target, **kw):
            if target is MicrotaskStatus.RECOVERY_REQUIRED:
                os._exit(43)  # the operation settlement is written, the microtask status is not
            return real(self, task_id, microtask_id, target, **kw)
        RecoveryCoordinator._set_micro_locked = die
    RecoveryCoordinator({storage!r}).recover({task!r})
"""


class Repair4AFixture(Repair4Fixture):
    def intent(self, target="a.txt", op="op_1", *, claim=True):
        if not (self.project / target).exists():
            self.write(target, BEFORE)
        self.ops.begin(TASK, "m1", "write", target, operation_id=op, payload=AFTER)
        if claim:
            out = TargetClaimService(self.storage).acquire(TASK, op, operation_revision=1)
            self.assertEqual(out["result"], "ACQUIRED", out["reason"])

    def accept(self, action, op="op_1"):
        record = self.resolve_any(action, op)
        self.assertEqual(record.result, ResolutionResult.ACCEPTED, record.result_reason)
        return record

    def authority(self, op):
        rev = self.ops.get(TASK, op).revision
        return TargetClaimService(self.storage).authorize(TASK, op, operation_revision=rev)["result_code"]

    def crash_step(self, where, expect_exit):
        child = self.run_child(STEP_CRASH.format(where=where, storage=str(self.storage), task=TASK))
        child.communicate(timeout=120)
        self.assertEqual(child.returncode, expect_exit)

    def assert_aborted_at_boundary(self):
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.settlements("op_1"), {"op_1": "ABORT"})
        self.assertEqual([c for c in self.active_claims() if c[1] == "op_1"], [])
        again = self.recover()
        self.assertEqual((again["state"], again["performed_steps"]), (MANUAL_DECISION_REQUIRED, []))


class PreparingWithAcceptedAbortTests(Repair4AFixture):
    """A1-A6, A8, A9: interrupted preparation x accepted ABORT."""

    def test_a1_w1_then_abort_reconciles_then_settles_in_a_fresh_process(self):
        self.intent()
        self.crash_prepare("W1", expect_exit=23)
        self.accept("ABORT")  # before any reconcile

        state, steps, results = self.fresh_recover()  # A5: restart between ABORT and recovery

        self.assertEqual(steps, ["RECONCILE_PREPARATION", "SETTLE_ABORT"])
        self.assertEqual(results, ["PREPARATION_DISCARDED", "SETTLED"])
        self.assertEqual(state, MANUAL_DECISION_REQUIRED)
        self.assertFalse((self.work() / "restore_point").exists())  # nothing taken for VERIFIED
        self.assert_aborted_at_boundary()

    def test_a2_w2_then_abort_keeps_the_published_restore_point_and_pre_state(self):
        self.intent()
        self.crash_prepare("W2", expect_exit=29)
        manifest_id = ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").manifest_id
        self.write("a.txt", b"edited after the crash\n")
        self.accept("ABORT")

        state, steps, results = self.fresh_recover()

        self.assertEqual((steps, results), (["RECONCILE_PREPARATION", "SETTLE_ABORT"],
                                            ["PREPARATION_COMPLETED", "SETTLED"]))
        self.assert_aborted_at_boundary()
        plan = ManifestSnapshotStore(self.storage).restore_plan(TASK, "m1")  # A9: integrity + pre-state
        self.assertEqual(plan["manifest_id"], manifest_id)
        self.assertEqual(plan["items"][0]["snapshot_bytes"], BEFORE)
        self.assertEqual(self.read("a.txt"), b"edited after the crash\n")  # nothing restored

    def test_a3_w1_reconciled_first_then_abort(self):
        self.intent()
        self.crash_prepare("W1", expect_exit=23)
        self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)
        self.accept("ABORT")

        result = self.recover()

        self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ABORT"])
        self.assert_aborted_at_boundary()

    def test_a3_w2_reconciled_first_then_abort(self):
        self.intent()
        self.crash_prepare("W2", expect_exit=29)
        self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)
        self.accept("ABORT")

        result = self.recover()

        self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ABORT"])
        self.assert_aborted_at_boundary()
        self.assertIsNotNone(ManifestSnapshotStore(self.storage).verify_restore_point(TASK, "m1"))

    def test_a4_repeated_recover_never_loops_fail_closed(self):
        self.intent()
        self.crash_prepare("W2", expect_exit=29)
        self.accept("ABORT")

        states = [self.recover()["state"] for _ in range(4)]

        self.assertNotIn("FAIL_CLOSED", states)
        self.assertEqual(set(states), {MANUAL_DECISION_REQUIRED})

    def test_a6_crash_after_reconcile_before_the_settlement(self):
        self.intent()
        self.crash_prepare("W2", expect_exit=29)
        self.accept("ABORT")
        self.crash_step("before_settlement", 41)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)
        self.assertIsNone(self.ops.get(TASK, "op_1").recovery_settlement)

        state, steps, _ = self.fresh_recover()

        self.assertEqual(steps, ["SETTLE_ABORT"])
        self.assert_aborted_at_boundary()

    def test_a6_crash_between_operation_settlement_and_microtask_status(self):
        self.intent()
        self.crash_prepare("W1", expect_exit=23)
        self.accept("ABORT")
        self.crash_step("between_writes", 43)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)
        self.assertEqual(self.settlements("op_1"), {"op_1": "ABORT"})

        state, steps, _ = self.fresh_recover()

        self.assertEqual(steps, ["FINISH_SETTLEMENT"])
        self.assert_aborted_at_boundary()

    def test_a8_no_mutation_authority_in_any_intermediate_state(self):
        self.intent()
        self.intent("b.txt", "op_2")  # a sibling that would like to write
        self.crash_prepare("W1", expect_exit=23)
        self.assertEqual(self.authority("op_2"), "MICROTASK_NOT_ACTIVE")  # PREPARING
        self.accept("ABORT")
        self.assertEqual(self.authority("op_1"), "RECOVERY_ABORTED")
        self.assertEqual(self.authority("op_2"), "MICROTASK_NOT_ACTIVE")
        self.recover()  # BLOCKED_PREPARE -> RECOVERY_REQUIRED within one call
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.authority("op_2"), "MICROTASK_NOT_ACTIVE")
        self.assertEqual((self.read("a.txt"), self.read("b.txt")), (BEFORE, BEFORE))


class ConcurrentPrepareRecoverAbortTests(Repair4AFixture):
    """A7: a live preparation, an accepted ABORT and recover at the same time."""

    def test_a7_live_preparation_is_never_settled_over_then_the_abort_completes(self):
        self.intent()
        self.write("a.txt", BEFORE)
        child = self.run_child(PREPARE_CRASH.format(
            window="HOLD", storage=str(self.storage), task=TASK, flags=str(self.flags)))
        try:
            self.wait_flag("capturing", child)
            self.accept("ABORT")  # the Resolver does not need the preparation lock

            during = self.recover()

            self.assertEqual(during["state"], RECOVERY_IN_PROGRESS)
            self.assertEqual(self.micro("m1"), MicrotaskStatus.PREPARING)
            self.assertIsNone(self.ops.get(TASK, "op_1").recovery_settlement)
        finally:
            (self.flags / "release").write_text("1")
            try:
                out, err = child.communicate(timeout=120)
            except Exception:
                child.kill()
                raise
        self.assertEqual(child.returncode, 0, err)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)

        after = self.recover()

        self.assertEqual([s["action"] for s in after["performed_steps"]], ["SETTLE_ABORT"])
        self.assert_aborted_at_boundary()

    def test_a7_settlement_is_deferred_when_a_preparation_starts_in_between(self):
        self.intent()
        self.accept("ABORT")  # chosen while m1 is PLANNED
        real = RecoveryCoordinator._accepted_resolution_locked
        fired = []

        def preparation_started_meanwhile(coordinator, task_id, *args, **kwargs):
            if not fired:  # a concurrent prepare's CAS landed after the projection chose the step
                fired.append(1)
                coordinator.tasks.set_microtask_status_locked(task_id, "m1", MicrotaskStatus.PREPARING)
            return real(coordinator, task_id, *args, **kwargs)

        with unittest.mock.patch.object(RecoveryCoordinator, "_accepted_resolution_locked", preparation_started_meanwhile):
            result = self.recover()

        self.assertEqual(
            [(s["action"], s["outcome"].get("result")) for s in result["performed_steps"]],
            [("SETTLE_ABORT", "DEFERRED_BY_PREPARATION"), ("RECONCILE_PREPARATION", "PREPARATION_DISCARDED"),
             ("SETTLE_ABORT", "SETTLED")],
        )
        self.assertNotEqual(result["state"], "FAIL_CLOSED")
        self.assert_aborted_at_boundary()

    def test_a7_prepare_after_the_abort_settlement_is_refused(self):
        self.intent()
        self.accept("ABORT")  # PLANNED microtask, no preparation at all
        self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        from web_alarm.state_machine import TransitionRejected
        with self.assertRaises(TransitionRejected):
            self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        self.assertFalse((self.work() / "restore_point").exists())


class NeverExecutedMicrotaskRecoveryTests(Repair4AFixture):
    """Adversarial: every accepted action of an operation of a never-executed microtask."""

    def test_abort_without_any_crash_from_planned_backup_verified_and_ready(self):
        for status in ("PLANNED", "BACKUP_VERIFIED", "READY"):
            with self.subTest(status=status):
                self.setUp()
                try:
                    if status != "PLANNED":
                        self.write("a.txt", BEFORE)
                        self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
                    if status == "READY":
                        self.machine.transition(TASK, "m1", MicrotaskStatus.READY)
                    self.intent()
                    self.accept("ABORT")

                    result = self.recover()

                    self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ABORT"])
                    self.assert_aborted_at_boundary()
                finally:
                    self.tearDown()

    def started_with_post_state(self, *, crash_w2=False):
        self.intent()
        if crash_w2:
            self.crash_prepare("W2", expect_exit=29)
        else:
            self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        self.write("a.txt", AFTER)  # written outside the server: no authority existed

    def test_adopt_is_a_manual_boundary_completed_after_normal_activation(self):
        self.started_with_post_state(crash_w2=True)
        self.accept("ADOPT")
        before = self.digest()

        first = self.recover()  # reconciles W2 first, then stops at the boundary
        second = self.recover()

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["RECONCILE_PREPARATION"])
        self.assertEqual((first["state"], second["state"]), (MANUAL_DECISION_REQUIRED, MANUAL_DECISION_REQUIRED))
        self.assertIn("activate the microtask", first["reason"])
        self.assertEqual(second["performed_steps"], [])
        self.assertIsNone(self.ops.get(TASK, "op_1").recovery_settlement)
        self.assertNotEqual(self.digest(), before)  # only the reconcile wrote
        self.machine.transition(TASK, "m1", MicrotaskStatus.READY)
        self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)

        done = self.recover()

        self.assertEqual([s["action"] for s in done["performed_steps"]], ["SETTLE_ADOPT"])
        self.assertEqual((done["state"], self.micro("m1")), (READY_FOR_VERIFICATION, MicrotaskStatus.DONE))

    def test_rollback_is_a_manual_boundary_without_an_rc4_session_and_abort_closes_it(self):
        for name, data in (("a.txt", BEFORE), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.intent()
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        self.write("a.txt", AFTER)
        (self.project / "b.txt").unlink()
        self.accept("ROLLBACK")

        blocked = self.recover()

        self.assertEqual(blocked["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(blocked["performed_steps"], [])
        self.assertEqual(RollbackService(self.storage).store.list(TASK), [])  # no claims, no restore
        self.accept("ABORT")
        closed = self.recover()
        self.assertEqual([s["action"] for s in closed["performed_steps"]], ["SETTLE_ABORT"])
        self.assert_aborted_at_boundary()
        self.assertEqual(self.read("a.txt"), AFTER)

    def test_retry_names_the_activation_and_proves_ready_after_it(self):
        self.intent()
        self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        self.accept("RETRY")

        blocked = self.recover()

        self.assertEqual(blocked["state"], RECOVERY_BLOCKED)
        self.assertIn("activate the microtask", blocked["reason"])
        self.machine.transition(TASK, "m1", MicrotaskStatus.READY)
        self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        ready = self.recover()
        self.assertEqual((ready["state"], ready["ready_proof"]["kind"]), (READY_FOR_EXECUTION, "RETRY"))

    def test_settlement_rule_sources(self):
        rule = RecoveryCoordinator._settlement_rule
        rr = MicrotaskStatus.RECOVERY_REQUIRED
        abort_only = rule(rr, finishing=False, actions=["ABORT", "ABORT"])["allowed_from"]
        with_rollback = rule(rr, finishing=False, actions=["ABORT", "ROLLBACK"])["allowed_from"]
        self.assertTrue(_ABORT_FROM_PRE_EXECUTION <= abort_only)
        self.assertFalse(_ABORT_FROM_PRE_EXECUTION & with_rollback)  # no rollback of a stage that never ran
        self.assertNotIn(MicrotaskStatus.PREPARING, abort_only)  # reconciled first, never settled over
        self.assertNotIn(MicrotaskStatus.VERIFIED, abort_only)
        self.assertNotIn(MicrotaskStatus.PREPARING, _ABORT_FROM_PRE_EXECUTION)


if __name__ == "__main__":
    unittest.main()
