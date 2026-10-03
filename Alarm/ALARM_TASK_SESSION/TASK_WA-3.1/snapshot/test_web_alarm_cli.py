import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from web_alarm.cli import main
from web_alarm.workspace_registry import WorkspaceRegistry


class WebAlarmCliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.workspace = WorkspaceRegistry(self.storage).register("Project", self.project)

    def tearDown(self):
        self.tempdir.cleanup()

    def run_cli(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--storage-root", str(self.storage), *args])
        return code, out.getvalue(), err.getvalue()

    def test_task_create_open_and_complete(self):
        code, out, err = self.run_cli(
            "task", "create",
            "--workspace-id", self.workspace.workspace_id,
            "--title", "Task",
            "--raw-task", "RAW",
            "--goal", "Goal",
            "--task-id", "task_cli",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["task_id"], "task_cli")

        code, out, err = self.run_cli("task", "open", "--task-id", "task_cli")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["raw_task"], "RAW")

        code, out, err = self.run_cli("task", "complete", "--task-id", "task_cli")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["status"], "COMPLETED")

    def test_microtask_prepare_checkpoint_status_and_report(self):
        self.run_cli(
            "task", "create",
            "--workspace-id", self.workspace.workspace_id,
            "--title", "Task",
            "--raw-task", "RAW",
            "--goal", "Goal",
            "--task-id", "task_cli",
        )
        code, out, err = self.run_cli(
            "microtask", "create",
            "--task-id", "task_cli",
            "--title", "M1",
            "--goal", "Prepare",
            "--microtask-id", "m1",
        )
        self.assertEqual(code, 0, err)

        target = self.project / "file.txt"
        target.write_text("before", encoding="utf-8")
        code, out, err = self.run_cli(
            "microtask", "prepare",
            "--task-id", "task_cli",
            "--microtask-id", "m1",
            "--target", "file.txt=edit",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["status"], "VERIFIED")

        code, out, err = self.run_cli(
            "checkpoint", "write",
            "--task-id", "task_cli",
            "--current-microtask", "m1",
            "--last-verified-microtask", "m1",
            "--current-status", "BACKUP_VERIFIED",
            "--snapshot-status", "VERIFIED",
            "--last-operation-id", "op_1",
            "--next-safe-action", "continue",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["next_safe_action"], "continue")

        code, out, err = self.run_cli("status", "--task-id", "task_cli")
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["checkpoint"]["snapshot_status"], "VERIFIED")

        code, out, err = self.run_cli("report", "--task-id", "task_cli")
        self.assertEqual(code, 0, err)
        self.assertIn("NEXT SAFE ACTION: continue", out)

    def test_snapshot_restore_and_verify(self):
        self.run_cli(
            "task", "create",
            "--workspace-id", self.workspace.workspace_id,
            "--title", "Task",
            "--raw-task", "RAW",
            "--goal", "Goal",
            "--task-id", "task_cli",
        )
        self.run_cli(
            "microtask", "create",
            "--task-id", "task_cli",
            "--title", "M1",
            "--goal", "Prepare",
            "--microtask-id", "m1",
        )
        target = self.project / "file.txt"
        target.write_text("before", encoding="utf-8")
        self.run_cli(
            "microtask", "prepare",
            "--task-id", "task_cli",
            "--microtask-id", "m1",
            "--target", "file.txt=edit",
        )
        target.write_text("after", encoding="utf-8")

        code, out, err = self.run_cli(
            "snapshot", "verify",
            "--task-id", "task_cli",
            "--microtask-id", "m1",
        )
        self.assertEqual(code, 0, err)

        code, out, err = self.run_cli(
            "snapshot", "restore",
            "--task-id", "task_cli",
            "--microtask-id", "m1",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(target.read_text(encoding="utf-8"), "before")

    def test_error_returns_nonzero_and_stderr(self):
        code, out, err = self.run_cli("task", "open", "--task-id", "missing")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("ERROR:", err)

    def test_module_entrypoint_help(self):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "web_alarm", "--help"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("webalarm", result.stdout)


if __name__ == "__main__":
    unittest.main()
