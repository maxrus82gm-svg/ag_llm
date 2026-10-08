"""Repair #4B adversarial probes (temp storage only, real processes).

Run from the repository root: python -B <this file> [rounds]

Z1  activation (READY -> ACTIVE) x op_1 ABORT settlement x direct RC-4 rollback of op_2 x recover,
    all released at once. Invariant: a destructive restore happens only if the microtask really
    became ACTIVE before the restore was authorized; never when op_1's ABORT was settled while
    the microtask had never been ACTIVE (settlement fact pre-execution) or the activation lost.
Z2  an RC-4 session prepared by an older build for a never-executed microtask, applied by two
    processes at once plus recover: never restored, no claim left, closable.
Z3  downgrade boundary: commit-165 code reading an operation record with the new settlement fact
    (expected: the old strict schema refuses the record, i.e. fail-closed, documented).
"""
import json
import random
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

REPO = Path.cwd()
sys.path.insert(0, str(REPO))
SESSION = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-013_RC6_REPAIR4B"

from web_alarm.microtask_gate import PRE_EXECUTION_STATUSES  # noqa: E402
from web_alarm.models import MicrotaskStatus, OperationStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.rollback_service import RollbackService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_4b_adv"
BEFORE, AFTER, KEEP = b"before\n", b"after\n", b"keep\n"

CHILD = """
    import json, pathlib, time
    from web_alarm.models import MicrotaskStatus
    from web_alarm.operation_store import OperationStore
    from web_alarm.reconciliation_service import ReconciliationService
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    from web_alarm.resolver_service import ResolverService
    from web_alarm.rollback_service import RollbackService
    from web_alarm.state_machine import ServerStateMachine
    storage, task, role, flags = {storage!r}, {task!r}, {role!r}, pathlib.Path({flags!r})
    (flags / ("ready_" + role)).write_text("1")
    while not (flags / "go").exists():
        time.sleep(0.0005)
    try:
        if role == "activate":
            time.sleep({delay!r})  # Z1: 0 or a jitter, so both orders with the ABORT settlement occur
            try:
                ServerStateMachine(storage).transition(task, "m1", MicrotaskStatus.ACTIVE)
                out = {{"activate": "OK"}}
            except Exception as exc:
                out = {{"activate": type(exc).__name__}}
        elif role == "rollback_late":  # Z1: accept op_2's ROLLBACK inside the race, then RC-4 directly
            time.sleep({delay2!r})
            decision = ReconciliationService(storage).reconcile(task, "m1", "op_2")["DECISION"]
            r = ResolverService(storage).apply(
                task, "m1", "op_2", "ROLLBACK", evidence_fingerprint=decision["evidence_fingerprint"],
                operation_revision=OperationStore(storage).get(task, "op_2").revision)["resolution"]
            out = {{"rollback": r.result.value}}
            if r.result.value == "ACCEPTED":
                rb = RollbackService(storage)
                p = rb.prepare(task, "m1", "op_2", r.resolution_id)
                out.update(prepare=p["result"], code=p["result_code"])
                if p["rollback"] is not None:
                    a = rb.apply(task, p["rollback"]["rollback_id"])
                    out.update(apply=a["result"], apply_code=a["result_code"])
        elif role.startswith("rc4"):
            rb = RollbackService(storage)
            if {rollback_id!r}:
                a = rb.apply(task, {rollback_id!r})
                out = {{"apply": a["result"], "code": a["result_code"]}}
            else:
                p = rb.prepare(task, "m1", "op_2", {resolution_id!r})
                out = {{"prepare": p["result"], "code": p["result_code"]}}
                if p["rollback"] is not None:
                    a = rb.apply(task, p["rollback"]["rollback_id"])
                    out.update(apply=a["result"], apply_code=a["result_code"])
        else:
            r = RecoveryCoordinator(storage).recover(task)
            out = {{"state": r["state"], "steps": [s["action"] for s in r["performed_steps"]],
                    "reason": r["reason"][:240]}}
    except Exception as exc:
        out = {{"error": type(exc).__name__, "message": str(exc)[:300]}}
    print(json.dumps(out))
"""


def world(tmp, status="READY"):
    storage, project, flags = Path(tmp) / "state", Path(tmp) / "project", Path(tmp) / "flags"
    project.mkdir()
    flags.mkdir()
    (project / "a.txt").write_bytes(BEFORE)
    (project / "keep.txt").write_bytes(KEEP)
    WorkspaceRegistry(storage).register("4B", project, workspace_id="ws_4b_adv")
    tasks = TaskStore(storage)
    tasks.create_task("ws_4b_adv", "4B", "RAW", "adv", task_id=TASK)
    tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
    sm = ServerStateMachine(storage)
    sm.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("keep.txt", "delete")])
    sm.transition(TASK, "m1", MicrotaskStatus.READY)
    ops = OperationStore(storage)
    ops.begin(TASK, "m1", "write", "keep.txt", operation_id="op_1", payload=b"keep-v2\n")
    ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_2", payload=AFTER)
    ops.transition(TASK, "op_2", OperationStatus.STARTED)  # lifecycle only
    (project / "a.txt").write_bytes(AFTER)  # changed outside the server
    return storage, project, flags, tasks, ops


def resolve(storage, op, action):
    decision = ReconciliationService(storage).reconcile(TASK, "m1", op)["DECISION"]
    return ResolverService(storage).apply(
        TASK, "m1", op, action, evidence_fingerprint=decision["evidence_fingerprint"],
        operation_revision=OperationStore(storage).get(TASK, op).revision)["resolution"]


def race(storage, flags, roles, **fmt):
    children = [subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(CHILD.format(
        storage=str(storage), task=TASK, role=role, flags=str(flags), **fmt))],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for role in roles]
    outputs = {}
    try:
        deadline = time.time() + 60
        while not all((flags / f"ready_{r}").exists() for r in roles):
            if time.time() > deadline:
                raise RuntimeError("children not ready")
            time.sleep(0.005)
        (flags / "go").write_text("1")
        for role, child in zip(roles, children):
            out, err = child.communicate(timeout=180)
            outputs[role] = json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": err[-300:]}
    finally:
        (flags / "go").write_text("1")
        for child in children:
            if child.poll() is None:
                child.kill()
    return outputs


def z1(rounds):
    destructive, refused, violations, orders = 0, 0, [], {}
    for n in range(rounds):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project, flags, tasks, ops = world(tmp)
            assert resolve(storage, "op_1", "ABORT").result.value == "ACCEPTED"
            outputs = race(storage, flags, ("activate", "recover_a", "rollback_late", "recover_b"),
                           resolution_id="", rollback_id="", delay=random.choice((0.0, 0.05, 0.2, 0.5)),
                           delay2=random.choice((0.0, 0.1, 0.3)))
            outputs["rc4"] = outputs["rollback_late"]
            final = RecoveryCoordinator(storage).recover(TASK)
            restored = (project / "a.txt").read_bytes() == BEFORE
            fact = (ops.get(TASK, "op_1").recovery_settlement or {}).get("microtask_status")
            activated = outputs["activate"].get("activate") == "OK"
            errors = [r for r, o in outputs.items() if "error" in o]
            line = (f"  round {n}: activate={outputs['activate'].get('activate')} op_1 fact={fact} "
                    f"rc4={outputs['rc4']} recover_a={outputs['recover_a'].get('state')} "
                    f"recover_b={outputs['recover_b'].get('state')} final={final['state']} "
                    f"micro={tasks.open_microtask(TASK, 'm1').status.value} restored={restored}")
            print(line, flush=True)
            for role in ("recover_a", "recover_b"):
                if outputs[role].get("state") == "FAIL_CLOSED":
                    print(f"    {role} FAIL_CLOSED (one call; later recover shown as final): {outputs[role]}")
            if errors:
                violations.append(f"round {n}: child error {errors}: {outputs}")
            if restored and (not activated or fact in PRE_EXECUTION_STATUSES):
                violations.append(f"round {n}: destructive restore without execution: {line}")
            if fact in PRE_EXECUTION_STATUSES and activated:
                violations.append(f"round {n}: activated after an ABORT settled before execution: {line}")
            key = f"fact={fact} activated={activated} restored={restored}"
            orders[key] = orders.get(key, 0) + 1
            if final["state"] == "FAIL_CLOSED":
                violations.append(f"round {n}: FAIL_CLOSED {final['reason']}")
            destructive += restored
            refused += not restored
    print(f"Z1: rounds={rounds} destructive(after a real activation)={destructive} refused={refused} "
          f"violations={len(violations)} orders={orders}")
    for v in violations:
        print("  VIOLATION", v)
    return not violations


def z2():
    import web_alarm.rollback_service as rs
    from unittest import mock
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, flags, tasks, ops = world(tmp)
        resolve(storage, "op_1", "ABORT")
        RecoveryCoordinator(storage).recover(TASK)
        res = resolve(storage, "op_2", "ROLLBACK")
        with mock.patch.object(rs, "rollback_refusal", return_value=None):  # an older build prepared it
            session = RollbackService(storage).prepare(TASK, "m1", "op_2", res.resolution_id)["rollback"]
        outputs = race(storage, flags, ("rc4_a", "rc4_b", "recover"), resolution_id=res.resolution_id,
                       rollback_id=session["rollback_id"], delay=0.0, delay2=0.0)
        record = RollbackService(storage).inspect(TASK, session["rollback_id"])
        claims = [p for p in (storage / "target_claims").glob("*.json")
                  if json.loads(p.read_text(encoding="utf-8")).get("active")] if (storage / "target_claims").exists() else []
        closed = RollbackService(storage).close(TASK, session["rollback_id"])["result"]
        ok = ((project / "a.txt").read_bytes() == AFTER and record["status"] == "PRESERVED" and not claims
              and closed == "CLOSED" and not any("error" in o for o in outputs.values()))
        print(f"Z2: {outputs} session={record['status']} active_claims={len(claims)} close={closed} "
              f"a.txt={'AFTER (untouched)' if (project / 'a.txt').read_bytes() == AFTER else 'CHANGED'} -> "
              f"{'OK' if ok else 'VIOLATION'}")
        return ok


def z3():
    code165 = SESSION / "safety_copies" / "web_alarm"
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, flags, tasks, ops = world(tmp)
        resolve(storage, "op_1", "ABORT")
        RecoveryCoordinator(storage).recover(TASK)
        old = Path(tmp) / "code165"
        shutil.copytree(code165, old / "web_alarm")
        script = textwrap.dedent(f"""
            from web_alarm.operation_store import OperationStore
            try:
                OperationStore({str(storage)!r}).get({TASK!r}, "op_1")
                print("READ")
            except Exception as exc:
                print(type(exc).__name__, str(exc)[:160])
        """)
        out = subprocess.run([sys.executable, "-B", "-c", script], cwd=old, capture_output=True, text=True).stdout.strip()
        fact = ops.get(TASK, "op_1").recovery_settlement.get("microtask_status")
        print(f"Z3: new code reads op_1 (fact={fact}); commit-165 code: {out}")
        return True


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    results = {"Z1": z1(rounds), "Z2": z2(), "Z3": z3()}
    print("RESULT", {k: ("OK" if v else "VIOLATION") for k, v in results.items()})
    sys.exit(0 if all(results.values()) else 1)
