import json
import unittest
from datetime import datetime

from web_alarm.models import (
    SCHEMA_VERSION,
    CheckpointRecord,
    EventRecord,
    ManifestEntry,
    MicrotaskRecord,
    MicrotaskStatus,
    OperationRecord,
    OperationStatus,
    SnapshotRecord,
    TaskRecord,
    TaskStatus,
    VerificationRecord,
    VerificationStatus,
    WorkspaceRegistration,
    record_to_dict,
)


class WebAlarmModelTests(unittest.TestCase):
    def _assert_common_record_fields(self, record, id_attr, prefix):
        record_id = getattr(record, id_attr)
        self.assertTrue(record_id.startswith(prefix + "_"))
        self.assertEqual(record.schema_version, SCHEMA_VERSION)
        self.assertIsNotNone(datetime.fromisoformat(record.created_at).tzinfo)
        self.assertIsNotNone(datetime.fromisoformat(record.updated_at).tzinfo)

    def test_all_core_records_have_stable_identity_version_and_timestamps(self):
        workspace = WorkspaceRegistration(
            display_name="ag_llm",
            workspace_root=r"M:\GitHub\ag_llm",
        )
        task = TaskRecord(
            workspace_id=workspace.workspace_id,
            title="WA-1",
            raw_task="Build Web Alarm Workspace core.",
            goal="Persist recoverable task state.",
        )
        micro = MicrotaskRecord(
            task_id=task.task_id,
            sequence=1,
            title="WA-1.1",
            goal="Define data schemas.",
        )
        manifest = ManifestEntry(
            microtask_id=micro.microtask_id,
            source_path="server.py",
            expected_change="edit",
            exists_before=True,
        )
        snapshot = SnapshotRecord(
            microtask_id=micro.microtask_id,
            manifest_entry_id=manifest.manifest_entry_id,
            source_path="server.py",
            exists_before=True,
            size_before=123,
            sha256_before="abc",
            snapshot_path="snapshots/server.py",
        )
        operation = OperationRecord(
            task_id=task.task_id,
            microtask_id=micro.microtask_id,
            action="edit",
            target="server.py",
        )
        verification = VerificationRecord(
            task_id=task.task_id,
            microtask_id=micro.microtask_id,
            operation_id=operation.operation_id,
            check_name="readback",
        )
        checkpoint = CheckpointRecord(
            task_id=task.task_id,
            workspace_id=workspace.workspace_id,
            current_microtask_id=micro.microtask_id,
            current_status=MicrotaskStatus.READY,
            snapshot_status="VERIFIED",
            last_operation_id=operation.operation_id,
            next_safe_action="begin implementation",
        )
        event = EventRecord(
            task_id=task.task_id,
            microtask_id=micro.microtask_id,
            operation_id=operation.operation_id,
            event_type="MICROTASK_READY",
            payload={"snapshot_status": "VERIFIED"},
        )

        checks = [
            (workspace, "workspace_id", "ws"),
            (task, "task_id", "task"),
            (micro, "microtask_id", "micro"),
            (manifest, "manifest_entry_id", "manifest"),
            (snapshot, "snapshot_id", "snapshot"),
            (operation, "operation_id", "op"),
            (verification, "verification_id", "verify"),
            (checkpoint, "checkpoint_id", "checkpoint"),
            (event, "event_id", "event"),
        ]
        for record, id_attr, prefix in checks:
            with self.subTest(record=type(record).__name__):
                self._assert_common_record_fields(record, id_attr, prefix)

    def test_microtask_state_machine_includes_recovery_states(self):
        expected = {
            "PLANNED",
            "PREPARING",
            "BACKUP_VERIFIED",
            "READY",
            "ACTIVE",
            "DONE",
            "VERIFIED",
            "BLOCKED_PREPARE",
            "UNKNOWN_AFTER_DISCONNECT",
            "RECOVERY_REQUIRED",
            "FAILED_VERIFICATION",
        }
        self.assertEqual({status.value for status in MicrotaskStatus}, expected)

    def test_operation_schema_supports_replay_and_unknown_disconnect_state(self):
        operation = OperationRecord(
            task_id="task_1",
            microtask_id="micro_1",
            action="write",
            target="file.txt",
            request_fingerprint="sha256:request",
            expected_precondition_sha256="sha256:before",
            status=OperationStatus.UNKNOWN_AFTER_DISCONNECT,
        )
        data = record_to_dict(operation)
        self.assertEqual(data["status"], "UNKNOWN_AFTER_DISCONNECT")
        self.assertEqual(data["request_fingerprint"], "sha256:request")
        self.assertEqual(data["expected_precondition_sha256"], "sha256:before")
        json.dumps(data)

    def test_new_file_snapshot_has_explicit_nonexistent_pre_state(self):
        manifest = ManifestEntry(
            microtask_id="micro_1",
            source_path="new_file.py",
            expected_change="create",
            exists_before=False,
        )
        snapshot = SnapshotRecord(
            microtask_id="micro_1",
            manifest_entry_id=manifest.manifest_entry_id,
            source_path="new_file.py",
            exists_before=False,
        )
        self.assertFalse(snapshot.exists_before)
        self.assertIsNone(snapshot.snapshot_path)
        self.assertIsNone(snapshot.sha256_before)

    def test_existing_file_snapshot_requires_restore_path(self):
        with self.assertRaises(ValueError):
            SnapshotRecord(
                microtask_id="micro_1",
                manifest_entry_id="manifest_1",
                source_path="server.py",
                exists_before=True,
            )

    def test_checkpoint_carries_next_safe_action(self):
        checkpoint = CheckpointRecord(
            task_id="task_1",
            workspace_id="ws_1",
            current_microtask_id="micro_1",
            current_status=MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
            snapshot_status="VERIFIED",
            last_operation_id="op_1",
            next_safe_action="reconcile disk state",
        )
        data = record_to_dict(checkpoint)
        self.assertEqual(data["current_status"], "UNKNOWN_AFTER_DISCONNECT")
        self.assertEqual(data["next_safe_action"], "reconcile disk state")
        json.dumps(data)

    def test_task_and_verification_statuses_are_json_friendly(self):
        task = TaskRecord(
            workspace_id="ws_1",
            title="Task",
            raw_task="Do work",
            goal="Finish safely",
            status=TaskStatus.ACTIVE,
        )
        verification = VerificationRecord(
            task_id=task.task_id,
            microtask_id="micro_1",
            check_name="hash",
            status=VerificationStatus.PASS,
            evidence="sha256 matched",
        )
        self.assertEqual(record_to_dict(task)["status"], "ACTIVE")
        self.assertEqual(record_to_dict(verification)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
