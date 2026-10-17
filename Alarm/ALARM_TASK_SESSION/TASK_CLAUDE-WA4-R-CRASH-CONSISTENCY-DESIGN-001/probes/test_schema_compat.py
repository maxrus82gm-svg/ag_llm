"""Rollback/compatibility facts for the design options, CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001.

Question: can a future writer add a field to the microtask / operation record and still be rolled back to
today's code? Today's readers build strict dataclasses (MicrotaskRecord(**raw), OperationRecord(**raw)).
Each test writes ONE extra key into a record of a disposable TEMP fixture and observes the CURRENT code.
Also checks that the OPERATION_INTENT event is fully derivable from the durable INTENT record (what the
operation store's own history validator expects), which a roll-forward design would rely on.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

TASK = "task_sc"


class SchemaCompat(unittest.TestCase):
    def setUp(self):
        from web_alarm.operation_store import OperationStore
        from web_alarm.state_machine import ServerStateMachine
        from web_alarm.task_store import TaskStore
        from web_alarm.workspace_registry import WorkspaceRegistry
        self.temp = tempfile.TemporaryDirectory(prefix="wa_schema_cc_")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.storage, project = base / "state", base / "project"
        project.mkdir()
        (project / "data.bin").write_bytes(b"pre")
        WorkspaceRegistry(self.storage).register("sc", project, workspace_id="ws_sc")
        tasks = TaskStore(self.storage)
        tasks.create_task("ws_sc", "sc", "RAW", "compat", task_id=TASK)
        tasks.create_microtask(TASK, "one", "one", microtask_id="m1")
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(TASK, "m1", [("data.bin", "edit")])
        machine.transition(TASK, "m1", "READY")
        machine.transition(TASK, "m1", "ACTIVE")
        OperationStore(self.storage).begin(TASK, "m1", "write", "data.bin", operation_id="op_s", payload=b"post")
        self.task_dir = self.storage / "tasks" / "active" / TASK
        self.facts = [{"task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001", "test": self.id()}]

    def add_field(self, rel: str, key: str, value) -> None:
        path = self.task_dir / rel
        data = json.loads(path.read_bytes())
        data[key] = value
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")

    def test_FACT_current_microtask_reader_rejects_an_unknown_field(self):
        from web_alarm.projection import ProjectionService
        from web_alarm.task_store import TaskStore, TaskStoreError
        self.add_field("microtasks/m1.json", "last_transition", {"event_id": "event_x", "to": "ACTIVE"})
        with self.assertRaises(TaskStoreError) as caught:
            TaskStore(self.storage).open_microtask(TASK, "m1")
        blockers = [b["code"] for b in ProjectionService(self.storage).build(TASK)["blockers"]]
        self.facts.append({"error": str(caught.exception)[:200], "projection_blockers": blockers})
        self.assertIn("MICROTASKS_UNREADABLE", blockers)

    def test_FACT_current_operation_reader_rejects_an_unknown_field(self):
        from web_alarm.operation_store import OperationStore, OperationStoreError
        self.add_field("operations/op_s.json", "pending_event", {"event_id": "event_y"})
        with self.assertRaises(OperationStoreError) as caught:
            OperationStore(self.storage).get(TASK, "op_s")
        self.facts.append({"error": str(caught.exception)[:200]})

    def test_FACT_operation_intent_event_is_derivable_from_the_durable_record(self):
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.file_state import authority_of
        from web_alarm.operation_store import OperationStore
        record = OperationStore(self.storage).get(TASK, "op_s")
        event = [e for e in EventCheckpointStore(self.storage).read_events(TASK)
                 if e.event_type == "OPERATION_INTENT" and e.operation_id == "op_s"][0]
        contract = record.contract
        derived = {
            "action": record.action, "target": record.target, "request_fingerprint": record.request_fingerprint,
            "contract_version": record.contract_version, "revision": 1, "target_key": contract["target_key"],
            "pre_state": authority_of(contract["pre_state"]),
            "expected_post_state": authority_of(contract["expected_post_state"]),
            "payload": ({k: contract["payload_ref"][k] for k in ("sha256", "size")}
                        if contract["payload_ref"] is not None else None),
            "contract_complete": contract["complete"],
        }
        self.facts.append({"event_keys": sorted(event.payload), "derived_keys": sorted(derived)})
        self.assertEqual(event.payload, derived, "OPERATION_INTENT is not reproducible from the INTENT record")
        self.assertEqual(event.microtask_id, record.microtask_id)


    def test_FACT_current_code_tolerates_new_event_types_and_extra_event_fields(self):
        """A write-ahead design adds event types (and an extra field in MICROTASK_TRANSITION): today's
        readers must ignore them, also when they carry the operation_id of an existing operation."""
        from web_alarm.closeout import CloseoutService
        from web_alarm.event_checkpoint_store import EventCheckpointStore
        from web_alarm.operation_store import OperationStore
        from web_alarm.projection import ProjectionService
        before = (ProjectionService(self.storage).build(TASK)["blockers"],
                  CloseoutService(self.storage).inspect(TASK)["blockers"])
        store = EventCheckpointStore(self.storage)
        store.append_event(TASK, "MICROTASK_TRANSITION_INTENT", microtask_id="m1", operation_id="op_s",
                           payload={"intent_id": "event_i", "from": "ACTIVE", "to": "DONE",
                                    "verification_evidence": None})
        store.append_event(TASK, "MICROTASK_TRANSITION_ABANDONED", microtask_id="m1", operation_id="op_s",
                           payload={"intent_id": "event_i", "reason": "probe"})
        store.append_event(TASK, "MICROTASK_TRANSITION", microtask_id="m1", operation_id="op_s",
                           payload={"from": "ACTIVE", "to": "ACTIVE", "verification_evidence": None,
                                    "intent_id": "event_j", "late": True})
        after = (ProjectionService(self.storage).build(TASK)["blockers"],
                 CloseoutService(self.storage).inspect(TASK)["blockers"])
        status = OperationStore(self.storage).get(TASK, "op_s").status.value
        self.facts.append({"blockers_before": before, "blockers_after": after, "op_status": status})
        self.assertEqual(status, "INTENT")
        self.assertEqual([b["code"] for b in after[0]], [b["code"] for b in before[0]])
        self.assertEqual([b["code"] for b in after[1]], [b["code"] for b in before[1]])


if __name__ == "__main__":
    unittest.main()
