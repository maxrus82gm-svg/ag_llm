"""WA4-R repair CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001: durable state / event crash consistency.

AUD-02b-R (R-MT): a microtask status must never be VERIFIED-closable without recorded evidence, and a
transition interrupted between its write-ahead intent, the status compare-and-set and its commit event
is reconciled only from durable facts (status == to -> commit from the intent; status == from and the
record untouched -> abandon; anything else -> fail-closed contradiction, operator).
AUD-03 (R-OP): an INTENT rev1 record whose OPERATION_INTENT was lost stays readable as pending and is
reconciled deterministically from the record; no physical mutation is ever started or repeated by it.

Faults run in a separate Python process (CHILD) that really dies (os._exit) at an exact phase and
fsyncs a phase marker first; every follow-up runs in a fresh process. Oracles read raw bytes: the
microtask/operation JSON, the TASK history split on the physical LF, the workspace target, and the
count of real physical applies traced by every process.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK = "task_ccr"
PRE = b"CCR-PRE\r\n\x01"
POST = b"CCR-POST\n\x02"
EVIDENCE = "verified by inspection" + chr(0x2028) + "target matches"

CHILD = r'''
import json, os, sys, traceback
from pathlib import Path
from unittest import mock
sys.path.insert(0, sys.argv[1])
cfg = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
from web_alarm.event_checkpoint_store import EventCheckpointStore, EventCheckpointStoreError
from web_alarm.mutation_executor import MutationExecutor
from web_alarm.server import ApiError, WebAlarmApi
storage, base, name = Path(cfg["storage"]), Path(cfg["base"]), cfg["name"]
fault = cfg.get("fault") or {}
trace = base / "applies.jsonl"
marker = base / f"{name}.phase.jsonl"

def mark(phase, **facts):
    with marker.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(phase=phase, **facts)) + "\n")
        handle.flush()
        os.fsync(handle.fileno())

real_append = EventCheckpointStore.append_event
real_fsync = os.fsync
real_apply = MutationExecutor._apply
fsync_fail = {"armed": False}

def append(store, task_id, kind, **kw):
    if fault.get("event") == kind and fault.get("when") == "before":
        mark("died_before_append", event=kind)
        os._exit(70)
    if fault.get("event") == kind and fault.get("when") == "fsync_error":
        fsync_fail["armed"] = True
    if fault.get("event") == kind and fault.get("when") == "raise":
        raise EventCheckpointStoreError("injected: append failed")
    try:
        record = real_append(store, task_id, kind, **kw)
    finally:
        fsync_fail["armed"] = False
    if fault.get("event") == kind and fault.get("when") == "after":
        mark("died_after_append", event=kind)
        os._exit(71)
    return record

def fsync(fd):
    if fsync_fail["armed"]:
        fsync_fail["armed"] = False
        raise OSError(5, "injected fsync failure")
    return real_fsync(fd)

def apply(kind, path, data):
    with trace.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"process": name, "target": Path(path).name}) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return real_apply(kind, path, data)

results = []
with mock.patch.object(EventCheckpointStore, "append_event", append), \
     mock.patch("web_alarm.event_checkpoint_store.os.fsync", fsync), \
     mock.patch.object(MutationExecutor, "_apply", staticmethod(apply)):
    api = WebAlarmApi(storage)
    for step in cfg["steps"]:
        try:
            if step["kind"] == "http":
                status, reply = api.dispatch(step["method"], step["path"], step.get("body"))
                results.append({"http": status, "reply": json.loads(json.dumps(reply, default=str))})
            elif step["kind"] == "recover":
                from web_alarm.recovery_coordinator import RecoveryCoordinator
                out = RecoveryCoordinator(storage).recover(cfg["task"])
                results.append({"recover": {k: (v if isinstance(v, (str, int, bool, type(None), list)) else str(v))
                                             for k, v in out.items()}})
            elif step["kind"] == "closeout":
                from web_alarm.closeout import CloseoutService
                out = CloseoutService(storage).complete(cfg["task"])
                results.append({"closeout": {"result": out["result"],
                                             "blockers": [b["code"] for b in out["closeout"]["blockers"]],
                                             "event_recorded": out.get("event_recorded")}})
            elif step["kind"] == "projection":
                from web_alarm.projection import ProjectionService
                p = ProjectionService(storage).build(cfg["task"])
                results.append({"projection": {"blockers": [b["code"] for b in p["blockers"]],
                                               "diagnostics": [d["code"] for d in p["diagnostics"]],
                                               "closeout": [b["code"] for b in p["closeout"]],
                                               "recovery_state": p["recovery"]["state"],
                                               "next": p["next_safe_action"]}})
            elif step["kind"] == "list_operations":
                from web_alarm.operation_store import OperationStore
                results.append({"list": [r.operation_id for r in OperationStore(storage).list(cfg["task"])]})
            else:
                raise ValueError(step["kind"])
        except ApiError as exc:
            results.append({"http": exc.status, "code": exc.code, "message": str(exc)[:400],
                            "details": json.loads(json.dumps(exc.details, default=str)) if exc.details else None})
        except Exception as exc:
            results.append({"raised": type(exc).__name__, "message": str(exc)[:400],
                            "tb": traceback.format_exc()[-600:]})
print(json.dumps(results, ensure_ascii=True))
'''


def body(op: str, data: bytes = POST) -> dict:
    return {"microtask_id": "m1", "operation_id": op, "action": "write", "target": "data.bin",
            "payload": {"encoding": "base64", "data": base64.b64encode(data).decode("ascii")}}


def lf_records(data: bytes) -> list[dict]:
    assert data == b"" or data.endswith(b"\n"), "unterminated history"
    return [json.loads(chunk) for chunk in data.split(b"\n")[:-1]]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_ccr_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.storage, self.project = self.base / "state", self.base / "project"
        self.facts = [{"task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001", "test": self.id()}]
        self.calls = 0

    def build(self, upto: str = "ACTIVE", *, microtasks=("m1",)) -> None:
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.project.mkdir()
        (self.project / "data.bin").write_bytes(PRE)
        WorkspaceRegistry(self.storage).register("ccr", self.project, workspace_id="ws_ccr")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_ccr", "ccr", "synthetic RAW TASK for crash consistency", "repair", task_id=TASK)
        for mid in microtasks:
            tasks.create_microtask(TASK, mid, mid, microtask_id=mid)
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        steps = {"BACKUP_VERIFIED": [], "READY": ["READY"], "ACTIVE": ["READY", "ACTIVE"],
                 "DONE": ["READY", "ACTIVE", "DONE"]}[upto]
        for step in steps:
            machine.transition(TASK, "m1", step)

    # --- processes -------------------------------------------------------------------------
    def child(self, name: str, steps: list, fault: dict | None = None) -> dict:
        self.calls += 1
        cfg = self.base / f"cfg_{self.calls}.json"
        cfg.write_text(json.dumps({"storage": str(self.storage), "base": str(self.base), "name": name,
                                   "task": TASK, "steps": steps, "fault": fault}), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", "-c", CHILD, str(ROOT), str(cfg)], capture_output=True,
                              timeout=240)
        marker = self.base / f"{name}.phase.jsonl"
        phases = [json.loads(l) for l in marker.read_text(encoding="utf-8").splitlines()] if marker.exists() else []
        out = proc.stdout.decode(errors="replace").strip().splitlines()
        result = {"exit": proc.returncode, "phases": phases, "results": json.loads(out[-1]) if out else None,
                  "stderr": proc.stderr.decode(errors="replace")[-600:]}
        self.facts.append({f"child:{name}": {k: v for k, v in result.items() if k != "stderr"}})
        return result

    def transition_step(self, target: str, **extra) -> dict:
        return {"kind": "http", "method": "POST", "path": "/microtasks/m1/transition",
                "body": dict({"task_id": TASK, "target_status": target}, **extra)}

    def mutate_step(self, op: str) -> dict:
        return {"kind": "http", "method": "POST", "path": f"/tasks/{TASK}/mutations", "body": body(op)}

    # --- raw oracles -----------------------------------------------------------------------
    def task_dir(self) -> Path:
        active = self.storage / "tasks" / "active" / TASK
        return active if active.is_dir() else self.storage / "tasks" / "completed" / TASK

    def events(self) -> list[dict]:
        return lf_records((self.task_dir() / "events.jsonl").read_bytes())

    def status(self, mid: str = "m1") -> str:
        return json.loads((self.task_dir() / "microtasks" / f"{mid}.json").read_bytes())["status"]

    def op_record(self, op: str) -> dict:
        return json.loads((self.task_dir() / "operations" / f"{op}.json").read_bytes())

    def applies(self) -> int:
        path = self.base / "applies.jsonl"
        return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0

    def kinds(self, mid: str = "m1") -> list:
        return [(e["event_type"], (e["payload"] or {}).get("from"), (e["payload"] or {}).get("to"))
                for e in self.events() if e.get("microtask_id") == mid and e["event_type"].startswith("MICROTASK_")]

    def transitions_to(self, target: str, mid: str = "m1") -> list[dict]:
        return [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION"
                and e.get("microtask_id") == mid and (e["payload"] or {}).get("to") == target]


class MicrotaskIntentTests(Fixture):
    """R-MT: write-ahead intent, compare-and-set, commit; reconciliation only from durable facts."""

    def test_healthy_transition_writes_intent_then_commit_with_one_intent_id(self):
        self.build("ACTIVE")
        out = self.child("done", [self.transition_step("DONE")])
        self.assertEqual(out["results"][0]["http"], 200)
        self.assertIs(out["results"][0]["reply"]["event_recorded"], True)
        tail = [e for e in self.events() if e.get("microtask_id") == "m1"][-2:]
        self.assertEqual([e["event_type"] for e in tail], ["MICROTASK_TRANSITION_INTENT", "MICROTASK_TRANSITION"])
        self.assertEqual(tail[0]["event_id"], tail[1]["payload"]["intent_id"])
        self.assertEqual((tail[0]["payload"]["from"], tail[0]["payload"]["to"]), ("ACTIVE", "DONE"))

    def test_death_after_verified_cas_never_closes_without_evidence(self):
        self.build("DONE")
        crash = self.child("crash", [self.transition_step("VERIFIED", verification_evidence=EVIDENCE)],
                           fault={"event": "MICROTASK_TRANSITION", "when": "before"})
        self.assertEqual(crash["exit"], 70, crash["stderr"])
        self.assertEqual(self.status(), "VERIFIED", "precondition: the VERIFIED CAS is durable")
        self.assertEqual(self.transitions_to("VERIFIED"), [], "precondition: its event is missing")
        follow = self.child("reopen", [{"kind": "projection"}, {"kind": "closeout"}])
        projection, closeout = follow["results"][0]["projection"], follow["results"][1]["closeout"]
        self.assertNotEqual(closeout["result"], "COMPLETED",
                            "closeout completed a TASK whose VERIFIED stage has no recorded evidence")

    def test_reconciliation_restores_the_original_evidence_from_the_durable_intent(self):
        self.build("DONE")
        self.child("crash", [self.transition_step("VERIFIED", verification_evidence=EVIDENCE)],
                   fault={"event": "MICROTASK_TRANSITION", "when": "before"})
        applies_before = self.applies()
        target_before = (self.project / "data.bin").read_bytes()
        follow = self.child("recover", [{"kind": "recover"}, {"kind": "closeout"}])
        commits = self.transitions_to("VERIFIED")
        self.facts.append({"commits": commits})
        self.assertEqual(len(commits), 1, "the lost VERIFIED event was not restored exactly once")
        self.assertEqual(commits[0]["payload"]["verification_evidence"], EVIDENCE)
        intents = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_INTENT"
                   and e["payload"]["to"] == "VERIFIED"]
        self.assertEqual(commits[0]["payload"]["intent_id"], intents[-1]["event_id"])
        self.assertIs(commits[0]["payload"].get("recovered_from_intent"), True)
        self.assertEqual(follow["results"][1]["closeout"]["result"], "COMPLETED")
        self.assertEqual(self.applies(), applies_before, "recovery performed a physical apply")
        self.assertEqual((self.project / "data.bin").read_bytes(), target_before)

    def test_death_after_intent_before_cas_is_abandoned_with_an_audit_record(self):
        self.build("ACTIVE")
        crash = self.child("crash", [self.transition_step("DONE")],
                           fault={"event": "MICROTASK_TRANSITION_INTENT", "when": "after"})
        self.assertEqual(crash["exit"], 71, f"phase not reached: {crash['phases']} {crash['stderr']}")
        self.assertEqual(self.status(), "ACTIVE")
        follow = self.child("next", [self.transition_step("DONE")])
        self.assertEqual(follow["results"][0]["http"], 200)
        kinds = self.kinds()
        self.facts.append({"kinds": kinds})
        self.assertIn(("MICROTASK_TRANSITION_ABANDONED", "ACTIVE", "DONE"), kinds)
        abandons = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_ABANDONED"]
        intents = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_INTENT"
                   and e["payload"]["to"] == "DONE"]
        self.assertEqual(len(intents), 2, "expected the interrupted intent and the new one")
        self.assertEqual([a["payload"]["intent_id"] for a in abandons], [intents[0]["event_id"]])
        self.assertEqual(self.transitions_to("DONE")[-1]["payload"]["intent_id"], intents[-1]["event_id"])
        self.assertEqual(self.status(), "DONE")

    def test_death_before_intent_changes_nothing(self):
        self.build("ACTIVE")
        before = (self.task_dir() / "events.jsonl").read_bytes(), self.status()
        crash = self.child("crash", [self.transition_step("DONE")],
                           fault={"event": "MICROTASK_TRANSITION_INTENT", "when": "before"})
        self.assertEqual(crash["exit"], 70, f"phase not reached: {crash['phases']} {crash['stderr']}")
        self.assertEqual(((self.task_dir() / "events.jsonl").read_bytes(), self.status()), before)

    def test_lost_done_commit_is_restored_before_the_next_transition(self):
        self.build("ACTIVE")
        self.child("crash", [self.transition_step("DONE")], fault={"event": "MICROTASK_TRANSITION", "when": "before"})
        follow = self.child("verify", [self.transition_step("VERIFIED", verification_evidence=EVIDENCE)])
        self.assertEqual(follow["results"][0]["http"], 200, follow["results"])
        commits = [(e["payload"]["from"], e["payload"]["to"]) for e in self.events()
                   if e["event_type"] == "MICROTASK_TRANSITION" and e.get("microtask_id") == "m1"]
        self.assertEqual(commits[-2:], [("ACTIVE", "DONE"), ("DONE", "VERIFIED")],
                         "the next transition ran on a status whose history was not reconciled first")

    def test_commit_fsync_failure_is_reported_and_reconciled_once(self):
        self.build("ACTIVE")
        out = self.child("fsync", [self.transition_step("DONE")],
                         fault={"event": "MICROTASK_TRANSITION", "when": "fsync_error"})
        reply = out["results"][0]
        self.assertEqual(reply["http"], 200, reply)
        self.assertIs(reply["reply"]["event_recorded"], False)
        follow = self.child("again", [{"kind": "recover"}, {"kind": "recover"}, {"kind": "projection"}])
        dones = self.transitions_to("DONE")
        self.facts.append({"dones": dones})
        self.assertEqual(len(dones), 1, "reconciliation is not idempotent (or the failed append was kept)")
        self.assertEqual(follow["results"][2]["projection"]["diagnostics"], [])

    def test_projection_reports_a_pending_transition_after_reopen(self):
        self.build("ACTIVE")
        self.child("crash", [self.transition_step("DONE")], fault={"event": "MICROTASK_TRANSITION", "when": "before"})
        projection = self.child("look", [{"kind": "projection"}])["results"][0]["projection"]
        codes = projection["blockers"] + projection["diagnostics"] + projection["closeout"]
        self.assertTrue([c for c in codes if "PENDING" in c or "HISTORY" in c],
                        f"a persisted status without its history event is invisible: {codes}")

    def test_foreign_update_after_an_intent_is_a_fail_closed_contradiction(self):
        from web_alarm.task_store import TaskStore
        self.build("ACTIVE", microtasks=("m1", "m2"))
        crash = self.child("crash", [self.transition_step("DONE")],
                           fault={"event": "MICROTASK_TRANSITION_INTENT", "when": "after"})
        self.assertEqual(crash["exit"], 71, f"phase not reached: {crash['phases']} {crash['stderr']}")
        TaskStore(self.storage).set_plan(TASK, ["m1", "m2"])  # rewrites every microtask record (updated_at)
        before = (self.task_dir() / "events.jsonl").read_bytes(), self.status()
        follow = self.child("next", [self.transition_step("DONE"), {"kind": "recover"}, {"kind": "projection"}])
        self.facts.append({"follow": follow["results"]})
        self.assertEqual(follow["results"][0]["http"], 409, "an ambiguous intent was resolved automatically")
        self.assertEqual(((self.task_dir() / "events.jsonl").read_bytes(), self.status()), before,
                         "a fail-closed refusal changed status or history")
        self.assertIn("MICROTASK_HISTORY_CONTRADICTION", follow["results"][2]["projection"]["blockers"])
        self.assertIs(follow["results"][1]["recover"]["requires_human"], True)

    def test_a_refused_step_that_blocks_the_restore_point_closes_the_open_intent_first(self):
        self.build("BACKUP_VERIFIED")
        crash = self.child("crash", [self.transition_step("READY")],
                           fault={"event": "MICROTASK_TRANSITION_INTENT", "when": "after"})
        self.assertEqual(crash["exit"], 71, f"phase not reached: {crash['phases']} {crash['stderr']}")
        intent = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_INTENT"][-1]
        restore = self.task_dir() / "microtasks" / "m1"
        snapshots = [p for p in (restore / "restore_point").rglob("*") if p.is_file() and p.name != "manifest.json"]
        self.assertTrue(snapshots, "fixture: no snapshot bytes to damage")
        snapshots[0].write_bytes(b"corrupted")
        # the next step meets a broken restore point: the manifest store writes BLOCKED_PREPARE
        follow = self.child("next", [self.transition_step("READY"), {"kind": "projection"}])
        self.facts.append({"follow": follow["results"], "status": self.status(), "kinds": self.kinds()})
        self.assertEqual(follow["results"][0]["http"], 409)
        self.assertEqual(self.status(), "BLOCKED_PREPARE")
        abandons = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_ABANDONED"]
        self.assertEqual([a["payload"]["intent_id"] for a in abandons], [intent["event_id"]],
                         "the open intent was not closed before another writer changed the status")
        self.assertNotIn("MICROTASK_HISTORY_CONTRADICTION", follow["results"][1]["projection"]["blockers"])

    def test_recovery_status_write_closes_an_open_intent_first(self):
        from web_alarm.models import MicrotaskStatus
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        self.build("ACTIVE")
        crash = self.child("crash", [self.transition_step("DONE")],
                           fault={"event": "MICROTASK_TRANSITION_INTENT", "when": "after"})
        self.assertEqual(crash["exit"], 71, f"phase not reached: {crash['phases']} {crash['stderr']}")
        intent = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_INTENT"][-1]
        coordinator = RecoveryCoordinator(self.storage)  # RC-6 writes statuses without an event of its own
        with coordinator.operations.task_lock(TASK), coordinator.tasks.mutation_lock(TASK):
            coordinator._set_micro_locked(TASK, "m1", MicrotaskStatus.RECOVERY_REQUIRED,
                                          allowed_from={MicrotaskStatus.ACTIVE})
        out = self.child("look", [{"kind": "projection"}])
        self.facts.append({"look": out["results"], "status": self.status(), "kinds": self.kinds()})
        self.assertEqual(self.status(), "RECOVERY_REQUIRED")
        abandons = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_ABANDONED"]
        self.assertEqual([a["payload"]["intent_id"] for a in abandons], [intent["event_id"]])
        self.assertNotIn("MICROTASK_HISTORY_CONTRADICTION", out["results"][0]["projection"]["blockers"])


class VerificationEvidenceTests(Fixture):
    """Legacy VERIFIED without recorded evidence: no closeout until a safe re-verification."""

    def legacy_verified(self) -> None:
        from web_alarm.task_store import TaskStore
        self.build("DONE")
        TaskStore(self.storage).set_microtask_status(TASK, "m1", "VERIFIED")  # pre-repair shape: no event

    def test_legacy_verified_without_evidence_blocks_closeout(self):
        self.legacy_verified()
        out = self.child("close", [{"kind": "closeout"}, {"kind": "projection"}])
        self.assertNotEqual(out["results"][0]["closeout"]["result"], "COMPLETED")
        self.assertIn("MICROTASK_VERIFICATION_UNPROVEN", out["results"][1]["projection"]["closeout"])

    def test_reaffirmation_without_mutation_proves_and_allows_closeout(self):
        self.legacy_verified()
        target = (self.project / "data.bin").read_bytes()
        out = self.child("reaffirm", [
            {"kind": "http", "method": "POST", "path": "/microtasks/m1/reaffirm",
             "body": {"task_id": TASK, "verification_evidence": "re-checked: target bytes match the contract"}},
            {"kind": "closeout"}])
        self.facts.append({"results": out["results"]})
        self.assertEqual(out["results"][0]["http"], 200, out["results"][0])
        reaffirmed = [e for e in self.events() if e["event_type"] == "MICROTASK_VERIFICATION_REAFFIRMED"]
        self.assertEqual(len(reaffirmed), 1)
        self.assertIs(reaffirmed[0]["payload"]["original_evidence_recorded"], False)
        self.assertEqual(self.status(), "VERIFIED")
        self.assertEqual(out["results"][1]["closeout"]["result"], "COMPLETED")
        self.assertEqual((self.applies(), (self.project / "data.bin").read_bytes()), (0, target))

    def test_reaffirmation_is_refused_when_a_safe_recheck_is_impossible(self):
        from web_alarm.operation_store import OperationStore
        self.legacy_verified()
        store = OperationStore(self.storage)
        store.begin(TASK, "m1", "write", "data.bin", operation_id="op_open", payload=POST)
        store.transition(TASK, "op_open", "STARTED")  # open mutation fate, never applied
        before = (self.task_dir() / "events.jsonl").read_bytes()
        out = self.child("reaffirm", [
            {"kind": "http", "method": "POST", "path": "/microtasks/m1/reaffirm",
             "body": {"task_id": TASK, "verification_evidence": "looks fine"}},
            {"kind": "http", "method": "POST", "path": "/microtasks/m1/reaffirm",
             "body": {"task_id": TASK, "verification_evidence": "   "}},
            {"kind": "closeout"}])
        self.facts.append({"results": out["results"]})
        self.assertEqual(out["results"][0]["http"], 409, out["results"][0])
        self.assertEqual(out["results"][1]["http"], 400, out["results"][1])
        self.assertNotEqual(out["results"][2]["closeout"]["result"], "COMPLETED")
        self.assertFalse([e for e in self.events() if e["event_type"] == "MICROTASK_VERIFICATION_REAFFIRMED"])
        self.assertEqual(self.applies(), 0)

    def test_healthy_verified_closes_without_reaffirmation(self):
        self.build("DONE")
        out = self.child("close", [self.transition_step("VERIFIED", verification_evidence=EVIDENCE),
                                   {"kind": "closeout"}])
        self.assertEqual(out["results"][1]["closeout"]["result"], "COMPLETED")

    def test_death_during_completion_leaves_a_proven_read_only_history(self):
        self.build("DONE")
        crash = self.child("crash", [self.transition_step("VERIFIED", verification_evidence=EVIDENCE),
                                     {"kind": "closeout"}],
                           fault={"event": "TASK_COMPLETED", "when": "before"})
        self.assertEqual(crash["exit"], 70, f"phase not reached: {crash['phases']} {crash['stderr']}")
        self.assertEqual(self.task_dir().parent.name, "completed")
        before = (self.task_dir() / "events.jsonl").read_bytes()
        out = self.child("reopen", [{"kind": "projection"}, {"kind": "recover"},
                                    self.transition_step("DONE"), {"kind": "closeout"}])
        self.facts.append({"reopen": out["results"]})
        projection = out["results"][0]["projection"]
        self.assertFalse([c for c in projection["diagnostics"] + projection["blockers"] + projection["closeout"]
                          if c.startswith(("MICROTASK_HISTORY", "MICROTASK_VERIFICATION", "OPERATION_INTENT"))])
        self.assertEqual(out["results"][2]["http"], 409)
        after = (self.task_dir() / "events.jsonl").read_bytes()
        self.assertTrue(after.startswith(before), "the history of a completed TASK was rewritten")
        added = [e["event_type"] for e in lf_records(after[len(before):])]
        self.facts.append({"added_by_reopen": added})
        # pre-existing: a refused step records its rejection; R-MT/R-OP write nothing into a closed TASK
        self.assertEqual([k for k in added if k != "MICROTASK_TRANSITION_REJECTED"], [])
        self.assertEqual([e["payload"].get("verification_evidence") for e in self.transitions_to("VERIFIED")],
                         [EVIDENCE])
        self.assertEqual(self.applies(), 0)


class OperationIntentTests(Fixture):
    """R-OP: a lost OPERATION_INTENT of a narrow INTENT rev1 record is reconciled, never executed."""

    def crash_intent(self, op: str = "op_c") -> dict:
        crash = self.child("crash", [self.mutate_step(op)], fault={"event": "OPERATION_INTENT", "when": "before"})
        self.assertEqual(crash["exit"], 70, crash["stderr"])
        self.assertEqual((self.op_record(op)["status"], self.op_record(op)["revision"]), ("INTENT", 1))
        self.assertFalse([e for e in self.events() if e["event_type"] == "OPERATION_INTENT" and e["operation_id"] == op])
        return crash

    def test_lost_intent_event_keeps_the_task_readable_and_is_reported(self):
        self.build("ACTIVE")
        self.child("first", [self.mutate_step("op_a")])
        self.crash_intent("op_b")
        out = self.child("look", [{"kind": "list_operations"}, {"kind": "projection"}])
        self.facts.append({"results": out["results"]})
        self.assertEqual(out["results"][0].get("list"), ["op_a", "op_b"],
                         "one lost OPERATION_INTENT made every operation of the TASK unreadable")
        projection = out["results"][1]["projection"]
        self.assertNotIn("OPERATIONS_UNREADABLE", projection["blockers"])
        self.assertIn("OPERATION_INTENT_PENDING", projection["diagnostics"])

    def test_recover_reconstructs_the_intent_event_without_any_apply(self):
        self.build("ACTIVE")
        self.crash_intent()
        target = (self.project / "data.bin").read_bytes()
        out = self.child("recover", [{"kind": "recover"}, {"kind": "list_operations"}])
        self.facts.append({"results": out["results"]})
        intents = [e for e in self.events() if e["event_type"] == "OPERATION_INTENT" and e["operation_id"] == "op_c"]
        self.assertEqual(len(intents), 1)
        self.assertIs(intents[0]["payload"].get("reconstructed_from_record"), True)
        self.assertEqual(self.op_record("op_c")["status"], "INTENT", "reconciliation changed the operation")
        self.assertEqual((self.applies(), (self.project / "data.bin").read_bytes()), (0, target))
        self.assertEqual(out["results"][1]["list"], ["op_c"])

    def test_reconciling_replay_executes_nothing_and_a_later_request_executes_once(self):
        self.build("ACTIVE")
        self.crash_intent()
        first = self.child("replay1", [self.mutate_step("op_c")])["results"][0]
        self.facts.append({"first": first})
        self.assertEqual((first["http"], first.get("code")), (409, "operation_intent_reconciled"), first)
        self.assertEqual((self.applies(), (self.project / "data.bin").read_bytes()), (0, PRE),
                         "the call that restored the intent event also executed the operation")
        out = self.child("replay2", [self.mutate_step("op_c"), self.mutate_step("op_c")])
        self.facts.append({"results": out["results"]})
        self.assertEqual(out["results"][0]["reply"]["result"], "EXECUTED", out["results"][0])
        self.assertEqual(out["results"][1]["reply"]["result"], "REPLAYED")
        self.assertEqual(self.applies(), 1, "a lost INTENT event led to more than one physical apply")
        intents = [e for e in self.events() if e["event_type"] == "OPERATION_INTENT" and e["operation_id"] == "op_c"]
        self.assertEqual(len(intents), 1)

    def test_live_intent_event_failure_is_reported_as_persisted_intent(self):
        self.build("ACTIVE")
        out = self.child("live", [self.mutate_step("op_l"), {"kind": "list_operations"}],
                         fault={"event": "OPERATION_INTENT", "when": "raise"})
        reply = out["results"][0]
        self.facts.append({"results": out["results"]})
        self.assertEqual((reply["http"], reply.get("code")), (409, "operation_history_pending"), reply)
        self.assertIn("persisted", reply["message"])
        self.assertEqual(out["results"][1]["list"], ["op_l"])
        self.assertEqual(self.applies(), 0)

    def test_intent_with_a_progress_event_is_not_reconstructed(self):
        self.assert_progress_blocks_reconstruction(
            "OPERATION_TRANSITION", {"from": "INTENT", "to": "STARTED", "revision": 2})

    def test_intent_with_an_unvalidated_progress_event_is_not_reconstructed(self):
        # no revision/receipt check covers these kinds: only the progress rule keeps them fail-closed
        self.assert_progress_blocks_reconstruction("MUTATION_RETRY_EXECUTING", {"attempt": 2})

    def test_intent_with_a_replay_event_is_not_reconstructed(self):
        self.assert_progress_blocks_reconstruction("OPERATION_TRANSITION_REPLAY", {"status": "STARTED"})

    def assert_progress_blocks_reconstruction(self, kind: str, payload: dict) -> None:
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        self.build("ACTIVE")
        self.crash_intent()
        EventCheckpointStore(self.storage).append_event(TASK, kind, microtask_id="m1", operation_id="op_c",
                                                        payload=payload)
        before = (self.task_dir() / "events.jsonl").read_bytes()
        out = self.child("look", [{"kind": "list_operations"}, {"kind": "recover"}, self.mutate_step("op_c")])
        self.facts.append({"results": out["results"]})
        self.assertIn("raised", out["results"][0], "a contradicting history was treated as recoverable")
        self.assertIs(out["results"][1]["recover"]["requires_human"], True)
        self.assertNotEqual((out["results"][2].get("reply") or {}).get("result"), "EXECUTED")
        self.assertEqual((self.task_dir() / "events.jsonl").read_bytes(), before)
        self.assertEqual(self.applies(), 0)

    def test_lost_started_event_never_starts_a_physical_apply(self):
        self.build("ACTIVE")
        crash = self.child("crash", [self.mutate_step("op_s")],
                           fault={"event": "OPERATION_TRANSITION", "when": "before"})  # first one: -> STARTED
        self.assertEqual(crash["exit"], 70, crash["stderr"])
        self.assertEqual(self.op_record("op_s")["status"], "STARTED")
        out = self.child("again", [self.mutate_step("op_s"), {"kind": "recover"}])
        self.facts.append({"results": out["results"]})
        self.assertEqual(self.applies(), 0, "an operation of unknown fate (STARTED) was applied after reopen")
        self.assertEqual((self.project / "data.bin").read_bytes(), PRE)

    def test_lost_executed_event_never_leads_to_a_second_apply(self):
        self.build("ACTIVE")
        crash = self.child("crash", [self.mutate_step("op_x")],
                           fault={"event": "MUTATION_EXECUTED", "when": "before"})
        self.assertEqual(crash["exit"], 70, crash["stderr"])
        out = self.child("again", [self.mutate_step("op_x"), {"kind": "recover"}])
        self.facts.append({"results": out["results"]})
        self.assertEqual(self.applies(), 1, "a replay after a lost event repeated the physical apply")


if __name__ == "__main__":
    unittest.main()
