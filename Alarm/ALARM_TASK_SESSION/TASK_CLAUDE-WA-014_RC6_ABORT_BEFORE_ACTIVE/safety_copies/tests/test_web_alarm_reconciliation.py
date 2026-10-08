import hashlib
import tempfile
import unittest
from pathlib import Path

from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import ManifestStatus, MicrotaskStatus
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation import ReconciliationEvidenceCollector
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ReconciliationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()

        self.workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_reconcile",
        )
        self.tasks = TaskStore(self.storage)
        self.task = self.tasks.create_task(
            self.workspace.workspace_id,
            "Reconciliation Task",
            "RAW TASK",
            "Collect evidence only.",
            task_id="task_reconcile",
        )
        self.micro = self.tasks.create_microtask(
            self.task.task_id,
            "M1",
            "Evidence",
            microtask_id="m1",
        )
        self.manifests = ManifestSnapshotStore(self.storage)
        self.operations = OperationStore(self.storage)
        self.collector = ReconciliationEvidenceCollector(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def prepare_existing(self, expected_change="edit"):
        target = self.project / "file.txt"
        before = b"before"
        target.write_bytes(before)
        self.manifests.prepare_microtask(
            self.task.task_id,
            self.micro.microtask_id,
            [("file.txt", expected_change)],
        )
        return target, before

    def begin_operation(self, pre_hash=None, target="file.txt", op_id="op_1"):
        return self.operations.begin(
            self.task.task_id,
            self.micro.microtask_id,
            "write",
            target,
            operation_id=op_id,
            expected_precondition_sha256=pre_hash,
            request_payload={"content": "after"},
        )

    def test_existing_pre_state_is_proven_read_only(self):
        target, before = self.prepare_existing()
        self.begin_operation(pre_hash=sha256(before))
        bytes_before_collect = target.read_bytes()

        evidence = self.collector.collect(
            self.task.task_id,
            self.micro.microtask_id,
            operation_id="op_1",
        )
        item = evidence.targets[0]

        self.assertTrue(evidence.evidence_complete)
        self.assertFalse(evidence.expected_post_complete)
        self.assertEqual(evidence.snapshot_status, "VERIFIED")
        self.assertTrue(item.snapshot_valid)
        self.assertTrue(item.matches_pre_state)
        self.assertIsNone(item.matches_expected_post_state)
        self.assertFalse(item.drift_detected)
        self.assertEqual(item.classification, "PRE_STATE")
        self.assertTrue(item.operation_target)
        self.assertTrue(item.operation_precondition_matches_manifest)
        self.assertEqual(target.read_bytes(), bytes_before_collect)
        self.assertEqual(
            self.tasks.open_microtask("task_reconcile", "m1").status,
            MicrotaskStatus.BACKUP_VERIFIED,
        )
        self.assertEqual(
            self.manifests.open_manifest("task_reconcile", "m1").status,
            ManifestStatus.VERIFIED,
        )

    def test_exact_expected_post_state_is_proven(self):
        target, before = self.prepare_existing()
        self.begin_operation(pre_hash=sha256(before))
        after = b"after"
        target.write_bytes(after)

        evidence = self.collector.collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
            expected_post_state={
                "file.txt": {"exists": True, "sha256": sha256(after)}
            },
        )
        item = evidence.targets[0]

        self.assertTrue(evidence.evidence_complete)
        self.assertTrue(evidence.expected_post_complete)
        self.assertFalse(item.matches_pre_state)
        self.assertTrue(item.matches_expected_post_state)
        self.assertFalse(item.drift_detected)
        self.assertEqual(item.classification, "EXPECTED_POST_STATE")

    def test_current_state_matching_neither_pre_nor_post_is_drift(self):
        target, before = self.prepare_existing()
        self.begin_operation(pre_hash=sha256(before))
        target.write_bytes(b"third-party")

        evidence = self.collector.collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
            expected_post_state={
                "file.txt": {"exists": True, "sha256": sha256(b"expected")}
            },
        )
        item = evidence.targets[0]

        self.assertFalse(item.matches_pre_state)
        self.assertFalse(item.matches_expected_post_state)
        self.assertTrue(item.drift_detected)
        self.assertEqual(item.classification, "DRIFT")

    def test_delete_expected_change_can_prove_absent_post_state(self):
        target, before = self.prepare_existing(expected_change="delete")
        self.begin_operation(pre_hash=sha256(before))
        target.unlink()

        evidence = self.collector.collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
        )
        item = evidence.targets[0]

        self.assertTrue(evidence.expected_post_complete)
        self.assertFalse(item.current_exists)
        self.assertFalse(item.matches_pre_state)
        self.assertTrue(item.matches_expected_post_state)
        self.assertEqual(item.classification, "EXPECTED_POST_STATE")

    def test_new_file_pre_state_and_exact_post_state(self):
        self.manifests.prepare_microtask(
            "task_reconcile",
            "m1",
            [("new.txt", "create")],
        )
        first = self.collector.collect("task_reconcile", "m1")
        item = first.targets[0]
        self.assertTrue(item.matches_pre_state)
        self.assertEqual(item.classification, "PRE_STATE")
        self.assertFalse(first.expected_post_complete)

        created = b"created"
        (self.project / "new.txt").write_bytes(created)
        second = self.collector.collect(
            "task_reconcile",
            "m1",
            expected_post_state={
                "new.txt": {"exists": True, "sha256": sha256(created)}
            },
        )
        item2 = second.targets[0]
        self.assertFalse(item2.matches_pre_state)
        self.assertTrue(item2.matches_expected_post_state)
        self.assertEqual(item2.classification, "EXPECTED_POST_STATE")

    def test_corrupted_snapshot_is_reported_without_mutating_manifest_status(self):
        self.prepare_existing()
        snapshot = self.manifests.list_snapshots("task_reconcile", "m1")[0]
        work_dir = self.tasks.microtask_directory(
            "task_reconcile",
            "m1",
            active_only=True,
        )
        binary = work_dir / "restore_point" / str(snapshot.snapshot_path)
        binary.write_bytes(b"corrupt")

        before_status = self.tasks.open_microtask(
            "task_reconcile", "m1"
        ).status
        evidence = self.collector.collect("task_reconcile", "m1")
        after_status = self.tasks.open_microtask(
            "task_reconcile", "m1"
        ).status

        self.assertFalse(evidence.evidence_complete)
        self.assertEqual(evidence.snapshot_status, "INVALID")
        self.assertFalse(evidence.targets[0].snapshot_valid)
        self.assertEqual(
            evidence.targets[0].classification,
            "MISSING_EVIDENCE",
        )
        self.assertEqual(before_status, MicrotaskStatus.BACKUP_VERIFIED)
        self.assertEqual(after_status, MicrotaskStatus.BACKUP_VERIFIED)
        self.assertEqual(
            self.manifests.open_manifest("task_reconcile", "m1").status,
            ManifestStatus.VERIFIED,
        )

    def test_verified_operation_result_is_exposed_as_verification_evidence(self):
        target, before = self.prepare_existing()
        self.begin_operation(pre_hash=sha256(before))
        self.operations.transition("task_reconcile", "op_1", "STARTED")
        self.operations.transition("task_reconcile", "op_1", "DONE")
        self.operations.transition(
            "task_reconcile",
            "op_1",
            "VERIFIED",
            result_summary="post-state checked",
        )

        evidence = self.collector.collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
        )

        self.assertEqual(evidence.operation_status, "VERIFIED")
        self.assertEqual(
            evidence.verification_evidence,
            "post-state checked",
        )

    def test_new_collector_instance_returns_same_evidence(self):
        target, before = self.prepare_existing()
        self.begin_operation(pre_hash=sha256(before))

        first = self.collector.collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
        ).to_dict()
        second = ReconciliationEvidenceCollector(self.storage).collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
        ).to_dict()

        self.assertEqual(first, second)

    def test_operation_target_outside_manifest_is_flagged(self):
        self.prepare_existing()
        self.begin_operation(target="other.txt")

        evidence = self.collector.collect(
            "task_reconcile",
            "m1",
            operation_id="op_1",
        )

        self.assertFalse(evidence.evidence_complete)
        self.assertIn(
            "operation target is not declared in manifest",
            evidence.errors,
        )

    def test_directory_replacing_file_is_missing_evidence_not_drift_guess(self):
        target, _ = self.prepare_existing()
        target.unlink()
        target.mkdir()

        evidence = self.collector.collect("task_reconcile", "m1")
        item = evidence.targets[0]

        self.assertFalse(evidence.evidence_complete)
        self.assertIsNotNone(item.path_error)
        self.assertIsNone(item.drift_detected)
        self.assertEqual(item.classification, "MISSING_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
