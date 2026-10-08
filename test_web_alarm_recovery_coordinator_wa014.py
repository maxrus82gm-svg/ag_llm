"""CLAUDE-WA-014 regressions: ACTIVE is no proof of mutation authority once an ABORT or
ROLLBACK of the microtask was accepted before it. The state machine refuses that activation
(microtask_gate.activation_refusal, decided under the TASK lock + mutation lock), so neither
RC-6 nor the direct RC-4 entry can restore the restore point over changes no authorized
executor made; a stage activated before the recovery decision keeps its legitimate rollback."""

import json
import time
import unittest
from unittest import mock

from test_web_alarm_recovery_coordinator_repair2 import TASK
from test_web_alarm_recovery_coordinator_repair4b import FILES, Repair4BFixture

from web_alarm.microtask_gate import activation_refusal
from web_alarm.models import MicrotaskStatus
from web_alarm.recovery_coordinator import MANUAL_DECISION_REQUIRED, RecoveryCoordinator
from web_alarm.rollback_service import RollbackService
from web_alarm.rollback_store import RollbackStore, RollbackStoreError
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.state_machine import TransitionRejected

ACTIVATE_HELD = """
    import pathlib, time
    import web_alarm.microtask_gate as gate
    from web_alarm.state_machine import ServerStateMachine
    flags = pathlib.Path({flags!r})
    real = gate.activation_refusal
    def held(*args, **kwargs):
        result = real(*args, **kwargs)
        (flags / "checked").write_text("1")  # decided, ACTIVE not written yet; locks held
        while not (flags / "release").exists():
            time.sleep(0.01)
        return result
    gate.activation_refusal = held
    try:
        ServerStateMachine({storage!r}).transition({task!r}, "m1", "ACTIVE")
        print("ACTIVE")
    except Exception as exc:
        print(type(exc).__name__)
"""

ABORT_CHILD = """
    import pathlib, time
    from web_alarm.operation_store import OperationStore
    from web_alarm.reconciliation_service import ReconciliationService
    from web_alarm.resolution_store import ResolutionStore
    from web_alarm.resolver_service import ResolverService
    flags, hold = pathlib.Path({flags!r}), {hold!r}
    if hold:
        real = ResolutionStore.write_new
        def held(self, record):
            (flags / "recording").write_text("1")  # the ABORT is decided under the TASK lock
            while not (flags / "release").exists():
                time.sleep(0.01)
            return real(self, record)
        ResolutionStore.write_new = held
    decision = ReconciliationService({storage!r}).reconcile({task!r}, "m1", "op_1")["DECISION"]
    r = ResolverService({storage!r}).apply(
        {task!r}, "m1", "op_1", "ABORT", evidence_fingerprint=decision["evidence_fingerprint"],
        operation_revision=OperationStore({storage!r}).get({task!r}, "op_1").revision)["resolution"]
    print(r.result.value)
"""

ACTIVATE_CHILD = """
    from web_alarm.state_machine import ServerStateMachine
    try:
        ServerStateMachine({storage!r}).transition({task!r}, "m1", "ACTIVE")
        print("ACTIVE")
    except Exception as exc:
        print(type(exc).__name__)
"""


class WA014Fixture(Repair4BFixture):
    def activate_refused(self):
        with self.assertRaises(TransitionRejected) as ctx:
            self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        self.assertIn("MICROTASK_RECOVERY_REQUIRED", ctx.exception.reason)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.READY)
        return ctx.exception

    def api_activate(self):
        with self.assertRaises(ApiError) as ctx:
            WebAlarmApi(self.storage).dispatch("POST", "/microtasks/m1/transition", {
                "task_id": TASK, "target_status": "ACTIVE"})
        return ctx.exception

    def finish(self, child):
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)
        return out.strip().splitlines()[-1]


class AbortBeforeActiveTests(WA014Fixture):
    """The exploit chain of the verifier hypothesis, through supported APIs."""

    def test_activation_after_an_accepted_abort_is_refused_and_nothing_is_restored(self):
        for kind in ("write", "delete", "create"):
            with self.subTest(kind=kind):
                self.setUp()
                try:
                    self.stage(kind, "READY")
                    self.begin_ops(kind)
                    self.resolve("ABORT", "op_1")  # accepted, not settled yet

                    self.activate_refused()
                    error = self.api_activate()

                    self.assertEqual((error.status, error.code), (409, "transition_rejected"))
                    self.assertEqual(self.gate()[0], "MICROTASK_NOT_ACTIVE")  # no mutation authority at all
                    self.external_partial(kind)
                    resolution = self.resolve("ROLLBACK", "op_2")
                    before = self.files()
                    result = self.recover()
                    direct = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
                    self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
                    self.assertNotIn("APPLY_ROLLBACK", [s["action"] for s in result["performed_steps"]])
                    self.assertEqual((direct["result"], direct["result_code"]), ("REJECTED", "MICROTASK_NEVER_EXECUTED"))
                    self.assert_nothing_restored(before)
                finally:
                    self.tearDown()

    def test_activation_after_an_accepted_rollback_is_refused_too(self):
        self.stage("write", "READY")
        self.begin_ops("write", sibling=False)
        self.external_partial("write")
        resolution = self.resolve("ROLLBACK", "op_2")
        before = self.files()

        self.activate_refused()
        result = self.recover()
        direct = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)

        self.assertEqual((result["state"], result["performed_steps"]), (MANUAL_DECISION_REQUIRED, []))
        self.assertNotIn("activate the microtask through", result["reason"])  # no activation exit for ROLLBACK
        self.assertIn("refuses the activation", result["reason"])
        self.assertEqual(direct["result_code"], "MICROTASK_NEVER_EXECUTED")
        self.assert_nothing_restored(before)
        self.resolve("ABORT", "op_2")  # the named way out
        closed = self.recover()
        self.assertEqual([s["action"] for s in closed["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.files(), before)

    def test_an_open_rc4_session_refuses_the_activation(self):
        self.stage("write", "READY")
        self.begin_ops("write", sibling=False)
        self.external_partial("write")
        resolution = self.resolve("ROLLBACK", "op_2")
        import web_alarm.rollback_service as rs
        with mock.patch.object(rs, "rollback_refusal", return_value=None):  # a session of an older build
            RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
        self.write("a.txt", b"changed again\n")  # the ROLLBACK is stale now: only the open session speaks
        before = self.files()

        error = self.activate_refused()

        self.assertIn("ROLLBACK", error.reason)
        self.assertEqual(self.files(), before)

    def test_repeated_refusals_write_nothing_and_a_fresh_process_agrees(self):
        self.stage("create", "READY")
        self.begin_ops("create")
        self.resolve("ABORT", "op_1")
        record = self.tasks.open_microtask(TASK, "m1")

        for _ in range(3):
            self.activate_refused()

        self.assertEqual(self.events("MICROTASK_TRANSITION_REJECTED"), 3)
        self.assertEqual(self.tasks.open_microtask(TASK, "m1").updated_at, record.updated_at)  # nothing written
        state, steps, _ = self.fresh_recover()
        self.assertEqual((state, steps), (MANUAL_DECISION_REQUIRED, ["SETTLE_ABORT"]))  # Repair #4A boundary
        self.assertEqual((self.micro("m1"), self.marker("op_1")), (MicrotaskStatus.RECOVERY_REQUIRED, "READY"))
        with self.assertRaises(TransitionRejected):  # RECOVERY_REQUIRED has no way to ACTIVE at all
            self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        self.assertEqual(self.recover()["performed_steps"], [])

    def test_failed_verification_is_not_reactivated_under_an_abort(self):
        self.stage("write", "ACTIVE")
        self.begin_ops("write")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        self.machine.transition(TASK, "m1", MicrotaskStatus.FAILED_VERIFICATION)
        self.resolve("ABORT", "op_1")

        with self.assertRaises(TransitionRejected) as ctx:
            self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)

        self.assertIn("MICROTASK_RECOVERY_REQUIRED", ctx.exception.reason)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.FAILED_VERIFICATION)

    def test_unreadable_recovery_facts_refuse_the_activation(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        with mock.patch.object(RollbackStore, "list", side_effect=RollbackStoreError("unreadable")):
            with self.assertRaises(TransitionRejected) as ctx:
                self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        self.assertIn("LIFECYCLE_STATE_UNAVAILABLE", ctx.exception.reason)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.READY)
        self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)  # facts readable again: activation works
        self.assertEqual(self.micro("m1"), MicrotaskStatus.ACTIVE)

    def test_the_rule_counts_only_destructive_dispositions(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        coordinator = RecoveryCoordinator(self.storage)
        kwargs = dict(operations=coordinator.operations, resolver=coordinator.resolver, rollbacks=coordinator.rollbacks.store)
        self.assertIsNone(activation_refusal(TASK, "m1", **kwargs))
        self.resolve("RETRY", "op_1")  # non-destructive (INTENT, pre-state): Repair #4A's activation exit stays
        self.assertIsNone(activation_refusal(TASK, "m1", **kwargs))
        self.resolve("ABORT", "op_2")
        self.assertEqual(activation_refusal(TASK, "m1", **kwargs)[0], "MICROTASK_RECOVERY_REQUIRED")


class LegitimateOrderTests(WA014Fixture):
    """Positive control: ACTIVE before the recovery decision is a stage that could have executed."""

    def test_rollback_after_activation_then_abort_still_restores(self):
        for kind in ("write", "delete", "create"):
            with self.subTest(kind=kind):
                self.setUp()
                try:
                    self.stage(kind, "ACTIVE")
                    self.assertIsNone(self.gate())  # the authority window exists
                    self.begin_ops(kind)
                    self.external_partial(kind)
                    self.resolve("ABORT", "op_1")
                    self.resolve("ROLLBACK", "op_2")

                    result = self.recover()

                    self.assertIn("APPLY_ROLLBACK", [s["action"] for s in result["performed_steps"]])
                    self.assertEqual(self.files(), FILES[kind])
                finally:
                    self.tearDown()

    def test_direct_rc4_after_activation_then_abort_still_restores(self):
        self.stage("write", "ACTIVE")
        self.begin_ops("write")
        self.external_partial("write")
        self.resolve("ABORT", "op_1")
        resolution = self.resolve("ROLLBACK", "op_2")
        service = RollbackService(self.storage)

        prepared = service.prepare(TASK, "m1", "op_2", resolution.resolution_id)
        applied = service.apply(TASK, prepared["rollback"]["rollback_id"])

        self.assertEqual((prepared["result"], applied["result"]), ("PRESERVED", "VERIFIED"))
        self.assertEqual(self.files(), FILES["write"])


class ActivationAbortSerializationTests(WA014Fixture):
    """Race: the activation decision and an ABORT acceptance never interleave (real processes)."""

    def test_an_abort_cannot_slip_between_the_activation_check_and_active(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        activation = self.run_child(ACTIVATE_HELD.format(flags=str(self.flags), storage=str(self.storage), task=TASK))
        abort = None
        try:
            self.wait_flag("checked", activation)
            abort = self.run_child(ABORT_CHILD.format(flags=str(self.flags), storage=str(self.storage), task=TASK, hold=False))
            time.sleep(1.5)
            self.assertIsNone(abort.poll(), "the ABORT was accepted inside the activation's locked section")
        finally:
            (self.flags / "release").write_text("1")
        self.assertEqual(self.finish(activation), "ACTIVE")
        self.assertEqual(self.finish(abort), "ACCEPTED")
        self.assertEqual(self.gate()[0], "MICROTASK_RECOVERY_REQUIRED")  # ACTIVE first, ABORT after: legit order

    def test_an_activation_waits_for_an_abort_being_recorded_and_is_then_refused(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        abort = self.run_child(ABORT_CHILD.format(flags=str(self.flags), storage=str(self.storage), task=TASK, hold=True))
        activation = None
        try:
            self.wait_flag("recording", abort)
            activation = self.run_child(ACTIVATE_CHILD.format(storage=str(self.storage), task=TASK))
            time.sleep(1.5)
            self.assertIsNone(activation.poll(), "ACTIVE was decided while the ABORT was being recorded")
        finally:
            (self.flags / "release").write_text("1")
        self.assertEqual(self.finish(abort), "ACCEPTED")
        self.assertEqual(self.finish(activation), "TransitionRejected")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.READY)


if __name__ == "__main__":
    unittest.main()
