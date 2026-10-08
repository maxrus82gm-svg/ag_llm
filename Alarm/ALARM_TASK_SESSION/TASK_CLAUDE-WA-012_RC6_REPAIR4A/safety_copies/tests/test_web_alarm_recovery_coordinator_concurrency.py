import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus, OperationStatus
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_coordinator import (
    FAIL_CLOSED,
    MANUAL_DECISION_REQUIRED,
    READY_FOR_EXECUTION,
    RecoveryCoordinator,
)
from web_alarm.resolver_service import ResolverService
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_rc6_concurrency"
OTHER = "task_rc6_foreign"
MICRO = "m1"
OP = "op_1"
BEFORE = b"before\n"
AFTER = b"after\n"

RECOVER_CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.recovery_coordinator import RecoveryCoordinator
storage, task_id, barrier, name = sys.argv[1:5]
barrier = Path(barrier)
(barrier / ("ready_" + name)).touch()
deadline = time.monotonic() + 60
while not (barrier / "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.001)
out = RecoveryCoordinator(storage, lock_timeout=30).recover(task_id)
print(json.dumps({
    "state": out["state"],
    "actions": [step["action"] for step in out["performed_steps"]],
    "recovery_state": out["recovery_state"],
    "error": out["error"],
}))
"""

PAUSED_RETRY_CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.recovery_coordinator import RecoveryCoordinator
storage, task_id, barrier = sys.argv[1:4]
barrier = Path(barrier)
coord = RecoveryCoordinator(storage, lock_timeout=30)
real = coord._rearm_retry
def paused(task_id_arg, projection):
    (barrier / "retry_classified").touch()
    deadline = time.monotonic() + 60
    while not (barrier / "abort_done").exists():
        if time.monotonic() > deadline:
            raise RuntimeError("abort barrier timeout")
        time.sleep(0.001)
    return real(task_id_arg, projection)
coord._rearm_retry = paused
out = coord.recover(task_id)
print(json.dumps({
    "state": out["state"],
    "actions": [step["action"] for step in out["performed_steps"]],
    "recovery_state": out["recovery_state"],
    "error": out["error"],
    "reason": out["reason"],
}))
"""

NEW_OPERATION_CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.operation_store import OperationStore
from web_alarm.target_claim_service import TargetClaimService
storage, task_id, microtask_id, barrier = sys.argv[1:5]
barrier = Path(barrier)
(barrier / "ready_new").touch()
deadline = time.monotonic() + 60
while not (barrier / "go").exists():
    if time.monotonic() > deadline:
        raise SystemExit("barrier timeout")
    time.sleep(0.001)
ops = OperationStore(storage)
ops.begin(
    task_id, microtask_id, "write", "target.txt",
    operation_id="op_new", payload=b"new\n", request_payload={"case": "new"},
)
claims = TargetClaimService(storage)
acquired = claims.acquire(task_id, "op_new", operation_revision=1, channel="race-new")
authorized = claims.authorize(task_id, "op_new", operation_revision=1)
print(json.dumps({
    "acquire": acquired["result"],
    "acquire_code": acquired["result_code"],
    "authorized": authorized["authorized"],
    "authorize_code": authorized["result_code"],
}))
"""

PAUSED_READY_CHILD = r"""
import json, sys, time
from pathlib import Path
from web_alarm.recovery_coordinator import RecoveryCoordinator
storage, task_id, barrier = sys.argv[1:4]
barrier = Path(barrier)
coord = RecoveryCoordinator(storage, lock_timeout=30)
real = coord._prove_retry_ready
def paused(task_id_arg, projection):
    (barrier / "proof_waiting").touch()
    deadline = time.monotonic() + 60
    while not (barrier / "foreign_done").exists():
        if time.monotonic() > deadline:
            raise RuntimeError("foreign claim barrier timeout")
        time.sleep(0.001)
    return real(task_id_arg, projection)
coord._prove_retry_ready = paused
out = coord.recover(task_id)
print(json.dumps({
    "state": out["state"],
    "error": out["error"],
    "reason": out["reason"],
}))
"""

FOREIGN_CLAIM_CHILD = r"""
import json, sys
from web_alarm.target_claim_service import TargetClaimService
storage, task_id, operation_id = sys.argv[1:4]
out = TargetClaimService(storage).acquire(
    task_id, operation_id, operation_revision=1, channel="foreign-race"
)
print(json.dumps({
    "result": out["result"],
    "result_code": out["result_code"],
}))
"""

ABORT_CHILD = r"""
import json, sys
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.resolver_service import ResolverService
storage, task_id, microtask_id, operation_id = sys.argv[1:5]
decision = ReconciliationService(storage).reconcile(task_id, microtask_id, operation_id)["DECISION"]
revision = OperationStore(storage).get(task_id, operation_id).revision
out = ResolverService(storage).apply(
    task_id, microtask_id, operation_id, "ABORT",
    evidence_fingerprint=decision["evidence_fingerprint"],
    operation_revision=revision,
    agent="race-abort", channel="multiprocess",
)
print(json.dumps({
    "accepted": out["accepted"],
    "resolution_id": out["resolution"].resolution_id,
    "result": out["resolution"].result.value,
}))
"""


class RecoveryCoordinatorConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.target = self.project / "target.txt"
        self.extra = self.project / "extra.txt"
        self.target.write_bytes(BEFORE)
        WorkspaceRegistry(self.storage).register("RC6", self.project, workspace_id="ws_rc6_concurrency")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task(
            "ws_rc6_concurrency", "RC6", "RAW TASK", "Recovery", task_id=TASK
        )
        self.tasks.create_microtask(TASK, "M1", "Recovery step", microtask_id=MICRO)
        self.tasks.create_task(
            "ws_rc6_concurrency", "Foreign", "RAW TASK", "Foreign", task_id=OTHER
        )
        self.tasks.create_microtask(OTHER, "F1", "Foreign", microtask_id="f1")
        self.ops = OperationStore(self.storage)
        self.resolver = ResolverService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def prepare(self, specs=(("target.txt", "edit"),)):
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, MICRO, list(specs))

    def begin_started(self, *, acquire_before_start=False):
        self.ops.begin(
            TASK, MICRO, "write", "target.txt",
            operation_id=OP, payload=AFTER, request_payload={"case": OP},
        )
        if acquire_before_start:
            acquired = TargetClaimService(self.storage).acquire(
                TASK, OP, operation_revision=1, channel="race-old"
            )
            self.assertEqual(acquired["result"], "ACQUIRED")
        self.ops.transition(TASK, OP, OperationStatus.STARTED)

    def resolve(self, action):
        decision = ReconciliationService(self.storage).reconcile(TASK, MICRO, OP)["DECISION"]
        revision = self.ops.get(TASK, OP).revision
        return self.resolver.apply(
            TASK, MICRO, OP, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=revision,
            agent="race-test", channel="multiprocess",
        )

    def retry_case(self, specs=(("target.txt", "edit"),)):
        self.prepare(specs)
        self.tasks.set_microtask_status(TASK, MICRO, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        result = self.resolve("RETRY")
        self.assertTrue(result["accepted"])

    def rollback_case(self):
        self.extra.write_bytes(b"keep\n")
        self.prepare((("target.txt", "edit"), ("extra.txt", "delete")))
        self.tasks.set_microtask_status(TASK, MICRO, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.begin_started()
        self.target.write_bytes(AFTER)
        result = self.resolve("ROLLBACK")
        self.assertTrue(result["accepted"])

    def start_recover_children(self, count):
        barrier = self.root / "barrier"
        barrier.mkdir()
        children = []
        for index in range(count):
            name = str(index)
            child = subprocess.Popen(
                [
                    sys.executable, "-B", "-c", RECOVER_CHILD,
                    str(self.storage), TASK, str(barrier), name,
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            children.append(child)
        deadline = time.monotonic() + 30
        while len(list(barrier.glob("ready_*"))) < count:
            if time.monotonic() > deadline:
                self.fail("recover children did not reach barrier")
            time.sleep(0.002)
        (barrier / "go").touch()
        outputs = []
        for child in children:
            stdout, stderr = child.communicate(timeout=60)
            self.assertEqual(child.returncode, 0, stderr)
            outputs.append(json.loads(stdout))
        return outputs

    def test_two_recover_processes_converge_on_same_retry_ready_state(self):
        self.retry_case()
        before = self.target.read_bytes()

        outputs = self.start_recover_children(2)

        self.assertEqual([item["state"] for item in outputs], [READY_FOR_EXECUTION] * 2)
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.ACTIVE)
        self.assertEqual(self.ops.get(TASK, OP).status, OperationStatus.STARTED)
        self.assertEqual(self.target.read_bytes(), before)

    def test_new_abort_between_retry_classification_and_step_blocks_old_retry(self):
        self.retry_case()
        barrier = self.root / "abort_race"
        barrier.mkdir()
        before = self.target.read_bytes()

        recover = subprocess.Popen(
            [
                sys.executable, "-B", "-c", PAUSED_RETRY_CHILD,
                str(self.storage), TASK, str(barrier),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 30
        while not (barrier / "retry_classified").exists():
            if time.monotonic() > deadline:
                recover.kill()
                self.fail("coordinator did not reach paused RETRY step")
            time.sleep(0.002)

        abort = subprocess.run(
            [
                sys.executable, "-B", "-c", ABORT_CHILD,
                str(self.storage), TASK, MICRO, OP,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(abort.returncode, 0, abort.stderr)
        abort_result = json.loads(abort.stdout)
        self.assertTrue(abort_result["accepted"])
        (barrier / "abort_done").touch()

        stdout, stderr = recover.communicate(timeout=60)
        self.assertEqual(recover.returncode, 0, stderr)
        outcome = json.loads(stdout)

        self.assertEqual(outcome["state"], FAIL_CLOSED)
        self.assertIn("no longer authoritative", outcome["reason"])
        self.assertEqual(self.tasks.open_microtask(TASK, MICRO).status, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT)
        self.assertEqual(self.target.read_bytes(), before)

        settled = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(settled["state"], MANUAL_DECISION_REQUIRED)
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ABORT")

    def test_recover_vs_new_operation_preserves_old_owner_and_denies_new_authority(self):
        self.prepare()
        self.tasks.set_microtask_status(
            TASK, MICRO, MicrotaskStatus.UNKNOWN_AFTER_DISCONNECT
        )
        self.begin_started(acquire_before_start=True)
        accepted = self.resolve("RETRY")
        self.assertTrue(accepted["accepted"])
        before = self.target.read_bytes()

        barrier = self.root / "new_operation_race"
        barrier.mkdir()
        recover = subprocess.Popen(
            [
                sys.executable, "-B", "-c", RECOVER_CHILD,
                str(self.storage), TASK, str(barrier), "recover",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        newcomer = subprocess.Popen(
            [
                sys.executable, "-B", "-c", NEW_OPERATION_CHILD,
                str(self.storage), TASK, MICRO, str(barrier),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 30
        while not (
            (barrier / "ready_recover").exists()
            and (barrier / "ready_new").exists()
        ):
            if time.monotonic() > deadline:
                recover.kill()
                newcomer.kill()
                self.fail("race processes did not reach barrier")
            time.sleep(0.002)
        (barrier / "go").touch()

        recover_out, recover_err = recover.communicate(timeout=60)
        new_out, new_err = newcomer.communicate(timeout=60)
        self.assertEqual(recover.returncode, 0, recover_err)
        self.assertEqual(newcomer.returncode, 0, new_err)
        recovered = json.loads(recover_out)
        new = json.loads(new_out)

        self.assertEqual(recovered["state"], READY_FOR_EXECUTION)
        self.assertEqual(new["acquire"], "CONFLICT")
        self.assertFalse(new["authorized"])
        self.assertEqual(self.target.read_bytes(), before)
        owner = TargetClaimService(self.storage).inspect(TASK, OP)
        self.assertTrue(owner["owned_by_operation"])

    def _foreign_claim_during_final_ready_proof(self, *, target, specs):
        if target == "extra.txt":
            self.extra.write_bytes(b"keep\n")
        self.retry_case(specs)
        first = RecoveryCoordinator(self.storage).recover(TASK)
        self.assertEqual(first["state"], READY_FOR_EXECUTION)

        foreign_op = "op_foreign_" + target.replace(".", "_")
        self.ops.begin(
            OTHER, "f1", "write", target,
            operation_id=foreign_op, payload=b"foreign\n",
            request_payload={"case": foreign_op},
        )

        barrier = self.root / ("foreign_ready_" + target.replace(".", "_"))
        barrier.mkdir()
        recover = subprocess.Popen(
            [
                sys.executable, "-B", "-c", PAUSED_READY_CHILD,
                str(self.storage), TASK, str(barrier),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 30
        while not (barrier / "proof_waiting").exists():
            if time.monotonic() > deadline:
                recover.kill()
                self.fail("recover child did not reach final READY proof")
            time.sleep(0.002)

        foreign = subprocess.run(
            [
                sys.executable, "-B", "-c", FOREIGN_CLAIM_CHILD,
                str(self.storage), OTHER, foreign_op,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(foreign.returncode, 0, foreign.stderr)
        claimed = json.loads(foreign.stdout)
        self.assertEqual(claimed["result"], "ACQUIRED")
        (barrier / "foreign_done").touch()

        stdout, stderr = recover.communicate(timeout=60)
        self.assertEqual(recover.returncode, 0, stderr)
        result = json.loads(stdout)
        self.assertEqual(result["state"], "RECOVERY_BLOCKED")
        self.assertIn("owned by another operation", result["reason"])

    def test_foreign_primary_claim_wins_before_final_retry_ready_proof(self):
        self._foreign_claim_during_final_ready_proof(
            target="target.txt",
            specs=(("target.txt", "edit"),),
        )

    def test_foreign_secondary_claim_wins_before_final_retry_ready_proof(self):
        self._foreign_claim_during_final_ready_proof(
            target="extra.txt",
            specs=(("target.txt", "edit"), ("extra.txt", "delete")),
        )

    def test_two_recover_processes_share_one_tracked_rollback(self):
        self.rollback_case()

        outputs = self.start_recover_children(2)

        self.assertEqual(
            [item["state"] for item in outputs],
            [MANUAL_DECISION_REQUIRED] * 2,
        )
        self.assertEqual(self.target.read_bytes(), BEFORE)
        self.assertEqual(self.extra.read_bytes(), b"keep\n")
        self.assertEqual(self.ops.get(TASK, OP).recovery_settlement["action"], "ROLLBACK")
        rollbacks = RecoveryCoordinator(self.storage).rollbacks.store.list(
            TASK, operation_id=OP
        )
        self.assertEqual(len(rollbacks), 1)


if __name__ == "__main__":
    unittest.main()
