"""Additional FINDING probe (not fixed in Repair #3): WA-1.4 prepare crash windows.

ManifestSnapshotStore.prepare_microtask writes PREPARING (CAS), captures the
restore point in a stage directory, publishes it with os.replace and only then
writes BACKUP_VERIFIED. A process crash
  W1: after the PREPARING write, before publication;
  W2: after publication, before the BACKUP_VERIFIED write,
leaves the microtask PREPARING. PREPARING has no state-machine exit and the state
machine prepares only from PLANNED / BLOCKED_PREPARE, so no workflow tool can
finish or redo the preparation (W2: "restore point already exists" as well).
Temp storage only.
"""
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from web_alarm.models import MicrotaskStatus  # noqa: E402
from web_alarm.projection import ProjectionService  # noqa: E402
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402
from web_alarm.state_machine import ServerStateMachine, TransitionRejected  # noqa: E402
from web_alarm.task_store import TaskStore  # noqa: E402
from web_alarm.workspace_registry import WorkspaceRegistry  # noqa: E402

CHILD = """
    import os, shutil
    from web_alarm.manifest_store import ManifestSnapshotStore
    from web_alarm.state_machine import ServerStateMachine
    from web_alarm.task_store import TaskStore
    window = {window!r}
    if window == "W1":
        real = ManifestSnapshotStore._resolve_target
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
    ServerStateMachine({storage!r}).prepare_microtask("task_p", "m1", [("a.txt", "edit")])
"""

for window in ("W1", "W2"):
    with tempfile.TemporaryDirectory() as tmp:
        storage, project = Path(tmp) / "state", Path(tmp) / "project"
        project.mkdir()
        (project / "a.txt").write_bytes(b"before\n")
        WorkspaceRegistry(storage).register("P", project, workspace_id="ws_p")
        tasks = TaskStore(storage)
        tasks.create_task("ws_p", "P", "RAW", "P", task_id="task_p")
        tasks.create_microtask("task_p", "M1", "m1", microtask_id="m1")
        proc = subprocess.run([sys.executable, "-B", "-c", textwrap.dedent(CHILD.format(window=window, storage=str(storage)))],
                              cwd=Path.cwd(), capture_output=True, text=True)
        status = tasks.open_microtask("task_p", "m1").status.value
        work = tasks.microtask_directory("task_p", "m1")
        published = (work / "restore_point" / "manifest.json").is_file()
        stages = sorted(p.name for p in work.glob(".restore.*"))
        try:
            ServerStateMachine(storage).prepare_microtask("task_p", "m1", [("a.txt", "edit")])
            retry = "prepare again: OK"
        except TransitionRejected as exc:
            retry = f"prepare again: REJECTED ({exc.reason})"
        except Exception as exc:  # noqa: BLE001
            retry = f"prepare again: {type(exc).__name__}: {exc}"
        projection = ProjectionService(storage).build("task_p")
        recover = RecoveryCoordinator(storage).recover("task_p")
        print(f"{window}: exit={proc.returncode} status={status} restore_point_published={published} "
              f"stage_dirs={len(stages)} | {retry} | NEXT={projection['next_safe_action']!r} | recover={recover['state']}")
print("FINDING: PREPARING after a crash has no workflow exit (manual repair only)")
