"""Repair #4: reproduction of Blocker A (PREPARING crash) and Blocker B (new recovery
action over an existing settlement). Temp storage only; never touches live storage.

Run from the repository root: python -B <this file>
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
from web_alarm.state_machine import ServerStateMachine, TransitionRejected  # noqa: E402
from web_alarm.target_claim_service import TargetClaimService  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_r4"
BEFORE, AFTER = b"before\n", b"after\n"


def world(tmp):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    WorkspaceRegistry(storage).register("R4", project, workspace_id="ws_r4")
    tasks = TaskStore(storage)
    tasks.create_task("ws_r4", "R4", "RAW", "Repair4", task_id=TASK)
    for mid in ("m1", "m2"):
        tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
    return storage, project, tasks


PREPARE_CRASH = """
    import os
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    if {window!r} == "W1":
        def die(self, *a, **k):
            os._exit(23)  # PREPARING is written, the stage is being captured
        ManifestSnapshotStore._resolve_target = die
    else:
        real = TaskStore.set_microtask_status
        def die(self, task_id, microtask_id, status):
            if status.value == "BACKUP_VERIFIED":
                os._exit(29)  # the restore point is published, its status is not
            return real(self, task_id, microtask_id, status)
        TaskStore.set_microtask_status = die
        real_cas = TaskStore.compare_and_set_microtask_status
        def die_cas(self, task_id, microtask_id, *, expected, status, activate=False):
            if getattr(status, "value", status) == "BACKUP_VERIFIED":
                os._exit(29)
            return real_cas(self, task_id, microtask_id, expected=expected, status=status, activate=activate)
        TaskStore.compare_and_set_microtask_status = die_cas
    ServerStateMachine({storage!r}).prepare_microtask({task!r}, "m1", [("a.txt", "edit")])
"""


def blocker_a():
    for window in ("W1", "W2"):
        with tempfile.TemporaryDirectory() as tmp:
            storage, project, tasks = world(tmp)
            (project / "a.txt").write_bytes(BEFORE)
            proc = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(PREPARE_CRASH.format(
                window=window, storage=str(storage), task=TASK))], cwd=Path.cwd(), capture_output=True, text=True)
            work = tasks.microtask_directory(TASK, "m1")
            evidence = {
                "status": tasks.open_microtask(TASK, "m1").status.value,
                "published": (work / "restore_point" / "manifest.json").is_file(),
                "stages": len(list(work.glob(".restore.*"))),
            }
            states = [RecoveryCoordinator(storage).recover(TASK)["state"] for _ in range(2)]
            try:
                ServerStateMachine(storage).prepare_microtask(TASK, "m1", [("a.txt", "edit")])
                again = "prepare again: OK"
            except TransitionRejected as exc:
                again = f"prepare again: REJECTED ({exc.reason})"
            except Exception as exc:  # noqa: BLE001
                again = f"prepare again: {type(exc).__name__}: {exc}"
            next_action = ProjectionService(storage).build(TASK)["next_safe_action"]
            stuck = tasks.open_microtask(TASK, "m1").status is MicrotaskStatus.PREPARING
            print(f"A-{window} | exit={proc.returncode} {evidence} recover x2={states} | {again} | "
                  f"NEXT={next_action!r} | {'GAP (PREPARING forever)' if stuck else 'closed'}", flush=True)


def activate(storage, project, mid, *targets):
    sm = ServerStateMachine(storage)
    for t in targets:
        (project / t).write_bytes(BEFORE)
    sm.prepare_microtask(TASK, mid, [(t, "edit") for t in targets])
    sm.transition(TASK, mid, MicrotaskStatus.READY)
    sm.transition(TASK, mid, MicrotaskStatus.ACTIVE)


def resolve(storage, action, op="op_1", mid="m1"):
    ops = OperationStore(storage)
    decision = ReconciliationService(storage).reconcile(TASK, mid, op)["DECISION"]
    out = ResolverService(storage).apply(
        TASK, mid, op, action, evidence_fingerprint=decision["evidence_fingerprint"],
        operation_revision=ops.get(TASK, op).revision,
    )
    record = out["resolution"]
    return f"{record.result.value}/{record.result_code}", decision["decision"]


def settled(storage, project, first):
    """op_1 of m1 (target a.txt) with a durable settlement `first`."""
    if first == "ROLLBACK":
        # a partial effect over a three-target restore point decides ROLLBACK_CURRENT_MICROTASK
        sm = ServerStateMachine(storage)
        for name, data in (("a.txt", BEFORE), ("b.txt", b"b-before\n"), ("c.txt", b"c-keep\n")):
            (project / name).write_bytes(data)
        sm.prepare_microtask(TASK, "m1", [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")])
        sm.transition(TASK, "m1", MicrotaskStatus.READY)
        sm.transition(TASK, "m1", MicrotaskStatus.ACTIVE)
    else:
        activate(storage, project, "m1", "a.txt")
    ops = OperationStore(storage)
    ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_1", payload=AFTER)
    TargetClaimService(storage).acquire(TASK, "op_1", operation_revision=1)
    ops.transition(TASK, "op_1", OperationStatus.STARTED)
    if first in ("ADOPT", "ROLLBACK"):
        (project / "a.txt").write_bytes(AFTER)
    if first == "ROLLBACK":
        (project / "b.txt").unlink()
    ServerStateMachine(storage).transition(TASK, "m1", MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
    resolve(storage, first)
    r = RecoveryCoordinator(storage).recover(TASK)
    settlement = (ops.get(TASK, "op_1").recovery_settlement or {}).get("action")
    return settlement, r["state"]


def restored_targets(storage):
    from web_alarm.rollback_service import RollbackService
    return sum(1 for s in RollbackService(storage).store.list(TASK) for t in s["targets"] if t["status"] == "RESTORED")


def blocker_b():
    for first in ("ADOPT", "ABORT", "ROLLBACK"):
        for later in ("ADOPT", "ROLLBACK", "RETRY", "ABORT"):
            with tempfile.TemporaryDirectory() as tmp:
                storage, project, tasks = world(tmp)
                settlement, first_state = settled(storage, project, first)
                # make the later action's decision reachable where a file state decides it
                if first == "ROLLBACK" and later == "ADOPT":
                    (project / "a.txt").write_bytes(AFTER)  # the full expected post-state again
                    (project / "b.txt").unlink()
                    (project / "c.txt").unlink()
                elif first == "ROLLBACK" and later == "ROLLBACK":
                    (project / "a.txt").write_bytes(AFTER)  # the same partial effect again
                    (project / "b.txt").unlink()
                elif later == "ADOPT":
                    (project / "a.txt").write_bytes(AFTER)
                elif later == "ROLLBACK":
                    (project / "a.txt").write_bytes(b"partial\n")
                elif later == "RETRY":
                    (project / "a.txt").write_bytes(BEFORE)
                restored_before = restored_targets(storage)
                try:
                    outcome, decision = resolve(storage, later)
                except Exception as exc:  # noqa: BLE001
                    outcome, decision = f"{type(exc).__name__}: {exc}", "-"
                states = [RecoveryCoordinator(storage).recover(TASK) for _ in range(2)]
                second_restore = restored_targets(storage) - restored_before
                trap = outcome.startswith("ACCEPTED") and all(s["state"] == "FAIL_CLOSED" for s in states)
                attention = (not outcome.startswith("ACCEPTED")) and states[1]["recovery_state"] not in ("NORMAL",)
                verdict = (
                    "GAP (second physical rollback)" if second_restore else
                    "GAP (accepted, never completed)" if trap else
                    "GAP (rejected/stale -> attention)" if attention else "ok"
                )
                print(f"B {first}->{later} | settled={settlement} ({first_state}) | Resolver {outcome} "
                      f"(decision {decision}) | recover x2={[s['state'] for s in states]} "
                      f"recovery={states[1]['recovery_state']} micro={tasks.open_microtask(TASK, 'm1').status.value} "
                      f"new restores={second_restore} | {verdict}", flush=True)


if __name__ == "__main__":
    blocker_a()
    blocker_b()
