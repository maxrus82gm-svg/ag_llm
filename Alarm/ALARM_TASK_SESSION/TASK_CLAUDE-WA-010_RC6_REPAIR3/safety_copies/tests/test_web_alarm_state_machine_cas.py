"""RC-6 Repair #2A: microtask lifecycle writes are compare-and-set.

No transition decided on an observed status may overwrite a newer one, and a
verification can no longer land while RC-6 rolls the stage back."""

import json
import time
import unittest
from unittest import mock

from test_web_alarm_recovery_coordinator_repair2 import TASK, Repair2Fixture

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus
from web_alarm.recovery_coordinator import MANUAL_DECISION_REQUIRED, RECOVERY_BLOCKED, RecoveryCoordinator
from web_alarm.rollback_service import RollbackService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.state_machine import ServerStateMachine, TransitionRejected
from web_alarm.task_store import MicrotaskStatusConflict, TaskStore

SM_CHILD = """
    import json, pathlib, time
    from web_alarm.task_store import TaskStore
    from web_alarm.state_machine import ServerStateMachine, TransitionRejected
    flags = pathlib.Path({flags!r})
    real = TaskStore.compare_and_set_microtask_status
    def gated(self, *args, **kwargs):
        (flags / {read_flag!r}).write_text("1")
        deadline = time.time() + 60
        while not (flags / {go_flag!r}).exists():
            if time.time() > deadline:
                raise SystemExit("barrier timeout")
            time.sleep(0.01)
        return real(self, *args, **kwargs)
    TaskStore.compare_and_set_microtask_status = gated
    try:
        ServerStateMachine({storage!r}).transition({task!r}, "m1", {target!r}, verification_evidence="looked fine")
        print(json.dumps({{"result": "APPLIED"}}))
    except TransitionRejected as exc:
        print(json.dumps({{"result": "REJECTED", "reason": exc.reason, "current": exc.current_status.value}}))
"""

COORDINATOR_CHILD = """
    import json, pathlib, time
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    flags = pathlib.Path({flags!r})
    real = RecoveryCoordinator._rollback_stage_preflight
    def gated(self, task_id, operation_id, action, rollback_id):
        if {before!r}:
            (flags / "preflight_entered").write_text(action)
            deadline = time.time() + 60
            while not (flags / "coord_go").exists():
                if time.time() > deadline:
                    raise SystemExit("barrier timeout")
                time.sleep(0.01)
        out = real(self, task_id, operation_id, action, rollback_id)
        if not {before!r} and action == "APPLY_ROLLBACK":
            (flags / "preflight_done").write_text(action)
            deadline = time.time() + 60
            while not (flags / "coord_go").exists():
                if time.time() > deadline:
                    raise SystemExit("barrier timeout")
                time.sleep(0.01)
        return out
    RecoveryCoordinator._rollback_stage_preflight = gated
    r = RecoveryCoordinator({storage!r}).recover({task!r})
    print(json.dumps({{"state": r["state"], "recovery": r["recovery_state"],
                      "steps": [s["action"] for s in r["performed_steps"]]}}))
"""


class CasFixture(Repair2Fixture):
    def done_m1_with_partial_effect(self, *, rollback=True, prepare=True):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        (self.project / "b.txt").unlink()
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        if rollback:
            resolution = self.resolve("ROLLBACK", "op_1")
            if prepare:
                record = RollbackService(self.storage).prepare(TASK, "m1", "op_1", resolution.resolution_id)
                self.assertEqual(record["rollback"]["status"], "PRESERVED")

    def sm_child(self, target, *, read_flag="sm_read", go_flag="sm_go"):
        return self.run_child(SM_CHILD.format(
            flags=str(self.flags), read_flag=read_flag, go_flag=go_flag,
            storage=str(self.storage), task=TASK, target=target,
        ))

    def coordinator_child(self, *, before):
        return self.run_child(COORDINATOR_CHILD.format(
            flags=str(self.flags), before=before, storage=str(self.storage), task=TASK,
        ))

    def finish(self, child):
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)
        return json.loads(out.strip().splitlines()[-1])

    def event_count(self, event_type):
        return sum(1 for e in EventCheckpointStore(self.storage).read_events(TASK) if e.event_type == event_type)


class RollbackVersusVerificationTests(CasFixture):
    """A: RC-6 rollback of the current stage vs a concurrent DONE -> VERIFIED."""

    def test_a1_verification_that_lands_first_keeps_the_stage_and_blocks_the_rollback(self):
        self.done_m1_with_partial_effect()
        coordinator = self.coordinator_child(before=True)
        self.wait_flag("preflight_entered", coordinator)
        self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        (self.flags / "coord_go").write_text("1")

        result = self.finish(coordinator)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual((self.read("a.txt"), self.read("b.txt")), (b"a-after\n", None))
        self.assertEqual(self.event_count("ROLLBACK_TARGET_RESTORED"), 0)

    def test_a2_stale_verification_cannot_land_while_rc6_rolls_back(self):
        self.done_m1_with_partial_effect()
        verifier = self.sm_child("VERIFIED")
        self.wait_flag("sm_read", verifier)  # it observed DONE and decided to verify
        coordinator = self.coordinator_child(before=False)
        self.wait_flag("preflight_done", coordinator)  # stage proved and put at RECOVERY_REQUIRED
        (self.flags / "sm_go").write_text("1")
        verdict = self.finish(verifier)  # its write lands while RC-4 has not restored yet
        (self.flags / "coord_go").write_text("1")
        result = self.finish(coordinator)

        self.assertEqual(verdict["result"], "REJECTED")
        self.assertIn("stale transition", verdict["reason"])
        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(result["steps"], ["APPLY_ROLLBACK", "SETTLE_ROLLBACK"])
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)  # never VERIFIED
        self.assertEqual((self.read("a.txt"), self.read("b.txt")), (b"a-before\n", b"b-before\n"))

    def test_rollback_apply_marks_the_stage_before_any_restore(self):
        self.done_m1_with_partial_effect()
        seen = []
        real_write = __import__("web_alarm.rollback_service", fromlist=["x"])._write_restored_bytes

        def observe_then_write(path, data):
            seen.append(self.tasks.open_microtask(TASK, "m1").status)
            return real_write(path, data)

        with mock.patch("web_alarm.rollback_service._write_restored_bytes", observe_then_write):
            result = self.recover()

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertTrue(seen)
        self.assertEqual(set(seen), {MicrotaskStatus.RECOVERY_REQUIRED})


class StaleTransitionTests(CasFixture):
    """B, C, D: no transition decided on an old status overwrites a newer one."""

    def test_b_abort_settlement_is_not_overwritten_by_a_stale_verification(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_1", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        self.resolve("ABORT", "op_1")
        verifier = self.sm_child("VERIFIED")
        self.wait_flag("sm_read", verifier)

        settled = self.recover()
        (self.flags / "sm_go").write_text("1")
        verdict = self.finish(verifier)

        self.assertEqual(settled["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(verdict["result"], "REJECTED")
        self.assertEqual(verdict["current"], "RECOVERY_REQUIRED")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        again = self.recover()
        self.assertEqual((again["state"], again["recovery_state"]), (MANUAL_DECISION_REQUIRED, "NORMAL"))

    def test_c_two_transitions_from_one_observed_status_only_one_applies(self):
        self.activate("m1", "a.txt")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        transitions_before = self.event_count("MICROTASK_TRANSITION")
        verify = self.sm_child("VERIFIED", read_flag="x_read", go_flag="go")
        fail = self.sm_child("FAILED_VERIFICATION", read_flag="y_read", go_flag="go")
        self.wait_flag("x_read", verify)
        self.wait_flag("y_read", fail)
        (self.flags / "go").write_text("1")

        results = sorted([self.finish(verify)["result"], self.finish(fail)["result"]])

        self.assertEqual(results, ["APPLIED", "REJECTED"])
        self.assertIn(self.micro("m1"), (MicrotaskStatus.VERIFIED, MicrotaskStatus.FAILED_VERIFICATION))
        self.assertEqual(self.event_count("MICROTASK_TRANSITION") - transitions_before, 1)

    def test_d1_delayed_transition_never_rewrites_the_newer_status(self):
        self.activate("m1", "a.txt")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        delayed = self.sm_child("VERIFIED")
        self.wait_flag("sm_read", delayed)
        # meanwhile another process moves on
        ServerStateMachine(self.storage).transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        time.sleep(0.2)
        (self.flags / "sm_go").write_text("1")

        verdict = self.finish(delayed)

        self.assertEqual(verdict["result"], "REJECTED")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)

    def test_d2_replayed_request_with_an_old_observed_status_is_refused_in_a_fresh_process(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_1", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        observed = "DONE"  # what the client saw before its connection dropped
        self.resolve("ABORT", "op_1")
        self.recover()
        micro_file = self.tasks.task_directory(TASK) / "microtasks" / "m1.json"
        before = micro_file.read_bytes()

        with self.assertRaises(TransitionRejected) as ctx:
            ServerStateMachine(self.storage).transition(
                TASK, "m1", "VERIFIED", verification_evidence="replayed", expected_status=observed
            )

        self.assertIn("stale transition", ctx.exception.reason)
        self.assertEqual(micro_file.read_bytes(), before)

    def test_d3_server_endpoint_maps_stale_and_invalid_basis(self):
        self.activate("m1", "a.txt")
        api = WebAlarmApi(self.storage)
        body = {"task_id": TASK, "target_status": "DONE", "expected_status": "READY"}
        with self.assertRaises(ApiError) as stale:
            api.dispatch("POST", "/microtasks/m1/transition", body)
        self.assertEqual((stale.exception.status, stale.exception.code), (409, "transition_rejected"))
        with self.assertRaises(ApiError) as invalid:
            api.dispatch("POST", "/microtasks/m1/transition", dict(body, expected_status="NOPE"))
        self.assertEqual(invalid.exception.status, 400)
        status, result = api.dispatch("POST", "/microtasks/m1/transition", dict(body, expected_status="ACTIVE"))
        self.assertEqual(status, 200)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.DONE)
        del result


class LockedLifecycleWriteTests(CasFixture):
    """E-G: activation, snapshot blocking and preparation never overwrite a newer status."""

    def test_e_activation_is_refused_whole_when_another_microtask_is_active(self):
        self.activate("m1", "a.txt")
        self.verify("m1")
        self.write("b.txt", b"b\n")
        self.machine.prepare_microtask(TASK, "m2", [("b.txt", "edit")])
        self.machine.transition(TASK, "m2", MicrotaskStatus.READY)
        TaskStore(self.storage).set_microtask_status(TASK, "m3", MicrotaskStatus.ACTIVE)  # foreign shape
        plan_before = self.tasks.open_plan(TASK).current_microtask_id

        with self.assertRaises(MicrotaskStatusConflict):
            self.tasks.compare_and_set_microtask_status(
                TASK, "m2", expected=MicrotaskStatus.READY, status=MicrotaskStatus.ACTIVE, activate=True
            )

        self.assertEqual(self.micro("m2"), MicrotaskStatus.READY)
        self.assertEqual(self.tasks.open_plan(TASK).current_microtask_id, plan_before)

    def test_f_snapshot_failure_inside_transition_does_not_overwrite_a_settlement(self):
        self.activate("m1", "a.txt")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        self.machine.transition(TASK, "m1", MicrotaskStatus.FAILED_VERIFICATION)
        snap = next((self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"))
        snap.write_bytes(b"tampered")
        real = ManifestSnapshotStore.verify_restore_point

        def settle_meanwhile(store, task_id, microtask_id, **kwargs):
            # a recovery settlement lands between the transition's read and its
            # snapshot check (only the transition's own, mutating verification;
            # the later pure checkpoint rebuild must not re-inject it)
            if kwargs.get("active_only"):
                TaskStore(self.storage).set_microtask_status(task_id, microtask_id, MicrotaskStatus.RECOVERY_REQUIRED)
            return real(store, task_id, microtask_id, **kwargs)

        with mock.patch.object(ManifestSnapshotStore, "verify_restore_point", settle_meanwhile):
            with self.assertRaises(TransitionRejected):
                self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)

        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)

    def test_g_state_machine_prepare_never_rewinds_a_microtask_that_moved_on(self):
        self.write("a.txt", b"a\n")
        real = ManifestSnapshotStore.prepare_microtask

        def moved_on_meanwhile(store, task_id, microtask_id, targets, **kwargs):
            # between the state machine's PLANNED check and the restore-point write,
            # the microtask advanced (a concurrent winner prepared and readied it)
            TaskStore(self.storage).set_microtask_status(task_id, microtask_id, MicrotaskStatus.READY)
            return real(store, task_id, microtask_id, targets, **kwargs)

        with mock.patch.object(ManifestSnapshotStore, "prepare_microtask", moved_on_meanwhile):
            try:
                self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
            except (TransitionRejected, Exception):  # noqa: BLE001 - outcome checked below
                pass

        self.assertEqual(self.micro("m1"), MicrotaskStatus.READY)

    def test_g_failed_prepare_never_blocks_a_status_beyond_preparation(self):
        self.activate("m1", "a.txt")
        store = ManifestSnapshotStore(self.storage)
        store._best_effort_microtask_status(
            TASK, "m1", MicrotaskStatus.BLOCKED_PREPARE,
            expected={MicrotaskStatus.PLANNED, MicrotaskStatus.PREPARING, MicrotaskStatus.BLOCKED_PREPARE},
        )
        self.assertEqual(self.micro("m1"), MicrotaskStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
