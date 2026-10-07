import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ui import INDEX_HTML


class WebAlarmUiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.api = WebAlarmApi(self.storage)

        _, ws_payload = self.api.dispatch(
            "POST",
            "/workspaces",
            {
                "display_name": "Project",
                "workspace_root": str(self.project),
                "workspace_id": "ws_ui",
            },
        )
        self.workspace = ws_payload["workspace"]
        _, task_payload = self.api.dispatch(
            "POST",
            "/tasks",
            {
                "workspace_id": "ws_ui",
                "title": "UI Task",
                "raw_task": "<b>RAW must stay text</b>",
                "goal": "Render state",
                "task_id": "task_ui",
            },
        )
        self.task = task_payload["task"]
        _, micro_payload = self.api.dispatch(
            "POST",
            "/tasks/task_ui/microtasks",
            {
                "title": "M1",
                "goal": "Prepare UI state",
                "microtask_id": "m1",
            },
        )
        self.micro = micro_payload["microtask"]

    def tearDown(self):
        self.tempdir.cleanup()

    def test_static_ui_contains_required_sections_and_safe_text_rendering(self):
        self.assertIn("Web Alarm Workspace", INDEX_HTML)
        self.assertIn("Новая TASK", INDEX_HTML)
        self.assertIn("RAW TASK", INDEX_HTML)
        self.assertIn("Manifest / Snapshot", INDEX_HTML)
        self.assertIn("Recovery state", INDEX_HTML)
        self.assertIn("NEXT SAFE ACTION", INDEX_HTML)
        self.assertIn("textContent", INDEX_HTML)
        self.assertNotIn("innerHTML", INDEX_HTML)
        self.assertNotIn("https://", INDEX_HTML)

    def test_ui_task_view_aggregates_required_state_without_project_mutation(self):
        target = self.project / "file.txt"
        target.write_text("before", encoding="utf-8")
        self.api.dispatch(
            "POST",
            "/microtasks/m1/prepare",
            {
                "task_id": "task_ui",
                "targets": [{"path": "file.txt", "expected_change": "edit"}],
                "operation_id": "op_prepare",
            },
        )
        self.api.dispatch(
            "POST",
            "/microtasks/m1/report",
            {
                "task_id": "task_ui",
                "report": "UI report",
                "operation_id": "op_report",
            },
        )
        before = target.read_bytes()

        status, payload = self.api.dispatch("GET", "/tasks/task_ui/ui")

        self.assertEqual(status, 200)
        self.assertEqual(payload["workspace"]["workspace_id"], "ws_ui")
        self.assertEqual(payload["task_state"]["task"]["raw_task"], "<b>RAW must stay text</b>")
        self.assertEqual(payload["current_microtask_id"], "m1")
        self.assertEqual(payload["manifest"]["record"]["status"], "VERIFIED")
        self.assertEqual(payload["snapshot_status"], "VERIFIED")
        self.assertEqual(payload["recovery_state"], "NORMAL")
        self.assertEqual(payload["reports"][-1]["payload"]["report"], "UI report")
        self.assertIn("READY", payload["next_safe_action"])
        self.assertEqual(target.read_bytes(), before)

    def test_ui_task_view_without_checkpoint_or_manifest_is_read_only(self):
        before_files = sorted(path.name for path in self.project.iterdir())

        status, payload = self.api.dispatch("GET", "/tasks/task_ui/ui")

        self.assertEqual(status, 200)
        self.assertIsNone(payload["task_state"]["checkpoint"])
        self.assertEqual(payload["manifest"]["available"], False)
        self.assertEqual(payload["snapshot_status"], "NOT_PREPARED")
        self.assertIn("prepare restore point", payload["next_safe_action"])
        self.assertEqual(sorted(path.name for path in self.project.iterdir()), before_files)

    def test_real_http_root_serves_html_ui(self):
        server = create_server(self.api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/", timeout=5) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertTrue(response.headers["Content-Type"].startswith("text/html"))
                self.assertIn("Web Alarm Workspace", body)
                self.assertIn("/tasks/", body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_real_http_ui_aggregate_is_json(self):
        server = create_server(self.api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        try:
            with urllib.request.urlopen(
                f"http://{host}:{port}/tasks/task_ui/ui",
                timeout=5,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(payload["task_state"]["task"]["task_id"], "task_ui")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
