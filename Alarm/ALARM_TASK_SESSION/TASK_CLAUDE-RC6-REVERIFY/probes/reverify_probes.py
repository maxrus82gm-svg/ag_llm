"""RC-6 re-verification after Repair #1: new adversarial probes (isolated temp storage only).

Each probe builds its own temporary storage + workspace, never touches live storage,
and prints facts plus a one-line VERDICT. Run: python -B reverify_probes.py [name ...]
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from pathlib import Path
from unittest import mock

REPO = r"M:\GitHub\ag_llm"
sys.path.insert(0, REPO)

from web_alarm.closeout import CloseoutService  # noqa: E402
from web_alarm.event_checkpoint_store import EventCheckpointStore  # noqa: E402
from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import (  # noqa: E402
    RecoveryCoordinator,
    RecoveryCoordinatorBlocked,
    RecoveryCoordinatorError,
)
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402
from web_alarm.target_claim_store import TargetClaimStore, physical_target_key  # noqa: E402
from web_alarm.target_identity import canonical_target  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_v"
FOREIGN = "task_foreign"
BEFORE, AFTER = b"before\n", b"after\n"


class Crash(BaseException):
    """Simulated process death inside a step (not caught by coordinator handlers)."""


class World:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage, self.project = root / "state", root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("P", self.project, workspace_id="ws")
        self.tasks = TaskStore(self.storage)
        for task in (TASK, FOREIGN):
            self.tasks.create_task("ws", task, "RAW", "Goal", task_id=task)
        for mid in ("m1", "m2", "m3"):
            self.tasks.create_microtask(TASK, mid, mid, microtask_id=mid)
        self.tasks.create_microtask(FOREIGN, "f1", "f1", microtask_id="f1")
        self.machine = ServerStateMachine(self.storage)
        self.ops = OperationStore(self.storage)

    def close(self):
        self.tmp.cleanup()

    def write(self, name, data):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, name):
        path = self.project / name
        return path.read_bytes() if path.exists() else None

    def to_active(self, mid, *targets, action="edit"):
        for target in targets:
            if not (self.project / target).exists():
                self.write(target, BEFORE)
        self.machine.prepare_microtask(TASK, mid, [(t, action) for t in targets])
        self.machine.transition(TASK, mid, "READY")
        self.machine.transition(TASK, mid, "ACTIVE")

    def verify(self, mid):
        self.machine.transition(TASK, mid, "DONE")
        self.machine.transition(TASK, mid, "VERIFIED", verification_evidence="ok")

    def started(self, mid, target, op="op_1", *, landed, claim=False, payload=AFTER):
        self.ops.begin(TASK, mid, "write", target, operation_id=op, payload=payload)
        if claim:
            out = TargetClaimService(self.storage).acquire(
                TASK, op, operation_revision=self.ops.get(TASK, op).revision, channel="probe")
            assert out["result"] == "ACQUIRED", out
        self.ops.transition(TASK, op, "STARTED")
        if landed:
            self.write(target, payload)

    def resolve(self, action, mid="m1", op="op_1", *, must=True):
        decision = ReconciliationService(self.storage).reconcile(TASK, mid, op)["DECISION"]
        out = ResolverService(self.storage).apply(
            TASK, mid, op, action, evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, op).revision, agent="probe", channel="probe")
        if must:
            assert out["accepted"], (action, out["resolution"].result_code, out["resolution"].result_reason)
        return out

    def foreign_claim(self, target, op):
        self.ops.begin(FOREIGN, "f1", "write", target, operation_id=op, payload=b"foreign\n")
        return TargetClaimService(self.storage).acquire(FOREIGN, op, operation_revision=1, channel="probe")

    def recover(self, **kw):
        return RecoveryCoordinator(self.storage).recover(TASK, **kw)

    def micro(self, mid):
        return self.tasks.open_microtask(TASK, mid).status.value

    def active_claims(self):
        out = []
        store = TargetClaimStore(self.storage)
        for path in sorted((self.storage / "target_claims").glob("**/*.json")) if (self.storage / "target_claims").exists() else []:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            active = data.get("active")
            if active:
                out.append((active.get("task_id"), active.get("operation_id"), (active.get("owner") or {}).get("kind")))
        del store
        return out

    def events(self, event_type):
        return sum(1 for e in EventCheckpointStore(self.storage).read_events(TASK) if e.event_type == event_type)

    def digest(self):
        h = hashlib.sha256()
        for path in sorted(self.storage.rglob("*")):
            rel = path.relative_to(self.storage).as_posix()
            if path.is_file():
                if rel.startswith("locks/") or rel.endswith(".lock"):
                    continue  # lock files are runtime artefacts, not state
                h.update(rel.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
        for path in sorted(self.project.rglob("*")):
            if path.is_file():
                h.update(b"W:" + path.relative_to(self.project).as_posix().encode() + hashlib.sha256(path.read_bytes()).digest())
        return h.hexdigest()[:16]


def show(label, result):
    steps = [s["action"] for s in result["performed_steps"]]
    cur = result["projection"]["position"]["current_microtask_id"]
    print(f"  {label}: state={result['state']} recovery={result['recovery_state']} current={cur} steps={steps}")
    if result["error"]:
        print(f"     error={result['error']} reason={result['reason'][:200]}")


def verdict(ok, text):
    print(f"  VERDICT: {'OK' if ok else 'DEFECT'} — {text}")


PROBES = {}


def probe(name):
    def wrap(fn):
        PROBES[fn.__name__] = (name, fn)
        return fn
    return wrap


def run_probe(key):
    name, fn = PROBES[key]
    print(f"\n### {key}: {name}")
    world = World()
    try:
        fn(world)
    except Exception:
        traceback.print_exc(limit=4)
        print("  VERDICT: ERROR — probe raised")
    finally:
        world.close()


# --------------------------------------------------------------------------------------------
@probe("READY identity drift: proof for m1, lifecycle advanced to m2 (foreign-owned target) before the fresh projection")
def n01(w):
    w.to_active("m1", "one.txt")
    w.write("two.txt", BEFORE)
    print("  foreign acquire two.txt (before recover):", w.foreign_claim("two.txt", "op_f2")["result"])
    real = RecoveryCoordinator._prove_normal_ready
    proved = []

    def hooked(self, task_id, projection):
        out = real(self, task_id, projection)
        proved.append(out["microtask_id"])
        # another actor advances the SAME task right after the proof released its locks
        w.verify("m1")
        w.to_active("m2", "two.txt")
        return out

    with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", hooked):
        result = w.recover()
    show("recover", result)
    print("  protected READY proofs actually executed for:", proved)
    try:
        RecoveryCoordinator(w.storage)._prove_normal_ready(TASK, ProjectionService(w.storage).build(TASK))
        direct = "READY_PROVED"
    except RecoveryCoordinatorBlocked as exc:
        direct = f"BLOCKED ({exc})"
    print("  direct protected proof for the returned microtask m2:", direct)
    show("recover again (no interleaving)", w.recover())
    returned = result["projection"]["position"]["current_microtask_id"]
    verdict(not (result["state"] == "READY_FOR_EXECUTION" and returned not in proved),
            "READY must only be returned for the microtask whose protected proof ran")


@probe("READY identity drift across REAL processes (barrier right after the protected proof)")
def n01b(w):
    w.to_active("m1", "one.txt")
    w.write("two.txt", BEFORE)
    print("  foreign acquire two.txt:", w.foreign_claim("two.txt", "op_f2")["result"])
    flags = Path(w.tmp.name) / "flags"
    flags.mkdir()
    child = textwrap.dedent(f"""
        import json, sys, time, pathlib
        sys.path.insert(0, {REPO!r})
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        flags = pathlib.Path({str(flags)!r})
        real = RecoveryCoordinator._prove_normal_ready
        def hooked(self, task_id, projection):
            out = real(self, task_id, projection)
            (flags / "proved").write_text(out["microtask_id"])
            deadline = time.time() + 60
            while not (flags / "go").exists():
                if time.time() > deadline:
                    raise SystemExit("barrier timeout")
                time.sleep(0.01)
            return out
        RecoveryCoordinator._prove_normal_ready = hooked
        r = RecoveryCoordinator({str(w.storage)!r}).recover({TASK!r})
        print(json.dumps({{"state": r["state"], "current": r["projection"]["position"]["current_microtask_id"]}}))
    """)
    proc = subprocess.Popen([sys.executable, "-B", "-c", child], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 60
    while not (flags / "proved").exists():
        if time.time() > deadline or proc.poll() is not None:
            print("  child did not reach the barrier:", proc.communicate())
            return
        time.sleep(0.01)
    print("  child proved:", (flags / "proved").read_text())
    w.verify("m1")                 # this (parent) process advances the lifecycle
    w.to_active("m2", "two.txt")
    (flags / "go").write_text("1")
    out, err = proc.communicate(timeout=120)
    print("  child result:", out.strip(), err.strip()[-300:])
    data = json.loads(out.strip().splitlines()[-1])
    verdict(not (data["state"] == "READY_FOR_EXECUTION" and data["current"] != "m1"),
            "two processes: READY returned for m2 while only m1 was proved and two.txt is foreign-owned")


@probe("ServerStateMachine blind write vs ABORT settlement (DONE -> VERIFIED overwrites RECOVERY_REQUIRED)")
def n02(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "DONE")
    w.resolve("ABORT")
    real_set = TaskStore.set_microtask_status
    fired = []

    def racing(self, task_id, microtask_id, status):
        if not fired and MicrotaskStatus(status) is MicrotaskStatus.VERIFIED:
            fired.append(1)
            show("recover (runs between machine read DONE and its locked write)", w.recover())
            print("  m1 after recover =", w.micro("m1"))
        return real_set(self, task_id, microtask_id, status)

    with mock.patch.object(TaskStore, "set_microtask_status", racing):
        w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="ok")
    op = w.ops.get(TASK, "op_1")
    print("  after race: m1 =", w.micro("m1"), "| op status =", op.status.value,
          "| settlement =", (op.recovery_settlement or {}).get("action"))
    show("recover#2", w.recover())
    w.to_active("m2", "two.txt")
    show("recover#3 (m2 ACTIVE)", w.recover())
    print("  closeout eligible:", CloseoutService(w.storage).inspect(TASK)["eligible"])
    verdict(w.micro("m1") != "VERIFIED",
            "ABORT-settled microtask must not end VERIFIED (pre-existing non-CAS state-machine write; RC-6 fails closed)")


@probe("ServerStateMachine blind write vs ABORT settlement across REAL processes")
def n02b(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "DONE")
    w.resolve("ABORT")
    flags = Path(w.tmp.name) / "flags"
    flags.mkdir()
    child = textwrap.dedent(f"""
        import sys, time, pathlib
        sys.path.insert(0, {REPO!r})
        from web_alarm.task_store import TaskStore
        from web_alarm.state_machine import ServerStateMachine
        flags = pathlib.Path({str(flags)!r})
        real = TaskStore.set_microtask_status
        def gated(self, task_id, microtask_id, status):
            (flags / "read_done").write_text("1")
            deadline = time.time() + 60
            while not (flags / "go").exists():
                if time.time() > deadline:
                    raise SystemExit("barrier timeout")
                time.sleep(0.01)
            return real(self, task_id, microtask_id, status)
        TaskStore.set_microtask_status = gated
        ServerStateMachine({str(w.storage)!r}).transition({TASK!r}, "m1", "VERIFIED", verification_evidence="ok")
        print("machine wrote VERIFIED")
    """)
    proc = subprocess.Popen([sys.executable, "-B", "-c", child], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 60
    while not (flags / "read_done").exists():
        if time.time() > deadline or proc.poll() is not None:
            print("  child did not reach the barrier:", proc.communicate())
            return
        time.sleep(0.01)
    show("parent recover while machine waits", w.recover())
    (flags / "go").write_text("1")
    out, err = proc.communicate(timeout=120)
    print("  child:", out.strip(), err.strip()[-200:])
    op = w.ops.get(TASK, "op_1")
    print("  final: m1 =", w.micro("m1"), "| settlement =", (op.recovery_settlement or {}).get("action"))
    show("recover after race", w.recover())
    verdict(w.micro("m1") != "VERIFIED", "same race with two real processes")


@probe("Later Resolver ABORT after a historical ADOPT settlement")
def n03(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    show("recover#1", w.recover())
    out = w.resolve("ABORT", must=False)
    print("  later ABORT on adopted op:", out["resolution"].result.value, out["resolution"].result_code)
    before = w.digest()
    r2 = w.recover()
    show("recover#2", r2)
    op = w.ops.get(TASK, "op_1")
    print("  m1 =", w.micro("m1"), "| op =", op.status.value, "| settlement =", op.recovery_settlement["action"],
          "| writes by recover#2:", before != w.digest())
    w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="ok")
    w.to_active("m2", "two.txt")
    r3 = w.recover()
    show("recover#3 (m1 VERIFIED, m2 ACTIVE)", r3)
    p = ProjectionService(w.storage).build(TASK)
    print("  projection focus:", p["recovery"]["state"], p["recovery"].get("operation_id"), "| NEXT:", p["next_safe_action"][:150])
    verdict(r2["state"] != "READY_FOR_EXECUTION" and op.recovery_settlement["action"] == "ADOPT",
            "no overwrite of ADOPT settlement, no false READY (liveness of the TASK is a separate question)")


@probe("ADOPT: crash after settlement + micro DONE, before own claim release; then normal verify + next microtask")
def n04(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True, claim=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    with mock.patch.object(TargetClaimService, "release", side_effect=Crash("die before release")):
        try:
            w.recover()
        except Crash:
            print("  crashed inside SETTLE_ADOPT before claim release")
    print("  m1 =", w.micro("m1"), "| claims:", w.active_claims())
    w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="verified while claim still held")
    w.to_active("m2", "two.txt")
    r = w.recover()
    show("fresh recover", r)
    print("  claims after:", w.active_claims(), "| m1 =", w.micro("m1"))
    verdict(r["state"] == "READY_FOR_EXECUTION" and not w.active_claims() and w.micro("m1") == "VERIFIED",
            "release-only replay, VERIFIED never moved backwards, next microtask READY")


@probe("B2 alias: foreign claim under a different spelling of the same physical file")
def n05(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("RETRY")
    show("recover#1", w.recover())
    results = {}
    for spelling, op in (("ONE.TXT", "op_fa"), ("sub/../one.txt", "op_fb")):
        try:
            results[spelling] = w.foreign_claim(spelling, op)["result"]
        except Exception as exc:  # noqa: BLE001
            results[spelling] = f"{type(exc).__name__}: {exc}"
        if results[spelling] == "ACQUIRED":
            break
    print("  foreign acquire attempts:", results)
    r = w.recover()
    show("recover#2", r)
    verdict(r["state"] != "READY_FOR_EXECUTION", "alias spelling must resolve to the same physical owner")


@probe("Foreign ROLLBACK-kind owner on the RETRY target and on a normal ACTIVE target")
def n06(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("RETRY")
    show("recover#1", w.recover())
    print("  foreign acquire:", w.foreign_claim("one.txt", "op_fr")["result"])
    store = TargetClaimStore(w.storage)
    key = physical_target_key(canonical_target(w.project, "one.txt").path)
    data = store.load(key)
    data["active"]["owner"] = {"kind": "ROLLBACK", "rollback_id": "rb_foreign"}
    store.write(data)
    r = w.recover()
    show("recover#2 (foreign rollback owner)", r)
    verdict(r["state"] != "READY_FOR_EXECUTION", "foreign rollback owner blocks READY")


@probe("B5 variants: missing snapshot / corrupt manifest / restore point changed inside or after the READY proof")
def n07(w):
    results = {}
    # a) missing snapshot binary
    w.to_active("m1", "one.txt")
    restore = w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
    snap = next(restore.glob("snapshots/*.bin"))
    data = snap.read_bytes()
    snap.unlink()
    results["missing_snapshot"] = w.recover()["state"]
    snap.write_bytes(data)
    # b) corrupt manifest.json
    manifest = restore / "manifest.json"
    original = manifest.read_bytes()
    manifest.write_bytes(b"{not json")
    try:
        results["corrupt_manifest"] = w.recover()["state"]
    except RecoveryCoordinatorError as exc:
        results["corrupt_manifest"] = f"raised {type(exc).__name__}"
    manifest.write_bytes(original)
    results["restored_baseline"] = w.recover()["state"]
    # c) corrupted between the projection and the protected proof
    real = RecoveryCoordinator._prove_normal_ready

    def corrupt_then_prove(self, task_id, projection):
        snap.write_bytes(b"tampered")
        return real(self, task_id, projection)

    with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", corrupt_then_prove):
        results["changed_before_proof"] = w.recover()["state"]
    snap.write_bytes(data)
    # d) corrupted right after the proof, before the fresh projection

    def prove_then_corrupt(self, task_id, projection):
        out = real(self, task_id, projection)
        snap.write_bytes(b"tampered")
        return out

    with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", prove_then_corrupt):
        results["changed_after_proof"] = w.recover()["state"]
    snap.write_bytes(data)
    print("  ", results)
    bad = {k: v for k, v in results.items() if k != "restored_baseline" and v == "READY_FOR_EXECUTION"}
    verdict(not bad and results["restored_baseline"] == "READY_FOR_EXECUTION", f"never READY with an invalid restore point {bad}")


@probe("B5 for RETRY: restore point corrupted inside the RETRY READY proof window")
def n07b(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("RETRY")
    show("recover#1", w.recover())
    restore = w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
    snap = next(restore.glob("snapshots/*.bin"))
    real = RecoveryCoordinator._lock_resolution_targets

    def corrupt_inside(self, stack, task_id, operation_id, resolution):
        real(self, stack, task_id, operation_id, resolution)
        snap.write_bytes(b"tampered")

    with mock.patch.object(RecoveryCoordinator, "_lock_resolution_targets", corrupt_inside):
        r = w.recover()
    show("recover#2 (snapshot tampered under the target locks)", r)
    verdict(r["state"] != "READY_FOR_EXECUTION", "restore point re-proved at the RETRY READY boundary")


@probe("ABORT with own claim: crash after RECOVERY_REQUIRED, before claim release -> replay")
def n08(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False, claim=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ABORT")
    with mock.patch.object(TargetClaimService, "release", side_effect=Crash("die before release")):
        try:
            w.recover()
        except Crash:
            print("  crashed inside SETTLE_ABORT before claim release")
    op = w.ops.get(TASK, "op_1")
    print("  m1 =", w.micro("m1"), "| op =", op.status.value, "| settlement =", op.recovery_settlement["action"],
          "| claims:", w.active_claims())
    r = w.recover()
    show("fresh recover", r)
    op = w.ops.get(TASK, "op_1")
    print("  claims after:", w.active_claims(), "| op =", op.status.value, "| m1 =", w.micro("m1"))
    print("  NEXT:", r["next_safe_action"][:200])
    r2 = w.recover()
    show("recover again", r2)
    verdict(r["state"] == "MANUAL_DECISION_REQUIRED" and not w.active_claims() and op.status.value == "STARTED"
            and r2["performed_steps"] == [], "release-only replay, forensic op status kept, idempotent")


@probe("ADOPT settlement vs concurrent normal verification in REAL processes")
def n09(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True, claim=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    flags = Path(w.tmp.name) / "flags"
    flags.mkdir()
    child = textwrap.dedent(f"""
        import json, sys, time, pathlib
        sys.path.insert(0, {REPO!r})
        from web_alarm.target_claim_service import TargetClaimService
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        flags = pathlib.Path({str(flags)!r})
        real = TargetClaimService.release
        def gated(self, *a, **kw):
            (flags / "settled").write_text("1")
            deadline = time.time() + 60
            while not (flags / "go").exists():
                if time.time() > deadline:
                    raise SystemExit("barrier timeout")
                time.sleep(0.01)
            return real(self, *a, **kw)
        TargetClaimService.release = gated
        r = RecoveryCoordinator({str(w.storage)!r}).recover({TASK!r})
        print(json.dumps({{"state": r["state"], "steps": [s["action"] for s in r["performed_steps"]], "error": r["error"]}}))
    """)
    proc = subprocess.Popen([sys.executable, "-B", "-c", child], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 60
    while not (flags / "settled").exists():
        if time.time() > deadline or proc.poll() is not None:
            print("  child did not reach the barrier:", proc.communicate())
            return
        time.sleep(0.01)
    print("  parent: m1 =", w.micro("m1"), "-> normal verification in this process")
    w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="raced verification")
    (flags / "go").write_text("1")
    out, err = proc.communicate(timeout=120)
    print("  child:", out.strip(), err.strip()[-200:])
    w.to_active("m2", "two.txt")
    r = w.recover()
    show("recover (m2 ACTIVE)", r)
    print("  claims:", w.active_claims(), "| m1 =", w.micro("m1"))
    verdict(r["state"] == "READY_FOR_EXECUTION" and w.micro("m1") == "VERIFIED" and not w.active_claims(),
            "verification racing the ADOPT settlement converges")


@probe("Rollback VERIFIED with release pending, then a newer reachable RETRY")
def n10(w):
    import web_alarm.rollback_service as rsm
    w.write("keep.txt", b"keep\n")
    w.write("one.txt", BEFORE)
    w.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit"), ("keep.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    res = w.resolve("ROLLBACK")["resolution"]
    rb = RollbackService(w.storage)
    record = rb.prepare(TASK, "m1", "op_1", res.resolution_id)["rollback"]
    with mock.patch.object(rsm.RollbackService, "_release_claims", side_effect=rsm.TargetClaimStoreError("io")):
        rb.apply(TASK, record["rollback_id"])
    s = rb.inspect(TASK, record["rollback_id"])
    print("  session:", s["status"], "released:", s["claims_released"], "| one.txt =", w.read("one.txt"))
    out = w.resolve("RETRY", must=False)
    print("  newer RETRY:", out["resolution"].result.value, out["resolution"].result_code)
    print("  projection:", ProjectionService(w.storage).build(TASK)["recovery"]["state"])
    restores = w.events("ROLLBACK_TARGET_RESTORED")
    r = w.recover()
    show("recover", r)
    s = rb.inspect(TASK, record["rollback_id"])
    print("  session after:", s["status"], "released:", s["claims_released"], "| restore events", restores, "->",
          w.events("ROLLBACK_TARGET_RESTORED"), "| claims:", w.active_claims())
    verdict(w.events("ROLLBACK_TARGET_RESTORED") == restores and s["claims_released"],
            "release-only before following the newer authority; no second restore")


@probe("READY recover is pure: repeated READY recover performs zero persistent writes")
def n11(w):
    w.to_active("m1", "one.txt")
    before = w.digest()
    r1, r2 = w.recover(), w.recover()
    show("recover#1", r1)
    show("recover#2", r2)
    after = w.digest()
    print("  storage+workspace digest:", before, "->", after)
    verdict(r1["state"] == r2["state"] == "READY_FOR_EXECUTION" and before == after, "READY proof writes nothing")


@probe("F1: after durable ABORT — is the manual boundary truthful and enforced?")
def n12(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ABORT")
    r = w.recover()
    show("recover", r)
    print("  NEXT:", r["next_safe_action"])
    for action in ("RETRY", "ROLLBACK", "ADOPT"):
        out = w.resolve(action, must=False)
        print(f"  later {action}:", out["resolution"].result.value, out["resolution"].result_code)
    try:
        w.ops.begin(TASK, "m1", "write", "one.txt", operation_id="op_new", payload=b"x\n")
        begin = "INTENT recorded"
        acq = TargetClaimService(w.storage).acquire(TASK, "op_new", operation_revision=1, channel="probe")["result"]
    except Exception as exc:  # noqa: BLE001
        begin, acq = f"{type(exc).__name__}: {exc}", "-"
    print("  new operation in RECOVERY_REQUIRED m1: begin =", begin, "| acquire =", acq)
    allowed = sorted(s.value for s in ServerStateMachine._ALLOWED.get(MicrotaskStatus.RECOVERY_REQUIRED, set()))
    print("  state-machine exits from RECOVERY_REQUIRED:", allowed)
    print("  closeout:", CloseoutService(w.storage).inspect(TASK)["eligible"])
    verdict(r["state"] == "MANUAL_DECISION_REQUIRED", "manual boundary reported (see facts for enforcement)")


def _decisions(w, ops):
    return {op: ReconciliationService(w.storage).reconcile(TASK, "m1", op)["DECISION"]["decision"] for op in ops}


def _settlements(w):
    return {o: (w.ops.get(TASK, o).recovery_settlement or {}).get("action") for o in ("op_a", "op_b")}


@probe("One microtask, sequential ops: ADOPT(op_a) settled (m1 DONE), then op_b begun in m1 and ABORTed")
def n13(w):
    w.to_active("m1", "a.txt")
    w.started("m1", "a.txt", op="op_a", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT", op="op_a")
    show("recover#1 (ADOPT op_a)", w.recover())
    print("     m1 =", w.micro("m1"))
    try:
        w.started("m1", "a.txt", op="op_b", landed=False, payload=b"after2\n")
        print("  op_b begun+STARTED in DONE m1: allowed | decision op_b:", _decisions(w, ("op_b",)))
    except Exception as exc:  # noqa: BLE001
        print("  op_b begin refused:", type(exc).__name__, exc)
        verdict(True, "sequence not reachable")
        return
    out = w.resolve("ABORT", op="op_b", must=False)
    print("  ABORT op_b:", out["resolution"].result.value, out["resolution"].result_code)
    trail = []
    for i in (2, 3):
        r = w.recover()
        show(f"recover#{i}", r)
        trail.append(w.micro("m1"))
        print("     m1 =", trail[-1], "| settlements:", _settlements(w))
    print("  m1 after each recover:", trail)
    if w.micro("m1") == "DONE":
        w.machine.transition(TASK, "m1", "VERIFIED", verification_evidence="looks DONE")
        print("  normal verify of the DONE m1 (op_b ABORT-settled inside): allowed -> m1 =", w.micro("m1"))
        c = CloseoutService(w.storage).inspect(TASK)
        print("  closeout eligible:", c["eligible"], "| blockers:", [b.get("code") for b in c.get("blockers", [])][:5])
        show("recover after verify", w.recover())
    verdict(not (r["state"] == "FAIL_CLOSED" and "budget" in r["reason"]),
            "two settlements of one microtask must not ping-pong its lifecycle until the step budget is exhausted")


@probe("One microtask, sequential ops: ABORT(op_a) settled (m1 RECOVERY_REQUIRED), then op_b begun, landed, ADOPTed")
def n13b(w):
    w.to_active("m1", "a.txt")
    w.started("m1", "a.txt", op="op_a", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ABORT", op="op_a")
    show("recover#1 (ABORT op_a)", w.recover())
    print("     m1 =", w.micro("m1"))
    w.started("m1", "a.txt", op="op_b", landed=True, payload=b"after2\n")
    print("  op_b begun+STARTED+landed in RECOVERY_REQUIRED m1 | decision op_b:", _decisions(w, ("op_b",)))
    out = w.resolve("ADOPT", op="op_b", must=False)
    print("  ADOPT op_b:", out["resolution"].result.value, out["resolution"].result_code)
    trail = []
    if out["accepted"]:
        for i in (2, 3):
            r = w.recover(max_recovery_steps=3)
            show(f"recover#{i} (budget 3)", r)
            trail.append(w.micro("m1"))
            print("     m1 =", trail[-1], "| settlements:", _settlements(w))
        print("  m1 after each recover:", trail)
    verdict("DONE" not in trail,
            "an ABORT-settled microtask must not be flipped back to DONE by a sibling ADOPT")


@probe("RC-3 enforcement of the F1 boundary: new operation + claim + mutation_boundary in RECOVERY_REQUIRED m1")
def n14(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ABORT")
    show("recover", w.recover())
    w.ops.begin(TASK, "m1", "write", "one.txt", operation_id="op_new", payload=b"x\n")
    svc = TargetClaimService(w.storage)
    print("  acquire:", svc.acquire(TASK, "op_new", operation_revision=1, channel="probe")["result"])
    try:
        with svc.mutation_boundary(TASK, "op_new", operation_revision=1) as boundary:
            print("  mutation_boundary outcome: mutation_authority =", boundary.get("mutation_authority"),
                  "| code =", boundary.get("result_code") or boundary.get("result"))
    except Exception as exc:  # noqa: BLE001
        print("  mutation_boundary refused:", type(exc).__name__, str(exc)[:200])
    print("  m1 =", w.micro("m1"))
    verdict(True, "facts only: lifecycle enforcement belongs to the future WA4-E executor")


LOCK_HOOK = """
import sys, time, pathlib
sys.path.insert(0, {repo!r})
import web_alarm.store_lock as sl
flags = pathlib.Path({flags!r})
claims_locks = pathlib.Path({locks!r}).resolve()
real_acquire = sl.InterProcessLock.acquire
state = {{"first": None}}
def acquire(self):
    real_acquire(self)
    if self.path.parent.resolve() == claims_locks and state["first"] is None:
        state["first"] = self.path.name
        (flags / {me!r}).write_text(self.path.name)
        deadline = time.time() + 30
        while not (flags / {peer!r}).exists():
            if time.time() > deadline:
                raise SystemExit("barrier timeout")
            time.sleep(0.01)
sl.InterProcessLock.acquire = acquire
t0 = time.time()
"""


@probe("Lock order: RC-6 READY proof (physical-key order) vs RC-4 apply of another TASK (hash order), REAL processes")
def n15(w):
    from web_alarm.target_claim_store import target_hash
    names = [f"t{i}.txt" for i in range(12)]
    keys = {n: physical_target_key(canonical_target(w.project, n).path) for n in names}
    pair = None
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            kx, ky = sorted([keys[x], keys[y]])
            if target_hash(kx) > target_hash(ky):
                pair = (x, y)
                break
        if pair:
            break
    x, y = pair
    print(f"  shared targets {x}, {y}: key order {sorted([x, y], key=lambda n: keys[n])}, "
          f"hash order {sorted([x, y], key=lambda n: target_hash(keys[n]))}")
    w.write(x, BEFORE)
    w.write(y, BEFORE)
    w.to_active("m1", x, y)                      # TASK: normal ACTIVE microtask on x, y
    w.machine.prepare_microtask(FOREIGN, "f1", [(x, "edit"), (y, "delete")])
    w.machine.transition(FOREIGN, "f1", "READY")
    w.machine.transition(FOREIGN, "f1", "ACTIVE")
    w.ops.begin(FOREIGN, "f1", "write", x, operation_id="op_fx", payload=AFTER)
    w.ops.transition(FOREIGN, "op_fx", "STARTED")
    w.write(x, AFTER)
    w.machine.transition(FOREIGN, "f1", "UNKNOWN_AFTER_DISCONNECT")
    decision = ReconciliationService(w.storage).reconcile(FOREIGN, "f1", "op_fx")["DECISION"]
    res = ResolverService(w.storage).apply(
        FOREIGN, "f1", "op_fx", "ROLLBACK", evidence_fingerprint=decision["evidence_fingerprint"],
        operation_revision=w.ops.get(FOREIGN, "op_fx").revision)["resolution"]
    rid = RollbackService(w.storage).prepare(FOREIGN, "f1", "op_fx", res.resolution_id)["rollback"]["rollback_id"]
    flags = Path(w.tmp.name) / "flags"
    flags.mkdir()
    locks = str(TargetClaimStore(w.storage).locks)
    coordinator = LOCK_HOOK.format(repo=REPO, flags=str(flags), locks=locks, me="A1", peer="B1") + textwrap.dedent(f"""
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        r = RecoveryCoordinator({str(w.storage)!r}).recover({TASK!r})
        print("A coordinator:", r["state"], "|", (r["reason"] or "")[:160], "| %.1fs" % (time.time() - t0))
    """)
    rollback = LOCK_HOOK.format(repo=REPO, flags=str(flags), locks=locks, me="B1", peer="A1") + textwrap.dedent(f"""
        from web_alarm.rollback_service import RollbackService
        try:
            out = RollbackService({str(w.storage)!r}).apply({FOREIGN!r}, {rid!r})
            print("B rc4 apply:", out["result"], out.get("result_code"), "| %.1fs" % (time.time() - t0))
        except Exception as exc:
            print("B rc4 apply raised:", type(exc).__name__, str(exc)[:160], "| %.1fs" % (time.time() - t0))
    """)
    a = subprocess.Popen([sys.executable, "-B", "-c", coordinator], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    b = subprocess.Popen([sys.executable, "-B", "-c", rollback], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out_a, err_a = a.communicate(timeout=120)
    out_b, err_b = b.communicate(timeout=120)
    print("  ", out_a.strip(), err_a.strip()[-200:])
    print("  ", out_b.strip(), err_b.strip()[-200:])
    print("  first locks taken: A ->", (flags / "A1").read_text() if (flags / "A1").exists() else None,
          "| B ->", (flags / "B1").read_text() if (flags / "B1").exists() else None)
    s = RollbackService(w.storage).inspect(FOREIGN, rid)
    print("  foreign rollback after:", s["status"], "| x =", w.read(x), "| claims:", w.active_claims())
    deadlocked = "timeout" in (out_a + out_b).lower()
    verdict(not deadlocked, "opposite target-lock orders between RC-6 and RC-4 deadlock until lock timeout")


def _rollback_world(w):
    """m1 declares a.txt edit, b.txt delete, c.txt delete; a landed, b deleted -> PARTIAL_KNOWN_STATE -> ROLLBACK."""
    for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
        w.write(name, data)
    w.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=b"a-after\n")
    w.ops.transition(TASK, "op_1", "STARTED")
    w.write("a.txt", b"a-after\n")
    (w.project / "b.txt").unlink()
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    res = w.resolve("ROLLBACK")["resolution"]
    rb = RollbackService(w.storage)
    rid = rb.prepare(TASK, "m1", "op_1", res.resolution_id)["rollback"]["rollback_id"]
    return rb, rid


@probe("F2: PARTIAL via external drift after own restore -> recover keeps ownership; later ABORT too")
def n16(w):
    rb, rid = _rollback_world(w)
    import web_alarm.rollback_service as rsm
    real_event = rsm.RollbackService._event
    done = []

    def drift_after_first_restore(self, record, event_type, payload):
        real_event(self, record, event_type, payload)
        if event_type == "ROLLBACK_TARGET_RESTORED" and not done:
            done.append(1)
            # a non-compliant external writer (editor / git) touches a still-PRESERVED target
            pending = [t["source_path"] for t in record["targets"] if t["status"] == "PRESERVED"]
            if pending:
                path = w.project / pending[0]
                path.write_bytes(b"external\n")

    with mock.patch.object(rsm.RollbackService, "_event", drift_after_first_restore):
        out = rb.apply(TASK, rid)
    s = rb.inspect(TASK, rid)
    print("  RC-4:", out["result"], "| session:", s["status"], [t["status"] for t in s["targets"]], "| claims:", len(w.active_claims()))
    r1 = w.recover()
    show("recover (no new action)", r1)
    claims1 = len(w.active_claims())
    abort = w.resolve("ABORT", must=False)
    print("  later ABORT:", abort["resolution"].result.value)
    r2 = w.recover()
    show("recover (after ABORT)", r2)
    s = rb.inspect(TASK, rid)
    print("  session:", s["status"], "| claims:", claims1, "->", len(w.active_claims()),
          "| op settlement:", (w.ops.get(TASK, "op_1").recovery_settlement or {}).get("action"))
    verdict(s["status"] in ("PARTIAL", "FAILED") and claims1 > 0 and len(w.active_claims()) == claims1
            and r1["state"] == r2["state"] == "RECOVERY_BLOCKED", "no auto close/release of an unsafe final rollback")


@probe("B4: real os._exit after a target is persisted DRIFTED, before RC-4 finalize (own hook point)")
def n17(w):
    rb, rid = _rollback_world(w)
    flags = Path(w.tmp.name)
    child = textwrap.dedent(f"""
        import os, sys
        sys.path.insert(0, {REPO!r})
        import web_alarm.rollback_service as rs
        real_finalize = rs.RollbackService._finalize
        def finalize(self, record, root):
            if any(t["status"] == "DRIFTED" for t in record["targets"]) and record["status"] == "APPLYING":
                os._exit(23)   # DRIFTED already persisted by _stop / _prove_current; finalize never runs
            return real_finalize(self, record, root)
        rs.RollbackService._finalize = finalize
        real_write = rs._write_restored_bytes
        calls = []
        def write(path, data):
            calls.append(1)
            real_write(path, data)
            if len(calls) == 1:
                # after the first restore, an external writer changes the delete-target that was not yet touched
                for name in ("b.txt", "c.txt"):
                    p = os.path.join({str(w.project)!r}, name)
                    if os.path.exists(p):
                        open(p, "wb").write(b"external\\n")
                        break
        rs._write_restored_bytes = write
        rs.RollbackService({str(w.storage)!r}).apply({TASK!r}, {rid!r})
        print("no crash")
    """)
    proc = subprocess.run([sys.executable, "-B", "-c", child], capture_output=True, text=True)
    s = rb.inspect(TASK, rid)
    print("  crash exit:", proc.returncode, proc.stdout.strip(), "| session:", s["status"], [t["status"] for t in s["targets"]])
    p = ProjectionService(w.storage).build(TASK)
    print("  projection recovery:", p["recovery"]["state"])
    restores = w.events("ROLLBACK_TARGET_RESTORED")
    r = w.recover()
    show("fresh recover", r)
    s = rb.inspect(TASK, rid)
    print("  session after:", s["status"], [t["status"] for t in s["targets"]], "| restore events", restores, "->",
          w.events("ROLLBACK_TARGET_RESTORED"), "| claims:", len(w.active_claims()))
    verdict(p["recovery"]["state"] != "ROLLBACK_STALE_OPEN" and s["status"] in ("PARTIAL", "FAILED")
            and w.events("ROLLBACK_TARGET_RESTORED") == restores and len(w.active_claims()) > 0
            and r["state"] == "RECOVERY_BLOCKED", "RC-4 finalizes the persisted outcome once, ownership kept")


@probe("RC-4 apply returns BLOCKED for an own-effect session (restore point broken mid-rollback): does recover stop?")
def n18(w):
    rb, rid = _rollback_world(w)
    import web_alarm.rollback_service as rsm
    real_event = rsm.RollbackService._event

    def crash_after_first(self, record, event_type, payload):
        real_event(self, record, event_type, payload)
        if event_type == "ROLLBACK_TARGET_RESTORED":
            raise Crash("die after the first own restore")

    with mock.patch.object(rsm.RollbackService, "_event", crash_after_first):
        try:
            rb.apply(TASK, rid)
        except Crash:
            pass
    s = rb.inspect(TASK, rid)
    print("  after crash:", s["status"], [t["status"] for t in s["targets"]])
    restore = w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point"
    for snap in restore.glob("snapshots/*.bin"):
        snap.write_bytes(b"tampered")  # restore point no longer verifiable
    blocked_before = w.events("ROLLBACK_BLOCKED")
    before = w.digest()
    r = w.recover()
    show("recover", r)
    print("  ROLLBACK_BLOCKED events:", blocked_before, "->", w.events("ROLLBACK_BLOCKED"),
          "| step outcomes:", [s_["outcome"].get("result_code") for s_ in r["performed_steps"]][:3], "...",
          "| writes:", before != w.digest())
    r2 = w.recover()
    show("recover again", r2)
    print("  ROLLBACK_BLOCKED events now:", w.events("ROLLBACK_BLOCKED"))
    verdict(len(r["performed_steps"]) <= 1, "a BLOCKED RC-4 outcome should stop the loop instead of exhausting the budget")


@probe("B3 for ROLLBACK: accepted ROLLBACK for an operation of an already VERIFIED microtask while m2 is ACTIVE")
def n19(w):
    for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
        w.write(name, data)
    w.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=b"a-after\n")
    w.ops.transition(TASK, "op_1", "STARTED")
    w.write("a.txt", b"a-after\n")
    (w.project / "b.txt").unlink()
    w.verify("m1")                                   # m1 VERIFIED although op_1 was never settled
    w.to_active("m2", "two.txt")
    w.write("two.txt", b"m2 work\n")
    print("  m1 =", w.micro("m1"), "| m2 =", w.micro("m2"))
    decision = ReconciliationService(w.storage).reconcile(TASK, "m1", "op_1")["DECISION"]
    print("  reconciliation for op_1:", decision["decision"], decision.get("reason_code"))
    out = w.resolve("ROLLBACK", must=False)
    print("  ROLLBACK op_1:", out["resolution"].result.value, out["resolution"].result_code)
    if not out["accepted"]:
        verdict(True, "not reachable: Resolver refuses ROLLBACK for the historical operation")
        return
    files_before = {n: w.read(n) for n in ("a.txt", "b.txt", "two.txt")}
    r = w.recover()
    show("recover", r)
    files_after = {n: w.read(n) for n in ("a.txt", "b.txt", "two.txt")}
    print("  workspace before:", files_before)
    print("  workspace after: ", files_after)
    print("  m1 =", w.micro("m1"), "| m2 =", w.micro("m2"))
    verdict(files_before == files_after and w.micro("m1") == "VERIFIED",
            "a VERIFIED microtask must never be rolled back because of its historical operation (invariant 5)")


if __name__ == "__main__":
    keys = sys.argv[1:] or list(PROBES)
    for key in keys:
        run_probe(key)
