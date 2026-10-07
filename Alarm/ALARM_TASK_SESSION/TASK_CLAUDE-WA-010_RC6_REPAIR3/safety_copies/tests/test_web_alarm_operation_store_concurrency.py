"""RC-1 storage-integrity tests with real concurrent OS processes.

They prove that Operation Store record/revision writes of one TASK are
serialized across processes. This is storage integrity only, not the RC-3
canonical-target conflict gate or mutation CAS.
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
from web_alarm.operation_store import OperationStore, OperationStoreError
from web_alarm.store_lock import InterProcessLock
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
WORKERS = 8

CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.operation_store import OperationConflictError, OperationStore
storage, barrier, mode, worker = sys.argv[1:5]
store = OperationStore(storage, lock_timeout=60)
Path(barrier, f"ready_{worker}").touch()
deadline = time.monotonic() + 60
while not Path(barrier, "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.0005)
out = {"worker": worker}
if mode == "same_id":
    try:
        result = store.begin("task_race", "m1", "write", "target.txt",
                             operation_id="op_same", request_payload={"worker": worker})
        out["created"] = result["created"]
    except OperationConflictError:
        out["conflict"] = True
elif mode == "same_transition":
    out["changed"] = store.transition("task_race", "op_shared", "STARTED")["changed"]
elif mode == "distinct":
    operation_id = f"op_{worker}"
    store.begin("task_race", "m1", "write", f"file_{worker}.txt",
                operation_id=operation_id, request_payload={"worker": worker})
    for status in ("STARTED", "UNKNOWN_AFTER_DISCONNECT"):
        store.transition("task_race", operation_id, status)
    out["revision"] = store.get("task_race", operation_id).revision
print(json.dumps(out))
"""

HOLD_AND_DIE = r"""
import os, sys
from web_alarm.store_lock import InterProcessLock
lock = InterProcessLock(sys.argv[1], timeout=10)
lock.acquire()
print("held", flush=True)
os._exit(0)
"""


class OperationStoreConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "target.txt").write_bytes(b"before")
        workspace = WorkspaceRegistry(self.storage).register(
            "Project", self.project, workspace_id="ws_race"
        )
        tasks = TaskStore(self.storage)
        tasks.create_task(
            workspace.workspace_id, "Race", "RAW TASK", "Race writers", task_id="task_race"
        )
        tasks.create_microtask("task_race", "M1", "Race step", microtask_id="m1")
        self.store = OperationStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def run_workers(self, mode: str) -> list[dict]:
        barrier = self.root / f"barrier_{mode}"
        barrier.mkdir()
        processes = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", CHILD, str(self.storage), str(barrier),
                 mode, str(index)],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
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

    def event_counts(self) -> Counter:
        # read_events is strict: any interleaved/torn line raises.
        events = EventCheckpointStore(self.storage).read_events("task_race")
        return Counter(event.event_type for event in events)

    def test_concurrent_begin_of_same_operation_id_creates_exactly_one_record(self):
        results = self.run_workers("same_id")

        created = [r for r in results if r.get("created") is True]
        conflicts = [r for r in results if r.get("conflict")]
        self.assertEqual(len(created), 1)
        self.assertEqual(len(conflicts), WORKERS - 1)
        winner = self.store.get("task_race", "op_same")
        self.assertEqual(winner.revision, 1)
        counts = self.event_counts()
        self.assertEqual(counts["OPERATION_INTENT"], 1)
        self.assertEqual(counts["OPERATION_REPLAY_CONFLICT"], WORKERS - 1)

    def test_concurrent_transition_is_applied_once_without_lost_revision(self):
        self.store.begin("task_race", "m1", "write", "target.txt", operation_id="op_shared")

        results = self.run_workers("same_transition")

        self.assertEqual(sum(1 for r in results if r["changed"]), 1)
        record = self.store.get("task_race", "op_shared")
        self.assertEqual(record.status.value, "STARTED")
        self.assertEqual(record.revision, 2)
        counts = self.event_counts()
        self.assertEqual(counts["OPERATION_TRANSITION"], 1)
        self.assertEqual(counts["OPERATION_TRANSITION_REPLAY"], WORKERS - 1)

    def test_concurrent_independent_writers_lose_no_record_revision_or_event(self):
        results = self.run_workers("distinct")

        self.assertEqual(sorted(r["revision"] for r in results), [3] * WORKERS)
        records = self.store.list("task_race")
        self.assertEqual(len(records), WORKERS)
        self.assertTrue(all(r.revision == 3 for r in records))
        counts = self.event_counts()
        self.assertEqual(counts["OPERATION_INTENT"], WORKERS)
        self.assertEqual(counts["OPERATION_TRANSITION"], 2 * WORKERS)

    def test_lock_of_a_crashed_process_is_released_by_the_os(self):
        lock_path = self.storage / "locks" / "operations" / "task_race.lock"
        completed = subprocess.run(
            [sys.executable, "-B", "-c", HOLD_AND_DIE, str(lock_path)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(completed.stdout.strip(), "held")

        with InterProcessLock(lock_path, timeout=2):
            pass
        result = OperationStore(self.storage, lock_timeout=2).begin(
            "task_race", "m1", "write", "target.txt", operation_id="op_after_crash"
        )
        self.assertTrue(result["created"])

    def test_lock_timeout_fails_closed_without_writing(self):
        lock_path = self.storage / "locks" / "operations" / "task_race.lock"
        with InterProcessLock(lock_path, timeout=2):
            with self.assertRaises(OperationStoreError):
                OperationStore(self.storage, lock_timeout=0.2).begin(
                    "task_race", "m1", "write", "target.txt", operation_id="op_blocked"
                )
        self.assertEqual(self.store.list("task_race"), [])


if __name__ == "__main__":
    unittest.main()
