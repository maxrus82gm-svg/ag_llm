"""Repair #2A probe b04 re-staged for WA-014: two concurrent activations of one READY microtask.

The original b04 (TASK_CLAUDE-WA-009_RC6_REPAIR2/repair2a/probes) parks both children inside
TaskStore.compare_and_set_microtask_status and waits until BOTH are parked. Since WA-014 that call
runs inside the activation's TASK-locked section (decision + CAS), so the second child can never
reach the barrier: it waits for the TASK lock held by the parked first child until its lock
timeout (a harness deadlock; no production path waits for another process while holding a lock).

Same intent, barrier at the new decision boundary: both children have read READY (the unlocked
checks of transition are done, ``current`` = READY) and are parked right before
ServerStateMachine._admit_active, i.e. before the TASK lock; then both are released.
Invariant (as b04): exactly one activation applies, m1 is ACTIVE, the plan points at m1.
Temp storage only. Run from the repository root: python -B <this file> [rounds]
"""
import json
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

REPO = Path.cwd()
sys.path.insert(0, str(REPO))

from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_v"
CHILD = """
    import json, pathlib, time
    from web_alarm.state_machine import ServerStateMachine, TransitionRejected
    flags = pathlib.Path({flags!r})
    real = ServerStateMachine._admit_active
    def gated(self, *a, **kw):
        (flags / {read!r}).write_text("1")  # READY observed, before the TASK lock
        deadline = time.time() + 60
        while not (flags / "go").exists():
            if time.time() > deadline:
                raise SystemExit("barrier timeout")
            time.sleep(0.01)
        return real(self, *a, **kw)
    ServerStateMachine._admit_active = gated
    try:
        ServerStateMachine({storage!r}).transition({task!r}, "m1", "ACTIVE")
        print(json.dumps({{"result": "APPLIED"}}))
    except TransitionRejected as exc:
        print(json.dumps({{"result": "REJECTED", "reason": exc.reason[:160]}}))
"""


def one_round():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, flags = Path(tmp) / "state", Path(tmp) / "project", Path(tmp) / "flags"
        project.mkdir()
        flags.mkdir()
        (project / "one.txt").write_bytes(b"x\n")
        WorkspaceRegistry(storage).register("V", project, workspace_id="ws_v")
        tasks = TaskStore(storage)
        tasks.create_task("ws_v", "V", "RAW", "v", task_id=TASK)
        tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
        machine = ServerStateMachine(storage)
        machine.prepare_microtask(TASK, "m1", [("one.txt", "edit")])
        machine.transition(TASK, "m1", "READY")
        children = [subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(CHILD.format(
            flags=str(flags), read=read, storage=str(storage), task=TASK))], cwd=REPO,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for read in ("x_read", "y_read")]
        try:
            deadline = time.time() + 60
            while not ((flags / "x_read").exists() and (flags / "y_read").exists()):
                if time.time() > deadline or any(c.poll() is not None for c in children):
                    raise RuntimeError([c.communicate() for c in children])
                time.sleep(0.01)
            (flags / "go").write_text("1")
            results = []
            for c in children:
                out, err = c.communicate(timeout=120)
                results.append(json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": err[-200:]})
        finally:
            (flags / "go").write_text("1")
            for c in children:
                if c.poll() is None:
                    c.kill()
        micro = tasks.open_microtask(TASK, "m1").status.value
        current = tasks.open_plan(TASK).current_microtask_id
        ok = sorted(r.get("result") for r in results) == ["APPLIED", "REJECTED"] and micro == "ACTIVE" and current == "m1"
        return ok, results, micro, current


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    good = 0
    for n in range(rounds):
        ok, results, micro, current = one_round()
        good += ok
        print(f"round {n}: {[r.get('result') for r in results]} | m1={micro} | plan current={current} | "
              f"{'OK' if ok else 'VIOLATION'} | rejected reason: {[r.get('reason', '')[:110] for r in results if r.get('result') == 'REJECTED']}")
    print(f"b04 re-staged: {good}/{rounds} OK — exactly one activation applies")
    sys.exit(0 if good == rounds else 1)
