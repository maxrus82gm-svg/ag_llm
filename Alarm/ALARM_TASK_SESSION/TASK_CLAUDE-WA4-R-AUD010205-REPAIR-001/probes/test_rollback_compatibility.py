"""Rollback compatibility (CLAUDE-WA4-R-AUD010205-REPAIR-001): a history written by the repaired writer,
including U+0085/U+2028/U+2029 payloads, is readable by the PRE-repair reader (baseline bytes, RAM only).
Disposable TEMP; the pre-repair method is taken byte-exact from ../baseline (AST slice)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.event_checkpoint_store as events
from quality_controls_aud010205 import pre_repair

TASK = "task_rb"


class RollbackCompatibility(unittest.TestCase):
    def test_pre_repair_reader_reads_history_written_by_repaired_writer(self):
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        temp = tempfile.TemporaryDirectory(prefix="wa_aud_rb_")
        self.addCleanup(temp.cleanup)
        storage, project = Path(temp.name) / "state", Path(temp.name) / "project"
        project.mkdir()
        WorkspaceRegistry(storage).register("rb", project, workspace_id="ws_rb")
        TaskStore(storage).create_task("ws_rb", "rb", "synthetic RAW TASK", "rollback", task_id=TASK)
        store = events.EventCheckpointStore(storage)
        written = [{"note": f"a{chr(c)}b"} for c in (0x85, 0x2028, 0x2029)]
        for payload in written:
            store.append_event(TASK, "RB_PROBE", payload=payload)
        old_reader = pre_repair(events, "EventCheckpointStore", "read_events")
        with mock.patch.object(events.EventCheckpointStore, "read_events", old_reader):
            read_back = [e.payload for e in events.EventCheckpointStore(storage).read_events(TASK)
                         if e.event_type == "RB_PROBE"]
        self.facts = [{"written": len(written), "read_by_pre_repair_reader": len(read_back)}]
        self.assertEqual(read_back, written)


if __name__ == "__main__":
    unittest.main()
