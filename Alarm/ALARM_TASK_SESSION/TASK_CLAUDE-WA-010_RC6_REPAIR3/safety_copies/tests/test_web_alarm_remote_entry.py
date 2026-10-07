import tempfile
import unittest
from pathlib import Path

from web_alarm.models import MicrotaskStatus
from web_alarm.remote_entry import RemoteEntry, RemoteEntryError
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


class RemoteEntryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_entry",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_task(self, task_id: str, *, with_microtask: bool = True):
        tasks = TaskStore(self.storage)
        task = tasks.create_task(
            self.workspace.workspace_id,
            f"Task {task_id}",
            f"RAW {task_id}",
            f"Goal {task_id}",
            task_id=task_id,
        )
        if with_microtask:
            tasks.create_microtask(
                task.task_id,
                "M1",
                "Entry step",
                microtask_id=f"{task_id}_m1",
            )
        return task

    def test_single_active_task_resolves_and_returns_read_only_context(self):
        task = self._create_task("task_one")
        marker = self.project / "marker.txt"
        marker.write_text("before", encoding="utf-8")
        before = marker.read_bytes()

        result = RemoteEntry(self.storage).enter()

        self.assertEqual(result["RESOLVED_TASK_ID"], task.task_id)
        self.assertEqual(result["ENTRY_STATE"], "CONTEXT_READY")
        self.assertFalse(result["RECOVERY_REVIEW_REQUIRED"])
        self.assertTrue(result["READ_ONLY"])
        self.assertEqual(
            result["MUTATION_DECISION"],
            "FOLLOW_NEXT_SAFE_ACTION_AFTER_CONTEXT_REVIEW",
        )
        self.assertEqual(result["CONTEXT_PACK"]["TASK"]["task_id"], task.task_id)
        self.assertEqual(marker.read_bytes(), before)

    def test_zero_active_tasks_fail_closed(self):
        with self.assertRaises(RemoteEntryError) as caught:
            RemoteEntry(self.storage).enter()

        self.assertIn("no active TASK", str(caught.exception))

    def test_multiple_active_tasks_require_explicit_task_id(self):
        self._create_task("task_a")
        self._create_task("task_b")

        with self.assertRaises(RemoteEntryError) as caught:
            RemoteEntry(self.storage).enter()

        self.assertIn("ambiguous", str(caught.exception))
        self.assertIn("--task-id", str(caught.exception))

        explicit = RemoteEntry(self.storage).enter("task_b")
        self.assertEqual(explicit["RESOLVED_TASK_ID"], "task_b")

    def test_explicit_completed_task_is_rejected(self):
        task = self._create_task("task_done")
        TaskStore(self.storage).complete_task(task.task_id)

        with self.assertRaises(Exception) as caught:
            RemoteEntry(self.storage).enter(task.task_id)

        self.assertIn("active", str(caught.exception))

    def test_recovery_status_marks_reconciliation_required(self):
        task = self._create_task("task_recovery")
        micro_id = "task_recovery_m1"
        TaskStore(self.storage).set_microtask_status(
            task.task_id,
            micro_id,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )

        result = RemoteEntry(self.storage).enter(task.task_id)

        self.assertEqual(result["ENTRY_STATE"], "RECOVERY_REVIEW_REQUIRED")
        self.assertTrue(result["RECOVERY_REVIEW_REQUIRED"])
        self.assertEqual(
            result["MUTATION_DECISION"],
            "RECONCILE_BEFORE_MUTATION",
        )
        self.assertEqual(
            result["CONTEXT_PACK"]["CURRENT_STATUS"],
            "UNKNOWN_AFTER_DISCONNECT",
        )
        self.assertIn(
            "reconcile disk state",
            result["CONTEXT_PACK"]["NEXT_SAFE_ACTION"],
        )

    def test_new_instance_resolves_same_single_active_task(self):
        task = self._create_task("task_restart")
        first = RemoteEntry(self.storage).enter()
        second = RemoteEntry(self.storage).enter()

        self.assertEqual(first["RESOLVED_TASK_ID"], task.task_id)
        self.assertEqual(second["RESOLVED_TASK_ID"], task.task_id)
        self.assertEqual(first["CONTEXT_PACK"], second["CONTEXT_PACK"])


if __name__ == "__main__":
    unittest.main()
