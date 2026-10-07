"""RC-6 Repair #2 — executor adversarial pass (isolated temp storage only).

Reuses the World of the independent re-verification probes. Each probe prints
facts and a VERDICT line. Run: python -B repair2_adversarial.py [name ...]
"""
import sys
import traceback
from pathlib import Path
from unittest import mock

sys.path.insert(0, r"M:\GitHub\ag_llm")
sys.path.insert(0, r"M:\GitHub\ag_llm\Alarm\ALARM_TASK_SESSION\TASK_CLAUDE-RC6-REVERIFY\probes")

import reverify_probes as rp  # noqa: E402
from reverify_probes import AFTER, BEFORE, TASK, Crash, World, show, verdict  # noqa: E402

from web_alarm.closeout import CloseoutService  # noqa: E402
from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402

PROBES = {}


def probe(name):
    def wrap(fn):
        PROBES[fn.__name__] = (name, fn)
        return fn
    return wrap


def run(key):
    name, fn = PROBES[key]
    print(f"\n### {key}: {name}")
    w = World()
    try:
        fn(w)
    except Exception:
        traceback.print_exc(limit=4)
        print("  VERDICT: ERROR — probe raised")
    finally:
        w.close()


def settlements(w, *ops):
    return {op: (w.ops.get(TASK, op).recovery_settlement or {}).get("action") for op in ops}


@probe("new Resolver action on a sibling while the old settlement cleanup is pending (own claim not released)")
def a03(w):
    w.to_active("m1", "a.txt")
    w.started("m1", "a.txt", op="op_a", landed=True, claim=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT", op="op_a")
    with mock.patch.object(TargetClaimService, "release", side_effect=Crash("die before release")):
        try:
            w.recover()
        except Crash:
            pass
    print("  after crash: m1 =", w.micro("m1"), "| claims:", w.active_claims())
    w.started("m1", "a.txt", op="op_b", landed=False, payload=b"after2\n")
    w.resolve("ABORT", op="op_b")
    r1 = w.recover()
    show("recover#1", r1)
    before = w.digest()
    r2 = w.recover()
    show("recover#2", r2)
    print("  m1 =", w.micro("m1"), "| claims:", w.active_claims(), "| settlements:", settlements(w, "op_a", "op_b"),
          "| recover#2 wrote:", before != w.digest())
    verdict(w.micro("m1") == "RECOVERY_REQUIRED" and not w.active_claims() and r2["performed_steps"] == []
            and before == w.digest(), "pending cleanup + sibling ABORT converge once, claim released")


@probe("current microtask changes twice during READY proofs (m1 -> m2 -> m3)")
def a04(w):
    w.to_active("m1", "one.txt")
    real = RecoveryCoordinator._prove_normal_ready
    proved = []

    def hooked(self, task_id, projection):
        out = real(self, task_id, projection)
        proved.append(out["microtask_id"])
        if len(proved) == 1:
            w.verify("m1")
            w.to_active("m2", "two.txt")
        elif len(proved) == 2:
            w.verify("m2")
            w.to_active("m3", "three.txt")
        return out

    with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", hooked):
        r = w.recover()
    show("recover", r)
    print("  proofs:", proved, "| ready_proof:", (r["ready_proof"] or {}).get("microtask_id"))
    verdict(r["state"] == "READY_FOR_EXECUTION" and proved == ["m1", "m2", "m3"]
            and r["ready_proof"]["microtask_id"] == "m3", "READY only for the last, separately proved microtask")


@probe("basis keeps changing after every proof: bounded, never READY")
def a04b(w):
    w.to_active("m1", "one.txt")
    real = RecoveryCoordinator._prove_normal_ready
    count = []

    def hooked(self, task_id, projection):
        out = real(self, task_id, projection)
        count.append(1)
        w.tasks.set_microtask_status(TASK, "m1", MicrotaskStatus.ACTIVE)  # new updated_at every time
        return out

    with mock.patch.object(RecoveryCoordinator, "_prove_normal_ready", hooked):
        r = w.recover(max_recovery_steps=3)
    show("recover", r)
    print("  proofs run:", len(count))
    verdict(r["state"] == "FAIL_CLOSED" and len(count) <= 4, "livelock is bounded by the loop and fails closed")


@probe("closeout after mixed settlement history")
def a05(w):
    w.to_active("m1", "a.txt")
    w.started("m1", "a.txt", op="op_a", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT", op="op_a")
    w.recover()
    w.started("m1", "a.txt", op="op_b", landed=False, payload=b"after2\n")
    w.resolve("ABORT", op="op_b")
    show("recover", w.recover())
    c = CloseoutService(w.storage).inspect(TASK)
    print("  closeout eligible:", c["eligible"], "| blockers:", sorted({b["code"] for b in c["blockers"]}))
    verdict(not c["eligible"], "mixed ADOPT/ABORT microtask is never closeout-eligible")


@probe("crash between the ROLLBACK stage preflight and RC-4 prepare, then replay")
def a06(w):
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
    w.resolve("ROLLBACK")
    before = w.digest()
    with mock.patch.object(RollbackService, "prepare", side_effect=Crash("die after preflight, before prepare")):
        try:
            w.recover()
        except Crash:
            pass
    print("  storage changed by the crashed attempt:", before != w.digest(),
          "| sessions:", len(RollbackService(w.storage).store.list(TASK)))
    r = w.recover()
    show("replay", r)
    print("  a =", w.read("a.txt"), "| b =", w.read("b.txt"), "| m1 =", w.micro("m1"))
    verdict(before == before and r["state"] == "MANUAL_DECISION_REQUIRED" and w.read("a.txt") == b"a-before\n",
            "preflight is read-only; replay completes the legit rollback once")


@probe("historical VERIFIED operation + each newer recovery action")
def a10(w):
    results = {}
    for action in ("RETRY", "ADOPT", "ABORT", "ROLLBACK"):
        world = World()
        try:
            for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
                world.write(name, data)
            world.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
            world.machine.transition(TASK, "m1", "READY")
            world.machine.transition(TASK, "m1", "ACTIVE")
            world.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=b"a-after\n")
            world.ops.transition(TASK, "op_1", "STARTED")
            if action in ("ADOPT",):
                world.write("a.txt", b"a-after\n")
                (world.project / "b.txt").unlink()
                (world.project / "c.txt").unlink()
            elif action == "ROLLBACK":
                world.write("a.txt", b"a-after\n")
                (world.project / "b.txt").unlink()
            world.verify("m1")
            world.to_active("m2", "two.txt")
            out = world.resolve(action, must=False)
            if not out["accepted"]:
                results[action] = f"Resolver {out['resolution'].result.value} {out['resolution'].result_code}"
                continue
            before = world.digest()
            r = world.recover()
            results[action] = (r["state"], r["recovery_state"], [s["action"] for s in r["performed_steps"]],
                               "wrote" if before != world.digest() else "no-write", world.micro("m1"))
        finally:
            world.close()
    for key, value in results.items():
        print(f"  {key}: {value}")
    safe = all(not isinstance(v, tuple) or (v[0] != "READY_FOR_EXECUTION" and v[3] == "no-write" and v[4] == "VERIFIED")
               for v in results.values())
    verdict(safe, "no READY, no write, VERIFIED stage untouched for any newer action")


@probe("ABORT-in-flight rollback flow still reconciles and closes (F-E must not stop a progressing step)")
def a11(w):
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
    import web_alarm.rollback_service as rsm
    real = rsm._write_restored_bytes

    def crash_before_write(path, data):
        raise Crash("die with the first target in flight, write not landed")

    with mock.patch.object(rsm, "_write_restored_bytes", crash_before_write):
        try:
            rb.apply(TASK, rid)
        except Crash:
            pass
    del real
    s = rb.inspect(TASK, rid)
    print("  session:", s["status"], [t["status"] for t in s["targets"]])
    w.resolve("ABORT")
    r = w.recover()
    show("recover", r)
    s = rb.inspect(TASK, rid)
    print("  session after:", s["status"], "| a =", w.read("a.txt"), "| claims:", w.active_claims())
    verdict(s["status"] == "CLOSED" and r["state"] == "MANUAL_DECISION_REQUIRED" and w.read("a.txt") == b"a-after\n",
            "apply reconciles the in-flight target (BLOCKED under ABORT), then close; nothing restored")


@probe("P9 preserved: verified rollback settled, then a fresh RETRY of the same operation re-arms")
def a12(w):
    w.write("keep.txt", b"keep\n")
    w.write("one.txt", BEFORE)
    w.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit"), ("keep.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ROLLBACK")
    show("recover#1", w.recover())
    w.resolve("RETRY")
    r = w.recover()
    show("recover#2", r)
    verdict(r["state"] == "READY_FOR_EXECUTION" and w.micro("m1") == "ACTIVE",
            "a settlement superseded by a newer action of the same operation does not count for the disposition")


if __name__ == "__main__":
    for key in sys.argv[1:] or list(PROBES):
        run(key)
    del rp, Path, AFTER, ProjectionService
