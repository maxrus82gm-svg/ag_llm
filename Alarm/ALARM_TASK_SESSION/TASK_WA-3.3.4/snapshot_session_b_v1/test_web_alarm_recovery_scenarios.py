import hashlib
import tempfile
import unittest
from pathlib import Path

from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RecoveryScenarioMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()

        workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_recovery_matrix",
        )
        self.tasks = TaskStore(self.storage)
        self.task = self.tasks.create_task(
            workspace.workspace_id,
            "Recovery Matrix",
            "RAW TASK",
            "Prove recovery decisions.",
            task_id="task_recovery_matrix",
        )
        self.micro = self.tasks.create_microtask(
            self.task.task_id,
            "M1",
            "Recovery scenario",
            microtask_id="m1",
        )
        self.machine = ServerStateMachine(self.storage)
        self.operations = OperationStore(self.storage)
        self.service = ReconciliationService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def prepare(self, targets):
        specs = []
        for name, before in targets.items():
            (self.project / name).write_bytes(before)
            specs.append((name, "edit"))
        self.machine.prepare_microtask(
            self.task.task_id,
            self.micro.microtask_id,
            specs,
            operation_id="prepare_m1",
        )

    def begin_operation(self, target, before, status="INTENT", operation_id="op_case"):
        self.operations.begin(
            self.task.task_id,
            self.micro.microtask_id,
            "write",
            target,
            operation_id=operation_id,
            expected_precondition_sha256=sha256(before),
            request_payload={"scenario": operation_id},
        )
        if status != "INTENT":
            self.operations.transition(
                self.task.task_id,
                operation_id,
                status,
            )

    def test_retry_safe_when_operation_never_left_intent_and_workspace_is_pre_state(self):
        before = b"before"
        after = b"after"
        self.prepare({"file.txt": before})
        self.begin_operation("file.txt", before, status="INTENT", operation_id="op_retry")
        original = (self.project / "file.txt").read_bytes()

        result = self.service.reconcile(
            self.task.task_id,
            self.micro.microtask_id,
            "op_retry",
            expected_post_state={
                "file.txt": {"exists": True, "sha256": sha256(after)}
            },
        )

        self.assertEqual(result["DECISION"]["decision"], "RETRY_SAFE")
        self.assertEqual(result["DECISION"]["reason_code"], "INTENT_AND_PRE_STATE")
        self.assertFalse(result["MUTATION_PERFORMED"])
        self.assertEqual((self.project / "file.txt").read_bytes(), original)

    def test_adopt_current_state_when_started_operation_reached_exact_post_state(self):
        before = b"before"
        after = b"after"
        self.prepare({"file.txt": before})
        self.begin_operation("file.txt", before, status="STARTED", operation_id="op_adopt")
        (self.project / "file.txt").write_bytes(after)
        current = (self.project / "file.txt").read_bytes()

        result = self.service.reconcile(
            self.task.task_id,
            self.micro.microtask_id,
            "op_adopt",
            expected_post_state={
                "file.txt": {"exists": True, "sha256": sha256(after)}
            },
        )

        self.assertEqual(result["DECISION"]["decision"], "ADOPT_CURRENT_STATE")
        self.assertEqual(result["DECISION"]["reason_code"], "EXACT_POST_STATE_PROVEN")
        self.assertFalse(result["MUTATION_PERFORMED"])
        self.assertEqual((self.project / "file.txt").read_bytes(), current)

    def test_partial_known_multi_target_state_requests_current_microtask_rollback(self):
        before_a = b"before-a"
        before_b = b"before-b"
        after_a = b"after-a"
        after_b = b"after-b"
        self.prepare({"a.txt": before_a, "b.txt": before_b})
        self.begin_operation("a.txt", before_a, status="STARTED", operation_id="op_partial")
        (self.project / "a.txt").write_bytes(after_a)

        result = self.service.reconcile(
            self.task.task_id,
            self.micro.microtask_id,
            "op_partial",
            expected_post_state={
                "a.txt": {"exists": True, "sha256": sha256(after_a)},
                "b.txt": {"exists": True, "sha256": sha256(after_b)},
            },
        )

        self.assertEqual(
            result["DECISION"]["decision"],
            "ROLLBACK_CURRENT_MICROTASK",
        )
        self.assertEqual(result["DECISION"]["reason_code"], "PARTIAL_KNOWN_STATE")
        self.assertFalse(result["MUTATION_PERFORMED"])
        self.assertEqual((self.project / "a.txt").read_bytes(), after_a)
        self.assertEqual((self.project / "b.txt").read_bytes(), before_b)

    def test_third_party_drift_requires_manual_review(self):
        before = b"before"
        expected = b"expected"
        drift = b"third-party-drift"
        self.prepare({"file.txt": before})
        self.begin_operation("file.txt", before, status="STARTED", operation_id="op_drift")
        (self.project / "file.txt").write_bytes(drift)

        result = self.service.reconcile(
            self.task.task_id,
            self.micro.microtask_id,
            "op_drift",
            expected_post_state={
                "file.txt": {"exists": True, "sha256": sha256(expected)}
            },
        )

        self.assertEqual(
            result["DECISION"]["decision"],
            "MANUAL_REVIEW_REQUIRED",
        )
        self.assertEqual(
            result["DECISION"]["reason_code"],
            "UNSAFE_TARGET_CLASSIFICATION",
        )
        self.assertEqual(result["EVIDENCE"]["targets"][0]["classification"], "DRIFT")
        self.assertFalse(result["MUTATION_PERFORMED"])
        self.assertEqual((self.project / "file.txt").read_bytes(), drift)


if __name__ == "__main__":
    unittest.main()
