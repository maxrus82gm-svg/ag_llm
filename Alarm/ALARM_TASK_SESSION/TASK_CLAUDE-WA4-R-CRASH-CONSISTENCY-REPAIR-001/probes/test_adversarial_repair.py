"""Adversarial probes for CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 (disposable TEMP only).

Complements the accumulated module test_web_alarm_crash_consistency.py: duplicate intents/events,
a recovery (RC-6) status writer meeting an open intent, a damaged history while an intent is open,
the pre-repair code reading histories the repaired code wrote (rollback), and a closeout racing a
transition paused between its intent and its compare-and-set. Oracles read raw bytes.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "baseline" / "web_alarm"
TASK = "task_adv"
EVIDENCE = "checked without mutation"
NL = bytes([10])


def lf(data: bytes) -> list[dict]:
    return [json.loads(c) for c in data.split(b"\n")[:-1]]


class Fixture(unittest.TestCase):
    def setUp(self):
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.temp = tempfile.TemporaryDirectory(prefix="wa_ccr_adv_")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.storage, self.project = base / "state", base / "project"
        self.project.mkdir()
        (self.project / "data.bin").write_bytes(b"pre")
        WorkspaceRegistry(self.storage).register("adv", self.project, workspace_id="ws_adv")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_adv", "adv", "RAW", "adversarial", task_id=TASK)
        tasks.create_microtask(TASK, "m1", "m1", microtask_id="m1")
        self.machine = ServerStateMachine(self.storage)
        self.machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        self.machine.transition(TASK, "m1", "READY")
        self.machine.transition(TASK, "m1", "ACTIVE")
        self.task_dir = self.storage / "tasks" / "active" / TASK
        self.facts = [{"task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001", "test": self.id()}]

    def events(self) -> list[dict]:
        return lf((self.task_dir / "events.jsonl").read_bytes())

    def status(self) -> str:
        return json.loads((self.task_dir / "microtasks" / "m1.json").read_bytes())["status"]

    def open_intent(self, to: str = "DONE") -> str:
        """An intent written exactly as the repaired code writes it, then the process 'died'."""
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.task_store import TaskStore
        record = TaskStore(self.storage).open_microtask(TASK, "m1")
        event = EventCheckpointStore(self.storage).append_event(
            TASK, "MICROTASK_TRANSITION_INTENT", microtask_id="m1",
            payload={"from": record.status.value, "to": to, "verification_evidence": None,
                     "basis_updated_at": record.updated_at})
        return event.event_id

    def snap(self, label: str) -> None:
        """Raw facts for the evidence: history bytes/hash, persisted status, project bytes (no apply)."""
        root = self.task_dir if self.task_dir.exists() else self.storage / "tasks" / "completed" / TASK
        raw = (root / "events.jsonl").read_bytes()
        record = json.loads((root / "microtasks" / "m1.json").read_bytes())
        self.facts.append({label: {"events_sha256": hashlib.sha256(raw).hexdigest(), "events_bytes": len(raw),
                                   "event_kinds_tail": ([e["event_type"] for e in lf(raw)[-5:]]
                                                        if raw.endswith(NL) else "TORN_TAIL"),
                                   "status": record["status"], "updated_at": record["updated_at"],
                                   "project_sha256": hashlib.sha256((self.project / "data.bin").read_bytes()).hexdigest(),
                                   "location": root.parent.name}})

    def journal(self) -> dict:
        from web_alarm.event_checkpoint_store import EventCheckpointStore, microtask_journal
        store = EventCheckpointStore(self.storage)
        return microtask_journal(store.read_events(TASK), store.microtask_statuses(TASK))


class DuplicatesAndContradictions(Fixture):
    def test_identical_duplicate_commit_is_tolerated_and_reconciliation_adds_nothing(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        self.machine.transition(TASK, "m1", "DONE")
        commit = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION"][-1]
        EventCheckpointStore(self.storage).append_event(TASK, "MICROTASK_TRANSITION", microtask_id="m1",
                                                        payload=commit["payload"])
        self.snap("before")
        before = (self.task_dir / "events.jsonl").read_bytes()
        from web_alarm.task_store import TaskStore
        with TaskStore(self.storage).mutation_lock(TASK):
            outcome = EventCheckpointStore(self.storage).resolve_microtask_intents_locked(TASK, "m1")
        self.assertEqual(outcome, [])
        self.assertEqual(self.journal()["contradictions"], [])
        self.assertEqual((self.task_dir / "events.jsonl").read_bytes(), before)

    def test_conflicting_duplicate_commit_is_a_contradiction_and_blocks(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.projection import ProjectionService
        self.machine.transition(TASK, "m1", "DONE")
        commit = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION"][-1]
        EventCheckpointStore(self.storage).append_event(
            TASK, "MICROTASK_TRANSITION", microtask_id="m1",
            payload=dict(commit["payload"], to="VERIFIED", verification_evidence="forged"))
        self.snap("before")
        codes = [b["code"] for b in ProjectionService(self.storage).build(TASK)["blockers"]]
        self.facts.append({"blockers": codes})
        self.assertIn("MICROTASK_HISTORY_CONTRADICTION", codes)

    def test_two_open_intents_are_never_resolved_automatically(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.state_machine import ServerStateMachineError
        self.open_intent("DONE")
        self.open_intent("UNKNOWN_AFTER_DISCONNECT")
        self.snap("before")
        before = (self.task_dir / "events.jsonl").read_bytes(), self.status()
        with self.assertRaises(ServerStateMachineError):
            self.machine.transition(TASK, "m1", "DONE")
        self.assertEqual(((self.task_dir / "events.jsonl").read_bytes(), self.status()), before)


class OtherWritersAndDamage(Fixture):
    def test_rc6_status_write_closes_an_open_intent_first(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.models import MicrotaskStatus
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        intent_id = self.open_intent("DONE")  # died after the intent, before the CAS
        self.snap("before")
        coordinator = RecoveryCoordinator(self.storage)
        with coordinator.operations.task_lock(TASK):
            with coordinator.tasks.mutation_lock(TASK):
                coordinator._set_micro_locked(TASK, "m1", MicrotaskStatus.RECOVERY_REQUIRED,
                                              allowed_from={MicrotaskStatus.ACTIVE})
        abandons = [e for e in self.events() if e["event_type"] == "MICROTASK_TRANSITION_ABANDONED"]
        self.facts.append({"abandons": abandons, "status": self.status()})
        self.assertEqual([a["payload"]["intent_id"] for a in abandons], [intent_id])
        self.assertEqual(self.status(), "RECOVERY_REQUIRED")
        self.assertEqual(self.journal()["contradictions"], [], "the recovery write left an undecidable intent")

    def test_damaged_history_with_an_open_intent_refuses_without_writes(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.recovery_coordinator import RecoveryCoordinator
        from web_alarm.state_machine import ServerStateMachineError
        self.open_intent("DONE")
        path = self.task_dir / "events.jsonl"
        path.write_bytes(path.read_bytes()[:-1])  # torn tail
        self.snap("before")
        before = path.read_bytes(), self.status()
        with self.assertRaises(ServerStateMachineError):
            self.machine.transition(TASK, "m1", "DONE")
        outcome = RecoveryCoordinator(self.storage).recover(TASK)
        self.facts.append({"recover": {k: outcome[k] for k in ("state", "requires_human")}})
        self.assertIs(outcome["requires_human"], True)
        self.assertEqual((path.read_bytes(), self.status()), before, "a damaged history was written or repaired")


class RollbackCompatibility(Fixture):
    """The pre-repair code (exact baseline bytes, loaded in RAM) reads histories the repaired code wrote."""

    def load_baseline(self, name: str):
        spec = importlib.util.spec_from_file_location(f"web_alarm._pre_ccr_{name}", BASELINE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_pre_repair_projection_and_operations_read_repaired_histories(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.operation_store import OperationStore
        from web_alarm.task_store import TaskStore
        self.machine.transition(TASK, "m1", "DONE")
        # a reconstructed OPERATION_INTENT (R-OP) and every new microtask event kind
        store = OperationStore(self.storage)
        real = store.events.append_event

        def lose_intent(task_id, kind, **kw):
            if kind == "OPERATION_INTENT":
                raise __import__("web_alarm.event_checkpoint_store", fromlist=["x"]).EventCheckpointStoreError("lost")
            return real(task_id, kind, **kw)

        with mock.patch.object(store.events, "append_event", lose_intent):
            try:
                store.begin(TASK, "m1", "write", "data.bin", operation_id="op_r", payload=b"post")
            except Exception:
                pass
        with store.task_lock(TASK), TaskStore(self.storage).mutation_lock(TASK):
            store._reconcile_intent_locked(TASK, store.get(TASK, "op_r"))
        self.open_intent("VERIFIED")  # an open intent (left for the old reader)
        self.snap("before")
        old_projection = self.load_baseline("projection")
        old_ops = self.load_baseline("operation_store")
        projection = old_projection.ProjectionService(self.storage).build(TASK)
        old_status = old_ops.OperationStore(self.storage).get(TASK, "op_r").status.value
        self.facts.append({"old_blockers": [b["code"] for b in projection["blockers"]], "old_op_status": old_status})
        self.assertEqual([b["code"] for b in projection["blockers"]], [])
        self.assertEqual(old_status, "INTENT")


class CloseoutRace(Fixture):
    def test_closeout_cannot_slip_between_intent_and_compare_and_set(self):
        self.addCleanup(self.snap, "after")
        from web_alarm.closeout import CloseoutService
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        self.machine.transition(TASK, "m1", "DONE")
        real = EventCheckpointStore.append_event
        entered, release = threading.Event(), threading.Event()

        def pausing(store, task_id, kind, **kw):
            record = real(store, task_id, kind, **kw)
            if kind == "MICROTASK_TRANSITION_INTENT" and (kw.get("payload") or {}).get("to") == "VERIFIED":
                entered.set()
                release.wait(20)
            return record

        self.snap("before")
        out = {}
        with mock.patch.object(EventCheckpointStore, "append_event", pausing):
            verify = threading.Thread(target=lambda: out.setdefault("verify", self.machine.transition(
                TASK, "m1", "VERIFIED", verification_evidence=EVIDENCE)))
            verify.start()
            self.assertTrue(entered.wait(20))
            close = threading.Thread(target=lambda: out.setdefault("close", CloseoutService(self.storage).complete(TASK)))
            close.start()
            close.join(1.0)
            slipped = not close.is_alive()
            release.set()
            verify.join(30)
            close.join(30)
        kinds = [e["event_type"] for e in lf(((self.storage / "tasks" / "completed" / TASK) / "events.jsonl").read_bytes())]
        self.facts.append({"slipped": slipped, "tail": kinds[-4:], "close": out["close"]["result"]})
        self.assertFalse(slipped, "closeout ran between a transition intent and its compare-and-set")
        self.assertEqual(kinds[-3:], ["MICROTASK_TRANSITION_INTENT", "MICROTASK_TRANSITION", "TASK_COMPLETED"])


if __name__ == "__main__":
    unittest.main()
