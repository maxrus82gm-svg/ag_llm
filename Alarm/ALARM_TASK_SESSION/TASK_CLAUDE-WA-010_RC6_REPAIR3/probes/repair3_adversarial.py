"""Repair #3 adversarial pass (temp storage only, real processes).

Run from the repository root: python -B <this file> [rounds]
  X1  VERIFIED vs ABORT acceptance, both orders, N rounds with jitter: the end state
      is always consistent (VERIFIED + absorbed ABORT, or RECOVERY_REQUIRED), never
      an endless FAIL_CLOSED, and a second recover performs nothing.
  X2  authority held in one process vs a sibling ABORT acceptance + RC-6 settlement
      in another: the recovery waits for the boundary; afterwards no authority.
  X3  a refused VERIFIED never writes (microtask file byte-identical).
  X4  RC-6 READY under foreign claim churn: whenever READY is returned, its proof is
      the re-derived basis of the same section (restore point + target set).
"""

import json
import random
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import READY_FOR_EXECUTION, RecoveryCoordinator
from web_alarm.resolver_service import ResolverService
from web_alarm.state_machine import ServerStateMachine, TransitionRejected
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

TASK, OTHER = "task_x", "task_x_other"
BEFORE, AFTER = b"before\n", b"after\n"
REPO = Path.cwd()
failures = []


def check(case, ok, detail):
    print(f"{case} | {'OK' if ok else 'FAIL'} | {detail}", flush=True)
    if not ok:
        failures.append(case)


def world(tmp):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    WorkspaceRegistry(storage).register("X", project, workspace_id="ws_x")
    tasks = TaskStore(storage)
    for task in (TASK, OTHER):
        tasks.create_task("ws_x", task, "RAW", "X", task_id=task)
    for mid in ("m1", "m2"):
        tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
    tasks.create_microtask(OTHER, "F1", "f", microtask_id="f1")
    return storage, project


def activate(storage, project, mid, *targets, task=TASK):
    sm = ServerStateMachine(storage)
    for t in targets:
        if not (project / t).exists():
            (project / t).write_bytes(BEFORE)
    sm.prepare_microtask(task, mid, [(t, "edit") for t in targets])
    sm.transition(task, mid, MicrotaskStatus.READY)
    sm.transition(task, mid, MicrotaskStatus.ACTIVE)


def resolve(storage, action, op, mid="m1", task=TASK):
    decision = ReconciliationService(storage).reconcile(task, mid, op)["DECISION"]
    return ResolverService(storage).apply(
        task, mid, op, action, evidence_fingerprint=decision["evidence_fingerprint"],
        operation_revision=OperationStore(storage).get(task, op).revision,
    )


def child(code):
    return subprocess.Popen([sys.executable, "-B", "-c", textwrap.dedent(code)], cwd=REPO,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def x1(rounds):
    seen = {}
    for index in range(rounds):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project = world(tmp)
            activate(storage, project, "m1", "a.txt")
            ops = OperationStore(storage)
            ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
            ops.transition(TASK, "op_1", OperationStatus.STARTED)
            (project / "a.txt").write_bytes(AFTER)
            ops.transition(TASK, "op_1", OperationStatus.DONE)
            ServerStateMachine(storage).transition(TASK, "m1", MicrotaskStatus.DONE)
            decision = ReconciliationService(storage).reconcile(TASK, "m1", "op_1")["DECISION"]
            delay_v, delay_r = random.random() * 0.05, random.random() * 0.05
            verifier = child(f"""
                import json, time
                from web_alarm.state_machine import ServerStateMachine, TransitionRejected
                time.sleep({delay_v})
                try:
                    ServerStateMachine({str(storage)!r}).transition({TASK!r}, "m1", "VERIFIED", verification_evidence="ok")
                    print(json.dumps("APPLIED"))
                except TransitionRejected as exc:
                    print(json.dumps("REJECTED"))
            """)
            resolver = child(f"""
                import json, time
                from web_alarm.resolver_service import ResolverService
                time.sleep({delay_r})
                out = ResolverService({str(storage)!r}).apply({TASK!r}, "m1", "op_1", "ABORT",
                    evidence_fingerprint={decision["evidence_fingerprint"]!r}, operation_revision={ops.get(TASK, "op_1").revision})
                print(json.dumps(out["accepted"]))
            """)
            v = json.loads(verifier.communicate(timeout=120)[0].strip().splitlines()[-1])
            r = json.loads(resolver.communicate(timeout=120)[0].strip().splitlines()[-1])
            first = RecoveryCoordinator(storage).recover(TASK)
            second = RecoveryCoordinator(storage).recover(TASK)
            micro = TaskStore(storage).open_microtask(TASK, "m1").status.value
            settled = (OperationStore(storage).get(TASK, "op_1").recovery_settlement or {}).get("action")
            shape = (v, micro, settled, first["state"])
            seen[shape] = seen.get(shape, 0) + 1
            consistent = (
                r is True and settled == "ABORT" and second["performed_steps"] == []
                and first["state"] != "FAIL_CLOSED" and second["state"] != "FAIL_CLOSED"
                and ((v == "APPLIED" and micro == "VERIFIED") or (v == "REJECTED" and micro == "RECOVERY_REQUIRED"))
            )
            if not consistent:
                check(f"X1 round {index}", False, f"{shape} second={second['state']}")
    check("X1 VERIFIED vs ABORT, both orders", not any(c.startswith("X1 round") for c in failures),
          f"{rounds} rounds, outcomes {seen}")


def x2():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = world(tmp)
        activate(storage, project, "m1", "a.txt")
        # op_old writes c.txt (outside op_1's reconciliation evidence), so the
        # authorized write does not make the rival's ABORT basis stale
        (project / "c.txt").write_bytes(BEFORE)
        ops, claims = OperationStore(storage), TargetClaimService(storage)
        ops.begin(TASK, "m1", "write", "c.txt", operation_id="op_old", payload=AFTER)
        claims.acquire(TASK, "op_old", operation_revision=1)
        ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        ops.transition(TASK, "op_1", OperationStatus.STARTED)
        decision = ReconciliationService(storage).reconcile(TASK, "m1", "op_1")["DECISION"]
        rival = None
        with claims.mutation_boundary(TASK, "op_old", operation_revision=1) as gate:
            authorized = gate["mutation_authority"]
            rival = child(f"""
                import json, time
                from web_alarm.resolver_service import ResolverService
                from web_alarm.recovery_coordinator import RecoveryCoordinator
                t0 = time.time()
                out = ResolverService({str(storage)!r}).apply({TASK!r}, "m1", "op_1", "ABORT",
                    evidence_fingerprint={decision["evidence_fingerprint"]!r}, operation_revision=2)
                r = RecoveryCoordinator({str(storage)!r}).recover({TASK!r})
                print(json.dumps({{"waited": time.time() - t0, "accepted": out["accepted"], "state": r["state"]}}))
            """)
            time.sleep(1.0)
            still_waiting = rival.poll() is None
            (project / "c.txt").write_bytes(AFTER)  # the authorized write
        out = json.loads(rival.communicate(timeout=120)[0].strip().splitlines()[-1])
        after = claims.authorize(TASK, "op_old", operation_revision=1)
        micro = TaskStore(storage).open_microtask(TASK, "m1").status.value
        check("X2 authority held vs sibling ABORT + settlement",
              authorized and still_waiting and out["waited"] >= 0.9 and out["accepted"]
              and micro == "RECOVERY_REQUIRED" and after["result_code"] == "MICROTASK_NOT_ACTIVE",
              f"authorized={authorized} rival_waited={out['waited']:.2f}s accepted={out['accepted']} "
              f"rival_state={out['state']} micro={micro} after={after['result_code']}")


def x3():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = world(tmp)
        activate(storage, project, "m1", "a.txt")
        ops = OperationStore(storage)
        ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
        ops.transition(TASK, "op_1", OperationStatus.STARTED)
        sm = ServerStateMachine(storage)
        sm.transition(TASK, "m1", MicrotaskStatus.DONE)
        micro_file = TaskStore(storage).task_directory(TASK) / "microtasks" / "m1.json"
        before = micro_file.read_bytes()
        try:
            sm.transition(TASK, "m1", MicrotaskStatus.VERIFIED, verification_evidence="ok")
            refused = False
        except TransitionRejected:
            refused = True
        check("X3 refused VERIFIED writes nothing", refused and micro_file.read_bytes() == before,
              f"refused={refused} identical={micro_file.read_bytes() == before}")


def x4(rounds):
    ready = bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = world(tmp)
        activate(storage, project, "m1", "a.txt")
        activate(storage, project, "f1", "a.txt", task=OTHER)
        churn = child(f"""
            import time
            from web_alarm.operation_store import OperationStore
            from web_alarm.target_claim_service import TargetClaimService
            ops, claims = OperationStore({str(storage)!r}), TargetClaimService({str(storage)!r})
            deadline, i = time.time() + {rounds * 0.6 + 5}, 0
            while time.time() < deadline:
                i += 1  # a new foreign operation each time (a released basis is never re-claimed)
                ops.begin({OTHER!r}, "f1", "write", "a.txt", operation_id=f"op_f{{i}}", payload=b"f\\n")
                claims.acquire({OTHER!r}, f"op_f{{i}}", operation_revision=1)
                time.sleep(0.01)
                claims.release({OTHER!r}, f"op_f{{i}}")
                time.sleep(0.01)
        """)
        for _ in range(rounds):
            r = RecoveryCoordinator(storage).recover(TASK)
            if r["state"] == READY_FOR_EXECUTION:
                ready += 1
                plan = __import__("web_alarm.manifest_store", fromlist=["x"]).ManifestSnapshotStore(storage).restore_plan(TASK, "m1")
                if r["ready_proof"]["restore_point_fingerprint"] != plan["restore_point_fingerprint"]:
                    bad += 1
        churn.kill()
        churn.communicate()
    check("X4 READY under foreign claim churn is bound to its basis", bad == 0,
          f"rounds={rounds} ready={ready} mismatched={bad}")


if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    random.seed(20261007)
    x1(rounds)
    x2()
    x3()
    x4(rounds)
    print("ALL OK" if not failures else f"FAILURES: {failures}")
