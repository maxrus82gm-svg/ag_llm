from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import planner_runtime
import verifier_runtime
from planner_runtime import PlannerError, PlannerSession
from task_planner import LifecycleBlocked, TaskLifecycle


def analysis_plan(changes=None):
    return {
        "stages": [{
            "stage_id": "main", "goal": "answer task", "stage_type": "analysis",
            "persistence_required": False, "allowed_capabilities": ["READ"],
            "artifacts": [], "completion_criteria": ["answer is complete"],
        }],
        "obligation_changes": list(changes or []),
    }


def create_plan(*, operation="create", artifact_id="result", changes=None):
    return {
        "stages": [{
            "stage_id": "main", "goal": "write result", "stage_type": "produce_artifact",
            "persistence_required": True, "allowed_capabilities": ["READ", "WRITE"],
            "artifacts": [{
                "artifact_id": artifact_id, "path": "result.md", "operation": operation,
                "allow_already_satisfied": False,
                "postcondition": {"kind": "equals", "value": "done"},
            }],
            "completion_criteria": ["result exists"],
        }],
        "obligation_changes": list(changes or []),
    }


class _Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"finish_reason": "stop", "message": {"content": self.content}}]}


class _Client:
    def __init__(self, outputs, bodies):
        self.outputs = outputs
        self.bodies = bodies

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, _url, *, headers, json):
        self.bodies.append(copy.deepcopy(json))
        return _Response(self.outputs.pop(0))


class PlannerSessionRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_session_sends_full_history_and_raw_task_once(self):
        outputs = [json.dumps(analysis_plan()), json.dumps({
            "status": "READY_TO_PERSIST", "reason": "ready",
            "unresolved_requirements": [], "next_action": "",
        })]
        bodies = []
        session = PlannerSession(raw_task="UNIQUE RAW TASK")
        with (patch.object(planner_runtime, "get_access_token", AsyncMock(return_value="token")),
              patch.object(planner_runtime.httpx, "AsyncClient",
                           side_effect=lambda **_kwargs: _Client(outputs, bodies))):
            await session.call(
                mode="INITIAL", raw_task="UNIQUE RAW TASK",
                context={"permissions": {"READ": True}, "tools": [{"name": "read_file"}]},
            )
            await session.call(
                mode="READINESS", raw_task="UNIQUE RAW TASK",
                context={"server_facts": {}},
            )
        self.assertEqual(len(bodies), 2)
        self.assertLess(len(bodies[0]["messages"]), len(bodies[1]["messages"]))
        transcript = json.dumps(session.transcript(), ensure_ascii=False)
        self.assertEqual(transcript.count("UNIQUE RAW TASK"), 1)
        initial = json.loads(session.messages[1]["content"])
        self.assertIn("permissions", initial["context"])
        self.assertIn("tools", initial["context"])
        self.assertNotIn("project_context", initial["context"])
        self.assertNotIn("recent_working_context", initial["context"])

    async def test_invalid_raw_assistant_response_remains_before_repair(self):
        outputs = ["not json", json.dumps(analysis_plan())]
        session = PlannerSession(raw_task="task")
        with (patch.object(planner_runtime, "get_access_token", AsyncMock(return_value="token")),
              patch.object(planner_runtime.httpx, "AsyncClient",
                           side_effect=lambda **_kwargs: _Client(outputs, []))):
            with self.assertRaises(PlannerError):
                await session.call(mode="INITIAL", raw_task="task", context={})
            session.add_control_message(
                speaker="SERVER", mode="INITIAL", attempt=1, text="SERVER VALIDATION",
            )
            await session.call(mode="INITIAL", raw_task="task", context={}, attempt=2)
        self.assertTrue(any(item["role"] == "assistant" and item["content"] == "not json"
                            for item in session.messages))

    def test_session_message_limit_fails_closed(self):
        session = PlannerSession(raw_task="task")
        with self.assertRaisesRegex(PlannerError, "Planner session exceeds bounded limit"):
            for index in range(PlannerSession.MAX_MESSAGES):
                session.add_control_message(
                    speaker="SERVER", mode="INITIAL", attempt=index, text="feedback",
                )

    async def test_dredd_review_receives_raw_task_and_full_transcript(self):
        transcript = [
            {"role": "system", "content": "planner protocols"},
            {"role": "user", "content": "raw task turn"},
            {"role": "assistant", "content": "invalid response"},
        ]
        request = AsyncMock(return_value=json.dumps({
            "diagnosis": "missing field", "required_action": "return the field",
        }))
        with patch.object(verifier_runtime, "_request_gigachat", request):
            result = await verifier_runtime.run_planner_dredd_review(
                verifier_model_id="gigachat_3_pro", raw_task="RAW TASK",
                planner_session_transcript=transcript, mode="INITIAL",
                validation_error="missing obligation_changes",
                task_block_id="tb_1234567890abcdef1234567890abcdef",
            )
        body = request.await_args.args[0]
        payload = json.loads(body["messages"][1]["content"])
        self.assertEqual(payload["raw_task"], "RAW TASK")
        self.assertEqual(payload["planner_session_transcript"], transcript)
        self.assertEqual(result.required_action, "return the field")
        self.assertEqual(body["model"], "GigaChat-3-Pro")

    async def test_dredd_review_runtime_logs_protocol_failure_with_usage(self):
        transcript = [{"role": "assistant", "content": "invalid"}]
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            verifier_runtime, "VERIFIER_LOG_ROOT", Path(temp_dir)
        ), patch.object(
            verifier_runtime, "_request_gigachat",
            AsyncMock(return_value=("not json", {"total_tokens": 17})),
        ):
            with self.assertRaises(verifier_runtime.VerifierProtocolError):
                await verifier_runtime.run_planner_dredd_review(
                    raw_task="RAW SECRET", planner_session_transcript=transcript,
                    mode="INITIAL", validation_error="missing field",
                    task_block_id="tb_test",
                )
            records = [
                json.loads(line)
                for path in Path(temp_dir).glob("*.jsonl")
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(
            [record["event"] for record in records],
            ["planner_review_started", "planner_review_failed"],
        )
        failed = records[-1]
        self.assertEqual(failed["error_type"], "VerifierProtocolError")
        self.assertEqual(failed["usage"], {"total_tokens": 17})
        self.assertEqual(failed["transcript_chars"], len(json.dumps(transcript, ensure_ascii=False)))
        self.assertIn("transcript_bytes", failed)
        self.assertEqual(failed["validation_error_chars"], len("missing field"))
        self.assertNotIn("RAW SECRET", json.dumps(records))


class PlannerRepairLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.events = []
        self.feedback = []

    def tearDown(self):
        self.temp.cleanup()

    def lifecycle(self, planner, *, review=None, dredd=True):
        return TaskLifecycle(
            path=Path(self.temp.name) / "plan.json", run_id="run_test",
            task_block_id="tb_1234567890abcdef", raw_task="task",
            planner_call=planner,
            emit=lambda name, payload: self.events.append({"event": name, **payload}),
            snapshot=lambda _path: {"exists": False, "sha256": None, "content": ""},
            prepare=lambda *_args: {}, planner_session_id="ps_test",
            planner_feedback=lambda **payload: self.feedback.append(payload),
            planner_review=review, dredd_enabled=dredd,
        )

    async def test_first_invalid_gets_server_feedback_and_second_valid_installs(self):
        planner = AsyncMock(side_effect=[PlannerError("missing obligation_changes"), analysis_plan()])
        review = AsyncMock()
        lifecycle = self.lifecycle(planner, review=review)
        await lifecycle.initialize({"permissions": {}, "tools": []})
        self.assertEqual(planner.await_count, 2)
        review.assert_not_awaited()
        self.assertEqual(lifecycle.state["plan_version"], 1)
        self.assertIn("SERVER VALIDATION", self.feedback[0]["text"])
        self.assertNotIn("stage_blocked", [event["event"] for event in self.events])

    async def test_second_invalid_calls_dredd_and_third_valid_installs(self):
        planner = AsyncMock(side_effect=[PlannerError("one"), PlannerError("two"), analysis_plan()])
        review = AsyncMock(return_value={
            "diagnosis": "missing field", "required_action": "return full JSON",
            "verifier_run_id": "vr_test", "model_id": "gigachat_3_pro",
            "model_display_name": "GigaChat 3 Pro", "provider_model_id": "GigaChat-3-Pro",
        })
        lifecycle = self.lifecycle(planner, review=review)
        await lifecycle.initialize({})
        self.assertEqual(planner.await_count, 3)
        review.assert_awaited_once()
        self.assertTrue(any("DREDD REVIEW" in item["text"] for item in self.feedback))
        self.assertEqual(lifecycle.state["plan_version"], 1)

    async def test_third_invalid_blocks(self):
        planner = AsyncMock(side_effect=PlannerError("invalid"))
        review = AsyncMock(return_value={
            "diagnosis": "invalid", "required_action": "correct",
            "verifier_run_id": "vr", "model_id": "m", "model_display_name": "M",
            "provider_model_id": "pm",
        })
        lifecycle = self.lifecycle(planner, review=review)
        with self.assertRaisesRegex(LifecycleBlocked, "planner_protocol_or_runtime_error"):
            await lifecycle.initialize({})
        self.assertEqual(planner.await_count, 3)
        self.assertEqual(review.await_count, 1)
        self.assertEqual(lifecycle.state["terminal_reason"], "planner_protocol_or_runtime_error")

    async def test_dredd_review_failure_preserves_review_and_planner_errors(self):
        planner = AsyncMock(side_effect=PlannerError("missing obligation_changes"))
        review = AsyncMock(side_effect=verifier_runtime.VerifierProtocolError("bad review json"))
        lifecycle = self.lifecycle(planner, review=review)
        with self.assertRaisesRegex(LifecycleBlocked, "planner_protocol_or_runtime_error"):
            await lifecycle.initialize({})

        names = [event["event"] for event in self.events]
        for name in (
            "planner_dredd_review_started", "planner_dredd_review_failed",
            "planner_failed", "planner_session_blocked",
        ):
            self.assertIn(name, names)
        review_failure = next(
            event for event in self.events
            if event["event"] == "planner_dredd_review_failed"
        )
        self.assertEqual(review_failure["planner_validation_error"], "missing obligation_changes")
        self.assertEqual(review_failure["review_error_type"], "VerifierProtocolError")
        self.assertEqual(review_failure["review_error_message"], "bad review json")
        failure = next(event for event in self.events if event["event"] == "planner_failed")
        self.assertEqual(failure["reason"], "planner_dredd_review_error")
        self.assertEqual(failure["error_type"], "VerifierProtocolError")
        self.assertEqual(failure["error_message"], "bad review json")
        self.assertEqual(failure["planner_error_type"], "PlannerError")
        self.assertEqual(failure["planner_error_message"], "missing obligation_changes")

    async def test_dredd_disabled_blocks_after_second_invalid(self):
        planner = AsyncMock(side_effect=PlannerError("invalid"))
        review = AsyncMock()
        lifecycle = self.lifecycle(planner, review=review, dredd=False)
        with self.assertRaises(LifecycleBlocked):
            await lifecycle.initialize({})
        self.assertEqual(planner.await_count, 2)
        review.assert_not_awaited()

    async def test_initial_obligation_changes_is_repairable(self):
        invalid = analysis_plan([{
            "old_artifact_id": "old", "action": "cancel", "replacement_ids": [],
            "reason": "invalid initial change", "fact_id": "fact_none",
        }])
        planner = AsyncMock(side_effect=[invalid, analysis_plan()])
        lifecycle = self.lifecycle(planner, review=AsyncMock())
        await lifecycle.initialize({})
        self.assertEqual(planner.await_count, 2)
        rejected = [event for event in self.events if event["event"] == "planner_attempt_rejected"]
        self.assertIn("INITIAL plan must return obligation_changes=[]", rejected[0]["error_message"])

    async def test_replan_rejects_identical_create_then_accepts_resolved_plan(self):
        fact_id = None

        async def planner(**kwargs):
            nonlocal fact_id
            if kwargs["mode"] == "INITIAL":
                return create_plan()
            fact_id = kwargs["context"]["authoritative_facts"][0]["fact_id"]
            if kwargs["attempt"] == 1:
                return create_plan()
            return create_plan(
                operation="update", artifact_id="replacement",
                changes=[{
                    "old_artifact_id": "result", "action": "replace",
                    "replacement_ids": ["replacement"], "reason": "target exists",
                    "fact_id": fact_id,
                }],
            )

        lifecycle = self.lifecycle(planner, review=AsyncMock())
        await lifecycle.initialize({})
        await lifecycle.replan({"reason": "create_target_already_exists", "path": "result.md"})
        self.assertEqual(lifecycle.state["plan_version"], 2)
        self.assertEqual(lifecycle.plan["stages"][0]["artifacts"][0]["operation"], "update")
        self.assertTrue(any("create_target_already_exists" in item["text"] for item in self.feedback))

    async def test_replan_never_installs_same_conflicting_create(self):
        async def planner(**kwargs):
            return create_plan()

        review = AsyncMock(return_value={
            "diagnosis": "create still conflicts", "required_action": "change the obligation",
            "verifier_run_id": "vr", "model_id": "m", "model_display_name": "M",
            "provider_model_id": "pm",
        })
        lifecycle = self.lifecycle(planner, review=review)
        await lifecycle.initialize({})
        with self.assertRaises(LifecycleBlocked):
            await lifecycle.replan({"reason": "create_target_already_exists", "path": "result.md"})
        self.assertEqual(lifecycle.state["plan_version"], 1)
        self.assertEqual(review.await_count, 1)

