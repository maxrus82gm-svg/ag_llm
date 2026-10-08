import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from web_alarm.server import ApiError, WebAlarmApi


class TransportRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.api = WebAlarmApi(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def create_task(self):
        self.api.dispatch(
            "POST",
            "/workspaces",
            {
                "display_name": "Project",
                "workspace_root": str(self.project),
                "workspace_id": "ws_recovery",
            },
        )
        self.api.dispatch(
            "POST",
            "/tasks",
            {
                "workspace_id": "ws_recovery",
                "title": "Task",
                "raw_task": "RAW",
                "goal": "Recovery",
                "task_id": "task_recovery",
            },
        )
        self.api.dispatch(
            "POST",
            "/tasks/task_recovery/microtasks",
            {
                "title": "M1",
                "goal": "Recover",
                "microtask_id": "m1",
            },
        )

    def test_offline_recovered_order_survives_new_server(self):
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "REMOTE_OFFLINE",
                "event_id": "event_offline",
            },
        )
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "REMOTE_RECOVERED",
                "event_id": "event_recovered",
            },
        )
        reopened = WebAlarmApi(self.storage)
        _, payload = reopened.dispatch("GET", "/transport/events")

        self.assertEqual(
            [item["event_type"] for item in payload["events"]],
            ["REMOTE_OFFLINE", "REMOTE_RECOVERED"],
        )

    def test_result_delivery_and_process_restart_survive_fresh_python_process(self):
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "RESULT_DELIVERY_FAILED",
                "event_id": "event_result",
                "error_class": "fetch_failed",
            },
        )
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "PROCESS_RESTARTED",
                "event_id": "event_restart",
                "process_id": 9001,
                "process_start_time": "2026-10-02T15:00:00+05:00",
                "payload": {"previous_process_id": 8001},
            },
        )

        code = (
            "import json,sys;"
            "from web_alarm.transport_event_store import TransportEventStore;"
            "events=TransportEventStore(sys.argv[1]).read_events();"
            "print(json.dumps([[e.event_id,e.event_type.value] for e in events]))"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", code, str(self.storage)],
            cwd=Path(__file__).parent,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        rows = json.loads(completed.stdout.strip())

        self.assertEqual(
            rows,
            [
                ["event_result", "RESULT_DELIVERY_FAILED"],
                ["event_restart", "PROCESS_RESTARTED"],
            ],
        )

    def test_duplicate_same_event_id_is_idempotent(self):
        body = {
            "event_type": "REMOTE_OFFLINE",
            "event_id": "event_duplicate",
            "error_class": "socket_closed",
            "payload": {"attempt": 1},
        }
        self.api.dispatch("POST", "/transport/events", body)
        self.api.dispatch("POST", "/transport/events", body)

        _, payload = self.api.dispatch("GET", "/transport/events")
        matching = [
            item
            for item in payload["events"]
            if item["event_id"] == "event_duplicate"
        ]
        self.assertEqual(len(matching), 1)

    def test_duplicate_event_id_conflict_fails_closed(self):
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "REMOTE_OFFLINE",
                "event_id": "event_conflict",
            },
        )

        with self.assertRaises(ApiError) as caught:
            self.api.dispatch(
                "POST",
                "/transport/events",
                {
                    "event_type": "REMOTE_RECOVERED",
                    "event_id": "event_conflict",
                },
            )

        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(caught.exception.code, "transport_evidence_error")

    def test_unknown_operation_and_transport_evidence_survive_reopen(self):
        self.create_task()
        self.api.operations.begin(
            "task_recovery",
            "m1",
            "write",
            "target.txt",
            operation_id="op_unknown",
            request_payload={"content": "after"},
        )
        self.api.operations.transition(
            "task_recovery",
            "op_unknown",
            "STARTED",
        )
        self.api.operations.transition(
            "task_recovery",
            "op_unknown",
            "UNKNOWN_AFTER_DISCONNECT",
        )
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "RESULT_DELIVERY_FAILED",
                "event_id": "event_unknown",
                "task_id": "task_recovery",
                "microtask_id": "m1",
                "operation_id": "op_unknown",
                "error_class": "fetch_failed",
            },
        )

        reopened = WebAlarmApi(self.storage)
        operation = reopened.operations.get("task_recovery", "op_unknown")
        _, transport = reopened.dispatch(
            "GET",
            "/transport/events?operation_id=op_unknown",
        )

        self.assertEqual(operation.status.value, "UNKNOWN_AFTER_DISCONNECT")
        self.assertEqual(len(transport["events"]), 1)
        self.assertEqual(
            transport["events"][0]["event_type"],
            "RESULT_DELIVERY_FAILED",
        )
        self.assertFalse(transport["workflow_mutation_performed"])


if __name__ == "__main__":
    unittest.main()
