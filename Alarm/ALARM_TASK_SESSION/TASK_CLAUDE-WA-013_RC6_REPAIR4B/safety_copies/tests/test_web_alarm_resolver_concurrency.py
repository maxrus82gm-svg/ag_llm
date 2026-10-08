"""RC-2: concurrent duplicate Resolver apply from real OS processes.

Exactly one process may create the resolution; the others must replay it.
This is Resolver-store integrity, not the RC-3 target conflict gate.
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
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
WORKERS = 8

CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.resolver_service import ResolverService
storage, barrier, worker, fingerprint, revision = sys.argv[1:6]
resolver = ResolverService(storage)
Path(barrier, f"ready_{worker}").touch()
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
result = resolver.apply("task_race", "m1", "op_1", "RETRY",
                        evidence_fingerprint=fingerprint, operation_revision=int(revision),
                        agent=f"worker-{worker}")
print(json.dumps({"created": result["created"], "accepted": result["accepted"],
                  "resolution_id": result["resolution"].resolution_id}))
"""


class ResolverConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        project = self.root / "project"
        project.mkdir()
        (project / "target.txt").write_bytes(b"before\n")
        WorkspaceRegistry(self.storage).register("Project", project, workspace_id="ws_race")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_race", "Race", "RAW TASK", "Resolver race", task_id="task_race")
        tasks.create_microtask("task_race", "M1", "Race step", microtask_id="m1")
        ManifestSnapshotStore(self.storage).prepare_microtask(
            "task_race", "m1", [("target.txt", "edit")]
        )
        operations = OperationStore(self.storage)
        operations.begin("task_race", "m1", "write", "target.txt",
                         operation_id="op_1", payload=b"after\n")
        operations.transition("task_race", "op_1", "STARTED")
        decision = ReconciliationService(self.storage).reconcile(
            "task_race", "m1", "op_1"
        )["DECISION"]
        self.assertEqual(decision["decision"], "RETRY_SAFE")
        self.fingerprint = decision["evidence_fingerprint"]
        self.revision = operations.get("task_race", "op_1").revision

    def tearDown(self):
        self.tempdir.cleanup()

    def test_concurrent_duplicate_apply_creates_one_successful_resolution(self):
        barrier = self.root / "barrier"
        barrier.mkdir()
        processes = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", CHILD, str(self.storage), str(barrier),
                 str(index), self.fingerprint, str(self.revision)],
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
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()

        self.assertEqual(sum(1 for r in results if r["created"]), 1)
        self.assertTrue(all(r["accepted"] for r in results))
        self.assertEqual(len({r["resolution_id"] for r in results}), 1)
        files = list((self.storage / "tasks" / "active" / "task_race" / "resolutions").glob("*.json"))
        self.assertEqual(len(files), 1)
        counts = Counter(
            event.event_type
            for event in EventCheckpointStore(self.storage).read_events("task_race")
        )
        self.assertEqual(counts["RESOLUTION_ACCEPTED"], 1)


if __name__ == "__main__":
    unittest.main()
