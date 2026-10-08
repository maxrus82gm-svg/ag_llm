import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.event_checkpoint_store import (
    EventCheckpointStore,
    EventCheckpointStoreError,
)
from web_alarm.models import CheckpointRecord, MicrotaskStatus
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


class EventCheckpointStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()

        registry = WorkspaceRegistry(self.storage)
        workspace = registry.register("Project", self.project)
        tasks = TaskStore(self.storage)
        self.task = tasks.create_task(
            workspace.workspace_id,
            "Task",
            "RAW TASK",
            "Test event/checkpoint storage",
            task_id="task_state",
        )
        self.micro = tasks.create_microtask(
            self.task.task_id,
            "M1",
            "Current microtask",
            microtask_id="m1",
        )
        self.store = EventCheckpointStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def _checkpoint(self, next_action="continue safely"):
        return CheckpointRecord(
            task_id=self.task.task_id,
            workspace_id=self.task.workspace_id,
            last_verified_microtask_id=self.micro.microtask_id,
            current_microtask_id=self.micro.microtask_id,
            current_status=MicrotaskStatus.BACKUP_VERIFIED,
            snapshot_status="VERIFIED",
            last_operation_id="op_1",
            next_safe_action=next_action,
        )

    def test_events_are_append_only_and_survive_restart(self):
        first = self.store.append_event(
            self.task.task_id,
            "MICROTASK_PREPARED",
            microtask_id="m1",
            payload={"snapshot_status": "VERIFIED"},
        )
        second = self.store.append_event(
            self.task.task_id,
            "CHECKPOINT_UPDATED",
            microtask_id="m1",
            operation_id="op_1",
        )

        reopened = EventCheckpointStore(self.storage)
        events = reopened.read_events(self.task.task_id)

        self.assertEqual([e.event_id for e in events], [first.event_id, second.event_id])
        self.assertEqual([e.event_type for e in events], ["MICROTASK_PREPARED", "CHECKPOINT_UPDATED"])

    def test_checkpoint_survives_restart_and_md_matches_json(self):
        written = self.store.write_checkpoint(self._checkpoint("reconcile and continue"))

        reopened = EventCheckpointStore(self.storage)
        loaded = reopened.read_checkpoint(self.task.task_id)
        task_dir = TaskStore(self.storage).task_directory(self.task.task_id)
        md = (task_dir / "checkpoint.md").read_text(encoding="utf-8")

        self.assertEqual(loaded.checkpoint_id, written.checkpoint_id)
        self.assertEqual(loaded.next_safe_action, "reconcile and continue")
        self.assertEqual(loaded.current_status, MicrotaskStatus.BACKUP_VERIFIED)
        self.assertIn("NEXT SAFE ACTION", md)
        self.assertIn("reconcile and continue", md)
        self.assertIn(self.micro.microtask_id, md)

    def test_checkpoint_updates_do_not_change_event_history(self):
        self.store.append_event(self.task.task_id, "ONE", microtask_id="m1")
        before = self.store.read_events(self.task.task_id)

        checkpoint = self._checkpoint("first")
        self.store.write_checkpoint(checkpoint)
        checkpoint.next_safe_action = "second"
        self.store.write_checkpoint(checkpoint)

        after = self.store.read_events(self.task.task_id)
        self.assertEqual([e.event_id for e in before], [e.event_id for e in after])

    def test_corrupted_checkpoint_fails_closed(self):
        self.store.write_checkpoint(self._checkpoint())
        task_dir = TaskStore(self.storage).task_directory(self.task.task_id)
        (task_dir / "checkpoint.json").write_text("{bad json", encoding="utf-8")

        with self.assertRaises(EventCheckpointStoreError):
            EventCheckpointStore(self.storage).read_checkpoint(self.task.task_id)

    def test_unknown_checkpoint_schema_fails_closed(self):
        self.store.write_checkpoint(self._checkpoint())
        task_dir = TaskStore(self.storage).task_directory(self.task.task_id)
        path = task_dir / "checkpoint.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["schema_version"] = 999
        path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(EventCheckpointStoreError):
            EventCheckpointStore(self.storage).read_checkpoint(self.task.task_id)

    def test_invalid_event_line_fails_closed(self):
        self.store.append_event(self.task.task_id, "ONE", microtask_id="m1")
        task_dir = TaskStore(self.storage).task_directory(self.task.task_id)
        with (task_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("not-json\n")

        with self.assertRaises(EventCheckpointStoreError):
            self.store.read_events(self.task.task_id)


if __name__ == "__main__":
    unittest.main()
