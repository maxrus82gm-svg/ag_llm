"""CLAUDE-WA-015: closeout verdict of the A1 (unsettled ABORT) and A7 (accepted ROLLBACK of a VERIFIED
stage) states on a given code root. Temp storage only; library calls of the public services.

Run: python -B <this file> <code_root>
Used to show when each behaviour appeared: commit 156 (RC-5 + Repair #1), 161 (just before RC-6
Repair #2 R1), 162 (R1 stage protection), HEAD.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

from web_alarm.closeout import CloseoutService  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.reconciliation_service import ReconciliationService  # noqa: E402
from web_alarm.resolver_service import ResolverService  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_s"


def world(tmp):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    for name in ("one.txt", "two.txt", "keep.txt"):
        (project / name).write_bytes(name.encode() + b"\n")
    WorkspaceRegistry(storage).register("S", project, workspace_id="ws_s")
    tasks = TaskStore(storage)
    tasks.create_task("ws_s", "S", "RAW", "s", task_id=TASK)
    machine = ServerStateMachine(storage)
    for mid, targets in (("m1", [("one.txt", "edit")]), ("m2", [("two.txt", "edit"), ("keep.txt", "edit")])):
        tasks.create_microtask(TASK, mid.upper(), mid, microtask_id=mid)
        machine.prepare_microtask(TASK, mid, targets)
        for status in ("READY", "ACTIVE", "DONE"):
            machine.transition(TASK, mid, status)
        machine.transition(TASK, mid, "VERIFIED", verification_evidence="ok")
    return storage, project


def resolve(storage, action):
    decision = ReconciliationService(storage).reconcile(TASK, "m2", "op_1")["DECISION"]
    out = ResolverService(storage).apply(TASK, "m2", "op_1", action, evidence_fingerprint=decision["evidence_fingerprint"],
                                         operation_revision=OperationStore(storage).get(TASK, "op_1").revision)
    return f"{action} {out['resolution'].result.value} ({decision['decision']})"


def verdict(storage):
    projection = ProjectionService(storage).build(TASK)
    states = [v["recovery"]["state"] for v in projection["operations"] if v["recovery"]]
    blockers = [b["code"] for b in projection["closeout"]]
    result = CloseoutService(storage).complete(TASK)["result"]
    return f"op recovery {states} | closeout blockers {blockers} | complete -> {result}"


def a1():
    with tempfile.TemporaryDirectory() as tmp:
        storage, _ = world(tmp)
        ops = OperationStore(storage)
        ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=b"after\n")
        ops.transition(TASK, "op_1", "STARTED")
        return f"A1 unsettled ABORT : {resolve(storage, 'ABORT')} | {verdict(storage)}"


def a7():
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = world(tmp)
        ops = OperationStore(storage)
        ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=b"after\n")
        ops.transition(TASK, "op_1", "FAILED")
        (project / "two.txt").write_bytes(b"after\n")
        return f"A7 ROLLBACK of VERIFIED stage : {resolve(storage, 'ROLLBACK')} | {verdict(storage)}"


if __name__ == "__main__":
    print(f"code root {sys.argv[1]}")
    print(a1())
    print(a7())
