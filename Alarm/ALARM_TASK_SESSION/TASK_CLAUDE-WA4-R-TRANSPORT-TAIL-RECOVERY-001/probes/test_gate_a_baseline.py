"""Gate A (RED/baseline) probe for CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001. Synthetic TEMP data only.

CONTROL (must PASS before and after): a torn transport tail blocks reads and appends, and the store
leaves the bytes untouched. TRIGGER (expected RED on the pre-task code): a separate operator recovery
operation exists and can bring the log back to its valid prefix without losing the original bytes.
"""
import hashlib
import importlib.util
import inspect
import shutil
import tempfile
import unittest
from pathlib import Path

from web_alarm import transport_event_store as tes


class GateA(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_tailrec_gatea_"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.root = self.base / "state"
        store = tes.TransportEventStore(self.root)
        for index in range(3):
            store.append("REMOTE_ONLINE", event_id=f"t{index}", payload={"i": index})
        self.prefix = store.events_path.read_bytes()
        with store.events_path.open("ab") as handle:
            handle.write(b'{"event_id":"lost","event_type":"PROCESS_REST')  # death inside one write
        self.original = store.events_path.read_bytes()
        self.store = store
        self.facts = [{"task": "CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001", "test": self.id(),
                       "original_sha256": hashlib.sha256(self.original).hexdigest(),
                       "prefix_sha256": hashlib.sha256(self.prefix).hexdigest()}]

    def test_control_torn_tail_blocks_reads_and_appends_and_is_never_touched(self):
        with self.assertRaises(tes.TransportEventStoreError) as read_error:
            self.store.read_events()
        with self.assertRaises(tes.TransportEventStoreError) as append_error:
            self.store.append("REMOTE_ONLINE", event_id="after")
        self.facts.append({"read_error": str(read_error.exception).split(":")[0],
                           "append_error": str(append_error.exception).split(":")[0]})
        self.assertEqual(self.store.events_path.read_bytes(), self.original)
        self.assertEqual(sorted(p.name for p in self.store.events_path.parent.iterdir()), ["transport_events.jsonl"])

    def test_control_store_has_no_repair_entry_point(self):
        public = sorted(name for name, _ in inspect.getmembers(tes.TransportEventStore, inspect.isfunction)
                        if not name.startswith("_"))
        self.facts.append({"public_store_methods": public})
        self.assertEqual(public, ["append", "list_events", "read_events"])

    def test_trigger_operator_recovery_restores_the_valid_prefix_and_keeps_the_original(self):
        spec = importlib.util.find_spec("web_alarm.transport_event_recovery")
        self.facts.append({"recovery_module_present": spec is not None})
        self.assertIsNotNone(spec, "no operator recovery operation exists for a torn transport tail (AUD-01T-R)")
        from web_alarm import transport_event_recovery as rec
        plan = rec.inspect(self.root)
        result = rec.apply(self.root, plan["plan_fingerprint"], "gate A synthetic")
        self.assertEqual(self.store.events_path.read_bytes(), self.prefix)
        self.assertEqual((self.root / result["archive"]["original.bin"]["path"]).read_bytes(), self.original)
        self.assertEqual([r.event_id for r in self.store.read_events()], ["t0", "t1", "t2"])


if __name__ == "__main__":
    unittest.main()
