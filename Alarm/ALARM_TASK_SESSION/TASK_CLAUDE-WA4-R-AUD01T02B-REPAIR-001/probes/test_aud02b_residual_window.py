"""RESIDUAL WINDOW characterization (not a product PASS), CLAUDE-WA4-R-AUD01T02B-REPAIR-001.

A real process death (os._exit) between the persisted compare-and-set and the MICROTASK_TRANSITION
append. The repair keeps both in one locked section and refuses every step whose event is known to
be impossible, but no lock survives a process death: this probe documents what remains after a fresh
process re-opens the storage. Each test asserts the OBSERVED residual state so that a future
transactional/reconciliation contract turns it red on purpose. Disposable TEMP only.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TASK = "task_residual"

CRASH_BETWEEN_STATUS_AND_EVENT = r'''
import os, sys
from pathlib import Path
from unittest import mock
sys.path.insert(0, sys.argv[1])
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.state_machine import ServerStateMachine
real = EventCheckpointStore.append_event
def dying(store, task_id, event_type, **kwargs):
    if event_type == "MICROTASK_TRANSITION":
        os._exit(70)  # the status is already persisted under the mutation lock
    return real(store, task_id, event_type, **kwargs)
with mock.patch.object(EventCheckpointStore, "append_event", dying):
    ServerStateMachine(Path(sys.argv[2])).transition(sys.argv[3], "m1", "DONE")
sys.exit(3)
'''


class ResidualCrashWindow(unittest.TestCase):
    def setUp(self):
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.temp = tempfile.TemporaryDirectory(prefix="aud02b_residual_")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.storage, project = base / "state", base / "project"
        project.mkdir()
        (project / "data.bin").write_bytes(b"pre")
        WorkspaceRegistry(self.storage).register("r", project, workspace_id="ws_r")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_r", "r", "RAW", "residual", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        machine.transition(TASK, "m1", "READY")
        machine.transition(TASK, "m1", "ACTIVE")
        self.facts = [{"task": "CLAUDE-WA4-R-AUD01T02B-REPAIR-001", "kind": "RESIDUAL_WINDOW", "test": self.id()}]

    def test_process_death_after_status_before_event_leaves_an_unrecorded_step(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        task_dir = self.storage / "tasks" / "active" / TASK
        before = (task_dir / "events.jsonl").read_bytes()
        proc = subprocess.run([sys.executable, "-B", "-c", CRASH_BETWEEN_STATUS_AND_EVENT, str(REPO),
                               str(self.storage), TASK], capture_output=True, timeout=120)
        status = json.loads((task_dir / "microtasks" / "m1.json").read_bytes())["status"]
        after = (task_dir / "events.jsonl").read_bytes()
        events = EventCheckpointStore(self.storage).read_events(TASK)  # fresh reader, history still readable
        blockers = [b["code"] for b in CloseoutService(self.storage).inspect(TASK)["blockers"]]
        self.facts.append({"child_exit": proc.returncode, "m1_status": status, "history_unchanged": after == before,
                           "last_event": events[-1].event_type if events else None, "closeout_blockers": blockers})
        self.assertEqual(proc.returncode, 70, proc.stderr.decode(errors="replace")[-600:])
        # RESIDUAL (documented, not fixed): the step is persisted, its event is not, and nothing flags it.
        self.assertEqual(status, "DONE")
        self.assertEqual(after, before)
        self.assertNotIn("HISTORY_UNREADABLE", " ".join(blockers))


if __name__ == "__main__":
    unittest.main()
