import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from web_alarm.server import ApiError, WebAlarmApi, create_server


def tree_snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class TransportIngestionTests(unittest.TestCase):
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
        _, workspace = self.api.dispatch(
            "POST",
            "/workspaces",
            {
                "display_name": "Project",
                "workspace_root": str(self.project),
                "workspace_id": "ws_transport",
            },
        )
        _, task = self.api.dispatch(
            "POST",
            "/tasks",
            {
                "workspace_id": workspace["workspace"]["workspace_id"],
                "title": "Task",
                "raw_task": "RAW",
                "goal": "Transport evidence",
                "task_id": "task_transport",
            },
        )
        _, micro = self.api.dispatch(
            "POST",
            "/tasks/task_transport/microtasks",
            {
                "title": "M1",
                "goal": "Current",
                "microtask_id": "m1",
            },
        )
        return task["task"], micro["microtask"]

    def test_status_advertises_transport_evidence(self):
        status, payload = self.api.dispatch("GET", "/status")

        self.assertEqual(status, 200)
        self.assertIn("transport_evidence", payload["capabilities"])

    def test_post_and_get_unbound_transport_event(self):
        status, payload = self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "REMOTE_OFFLINE",
                "remote_call_kind": "read_file",
                "error_class": "transport_disconnect",
                "process_id": 4242,
                "process_start_time": "2026-10-02T08:17:59+05:00",
                "payload": {"channel": "remote"},
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["authority"], "evidence_only")
        self.assertFalse(payload["workflow_mutation_performed"])
        self.assertIsNone(payload["event"]["task_id"])

        reopened = WebAlarmApi(self.storage)
        status, listed = reopened.dispatch("GET", "/transport/events")
        self.assertEqual(status, 200)
        self.assertEqual(len(listed["events"]), 1)
        self.assertEqual(listed["events"][0]["event_type"], "REMOTE_OFFLINE")
        self.assertFalse(listed["workflow_mutation_performed"])

    def test_bound_events_are_filterable(self):
        self.create_task()
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "RESULT_DELIVERY_FAILED",
                "task_id": "task_transport",
                "microtask_id": "m1",
                "operation_id": "op_a",
                "event_id": "transport_a",
            },
        )
        self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "REMOTE_RECOVERED",
                "task_id": "task_transport",
                "microtask_id": "m1",
                "operation_id": "op_b",
                "event_id": "transport_b",
            },
        )

        _, payload = self.api.dispatch(
            "GET",
            "/transport/events?operation_id=op_b&event_type=REMOTE_RECOVERED",
        )
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["event_id"], "transport_b")
        self.assertEqual(payload["events"][0]["task_id"], "task_transport")

    def test_transport_ingestion_does_not_mutate_task_checkpoint_or_workspace(self):
        task, micro = self.create_task()
        target = self.project / "target.txt"
        target.write_text("before", encoding="utf-8")
        self.api.dispatch(
            "POST",
            f"/microtasks/{micro['microtask_id']}/prepare",
            {
                "task_id": task["task_id"],
                "targets": [{"path": "target.txt", "expected_change": "edit"}],
                "operation_id": "op_prepare",
            },
        )
        task_dir = self.api.tasks.task_directory(task["task_id"])
        task_before = tree_snapshot(task_dir)
        project_before = tree_snapshot(self.project)
        checkpoint_before = self.api.state.read_checkpoint(task["task_id"])

        status, payload = self.api.dispatch(
            "POST",
            "/transport/events",
            {
                "event_type": "MESSAGE_DELIVERY_TIMEOUT",
                "task_id": task["task_id"],
                "microtask_id": micro["microtask_id"],
                "operation_id": "op_remote",
                "error_class": "message_delivery_timeout",
            },
        )

        self.assertEqual(status, 201)
        self.assertFalse(payload["workflow_mutation_performed"])
        self.assertEqual(tree_snapshot(task_dir), task_before)
        self.assertEqual(tree_snapshot(self.project), project_before)
        checkpoint_after = self.api.state.read_checkpoint(task["task_id"])
        self.assertEqual(checkpoint_after, checkpoint_before)

    def test_invalid_payload_process_and_event_type_fail_with_400(self):
        bad_bodies = [
            {"event_type": "REMOTE_ONLINE", "payload": ["not", "object"]},
            {"event_type": "PROCESS_RESTARTED", "process_id": 0},
            {"event_type": "WATCHDOG_DECIDED_TO_ROLLBACK"},
        ]
        for body in bad_bodies:
            with self.subTest(body=body):
                with self.assertRaises(ApiError) as caught:
                    self.api.dispatch("POST", "/transport/events", body)
                self.assertEqual(caught.exception.status, 400)

    def test_invalid_query_fails_closed(self):
        with self.assertRaises(ApiError) as caught:
            self.api.dispatch(
                "GET",
                "/transport/events?task_id=&task_id=second",
            )

        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(caught.exception.code, "invalid_query")

    def test_real_http_post_and_get_transport_evidence(self):
        server = create_server(self.api, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            body = json.dumps(
                {
                    "event_type": "REMOTE_RECOVERED",
                    "event_id": "transport_http",
                    "payload": {"source": "watchdog"},
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/transport/events",
                data=body,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                created = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 201)
            self.assertEqual(created["event"]["event_id"], "transport_http")
            self.assertEqual(created["authority"], "evidence_only")

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/transport/events",
                timeout=5,
            ) as response:
                listed = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
            self.assertEqual(
                [item["event_id"] for item in listed["events"]],
                ["transport_http"],
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
