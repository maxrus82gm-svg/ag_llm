from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from planner_runtime import PlannerError, validate_plan
from task_planner import TaskLifecycle, evidence_arguments_fingerprint


def read_evidence_plan(*, mode="server_evidence"):
    return {
        "stages": [{
            "stage_id": "read_stage",
            "goal": "read exact target",
            "stage_type": "analysis",
            "persistence_required": False,
            "allowed_capabilities": ["READ"],
            "artifacts": [],
            "completion_mode": mode,
            "evidence_requirements": [{
                "evidence_id": "readback",
                "tool": "read_file",
                "arguments": {"path": "result.md"},
            }],
            "completion_criteria": ["target read"],
        }],
        "obligation_changes": [],
    }


def verify_evidence_plan():
    return {
        "stages": [{
            "stage_id": "verify_stage",
            "goal": "verify exact content",
            "stage_type": "verification",
            "persistence_required": False,
            "allowed_capabilities": ["VERIFY"],
            "artifacts": [],
            "completion_mode": "server_evidence",
            "evidence_requirements": [{
                "evidence_id": "equals_check",
                "tool": "verify_file_content",
                "arguments": {
                    "path": "result.md",
                    "kind": "equals",
                    "value": "done\n",
                },
            }],
            "completion_criteria": ["exact deterministic verification passed"],
        }],
        "obligation_changes": [],
    }


class StageEvidenceContractTests(unittest.IsolatedAsyncioTestCase):
    def lifecycle(self, plan, tools):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        events = []
        planner = AsyncMock(return_value=copy.deepcopy(plan))
        lifecycle = TaskLifecycle(
            path=Path(temp.name) / "plan.json",
            run_id="run_evidence",
            task_block_id="tb_1234567890abcdef1234567890abcdef",
            raw_task="task",
            planner_call=planner,
            emit=lambda name, payload: events.append({"event": name, **payload}),
            snapshot=lambda _path: {"exists": False, "sha256": None, "content": ""},
            prepare=lambda *_args: {},
            dredd_enabled=False,
        )
        return lifecycle, events, [{"name": name} for name in tools]

    async def test_exact_read_evidence_auto_completes_server_evidence_stage(self):
        lifecycle, events, tools = self.lifecycle(read_evidence_plan(), ["read_file"])
        await lifecycle.initialize({"tools": tools})
        args = {"path": "result.md"}
        decision = lifecycle.after_non_persistence_evidence([{
            "stage_id": "read_stage",
            "tool": "read_file",
            "capability": "READ",
            "status": "OK",
            "executed": True,
            "arguments_sha256": evidence_arguments_fingerprint(args),
        }])
        self.assertEqual(decision, {"action": "final"})
        self.assertIsNone(lifecycle.stage)
        self.assertIn(
            "non_persistence_evidence_satisfied",
            [event["event"] for event in events],
        )

    async def test_contains_does_not_satisfy_required_equals(self):
        lifecycle, _events, tools = self.lifecycle(
            verify_evidence_plan(), ["verify_file_content"]
        )
        await lifecycle.initialize({"tools": tools})
        wrong = {
            "path": "result.md",
            "kind": "contains",
            "value": "done\n",
        }
        decision = lifecycle.after_non_persistence_evidence([{
            "stage_id": "verify_stage",
            "tool": "verify_file_content",
            "capability": "VERIFY",
            "status": "OK",
            "executed": True,
            "arguments_sha256": evidence_arguments_fingerprint(wrong),
        }])
        self.assertIsNone(decision)
        self.assertEqual(lifecycle.stage["stage_id"], "verify_stage")
        self.assertFalse(lifecycle.non_persistence_evidence_satisfied([{
            "stage_id": "verify_stage",
            "tool": "verify_file_content",
            "capability": "VERIFY",
            "status": "OK",
            "executed": True,
            "arguments_sha256": evidence_arguments_fingerprint(wrong),
        }]))

    async def test_model_result_stage_does_not_auto_complete_from_evidence(self):
        lifecycle, _events, tools = self.lifecycle(
            read_evidence_plan(mode="model_result"), ["read_file"]
        )
        await lifecycle.initialize({"tools": tools})
        args = {"path": "result.md"}
        decision = lifecycle.after_non_persistence_evidence([{
            "stage_id": "read_stage",
            "tool": "read_file",
            "capability": "READ",
            "status": "OK",
            "executed": True,
            "arguments_sha256": evidence_arguments_fingerprint(args),
        }])
        self.assertIsNone(decision)
        self.assertEqual(lifecycle.stage["stage_id"], "read_stage")

    def test_verification_stage_cannot_fall_back_to_model_result(self):
        candidate = verify_evidence_plan()
        candidate["stages"][0]["completion_mode"] = "model_result"
        with self.assertRaisesRegex(
            PlannerError, "Verification stage requires server_evidence"
        ):
            validate_plan(candidate)

    async def test_unavailable_evidence_tool_is_rejected_by_initial_validation(self):
        plan = verify_evidence_plan()
        lifecycle, events, _tools = self.lifecycle(plan, [])
        with self.assertRaisesRegex(Exception, "planner_protocol_or_runtime_error"):
            await lifecycle.initialize({"tools": [{"name": "read_file"}]})
        rejected = [
            event for event in events
            if event["event"] == "planner_attempt_rejected"
        ]
        self.assertTrue(rejected)
        self.assertIn("unavailable tool", rejected[0]["error_message"])


if __name__ == "__main__":
    unittest.main()
