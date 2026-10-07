"""Repair #2A — executor adversarial pass (isolated temp storage, real processes where it matters)."""
import json
import subprocess
import sys
import textwrap
import time
import traceback
from pathlib import Path
from unittest import mock

REPO = r"M:\GitHub\ag_llm"
sys.path.insert(0, REPO)
sys.path.insert(0, r"M:\GitHub\ag_llm\Alarm\ALARM_TASK_SESSION\TASK_CLAUDE-RC6-REVERIFY\probes")

from reverify_probes import TASK, World, show, verdict  # noqa: E402

from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.state_machine import TransitionRejected  # noqa: E402

SM_CHILD = """
import json, pathlib, sys, time
sys.path.insert(0, {repo!r})
from web_alarm.task_store import TaskStore
from web_alarm.state_machine import ServerStateMachine, TransitionRejected
flags = pathlib.Path({flags!r})
real = TaskStore.compare_and_set_microtask_status
def gated(self, *a, **kw):
    (flags / {read!r}).write_text("1")
    deadline = time.time() + 60
    while not (flags / {go!r}).exists():
        if time.time() > deadline:
            raise SystemExit("barrier timeout")
        time.sleep(0.01)
    return real(self, *a, **kw)
TaskStore.compare_and_set_microtask_status = gated
try:
    ServerStateMachine({storage!r}).transition({task!r}, {micro!r}, {target!r}, verification_evidence="x")
    print(json.dumps({{"result": "APPLIED"}}))
except TransitionRejected as exc:
    print(json.dumps({{"result": "REJECTED", "reason": exc.reason}}))
"""


def sm_child(w, target, read, go, micro="m1"):
    flags = Path(w.tmp.name) / "flags"
    flags.mkdir(exist_ok=True)
    script = SM_CHILD.format(repo=REPO, flags=str(flags), read=read, go=go, storage=str(w.storage),
                             task=TASK, micro=micro, target=target)
    return subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(script)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True), flags


def wait(flags, name, proc):
    deadline = time.time() + 60
    while not (flags / name).exists():
        if proc.poll() is not None or time.time() > deadline:
            raise RuntimeError(f"child did not reach {name}: {proc.communicate()}")
        time.sleep(0.01)


def finish(proc):
    out, err = proc.communicate(timeout=120)
    return json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": err[-300:]}


PROBES = {}


def probe(name):
    def wrap(fn):
        PROBES[fn.__name__] = (name, fn)
        return fn
    return wrap


@probe("RETRY re-arm vs a stale manual UNKNOWN -> RECOVERY_REQUIRED decided before the re-arm (real processes)")
def b01(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=False)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("RETRY")
    child, flags = sm_child(w, "RECOVERY_REQUIRED", "read", "go")
    wait(flags, "read", child)          # a human decided on UNKNOWN
    r = w.recover()                     # RC-6 re-arms to ACTIVE meanwhile
    show("recover", r)
    (flags / "go").write_text("1")
    res = finish(child)
    print("  stale manual transition:", res, "| m1 =", w.micro("m1"))
    show("recover again", w.recover())
    verdict(res.get("result") == "REJECTED" and w.micro("m1") == "ACTIVE",
            "a manual decision taken on UNKNOWN never overwrites the re-armed ACTIVE")


@probe("ADOPT settlement vs a stale UNKNOWN -> RECOVERY_REQUIRED (real processes)")
def b02(w):
    w.to_active("m1", "one.txt")
    w.started("m1", "one.txt", landed=True)
    w.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
    w.resolve("ADOPT")
    child, flags = sm_child(w, "RECOVERY_REQUIRED", "read", "go")
    wait(flags, "read", child)
    r = w.recover()
    show("recover", r)
    (flags / "go").write_text("1")
    res = finish(child)
    print("  stale manual transition:", res, "| m1 =", w.micro("m1"))
    r2 = w.recover()
    show("recover again", r2)
    verdict(res.get("result") == "REJECTED" and w.micro("m1") == "DONE" and r2["performed_steps"] == [],
            "ADOPT's DONE is not overwritten; no FINISH_SETTLEMENT churn afterwards")


@probe("destructive apply refused by RC-4 after the RECOVERY_REQUIRED mark: nothing restored, manual, one attempt")
def b03(w):
    for name, data in (("a.txt", b"a-before\n"), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
        w.write(name, data)
    w.machine.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
    w.machine.transition(TASK, "m1", "READY")
    w.machine.transition(TASK, "m1", "ACTIVE")
    w.ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=b"a-after\n")
    w.ops.transition(TASK, "op_1", "STARTED")
    w.write("a.txt", b"a-after\n")
    (w.project / "b.txt").unlink()
    w.machine.transition(TASK, "m1", "DONE")
    res = w.resolve("ROLLBACK")["resolution"]
    rb = RollbackService(w.storage)
    rid = rb.prepare(TASK, "m1", "op_1", res.resolution_id)["rollback"]["rollback_id"]
    import web_alarm.rollback_service as rsm
    real_event = rsm.RollbackService._event

    def crash_after_first(self, record, event_type, payload):
        real_event(self, record, event_type, payload)
        if event_type == "ROLLBACK_TARGET_RESTORED":
            raise KeyboardInterrupt("crash after the first own restore")

    with mock.patch.object(rsm.RollbackService, "_event", crash_after_first):
        try:
            rb.apply(TASK, rid)
        except KeyboardInterrupt:
            pass
    print("  after crash: m1 =", w.micro("m1"), "| session:", rb.inspect(TASK, rid)["status"])
    for snap in (w.tasks.task_directory(TASK) / "microtasks" / "m1" / "restore_point").glob("snapshots/*.bin"):
        snap.write_bytes(b"tampered")  # RC-4 refuses to continue: RESTORE_POINT_INVALID
    restores = w.events("ROLLBACK_TARGET_RESTORED")
    r = w.recover()
    show("recover", r)
    print("  m1 =", w.micro("m1"), "| restore events", restores, "->", w.events("ROLLBACK_TARGET_RESTORED"))
    verdict(r["state"] == "RECOVERY_BLOCKED" and w.micro("m1") == "RECOVERY_REQUIRED"
            and w.events("ROLLBACK_TARGET_RESTORED") == restores and len(r["performed_steps"]) == 1,
            "stage put at the manual boundary, no further restore, the refused apply is not repeated")


@probe("two concurrent activations of the same READY microtask (real processes)")
def b04(w):
    w.write("one.txt", b"x\n")
    w.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit")])
    w.machine.transition(TASK, "m1", "READY")
    first, flags = sm_child(w, "ACTIVE", "x_read", "go")
    second, _ = sm_child(w, "ACTIVE", "y_read", "go")
    wait(flags, "x_read", first)
    wait(flags, "y_read", second)
    (flags / "go").write_text("1")
    results = sorted([finish(first).get("result"), finish(second).get("result")])
    plan = w.tasks.open_plan(TASK)
    print("  results:", results, "| m1 =", w.micro("m1"), "| plan current:", plan.current_microtask_id)
    verdict(results == ["APPLIED", "REJECTED"] and w.micro("m1") == "ACTIVE" and plan.current_microtask_id == "m1",
            "exactly one activation applies")


@probe("in-process stale request via expected_status is refused without any status write")
def b05(w):
    w.to_active("m1", "one.txt")
    before = (w.tasks.task_directory(TASK) / "microtasks" / "m1.json").read_bytes()
    try:
        w.machine.transition(TASK, "m1", "DONE", expected_status="READY")
        outcome = "APPLIED"
    except TransitionRejected as exc:
        outcome = f"REJECTED ({exc.reason[:80]})"
    after = (w.tasks.task_directory(TASK) / "microtasks" / "m1.json").read_bytes()
    print("  ", outcome, "| microtask record unchanged:", before == after)
    verdict(outcome.startswith("REJECTED") and before == after, "stale basis refused, nothing written")


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


if __name__ == "__main__":
    for key in sys.argv[1:] or list(PROBES):
        run(key)
    del mock
