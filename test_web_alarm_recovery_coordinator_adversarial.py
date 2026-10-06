import tempfile
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.rollback_service as rs
from web_alarm.closeout import CloseoutService
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import (
    FAIL_CLOSED,
    MANUAL_DECISION_REQUIRED,
    READY_FOR_EXECUTION,
    READY_FOR_VERIFICATION,
    RECOVERY_BLOCKED,
    TASK_COMPLETED,
    TASK_READY_TO_CLOSE,
    RecoveryCoordinator,
)
from web_alarm.recovery_report_service import RecoveryReportService
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

TASK = "task_rc6_adv"
OTHER = "task_rc6_other"
MICRO = "m1"
OP = "op_1"
BEFORE = b"before\n"
AFTER = b"after-content\n"
KEEP = b"keep\n"


class RecoveryCoordinatorAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_adv")
        self.tasks = TaskStore(self.storage)
        for task_id in (TASK, OTHER):
            self.tasks.create_task("ws_adv", task_id, "RAW TASK", "RC6 adversarial", task_id=task_id)
            self.tasks.create_microtask(task_id, "M1", "Recovery", microtask_id=MICRO)
        self.ops = OperationStore(self.storage)
        self.resolver = ResolverService(self.storage)
        self.rollbacks = RollbackService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def set_micro(self, status, task_id=TASK):
        self.tasks.set_microtask_status(task_id, MICRO, status)

    def started_operation(self, *, at, kind="single", acquire_before_start=False):
        self.write("target.txt", BEFORE)
        specs = [("target.txt", "edit")]
        if kind == "mixed":
            self.write("keep.txt", KEEP)
            specs.append(("keep.txt", "delete"))
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, MICRO, specs)
        self.ops.begin(
            TASK, MICRO, "write", "target.txt",
            operation_id=OP, payload=AFTER, request_payload={"case": OP},
        )
        claim = None
        if acquire_before_start:
            claim = TargetClaimService(self.storage).acquire(
                TASK, OP, operation_revision=1, channel="adv-test"
            )
            self.assertEqual(claim["result"], "ACQUIRED")
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        self.write("target.txt", at)
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        return claim

    def resolve(self, action, operation_id=OP):
        decision = ReconciliationService(self.storage).reconcile(
            TASK, MICRO, operation_id
        )["DECISION"]
        result = self.resolver.apply(
            TASK, MICRO, operation_id, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, operation_id).revision,
            agent="adv-test", channel="test",
        )
        self.assertTrue(result["accepted"], result["resolution"].result_reason)
        return result["resolution"]

    def coordinator(self):
        return RecoveryCoordinator(self.storage)

    def prepare_open_rollback(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        record = self.rollbacks.prepare(
            TASK, MICRO, OP, resolution.resolution_id, channel="adv-test"
        )["rollback"]
        return resolution, record

    def test_open_rollback_then_abort_closes_without_destructive_restore(self):
        _, record = self.prepare_open_rollback()
        self.resolve("ABORT")
        before_target = (self.project / "target.txt").read_bytes()
        before_keep = (self.project / "keep.txt").read_bytes()

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual((self.project / "target.txt").read_bytes(), before_target)
        self.assertEqual((self.project / "keep.txt").read_bytes(), before_keep)
        self.assertEqual(
            self.rollbacks.inspect(TASK, record["rollback_id"])["status"], "CLOSED"
        )
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ABORT")

    def test_open_rollback_then_retry_closes_old_session_before_ready(self):
        _, record = self.prepare_open_rollback()
        self.write("target.txt", BEFORE)
        self.resolve("RETRY")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.ACTIVE)
        self.assertEqual((self.project / "target.txt").read_bytes(), BEFORE)
        self.assertEqual((self.project / "keep.txt").read_bytes(), KEEP)
        self.assertEqual(
            self.rollbacks.inspect(TASK, record["rollback_id"])["status"], "CLOSED"
        )
        actions = [step["action"] for step in result["performed_steps"]]
        self.assertEqual(actions[:2], ["CLOSE_ROLLBACK", "REARM_RETRY"])

    def test_open_rollback_then_adopt_closes_old_session_before_settlement(self):
        _, record = self.prepare_open_rollback()
        (self.project / "keep.txt").unlink()
        self.resolve("ADOPT")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], READY_FOR_VERIFICATION)
        self.assertEqual((self.project / "target.txt").read_bytes(), AFTER)
        self.assertFalse((self.project / "keep.txt").exists())
        self.assertEqual(
            self.rollbacks.inspect(TASK, record["rollback_id"])["status"], "CLOSED"
        )
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ADOPT")

    def test_stale_open_rollback_is_closed_without_destructive_apply(self):
        _, record = self.prepare_open_rollback()
        self.write("target.txt", b"conflicting-state\n")
        before = (self.project / "target.txt").read_bytes()

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual((self.project / "target.txt").read_bytes(), before)
        self.assertEqual(
            self.rollbacks.inspect(TASK, record["rollback_id"])["status"], "CLOSED"
        )
        self.assertNotIn("APPLY_ROLLBACK", [step["action"] for step in result["performed_steps"]])

    def test_aborted_in_flight_target_is_reconciled_then_closed_without_restore(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        record = self.rollbacks.prepare(
            TASK, MICRO, OP, resolution.resolution_id, channel="adv-test"
        )["rollback"]
        before_target = (self.project / "target.txt").read_bytes()
        before_keep = (self.project / "keep.txt").read_bytes()

        with mock.patch.object(rs, "_write_restored_bytes", side_effect=KeyboardInterrupt("crash")):
            with self.assertRaises(KeyboardInterrupt):
                self.rollbacks.apply(TASK, record["rollback_id"])
        interrupted = self.rollbacks.inspect(TASK, record["rollback_id"])
        self.assertIn("APPLYING", [target["status"] for target in interrupted["targets"]])
        self.resolve("ABORT")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual((self.project / "target.txt").read_bytes(), before_target)
        self.assertEqual((self.project / "keep.txt").read_bytes(), before_keep)
        self.assertEqual(
            self.rollbacks.inspect(TASK, record["rollback_id"])["status"], "CLOSED"
        )
        self.assertIn("APPLY_ROLLBACK", [step["action"] for step in result["performed_steps"]])

    def test_superseded_in_flight_rollback_fails_closed_without_blind_apply(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        record = self.rollbacks.prepare(
            TASK, MICRO, OP, resolution.resolution_id, channel="adv-test"
        )["rollback"]
        real_write = rs._write_restored_bytes

        def write_then_crash(path, data):
            real_write(path, data)
            raise KeyboardInterrupt("crash after write")

        with mock.patch.object(rs, "_write_restored_bytes", side_effect=write_then_crash):
            with self.assertRaises(KeyboardInterrupt):
                self.rollbacks.apply(TASK, record["rollback_id"])
        self.assertIn(
            "APPLYING",
            [target["status"] for target in self.rollbacks.inspect(TASK, record["rollback_id"])["targets"]],
        )
        self.resolve("RETRY")
        before = (self.project / "target.txt").read_bytes()

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(result["performed_steps"], [])
        self.assertEqual((self.project / "target.txt").read_bytes(), before)
        self.assertEqual(
            self.rollbacks.inspect(TASK, record["rollback_id"])["status"], "APPLYING"
        )

    def test_multiple_open_rollbacks_fail_closed_without_silent_selection(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.started_operation(at=AFTER, kind="mixed")
        first_resolution = self.resolve("ROLLBACK")
        first = self.rollbacks.prepare(
            TASK, MICRO, OP, first_resolution.resolution_id, channel="adv-test"
        )["rollback"]

        self.write("target.txt", BEFORE)
        self.resolve("RETRY")
        self.ops.transition(TASK, OP, OperationStatus.UNKNOWN_AFTER_DISCONNECT)
        self.write("target.txt", AFTER)
        second_resolution = self.resolve("ROLLBACK")
        second = self.rollbacks.prepare(
            TASK, MICRO, OP, second_resolution.resolution_id, channel="adv-test"
        )["rollback"]

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(result["performed_steps"], [])
        open_ids = set(result["projection"]["recovery"]["open_rollback_ids"])
        self.assertEqual(open_ids, {first["rollback_id"], second["rollback_id"]})

    def test_fresh_process_finishes_adopt_after_lost_response_between_settlement_and_cleanup(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        claim = self.started_operation(
            at=AFTER, kind="single", acquire_before_start=True
        )
        resolution = self.resolve("ADOPT")

        with self.ops.task_lock(TASK):
            settled = self.ops._settle_recovery_locked(
                TASK, OP, "ADOPT",
                resolution_id=resolution.resolution_id,
                expected_revision=resolution.basis["operation_revision"],
            )
        self.assertTrue(settled["changed"])
        self.assertEqual(
            self.tasks.open_microtask(TASK, MICRO).status,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )
        self.assertTrue(
            TargetClaimService(self.storage).inspect(TASK, OP)["owned_by_operation"]
        )

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], READY_FOR_VERIFICATION)
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.DONE)
        self.assertFalse(
            TargetClaimService(self.storage).inspect(TASK, OP)["owned_by_operation"]
        )
        self.assertEqual((self.project / "target.txt").read_bytes(), AFTER)

    def test_corrupt_checkpoint_cannot_steer_recover(self):
        self.set_micro(MicrotaskStatus.ACTIVE)
        task_dir = self.tasks.task_directory(TASK)
        (task_dir / "checkpoint.json").write_text("{broken", encoding="utf-8")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(result["performed_steps"], [])

    def test_stale_recovery_report_cannot_override_fresh_retry(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.started_operation(at=BEFORE)
        report = RecoveryReportService(self.storage).create_report(
            task_id=TASK,
            microtask_id=MICRO,
            operation_id=OP,
            incident_id="before_retry",
        )
        self.resolve("RETRY")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertIsNotNone(report.report_id)
        self.assertEqual(result["recovery_state"], "RETRY_ACCEPTED")

    def test_foreign_claim_blocks_retry_and_is_not_released(self):
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.started_operation(at=BEFORE)
        self.resolve("RETRY")

        other_ops = OperationStore(self.storage)
        other_ops.begin(
            OTHER, MICRO, "write", "target.txt",
            operation_id="op_other", payload=b"other\n",
        )
        claims = TargetClaimService(self.storage)
        acquired = claims.acquire(
            OTHER, "op_other", operation_revision=1, channel="adv-test"
        )
        self.assertEqual(acquired["result"], "ACQUIRED")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(
            self.tasks.open_microtask(TASK, MICRO).status,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )
        owner = claims.inspect(OTHER, "op_other")
        self.assertTrue(owner["owned_by_operation"])

    def test_foreign_claim_on_secondary_target_blocks_retry_basis(self):
        self.write("target.txt", BEFORE)
        self.write("extra.txt", KEEP)
        ManifestSnapshotStore(self.storage).prepare_microtask(
            TASK, MICRO, [("target.txt", "edit"), ("extra.txt", "delete")]
        )
        self.ops.begin(
            TASK, MICRO, "write", "target.txt",
            operation_id=OP, payload=AFTER, request_payload={"case": OP},
        )
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("RETRY")

        other_ops = OperationStore(self.storage)
        other_ops.begin(
            OTHER, MICRO, "write", "extra.txt",
            operation_id="op_other_extra", payload=b"other\n",
        )
        claims = TargetClaimService(self.storage)
        acquired = claims.acquire(
            OTHER, "op_other_extra", operation_revision=1, channel="adv-test"
        )
        self.assertEqual(acquired["result"], "ACQUIRED")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(
            self.tasks.open_microtask(TASK, MICRO).status,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )
        self.assertTrue(
            claims.inspect(OTHER, "op_other_extra")["owned_by_operation"]
        )

    def test_foreign_claim_on_secondary_target_blocks_adopt_basis(self):
        self.write("target.txt", BEFORE)
        self.write("extra.txt", KEEP)
        ManifestSnapshotStore(self.storage).prepare_microtask(
            TASK, MICRO, [("target.txt", "edit"), ("extra.txt", "delete")]
        )
        self.ops.begin(
            TASK, MICRO, "write", "target.txt",
            operation_id=OP, payload=AFTER, request_payload={"case": OP},
        )
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        self.write("target.txt", AFTER)
        (self.project / "extra.txt").unlink()
        self.set_micro(MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ADOPT")

        other_ops = OperationStore(self.storage)
        other_ops.begin(
            OTHER, MICRO, "create", "extra.txt",
            operation_id="op_other_extra", payload=b"other\n",
        )
        claims = TargetClaimService(self.storage)
        acquired = claims.acquire(
            OTHER, "op_other_extra", operation_revision=1, channel="adv-test"
        )
        self.assertEqual(acquired["result"], "ACQUIRED")

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertIsNone(self.ops.get(TASK, OP).recovery_settlement)
        self.assertEqual(
            self.tasks.open_microtask(TASK, MICRO).status,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )
        self.assertTrue(
            claims.inspect(OTHER, "op_other_extra")["owned_by_operation"]
        )

    def test_projection_contradiction_fails_closed(self):
        self.tasks.create_microtask(TASK, "M2", "Second", microtask_id="m2")
        self.tasks.set_microtask_status(TASK, MICRO, MicrotaskStatus.ACTIVE)
        self.tasks.set_microtask_status(TASK, "m2", MicrotaskStatus.ACTIVE)

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], FAIL_CLOSED)
        self.assertTrue(result["requires_human"])
        self.assertEqual(result["performed_steps"], [])
        blocker_codes = [item["code"] for item in result["projection"]["blockers"]]
        self.assertTrue(
            {"MULTIPLE_ACTIVE", "LATER_STAGE_STARTED"}.intersection(blocker_codes)
        )

    def test_completed_task_is_read_only_terminal_result(self):
        self.tasks.complete_task(TASK)

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], TASK_COMPLETED)
        self.assertEqual(result["performed_steps"], [])
        self.assertEqual(self.tasks.open_task(TASK).status.value, "COMPLETED")

    def test_closeout_eligible_task_is_not_silently_completed(self):
        self.tasks.set_microtask_status(TASK, MICRO, MicrotaskStatus.VERIFIED)

        result = self.coordinator().recover(TASK)

        self.assertEqual(result["state"], TASK_READY_TO_CLOSE)
        self.assertEqual(self.tasks.open_task(TASK).status.value, "PLANNED")
        self.assertEqual(result["performed_steps"], [])
        self.assertTrue(CloseoutService(self.storage).inspect(TASK)["eligible"])


if __name__ == "__main__":
    unittest.main()
