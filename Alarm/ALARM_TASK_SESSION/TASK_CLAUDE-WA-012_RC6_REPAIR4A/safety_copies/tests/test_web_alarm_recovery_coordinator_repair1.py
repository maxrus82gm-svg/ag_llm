import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.rollback_service as rs

from web_alarm.closeout import CloseoutService
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionService
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import (
    MANUAL_DECISION_REQUIRED,
    READY_FOR_EXECUTION,
    RECOVERY_BLOCKED,
    TASK_READY_TO_CLOSE,
    RecoveryCoordinator,
)
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.target_claim_store import TargetClaimStoreError
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

TASK = "task_repair1"
OTHER = "task_repair1_other"
M1 = "m1"
M2 = "m2"
OP = "op_1"
BEFORE = b"before\n"
AFTER = b"after\n"
KEEP = b"keep\n"


class RecoveryCoordinatorRepair1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.storage = root / "state"
        self.project = root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register(
            "Repair1", self.project, workspace_id="ws_repair1"
        )
        self.tasks = TaskStore(self.storage)
        for task_id in (TASK, OTHER):
            self.tasks.create_task(
                "ws_repair1", task_id, "RAW", "Repair1", task_id=task_id
            )
        self.tasks.create_microtask(TASK, "M1", "one", microtask_id=M1)
        self.tasks.create_microtask(TASK, "M2", "two", microtask_id=M2)
        self.tasks.create_microtask(OTHER, "F1", "foreign", microtask_id="f1")
        self.machine = ServerStateMachine(self.storage)
        self.ops = OperationStore(self.storage)
        self.resolver = ResolverService(self.storage)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def activate(self, mid, specs):
        for source, _action in specs:
            path = self.project / source
            if not path.exists():
                path.write_bytes(BEFORE)
        self.machine.prepare_microtask(TASK, mid, specs)
        self.machine.transition(TASK, mid, MicrotaskStatus.READY)
        self.machine.transition(TASK, mid, MicrotaskStatus.ACTIVE)

    def start_op(self, mid=M1, *, target="one.txt", landed=False):
        self.ops.begin(
            TASK, mid, "write", target,
            operation_id=OP, payload=AFTER,
            request_payload={"case": OP},
        )
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        if landed:
            self.write(target, AFTER)

    def resolve(self, action):
        decision = ReconciliationService(self.storage).reconcile(
            TASK, M1, OP
        )["DECISION"]
        out = self.resolver.apply(
            TASK, M1, OP, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, OP).revision,
            agent="repair1", channel="test",
        )
        self.assertTrue(out["accepted"], out["resolution"].result_reason)
        return out["resolution"]

    def adopt_m1(self):
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        self.start_op(landed=True)
        self.machine.transition(TASK, M1, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("ADOPT")
        first = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(first["state"], "READY_FOR_VERIFICATION")
        self.machine.transition(
            TASK, M1, MicrotaskStatus.VERIFIED,
            verification_evidence="adopt verified",
        )

    def retry_case(self, *, secondary=False):
        self.write("one.txt", BEFORE)
        specs = [("one.txt", "edit")]
        if secondary:
            self.write("extra.txt", KEEP)
            specs.append(("extra.txt", "delete"))
        self.activate(M1, specs)
        self.start_op(landed=False)
        self.machine.transition(TASK, M1, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.resolve("RETRY")
        first = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(first["state"], READY_FOR_EXECUTION)

    def foreign_claim(self, target, operation_id):
        self.ops.begin(
            OTHER, "f1", "write", target,
            operation_id=operation_id, payload=b"foreign\n",
        )
        out = TargetClaimService(self.storage).acquire(
            OTHER, operation_id, operation_revision=1, channel="repair1"
        )
        self.assertEqual(out["result"], "ACQUIRED")

    def test_b1_adopt_verified_does_not_capture_next_active_microtask(self):
        self.adopt_m1()
        self.write("two.txt", BEFORE)
        self.activate(M2, [("two.txt", "edit")])

        projection = ProjectionService(self.storage).build(TASK)
        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(projection["position"]["current_microtask_id"], M2)
        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(result["projection"]["position"]["current_microtask_id"], M2)
        self.assertNotEqual(result["recovery_state"], "ADOPT_SETTLED")

    def test_b1_adopt_history_does_not_block_task_ready_to_close(self):
        self.adopt_m1()
        self.write("two.txt", BEFORE)
        self.activate(M2, [("two.txt", "edit")])
        self.machine.transition(TASK, M2, MicrotaskStatus.DONE)
        self.machine.transition(
            TASK, M2, MicrotaskStatus.VERIFIED,
            verification_evidence="m2 verified",
        )
        self.assertTrue(CloseoutService(self.storage).inspect(TASK)["eligible"])

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], TASK_READY_TO_CLOSE)

    def test_b2_foreign_primary_claim_after_retry_rearm_blocks_replay_ready(self):
        self.retry_case()
        self.foreign_claim("one.txt", "op_foreign_primary")

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)

    def test_b2_foreign_secondary_claim_after_retry_rearm_blocks_replay_ready(self):
        self.retry_case(secondary=True)
        self.foreign_claim("extra.txt", "op_foreign_secondary")

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)

    def legacy_verify_m1(self):
        """M1 VERIFIED despite its still STARTED operation.

        Since Repair #3 (F-B) the state machine refuses this verification; the
        shape stays reachable through the blind storage primitive (data written
        before Repair #3 or by a legacy WA-1 writer).
        """
        self.machine.transition(TASK, M1, MicrotaskStatus.DONE)
        self.tasks.set_microtask_status(TASK, M1, MicrotaskStatus.VERIFIED)

    def test_b3_retry_for_operation_of_verified_microtask_never_uses_later_active_status(self):
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        self.start_op(landed=False)
        self.legacy_verify_m1()
        self.resolve("RETRY")
        self.write("two.txt", BEFORE)
        self.activate(M2, [("two.txt", "edit")])

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertNotEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(
            self.tasks.open_microtask(TASK, M1).status,
            MicrotaskStatus.VERIFIED,
        )

    def test_b3_abort_verified_microtask_settles_administratively_without_moving_it(self):
        # Formerly test_b3_abort_verified_microtask_fails_before_persisting_settlement:
        # it pinned a FAIL_CLOSED that repeated forever (finding F-B). Repair #3
        # takes the B3 option "settlement without changing the microtask": the
        # ABORT is settled in full (no half settlement), M1 stays VERIFIED, and
        # only then does M2, the current stage, get its own READY proof.
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        self.start_op(landed=False)
        self.legacy_verify_m1()
        self.resolve("ABORT")
        self.write("two.txt", BEFORE)
        self.activate(M2, [("two.txt", "edit")])

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual([s["action"] for s in result["performed_steps"]], ["SETTLE_ABORT"])
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ABORT")
        self.assertEqual(
            self.tasks.open_microtask(TASK, M1).status,
            MicrotaskStatus.VERIFIED,
        )
        self.assertEqual(result["state"], READY_FOR_EXECUTION)
        self.assertEqual(result["ready_proof"]["microtask_id"], M2)
        again = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual((again["state"], again["performed_steps"]), (READY_FOR_EXECUTION, []))

    def _prepare_interrupted_rollback(self):
        for name, data in (
            ("a.txt", b"a-before\n"),
            ("b.txt", b"b-before\n"),
            ("c.txt", b"c-keep\n"),
        ):
            self.write(name, data)
        self.machine.prepare_microtask(
            TASK,
            M1,
            [("a.txt", "edit"), ("b.txt", "delete"), ("c.txt", "delete")],
        )
        self.machine.transition(TASK, M1, MicrotaskStatus.READY)
        self.machine.transition(TASK, M1, MicrotaskStatus.ACTIVE)
        self.ops.begin(
            TASK, M1, "write", "a.txt",
            operation_id=OP, payload=b"a-after\n",
        )
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        self.write("a.txt", b"a-after\n")
        (self.project / "b.txt").unlink()
        self.machine.transition(TASK, M1, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        resolution = self.resolve("ROLLBACK")
        rollbacks = RollbackService(self.storage)
        record = rollbacks.prepare(
            TASK, M1, OP, resolution.resolution_id, channel="repair1"
        )["rollback"]
        return rollbacks, record

    def _restore_event_count(self):
        return sum(
            1
            for event in EventCheckpointStore(self.storage).read_events(TASK)
            if event.event_type == "ROLLBACK_TARGET_RESTORED"
        )

    def test_b4_crash_after_one_restored_target_resumes_to_verified(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        crash = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real_event = rs.RollbackService._event
def event(self, record, event_type, payload):
    real_event(self, record, event_type, payload)
    if event_type == "ROLLBACK_TARGET_RESTORED":
        os._exit(18)
rs.RollbackService._event = event
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 18)
        interrupted = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(interrupted["status"], "APPLYING")
        self.assertIn("RESTORED", [t["status"] for t in interrupted["targets"]])
        self.assertEqual(
            ProjectionService(self.storage).build(TASK)["recovery"]["state"],
            "ROLLBACK_APPLYING",
        )

        result = RecoveryCoordinator(self.storage).recover(TASK)

        final = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(final["status"], "VERIFIED")
        self.assertTrue(final["claims_released"])
        self.assertEqual((self.project / "a.txt").read_bytes(), b"a-before\n")
        self.assertEqual((self.project / "b.txt").read_bytes(), b"b-before\n")
        self.assertEqual((self.project / "c.txt").read_bytes(), b"c-keep\n")
        self.assertEqual(self._restore_event_count(), 2)
        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)

    def _assert_applying_crash_resumes(self, mode):
        rollbacks, record = self._prepare_interrupted_rollback()
        crash = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id, mode = sys.argv[1:5]
real = rs._write_restored_bytes
calls = []
def crash(path, data):
    calls.append(1)
    if len(calls) == 1:
        return real(path, data)
    if mode == "after_write":
        real(path, data)
    os._exit(17)
rs._write_restored_bytes = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash,
                str(self.storage), TASK, record["rollback_id"], mode,
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 17)
        interrupted = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(interrupted["status"], "APPLYING")
        self.assertIn("APPLYING", [t["status"] for t in interrupted["targets"]])
        self.assertEqual(
            ProjectionService(self.storage).build(TASK)["recovery"]["state"],
            "ROLLBACK_APPLYING",
        )

        RecoveryCoordinator(self.storage).recover(TASK)

        final = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(final["status"], "VERIFIED")
        self.assertTrue(final["claims_released"])
        self.assertEqual((self.project / "a.txt").read_bytes(), b"a-before\n")
        self.assertEqual((self.project / "b.txt").read_bytes(), b"b-before\n")
        self.assertEqual((self.project / "c.txt").read_bytes(), b"c-keep\n")
        self.assertEqual(self._restore_event_count(), 2)

    def test_b4_applying_write_landed_reconciles_without_double_restore(self):
        self._assert_applying_crash_resumes("after_write")

    def test_b4_applying_write_not_landed_reconciles_and_restores_once(self):
        self._assert_applying_crash_resumes("before_write")

    def test_f2_partial_rollback_is_not_auto_closed_or_released(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        write_targets = [
            t["source_path"]
            for t in record["targets"]
            if t["planned_action"] == "WRITE_RESTORE"
        ]
        self.assertGreaterEqual(len(write_targets), 2)
        real = rs._write_restored_bytes
        calls = []

        def write_then_drift(path, data):
            calls.append(path)
            real(path, data)
            if len(calls) == 1:
                self.write(write_targets[1], b"external drift\n")

        with mock.patch.object(rs, "_write_restored_bytes", write_then_drift):
            outcome = rollbacks.apply(TASK, record["rollback_id"])
        self.assertEqual(outcome["rollback"]["status"], "PARTIAL")
        self.assertFalse(outcome["rollback"]["claims_released"])

        result = RecoveryCoordinator(self.storage).recover(TASK)

        after = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(after["status"], "PARTIAL")
        self.assertFalse(after["claims_released"])

    def _crash_after_first_rollback_restore(self, rollbacks, record):
        crash = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real_event = rs.RollbackService._event
def event(self, record, event_type, payload):
    real_event(self, record, event_type, payload)
    if event_type == "ROLLBACK_TARGET_RESTORED":
        os._exit(18)
rs.RollbackService._event = event
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 18, proc.stderr)
        interrupted = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(interrupted["status"], "APPLYING")
        self.assertIn("RESTORED", [target["status"] for target in interrupted["targets"]])
        self.assertNotIn("APPLYING", [target["status"] for target in interrupted["targets"]])
        return interrupted

    def _project_bytes(self):
        return {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in sorted(self.project.rglob("*"))
            if path.is_file()
        }

    def test_f2_abort_reconciles_landed_inflight_only_then_preserves_ownership(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        crash = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real = rs._write_restored_bytes
def landed_then_crash(path, data):
    real(path, data)
    os._exit(19)
rs._write_restored_bytes = landed_then_crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 19, proc.stderr)
        interrupted = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertIn("APPLYING", [target["status"] for target in interrupted["targets"]])
        before = self._project_bytes()

        self.resolve("ABORT")
        initial_projection = ProjectionService(self.storage).build(TASK)
        result = RecoveryCoordinator(self.storage).recover(TASK)

        after = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(
            initial_projection["recovery"]["state"],
            "ROLLBACK_ABORTED_IN_FLIGHT",
        )
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(
            [step["action"] for step in result["performed_steps"]],
            ["APPLY_ROLLBACK"],
        )
        self.assertEqual(result["recovery_state"], "ROLLBACK_ABORTED_AFTER_EFFECTS")
        self.assertEqual(after["status"], "APPLYING")
        self.assertFalse(after["claims_released"])
        self.assertNotIn("APPLYING", [target["status"] for target in after["targets"]])
        self.assertIn("RESTORED", [target["status"] for target in after["targets"]])
        self.assertEqual(self._project_bytes(), before)

    def test_f2_abort_after_rollback_own_effect_preserves_session_and_claims(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        self._crash_after_first_rollback_restore(rollbacks, record)
        self.resolve("ABORT")
        before = self._project_bytes()

        projection = ProjectionService(self.storage).build(TASK)
        result = RecoveryCoordinator(self.storage).recover(TASK)

        after = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(
            projection["recovery"]["state"],
            "ROLLBACK_ABORTED_AFTER_EFFECTS",
        )
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(result["performed_steps"], [])
        self.assertEqual(after["status"], "APPLYING")
        self.assertFalse(after["claims_released"])
        self.assertEqual(self._project_bytes(), before)

    def test_f2_retry_after_rollback_own_effect_is_rejected_by_public_resolver(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        self._crash_after_first_rollback_restore(rollbacks, record)
        before = self._project_bytes()

        decision = ReconciliationService(self.storage).reconcile(
            TASK, M1, OP
        )["DECISION"]
        retry = self.resolver.apply(
            TASK,
            M1,
            OP,
            "RETRY",
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, OP).revision,
            agent="repair1",
            channel="test",
        )

        after = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertFalse(retry["accepted"])
        self.assertEqual(decision["decision"], "ROLLBACK_CURRENT_MICROTASK")
        self.assertIn("RETRY requires RETRY_SAFE", retry["resolution"].result_reason)
        self.assertEqual(after["status"], "APPLYING")
        self.assertFalse(after["claims_released"])
        self.assertEqual(self._project_bytes(), before)

    def test_normal_active_ready_is_blocked_by_foreign_target_owner(self):
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        self.foreign_claim("one.txt", "op_foreign_normal")

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertIn("already owned", result["reason"])

    def test_b4_crash_after_persisted_drift_resumes_rc4_finalization(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        crash_before_first_effect = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
def crash(path, data):
    os._exit(21)
rs._write_restored_bytes = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash_before_first_effect,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 21)
        applying = rollbacks.inspect(TASK, record["rollback_id"])
        inflight = [t for t in applying["targets"] if t["status"] == "APPLYING"]
        self.assertEqual(len(inflight), 1)
        self.write(inflight[0]["source_path"], b"neither-preserved-nor-restore\n")

        crash_after_drift_persist = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real = rs.RollbackService._stop
def stop(self, record, target, status, code, reason, observed):
    real(self, record, target, status, code, reason, observed)
    if status == rs.T_DRIFTED:
        os._exit(22)
rs.RollbackService._stop = stop
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash_after_drift_persist,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 22)

        persisted = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(persisted["status"], "APPLYING")
        self.assertIn("DRIFTED", [t["status"] for t in persisted["targets"]])

        projection = ProjectionService(self.storage).build(TASK)
        self.assertEqual(projection["recovery"]["state"], "ROLLBACK_APPLYING")

        result = RecoveryCoordinator(self.storage).recover(TASK)

        final = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertIn(final["status"], {"PARTIAL", "FAILED"})
        self.assertFalse(final["claims_released"])
        self.assertEqual(result["state"], RECOVERY_BLOCKED)

    def test_b4_abort_after_persisted_drift_finalizes_but_keeps_ownership(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        crash_before_first_effect = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
def crash(path, data):
    os._exit(21)
rs._write_restored_bytes = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash_before_first_effect,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 21)
        applying = rollbacks.inspect(TASK, record["rollback_id"])
        inflight = [t for t in applying["targets"] if t["status"] == "APPLYING"]
        self.assertEqual(len(inflight), 1)
        self.write(inflight[0]["source_path"], b"neither-preserved-nor-restore\n")

        crash_after_drift_persist = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real = rs.RollbackService._stop
def stop(self, record, target, status, code, reason, observed):
    real(self, record, target, status, code, reason, observed)
    if status == rs.T_DRIFTED:
        os._exit(22)
rs.RollbackService._stop = stop
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash_after_drift_persist,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 22)
        self.resolve("ABORT")

        projection = ProjectionService(self.storage).build(TASK)
        self.assertEqual(
            projection["recovery"]["state"],
            "ROLLBACK_ABORTED_NEEDS_FINALIZE",
        )
        before_restore_events = self._restore_event_count()

        result = RecoveryCoordinator(self.storage).recover(TASK)

        final = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertIn(final["status"], {"PARTIAL", "FAILED"})
        self.assertFalse(final["claims_released"])
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(self._restore_event_count(), before_restore_events)
        self.assertIsNone(self.ops.get(TASK, OP).recovery_settlement)

    def test_b4_verified_release_pending_then_abort_is_release_only_before_abort_settlement(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        with mock.patch.object(
            rollbacks,
            "_release_claims",
            side_effect=TargetClaimStoreError("forced release interruption"),
        ):
            outcome = rollbacks.apply(TASK, record["rollback_id"])
        self.assertEqual(outcome["rollback"]["status"], "VERIFIED")
        self.assertFalse(outcome["rollback"]["claims_released"])
        restore_events = self._restore_event_count()

        self.resolve("ABORT")
        projection = ProjectionService(self.storage).build(TASK)
        self.assertEqual(
            projection["recovery"]["state"],
            "ROLLBACK_ABORTED_RELEASE_PENDING",
        )

        result = RecoveryCoordinator(self.storage).recover(TASK)

        final = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertEqual(final["status"], "VERIFIED")
        self.assertTrue(final["claims_released"])
        self.assertEqual(self._restore_event_count(), restore_events)
        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ABORT")

    def test_b4_persisted_drift_then_abort_finalizes_but_keeps_ownership(self):
        rollbacks, record = self._prepare_interrupted_rollback()
        crash_before_first_effect = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
def crash(path, data):
    os._exit(31)
rs._write_restored_bytes = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash_before_first_effect,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 31)
        applying = rollbacks.inspect(TASK, record["rollback_id"])
        inflight = [t for t in applying["targets"] if t["status"] == "APPLYING"]
        self.assertEqual(len(inflight), 1)
        self.write(inflight[0]["source_path"], b"post-crash-drift\n")

        crash_after_drift = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
real = rs.RollbackService._stop
def stop(self, record, target, status, code, reason, observed):
    real(self, record, target, status, code, reason, observed)
    if status == rs.T_DRIFTED:
        os._exit(32)
rs.RollbackService._stop = stop
rs.RollbackService(storage).apply(task_id, rollback_id)
"""
        proc = subprocess.run(
            [
                sys.executable, "-B", "-c", crash_after_drift,
                str(self.storage), TASK, record["rollback_id"],
            ],
            cwd=Path(__file__).resolve().parent,
        )
        self.assertEqual(proc.returncode, 32)
        self.resolve("ABORT")

        projection = ProjectionService(self.storage).build(TASK)
        self.assertEqual(
            projection["recovery"]["state"],
            "ROLLBACK_ABORTED_NEEDS_FINALIZE",
        )

        result = RecoveryCoordinator(self.storage).recover(TASK)

        final = rollbacks.inspect(TASK, record["rollback_id"])
        self.assertIn(final["status"], {"PARTIAL", "FAILED"})
        self.assertFalse(final["claims_released"])
        self.assertEqual(result["state"], RECOVERY_BLOCKED)
        self.assertEqual(
            result["recovery_state"],
            "ROLLBACK_ABORTED_UNSAFE_FINAL",
        )

    def test_b5_corrupt_restore_point_never_returns_ready(self):
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        restore_dir = (
            self.tasks.task_directory(TASK)
            / "microtasks" / M1 / "restore_point" / "snapshots"
        )
        next(restore_dir.glob("*.bin")).write_bytes(b"corrupt")

        projection = ProjectionService(self.storage).build(TASK)
        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(projection["restore_point"]["status"], "NOT_VERIFIED")
        self.assertIn(
            "RESTORE_POINT_NOT_VERIFIED",
            [item["code"] for item in projection["blockers"]],
        )
        self.assertEqual(projection["authority_source"], "projection_blocker")
        self.assertNotIn("perform scoped implementation", projection["next_safe_action"])
        self.assertNotEqual(result["state"], READY_FOR_EXECUTION)
        self.assertIn("RESTORE_POINT_NOT_VERIFIED", result["next_safe_action"])


    def test_adopt_settlement_written_before_micro_update_is_replayed_once(self):
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        self.ops.begin(
            TASK, M1, "write", "one.txt",
            operation_id=OP, payload=AFTER,
            request_payload={"case": "settlement-crash"},
        )
        acquired = TargetClaimService(self.storage).acquire(
            TASK, OP, operation_revision=1, channel="repair1"
        )
        self.assertEqual(acquired["result"], "ACQUIRED")
        self.ops.transition(TASK, OP, OperationStatus.STARTED)
        self.write("one.txt", AFTER)
        self.machine.transition(TASK, M1, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        resolution = self.resolve("ADOPT")

        with self.ops.task_lock(TASK):
            self.ops._settle_recovery_locked(
                TASK,
                OP,
                "ADOPT",
                resolution_id=resolution.resolution_id,
                expected_revision=resolution.basis["operation_revision"],
            )

        self.assertEqual(
            self.tasks.open_microtask(TASK, M1).status,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )
        self.assertTrue(
            TargetClaimService(self.storage).inspect(TASK, OP)["owned_by_operation"]
        )

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], "READY_FOR_VERIFICATION")
        self.assertEqual(
            self.tasks.open_microtask(TASK, M1).status,
            MicrotaskStatus.DONE,
        )
        self.assertFalse(
            TargetClaimService(self.storage).inspect(TASK, OP)["owned_by_operation"]
        )
        replay = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(replay["state"], "READY_FOR_VERIFICATION")
        self.assertEqual(replay["performed_steps"], [])

    def test_abort_settlement_written_before_micro_update_replays_to_manual_boundary(self):
        self.write("one.txt", BEFORE)
        self.activate(M1, [("one.txt", "edit")])
        self.start_op(landed=False)
        self.machine.transition(TASK, M1, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        resolution = self.resolve("ABORT")

        with self.ops.task_lock(TASK):
            self.ops._settle_recovery_locked(
                TASK,
                OP,
                "ABORT",
                resolution_id=resolution.resolution_id,
                expected_revision=resolution.basis["operation_revision"],
            )

        self.assertEqual(
            self.tasks.open_microtask(TASK, M1).status,
            MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT,
        )

        result = RecoveryCoordinator(self.storage).recover(TASK)

        self.assertEqual(result["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(
            self.tasks.open_microtask(TASK, M1).status,
            MicrotaskStatus.RECOVERY_REQUIRED,
        )
        self.assertIn("explicit project-level replan", result["next_safe_action"])


if __name__ == "__main__":
    unittest.main()
