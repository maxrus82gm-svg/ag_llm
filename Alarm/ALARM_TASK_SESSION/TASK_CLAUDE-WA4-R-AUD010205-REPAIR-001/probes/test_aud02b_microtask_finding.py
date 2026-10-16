"""FINDING probe AUD-02b (state_machine microtask transition), CLAUDE-WA4-R-AUD010205-REPAIR-001.

Not a repair: state_machine.py is outside this TASK's write-scope. Same class as AUD-02 (durable
record before its history event), on the microtask lifecycle instead of operation admission.
Invariant: a transition refused because the history is unreadable changes no persisted status.
A FAIL is the reproduced defect. Disposable TEMP only; real HTTP handler path.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

TASK = "task_aud02b"


class MicrotaskTransitionFinding(unittest.TestCase):
    def setUp(self):
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.temp = tempfile.TemporaryDirectory(prefix="wa_aud02b_")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.storage, project = base / "state", base / "project"
        project.mkdir()
        (project / "data.bin").write_bytes(b"pre")
        WorkspaceRegistry(self.storage).register("aud02b", project, workspace_id="ws_aud02b")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_aud02b", "aud02b", "synthetic RAW TASK", "finding", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        machine.transition(TASK, "m1", "READY")
        machine.transition(TASK, "m1", "ACTIVE")
        self.task_dir = self.storage / "tasks" / "active" / TASK
        self.facts = [{"task": "CLAUDE-WA4-R-AUD010205-REPAIR-001", "finding": "AUD-02b", "test": self.id()}]

    def test_transition_on_torn_history_changes_no_persisted_status(self):
        from web_alarm.server import ApiError, WebAlarmApi
        events = self.task_dir / "events.jsonl"
        events.write_bytes(events.read_bytes()[:-1])  # unterminated tail (crash shape)
        micro = self.task_dir / "microtasks" / "m1.json"
        before = {"m1": hashlib.sha256(micro.read_bytes()).hexdigest(),
                  "events": hashlib.sha256(events.read_bytes()).hexdigest()}
        try:
            status, _ = WebAlarmApi(self.storage).dispatch(
                "POST", "/microtasks/m1/transition", {"task_id": TASK, "target_status": "DONE"})
            http = [status]
        except ApiError as exc:
            http = [exc.status, exc.code, str(exc.details)[:200]]
        after_status = json.loads(micro.read_bytes())["status"]
        self.facts.append({"http": http, "m1_status_after": after_status,
                           "m1_changed": hashlib.sha256(micro.read_bytes()).hexdigest() != before["m1"],
                           "events_changed": hashlib.sha256(events.read_bytes()).hexdigest() != before["events"]})
        self.assertEqual(after_status, "ACTIVE", "microtask status persisted although its history event was refused")


if __name__ == "__main__":
    unittest.main()
