import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import record_to_dict
from web_alarm.operation_contract import fingerprint_v1
from web_alarm.operation_store import OperationStore
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_report_service import RecoveryReportClaimError, RecoveryReportService
from web_alarm.resolution_store import ResolutionConflictError
from web_alarm.resolver_service import ResolverError, ResolverInputError, ResolverService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_res"
BEFORE = b"before\n"
AFTER = b"after\n"

FRESH = r"""
import json, sys
from web_alarm.recovery_report_service import RecoveryReportService
from web_alarm.resolver_service import ResolverService
storage, task_id, microtask_id, operation_id = sys.argv[1:5]
resolver = ResolverService(storage)
items = resolver.store.list(task_id, operation_id=operation_id)
report = RecoveryReportService(storage).create_report(
    task_id=task_id, microtask_id=microtask_id, operation_id=operation_id,
    incident_id="fresh_" + operation_id,
)
print(json.dumps({
    "resolutions": [item.to_dict() for item in items],
    "freshness": [resolver.freshness(item) for item in items],
    "report": {
        "next_safe_action": report.next_safe_action,
        "evidence_identity": report.evidence_identity,
        "accepted_as_already_done": report.accepted_as_already_done,
        "actually_retried": report.actually_retried,
        "actually_rolled_back": report.actually_rolled_back,
        "resolver_actions": report.resolver_actions,
    },
}))
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ResolverFixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.target = self.project / "target.txt"
        self.target.write_bytes(BEFORE)
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_res")
        self.tasks = TaskStore(self.storage)
        self.tasks.create_task("ws_res", "Resolver", "RAW TASK", "Tracked recovery", task_id=TASK)
        self.tasks.create_microtask(TASK, "M1", "Resolver step", microtask_id="m1")
        self.ops = OperationStore(self.storage)
        self.resolver = ResolverService(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def prepare(self, specs=(("target.txt", "edit"),), microtask_id="m1"):
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, microtask_id, list(specs))

    def begin(self, operation_id="op_1", status="STARTED", target="target.txt", **overrides):
        values = dict(operation_id=operation_id, payload=AFTER, request_payload={"case": operation_id})
        values.update(overrides)
        self.ops.begin(TASK, "m1", "write", target, **values)
        if status != "INTENT":
            self.ops.transition(TASK, operation_id, status)

    def basis(self, operation_id="op_1"):
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", operation_id)["DECISION"]
        return decision, self.ops.get(TASK, operation_id).revision

    def apply(self, action, operation_id="op_1", basis=None, **kwargs):
        if basis is None:
            basis = self.basis(operation_id)
        decision, revision = basis
        return self.resolver.apply(
            TASK, "m1", operation_id, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=revision,
            agent="claude-test",
            **kwargs,
        )

    def project_digest(self):
        return {
            str(path.relative_to(self.project)): sha256(path.read_bytes())
            for path in sorted(self.project.rglob("*")) if path.is_file()
        }

    def op_dict(self, operation_id="op_1"):
        return record_to_dict(self.ops.get(TASK, operation_id))

    def resolution_files(self):
        directory = self.storage / "tasks" / "active" / TASK / "resolutions"
        return sorted(directory.glob("*.json")) if directory.is_dir() else []

    def event_counts(self):
        return Counter(e.event_type for e in EventCheckpointStore(self.storage).read_events(TASK))

    def fresh(self, operation_id="op_1"):
        completed = subprocess.run(
            [sys.executable, "-B", "-c", FRESH, str(self.storage), TASK, "m1", operation_id],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def assert_no_side_effects(self, action, operation_id="op_1"):
        digest, op = self.project_digest(), self.op_dict(operation_id)
        result = self.apply(action, operation_id)
        self.assertEqual(self.project_digest(), digest)
        self.assertEqual(self.op_dict(operation_id), op)
        self.assertFalse(result["physical_mutation_performed"])
        self.assertFalse(result["resolution"].physical_mutation_performed)
        return result


class ResolverActionTests(ResolverFixture):
    def test_retry_is_persistent_rearm_only_and_survives_fresh_process(self):
        self.prepare()
        self.begin()

        result = self.assert_no_side_effects("RETRY")
        record = result["resolution"]

        self.assertTrue(result["accepted"])
        self.assertEqual(record.effect, "REARMED_FOR_FUTURE_EXECUTOR")
        self.assertEqual(record.basis["decision"], "RETRY_SAFE")
        self.assertEqual(record.basis["operation_revision"], 2)
        self.assertTrue(record.payload_verified)
        self.assertEqual(self.target.read_bytes(), BEFORE)
        fresh = self.fresh()
        self.assertEqual(fresh["resolutions"], [record.to_dict()])
        self.assertTrue(fresh["freshness"][0]["fresh"])
        self.assertEqual(fresh["report"]["actually_retried"], [])
        self.assertEqual(fresh["report"]["resolver_actions"][0]["effect"], "REARMED_FOR_FUTURE_EXECUTOR")
        self.assertIn("re-armed", record.next_safe_action)

    def test_adopt_records_fact_without_mutation_or_lifecycle_change(self):
        self.prepare()
        self.begin()
        self.target.write_bytes(AFTER)

        result = self.assert_no_side_effects("ADOPT")

        self.assertTrue(result["accepted"])
        self.assertEqual(result["resolution"].effect, "WORKSPACE_STATE_ADOPTED")
        self.assertEqual(self.ops.get(TASK, "op_1").status.value, "STARTED")
        fresh = self.fresh()
        self.assertEqual(fresh["resolutions"][0], result["resolution"].to_dict())
        self.assertEqual(fresh["report"]["accepted_as_already_done"], ["target.txt"])

    def test_rollback_is_tracked_request_only(self):
        (self.project / "extra.txt").write_bytes(b"keep\n")
        self.prepare((("target.txt", "edit"), ("extra.txt", "delete")))
        self.begin()
        self.target.write_bytes(AFTER)
        micro_before = record_to_dict(self.tasks.open_microtask(TASK, "m1"))
        manifest_before = record_to_dict(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1"))

        result = self.assert_no_side_effects("ROLLBACK")

        self.assertTrue(result["accepted"])
        self.assertEqual(result["resolution"].effect, "ROLLBACK_REQUESTED")
        self.assertEqual(result["resolution"].basis["decision"], "ROLLBACK_CURRENT_MICROTASK")
        self.assertEqual(self.target.read_bytes(), AFTER)
        self.assertEqual(record_to_dict(self.tasks.open_microtask(TASK, "m1")), micro_before)
        self.assertEqual(
            record_to_dict(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1")),
            manifest_before,
        )
        fresh = self.fresh()
        self.assertEqual(fresh["resolutions"][0]["result"], "ACCEPTED")
        self.assertEqual(fresh["report"]["actually_rolled_back"], [])

    def test_abort_is_persistent_idempotent_and_closes_resolver_recovery(self):
        self.prepare()
        self.begin()
        self.target.write_bytes(b"drift\n")  # MANUAL_REVIEW_REQUIRED
        basis = self.basis()
        self.assertEqual(basis[0]["decision"], "MANUAL_REVIEW_REQUIRED")

        aborted = self.assert_no_side_effects("ABORT")
        replay = self.apply("ABORT", basis=basis)
        self.target.write_bytes(BEFORE)  # back to RETRY_SAFE
        retry = self.apply("RETRY")
        second_abort = self.apply("ABORT")

        self.assertTrue(aborted["accepted"])
        self.assertEqual(aborted["resolution"].effect, "RECOVERY_ABORTED")
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["resolution"].to_dict(), aborted["resolution"].to_dict())
        self.assertFalse(retry["accepted"])
        self.assertEqual(retry["resolution"].result_code, "RECOVERY_ABORTED")
        self.assertEqual(second_abort["resolution"].result_code, "RECOVERY_ALREADY_ABORTED")
        self.assertEqual(self.ops.get(TASK, "op_1").status.value, "STARTED")
        self.assertEqual(self.fresh()["resolutions"][0]["effect"], "RECOVERY_ABORTED")

    def test_action_decision_mismatch_is_rejected(self):
        self.prepare()
        self.begin()  # RETRY_SAFE
        adopt = self.apply("ADOPT")
        rollback = self.apply("ROLLBACK")
        self.target.write_bytes(AFTER)  # ADOPT_CURRENT_STATE
        retry = self.apply("RETRY")

        for result, decision in ((adopt, "RETRY_SAFE"), (rollback, "RETRY_SAFE"), (retry, "ADOPT_CURRENT_STATE")):
            with self.subTest(action=result["resolution"].action.value):
                self.assertFalse(result["accepted"])
                self.assertEqual(result["resolution"].result.value, "REJECTED")
                self.assertEqual(result["resolution"].result_code, "ACTION_DECISION_MISMATCH")
                self.assertEqual(result["resolution"].basis["decision"], decision)
                self.assertIsNone(result["resolution"].effect)
        self.assertEqual(self.event_counts()["RESOLUTION_ACCEPTED"], 0)

    def test_stale_target_evidence_fails_closed(self):
        self.prepare()
        self.begin()
        old = self.basis()
        self.target.write_bytes(b"changed by someone\n")

        result = self.apply("RETRY", basis=old)

        self.assertFalse(result["accepted"])
        self.assertEqual(result["resolution"].result.value, "STALE")
        self.assertEqual(result["resolution"].result_code, "EVIDENCE_FINGERPRINT_CHANGED")
        self.assertNotEqual(
            result["resolution"].basis["evidence_fingerprint"],
            old[0]["evidence_fingerprint"],
        )

    def test_stale_operation_revision_fails_closed(self):
        self.prepare()
        self.begin(status="INTENT")
        old = self.basis()
        self.assertEqual((old[0]["decision"], old[1]), ("RETRY_SAFE", 1))
        self.ops.transition(TASK, "op_1", "STARTED")

        result = self.apply("RETRY", basis=old)

        self.assertEqual(result["resolution"].result.value, "STALE")
        self.assertEqual(result["resolution"].result_code, "OPERATION_REVISION_CHANGED")

    def test_replay_is_idempotent_and_identity_conflicts_fail_closed(self):
        self.prepare()
        self.begin()
        basis = self.basis()

        first = self.apply("RETRY", basis=basis, resolution_id="res_custom")
        again = self.apply("RETRY", basis=basis, resolution_id="res_custom")

        self.assertTrue(first["created"])
        self.assertTrue(again["replayed"])
        self.assertEqual(again["resolution"].to_dict(), first["resolution"].to_dict())
        self.assertEqual(len(self.resolution_files()), 1)
        self.assertEqual(self.event_counts()["RESOLUTION_ACCEPTED"], 1)
        with self.assertRaises(ResolutionConflictError):
            self.apply("ABORT", basis=basis, resolution_id="res_custom")
        with self.assertRaises(ResolutionConflictError):
            self.apply("RETRY", basis=({"evidence_fingerprint": "0" * 64}, basis[1]),
                       resolution_id="res_custom")
        with self.assertRaises(ResolutionConflictError):
            self.apply("RETRY", basis=basis)  # same logical identity, derived id
        self.assertEqual(len(self.resolution_files()), 1)

    def test_retry_is_rejected_for_legacy_contract(self):
        legacy_target = self.project / "legacy.txt"
        legacy_target.write_bytes(BEFORE)
        self.prepare((("legacy.txt", "delete"),))
        record = {
            "operation_id": "op_legacy",
            "task_id": TASK,
            "microtask_id": "m1",
            "action": "delete",
            "target": "legacy.txt",
            "status": "STARTED",
            "request_fingerprint": fingerprint_v1(
                task_id=TASK, microtask_id="m1", action="delete", target="legacy.txt",
                expected_precondition_sha256=None, request_payload=None,
            ),
            "expected_precondition_sha256": None,
            "result_summary": None,
            "schema_version": 1,
            "created_at": "2026-10-02T19:00:00+00:00",
            "updated_at": "2026-10-02T19:00:00+00:00",
        }
        path = self.storage / "tasks" / "active" / TASK / "operations" / "op_legacy.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        legacy_bytes = path.read_bytes()

        result = self.apply("RETRY", operation_id="op_legacy")

        self.assertEqual(result["resolution"].basis["decision"], "RETRY_SAFE")
        self.assertIsNone(result["resolution"].basis["operation_revision"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["resolution"].result_code, "LEGACY_CONTRACT")
        self.assertEqual(path.read_bytes(), legacy_bytes)

    def test_retry_is_rejected_for_incomplete_contract(self):
        self.prepare()
        self.begin(payload=None, expected_post_state={
            "exists": True, "size": len(AFTER), "sha256": sha256(AFTER),
        })

        result = self.apply("RETRY")

        self.assertEqual(result["resolution"].basis["decision"], "RETRY_SAFE")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["resolution"].result_code, "CONTRACT_INSUFFICIENT")
        self.assertIn("payload_missing", result["resolution"].result_reason)

    def test_retry_is_rejected_for_corrupt_contract_without_recording(self):
        self.prepare()
        self.begin()
        basis = self.basis()
        path = self.storage / "tasks" / "active" / TASK / "operations" / "op_1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["contract"]["target_key"] = "other.txt"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        with self.assertRaises(ResolverError):
            self.apply("RETRY", basis=basis)
        self.assertEqual(self.resolution_files(), [])

    def test_payload_integrity_failure_blocks_rearm(self):
        self.prepare()
        self.begin()
        blob = next((self.storage / "tasks" / "active" / TASK / "payloads").glob("*.bin"))
        blob.write_bytes(b"tampered\n")

        result = self.apply("RETRY")

        self.assertFalse(result["accepted"])
        self.assertEqual(result["resolution"].result_code, "PAYLOAD_INTEGRITY_FAILURE")
        self.assertFalse(result["resolution"].payload_verified)

    def test_malformed_requests_fail_before_any_record(self):
        self.prepare()
        self.begin()
        decision, revision = self.basis()
        for kwargs in (
            dict(action="REDO"),
            dict(evidence_fingerprint="abc"),
            dict(operation_revision=0),
            dict(operation_revision=True),
        ):
            values = dict(
                action="RETRY",
                evidence_fingerprint=decision["evidence_fingerprint"],
                operation_revision=revision,
            )
            values.update(kwargs)
            action = values.pop("action")
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ResolverInputError):
                    self.resolver.apply(TASK, "m1", "op_1", action, **values)
        self.assertEqual(self.resolution_files(), [])


class ResolverRecoveryReportTests(ResolverFixture):
    def report(self, **claims):
        return RecoveryReportService(self.storage).create_report(
            task_id=TASK, microtask_id="m1", operation_id="op_1",
            incident_id="incident_" + "_".join(sorted(claims)) if claims else "incident_plain",
            **claims,
        )

    def test_adopt_is_the_only_source_of_accepted_facts(self):
        self.prepare()
        self.begin()
        self.target.write_bytes(AFTER)

        with self.assertRaises(RecoveryReportClaimError):
            self.report(accepted_as_already_done=["target.txt"])
        self.apply("ADOPT")
        report = self.report()
        repeated_claim = self.report(accepted_as_already_done=["target.txt"])

        self.assertEqual(report.accepted_as_already_done, ["target.txt"])
        self.assertEqual(repeated_claim.accepted_as_already_done, ["target.txt"])
        self.assertEqual(report.resolver_actions[0]["action"], "ADOPT")
        self.assertTrue(report.resolver_actions[0]["fresh"])
        self.assertEqual(report.authority, "evidence_only")
        self.assertFalse(report.automatic_mutation_authorized)

    def test_retry_rearm_and_rollback_request_are_never_reported_as_executed(self):
        self.prepare()
        self.begin()
        self.apply("RETRY")

        report = self.report()
        self.assertEqual(report.actually_retried, [])
        self.assertEqual(report.resolver_actions[0]["effect"], "REARMED_FOR_FUTURE_EXECUTOR")
        for claim in ("actually_retried", "actually_rolled_back"):
            with self.subTest(claim=claim):
                with self.assertRaises(RecoveryReportClaimError):
                    self.report(**{claim: ["target.txt"]})

    def test_rollback_request_is_not_actually_rolled_back(self):
        (self.project / "extra.txt").write_bytes(b"keep\n")
        self.prepare((("target.txt", "edit"), ("extra.txt", "delete")))
        self.begin()
        self.target.write_bytes(AFTER)
        self.apply("ROLLBACK")

        report = self.report()

        self.assertEqual(report.actually_rolled_back, [])
        self.assertEqual(report.resolver_actions[0]["effect"], "ROLLBACK_REQUESTED")
        self.assertIn("nothing was restored", report.next_safe_action)

    def test_stale_adopt_is_not_authority(self):
        self.prepare()
        self.begin()
        self.target.write_bytes(AFTER)
        self.apply("ADOPT")
        self.target.write_bytes(b"later external edit\n")

        report = self.report()

        self.assertEqual(report.accepted_as_already_done, [])
        self.assertFalse(report.resolver_actions[0]["fresh"])
        self.assertFalse(report.resolver_actions[0]["authority"])
        self.assertEqual(report.resolver_actions[0]["freshness_code"], "EVIDENCE_FINGERPRINT_CHANGED")
        self.assertIn("run a new reconciliation", report.next_safe_action)

    # --- Independent Review Repair (RC-2 blockers 1 and 2) -------------------

    def test_accepted_abort_drives_report_next_safe_action(self):
        """TEST A: after accepted ABORT the report must not recommend RETRY."""
        self.prepare()
        self.begin()
        decision, _ = self.basis()
        self.assertEqual(decision["decision"], "RETRY_SAFE")
        digest = self.project_digest()
        aborted = self.apply("ABORT")["resolution"]

        fresh = self.fresh()
        report = fresh["report"]

        self.assertTrue(fresh["freshness"][0]["fresh"])
        self.assertEqual(fresh["resolutions"], [aborted.to_dict()])
        self.assertEqual(report["next_safe_action"], aborted.next_safe_action)
        self.assertNotEqual(report["next_safe_action"], decision["next_safe_action"])
        self.assertNotIn("retry only through", report["next_safe_action"])
        self.assertIn("is closed", report["next_safe_action"])
        self.assertEqual(report["evidence_identity"]["next_safe_action_source"], "resolver")
        self.assertEqual(
            report["evidence_identity"]["next_safe_action_resolution_id"], aborted.resolution_id
        )
        action = report["resolver_actions"][0]
        self.assertEqual(
            (action["action"], action["result"], action["effect"], action["authority"]),
            ("ABORT", "ACCEPTED", "RECOVERY_ABORTED", True),
        )
        self.assertEqual(report["accepted_as_already_done"], [])
        self.assertEqual(report["actually_retried"], [])
        self.assertEqual(self.project_digest(), digest)

    def test_stale_outcome_survives_report_and_fresh_process(self):
        """TEST B: a persisted STALE result is reported, without authority."""
        self.prepare()
        self.begin()
        old = self.basis()
        self.target.write_bytes(b"changed by someone\n")
        stale = self.apply("RETRY", basis=old)["resolution"]
        self.assertEqual(stale.result.value, "STALE")

        fresh = self.fresh()
        report = fresh["report"]

        self.assertEqual(fresh["resolutions"], [stale.to_dict()])
        self.assertEqual(len(report["resolver_actions"]), 1)
        action = report["resolver_actions"][0]
        self.assertEqual(action["resolution_id"], stale.resolution_id)
        self.assertEqual(action["result"], "STALE")
        self.assertEqual(action["result_code"], "EVIDENCE_FINGERPRINT_CHANGED")
        self.assertIsNone(action["effect"])
        self.assertFalse(action["authority"])
        self.assertFalse(action["physical_mutation_performed"])
        self.assertEqual(report["accepted_as_already_done"], [])
        self.assertEqual(report["actually_retried"], [])
        self.assertEqual(report["actually_rolled_back"], [])
        self.assertIn("run a new reconciliation", report["next_safe_action"])
        self.assertEqual(report["evidence_identity"]["next_safe_action_source"], "resolver")
        self.assertEqual(self.target.read_bytes(), b"changed by someone\n")

    def test_rejected_outcomes_are_reported_without_authority(self):
        self.prepare()
        self.begin()  # RETRY_SAFE
        decision, _ = self.basis()
        rejected = self.apply("ADOPT")["resolution"]

        report = self.report()

        action = report.resolver_actions[0]
        self.assertEqual((action["result"], action["result_code"]), ("REJECTED", "ACTION_DECISION_MISMATCH"))
        self.assertFalse(action["authority"])
        self.assertEqual(report.accepted_as_already_done, [])
        # a fresh rejection of the wrong action leaves the deterministic advice in force
        self.assertEqual(report.next_safe_action, rejected.next_safe_action)
        self.assertEqual(report.next_safe_action, decision["next_safe_action"])

    def test_rejected_rearm_is_not_recommended_as_retry(self):
        self.prepare()
        self.begin(payload=None, expected_post_state={
            "exists": True, "size": len(AFTER), "sha256": sha256(AFTER),
        })
        decision, _ = self.basis()
        self.assertEqual(decision["decision"], "RETRY_SAFE")
        rejected = self.apply("RETRY")["resolution"]

        report = self.report()

        self.assertEqual(report.resolver_actions[0]["result_code"], "CONTRACT_INSUFFICIENT")
        self.assertEqual(report.next_safe_action, rejected.next_safe_action)
        self.assertNotEqual(report.next_safe_action, decision["next_safe_action"])

    def test_report_next_action_follows_fresh_accepted_semantics(self):
        self.prepare()
        self.begin()
        retry = self.apply("RETRY")["resolution"]
        self.assertEqual(self.report().next_safe_action, retry.next_safe_action)
        self.assertIn("nothing was executed", retry.next_safe_action)

        self.target.write_bytes(AFTER)
        adopt = self.apply("ADOPT")["resolution"]
        report = self.report()
        self.assertEqual(report.next_safe_action, adopt.next_safe_action)
        self.assertEqual(report.accepted_as_already_done, ["target.txt"])
        authorities = {a["action"]: a["authority"] for a in report.resolver_actions}
        self.assertEqual(authorities, {"RETRY": False, "ADOPT": True})

    def test_report_without_resolutions_keeps_decision_next_action(self):
        self.prepare()
        self.begin()
        decision, _ = self.basis()

        report = self.report()

        self.assertEqual(report.resolver_actions, [])
        self.assertEqual(report.next_safe_action, decision["next_safe_action"])
        self.assertNotIn("next_safe_action_source", report.evidence_identity)


class ResolverServerTests(ResolverFixture):
    def test_server_resolution_endpoints(self):
        self.prepare()
        self.begin()
        api = WebAlarmApi(self.storage)
        decision, revision = self.basis()
        body = {
            "microtask_id": "m1",
            "operation_id": "op_1",
            "action": "RETRY",
            "evidence_fingerprint": decision["evidence_fingerprint"],
            "operation_revision": revision,
            "agent": "chatgpt",
        }

        status, created = api.dispatch("POST", f"/tasks/{TASK}/resolutions", body)
        self.assertEqual(status, 201)
        self.assertTrue(created["accepted"])
        status, replay = api.dispatch("POST", f"/tasks/{TASK}/resolutions", body)
        self.assertEqual(status, 200)
        self.assertTrue(replay["replayed"])
        resolution_id = created["resolution"]["resolution_id"]
        status, one = api.dispatch("GET", f"/tasks/{TASK}/resolutions/{resolution_id}")
        self.assertEqual(status, 200)
        self.assertTrue(one["freshness"]["fresh"])
        status, listed = api.dispatch("GET", f"/tasks/{TASK}/resolutions?operation_id=op_1")
        self.assertEqual(len(listed["resolutions"]), 1)

        with self.assertRaises(ApiError) as rejected:
            api.dispatch("POST", f"/tasks/{TASK}/resolutions", dict(body, action="ADOPT"))
        self.assertEqual(rejected.exception.status, 409)
        self.assertEqual(rejected.exception.code, "resolution_not_accepted")
        self.assertEqual(rejected.exception.details["resolution"]["result"], "REJECTED")
        with self.assertRaises(ApiError) as conflict:
            api.dispatch("POST", f"/tasks/{TASK}/resolutions",
                         dict(body, action="ABORT", resolution_id=resolution_id))
        self.assertEqual(conflict.exception.code, "resolution_conflict")
        with self.assertRaises(ApiError) as invalid:
            api.dispatch("POST", f"/tasks/{TASK}/resolutions", dict(body, action="REDO"))
        self.assertEqual(invalid.exception.status, 400)
        status, info = api.dispatch("GET", "/status")
        self.assertIn("resolutions", info["capabilities"])
        self.assertEqual(self.target.read_bytes(), BEFORE)


if __name__ == "__main__":
    unittest.main()
