"""CLAUDE-WA-017 F-5: crash windows of TASK completion (temp storage only).

Run from the repository root:  python -B <this file> [<code root>]   (default: the current tree)
A child process completes a clean TASK through the public gate (CloseoutService.complete) and is
killed with os._exit(9) at a chosen point of TaskStore.complete_task_locked:
  status_written : after task.json is written COMPLETED, before the directory move (pre-fix order)
  moved          : after the directory move (the move happens before the status write)
  before_move    : the directory move is the next step (nothing durable yet)
For each window the parent then shows, from fresh processes' point of view:
  where the TASK is and its status; projection NEXT / authority; closeout verdict; RemoteEntry;
  whether writers still accept it (operation begin, microtask create, Resolver, manifest prepare);
  whether a microtask can still get ACTIVE (mutation authority needs ACTIVE); and whether a second
  public `task complete` converges.
"""
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

CODE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
sys.path.insert(0, str(CODE))

from web_alarm.closeout import CloseoutService  # noqa: E402
from web_alarm.manifest_store import ManifestSnapshotStore  # noqa: E402
from web_alarm.operation_store import OperationStore  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.remote_entry import RemoteEntry  # noqa: E402
from web_alarm.state_machine import ServerStateMachine  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

TASK = "task_f5"
CHILD = """
    import os, sys
    sys.path.insert(0, {code!r})
    import web_alarm.task_store as ts
    from pathlib import Path
    point = {point!r}
    real_replace, real_write = ts.os.replace, ts.TaskStore._write_task
    def replace(src, dst):
        if Path(src).is_dir():                 # the directory move of complete_task_locked
            if point == "before_move":
                os._exit(9)
            real_replace(src, dst)
            if point == "moved":
                os._exit(9)
            return None
        return real_replace(src, dst)
    def write_task(self, task_dir, record):
        real_write(self, task_dir, record)
        if point == "status_written" and record.status.value == "COMPLETED":
            os._exit(9)
    ts.os.replace = replace
    ts.TaskStore._write_task = write_task
    from web_alarm.closeout import CloseoutService
    print(CloseoutService({storage!r}).complete({task!r})["result"])
"""


def world(tmp):
    storage, project = Path(tmp) / "state", Path(tmp) / "project"
    project.mkdir()
    (project / "one.txt").write_bytes(b"one\n")
    (project / "two.txt").write_bytes(b"two\n")
    WorkspaceRegistry(storage).register("F5", project, workspace_id="ws_f5")
    tasks = TaskStore(storage)
    tasks.create_task("ws_f5", "F5", "RAW", "f5", task_id=TASK)
    tasks.create_microtask(TASK, "M1", "m1", microtask_id="m1")
    machine = ServerStateMachine(storage)
    machine.prepare_microtask(TASK, "m1", [("one.txt", "edit")])
    for status in ("READY", "ACTIVE", "DONE"):
        machine.transition(TASK, "m1", status)
    machine.transition(TASK, "m1", "VERIFIED", verification_evidence="ok")
    return storage


def attempt(label, fn):
    try:
        fn()
        return f"{label}: ACCEPTED"
    except Exception as exc:  # noqa: BLE001
        return f"{label}: refused ({type(exc).__name__})"


def inspect(storage):
    tasks = TaskStore(storage)
    active, completed = (tasks.active_dir / TASK).is_dir(), (tasks.completed_dir / TASK).is_dir()
    status = tasks.open_task(TASK).status.value
    projection = ProjectionService(storage).build(TASK)
    verdict = CloseoutService(storage).inspect(TASK)
    try:
        entry = RemoteEntry(storage).active_task_ids()
    except Exception as exc:  # noqa: BLE001
        entry = f"ERROR {type(exc).__name__}: {exc}"
    writers = [
        attempt("operation begin", lambda: OperationStore(storage).begin(
            TASK, "m1", "write", "two.txt", operation_id="op_late", payload=b"late\n")),
        attempt("microtask create", lambda: TaskStore(storage).create_microtask(TASK, "late", "late", microtask_id="late")),
        attempt("manifest restore-point write", lambda: ManifestSnapshotStore(storage).prepare_microtask(
            TASK, "m1", [("two.txt", "edit")])),
        attempt("checkpoint rebuild", lambda: ProjectionService(storage).rebuild_checkpoint(TASK)),
    ]
    return {
        "dir": "active" if active else ("completed" if completed else "MISSING"),
        "status": status,
        "NEXT": projection["next_safe_action"][:150],
        "authority": projection["authority_source"],
        "closeout": [b["code"] for b in verdict["blockers"]],
        "remote_entry_active": entry,
        "writers": writers,
        "ops_after": [op.operation_id for op in OperationStore(storage).list(TASK)],
    }


def scenario(point):
    with tempfile.TemporaryDirectory() as tmp:
        storage = world(tmp)
        child = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(CHILD.format(
            code=str(CODE), point=point, storage=str(storage), task=TASK))],
            cwd=str(CODE), capture_output=True, text=True, timeout=120)
        print(f"== crash point {point}: child exit {child.returncode} {child.stdout.strip()} {child.stderr.strip()[-120:]}")
        for key, value in inspect(storage).items():
            print(f"   {key}: {json.dumps(value, ensure_ascii=False)}")
        try:
            second = CloseoutService(storage).complete(TASK)
            outcome = f"{second['result']} (resumed={second.get('resumed')})"
        except Exception as exc:  # noqa: BLE001
            outcome = f"ERROR {type(exc).__name__}: {exc}"
        tasks = TaskStore(storage)
        where = "active" if (tasks.active_dir / TASK).is_dir() else "completed"
        print(f"   second public complete: {outcome} -> dir={where}, status={tasks.open_task(TASK).status.value}")
        print(f"   NEXT after: {ProjectionService(storage).build(TASK)['next_safe_action'][:150]!r}")


if __name__ == "__main__":
    print(f"code root: {CODE}")
    for point in ("status_written", "moved", "before_move"):
        scenario(point)
