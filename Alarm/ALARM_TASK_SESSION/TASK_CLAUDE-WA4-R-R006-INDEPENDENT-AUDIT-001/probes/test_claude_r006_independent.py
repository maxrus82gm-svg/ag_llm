"""CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001 — independent offline probes (disposable TEMP only).

Own fixture/oracles (own PRE/POST bytes, own child actor, raw-byte snapshots), not the Codex diagnostic fixture.
GateChecks: independent F1/F2/F3 reproductions; expected PASS.
FindingProbes: safety invariants written as assertions; a FAIL here is a CONFIRMED defect (reported as FINDING),
not a test-harness problem. Every case stores facts for the evidence file.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
WORKER = HERE / "claude_probe_worker.py"
REPO = Path(r"M:\GitHub\ag_llm")
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
TASK = "task_cl"
PRE = b"CLAUDE-PRE\r\n\x01\xfe"
POST = b"CLAUDE-POST\n\x00\x7f"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def chain(exc):
    out, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append({"type": type(exc).__name__, "message": str(exc)[:400],
                    "winerror": getattr(exc, "winerror", None)})
        exc = exc.__cause__ or exc.__context__
    return out


def jsonl_by_lf(data):
    """Independent framing oracle: records are delimited by LF only (the writer's contract)."""
    assert data == b"" or data.endswith(b"\n"), "unterminated"
    return [json.loads(line) for line in data.split(b"\n")[:-1]] if data else []


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="claude_r006_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.storage, self.project = self.base / "state", self.base / "project"
        self.children = []
        self.addCleanup(self._reap)
        self.facts = [{"audit": "CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001", "test": self.id(),
                       "oracle": "raw bytes / directory existence / LF framing / child exit + trace"}]

    def _reap(self):
        for p in self.children:
            if p.poll() is None:
                p.kill()
            try:
                p.communicate(timeout=10)
            except Exception:
                pass

    # --- fixture through production APIs, own bytes ------------------------------------------
    def build(self):
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.project.mkdir()
        (self.project / "data.bin").write_bytes(PRE)
        WorkspaceRegistry(self.storage).register("claude probe", self.project, workspace_id="ws_cl")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_cl", "probe", "synthetic RAW TASK for the Claude R-006 audit", "probe", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        machine.transition(TASK, "m1", "READY")
        machine.transition(TASK, "m1", "ACTIVE")

    def build_closable(self):
        """One real executed operation, then verified, so closeout has nonempty evidence."""
        from web_alarm.operation_store import OperationStore
        from web_alarm.state_machine import ServerStateMachine
        self.build()
        out = self.run_actor("setup_apply", "mutate", op="op1")
        self.assertEqual(out["result"], "EXECUTED", out)
        OperationStore(self.storage).transition(TASK, "op1", "VERIFIED")
        machine = ServerStateMachine(self.storage)
        machine.transition(TASK, "m1", "DONE")
        machine.transition(TASK, "m1", "VERIFIED", verification_evidence="Claude probe: POST bytes checked")
        self.receipt = out["receipt"]
        self.assertEqual(self.receipt["sha256"], sha(POST))

    def location(self):
        active = self.storage / "tasks" / "active" / TASK
        return active if active.is_dir() else self.storage / "tasks" / "completed" / TASK

    def raw(self, label):
        loc = self.location()
        files = {p.relative_to(loc).as_posix(): sha(p.read_bytes()) for p in sorted(loc.rglob("*")) if p.is_file()}
        events = (loc / "events.jsonl").read_bytes() if (loc / "events.jsonl").exists() else b""
        task_json = (loc / "task.json").read_bytes()
        ops = {p.stem: json.loads(p.read_bytes()) for p in sorted((loc / "operations").glob("*.json"))} \
            if (loc / "operations").is_dir() else {}
        value = {"active": (self.storage / "tasks/active" / TASK).is_dir(),
                 "completed": (self.storage / "tasks/completed" / TASK).is_dir(),
                 "task_status": json.loads(task_json)["status"], "task_json_sha256": sha(task_json),
                 "events_sha256": sha(events), "events_len": len(events), "events_tail_lf": events.endswith(b"\n"),
                 "files": files, "ops": {k: (v["status"], v.get("receipt")) for k, v in ops.items()},
                 "target_hex": (self.project / "data.bin").read_bytes().hex()}
        self.facts.append({label: value})
        self._events_bytes = events
        return value

    def lock_files(self):
        root = self.storage / "locks"
        return sorted(p.relative_to(self.storage).as_posix() for p in root.rglob("*") if p.is_file()) \
            if root.exists() else []

    # --- child actors -----------------------------------------------------------------------------
    def start(self, name, action, mode="normal", op="op1"):
        cfg = {"base": str(self.base), "storage": str(self.storage), "name": name, "action": action,
               "mode": mode, "op": op, "payload_hex": POST.hex()}
        path = self.base / (name + ".json")
        path.write_text(json.dumps(cfg), encoding="utf-8")
        proc = subprocess.Popen([sys.executable, "-B", str(WORKER), str(path)], cwd=REPO,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.children.append(proc)
        return proc

    def finish(self, name, proc, exit_code=0):
        out, err = proc.communicate(timeout=60)
        trace_path = self.base / (name + ".trace")
        trace = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()] if trace_path.exists() else []
        parsed = json.loads(out) if out.strip() else None
        self.facts.append({"actor": name, "pid": proc.pid, "exit": proc.returncode, "stdout": out[-2000:],
                           "stderr": err[-1500:], "trace": trace,
                           "error_chain": (parsed or {}).get("error") if isinstance(parsed, dict) else None})
        self.assertEqual(proc.returncode, exit_code, (out, err[-1500:]))
        return parsed

    def run_actor(self, name, action, mode="normal", exit_code=0, op="op1"):
        return self.finish(name, self.start(name, action, mode, op), exit_code)

    def wait_phase(self, name, phase, proc, timeout=40):
        deadline = time.monotonic() + timeout
        while not (self.base / f"{name}.{phase}").exists():
            if proc.poll() is not None:
                raise AssertionError(f"{name} exited before {phase}: {proc.communicate()}")
            if time.monotonic() > deadline:
                raise TimeoutError(f"{name} never reached {phase}")
            time.sleep(0.005)

    def go(self, name):
        (self.base / f"{name}.go").touch()

    def applies(self):
        return sum(json.loads(l)["phase"] == "apply_enter" for p in self.base.glob("*.trace")
                   for l in p.read_text(encoding="utf-8").splitlines())

    def assert_tail_appended(self, before, after_bytes, kinds):
        self.assertTrue(after_bytes.startswith(before), "historical event bytes changed")
        tail = jsonl_by_lf(after_bytes[len(before):])
        self.assertEqual([e["event_type"] for e in tail], kinds)


class GateChecks(Base):
    """Independent F1/F2/F3 reproductions on the pinned R-006 runtime; expected PASS."""

    def test_F3_crash_after_commit_point_then_late_writers_and_fresh_recovery(self):
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.build_closable()
        s0 = self.raw("PRE_closable")
        ev0 = self._events_bytes
        self.assertIsNone(self.run_actor("crasher", "close", "crash_after_move", exit_code=77))
        self.assertTrue((self.base / "crasher.moved").exists())
        s1 = self.raw("after_crash_at_commit_point")
        self.assertEqual((s1["active"], s1["completed"]), (False, True))
        self.assertEqual(s1["task_status"], s0["task_status"])
        self.assertNotEqual(s1["task_status"], "COMPLETED")
        self.assertEqual((s1["files"], s1["target_hex"]), (s0["files"], POST.hex()))
        self.assertEqual(TaskStore(self.storage).completion_state(TASK), "MOVED_STATUS_PENDING")
        late = self.run_actor("late_writer", "mutate", op="op_late")
        self.assertEqual(late["result"], "REFUSED", late)
        replay = self.run_actor("pending_replay", "mutate", op="op1")
        self.assertEqual((replay["result"], replay["receipt"]), ("REPLAYED", self.receipt))
        with self.assertRaises(TaskStoreError):
            TaskStore(self.storage).create_microtask(TASK, "late", "late", microtask_id="m_late")
        with self.assertRaises(TaskStoreError):
            TaskStore(self.storage).set_microtask_status(TASK, "m1", "DONE")
        s2 = self.raw("after_late_writers")
        self.assertEqual((s2["files"], s2["target_hex"], s2["task_status"]), (s1["files"], POST.hex(), s1["task_status"]))
        rec = self.run_actor("fresh_recover", "close")
        self.assertEqual((rec["result"], rec["resumed"]), ("COMPLETED", "MOVED_STATUS_PENDING"), rec)
        s3 = self.raw("after_fresh_recovery")
        self.assertEqual((s3["completed"], s3["task_status"], s3["target_hex"]), (True, "COMPLETED", POST.hex()))
        self.assert_tail_appended(ev0, self._events_bytes, ["TASK_COMPLETED"])
        again = self.run_actor("again", "close")
        self.assertEqual(again["result"], "REJECTED", again)
        self.assertEqual(self.applies(), 1)

    @unittest.skipUnless(sys.platform == "win32", "native Windows sharing semantics")
    def test_F1_native_pre_move_handle_from_other_process_refuses_then_fresh_retry(self):
        self.build_closable()
        s0 = self.raw("PRE_closable")
        ev0 = self._events_bytes
        handle = (self.location() / "task.md").open("rb")  # parent process: no FILE_SHARE_DELETE
        try:
            out = self.run_actor("closer", "close", exit_code=2)
        finally:
            handle.close()
        kinds = [c["type"] for c in out["error"]]
        self.assertEqual(kinds[0], "CloseoutError", out)
        self.assertEqual(kinds[-1], "PermissionError", out)
        self.assertIn(out["error"][-1]["winerror"], (5, 32))
        self.assertEqual(self.raw("after_native_pre_move_refusal"), s0 | {})
        retry = self.run_actor("fresh_retry", "close")
        self.assertEqual((retry["result"], retry["resumed"]), ("COMPLETED", None), retry)
        s2 = self.raw("after_retry")
        self.assertEqual((s2["completed"], s2["task_status"], s2["target_hex"]), (True, "COMPLETED", POST.hex()))
        self.assert_tail_appended(ev0, self._events_bytes, ["TASK_COMPLETED"])
        replay = self.run_actor("historical_replay", "mutate", op="op1")
        self.assertEqual((replay["result"], replay["receipt"]), ("REPLAYED", self.receipt))
        self.assertEqual(self.applies(), 1)

    @unittest.skipUnless(sys.platform == "win32", "native Windows sharing semantics")
    def test_F1_native_post_move_status_refusal_then_fresh_recovery(self):
        from web_alarm.task_store import TaskStore
        self.build_closable()
        s0 = self.raw("PRE_closable")
        ev0 = self._events_bytes
        closer = self.start("closer", "close", "pause_after_move")
        self.wait_phase("closer", "moved", closer)
        handle = (self.storage / "tasks/completed" / TASK / "task.json").open("rb")
        try:
            self.go("closer")
            out = self.finish("closer", closer, exit_code=2)
        finally:
            handle.close()
        self.assertEqual(out["error"][-1]["type"], "PermissionError", out)
        self.assertIn(out["error"][-1]["winerror"], (5, 32))
        s1 = self.raw("status_pending")
        self.assertEqual((s1["active"], s1["completed"], s1["task_status"]), (False, True, s0["task_status"]))
        self.assertEqual((s1["files"], s1["events_sha256"]), (s0["files"], s0["events_sha256"]))
        self.assertEqual(TaskStore(self.storage).completion_state(TASK), "MOVED_STATUS_PENDING")
        self.assertEqual(self.run_actor("late", "mutate", op="op_late")["result"], "REFUSED")
        replay = self.run_actor("pending_replay", "mutate", op="op1")
        self.assertEqual((replay["result"], replay["receipt"]), ("REPLAYED", self.receipt))
        self.assertEqual(self.raw("after_late_and_replay")["files"], s1["files"])
        rec = self.run_actor("recover", "close")
        self.assertEqual((rec["result"], rec["resumed"]), ("COMPLETED", "MOVED_STATUS_PENDING"), rec)
        s2 = self.raw("recovered")
        self.assertEqual((s2["task_status"], s2["target_hex"]), ("COMPLETED", POST.hex()))
        self.assert_tail_appended(ev0, self._events_bytes, ["TASK_COMPLETED"])
        self.assertEqual(self.run_actor("again", "close")["result"], "REJECTED")
        self.assertEqual(self.applies(), 1)

    def test_F2_direct_close_cannot_interleave_inflight_apply(self):
        from web_alarm.closeout import CloseoutError, CloseoutService
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.build()
        writer = self.start("writer", "mutate", "pause_in_apply", op="op_a")
        self.wait_phase("writer", "in_apply", writer)
        t0 = time.monotonic()
        with self.assertRaises(TaskStoreError) as direct:
            TaskStore(self.storage, lock_timeout=0.3).complete_task(TASK)
        with self.assertRaises(CloseoutError) as gated:
            CloseoutService(self.storage, lock_timeout=0.3).complete(TASK)
        self.facts.append({"direct_close_during_apply": chain(direct.exception),
                           "gated_close_during_apply": chain(gated.exception),
                           "blocked_seconds": round(time.monotonic() - t0, 3)})
        self.assertIn("timeout", str(direct.exception).lower())
        mid = self.raw("while_apply_paused")
        self.assertEqual((mid["active"], mid["target_hex"], mid["ops"]["op_a"][0]), (True, PRE.hex(), "STARTED"))
        self.go("writer")
        res = self.finish("writer", writer)
        self.assertEqual(res["result"], "EXECUTED", res)
        self.assertEqual(TaskStore(self.storage).complete_task(TASK).status.value, "COMPLETED")
        late = self.run_actor("late", "mutate", op="op_b")
        self.assertEqual(late["result"], "REFUSED", late)
        replay = self.run_actor("replay", "mutate", op="op_a")
        self.assertEqual((replay["result"], replay["receipt"]), ("REPLAYED", res["receipt"]))
        end = self.raw("terminal")
        self.assertEqual((end["completed"], end["target_hex"], sorted(end["ops"])), (True, POST.hex(), ["op_a"]))
        self.assertEqual(self.applies(), 1)

    def test_F2_direct_close_first_blocks_executor_before_intent_then_refuses(self):
        self.build()
        closer = self.start("closer", "direct_close", "pause_before_move")
        self.wait_phase("closer", "before_move", closer)
        writer = self.start("writer", "mutate", op="op_w")
        self.wait_phase("writer", "actor_enter", writer)
        time.sleep(1.0)
        mid = self.raw("closer_holds_locks_writer_waiting")
        self.assertIsNone(writer.poll(), "executor did not wait for the TASK locks")
        self.assertEqual((mid["active"], mid["ops"], mid["target_hex"]), (True, {}, PRE.hex()))
        self.go("closer")
        self.assertEqual(self.finish("closer", closer)["status"], "COMPLETED")
        res = self.finish("writer", writer)
        self.assertEqual(res["result"], "REFUSED", res)
        end = self.raw("terminal")
        self.assertEqual((end["completed"], end["ops"], end["target_hex"]), (True, {}, PRE.hex()))
        self.assertEqual(self.applies(), 0)

    def test_F2_process_death_after_durable_DONE_replays_receipt_without_second_apply(self):
        self.build()
        self.assertIsNone(self.run_actor("dier", "mutate", "crash_after_done", exit_code=79, op="op_d"))
        mid = self.raw("after_death_post_DONE")
        self.assertEqual((mid["ops"]["op_d"][0], mid["target_hex"]), ("DONE", POST.hex()))
        receipt = mid["ops"]["op_d"][1]
        self.assertEqual(receipt["sha256"], sha(POST))
        replay = self.run_actor("fresh", "mutate", op="op_d")
        self.assertEqual((replay["result"], replay["receipt"]), ("REPLAYED", receipt))
        self.assertEqual(self.raw("after_replay")["target_hex"], POST.hex())
        self.assertEqual(self.applies(), 1, "a fresh delivery must not enter physical apply again")


def before_function(module_file, name):
    """Pre-R-006 method source from the byte copy preserved in evidence.zip (RAM-only control)."""
    with zipfile.ZipFile(PKG / "evidence.zip") as zf:
        text = zf.read("sources/before/" + module_file).decode("utf-8")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            lines = text.splitlines(keepends=True)
            src = "".join(lines[node.lineno - 1:node.end_lineno])
            indent = len(src) - len(src.lstrip())
            return "\n".join(l[indent:] if l.strip() else l for l in src.splitlines())
    raise LookupError(name)


class FindingProbes(Base):
    """Adversarial invariants; a FAIL is a reproducible defect, recorded as FINDING."""

    def test_P1_admitted_request_with_U2028_in_target_keeps_event_history_readable(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.server import ApiError, WebAlarmApi
        self.build()
        s0 = self.raw("PRE")
        body = {"microtask_id": "m1", "operation_id": "op_u", "action": "write", "target": "x\u2028y.bin",
                "payload": {"encoding": "base64", "data": base64.b64encode(POST).decode("ascii")}}
        try:
            status, reply = WebAlarmApi(self.storage).dispatch("POST", f"/tasks/{TASK}/mutations", body)
            http = {"status": status, "result": reply.get("result"), "result_code": reply.get("result_code")}
        except ApiError as exc:
            details = exc.details if isinstance(exc.details, dict) else {}
            http = {"api_error": exc.status, "code": exc.code, "result_code": details.get("result_code"),
                    "next_safe_action": str(details.get("next_safe_action"))[:200]}
        self.facts.append({"http_mutation_with_U+2028_target": http})
        s1 = self.raw("after_request")
        raw_events = self._events_bytes
        self.facts.append({"U+2028_bytes_in_events": raw_events.count("\u2028".encode()),
                           "LF_records_parse": len(jsonl_by_lf(raw_events))})
        history = {}
        try:
            history["read_events"] = len(EventCheckpointStore(self.storage).read_events(TASK))
        except Exception as exc:
            history["read_events_error"] = chain(exc)
        try:
            verdict = CloseoutService(self.storage).inspect(TASK)
            history["closeout_inspect"] = {"eligible": verdict["eligible"],
                                           "blockers": [b["code"] for b in verdict["blockers"]]}
        except Exception as exc:
            history["closeout_inspect_error"] = chain(exc)
        self.facts.append({"history_after_U+2028": history, "target_unchanged": s1["target_hex"] == s0["target_hex"]})
        self.assertIn("read_events", history, "a server-accepted request made the TASK event history unreadable")

    def test_P1c_verification_evidence_with_U2029_keeps_event_history_readable(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.server import ApiError, WebAlarmApi
        self.build()
        api, replies = WebAlarmApi(self.storage), []
        for status, evidence in (("DONE", None), ("VERIFIED", "checked by agent all targets match")):
            body = {"task_id": TASK, "target_status": status}
            if evidence:
                body["verification_evidence"] = evidence
            try:
                code, reply = api.dispatch("POST", "/microtasks/m1/transition", body)
                replies.append({"status": code, "to": status})
            except ApiError as exc:
                replies.append({"api_error": exc.status, "code": exc.code, "to": status})
        history = {}
        try:
            history["read_events"] = len(EventCheckpointStore(self.storage).read_events(TASK))
        except Exception as exc:
            history["read_events_error"] = chain(exc)[0]["message"]
        try:
            v = CloseoutService(self.storage).inspect(TASK)
            history["closeout_inspect"] = {"eligible": v["eligible"], "blockers": [b["code"] for b in v["blockers"]]}
        except Exception as exc:
            history["closeout_inspect_error"] = chain(exc)[0]
        try:
            done = CloseoutService(self.storage).complete(TASK)
            history["closeout_complete"] = {k: done.get(k) for k in ("result", "event_recorded", "resumed")}
        except Exception as exc:
            history["closeout_complete_error"] = chain(exc)[0]
        self.raw("after_verified_with_U+2029_and_closeout")
        self.facts.append({"http_transitions": replies, "history": history,
                           "U+2029_bytes_in_events": self._events_bytes.count(" ".encode()),
                           "LF_records_parse": len(jsonl_by_lf(self._events_bytes))})
        self.assertIn("read_events", history, "normal verification evidence made the TASK history unreadable")

    def test_P1b_payload_separators_unit_level(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        self.build()
        store = EventCheckpointStore(self.storage)
        outcome = {}
        for label, ch in (("U+0085", "\u0085"), ("U+2028", "\u2028"), ("U+2029", "\u2029"), ("U+000B", "\u000b")):
            store.append_event(TASK, "CLAUDE_PROBE", payload={"note": "a" + ch + "b"})
            try:
                store.read_events(TASK)
                outcome[label] = "READABLE"
            except Exception as exc:
                outcome[label] = chain(exc)[0]["message"]
                # restore readable history for the next character (TEMP fixture only)
                path = self.location() / "events.jsonl"
                data = path.read_bytes()
                path.write_bytes(data[:data.rstrip(b"\n").rfind(b"\n") + 1])
        self.facts.append({"append_then_read_by_separator": outcome})
        self.assertEqual({k: v for k, v in outcome.items() if v != "READABLE"}, {},
                         "writer emits a record its own reader cannot frame")

    def test_P2_refused_admission_on_torn_history_persists_no_operation_record(self):
        from web_alarm.mutation_executor import MutationExecutor
        self.build()
        path = self.location() / "events.jsonl"
        data = path.read_bytes()
        self.assertTrue(data.endswith(b"\n"))
        path.write_bytes(data[:-1])  # complete JSON record without its delimiter (crash shape)
        s0 = self.raw("torn_PRE")
        try:
            res = MutationExecutor(self.storage).execute(TASK, "m1", "op_new", "write", "data.bin", payload=POST)
            outcome = {"returned": {k: res.get(k) for k in ("result", "result_code")}}
        except Exception as exc:
            outcome = {"raised": chain(exc)}
        s1 = self.raw("torn_after_new_admission")
        payload_files = sorted(p.relative_to(self.storage).as_posix() for p in self.storage.rglob("*")
                               if p.is_file() and "payload" in p.as_posix().lower())
        self.facts.append({"new_admission_on_torn_history": outcome, "payload_files": payload_files,
                           "new_files": sorted(set(s1["files"]) - set(s0["files"])),
                           "events_unchanged": s1["events_sha256"] == s0["events_sha256"]})
        follow = {}
        if "operations/op_new.json" in s1["files"]:
            path.write_bytes(path.read_bytes() + b"\n")  # operator repairs only the delimiter (TEMP fixture)
            from web_alarm.closeout import CloseoutService
            from web_alarm.operation_store import OperationStore
            try:
                OperationStore(self.storage).get(TASK, "op_new")
                follow["get_after_delimiter_repair"] = "READABLE"
            except Exception as exc:
                follow["get_after_delimiter_repair"] = chain(exc)[0]["message"]
            try:
                v = CloseoutService(self.storage).inspect(TASK)
                follow["closeout_inspect"] = [b["code"] for b in v["blockers"]]
            except Exception as exc:
                follow["closeout_inspect_error"] = chain(exc)[0]
        self.facts.append({"after_delimiter_repair": follow})
        self.assertEqual(sorted(set(s1["files"]) - set(s0["files"])), [],
                         "a refused admission left a durable operation record without history")

    def test_P6_torn_history_without_operations_does_not_become_clean_completion(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.state_machine import ServerStateMachine
        self.build()
        machine = ServerStateMachine(self.storage)
        machine.transition(TASK, "m1", "DONE")
        machine.transition(TASK, "m1", "VERIFIED", verification_evidence="Claude probe: no mutation needed")
        path = self.location() / "events.jsonl"
        data = path.read_bytes()
        path.write_bytes(data[:-1])  # complete JSON record without its delimiter (crash shape)
        s0 = self.raw("torn_no_operations_PRE")
        try:
            done = CloseoutService(self.storage).complete(TASK)
            outcome = {k: done.get(k) for k in ("result", "event_recorded", "resumed")}
        except Exception as exc:
            outcome = {"raised": chain(exc)[0]}
        s1 = self.raw("torn_no_operations_after_closeout")
        self.facts.append({"closeout_on_torn_history_without_operations": outcome,
                           "events_bytes_unchanged": s1["events_sha256"] == s0["events_sha256"]})
        self.assertNotEqual(outcome.get("result"), "COMPLETED",
                            "torn (unterminated) history became a clean completion when the TASK had no operations")

    def test_P3_crash_between_intent_record_and_intent_event_is_recoverable(self):
        from web_alarm.closeout import CloseoutService
        from web_alarm.operation_store import OperationStore
        self.build()
        self.assertIsNone(self.run_actor("dier", "mutate", "crash_before_intent", exit_code=78, op="op_c"))
        s1 = self.raw("after_crash_before_intent_event")
        intent_events = [e for e in jsonl_by_lf(self._events_bytes)
                         if e.get("operation_id") == "op_c" and e["event_type"] == "OPERATION_INTENT"]
        self.facts.append({"op_c_record": s1["ops"].get("op_c"), "op_c_intent_events": len(intent_events)})
        replay = self.run_actor("replay", "mutate", op="op_c")
        follow = {"replay": replay}
        try:
            OperationStore(self.storage).get(TASK, "op_c")
            follow["get"] = "READABLE"
        except Exception as exc:
            follow["get"] = chain(exc)[0]["message"]
        try:
            v = CloseoutService(self.storage).inspect(TASK)
            follow["closeout_inspect"] = [b["code"] for b in v["blockers"]]
        except Exception as exc:
            follow["closeout_inspect_error"] = chain(exc)[0]
        self.facts.append({"follow_up": follow, "applies": self.applies(),
                           "target_unchanged": s1["target_hex"] == PRE.hex()})
        self.assertEqual(follow["get"], "READABLE",
                         "crash window leaves an operation no server API can read, settle or abort")

    def test_P4_invalid_ids_create_no_lock_files_in_restore_point_preparation(self):
        from web_alarm import cli
        from web_alarm.manifest_store import ManifestSnapshotStore as ManifestStore
        self.build()
        before = self.lock_files()
        seen = {}
        for label, call in (
            ("prepare_microtask", lambda: ManifestStore(self.storage).prepare_microtask("..", "zz_p", [("data.bin", "edit")])),
            ("reconcile_interrupted_preparation", lambda: ManifestStore(self.storage).reconcile_interrupted_preparation("..", "zz_r")),
        ):
            try:
                seen[label] = {"returned": str(call())[:200]}
            except Exception as exc:
                seen[label] = {"raised": chain(exc)[0]}
        with mock.patch("sys.stderr"), mock.patch("sys.stdout"):
            seen["cli_microtask_prepare"] = {"exit": cli.main(["--storage-root", str(self.storage), "microtask", "prepare",
                                                               "--task-id", "..", "--microtask-id", "zz_cli",
                                                               "--target", "data.bin=edit"])}
        after = self.lock_files()
        # Observation only (not asserted): whitespace-padded TASK ids map to different operations-lock files.
        from web_alarm.operation_store import OperationStore
        with OperationStore(self.storage).task_lock(" " + TASK):
            ws_lock = sorted(set(self.lock_files()) - set(after))
        self.facts.append({"calls": seen, "locks_before": before, "locks_after": after,
                           "new_lock_files": sorted(set(after) - set(before)),
                           "observation_operations_lock_for_space_prefixed_id": ws_lock or "reused existing",
                           "observation_taskstore_complete_task_would_use": f"locks/operations/ {TASK}.lock"})
        self.assertEqual(sorted(set(after) - set(before)), [], "invalid TASK id created a lock file before validation")

    @unittest.skipUnless(sys.platform == "win32", "Win32 trailing-dot/space and case-insensitive aliasing")
    def test_P5_windows_alias_task_ids_are_refused_and_old_loader_was_exposed(self):
        import web_alarm.task_store as ts
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.mutation_executor import MutationExecutor
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.build()
        s0 = self.raw("PRE")
        locks0 = self.lock_files()
        current = {}
        for alias in (TASK + ".", TASK + " ", TASK.upper()):
            row = {"dir_resolves_to_real_TASK": (self.storage / "tasks/active" / alias / "task.json").is_file()}
            try:
                TaskStore(self.storage).open_task(alias)
                row["open_task"] = "ACCEPTED"
            except TaskStoreError as exc:
                row["open_task"] = str(exc)[:120]
            try:
                EventCheckpointStore(self.storage).append_event(alias, "CLAUDE_ALIAS_PROBE")
                row["append_event"] = "ACCEPTED"
            except Exception as exc:
                row["append_event"] = type(exc).__name__
            if alias.strip() == alias:  # the executor strips whitespace by design (same TASK, same locks)
                res = MutationExecutor(self.storage).execute(alias, "m1", "op_alias", "write", "data.bin", payload=POST)
                row["execute"] = (res["result"], res.get("result_code"))
            current[alias] = row
        s1 = self.raw("after_alias_attempts_R006")
        self.facts.append({"R006_alias_attempts": current, "new_lock_files": sorted(set(self.lock_files()) - set(locks0))})
        # RAM control: the pre-R-006 TASK loader (from evidence.zip 'before' bytes) accepts the alias
        namespace = dict(vars(ts))
        exec(compile(before_function("web_alarm/task_store.py", "_load_task_from"), "before:_load_task_from", "exec"),
             namespace)
        with mock.patch.object(TaskStore, "_load_task_from", namespace["_load_task_from"]):
            try:
                EventCheckpointStore(self.storage).append_event(TASK + ".", "CLAUDE_ALIAS_PROBE_OLD")
                old = "ACCEPTED"
            except Exception as exc:
                old = type(exc).__name__
        s2 = self.raw("after_old_loader_control")
        foreign = [e["task_id"] for e in jsonl_by_lf(self._events_bytes) if e["task_id"] != TASK]
        try:
            EventCheckpointStore(self.storage).read_events(TASK)
            real_history = "READABLE"
        except Exception as exc:
            real_history = str(exc)[:120]
        self.facts.append({"old_loader_append_via_alias": old, "foreign_task_ids_in_real_history": foreign,
                           "real_history_after_old_alias_append": real_history})
        # R-006 runtime: every alias refused with zero byte change
        for alias, row in current.items():
            self.assertNotEqual(row["open_task"], "ACCEPTED", alias)
            self.assertNotEqual(row["append_event"], "ACCEPTED", alias)
            if "execute" in row:
                self.assertEqual(row["execute"][0], "REFUSED", alias)
        self.assertEqual((s1["files"], s1["events_sha256"], s1["target_hex"]), (s0["files"], s0["events_sha256"], s0["target_hex"]))
        # Control: the old loader really was exposed (foreign-id event injected into the real history)
        self.assertEqual(old, "ACCEPTED")
        self.assertEqual(foreign, [TASK + "."])


if __name__ == "__main__":
    unittest.main()
