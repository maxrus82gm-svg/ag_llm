"""CLAUDE-WA-014 adversarial race (temp storage only, real processes).

Run from the repository root: python -B <this file> [rounds]

Per round: m1 READY with a verified restore point; op2 STARTED (lifecycle only) and its target
changed outside the server. Released at once, with random jitter:
  abort    - accept ABORT of op1
  activate - READY -> ACTIVE through the state machine; the activation decision is instrumented
             INSIDE its locked section: it records how many ABORT/ROLLBACK resolutions were already
             accepted when it decided
  rollback - accept ROLLBACK of op2, then direct RC-4 prepare + apply
  recover  - RC-6 recover
Invariants:
  I1 activation succeeded  => no accepted ABORT/ROLLBACK existed when it was decided
  I2 files restored        => the activation succeeded (a stage that could have had authority)
  I3 no child error, the final recover is never FAIL_CLOSED
A child error "cannot persist rollback record" (os.replace hit by a concurrent reader on Windows, the
known RC-4/RC-5 sharing-violation FINDING) is counted separately as KNOWN_WINDOWS_REPLACE, never hidden.
"""
import json
import random
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

REPO = Path.cwd()
sys.path.insert(0, str(REPO))

from web_alarm.models import MicrotaskStatus, OperationStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_014_adv"
BEFORE, AFTER = b"before\n", b"after\n"

CHILD = """
    import json, pathlib, time
    flags, role, storage, task = pathlib.Path({flags!r}), {role!r}, {storage!r}, {task!r}
    (flags / ("ready_" + role)).write_text("1")
    while not (flags / "go").exists():
        time.sleep(0.0005)
    time.sleep({delay!r})
    try:
        from web_alarm.operation_store import OperationStore
        from web_alarm.reconciliation_service import ReconciliationService
        from web_alarm.resolver_service import ResolverService
        def resolve(op, action):
            d = ReconciliationService(storage).reconcile(task, "m1", op)["DECISION"]
            return ResolverService(storage).apply(task, "m1", op, action, evidence_fingerprint=d["evidence_fingerprint"],
                operation_revision=OperationStore(storage).get(task, op).revision)["resolution"]
        if role == "abort":
            out = {{"abort": resolve("op_1", "ABORT").result.value}}
        elif role == "activate":
            import web_alarm.microtask_gate as gate
            from web_alarm.resolution_store import ResolutionStore
            real = gate.activation_refusal
            seen = {{}}
            def instrumented(*a, **k):
                result = real(*a, **k)
                seen["destructive_accepted_at_decision"] = sum(
                    1 for r in ResolutionStore(storage).list(task)
                    if r.action.value in ("ABORT", "ROLLBACK") and r.result.value == "ACCEPTED")
                seen["refusal"] = result[0] if result else None
                return result
            gate.activation_refusal = instrumented
            from web_alarm.state_machine import ServerStateMachine
            try:
                ServerStateMachine(storage).transition(task, "m1", "ACTIVE")
                out = dict(seen, activate="OK")
            except Exception as exc:
                out = dict(seen, activate=type(exc).__name__)
        elif role == "rollback":
            r = resolve("op_2", "ROLLBACK")
            out = {{"rollback": r.result.value}}
            if r.result.value == "ACCEPTED":
                from web_alarm.rollback_service import RollbackService
                rb = RollbackService(storage)
                p = rb.prepare(task, "m1", "op_2", r.resolution_id)
                out.update(prepare=p["result"], code=p["result_code"])
                if p["rollback"] is not None:
                    a = rb.apply(task, p["rollback"]["rollback_id"])
                    out.update(apply=a["result"])
        else:
            from web_alarm.recovery_coordinator import RecoveryCoordinator
            r = RecoveryCoordinator(storage).recover(task)
            out = {{"state": r["state"], "steps": [s["action"] for s in r["performed_steps"]]}}
    except Exception as exc:
        out = {{"error": type(exc).__name__, "message": str(exc)[:300]}}
    print(json.dumps(out))
"""


def world(tmp):
    storage, project, flags = Path(tmp) / "state", Path(tmp) / "project", Path(tmp) / "flags"
    project.mkdir()
    flags.mkdir()
    (project / "a.txt").write_bytes(BEFORE)
    (project / "keep.txt").write_bytes(b"keep\n")
    WorkspaceRegistry(storage).register("A", project, workspace_id="ws_014a")
    tasks = TaskStore(storage)
    tasks.create_task("ws_014a", "A", "RAW", "adv", task_id=TASK)
    tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
    sm = ServerStateMachine(storage)
    sm.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("keep.txt", "delete")])
    sm.transition(TASK, "m1", MicrotaskStatus.READY)
    ops = OperationStore(storage)
    ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_1", payload=b"keep-v2\n")
    ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_2", payload=AFTER)
    ops.transition(TASK, "op_2", OperationStatus.STARTED)
    (project / "a.txt").write_bytes(AFTER)
    return storage, project, flags, tasks


def race(storage, flags, delays):
    roles = list(delays)
    children = [subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(CHILD.format(
        flags=str(flags), role=r, storage=str(storage), task=TASK, delay=delays[r]))],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for r in roles]
    out = {}
    try:
        deadline = time.time() + 60
        while not all((flags / f"ready_{r}").exists() for r in roles):
            if time.time() > deadline:
                raise RuntimeError("children not ready")
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
    return out


def main(rounds):
    violations, orders, known = [], {}, []
    for n in range(rounds):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project, flags, tasks = world(tmp)
            delays = {r: random.choice((0.0, 0.02, 0.1, 0.3)) for r in ("abort", "activate", "rollback", "recover")}
            out = race(storage, flags, delays)
            final = RecoveryCoordinator(storage).recover(TASK)
            restored = (project / "a.txt").read_bytes() == BEFORE
            act = out["activate"]
            activated = act.get("activate") == "OK"
            line = (f"round {n}: delays={delays} activate={act} abort={out['abort']} rollback={out['rollback']} "
                    f"recover={out['recover'].get('state')} final={final['state']} "
                    f"micro={tasks.open_microtask(TASK, 'm1').status.value} restored={restored}")
            print(line, flush=True)
            errors = [r for r, o in out.items() if "error" in o]
            replace = [r for r in errors if "cannot persist" in out[r].get("message", "")]
            if replace:
                known.append(f"round {n}: {replace}")
            if set(errors) - set(replace):
                violations.append(f"I3 child error {errors}: {line}")
            if activated and act.get("destructive_accepted_at_decision"):
                violations.append(f"I1 ACTIVE decided over an accepted ABORT/ROLLBACK: {line}")
            if restored and not activated:
                violations.append(f"I2 restored without a successful activation: {line}")
            if final["state"] == "FAIL_CLOSED":
                violations.append(f"I3 final FAIL_CLOSED: {line}")
            key = f"activated={activated} refused_by={act.get('refusal')} restored={restored}"
            orders[key] = orders.get(key, 0) + 1
    print(f"rounds={rounds} violations={len(violations)} outcomes={orders} KNOWN_WINDOWS_REPLACE={known}")
    for v in violations:
        print("  VIOLATION", v)
    return not violations


if __name__ == "__main__":
    sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 10) else 1)
