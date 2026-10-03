import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from web_alarm.server import ApiError, WebAlarmApi, create_server


class WebAlarmServerApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.api = WebAlarmApi(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_workspace(self, workspace_id="ws_api"):
        status, payload = self.api.dispatch(
            "POST",
            "/workspaces",
            {
                "display_name": "Project",
                "workspace_root": str(self.project),
                "workspace_id": workspace_id,
            },
        )
        self.assertEqual(status, 201)
        return payload["workspace"]

    def _create_task(self, task_id="task_api"):
        workspace = self._create_workspace()
        status, payload = self.api.dispatch(
            "POST",
            "/tasks",
            {
                "workspace_id": workspace["workspace_id"],
                "title": "Task",
                "raw_task": "RAW TASK",
                "goal": "Exercise Server API",
                "task_id": task_id,
            },
        )
        self.assertEqual(status, 201)
        return payload["task"]

    def _create_microtask(self, task_id="task_api", microtask_id="m1"):
        status, payload = self.api.dispatch(
            "POST",
            f"/tasks/{task_id}/microtasks",
            {
                "title": "M1",
                "goal": "Prepare snapshot",
                "microtask_id": microtask_id,
            },
        )
        self.assertEqual(status, 201)
        return payload["microtask"]

    def test_status_is_narrow_advisory_server_contract(self):
        status, payload = self.api.dispatch("GET", "/status")

        self.assertEqual(status, 200)
        self.assertEqual(payload["service"], "web_alarm_server")
        self.assertEqual(payload["mode"], "advisory")
        self.assertTrue(payload["loopback_default"])
        self.assertIn("prepare_restore_point", payload["capabilities"])
        self.assertNotIn("transition", payload["capabilities"])

    def test_workspace_task_microtask_and_plan_endpoints(self):
        task = self._create_task()
        m1 = self._create_microtask()
        status, payload = self.api.dispatch(
            "POST",
            f"/tasks/{task['task_id']}/microtasks",
            {"title": "M2", "goal": "Second", "microtask_id": "m2"},
        )
        self.assertEqual(status, 201)
        m2 = payload["microtask"]

        status, payload = self.api.dispatch(
            "POST",
            f"/tasks/{task['task_id']}/plan",
            {"microtask_ids": [m2["microtask_id"], m1["microtask_id"]]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["plan"]["microtask_ids"], ["m2", "m1"])

        status, payload = self.api.dispatch("GET", f"/tasks/{task['task_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(
            [item["microtask_id"] for item in payload["microtasks"]],
            ["m2", "m1"],
        )

    def test_prepare_and_snapshot_verify_do_not_mutate_real_project(self):
        task = self._create_task()
        micro = self._create_microtask()
        target = self.project / "existing.txt"
        target.write_text("before", encoding="utf-8")

        status, payload = self.api.dispatch(
            "POST",
            f"/microtasks/{micro['microtask_id']}/prepare",
            {
                "task_id": task["task_id"],
                "targets": [
                    {"path": "existing.txt", "expected_change": "edit"},
                    {"path": "new.txt", "expected_change": "create"},
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["manifest"]["status"], "VERIFIED")
        self.assertEqual(target.read_text(encoding="utf-8"), "before")
        self.assertFalse((self.project / "new.txt").exists())

        status, payload = self.api.dispatch(
            "POST",
            f"/microtasks/{micro['microtask_id']}/snapshot",
            {"task_id": task["task_id"], "action": "verify"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["manifest"]["status"], "VERIFIED")
    def test_snapshot_restore_is_not_exposed_by_server_api(self):
        task = self._create_task()
        micro = self._create_microtask()
        target = self.project / "existing.txt"
        target.write_text("before", encoding="utf-8")
        self.api.dispatch(
            "POST",
            f"/microtasks/{micro['microtask_id']}/prepare",
            {
                "task_id": task["task_id"],
                "targets": [{"path": "existing.txt", "expected_change": "edit"}],
            },
        )
        target.write_text("changed outside server", encoding="utf-8")

        with self.assertRaises(ApiError) as caught:
            self.api.dispatch(
                "POST",
                f"/microtasks/{micro['microtask_id']}/snapshot",
                {"task_id": task["task_id"], "action": "restore"},
            )

        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(
            caught.exception.code,
            "real_workspace_mutation_not_exposed",
        )
        self.assertEqual(target.read_text(encoding="utf-8"), "changed outside server")

    def test_report_and_recovery_entry_are_state_only(self):
        task = self._create_task()
        micro = self._create_microtask()

        status, payload = self.api.dispatch(
            "POST",
            f"/microtasks/{micro['microtask_id']}/report",
            {
                "task_id": task["task_id"],
                "report": "schema verified",
                "operation_id": "op_report",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["event"]["event_type"], "REPORT")

        status, payload = self.api.dispatch(
            "POST",
            f"/tasks/{task['task_id']}/recover",
            {},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["mode"], "advisory_only")
        self.assertFalse(payload["mutation_performed"])
        self.assertEqual(payload["recovery_engine"], "WA-3_NOT_IMPLEMENTED")
        self.assertEqual(payload["recent_events"][-1]["event_type"], "REPORT")

    def test_task_creation_requires_registered_workspace(self):
        with self.assertRaises(ApiError) as caught:
            self.api.dispatch(
                "POST",
                "/tasks",
                {
                    "workspace_id": "ws_missing",
                    "title": "Task",
                    "raw_task": "RAW",
                    "goal": "Goal",
                    "task_id": "task_bad",
                },
            )

        self.assertIn(caught.exception.status, {404, 409})
        self.assertFalse((self.storage / "tasks" / "active" / "task_bad").exists())

    def test_tasks_listing_separates_active_and_completed(self):
        task = self._create_task()
        status, payload = self.api.dispatch("GET", "/tasks")
        self.assertEqual(status, 200)
        self.assertEqual([item["task_id"] for item in payload["active"]], [task["task_id"]])

        self.api.tasks.complete_task(task["task_id"])
        status, payload = self.api.dispatch("GET", "/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(payload["active"], [])
        self.assertEqual([item["task_id"] for item in payload["completed"]], [task["task_id"]])

    def test_invalid_target_shape_is_400(self):
        task = self._create_task()
        micro = self._create_microtask()

        with self.assertRaises(ApiError) as caught:
            self.api.dispatch(
                "POST",
                f"/microtasks/{micro['microtask_id']}/prepare",
                {"task_id": task["task_id"], "targets": ["not-an-object"]},
            )
        self.assertEqual(caught.exception.status, 400)

    def test_non_loopback_bind_requires_explicit_override(self):
        with self.assertRaises(ValueError):
            create_server(self.api, host="0.0.0.0", port=0)
    def test_real_http_loopback_status_and_json_error(self):
        server = create_server(self.api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        base = f"http://{host}:{port}"
        try:
            with urllib.request.urlopen(base + "/status", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(payload["service"], "web_alarm_server")

            request = urllib.request.Request(
                base + "/tasks",
                data=b"{bad json",
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(caught.exception.code, 400)
            payload = json.loads(caught.exception.read().decode("utf-8"))
            self.assertEqual(payload["error"]["code"], "invalid_json")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
