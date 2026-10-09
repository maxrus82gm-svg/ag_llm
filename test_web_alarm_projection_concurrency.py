"""RC-5 races under real concurrent OS processes (start barrier, test-only widened windows).

W: gated TASK completion vs a new operation / microtask for the same TASK —
   never "TASK completed" + "new open state admitted inside it".
X: checkpoint rebuild vs an authoritative change — a later validation never
   calls a checkpoint VALID unless it equals the fresh projection.
   F-6 (CLAUDE-WA-017): a rebuild may fail closed (ProjectionError, e.g. a
   Windows sharing violation on its atomic replace); that is not lost data. A
   rebuild that reports success must leave a checkpoint behind.
Two rebuilders: serialized; JSON and Markdown always belong together.
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService, checkpoint_fields
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
ROUNDS = 4

CHILD = r"""
import json, random, sys, time
from pathlib import Path
storage, barrier, name, mode, jitter = sys.argv[1:6]
import web_alarm.projection as projection_module
from web_alarm.closeout import CloseoutService
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService
from web_alarm.task_store import TaskStore
import web_alarm.event_checkpoint_store as ecs
if mode == "complete":
    real = projection_module.ProjectionService.build
    def widened(self, task_id):  # test-only: hold the inspect -> complete window open
        result = real(self, task_id)
        time.sleep(0.3)
        return result
    projection_module.ProjectionService.build = widened
    service = CloseoutService(storage, lock_timeout=60)
elif mode in ("rebuild", "rebuild_fail"):
    real_write = ecs.EventCheckpointStore.write_checkpoint
    def slow_write(self, record):  # test-only: projection built, file not written yet
        time.sleep(0.3)
        return real_write(self, record)
    ecs.EventCheckpointStore.write_checkpoint = slow_write
    if mode == "rebuild_fail":  # test-only: the atomic replace is refused (a Windows sharing violation)
        real_replace = ecs.os.replace
        def refuse(src, dst):
            if Path(dst).name == "checkpoint.json":
                raise PermissionError(13, "sharing violation (test)", str(dst))
            return real_replace(src, dst)
        ecs.os.replace = refuse
    service = ProjectionService(storage, lock_timeout=60)
elif mode in ("begin", "transition"):
    service = OperationStore(storage, lock_timeout=60)
else:
    service = TaskStore(storage, lock_timeout=60)
Path(barrier, f"ready_{name}").touch()
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
if jitter == "1":
    time.sleep(random.uniform(0, 0.6))
try:
    if mode == "complete":
        outcome = service.complete("task_r")
        result = outcome["result"]
    elif mode in ("rebuild", "rebuild_fail"):
        service.rebuild_checkpoint("task_r")
        result = "REBUILT"
    elif mode == "begin":
        service.begin("task_r", "m2", "write", "two.txt", operation_id="op_" + name, payload=b"x\n")
        result = "BEGUN"
    elif mode == "transition":
        service.transition("task_r", "op_seed", "STARTED")
        result = "TRANSITIONED"
    else:
        service.create_microtask("task_r", "late", "late", microtask_id="late_" + name)
        result = "CREATED"
except Exception as exc:
    result = "FAILED:" + type(exc).__name__
print(json.dumps({"name": name, "mode": mode, "result": result}))
"""


class ProjectionRaceTests(unittest.TestCase):
    def setup_task(self, root: Path, *, verified: bool) -> Path:
        storage, project = root / "state", root / "project"
        project.mkdir()
        WorkspaceRegistry(storage).register("Project", project, workspace_id="ws")
        tasks = TaskStore(storage)
        tasks.create_task("ws", "task_r", "RAW", "Race", task_id="task_r")
        machine = ServerStateMachine(storage)
        for microtask_id, target in (("m1", "one.txt"), ("m2", "two.txt")):
            tasks.create_microtask("task_r", microtask_id, "step", microtask_id=microtask_id)
            if verified:
                (project / target).write_bytes(b"before\n")
                machine.prepare_microtask("task_r", microtask_id, [(target, "edit")])
                for status in ("READY", "ACTIVE", "DONE"):
                    machine.transition("task_r", microtask_id, status)
                machine.transition("task_r", microtask_id, "VERIFIED", verification_evidence="ok")
        return storage

    def run_jobs(self, storage: Path, root: Path, jobs, jitter: bool) -> list[dict]:
        barrier = root / "barrier"
        barrier.mkdir()
        processes = [
            subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(storage), str(barrier), name, mode,
                              "1" if jitter and mode not in ("complete", "rebuild", "rebuild_fail") else "0"],
                             cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for name, mode in jobs
        ]
        try:
            deadline = time.monotonic() + 60
            while len(list(barrier.glob("ready_*"))) < len(jobs):
                if time.monotonic() > deadline:
                    self.fail("workers did not reach the start barrier")
                time.sleep(0.01)
            (barrier / "go").touch()
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=120)
                self.assertEqual(process.returncode, 0, stderr)
                results.append(json.loads(stdout))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
        return results

    def test_completion_never_admits_new_open_state(self):  # W
        outcomes = Counter()
        for index in range(ROUNDS):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage = self.setup_task(root, verified=True)
                jobs = [("a", "complete"), ("b1", "begin"), ("b2", "begin"), ("c1", "microtask")]
                results = self.run_jobs(storage, root, jobs, jitter=bool(index % 2))
                by_mode = {r["name"]: r["result"] for r in results}
                completed_dir = storage / "tasks" / "completed" / "task_r"
                active_dir = storage / "tasks" / "active" / "task_r"
                if by_mode["a"] == "COMPLETED":
                    outcomes["completion_won"] += 1
                    self.assertTrue(completed_dir.is_dir())
                    self.assertFalse(active_dir.exists())  # no write recreated the active TASK
                    ops = OperationStore(storage).list("task_r")
                    self.assertEqual([op.operation_id for op in ops], [])  # nothing admitted inside
                    plan = TaskStore(storage).open_plan("task_r")
                    self.assertEqual(plan.microtask_ids, ["m1", "m2"])
                    self.assertTrue(all(r["result"].startswith("FAILED") for r in results if r["name"] != "a"))
                else:
                    outcomes["writer_won"] += 1
                    self.assertEqual(by_mode["a"], "REJECTED")
                    self.assertTrue(active_dir.is_dir())
                    self.assertFalse(completed_dir.exists())
                    admitted = [r for r in results if r["result"] in ("BEGUN", "CREATED")]
                    self.assertTrue(admitted)
        self.assertEqual(sum(outcomes.values()), ROUNDS)

    def race_rebuild(self, rebuild_mode: str) -> Counter:
        outcomes = Counter()
        for _ in range(ROUNDS):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage = self.setup_task(root, verified=False)
                (root / "project" / "two.txt").write_bytes(b"before\n")
                OperationStore(storage).begin("task_r", "m2", "write", "two.txt", operation_id="op_seed",
                                              payload=b"after\n")
                jobs = [("r", rebuild_mode), ("m", "microtask"), ("t", "transition")]
                rebuild = {r["name"]: r["result"] for r in self.run_jobs(storage, root, jobs, jitter=True)}["r"]
                # F-6: the only admissible rebuild failure is the fail-closed ProjectionError
                self.assertIn(rebuild, ("REBUILT", "FAILED:ProjectionError"))
                service = ProjectionService(storage)
                projection = service.build("task_r")
                validation = service.validate_checkpoint("task_r", projection)
                checkpoint_file = TaskStore(storage).task_directory("task_r") / "checkpoint.json"
                outcomes[(rebuild, validation["status"])] += 1
                if checkpoint_file.is_file():
                    state = EventCheckpointStore(storage)
                    record = state.read_checkpoint("task_r")
                    matches = (
                        record.projection is not None
                        and record.projection["source_fingerprint"] == projection["source_fingerprint"]
                        and checkpoint_fields(projection) == {
                            "last_verified_microtask_id": record.last_verified_microtask_id,
                            "current_microtask_id": record.current_microtask_id,
                            "current_status": record.current_status.value,
                            "snapshot_status": record.snapshot_status,
                            "last_operation_id": record.last_operation_id,
                            "next_safe_action": record.next_safe_action,
                        }
                        and state.checkpoint_markdown("task_r") == state.render_checkpoint_md(record)
                    )
                    self.assertEqual(validation["status"] == "VALID", matches)  # never falsely VALID
                    self.assertIn(validation["status"], ("VALID", "STALE", "INCONSISTENT"))
                else:
                    # nothing existed before the race: only a rebuild that failed may leave none;
                    # a rebuild reporting success without a checkpoint would be lost data
                    self.assertEqual((rebuild, validation["status"]), ("FAILED:ProjectionError", "MISSING"))
                self.assertEqual(service.rebuild_checkpoint("task_r")["validation"]["status"], "VALID")
        self.assertEqual(sum(outcomes.values()), ROUNDS)
        return outcomes

    def test_rebuild_racing_an_authoritative_change_is_never_falsely_valid(self):  # X
        self.race_rebuild("rebuild")

    def test_a_failed_rebuild_in_the_race_fails_closed_and_loses_nothing(self):  # X, F-6
        outcomes = self.race_rebuild("rebuild_fail")
        self.assertEqual(set(outcomes), {("FAILED:ProjectionError", "MISSING")})

    def test_concurrent_rebuilders_keep_json_and_markdown_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = self.setup_task(root, verified=True)
            self.run_jobs(storage, root, [("r1", "rebuild"), ("r2", "rebuild"), ("r3", "rebuild")], jitter=False)
            validation = ProjectionService(storage).validate_checkpoint("task_r")
            self.assertEqual(validation["status"], "VALID", validation["reasons"])


if __name__ == "__main__":
    unittest.main()
