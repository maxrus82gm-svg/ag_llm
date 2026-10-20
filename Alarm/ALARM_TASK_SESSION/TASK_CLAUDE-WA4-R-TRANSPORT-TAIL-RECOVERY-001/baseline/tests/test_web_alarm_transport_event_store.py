import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.models import SCHEMA_VERSION
from web_alarm.transport_event_store import (
    TransportEventRecord,
    TransportEventStore,
    TransportEventStoreError,
    TransportEventType,
)


class TransportEventStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = Path(self.tempdir.name) / "state"
        self.store = TransportEventStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_all_supported_event_types_round_trip(self):
        for event_type in TransportEventType:
            self.store.append(event_type)

        reopened = TransportEventStore(self.storage)
        events = reopened.read_events()
        self.assertEqual(
            [event.event_type for event in events],
            list(TransportEventType),
        )

    def test_event_can_exist_without_task_identity(self):
        event = self.store.append(
            "REMOTE_OFFLINE",
            error_class="transport_disconnect",
            remote_call_kind="read_file",
            process_id=1234,
            process_start_time="2026-10-02T08:17:59+05:00",
            payload={"channel": "remote"},
        )

        loaded = TransportEventStore(self.storage).read_events()[0]
        self.assertIsNone(loaded.task_id)
        self.assertIsNone(loaded.microtask_id)
        self.assertIsNone(loaded.operation_id)
        self.assertEqual(loaded.event_id, event.event_id)
        self.assertEqual(loaded.error_class, "transport_disconnect")
        self.assertEqual(loaded.remote_call_kind, "read_file")
        self.assertEqual(loaded.process_id, 1234)
        self.assertEqual(loaded.payload, {"channel": "remote"})

    def test_task_operation_binding_and_filters(self):
        self.store.append(
            "RESULT_DELIVERY_FAILED",
            task_id="task_a",
            microtask_id="micro_a",
            operation_id="op_a",
        )
        self.store.append(
            "REMOTE_RECOVERED",
            task_id="task_b",
            microtask_id="micro_b",
            operation_id="op_b",
        )

        by_task = self.store.list_events(task_id="task_a")
        by_operation = self.store.list_events(operation_id="op_b")
        by_type = self.store.list_events(event_type="REMOTE_RECOVERED")

        self.assertEqual([event.operation_id for event in by_task], ["op_a"])
        self.assertEqual([event.task_id for event in by_operation], ["task_b"])
        self.assertEqual([event.task_id for event in by_type], ["task_b"])

    def test_append_is_persistent_and_preserves_existing_prefix(self):
        first = self.store.append("REMOTE_ONLINE", event_id="transport_first")
        before = self.store.events_path.read_bytes()

        second = self.store.append("REMOTE_OFFLINE", event_id="transport_second")
        after = self.store.events_path.read_bytes()
        reopened = TransportEventStore(self.storage).read_events()

        self.assertTrue(after.startswith(before))
        self.assertGreater(len(after), len(before))
        self.assertEqual(
            [event.event_id for event in reopened],
            [first.event_id, second.event_id],
        )

    def test_transport_store_does_not_create_task_state(self):
        self.store.append("MESSAGE_DELIVERY_TIMEOUT")

        self.assertTrue(self.store.events_path.is_file())
        self.assertFalse((self.storage / "tasks").exists())
        self.assertFalse((self.storage / "checkpoint.json").exists())

    def test_corrupted_line_fails_closed(self):
        self.store.append("REMOTE_ONLINE")
        with self.store.events_path.open("a", encoding="utf-8") as handle:
            handle.write("not-json\n")

        with self.assertRaises(TransportEventStoreError):
            TransportEventStore(self.storage).read_events()

    def test_unknown_schema_fails_closed(self):
        self.store.append("REMOTE_ONLINE")
        lines = self.store.events_path.read_text(encoding="utf-8").splitlines()
        payload = json.loads(lines[0])
        payload["schema_version"] = SCHEMA_VERSION + 999
        self.store.events_path.write_text(
            json.dumps(payload) + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(TransportEventStoreError):
            self.store.read_events()

    def test_unknown_event_type_fails_closed(self):
        self.store.append("REMOTE_ONLINE")
        payload = json.loads(
            self.store.events_path.read_text(encoding="utf-8").splitlines()[0]
        )
        payload["event_type"] = "WATCHDOG_DECIDED_TO_ROLLBACK"
        self.store.events_path.write_text(
            json.dumps(payload) + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(TransportEventStoreError):
            self.store.read_events()

    def test_invalid_process_id_is_rejected_before_persistence(self):
        with self.assertRaises(ValueError):
            self.store.append("PROCESS_RESTARTED", process_id=0)

        self.assertFalse(self.store.events_path.exists())

    def test_record_rejects_blank_optional_identity(self):
        with self.assertRaises(ValueError):
            TransportEventRecord(
                event_type=TransportEventType.REMOTE_ONLINE,
                task_id=" ",
            )


if __name__ == "__main__":
    unittest.main()
