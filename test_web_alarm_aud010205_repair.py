"""WA4-R repair CLAUDE-WA4-R-AUD010205-REPAIR-001: event framing, admission before durable
write and closeout with unreadable history (findings AUD-01, AUD-02, AUD-05).

Oracles read raw bytes: every storage file outside ``locks/``, the event log split on the
physical LF only, and the workspace target. Separator characters are real code points
(chr(0x85), chr(0x2028), chr(0x2029)), never escape sequences.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK = "task_aud"
PRE = b"AUD-PRE\r\n\x02\xfd"
POST = b"AUD-POST\n\x00\x7e"
SEPARATORS = (chr(0x85), chr(0x2028), chr(0x2029))

CRASH_AFTER_MOVE = r'''
import os, sys
from pathlib import Path
from unittest import mock
sys.path.insert(0, sys.argv[1])
from web_alarm.closeout import CloseoutService
storage, task = Path(sys.argv[2]).resolve(), sys.argv[3]
real = os.replace
def replace(src, dst):
    result = real(src, dst)
    if Path(src) == storage / "tasks" / "active" / task and Path(dst) == storage / "tasks" / "completed" / task:
        os._exit(77)
    return result
with mock.patch.object(os, "replace", replace):
    CloseoutService(storage).complete(task)
sys.exit(3)
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lf_records(data: bytes) -> list[dict]:
    """Independent framing oracle: one physical LF ends one record."""
    assert data == b"" or data.endswith(b"\n"), "unterminated"
    return [json.loads(chunk) for chunk in data.split(b"\n")[:-1]]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_aud010205_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.storage, self.project = self.base / "state", self.base / "project"
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.project.mkdir()
        (self.project / "data.bin").write_bytes(PRE)
        WorkspaceRegistry(self.storage).register("aud repair", self.project, workspace_id="ws_aud")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_aud", "aud", "synthetic RAW TASK for AUD-01/02/05", "repair", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        self.machine = ServerStateMachine(self.storage)
        self.machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        self.machine.transition(TASK, "m1", "READY")
        self.machine.transition(TASK, "m1", "ACTIVE")
        self.facts = [{"task": "CLAUDE-WA4-R-AUD010205-REPAIR-001", "test": self.id()}]

    # --- raw oracles ----------------------------------------------------------------------
    def location(self) -> Path:
        active = self.storage / "tasks" / "active" / TASK
        return active if active.is_dir() else self.storage / "tasks" / "completed" / TASK

    def events_path(self) -> Path:
        return self.location() / "events.jsonl"

    def snapshot(self, label: str) -> dict:
        files = {p.relative_to(self.storage).as_posix(): sha(p.read_bytes())
                 for p in sorted(self.storage.rglob("*"))
                 if p.is_file() and p.relative_to(self.storage).parts[0] != "locks"}
        value = {"files": files, "target_hex": (self.project / "data.bin").read_bytes().hex(),
                 "active": (self.storage / "tasks/active" / TASK).is_dir(),
                 "completed": (self.storage / "tasks/completed" / TASK).is_dir()}
        self.facts.append({label: value})
        return value

    def tear_tail(self) -> bytes:
        path = self.events_path()
        data = path.read_bytes()
        self.assertTrue(data.endswith(b"\n"))
        path.write_bytes(data[:-1])
        return data

    def insert_invalid_line(self) -> bytes:
        path = self.events_path()
        data = path.read_bytes()
        first = data.index(b"\n") + 1
        path.write_bytes(data[:first] + b"{not json\n" + data[first:])
        return data

    def verify_m1(self, evidence: str = "AUD repair: microtask verified without mutation"):
        self.machine.transition(TASK, "m1", "DONE")
        self.machine.transition(TASK, "m1", "VERIFIED", verification_evidence=evidence)

    def read_events_or_error(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        try:
            return EventCheckpointStore(self.storage).read_events(TASK), None
        except Exception as exc:  # the assertion below names the failure
            return None, f"{type(exc).__name__}: {exc}"

    def closeout_blocker_codes(self) -> list[str]:
        from web_alarm.closeout import CloseoutService
        return [b["code"] for b in CloseoutService(self.storage).inspect(TASK)["blockers"]]


class EventFramingTests(Fixture):
    """AUD-01: one physical LF is one record; separators inside JSON strings are data."""

    def test_separator_characters_round_trip_and_are_escaped_on_write(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        store = EventCheckpointStore(self.storage)
        expected = []
        for ch in SEPARATORS:
            payload = {"note": f"a{ch}b", f"key{ch}": ch}
            store.append_event(TASK, "AUD01_PROBE", payload=payload)
            expected.append(payload)
        events, error = self.read_events_or_error()
        self.facts.append({"read_error": error})
        self.assertIsNone(error, "a record written by append_event is not readable by read_events")
        got = [e.payload for e in events if e.event_type == "AUD01_PROBE"]
        self.assertEqual(got, expected)
        data = self.events_path().read_bytes()
        self.assertEqual(len(lf_records(data)), len(events))
        for ch in SEPARATORS:
            self.assertNotIn(ch.encode("utf-8"), data, "raw line separator written into the JSONL log")

    def test_pre_repair_records_with_raw_separators_stay_readable(self):
        """Logs written by the pre-repair writer (raw U+0085/U+2028/U+2029) are valid JSONL."""
        from web_alarm.models import EventRecord, record_to_dict
        path = self.events_path()
        before = path.read_bytes()
        lines = []
        for ch in SEPARATORS:
            record = EventRecord(event_id="evt_" + format(ord(ch), "x"), task_id=TASK, event_type="LEGACY_RAW",
                                 payload={"note": f"x{ch}y"})
            lines.append(json.dumps(record_to_dict(record), ensure_ascii=False, separators=(",", ":")) + "\n")
        path.write_bytes(before + "".join(lines).encode("utf-8"))
        events, error = self.read_events_or_error()
        self.assertIsNone(error, "a valid pre-repair record with a raw separator became unreadable")
        self.assertEqual([e.payload["note"] for e in events if e.event_type == "LEGACY_RAW"],
                         [f"x{ch}y" for ch in SEPARATORS])
        self.assertEqual(path.read_bytes(), before + "".join(lines).encode("utf-8"), "reading changed bytes")

    def test_crlf_terminated_records_read_like_lf(self):
        from web_alarm.models import record_to_dict
        lf_events, error = self.read_events_or_error()
        self.assertIsNone(error)
        path = self.events_path()
        crlf = path.read_bytes().replace(b"\n", b"\r\n")
        path.write_bytes(crlf)
        crlf_events, error = self.read_events_or_error()
        self.assertIsNone(error, "CRLF-terminated history must stay readable")
        self.assertEqual([record_to_dict(e) for e in crlf_events], [record_to_dict(e) for e in lf_events])
        self.assertEqual(path.read_bytes(), crlf)

    def test_unreadable_history_is_refused_and_never_repaired(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
        path = self.events_path()
        good = path.read_bytes()
        first = good.index(b"\n") + 1
        cases = {
            "unterminated_tail": good[:-1],
            "invalid_json_line": good[:first] + b"{not json\n" + good[first:],
            "blank_line": good[:first] + b"\n" + good[first:],
            "invalid_utf8": good[:first] + b"\xff\xfe\n" + good[first:],
            "two_records_on_one_line": good[:-1] + b"\r" + good.split(b"\n")[0] + b"\n",
        }
        store = EventCheckpointStore(self.storage)
        for name, broken in cases.items():
            path.write_bytes(broken)
            with self.assertRaises(EventCheckpointStoreError, msg=name):
                store.read_events(TASK)
            self.assertEqual(path.read_bytes(), broken, f"{name}: reading repaired or changed history")
        path.write_bytes(good[:-1])
        with self.assertRaises(EventCheckpointStoreError):
            store.append_event(TASK, "MUST_NOT_APPEND")
        self.assertEqual(path.read_bytes(), good[:-1], "append joined or repaired an unterminated record")

    def test_http_mutation_with_U2028_target_keeps_history_readable(self):
        from web_alarm.server import ApiError, WebAlarmApi
        target = f"x{chr(0x2028)}y.bin"
        body = {"microtask_id": "m1", "operation_id": "op_u", "action": "write", "target": target,
                "payload": {"encoding": "base64", "data": base64.b64encode(POST).decode("ascii")}}
        try:
            status, reply = WebAlarmApi(self.storage).dispatch("POST", f"/tasks/{TASK}/mutations", body)
            self.facts.append({"http": [status, reply.get("result"), reply.get("result_code")]})
        except ApiError as exc:
            self.facts.append({"http_error": [exc.status, exc.code, str(exc.details)[:300]]})
        events, error = self.read_events_or_error()
        self.assertIsNone(error, "an ordinary HTTP request made the TASK history unreadable")
        intents = [e for e in events if e.event_type == "OPERATION_INTENT" and e.operation_id == "op_u"]
        self.assertEqual([e.payload["target"] for e in intents], [target])
        codes = self.closeout_blocker_codes()
        self.facts.append({"closeout_blockers": codes})
        self.assertFalse([c for c in codes if c.endswith("UNREADABLE")], codes)
        self.assertEqual((self.project / "data.bin").read_bytes(), PRE)

    def test_http_verification_evidence_with_U2029_is_preserved_and_closeout_is_clean(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.server import WebAlarmApi
        evidence = f"checked by agent{chr(0x2029)}all targets match{chr(0x85)}ok"
        api = WebAlarmApi(self.storage)
        for status, extra in (("DONE", {}), ("VERIFIED", {"verification_evidence": evidence})):
            code, _ = api.dispatch("POST", "/microtasks/m1/transition",
                                   dict({"task_id": TASK, "target_status": status}, **extra))
            self.assertEqual(code, 200)
        events, error = self.read_events_or_error()
        self.assertIsNone(error, "verification evidence text made the TASK history unreadable")
        raw = json.dumps([e.payload for e in events], ensure_ascii=False)
        self.assertIn(json.dumps(evidence, ensure_ascii=False)[1:-1], raw, "evidence text not preserved exactly")
        prefix = self.events_path().read_bytes()
        result = CloseoutService(self.storage).complete(TASK)
        self.assertEqual((result["result"], result["event_recorded"]), ("COMPLETED", True))
        after = self.events_path().read_bytes()
        self.assertTrue(after.startswith(prefix))
        self.assertEqual([r["event_type"] for r in lf_records(after[len(prefix):])], ["TASK_COMPLETED"])


class AdmissionTests(Fixture):
    """AUD-02: a refused admission on unreadable history leaves no durable artifact."""

    def execute(self, op: str):
        from web_alarm.mutation_executor import MutationExecutor
        try:
            result = MutationExecutor(self.storage).execute(TASK, "m1", op, "write", "data.bin", payload=POST)
            return {"returned": {k: result.get(k) for k in ("result", "result_code", "reason")}}
        except Exception as exc:  # the snapshot assertion decides; the type is recorded
            return {"raised": f"{type(exc).__name__}: {exc}"}

    def assert_refused_without_artifacts(self, damage):
        damage()
        before = self.snapshot("damaged_PRE")
        outcome = self.execute("op_new")
        self.facts.append({"outcome": outcome})
        after = self.snapshot("after_refused_admission")
        self.assertEqual(after, before, "a refused admission left durable artifacts or changed bytes")
        self.assertEqual(outcome.get("returned", {}).get("result"), "REFUSED", outcome)
        self.assertIn("history", outcome["returned"]["reason"])

    def test_torn_history_refuses_new_operation_without_artifacts(self):
        self.assert_refused_without_artifacts(self.tear_tail)

    def test_invalid_history_line_refuses_new_operation_without_artifacts(self):
        self.assert_refused_without_artifacts(self.insert_invalid_line)

    def test_begin_raises_operation_store_error_before_any_write(self):
        from web_alarm.operation_store import OperationStore, OperationStoreError
        self.tear_tail()
        before = self.snapshot("torn_PRE")
        with self.assertRaises(OperationStoreError):
            OperationStore(self.storage).begin(TASK, "m1", "write", "data.bin", operation_id="op_b", payload=POST)
        self.assertEqual(self.snapshot("after_begin"), before)

    def test_http_mutation_on_torn_history_is_refused_without_artifacts(self):
        from web_alarm.server import ApiError, WebAlarmApi
        self.tear_tail()
        before = self.snapshot("torn_PRE")
        body = {"microtask_id": "m1", "operation_id": "op_h", "action": "write", "target": "data.bin",
                "payload": {"encoding": "base64", "data": base64.b64encode(POST).decode("ascii")}}
        try:
            status, reply = WebAlarmApi(self.storage).dispatch("POST", f"/tasks/{TASK}/mutations", body)
            observed = [status, reply.get("result"), reply.get("result_code")]
        except ApiError as exc:
            observed = [exc.status, exc.code, (exc.details or {}).get("result_code") if isinstance(exc.details, dict) else None]
        self.facts.append({"http": observed})
        self.assertEqual(self.snapshot("after_http"), before)
        self.assertEqual(observed[0], 409, observed)

    def test_healthy_history_admission_is_unchanged(self):
        prefix = self.events_path().read_bytes()
        outcome = self.execute("op_ok")
        self.assertEqual(outcome["returned"]["result"], "EXECUTED", outcome)
        self.assertEqual((self.project / "data.bin").read_bytes(), POST)
        kinds = [(r["event_type"], r.get("operation_id")) for r in lf_records(self.events_path().read_bytes()[len(prefix):])]
        self.assertEqual(kinds[0], ("OPERATION_INTENT", "op_ok"))
        self.assertIn(("MUTATION_EXECUTED", "op_ok"), kinds)

    def test_replay_on_torn_history_writes_nothing(self):
        self.assertEqual(self.execute("op_r")["returned"]["result"], "EXECUTED")
        self.tear_tail()
        before = self.snapshot("torn_after_execution")
        outcome = self.execute("op_r")
        self.facts.append({"replay": outcome})
        self.assertEqual(self.snapshot("after_replay"), before)
        self.assertEqual(outcome.get("returned", {}).get("result"), "REFUSED", outcome)


class CloseoutHistoryTests(Fixture):
    """AUD-05: no ACTIVE -> COMPLETED with an unreadable audit trail, even without operations."""

    def assert_rejected_unchanged(self, damage):
        from web_alarm.closeout import CloseoutService
        self.verify_m1()
        damage()
        before = self.snapshot("damaged_PRE")
        result = CloseoutService(self.storage).complete(TASK)
        codes = [b["code"] for b in result["closeout"]["blockers"]]
        self.facts.append({"closeout": [result["result"], codes]})
        self.assertEqual(result["result"], "REJECTED", "closeout completed a TASK with unreadable history")
        self.assertIn("PROJECTION_HISTORY_UNREADABLE", codes)
        self.assertEqual(self.snapshot("after_rejected_closeout"), before)
        self.assertIn("PROJECTION_HISTORY_UNREADABLE", self.closeout_blocker_codes())

    def test_torn_history_without_operations_blocks_closeout(self):
        self.assert_rejected_unchanged(self.tear_tail)

    def test_invalid_history_line_without_operations_blocks_closeout(self):
        self.assert_rejected_unchanged(self.insert_invalid_line)

    def test_projection_is_fail_closed_and_names_the_blocker(self):
        from web_alarm.projection import ProjectionService
        self.verify_m1()
        self.tear_tail()
        projection = ProjectionService(self.storage).build(TASK)
        self.facts.append({"recovery": projection["recovery"]["state"], "next": projection["next_safe_action"]})
        self.assertEqual([b["code"] for b in projection["blockers"]], ["HISTORY_UNREADABLE"])
        self.assertEqual(projection["recovery"]["state"], "PROJECTION_BLOCKED")
        self.assertIn("HISTORY_UNREADABLE", projection["next_safe_action"])

    def test_checkpoint_is_not_valid_after_history_becomes_unreadable(self):
        from web_alarm.projection import ProjectionService
        self.verify_m1()
        service = ProjectionService(self.storage)
        service.rebuild_checkpoint(TASK)
        self.assertEqual(service.validate_checkpoint(TASK)["status"], "VALID")
        self.tear_tail()
        status = service.validate_checkpoint(TASK)["status"]
        self.facts.append({"checkpoint_after_tear": status})
        self.assertNotEqual(status, "VALID")

    def test_rejected_closeout_completes_after_operator_restores_the_delimiter(self):
        from web_alarm.closeout import CloseoutService
        self.verify_m1()
        good = self.tear_tail()
        self.assertEqual(CloseoutService(self.storage).complete(TASK)["result"], "REJECTED")
        self.events_path().write_bytes(good)  # manual repair outside the system, not by Web Alarm
        result = CloseoutService(self.storage).complete(TASK)
        self.assertEqual((result["result"], result["event_recorded"]), ("COMPLETED", True))
        after = self.events_path().read_bytes()
        self.assertTrue(after.startswith(good))
        self.assertEqual([r["event_type"] for r in lf_records(after[len(good):])], ["TASK_COMPLETED"])

    def test_healthy_closeout_and_projection_basis_are_unchanged(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.projection import ProjectionService
        self.verify_m1()
        service = ProjectionService(self.storage)
        projection = service.build(TASK)
        self.assertNotIn("history", projection["source_basis"])
        self.assertEqual(projection["blockers"], [])
        prefix = self.events_path().read_bytes()
        result = CloseoutService(self.storage).complete(TASK)
        self.assertEqual((result["result"], result["event_recorded"]), ("COMPLETED", True))
        after = self.events_path().read_bytes()
        self.assertEqual([r["event_type"] for r in lf_records(after[len(prefix):])], ["TASK_COMPLETED"])

    def test_pre_wa017_status_written_not_moved_needs_readable_history_before_the_move(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.models import TaskStatus
        from web_alarm.task_store import TaskStore
        self.verify_m1()
        tasks = TaskStore(self.storage)
        task = tasks.open_task(TASK)
        task.status = TaskStatus.COMPLETED  # the shape a pre-WA-017 crash left: status written, never moved
        tasks._write_task(tasks.active_dir / TASK, task)
        self.assertEqual(tasks.completion_state(TASK), "STATUS_WRITTEN_NOT_MOVED")
        good = self.tear_tail()
        before = self.snapshot("pre_wa017_torn_PRE")
        result = CloseoutService(self.storage).complete(TASK)
        codes = [b["code"] for b in result["closeout"]["blockers"]]
        self.facts.append({"closeout": [result["result"], codes]})
        self.assertEqual(result["result"], "REJECTED", "moved a TASK with unreadable history")
        self.assertIn("PROJECTION_HISTORY_UNREADABLE", codes)
        self.assertEqual(self.snapshot("after_rejected"), before)
        self.events_path().write_bytes(good)  # manual repair outside the system
        result = CloseoutService(self.storage).complete(TASK)
        self.assertEqual((result["result"], result["resumed"]), ("COMPLETED", "STATUS_WRITTEN_NOT_MOVED"))
        self.assertEqual((self.location().parent.name, tasks.completion_state(TASK)), ("completed", "COMPLETED"))

    def test_moved_status_pending_still_finishes_when_history_is_unreadable(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.task_store import TaskStore
        self.verify_m1()
        script = self.base / "crash_after_move.py"
        script.write_text(CRASH_AFTER_MOVE, encoding="utf-8")
        done = subprocess.run([sys.executable, "-B", str(script), str(ROOT), str(self.storage), TASK],
                              cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.facts.append({"crash_child": [done.returncode, done.stdout[-300:], done.stderr[-600:]]})
        self.assertEqual(done.returncode, 77, done.stderr)
        self.assertEqual(TaskStore(self.storage).completion_state(TASK), "MOVED_STATUS_PENDING")
        self.tear_tail()
        torn = self.events_path().read_bytes()
        result = CloseoutService(self.storage).complete(TASK)
        self.facts.append({"resumed": [result["result"], result["resumed"], result["event_recorded"]]})
        self.assertEqual((result["result"], result["resumed"], result["event_recorded"]),
                         ("COMPLETED", "MOVED_STATUS_PENDING", False))
        self.assertEqual(self.events_path().read_bytes(), torn, "status-only recovery changed history bytes")
        self.assertEqual(json.loads((self.location() / "task.json").read_bytes())["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
