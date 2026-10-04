"""RC-5: checkpoint = projection, pure inspection, Resolver/rollback precedence, closeout gate."""

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import web_alarm.rollback_service as rs
from web_alarm.cli import main as cli_main
from web_alarm.closeout import CloseoutService
from web_alarm.context_pack import EntryContextPackBuilder
from web_alarm.event_checkpoint_store import EventCheckpointStore
from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import CheckpointRecord, MicrotaskStatus
from web_alarm.operation_store import OperationStore
from web_alarm.projection import ProjectionError, ProjectionService
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.recovery_report_service import RecoveryReportService
from web_alarm.remote_entry import RemoteEntry
from web_alarm.resolver_service import ResolverService
from web_alarm.rollback_service import RollbackService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.state_machine import ServerStateMachine
from web_alarm.target_claim_service import TargetClaimService
from web_alarm.task_store import TaskStore, TaskStoreError
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
TASK = "task_p"
BEFORE, AFTER, KEEP = b"before\n", b"after-content\n", b"keep\n"

FRESH_PROJECTION = r"""
import json, sys
from web_alarm.projection import ProjectionService
from web_alarm.context_pack import EntryContextPackBuilder
storage, task_id = sys.argv[1:3]
service = ProjectionService(storage)
projection = service.build(task_id)
pack = EntryContextPackBuilder(storage).build(task_id)
print(json.dumps({
    "source": projection["source_fingerprint"],
    "projection": projection["projection_fingerprint"],
    "next": projection["next_safe_action"],
    "authority": projection["authority_source"],
    "checkpoint": service.validate_checkpoint(task_id, projection)["status"],
    "pack_next": pack["NEXT_SAFE_ACTION"],
}))
"""

REBUILD_CRASH_BEFORE_MD = r"""
import os, sys
import web_alarm.event_checkpoint_store as ecs
from web_alarm.projection import ProjectionService
storage, task_id = sys.argv[1:3]
real = ecs._atomic_write_text
def crash(path, text):
    if path.name == "checkpoint.md":
        os._exit(31)
    return real(path, text)
ecs._atomic_write_text = crash
ProjectionService(storage).rebuild_checkpoint(task_id)
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree(root: Path) -> dict:
    """Every file (exact bytes) and directory under root."""
    if not root.exists():
        return {}
    result = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        result[rel] = sha256(path.read_bytes()) if path.is_file() else "<dir>"
    return result


class ProjectionFixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        WorkspaceRegistry(self.storage).register("Project", self.project, workspace_id="ws_p")
        self.tasks = TaskStore(self.storage)
        for task in (TASK, "task_other"):
            self.tasks.create_task("ws_p", task, "RAW TASK", "Projection", task_id=task)
        self.tasks.create_microtask(TASK, "M1", "First", microtask_id="m1")
        self.tasks.create_microtask(TASK, "M2", "Second", microtask_id="m2")
        self.tasks.create_microtask("task_other", "M1", "Other", microtask_id="m1")
        self.ops = OperationStore(self.storage)
        self.projection = ProjectionService(self.storage)
        self.machine = ServerStateMachine(self.storage)
        self.api = WebAlarmApi(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, name, data):
        (self.project / name).write_bytes(data)

    def digest(self):
        return {"storage": tree(self.storage), "project": tree(self.project)}

    def task_dir(self, task=TASK):
        return self.tasks.task_directory(task)

    def checkpoint_path(self):
        return self.task_dir() / "checkpoint.json"

    def fresh(self, script, *args):
        completed = subprocess.run([sys.executable, "-B", "-c", script, str(self.storage), *args],
                                   cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        return completed

    # --- workflow helpers ------------------------------------------------------------------

    def verify_microtask(self, microtask_id, target):
        self.write(target, BEFORE)
        self.machine.prepare_microtask(TASK, microtask_id, [(target, "edit")])
        for status in ("READY", "ACTIVE", "DONE"):
            self.machine.transition(TASK, microtask_id, status)
        self.machine.transition(TASK, microtask_id, "VERIFIED", verification_evidence="checked")

    def started_operation(self, *, at, kind="single"):
        """op_1 on m1, STARTED; ``at`` = BEFORE (retry), AFTER (adopt); kind=mixed -> rollback."""
        self.write("target.txt", BEFORE)
        specs = [("target.txt", "edit")]
        if kind == "mixed":
            self.write("keep.txt", KEEP)
            specs.append(("keep.txt", "delete"))
        ManifestSnapshotStore(self.storage).prepare_microtask(TASK, "m1", specs)
        self.ops.begin(TASK, "m1", "write", "target.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "STARTED")
        self.write("target.txt", at)

    def resolve(self, action, operation_id="op_1"):
        decision = ReconciliationService(self.storage).reconcile(TASK, "m1", operation_id)["DECISION"]
        outcome = ResolverService(self.storage).apply(
            TASK, "m1", operation_id, action,
            evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, operation_id).revision,
        )
        self.assertTrue(outcome["accepted"], outcome["resolution"].result_reason)
        return outcome["resolution"]

    @staticmethod
    def without_locks(digest):
        return {"project": digest["project"],
                "storage": {k: v for k, v in digest["storage"].items() if not k.startswith("locks")}}

    def tamper(self, path, **fields):
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(fields)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class CheckpointProjectionTests(ProjectionFixture):
    def test_missing_checkpoint_projection_is_built_and_reading_creates_nothing(self):  # A
        before = self.digest()

        projection = self.projection.build(TASK)
        validation = self.projection.validate_checkpoint(TASK)
        pack = EntryContextPackBuilder(self.storage).build(TASK)
        self.api.dispatch("GET", f"/tasks/{TASK}/ui")
        self.api.dispatch("GET", f"/tasks/{TASK}")

        self.assertEqual(self.digest(), before)
        self.assertFalse(self.checkpoint_path().exists())
        self.assertEqual(validation["status"], "MISSING")
        self.assertEqual(projection["position"]["current_microtask_id"], "m1")
        self.assertEqual(projection["position"]["current_status"], "PLANNED")
        self.assertEqual(projection["authority_source"], "lifecycle")
        self.assertEqual(pack["NEXT_SAFE_ACTION"], projection["next_safe_action"])
        self.assertIn("prepare restore point for m1", projection["next_safe_action"])

    def test_valid_modern_checkpoint_is_reproduced_by_a_fresh_process(self):  # B, Z
        self.verify_microtask("m1", "one.txt")
        rebuilt = self.projection.rebuild_checkpoint(TASK)

        fresh = json.loads(self.fresh(FRESH_PROJECTION, TASK).stdout)

        self.assertEqual(rebuilt["validation"]["status"], "VALID")
        self.assertEqual(fresh["checkpoint"], "VALID")
        self.assertEqual(fresh["source"], rebuilt["projection"]["source_fingerprint"])
        self.assertEqual(fresh["projection"], rebuilt["projection"]["projection_fingerprint"])
        self.assertEqual((fresh["next"], fresh["pack_next"]), (rebuilt["checkpoint"].next_safe_action,) * 2)
        self.assertIn("prepare restore point for m2", fresh["next"])

    def test_source_change_makes_an_old_checkpoint_stale_and_never_used(self):  # C
        self.verify_microtask("m1", "one.txt")
        self.projection.rebuild_checkpoint(TASK)
        saved = {name: (self.task_dir() / name).read_bytes() for name in ("checkpoint.json", "checkpoint.md")}
        changes = {
            "plan": lambda: self.tasks.create_microtask(TASK, "M3", "Third", microtask_id="m3"),
            "microtask": lambda: self.tasks.set_microtask_status(TASK, "m2", MicrotaskStatus.BLOCKED_PREPARE),
            "operation": lambda: (self.write("two.txt", BEFORE),
                                  self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_x", payload=AFTER)),
            "operation_revision": lambda: self.ops.transition(TASK, "op_x", "STARTED"),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                change()
                for file, data in saved.items():  # the checkpoint built before the change
                    (self.task_dir() / file).write_bytes(data)
                validation = self.projection.validate_checkpoint(TASK)
                pack = EntryContextPackBuilder(self.storage).build(TASK)
                ui = self.api.dispatch("GET", f"/tasks/{TASK}/ui")[1]
                projection = self.projection.build(TASK)

                self.assertEqual(validation["status"], "STALE")
                self.assertEqual(pack["CHECKPOINT"]["status"], "STALE")
                self.assertEqual(pack["NEXT_SAFE_ACTION"], projection["next_safe_action"])
                self.assertEqual(ui["next_safe_action"], projection["next_safe_action"])
                self.assertEqual(ui["checkpoint_validation"]["status"], "STALE")

    def test_tampered_checkpoint_is_never_valid(self):  # D
        self.verify_microtask("m1", "one.txt")
        self.projection.rebuild_checkpoint(TASK)
        path = self.checkpoint_path()
        original = path.read_bytes()
        tampers = {
            "next_safe_action": {"next_safe_action": "do dangerous thing"},
            "current_status": {"current_status": "VERIFIED"},
            "current_microtask_id": {"current_microtask_id": "m1"},
            "projection_fingerprint": None,
        }
        for name, fields in tampers.items():
            with self.subTest(tamper=name):
                path.write_bytes(original)
                if fields is None:
                    data = json.loads(original)
                    data["projection"]["projection_fingerprint"] = "0" * 64
                    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                else:
                    self.tamper(path, **fields)
                validation = self.projection.validate_checkpoint(TASK)
                pack = EntryContextPackBuilder(self.storage).build(TASK)

                self.assertEqual(validation["status"], "INCONSISTENT")
                self.assertNotEqual(pack["NEXT_SAFE_ACTION"], "do dangerous thing")
                self.assertEqual(pack["CURRENT_MICROTASK"], "m2")
                self.assertEqual(pack["CURRENT_STATUS"], "PLANNED")

    def test_markdown_tamper_or_corrupt_json_is_detected(self):  # adversarial
        self.verify_microtask("m1", "one.txt")
        self.projection.rebuild_checkpoint(TASK)
        md = self.task_dir() / "checkpoint.md"
        md.write_text(md.read_text(encoding="utf-8").replace("prepare", "skip"), encoding="utf-8")
        self.assertEqual(self.projection.validate_checkpoint(TASK)["status"], "INCONSISTENT")

        self.checkpoint_path().write_text("{not json", encoding="utf-8")
        pack = EntryContextPackBuilder(self.storage).build(TASK)
        self.assertEqual(pack["CHECKPOINT"]["status"], "CORRUPT")
        self.assertIn("prepare restore point for m2", pack["NEXT_SAFE_ACTION"])
        self.assertEqual(self.projection.rebuild_checkpoint(TASK)["validation"]["status"], "VALID")

    def test_legacy_checkpoint_is_read_unvalidated_never_rewritten_then_rebuilt(self):  # E
        self.verify_microtask("m1", "one.txt")
        legacy = CheckpointRecord(task_id=TASK, workspace_id="ws_p", current_microtask_id="m1",
                                  current_status=MicrotaskStatus.VERIFIED, snapshot_status="VERIFIED",
                                  last_operation_id="op_legacy", next_safe_action="complete TASK now")
        EventCheckpointStore(self.storage).write_checkpoint(legacy)
        raw = json.loads(self.checkpoint_path().read_text(encoding="utf-8"))
        raw.pop("projection")  # exactly the RC-0..RC-4 file shape
        self.checkpoint_path().write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        before = self.digest()

        validation = self.projection.validate_checkpoint(TASK)
        pack = EntryContextPackBuilder(self.storage).build(TASK)
        RemoteEntry(self.storage).enter(TASK)
        self.api.dispatch("GET", f"/tasks/{TASK}/ui")

        self.assertEqual(self.digest(), before)  # read never migrates
        self.assertEqual(validation["status"], "LEGACY_UNVALIDATED")
        self.assertNotEqual(pack["NEXT_SAFE_ACTION"], "complete TASK now")
        self.assertEqual(pack["CURRENT_MICROTASK"], "m2")
        rebuilt = self.projection.rebuild_checkpoint(TASK)
        self.assertEqual(rebuilt["validation"]["status"], "VALID")
        self.assertEqual(rebuilt["checkpoint"].checkpoint_id, legacy.checkpoint_id)

    def test_fabricated_checkpoint_cannot_steer_context(self):  # H, §23
        self.verify_microtask("m1", "one.txt")
        real = self.projection.rebuild_checkpoint(TASK)["checkpoint"]
        fake = CheckpointRecord(task_id=TASK, workspace_id="ws_p", current_microtask_id="m1",
                                last_verified_microtask_id="m1", current_status=MicrotaskStatus.ACTIVE,
                                snapshot_status="VERIFIED", next_safe_action="do dangerous thing",
                                projection=dict(real.projection))  # even with copied metadata
        EventCheckpointStore(self.storage).write_checkpoint(fake)

        pack = EntryContextPackBuilder(self.storage).build(TASK)
        entry = RemoteEntry(self.storage).enter(TASK)
        code = self.cli("report", "--task-id", TASK)

        self.assertEqual(pack["CHECKPOINT"]["status"], "INCONSISTENT")
        self.assertEqual((pack["CURRENT_MICROTASK"], pack["CURRENT_STATUS"]), ("m2", "PLANNED"))
        self.assertNotIn("dangerous", pack["NEXT_SAFE_ACTION"] + entry["CONTEXT_PACK"]["NEXT_SAFE_ACTION"])
        self.assertNotIn("dangerous", code[1])

    def test_interrupted_rebuild_between_json_and_md_is_not_valid(self):  # adversarial
        self.verify_microtask("m1", "one.txt")
        self.assertEqual(self.fresh(REBUILD_CRASH_BEFORE_MD, TASK).returncode, 31)
        md = self.task_dir() / "checkpoint.md"
        data = json.loads(self.checkpoint_path().read_text(encoding="utf-8"))

        validation = self.projection.validate_checkpoint(TASK)

        self.assertIsNotNone(data["projection"])  # JSON landed, markdown did not match it
        self.assertNotEqual(validation["status"], "VALID")
        self.assertTrue(md.exists())
        self.assertEqual(self.projection.rebuild_checkpoint(TASK)["validation"]["status"], "VALID")

    def test_rebuild_is_refused_for_a_completed_task(self):  # adversarial: history stays read-only
        self.verify_microtask("m1", "one.txt")
        self.verify_microtask("m2", "two.txt")
        self.assertEqual(CloseoutService(self.storage).complete(TASK)["result"], "COMPLETED")
        before = self.digest()

        with self.assertRaises(ProjectionError):
            self.projection.rebuild_checkpoint(TASK)
        projection = self.projection.build(TASK)

        self.assertEqual(self.without_locks(self.digest()), self.without_locks(before))
        self.assertEqual(projection["task"]["location"], "completed")
        self.assertEqual(projection["authority_source"], "task_status")
        self.assertIn("TASK_NOT_ACTIVE", [b["code"] for b in projection["closeout"]])

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(["--storage-root", str(self.storage), *args])
        return code, out.getvalue(), err.getvalue()


class PurityTests(ProjectionFixture):
    def test_snapshot_verify_success_and_failures_write_nothing(self):  # F, G
        self.write("one.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit"), ("new.txt", "create")])
        before = self.digest()
        status, payload = self.api.dispatch("POST", "/microtasks/m1/snapshot", {"task_id": TASK, "action": "verify"})
        self.assertEqual((status, payload["workflow_mutation_performed"]), (200, False))
        self.assertEqual(self.digest(), before)

        restore = self.task_dir() / "microtasks" / "m1" / "restore_point"
        snapshot = next(restore.glob("snapshots/*.bin"))
        manifest = restore / "manifest.json"
        corruptions = {
            "corrupt_snapshot": lambda: snapshot.write_bytes(b"corrupt"),
            "missing_snapshot": lambda: snapshot.unlink(),
            "invalid_manifest": lambda: manifest.write_text("{broken", encoding="utf-8"),
        }
        originals = {snapshot: snapshot.read_bytes(), manifest: manifest.read_bytes()}
        for name, corrupt in corruptions.items():
            with self.subTest(case=name):
                for path, data in originals.items():
                    path.write_bytes(data)
                corrupt()
                before = self.digest()
                with self.assertRaises(ApiError) as caught:
                    self.api.dispatch("POST", "/microtasks/m1/snapshot", {"task_id": TASK, "action": "verify"})
                self.assertEqual((caught.exception.status, caught.exception.code), (409, "snapshot_not_verified"))
                self.assertFalse(caught.exception.details["workflow_mutation_performed"])
                self.assertEqual(self.digest(), before)
                self.assertEqual(self.tasks.open_microtask(TASK, "m1").status, MicrotaskStatus.BACKUP_VERIFIED)
        for path, data in originals.items():
            path.write_bytes(data)
        self.assertEqual(ManifestSnapshotStore(self.storage).open_manifest(TASK, "m1").status.value, "VERIFIED")

    def test_every_inspection_path_is_read_only(self):  # Y, §24
        self.verify_microtask("m1", "one.txt")
        self.started_operation_on_m2()
        self.projection.rebuild_checkpoint(TASK)
        before = self.digest()
        reads = [
            ("GET", f"/tasks/{TASK}"), ("GET", f"/tasks/{TASK}/ui"), ("GET", f"/tasks/{TASK}/context"),
            ("GET", f"/tasks/{TASK}/projection"), ("GET", f"/tasks/{TASK}/checkpoint"),
            ("GET", f"/tasks/{TASK}/closeout"), ("GET", f"/tasks/{TASK}/operations"),
            ("GET", f"/tasks/{TASK}/operations/op_2"), ("GET", f"/tasks/{TASK}/resolutions"),
            ("GET", f"/tasks/{TASK}/rollbacks"), ("GET", f"/tasks/{TASK}/recovery-reports"),
            ("GET", f"/tasks/{TASK}/operations/op_2/claim"),
        ]
        for _ in range(3):
            for method, path in reads:
                self.api.dispatch(method, path)
            self.api.dispatch("POST", f"/tasks/{TASK}/reconcile", {"microtask_id": "m2", "operation_id": "op_2"})
            self.api.dispatch("POST", "/microtasks/m1/snapshot", {"task_id": TASK, "action": "verify"})
            self.projection.build(TASK)
            self.projection.validate_checkpoint(TASK)
            CloseoutService(self.storage).inspect(TASK)
            RemoteEntry(self.storage).enter(TASK)
            for args in (("status", "--task-id", TASK), ("report", "--task-id", TASK),
                         ("checkpoint", "show", "--task-id", TASK), ("checkpoint", "validate", "--task-id", TASK),
                         ("task", "closeout", "--task-id", TASK)):
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    self.assertEqual(cli_main(["--storage-root", str(self.storage), *args]), 0, err.getvalue())

        self.assertEqual(self.digest(), before)

    def started_operation_on_m2(self):
        self.write("two.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m2", [("two.txt", "edit")])
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_2", payload=AFTER)
        self.ops.transition(TASK, "op_2", "STARTED")

    def test_event_history_never_overrides_authoritative_records(self):  # adversarial
        before = self.projection.build(TASK)
        EventCheckpointStore(self.storage).append_event(
            TASK, "MICROTASK_TRANSITION", microtask_id="m1", payload={"from": "PLANNED", "to": "VERIFIED"})

        after = self.projection.build(TASK)

        self.assertEqual(after["projection_fingerprint"], before["projection_fingerprint"])
        self.assertEqual(after["position"]["current_status"], "PLANNED")


class PositionTests(ProjectionFixture):
    def test_current_microtask_is_derived_from_lifecycle_not_pointers(self):  # §7
        self.verify_microtask("m1", "one.txt")
        self.tasks.set_current_microtask(TASK, "m1")  # pointer stays behind the lifecycle

        projection = self.projection.build(TASK)

        self.assertEqual(projection["position"]["current_microtask_id"], "m2")
        self.assertEqual(projection["position"]["plan_pointer_state"], "STALE_BEHIND_LIFECYCLE")
        self.assertIn("PLAN_POINTER_STALE_BEHIND_LIFECYCLE", [d["code"] for d in projection["diagnostics"]])
        self.assertEqual(projection["blockers"], [])

    def test_impossible_plan_states_fail_closed(self):  # adversarial
        micro_dir = self.task_dir() / "microtasks"
        cases = {
            "MULTIPLE_ACTIVE": {"m1": "ACTIVE", "m2": "ACTIVE"},
            "VERIFIED_OUT_OF_ORDER": {"m1": "PLANNED", "m2": "VERIFIED"},
            "LATER_STAGE_STARTED": {"m1": "DONE", "m2": "BACKUP_VERIFIED"},
        }
        for code, statuses in cases.items():
            with self.subTest(case=code):
                for microtask_id, status in statuses.items():
                    self.tamper(micro_dir / f"{microtask_id}.json", status=status)
                projection = self.projection.build(TASK)
                entry = RemoteEntry(self.storage).enter(TASK)

                self.assertIn(code, [b["code"] for b in projection["blockers"]])
                self.assertEqual(projection["authority_source"], "projection_blocker")
                self.assertIn("manual review", projection["next_safe_action"])
                self.assertEqual(entry["ENTRY_STATE"], "PROJECTION_BLOCKED")
                self.assertFalse(CloseoutService(self.storage).inspect(TASK)["eligible"])

    def test_orphan_microtask_record_blocks_closeout(self):  # adversarial: crash inside create_microtask
        self.verify_microtask("m1", "one.txt")
        self.verify_microtask("m2", "two.txt")
        orphan = json.loads((self.task_dir() / "microtasks" / "m2.json").read_text(encoding="utf-8"))
        orphan.update(microtask_id="m9", sequence=3)
        (self.task_dir() / "microtasks" / "m9.json").write_text(json.dumps(orphan), encoding="utf-8")

        verdict = CloseoutService(self.storage).inspect(TASK)

        self.assertIn("ORPHAN_MICROTASKS", [b["code"] for b in verdict["blockers"]])


class PrecedenceTests(ProjectionFixture):
    def assert_authority(self, source, state, expected_next):
        projection = self.projection.build(TASK)
        pack = EntryContextPackBuilder(self.storage).build(TASK)
        advisory = ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["NEXT_SAFE_ACTION"]
        self.assertEqual((projection["authority_source"], projection["recovery"]["state"]), (source, state))
        self.assertEqual(pack["NEXT_SAFE_ACTION"], expected_next)
        self.assertEqual(projection["next_safe_action"], expected_next)
        if source != "reconciliation":
            self.assertNotEqual(pack["NEXT_SAFE_ACTION"], advisory)  # raw reconciliation never overrides
            self.assertEqual(RemoteEntry(self.storage).enter(TASK)["ENTRY_STATE"], "RECOVERY_AUTHORITY_READY")
        return projection

    def test_without_resolution_advisory_reconciliation_leads(self):
        self.started_operation(at=BEFORE)
        advisory = ReconciliationService(self.storage).reconcile(TASK, "m1", "op_1")["NEXT_SAFE_ACTION"]
        self.assert_authority("reconciliation", "RECONCILIATION_REQUIRED", advisory)

    def test_fresh_accepted_retry_adopt_abort_outrank_reconciliation(self):  # I, J, K
        for action, at in (("RETRY", BEFORE), ("ADOPT", AFTER), ("ABORT", AFTER)):
            with self.subTest(action=action):
                self.setUp_fresh()
                self.started_operation(at=at)
                resolution = self.resolve(action)
                self.assert_authority("resolver", f"{action}_ACCEPTED", resolution.next_safe_action)

    def setUp_fresh(self):
        self.tearDown()
        self.setUp()

    def test_tracked_rollback_session_outranks_its_request(self):  # L
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        self.assert_authority("resolver", "ROLLBACK_ACCEPTED", resolution.next_safe_action)
        rollbacks = RollbackService(self.storage)
        record = rollbacks.prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]
        self.assert_authority("rollback", "ROLLBACK_PRESERVED", record["next_safe_action"])

        applied = rollbacks.apply(TASK, record["rollback_id"])["rollback"]
        projection = self.assert_authority("rollback", "ROLLBACK_VERIFIED", applied["next_safe_action"])

        session = projection["rollbacks"][0]
        self.assertEqual((session["facts_source"], session["current_physical_state_asserted"]), ("rollback_receipt", False))
        self.assertEqual(session["facts_as_of"], applied["result"]["at"])
        self.assertEqual(session["verified_at"], applied["result"]["final_verification"]["at"])

    def test_stale_accepted_resolution_is_never_authority(self):  # M
        self.started_operation(at=AFTER)
        adopt = self.resolve("ADOPT")
        self.write("target.txt", b"moved on\n")  # the adopted evidence no longer holds

        projection = self.projection.build(TASK)

        self.assertEqual((projection["authority_source"], projection["recovery"]["state"]),
                         ("resolver_stale", "RESOLUTION_STALE"))
        self.assertNotEqual(projection["next_safe_action"], adopt.next_safe_action)
        self.assertIn("run a new reconciliation", projection["next_safe_action"])

    def test_recovery_report_never_outranks_a_newer_resolution(self):  # adversarial
        self.started_operation(at=AFTER)
        report = RecoveryReportService(self.storage).create_report(
            task_id=TASK, microtask_id="m1", operation_id="op_1", incident_id="before_adopt")
        adopt = self.resolve("ADOPT")

        pack = EntryContextPackBuilder(self.storage).build(TASK)

        self.assertEqual(pack["LATEST_RECOVERY_REPORT"]["report_id"], report.report_id)  # evidence only
        self.assertEqual(pack["NEXT_SAFE_ACTION"], adopt.next_safe_action)

    def test_rollback_facts_are_historical_after_a_later_legitimate_writer(self):  # N
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        rollbacks = RollbackService(self.storage)
        record = rollbacks.prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]
        rollbacks.apply(TASK, record["rollback_id"])
        self.ops.begin("task_other", "m1", "write", "target.txt", operation_id="op_later", payload=b"later\n")
        claims = TargetClaimService(self.storage)
        claims.acquire("task_other", "op_later", operation_revision=1)
        with claims.mutation_boundary("task_other", "op_later", operation_revision=1) as gate:
            self.assertTrue(gate["mutation_authority"])
            self.write("target.txt", b"later\n")  # legitimate RC-3 writer after the rollback

        session = self.projection.build(TASK)["rollbacks"][0]
        report = RecoveryReportService(self.storage).create_report(
            task_id=TASK, microtask_id="m1", operation_id="op_1", incident_id="after_writer")

        self.assertEqual(session["restored"], ["target.txt"])  # a fact as of facts_as_of ...
        self.assertFalse(session["current_physical_state_asserted"])  # ... never current proof
        self.assertIsNotNone(session["facts_as_of"])
        self.assertEqual((self.project / "target.txt").read_bytes(), b"later\n")
        self.assertFalse(report.rollback_receipts[0]["current_physical_state_asserted"])
        self.assertEqual(report.rollback_receipts[0]["facts_source"], "rollback_receipt")


class AdversarialRepairTests(ProjectionFixture):
    """Defects found in the RC-5 adversarial pass (fixed inside scope)."""

    def test_unfinished_rollback_outranks_a_newer_reconciliation(self):
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        record = RollbackService(self.storage).prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]
        self.write("two.txt", BEFORE)
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_newer", payload=AFTER)
        self.ops.transition(TASK, "op_newer", "STARTED")  # newer activity on another operation

        projection = self.projection.build(TASK)

        self.assertEqual(projection["recovery"]["attention"], ["op_1", "op_newer"])
        self.assertEqual((projection["recovery"]["operation_id"], projection["authority_source"]), ("op_1", "rollback"))
        self.assertEqual(projection["next_safe_action"], record["next_safe_action"])

    def test_projection_failure_never_undoes_a_persisted_workflow_mutation(self):
        self.write("one.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m1", [("one.txt", "edit")])
        self.assertEqual(self.projection.validate_checkpoint(TASK)["status"], "VALID")
        broken = mock.patch.object(ProjectionService, "build", side_effect=RuntimeError("projection store down"))

        with broken:
            result = self.machine.transition(TASK, "m1", "READY")
            begun = self.ops.begin(TASK, "m1", "write", "one.txt", operation_id="op_q", payload=AFTER)

        self.assertIsNone(result["checkpoint"])
        self.assertIn("projection store down", result["checkpoint_error"])
        self.assertIn("rebuild the checkpoint", result["next_safe_action"])
        self.assertEqual(self.tasks.open_microtask(TASK, "m1").status, MicrotaskStatus.READY)  # state first
        self.assertTrue(begun["created"])  # the operation is persistent although the projection failed
        self.assertEqual(self.projection.validate_checkpoint(TASK)["status"], "STALE")
        self.assertEqual(self.projection.rebuild_checkpoint(TASK)["validation"]["status"], "VALID")


class CloseoutTests(ProjectionFixture):
    def clean_task(self):
        self.verify_microtask("m1", "one.txt")
        self.verify_microtask("m2", "two.txt")

    def blockers(self):
        return [b["code"] for b in CloseoutService(self.storage).inspect(TASK)["blockers"]]

    def test_closeout_inspection_is_pure(self):  # O
        self.started_operation(at=AFTER)
        before = self.digest()
        verdict = CloseoutService(self.storage).inspect(TASK)
        self.assertEqual(self.digest(), before)
        self.assertFalse(verdict["eligible"])
        self.assertFalse(verdict["workflow_mutation_performed"])

    def test_closeout_blocks_unverified_microtask_and_open_operations(self):  # P, Q
        self.verify_microtask("m1", "one.txt")
        self.assertIn("MICROTASK_NOT_VERIFIED", self.blockers())
        self.write("two.txt", BEFORE)
        self.machine.prepare_microtask(TASK, "m2", [("two.txt", "edit")])
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_open", payload=AFTER)
        self.assertIn("OPERATION_OPEN", self.blockers())
        self.ops.transition(TASK, "op_open", "STARTED")
        self.assertIn("OPERATION_UNRESOLVED", self.blockers())
        for status in ("READY", "ACTIVE", "DONE"):
            self.machine.transition(TASK, "m2", status)
        self.machine.transition(TASK, "m2", "VERIFIED", verification_evidence="ok")
        self.write("two.txt", AFTER)  # DONE needs the server-observed expected post-state
        self.ops.transition(TASK, "op_open", "DONE")
        self.assertEqual(self.blockers(), ["OPERATION_NOT_VERIFIED"])
        self.ops.transition(TASK, "op_open", "VERIFIED")
        self.assertEqual(self.blockers(), [])

    def test_closeout_blocks_an_active_target_claim(self):  # R
        self.clean_task()
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_c", payload=AFTER)
        TargetClaimService(self.storage).acquire(TASK, "op_c", operation_revision=1)
        self.ops.transition(TASK, "op_c", "STARTED")
        self.write("two.txt", AFTER)
        self.ops.transition(TASK, "op_c", "DONE")
        self.ops.transition(TASK, "op_c", "VERIFIED")  # the claim outlives the operation lifecycle
        self.assertEqual(self.blockers(), ["ACTIVE_CLAIM"])

    def test_closeout_blocks_open_rollback_and_pending_release(self):  # S, T
        self.started_operation(at=AFTER, kind="mixed")
        resolution = self.resolve("ROLLBACK")
        self.assertIn("ROLLBACK_PENDING", self.blockers())
        rollbacks = RollbackService(self.storage)
        record = rollbacks.prepare(TASK, "m1", "op_1", resolution.resolution_id)["rollback"]
        self.assertIn("ROLLBACK_OPEN", self.blockers())
        with mock.patch.object(rs.RollbackService, "_release_claims", side_effect=rs.TargetClaimStoreError("io")):
            rollbacks.apply(TASK, record["rollback_id"])
        blockers = self.blockers()
        self.assertIn("ROLLBACK_RELEASE_PENDING", blockers)
        self.assertIn("ACTIVE_CLAIM", blockers)
        rollbacks.apply(TASK, record["rollback_id"])  # finishes the release
        self.assertNotIn("ROLLBACK_RELEASE_PENDING", self.blockers())
        verdict = CloseoutService(self.storage).inspect(TASK)
        unresolved = next(b for b in verdict["blockers"] if b["code"] == "OPERATION_UNRESOLVED")
        self.assertIn("accepted ABORT", unresolved["next"])  # post-rollback op lifecycle stays explicit

    def test_closeout_blocks_a_fresh_retry(self):
        self.started_operation(at=BEFORE)
        self.resolve("RETRY")
        self.assertIn("RETRY_PENDING", self.blockers())

    def test_public_completion_cannot_bypass_the_gate(self):  # U
        self.verify_microtask("m1", "one.txt")
        before = self.digest()
        outcome = CloseoutService(self.storage).complete(TASK)
        with self.assertRaises(ApiError) as caught:
            self.api.dispatch("POST", f"/tasks/{TASK}/complete", {})
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(["--storage-root", str(self.storage), "task", "complete", "--task-id", TASK])

        self.assertEqual((outcome["result"], caught.exception.code, code), ("REJECTED", "closeout_rejected", 3))
        after = self.digest()
        self.assertEqual({k: v for k, v in after["storage"].items() if not k.startswith("locks")},
                         {k: v for k, v in before["storage"].items() if not k.startswith("locks")})
        self.assertTrue((self.storage / "tasks" / "active" / TASK).is_dir())

    def test_clean_task_completes_through_the_gate(self):  # V
        self.clean_task()
        self.assertEqual(self.blockers(), [])

        status, payload = self.api.dispatch("POST", f"/tasks/{TASK}/complete", {})

        self.assertEqual((status, payload["result"]), (200, "COMPLETED"))
        self.assertTrue((self.storage / "tasks" / "completed" / TASK).is_dir())
        self.assertFalse((self.storage / "tasks" / "active" / TASK).exists())
        events = EventCheckpointStore(self.storage).read_events(TASK)
        self.assertEqual(events[-1].event_type, "TASK_COMPLETED")
        with self.assertRaises(TaskStoreError):  # a completed TASK admits no new operation
            self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_late", payload=AFTER)
        replay = CloseoutService(self.storage).complete(TASK)
        self.assertEqual(replay["result"], "REJECTED")
        self.assertIn("TASK_NOT_ACTIVE", [b["code"] for b in replay["closeout"]["blockers"]])

    def test_aborted_operation_no_longer_blocks(self):  # conservative ABORT rule
        self.clean_task()
        self.ops.begin(TASK, "m2", "write", "two.txt", operation_id="op_1", payload=AFTER)
        self.ops.transition(TASK, "op_1", "STARTED")
        self.assertIn("OPERATION_UNRESOLVED", self.blockers())
        decision = ReconciliationService(self.storage).reconcile(TASK, "m2", "op_1")["DECISION"]
        aborted = ResolverService(self.storage).apply(
            TASK, "m2", "op_1", "ABORT", evidence_fingerprint=decision["evidence_fingerprint"],
            operation_revision=self.ops.get(TASK, "op_1").revision)
        self.assertTrue(aborted["accepted"])
        self.assertEqual(self.blockers(), [])


class ProjectionServerTests(ProjectionFixture):
    def test_projection_checkpoint_and_rebuild_endpoints(self):
        self.verify_microtask("m1", "one.txt")
        status, view = self.api.dispatch("GET", f"/tasks/{TASK}/checkpoint")
        self.assertEqual(view["validation"]["status"], "VALID")  # the state machine rebuilt it
        (self.task_dir() / "checkpoint.json").unlink()
        status, view = self.api.dispatch("GET", f"/tasks/{TASK}/checkpoint")
        self.assertEqual((view["checkpoint"], view["validation"]["status"]), (None, "MISSING"))
        status, rebuilt = self.api.dispatch("POST", f"/tasks/{TASK}/checkpoint/rebuild", {})
        self.assertEqual((status, rebuilt["validation"]["status"]), (200, "VALID"))
        status, projection = self.api.dispatch("GET", f"/tasks/{TASK}/projection")
        self.assertEqual(projection["projection"]["source_fingerprint"],
                         rebuilt["validation"]["current_source_fingerprint"])
        status, info = self.api.dispatch("GET", "/status")
        self.assertTrue({"projection", "closeout"} <= set(info["capabilities"]))


if __name__ == "__main__":
    unittest.main()
