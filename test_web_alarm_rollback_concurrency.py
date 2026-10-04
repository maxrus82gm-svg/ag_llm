"""RC-4 rollback vs normal RC-3 owners under real concurrent OS processes.

Several processes apply the same rollback while processes of other TASKs try to
claim the same physical target. Either the rollback wins (one restore, no
foreign owner) or one foreign operation wins (no restore at all) — never both,
and the restore never happens twice.
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
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
APPLIERS = 4
CLAIMERS = 4
ROUNDS = 4
BEFORE, AFTER = b"before\n", b"after\n"

CHILD = r"""
import json, random, sys, time
from pathlib import Path
from web_alarm.rollback_service import RollbackService
from web_alarm.target_claim_service import TargetClaimService
storage, barrier, name, mode, task_id, ident, jitter = sys.argv[1:8]
service = RollbackService(storage, lock_timeout=60) if mode == "rollback" else TargetClaimService(storage, lock_timeout=60)
Path(barrier, f"ready_{name}").touch()
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
if mode == "rollback":
    outcome = service.apply(task_id, ident)
else:
    if jitter == "1":
        time.sleep(random.uniform(0, 0.4))  # let both race orders actually occur
    outcome = service.acquire(task_id, ident, operation_revision=1)
print(json.dumps({"mode": mode, "result": outcome["result"]}))
"""


class RollbackRaceTests(unittest.TestCase):
    def round(self, root: Path, jitter: bool) -> tuple[list[dict], dict, bytes, Counter]:
        storage, project = root / "state", root / "project"
        project.mkdir()
        (project / "target.txt").write_bytes(BEFORE)
        (project / "keep.txt").write_bytes(b"keep\n")
        WorkspaceRegistry(storage).register("Project", project, workspace_id="ws")
        tasks, ops = TaskStore(storage), OperationStore(storage)
        for task in ["task_rb"] + [f"task_c{i}" for i in range(CLAIMERS)]:
            tasks.create_task("ws", task, "RAW TASK", "Race", task_id=task)
            tasks.create_microtask(task, "M1", "Step", microtask_id="m1")
        ManifestSnapshotStore(storage).prepare_microtask(
            "task_rb", "m1", [("target.txt", "edit"), ("keep.txt", "delete")])
        ops.begin("task_rb", "m1", "write", "target.txt", operation_id="op_1", payload=AFTER)
        ops.transition("task_rb", "op_1", "STARTED")
        (project / "target.txt").write_bytes(AFTER)
        decision = ReconciliationService(storage).reconcile("task_rb", "m1", "op_1")["DECISION"]
        resolution = ResolverService(storage).apply(
            "task_rb", "m1", "op_1", "ROLLBACK",
            evidence_fingerprint=decision["evidence_fingerprint"], operation_revision=2)["resolution"]
        rollback_id = RollbackService(storage).prepare(
            "task_rb", "m1", "op_1", resolution.resolution_id)["rollback"]["rollback_id"]
        for i in range(CLAIMERS):  # foreign operations whose CAS basis is the current AFTER state
            ops.begin(f"task_c{i}", "m1", "write", "target.txt", operation_id="op_c", payload=b"x\n")

        barrier = root / "barrier"
        barrier.mkdir()
        jobs = [(f"rb{i}", "rollback", "task_rb", rollback_id) for i in range(APPLIERS)]
        jobs += [(f"c{i}", "claim", f"task_c{i}", "op_c") for i in range(CLAIMERS)]
        processes = [
            subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(storage), str(barrier), *job,
                              "1" if jitter else "0"],
                             cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for job in jobs
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
        record = RollbackService(storage).inspect("task_rb", rollback_id)
        events = Counter(e.event_type for e in EventCheckpointStore(storage).read_events("task_rb"))
        return results, record, (project / "target.txt").read_bytes(), events

    def test_rollback_and_normal_owner_never_both_win(self):
        outcomes = Counter()
        for index in range(ROUNDS):  # even rounds: maximum contention; odd: jittered order
            with tempfile.TemporaryDirectory() as tmp:
                results, record, final, events = self.round(Path(tmp), jitter=bool(index % 2))
            acquired = sum(1 for r in results if r["mode"] == "claim" and r["result"] == "ACQUIRED")
            restored = events["ROLLBACK_TARGET_RESTORED"]
            self.assertLessEqual(restored, 1)  # never a second destructive write
            if record["status"] == "VERIFIED":
                outcomes["rollback_won"] += 1
                self.assertEqual((acquired, restored, final), (0, 1, BEFORE))
            else:
                outcomes["owner_won"] += 1
                self.assertEqual(record["status"], "PRESERVED")
                self.assertEqual((acquired, restored, final), (1, 0, AFTER))
        self.assertEqual(sum(outcomes.values()), ROUNDS)


if __name__ == "__main__":
    unittest.main()
