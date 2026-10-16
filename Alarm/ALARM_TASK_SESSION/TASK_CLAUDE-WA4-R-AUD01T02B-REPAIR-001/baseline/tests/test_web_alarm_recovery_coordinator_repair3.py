"""RC-6 Repair #3 regressions: F-C one mutation-authority gate, F-B late recovery
vs VERIFIED, R3 READY bound to the full protected basis, crash consistency of
activation (F4) and restore-point blocking (F5), C1 ABORT of a terminal
operation."""

import json
import time
import unittest
from unittest import mock

from test_web_alarm_recovery_coordinator_repair2 import (
    AFTER,
    BEFORE,
    OTHER,
    TASK,
    Repair2Fixture,
)

from web_alarm.manifest_store import ManifestSnapshotStore, ManifestStoreError
from web_alarm.microtask_gate import (
    effective_settlement_target,
    execution_refusal,
    verification_refusal,
)
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.projection import ProjectionService
from web_alarm.recovery_coordinator import (
    MANUAL_DECISION_REQUIRED,
    NO_ACTION_REQUIRED,
    READY_FOR_EXECUTION,
    RECOVERY_BLOCKED,
    RecoveryCoordinator,
)
from web_alarm.rollback_service import RollbackService
from web_alarm.rollback_store import RollbackStore, RollbackStoreError
from web_alarm.state_machine import TransitionRejected
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore


class Repair3Fixture(Repair2Fixture):
    def claims(self):
        return TargetClaimService(self.storage)

    def rev(self, op, task=TASK):
        return self.ops.get(task, op).revision

    def intent(self, mid, target, op, *, claim=True, task=TASK, payload=AFTER):
        self.ops.begin(task, mid, "write", target, operation_id=op, payload=payload)
        if claim:
            out = self.claims().acquire(task, op, operation_revision=self.rev(op, task))
            self.assertEqual(out["result"], "ACQUIRED", out["reason"])

    def authorize(self, op, task=TASK):
        return self.claims().authorize(task, op, operation_revision=self.rev(op, task))

    def assert_denied(self, outcome, code):
        self.assertEqual((outcome["result"], outcome["result_code"]), ("DENIED", code), outcome["reason"])
        self.assertFalse(outcome["authorized"])

    def done_op(self, mid, target, op):
        """An operation whose mutation fate is closed: STARTED, landed, DONE."""
        self.start(mid, target, op, landed=True)
        self.ops.transition(TASK, op, OperationStatus.DONE)

    def gate(self, mid, task=TASK):
        service = RecoveryCoordinator(self.storage)
        return execution_refusal(
            task, mid, tasks=service.tasks, operations=service.operations,
            resolver=service.resolver, rollbacks=service.rollbacks.store,
        )


class MutationAuthorityGateTests(Repair3Fixture):
    """F-C: no operation gets mutation authority where its microtask forbids normal mutation."""

    def test_fc_new_operation_after_abort_gets_no_authority(self):
        self.activate("m1", "a.txt", "b.txt")
        self.start("m1", "a.txt", "op_1", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ABORT", "op_1")
        self.assertEqual(self.recover()["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)

        self.intent("m1", "b.txt", "op_new")  # ownership stays grantable (RC-3) ...
        outcome = self.authorize("op_new")    # ... authority is not

        self.assert_denied(outcome, "MICROTASK_NOT_ACTIVE")
        self.assertEqual(self.read("b.txt"), BEFORE)
        with self.claims().mutation_boundary(TASK, "op_new", operation_revision=self.rev("op_new")) as boundary:
            self.assertFalse(boundary["mutation_authority"])

    def test_fc_old_sibling_claim_gets_no_authority_after_abort(self):
        self.activate("m1", "a.txt", "b.txt")
        self.intent("m1", "b.txt", "op_old")
        self.assertEqual(self.authorize("op_old")["result"], "AUTHORIZED")  # legitimate while ACTIVE
        self.start("m1", "a.txt", "op_1", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ABORT", "op_1")
        self.recover()

        self.assert_denied(self.authorize("op_old"), "MICROTASK_NOT_ACTIVE")

    def test_fc_accepted_but_unsettled_abort_of_a_sibling_already_blocks_authority(self):
        self.activate("m1", "a.txt", "b.txt")
        self.intent("m1", "b.txt", "op_old")
        self.start("m1", "a.txt", "op_1", landed=False)
        self.resolve("ABORT", "op_1")  # not settled yet: m1 is still ACTIVE
        self.assertEqual(self.micro("m1"), MicrotaskStatus.ACTIVE)

        self.assert_denied(self.authorize("op_old"), "MICROTASK_RECOVERY_REQUIRED")

    def test_fc_open_rollback_session_of_a_sibling_blocks_authority(self):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", BEFORE), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "edit"), ("c.txt", "delete")])
        self.intent("m1", "b.txt", "op_old")
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        resolution = self.resolve("ROLLBACK", "op_1")
        self.assert_denied(self.authorize("op_old"), "MICROTASK_RECOVERY_REQUIRED")  # accepted ROLLBACK
        RollbackService(self.storage).prepare(TASK, "m1", "op_1", resolution.resolution_id)

        self.assertEqual(self.gate("m1")[0], "MICROTASK_RECOVERY_REQUIRED")  # open RC-4 session

    def test_fc_verified_and_not_yet_active_microtasks_give_no_authority(self):
        self.activate("m1", "a.txt")
        self.verify("m1")
        self.intent("m1", "a.txt", "op_late")
        self.assert_denied(self.authorize("op_late"), "MICROTASK_NOT_ACTIVE")
        self.write("b.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m2", [("b.txt", "edit")])
        self.machine.transition(TASK, "m2", MicrotaskStatus.READY)
        self.intent("m2", "b.txt", "op_early")
        self.assert_denied(self.authorize("op_early"), "MICROTASK_NOT_ACTIVE")
        self.machine.transition(TASK, "m2", MicrotaskStatus.ACTIVE)
        self.assertEqual(self.authorize("op_early")["result"], "AUTHORIZED")

    def test_fc_active_microtask_that_is_not_the_current_stage_gets_no_authority(self):
        self.activate("m1", "a.txt")
        self.write("b.txt", BEFORE)
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, "m2", [("b.txt", "edit")])
        self.tasks.set_microtask_status(TASK, "m2", MicrotaskStatus.ACTIVE)  # legacy shape: two ACTIVE
        self.intent("m2", "b.txt", "op_2")

        self.assert_denied(self.authorize("op_2"), "MICROTASK_NOT_CURRENT")
        self.intent("m1", "a.txt", "op_1")
        self.assertEqual(self.authorize("op_1")["result"], "AUTHORIZED")

    def test_fc_lifecycle_cannot_change_while_authority_is_held(self):
        self.activate("m1", "a.txt")
        self.intent("m1", "a.txt", "op_1")
        child = self.run_child(f"""
            import json
            from web_alarm.state_machine import ServerStateMachine
            ServerStateMachine({str(self.storage)!r}).transition({TASK!r}, "m1", "DONE")
            print(json.dumps("DONE"))
        """)
        with self.claims().mutation_boundary(TASK, "op_1", operation_revision=self.rev("op_1")) as boundary:
            self.assertTrue(boundary["mutation_authority"])
            self.write("a.txt", AFTER)  # stand-in WA-4E write
            time.sleep(1.5)
            self.assertIsNone(child.poll())  # the transition waits for the boundary
            self.assertEqual(self.micro("m1"), MicrotaskStatus.ACTIVE)
        out, err = child.communicate(timeout=60)
        self.assertEqual(child.returncode, 0, err)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.DONE)

    def test_fc_rc6_ready_and_rc3_authority_follow_the_same_gate(self):
        self.activate("m1", "a.txt")
        self.intent("m1", "a.txt", "op_1")
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("RETRY", "op_1")

        ready = self.recover()

        self.assertEqual((ready["state"], ready["ready_proof"]["kind"]), (READY_FOR_EXECUTION, "RETRY"))
        self.assertEqual(self.claims().acquire(TASK, "op_1", operation_revision=self.rev("op_1"))["result"], "REBASED")
        self.assertEqual(self.authorize("op_1")["result"], "AUTHORIZED")

    def test_fc_rc6_retry_ready_is_refused_by_the_gate_over_a_pending_sibling_abort(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_2", landed=False)
        self.resolve("ABORT", "op_2")  # accepted, not settled
        self.intent("m1", "a.txt", "op_1", claim=False)
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("RETRY", "op_1")  # later activity: RC-6 focuses op_1

        result = self.recover()

        self.assertNotEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertIn("MICROTASK_RECOVERY_REQUIRED", result["reason"])
        self.assertNotIn("REARM_RETRY", [s["action"] for s in result["performed_steps"]])

    def test_fc_unreadable_lifecycle_facts_refuse_authority(self):
        self.activate("m1", "a.txt")
        self.intent("m1", "a.txt", "op_1")
        with mock.patch.object(RollbackStore, "list", side_effect=RollbackStoreError("unreadable")):
            self.assert_denied(self.authorize("op_1"), "LIFECYCLE_STATE_UNAVAILABLE")
        self.assertEqual(self.authorize("op_1")["result"], "AUTHORIZED")


class LateRecoveryVersusVerifiedTests(Repair3Fixture):
    """F-B: verification and a recovery decision of one microtask can no longer deadlock it."""

    def test_fb_verified_is_refused_while_an_accepted_abort_is_unsettled(self):
        self.activate("m1", "a.txt")
        self.done_op("m1", "a.txt", "op_1")  # mutation fate closed
        self.resolve("ABORT", "op_1")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)

        with self.assertRaises(TransitionRejected) as refused:
            self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        self.assertIn("RECOVERY_OPEN", refused.exception.reason)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.DONE)

        first = self.recover()
        second = self.recover()
        self.assertEqual(first["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual([s["action"] for s in first["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual((second["state"], second["performed_steps"]), (MANUAL_DECISION_REQUIRED, []))
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)

    def test_fb_verified_is_refused_while_an_operation_fate_is_open(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_1", landed=True)
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        with self.assertRaises(TransitionRejected) as refused:
            self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        self.assertIn("OPERATION_FATE_OPEN", refused.exception.reason)
        self.ops.transition(TASK, "op_1", OperationStatus.DONE)  # the executor closes the fate
        self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)

    def test_fb_abort_accepted_after_verified_is_settled_administratively(self):
        self.activate("m1", "a.txt")
        self.done_op("m1", "a.txt", "op_1")
        self.verify("m1")
        self.resolve("ABORT", "op_1")  # a later decision about an operation of a verified stage

        first = self.recover()
        before = self.digest()
        second = self.recover()

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(first["state"], NO_ACTION_REQUIRED)  # m2 is only PLANNED
        self.assertEqual(self.settlements("op_1"), {"op_1": "ABORT"})
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual(self.read("a.txt"), AFTER)
        self.assertEqual((second["state"], second["performed_steps"]), (NO_ACTION_REQUIRED, []))
        self.assertEqual(self.digest(), before)

    def test_fb_legacy_verified_with_adopt_accepted_is_settled_without_moving_it(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_1", landed=True)
        self.legacy_verify("m1")
        self.resolve("ADOPT", "op_1")

        result = self.recover()

        self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ADOPT"])
        self.assertEqual(self.ops.get(TASK, "op_1").status, OperationStatus.VERIFIED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual(result["recovery_state"], "NORMAL")

    def test_fb_rollback_of_a_verified_stage_waits_for_an_explicit_abort_which_closes_it(self):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        self.legacy_verify("m1")
        self.resolve("ROLLBACK", "op_1")
        blocked = self.recover()
        self.assertEqual(blocked["recovery_state"], "ROLLBACK_STAGE_PROTECTED")

        self.resolve("ABORT", "op_1")  # the explicit decision
        closed = self.recover()

        self.assertEqual([s["action"] for s in closed["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(closed["recovery_state"], "NORMAL")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual(self.read("a.txt"), b"a-after\n")  # nothing restored

    VERIFY_CHILD = """
        import json, pathlib, time
        import web_alarm.microtask_gate as gate
        from web_alarm.state_machine import ServerStateMachine, TransitionRejected
        flags = pathlib.Path({flags!r})
        real = gate.verification_refusal
        def paused(projection, microtask_id):
            # inside the locked admission section: TASK lock + mutation lock held
            (flags / "admission_locked").write_text("1")
            deadline = time.time() + 60
            while not (flags / "admission_go").exists() and time.time() < deadline:
                time.sleep(0.01)
            return real(projection, microtask_id)
        gate.verification_refusal = paused
        try:
            ServerStateMachine({storage!r}).transition({task!r}, "m1", "VERIFIED", verification_evidence="ok")
            print(json.dumps("APPLIED"))
        except TransitionRejected as exc:
            print(json.dumps("REJECTED: " + exc.reason))
    """

    RESOLVE_CHILD = """
        import json, pathlib, time
        from web_alarm.operation_store import OperationStore
        from web_alarm.reconciliation_service import ReconciliationService
        from web_alarm.resolver_service import ResolverService
        flags = pathlib.Path({flags!r})
        decision = ReconciliationService({storage!r}).reconcile({task!r}, "m1", "op_1")["DECISION"]
        (flags / "resolver_ready").write_text("1")
        t0 = time.time()
        out = ResolverService({storage!r}).apply(
            {task!r}, "m1", "op_1", "ABORT",
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=OperationStore({storage!r}).get({task!r}, "op_1").revision,
        )
        print(json.dumps({{"accepted": out["accepted"], "waited": time.time() - t0}}))
    """

    def test_fb_race_verification_holds_the_lock_then_late_abort_is_absorbed(self):
        self.activate("m1", "a.txt")
        self.done_op("m1", "a.txt", "op_1")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        verifier = self.run_child(self.VERIFY_CHILD.format(flags=str(self.flags), storage=str(self.storage), task=TASK))
        self.wait_flag("admission_locked", verifier)
        resolver = self.run_child(self.RESOLVE_CHILD.format(flags=str(self.flags), storage=str(self.storage), task=TASK))
        self.wait_flag("resolver_ready", resolver)
        time.sleep(0.5)
        self.assertIsNone(resolver.poll())  # the ABORT acceptance waits for the TASK lock
        (self.flags / "admission_go").write_text("1")
        v_out, v_err = verifier.communicate(timeout=120)
        r_out, r_err = resolver.communicate(timeout=120)
        self.assertEqual((verifier.returncode, resolver.returncode), (0, 0), v_err + r_err)

        self.assertEqual(json.loads(v_out.strip().splitlines()[-1]), "APPLIED")
        self.assertTrue(json.loads(r_out.strip().splitlines()[-1])["accepted"])
        result = self.recover()
        again = self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual(self.settlements("op_1"), {"op_1": "ABORT"})
        self.assertEqual(result["recovery_state"], "NORMAL")
        self.assertEqual(again["performed_steps"], [])

    def test_fb_race_abort_accepted_first_then_verification_is_refused(self):
        self.activate("m1", "a.txt")
        self.done_op("m1", "a.txt", "op_1")
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        child = self.run_child(f"""
            import json, pathlib, time
            from web_alarm.state_machine import ServerStateMachine, TransitionRejected
            flags = pathlib.Path({str(self.flags)!r})
            real = ServerStateMachine._admit_verified
            def decided(self, *a, **k):
                (flags / "decided").write_text("1")   # observed DONE, locks not taken yet
                while not (flags / "go").exists():
                    time.sleep(0.01)
                return real(self, *a, **k)
            ServerStateMachine._admit_verified = decided
            try:
                ServerStateMachine({str(self.storage)!r}).transition({TASK!r}, "m1", "VERIFIED", verification_evidence="ok")
                print(json.dumps("APPLIED"))
            except TransitionRejected as exc:
                print(json.dumps("REJECTED: " + exc.reason))
        """)
        self.wait_flag("decided", child)
        self.resolve("ABORT", "op_1")
        (self.flags / "go").write_text("1")
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)

        verdict = json.loads(out.strip().splitlines()[-1])
        self.assertTrue(verdict.startswith("REJECTED"), verdict)
        self.assertIn("RECOVERY_OPEN", verdict)
        result = self.recover()
        self.assertEqual((result["state"], self.micro("m1")), (MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED))

    def test_fb_terminal_abort_of_a_failed_operation_settles_instead_of_failing_closed(self):
        # C1 (found during Repair #3): an accepted ABORT of a FAILED operation was
        # an endless FAIL_CLOSED (the settlement primitive refused FAILED)
        self.activate("m1", "a.txt")
        self.intent("m1", "a.txt", "op_f", claim=False)
        self.ops.transition(TASK, "op_f", OperationStatus.FAILED)
        self.resolve("ABORT", "op_f")

        first = self.recover()
        second = self.recover()

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(first["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.ops.get(TASK, "op_f").status, OperationStatus.FAILED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(second["performed_steps"], [])

    def adopted_m1(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_1", landed=True)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ADOPT", "op_1")
        first = self.recover()
        self.assertEqual([s["action"] for s in first["performed_steps"]], ["SETTLE_ADOPT"])
        self.assertEqual(self.micro("m1"), MicrotaskStatus.DONE)

    def test_fb_late_abort_after_an_adopt_settlement_reaches_the_manual_boundary(self):
        # reverify probe n03: this was an endless FAIL_CLOSED (a second settlement is refused)
        self.adopted_m1()
        self.resolve("ABORT", "op_1")

        first = self.recover()
        second = self.recover()

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["FINISH_SETTLEMENT"])
        self.assertEqual(first["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)
        op = self.ops.get(TASK, "op_1")
        self.assertEqual((op.status, op.recovery_settlement["action"]), (OperationStatus.VERIFIED, "ADOPT"))
        self.assertEqual((second["state"], second["performed_steps"]), (MANUAL_DECISION_REQUIRED, []))
        self.assert_denied_gate("m1")

    def assert_denied_gate(self, mid):
        self.assertIsNotNone(self.gate(mid))

    def test_fb_late_abort_after_adopt_on_a_verified_stage_is_absorbed(self):
        self.adopted_m1()
        self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="adopted")
        self.resolve("ABORT", "op_1")

        result = self.recover()

        self.assertEqual(result["performed_steps"], [])
        self.assertEqual(result["recovery_state"], "NORMAL")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)

    def test_fb_abort_after_a_superseded_rollback_settlement_closes_the_retry(self):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        (self.project / "b.txt").unlink()
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ROLLBACK", "op_1")
        self.assertEqual(self.recover()["state"], MANUAL_DECISION_REQUIRED)  # verified rollback settled
        self.resolve("RETRY", "op_1")
        rearmed = self.recover()
        self.assertEqual((rearmed["state"], self.micro("m1")), (READY_FOR_EXECUTION, MicrotaskStatus.ACTIVE))
        self.resolve("ABORT", "op_1")  # the explicit decision not to re-execute after all

        first = self.recover()
        second = self.recover()

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["FINISH_SETTLEMENT"])
        self.assertEqual((first["state"], self.micro("m1")), (MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED))
        self.assertEqual(self.ops.get(TASK, "op_1").recovery_settlement["action"], "ROLLBACK")
        self.assertEqual(second["performed_steps"], [])

    def test_fb_pure_rules(self):
        self.assertIs(effective_settlement_target(["ABORT"], "VERIFIED"), MicrotaskStatus.VERIFIED)
        self.assertIs(effective_settlement_target(["ADOPT"], "VERIFIED"), MicrotaskStatus.VERIFIED)
        self.assertIs(effective_settlement_target(["ABORT", "ROLLBACK"], "VERIFIED"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertIs(effective_settlement_target(["ABORT"], "DONE"), MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertIs(effective_settlement_target(["ADOPT"], "DONE"), MicrotaskStatus.DONE)
        self.assertIsNone(effective_settlement_target([], "VERIFIED"))
        broken = {"blockers": [{"code": "OPERATIONS_UNREADABLE", "reason": "io"}], "diagnostics": [], "operations": []}
        self.assertEqual(verification_refusal(broken, "m1")[0], "RECOVERY_FACTS_UNAVAILABLE")


class ReadyProofBasisTests(Repair3Fixture):
    """R3: READY only for exactly the restore point + target set + lifecycle basis that was locked."""

    def proof_calls(self, after_first):
        real = RecoveryCoordinator._prove_normal_ready
        calls = []

        def prove(coordinator, task_id, projection):
            out = real(coordinator, task_id, projection)
            calls.append(out)
            if len(calls) == 1:
                after_first()
            return out

        with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", prove):
            result = self.recover()
        return result, calls

    def test_r3_restore_point_content_change_behind_the_same_surface_ids(self):
        self.activate("m1", "a.txt")
        self.write("z.txt", b"other\n")
        rp = self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
        manifest_before = (rp / "manifest.json").read_bytes()

        def retarget():
            # entry + snapshot metadata rewritten consistently: manifest.json (id,
            # updated_at) unchanged, pure verification still passes
            for sub in ("manifest_entries", "snapshots"):
                for path in (rp / sub).glob("*.json"):
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["source_path"] = "z.txt"
                    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result, calls = self.proof_calls(retarget)

        self.assertEqual((rp / "manifest.json").read_bytes(), manifest_before)
        self.assertEqual(len(calls), 2)  # the first proof was not reused
        self.assertNotEqual(calls[0]["restore_point_fingerprint"], calls[1]["restore_point_fingerprint"])
        self.assertNotEqual(calls[0]["target_set_fingerprint"], calls[1]["target_set_fingerprint"])
        now = ManifestSnapshotStore(self.storage).restore_plan(TASK, "m1")["restore_point_fingerprint"]
        if result["state"] == READY_FOR_EXECUTION:
            self.assertEqual(result["ready_proof"]["restore_point_fingerprint"], now)
            self.assertEqual(result["ready_proof"], dict(calls[1], source_fingerprint=result["ready_proof"]["source_fingerprint"]))

    def test_r3_aba_back_to_the_same_status_needs_a_new_proof(self):
        self.activate("m1", "a.txt")

        def aba():
            store = TaskStore(self.storage)
            store.set_microtask_status(TASK, "m1", MicrotaskStatus.DONE)
            store.set_microtask_status(TASK, "m1", MicrotaskStatus.ACTIVE)  # same surface status

        result, calls = self.proof_calls(aba)

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0]["microtask_updated_at"], calls[1]["microtask_updated_at"])
        self.assertEqual(result["ready_proof"]["microtask_updated_at"], self.tasks.open_microtask(TASK, "m1").updated_at)

    def test_r3_foreign_ownership_after_the_proof_is_never_ready(self):
        self.activate("m1", "a.txt")
        result, calls = self.proof_calls(lambda: self.foreign_claim("a.txt", "op_f"))

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertIsNone(result["ready_proof"])
        self.assertIn("already owned", result["reason"])

    def test_r3_proof_matches_compares_every_projection_field(self):
        self.activate("m1", "a.txt")
        ready = self.recover()
        proof, projection = ready["ready_proof"], ready["projection"]
        self.assertTrue(RecoveryCoordinator._proof_matches(proof, projection))
        for field, value in (
            ("microtask_id", "m2"),
            ("microtask_status", "DONE"),
            ("microtask_updated_at", "1999-01-01T00:00:00+00:00"),
            ("manifest_id", "manifest_other"),
        ):
            with self.subTest(field=field):
                self.assertFalse(RecoveryCoordinator._proof_matches(dict(proof, **{field: value}), projection))

    def test_r3_retry_ready_proof_is_bound_to_operation_and_resolution(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_1", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("RETRY", "op_1")
        ready = self.recover()
        proof, projection = ready["ready_proof"], ready["projection"]
        self.assertEqual(ready["state"], READY_FOR_EXECUTION)
        self.assertTrue(RecoveryCoordinator._proof_matches(proof, projection))
        for field, value in (("operation_revision", proof["operation_revision"] + 1), ("resolution_id", "res_x")):
            with self.subTest(field=field):
                self.assertFalse(RecoveryCoordinator._proof_matches(dict(proof, **{field: value}), projection))


ACTIVATION_CRASH = """
    import os, sys
    from web_alarm.task_store import TaskStore
    from web_alarm.state_machine import ServerStateMachine
    real = TaskStore._write_plan
    def plan_then_die(self, task_dir, plan):
        real(self, task_dir, plan)
        if plan.current_microtask_id == {mid!r}:
            os._exit(17)  # process crash between the plan pointer and the status write
    TaskStore._write_plan = plan_then_die
    ServerStateMachine({storage!r}).transition({task!r}, {mid!r}, "ACTIVE")
"""

BLOCK_CRASH = """
    import os
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    real = ManifestSnapshotStore._write_blocked_manifest
    def manifest_then_die(self, *args, **kwargs):
        real(self, *args, **kwargs)
        os._exit(19)  # process crash between the manifest and the microtask block
    ManifestSnapshotStore._write_blocked_manifest = manifest_then_die
    ServerStateMachine({storage!r}).transition({task!r}, "m1", "ACTIVE")
"""


class CrashConsistencyTests(Repair3Fixture):
    """F4 activation, F5 restore-point blocking: every crash state is recognizable and recoverable."""

    def ready_m1(self):
        self.write("a.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        self.machine.transition(TASK, "m1", MicrotaskStatus.READY)

    def test_f4_crash_between_pointer_and_status_is_a_recoverable_state(self):
        self.ready_m1()
        child = self.run_child(ACTIVATION_CRASH.format(storage=str(self.storage), task=TASK, mid="m1"))
        child.communicate(timeout=120)
        self.assertEqual(child.returncode, 17)

        projection = ProjectionService(self.storage).build(TASK)
        self.assertEqual(self.tasks.open_plan(TASK).current_microtask_id, "m1")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.READY)
        self.assertEqual(projection["position"]["plan_pointer_state"], "CORROBORATED")
        self.assertEqual(projection["blockers"], [])
        self.assertIn("ACTIVE", projection["next_safe_action"])
        self.assertNotEqual(self.recover()["state"], READY_FOR_EXECUTION)  # nothing executes from READY

        self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)  # the restart repeats the activation

        self.assertEqual(self.micro("m1"), MicrotaskStatus.ACTIVE)
        self.assertEqual(self.recover()["state"], READY_FOR_EXECUTION)

    def test_f4_activation_rechecks_earlier_microtasks_under_the_lock(self):
        self.activate("m1", "a.txt")
        self.verify("m1")
        self.write("b.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m2", [("b.txt", "edit")])
        self.machine.transition(TASK, "m2", MicrotaskStatus.READY)
        real = TaskStore.compare_and_set_microtask_status

        def reorder_meanwhile(store, task_id, microtask_id, **kwargs):
            # a concurrent replan puts the unprepared m3 before m2 after the state
            # machine's unlocked "previous VERIFIED" check
            TaskStore(self.storage).set_plan(TASK, ["m1", "m3", "m2"])
            return real(store, task_id, microtask_id, **kwargs)

        with mock.patch.object(TaskStore, "compare_and_set_microtask_status", reorder_meanwhile):
            with self.assertRaises(TransitionRejected) as refused:
                self.machine.transition(TASK, "m2", MicrotaskStatus.ACTIVE)

        self.assertIn("previous microtask m3 is PLANNED", refused.exception.reason)
        self.assertEqual(self.micro("m2"), MicrotaskStatus.READY)
        self.assertNotEqual(self.tasks.open_plan(TASK).current_microtask_id, "m2")

    def test_f5_stale_failing_verification_never_blocks_an_advanced_restore_point(self):
        self.ready_m1()
        real = ManifestSnapshotStore._load_paired_records
        fired = []

        def winner_then_transient_failure(store, task_id, microtask_id, *, active_only=False):
            if active_only and not fired:
                fired.append(1)
                for status in (MicrotaskStatus.ACTIVE, MicrotaskStatus.DONE, MicrotaskStatus.VERIFIED):
                    TaskStore(self.storage).set_microtask_status(task_id, microtask_id, status)
                raise ManifestStoreError("transient: cannot read JSON record")
            return real(store, task_id, microtask_id, active_only=active_only)

        with mock.patch.object(ManifestSnapshotStore, "_load_paired_records", winner_then_transient_failure):
            with self.assertRaises(TransitionRejected):
                self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)

        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").status.value, "VERIFIED")

    def test_f5_current_verification_failure_still_blocks_both(self):
        self.ready_m1()
        snap = next((self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"))
        snap.write_bytes(b"tampered")

        with self.assertRaises(TransitionRejected):
            self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)

        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)
        self.assertEqual(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").status.value, "BLOCKED_PREPARE")

    def test_f5_crash_between_manifest_and_status_block_is_recoverable(self):
        self.ready_m1()
        snap = next((self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"))
        snap.write_bytes(b"tampered")
        child = self.run_child(BLOCK_CRASH.format(storage=str(self.storage), task=TASK))
        child.communicate(timeout=120)
        self.assertEqual(child.returncode, 19)

        self.assertEqual(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").status.value, "BLOCKED_PREPARE")
        self.assertEqual(self.micro("m1"), MicrotaskStatus.READY)
        projection = ProjectionService(self.storage).build(TASK)
        self.assertEqual(projection["restore_point"]["status"], "NOT_VERIFIED")
        self.assertIn("BLOCKED_PREPARE", projection["restore_point"]["reason"])

        with self.assertRaises(TransitionRejected):  # the next attempt completes the block
            self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)

    def test_f5_crash_window_never_opens_mutation(self):
        self.ready_m1()
        snap = next((self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"))
        snap.write_bytes(b"tampered")
        self.run_child(BLOCK_CRASH.format(storage=str(self.storage), task=TASK)).communicate(timeout=120)
        self.intent("m1", "a.txt", "op_1")
        self.assert_denied(self.authorize("op_1"), "MICROTASK_NOT_ACTIVE")


class LockOrderTests(Repair3Fixture):
    """The boundary's TASK -> mutation -> target order composes with RC-6 and RC-4."""

    def test_boundary_and_foreign_rc6_proof_on_a_shared_target_do_not_deadlock(self):
        self.activate("m1", "a.txt")
        self.machine.prepare_microtask(OTHER, "f1", [("a.txt", "edit")])
        self.machine.transition(OTHER, "f1", MicrotaskStatus.READY)
        self.machine.transition(OTHER, "f1", MicrotaskStatus.ACTIVE)
        self.intent("f1", "a.txt", "op_f", task=OTHER)
        child = self.run_child(f"""
            import json, time
            from web_alarm.recovery_coordinator import RecoveryCoordinator
            t0 = time.time()
            r = RecoveryCoordinator({str(self.storage)!r}, lock_timeout=6).recover({TASK!r})
            print(json.dumps({{"state": r["state"], "reason": r["reason"], "elapsed": time.time() - t0}}))
        """)
        with self.claims().mutation_boundary(OTHER, "op_f", operation_revision=self.rev("op_f", OTHER)) as boundary:
            self.assertTrue(boundary["mutation_authority"])
            time.sleep(1.0)
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)
        result = json.loads(out.strip().splitlines()[-1])
        self.assertNotIn("timeout", result["reason"])
        self.assertEqual(result["state"], RECOVERY_BLOCKED)  # op_f owns a.txt
        self.assertLess(result["elapsed"], 6)


if __name__ == "__main__":
    unittest.main()
