"""RC-3 conflict gate under real concurrent OS processes.

Independent processes acting for different TASKs/operations race for target
ownership. One physical target must end with exactly one owner; distinct
targets must all be granted.
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

from web_alarm.operation_store import OperationStore
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
WORKERS = 8

CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.target_claim_service import TargetClaimService
storage, barrier, task_id, operation_id = sys.argv[1:5]
service = TargetClaimService(storage, lock_timeout=60)
Path(barrier, f"ready_{task_id}").touch()
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
outcome = service.acquire(task_id, operation_id, operation_revision=1, agent=task_id)
print(json.dumps({"task_id": task_id, "result": outcome["result"],
                  "claim_id": (outcome["claim"] or {}).get("claim_id"),
                  "blocking": (outcome["blocking_owner"] or {}).get("claim_id")}))
"""


class TargetClaimConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_race")
        self.tasks = TaskStore(self.storage)
        self.ops = OperationStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_operations(self, target_for):
        for index in range(WORKERS):
            task_id = f"task_{index}"
            target = target_for(index)
            path = self.project / target
            if not path.exists():
                path.write_bytes(b"before\n")
            self.tasks.create_task("ws_race", task_id, "RAW TASK", "Race", task_id=task_id)
            self.tasks.create_microtask(task_id, "M1", "Race step", microtask_id="m1")
            self.ops.begin(task_id, "m1", "write", target, operation_id="op", payload=b"after\n")

    def race(self, name):
        barrier = self.root / f"barrier_{name}"
        barrier.mkdir()
        processes = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", CHILD, str(self.storage), str(barrier), f"task_{index}", "op"],
                cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            for index in range(WORKERS)
        ]
        try:
            deadline = time.monotonic() + 60
            while len(list(barrier.glob("ready_*"))) < WORKERS:
                if time.monotonic() > deadline:
                    self.fail("workers did not reach the start barrier")
                time.sleep(0.01)
            (barrier / "go").touch()
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=120)
                self.assertEqual(process.returncode, 0, stderr)
                results.append(json.loads(stdout))
            return results
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()

    def test_cross_task_race_on_one_target_has_exactly_one_owner(self):
        self.make_operations(lambda index: "shared.txt")

        results = self.race("shared")

        counts = Counter(r["result"] for r in results)
        self.assertEqual(counts, Counter({"ACQUIRED": 1, "CONFLICT": WORKERS - 1}))
        winner = next(r for r in results if r["result"] == "ACQUIRED")
        self.assertTrue(all(r["blocking"] == winner["claim_id"] for r in results if r["result"] == "CONFLICT"))
        files = list((self.storage / "target_claims").glob("*.json"))
        self.assertEqual(len(files), 1)
        data = json.loads(files[0].read_text(encoding="utf-8"))  # store stays valid
        self.assertEqual((data["active"]["claim_id"], data["next_generation"], data["history"]),
                         (winner["claim_id"], 2, []))
        views = [TargetClaimService(self.storage).inspect(f"task_{i}", "op") for i in range(WORKERS)]
        self.assertEqual(sum(v["owned_by_operation"] for v in views), 1)

    def test_independent_targets_race_all_acquire(self):
        self.make_operations(lambda index: f"file_{index}.txt")

        results = self.race("distinct")

        self.assertEqual(Counter(r["result"] for r in results), Counter({"ACQUIRED": WORKERS}))
        self.assertEqual(len(list((self.storage / "target_claims").glob("*.json"))), WORKERS)


if __name__ == "__main__":
    unittest.main()
