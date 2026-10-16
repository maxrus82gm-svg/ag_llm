"""Rollback / mixed-version compatibility, CLAUDE-WA4-R-AUD01T02B-REPAIR-001 (TEMP only).

The pre-repair modules are loaded byte-exact from ../baseline/web_alarm/ into RAM (they import the
current package's models), so a rollback of the code can be checked against data written by the
repaired code and the other way round. Oracles split raw bytes on the physical LF.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASELINE = Path(__file__).resolve().parent.parent / "baseline" / "web_alarm"
SEPARATORS = (chr(0x85), chr(0x2028), chr(0x2029))
PINS = {
    "transport_event_store.py": "107a8e89cff2ffaae2a6eb899d0028e1c2a46788e12edfc3de5b9448a3b020cf",
    "event_checkpoint_store.py": "7342b221e6663bee65bef116f57507b0de84b74269cb7541f4955b527eb91304",
}


def load_baseline(name: str):
    path = BASELINE / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PINS[name], f"baseline copy drifted: {name}"
    spec = importlib.util.spec_from_file_location(f"web_alarm._pre_repair_{name[:-3]}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


class RollbackCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aud01t02b_compat_")
        self.addCleanup(self.temp.cleanup)
        self.storage = Path(self.temp.name) / "state"
        self.facts = [{"task": "CLAUDE-WA4-R-AUD01T02B-REPAIR-001", "test": self.id()}]

    def test_pre_repair_transport_reader_reads_repaired_writer_log(self):
        from web_alarm.transport_event_store import TransportEventStore
        old = load_baseline("transport_event_store.py")
        new = TransportEventStore(self.storage)
        for index, ch in enumerate(SEPARATORS):
            new.append("REMOTE_OFFLINE", event_id=f"n_{index}", error_class=f"e{ch}x", payload={"note": f"a{ch}b"})
        got = [(e.event_id, e.error_class, e.payload) for e in old.TransportEventStore(self.storage).read_events()]
        self.facts.append({"old_reader_records": len(got)})
        self.assertEqual(got, [(f"n_{i}", f"e{ch}x", {"note": f"a{ch}b"}) for i, ch in enumerate(SEPARATORS)])

    def test_mixed_versions_append_to_one_transport_log(self):
        """Rolled-back code may append (raw separators); the repaired reader still reads every record."""
        from web_alarm.transport_event_store import TransportEventStore
        old = load_baseline("transport_event_store.py")
        TransportEventStore(self.storage).append("REMOTE_ONLINE", event_id="new_1", payload={"note": "n"})
        old.TransportEventStore(self.storage).append("REMOTE_OFFLINE", event_id="old_1",
                                                     payload={"note": "o" + SEPARATORS[1]})
        TransportEventStore(self.storage).append("REMOTE_RECOVERED", event_id="new_2", payload={"note": "m"})
        data = (self.storage / "transport" / "transport_events.jsonl").read_bytes()
        raw = [json.loads(chunk) for chunk in data.split(b"\n")[:-1]]
        self.assertEqual([r["event_id"] for r in raw], ["new_1", "old_1", "new_2"])
        self.assertEqual([e.event_id for e in TransportEventStore(self.storage).read_events()],
                         ["new_1", "old_1", "new_2"])

    def test_pre_repair_event_store_reads_history_written_with_the_events_lock(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        project = Path(self.temp.name) / "project"
        project.mkdir()
        WorkspaceRegistry(self.storage).register("c", project, workspace_id="ws_c")
        TaskStore(self.storage).create_task("ws_c", "c", "RAW", "compat", task_id="task_c")
        new = EventCheckpointStore(self.storage)
        for ch in SEPARATORS:
            new.append_event("task_c", "COMPAT", payload={"note": f"a{ch}b"})
        old = load_baseline("event_checkpoint_store.py")
        got = [e.payload["note"] for e in old.EventCheckpointStore(self.storage).read_events("task_c")]
        old.EventCheckpointStore(self.storage).append_event("task_c", "COMPAT_OLD", payload={"note": "o"})
        again = [e.event_type for e in new.read_events("task_c")]
        self.facts.append({"lock_files": sorted(p.name for p in (self.storage / "locks" / "events").glob("*"))})
        self.assertEqual(got, [f"a{ch}b" for ch in SEPARATORS])
        self.assertEqual(again, ["COMPAT"] * 3 + ["COMPAT_OLD"])


if __name__ == "__main__":
    unittest.main()
