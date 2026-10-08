"""CLAUDE-WA-016 adversarial probe (temp storage only). Run from the repository root:
    python -B <this file> [<pre-fix code root>]

D1 checkpoint compatibility: a checkpoint rebuilt by the pre-fix code (optional argument: an
   export of commit 172 web_alarm/) is validated by the fixed code, then rebuilt.
D2 crash window of TaskStore.complete_task_locked: the process dies after the COMPLETED status
   is written and before the directory move. What do projection / closeout / RC-6 / writers do?
D3 two unsettled decisions in one TASK (ABORT + ADOPT): closeout waits for both; one recover
   settles both; the TASK then closes.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import web_alarm.task_store as task_store_module  # noqa: E402
from web_alarm.closeout import CloseoutService  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.remote_entry import RemoteEntry  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_d"
OLD_REBUILD = r"""
import sys
sys.path.insert(0, sys.argv[1])
from web_alarm.projection import ProjectionService
ProjectionService(sys.argv[2]).rebuild_checkpoint(sys.argv[3])
print("rebuilt by", __import__("web_alarm").__file__)
"""


class Death(BaseException):
    pass


def world(tmp, stages=("m1", "m2")):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    WorkspaceRegistry(storage).register("D", project, workspace_id="ws_d")
    tasks = TaskStore(storage)
    tasks.create_task("ws_d", "D", "RAW", "d", task_id=TASK)
    machine = ServerStateMachine(storage)
    for mid in stages:
        (project / f"{mid}.txt").write_bytes(b"before\n")
        tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
        machine.prepare_microtask(TASK, mid, [(f"{mid}.txt", "edit")])
        for status in ("READY", "ACTIVE", "DONE"):
            machine.transition(TASK, mid, status)
        machine.transition(TASK, mid, "VERIFIED", verification_evidence="ok")
    return storage, project


def resolve(storage, mid, op, action):
    decision = ReconciliationService(storage).reconcile(TASK, mid, op)["DECISION"]
    out = ResolverService(storage).apply(TASK, mid, op, action, evidence_fingerprint=decision["evidence_fingerprint"],
                                         operation_revision=OperationStore(storage).get(TASK, op).revision)
    return out["resolution"].result.value


def blockers(storage):
    return [b["code"] for b in CloseoutService(storage).inspect(TASK)["blockers"]]


def d1(old_root):
    with tempfile.TemporaryDirectory() as tmp:
        storage, _ = world(tmp)
        ops = OperationStore(storage)
        ops.begin(TASK, "m2", "write", "m2.txt", operation_id="op_1", payload=b"x\n")
        ops.transition(TASK, "op_1", "STARTED")
        resolve(storage, "m2", "op_1", "ABORT")
        out = subprocess.run([sys.executable, "-B", "-c", OLD_REBUILD, str(old_root), str(storage), TASK],
                             capture_output=True, text=True)
        service = ProjectionService(storage)
        old = service.validate_checkpoint(TASK)
        new = service.rebuild_checkpoint(TASK)["validation"]["status"]
        print(f"D1 checkpoint from pre-fix code: {out.stdout.strip() or out.stderr[-200:]}")
        print(f"   validated by fixed code: {old['status']} ({'; '.join(old['reasons'])}); authoritative={old['authoritative']}; "
              f"after rebuild: {new}")


def d2():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = world(tmp, stages=("m1",))
        real = task_store_module.os.replace

        def die(src, dst):  # the status file write (an atomic replace) lands; the directory move dies
            if Path(src).is_dir():
                raise Death()
            return real(src, dst)
        task_store_module.os.replace = die
        try:
            TaskStore(storage).complete_task(TASK)
        except Death:
            pass
        finally:
            task_store_module.os.replace = real
        tasks = TaskStore(storage)
        task = tasks.open_task(TASK)
        projection = ProjectionService(storage).build(TASK)
        print(f"D2 crash after the COMPLETED status write: status={task.status.value}, "
              f"location={projection['task']['location']}")
        print(f"   projection NEXT: {projection['next_safe_action']!r} ({projection['authority_source']})")
        print(f"   closeout blockers: {blockers(storage)}; complete again: "
              f"{CloseoutService(storage).complete(TASK)['result']}")
        print(f"   recover: {RecoveryCoordinator(storage).recover(TASK)['state']}")
        print(f"   RemoteEntry active tasks: {RemoteEntry(storage).active_task_ids()}")
        try:
            OperationStore(storage).begin(TASK, "m1", "write", "m1.txt", operation_id="op_late", payload=b"late\n")
            begin = "ACCEPTED (an operation was written into the COMPLETED TASK)"
        except Exception as exc:  # noqa: BLE001
            begin = f"refused: {type(exc).__name__}"
        try:
            tasks.create_microtask(TASK, "late", "late", microtask_id="late")
            micro = "ACCEPTED"
        except Exception as exc:  # noqa: BLE001
            micro = f"refused: {type(exc).__name__}"
        print(f"   OperationStore.begin: {begin}; TaskStore.create_microtask: {micro}")


def d3():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = world(tmp)
        ops = OperationStore(storage)
        ops.begin(TASK, "m1", "write", "m1.txt", operation_id="op_a", payload=b"a\n")
        ops.transition(TASK, "op_a", "STARTED")
        ops.begin(TASK, "m2", "write", "m2.txt", operation_id="op_b", payload=b"b\n")
        ops.transition(TASK, "op_b", "STARTED")
        (project / "m2.txt").write_bytes(b"b\n")
        print(f"D3 op_a ABORT {resolve(storage, 'm1', 'op_a', 'ABORT')}, op_b ADOPT {resolve(storage, 'm2', 'op_b', 'ADOPT')}")
        print(f"   closeout: {blockers(storage)}; complete: {CloseoutService(storage).complete(TASK)['result']}")
        result = RecoveryCoordinator(storage).recover(TASK)
        print(f"   recover: {result['state']} steps={[s['action'] for s in result['performed_steps']]}")
        settled = {op: (ops.get(TASK, op).recovery_settlement or {}).get("action") for op in ("op_a", "op_b")}
        print(f"   settlements {settled}; closeout: {blockers(storage)}; "
              f"complete: {CloseoutService(storage).complete(TASK)['result']}")
        print(f"   completed NEXT: {ProjectionService(storage).build(TASK)['next_safe_action']!r}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        d1(Path(sys.argv[1]).resolve())
    d2()
    d3()
