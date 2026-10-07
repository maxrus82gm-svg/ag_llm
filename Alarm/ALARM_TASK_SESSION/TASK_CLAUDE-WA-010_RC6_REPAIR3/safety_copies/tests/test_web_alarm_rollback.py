import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import web_alarm.rollback_service as rs
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_report_service import RecoveryReportClaimError, RecoveryReportService
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackError, RollbackService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.target_claim_service import TargetClaimError, TargetClaimService
from web_alarm.target_claim_store import physical_target_key
from web_alarm.target_identity import canonical_target
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_rb"
BEFORE, AFTER, KEEP, GONE, NEW = b"before\n", b"after-content-long\n", b"keep\n", b"gone\n", b"new file\n"

APPLY_WITH_CRASH = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id, mode = sys.argv[1:5]
real = rs._write_restored_bytes
calls = []
def crash(path, data):
    calls.append(1)
    if mode == "second_before_write" and len(calls) == 1:
        return real(path, data)
    if mode == "after_write":
        real(path, data)
    os._exit(17)
rs._write_restored_bytes = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""

PREPARE_WITH_CRASH = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, microtask_id, operation_id, resolution_id = sys.argv[1:6]
real = rs.RollbackService._preserve
calls = []
def crash(self, *args):
    calls.append(1)
    if len(calls) == 2:
        os._exit(19)
    return real(self, *args)
rs.RollbackService._preserve = crash
rs.RollbackService(storage).prepare(task_id, microtask_id, operation_id, resolution_id)
"""

RELEASE_WITH_CRASH = r"""
import os, sys
import web_alarm.rollback_service as rs
storage, task_id, rollback_id = sys.argv[1:4]
def crash(self, *args, **kwargs):
    os._exit(23)
rs.RollbackService._release_claims = crash
rs.RollbackService(storage).apply(task_id, rollback_id)
"""

FRESH_VIEW = r"""
import json, sys
from web_alarm.recovery_report_service import RecoveryReportService
from web_alarm.rollback_service import RollbackService
storage, task_id, rollback_id, operation_id = sys.argv[1:5]
record = RollbackService(storage).inspect(task_id, rollback_id)
report = RecoveryReportService(storage).create_report(
    task_id=task_id, microtask_id=record["microtask_id"], operation_id=operation_id,
    incident_id="fresh_" + rollback_id + "_" + record["status"],
)
print(json.dumps({"record": record, "report": {
    "actually_rolled_back": report.actually_rolled_back,
    "rollback_receipts": report.rollback_receipts,
    "next_safe_action": report.next_safe_action,
    "evidence_identity": report.evidence_identity,
}}))
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state(data: bytes | None) -> dict:
    if data is None:
        return {"exists": False, "size": None, "sha256": None}
    return {"exists": True, "size": len(data), "sha256": sha256(data)}


class RollbackFixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_rb")
        self.tasks = TaskStore(self.storage)
        for task in (TASK, "task_b"):
            self.tasks.create_task("ws_rb", task, "RAW TASK", "Rollback", task_id=task)
            self.tasks.create_microtask(task, "M1", "Step", microtask_id="m1")
        self.ops = OperationStore(self.storage)
        self.rollbacks = RollbackService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def path(self, name):
        return self.project / name

    def write(self, name, data):
        self.path(name).write_bytes(data)

    def digest(self):
        return {str(p.relative_to(self.project)): sha256(p.read_bytes())
                for p in sorted(self.project.rglob("*")) if p.is_file()}

    def resolve(self, action, operation_id="op_1", task=TASK):
        decision = ReconciliationService(self.storage).reconcile(task, "m1", operation_id)["DECISION"]
        return ResolverService(self.storage).apply(
            task, "m1", operation_id, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(task, operation_id).revision,
        )

    def scenario(self, kind="write", keep="keep.txt"):
        """Accepted fresh ROLLBACK for op_1; returns the resolution id."""
        self.write(keep, KEEP)
        if kind == "write":
            self.write("target.txt", BEFORE)
            specs = [("target.txt", "edit"), (keep, "delete")]
        elif kind == "two":
            self.write("target.txt", BEFORE)
            self.write("gone.txt", GONE)
            specs = [("target.txt", "edit"), ("gone.txt", "delete"), (keep, "delete")]
        else:
            specs = [("new.txt", "create"), (keep, "delete")]
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, "m1", specs)
        if kind == "new":
            self.ops.begin(TASK, "m1", "create_file", "new.txt", operation_id="op_1", payload=NEW)
        else:
            self.ops.begin(TASK, "m1", "write", "target.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "STARTED")
        if kind == "new":
            self.write("new.txt", NEW)
        else:
            self.write("target.txt", AFTER)
        if kind == "two":
            self.path("gone.txt").unlink()
        outcome = self.resolve("ROLLBACK")
        self.assertTrue(outcome["accepted"], outcome["resolution"].result_reason)
        return outcome["resolution"].resolution_id

    def prepare(self, resolution_id, service=None):
        return (service or self.rollbacks).prepare(TASK, "m1", "op_1", resolution_id, agent="claude-test")

    def fresh(self, script, *args):
        completed = subprocess.run([sys.executable, "-B", "-c", script, str(self.storage), *args],
                                   cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        return completed

    def target(self, record, source_path):
        return next(t for t in record["targets"] if t["source_path"] == source_path)


class RollbackAuthorityTests(RollbackFixture):
    def test_accepted_fresh_rollback_creates_persistent_preserved_session(self):
        resolution_id = self.scenario()
        digest = self.digest()

        outcome = self.prepare(resolution_id)
        record = outcome["rollback"]

        self.assertEqual((outcome["result"], record["status"]), ("PRESERVED", "PRESERVED"))
        self.assertEqual(record["resolution_id"], resolution_id)
        self.assertEqual(record["basis"]["operation_revision"], 2)
        self.assertEqual({t["source_path"]: t["planned_action"] for t in record["targets"]},
                         {"target.txt": "WRITE_RESTORE", "keep.txt": "NOOP"})
        self.assertEqual([t["target_hash"] for t in record["targets"]],
                         sorted(t["target_hash"] for t in record["targets"]))
        self.assertEqual(self.digest(), digest)
        replay = self.prepare(resolution_id)
        self.assertEqual((replay["result"], replay["rollback"]), ("REPLAYED", record))

    def test_missing_wrong_stale_rejected_or_aborted_resolution_never_restores(self):
        resolution_id = self.scenario()
        digest = self.digest()

        self.assertEqual(self.prepare("res_missing")["result_code"], "NO_ROLLBACK_RESOLUTION")
        rejected = self.resolve("RETRY")  # wrong action under a ROLLBACK decision -> REJECTED record
        self.assertFalse(rejected["accepted"])
        self.assertEqual(self.prepare(rejected["resolution"].resolution_id)["result_code"], "NOT_A_ROLLBACK")
        self.write("keep.txt", b"keep changed\n")  # evidence moves on: the ROLLBACK goes stale
        self.assertEqual(self.prepare(resolution_id)["result_code"], "STALE_RESOLUTION")
        self.write("keep.txt", KEEP)
        self.assertTrue(self.resolve("ABORT")["accepted"])
        self.assertEqual(self.prepare(resolution_id)["result_code"], "RECOVERY_ABORTED")

        self.assertEqual(self.digest(), digest)
        self.assertFalse((self.storage / "tasks" / "active" / TASK / "rollbacks").exists())

    def test_abort_after_prepare_blocks_destructive_phase(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.assertTrue(self.resolve("ABORT")["accepted"])
        digest = self.digest()

        outcome = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual((outcome["result"], outcome["result_code"]), ("BLOCKED", "RECOVERY_ABORTED"))
        self.assertEqual(self.digest(), digest)

    def test_restore_point_integrity_failure_never_restores_and_is_side_effect_free(self):
        resolution_id = self.scenario()
        restore = self.storage / "tasks" / "active" / TASK / "microtasks" / "m1" / "restore_point"
        manifest_bytes = (restore / "manifest.json").read_bytes()
        snapshot = next(restore.glob("snapshots/*.bin"))
        original = snapshot.read_bytes()
        digest = self.digest()

        snapshot.write_bytes(b"corrupt")  # before prepare
        early = self.prepare(resolution_id)
        snapshot.write_bytes(original)
        record = self.prepare(resolution_id)["rollback"]
        snapshot.write_bytes(b"corrupt")  # after prepare, before the destructive phase
        late = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual((early["result"], early["result_code"]), ("REJECTED", "RESTORE_POINT_INVALID"))
        self.assertEqual((late["result"], late["result_code"]), ("BLOCKED", "RESTORE_POINT_INVALID"))
        self.assertEqual(self.digest(), digest)
        self.assertEqual((restore / "manifest.json").read_bytes(), manifest_bytes)  # side-effect free


class PreservationTests(RollbackFixture):
    def test_existing_bytes_and_absence_are_preserved_and_verified_before_restore(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]

        target = self.target(record, "target.txt")
        gone = self.target(record, "gone.txt")
        self.assertEqual({k: target["preserved"][k] for k in ("exists", "size", "sha256")}, state(AFTER))
        blob = self.storage / "tasks" / "active" / TASK / "rollback_preserved" / f"{sha256(AFTER)}.bin"
        self.assertEqual(blob.read_bytes(), AFTER)
        self.assertEqual(target["preserved"]["blob"]["store"], "rollback_preserved")
        self.assertEqual({k: gone["preserved"][k] for k in ("exists", "size", "sha256")}, state(None))
        self.assertIsNone(gone["preserved"]["blob"])
        self.assertEqual(gone["planned_action"], "WRITE_RESTORE")
        self.assertTrue(any(e["event_type"] == "ROLLBACK_PRESERVED" for e in self._events()))

    def _events(self):
        lines = (self.storage / "tasks" / "active" / TASK / "events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(AFTER.decode().strip(), lines)  # never content, only metadata
        return [json.loads(line) for line in lines.splitlines()]

    def test_preservation_failure_of_one_target_blocks_every_target(self):
        resolution_id = self.scenario()
        digest = self.digest()
        small = RollbackService(self.storage, max_preserved_bytes=len(KEEP))

        outcome = self.prepare(resolution_id, small)

        self.assertEqual((outcome["result"], outcome["result_code"]), ("PRESERVATION_FAILED", "PRESERVATION_SCOPE"))
        replay = small.apply(TASK, outcome["rollback"]["rollback_id"])
        self.assertEqual((replay["result"], replay["rollback"]["status"]), ("REPLAYED", "PRESERVATION_FAILED"))
        self.assertEqual(self.digest(), digest)

    def test_crash_during_preservation_resumes_without_any_mutation(self):
        resolution_id = self.scenario()
        digest = self.digest()
        crashed = self.fresh(PREPARE_WITH_CRASH, TASK, "m1", "op_1", resolution_id)
        self.assertEqual(crashed.returncode, 19)

        rollback_id = rs.rollback_identity(TASK, resolution_id)
        self.assertEqual(self.rollbacks.inspect(TASK, rollback_id)["status"], "PREPARED")
        resumed = self.prepare(resolution_id)
        self.assertEqual(resumed["result"], "PRESERVED")
        self.assertEqual(self.digest(), digest)


class RestoreTests(RollbackFixture):
    def run_rollback(self, kind="write", service=None):
        resolution_id = self.scenario(kind)
        record = self.prepare(resolution_id)["rollback"]
        writes = []
        real = rs._write_restored_bytes

        def spy(path, data):
            writes.append(Path(path).name)
            real(path, data)

        with mock.patch.object(rs, "_write_restored_bytes", spy):
            outcome = (service or self.rollbacks).apply(TASK, record["rollback_id"])
        return outcome, writes

    def test_existing_target_restored_exactly_and_pre_state_target_is_noop(self):
        outcome, writes = self.run_rollback()
        record = outcome["rollback"]

        self.assertEqual((outcome["result"], record["status"]), ("VERIFIED", "VERIFIED"))
        self.assertEqual(self.path("target.txt").read_bytes(), BEFORE)
        self.assertEqual(writes, ["target.txt"])  # keep.txt never rewritten
        target, keep = self.target(record, "target.txt"), self.target(record, "keep.txt")
        self.assertEqual(target["receipt"]["action"], "WRITE_RESTORE")
        self.assertEqual(target["receipt"]["observed_post"], state(BEFORE))
        self.assertEqual(target["receipt"]["preserved"], state(AFTER))
        self.assertTrue(target["receipt"]["matches_expected_restore"])
        self.assertEqual((keep["status"], keep["receipt"]["action"]), ("NOOP", "NOOP"))
        self.assertEqual(record["result"]["overall"], "SUCCESS")
        self.assertTrue(record["claims_released"])
        self.assertIsNone(TargetClaimService(self.storage).inspect(TASK, "op_1")["active_claim"])
        self.assertEqual(self.ops.get(TASK, "op_1").status.value, "STARTED")  # no lifecycle change

    def test_created_file_is_deleted_and_absence_verified(self):
        outcome, writes = self.run_rollback("new")
        target = self.target(outcome["rollback"], "new.txt")

        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertFalse(self.path("new.txt").exists())
        self.assertEqual((target["receipt"]["action"], target["receipt"]["observed_post"]),
                         ("DELETE_CREATED", state(None)))
        self.assertEqual(writes, [])

    def test_two_targets_restored_including_recreated_file(self):
        outcome, writes = self.run_rollback("two")

        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertEqual(self.path("gone.txt").read_bytes(), GONE)
        self.assertEqual(self.path("target.txt").read_bytes(), BEFORE)
        self.assertEqual(sorted(writes), ["gone.txt", "target.txt"])

    def test_replay_of_completed_rollback_has_no_second_side_effect(self):
        outcome, _ = self.run_rollback()
        record = outcome["rollback"]
        mtime = self.path("target.txt").stat().st_mtime_ns
        writes = []
        with mock.patch.object(rs, "_write_restored_bytes", lambda p, d: writes.append(p)):
            replay = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual((replay["result"], replay["rollback"]), ("REPLAYED", record))
        self.assertEqual((writes, self.path("target.txt").stat().st_mtime_ns), ([], mtime))

    def test_drift_after_preservation_is_never_overwritten(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.write("target.txt", b"someone else\n")

        blocked = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual((blocked["result"], blocked["result_code"]), ("BLOCKED", "STATE_DRIFT"))
        self.assertEqual(self.path("target.txt").read_bytes(), b"someone else\n")
        self.assertEqual(blocked["rollback"]["status"], "PRESERVED")

    def test_drift_at_the_destructive_boundary_stops_as_partial(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        order = [t["source_path"] for t in record["targets"] if t["planned_action"] == "WRITE_RESTORE"]
        real = rs._write_restored_bytes

        def write_then_drift(path, data):
            real(path, data)
            self.write(order[1], b"external drift\n")  # second target changes after authorization

        with mock.patch.object(rs, "_write_restored_bytes", write_then_drift):
            outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        record = outcome["rollback"]

        self.assertEqual((outcome["result"], record["status"]), ("PARTIAL", "PARTIAL"))
        first, second = self.target(record, order[0]), self.target(record, order[1])
        self.assertEqual(first["status"], "RESTORED")
        self.assertEqual((second["status"], second["failure"]["code"]), ("DRIFTED", "STATE_DRIFT"))
        self.assertEqual(self.path(order[1]).read_bytes(), b"external drift\n")
        self.assertEqual(record["result"]["overall"], "PARTIAL")
        self.assertFalse(record["claims_released"])
        replay = self.rollbacks.apply(TASK, record["rollback_id"])
        self.assertEqual(replay["result"], "REPLAYED")
        report = RecoveryReportService(self.storage).create_report(
            task_id=TASK, microtask_id="m1", operation_id="op_1", incident_id="partial")
        self.assertEqual(report.actually_rolled_back, [order[0]])
        self.assertEqual(report.rollback_receipts[0]["overall"], "PARTIAL")
        self.assertIn(order[1], report.rollback_receipts[0]["unresolved"])
        self.assertIn("PARTIAL", report.next_safe_action)


class OwnershipTests(RollbackFixture):
    def foreign_claim(self, target, action="write", payload=b"other\n"):
        self.ops.begin("task_b", "m1", action, target, operation_id="op_b", payload=payload)
        outcome = TargetClaimService(self.storage).acquire("task_b", "op_b", operation_revision=1)
        self.assertEqual(outcome["result"], "ACQUIRED")
        return outcome["claim"]

    def test_same_target_normal_owner_blocks_rollback(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        claim = self.foreign_claim("target.txt")
        digest = self.digest()

        blocked = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual((blocked["result"], blocked["result_code"]), ("BLOCKED", "TARGET_CONFLICT"))
        self.assertEqual(blocked["rollback"]["last_attempt"]["blocking_owners"][0]["claim_id"], claim["claim_id"])
        self.assertEqual(self.digest(), digest)

    def test_conflict_on_one_target_blocks_the_whole_destructive_phase(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        self.foreign_claim("gone.txt", action="create_file")
        digest = self.digest()

        blocked = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual(blocked["result_code"], "TARGET_CONFLICT")
        self.assertEqual(self.digest(), digest)
        view = TargetClaimService(self.storage).inspect(TASK, "op_1")
        self.assertIsNone(view["active_claim"])  # no partial reservation left on target.txt

    def test_rollback_ownership_is_per_target_and_visible_to_rc3(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        order = [t["source_path"] for t in record["targets"] if t["planned_action"] == "WRITE_RESTORE"]
        real = rs._write_restored_bytes

        def write_then_drift(path, data):
            real(path, data)
            self.write(order[1], b"external drift\n")

        with mock.patch.object(rs, "_write_restored_bytes", write_then_drift):
            self.rollbacks.apply(TASK, record["rollback_id"])  # PARTIAL: claims stay held
        self.write("other.txt", b"independent\n")
        claims = TargetClaimService(self.storage)
        self.ops.begin("task_b", "m1", "write", "other.txt", operation_id="op_free", payload=b"x\n")
        self.ops.begin("task_b", "m1", "write", order[0], operation_id="op_held", payload=b"x\n")

        free = claims.acquire("task_b", "op_free", operation_revision=1)
        held = claims.acquire("task_b", "op_held", operation_revision=1)

        self.assertEqual(free["result"], "ACQUIRED")
        self.assertEqual((held["result"], held["blocking_owner"]["owner"]["kind"]), ("CONFLICT", "ROLLBACK"))
        closed = self.rollbacks.close(TASK, record["rollback_id"], reason="reviewed")
        self.assertEqual((closed["result"], closed["rollback"]["claims_released"]), ("CLOSED", True))
        self.assertEqual(claims.acquire("task_b", "op_held", operation_revision=1)["result"], "ACQUIRED")

    def test_source_operation_claim_is_taken_over_not_bypassed(self):
        self.write("keep.txt", KEEP)
        self.write("target.txt", BEFORE)
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, "m1", [("target.txt", "edit"), ("keep.txt", "delete")])
        self.ops.begin(TASK, "m1", "write", "target.txt", operation_id="op_1", payload=AFTER)
        claims = TargetClaimService(self.storage)
        own = claims.acquire(TASK, "op_1", operation_revision=1)["claim"]
        self.ops.transition(TASK, "op_1", "STARTED")
        self.write("target.txt", AFTER)  # executor wrote, then the session was lost
        resolution_id = self.resolve("ROLLBACK")["resolution"].resolution_id

        record = self.prepare(resolution_id)["rollback"]
        outcome = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual(outcome["result"], "VERIFIED")
        view = claims.inspect(TASK, "op_1")
        ended = {c["claim_id"]: c for c in view["operation_claims"]}
        self.assertEqual(ended[own["claim_id"]]["status"], "SUPERSEDED")
        self.assertEqual(ended[own["claim_id"]]["end_reason"], "SUPERSEDED_BY_ROLLBACK")
        self.assertIsNone(view["active_claim"])


class InterruptionTests(RollbackFixture):
    def test_crash_after_preservation_before_mutation_leaves_project_unchanged(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]  # this process "ends" here
        digest = self.digest()

        view = json.loads(self.fresh(FRESH_VIEW, TASK, record["rollback_id"], "op_1").stdout)

        self.assertEqual(view["record"]["status"], "PRESERVED")
        self.assertEqual(view["report"]["actually_rolled_back"], [])
        self.assertEqual(self.digest(), digest)
        self.assertEqual(RollbackService(self.storage).apply(TASK, record["rollback_id"])["result"], "VERIFIED")

    def test_crash_after_one_restore_is_proven_not_repeated(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        crashed = self.fresh(APPLY_WITH_CRASH, TASK, record["rollback_id"], "after_write")
        self.assertEqual(crashed.returncode, 17)
        interrupted = self.rollbacks.inspect(TASK, record["rollback_id"])
        in_flight = [t for t in interrupted["targets"] if t["status"] == "APPLYING"]
        self.assertEqual((interrupted["status"], len(in_flight)), ("APPLYING", 1))
        first = in_flight[0]["source_path"]

        writes = []
        real = rs._write_restored_bytes
        with mock.patch.object(rs, "_write_restored_bytes", lambda p, d: (writes.append(Path(p).name), real(p, d))):
            outcome = RollbackService(self.storage).apply(TASK, record["rollback_id"])

        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertNotIn(first, writes)  # proven restored, never written a second time
        recovered = self.target(outcome["rollback"], first)
        self.assertTrue(recovered["receipt"]["recovered_after_interruption"])
        self.assertEqual(self.path("target.txt").read_bytes(), BEFORE)
        self.assertEqual(self.path("gone.txt").read_bytes(), GONE)

    def test_crash_before_the_write_landed_is_safely_applied_once(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.fresh(APPLY_WITH_CRASH, TASK, record["rollback_id"], "before_write").returncode, 17)
        self.assertEqual(self.path("target.txt").read_bytes(), AFTER)

        outcome = RollbackService(self.storage).apply(TASK, record["rollback_id"])

        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertFalse(self.target(outcome["rollback"], "target.txt")["receipt"]["recovered_after_interruption"])

    def test_fresh_process_sees_same_status_receipts_and_next_action(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        local = self.rollbacks.apply(TASK, record["rollback_id"])["rollback"]

        view = json.loads(self.fresh(FRESH_VIEW, TASK, record["rollback_id"], "op_1").stdout)

        self.assertEqual(view["record"], local)
        self.assertEqual(view["report"]["actually_rolled_back"], ["target.txt"])
        self.assertEqual(view["report"]["next_safe_action"], local["next_safe_action"])
        self.assertEqual(view["report"]["rollback_receipts"][0]["overall"], "SUCCESS")

    def test_tampered_receipt_fails_closed(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.rollbacks.apply(TASK, record["rollback_id"])
        path = self.storage / "tasks" / "active" / TASK / "rollbacks" / f"{record['rollback_id']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.target(data, "target.txt")["receipt"]["matches_expected_restore"] = False
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        with self.assertRaises(RollbackError):
            self.rollbacks.inspect(TASK, record["rollback_id"])


class RollbackReportTests(RollbackFixture):
    def report(self, **claims):
        return RecoveryReportService(self.storage).create_report(
            task_id=TASK, microtask_id="m1", operation_id="op_1",
            incident_id="incident_" + ("_".join(sorted(claims)) or "plain"), **claims)

    def test_request_only_rollback_is_not_actually_rolled_back(self):
        self.scenario()

        report = self.report()

        self.assertEqual(report.actually_rolled_back, [])
        self.assertEqual(report.rollback_receipts, [])
        self.assertEqual(report.resolver_actions[0]["effect"], "ROLLBACK_REQUESTED")
        with self.assertRaises(RecoveryReportClaimError):
            self.report(actually_rolled_back=["target.txt"])

    def test_verified_rollback_populates_actual_facts_and_rejects_unbacked_claims(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.rollbacks.apply(TASK, record["rollback_id"])

        report = self.report(actually_rolled_back=["target.txt"])

        self.assertEqual(report.actually_rolled_back, ["target.txt"])
        self.assertEqual(report.rollback_receipts[0]["noop"], ["keep.txt"])
        self.assertEqual(report.evidence_identity["next_safe_action_source"], "rollback")
        self.assertIn("restored and verified", report.next_safe_action)
        with self.assertRaises(RecoveryReportClaimError):
            self.report(actually_rolled_back=["keep.txt"])  # NOOP is not a rollback


class FinalVerificationRepairTests(RollbackFixture):
    """Independent review repair: a receipt is history, not proof of the current state."""

    def name_sorting_before(self, other):
        from web_alarm.target_claim_store import physical_target_key, target_hash
        from web_alarm.target_identity import canonical_target

        def digest(name):
            return target_hash(physical_target_key(canonical_target(self.project, name).path))

        return next(f"keep_{i}.txt" for i in range(1000) if digest(f"keep_{i}.txt") < digest(other))

    def apply_with(self, rollback_id, hook):
        writes = []
        real = rs._write_restored_bytes

        def spy(path, data):
            writes.append(Path(path).name)
            hook(len(writes))
            real(path, data)

        with mock.patch.object(rs, "_write_restored_bytes", spy):
            return self.rollbacks.apply(TASK, rollback_id), writes

    def test_restored_target_drifting_before_completion_is_not_success(self):  # TEST A
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        order = [t["source_path"] for t in record["targets"] if t["planned_action"] == "WRITE_RESTORE"]
        drift = b"external-after-first-receipt\n"

        def external_writer(call):
            if call == 2:  # A is restored and receipted; B is about to be restored
                self.write(order[0], drift)

        outcome, writes = self.apply_with(record["rollback_id"], external_writer)
        record = outcome["rollback"]
        first, second = self.target(record, order[0]), self.target(record, order[1])

        self.assertNotEqual(record["status"], "VERIFIED")
        self.assertNotEqual(record["result"]["overall"], "SUCCESS")
        self.assertEqual(record["status"], "PARTIAL")
        self.assertEqual(self.path(order[0]).read_bytes(), drift)  # not rewritten
        self.assertEqual(writes, order)  # A written exactly once
        self.assertEqual((first["status"], first["failure"]["code"]), ("DRIFTED", "POST_RECEIPT_DRIFT"))
        self.assertTrue(first["receipt"]["matches_expected_restore"])  # historical receipt kept
        self.assertEqual(first["failure"]["observed"]["sha256"], sha256(drift))
        self.assertEqual(second["status"], "RESTORED")
        self.assertEqual(record["result"]["drifted_after_receipt"], [order[0]])
        self.assertFalse(record["result"]["final_verification"]["verified"])
        self.assertFalse(record["claims_released"])
        self.assertIn("reconciliation", record["next_safe_action"])
        replay = self.rollbacks.apply(TASK, record["rollback_id"])
        self.assertEqual((replay["result"], self.path(order[0]).read_bytes()), ("REPLAYED", drift))

    def test_noop_target_drifting_after_its_check_is_not_success(self):  # TEST B
        keep = self.name_sorting_before("target.txt")
        resolution_id = self.scenario("write", keep=keep)
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual([t["source_path"] for t in record["targets"]], [keep, "target.txt"])

        def external_writer(call):
            self.write(keep, b"external noop drift\n")  # after the NOOP proof, during the restore

        outcome, writes = self.apply_with(record["rollback_id"], external_writer)
        record = outcome["rollback"]
        noop = self.target(record, keep)

        self.assertNotEqual(record["status"], "VERIFIED")
        self.assertEqual((noop["status"], noop["failure"]["code"]), ("DRIFTED", "POST_RECEIPT_DRIFT"))
        self.assertEqual(noop["receipt"]["action"], "NOOP")
        self.assertEqual(self.path(keep).read_bytes(), b"external noop drift\n")
        self.assertEqual(writes, ["target.txt"])

    def test_clean_multi_target_rollback_passes_final_verification(self):  # TEST C
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]

        outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        record = outcome["rollback"]

        self.assertEqual((record["status"], record["result"]["overall"]), ("VERIFIED", "SUCCESS"))
        self.assertTrue(record["result"]["final_verification"]["verified"])
        self.assertEqual(record["result"]["final_verification"]["checked"], len(record["targets"]))
        self.assertTrue(record["claims_released"])
        self.assertEqual(record["result"]["drifted_after_receipt"], [])

    def test_resume_never_trusts_an_old_receipt(self):  # TEST D
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        crashed = self.fresh(APPLY_WITH_CRASH, TASK, record["rollback_id"], "second_before_write")
        self.assertEqual(crashed.returncode, 17)
        interrupted = self.rollbacks.inspect(TASK, record["rollback_id"])
        restored = [t["source_path"] for t in interrupted["targets"] if t["status"] == "RESTORED"]
        self.assertEqual(len(restored), 1)
        self.write(restored[0], b"changed after its receipt\n")

        outcome, writes = self.apply_with(record["rollback_id"], lambda call: None)
        record = outcome["rollback"]
        first = self.target(record, restored[0])

        self.assertEqual(writes, [])  # no blind second restore, no continuation past the drift
        self.assertNotEqual(record["status"], "VERIFIED")
        self.assertNotEqual(record["result"]["overall"], "SUCCESS")
        self.assertEqual((first["status"], first["failure"]["code"]), ("DRIFTED", "POST_RECEIPT_DRIFT"))
        self.assertIsNotNone(first["receipt"])
        self.assertEqual(self.path(restored[0]).read_bytes(), b"changed after its receipt\n")
        self.assertEqual(self.rollbacks.inspect(TASK, record["rollback_id"]), record)  # persistent

    def test_report_separates_historical_restore_from_verified_completion(self):  # TEST E
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        order = [t["source_path"] for t in record["targets"] if t["planned_action"] == "WRITE_RESTORE"]
        self.apply_with(record["rollback_id"], lambda call: call == 2 and self.write(order[0], b"external\n"))

        view = json.loads(self.fresh(FRESH_VIEW, TASK, record["rollback_id"], "op_1").stdout)
        receipt = view["report"]["rollback_receipts"][0]

        self.assertEqual(receipt["overall"], "PARTIAL")
        self.assertEqual(receipt["drifted_after_receipt"], [order[0]])
        self.assertEqual(receipt["restored"], [order[1]])  # currently verified
        self.assertEqual(sorted(receipt["historically_restored"]), sorted(order))
        self.assertIn(order[0], receipt["unresolved"])
        self.assertIn("reconciliation", view["report"]["next_safe_action"])
        self.assertEqual(view["report"]["evidence_identity"]["next_safe_action_source"], "rollback")
        self.assertEqual(view["record"]["status"], "PARTIAL")
        with self.assertRaises(RecoveryReportClaimError):
            RecoveryReportService(self.storage).create_report(
                task_id=TASK, microtask_id="m1", operation_id="op_1", incident_id="claim",
                actually_rolled_back=["keep.txt"])


class FullTargetOwnershipRepairTests(RollbackFixture):
    """Independent review repair #2: every target of the final proof — NOOP included —
    is owned by the rollback through RC-3 until VERIFIED is persistent."""

    def claim_file(self, name):
        return self.rollbacks.claims.load(physical_target_key(canonical_target(self.project, name).path))

    def foreign(self, name="keep.txt"):
        self.ops.begin("task_b", "m1", "write", name, operation_id="op_b", payload=b"foreign\n")
        return TargetClaimService(self.storage, lock_timeout=0.3)

    def foreign_writer(self, claims, name="keep.txt"):
        """A cooperative RC-3 writer: acquire -> mutation_boundary -> write (as WA4-E will)."""
        try:
            acquired = claims.acquire("task_b", "op_b", operation_revision=1)
            if acquired["result"] not in ("ACQUIRED", "REPLAYED"):
                return acquired["result"], False
            with claims.mutation_boundary("task_b", "op_b", operation_revision=1) as gate:
                if gate["mutation_authority"]:
                    self.write(name, b"foreign\n")
                return acquired["result"], gate["mutation_authority"]
        except TargetClaimError:  # the target lock is held: no authority can be issued
            return "LOCKED_OUT", False

    def test_foreign_rc3_writer_never_wins_after_the_final_proof(self):  # TEST F
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.target(record, "keep.txt")["planned_action"], "NOOP")
        foreign, attempts = {}, []
        real = rs.RollbackService._prove_current

        def proof_then_foreign(service, record, root):  # final proof done, VERIFIED not yet persisted
            result = real(service, record, root)
            foreign["claims"] = self.foreign()  # another TASK creates a normal v2 operation on the NOOP target
            attempts.append(self.foreign_writer(foreign["claims"]))
            return result

        with mock.patch.object(rs.RollbackService, "_prove_current", proof_then_foreign):
            outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        record = outcome["rollback"]

        self.assertEqual(attempts, [("LOCKED_OUT", False)])  # never foreign AUTHORIZED + rollback VERIFIED
        self.assertEqual((outcome["result"], record["result"]["overall"]), ("VERIFIED", "SUCCESS"))
        self.assertEqual(self.path("keep.txt").read_bytes(), KEEP)
        # the rollback won the window; afterwards the foreign operation proceeds normally
        self.assertEqual(self.foreign_writer(foreign["claims"]), ("ACQUIRED", True))
        self.assertEqual(self.path("keep.txt").read_bytes(), b"foreign\n")

    def test_noop_target_is_owned_by_the_rollback_but_never_written(self):  # TEST G
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        mtime = self.path("keep.txt").stat().st_mtime_ns
        claims = self.foreign()
        seen = {}
        real = rs._write_restored_bytes

        def write(path, data):  # acquire-all is done; the destructive phase runs
            seen["claim"] = self.claim_file("keep.txt")["active"]
            seen["foreign"] = self.foreign_writer(claims)
            real(path, data)

        with mock.patch.object(rs, "_write_restored_bytes", write):
            outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        record = outcome["rollback"]
        keep = self.target(record, "keep.txt")

        self.assertIsNotNone(seen["claim"])
        self.assertEqual(seen["claim"]["owner"], {"kind": "ROLLBACK", "rollback_id": record["rollback_id"]})
        self.assertEqual(seen["claim"]["claim_id"], keep["claim_id"])
        self.assertEqual(seen["foreign"], ("LOCKED_OUT", False))
        self.assertEqual((keep["status"], keep["receipt"]["action"]), ("NOOP", "NOOP"))
        self.assertEqual(self.path("keep.txt").read_bytes(), KEEP)
        self.assertEqual(self.path("keep.txt").stat().st_mtime_ns, mtime)  # no physical mutation
        self.assertEqual(outcome["result"], "VERIFIED")

    def test_interrupted_rollback_keeps_its_noop_target_owned_between_calls(self):  # TEST G
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.fresh(APPLY_WITH_CRASH, TASK, record["rollback_id"], "before_write").returncode, 17)
        claims = self.foreign()

        acquired = claims.acquire("task_b", "op_b", operation_revision=1)
        with claims.mutation_boundary("task_b", "op_b", operation_revision=1) as gate:
            boundary = (gate["result"], gate["result_code"], gate["mutation_authority"])

        self.assertEqual(acquired["result"], "CONFLICT")
        self.assertEqual(acquired["blocking_owner"]["owner"],
                         {"kind": "ROLLBACK", "rollback_id": record["rollback_id"]})
        self.assertEqual(boundary, ("DENIED", "NOT_OWNER", False))
        outcome = RollbackService(self.storage).apply(TASK, record["rollback_id"])
        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertEqual(self.path("keep.txt").read_bytes(), KEEP)

    def test_source_operation_claim_on_a_noop_target_is_taken_over(self):  # TEST H
        self.write("target.txt", BEFORE)
        self.write("gone.txt", GONE)
        ManifestSnapshotStore(self.storage).prepare_microtask(
            TASK, "m1", [("target.txt", "edit"), ("gone.txt", "delete")])
        self.ops.begin(TASK, "m1", "write", "target.txt", operation_id="op_1", payload=AFTER)
        own = TargetClaimService(self.storage).acquire(TASK, "op_1", operation_revision=1)["claim"]
        self.ops.transition(TASK, "op_1", "STARTED")
        self.path("gone.txt").unlink()  # another change of the microtask landed; op_1's write never did
        resolved = self.resolve("ROLLBACK")
        self.assertTrue(resolved["accepted"], resolved["resolution"].result_reason)
        record = self.prepare(resolved["resolution"].resolution_id)["rollback"]
        self.assertEqual(self.target(record, "target.txt")["planned_action"], "NOOP")

        outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        record = outcome["rollback"]
        rollback_claim = self.target(record, "target.txt")["claim_id"]
        data = self.claim_file("target.txt")
        history = {claim["claim_id"]: claim for claim in data["history"]}

        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertIsNone(data["active"])  # no source claim left behind, no second owner
        self.assertEqual((history[own["claim_id"]]["status"], history[own["claim_id"]]["end_reason"]),
                         ("SUPERSEDED", "SUPERSEDED_BY_ROLLBACK"))
        self.assertEqual(history[own["claim_id"]]["superseded_by"], rollback_claim)
        self.assertEqual((history[rollback_claim]["status"], history[rollback_claim]["owner"]["kind"]),
                         ("RELEASED", "ROLLBACK"))
        self.assertEqual(history[rollback_claim]["generation"], own["generation"] + 1)
        self.assertEqual(self.path("target.txt").read_bytes(), BEFORE)  # NOOP: never written
        self.assertEqual(self.path("gone.txt").read_bytes(), GONE)

    def test_clean_rollback_releases_every_claim_only_after_verified_is_persistent(self):  # TEST I
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]

        outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        record = outcome["rollback"]

        self.assertEqual((record["status"], record["result"]["overall"], record["claims_released"]),
                         ("VERIFIED", "SUCCESS", True))
        self.assertEqual(sorted(t["planned_action"] for t in record["targets"]),
                         ["NOOP", "WRITE_RESTORE", "WRITE_RESTORE"])
        for target in record["targets"]:
            data = self.claim_file(target["source_path"])
            self.assertIsNone(data["active"])
            ended = {claim["claim_id"]: claim for claim in data["history"]}[target["claim_id"]]
            self.assertEqual((ended["status"], ended["end_reason"], ended["owner"]["rollback_id"]),
                             ("RELEASED", "ROLLBACK_VERIFIED", record["rollback_id"]))
            self.assertGreaterEqual(ended["ended_at"], record["result"]["at"])  # VERIFIED persisted first

    def test_foreign_owner_of_a_noop_target_blocks_before_any_destructive_step(self):  # TEST J
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        foreign = self.foreign().acquire("task_b", "op_b", operation_revision=1)["claim"]
        digest = self.digest()
        writes = []

        with mock.patch.object(rs, "_write_restored_bytes", lambda p, d: writes.append(p)), \
                mock.patch.object(rs, "_delete_created", lambda p: writes.append(p)):
            blocked = self.rollbacks.apply(TASK, record["rollback_id"])
        record = blocked["rollback"]

        self.assertEqual((blocked["result"], blocked["result_code"]), ("BLOCKED", "TARGET_CONFLICT"))
        self.assertEqual([o["target"] for o in record["last_attempt"]["blocking_owners"]], ["keep.txt"])
        self.assertEqual((writes, self.digest()), ([], digest))
        self.assertEqual(record["status"], "PRESERVED")
        self.assertTrue(all(t["claim_id"] is None for t in record["targets"]))
        for name in ("target.txt", "gone.txt"):
            self.assertIsNone(self.claim_file(name)["active"])  # no partial rollback ownership
        self.assertEqual(self.claim_file("keep.txt")["active"]["claim_id"], foreign["claim_id"])

    def test_crash_between_verified_and_release_keeps_ownership_until_replay(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.fresh(RELEASE_WITH_CRASH, TASK, record["rollback_id"]).returncode, 23)
        crashed = self.rollbacks.inspect(TASK, record["rollback_id"])
        claims = self.foreign()

        self.assertEqual((crashed["status"], crashed["result"]["overall"], crashed["claims_released"]),
                         ("VERIFIED", "SUCCESS", False))
        self.assertIn("release", crashed["next_safe_action"])
        self.assertEqual(claims.acquire("task_b", "op_b", operation_revision=1)["result"], "CONFLICT")
        writes = []
        with mock.patch.object(rs, "_write_restored_bytes", lambda p, d: writes.append(p)):
            replay = self.rollbacks.apply(TASK, record["rollback_id"])
        released = replay["rollback"]

        self.assertEqual((replay["result"], released["status"], released["claims_released"]),
                         ("REPLAYED", "VERIFIED", True))
        self.assertEqual(writes, [])
        self.assertEqual([t["receipt"] for t in released["targets"]], [t["receipt"] for t in crashed["targets"]])
        self.assertTrue(all(self.claim_file(t["source_path"])["active"] is None for t in released["targets"]))
        self.assertEqual(claims.acquire("task_b", "op_b", operation_revision=1)["result"], "ACQUIRED")

    def test_release_failure_keeps_verified_and_ownership_until_replay(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        failing = mock.patch.object(rs.RollbackService, "_release_claims",
                                    side_effect=rs.TargetClaimStoreError("disk full"))

        with failing:
            outcome = self.rollbacks.apply(TASK, record["rollback_id"])
        stored = self.rollbacks.inspect(TASK, record["rollback_id"])

        self.assertEqual((outcome["result"], stored["status"], stored["claims_released"]), ("VERIFIED", "VERIFIED", False))
        self.assertIn("release", stored["next_safe_action"])
        self.assertIsNotNone(self.claim_file("keep.txt")["active"])  # still owned, never half-unprotected
        replay = self.rollbacks.apply(TASK, record["rollback_id"])
        self.assertEqual((replay["result"], replay["rollback"]["claims_released"]), ("REPLAYED", True))

    def test_close_completes_a_pending_release_of_a_verified_rollback(self):
        resolution_id = self.scenario()
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.fresh(RELEASE_WITH_CRASH, TASK, record["rollback_id"]).returncode, 23)

        closed = self.rollbacks.close(TASK, record["rollback_id"], reason="operator")

        self.assertEqual((closed["rollback"]["status"], closed["rollback"]["claims_released"]), ("VERIFIED", True))
        self.assertTrue(all(self.claim_file(t["source_path"])["active"] is None for t in closed["rollback"]["targets"]))

    def test_blocked_session_with_own_effects_can_still_be_closed(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.fresh(APPLY_WITH_CRASH, TASK, record["rollback_id"], "second_before_write").returncode, 17)
        self.ops.transition(TASK, "op_1", "UNKNOWN_AFTER_DISCONNECT")  # the lost executor resurfaces

        blocked = self.rollbacks.apply(TASK, record["rollback_id"])
        record = blocked["rollback"]

        self.assertEqual((blocked["result"], blocked["result_code"]), ("BLOCKED", "OPERATION_REVISION_CHANGED"))
        self.assertEqual(record["status"], "APPLYING")
        self.assertNotIn("APPLYING", [t["status"] for t in record["targets"]])  # every fate is proven
        self.assertIn("close", record["next_safe_action"])
        restored = [t["source_path"] for t in record["targets"] if t["status"] == "RESTORED"]
        closed = self.rollbacks.close(TASK, record["rollback_id"], reason="operation moved on")
        self.assertEqual((closed["result"], closed["rollback"]["claims_released"]), ("CLOSED", True))
        self.assertTrue(all(self.claim_file(t["source_path"])["active"] is None for t in record["targets"]))
        report = RecoveryReportService(self.storage).create_report(
            task_id=TASK, microtask_id="m1", operation_id="op_1", incident_id="closed_mid_session")
        self.assertEqual(report.actually_rolled_back, restored)  # the historical restore stays a fact

    def test_in_flight_target_is_proven_even_when_the_restore_point_breaks(self):
        resolution_id = self.scenario("two")
        record = self.prepare(resolution_id)["rollback"]
        self.assertEqual(self.fresh(APPLY_WITH_CRASH, TASK, record["rollback_id"], "second_before_write").returncode, 17)
        restore = self.storage / "tasks" / "active" / TASK / "microtasks" / "m1" / "restore_point"
        for snapshot in restore.glob("snapshots/*.bin"):
            snapshot.write_bytes(b"corrupt")
        digest = self.digest()
        early = self.rollbacks.close(TASK, record["rollback_id"])
        self.assertEqual((early["result"], early["result_code"]), ("REJECTED", "TARGET_FATE_UNKNOWN"))

        blocked = self.rollbacks.apply(TASK, record["rollback_id"])

        self.assertEqual((blocked["result"], blocked["result_code"]), ("BLOCKED", "RESTORE_POINT_INVALID"))
        self.assertNotIn("APPLYING", [t["status"] for t in blocked["rollback"]["targets"]])
        self.assertEqual(self.digest(), digest)
        closed = self.rollbacks.close(TASK, record["rollback_id"])
        self.assertEqual(closed["result"], "CLOSED")


class RollbackServerTests(RollbackFixture):
    def test_server_rollback_endpoints(self):
        resolution_id = self.scenario()
        api = WebAlarmApi(self.storage)

        status, prepared = api.dispatch("POST", f"/tasks/{TASK}/rollbacks", {
            "microtask_id": "m1", "operation_id": "op_1", "resolution_id": resolution_id})
        self.assertEqual((status, prepared["result"]), (201, "PRESERVED"))
        rollback_id = prepared["rollback"]["rollback_id"]
        status, view = api.dispatch("GET", f"/tasks/{TASK}/rollbacks/{rollback_id}")
        self.assertEqual(view["rollback"]["status"], "PRESERVED")
        status, applied = api.dispatch("POST", f"/tasks/{TASK}/rollbacks/{rollback_id}/apply", {})
        self.assertEqual((status, applied["result"]), (200, "VERIFIED"))
        status, replay = api.dispatch("POST", f"/tasks/{TASK}/rollbacks/{rollback_id}/apply", {})
        self.assertEqual(replay["result"], "REPLAYED")
        status, listed = api.dispatch("GET", f"/tasks/{TASK}/rollbacks?operation_id=op_1")
        self.assertEqual(len(listed["rollbacks"]), 1)
        with self.assertRaises(ApiError) as rejected:
            api.dispatch("POST", f"/tasks/{TASK}/rollbacks", {
                "microtask_id": "m1", "operation_id": "op_1", "resolution_id": "res_missing"})
        self.assertEqual((rejected.exception.status, rejected.exception.code), (409, "rollback_rejected"))
        with self.assertRaises(ApiError) as unknown:
            api.dispatch("POST", f"/tasks/{TASK}/rollbacks/{rollback_id}/restore_all", {})
        self.assertEqual(unknown.exception.status, 404)
        status, info = api.dispatch("GET", "/status")
        self.assertIn("rollbacks", info["capabilities"])
        self.assertEqual(self.path("target.txt").read_bytes(), BEFORE)


if __name__ == "__main__":
    unittest.main()
