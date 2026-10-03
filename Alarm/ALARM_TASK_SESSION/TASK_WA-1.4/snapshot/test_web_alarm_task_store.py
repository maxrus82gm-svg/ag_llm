import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.models import TaskStatus
from web_alarm.task_store import TaskStore, TaskStoreError


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.store = TaskStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def _create_task(self, *, task_id=None):
        return self.store.create_task(
            "ws_test",
            "Web Alarm test task",
            "RAW TASK\nkeep this exact",
            "Persist TASK state safely.",
            task_id=task_id,
        )

    def test_create_and_reopen_task_preserves_raw_source(self):
        task = self._create_task()
        task_dir = self.storage / "tasks" / "active" / task.task_id
        self.assertTrue((task_dir / "task.json").is_file())
        self.assertTrue((task_dir / "task.md").is_file())
        self.assertTrue((task_dir / "plan.json").is_file())
        self.assertEqual(
            (task_dir / "task.md").read_text(encoding="utf-8"),
            "RAW TASK\nkeep this exact",
        )

        reopened = TaskStore(self.storage).open_task(task.task_id)
        self.assertEqual(reopened.task_id, task.task_id)
        self.assertEqual(reopened.raw_task, task.raw_task)
        self.assertEqual(reopened.workspace_id, "ws_test")

    def test_save_raw_task_is_idempotent_but_immutable(self):
        task = self._create_task()
        same = self.store.save_raw_task(task.task_id, task.raw_task)
        self.assertEqual(same.task_id, task.task_id)

        with self.assertRaises(TaskStoreError):
            self.store.save_raw_task(task.task_id, "changed RAW TASK")

    def test_raw_task_drift_is_detected_fail_closed(self):
        task = self._create_task()
        task_md = self.storage / "tasks" / "active" / task.task_id / "task.md"
        task_md.write_text("tampered", encoding="utf-8")

        with self.assertRaises(TaskStoreError):
            TaskStore(self.storage).open_task(task.task_id)
    def test_microtask_plan_order_and_current_survive_restart(self):
        task = self._create_task()
        m1 = self.store.create_microtask(
            task.task_id, "M1", "First", microtask_id="m1"
        )
        m2 = self.store.create_microtask(
            task.task_id, "M2", "Second", microtask_id="m2"
        )
        m3 = self.store.create_microtask(
            task.task_id, "M3", "Third", microtask_id="m3"
        )

        plan = self.store.set_plan(task.task_id, [m3.microtask_id, m1.microtask_id, m2.microtask_id])
        self.store.set_current_microtask(task.task_id, m1.microtask_id)

        reopened = TaskStore(self.storage)
        loaded_plan = reopened.open_plan(task.task_id)
        loaded_microtasks = reopened.list_microtasks(task.task_id)

        self.assertEqual(loaded_plan.plan_id, plan.plan_id)
        self.assertEqual(loaded_plan.microtask_ids, ["m3", "m1", "m2"])
        self.assertEqual(loaded_plan.current_microtask_id, "m1")
        self.assertEqual([item.microtask_id for item in loaded_microtasks], ["m3", "m1", "m2"])
        self.assertEqual([item.sequence for item in loaded_microtasks], [1, 2, 3])

    def test_set_plan_rejects_duplicates_and_unknown_microtasks(self):
        task = self._create_task()
        self.store.create_microtask(task.task_id, "M1", "First", microtask_id="m1")
        self.store.create_microtask(task.task_id, "M2", "Second", microtask_id="m2")

        with self.assertRaises(TaskStoreError):
            self.store.set_plan(task.task_id, ["m1", "m1"])
        with self.assertRaises(TaskStoreError):
            self.store.set_plan(task.task_id, ["m1", "unknown"])

    def test_set_current_requires_member_of_plan(self):
        task = self._create_task()
        self.store.create_microtask(task.task_id, "M1", "First", microtask_id="m1")

        with self.assertRaises(TaskStoreError):
            self.store.set_current_microtask(task.task_id, "not_in_plan")

    def test_complete_moves_task_and_preserves_all_files(self):
        task = self._create_task()
        micro = self.store.create_microtask(
            task.task_id, "M1", "First", microtask_id="m1"
        )
        self.store.set_current_microtask(task.task_id, micro.microtask_id)

        completed = self.store.complete_task(task.task_id)
        active_dir = self.storage / "tasks" / "active" / task.task_id
        completed_dir = self.storage / "tasks" / "completed" / task.task_id

        self.assertFalse(active_dir.exists())
        self.assertTrue((completed_dir / "task.json").is_file())
        self.assertTrue((completed_dir / "task.md").is_file())
        self.assertTrue((completed_dir / "plan.json").is_file())
        self.assertTrue((completed_dir / "microtasks" / "m1.json").is_file())
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(TaskStore(self.storage).open_task(task.task_id).status, TaskStatus.COMPLETED)

        with self.assertRaises(TaskStoreError):
            self.store.create_microtask(task.task_id, "M2", "Late")

    def test_archive_keeps_completed_task_readable(self):
        task = self._create_task()
        self.store.complete_task(task.task_id)

        archived = self.store.archive_task(task.task_id)
        reopened = TaskStore(self.storage).open_task(task.task_id)

        self.assertEqual(archived.status, TaskStatus.ARCHIVED)
        self.assertEqual(reopened.status, TaskStatus.ARCHIVED)
        self.assertEqual(reopened.raw_task, task.raw_task)

    def test_explicit_task_id_cannot_escape_storage(self):
        with self.assertRaises(TaskStoreError):
            self._create_task(task_id="../escape")

    def test_unknown_plan_schema_fails_closed(self):
        task = self._create_task()
        plan_path = self.storage / "tasks" / "active" / task.task_id / "plan.json"
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
        payload["schema_version"] = 999
        plan_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(TaskStoreError):
            TaskStore(self.storage).open_plan(task.task_id)


if __name__ == "__main__":
    unittest.main()
