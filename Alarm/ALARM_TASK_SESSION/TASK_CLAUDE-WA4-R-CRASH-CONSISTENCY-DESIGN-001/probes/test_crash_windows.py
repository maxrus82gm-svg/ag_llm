"""Crash-window probes, CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 (disposable TEMP only).

W1 = AUD-02b-R: microtask status CAS durable -> process dies -> MICROTASK_TRANSITION missing.
W2 = AUD-03:    operation INTENT record durable -> process dies -> OPERATION_INTENT missing.

Each fault runs in its own child process (crash_worker.py) that re-reads the durable record from disk
right before os._exit, so the reached phase is proven, not assumed. A second, unpatched process
(reopen_inspector.py) re-opens the storage and reports raw bytes + server views + follow-up steps.

Test name prefixes state what a result means:
  CONTROL_   healthy run without fault: must PASS
  TRIGGER_   the fault phase was really reached: must PASS
  SAFETY_    no false-safe outcome (no apply, no completion, target unchanged): must PASS
  INVARIANT_ the contract a fix must provide; a FAIL here is the reproduced defect (expected today)
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TASK = "task_cc"
PRE = b"CC-PRE\r\n\x01"
POST = b"CC-POST\n\x02"


def body(op: str, data: bytes = POST) -> dict:
    return {"microtask_id": "m1", "operation_id": op, "action": "write", "target": "data.bin",
            "payload": {"encoding": "base64", "data": base64.b64encode(data).decode("ascii")}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_crash_cc_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.storage, self.project = self.base / "state", self.base / "project"
        self.facts = [{"task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001", "test": self.id()}]
        self.calls = 0

    def build(self, upto: str = "ACTIVE") -> None:
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.project.mkdir()
        (self.project / "data.bin").write_bytes(PRE)
        WorkspaceRegistry(self.storage).register("cc", self.project, workspace_id="ws_cc")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_cc", "cc", "synthetic RAW TASK for crash windows", "probe", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        for step in {"READY": ["READY"], "ACTIVE": ["READY", "ACTIVE"], "DONE": ["READY", "ACTIVE", "DONE"]}[upto]:
            machine.transition(TASK, "m1", step)

    def _cfg(self, **cfg) -> Path:
        self.calls += 1
        path = self.base / f"cfg_{self.calls}.json"
        path.write_text(json.dumps(dict(cfg, storage=str(self.storage), task=TASK, base=str(self.base),
                                        project=str(self.project))), encoding="utf-8")
        return path

    def worker(self, name: str, mode: str, action: str, **cfg) -> dict:
        path = self._cfg(name=name, mode=mode, action=action, **cfg)
        proc = subprocess.run([sys.executable, "-B", str(HERE / "crash_worker.py"), str(REPO), str(path)],
                              capture_output=True, timeout=180)
        trace_path = self.base / f"{name}.trace.jsonl"
        trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] \
            if trace_path.exists() else []
        out = proc.stdout.decode(errors="replace").strip().splitlines()
        result = {"exit": proc.returncode, "stdout": json.loads(out[-1]) if out else None,
                  "phases": [t["phase"] for t in trace], "trace": trace,
                  "stderr_tail": proc.stderr.decode(errors="replace")[-400:]}
        self.facts.append({f"worker:{name}": {k: v for k, v in result.items() if k != "stderr_tail"}})
        return result

    def reopen(self, *followups: dict) -> dict:
        path = self._cfg(followups=list(followups))
        proc = subprocess.run([sys.executable, "-B", str(HERE / "reopen_inspector.py"), str(REPO), str(path)],
                              capture_output=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace")[-1500:])
        report = json.loads(proc.stdout.decode().strip().splitlines()[-1])
        self.facts.append({f"reopen_{self.calls}": report})
        return report

    def applies(self) -> int:
        return sum(1 for p in self.base.glob("*.trace.jsonl")
                   for line in p.read_text(encoding="utf-8").splitlines() if '"apply_enter"' in line)

    @staticmethod
    def transitions(raw: dict, microtask: str = "m1") -> list:
        return [[e[3], e[4], e[5]] for e in raw["events"] if e[0] == "MICROTASK_TRANSITION" and e[1] == microtask]


class W1StatusEventWindow(Fixture):
    """AUD-02b-R: status CAS persisted, process dead before MICROTASK_TRANSITION."""

    def test_CONTROL_healthy_steps_record_events_and_close(self):
        self.build("ACTIVE")
        done = self.worker("done", "none", "transition", microtask="m1", target="DONE")
        report = self.reopen({"kind": "transition", "microtask": "m1", "target": "VERIFIED",
                              "extra": {"verification_evidence": "control evidence"}},
                             {"kind": "closeout"})
        self.assertEqual((done["exit"], done["stdout"]["http"], done["stdout"]["event_recorded"]), (0, 200, True))
        final = report["followups"][-1]
        self.assertEqual(final["outcome"]["ok"]["result"], "COMPLETED")
        self.assertEqual(self.transitions(final["raw_after"])[-2:],
                         [["ACTIVE", "DONE", False], ["DONE", "VERIFIED", True]])

    def crash_done(self) -> dict:
        self.build("ACTIVE")
        return self.worker("crash_done", "crash_after_status", "transition", microtask="m1", target="DONE")

    def test_TRIGGER_process_dies_after_durable_DONE_before_its_event(self):
        crash = self.crash_done()
        report = self.reopen()
        raw = report["before"]["raw"]
        self.assertEqual(crash["exit"], 70, crash["stderr_tail"])
        self.assertEqual(crash["phases"], ["actor_enter", "status_persisted_event_pending"])
        self.assertEqual(crash["trace"][-1]["persisted_status"], "DONE")
        self.assertEqual(raw["microtasks"]["m1"], "DONE")
        self.assertNotIn(["ACTIVE", "DONE", False], self.transitions(raw))
        self.assertTrue(raw["events_terminated"])
        self.assertEqual(raw["events_invalid_lines"], 0)

    def test_INVARIANT_reopen_reports_a_status_without_its_event(self):
        self.crash_done()
        views = self.reopen()["before"]["views"]
        codes = views["projection"].get("blockers", []) + views["projection"].get("diagnostics", [])
        self.assertTrue([c for c in codes if "EVENT" in c or "HISTORY" in c or "UNRECORDED" in c],
                        f"a persisted status without its history event is invisible after reopen: {codes}")

    def test_INVARIANT_verified_without_recorded_evidence_never_closes(self):
        self.build("DONE")
        crash = self.worker("crash_verified", "crash_after_status", "transition", microtask="m1",
                            target="VERIFIED", extra={"verification_evidence": "evidence that will be lost"})
        report = self.reopen({"kind": "closeout"})
        raw = report["followups"][0]["raw_after"]
        outcome = report["followups"][0]["outcome"]
        self.assertEqual(crash["exit"], 70)
        self.assertEqual(crash["trace"][-1]["persisted_status"], "VERIFIED")
        self.facts.append({"verified_events_with_evidence": [t for t in self.transitions(raw) if t[2]],
                           "closeout": outcome})
        self.assertFalse([t for t in self.transitions(raw) if t[1] == "VERIFIED"], "precondition: no event")
        self.assertNotEqual((outcome.get("ok") or {}).get("result"), "COMPLETED",
                            "closeout completed a TASK whose VERIFIED stage has no recorded verification evidence")

    def test_TRIGGER_activation_dies_after_durable_ACTIVE_and_plan_pointer(self):
        self.build("READY")
        crash = self.worker("crash_active", "crash_after_status", "transition", microtask="m1", target="ACTIVE")
        report = self.reopen({"kind": "mutate", "body": body("op_after_lost_activation")})
        before, after = report["before"]["raw"], report["followups"][0]["raw_after"]
        self.facts.append({"activation_lost_event_then_mutation": report["followups"][0]["outcome"]})
        self.assertEqual(crash["exit"], 70)
        self.assertEqual((before["microtasks"]["m1"], before["plan_current"]), ("ACTIVE", "m1"))
        self.assertNotIn(["READY", "ACTIVE", False], self.transitions(before))
        self.assertEqual(after["target_sha256"] != before["target_sha256"],
                         report["followups"][0]["outcome"].get("result") == "EXECUTED")

    def test_CONTROL_injected_exception_is_reported_but_leaves_the_same_divergence(self):
        self.build("ACTIVE")
        injected = self.worker("raise_done", "raise_after_status", "transition", microtask="m1", target="DONE")
        raw = self.reopen()["before"]["raw"]
        self.assertEqual(injected["exit"], 0)
        self.assertEqual((injected["stdout"]["http"], injected["stdout"]["event_recorded"]), (200, False))
        self.assertIn("injected", injected["stdout"]["history_error"])
        self.assertEqual(raw["microtasks"]["m1"], "DONE")
        self.assertNotIn(["ACTIVE", "DONE", False], self.transitions(raw))


class W2IntentEventWindow(Fixture):
    """AUD-03: durable INTENT record, process dead before OPERATION_INTENT."""

    def test_CONTROL_healthy_mutation_records_intent_and_executes_once(self):
        self.build("ACTIVE")
        run = self.worker("ok", "none", "mutate", body=body("op_ok"))
        report = self.reopen()
        raw = report["before"]["raw"]
        self.assertEqual((run["exit"], run["stdout"]["http"], run["stdout"]["result"]), (0, 200, "EXECUTED"))
        self.assertEqual(self.applies(), 1)
        self.assertIn(["OPERATION_INTENT", "m1", "op_ok", None, None, False], raw["events"])
        self.assertEqual(report["before"]["views"]["operations_list"], {"ok": ["op_ok"]})

    def crash_intent(self, op: str = "op_c") -> dict:
        return self.worker("crash_intent", "crash_after_intent", "mutate", body=body(op))

    def test_TRIGGER_process_dies_after_durable_INTENT_before_its_event(self):
        self.build("ACTIVE")
        crash = self.crash_intent()
        raw = self.reopen()["before"]["raw"]
        self.assertEqual(crash["exit"], 78, crash["stderr_tail"])
        self.assertEqual(crash["phases"], ["actor_enter", "intent_persisted_event_pending"])
        self.assertEqual((crash["trace"][-1]["persisted_status"], crash["trace"][-1]["revision"]), ("INTENT", 1))
        self.assertEqual(raw["operations"], {"op_c": {"status": "INTENT", "revision": 1, "settlement": None}})
        self.assertFalse([e for e in raw["events"] if e[0] == "OPERATION_INTENT"])
        self.assertEqual(self.applies(), 0)

    def test_SAFETY_reopen_never_turns_the_orphan_into_a_mutation_or_a_closed_task(self):
        self.build("ACTIVE")
        self.crash_intent()
        report = self.reopen({"kind": "mutate", "body": body("op_c")},
                             {"kind": "recover"},
                             {"kind": "transition", "microtask": "m1", "target": "DONE"},
                             {"kind": "transition", "microtask": "m1", "target": "VERIFIED",
                              "extra": {"verification_evidence": "after orphan"}},
                             {"kind": "closeout"})
        steps = {f["step"] + str(i): f["outcome"] for i, f in enumerate(report["followups"])}
        final = report["followups"][-1]["raw_after"]
        self.facts.append({"steps": steps})
        self.assertEqual(self.applies(), 0, "a physical apply happened for an operation of unknown fate")
        self.assertEqual(final["target_sha256"], report["before"]["raw"]["target_sha256"])
        self.assertEqual(final["operations"]["op_c"]["status"], "INTENT")
        self.assertNotEqual(steps["mutate0"].get("result"), "EXECUTED")
        self.assertNotEqual((steps["closeout4"].get("ok") or {}).get("result"), "COMPLETED",
                            "a TASK with an unreadable operation was completed")
        self.assertEqual(final["location"], "active")

    def test_INVARIANT_orphan_intent_has_a_server_recovery_path(self):
        self.build("ACTIVE")
        self.crash_intent()
        report = self.reopen({"kind": "get_operation", "operation": "op_c"},
                             {"kind": "resolve", "microtask": "m1", "operation": "op_c", "action": "ABORT",
                              "revision": 1, "evidence_fingerprint": "0" * 64},
                             {"kind": "recover"})
        outcomes = [f["outcome"] for f in report["followups"]]
        self.facts.append({"recovery_paths": outcomes})
        self.assertTrue(any("ok" in o and o["ok"] not in (None, False) for o in outcomes[:2]),
                        "no server API can read, settle or abort an INTENT whose event was lost: dead end")

    def test_INVARIANT_a_lost_intent_event_does_not_blind_the_rest_of_the_task(self):
        self.build("ACTIVE")
        healthy = self.worker("first", "none", "mutate", body=body("op_a", b"FIRST"))
        self.crash_intent("op_b")
        views = self.reopen()["before"]["views"]
        self.facts.append({"healthy_first": healthy["stdout"], "views": views})
        self.assertEqual(healthy["stdout"]["result"], "EXECUTED")
        self.assertIn("ok", views["operations_list"],
                      "one orphan INTENT makes every operation of the TASK unreadable (TASK-wide blast radius)")

    def test_INVARIANT_injected_intent_event_failure_leaves_no_unreadable_orphan(self):
        self.build("ACTIVE")
        injected = self.worker("raise_intent", "raise_after_intent", "mutate", body=body("op_r"))
        report = self.reopen({"kind": "get_operation", "operation": "op_r"})
        self.facts.append({"injected": injected["stdout"], "get": report["followups"][0]["outcome"]})
        self.assertEqual(injected["exit"], 0)
        self.assertEqual(self.applies(), 0)
        self.assertIn("ok", report["followups"][0]["outcome"],
                      "an admission whose INTENT event failed (process alive) left an unreadable orphan record")


class W3OperationTransitionWindow(Fixture):
    """Comparison: the operation store already tolerates a missing post-INTENT event by design."""

    def test_TRIGGER_and_SAFETY_lost_DONE_event_is_tolerated_and_replay_never_reapplies(self):
        self.build("ACTIVE")
        crash = self.worker("crash_op_done", "crash_after_op_done", "mutate", body=body("op_d"))
        report = self.reopen({"kind": "mutate", "body": body("op_d")}, {"kind": "recover"})
        before = report["before"]
        replay = report["followups"][0]
        self.facts.append({"replay": replay["outcome"], "recover": report["followups"][1]["outcome"]})
        self.assertEqual(crash["exit"], 79, crash["stderr_tail"])
        self.assertEqual(crash["phases"], ["actor_enter", "apply_enter", "op_done_persisted_event_pending"])
        self.assertEqual((crash["trace"][-1]["persisted_status"], crash["trace"][-1]["receipt"]), ("DONE", True))
        self.assertEqual(before["raw"]["operations"]["op_d"]["status"], "DONE")
        self.assertFalse([e for e in before["raw"]["events"]
                          if e[0] == "OPERATION_TRANSITION" and e[2] == "op_d" and e[4] == "DONE"])
        self.assertEqual(before["views"]["operations_list"], {"ok": ["op_d"]},
                         "a lost post-INTENT event is a tolerated crash window (record is authority)")
        self.assertEqual(self.applies(), 1, "the replay re-applied an already executed mutation")
        self.assertEqual(replay["raw_after"]["target_sha256"], before["raw"]["target_sha256"])


if __name__ == "__main__":
    unittest.main()
