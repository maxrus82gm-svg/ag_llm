import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import MicrotaskStatus
from web_alarm.operation_contract import fingerprint_v1
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.resolver_service import ResolverService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.target_claim_service import TargetClaimInputError, TargetClaimService
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
WINDOWS = os.name == "nt"
BEFORE = b"before\n"
AFTER = b"after\n"

ACQUIRE_AND_DIE = r"""
import os, sys
from web_alarm.target_claim_service import TargetClaimService
storage, task_id, operation_id = sys.argv[1:4]
outcome = TargetClaimService(storage).acquire(task_id, operation_id, operation_revision=1)
print(outcome["result"], outcome["claim"]["claim_id"], flush=True)
os._exit(0)  # no cleanup, no release: simulated process death
"""

INSPECT = r"""
import json, sys
from web_alarm.target_claim_service import TargetClaimService
storage = sys.argv[1]
service = TargetClaimService(storage)
print(json.dumps({op: service.inspect(task, op) for task, op in
                  (item.split("/") for item in sys.argv[2:])}))
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ClaimFixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        (self.project / "sub").mkdir(parents=True)
        for name in ("shared.txt", "other.txt", "side.txt", "sub/nested.txt"):
            (self.project / name).write_bytes(BEFORE)
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_claim")
        self.tasks = TaskStore(self.storage)
        for task in ("task_a", "task_b"):
            self.tasks.create_task("ws_claim", task, "RAW TASK", "Claims", task_id=task)
            self.tasks.create_microtask(task, "M1", "Claim step", microtask_id="m1")
            # Repair #3 (F-C): mutation authority needs an ACTIVE microtask
            self.tasks.set_microtask_status(task, "m1", MicrotaskStatus.ACTIVE)
        self.ops = OperationStore(self.storage)
        self.claims = TargetClaimService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def op(self, task, operation_id, target="shared.txt", status="INTENT", **overrides):
        values = dict(operation_id=operation_id, payload=AFTER, request_payload={"op": operation_id})
        values.update(overrides)
        self.ops.begin(task, "m1", "write", target, **values)
        for step in {"INTENT": [], "STARTED": ["STARTED"]}[status]:
            self.ops.transition(task, operation_id, step)

    def rev(self, task, operation_id):
        return self.ops.get(task, operation_id).revision

    def acquire(self, task, operation_id, revision=None):
        return self.claims.acquire(
            task, operation_id,
            operation_revision=revision if revision is not None else self.rev(task, operation_id),
            agent="claude-test",
        )

    def authorize(self, task, operation_id, revision=None):
        return self.claims.authorize(
            task, operation_id,
            operation_revision=revision if revision is not None else self.rev(task, operation_id),
        )

    def digest(self):
        return {
            str(p.relative_to(self.project)): sha256(p.read_bytes())
            for p in sorted(self.project.rglob("*")) if p.is_file()
        }

    def claim_files(self):
        directory = self.storage / "target_claims"
        return sorted(directory.glob("*.json")) if directory.is_dir() else []

    def events(self, task):
        return Counter(e.event_type for e in EventCheckpointStore(self.storage).read_events(task))

    def prepare(self, task="task_a", specs=(("shared.txt", "edit"),)):
        ManifestSnapshotStore(self.storage).prepare_microtask(task, "m1", list(specs))
        # the storage primitive leaves BACKUP_VERIFIED; authority needs ACTIVE (Repair #3)
        self.tasks.set_microtask_status(task, "m1", MicrotaskStatus.ACTIVE)

    def resolve(self, task, operation_id, action):
        decision = ReconciliationService(self.storage).reconcile(task, "m1", operation_id)["DECISION"]
        return ResolverService(self.storage).apply(
            task, "m1", operation_id, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.rev(task, operation_id),
        )


class ConflictGateTests(ClaimFixture):
    def test_basic_acquire_creates_one_persistent_owner(self):
        self.op("task_a", "op_a")
        digest = self.digest()

        outcome = self.acquire("task_a", "op_a")

        self.assertEqual(outcome["result"], "ACQUIRED")
        self.assertFalse(outcome["mutation_authority"])
        claim = outcome["claim"]
        self.assertEqual((claim["task_id"], claim["operation_id"], claim["status"]), ("task_a", "op_a", "ACTIVE"))
        self.assertEqual(claim["operation_revision"], 1)
        self.assertEqual(claim["cas_basis"], {"exists": True, "size": len(BEFORE), "sha256": sha256(BEFORE)})
        self.assertEqual(len(self.claim_files()), 1)
        self.assertNotIn("shared", self.claim_files()[0].name)  # hashed identity, never the raw path
        view = TargetClaimService(self.storage).inspect("task_a", "op_a")
        self.assertTrue(view["owned_by_operation"])
        self.assertEqual(view["cas_preview"]["result"], "AUTHORIZED")
        self.assertEqual(self.digest(), digest)

    def test_replay_returns_same_claim_without_duplicate_effect(self):
        self.op("task_a", "op_a")
        first = self.acquire("task_a", "op_a")
        second = self.acquire("task_a", "op_a")

        self.assertEqual(second["result"], "REPLAYED")
        self.assertEqual(second["claim"], first["claim"])
        data = json.loads(self.claim_files()[0].read_text(encoding="utf-8"))
        self.assertEqual((data["next_generation"], data["history"]), (2, []))
        self.assertEqual(self.events("task_a")["TARGET_CLAIM_ACQUIRED"], 1)

    def test_same_task_and_cross_task_operations_conflict(self):
        self.op("task_a", "op_a")
        self.op("task_a", "op_a2")
        self.op("task_b", "op_b")
        owner = self.acquire("task_a", "op_a")["claim"]

        for task, operation_id in (("task_a", "op_a2"), ("task_b", "op_b")):
            with self.subTest(operation=operation_id):
                outcome = self.acquire(task, operation_id)
                self.assertEqual((outcome["result"], outcome["result_code"]), ("CONFLICT", "TARGET_OWNED"))
                self.assertEqual(outcome["blocking_owner"]["claim_id"], owner["claim_id"])
                self.assertEqual(outcome["blocking_owner"]["operation_id"], "op_a")
                self.assertIsNone(outcome["claim"])
                view = self.claims.inspect(task, operation_id)
                self.assertFalse(view["owned_by_operation"])
                self.assertEqual(view["blocking_owner"]["operation_id"], "op_a")
                self.assertEqual(view["cas_preview"]["result_code"], "NOT_OWNER")
        self.assertEqual(self.events("task_b")["TARGET_CLAIM_CONFLICT"], 1)

    def test_different_targets_do_not_conflict(self):
        self.op("task_a", "op_a")
        self.op("task_b", "op_other", target="other.txt")
        self.acquire("task_a", "op_a")

        outcome = self.acquire("task_b", "op_other")

        self.assertEqual(outcome["result"], "ACQUIRED")
        self.assertEqual(len(self.claim_files()), 2)

    def test_equivalent_spellings_share_one_conflict_identity(self):
        self.op("task_a", "op_a", target="sub/nested.txt")
        self.acquire("task_a", "op_a")
        spellings = ["./sub/nested.txt", "sub\\nested.txt", str(self.project / "sub" / "nested.txt")]
        if WINDOWS:
            spellings.append("SUB/NESTED.TXT")
            import _winapi
            _winapi.CreateJunction(str(self.project / "sub"), str(self.project / "alias"))
            spellings.append("alias/nested.txt")
        for index, spelling in enumerate(spellings):
            with self.subTest(spelling=spelling):
                self.op("task_b", f"op_b{index}", target=spelling)
                self.assertEqual(self.acquire("task_b", f"op_b{index}")["result"], "CONFLICT")

        # a second, nested workspace names the same physical file differently
        WorkspaceRegistry(self.storage).register("Nested", self.project / "sub", workspace_id="ws_nested")
        self.tasks.create_task("ws_nested", "nested", "RAW TASK", "Claims", task_id="task_n")
        self.tasks.create_microtask("task_n", "M1", "Claim step", microtask_id="m1")
        self.op("task_n", "op_n", target="nested.txt")
        self.assertEqual(self.ops.get("task_n", "op_n").contract["target_key"], "nested.txt")
        outcome = self.acquire("task_n", "op_n")
        self.assertEqual(outcome["result"], "CONFLICT")
        self.assertEqual(outcome["blocking_owner"]["operation_id"], "op_a")
        self.assertEqual(len(self.claim_files()), 1)


class MutationBoundaryCasTests(ClaimFixture):
    def test_authorization_is_cas_checked_persisted_and_replay_safe(self):
        self.op("task_a", "op_a")
        self.acquire("task_a", "op_a")
        digest = self.digest()

        first = self.authorize("task_a", "op_a")
        second = self.authorize("task_a", "op_a")

        self.assertEqual((first["result"], first["result_code"]), ("AUTHORIZED", "CAS_BASIS_HOLDS"))
        self.assertTrue(first["authorized"])
        self.assertFalse(first["mutation_authority"])  # authority never leaves the boundary
        self.assertEqual(second["authorization"], first["authorization"])
        claim = self.claims.inspect("task_a", "op_a")["active_claim"]
        self.assertEqual(len(claim["authorizations"]), 1)
        self.assertEqual(self.digest(), digest)

    def test_stale_operation_revision_gets_no_authority(self):
        self.op("task_a", "op_a")
        self.acquire("task_a", "op_a", revision=1)
        self.ops.transition("task_a", "op_a", "STARTED")  # revision 2

        old = self.authorize("task_a", "op_a", revision=1)
        new = self.authorize("task_a", "op_a", revision=2)
        stale_acquire = self.claims.acquire("task_a", "op_a", operation_revision=1)

        self.assertEqual((old["result"], old["result_code"]), ("DENIED", "OPERATION_REVISION_CHANGED"))
        self.assertEqual((new["result"], new["result_code"]), ("DENIED", "CLAIM_BASIS_STALE"))
        self.assertEqual(stale_acquire["result"], "REPLAYED")  # known claim, still no authority
        self.op("task_b", "op_b")
        with self.assertRaises(TargetClaimInputError):
            self.claims.acquire("task_b", "op_b", operation_revision=0)
        self.assertEqual(
            self.claims.acquire("task_b", "op_b", operation_revision=7)["result_code"],
            "OPERATION_REVISION_CHANGED",
        )

    def test_physical_drift_after_acquire_fails_closed_without_overwrite(self):
        self.op("task_a", "op_a")
        self.acquire("task_a", "op_a")
        (self.project / "shared.txt").write_bytes(b"external writer\n")

        outcome = self.authorize("task_a", "op_a")

        self.assertEqual((outcome["result"], outcome["result_code"]), ("DENIED", "STATE_DRIFT"))
        self.assertEqual(outcome["authorization"]["observed"]["sha256"], sha256(b"external writer\n"))
        self.assertEqual((self.project / "shared.txt").read_bytes(), b"external writer\n")
        self.op("task_b", "op_b", target="other.txt")
        (self.project / "other.txt").write_bytes(b"changed before acquire\n")
        self.assertEqual(self.acquire("task_b", "op_b")["result_code"], "STATE_DRIFT")

    def test_executor_flow_boundary_then_lifecycle_then_release(self):
        """Simulates the future WA4-E order; the write is the test's, not RC-3's."""
        self.op("task_a", "op_a")
        self.acquire("task_a", "op_a")
        with self.claims.mutation_boundary("task_a", "op_a", operation_revision=1) as boundary:
            self.assertTrue(boundary["mutation_authority"])
            (self.project / "shared.txt").write_bytes(AFTER)  # stand-in executor write
        self.ops.transition("task_a", "op_a", "STARTED")
        released_early = self.claims.release("task_a", "op_a")
        self.ops.transition("task_a", "op_a", "DONE")
        released = self.claims.release("task_a", "op_a", reason="executor finished")

        self.assertEqual((released_early["result"], released_early["result_code"]),
                         ("REJECTED", "RELEASE_REQUIRES_RECOVERY_OUTCOME"))
        self.assertEqual(released["result"], "RELEASED")
        self.assertEqual(released["claim"]["end_reason"], "executor finished")


class ReleaseTests(ClaimFixture):
    def test_wrong_owner_cannot_release_and_release_replay_is_idempotent(self):
        self.op("task_a", "op_a")
        self.op("task_b", "op_b")
        claim = self.acquire("task_a", "op_a")["claim"]

        foreign = self.claims.release("task_b", "op_b", claim_id=claim["claim_id"])
        self.assertEqual((foreign["result"], foreign["result_code"]), ("REJECTED", "NOT_OWNER"))
        self.assertTrue(self.claims.inspect("task_a", "op_a")["owned_by_operation"])

        first = self.claims.release("task_a", "op_a")
        second = self.claims.release("task_a", "op_a")
        self.assertEqual(first["result"], "RELEASED")
        self.assertEqual((second["result"], second["result_code"]), ("REPLAYED", "ALREADY_RELEASED"))
        self.assertEqual(second["claim"], first["claim"])
        self.assertEqual(self.events("task_a")["TARGET_CLAIM_RELEASED"], 1)

    def test_after_release_other_operation_acquires_only_on_fresh_basis(self):
        self.op("task_a", "op_a")
        self.op("task_b", "op_b")
        self.op("task_b", "op_c")
        self.acquire("task_a", "op_a")
        self.claims.release("task_a", "op_a")

        late_duplicate = self.acquire("task_a", "op_a")
        taken = self.acquire("task_b", "op_b")
        self.assertEqual((late_duplicate["result"], late_duplicate["result_code"]),
                         ("REPLAYED", "SAME_BASIS_ALREADY_RELEASED"))
        self.assertEqual((taken["result"], taken["claim"]["generation"]), ("ACQUIRED", 2))

        self.claims.release("task_b", "op_b")
        (self.project / "shared.txt").write_bytes(b"moved on\n")
        self.assertEqual(self.acquire("task_b", "op_c")["result_code"], "STATE_DRIFT")

    def test_claim_survives_process_death_and_restart(self):
        self.op("task_a", "op_a")
        self.op("task_b", "op_b")
        died = subprocess.run(
            [sys.executable, "-B", "-c", ACQUIRE_AND_DIE, str(self.storage), "task_a", "op_a"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        )
        result, claim_id = died.stdout.split()
        self.assertEqual(result, "ACQUIRED")

        fresh = subprocess.run(
            [sys.executable, "-B", "-c", INSPECT, str(self.storage), "task_a/op_a", "task_b/op_b"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        )
        views = json.loads(fresh.stdout)
        self.assertTrue(views["op_a"]["owned_by_operation"])
        self.assertEqual(views["op_a"]["active_claim"]["claim_id"], claim_id)
        self.assertEqual(views["op_a"]["active_claim"]["operation_revision"], 1)
        self.assertEqual(views["op_a"]["cas_preview"]["result"], "AUTHORIZED")
        self.assertEqual(views["op_b"]["blocking_owner"]["claim_id"], claim_id)
        self.assertEqual(self.acquire("task_b", "op_b")["result"], "CONFLICT")


class ContractAndResolverGateTests(ClaimFixture):
    def test_legacy_contract_cannot_acquire_or_authorize(self):
        record = {
            "operation_id": "op_legacy", "task_id": "task_a", "microtask_id": "m1",
            "action": "write", "target": "shared.txt", "status": "INTENT",
            "request_fingerprint": fingerprint_v1(
                task_id="task_a", microtask_id="m1", action="write", target="shared.txt",
                expected_precondition_sha256=None, request_payload=None),
            "expected_precondition_sha256": None, "result_summary": None, "schema_version": 1,
            "created_at": "2026-10-02T19:00:00+00:00", "updated_at": "2026-10-02T19:00:00+00:00",
        }
        path = self.storage / "tasks" / "active" / "task_a" / "operations" / "op_legacy.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        raw = path.read_bytes()

        acquired = self.claims.acquire("task_a", "op_legacy", operation_revision=None)
        authorized = self.claims.authorize("task_a", "op_legacy", operation_revision=None)

        self.assertEqual((acquired["result"], acquired["result_code"]), ("REJECTED", "LEGACY_CONTRACT"))
        self.assertEqual((authorized["result"], authorized["result_code"]), ("DENIED", "LEGACY_CONTRACT"))
        self.assertEqual(self.claim_files(), [])
        self.assertEqual(path.read_bytes(), raw)

    def test_incomplete_or_corrupt_payload_contract_cannot_acquire(self):
        self.op("task_a", "op_old", payload=None)  # old-style v2: no payload / post
        self.op("task_b", "op_blob")
        next((self.storage / "tasks" / "active" / "task_b" / "payloads").glob("*.bin")).write_bytes(b"x")

        incomplete = self.acquire("task_a", "op_old")
        corrupt = self.acquire("task_b", "op_blob")

        self.assertEqual((incomplete["result"], incomplete["result_code"]), ("REJECTED", "CONTRACT_INSUFFICIENT"))
        self.assertEqual(corrupt["result_code"], "PAYLOAD_INTEGRITY_FAILURE")
        self.assertEqual(self.claim_files(), [])

    def test_resolver_state_never_grants_false_authority(self):
        (self.project / "side.txt").write_bytes(BEFORE)
        self.prepare(specs=(("shared.txt", "edit"), ("side.txt", "delete")))
        self.op("task_a", "op_a", status="STARTED")

        no_resolution = self.acquire("task_a", "op_a")
        self.assertEqual(no_resolution["result_code"], "RECOVERY_RESOLUTION_REQUIRED")
        rejected = self.resolve("task_a", "op_a", "ADOPT")  # wrong action -> REJECTED record
        self.assertFalse(rejected["accepted"])
        self.assertEqual(self.acquire("task_a", "op_a")["result_code"], "RECOVERY_RESOLUTION_REQUIRED")

        self.assertTrue(self.resolve("task_a", "op_a", "RETRY")["accepted"])
        rearm_only = self.authorize("task_a", "op_a")
        self.assertEqual(rearm_only["result_code"], "NO_ACTIVE_CLAIM")  # re-arm is not authority
        claimed = self.acquire("task_a", "op_a")
        self.assertEqual(claimed["result"], "ACQUIRED")
        self.assertEqual(self.authorize("task_a", "op_a")["result"], "AUTHORIZED")

        (self.project / "side.txt").write_bytes(b"other evidence changed\n")  # RETRY now stale
        stale = self.authorize("task_a", "op_a")
        self.assertEqual((stale["result"], stale["result_code"]), ("DENIED", "RECOVERY_RESOLUTION_REQUIRED"))
        self.assertEqual(
            self.claims.release("task_a", "op_a")["result_code"], "RELEASE_REQUIRES_RECOVERY_OUTCOME"
        )

        self.assertTrue(self.resolve("task_a", "op_a", "ABORT")["accepted"])
        aborted = self.authorize("task_a", "op_a")
        self.assertEqual(aborted["result_code"], "RECOVERY_ABORTED")
        self.assertEqual(self.claims.release("task_a", "op_a")["result"], "RELEASED")
        (self.project / "side.txt").write_bytes(BEFORE)
        again = self.acquire("task_a", "op_a")  # same basis: the known released claim, no new one
        self.assertEqual((again["result"], again["claim"]["status"]), ("REPLAYED", "RELEASED"))
        view = self.claims.inspect("task_a", "op_a")
        self.assertIsNone(view["active_claim"])
        self.assertEqual(view["cas_preview"]["result"], "DENIED")
        self.assertEqual((self.project / "shared.txt").read_bytes(), BEFORE)

    def test_aborted_operation_cannot_take_a_free_target(self):
        self.prepare()
        self.op("task_a", "op_a", status="STARTED")
        self.assertTrue(self.resolve("task_a", "op_a", "ABORT")["accepted"])

        outcome = self.acquire("task_a", "op_a")

        self.assertEqual((outcome["result"], outcome["result_code"]), ("REJECTED", "RECOVERY_ABORTED"))
        self.assertEqual(self.claim_files(), [])

    def test_rollback_request_is_not_mutation_authority(self):
        (self.project / "side.txt").write_bytes(BEFORE)
        self.prepare(specs=(("shared.txt", "edit"), ("side.txt", "delete")))
        self.op("task_a", "op_a", status="STARTED")
        (self.project / "shared.txt").write_bytes(AFTER)
        self.assertTrue(self.resolve("task_a", "op_a", "ROLLBACK")["accepted"])

        outcome = self.acquire("task_a", "op_a")

        self.assertEqual(outcome["result_code"], "RECOVERY_RESOLUTION_REQUIRED")
        self.assertIn("ROLLBACK", outcome["reason"])


class ClaimServerTests(ClaimFixture):
    def test_server_claim_endpoints(self):
        self.op("task_a", "op_a")
        self.op("task_b", "op_b")
        api = WebAlarmApi(self.storage)
        base_a, base_b = "/tasks/task_a/operations/op_a/claim", "/tasks/task_b/operations/op_b/claim"

        status, acquired = api.dispatch("POST", base_a, {"operation_revision": 1, "agent": "chatgpt"})
        self.assertEqual((status, acquired["result"]), (201, "ACQUIRED"))
        status, replay = api.dispatch("POST", base_a, {"operation_revision": 1})
        self.assertEqual((status, replay["result"]), (200, "REPLAYED"))
        with self.assertRaises(ApiError) as conflict:
            api.dispatch("POST", base_b, {"operation_revision": 1})
        self.assertEqual((conflict.exception.status, conflict.exception.code), (409, "claim_conflict"))
        self.assertEqual(conflict.exception.details["blocking_owner"]["operation_id"], "op_a")
        status, view = api.dispatch("GET", base_a)
        self.assertTrue(view["owned_by_operation"])
        status, authorized = api.dispatch("POST", base_a + "/authorize", {"operation_revision": 1})
        self.assertEqual((status, authorized["result"]), (200, "AUTHORIZED"))
        with self.assertRaises(ApiError) as denied:
            api.dispatch("POST", base_b + "/authorize", {"operation_revision": 1})
        self.assertEqual(denied.exception.code, "claim_denied")
        with self.assertRaises(ApiError) as foreign:
            api.dispatch("POST", base_b + "/release", {})
        self.assertEqual(foreign.exception.code, "claim_rejected")
        status, released = api.dispatch("POST", base_a + "/release", {"reason": "done"})
        self.assertEqual((status, released["result"]), (200, "RELEASED"))
        with self.assertRaises(ApiError) as bad:
            api.dispatch("POST", base_a, {"operation_revision": "1"})
        self.assertEqual(bad.exception.status, 400)
        with self.assertRaises(ApiError) as unknown:
            api.dispatch("POST", base_a + "/steal", {})
        self.assertEqual(unknown.exception.status, 404)
        status, info = api.dispatch("GET", "/status")
        self.assertIn("target_claims", info["capabilities"])
        self.assertEqual((self.project / "shared.txt").read_bytes(), BEFORE)


if __name__ == "__main__":
    unittest.main()
