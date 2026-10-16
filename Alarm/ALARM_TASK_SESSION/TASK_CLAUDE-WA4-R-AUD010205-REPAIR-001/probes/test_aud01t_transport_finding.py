"""FINDING probe AUD-01T (transport_event_store), CLAUDE-WA4-R-AUD010205-REPAIR-001.

Not a repair: transport_event_store.py is outside this TASK's write-scope (STOP / needs agreement).
Each test states the invariant the store should keep; a FAIL is the reproduced defect.
Disposable TEMP only; the real HTTP handler path (WebAlarmApi.dispatch) is used where it exists.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class TransportFramingFinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_aud01t_")
        self.addCleanup(self.temp.cleanup)
        self.storage = Path(self.temp.name) / "state"
        self.facts = [{"task": "CLAUDE-WA4-R-AUD010205-REPAIR-001", "finding": "AUD-01T", "test": self.id()}]

    def post(self, body):
        from web_alarm.server import ApiError, WebAlarmApi
        try:
            status, reply = WebAlarmApi(self.storage).dispatch("POST", "/transport/events", body)
            return [status, reply.get("authority")]
        except ApiError as exc:
            return [exc.status, exc.code, str(exc.details)[:200]]

    def get(self):
        from web_alarm.server import ApiError, WebAlarmApi
        try:
            status, reply = WebAlarmApi(self.storage).dispatch("GET", "/transport/events", None)
            return [status, len(reply["events"])]
        except ApiError as exc:
            return [exc.status, exc.code]

    def test_U2028_in_one_payload_keeps_transport_evidence_readable_and_appendable(self):
        first = self.post({"event_type": "REMOTE_OFFLINE", "payload": {"note": "drop\u2028reason"}})
        listing = self.get()
        second = self.post({"event_type": "REMOTE_RECOVERED", "payload": {"note": "plain"}})
        raw = (self.storage / "transport" / "transport_events.jsonl").read_bytes()
        self.facts.append({"first_post": first, "get_after": listing, "second_post": second,
                           "lf_records": len(raw.split(b"\n")) - 1,
                           "raw_U2028_bytes": raw.count("\u2028".encode())})
        self.assertEqual(listing[0], 200, "one accepted transport event made all transport evidence unreadable")
        self.assertEqual(second[0], 201, "one accepted transport event blocked every later transport append")

    def test_unterminated_tail_is_not_spliced_by_the_next_append(self):
        from web_alarm.transport_event_store import TransportEventStore, TransportEventStoreError
        store = TransportEventStore(self.storage)
        store.append("REMOTE_ONLINE", payload={"n": 1})
        path = store.events_path
        good = path.read_bytes()
        path.write_bytes(good[:-1])  # complete JSON record without its delimiter (crash shape)
        try:
            store.append("REMOTE_OFFLINE", payload={"n": 2})
            appended = "ACCEPTED"
        except TransportEventStoreError as exc:
            appended = f"REFUSED: {exc}"
        after = path.read_bytes()
        self.facts.append({"append_on_torn_tail": appended, "spliced": after.count(b"}{") > 0,
                           "after_hex_tail": after[-80:].hex()})
        self.assertNotEqual(appended, "ACCEPTED", "append joined a new record onto an unterminated one")
        self.assertEqual(after, good[:-1])


if __name__ == "__main__":
    unittest.main()
