"""Repair #4A: PREPARING x accepted recovery. Reproduction in temp storage only.

Run from the repository root: python -B <this file>
Each line: scenario | Resolver outcome | recover x3 (+ fresh process) | lifecycle | verdict
(GAP = an accepted authority without a completion path / an endless FAIL_CLOSED).
"""
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from web_alarm.models import MicrotaskStatus, OperationStatus  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_4a"
BEFORE, AFTER = b"before\n", b"after\n"
REPO = Path.cwd()

CRASH = """
    import os
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    if {window!r} == "W1":
        def die(self, *a, **k):
            os._exit(23)
        ManifestSnapshotStore._resolve_target = die
    else:
        real = TaskStore.compare_and_set_microtask_status
        def die(self, t, m, *, expected, status, activate=False):
            if getattr(status, "value", status) == "BACKUP_VERIFIED":
                os._exit(29)
            return real(self, t, m, expected=expected, status=status, activate=activate)
        TaskStore.compare_and_set_microtask_status = die
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", [("a.txt", "edit")])
"""

FRESH = """
    import json
    from web_alarm.recovery_coordinator import RecoveryCoordinator
    r = RecoveryCoordinator({storage!r}).recover({task!r})
    print(json.dumps([r["state"], r["recovery_state"], r["reason"][:160]]))
"""


def world(tmp):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    (project / "a.txt").write_bytes(BEFORE)
    WorkspaceRegistry(storage).register("4A", project, workspace_id="ws_4a")
    tasks = TaskStore(storage)
    tasks.create_task("ws_4a", "4A", "RAW", "Repair4A", task_id=TASK)
    tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
    return storage, project, tasks


def run(code):
    return subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(code)], cwd=REPO,
                          capture_output=True, text=True)


def resolve(storage, action, op="op_1"):
    try:
        decision = ReconciliationService(storage).reconcile(TASK, "m1", op)["DECISION"]
        out = ResolverService(storage).apply(
            TASK, "m1", op, action, evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=OperationStore(storage).get(TASK, op).revision)
        r = out["resolution"]
        return f"{r.result.value}/{r.result_code} (decision {decision['decision']})"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:120]}"


def summary(storage, tasks, label, resolution):
    runs = [RecoveryCoordinator(storage).recover(TASK) for _ in range(3)]
    fresh = json.loads(run(FRESH.format(storage=str(storage), task=TASK)).stdout.strip().splitlines()[-1])
    states = [r["state"] for r in runs] + [f"fresh:{fresh[0]}"]
    micro = tasks.open_microtask(TASK, "m1").status.value
    op = OperationStore(storage).get(TASK, "op_1")
    settlement = (op.recovery_settlement or {}).get("action")
    authority = TargetClaimService(storage).authorize(TASK, "op_1", operation_revision=op.revision)["result_code"]
    endless = resolution.startswith("ACCEPTED") and all(s.endswith("FAIL_CLOSED") for s in states)
    verdict = "GAP (endless FAIL_CLOSED)" if endless else "no trap"
    print(f"{label} | Resolver {resolution} | recover x3+fresh={states} | last recovery={runs[-1]['recovery_state']} "
          f"| micro={micro} op={op.status.value} settlement={settlement} authority={authority} | {verdict}"
          + (f" | reason: {runs[-1]['reason'][:150]}" if endless else ""), flush=True)


def intent(storage, *, claim=True):
    OperationStore(storage).begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
    if claim:
        TargetClaimService(storage).acquire(TASK, "op_1", operation_revision=1)


def scenario_crash_then_abort(window):
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        intent(storage)                                  # 2. operation INTENT before ACTIVE (m1 PLANNED)
        crash = run(CRASH.format(window=window, storage=str(storage), task=TASK))   # 3-4. PREPARING + crash
        before = tasks.open_microtask(TASK, "m1").status.value
        resolution = resolve(storage, "ABORT")           # 5. ABORT before any reconcile
        projection = ProjectionService(storage).build(TASK)
        print(f"  [{window}] crash exit={crash.returncode} micro={before} projection recovery="
              f"{projection['recovery']['state']} NEXT={projection['next_safe_action'][:90]!r}")
        summary(storage, tasks, f"A{'1' if window == 'W1' else '2'} {window} + ABORT before reconcile", resolution)


def scenario_reconcile_then_abort(window):
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        intent(storage)
        run(CRASH.format(window=window, storage=str(storage), task=TASK))
        first = RecoveryCoordinator(storage).recover(TASK)
        reconciled = tasks.open_microtask(TASK, "m1").status.value
        resolution = resolve(storage, "ABORT")
        print(f"  [{window}] reconcile first: {first['state']} steps="
              f"{[s['action'] for s in first['performed_steps']]} -> micro={reconciled}")
        summary(storage, tasks, f"A3 {window} reconciled ({reconciled}), then ABORT", resolution)


def scenario_pre_execution(status, action):
    with tempfile.TemporaryDirectory() as tmp:
        storage, project, tasks = world(tmp)
        sm = ServerStateMachine(storage)
        if status in ("BACKUP_VERIFIED", "READY"):
            sm.prepare_microtask(TASK, "m1", [("a.txt", "edit")])
        if status == "READY":
            sm.transition(TASK, "m1", MicrotaskStatus.READY)
        intent(storage)
        if action == "ADOPT":
            (project / "a.txt").write_bytes(AFTER)  # the declared post-state already present
        elif action == "ROLLBACK":
            (project / "a.txt").write_bytes(b"partial\n")
        summary(storage, tasks, f"X {status} INTENT op + {action}", resolve(storage, action))


if __name__ == "__main__":
    scenario_crash_then_abort("W1")
    scenario_crash_then_abort("W2")
    scenario_reconcile_then_abort("W1")
    scenario_reconcile_then_abort("W2")
    for status in ("PLANNED", "BACKUP_VERIFIED", "READY"):
        for action in ("ABORT", "ADOPT", "RETRY", "ROLLBACK"):
            scenario_pre_execution(status, action)
