import json
import tempfile
import unittest
from pathlib import Path

from web_alarm.context_pack import EntryContextPackBuilder, PROTOCOL_RULES
from web_alarm.server import WebAlarmApi
from web_alarm.state_machine import ServerStateMachine
from web_alarm.task_store import TaskStore
from web_alarm.workspace_registry import WorkspaceRegistry


class EntryContextPackTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.project = self.root / "project"
        self.project.mkdir()
        self.marker = self.project / "marker.txt"
        self.marker.write_text("original", encoding="utf-8")

        workspace = WorkspaceRegistry(self.storage).register(
            "Project",
            self.project,
            workspace_id="ws_context",
        )
        tasks = TaskStore(self.storage)
        self.task = tasks.create_task(
            workspace.workspace_id,
            "Context Task",
            "RAW TASK\nDo the exact requested work.",
            "Resume a new Chat safely.",
            task_id="task_context",
        )
        self.m1 = tasks.create_microtask(
            self.task.task_id,
            "M1",
            "First step",
            microtask_id="m1",
        )
        self.m2 = tasks.create_microtask(
            self.task.task_id,
            "M2",
            "Second step",
            microtask_id="m2",
        )
        self.builder = EntryContextPackBuilder(self.storage)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_pack_contains_exact_required_sections_without_event_history(self):
        before = self.marker.read_bytes()
        pack = self.builder.build(self.task.task_id)

        required = {
            "TASK",
            "WORKSPACE",
            "GOAL",
            "PLAN_SUMMARY",
            "LAST_VERIFIED",
            "CURRENT_MICROTASK",
            "CURRENT_STATUS",
            "SNAPSHOT_STATUS",
            "LAST_OPERATION",
            "NEXT_SAFE_ACTION",
            "PROTOCOL_RULES",
            "CONTEXT_TEXT",
        }
        self.assertTrue(required.issubset(pack))
        self.assertEqual(pack["TASK"]["raw_task"], "RAW TASK\nDo the exact requested work.")
        self.assertEqual(pack["WORKSPACE"]["workspace_root"], str(self.project.resolve()))
        self.assertEqual(pack["CURRENT_MICROTASK"], "m1")
        self.assertEqual(pack["CURRENT_STATUS"], "PLANNED")
        self.assertEqual(pack["SNAPSHOT_STATUS"], "NOT_VERIFIED")
        self.assertEqual(pack["PROTOCOL_RULES"], PROTOCOL_RULES)
        self.assertNotIn("events", pack)
        self.assertNotIn("recent_events", pack)
        self.assertEqual(self.marker.read_bytes(), before)

    def test_pack_tracks_verified_then_current_microtask_from_authoritative_state(self):
        machine = ServerStateMachine(self.storage)
        machine.prepare_microtask(
            self.task.task_id,
            "m1",
            [("marker.txt", "edit")],
            operation_id="op_prepare_1",
        )
        machine.transition(self.task.task_id, "m1", "READY", operation_id="op_ready_1")
        machine.transition(self.task.task_id, "m1", "ACTIVE", operation_id="op_active_1")
        machine.transition(self.task.task_id, "m1", "DONE", operation_id="op_done_1")
        machine.transition(
            self.task.task_id,
            "m1",
            "VERIFIED",
            verification_evidence="tests pass",
            operation_id="op_verified_1",
        )

        second = self.project / "second.txt"
        second.write_text("before", encoding="utf-8")
        machine.prepare_microtask(
            self.task.task_id,
            "m2",
            [("second.txt", "edit")],
            operation_id="op_prepare_2",
        )

        pack = EntryContextPackBuilder(self.storage).build(self.task.task_id)

        self.assertEqual(pack["LAST_VERIFIED"], "m1")
        self.assertEqual(pack["CURRENT_MICROTASK"], "m2")
        self.assertEqual(pack["CURRENT_STATUS"], "BACKUP_VERIFIED")
        self.assertEqual(pack["SNAPSHOT_STATUS"], "VERIFIED")
        # RC-5: state-machine call labels are history (events), not tracked operations
        self.assertIsNone(pack["LAST_OPERATION"])
        self.assertIn("READY", pack["NEXT_SAFE_ACTION"])
        self.assertEqual(pack["AUTHORITY_SOURCE"], "lifecycle")
        self.assertEqual(pack["CHECKPOINT"]["status"], "VALID")

    def test_pack_survives_new_builder_instance_with_same_authoritative_state(self):
        first = self.builder.build(self.task.task_id)
        second = EntryContextPackBuilder(self.storage).build(self.task.task_id)

        for key in (
            "TASK",
            "WORKSPACE",
            "GOAL",
            "PLAN_SUMMARY",
            "LAST_VERIFIED",
            "CURRENT_MICROTASK",
            "CURRENT_STATUS",
            "SNAPSHOT_STATUS",
            "LAST_OPERATION",
            "NEXT_SAFE_ACTION",
            "PROTOCOL_RULES",
        ):
            self.assertEqual(second[key], first[key])

    def test_pack_is_compact_for_normal_task_and_plan(self):
        pack = self.builder.build(self.task.task_id)
        encoded = json.dumps(pack, ensure_ascii=False)

        self.assertLess(len(encoded), 12000)
        self.assertLess(len(pack["CONTEXT_TEXT"]), 8000)

    def test_server_context_endpoint_is_single_read_only_operation(self):
        api = WebAlarmApi(self.storage)
        before = self.marker.read_bytes()
        status, payload = api.dispatch("GET", "/tasks/task_context/context")

        self.assertEqual(status, 200)
        self.assertEqual(payload["TASK"]["task_id"], "task_context")
        self.assertEqual(payload["WORKSPACE"]["workspace_id"], "ws_context")
        self.assertIn("NEXT SAFE ACTION:", payload["CONTEXT_TEXT"])
        self.assertEqual(self.marker.read_bytes(), before)

    def test_many_events_do_not_expand_context_pack(self):
        api = WebAlarmApi(self.storage)
        baseline = self.builder.build(self.task.task_id)
        for index in range(100):
            api.state.append_event(
                self.task.task_id,
                "NOISE_EVENT",
                microtask_id="m1",
                payload={"index": index, "noise": "x" * 100},
            )

        after = EntryContextPackBuilder(self.storage).build(self.task.task_id)

        self.assertEqual(after["CONTEXT_TEXT"], baseline["CONTEXT_TEXT"])
        self.assertNotIn("NOISE_EVENT", json.dumps(after, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
