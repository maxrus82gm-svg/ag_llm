"""Contention probe: RC-6 recover x direct RC-4 prepare/apply on an EXECUTED (ACTIVE) stage.

Temp storage only. Run from the repository root: python -B <this file> <code_root> [rounds]
``code_root`` holds the web_alarm package to test (the working tree, or a commit-165 copy),
so a one-off FAIL_CLOSED of a concurrent recover call can be attributed (new vs pre-existing).
Both rollback paths are legitimate here (the microtask was ACTIVE); the probe only records
what each concurrent recover call reports and checks the final state.
"""
import json
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

CODE = Path(sys.argv[1]).resolve()
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
sys.path.insert(0, str(CODE))

from web_alarm.models import MicrotaskStatus, OperationStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_contention"
CHILD = """
    import json, pathlib, time
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    from web_alarm.rollback_service import RollbackService
    storage, task, role, flags = {storage!r}, {task!r}, {role!r}, pathlib.Path({flags!r})
    (flags / ("ready_" + role)).write_text("1")
    while not (flags / "go").exists():
        time.sleep(0.0005)
    try:
        if role == "rc4":
            rb = RollbackService(storage)
            p = rb.prepare(task, "m1", "op_2", {resolution_id!r})
            out = {{"prepare": p["result"], "code": p["result_code"]}}
            if p["rollback"] is not None:
                a = rb.apply(task, p["rollback"]["rollback_id"])
                out.update(apply=a["result"], apply_code=a["result_code"])
        else:
            r = RecoveryCoordinator(storage).recover(task)
            out = {{"state": r["state"], "steps": [s["action"] for s in r["performed_steps"]], "reason": r["reason"][:260]}}
    except Exception as exc:
        out = {{"error": type(exc).__name__, "message": str(exc)[:300]}}
    print(json.dumps(out))
"""


def round_once(tmp):
    storage, project, flags = Path(tmp) / "state", Path(tmp) / "project", Path(tmp) / "flags"
    project.mkdir()
    flags.mkdir()
    (project / "a.txt").write_bytes(b"before\n")
    (project / "keep.txt").write_bytes(b"keep\n")
    WorkspaceRegistry(storage).register("C", project, workspace_id="ws_c")
    TaskStore(storage).create_task("ws_c", "C", "RAW", "c", task_id=TASK)
    TaskStore(storage).create_microtask(TASK, "M1", "m1", microtask_id="m1")
    sm = ServerStateMachine(storage)
    sm.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("keep.txt", "delete")])
    sm.transition(TASK, "m1", MicrotaskStatus.READY)
    sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
    ops = OperationStore(storage)
    ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_1", payload=b"keep-v2\n")
    ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_2", payload=b"after\n")
    ops.transition(TASK, "op_2", OperationStatus.STARTED)
    (project / "a.txt").write_bytes(b"after\n")
    resolutions = {}
    for op, action in (("op_1", "ABORT"), ("op_2", "ROLLBACK")):
        decision = ReconciliationService(storage).reconcile(TASK, "m1", op)["DECISION"]
        resolutions[op] = ResolverService(storage).apply(
            TASK, "m1", op, action, evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=ops.get(TASK, op).revision)["resolution"]
    roles = ("recover_a", "rc4", "recover_b")
    children = [subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(CHILD.format(
        storage=str(storage), task=TASK, role=r, flags=str(flags), resolution_id=resolutions["op_2"].resolution_id))],
        cwd=CODE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for r in roles]
    out = {}
    try:
        while not all((flags / f"ready_{r}").exists() for r in roles):
            time.sleep(0.005)
        (flags / "go").write_text("1")
        for r, c in zip(roles, children):
            o, e = c.communicate(timeout=180)
            out[r] = json.loads(o.strip().splitlines()[-1]) if o.strip() else {"error": e[-300:]}
    finally:
        (flags / "go").write_text("1")
        for c in children:
            if c.poll() is None:
                c.kill()
    final = RecoveryCoordinator(storage).recover(TASK)
    return out, final, (project / "a.txt").read_bytes()


counts, fails = {}, []
for n in range(ROUNDS):
    with tempfile.TemporaryDirectory() as tmp:
        out, final, a = round_once(tmp)
    for r in ("recover_a", "recover_b"):
        st = out[r].get("state", out[r].get("error"))
        counts[st] = counts.get(st, 0) + 1
        if st == "FAIL_CLOSED":
            fails.append(f"round {n} {r}: {out[r]['reason']} | rc4={out['rc4']}")
    counts["final:" + final["state"]] = counts.get("final:" + final["state"], 0) + 1
    counts["a.txt restored" if a == b"before\n" else "a.txt NOT restored"] = counts.get(
        "a.txt restored" if a == b"before\n" else "a.txt NOT restored", 0) + 1
print(f"code root: {CODE}")
print(f"rounds={ROUNDS} counts={counts}")
for f in fails:
    print("  ", f)
