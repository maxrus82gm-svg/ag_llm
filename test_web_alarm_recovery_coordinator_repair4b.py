"""RC-6 Repair #4B regressions: a microtask that has never been ACTIVE never gets a
destructive rollback, neither through RC-6 (after a pre-execution ABORT of a sibling
operation put it at RECOVERY_REQUIRED) nor through the direct RC-4 entry (service or
HTTP API); RC-4 never rolls back a VERIFIED or non-current stage either; the rollback
of a stage that has really executed keeps working."""

import json
import unittest
from unittest import mock

import web_alarm.rollback_service as rs

from test_web_alarm_recovery_coordinator_repair2 import AFTER, BEFORE, TASK
from test_web_alarm_recovery_coordinator_repair4a import STEP_CRASH, Repair4AFixture

from web_alarm.microtask_gate import EXECUTED_STATUSES, PRE_EXECUTION_STATUSES, rollback_refusal
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_contract import OperationContractError
from web_alarm.operation_store import OperationStoreError
from web_alarm.recovery_coordinator import (
    MANUAL_DECISION_REQUIRED,
    RECOVERY_BLOCKED,
    RecoveryCoordinator,
    RecoveryCoordinatorBlocked,
)
from web_alarm.resolution_store import ResolutionResult
from web_alarm.rollback_service import RollbackService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.state_machine import TransitionRejected

KEEP, GONE, NEW = b"keep\n", b"gone\n", b"new file\n"
FILES = {
    "write": {"a.txt": BEFORE, "keep.txt": KEEP},
    "delete": {"a.txt": BEFORE, "gone.txt": GONE, "keep.txt": KEEP},
    "create": {"keep.txt": KEEP},
}
SPECS = {
    "write": [("a.txt", "edit"), ("keep.txt", "delete")],
    "delete": [("a.txt", "edit"), ("gone.txt", "delete"), ("keep.txt", "delete")],
    "create": [("new.txt", "create"), ("keep.txt", "delete")],
}
PATH = {
    "BACKUP_VERIFIED": (),
    "READY": (MicrotaskStatus.READY,),
    "ACTIVE": (MicrotaskStatus.READY, MicrotaskStatus.ACTIVE),
    "UNKNOWN_AFTER_DISCONNECT": (
        MicrotaskStatus.READY, MicrotaskStatus.ACTIVE, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
    ),
}

PREPARE_CRASH_SPECS = """
    import os
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    if {window!r} == "W1":
        def die(self, *a, **k):
            os._exit(23)  # PREPARING written, nothing published
        ManifestSnapshotStore._resolve_target = die
    else:
        real = TaskStore.compare_and_set_microtask_status
        def die(self, t, m, *, expected, status, activate=False):
            if getattr(status, "value", status) == "BACKUP_VERIFIED":
                os._exit(29)  # the restore point is published, its status is not
            return real(self, t, m, expected=expected, status=status, activate=activate)
        TaskStore.compare_and_set_microtask_status = die
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", {specs!r})
"""

RACE_CHILD = """
    import json, pathlib, time
    from web_alarm.operation_store import OperationStore
    from web_alarm.reconciliation_service import ReconciliationService
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    from web_alarm.resolver_service import ResolverService
    from web_alarm.rollback_service import RollbackService
    storage, task, role = {storage!r}, {task!r}, {role!r}
    flags = pathlib.Path({flags!r})
    (flags / ("ready_" + role)).write_text("1")
    while not (flags / "go").exists():
        time.sleep(0.001)
    try:
        if role == "abort":
            decision = ReconciliationService(storage).reconcile(task, "m1", "op_1")["DECISION"]
            r = ResolverService(storage).apply(
                task, "m1", "op_1", "ABORT", evidence_fingerprint=decision["evidence_fingerprint"],
                operation_revision=OperationStore(storage).get(task, "op_1").revision)["resolution"]
            out = {{"abort": r.result.value}}
        elif role == "rc4":
            rb = RollbackService(storage)
            p = rb.prepare(task, "m1", "op_2", {resolution_id!r})
            out = {{"prepare": p["result"], "code": p["result_code"]}}
            if p["rollback"] is not None:
                a = rb.apply(task, p["rollback"]["rollback_id"])
                out.update(apply=a["result"], apply_code=a["result_code"])
        else:
            r = RecoveryCoordinator(storage).recover(task)
            out = {{"state": r["state"], "steps": [s["action"] for s in r["performed_steps"]]}}
    except Exception as exc:
        out = {{"error": type(exc).__name__, "message": str(exc)[:300]}}
    print(json.dumps(out))
"""


class Repair4BFixture(Repair4AFixture):
    def stage(self, kind, status):
        for name, data in FILES[kind].items():
            self.write(name, data)
        self.machine.prepare_microtask(TASK, "m1", SPECS[kind])
        for step in PATH[status]:
            self.machine.transition(TASK, "m1", step)

    def begin_ops(self, kind, *, sibling=True):
        if sibling:
            self.ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_1", payload=b"keep-v2\n")
        if kind == "create":
            self.ops.begin(TASK, "m1", "create_file", "new.txt", operation_id="op_2", payload=NEW)
        else:
            self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_2", payload=AFTER)

    def external_partial(self, kind):
        """op_2 STARTED (a lifecycle record only) and its target changed outside the server."""
        self.ops.transition(TASK, "op_2", OperationStatus.STARTED)
        if kind == "create":
            self.write("new.txt", NEW)
        else:
            self.write("a.txt", AFTER)
        if kind == "delete":
            (self.project / "gone.txt").unlink()

    def files(self):
        return {p.name: p.read_bytes() for p in sorted(self.project.iterdir()) if p.is_file()}

    def sessions(self):
        return RollbackService(self.storage).store.list(TASK)

    def marker(self, op):
        return (self.ops.get(TASK, op).recovery_settlement or {}).get("microtask_status")

    def abort_op1_settled(self):
        self.resolve("ABORT", "op_1")
        result = self.recover()
        self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)

    def never_executed_with_rollback(self, kind="write", status="READY"):
        """m1 never ACTIVE; op_1 ABORT settled (m1 RECOVERY_REQUIRED); op_2 ROLLBACK accepted."""
        self.stage(kind, status)
        self.begin_ops(kind)
        self.abort_op1_settled()
        self.external_partial(kind)
        return self.resolve("ROLLBACK", "op_2")

    def assert_nothing_restored(self, files_before, *, sessions=0):
        self.assertEqual(self.files(), files_before)
        self.assertEqual(len(self.sessions()), sessions)
        self.assertEqual([c for c in self.active_claims() if c[0] == TASK], [])
        self.assertIsNone(self.ops.get(TASK, "op_2").recovery_settlement)

    def api_prepare(self, resolution_id, op="op_2"):
        with self.assertRaises(ApiError) as ctx:
            WebAlarmApi(self.storage).dispatch("POST", f"/tasks/{TASK}/rollbacks", {
                "microtask_id": "m1", "operation_id": op, "resolution_id": resolution_id})
        return ctx.exception


class SiblingRollbackOfNeverExecutedMicrotaskTests(Repair4BFixture):
    """B1 / B8: pre-execution ABORT (op_1) x accepted ROLLBACK (op_2) through RC-6."""

    def test_b1_rc6_never_restores_for_any_target_kind_or_pre_execution_status(self):
        for kind in ("write", "delete", "create"):
            for status in ("BACKUP_VERIFIED", "READY"):
                with self.subTest(kind=kind, status=status):
                    self.setUp()
                    try:
                        self.never_executed_with_rollback(kind, status)
                        self.assertEqual(self.marker("op_1"), status)  # decided before execution
                        before, digest = self.files(), self.digest()

                        result = self.recover()

                        self.assertEqual((result["state"], result["performed_steps"]), (MANUAL_DECISION_REQUIRED, []))
                        self.assertIn("never been ACTIVE", result["reason"])
                        self.assert_nothing_restored(before)
                        self.assertEqual(self.digest(), digest)  # nothing written at all
                        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
                    finally:
                        self.tearDown()

    def test_b1_rollback_preflight_refuses_even_if_the_step_were_chosen(self):
        resolution = self.never_executed_with_rollback()
        coordinator = RecoveryCoordinator(self.storage)
        before = self.files()

        for action, rollback_id in (("PREPARE_ROLLBACK", None), ("APPLY_ROLLBACK", "rb_any")):
            with self.subTest(action=action), self.assertRaises(RecoveryCoordinatorBlocked) as ctx:
                if rollback_id is None:
                    coordinator._rollback_stage_preflight(TASK, "op_2", action, None)
                else:  # an RC-4 session made by an older build: still no destructive apply
                    with mock.patch.object(rs, "rollback_refusal", return_value=None):
                        session = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
                    coordinator._rollback_stage_preflight(TASK, "op_2", action, session["rollback"]["rollback_id"])
            self.assertIn("MICROTASK_NEVER_EXECUTED", str(ctx.exception))
        self.assertEqual(self.files(), before)

    def test_b1_abort_of_the_rollback_operation_closes_it_without_any_restore(self):
        self.never_executed_with_rollback("delete")
        before = self.files()
        self.recover()
        self.resolve("ABORT", "op_2")

        result = self.recover()

        self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(self.settlements("op_1", "op_2"), {"op_1": "ABORT", "op_2": "ABORT"})
        self.assertEqual(self.marker("op_2"), "RECOVERY_REQUIRED")
        self.assertEqual(self.files(), before)
        self.assertEqual(self.sessions(), [])


class DirectRollbackEntryTests(Repair4BFixture):
    """B2 / B8 + R1: RC-4 itself (service and HTTP API) refuses a protected or never-executed stage."""

    def test_b2_direct_rc4_refuses_after_the_sibling_abort(self):
        for kind in ("write", "create"):
            with self.subTest(kind=kind):
                self.setUp()
                try:
                    resolution = self.never_executed_with_rollback(kind)
                    before = self.files()

                    outcome = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)

                    self.assertEqual((outcome["result"], outcome["result_code"]), ("REJECTED", "MICROTASK_NEVER_EXECUTED"))
                    self.assertIsNone(outcome["rollback"])
                    self.assert_nothing_restored(before)
                    self.assertEqual(self.events("ROLLBACK_REJECTED"), 1)
                    error = self.api_prepare(resolution.resolution_id)
                    self.assertEqual((error.status, error.code), (409, "rollback_rejected"))
                    self.assert_nothing_restored(before)
                finally:
                    self.tearDown()

    def test_b2_direct_rc4_refuses_a_never_executed_microtask_without_any_abort(self):
        for status in ("BACKUP_VERIFIED", "READY"):
            with self.subTest(status=status):
                self.setUp()
                try:
                    self.stage("write", status)
                    self.begin_ops("write")
                    self.external_partial("write")
                    resolution = self.resolve("ROLLBACK", "op_2")
                    before = self.files()

                    outcome = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
                    error = self.api_prepare(resolution.resolution_id)

                    self.assertEqual(outcome["result_code"], "MICROTASK_NEVER_EXECUTED")
                    self.assertEqual(error.code, "rollback_rejected")
                    self.assert_nothing_restored(before)
                    self.assertEqual(self.recover()["state"], MANUAL_DECISION_REQUIRED)  # Repair #4A boundary
                    self.assert_nothing_restored(before)
                finally:
                    self.tearDown()

    def test_b2_session_prepared_by_an_older_build_is_never_applied(self):
        resolution = self.never_executed_with_rollback()
        with mock.patch.object(rs, "rollback_refusal", return_value=None):
            session = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
        self.assertEqual(session["result"], "PRESERVED")
        before = self.files()

        applied = RollbackService(self.storage).apply(TASK, session["rollback"]["rollback_id"])
        recovered = self.recover()

        self.assertEqual((applied["result"], applied["result_code"]), ("BLOCKED", "MICROTASK_NEVER_EXECUTED"))
        self.assertEqual(applied["rollback"]["status"], "PRESERVED")  # never AUTHORIZED: no claim taken
        self.assertEqual(recovered["state"], RECOVERY_BLOCKED)
        self.assertIn("MICROTASK_NEVER_EXECUTED", recovered["reason"])
        self.assert_nothing_restored(before, sessions=1)
        closed = RollbackService(self.storage).close(TASK, session["rollback"]["rollback_id"])
        self.assertEqual(closed["result"], "CLOSED")
        self.assertEqual(self.files(), before)

    def test_r1_direct_rc4_never_rolls_back_a_verified_or_non_current_stage(self):
        for last_stage in (True, False):
            with self.subTest(last_stage=last_stage):
                self.setUp()
                try:
                    if last_stage:  # nothing after m1 is left to do: no current stage at all
                        for mid in ("m2", "m3"):
                            self.tasks.set_microtask_status(TASK, mid, MicrotaskStatus.VERIFIED)
                    self.stage("write", "ACTIVE")
                    self.verify("m1")
                    self.begin_ops("write")
                    self.external_partial("write")  # a late operation of the VERIFIED stage
                    resolution = self.resolve("ROLLBACK", "op_2")
                    before = self.files()

                    outcome = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
                    error = self.api_prepare(resolution.resolution_id)

                    self.assertEqual(outcome["result_code"], "ROLLBACK_STAGE_PROTECTED")
                    self.assertEqual(error.code, "rollback_rejected")
                    self.assert_nothing_restored(before)
                    self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
                finally:
                    self.tearDown()


class ExecutedStageRollbackTests(Repair4BFixture):
    """B3 / B8: a stage that has really been ACTIVE is still rolled back (RC-6 and direct RC-4)."""

    def test_b3_rollback_after_active_then_unknown_restores_every_kind(self):
        for kind in ("write", "delete", "create"):
            with self.subTest(kind=kind):
                self.setUp()
                try:
                    self.stage(kind, "UNKNOWN_AFTER_DISCONNECT")
                    self.begin_ops(kind, sibling=False)
                    self.external_partial(kind)
                    self.resolve("ROLLBACK", "op_2")

                    result = self.recover()

                    self.assertEqual([s["action"] for s in result["performed_steps"]],
                                     ["PREPARE_ROLLBACK", "APPLY_ROLLBACK", "SETTLE_ROLLBACK"])
                    self.assertEqual(self.files(), FILES[kind])  # exact restore-point bytes
                    self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
                    self.assertEqual(self.settlements("op_2"), {"op_2": "ROLLBACK"})
                    self.assertEqual(self.marker("op_2"), "RECOVERY_REQUIRED")
                finally:
                    self.tearDown()

    def test_b3_sibling_abort_settled_while_active_keeps_the_rollback(self):
        self.stage("write", "ACTIVE")
        self.begin_ops("write")
        self.abort_op1_settled()
        self.assertEqual(self.marker("op_1"), "ACTIVE")
        self.external_partial("write")
        self.resolve("ROLLBACK", "op_2")

        result = self.recover()

        self.assertEqual([s["action"] for s in result["performed_steps"]],
                         ["PREPARE_ROLLBACK", "APPLY_ROLLBACK", "SETTLE_ROLLBACK"])
        self.assertEqual(self.files(), FILES["write"])

    def test_b3_direct_rc4_restores_an_active_stage(self):
        self.stage("delete", "ACTIVE")
        self.begin_ops("delete", sibling=False)
        self.external_partial("delete")
        resolution = self.resolve("ROLLBACK", "op_2")
        service = RollbackService(self.storage)

        prepared = service.prepare(TASK, "m1", "op_2", resolution.resolution_id)
        applied = service.apply(TASK, prepared["rollback"]["rollback_id"])

        self.assertEqual((prepared["result"], applied["result"]), ("PRESERVED", "VERIFIED"))
        self.assertEqual(self.files(), FILES["delete"])
        self.assertEqual(self.active_claims(), [])


class RestartAndCrashTests(Repair4BFixture):
    """B4 / B5: repeated recover, a fresh process, crashes around the settlement and the preparation."""

    def test_b4_repeated_recover_and_a_fresh_process_stay_at_the_boundary(self):
        self.never_executed_with_rollback("create")
        before, digest = self.files(), self.digest()

        states = [self.recover()["state"] for _ in range(3)]
        state, steps, _ = self.fresh_recover()

        self.assertEqual(set(states) | {state}, {MANUAL_DECISION_REQUIRED})
        self.assertEqual(steps, [])
        self.assert_nothing_restored(before)
        self.assertEqual(self.digest(), digest)

    def test_b4_crash_between_the_abort_settlement_and_the_status_keeps_the_fact(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        self.resolve("ABORT", "op_1")
        self.crash_step("between_writes", 43)
        self.assertEqual((self.micro("m1"), self.marker("op_1")), (MicrotaskStatus.READY, "READY"))
        with self.assertRaises(TransitionRejected):  # WA-014: no activation in the crash window either
            self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        self.external_partial("write")
        resolution = self.resolve("ROLLBACK", "op_2")
        before = self.files()

        direct = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
        state, steps, _ = self.fresh_recover()

        self.assertEqual(direct["result_code"], "MICROTASK_NEVER_EXECUTED")  # ABORT preceded any authority
        self.assertEqual(state, MANUAL_DECISION_REQUIRED)
        self.assertTrue(set(steps) <= {"FINISH_SETTLEMENT"}, steps)  # never a rollback step
        self.assertEqual(self.gate()[0], "MICROTASK_NOT_ACTIVE")  # no mutation authority at any point
        self.assert_nothing_restored(before)
        self.resolve("ABORT", "op_2")  # the named way out
        closed = self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.settlements("op_1", "op_2"), {"op_1": "ABORT", "op_2": "ABORT"})
        self.assertEqual((self.recover()["state"], self.recover()["performed_steps"]), (MANUAL_DECISION_REQUIRED, []))
        self.assertNotEqual(closed["state"], "FAIL_CLOSED")
        self.assertEqual(self.files(), before)
        self.assertEqual(self.sessions(), [])

    def crash_prepare_specs(self, window, kind, expect_exit):
        for name, data in FILES[kind].items():
            self.write(name, data)
        child = self.run_child(PREPARE_CRASH_SPECS.format(
            window=window, storage=str(self.storage), task=TASK, specs=SPECS[kind]))
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, expect_exit, err)

    def test_b5_w2_abort_then_sibling_rollback_is_refused(self):
        self.begin_ops("write")
        self.crash_prepare_specs("W2", "write", 29)
        self.resolve("ABORT", "op_1")

        settled = self.recover()

        self.assertEqual([s["action"] for s in settled["performed_steps"]], ["RECONCILE_PREPARATION", "SETTLE_ABORT"])
        self.assertEqual(self.marker("op_1"), "BACKUP_VERIFIED")
        self.external_partial("write")
        resolution = self.resolve("ROLLBACK", "op_2")
        before = self.files()
        self.assertEqual(self.recover()["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
                         ["result_code"], "MICROTASK_NEVER_EXECUTED")
        self.assert_nothing_restored(before)

    def test_b5_w1_abort_leaves_no_restore_point_to_roll_back(self):
        self.begin_ops("write")
        self.crash_prepare_specs("W1", "write", 23)
        self.resolve("ABORT", "op_1")
        self.recover()
        self.assertEqual((self.micro("m1"), self.marker("op_1")), (MicrotaskStatus.RECOVERY_REQUIRED, "BLOCKED_PREPARE"))
        self.external_partial("write")
        before = self.files()

        rollback = self.resolve_any("ROLLBACK", "op_2")

        self.assertEqual(rollback.result, ResolutionResult.REJECTED)  # no restore point: nothing to restore
        self.assertEqual(self.recover()["performed_steps"], [])
        self.assert_nothing_restored(before)


class SettlementFactTests(Repair4BFixture):
    """B6: stale resolution, legacy settlements, the settlement fact itself."""

    def test_b6_stale_rollback_of_a_never_executed_microtask_restores_nothing(self):
        resolution = self.never_executed_with_rollback()
        self.write("a.txt", b"changed again outside\n")  # the ROLLBACK basis is stale now
        before = self.files()

        direct = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
        result = self.recover()

        self.assertEqual(direct["result"], "REJECTED")
        self.assertNotIn(result["state"], {"FAIL_CLOSED"})
        self.assert_nothing_restored(before)

    def test_b6_abort_settlement_recorded_before_repair_4b_leaves_execution_unproven(self):
        self.stage("write", "ACTIVE")
        self.begin_ops("write")
        self.abort_op1_settled()
        path = self.ops._path(TASK, "op_1", active_only=True)
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["recovery_settlement"]["microtask_status"]  # the shape written before Repair #4B
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.assertNotIn("microtask_status", self.ops.get(TASK, "op_1").recovery_settlement)  # still readable
        self.external_partial("write")
        resolution = self.resolve("ROLLBACK", "op_2")
        before = self.files()

        direct = RollbackService(self.storage).prepare(TASK, "m1", "op_2", resolution.resolution_id)
        result = self.recover()

        self.assertEqual(direct["result_code"], "MICROTASK_EXECUTION_UNPROVEN")
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertIn("MICROTASK_EXECUTION_UNPROVEN", result["reason"])
        self.assert_nothing_restored(before)

    def test_b6_the_settlement_fact_is_validated_and_not_part_of_the_replay_identity(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        resolution = self.resolve("ABORT", "op_1")
        with self.ops.task_lock(TASK):
            with self.assertRaises((OperationContractError, OperationStoreError)):
                self.ops._settle_recovery_locked(TASK, "op_1", "ABORT", resolution_id=resolution.resolution_id,
                                                 expected_revision=1, microtask_status="NOT_A_STATUS")
            first = self.ops._settle_recovery_locked(TASK, "op_1", "ABORT", resolution_id=resolution.resolution_id,
                                                     expected_revision=1, microtask_status="READY")
            replay = self.ops._settle_recovery_locked(TASK, "op_1", "ABORT", resolution_id=resolution.resolution_id,
                                                      expected_revision=1, microtask_status="ACTIVE")
        self.assertEqual((first["changed"], replay["replayed"]), (True, True))
        self.assertEqual(self.marker("op_1"), "READY")  # the first fact stays

    def test_b6_every_rc6_settlement_records_the_status_it_was_decided_on(self):
        self.activate("m1", "a.txt")  # a single target: ADOPT needs the exact post-state everywhere
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        self.write("a.txt", AFTER)
        self.resolve("ADOPT", "op_1")

        self.recover()

        self.assertEqual((self.settlements("op_1"), self.marker("op_1")), ({"op_1": "ADOPT"}, "ACTIVE"))


class RollbackGateTableTests(Repair4BFixture):
    """The one rule RC-4 and RC-6 share (microtask_gate.rollback_refusal)."""

    def refusal(self, mid="m1"):
        coordinator = RecoveryCoordinator(self.storage)
        result = rollback_refusal(TASK, mid, tasks=coordinator.tasks, operations=coordinator.operations)
        return result[0] if result else None

    def test_status_table(self):
        for status in MicrotaskStatus:
            with self.subTest(status=status.value):
                self.tasks.set_microtask_status(TASK, "m1", status)
                expected = (
                    "ROLLBACK_STAGE_PROTECTED" if status is MicrotaskStatus.VERIFIED
                    else None if status.value in EXECUTED_STATUSES | {"RECOVERY_REQUIRED"}
                    else "MICROTASK_NEVER_EXECUTED"
                )
                self.assertEqual(self.refusal(), expected)
        self.assertTrue(PRE_EXECUTION_STATUSES.isdisjoint(EXECUTED_STATUSES))

    def test_non_current_stage_and_unreadable_facts_refuse(self):
        self.tasks.set_microtask_status(TASK, "m2", MicrotaskStatus.ACTIVE)  # m1 is not VERIFIED
        self.assertEqual(self.refusal("m2"), "ROLLBACK_STAGE_PROTECTED")
        with mock.patch.object(type(self.ops), "list", side_effect=OperationStoreError("unreadable")):
            self.assertEqual(self.refusal("m1"), "LIFECYCLE_STATE_UNAVAILABLE")

    def test_a_pre_execution_settlement_refuses_whatever_the_status_is_now(self):
        self.stage("write", "READY")
        self.begin_ops("write")
        self.abort_op1_settled()
        for status in ("RECOVERY_REQUIRED", "ACTIVE", "UNKNOWN_AFTER_DISCONNECT"):
            with self.subTest(status=status):
                self.tasks.set_microtask_status(TASK, "m1", MicrotaskStatus(status))
                self.assertEqual(self.refusal(), "MICROTASK_NEVER_EXECUTED")


class ConcurrentAbortRollbackRecoverTests(Repair4BFixture):
    """B7: ABORT acceptance, direct RC-4 and two recover calls race on a never-executed microtask."""

    def test_b7_race_never_restores_a_never_executed_stage(self):
        for round_no in range(3):
            with self.subTest(round=round_no):
                self.setUp()
                try:
                    self.stage("write", "READY")
                    self.begin_ops("write")
                    self.external_partial("write")
                    resolution = self.resolve("ROLLBACK", "op_2")
                    before = self.files()
                    roles = ("abort", "recover_a", "rc4", "recover_b")
                    children = [self.run_child(RACE_CHILD.format(
                        storage=str(self.storage), task=TASK, role=role, flags=str(self.flags),
                        resolution_id=resolution.resolution_id)) for role in roles]
                    try:
                        for role, child in zip(roles, children):
                            self.wait_flag("ready_" + role, child)
                        (self.flags / "go").write_text("1")
                        outputs = {}
                        for role, child in zip(roles, children):
                            out, err = child.communicate(timeout=180)
                            self.assertEqual(child.returncode, 0, err)
                            outputs[role] = json.loads(out.strip().splitlines()[-1])
                    finally:
                        (self.flags / "go").write_text("1")
                        for child in children:
                            if child.poll() is None:
                                child.kill()
                    for role, out in outputs.items():
                        self.assertNotIn("error", out, (role, out))
                    self.assertEqual(outputs["rc4"]["prepare"], "REJECTED")
                    self.assertEqual(outputs["abort"]["abort"], "ACCEPTED")
                    final = self.recover()
                    self.assertNotEqual(final["state"], "FAIL_CLOSED")
                    self.assert_nothing_restored(before)
                finally:
                    self.tearDown()


if __name__ == "__main__":
    unittest.main()
