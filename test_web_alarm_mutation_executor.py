"""WA4-E (CLAUDE-WA-018): authoritative mutation executor / gateway.

Positive: write/edit/create/delete/move/rename with snapshot, CAS, STARTED-before-write, exact
post-proof and receipt; replay of the same contract (also from a fresh process) never repeats a
side effect. Negative: closed TASK, wrong / not ACTIVE microtask, target outside the manifest or
the root, invalid restore point, pre-state drift, operation_id conflict, path spellings, ownership.
Failures: STARTED / write / post-proof / receipt persistence, real process deaths in the four
critical windows (before STARTED, after STARTED, after the write, after the receipt), Windows
sharing violations. Races (real processes): two executors on one physical target, execution vs
TASK completion. Compatibility: RC-2 RETRY / ADOPT, RC-4 rollback, RC-6 recover / READY.
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.mutation_executor as mx
from web_alarm.closeout import CloseoutService
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.models import OperationStatus, TaskStatus
from web_alarm.mutation_executor import (
    EXECUTED,
    PARTIAL,
    RECONCILIATION_REQUIRED,
    REFUSED,
    REPLAYED,
    MutationExecutor,
    MutationRequestError,
)
from web_alarm.operation_store import OperationStore, OperationStoreError
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import READY_FOR_EXECUTION, RecoveryCoordinator
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_e"
BEFORE, AFTER = b"before\n", b"after-content\n"
FILES = {"a.txt": BEFORE, "gone.txt": b"gone\n", "src.txt": b"move me\n", "keep.txt": b"keep\n",
         "outside_manifest.txt": b"x\n"}
MANIFEST = [("a.txt", "edit"), ("gone.txt", "delete"), ("new.txt", "create"), ("src.txt", "move"),
            ("dst.txt", "move"), ("keep.txt", "edit"), ("sub/r_src.txt", "rename"), ("sub/r_dst.txt", "rename"),
            ("x_dst.txt", "move")]

# one execution in a separate process, optionally dying at a critical point (os._exit)
CHILD = """
    import json, os, sys, time
    point, storage = sys.argv[1], sys.argv[2]
    import web_alarm.mutation_executor as mx
    import web_alarm.operation_store as store
    real_transition = store.OperationStore._transition_locked
    real_apply = mx.MutationExecutor._apply
    real_release = mx.MutationExecutor._release
    def transition(self, task_id, operation_id, requested, **kw):
        status = store.OperationStatus(requested).value
        if point == "before_started" and status == "STARTED":
            os._exit(9)
        return real_transition(self, task_id, operation_id, requested, **kw)
    def apply(kind, path, data):
        if point == "after_started":
            os._exit(9)
        if point == "slow_write":
            time.sleep(0.4)
        real_apply(kind, path, data)
        if point == "after_write":
            os._exit(9)
    def release(self, task_id, operation_id, reason):
        if point == "after_receipt":
            os._exit(9)
        return real_release(self, task_id, operation_id, reason)
    store.OperationStore._transition_locked = transition
    mx.MutationExecutor._apply = staticmethod(apply)
    mx.MutationExecutor._release = release
    barrier = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    if barrier:
        from pathlib import Path
        Path(barrier, "ready_" + sys.argv[4]).touch()
        while not Path(barrier, "go").exists():
            time.sleep(0.0005)
    request = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
    out = mx.MutationExecutor(storage, lock_timeout=60).execute(
        "task_e", "m1", request.get("operation_id", "op_1"), request.get("action", "write"),
        request.get("target", "a.txt"), payload=request.get("payload", "after-content\\n").encode())
    print(json.dumps({k: out.get(k) for k in ("result", "result_code", "physical_mutation_performed", "receipt")}))
"""

CLOSE_CHILD = """
    import json, sys, time
    from pathlib import Path
    storage, barrier = sys.argv[1:3]
    from web_alarm.task_store import TaskStore
    Path(barrier, "ready_close").touch()
    while not Path(barrier, "go").exists():
        time.sleep(0.0005)
    time.sleep(0.05)
    result = None
    for attempt in range(100):  # Windows refuses the move while a file inside the TASK is open: retry
        try:
            TaskStore(storage, lock_timeout=60).complete_task("task_e")
            result = "CLOSED"
            break
        except Exception as exc:
            result = "FAILED:" + type(exc).__name__ + ": " + str(exc)
            time.sleep(0.05)
    print(json.dumps({"result": result}))
"""

HOLD_OPEN = """
    import sys, time
    handle = open(sys.argv[1], "rb")
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
"""


class Fixture(unittest.TestCase):
    manifest = MANIFEST

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.storage, self.project = root / "state", root / "project"
        (self.project / "sub").mkdir(parents=True)
        for name, data in FILES.items():
            self.write(name, data)
        self.write("sub/r_src.txt", b"rename me\n")
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_e")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_e", TASK, "RAW TASK", "WA4-E", task_id=TASK)
        self.tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
        self.tasks.create_microtask(TASK, "M2", "m2", microtask_id="m2")
        self.machine = ServerStateMachine(self.storage)
        self.machine.prepare_microtask(TASK, "m1", self.manifest)
        self.ops = OperationStore(self.storage)
        self.executor = MutationExecutor(self.storage)

    def activate(self):
        self.machine.transition(TASK, "m1", "READY")
        self.machine.transition(TASK, "m1", "ACTIVE")

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def read(self, name):
        path = self.project / name
        return path.read_bytes() if path.exists() else None

    def run_write(self, op="op_1", target="a.txt", payload=AFTER, **kw):
        return self.executor.execute(TASK, "m1", op, "write", target, payload=payload, **kw)

    def op(self, op="op_1"):
        return self.ops.get(TASK, op)

    def events(self, event_type):
        return [e for e in EventCheckpointStore(self.storage).read_events(TASK) if e.event_type == event_type]

    def active_claims(self):
        root = self.storage / "target_claims"
        if not root.is_dir():
            return []
        return [json.loads(p.read_text(encoding="utf-8"))["active"] for p in sorted(root.glob("*.json"))
                if json.loads(p.read_text(encoding="utf-8"))["active"]]

    def resolve(self, action, op="op_1"):
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", op)["DECISION"]
        out = ResolverService(self.storage).apply(TASK, "m1", op, action,
                                                  evidence_fingerprint=decision["evidence_fingerprint"],
                                                  operation_revision=self.op(op).revision)
        self.assertTrue(out["accepted"], out["resolution"].result_reason)
        return decision

    def count_writes(self):
        calls = []
        real = MutationExecutor._apply

        def counting(kind, path, data):
            calls.append(kind.value)
            return real(kind, path, data)
        patcher = mock.patch.object(MutationExecutor, "_apply", staticmethod(counting))
        patcher.start()
        self.addCleanup(patcher.stop)
        return calls

    def child(self, point, *extra):
        return subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(CHILD), point, str(self.storage), *extra],
                              cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)


class PositiveTests(Fixture):
    def test_write_and_edit_follow_the_whole_chain(self):
        self.activate()
        writes = self.count_writes()
        out = self.run_write()
        self.assertEqual((out["result"], out["result_code"], out["physical_mutation_performed"]),
                         (EXECUTED, "EXACT_POST_STATE_PROVED", True))
        self.assertEqual(self.read("a.txt"), AFTER)
        record = self.op()
        self.assertEqual(record.status, OperationStatus.DONE)
        self.assertTrue(record.receipt["matches_expected_post"])
        self.assertEqual((record.receipt["sha256"], record.receipt["size"]),
                         (record.contract["expected_post_state"]["sha256"], len(AFTER)))
        self.assertEqual(out["receipt"], record.receipt)
        self.assertEqual(self.active_claims(), [])
        self.assertEqual(len(self.events("MUTATION_EXECUTED")), 1)
        edit = self.executor.execute(TASK, "m1", "op_2", "edit", "a.txt", payload=b"edited\n")
        self.assertEqual((edit["result"], self.read("a.txt")), (EXECUTED, b"edited\n"))
        self.assertEqual(writes, ["WRITE", "WRITE"])

    def test_create_and_delete(self):
        self.activate()
        created = self.executor.execute(TASK, "m1", "op_c", "create", "new.txt", payload=b"new\n")
        deleted = self.executor.execute(TASK, "m1", "op_d", "delete", "gone.txt")
        self.assertEqual((created["result"], deleted["result"]), (EXECUTED, EXECUTED))
        self.assertEqual((self.read("new.txt"), self.read("gone.txt")), (b"new\n", None))
        self.assertFalse(self.op("op_d").receipt["exists"])
        self.assertEqual([p.name for p in self.project.iterdir() if p.name.endswith(".tmp")], [])

    def test_move_and_rename_are_two_tracked_operations(self):
        self.activate()
        moved = self.executor.execute(TASK, "m1", "op_m", "move", "src.txt", destination="dst.txt")
        self.assertEqual((moved["result"], moved["result_code"]), (EXECUTED, "MOVE_COMPLETED"))
        self.assertEqual([s["operation_id"] for s in moved["steps"]],
                         ["op_m.create-destination", "op_m.delete-source"])
        self.assertEqual((self.read("dst.txt"), self.read("src.txt")), (b"move me\n", None))
        self.assertTrue(all(self.op(s["operation_id"]).status is OperationStatus.DONE for s in moved["steps"]))
        renamed = self.executor.execute(TASK, "m1", "op_r", "rename", "sub/r_src.txt", destination="sub/r_dst.txt")
        self.assertEqual((renamed["result"], self.read("sub/r_dst.txt"), self.read("sub/r_src.txt")),
                         (EXECUTED, b"rename me\n", None))
        self.assertEqual(self.active_claims(), [])

    def test_replay_of_the_same_contract_never_repeats_the_side_effect(self):
        self.activate()
        first = self.run_write()
        writes = self.count_writes()
        again = self.run_write()
        self.assertEqual((again["result"], again["physical_mutation_performed"]), (REPLAYED, False))
        self.assertEqual(again["receipt"], first["receipt"])
        self.assertEqual(writes, [])
        moved = self.executor.execute(TASK, "m1", "op_m", "move", "src.txt", destination="dst.txt")
        replay = self.executor.execute(TASK, "m1", "op_m", "move", "src.txt", destination="dst.txt")
        self.assertEqual((moved["result"], replay["result"], writes), (EXECUTED, REPLAYED, ["CREATE", "DELETE"]))
        fresh = self.child("none")  # the same op_1 write from a fresh process
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertEqual(json.loads(fresh.stdout)["result"], REPLAYED)
        self.assertEqual(len(self.events("MUTATION_EXECUTED")), 3)  # write, create, delete — once each

    def test_started_is_persisted_before_the_first_physical_write(self):
        self.activate()
        seen = []
        real = MutationExecutor._apply

        def observe(kind, path, data):
            fresh = OperationStore(self.storage).get(TASK, "op_1")  # what any other process reads now
            seen.append((fresh.status.value, path.read_bytes()))
            return real(kind, path, data)
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(observe)):
            self.assertEqual(self.run_write()["result"], EXECUTED)
        self.assertEqual(seen, [("STARTED", BEFORE)])


class AdmissionTests(Fixture):
    def assert_refused(self, out, code, *, files=None, owned=False):
        self.assertEqual((out["result"], out["result_code"]), (REFUSED, code), out["reason"])
        self.assertFalse(out["physical_mutation_performed"])
        for name, data in (files or {"a.txt": BEFORE}).items():
            self.assertEqual(self.read(name), data)
        # a refusal before the claim leaves no ownership; one after it keeps the operation's claim
        self.assertEqual([c["operation_id"] for c in self.active_claims()], [out["operation_id"]] if owned else [])

    def test_closed_and_archived_tasks_admit_nothing(self):
        self.activate()
        self.tasks.complete_task(TASK)
        out = self.run_write()
        self.assertEqual(out["result"], REFUSED)
        self.assertIn(out["result_code"], ("TASK_NOT_ACTIVE", "TASK_CLOSED"))
        self.tasks.archive_task(TASK)
        self.assertEqual(self.run_write()["result"], REFUSED)
        self.assertEqual(self.read("a.txt"), BEFORE)

    def test_microtask_not_active_or_not_current(self):
        self.assert_refused(self.run_write(), "MICROTASK_NOT_ACTIVE", owned=True)  # restore point VERIFIED
        self.assertEqual(self.op().status, OperationStatus.INTENT)
        self.activate()
        self.assertEqual(self.run_write()["result"], EXECUTED)  # the same operation continues once ACTIVE
        self.write("a.txt", BEFORE)
        other = self.executor.execute(TASK, "m2", "op_m2", "write", "a.txt", payload=AFTER)
        self.assertEqual(other["result"], REFUSED)  # m2 is not the ACTIVE current stage / has no restore point
        self.assertEqual(self.read("a.txt"), BEFORE)

    def test_target_outside_the_manifest_or_the_root(self):
        self.activate()
        self.assert_refused(self.run_write(target="outside_manifest.txt"), "TARGET_NOT_IN_MANIFEST",
                            files={"outside_manifest.txt": b"x\n"})
        self.assert_refused(self.run_write(op="op_2", target="../escape.txt"), "CONTRACT_REJECTED")
        self.assertFalse((self.project.parent / "escape.txt").exists())

    def test_invalid_restore_point(self):
        self.activate()
        snapshot = next(p for p in (self.tasks.task_directory(TASK) / "microtasks" / "m1").rglob("*.bin"))
        snapshot.write_bytes(b"tampered")
        self.assert_refused(self.run_write(), "RESTORE_POINT_NOT_VERIFIED")

    def test_changed_pre_state_is_never_overwritten(self):
        self.activate()
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)  # INTENT, basis BEFORE
        self.write("a.txt", b"edited by someone else\n")
        self.assert_refused(self.run_write(), "PRECONDITION_FAILED", files={"a.txt": b"edited by someone else\n"})

    def test_same_operation_id_with_another_payload_or_target(self):
        self.activate()
        self.run_write()
        self.assertEqual(self.run_write(payload=b"other\n")["result_code"], "OPERATION_ID_CONFLICT")
        self.assertEqual(self.run_write(target="keep.txt")["result_code"], "OPERATION_ID_CONFLICT")
        self.assertEqual(self.read("a.txt"), AFTER)
        with self.assertRaises(MutationRequestError):
            self.executor.execute(TASK, "m1", "", "write", "a.txt", payload=AFTER)

    def test_path_spellings_name_one_physical_target(self):
        self.activate()
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_owner", payload=b"owner\n")
        TargetClaimService(self.storage).acquire(TASK, "op_owner", operation_revision=1)
        variants = ["./sub/../a.txt", "sub/../a.txt"] + (["A.TXT"] if os.name == "nt" else [])
        for index, spelling in enumerate(variants):
            out = self.executor.execute(TASK, "m1", f"op_v{index}", "write", spelling, payload=AFTER)
            self.assertEqual((out["result"], out["result_code"]), (REFUSED, "TARGET_OWNED"), spelling)
        self.assertEqual(self.read("a.txt"), BEFORE)
        replay = self.executor.execute(TASK, "m1", "op_owner", "write", "./a.txt", payload=b"owner\n")
        self.assertEqual(replay["result"], EXECUTED)  # the same contract under another spelling

    def test_incomplete_contract_and_corrupt_payload(self):
        self.activate()
        incomplete = self.executor.execute(TASK, "m1", "op_i", "write", "a.txt")
        self.assertEqual(incomplete["result_code"], "CONTRACT_INCOMPLETE")
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_p", payload=AFTER)
        blob = next((self.tasks.task_directory(TASK) / "payloads").glob("*.bin"))
        blob.write_bytes(b"corrupted")
        self.assertEqual(self.run_write(op="op_p")["result_code"], "PAYLOAD_INTEGRITY_FAILURE")
        self.assertEqual(self.op("op_p").status, OperationStatus.INTENT)
        self.assertEqual(self.read("a.txt"), BEFORE)

    def test_move_protections(self):
        self.activate()
        self.assertEqual(self.executor.execute(TASK, "m1", "op_x", "rename", "src.txt",
                                               destination="sub/r_dst.txt")["result_code"],
                         "RENAME_ACROSS_DIRECTORIES")
        self.assertEqual(self.executor.execute(TASK, "m1", "op_y", "move", "src.txt",
                                               destination="./src.txt")["result_code"], "SAME_PHYSICAL_TARGET")
        with self.assertRaises(MutationRequestError):
            self.executor.execute(TASK, "m1", "op_z", "move", "src.txt")
        # both targets are owned before the first write: the source is protected during step 1
        seen = []
        real = MutationExecutor._apply

        def probe(kind, path, data):
            if kind.value == "CREATE":  # inside the destination boundary: who owns what right now
                seen.append(sorted(claim["operation_id"] for claim in self.active_claims()))
            return real(kind, path, data)
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(probe)):
            moved = self.executor.execute(TASK, "m1", "op_m", "move", "src.txt", destination="dst.txt")
        self.assertEqual((moved["result"], seen),
                         (EXECUTED, [["op_m.create-destination", "op_m.delete-source"]]))
        # and a compliant intruder cannot take the source while the pair is open
        self.ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_hold", payload=b"x\n")
        claims = TargetClaimService(self.storage)
        claims.acquire(TASK, "op_hold", operation_revision=1)
        intruder = self.executor.execute(TASK, "m1", "op_i", "write", "keep.txt", payload=b"intruder\n")
        self.assertEqual(intruder["result_code"], "TARGET_OWNED")

    def test_a_move_interrupted_between_its_steps_is_partial(self):
        self.activate()
        real = MutationExecutor._apply

        def drift_source_after_create(kind, path, data):
            real(kind, path, data)
            if kind.value == "CREATE":
                (self.project / "src.txt").write_bytes(b"changed during the move\n")  # a non-compliant writer
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(drift_source_after_create)):
            out = self.executor.execute(TASK, "m1", "op_m", "move", "src.txt", destination="dst.txt")
        self.assertEqual((out["result"], out["result_code"]), (PARTIAL, "MOVE_INTERRUPTED"))
        self.assertEqual((self.read("dst.txt"), self.read("src.txt")), (b"move me\n", b"changed during the move\n"))
        self.assertEqual(out["steps"][1]["result_code"], "PRECONDITION_FAILED")  # never deletes changed bytes


class FailureTests(Fixture):
    def test_started_not_persisted_writes_nothing(self):
        self.activate()
        real = OperationStore._transition_locked

        def refuse_started(store, task_id, operation_id, requested, **kw):
            if OperationStatus(requested) is OperationStatus.STARTED:
                raise OperationStoreError("disk full (test)")
            return real(store, task_id, operation_id, requested, **kw)
        with mock.patch.object(OperationStore, "_transition_locked", refuse_started):
            out = self.run_write()
        self.assertEqual((out["result"], out["result_code"]), (REFUSED, "STARTED_NOT_PERSISTED"))
        self.assertEqual((self.read("a.txt"), self.op().status), (BEFORE, OperationStatus.INTENT))
        self.assertEqual([c["operation_id"] for c in self.active_claims()], ["op_1"])  # kept for the replay
        self.assertEqual(self.run_write()["result"], EXECUTED)
        self.assertEqual(self.active_claims(), [])
        # an abandoned basis is final: released ownership is never re-owned (RC-3)
        self.ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_k", payload=b"k2\n")
        claims = TargetClaimService(self.storage)
        claims.acquire(TASK, "op_k", operation_revision=1)
        claims.release(TASK, "op_k", reason="abandoned")
        self.assertEqual(self.run_write(op="op_k", target="keep.txt", payload=b"k2\n")["result_code"],
                         "CLAIM_ALREADY_RELEASED")
        self.assertEqual(self.read("keep.txt"), b"keep\n")

    def test_post_proof_failure_never_reports_success(self):
        self.activate()

        def wrong_bytes(kind, path, data):
            path.write_bytes(b"not the contracted bytes\n")
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(wrong_bytes)):
            out = self.run_write()
        self.assertEqual((out["result"], out["result_code"]), (RECONCILIATION_REQUIRED, "POST_PROOF_FAILED"))
        self.assertEqual((self.op().status, self.op().receipt), (OperationStatus.STARTED, None))

    def test_external_creation_inside_the_window_is_never_overwritten(self):
        self.activate()
        real = MutationExecutor._apply

        def race(kind, path, data):
            path.write_bytes(b"created by someone else\n")  # after the CAS, before the create
            return real(kind, path, data)
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(race)):
            out = self.executor.execute(TASK, "m1", "op_c", "create", "new.txt", payload=b"new\n")
        self.assertEqual((out["result"], out["result_code"]), (RECONCILIATION_REQUIRED, "WRITE_OUTCOME_UNKNOWN"))
        self.assertEqual(self.read("new.txt"), b"created by someone else\n")

    def test_a_write_of_an_absent_file_never_replaces_one_that_appeared(self):
        self.activate()
        real = MutationExecutor._apply

        def race(kind, path, data):
            path.write_bytes(b"appeared meanwhile\n")
            return real(kind, path, data)
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(race)):
            out = self.executor.execute(TASK, "m1", "op_w", "write", "dst.txt", payload=b"mine\n")
        self.assertEqual((out["result"], out["result_code"]), (RECONCILIATION_REQUIRED, "WRITE_OUTCOME_UNKNOWN"))
        self.assertEqual(self.read("dst.txt"), b"appeared meanwhile\n")

    @unittest.skipUnless(os.name == "nt", "Windows sharing semantics")
    def test_a_real_windows_sharing_violation_fails_closed(self):
        self.activate()
        holder = subprocess.Popen([sys.executable, "-c", textwrap.dedent(HOLD_OPEN), str(self.project / "a.txt"), "5"],
                                  stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            out = self.run_write()
        finally:
            holder.kill()
            holder.communicate()
        self.assertEqual((out["result"], out["result_code"]), (RECONCILIATION_REQUIRED, "WRITE_REFUSED_TARGET_UNCHANGED"))
        self.assertEqual((self.read("a.txt"), self.op().receipt), (BEFORE, None))


class SingleTargetRecoveryTests(Fixture):
    """RC-2 decides RETRY / ADOPT over the whole restore point of the microtask (all its targets):
    these recoveries are exercised on a one-target stage (see CompatibilityTests for many targets)."""

    manifest = [("a.txt", "edit")]

    def test_a_refused_write_is_proved_unchanged_and_a_retry_executes_it(self):
        self.activate()
        with mock.patch.object(mx, "_atomic_write_bytes", side_effect=mx.ManifestStoreError("sharing violation")):
            out = self.run_write()
        self.assertEqual((out["result"], out["result_code"]), (RECONCILIATION_REQUIRED, "WRITE_REFUSED_TARGET_UNCHANGED"))
        self.assertEqual((self.read("a.txt"), self.op().status, self.op().receipt), (BEFORE, OperationStatus.STARTED, None))
        again = self.run_write()  # a replay never repeats an unknown result blindly
        self.assertEqual((again["result"], again["reconciliation"]["decision"]), (RECONCILIATION_REQUIRED, "RETRY_SAFE"))
        self.resolve("RETRY")
        retried = self.run_write()
        self.assertEqual((retried["result"], self.read("a.txt"), self.op().status),
                         (EXECUTED, AFTER, OperationStatus.DONE))

    def test_receipt_not_persisted_then_adopted_without_a_second_write(self):
        self.activate()
        real = OperationStore._transition_locked

        def refuse_done(store, task_id, operation_id, requested, **kw):
            if OperationStatus(requested) is OperationStatus.DONE:
                raise OperationStoreError("disk full (test)")
            return real(store, task_id, operation_id, requested, **kw)
        with mock.patch.object(OperationStore, "_transition_locked", refuse_done):
            out = self.run_write()
        self.assertEqual((out["result"], out["result_code"]), (RECONCILIATION_REQUIRED, "RECEIPT_NOT_PERSISTED"))
        self.assertEqual((self.read("a.txt"), self.op().status), (AFTER, OperationStatus.STARTED))
        writes = self.count_writes()
        self.assertEqual(self.run_write()["reconciliation"]["decision"], "ADOPT_CURRENT_STATE")
        self.resolve("ADOPT")
        RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual((self.op().status, writes), (OperationStatus.VERIFIED, []))

    def test_retry_of_an_unknown_after_disconnect_operation_is_refused(self):
        self.activate()
        self.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "UNKNOWN_AFTER_DISCONNECT")
        self.resolve("RETRY")
        out = self.run_write()
        self.assertEqual((out["result"], out["result_code"]), (REFUSED, "RETRY_LIFECYCLE_UNSUPPORTED"))
        self.assertEqual(self.read("a.txt"), BEFORE)


class CrashWindowTests(Fixture):
    """Real process deaths (os._exit) in the four critical windows, then a fresh process replays."""

    manifest = [("a.txt", "edit")]

    def die_and_replay(self, point):
        died = self.child(point)
        self.assertEqual(died.returncode, 9, died.stderr)
        replay = self.child("none")
        self.assertEqual(replay.returncode, 0, replay.stderr)
        return json.loads(replay.stdout)

    def test_death_before_started_is_executed_once_on_replay(self):
        self.activate()
        died = self.child("before_started")
        self.assertEqual(died.returncode, 9, died.stderr)
        self.assertEqual((self.op().status, self.read("a.txt")), (OperationStatus.INTENT, BEFORE))
        replay = json.loads(self.child("none").stdout)
        self.assertEqual((replay["result"], self.read("a.txt")), (EXECUTED, AFTER))

    def test_death_after_started_before_the_write_needs_a_retry(self):
        self.activate()
        replay = self.die_and_replay("after_started")
        self.assertEqual((replay["result"], self.op().status, self.read("a.txt")),
                         (RECONCILIATION_REQUIRED, OperationStatus.STARTED, BEFORE))
        self.resolve("RETRY")
        self.assertEqual((json.loads(self.child("none").stdout)["result"], self.read("a.txt")), (EXECUTED, AFTER))
        self.assertEqual(len(self.events("MUTATION_EXECUTED")), 1)

    def test_death_after_the_write_before_the_receipt_is_adopted_not_repeated(self):
        self.activate()
        replay = self.die_and_replay("after_write")
        self.assertEqual((replay["result"], self.op().status, self.read("a.txt")),
                         (RECONCILIATION_REQUIRED, OperationStatus.STARTED, AFTER))
        self.assertEqual(ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["DECISION"]["decision"],
                         "ADOPT_CURRENT_STATE")
        self.resolve("ADOPT")
        RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(self.op().status, OperationStatus.VERIFIED)
        self.assertEqual(self.events("MUTATION_EXECUTED"), [])  # the write landed once, never twice

    def test_death_after_the_receipt_returns_the_same_receipt(self):
        self.activate()
        died = self.child("after_receipt")
        self.assertEqual(died.returncode, 9, died.stderr)
        receipt = self.op().receipt
        self.assertEqual((self.op().status, len(self.active_claims())), (OperationStatus.DONE, 1))
        replay = json.loads(self.child("none").stdout)
        self.assertEqual((replay["result"], replay["physical_mutation_performed"], replay["receipt"]),
                         (REPLAYED, False, receipt))
        self.assertEqual((self.active_claims(), len(self.events("MUTATION_EXECUTED"))), ([], 1))


class RaceTests(Fixture):
    def race(self, jobs):
        barrier = Path(self.tempdir.name) / "barrier"
        barrier.mkdir()
        procs = []
        for name, point, request in jobs:
            if point == "close":
                args = [sys.executable, "-B", "-c", textwrap.dedent(CLOSE_CHILD), str(self.storage), str(barrier)]
            else:
                args = [sys.executable, "-B", "-c", textwrap.dedent(CHILD), point, str(self.storage), str(barrier), name,
                        json.dumps(request)]
            procs.append(subprocess.Popen(args, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        try:
            deadline = time.monotonic() + 60
            while len(list(barrier.glob("ready_*"))) < len(jobs):
                self.assertLess(time.monotonic(), deadline, "workers did not reach the barrier")
                time.sleep(0.01)
            (barrier / "go").touch()
            results = {}
            for proc, (name, _, _) in zip(procs, jobs):
                out, err = proc.communicate(timeout=120)
                self.assertEqual(proc.returncode, 0, err)
                results[name] = json.loads(out)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.kill()
        return results

    def test_two_executors_on_one_physical_target_never_both_write(self):
        for round_ in range(4):
            self.setUp()
            self.activate()
            results = self.race([
                ("a", "none", {"operation_id": "op_a", "target": "a.txt", "payload": "from a\n"}),
                ("b", "none", {"operation_id": "op_b", "target": "./sub/../a.txt", "payload": "from b\n"}),
            ])
            executed = [name for name, out in results.items() if out["result"] == EXECUTED]
            self.assertEqual(len(executed), 1, results)
            loser = "b" if executed == ["a"] else "a"
            self.assertEqual(results[loser]["result"], REFUSED)
            self.assertIn(results[loser]["result_code"], ("TARGET_OWNED", "PRECONDITION_FAILED"))
            self.assertEqual(self.read("a.txt"), f"from {executed[0]}\n".encode())
            self.assertEqual(self.active_claims(), [])

    def test_the_same_contract_delivered_twice_at_once_executes_once(self):
        for round_ in range(4):
            self.setUp()
            self.activate()
            same = {"operation_id": "op_1", "target": "a.txt", "payload": "after-content\n"}
            results = self.race([("a", "none", same), ("b", "none", same)])
            self.assertEqual(sorted(out["result"] for out in results.values()), [EXECUTED, REPLAYED], results)
            self.assertEqual(results["a"]["receipt"], results["b"]["receipt"])
            self.assertEqual((self.read("a.txt"), len(self.events("MUTATION_EXECUTED"))), (AFTER, 1))
            self.assertEqual(self.active_claims(), [])

    def test_execution_racing_the_task_closure_never_writes_into_a_closed_task(self):
        outcomes = set()
        for round_ in range(4):
            self.setUp()
            self.activate()
            results = self.race([("w", "slow_write", {}), ("close", "close", None)])
            closed = (self.tasks.completed_dir / TASK).is_dir()
            self.assertEqual(results["close"]["result"], "CLOSED")
            if results["w"]["result"] == EXECUTED:
                outcomes.add("executed_then_closed")
                self.assertEqual((self.read("a.txt"), self.op().status), (AFTER, OperationStatus.DONE))
            else:
                outcomes.add("closed_first")
                self.assertEqual(results["w"]["result"], REFUSED)
                self.assertEqual(self.read("a.txt"), BEFORE)
            self.assertTrue(closed)
        self.assertTrue(outcomes)


class CompatibilityTests(Fixture):
    def test_rc4_rolls_back_an_executed_mutation(self):
        self.activate()
        self.assertEqual(self.run_write()["result"], EXECUTED)
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["DECISION"]
        self.assertEqual(decision["decision"], "ROLLBACK_CURRENT_MICROTASK")
        resolution = ResolverService(self.storage).apply(
            TASK, "m1", "op_1", "ROLLBACK", evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.op().revision)["resolution"]
        rollbacks = RollbackService(self.storage)
        record = rollbacks.prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]
        self.assertEqual(rollbacks.apply(TASK, record["rollback_id"])["result"], "VERIFIED")
        self.assertEqual(self.read("a.txt"), BEFORE)

    def test_many_target_stage_recovers_an_interrupted_write_through_rollback(self):
        self.activate()
        real = OperationStore._transition_locked

        def refuse_done(store, task_id, operation_id, requested, **kw):
            if OperationStatus(requested) is OperationStatus.DONE:
                raise OperationStoreError("disk full (test)")
            return real(store, task_id, operation_id, requested, **kw)
        with mock.patch.object(OperationStore, "_transition_locked", refuse_done):
            self.assertEqual(self.run_write()["result_code"], "RECEIPT_NOT_PERSISTED")
        replay = self.run_write()
        self.assertEqual((replay["result"], replay["reconciliation"]["decision"]),
                         (RECONCILIATION_REQUIRED, "ROLLBACK_CURRENT_MICROTASK"))
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["DECISION"]
        resolution = ResolverService(self.storage).apply(
            TASK, "m1", "op_1", "ROLLBACK", evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.op().revision)["resolution"]
        result = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(self.read("a.txt"), BEFORE, result["state"])  # restored from the restore point

    def test_rc6_is_ready_again_after_an_execution(self):
        self.activate()
        self.run_write()
        result = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(result["state"], READY_FOR_EXECUTION)  # no leftover ownership or recovery
        self.assertEqual(self.active_claims(), [])

    def test_closed_task_replay_returns_the_persisted_receipt(self):
        self.activate()
        first = self.run_write()
        self.ops.transition(TASK, "op_1", "VERIFIED")
        self.machine.transition(TASK, "m1", "DONE")
        self.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="checked")
        self.tasks.complete_task(TASK)  # m2 stays PLANNED: closed through the storage primitive
        replay = self.run_write()
        self.assertEqual((replay["result"], replay["receipt"]), (REPLAYED, first["receipt"]))
        self.assertEqual(self.run_write(op="op_new")["result"], REFUSED)

    def test_http_endpoint(self):
        self.activate()
        api = WebAlarmApi(self.storage)
        body = {"microtask_id": "m1", "operation_id": "op_h", "action": "write", "target": "a.txt",
                "payload": {"encoding": "utf-8", "data": "via http\n"}}
        status, out = api.dispatch("POST", f"/tasks/{TASK}/mutations", body)
        self.assertEqual((status, out["result"]), (200, EXECUTED))
        status, out = api.dispatch("POST", f"/tasks/{TASK}/mutations", body)
        self.assertEqual((status, out["result"]), (200, REPLAYED))
        with self.assertRaises(ApiError) as caught:
            api.dispatch("POST", f"/tasks/{TASK}/mutations", dict(body, payload={"encoding": "utf-8", "data": "x"}))
        self.assertEqual((caught.exception.status, caught.exception.code), (409, "mutation_refused"))
        with self.assertRaises(ApiError) as caught:
            api.dispatch("POST", f"/tasks/{TASK}/mutations", {k: v for k, v in body.items() if k != "operation_id"})
        self.assertEqual(caught.exception.status, 400)
        self.assertIn("mutations", api.dispatch("GET", "/status")[1]["capabilities"])
        self.assertEqual(self.read("a.txt"), b"via http\n")

    def test_cli_entrypoint(self):
        from contextlib import redirect_stderr, redirect_stdout
        import io
        from web_alarm.cli import main as cli_main
        self.activate()
        payload = Path(self.tempdir.name) / "payload.bin"
        payload.write_bytes(b"via cli\n")
        args = ["--storage-root", str(self.storage), "mutate", "--task-id", TASK, "--microtask-id", "m1",
                "--operation-id", "op_cli", "--action", "edit", "--target", "a.txt", "--payload-file", str(payload)]
        codes = []
        for _ in range(2):
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                codes.append(cli_main(args))
            codes.append(json.loads(out.getvalue())["result"])
        self.assertEqual(codes, [0, EXECUTED, 0, REPLAYED])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            refused = cli_main(args[:-6] + ["--action", "write", "--target", "outside_manifest.txt",
                                            "--payload-file", str(payload)])
        self.assertEqual((refused, self.read("a.txt")), (3, b"via cli\n"))


if __name__ == "__main__":
    unittest.main()
