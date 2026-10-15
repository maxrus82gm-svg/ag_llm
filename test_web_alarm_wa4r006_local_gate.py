"""WA4-R local gate: record identity, torn event framing and interrupted workers.

Uses the existing diagnostic fixture/actors without inheriting its test methods.
Expected state comes from raw bytes and explicit fault barriers, not projection.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import test_web_alarm_wa4r002_diagnostics as diagnostic
from web_alarm.closeout import CloseoutError, CloseoutService
from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from web_alarm.models import OperationStatus
from web_alarm.mutation_executor import MutationExecutor
from web_alarm.operation_store import OperationStore, OperationStoreError
from web_alarm.task_store import TaskStore, TaskStoreError

TASK, PRE, POST = diagnostic.TASK, diagnostic.PRE, diagnostic.POST


class LocalGateTests(unittest.TestCase):
    def setUp(self):
        self.h = diagnostic.RaceEvidenceTests()
        self.h.id = self.id
        self.h.setUp()
        self.facts = self.h.facts
        self.facts[0]["execution_task"] = "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
        self.addCleanup(self.h.cleanup)

    def location(self):
        active = self.h.storage / "tasks/active" / TASK
        completed = self.h.storage / "tasks/completed" / TASK
        return active if active.is_dir() else completed

    def byte_state(self, label):
        """Also works when JSON/JSONL is deliberately unparseable."""
        folder = self.location()
        value = {
            "active": (self.h.storage / "tasks/active" / TASK).is_dir(),
            "completed": (self.h.storage / "tasks/completed" / TASK).is_dir(),
            "target_hex": (self.h.project / "data.bin").read_bytes().hex(),
            "files_sha256": {p.relative_to(folder).as_posix(): diagnostic.sha(p.read_bytes())
                             for p in folder.rglob("*") if p.is_file()},
            "task_json_hex": (folder / "task.json").read_bytes().hex(),
            "events_hex": (folder / "events.jsonl").read_bytes().hex(),
        }
        self.facts.append({label: value})
        return value

    def corrupt_identity(self, filename, field, value):
        path = self.location() / filename
        original = path.read_bytes()
        record = json.loads(original)
        record[field] = value
        path.write_text(json.dumps(record), encoding="utf-8")
        self.facts.append({"fault": {"file": filename, "field": field, "value": value,
                                     "before_sha256": diagnostic.sha(original),
                                     "fault_bytes_hex": path.read_bytes().hex()}})
        self.addCleanup(lambda: (self.location() / filename).write_bytes(original))

    def test_task_identity_mismatch_blocks_gated_and_direct_completion(self):
        self.h.setup_closeout_evidence()
        self.corrupt_identity("task.json", "task_id", "foreign_task")
        before = self.byte_state("identity_fault_PRE")
        for name, call, kind in (
            ("gated", lambda: CloseoutService(self.h.storage).complete(TASK), CloseoutError),
            ("direct", lambda: TaskStore(self.h.storage).complete_task(TASK), TaskStoreError),
        ):
            error, result = None, None
            try:
                result = call()
            except kind as exc:
                error = diagnostic.error_chain(exc)
            self.facts.append({"completion_attempt": name, "error": error,
                               "returned": str(result) if result is not None else None})
            after = self.byte_state("identity_fault_after_" + name)
            self.assertIsNotNone(error, "mismatched TASK identity accepted completion")
            self.assertEqual(after, before)

    def test_plan_identity_mismatch_blocks_gated_completion(self):
        self.h.setup_closeout_evidence()
        self.corrupt_identity("plan.json", "task_id", "foreign_task")
        before = self.byte_state("plan_fault_PRE")
        error, result = None, None
        try:
            result = CloseoutService(self.h.storage).complete(TASK)
        except CloseoutError as exc:
            error = diagnostic.error_chain(exc)
        self.facts.append({"plan_completion_error": error, "returned": str(result)})
        after = self.byte_state("plan_fault_terminal")
        self.assertIsNotNone(error, "foreign plan accepted by closeout")
        self.assertEqual(after, before)

    def test_invalid_closeout_and_public_lock_identity_create_no_lock_files(self):
        self.h.setup_fixture()
        locks = self.h.storage / "locks"
        before = {p.relative_to(locks).as_posix(): diagnostic.sha(p.read_bytes())
                  for p in locks.rglob("*") if p.is_file()}
        for task_id in ("../outside", "..\\outside", "", ".", ".."):
            with self.assertRaises(CloseoutError) as caught:
                CloseoutService(self.h.storage).complete(task_id)
            self.facts.append({"invalid_task_id": task_id, "closeout_error": diagnostic.error_chain(caught.exception)})
            with self.assertRaises(OperationStoreError):
                with OperationStore(self.h.storage).task_lock(task_id):
                    self.fail("invalid task lock acquired")
        after = {p.relative_to(locks).as_posix(): diagnostic.sha(p.read_bytes())
                 for p in locks.rglob("*") if p.is_file()}
        self.facts.append({"lock_files_before": before, "lock_files_after": after})
        self.assertEqual(after, before)

    def micro_identity_case(self, field, value):
        self.h.setup_fixture()
        self.corrupt_identity("microtasks/m1.json", field, value)
        before = self.byte_state("micro_identity_fault_PRE")
        outcome = self.h.run_actor("foreign_micro", "mutate")
        terminal = self.h.state("micro_identity_fault_terminal")
        self.assertEqual(outcome["result"], "REFUSED")
        self.assertEqual(terminal["operations"], {}, "invalid stage must fail before INTENT")
        self.assertEqual(self.byte_state("micro_identity_fault_bytes"), before)
        self.assertEqual(self.h.apply_count(), 0)

    def test_foreign_microtask_parent_refuses_before_intent_and_apply(self):
        self.micro_identity_case("task_id", "foreign_task")

    def test_microtask_record_id_mismatch_refuses_before_intent_and_apply(self):
        self.micro_identity_case("microtask_id", "foreign_micro")

    def test_unterminated_event_read_and_append_fail_without_modifying_prefix(self):
        self.h.setup_closeout_evidence()
        path = self.location() / "events.jsonl"
        original = path.read_bytes()
        self.assertTrue(original.endswith(b"\n"))
        path.write_bytes(original[:-1])
        self.addCleanup(lambda: (self.location() / "events.jsonl").write_bytes(original))
        before = self.byte_state("unterminated_events_PRE")
        errors = {}
        store = EventCheckpointStore(self.h.storage)
        for name, call in (("read", lambda: store.read_events(TASK)),
                           ("append", lambda: store.append_event(TASK, "SHOULD_NOT_APPEND"))):
            try:
                call()
                errors[name] = None
            except EventCheckpointStoreError as exc:
                errors[name] = diagnostic.error_chain(exc)
        self.facts.append({"unterminated_event_errors": errors})
        after = self.byte_state("unterminated_events_terminal")
        self.assertIsNotNone(errors["read"], "unterminated event accepted as durable history")
        self.assertIsNotNone(errors["append"], "append joined onto an unterminated JSON record")
        self.assertEqual(after, before)

    def test_unterminated_events_block_closeout_and_known_receipt_replay(self):
        self.h.setup_closeout_evidence()
        path = self.location() / "events.jsonl"
        original = path.read_bytes()
        path.write_bytes(original[:-1])
        self.addCleanup(lambda: (self.location() / "events.jsonl").write_bytes(original))
        before = self.byte_state("torn_history_PRE")
        result = self.h.run_actor("torn_close", "complete")
        after = self.byte_state("torn_history_after_closeout")
        self.assertEqual(result["result"], "REJECTED", "torn history must not become clean completion")
        self.assertEqual(after, before)
        replay = self.h.run_actor("torn_replay", "mutate")
        self.assertEqual(replay["result"], "REFUSED")
        self.assertEqual(self.byte_state("torn_history_after_replay"), before)
        self.assertEqual(self.h.apply_count(), 1)

    def test_truncated_operation_json_refuses_closeout_and_replay_without_writes(self):
        self.h.setup_closeout_evidence()
        filename = "operations/op_diag.json"
        path = self.location() / filename
        original = path.read_bytes()
        broken = original[:len(original) // 2]
        path.write_bytes(broken)
        self.addCleanup(lambda: (self.location() / filename).write_bytes(original))
        before = self.byte_state("truncated_operation_PRE")
        self.facts.append({"truncated_operation_hex": broken.hex()})
        self.assertEqual(self.h.run_actor("broken_close", "complete")["result"], "REJECTED")
        self.assertEqual(self.h.run_actor("broken_replay", "mutate")["result"], "REFUSED")
        self.assertEqual(self.byte_state("truncated_operation_terminal"), before)
        self.assertEqual(self.h.apply_count(), 1)

    @unittest.skipUnless(sys.platform == "win32", "requires real Windows sharing refusal")
    def test_fresh_recovery_can_fail_again_without_success_or_second_apply(self):
        self.h.setup_closeout_evidence()
        first = self.h.run_actor("initial_fault", "complete", "native_status", exit_code=2)
        self.h.assert_error(first, "CloseoutError", deepest="PermissionError")
        pending = self.h.state("first_status_pending")
        second = self.h.run_actor("recovery_fault", "complete", "native_status", exit_code=2)
        self.h.assert_error(second, "CloseoutError", deepest="PermissionError")
        self.assertEqual(self.h.state("second_status_pending"), pending)
        self.assertEqual(self.h.run_actor("late", "mutate_late")["result"], "REFUSED")
        self.assertEqual(self.h.run_actor("recover", "complete")["resumed"], "MOVED_STATUS_PENDING")
        self.h.assert_fresh_closed_evidence()
        self.assertEqual(self.h.run_actor("again", "complete")["result"], "REJECTED")

    def test_killed_started_worker_releases_locks_without_blind_repeat(self):
        self.h.setup_fixture()
        actor = self.h.start("killed_writer", "mutate", "boundary")
        self.h.phase("killed_writer", "before_apply", actor)
        before = self.h.state("STARTED_before_physical_apply")
        self.assertEqual(before["operations"]["op_diag"]["status"], "STARTED")
        self.assertEqual(before["target_hex"], PRE.hex())
        self.facts.append({"external_termination": {"pid": actor.pid, "phase": "before_apply"}})
        actor.kill()
        code = actor.wait(timeout=10)
        stdout, stderr = actor.communicate(timeout=10)
        killed_trace = [json.loads(line) for line in
                        (self.h.base / "killed_writer.trace").read_text(encoding="utf-8").splitlines()]
        self.facts.append({"worker": "killed_writer", "pid": actor.pid,
                           "exit": code, "stdout": stdout, "stderr": stderr,
                           "trace": killed_trace, "json_reply": "NOT PRESENT IN SOURCE: externally killed"})
        self.assertNotEqual(code, 0)
        self.assertEqual(self.h.state("terminal_after_forced_death"), before)
        with OperationStore(self.h.storage, lock_timeout=.2).task_lock(TASK), \
             TaskStore(self.h.storage, lock_timeout=.2).mutation_lock(TASK):
            self.facts.append({"fresh_parent_lock_probe": "both acquired after killed worker"})
        replay = self.h.run_actor("fresh_unknown_replay", "mutate")
        self.assertEqual(replay["result"], "RECONCILIATION_REQUIRED")
        self.assertEqual(self.h.run_actor("close", "complete")["result"], "REJECTED")
        self.assertEqual(self.h.run_actor("late", "mutate_late")["result"], "REFUSED")
        terminal = self.h.state("fresh_processes_after_death")
        self.assertEqual(terminal["target_hex"], PRE.hex())
        self.assertIsNone(terminal["operations"]["op_diag"]["receipt"])
        trace = diagnostic.read_json(self.h.base / "killed_writer.json")
        self.assertEqual(trace["mode"], "boundary")
        phases = [json.loads(s)["phase"] for s in (self.h.base / "killed_writer.trace").read_text().splitlines()]
        self.assertIn("durable_STARTED", phases)
        self.assertNotIn("apply_exit", phases)
        self.assertNotIn("durable_DONE", phases)

    def test_exception_after_durable_done_replays_without_second_apply(self):
        self.h.setup_fixture()
        actual_event = EventCheckpointStore.append_event
        actual_apply = MutationExecutor._apply
        applies = []

        def apply(kind, path, data):
            applies.append({"target": str(path), "pre_hex": Path(path).read_bytes().hex()})
            return actual_apply(kind, path, data)

        def event(store, task, kind, **kwargs):
            if kind == "MUTATION_EXECUTED":
                self.facts.append({"fault_phase": "after durable DONE before MUTATION_EXECUTED event"})
                raise EventCheckpointStoreError("injected post-DONE event persistence refusal")
            return actual_event(store, task, kind, **kwargs)

        with mock.patch.object(MutationExecutor, "_apply", staticmethod(apply)), \
             mock.patch.object(EventCheckpointStore, "append_event", event):
            with self.assertRaises(EventCheckpointStoreError) as caught:
                MutationExecutor(self.h.storage).execute(TASK, "m1", "op_diag", "write", "data.bin", payload=POST)
        state = self.h.state("DONE_without_response")
        self.facts.append({"post_DONE_error": diagnostic.error_chain(caught.exception), "parent_applies": applies})
        self.assertEqual(state["target_hex"], POST.hex())
        self.assertEqual(state["operations"]["op_diag"]["status"], OperationStatus.DONE.value)
        receipt = state["operations"]["op_diag"]["receipt"]
        self.assertEqual(receipt["sha256"], diagnostic.sha(POST))
        replay = self.h.run_actor("fresh_receipt_replay", "mutate")
        self.assertEqual((replay["result"], replay["receipt"]), ("REPLAYED", receipt))
        self.assertEqual(len(applies), 1)
        self.assertEqual(self.h.apply_count(), 0, "fresh delivery must not enter physical apply")
        self.assertEqual(self.h.observe()["target_hex"], POST.hex())


if __name__ == "__main__":
    unittest.main()
