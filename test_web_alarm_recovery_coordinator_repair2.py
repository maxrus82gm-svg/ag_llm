"""RC-6 Repair #2 regressions: R1 verified-stage protection, R2 one settlement
disposition per microtask, R3 READY bound to its proof, F-D lock order, F-E
refused step not repeated."""

import hashlib
import json
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.rollback_service as rs

from web_alarm.closeout import CloseoutService
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import (
    MANUAL_DECISION_REQUIRED,
    READY_FOR_EXECUTION,
    READY_FOR_VERIFICATION,
    RECOVERY_BLOCKED,
    RecoveryCoordinator,
    RecoveryCoordinatorBlocked,
)
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.target_claim_store import (
    TargetClaimStore,
    physical_target_key,
    target_hash,
    target_lock_order,
)
from web_alarm.target_identity import canonical_target
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO = Path(__file__).resolve().parent
TASK = "task_repair2"
OTHER = "task_repair2_other"
BEFORE = b"before\n"
AFTER = b"after\n"


class Repair2Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage = root / "state"
        self.project = root / "project"
        self.flags = root / "flags"
        self.project.mkdir()
        self.flags.mkdir()
        WorkspaceRegistry(self.storage).register("Repair2", self.project, workspace_id="ws_repair2")
        self.tasks = TaskStore(self.storage)
        for task_id in (TASK, OTHER):
            self.tasks.create_task("ws_repair2", task_id, "RAW", "Repair2", task_id=task_id)
        for mid in ("m1", "m2", "m3"):
            self.tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
        self.tasks.create_microtask(OTHER, "F1", "foreign", microtask_id="f1")
        self.machine = ServerStateMachine(self.storage)
        self.ops = OperationStore(self.storage)

    def tearDown(self):
        self.tmp.cleanup()

    # --- helpers -------------------------------------------------------------------------------

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def read(self, name):
        path = self.project / name
        return path.read_bytes() if path.exists() else None

    def activate(self, mid, *targets, task=TASK, specs=None):
        for target in targets:
            if not (self.project / target).exists():
                self.write(target, BEFORE)
        self.machine.prepare_microtask(task, mid, specs or [(t, "edit") for t in targets])
        self.machine.transition(task, mid, MicrotaskStatus.READY)
        self.machine.transition(task, mid, MicrotaskStatus.ACTIVE)

    def verify(self, mid):
        self.machine.transition(TASK, mid, MicrotaskStatus.DONE)
        self.machine.transition(TASK, mid, MicrotaskStatus.VERIFIED, verification_evidence="ok")

    def start(self, mid, target, op, *, landed, payload=AFTER, task=TASK):
        self.ops.begin(task, mid, "write", target, operation_id=op, payload=payload)
        self.ops.transition(task, op, OperationStatus.STARTED)
        if landed:
            self.write(target, payload)

    def resolve(self, action, op, mid="m1", *, task=TASK):
        decision = ReconciliationService(self.storage).reconcile(task, mid, op)["DECISION"]
        out = ResolverService(self.storage).apply(
            task, mid, op, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(task, op).revision,
            agent="repair2", channel="test",
        )
        self.assertTrue(out["accepted"], out["resolution"].result_reason)
        return out["resolution"]

    def foreign_claim(self, target, op):
        self.ops.begin(OTHER, "f1", "write", target, operation_id=op, payload=b"foreign\n")
        out = TargetClaimService(self.storage).acquire(OTHER, op, operation_revision=1, channel="repair2")
        self.assertEqual(out["result"], "ACQUIRED")

    def recover(self, **kw):
        return RecoveryCoordinator(self.storage).recover(TASK, **kw)

    def micro(self, mid):
        return self.tasks.open_microtask(TASK, mid).status

    def events(self, event_type):
        return sum(1 for e in EventCheckpointStore(self.storage).read_events(TASK) if e.event_type == event_type)

    def digest(self):
        h = hashlib.sha256()
        for root in (self.storage, self.project):
            for path in sorted(root.rglob("*")):
                rel = path.relative_to(root).as_posix()
                if path.is_file() and not rel.startswith("locks/"):
                    h.update(rel.encode() + hashlib.sha256(path.read_bytes()).digest())
        return h.hexdigest()

    def active_claims(self):
        store = TargetClaimStore(self.storage)
        if not store.root.is_dir():
            return []
        result = []
        for path in sorted(store.root.glob("*.json")):
            active = json.loads(path.read_text(encoding="utf-8")).get("active")
            if active:
                result.append((active["task_id"], active["operation_id"]))
        return result

    def settlements(self, *ops):
        return {op: (self.ops.get(TASK, op).recovery_settlement or {}).get("action") for op in ops}

    def run_child(self, script):
        return subprocess.Popen(
            [sys.executable, "-B", "-c", textwrap.dedent(script)],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def wait_flag(self, name, proc, timeout=60):
        deadline = time.time() + timeout
        while not (self.flags / name).exists():
            if proc.poll() is not None:
                self.fail(f"child exited before {name}: {proc.communicate()}")
            if time.time() > deadline:
                self.fail(f"timeout waiting for {name}")
            time.sleep(0.01)


class VerifiedStageProtectionTests(Repair2Fixture):
    """R1: RC-6 never prepares/applies a destructive rollback of a VERIFIED stage."""

    def historical_rollback(self, *, later=("m2",)):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        (self.project / "b.txt").unlink()
        self.verify("m1")  # the state machine verifies m1 although op_1 was never settled
        for mid in later:
            target = f"{mid}.txt"
            self.activate(mid, target)
            if mid != later[-1]:
                self.verify(mid)
        self.write(f"{later[-1]}.txt", b"later stage work\n")
        resolution = self.resolve("ROLLBACK", "op_1")
        return resolution

    def assert_untouched(self, files, digest_before=None):
        self.assertEqual({n: self.read(n) for n in files}, {"a.txt": b"a-after\n", "b.txt": None})
        self.assertEqual(RollbackService(self.storage).store.list(TASK), [])
        self.assertEqual(self.events("ROLLBACK_TARGET_RESTORED"), 0)
        self.assertIsNone(self.ops.get(TASK, "op_1").recovery_settlement)
        self.assertEqual(self.micro("m1"), MicrotaskStatus.VERIFIED)
        self.assertEqual(self.active_claims(), [])
        if digest_before is not None:
            self.assertEqual(self.digest(), digest_before)

    def test_r1a_rollback_of_verified_stage_is_blocked_before_any_rc4_step(self):
        self.historical_rollback()
        before = self.digest()

        result = self.recover()

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(result["recovery_state"], "ROLLBACK_STAGE_PROTECTED")
        self.assertEqual(result["performed_steps"], [])
        self.assertFalse(result["ready_for_execution"])
        self.assertIn("protected history", result["next_safe_action"])
        self.assert_untouched(("a.txt", "b.txt"), before)

    def test_r1b_fresh_process_gives_the_same_blocked_result_and_is_idempotent(self):
        self.historical_rollback()
        before = self.digest()
        child = self.run_child(f"""
            import json
            from web_alarm.recovery_coordinator import RecoveryCoordinator
            r = RecoveryCoordinator({str(self.storage)!r}).recover({TASK!r})
            print(json.dumps([r["state"], r["recovery_state"], len(r["performed_steps"])]))
        """)
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)
        self.assertEqual(json.loads(out.strip().splitlines()[-1]), [RECOVERY_BLOCKED, "ROLLBACK_STAGE_PROTECTED", 0])
        second = self.recover()
        self.assertEqual(second["state"], RECOVERY_BLOCKED)
        self.assert_untouched(("a.txt", "b.txt"), before)

    def test_r1_open_preserved_session_of_a_later_verified_stage_is_not_applied(self):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        (self.project / "b.txt").unlink()
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        resolution = self.resolve("ROLLBACK", "op_1")
        record = RollbackService(self.storage).prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]
        self.assertEqual(record["status"], "PRESERVED")
        self.machine.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
        self.activate("m2", "m2.txt")

        result = self.recover()

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(result["recovery_state"], "ROLLBACK_STAGE_PROTECTED")
        self.assertEqual(self.read("a.txt"), b"a-after\n")
        self.assertIsNone(self.read("b.txt"))
        self.assertEqual(RollbackService(self.storage).inspect(TASK, record["rollback_id"])["status"], "PRESERVED")
        self.assertEqual(self.events("ROLLBACK_TARGET_RESTORED"), 0)

    def test_r1c_done_current_stage_rollback_keeps_the_existing_recovery_semantics(self):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        (self.project / "b.txt").unlink()
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)  # DONE, not VERIFIED, still current
        self.resolve("ROLLBACK", "op_1")

        result = self.recover()

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(
            [step["action"] for step in result["performed_steps"]],
            ["PREPARE_ROLLBACK", "APPLY_ROLLBACK", "SETTLE_ROLLBACK"],
        )
        self.assertEqual((self.read("a.txt"), self.read("b.txt")), (b"a-before\n", b"b-before\n"))
        self.assertEqual(self.micro("m1"), MicrotaskStatus.RECOVERY_REQUIRED)

    def test_r1d_several_later_stages_do_not_change_the_result(self):
        self.historical_rollback(later=("m2", "m3"))
        before = self.digest()

        result = self.recover()

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(result["projection"]["position"]["current_microtask_id"], "m3")
        self.assert_untouched(("a.txt", "b.txt"), before)

    def test_r1_coordinator_preflight_refuses_even_when_handed_a_destructive_step(self):
        self.historical_rollback()
        coordinator = RecoveryCoordinator(self.storage)
        projection = ProjectionService(self.storage).build(TASK)
        forged = dict(projection, recovery=dict(projection["recovery"], state="ROLLBACK_ACCEPTED"))

        with self.assertRaises(RecoveryCoordinatorBlocked):
            coordinator._perform(TASK, forged, "PREPARE_ROLLBACK")

        self.assertEqual(RollbackService(self.storage).store.list(TASK), [])
        self.assertEqual(self.read("a.txt"), b"a-after\n")


class MicrotaskDispositionTests(Repair2Fixture):
    """R2: settlements of one microtask are aggregated into one disposition."""

    def adopted_m1(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_a", landed=True)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ADOPT", "op_a")
        self.assertEqual(self.recover()["state"], READY_FOR_VERIFICATION)

    def aborted_m1(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_a", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ABORT", "op_a")
        self.assertEqual(self.recover()["state"], MANUAL_DECISION_REQUIRED)

    def assert_stable(self, state, micro_status):
        first = self.recover()
        self.assertEqual((first["state"], self.micro("m1")), (state, micro_status), first["reason"])
        self.assertNotIn("budget", first["reason"])
        before = self.digest()
        second = self.recover()
        self.assertEqual((second["state"], self.micro("m1")), (state, micro_status))
        self.assertEqual(second["performed_steps"], [])
        self.assertEqual(self.digest(), before)
        return first

    def test_r2a_completed_adopt_then_later_abort_converges_without_ping_pong(self):
        self.adopted_m1()
        self.start("m1", "a.txt", "op_b", landed=False, payload=b"after2\n")
        self.resolve("ABORT", "op_b")

        first = self.assert_stable(MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED)

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(self.settlements("op_a", "op_b"), {"op_a": "ADOPT", "op_b": "ABORT"})

    def test_r2b_abort_first_then_adopt_never_lifts_the_microtask_to_done(self):
        self.aborted_m1()
        self.start("m1", "a.txt", "op_b", landed=True, payload=b"after2\n")
        self.resolve("ADOPT", "op_b")

        first = self.assert_stable(MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED)

        self.assertEqual([s["action"] for s in first["performed_steps"]], ["SETTLE_ADOPT"])
        self.assertEqual(self.settlements("op_a", "op_b"), {"op_a": "ABORT", "op_b": "ADOPT"})
        self.assertEqual(self.ops.get(TASK, "op_b").status, OperationStatus.VERIFIED)

    def test_r2c_two_adopt_settlements(self):
        self.adopted_m1()
        self.start("m1", "a.txt", "op_b", landed=True, payload=b"after2\n")
        self.resolve("ADOPT", "op_b")

        self.assert_stable(READY_FOR_VERIFICATION, MicrotaskStatus.DONE)
        self.assertEqual(self.settlements("op_a", "op_b"), {"op_a": "ADOPT", "op_b": "ADOPT"})

    def test_r2d_two_abort_settlements(self):
        self.aborted_m1()
        self.start("m1", "a.txt", "op_b", landed=False, payload=b"after2\n")
        self.resolve("ABORT", "op_b")

        self.assert_stable(MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.settlements("op_a", "op_b"), {"op_a": "ABORT", "op_b": "ABORT"})

    def test_r2e_adopt_with_rollback_settlement_in_the_same_microtask(self):
        # White-box: the public reconciliation refuses this mix for one
        # microtask (it asks for manual review), so the persistent shape is
        # written through the internal settlement path to pin the aggregation.
        self.adopted_m1()
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_b", payload=b"after2\n")
        with self.ops.task_lock(TASK):
            self.ops._settle_recovery_locked(TASK, "op_b", "ROLLBACK", resolution_id="res_whitebox", expected_revision=1)

        self.assert_stable(MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED)

    def test_r2f_complete_settlement_plus_three_operations_mixed(self):
        self.adopted_m1()
        self.start("m1", "a.txt", "op_b", landed=True, payload=b"after2\n")
        self.resolve("ADOPT", "op_b")
        self.assertEqual(self.recover()["state"], READY_FOR_VERIFICATION)
        self.start("m1", "a.txt", "op_c", landed=False, payload=b"after3\n")
        self.resolve("ABORT", "op_c")

        self.assert_stable(MANUAL_DECISION_REQUIRED, MicrotaskStatus.RECOVERY_REQUIRED)
        self.assertEqual(self.settlements("op_a", "op_b", "op_c"), {"op_a": "ADOPT", "op_b": "ADOPT", "op_c": "ABORT"})
        self.assertFalse(CloseoutService(self.storage).inspect(TASK)["eligible"])

    def test_r2_retry_is_not_rearmed_over_a_sibling_abort_disposition(self):
        self.aborted_m1()
        self.start("m1", "a.txt", "op_b", landed=False, payload=b"after2\n")
        self.resolve("RETRY", "op_b")

        first = self.assert_stable(RECOVERY_BLOCKED, MicrotaskStatus.RECOVERY_REQUIRED)

        self.assertIn("ABORT/ROLLBACK recovery settlement", first["reason"])

    def test_r2_abort_settled_microtask_found_verified_is_a_zero_write_contradiction(self):
        self.activate("m1", "a.txt")
        self.start("m1", "a.txt", "op_a", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.DONE)
        self.resolve("ABORT", "op_a")
        self.assertEqual(self.recover()["state"], MANUAL_DECISION_REQUIRED)
        # the non-CAS state-machine write (finding F-A) can leave this shape behind
        self.tasks.set_microtask_status(TASK, "m1", MicrotaskStatus.VERIFIED)
        before = self.digest()

        result = self.recover()

        self.assertEqual((result["state"], result["recovery_state"]), (RECOVERY_BLOCKED, "SETTLEMENT_CONTRADICTION"))
        self.assertEqual(result["performed_steps"], [])
        self.assertEqual(self.digest(), before)


class ReadyProofBindingTests(Repair2Fixture):
    """R3: READY is returned only for the exact basis its protected proof covered."""

    CHILD = """
        import json, pathlib, sys, time
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        flags = pathlib.Path({flags!r})
        proved = []
        real = RecoveryCoordinator._prove_normal_ready
        def hooked(self, task_id, projection):
            out = real(self, task_id, projection)
            proved.append(out["microtask_id"])
            if len(proved) == 1:
                (flags / "proved").write_text(out["microtask_id"])
                deadline = time.time() + 60
                while not (flags / "go").exists():
                    if time.time() > deadline:
                        raise SystemExit("barrier timeout")
                    time.sleep(0.01)
            return out
        RecoveryCoordinator._prove_normal_ready = hooked
        r = RecoveryCoordinator({storage!r}).recover({task!r})
        proof = r["ready_proof"] or {{}}
        print(json.dumps({{"state": r["state"], "current": r["projection"]["position"]["current_microtask_id"],
                          "proved": proved, "ready_proof_microtask": proof.get("microtask_id")}}))
    """

    def race(self, *, foreign_owned):
        self.activate("m1", "one.txt")
        self.write("two.txt", BEFORE)
        if foreign_owned:
            self.foreign_claim("two.txt", "op_f2")
        child = self.run_child(self.CHILD.format(flags=str(self.flags), storage=str(self.storage), task=TASK))
        self.wait_flag("proved", child)
        self.verify("m1")  # another process advances the same TASK right after the proof
        self.activate("m2", "two.txt")
        (self.flags / "go").write_text("1")
        out, err = child.communicate(timeout=120)
        self.assertEqual(child.returncode, 0, err)
        return json.loads(out.strip().splitlines()[-1])

    def test_r3a_proof_of_m1_never_returns_ready_for_foreign_owned_m2(self):
        data = self.race(foreign_owned=True)

        self.assertNotEqual(data["state"], READY_FOR_EXECUTION)
        self.assertEqual(data["state"], RECOVERY_BLOCKED)
        self.assertEqual(data["proved"], ["m1"])  # the m2 proof ran and was blocked

    def test_r3b_clean_m2_needs_its_own_second_proof(self):
        data = self.race(foreign_owned=False)

        self.assertEqual(data["state"], READY_FOR_EXECUTION)
        self.assertEqual(data["proved"], ["m1", "m2"])
        self.assertEqual(data["ready_proof_microtask"], "m2")
        self.assertEqual(data["current"], "m2")

    def test_r3c_restore_point_change_between_proof_and_return_is_not_ready(self):
        self.activate("m1", "one.txt")
        snap = next((self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"))
        real = RecoveryCoordinator._prove_normal_ready

        def prove_then_corrupt(coordinator, task_id, projection):
            out = real(coordinator, task_id, projection)
            snap.write_bytes(b"tampered")
            return out

        with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", prove_then_corrupt):
            result = self.recover()

        self.assertNotEqual(result["state"], READY_FOR_EXECUTION)
        self.assertIsNone(result["ready_proof"])

    def retry_ready(self):
        self.activate("m1", "one.txt")
        self.start("m1", "one.txt", "op_1", landed=False)
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("RETRY", "op_1")
        first = self.recover()
        self.assertEqual(first["state"], READY_FOR_EXECUTION)
        self.assertEqual(first["ready_proof"]["kind"], "RETRY")

    def test_r3d_resolution_identity_change_after_proof_is_not_ready(self):
        self.retry_ready()
        real = RecoveryCoordinator._prove_retry_ready

        def prove_then_abort(coordinator, task_id, projection):
            out = real(coordinator, task_id, projection)
            self.resolve("ABORT", "op_1")  # the RETRY stops being the authority
            return out

        with mock.patch.object(RecoveryCoordinator, "_prove_retry_ready", prove_then_abort):
            result = self.recover()

        self.assertNotEqual(result["state"], READY_FOR_EXECUTION)

    def test_r3e_operation_revision_change_after_proof_is_not_ready(self):
        self.retry_ready()
        real = RecoveryCoordinator._prove_retry_ready

        def prove_then_bump(coordinator, task_id, projection):
            out = real(coordinator, task_id, projection)
            self.ops.transition(TASK, "op_1", OperationStatus.UNKNOWN_AFTER_DISCONNECT)
            return out

        with mock.patch.object(RecoveryCoordinator, "_prove_retry_ready", prove_then_bump):
            result = self.recover()

        self.assertNotEqual(result["state"], READY_FOR_EXECUTION)

    def test_r3f_same_microtask_basis_change_requires_a_second_proof(self):
        self.activate("m1", "one.txt")
        real = RecoveryCoordinator._prove_normal_ready
        calls = []

        def prove_then_change(coordinator, task_id, projection):
            out = real(coordinator, task_id, projection)
            calls.append(out["microtask_id"])
            if len(calls) == 1:  # same microtask, but its authoritative basis changes
                self.tasks.set_microtask_status(TASK, "m1", MicrotaskStatus.ACTIVE)
            return out

        with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", prove_then_change):
            result = self.recover()

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(calls, ["m1", "m1"])
        self.assertEqual(result["ready_proof"]["source_fingerprint"], result["projection"]["source_fingerprint"])

    def test_ready_proof_identity_is_reported(self):
        self.activate("m1", "one.txt")

        result = self.recover()

        proof = result["ready_proof"]
        self.assertEqual((proof["kind"], proof["task_id"], proof["microtask_id"]), ("NORMAL", TASK, "m1"))
        self.assertEqual(proof["manifest_id"], result["projection"]["restore_point"]["manifest_id"])
        self.assertFalse(proof["physical_mutation_performed"])


class LockOrderTests(Repair2Fixture):
    """F-D: RC-6 proofs and RC-4 apply share one target lock order."""

    HOOK = """
        import json, pathlib, sys, time
        import web_alarm.store_lock as sl
        flags = pathlib.Path({flags!r})
        locks = pathlib.Path({locks!r}).resolve()
        real_acquire = sl.InterProcessLock.acquire
        state = {{"first": False}}
        def acquire(self):
            first = self.path.parent.resolve() == locks and not state["first"]
            if first:
                (flags / ({me!r} + "_trying")).write_text(self.path.name)
            real_acquire(self)
            if first:
                state["first"] = True
                # hold the first target lock until the peer is trying its own first one
                deadline = time.time() + 20
                while not (flags / ({peer!r} + "_trying")).exists() and time.time() < deadline:
                    time.sleep(0.01)
                time.sleep(0.2)
        sl.InterProcessLock.acquire = acquire
        t0 = time.time()
    """

    def test_target_lock_order_is_the_rc4_hash_order(self):
        keys = [f"c:/w/file{i}.txt" for i in range(30)]
        self.assertEqual(target_lock_order(keys), sorted(keys, key=target_hash))
        self.assertEqual(target_lock_order(keys + keys[:3]), target_lock_order(keys))

    def test_rc6_proof_and_foreign_rc4_apply_on_shared_targets_do_not_deadlock(self):
        names = [f"t{i}.txt" for i in range(16)]
        keys = {n: physical_target_key(canonical_target(self.project, n).path) for n in names}
        pair = next(
            (x, y)
            for i, x in enumerate(names)
            for y in names[i + 1:]
            if sorted([x, y], key=lambda n: keys[n]) != sorted([x, y], key=lambda n: target_hash(keys[n]))
        )
        x, y = pair
        self.activate("m1", x, y)
        self.machine.prepare_microtask(OTHER, "f1", [(x, "edit"), (y, "delete")])
        self.machine.transition(OTHER, "f1", MicrotaskStatus.READY)
        self.machine.transition(OTHER, "f1", MicrotaskStatus.ACTIVE)
        self.start("f1", x, "op_fx", landed=True, task=OTHER)
        self.machine.transition(OTHER, "f1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        resolution = self.resolve("ROLLBACK", "op_fx", mid="f1", task=OTHER)
        rid = RollbackService(self.storage).prepare(OTHER, "f1", "op_fx", resolution.resolution_id)["rollback"]["rollback_id"]
        locks = str(TargetClaimStore(self.storage).locks)
        hook = textwrap.dedent(self.HOOK)
        coordinator = hook.format(flags=str(self.flags), locks=locks, me="A", peer="B") + f"""
r = __import__("web_alarm.recovery_coordinator", fromlist=["x"]).RecoveryCoordinator({str(self.storage)!r}, lock_timeout=6).recover({TASK!r})
print(json.dumps({{"state": r["state"], "reason": r["reason"], "elapsed": time.time() - t0}}))
"""
        rollback = hook.format(flags=str(self.flags), locks=locks, me="B", peer="A") + f"""
out = __import__("web_alarm.rollback_service", fromlist=["x"]).RollbackService({str(self.storage)!r}, lock_timeout=6).apply({OTHER!r}, {rid!r})
print(json.dumps({{"result": out["result"], "elapsed": time.time() - t0}}))
"""
        a = self.run_child(coordinator)
        b = self.run_child(rollback)
        out_a, err_a = a.communicate(timeout=120)
        out_b, err_b = b.communicate(timeout=120)

        self.assertEqual(a.returncode, 0, err_a)
        self.assertEqual(b.returncode, 0, err_b)
        res_a = json.loads(out_a.strip().splitlines()[-1])
        res_b = json.loads(out_b.strip().splitlines()[-1])
        self.assertNotIn("timeout", res_a["reason"])
        self.assertIn(res_a["state"], (READY_FOR_EXECUTION, RECOVERY_BLOCKED))
        self.assertEqual(res_b["result"], "VERIFIED")
        self.assertLess(max(res_a["elapsed"], res_b["elapsed"]), 6)
        self.assertEqual(self.read(x), BEFORE)


class RefusedStepTests(Repair2Fixture):
    """F-E: a step RC-4 refused is not repeated within one recover invocation."""

    def test_blocked_rc4_apply_runs_once_per_recover(self):
        for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            self.write(name, data)
        self.activate("m1", specs=[("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        self.start("m1", "a.txt", "op_1", landed=True, payload=b"a-after\n")
        (self.project / "b.txt").unlink()
        self.machine.transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        resolution = self.resolve("ROLLBACK", "op_1")
        rollbacks = RollbackService(self.storage)
        rid = rollbacks.prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]["rollback_id"]
        real_event = rs.RollbackService._event

        def crash_after_first(service, record, event_type, payload):
            real_event(service, record, event_type, payload)
            if event_type == "ROLLBACK_TARGET_RESTORED":
                raise KeyboardInterrupt("simulated crash after the first own restore")

        with mock.patch.object(rs.RollbackService, "_event", crash_after_first):
            with self.assertRaises(KeyboardInterrupt):
                rollbacks.apply(TASK, rid)
        for snap in (self.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"):
            snap.write_bytes(b"tampered")  # RC-4 now refuses: RESTORE_POINT_INVALID

        first = self.recover()
        blocked_after_first = self.events("ROLLBACK_BLOCKED")
        second = self.recover()

        for result in (first, second):
            self.assertEqual(result["state"], RECOVERY_BLOCKED)
            self.assertEqual(result["error"], "RECOVERY_STEP_REFUSED")
            self.assertEqual([s["action"] for s in result["performed_steps"]], ["APPLY_ROLLBACK"])
            self.assertIn("RESTORE_POINT_INVALID", result["reason"])
        self.assertEqual(blocked_after_first, 1)
        self.assertEqual(self.events("ROLLBACK_BLOCKED"), 2)
        self.assertEqual(rollbacks.inspect(TASK, rid)["status"], "APPLYING")


if __name__ == "__main__":
    unittest.main()
