import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.manifest_store import (
    ManifestSnapshotStore,
    ManifestStoreError,
)
from web_alarm.models import ManifestStatus, MicrotaskStatus
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


class ManifestSnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.existing = self.project / "existing.bin"
        self.original_bytes = b"\x00before\r\n"
        self.existing.write_bytes(self.original_bytes)

        registry = WorkspaceRegistry(self.storage)
        workspace = registry.register("Project", self.project)
        self.task_store = TaskStore(self.storage)
        self.task = self.task_store.create_task(
            workspace.workspace_id,
            "Task",
            "RAW TASK",
            "Test manifest and snapshots",
            task_id="task_manifest",
        )
        self.micro = self.task_store.create_microtask(
            self.task.task_id,
            "M1",
            "Prepare restore point",
            microtask_id="m1",
        )
        self.store = ManifestSnapshotStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_prepare_existing_and_new_targets_survives_restart(self):
        manifest = self.store.prepare_microtask(
            self.task.task_id,
            self.micro.microtask_id,
            [("existing.bin", "edit"), ("new.txt", "create")],
        )

        self.assertEqual(manifest.status, ManifestStatus.VERIFIED)
        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BACKUP_VERIFIED,
        )

        reopened = ManifestSnapshotStore(self.storage)
        loaded = reopened.open_manifest(self.task.task_id, "m1")
        entries = reopened.list_entries(self.task.task_id, "m1")
        snapshots = reopened.list_snapshots(self.task.task_id, "m1")

        self.assertEqual(loaded.manifest_id, manifest.manifest_id)
        self.assertEqual(len(entries), 2)
        self.assertEqual(len(snapshots), 2)

        by_path = {item.source_path: item for item in entries}
        self.assertTrue(by_path["existing.bin"].exists_before)
        self.assertEqual(by_path["existing.bin"].size_before, len(self.original_bytes))
        self.assertIsNotNone(by_path["existing.bin"].sha256_before)
        self.assertFalse(by_path["new.txt"].exists_before)
        self.assertIsNone(by_path["new.txt"].snapshot_path)

    def test_restore_returns_existing_bytes_and_removes_new_file(self):
        self.store.prepare_microtask(
            self.task.task_id,
            "m1",
            [("existing.bin", "edit"), ("new.txt", "create")],
        )
        self.existing.write_bytes(b"changed")
        new_file = self.project / "new.txt"
        new_file.write_text("created later", encoding="utf-8")

        self.store.restore_microtask(self.task.task_id, "m1")

        self.assertEqual(self.existing.read_bytes(), self.original_bytes)
        self.assertFalse(new_file.exists())
        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BACKUP_VERIFIED,
        )

    def test_corrupted_snapshot_fails_closed_and_blocks_microtask(self):
        self.store.prepare_microtask(
            self.task.task_id,
            "m1",
            [("existing.bin", "edit")],
        )
        snapshot = self.store.list_snapshots(self.task.task_id, "m1")[0]
        restore_dir = (
            self.task_store.microtask_directory(
                self.task.task_id, "m1", active_only=True
            )
            / "restore_point"
        )
        binary = restore_dir / str(snapshot.snapshot_path)
        binary.write_bytes(b"corrupted")

        with self.assertRaises(ManifestStoreError):
            self.store.verify_restore_point(
                self.task.task_id, "m1", active_only=True
            )

        self.assertEqual(
            self.store.open_manifest(self.task.task_id, "m1").status,
            ManifestStatus.BLOCKED_PREPARE,
        )
        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BLOCKED_PREPARE,
        )

    def test_outside_workspace_target_is_rejected(self):
        outside = self.root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")

        with self.assertRaises(ManifestStoreError):
            self.store.prepare_microtask(
                self.task.task_id,
                "m1",
                [("../outside.txt", "edit")],
            )

        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BLOCKED_PREPARE,
        )
        self.assertFalse(
            (
                self.task_store.microtask_directory(
                    self.task.task_id, "m1", active_only=True
                )
                / "restore_point"
            ).exists()
        )

    def test_duplicate_target_is_rejected_without_publishing_restore_point(self):
        with self.assertRaises(ManifestStoreError):
            self.store.prepare_microtask(
                self.task.task_id,
                "m1",
                [("existing.bin", "edit"), ("existing.bin", "edit again")],
            )

        self.assertFalse(
            (
                self.task_store.microtask_directory(
                    self.task.task_id, "m1", active_only=True
                )
                / "restore_point"
            ).exists()
        )
        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BLOCKED_PREPARE,
        )

    def test_existing_restore_point_is_never_overwritten(self):
        first = self.store.prepare_microtask(
            self.task.task_id,
            "m1",
            [("existing.bin", "edit")],
        )

        with self.assertRaises(ManifestStoreError):
            self.store.prepare_microtask(
                self.task.task_id,
                "m1",
                [("existing.bin", "edit")],
            )

        loaded = self.store.open_manifest(self.task.task_id, "m1")
        self.assertEqual(loaded.manifest_id, first.manifest_id)
        self.assertEqual(loaded.status, ManifestStatus.VERIFIED)

    def test_directory_target_is_rejected(self):
        directory = self.project / "folder"
        directory.mkdir()

        with self.assertRaises(ManifestStoreError):
            self.store.prepare_microtask(
                self.task.task_id,
                "m1",
                [("folder", "edit")],
            )

        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BLOCKED_PREPARE,
        )

    def test_tampered_snapshot_path_is_rejected_before_external_read(self):
        self.store.prepare_microtask(
            self.task.task_id,
            "m1",
            [("existing.bin", "edit")],
        )
        snapshot = self.store.list_snapshots(self.task.task_id, "m1")[0]
        restore_dir = (
            self.task_store.microtask_directory(
                self.task.task_id, "m1", active_only=True
            )
            / "restore_point"
        )
        meta_path = restore_dir / "snapshots" / f"{snapshot.snapshot_id}.json"
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        payload["snapshot_path"] = "..\\..\\outside.bin"
        meta_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ManifestStoreError):
            self.store.verify_restore_point(
                self.task.task_id, "m1", active_only=True
            )

        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.BLOCKED_PREPARE,
        )

    def test_restore_validation_failure_marks_recovery_required(self):
        self.store.prepare_microtask(
            self.task.task_id,
            "m1",
            [("new.txt", "create")],
        )
        (self.project / "new.txt").mkdir()

        with self.assertRaises(ManifestStoreError):
            self.store.restore_microtask(self.task.task_id, "m1")

        self.assertEqual(
            self.task_store.open_microtask(self.task.task_id, "m1").status,
            MicrotaskStatus.RECOVERY_REQUIRED,
        )

    def test_empty_manifest_is_rejected(self):
        with self.assertRaises(ManifestStoreError):
            self.store.prepare_microtask(
                self.task.task_id,
                "m1",
                [],
            )


if __name__ == "__main__":
    unittest.main()
