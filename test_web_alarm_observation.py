"""WA4-R OBSERVE acceptance + explicit demonstrations of unclosed bypasses.

All mutations, including deliberately unprotected ones, affect disposable
fixtures only. Observation itself must leave both project and storage intact.
"""
import contextlib
import hashlib
import json
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from wa4a_acceptance import AFTER, BEFORE, TASK, DisposableWorkspace, request
from web_alarm.cli import main as cli_main
from web_alarm.file_state import authority_of
from web_alarm.server import ApiError, WebAlarmApi, create_server


def inventory(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
            for p in root.rglob("*")}


class Harness(DisposableWorkspace):
    """Independent disposable baseline, without inherited unittest methods."""
    manifest = [("a.txt", "edit"), ("new.txt", "create"), ("src.txt", "move"), ("dst.txt", "move")]

    def __enter__(self):
        self.cleanups = contextlib.ExitStack()
        self.addCleanup = self.cleanups.callback
        self.setUp()
        self.api = WebAlarmApi(self.storage)
        return self

    def __exit__(self, *args):
        self.cleanups.close()


class ObservationTests(DisposableWorkspace, unittest.TestCase):
    manifest = [("a.txt", "edit"), ("new.txt", "create"), ("src.txt", "move"), ("dst.txt", "move")]

    def setUp(self):
        super().setUp()
        self.api = WebAlarmApi(self.storage)

    def observe(self, api=None):
        status, result = (api or self.api).dispatch("GET", f"/tasks/{TASK}/observe")
        self.assertEqual(status, 200)
        self.assertFalse(result["mutation_authority"])
        self.assertFalse(result["enforcement_enabled"])
        self.assertFalse(result["workflow_mutation_performed"])
        return result

    def target(self, result, name="a.txt"):
        return next(t for t in result["state_observation"]["targets"] if t["source_path"] == name)

    def execute(self, body=None):
        return self.api.dispatch("POST", f"/tasks/{TASK}/mutations", body or request())[1]

    def test_pure_observation_no_new_files_or_authority_calls(self):
        before = inventory(self.base)
        with contextlib.ExitStack() as stack:
            for obj, method in [(self.api.executor, "execute"), (self.api.recovery, "recover"),
                                (self.api.rollbacks, "apply"), (self.api.resolver, "apply"),
                                (self.api.projection, "rebuild_checkpoint"), (self.api.state, "append_event"),
                                (self.api.tasks, "set_microtask_status"), (self.api.machine, "transition")]:
                stack.enter_context(mock.patch.object(obj, method, side_effect=AssertionError(method)))
            first = self.observe()
            second = self.observe()
        self.assertEqual(inventory(self.base), before)
        self.assertEqual(first, second)
        self.assertTrue(first["storage_evidence_coherent"])
        self.assertTrue(first["state_observation"]["complete"])
        self.assertFalse(self.target(first)["differs_from_snapshot"])
        self.assertFalse(first["diagnostics_persisted"])

    def test_gateway_receipt_historical_even_after_external_drift(self):
        self.observe()
        outcome = self.execute()
        diag = self.observe()
        row = diag["operation_history"][0]
        self.assertEqual(row["gateway_execution_evidence"], "CORRELATED_EXECUTOR_EVENT")
        self.assertEqual(row["status"], "DONE")
        self.assertEqual(row["receipt"], authority_of(outcome["receipt"]))
        self.assertEqual(row["receipt_scope"], "HISTORICAL_ONLY")
        self.assertFalse(row["current_post_state_proved"])
        self.assertTrue(self.target(diag)["differs_from_snapshot"])
        (self.project / "a.txt").write_bytes(b"external later\n")
        later = self.observe()
        self.assertEqual(later["operation_history"], diag["operation_history"])
        self.assertNotEqual(self.target(later)["observed_state"], row["receipt"])
        self.assertIsNone(self.target(later)["external_mutation_proved"])

    def test_replay_keeps_original_receipt_without_second_write(self):
        from web_alarm.mutation_executor import MutationExecutor
        original = MutationExecutor._apply
        with mock.patch.object(MutationExecutor, "_apply", wraps=original) as apply:
            first = self.execute()
            self.observe()
            replay = self.execute()
            self.observe()
        self.assertEqual(apply.call_count, 1)
        self.assertEqual(replay["result"], "REPLAYED")
        self.assertEqual(first["receipt"], replay["receipt"])

    def test_gateway_behavior_identical_with_and_without_observe_all_actions(self):
        for action in ("write", "edit", "create", "delete", "move", "rename"):
            with self.subTest(action=action), Harness() as baseline, Harness() as observed:
                target = "new.txt" if action == "create" else "src.txt" if action in ("move", "rename") else "a.txt"
                body = request(action=action, target=target)
                if action in ("move", "rename"):
                    body["destination"] = "dst.txt"
                self.observe(observed.api)
                left = baseline.api.dispatch("POST", f"/tasks/{TASK}/mutations", body)[1]
                right = observed.api.dispatch("POST", f"/tasks/{TASK}/mutations", body)[1]
                self.observe(observed.api)
                for key in ("result", "result_code", "physical_mutation_performed"):
                    self.assertEqual(left[key], right[key])
                self.assertEqual(inventory(baseline.project), inventory(observed.project))
                self.assertEqual([(r.status, authority_of(r.receipt)) for r in baseline.api.operations.list(TASK)],
                                 [(r.status, authority_of(r.receipt)) for r in observed.api.operations.list(TASK)])

    def test_no_mode_escalation_or_post_authority(self):
        before = inventory(self.base)
        for mode in ("WARN", "GATEWAY REQUIRED", "STRICT"):
            with self.subTest(mode=mode), self.assertRaises(ApiError) as error:
                self.api.dispatch("POST", f"/tasks/{TASK}/observe", {"mode": mode})
            self.assertEqual(error.exception.status, 405)
        for path, body in [(f"/tasks/{TASK}/observe?mode=STRICT", None),
                           (f"/tasks/{TASK}/observe", {"mutation_authority": True})]:
            with self.assertRaises(ApiError) as error:
                self.api.dispatch("GET", path, body)
            self.assertEqual(error.exception.status, 400)
        self.assertEqual(inventory(self.base), before)

    def test_direct_external_edit_visible_as_unattributed_state_only(self):
        (self.project / "a.txt").write_bytes(b"direct local writer")
        diag = self.observe()
        self.assertTrue(self.target(diag)["differs_from_snapshot"])
        self.assertEqual(self.target(diag)["attribution"], "NOT_ESTABLISHED")
        self.assertEqual(diag["operation_history"], [])
        self.assertIsNone(diag["coverage"]["external_events"])
        self.assertIsNone(diag["coverage"]["external_operation_count"])

    def test_external_create_delete_rename_and_eol_differences(self):
        (self.project / "new.txt").write_bytes(b"created")
        (self.project / "src.txt").rename(self.project / "dst.txt")
        (self.project / "a.txt").write_bytes(BEFORE.replace(b"\n", b"\r\n"))
        diag = self.observe()
        for name in ("new.txt", "src.txt", "dst.txt", "a.txt"):
            self.assertTrue(self.target(diag, name)["differs_from_snapshot"])
        self.assertIsNone(diag["coverage"]["external_operation_count"])

    def test_changes_outside_manifest_remain_unobservable(self):
        first = self.observe()
        (self.project / "outside.txt").write_bytes(b"uncontrolled")
        (self.project / "unregistered.txt").write_bytes(b"uncontrolled new")
        second = self.observe()
        self.assertEqual(first, second)
        self.assertFalse(second["coverage"]["outside_manifest_scanned"])
        self.assertFalse(second["coverage"]["absence_of_telemetry_proves_no_mutation"])

    def test_transient_external_change_restored_between_reads_is_missed(self):
        first = self.observe()
        (self.project / "a.txt").write_bytes(b"transient")
        (self.project / "a.txt").write_bytes(BEFORE)
        self.assertEqual(first, self.observe())
        self.assertTrue(first["coverage"]["transient_changes_may_be_missed"])

    def test_done_from_external_write_not_mislabelled_gateway(self):
        record = self.api.operations.begin(TASK, "m1", "write", "a.txt", operation_id="manual", payload=AFTER)["operation"]
        self.api.operations.transition(TASK, record.operation_id, "STARTED")
        (self.project / "a.txt").write_bytes(AFTER)
        self.api.operations.transition(TASK, record.operation_id, "DONE")
        row = self.observe()["operation_history"][0]
        self.assertEqual(row["status"], "DONE")
        self.assertEqual(row["gateway_execution_evidence"], "NOT_ESTABLISHED")
        self.assertIsNotNone(row["receipt"])

    def test_missing_executor_event_not_proof_of_no_write(self):
        original = self.api.executor.events.append_event
        def fail(task_id, event_type, **kwargs):
            if event_type == "MUTATION_EXECUTED":
                raise OSError("simulated final event failure after DONE")
            return original(task_id, event_type, **kwargs)
        with mock.patch.object(self.api.executor.events, "append_event", side_effect=fail):
            with self.assertRaises(OSError):
                self.execute()
        diag = self.observe()
        self.assertEqual((self.project / "a.txt").read_bytes(), AFTER)
        self.assertEqual(diag["operation_history"][0]["gateway_execution_evidence"], "NOT_ESTABLISHED")
        self.assertIsNone(diag["coverage"]["unobserved_operation_count"])

    def test_legacy_snapshot_restore_bypasses_rc4_and_is_not_attributed(self):
        (self.project / "a.txt").write_bytes(b"unknown bytes must normally be preserved")
        self.assertTrue(self.target(self.observe())["differs_from_snapshot"])
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli_main(["--storage-root", str(self.storage), "snapshot", "restore",
                             "--task-id", TASK, "--microtask-id", "m1"])
        self.assertEqual(code, 0)
        self.assertEqual((self.project / "a.txt").read_bytes(), BEFORE)
        diag = self.observe()
        self.assertFalse(self.target(diag)["differs_from_snapshot"])
        self.assertEqual(diag["operation_history"], [])
        self.assertEqual(self.api.rollbacks.store.list(TASK), [])

    def test_stale_physical_cas_still_refused(self):
        self.api.operations.begin(TASK, "m1", "write", "a.txt", operation_id="op_a", payload=AFTER)
        (self.project / "a.txt").write_bytes(b"drift")
        self.observe()
        with self.assertRaises(ApiError) as error:
            self.execute()
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(error.exception.details["result_code"], "PRECONDITION_FAILED")
        self.assertEqual((self.project / "a.txt").read_bytes(), b"drift")

    def test_target_outside_manifest_still_refused(self):
        self.observe()
        with self.assertRaises(ApiError) as error:
            self.execute(request(target="outside.txt"))
        self.assertEqual(error.exception.details["result_code"], "TARGET_NOT_IN_MANIFEST")
        self.assertEqual((self.project / "outside.txt").read_bytes(), b"outside\n")

    def test_observe_does_not_grant_active_to_planned_microtask(self):
        self.tasks.set_microtask_status(TASK, "m1", "PLANNED")
        before = inventory(self.base)
        self.observe()
        self.assertEqual(inventory(self.base), before)
        with self.assertRaises(ApiError) as error:
            self.execute()
        self.assertEqual(error.exception.status, 409)
        self.assertEqual((self.project / "a.txt").read_bytes(), BEFORE)
        self.assertEqual(self.tasks.open_microtask(TASK, "m1").status.value, "PLANNED")

    def test_contradictory_receipt_not_repaired_and_replay_refused(self):
        self.execute()
        path = self.operation_path()
        value = json.loads(path.read_text(encoding="utf-8"))
        value["receipt"]["sha256"] = "0" * 64
        path.write_text(json.dumps(value), encoding="utf-8")
        before = inventory(self.base)
        diag = self.observe()
        self.assertFalse(diag["operations_available"])
        self.assertEqual(inventory(self.base), before)
        with self.assertRaises(ApiError):
            self.execute()
        self.assertEqual((self.project / "a.txt").read_bytes(), AFTER)

    def test_invalid_snapshot_still_refused_without_repair(self):
        restore = self.tasks.microtask_directory(TASK, "m1") / "restore_point"
        snapshot = next((restore / "snapshots").glob("*.bin"))
        snapshot.write_bytes(b"corrupt")
        before = inventory(self.base)
        diag = self.observe()
        self.assertFalse(diag["state_observation"]["complete"])
        self.assertEqual(inventory(self.base), before)
        with self.assertRaises(ApiError) as error:
            self.execute()
        self.assertEqual(error.exception.details["result_code"], "RESTORE_POINT_NOT_VERIFIED")

    def test_corrupt_operation_is_unavailable_not_empty_success(self):
        self.execute()
        self.operation_path().write_text("{}", encoding="utf-8")
        before = inventory(self.base)
        diag = self.observe()
        self.assertFalse(diag["operations_available"])
        self.assertFalse(diag["storage_evidence_coherent"])
        self.assertTrue(diag["canonical_state"]["blockers"])
        self.assertEqual(inventory(self.base), before)

    def test_corrupt_event_log_does_not_repair_or_claim_no_write(self):
        self.execute()
        path = self.tasks.task_directory(TASK) / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("broken\n")
        before = inventory(self.base)
        diag = self.observe()
        self.assertFalse(diag["events_available"])
        self.assertFalse(diag["operations_available"])
        self.assertIsNone(diag["coverage"]["external_operation_count"])
        self.assertEqual(inventory(self.base), before)

    def test_closed_task_stays_read_only_and_refuses_new_mutation(self):
        self.tasks.complete_task(TASK)
        before = inventory(self.base)
        diag = self.observe()
        self.assertEqual(diag["state_observation"]["availability"], "CLOSED_TASK_HISTORY_ONLY")
        self.assertEqual(diag["canonical_state"]["authority_source"], "task_status")
        self.assertEqual(inventory(self.base), before)
        with self.assertRaises(ApiError):
            self.execute()
        self.assertEqual((self.project / "a.txt").read_bytes(), BEFORE)

    def test_unknown_after_disconnect_kept_unknown_and_no_recovery(self):
        self.api.operations.begin(TASK, "m1", "write", "a.txt", operation_id="uncertain", payload=AFTER)
        self.api.operations.transition(TASK, "uncertain", "STARTED")
        self.api.operations.transition(TASK, "uncertain", "UNKNOWN_AFTER_DISCONNECT")
        before = inventory(self.base)
        diag = self.observe()
        self.assertEqual(diag["operation_history"][0]["status"], "UNKNOWN_AFTER_DISCONNECT")
        self.assertEqual(diag["canonical_state"]["next_safe_action"], self.api.projection.build(TASK)["next_safe_action"])
        self.assertEqual(inventory(self.base), before)

    def test_bounded_store_race_never_retries_or_claims_coherence(self):
        original = self.api.projection.build
        count = 0
        def build(task_id):
            nonlocal count
            count += 1
            result = original(task_id)
            if count == 2:
                result["source_fingerprint"] = "changed"
            return result
        with mock.patch.object(self.api.projection, "build", side_effect=build):
            self.assertFalse(self.observe()["storage_evidence_coherent"])
        self.assertEqual(count, 2)

    def test_actual_store_change_between_projections_detected(self):
        collector = self.api.reconciliation.evidence
        original = collector.collect
        def collect(*args, **kwargs):
            result = original(*args, **kwargs)
            self.api.operations.begin(TASK, "m1", "write", "a.txt", operation_id="concurrent", payload=AFTER)
            return result
        with mock.patch.object(collector, "collect", side_effect=collect):
            diag = self.observe()
        self.assertFalse(diag["storage_evidence_coherent"])
        self.assertEqual((self.project / "a.txt").read_bytes(), BEFORE)

    def test_unreadable_current_target_not_clean_observation(self):
        collector = self.api.reconciliation.evidence
        with mock.patch.object(collector, "_current_file_state", return_value=(None, None, None, None, "unreadable")):
            diag = self.observe()
        self.assertFalse(diag["state_observation"]["complete"])
        self.assertIsNone(self.target(diag)["differs_from_snapshot"])

    def test_unprepared_task_diagnostics_do_not_prepare_it(self):
        task = self.tasks.create_task("wa4a_ws", "unprepared", "raw", "goal", task_id="unprepared")
        self.tasks.create_microtask(task.task_id, "one", "goal", microtask_id="m1")
        before = inventory(self.base)
        _, diag = self.api.dispatch("GET", "/tasks/unprepared/observe")
        self.assertEqual(diag["state_observation"]["availability"], "NOT_PREPARED")
        self.assertEqual(diag["operation_history"], [])
        self.assertEqual(inventory(self.base), before)

    def test_http_restore_remains_unexposed(self):
        before = inventory(self.base)
        with self.assertRaises(ApiError) as error:
            self.api.dispatch("POST", "/microtasks/m1/snapshot", {"task_id": TASK, "action": "restore"})
        self.assertEqual(error.exception.code, "real_workspace_mutation_not_exposed")
        self.assertEqual(inventory(self.base), before)

    def test_no_cross_workspace_scan(self):
        from web_alarm.workspace_registry import WorkspaceRegistry
        other = self.base / "other_project"
        other.mkdir()
        (other / "secret.txt").write_bytes(b"unregistered contents must not be read")
        WorkspaceRegistry(self.storage).register("other", other, workspace_id="other")
        diag = self.observe()
        self.assertEqual(diag["canonical_state"]["task"]["workspace_id"], "wa4a_ws")
        self.assertNotIn("secret.txt", json.dumps(diag))

    def test_cli_missing_task_returns_error_without_traceback(self):
        import io
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = cli_main(["--storage-root", str(self.storage), "observe", "--task-id", "missing"])
        self.assertEqual(code, 2)
        self.assertIn("ERROR:", error.getvalue())

    def test_reopen_fresh_process_recomputes_same_diagnostics(self):
        self.execute()
        first = self.observe()
        before = inventory(self.base)
        command = [sys.executable, "-B", "-m", "web_alarm.cli", "--storage-root", str(self.storage),
                   "observe", "--task-id", TASK]
        proc = subprocess.run(command, cwd=Path(__file__).parent, capture_output=True, text=True, timeout=45)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(first, json.loads(proc.stdout))
        self.assertEqual(inventory(self.base), before)

    def test_actual_loopback_http_diagnostics_and_method_guard(self):
        server = create_server(self.api, host="127.0.0.1", port=0)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 10)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/tasks/{TASK}/observe"
        before = inventory(self.base)
        with urllib.request.urlopen(url, timeout=10) as response:
            self.assertEqual(json.load(response)["mode"], "OBSERVE")
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(url, data=b'{}', method="POST",
                                                         headers={"Content-Type": "application/json"}), timeout=10)
        self.assertEqual(error.exception.code, 405)
        self.assertEqual(inventory(self.base), before)


if __name__ == "__main__":
    unittest.main()
