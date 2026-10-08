"""RC-6 Repair #4 regressions: restart-safe recovery of an interrupted restore-point
preparation (Blocker A) and one settlement-supersession policy shared by the
Resolver, Projection and the coordinator (Blocker B)."""

import json
import time
import unittest
from unittest import mock

from test_web_alarm_recovery_coordinator_repair2 import (
    AFTER,
    BEFORE,
    TASK,
    Repair2Fixture,
)

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore, ManifestStoreError
from web_alarm.microtask_gate import execution_refusal
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.projection import ProjectionService
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import (
    MANUAL_DECISION_REQUIRED,
    NO_ACTION_REQUIRED,
    READY_FOR_EXECUTION,
    READY_FOR_VERIFICATION,
    RECOVERY_IN_PROGRESS,
    RecoveryCoordinator,
)
from web_alarm.resolution_store import ResolutionRecord, ResolutionResult, ResolutionStore
from web_alarm.resolver_service import SETTLEMENT_ADMITS, ResolverService, settlement_admits
from web_alarm.rollback_service import RollbackService
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore, TaskStoreError

PREPARE_CRASH = """
    import os, pathlib, time
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    window = {window!r}
    if window == "W1":
        real = ManifestSnapshotStore._resolve_target
        def die(self, *a, **k):
            os._exit(23)  # PREPARING written, capture in its stage directory
        ManifestSnapshotStore._resolve_target = die
    elif window == "W2":
        real = TaskStore.compare_and_set_microtask_status
        def die(self, task_id, microtask_id, *, expected, status, activate=False):
            if getattr(status, "value", status) == "BACKUP_VERIFIED":
                os._exit(29)  # the restore point is published, its status is not
            return real(self, task_id, microtask_id, expected=expected, status=status, activate=activate)
        TaskStore.compare_and_set_microtask_status = die
    elif window == "HOLD":
        flags = pathlib.Path({flags!r})
        real = ManifestSnapshotStore._resolve_target
        def hold(self, *a, **k):
            (flags / "capturing").write_text("1")  # a live preparation, lock held
            while not (flags / "release").exists():
                time.sleep(0.01)
            return real(self, *a, **k)
        ManifestSnapshotStore._resolve_target = hold
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", [("a.txt", "edit")])
    print("PREPARED")
"""

RECONCILE_CRASH = """
    import os
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    from web_alarm.task_store import TaskStore
    real = TaskStore.compare_and_set_microtask_status
    def die(self, task_id, microtask_id, *, expected, status, activate=False):
        os._exit(31)  # the reconcile decided, its status write is lost
    TaskStore.compare_and_set_microtask_status = die
    RecoveryCoordinator({storage!r}).recover({task!r})
"""

FRESH_RECOVER = """
    import json
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    r = RecoveryCoordinator({storage!r}).recover({task!r})
    print(json.dumps([r["state"], [s["action"] for s in r["performed_steps"]],
                      [s["outcome"].get("result") for s in r["performed_steps"]]]))
"""


class Repair4Fixture(Repair2Fixture):
    def crash_prepare(self, window, *, expect_exit):
        self.write("a.txt", BEFORE)
        child = self.run_child(PREPARE_CRASH.format(
            window=window, storage=str(self.storage), task=TASK, flags=str(self.flags)))
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, expect_exit, err)

    def work(self):
        return self.tasks.microtask_directory(TASK, "m1")

    def evidence(self):
        work = self.work()
        return (
            self.micro("m1"),
            (work / "restore_point" / "manifest.json").is_file(),
            len([p for p in work.glob(".restore.*") if p.is_dir()]),
        )

    def fresh_recover(self):
        child = self.run_child(FRESH_RECOVER.format(storage=str(self.storage), task=TASK))
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)
        return json.loads(out.strip().splitlines()[-1])

    def reconciled_events(self):
        return [e.payload for e in EventCheckpointStore(self.storage).read_events(TASK)
                if e.event_type == "RESTORE_POINT_PREPARATION_RECONCILED"]

    def gate(self, mid="m1"):
        c = RecoveryCoordinator(self.storage)
        return execution_refusal(TASK, mid, tasks=c.tasks, operations=c.operations,
                                 resolver=c.resolver, rollbacks=c.rollbacks.store)

    def resolve_any(self, action, op="op_1", mid="m1"):
        decision = ReconciliationService(self.storage).reconcile(TASK, mid, op)["DECISION"]
        return ResolverService(self.storage).apply(
            TASK, mid, op, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, op).revision,
            agent="repair4", channel="test",
        )["resolution"]


class InterruptedPreparationTests(Repair4Fixture):
    """Blocker A: a crash while PREPARING always has a deterministic, safe way out."""

    def test_w1_crash_fresh_process_reaches_blocked_prepare_then_prepares_again(self):
        self.crash_prepare("W1", expect_exit=23)
        self.assertEqual(self.evidence(), (MicrotaskStatus.PREPARING, False, 1))
        self.assertIn("Run recover", ProjectionService(self.storage).build(TASK)["next_safe_action"])

        state, steps, results = self.fresh_recover()

        self.assertEqual((state, steps, results), (NO_ACTION_REQUIRED, ["RECONCILE_PREPARATION"], ["PREPARATION_DISCARDED"]))
        self.assertEqual(self.evidence(), (MicrotaskStatus.BLOCKED_PREPARE, False, 0))
        event = self.reconciled_events()[-1]
        self.assertEqual((event["result"], event["evidence"]), ("PREPARATION_DISCARDED", "NO_PUBLISHED_RESTORE_POINT"))
        self.assertIn("prepare the restore point again", ProjectionService(self.storage).build(TASK)["next_safe_action"])
        self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])  # NEXT is executable
        self.machine.transition(TASK, "m1", MicrotaskStatus.READY)
        self.machine.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
        self.assertEqual(self.recover()["state"], READY_FOR_EXECUTION)

    def test_w2_crash_published_restore_point_is_reverified_and_completed_without_recapture(self):
        self.crash_prepare("W2", expect_exit=29)
        self.assertEqual(self.evidence(), (MicrotaskStatus.PREPARING, True, 0))
        manifest_id = ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").manifest_id
        self.write("a.txt", b"edited after the crash\n")  # the captured pre-state must survive

        state, steps, results = self.fresh_recover()

        self.assertEqual((steps, results), (["RECONCILE_PREPARATION"], ["PREPARATION_COMPLETED"]))
        self.assertEqual(state, NO_ACTION_REQUIRED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)
        plan = ManifestSnapshotStore(self.storage).restore_plan(TASK, "m1")
        self.assertEqual(plan["manifest_id"], manifest_id)
        self.assertEqual(plan["items"][0]["snapshot_bytes"], BEFORE)
        self.assertEqual(self.reconciled_events()[-1]["evidence"], "PUBLISHED_RESTORE_POINT")

    def test_reconcile_is_idempotent(self):
        self.crash_prepare("W2", expect_exit=29)
        first = self.recover()
        before = self.digest()
        second = self.recover()
        direct = ManifestSnapshotStore(self.storage).reconcile_interrupted_preparation(TASK, "m1")

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["RECONCILE_PREPARATION"])
        self.assertEqual(second["performed_steps"], [])
        self.assertEqual(direct["result"], "NOT_INTERRUPTED")
        self.assertEqual(self.digest(), before)

    def test_corrupt_published_restore_point_fails_closed_and_next_is_manual(self):
        self.crash_prepare("W2", expect_exit=29)
        next(self.work().glob("restore_point/snapshots/*.bin")).write_bytes(b"tampered")

        result = self.recover()

        self.assertEqual([s["outcome"]["result"] for s in result["performed_steps"]], ["PREPARATION_BLOCKED"])
        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)
        self.assertEqual(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").status.value, "BLOCKED_PREPARE")
        self.assertIn("manual review and repair", result["next_safe_action"])
        with self.assertRaises(ManifestStoreError):  # the evidence is never overwritten
            self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])

    def test_unreadable_published_manifest_fails_closed(self):
        self.crash_prepare("W2", expect_exit=29)
        (self.work() / "restore_point" / "manifest.json").write_text("{not json", encoding="utf-8")

        result = self.recover()

        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)
        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)

    def test_no_mutation_authority_while_preparing_and_after_reconcile(self):
        self.crash_prepare("W1", expect_exit=23)
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_x", payload=AFTER)
        claims = TargetClaimService(self.storage)
        claims.acquire(TASK, "op_x", operation_revision=1)
        self.assertEqual(claims.authorize(TASK, "op_x", operation_revision=1)["result_code"], "MICROTASK_NOT_ACTIVE")
        self.recover()
        self.assertEqual(claims.authorize(TASK, "op_x", operation_revision=1)["result_code"], "MICROTASK_NOT_ACTIVE")
        self.assertEqual(self.read("a.txt"), BEFORE)

    def test_a_running_preparation_is_never_touched(self):
        self.write("a.txt", BEFORE)
        child = self.run_child(PREPARE_CRASH.format(
            window="HOLD", storage=str(self.storage), task=TASK, flags=str(self.flags)))
        try:
            self.wait_flag("capturing", child)
            stages_before = self.evidence()

            result = self.recover()

            self.assertEqual(result["state"], RECOVERY_IN_PROGRESS)
            self.assertFalse(result["requires_human"])
            self.assertEqual(self.evidence(), stages_before)  # PREPARING, its stage intact
        finally:
            (self.flags / "release").write_text("1")  # never leave the live preparer waiting
            try:
                out, err = child.communicate(timeout=120)
            except Exception:
                child.kill()
                raise
        self.assertEqual(child.returncode, 0, err)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)
        self.assertEqual(self.recover()["performed_steps"], [])

    def test_crash_inside_the_reconcile_restarts_cleanly(self):
        self.crash_prepare("W1", expect_exit=23)
        child = self.run_child(RECONCILE_CRASH.format(storage=str(self.storage), task=TASK))
        child.communicate(timeout=120)
        self.assertEqual(child.returncode, 31)
        self.assertEqual(self.evidence(), (MicrotaskStatus.PREPARING, False, 0))  # stage gone, status not written

        state, steps, results = self.fresh_recover()

        self.assertEqual(results, ["PREPARATION_DISCARDED"])
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BLOCKED_PREPARE)

    def test_status_write_failure_after_publication_leaves_w2_not_a_blocked_dead_end(self):
        self.write("a.txt", BEFORE)
        real = TaskStore.compare_and_set_microtask_status

        def lose_backup_verified(store, task_id, microtask_id, *, expected, status, activate=False):
            if MicrotaskStatus(status) is MicrotaskStatus.BACKUP_VERIFIED:
                raise TaskStoreError("cannot persist JSON record (I/O)")
            return real(store, task_id, microtask_id, expected=expected, status=status, activate=activate)

        with mock.patch.object(TaskStore, "compare_and_set_microtask_status", lose_backup_verified):
            with self.assertRaises(ManifestStoreError):
                self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])

        self.assertEqual(self.evidence(), (MicrotaskStatus.PREPARING, True, 0))
        self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)

    def test_two_concurrent_recovers_reconcile_exactly_once(self):
        self.crash_prepare("W2", expect_exit=29)
        children = [self.run_child(FRESH_RECOVER.format(storage=str(self.storage), task=TASK)) for _ in range(2)]
        outs = []
        for child in children:
            out, err = child.communicate(timeout=120)
            self.assertEqual(child.returncode, 0, err)
            outs.append(json.loads(out.strip().splitlines()[-1]))

        results = sorted(r for _, _, rs in outs for r in rs)
        self.assertEqual(results.count("PREPARATION_COMPLETED"), 1)
        self.assertEqual(len(self.reconciled_events()), 1)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)

    def test_leftover_stage_of_an_attempt_that_died_before_preparing_is_discarded(self):
        self.write("a.txt", BEFORE)
        leftover = self.work() / ".restore.stage_dead"
        (leftover / "snapshots").mkdir(parents=True)

        self.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit")])

        self.assertFalse(leftover.exists())
        self.assertEqual(self.micro("m1"), MicrotaskStatus.BACKUP_VERIFIED)


class SettlementSupersessionPolicyTests(Repair4Fixture):
    """Blocker B: the Resolver never accepts what RC-6 cannot carry out over a settlement."""

    def settle(self, first):
        if first == "ROLLBACK":
            for name, data in (("a.txt", BEFORE), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
                self.write(name, data)
            self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        else:
            self.activate("m1", "a.txt")
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        TargetClaimService(self.storage).acquire(TASK, "op_1", operation_revision=1)
        self.ops.transition(TASK, "op_1", OperationStatus.STARTED)
        if first in ("ADOPT", "ROLLBACK"):
            self.write("a.txt", AFTER)
        if first == "ROLLBACK":
            (self.project / "b.txt").unlink()
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve(first, "op_1")
        self.recover()
        self.assertEqual(self.settlements("op_1"), {"op_1": first})

    def restored(self):
        return sum(1 for s in RollbackService(self.storage).store.list(TASK) for t in s["targets"]
                   if t["status"] == "RESTORED")

    def later(self, first, later):
        """the file state that makes the later action's reconciliation decision reachable"""
        if first == "ROLLBACK" and later == "ADOPT":
            self.write("a.txt", AFTER)
            (self.project / "b.txt").unlink()
            (self.project / "c.txt").unlink()
        elif first == "ROLLBACK" and later == "ROLLBACK":
            self.write("a.txt", AFTER)
            (self.project / "b.txt").unlink()
        elif later == "ADOPT":
            self.write("a.txt", AFTER)
        return self.resolve_any(later)

    MATRIX = {
        ("ADOPT", "ADOPT"): "RECOVERY_ALREADY_SETTLED",
        ("ADOPT", "ROLLBACK"): "RECOVERY_ALREADY_SETTLED",
        ("ADOPT", "RETRY"): "RECOVERY_ALREADY_SETTLED",
        ("ABORT", "ADOPT"): "RECOVERY_ABORTED",
        ("ABORT", "ROLLBACK"): "RECOVERY_ABORTED",
        ("ABORT", "RETRY"): "RECOVERY_ABORTED",
        ("ROLLBACK", "ADOPT"): "RECOVERY_ALREADY_SETTLED",
        ("ROLLBACK", "ROLLBACK"): "RECOVERY_ALREADY_SETTLED",
    }

    def test_refused_combinations_never_become_authority_or_attention(self):
        # every combination gets its own fresh storage (setUp/tearDown per subTest)
        for (first, later), code in self.MATRIX.items():
            with self.subTest(first=first, later=later):
                self.setUp()
                try:
                    self.settle(first)
                    micro_before, restored_before = self.micro("m1"), self.restored()
                    record = self.later(first, later)
                    first_run, second_run = self.recover(), self.recover()

                    self.assertEqual((record.result, record.result_code), (ResolutionResult.REJECTED, code))
                    self.assertNotIn("FAIL_CLOSED", (first_run["state"], second_run["state"]))
                    self.assertEqual(second_run["recovery_state"], "NORMAL")  # history, not attention
                    self.assertEqual(second_run["performed_steps"], [])
                    self.assertEqual(self.settlements("op_1"), {"op_1": first})  # immutable
                    self.assertEqual(self.micro("m1"), micro_before)
                    self.assertEqual(self.restored(), restored_before)  # no second physical effect
                finally:
                    self.tearDown()

    def test_admitted_combinations_are_carried_out(self):
        cases = {
            ("ADOPT", "ABORT"): (MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED),  # Repair #3 late ABORT
            ("ROLLBACK", "ABORT"): (MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED),
            ("ROLLBACK", "RETRY"): (READY_FOR_EXECUTION, MicrotaskStatus.ACTIVE),  # re-arm after rollback
        }
        for (first, later), (state, micro) in cases.items():
            with self.subTest(first=first, later=later):
                self.setUp()
                try:
                    self.settle(first)
                    restored_before = self.restored()
                    record = self.later(first, later)
                    result, again = self.recover(), self.recover()

                    self.assertEqual(record.result, ResolutionResult.ACCEPTED)
                    self.assertEqual((result["state"], self.micro("m1")), (state, micro))
                    self.assertEqual(again["state"], state)
                    self.assertEqual(self.settlements("op_1"), {"op_1": first})
                    self.assertEqual(self.restored(), restored_before)
                finally:
                    self.tearDown()

    def test_rejected_decision_after_a_settlement_is_history_not_attention(self):
        # on 163 this ADOPT-settled op showed ROLLBACK_REJECTED -> MANUAL forever
        self.settle("ADOPT")
        record = self.resolve_any("ROLLBACK")
        result = self.recover()
        self.assertEqual(record.result, ResolutionResult.REJECTED)
        self.assertEqual((result["state"], result["recovery_state"]), (READY_FOR_VERIFICATION, "NORMAL"))

    def test_legacy_accepted_action_over_a_settlement_is_not_authority(self):
        # an ACCEPTED ADOPT written before Repair #4 over an ADOPT settlement
        self.settle("ADOPT")
        store = ResolutionStore(self.storage)
        settled = store.get(TASK, self.ops.get(TASK, "op_1").recovery_settlement["resolution_id"])
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["DECISION"]
        legacy = ResolutionRecord(
            resolution_id="res_legacy_adopt", task_id=TASK, microtask_id="m1", operation_id="op_1",
            action=settled.action, requested_basis=dict(settled.requested_basis,
                                                        evidence_fingerprint=decision["evidence_fingerprint"],
                                                        operation_revision=self.ops.get(TASK, "op_1").revision),
            basis=dict(settled.basis, evidence_fingerprint=decision["evidence_fingerprint"],
                       operation_revision=self.ops.get(TASK, "op_1").revision),
            result=ResolutionResult.ACCEPTED, result_code="BASIS_FRESH_ACTION_ALLOWED",
            result_reason="legacy", effect=settled.effect, next_safe_action="legacy",
            provenance=settled.provenance, payload_verified=None,
        )
        store.write_new(legacy)
        facts = ResolverService(self.storage).report_facts(TASK, "m1", "op_1")
        entry = next(a for a in facts["resolver_actions"] if a["resolution_id"] == "res_legacy_adopt")

        result = self.recover()

        self.assertTrue(entry["fresh"])
        self.assertFalse(entry["authority"])
        self.assertEqual(facts["next_safe_action"]["resolution_id"], settled.resolution_id)
        self.assertEqual((result["state"], result["recovery_state"]), (READY_FOR_VERIFICATION, "NORMAL"))

    def test_rc4_refuses_a_second_rollback_from_a_legacy_record_over_a_settlement(self):
        self.settle("ROLLBACK")
        restored_before = self.restored()
        self.write("a.txt", AFTER)
        (self.project / "b.txt").unlink()
        store = ResolutionStore(self.storage)
        settled = store.get(TASK, self.ops.get(TASK, "op_1").recovery_settlement["resolution_id"])
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["DECISION"]
        revision = self.ops.get(TASK, "op_1").revision
        store.write_new(ResolutionRecord(  # accepted before Repair #4 existed
            resolution_id="res_legacy_rollback", task_id=TASK, microtask_id="m1", operation_id="op_1",
            action=settled.action,
            requested_basis=dict(settled.requested_basis, evidence_fingerprint=decision["evidence_fingerprint"],
                                 operation_revision=revision),
            basis=dict(settled.basis, evidence_fingerprint=decision["evidence_fingerprint"],
                       operation_revision=revision, decision=decision["decision"]),
            result=ResolutionResult.ACCEPTED, result_code="BASIS_FRESH_ACTION_ALLOWED", result_reason="legacy",
            effect=settled.effect, next_safe_action="legacy", provenance=settled.provenance, payload_verified=None,
        ))

        outcome = RollbackService(self.storage).prepare(TASK, "m1", "op_1", "res_legacy_rollback", channel="test")
        runs = [self.recover(), self.recover()]

        self.assertEqual((outcome["result"], outcome["result_code"]), ("REJECTED", "RECOVERY_ALREADY_SETTLED"))
        self.assertNotIn("FAIL_CLOSED", [r["state"] for r in runs])
        self.assertEqual(self.restored(), restored_before)  # no second physical rollback
        self.assertEqual(self.read("a.txt"), AFTER)

    def test_verified_stage_never_moves_back(self):
        self.settle("ADOPT")
        self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="adopted")
        for later in ("ADOPT", "ROLLBACK", "RETRY"):
            self.assertEqual(self.later("ADOPT", later).result_code, "RECOVERY_ALREADY_SETTLED")
        self.assertEqual(self.recover()["performed_steps"], [])
        self.resolve_any("ABORT")  # Repair #3: absorbed by the verified stage
        self.recover()
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)

    def test_retry_after_rollback_stays_authority_over_a_later_refused_action(self):
        self.settle("ROLLBACK")
        self.assertEqual(self.later("ROLLBACK", "RETRY").result, ResolutionResult.ACCEPTED)
        self.assertEqual(self.recover()["state"], READY_FOR_EXECUTION)
        refused = self.resolve_any("ROLLBACK")

        result = self.recover()

        self.assertEqual(refused.result_code, "RECOVERY_ALREADY_SETTLED")
        self.assertEqual((result["state"], result["recovery_state"]), (READY_FOR_EXECUTION, "RETRY_ACCEPTED"))

    def test_policy_is_the_same_for_resolver_projection_coordinator_and_gate(self):
        self.settle("ADOPT")
        self.later("ADOPT", "ROLLBACK")
        facts = ResolverService(self.storage).report_facts(TASK, "m1", "op_1")
        projection = ProjectionService(self.storage).build(TASK)
        view = next(v for v in projection["operations"] if v["operation_id"] == "op_1")
        settlement = self.ops.get(TASK, "op_1").recovery_settlement

        self.assertEqual(facts["next_safe_action"]["resolution_id"], settlement["resolution_id"])
        self.assertIsNone(view["recovery"])
        self.assertEqual(view["microtask_disposition"], "DONE")
        self.assertEqual(self.gate()[0], "MICROTASK_NOT_ACTIVE")  # DONE: no mutation either way
        self.assertEqual(self.fresh_recover()[0], READY_FOR_VERIFICATION)

    def test_policy_table(self):
        self.assertEqual(SETTLEMENT_ADMITS["ADOPT"], frozenset({"ABORT"}))
        self.assertEqual(SETTLEMENT_ADMITS["ABORT"], frozenset())
        self.assertEqual(SETTLEMENT_ADMITS["ROLLBACK"], frozenset({"ABORT", "RETRY"}))
        self.assertFalse(settlement_admits("ROLLBACK", "ROLLBACK"))
        self.assertFalse(settlement_admits("UNKNOWN", "ABORT"))


if __name__ == "__main__":
    unittest.main()
