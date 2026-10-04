import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from web_alarm.manifest_store import ManifestSnapshotStore
from web_alarm.models import record_to_dict
from web_alarm.operation_contract import assess, fingerprint_v1
from web_alarm.operation_store import (
    OperationConflictError,
    OperationContractRejected,
    OperationPayloadIntegrityError,
    OperationReceiptMismatch,
    OperationScopeRejected,
    OperationStore,
    OperationStoreError,
)
from web_alarm.reconciliation_service import ReconciliationService
from web_alarm.server import ApiError, WebAlarmApi
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry

REPO_ROOT = Path(__file__).resolve().parent
WINDOWS = os.name == "nt"

# Byte-identical copies of the two live legacy records of completed TASK WA-3.7
# (machine-local storage, 2026-10-04). Their SHA-256 pins the fixture to them.
LEGACY_RECORDS = {
    "WA37-CTRL-001": (
        "083bdf8fb2d3c74ee1bb22b7829c9074411734d7c5b9247a356b6e554e386096",
        '{\n'
        '  "operation_id": "WA37-CTRL-001",\n'
        '  "task_id": "WA-3.7",\n'
        '  "microtask_id": "WA37-M002",\n'
        '  "action": "create_file",\n'
        '  "target": "Alarm/ALARM_TASK_SESSION/TASK_WA-3.7/controlled_disconnect_target.txt",\n'
        '  "status": "VERIFIED",\n'
        '  "request_fingerprint": "286db8c7a19ebc781de00cd9e6a533992936afb2c9c93ec3b071c83cd2991a96",\n'
        '  "expected_precondition_sha256": null,\n'
        '  "result_summary": "FULL mutation proven; no disconnect; attempt retained as non-acceptance evidence.",\n'
        '  "schema_version": 1,\n'
        '  "created_at": "2026-10-02T19:00:39.847084+00:00",\n'
        '  "updated_at": "2026-10-02T19:07:53.495844+00:00"\n'
        '}\n',
    ),
    "WA37-CTRL-002": (
        "319ca763f0367ffa72fc93ddbb9defa7a644558b350b075d26b3d995d6b4f489",
        '{\n'
        '  "operation_id": "WA37-CTRL-002",\n'
        '  "task_id": "WA-3.7",\n'
        '  "microtask_id": "WA37-M002",\n'
        '  "action": "create_file",\n'
        '  "target": "Alarm/ALARM_TASK_SESSION/TASK_WA-3.7/controlled_disconnect_target.txt",\n'
        '  "status": "FAILED",\n'
        '  "request_fingerprint": "286db8c7a19ebc781de00cd9e6a533992936afb2c9c93ec3b071c83cd2991a96",\n'
        '  "expected_precondition_sha256": null,\n'
        '  "result_summary": "Controlled disconnect acceptance: exact PRE_STATE proven after reconnect; side effect none; RETRY_SAFE decision recorded; retry intentionally not performed.",\n'
        '  "schema_version": 1,\n'
        '  "created_at": "2026-10-02T19:08:27.465557+00:00",\n'
        '  "updated_at": "2026-10-02T19:21:08.792541+00:00"\n'
        '}\n',
    ),
}
LEGACY_KEYS = set(json.loads(LEGACY_RECORDS["WA37-CTRL-001"][1]))

FRESH_READ = r"""
import hashlib, json, sys
from web_alarm.models import record_to_dict
from web_alarm.operation_store import OperationStore
storage, task_id = sys.argv[1:3]
store = OperationStore(storage)
out = {}
for operation_id in sys.argv[3:]:
    record = store.get(task_id, operation_id)
    item = {
        "record": record_to_dict(record),
        "contract_status": store.contract_status(task_id, operation_id),
    }
    if (record.contract or {}).get("payload_ref"):
        item["payload_sha256"] = hashlib.sha256(
            store.read_payload(task_id, operation_id)
        ).hexdigest()
    out[operation_id] = item
print(json.dumps(out))
"""

FRESH_RECONCILE = r"""
import json, sys
from web_alarm.reconciliation_service import ReconciliationService
storage, task_id, microtask_id, operation_id = sys.argv[1:5]
result = ReconciliationService(storage).reconcile(task_id, microtask_id, operation_id)
print(json.dumps({
    "decision": result["DECISION"]["decision"],
    "errors": result["EVIDENCE"]["errors"],
    "targets": result["EVIDENCE"]["targets"],
    "mutation": result["MUTATION_PERFORMED"],
}))
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_fresh(script: str, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise AssertionError(f"fresh process failed:\n{completed.stderr}")
    return json.loads(completed.stdout)


class ContractFixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.before = b"before\n"
        self.marker = self.project / "marker.txt"
        self.marker.write_bytes(self.before)

        self.workspace = WorkspaceRegistry(self.storage).register(
            "Project", self.project, workspace_id="ws_contract"
        )
        self.tasks = TaskStore(self.storage)
        self.task = self.tasks.create_task(
            self.workspace.workspace_id,
            "Contract Task",
            "RAW TASK",
            "Durable operation contract",
            task_id="task_contract",
        )
        self.tasks.create_microtask("task_contract", "M1", "Contract step", microtask_id="m1")
        self.store = OperationStore(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    @property
    def task_dir(self) -> Path:
        return self.storage / "tasks" / "active" / "task_contract"

    def record_path(self, operation_id: str) -> Path:
        return self.task_dir / "operations" / f"{operation_id}.json"

    def payload_files(self) -> list[Path]:
        directory = self.task_dir / "payloads"
        return sorted(directory.glob("*.bin")) if directory.is_dir() else []

    def begin_write(self, operation_id="op_write", payload=b"after\n", **overrides):
        values = dict(
            operation_id=operation_id,
            payload=payload,
            agent="claude-test",
            channel="unit",
            request_payload={"mode": "full-replace"},
        )
        values.update(overrides)
        target = values.pop("target", "marker.txt")
        action = values.pop("action", "write")
        return self.store.begin("task_contract", "m1", action, target, **values)


class OperationContractTests(ContractFixture):
    def test_explicit_write_persists_self_contained_contract_without_mutation(self):
        result = self.begin_write()
        record = result["operation"]
        contract = record.contract

        self.assertTrue(result["created"])
        self.assertEqual(self.marker.read_bytes(), self.before)
        self.assertEqual(record.contract_version, 2)
        self.assertEqual(record.revision, 1)
        self.assertEqual(record.target, "marker.txt")
        self.assertEqual(contract["workspace_id"], "ws_contract")
        self.assertEqual(contract["mutation_kind"], "WRITE")
        self.assertEqual(
            {k: contract["pre_state"][k] for k in ("exists", "size", "sha256")},
            {"exists": True, "size": len(self.before), "sha256": sha256(self.before)},
        )
        self.assertEqual(contract["pre_state"]["source"], "server_observed_at_intent")
        self.assertEqual(contract["expected_post_state"]["sha256"], sha256(b"after\n"))
        self.assertEqual(contract["expected_post_state"]["source"], "payload")
        self.assertEqual(contract["payload_ref"]["sha256"], sha256(b"after\n"))
        self.assertEqual(contract["provenance"]["agent"], "claude-test")
        self.assertEqual(contract["provenance"]["authority"], "claimed")
        self.assertTrue(contract["complete"])
        self.assertTrue(result["contract_status"]["rearm_contract_sufficient"])

        # payload lives in machine-local storage, never in the workspace or events
        self.assertEqual([p.read_bytes() for p in self.payload_files()], [b"after\n"])
        self.assertEqual(sorted(p.name for p in self.project.iterdir()), ["marker.txt"])
        events = (self.task_dir / "events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("after\\n", events)
        self.assertNotIn("full-replace", events)
        self.assertIn('"contract_version":2', events)

    def test_fresh_process_reopens_same_contract_revision_and_payload(self):
        created = self.begin_write()["operation"]
        self.store.transition("task_contract", "op_write", "STARTED")

        fresh = run_fresh(FRESH_READ, str(self.storage), "task_contract", "op_write")
        item = fresh["op_write"]
        local = self.store.get("task_contract", "op_write")

        self.assertEqual(item["record"], record_to_dict(local))
        self.assertEqual(item["record"]["contract"], created.contract)
        self.assertEqual(item["record"]["revision"], 2)
        self.assertEqual(item["record"]["request_fingerprint"], created.request_fingerprint)
        self.assertEqual(item["payload_sha256"], sha256(b"after\n"))
        self.assertTrue(item["contract_status"]["payload_verified"])

    def test_target_spellings_replay_same_logical_operation(self):
        (self.project / "Sub").mkdir()
        (self.project / "Sub" / "Note.txt").write_bytes(self.before)
        first = self.begin_write(operation_id="op_spell", target="Sub/Note.txt")
        spellings = ["Sub\\Note.txt", "./Sub/Note.txt", str(self.project / "Sub" / "Note.txt")]
        if WINDOWS:
            spellings.append("sub/NOTE.TXT")

        for spelling in spellings:
            with self.subTest(spelling=spelling):
                replay = self.begin_write(operation_id="op_spell", target=spelling)
                self.assertFalse(replay["created"])
                self.assertTrue(replay["replayed"])
                self.assertEqual(
                    replay["operation"].request_fingerprint,
                    first["operation"].request_fingerprint,
                )
        self.assertEqual(len(self.store.list("task_contract")), 1)

    def test_duplicate_operation_id_with_different_payload_fails_closed(self):
        self.begin_write()
        before_record = self.record_path("op_write").read_bytes()

        with self.assertRaises(OperationConflictError):
            self.begin_write(payload=b"different\n")
        with self.assertRaises(OperationConflictError):
            self.begin_write(request_payload={"mode": "other"})

        self.assertEqual(self.record_path("op_write").read_bytes(), before_record)
        self.assertEqual([p.read_bytes() for p in self.payload_files()], [b"after\n"])

    def test_old_style_request_is_v2_but_incomplete_and_not_rearm_sufficient(self):
        result = self.store.begin(
            "task_contract",
            "m1",
            "write",
            "marker.txt",
            operation_id="op_old",
            expected_precondition_sha256="0" * 64,
            request_payload={"content": "after"},
        )
        status = result["contract_status"]

        self.assertEqual(result["operation"].contract_version, 2)
        self.assertFalse(status["complete"])
        self.assertFalse(status["rearm_contract_sufficient"])
        self.assertEqual(
            status["issues"],
            [
                "declared_precondition_sha256_mismatch",
                "expected_post_state_missing",
                "payload_missing",
            ],
        )
        self.assertEqual(self.payload_files(), [])

    def test_contract_inconsistencies_are_rejected_before_any_write(self):
        cases = {
            "create_existing": dict(action="create_file"),
            "delete_absent": dict(action="delete", target="absent.txt", payload=None,
                                  expected_post_state={"exists": False}),
            "delete_with_payload": dict(action="delete"),
            "post_contradicts_payload": dict(
                expected_post_state={"exists": True, "size": 1, "sha256": "0" * 64}
            ),
            "declared_pre_mismatch": dict(
                expected_pre_state={"exists": True, "size": 1, "sha256": "0" * 64}
            ),
            "invalid_post_shape": dict(expected_post_state={"exists": True, "sha256": "x"}),
            "unknown_state_field": dict(expected_pre_state={"exists": False, "mtime": 1}),
        }
        for name, overrides in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(OperationContractRejected):
                    self.begin_write(operation_id=f"op_{name}", **overrides)
                self.assertFalse(self.record_path(f"op_{name}").exists())
        self.assertEqual(self.payload_files(), [])
        self.assertEqual(self.marker.read_bytes(), self.before)

    def test_secret_target_requires_explicit_recorded_override(self):
        (self.project / "config").mkdir()
        for target in (".env", "config/api_token.txt", "deploy.pem"):
            with self.subTest(target=target):
                with self.assertRaises(OperationScopeRejected):
                    self.begin_write(operation_id="op_secret", target=target, action="create_file")
        self.assertFalse(self.record_path("op_secret").exists())

        allowed = self.begin_write(
            operation_id="op_secret",
            target=".env",
            action="create_file",
            allow_secret_target=True,
        )["operation"]
        self.assertEqual(
            allowed.contract["policy"]["secret_pattern"], ".env*"
        )
        self.assertTrue(allowed.contract["policy"]["secret_override"])
        before_record = self.record_path("op_secret").read_bytes()
        with self.assertRaises(OperationScopeRejected):
            # the scope gate runs for every request, replays included
            self.store.begin(
                "task_contract", "m1", "create_file", ".env",
                operation_id="op_secret", payload=b"after\n",
                agent="claude-test", channel="unit",
                request_payload={"mode": "full-replace"},
                allow_secret_target=False,
            )
        self.assertEqual(self.record_path("op_secret").read_bytes(), before_record)

    def test_payload_size_limit_and_storage_inside_workspace_fail_closed(self):
        small = OperationStore(self.storage, max_payload_bytes=4)
        with self.assertRaises(OperationScopeRejected):
            small.begin("task_contract", "m1", "write", "marker.txt",
                        operation_id="op_big", payload=b"12345")
        self.assertFalse(self.record_path("op_big").exists())

        inner_storage = self.project / "state_inside"
        WorkspaceRegistry(inner_storage).register(
            "Inner", self.project, workspace_id="ws_contract"
        )
        inner_tasks = TaskStore(inner_storage)
        inner_tasks.create_task("ws_contract", "Inner", "RAW", "Goal", task_id="task_inner")
        inner_tasks.create_microtask("task_inner", "M1", "Step", microtask_id="m1")
        with self.assertRaises(OperationScopeRejected):
            OperationStore(inner_storage).begin(
                "task_inner", "m1", "write", "marker.txt",
                operation_id="op_inside", payload=b"after\n",
            )
        self.assertFalse(
            (inner_storage / "tasks" / "active" / "task_inner" / "operations"
             / "op_inside.json").exists()
        )

    def test_corrupted_or_missing_payload_fails_closed(self):
        self.begin_write()
        blob = self.payload_files()[0]

        blob.write_bytes(b"AFTER\n")
        with self.assertRaises(OperationPayloadIntegrityError):
            self.store.read_payload("task_contract", "op_write")
        status = self.store.contract_status("task_contract", "op_write")
        self.assertFalse(status["payload_verified"])
        self.assertFalse(status["rearm_contract_sufficient"])
        self.assertIn("payload_integrity_failure", status["issues"])
        with self.assertRaises(OperationPayloadIntegrityError):
            # a new operation must not silently reuse or overwrite a bad blob
            self.begin_write(operation_id="op_reuse")

        blob.unlink()
        with self.assertRaises(OperationPayloadIntegrityError):
            self.store.read_payload("task_contract", "op_write")

    def test_unknown_or_corrupted_contract_version_fails_closed(self):
        self.begin_write()
        path = self.record_path("op_write")
        original = json.loads(path.read_text(encoding="utf-8"))

        def corrupt(mutator):
            data = json.loads(json.dumps(original))
            mutator(data)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        mutations = {
            "future_version": lambda d: d.update(contract_version=3),
            "bool_version": lambda d: d.update(contract_version=True),
            "missing_contract": lambda d: d.update(contract=None),
            "extra_contract_field": lambda d: d["contract"].update(guess=True),
            "target_key_drift": lambda d: d["contract"].update(target_key="other.txt"),
            "complete_contradicts_issues": lambda d: d["contract"].update(issues=["x"]),
            "bad_pre_hash": lambda d: d["contract"]["pre_state"].update(sha256="zz"),
            "zero_revision": lambda d: d.update(revision=0),
            "unknown_top_field": lambda d: d.update(lease_owner="x"),
            "legacy_with_v2_fields": lambda d: d.update(contract_version=1),
            "payload_ref_mismatch": lambda d: d["contract"]["payload_ref"].update(size=1),
        }
        for name, mutator in mutations.items():
            with self.subTest(case=name):
                corrupt(mutator)
                with self.assertRaises(OperationStoreError):
                    self.store.get("task_contract", "op_write")
                with self.assertRaises(OperationStoreError):
                    self.store.transition("task_contract", "op_write", "STARTED")

    def test_done_receipt_is_server_observed_and_revision_advances(self):
        self.begin_write()
        self.store.transition("task_contract", "op_write", "STARTED")
        self.marker.write_bytes(b"after\n")  # the external writer performs the mutation

        done = self.store.transition("task_contract", "op_write", "DONE")["operation"]
        verified = self.store.transition("task_contract", "op_write", "VERIFIED")["operation"]

        self.assertEqual(done.revision, 3)
        self.assertEqual(done.receipt["source"], "server_observed_at_done")
        self.assertEqual(done.receipt["sha256"], sha256(b"after\n"))
        self.assertTrue(done.receipt["matches_expected_post"])
        self.assertEqual(done.receipt["revision"], 3)
        self.assertEqual(verified.revision, 4)
        self.assertEqual(verified.receipt, done.receipt)
        replay = self.store.transition("task_contract", "op_write", "VERIFIED")
        self.assertFalse(replay["changed"])
        self.assertEqual(replay["operation"].revision, 4)

    def test_done_is_refused_when_target_bytes_contradict_contract(self):
        self.begin_write(payload=b"a\nb\n")
        self.store.transition("task_contract", "op_write", "STARTED")
        self.marker.write_bytes(b"a\r\nb\r\n")

        with self.assertRaises(OperationReceiptMismatch) as caught:
            self.store.transition("task_contract", "op_write", "DONE")

        self.assertIn("EOL_ONLY_DRIFT", str(caught.exception))
        record = self.store.get("task_contract", "op_write")
        self.assertEqual(record.status.value, "STARTED")
        self.assertEqual(record.revision, 2)
        self.assertIsNone(record.receipt)
        events = [
            json.loads(line)
            for line in (self.task_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        mismatch = [e for e in events if e["event_type"] == "OPERATION_RECEIPT_MISMATCH"]
        self.assertEqual(len(mismatch), 1)
        self.assertTrue(mismatch[0]["payload"]["eol_only_drift"])

    def test_old_style_done_records_receipt_without_expectation(self):
        self.store.begin("task_contract", "m1", "write", "marker.txt", operation_id="op_old")
        self.store.transition("task_contract", "op_old", "STARTED")
        self.marker.write_bytes(b"anything\n")

        done = self.store.transition("task_contract", "op_old", "DONE")["operation"]

        self.assertIsNone(done.receipt["matches_expected_post"])
        self.assertEqual(done.receipt["sha256"], sha256(b"anything\n"))

    def test_fresh_reconciliation_uses_persisted_post_without_caller_input(self):
        ManifestSnapshotStore(self.storage).prepare_microtask(
            "task_contract", "m1", [("marker.txt", "edit")]
        )
        self.begin_write()
        self.store.transition("task_contract", "op_write", "STARTED")

        not_reached = run_fresh(
            FRESH_RECONCILE, str(self.storage), "task_contract", "m1", "op_write"
        )
        self.marker.write_bytes(b"after\n")
        reached = run_fresh(
            FRESH_RECONCILE, str(self.storage), "task_contract", "m1", "op_write"
        )

        self.assertEqual(not_reached["decision"], "RETRY_SAFE")
        self.assertEqual(reached["decision"], "ADOPT_CURRENT_STATE")
        for result in (not_reached, reached):
            self.assertEqual(result["errors"], [])
            self.assertFalse(result["mutation"])
            self.assertEqual(result["targets"][0]["expected_post_source"], "operation.contract")
        self.assertEqual(self.marker.read_bytes(), b"after\n")

    def test_supplied_post_contradicting_contract_requires_manual_review(self):
        ManifestSnapshotStore(self.storage).prepare_microtask(
            "task_contract", "m1", [("marker.txt", "edit")]
        )
        self.begin_write()
        self.store.transition("task_contract", "op_write", "STARTED")
        self.marker.write_bytes(b"other\n")

        result = ReconciliationService(self.storage).reconcile(
            "task_contract",
            "m1",
            "op_write",
            expected_post_state={"marker.txt": {"exists": True, "sha256": sha256(b"other\n")}},
        )

        self.assertEqual(result["DECISION"]["decision"], "MANUAL_REVIEW_REQUIRED")
        self.assertTrue(
            any("contradicts operation contract" in e for e in result["EVIDENCE"]["errors"])
        )

    def test_server_accepts_contract_fields_and_reports_status(self):
        api = WebAlarmApi(self.storage)
        body = {
            "microtask_id": "m1",
            "action": "write",
            "target": "marker.txt",
            "operation_id": "op_api",
            "payload": {"encoding": "utf-8", "data": "after\n"},
            "agent": "chatgpt",
            "channel": "desktop-commander",
        }

        status, created = api.dispatch("POST", "/tasks/task_contract/operations", body)
        self.assertEqual(status, 201)
        self.assertTrue(created["contract_status"]["complete"])
        status, inspected = api.dispatch("GET", "/tasks/task_contract/operations/op_api")
        self.assertEqual(status, 200)
        self.assertEqual(inspected["operation"]["contract_version"], 2)
        self.assertTrue(inspected["contract_status"]["payload_verified"])
        self.assertEqual(self.marker.read_bytes(), self.before)

        with self.assertRaises(ApiError) as secret:
            api.dispatch("POST", "/tasks/task_contract/operations",
                         dict(body, operation_id="op_s", target=".env", action="create_file"))
        self.assertEqual(secret.exception.status, 403)
        with self.assertRaises(ApiError) as bad_payload:
            api.dispatch("POST", "/tasks/task_contract/operations",
                         dict(body, operation_id="op_b",
                              payload={"encoding": "base64", "data": "%%%"}))
        self.assertEqual(bad_payload.exception.status, 400)
        with self.assertRaises(ApiError) as rejected:
            api.dispatch("POST", "/tasks/task_contract/operations",
                         dict(body, operation_id="op_c", action="create_file"))
        self.assertEqual(rejected.exception.status, 400)
        self.assertEqual(rejected.exception.code, "operation_contract_rejected")


class LegacyOperationCompatibilityTests(ContractFixture):
    def install_legacy_task(self):
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_contract", "WA-3.7", "RAW", "Legacy", task_id="WA-3.7")
        tasks.create_microtask("WA-3.7", "M2", "Legacy step", microtask_id="WA37-M002")
        operations = self.storage / "tasks" / "active" / "WA-3.7" / "operations"
        operations.mkdir()
        for operation_id, (digest, text) in LEGACY_RECORDS.items():
            raw = text.encode("utf-8")
            self.assertEqual(sha256(raw), digest)
            (operations / f"{operation_id}.json").write_bytes(raw)
        tasks.complete_task("WA-3.7")
        return self.storage / "tasks" / "completed" / "WA-3.7" / "operations"

    def test_frozen_wa37_records_read_safely_without_rewrite(self):
        operations = self.install_legacy_task()

        records = self.store.list("WA-3.7")
        fresh = run_fresh(FRESH_READ, str(self.storage), "WA-3.7", *LEGACY_RECORDS)

        self.assertEqual([r.status.value for r in records], ["VERIFIED", "FAILED"])
        for record in records:
            self.assertEqual(record.contract_version, 1)
            self.assertIsNone(record.contract)
            status = self.store.contract_status("WA-3.7", record.operation_id)
            self.assertTrue(status["legacy"])
            self.assertFalse(status["rearm_contract_sufficient"])
            self.assertEqual(status["issues"], ["legacy_contract_v1"])
            self.assertEqual(
                fresh[record.operation_id]["record"]["status"], record.status.value
            )
            self.assertFalse(fresh[record.operation_id]["contract_status"]["complete"])
            self.assertEqual(
                self.store.replay_decision(record.status), "RETURN_KNOWN_STATE"
            )
        for operation_id, (digest, _) in LEGACY_RECORDS.items():
            self.assertEqual(sha256((operations / f"{operation_id}.json").read_bytes()), digest)

    def test_legacy_fingerprint_algorithm_is_unchanged(self):
        # Golden value computed with the WA-3.2 implementation at HEAD 8029a69.
        self.assertEqual(
            fingerprint_v1(
                task_id="task_ops",
                microtask_id="m1",
                action="write",
                target="marker.txt",
                expected_precondition_sha256="abc123",
                request_payload={"content": "after", "mode": "rewrite"},
            ),
            "a0eea63a91d7a73a36cd212226acd87570e75963bffd4a3bbc72cfd17682b39e",
        )

    def test_legacy_record_in_active_task_replays_and_keeps_legacy_shape(self):
        fingerprint = fingerprint_v1(
            task_id="task_contract",
            microtask_id="m1",
            action="write",
            target="marker.txt",
            expected_precondition_sha256=None,
            request_payload={"content": "after"},
        )
        legacy = {
            "operation_id": "op_legacy",
            "task_id": "task_contract",
            "microtask_id": "m1",
            "action": "write",
            "target": "marker.txt",
            "status": "INTENT",
            "request_fingerprint": fingerprint,
            "expected_precondition_sha256": None,
            "result_summary": None,
            "schema_version": 1,
            "created_at": "2026-10-02T19:00:00+00:00",
            "updated_at": "2026-10-02T19:00:00+00:00",
        }
        path = self.record_path("op_legacy")
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")

        replay = self.store.begin(
            "task_contract", "m1", "write", "marker.txt",
            operation_id="op_legacy", request_payload={"content": "after"},
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["contract_status"]["issues"], ["legacy_contract_v1"])
        with self.assertRaises(OperationConflictError):
            # a legacy record cannot be upgraded by replaying it with a payload
            self.store.begin(
                "task_contract", "m1", "write", "marker.txt",
                operation_id="op_legacy", request_payload={"content": "after"},
                payload=b"after",
            )

        self.store.transition("task_contract", "op_legacy", "STARTED")
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(stored), LEGACY_KEYS)
        self.assertEqual(stored["status"], "STARTED")
        self.assertFalse(assess(self.store.get("task_contract", "op_legacy"))["rearm_contract_sufficient"])


if __name__ == "__main__":
    unittest.main()
