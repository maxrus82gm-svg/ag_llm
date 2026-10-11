"""WA4-A acceptance: deterministic delivery loss, real restart, no duplicate writes."""
import json
import subprocess
import time
import unittest
from unittest import mock

from wa4a_acceptance import AFTER, BEFORE, ROOT, TASK, DisposableWorkspace, lines, request, sha
from web_alarm.models import OperationStatus
from web_alarm.mutation_executor import MutationExecutor
from web_alarm.operation_store import OperationStore
from web_alarm.recovery_coordinator import RecoveryCoordinator


class LostResponseTests(DisposableWorkspace, unittest.TestCase):
    def test_A1_A2_http_lost_delivery_then_new_process_replays_exact_receipt(self):
        lost = self.child("drop_response", name="lost")
        self.assertEqual(lost["client"], {"state": "UNKNOWN", "received_bytes": 0, "body": None})
        stored = self.operation_path().read_bytes()
        receipt = self.op().receipt
        contract = self.op().contract
        history = self.history()
        count = self.apply_count()
        before_stat = (self.project / "a.txt").stat()
        trace = lines(self.base / "lost.jsonl")
        ready = next(e for e in trace if e["event"] == "RESPONSE_READY")
        self.assertEqual((ready["status"], ready["result"], ready["receipt"]), (200, "EXECUTED", receipt))
        self.assertLess(trace.index(ready), next(i for i,e in enumerate(trace) if e["event"] == "DELIVERY_DROPPED"))
        self.assertEqual(count, 1)
        evidence = self.decision()
        self.assertEqual(evidence["DECISION"]["decision"], "ADOPT_CURRENT_STATE")
        for name in ("fresh_client", "fresh_again"):
            retry = self.child(name=name)
            client = retry["client"]
            self.assertEqual((client["status"], client["body"]["result"], client["body"]["receipt"]), (200, "REPLAYED", receipt))
            self.assertFalse(client["body"]["physical_mutation_performed"])
            self.assertNotEqual(lost["pid"], retry["pid"])
            self.assertEqual(self.operation_path().read_bytes(), stored)
            self.assertEqual(self.op().contract, contract)
            self.assertEqual(self.history()[:len(history)], history)
            self.assertEqual(self.apply_count(), count)
        after_stat = (self.project / "a.txt").stat()
        self.assertEqual((self.project / "a.txt").read_bytes(), AFTER)
        self.assertEqual((before_stat.st_mtime_ns, before_stat.st_ino), (after_stat.st_mtime_ns, after_stat.st_ino))
        self.assertEqual(len(self.events("MUTATION_EXECUTED")), 1)
        self.note(acceptance=["A1", "A2", "A8"], expected="same receipt, one write, one execution event",
                  operation_sha256=sha(stored), target_sha256=sha(AFTER), receipt=receipt,
                  history_prefix_sha256=sha(json.dumps(history, sort_keys=True).encode()),
                  recovery=evidence, physical_calls=self.apply_count(), execution_events=1)

    def test_A1_create_response_loss_does_not_attempt_create_again(self):
        self.check_action("create", "new.txt", AFTER)

    def test_A1_delete_response_loss_does_not_attempt_delete_again(self):
        self.check_action("delete", "a.txt", None)

    def check_action(self, action, target, expected):
        if action == "create":
            # New disposable setup with the proper manifest, before any request.
            self.manifest = [("new.txt", "create")]
            self.setUp()
        body = request(action, target)
        self.child("drop_response", body, "lost")
        receipt = self.op().receipt
        replay = self.child(body=body, name="fresh")["client"]
        self.assertEqual((replay["status"], replay["body"]["result"], replay["body"]["receipt"]), (200, "REPLAYED", receipt))
        p = self.project / target
        self.assertEqual(p.read_bytes() if p.exists() else None, expected)
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (1, 1))
        self.note(acceptance=["A1", "A2"], action=action, physical_calls=1, receipt=receipt)

    def race_clients(self):
        barrier = self.base / "barrier"
        barrier.mkdir()
        procs = []
        try:
            for i in range(4):
                procs.append(subprocess.Popen(self.worker_args(name=f"race_{i}", barrier=barrier),
                    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            deadline = time.monotonic() + 30
            while len(list(barrier.glob("*.ready"))) != 4:
                self.assertLess(time.monotonic(), deadline, "clients failed to reach barrier")
                time.sleep(.01)
            (barrier / "go").touch()
            responses = []
            for p in procs:
                stdout, stderr = p.communicate(timeout=90)
                self.assertEqual(p.returncode, 0, stderr)
                responses.append(json.loads(stdout)["client"])
        finally:
            for p in procs:
                if p.poll() is None:
                    p.kill()
                p.communicate()
        return responses

    def test_A3_four_fresh_clients_deliver_one_contract_concurrently(self):
        responses = self.race_clients()
        self.assertEqual(sum(r["status"] == 200 and r["body"]["result"] == "EXECUTED" for r in responses), 1)
        for r in responses:
            self.assertIn(r["status"], (200, 409), responses)
            if r["status"] == 200:
                self.assertIn(r["body"]["result"], ("EXECUTED", "REPLAYED"))
                self.assertEqual(r["body"]["receipt"], self.op().receipt)
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (1, 1))
        self.note(acceptance=["A3"], expected="one execution", responses=responses, physical_calls=1)

    def test_A3_concurrent_redelivery_after_lost_response_never_executes_again(self):
        self.child("drop_response", name="lost")
        receipt = self.op().receipt
        original = self.operation_path().read_bytes()
        responses = self.race_clients()
        for client in responses:
            self.assertEqual((client["status"], client["body"]["result"], client["body"]["receipt"]), (200, "REPLAYED", receipt))
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (1, 1))
        self.assertEqual(self.operation_path().read_bytes(), original)
        self.note(acceptance=["A3"], expected="four replays, zero additional writes", responses=responses, physical_calls=1)

    def test_A4_changed_request_never_rewrites_original_contract_or_receipt(self):
        self.child("drop_response", name="lost")
        original = self.operation_path().read_bytes()
        variants = {
            "payload": {"payload": {"encoding": "utf-8", "data": "different"}},
            "target": {"target": "outside.txt"}, "action": {"action": "edit"},
            "precondition": {"expected_precondition_sha256": sha(BEFORE)},
            "request_metadata": {"request": {"changed": True}},
            "microtask": {"microtask_id": "m2"},
        }
        for name, delta in variants.items():
            with self.subTest(name=name):
                status, out = self.dispatch(request(**delta))
                self.assertEqual((status, out["details"]["result_code"]), (409, "OPERATION_ID_CONFLICT"))
                self.assertEqual(self.operation_path().read_bytes(), original)
        self.assertEqual((self.apply_count(), (self.project / "a.txt").read_bytes()), (1, AFTER))
        self.note(acceptance=["A4"], variants=list(variants), operation_sha256=sha(original), physical_calls=1)


class InterruptionTests(DisposableWorkspace, unittest.TestCase):
    def test_A5_before_started_safe_first_execution_in_fresh_process(self):
        self.child("before_started", name="lost")
        self.assertEqual((self.op().status, self.apply_count()), (OperationStatus.INTENT, 0))
        dec = self.decision()["DECISION"]
        self.assertEqual(dec["decision"], "RETRY_SAFE")
        replay = self.child(name="retry")["client"]
        self.assertEqual((replay["status"], replay["body"]["result"], self.apply_count()), (200, "EXECUTED", 1))
        self.note(acceptance=["A5"], window="before STARTED", recovery=dec, physical_calls=1)

    def test_A5_after_started_requires_resolver_before_any_write(self):
        self.child("after_started", name="lost")
        replay = self.child(name="unknown")["client"]
        self.assertEqual((replay["status"], replay["body"]["error"]["details"]["result"]), (409, "RECONCILIATION_REQUIRED"))
        self.assertEqual((self.op().status, self.apply_count()), (OperationStatus.STARTED, 0))
        self.resolve("RETRY")
        retry = self.child(name="authorized_retry")["client"]
        self.assertEqual((retry["status"], retry["body"]["result"], self.apply_count()), (200, "EXECUTED", 1))
        self.note(acceptance=["A5"], window="after STARTED", physical_calls=1)

    def test_A5_after_physical_write_adopt_without_second_execution(self):
        self.child("after_write", name="lost")
        self.assertEqual((self.op().status, self.op().receipt), (OperationStatus.STARTED, None))
        replay = self.child(name="unknown")["client"]
        self.assertEqual(replay["status"], 409)
        decision = self.decision()["DECISION"]
        self.assertEqual(decision["decision"], "ADOPT_CURRENT_STATE")
        self.resolve("ADOPT")
        RecoveryCoordinator(self.storage).recover(TASK)
        receipt = self.op().receipt
        self.assertEqual(self.op().status, OperationStatus.VERIFIED)
        replay = self.child(name="adopted")["client"]
        self.assertEqual((replay["status"], replay["body"]["receipt"]), (200, receipt))
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (1, 0))
        self.note(acceptance=["A5", "A6"], window="after physical write", recovery=decision, physical_calls=1,
                  execution_events=0, receipt_origin="RC-6 ADOPT; not a fabricated execution event")

    def test_A5_after_receipt_before_execution_event_preserves_receipt(self):
        self.child("after_receipt", name="lost")
        receipt = self.op().receipt
        self.assertEqual(len(self.events("MUTATION_EXECUTED")), 0)
        replay = self.child(name="replay")["client"]
        self.assertEqual((replay["status"], replay["body"]["result"], replay["body"]["receipt"]), (200, "REPLAYED", receipt))
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (1, 0))
        self.note(acceptance=["A5", "A8"], window="after receipt, before execution event", physical_calls=1)

    def test_A5_durable_receipt_before_DONE_event_is_still_replayable(self):
        self.child("receipt_before_event", name="lost")
        receipt = self.op().receipt
        self.assertFalse(any(e.payload.get("to") == "DONE" for e in self.events("OPERATION_TRANSITION")))
        replay = self.child(name="fresh")["client"]
        self.assertEqual((replay["status"], replay["body"]["result"], replay["body"]["receipt"]), (200, "REPLAYED", receipt))
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (1, 0))
        self.note(acceptance=["A5", "A8"], window="durable receipt before DONE event", physical_calls=1,
                  receipt=receipt, execution_events=0)

    def test_A5_unknown_retry_lifecycle_is_explicit_safe_refusal(self):
        ops = OperationStore(self.storage)
        ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_a", payload=AFTER)
        ops.transition(TASK, "op_a", "UNKNOWN_AFTER_DISCONNECT")
        self.resolve("RETRY")
        client = self.child(name="unsupported")["client"]
        self.assertEqual((client["status"], client["body"]["error"]["details"]["result_code"]), (409, "RETRY_LIFECYCLE_UNSUPPORTED"))
        self.assertEqual((self.apply_count(), (self.project / "a.txt").read_bytes()), (0, BEFORE))
        self.note(acceptance=["A5"], retained_limit="P-2", physical_calls=0)

    def test_A6_unclassified_bytes_never_adopt_or_retry_blindly(self):
        self.child("after_write", name="lost")
        (self.project / "a.txt").write_bytes(b"neither pre nor post\n")
        decision = self.decision()["DECISION"]
        self.assertEqual(decision["decision"], "MANUAL_REVIEW_REQUIRED")
        replay = self.child(name="ambiguous")["client"]
        self.assertEqual(replay["status"], 409)
        self.assertEqual((self.apply_count(), self.op().receipt), (1, None))
        self.note(acceptance=["A6"], recovery=decision, physical_calls=1)

    def test_A6_identical_pre_and_post_is_not_proof_of_unexecuted_work(self):
        ops = OperationStore(self.storage)
        body = request(payload={"encoding": "utf-8", "data": BEFORE.decode()})
        ops.begin(TASK, "m1", "write", "a.txt", operation_id="op_a", payload=BEFORE)
        ops.transition(TASK, "op_a", "STARTED")
        decision = self.decision()["DECISION"]
        self.assertEqual(decision["decision"], "MANUAL_REVIEW_REQUIRED")
        self.assertEqual(self.child(body=body)["client"]["status"], 409)
        self.assertEqual(self.apply_count(), 0)
        self.note(acceptance=["A6"], recovery=decision, physical_calls=0)


class CompositeTests(DisposableWorkspace, unittest.TestCase):
    manifest = [("src.txt", "move"), ("dst.txt", "move")]

    def test_A1_A6_move_lost_response_replays_both_original_receipts(self):
        self.check_composite("move")

    def test_A1_A6_rename_lost_response_replays_both_original_receipts(self):
        self.check_composite("rename")

    def check_composite(self, action):
        body = request(action, "src.txt", destination="dst.txt")
        self.child("drop_response", body, "lost")
        receipts = [self.op("op_a."+suffix).receipt for suffix in ("create-destination", "delete-source")]
        replay = self.child(body=body, name="fresh")["client"]
        self.assertEqual((replay["status"], replay["body"]["result"]), (200, "REPLAYED"))
        self.assertEqual([s["receipt"] for s in replay["body"]["steps"]], receipts)
        self.assertEqual((self.apply_count(), len(self.events("MUTATION_EXECUTED"))), (2, 2))
        self.assertFalse((self.project / "src.txt").exists())
        self.assertEqual((self.project / "dst.txt").read_bytes(), BEFORE)
        self.note(acceptance=["A1", "A2", "A6"], action=action, receipts=receipts, physical_calls=2,
                  atomic=False)

    def test_A6_partial_move_can_only_finish_the_unexecuted_step(self):
        body = request("move", "src.txt", destination="dst.txt")
        self.child("move_partial", body, "lost")
        first_receipt = self.op("op_a.create-destination").receipt
        decision = self.decision("op_a.create-destination")["DECISION"]
        self.assertEqual(decision["decision"], "ROLLBACK_CURRENT_MICROTASK")
        self.assertEqual((self.apply_count(), self.op("op_a.delete-source").status), (1, OperationStatus.INTENT))
        replay = self.child(body=body, name="finish")["client"]
        self.assertEqual((replay["status"], replay["body"]["result"]), (200, "EXECUTED"))
        self.assertEqual(replay["body"]["steps"][0]["receipt"], first_receipt)
        self.assertEqual(self.apply_count(), 2)
        self.note(acceptance=["A6"], recovery=decision, physical_calls=2, completed_only="delete-source")

    def test_A6_partial_move_source_drift_is_preserved(self):
        body = request("move", "src.txt", destination="dst.txt")
        self.child("move_partial", body, "lost")
        (self.project / "src.txt").write_bytes(b"external source\n")
        replay = self.child(body=body, name="refuse")["client"]
        details = replay["body"]["error"]["details"]
        self.assertEqual((replay["status"], details["result"]), (409, "PARTIAL"))
        self.assertEqual(self.apply_count(), 1)
        self.assertEqual((self.project / "src.txt").read_bytes(), b"external source\n")
        self.note(acceptance=["A6", "A7"], result=details, physical_calls=1)


class SafetyTests(DisposableWorkspace, unittest.TestCase):
    def pending(self):
        self.child("before_started", name="lost")

    def assert_refused_unchanged(self, body=None, expected_code=None):
        before = (self.project / "a.txt").read_bytes()
        result = self.child(body=body, name="refused")["client"]
        self.assertEqual(result["status"], 409)
        details = result["body"]["error"]["details"]
        if expected_code:
            self.assertEqual(details["result_code"], expected_code)
        self.assertEqual((self.apply_count(), (self.project / "a.txt").read_bytes()), (0, before))
        self.note(acceptance=["A7"], refusal=details, physical_calls=0)

    def test_A7_closed_task_returns_history_but_never_new_authority(self):
        self.child("drop_response", name="lost")
        receipt = self.op().receipt
        self.tasks.complete_task(TASK)
        historical = self.child(name="historical")["client"]
        self.assertEqual((historical["status"], historical["body"]["receipt"]), (200, receipt))
        new = self.child(body=request(operation_id="op_new"), name="new")["client"]
        self.assertEqual(new["status"], 409)
        self.assertEqual(self.apply_count(), 1)
        self.note(acceptance=["A7"], historical_receipt=receipt, physical_calls=1)

    def test_A7_closed_task_cannot_execute_pending_intent(self):
        self.pending()
        self.tasks.complete_task(TASK)
        self.assert_refused_unchanged(expected_code="TASK_CLOSED")

    def test_A7_nonactive_microtask_blocks_pending_execution(self):
        self.pending()
        self.machine.transition(TASK, "m1", "UNKNOWN_AFTER_DISCONNECT")
        self.assert_refused_unchanged()

    def test_A7_corrupt_snapshot_blocks_retry(self):
        self.pending()
        snapshots = [p for p in self.tasks.task_directory(TASK).rglob("*.bin") if "snapshots" in p.parts]
        self.assertTrue(snapshots)
        snapshots[0].write_bytes(b"corrupt snapshot")
        self.assert_refused_unchanged(expected_code="RESTORE_POINT_NOT_VERIFIED")

    def test_A7_released_claim_does_not_regain_authority(self):
        from web_alarm.target_claim_service import TargetClaimService
        self.pending()
        TargetClaimService(self.storage).release(TASK, "op_a", reason="abandoned")
        self.assert_refused_unchanged(expected_code="CLAIM_ALREADY_RELEASED")

    def test_A7_other_operation_cannot_bypass_held_ownership(self):
        self.pending()
        self.assert_refused_unchanged(body=request(operation_id="op_other"))

    def test_A7_target_outside_verified_manifest_is_refused(self):
        self.assert_refused_unchanged(body=request(target="outside.txt"), expected_code="TARGET_NOT_IN_MANIFEST")

    def test_A7_corrupt_payload_blocks_pending_retry(self):
        self.pending()
        ref = self.op().contract["payload_ref"]
        payloads = list(self.tasks.task_directory(TASK).rglob(ref["sha256"]+"*"))
        self.assertTrue(payloads)
        next(p for p in payloads if p.is_file()).write_bytes(b"corrupt payload")
        self.assert_refused_unchanged(expected_code="PAYLOAD_INTEGRITY_FAILURE")

    def test_A7_current_post_proof_cannot_be_replaced_by_declared_intent(self):
        def bad_write(kind, path, data):
            path.write_bytes(b"not expected post\n")
        with mock.patch.object(MutationExecutor, "_apply", staticmethod(bad_write)):
            status, out = self.dispatch()
        self.assertEqual((status, out["details"]["result_code"]), (409, "POST_PROOF_FAILED"))
        self.assertIsNone(self.op().receipt)
        self.assertEqual(self.op().status, OperationStatus.STARTED)
        self.note(acceptance=["A7"], refusal=out["details"], receipt=None)

    def test_A7_byte_drift_after_retry_authorization_blocks_CAS(self):
        self.child("after_started", name="lost")
        self.resolve("RETRY")
        (self.project / "a.txt").write_bytes(b"changed after decision\n")
        self.assert_refused_unchanged()

    def test_A7_durable_receipt_is_historical_and_does_not_overwrite_later_drift(self):
        self.child("drop_response", name="lost")
        receipt = self.op().receipt
        (self.project / "a.txt").write_bytes(b"later external version\n")
        replay = self.child(name="history")["client"]
        self.assertEqual((replay["status"], replay["body"]["receipt"]), (200, receipt))
        self.assertEqual((self.project / "a.txt").read_bytes(), b"later external version\n")
        self.assertEqual(self.apply_count(), 1)
        decision = self.decision()["DECISION"]
        self.assertEqual(decision["decision"], "MANUAL_REVIEW_REQUIRED")
        self.note(acceptance=["A7"], recovery=decision, historical_only=True, physical_calls=1)


class IntegrityTests(DisposableWorkspace, unittest.TestCase):
    def corrupt_record(self, change):
        self.child("drop_response", name="lost")
        path = self.operation_path()
        data = json.loads(path.read_bytes())
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assert_corruption_refused(path)

    def assert_corruption_refused(self, path):
        corrupt = path.read_bytes()
        client = self.child(name="corrupt_replay")["client"]
        self.note(acceptance=["A8"], expected="fail closed", actual_status=client["status"],
                  corrupt_sha256=sha(corrupt), physical_calls=self.apply_count())
        self.assertNotEqual(client["status"], 200, client)
        self.assertEqual(path.read_bytes(), corrupt, "must not heal or overwrite forensic evidence")
        self.assertEqual((self.apply_count(), (self.project / "a.txt").read_bytes()), (1, AFTER))

    def test_A8_receipt_wrong_hash_cannot_be_replayed_as_success(self):
        self.corrupt_record(lambda d: d["receipt"].update(sha256="0"*64))

    def test_A8_receipt_false_match_flag_is_a_contradiction(self):
        self.corrupt_record(lambda d: d["receipt"].update(matches_expected_post=False))

    def test_A8_receipt_future_revision_is_rejected(self):
        self.corrupt_record(lambda d: d["receipt"].update(revision=d["revision"]+1))

    def test_A8_receipt_backdated_revision_is_rejected(self):
        self.corrupt_record(lambda d: d["receipt"].update(revision=1))

    def test_A8_receipt_missing_is_rejected(self):
        self.corrupt_record(lambda d: d.update(receipt=None))

    def test_A8_record_identity_mismatch_is_rejected(self):
        self.corrupt_record(lambda d: d.update(operation_id="someone_else"))

    def test_A8_contract_kind_cannot_disagree_with_request_action(self):
        self.corrupt_record(lambda d: d["contract"].update(mutation_kind="DELETE"))

    def test_A8_contract_pre_state_cannot_disagree_with_intent_history(self):
        self.corrupt_record(lambda d: d["contract"]["pre_state"].update(sha256="0"*64))

    def test_A8_contract_workspace_identity_must_match_TASK(self):
        self.corrupt_record(lambda d: d["contract"].update(workspace_id="wrong_workspace"))

    def corrupt_history(self, change):
        self.child("drop_response", name="lost")
        path = self.tasks.task_directory(TASK) / "events.jsonl"
        data = lines(path)
        change(data)
        path.write_text("".join(json.dumps(e)+"\n" for e in data), encoding="utf-8")
        self.assert_corruption_refused(path)

    def test_A8_corrupt_event_JSON_is_rejected(self):
        self.child("drop_response", name="lost")
        path = self.tasks.task_directory(TASK) / "events.jsonl"
        path.write_text("not json\n", encoding="utf-8")
        self.assert_corruption_refused(path)

    def test_A8_intent_history_fingerprint_contradiction_is_rejected(self):
        def change(data):
            next(e for e in data if e["event_type"] == "OPERATION_INTENT")["payload"]["request_fingerprint"] = "0"*64
        self.corrupt_history(change)

    def test_A8_receipt_history_contradiction_is_rejected(self):
        def change(data):
            next(e for e in data if e["event_type"] == "OPERATION_TRANSITION" and e["payload"]["to"] == "DONE")["payload"]["receipt"]["sha256"] = "0"*64
        self.corrupt_history(change)

    def test_A8_terminal_status_history_contradiction_is_rejected(self):
        def change(data):
            next(e for e in data if e["event_type"] == "OPERATION_TRANSITION" and e["payload"]["to"] == "DONE")["payload"]["to"] = "FAILED"
        self.corrupt_history(change)

    def test_A8_execution_event_cannot_contradict_receipt(self):
        def change(data):
            next(e for e in data if e["event_type"] == "MUTATION_EXECUTED")["payload"]["receipt"]["sha256"] = "0"*64
        self.corrupt_history(change)

    def test_A8_missing_intent_history_is_not_a_valid_success(self):
        self.corrupt_history(lambda data: data.clear())

    def test_A8_pending_intent_with_lost_history_cannot_grant_new_mutation(self):
        self.child("before_started", name="lost")
        path = self.tasks.task_directory(TASK) / "events.jsonl"
        path.write_bytes(b"")
        replay = self.child(name="corrupt_pending")["client"]
        self.note(acceptance=["A8"], expected="fail closed before mutation", actual_status=replay["status"],
                  physical_calls=self.apply_count())
        self.assertNotEqual(replay["status"], 200)
        self.assertEqual((self.apply_count(), (self.project / "a.txt").read_bytes()), (0, BEFORE))

    def test_A8_truncated_record_JSON_is_rejected(self):
        self.child("drop_response", name="lost")
        path = self.operation_path()
        path.write_bytes(b'{"receipt":')
        self.assert_corruption_refused(path)


if __name__ == "__main__":
    unittest.main()
