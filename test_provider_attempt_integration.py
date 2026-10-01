import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from audit_storage import AuditThreadRecorder
from planner_runtime import PlannerSession
import compressor_runtime
import planner_runtime
from run_store import load_run_summary, load_stream_records
import server
import verifier_runtime


USAGE = {
    "prompt_tokens": 40,
    "completion_tokens": 10,
    "total_tokens": 50,
    "raw": {},
}


def valid_plan():
    return {
        "stages": [{
            "stage_id": "stage_1",
            "goal": "Inspect",
            "stage_type": "analysis",
            "persistence_required": False,
            "allowed_capabilities": ["READ"],
            "artifacts": [],
            "completion_mode": "model_result",
            "evidence_requirements": [],
            "completion_criteria": ["done"],
        }],
        "obligation_changes": [],
    }


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.response = FakeResponse(payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        return self.response


class ProviderAttemptIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_planner_session_emits_started_and_completed_terminal(self):
        diagnostics = []
        payload = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(valid_plan())},
            }],
            "usage": {
                "prompt_tokens": 40,
                "completion_tokens": 10,
                "total_tokens": 50,
            },
        }
        session = PlannerSession(
            raw_task="Inspect",
            diagnostic_callback=lambda kind, data: diagnostics.append((kind, data)),
        )
        with (
            patch.object(planner_runtime, "get_access_token", AsyncMock(return_value="token")),
            patch.object(
                planner_runtime.httpx,
                "AsyncClient",
                return_value=FakeClient(payload),
            ),
        ):
            result = await session.call(
                mode="INITIAL",
                raw_task="Inspect",
                context={},
            )

        self.assertEqual(result, valid_plan())
        provider_events = [
            (kind, data)
            for kind, data in diagnostics
            if kind.startswith("provider_attempt_")
        ]
        self.assertEqual(
            [kind for kind, _data in provider_events],
            ["provider_attempt_started", "provider_attempt_terminal"],
        )
        started = provider_events[0][1]
        terminal = provider_events[1][1]
        self.assertEqual(started["role"], "planner")
        self.assertEqual(started["mode"], "INITIAL")
        self.assertEqual(terminal["outcome"], "completed")
        self.assertEqual(terminal["provider_usage"]["total_tokens"], 50)
        self.assertEqual(
            terminal["provider_attempt_id"],
            started["provider_attempt_id"],
        )
        self.assertTrue(started["request_blocks"])
        self.assertNotIn("Inspect", json.dumps(started))

    async def test_dredd_emits_completed_and_parse_error_terminals(self):
        events = []
        good = json.dumps({
            "result": "PASS",
            "check_type": "FINAL",
            "violations": [],
            "reason": "ok",
            "required_action": "none",
        })
        with patch.object(
            verifier_runtime,
            "_request_gigachat",
            AsyncMock(return_value=(good, USAGE)),
        ):
            result = await verifier_runtime.run_verifier_check(
                check_type="FINAL",
                raw_task="Change a file.",
                verification_context="Evidence",
                task_id="run_1",
                diagnostic_callback=lambda event, data: events.append((event, data)),
            )
        self.assertEqual(result.verdict, "PASS")
        self.assertEqual(
            [event for event, _data in events],
            ["provider_attempt_started", "provider_attempt_terminal"],
        )
        self.assertEqual(events[-1][1]["outcome"], "completed")
        self.assertEqual(events[-1][1]["provider_usage"]["total_tokens"], 50)

        failed_events = []
        with patch.object(
            verifier_runtime,
            "_request_gigachat",
            AsyncMock(return_value=("not-json", USAGE)),
        ):
            with self.assertRaises(verifier_runtime.VerifierProtocolError):
                await verifier_runtime.run_verifier_check(
                    check_type="FINAL",
                    raw_task="Change a file.",
                    verification_context="Evidence",
                    task_id="run_2",
                    diagnostic_callback=lambda event, data: failed_events.append(
                        (event, data)
                    ),
                )
        self.assertEqual(
            [event for event, _data in failed_events],
            ["provider_attempt_started", "provider_attempt_terminal"],
        )
        self.assertEqual(failed_events[-1][1]["outcome"], "parse_error")
        self.assertEqual(
            failed_events[-1][1]["provider_usage"]["total_tokens"],
            50,
        )

    async def test_compressor_request_emits_provider_attempt_accounting(self):
        events = []
        payload = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": "compressed"},
            }],
            "usage": {
                "prompt_tokens": 40,
                "completion_tokens": 10,
                "total_tokens": 50,
            },
        }
        body = {
            "model": "provider-model",
            "messages": [{"role": "user", "content": "Sensitive source"}],
            "temperature": 0.0,
            "max_tokens": 100,
            "stream": False,
        }
        with (
            patch.object(
                compressor_runtime,
                "get_access_token",
                AsyncMock(return_value="token"),
            ),
            patch.object(
                compressor_runtime.httpx,
                "AsyncClient",
                return_value=FakeClient(payload),
            ),
        ):
            content = await compressor_runtime._request_gigachat(
                body,
                model_id="gigachat_3_pro",
                provider="gigachat",
                mode="COMPRESS:1",
                logical_call_id="lc_compressor_test",
                diagnostic_callback=lambda event, data: events.append(
                    (event, data)
                ),
            )

        self.assertEqual(content, "compressed")
        self.assertEqual(
            [event for event, _data in events],
            ["provider_attempt_started", "provider_attempt_terminal"],
        )
        started = events[0][1]
        terminal = events[1][1]
        self.assertEqual(started["role"], "compressor")
        self.assertEqual(started["mode"], "COMPRESS:1")
        self.assertEqual(started["logical_call_id"], "lc_compressor_test")
        self.assertEqual(terminal["outcome"], "completed")
        self.assertEqual(terminal["provider_usage"]["total_tokens"], 50)
        self.assertEqual(
            terminal["provider_attempt_id"],
            started["provider_attempt_id"],
        )
        self.assertNotIn(
            "Sensitive source",
            json.dumps(started, ensure_ascii=False),
        )

    async def test_audit_diagnostic_emits_executor_attempt_and_usage(self):
        events = []
        payload = {
            "choices": [{"message": {"content": "diagnosis"}}],
            "usage": {
                "prompt_tokens": 40,
                "completion_tokens": 10,
                "total_tokens": 50,
            },
        }
        answer = await server._request_audit_diagnostic(
            FakeClient(payload),
            {"Authorization": "token"},
            "provider-model",
            [{"role": "user", "content": "Task context"}],
            "Rejected candidate",
            "Why was it wrong?",
            model_id="gigachat_ultra",
            provider="gigachat",
            diagnostic_callback=lambda event, data: events.append((event, data)),
            source_references=["run:r1", "task_block:tb1"],
        )

        self.assertEqual(answer, "diagnosis")
        self.assertEqual(
            [event for event, _data in events],
            ["provider_attempt_started", "provider_attempt_terminal"],
        )
        started = events[0][1]
        terminal = events[1][1]
        self.assertEqual(started["role"], "executor")
        self.assertEqual(started["mode"], "AUDIT_DIAGNOSTIC")
        self.assertEqual(terminal["outcome"], "completed")
        self.assertEqual(terminal["provider_usage"]["total_tokens"], 50)
        self.assertEqual(
            terminal["provider_attempt_id"],
            started["provider_attempt_id"],
        )
        self.assertEqual(
            [item["name"] for item in started["request_blocks"]],
            ["executor_context", "rejected_candidate", "diagnostic_question"],
        )
        serialized = json.dumps(started, ensure_ascii=False)
        self.assertNotIn("Task context", serialized)
        self.assertNotIn("Rejected candidate", serialized)
        self.assertNotIn("Why was it wrong?", serialized)

    async def test_audit_diagnostic_parse_error_closes_attempt(self):
        events = []
        with self.assertRaises(ValueError):
            await server._request_audit_diagnostic(
                FakeClient({}),
                {"Authorization": "token"},
                "provider-model",
                [{"role": "user", "content": "Task"}],
                "Rejected",
                "Why?",
                model_id="gigachat_ultra",
                provider="gigachat",
                diagnostic_callback=lambda event, data: events.append(
                    (event, data)
                ),
            )

        self.assertEqual(
            [event for event, _data in events],
            ["provider_attempt_started", "provider_attempt_terminal"],
        )
        self.assertEqual(events[-1][1]["outcome"], "parse_error")
        self.assertIsNone(events[-1][1]["provider_usage"]["total_tokens"])
        self.assertIsNone(events[-1][1]["provider_usage"]["raw"])

    def test_audit_routes_attempts_to_role_streams_and_aggregates_once(self):
        task = "tb_" + "c" * 32
        recorder = AuditThreadRecorder(
            self._testMethodName_root,
            "ws",
            "chat",
            "run",
            task_block_id=task,
        )
        for index, role in enumerate(("planner", "executor", "dredd"), start=1):
            attempt_id = f"pa_{role}"
            recorder.observe({
                "event": "provider_attempt_started",
                "timestamp": index,
                "role": role,
                "provider_attempt_id": attempt_id,
                "logical_call_id": f"lc_{role}",
                "mode": "test",
            })
            recorder.observe({
                "event": "provider_attempt_terminal",
                "timestamp": index + 0.1,
                "role": role,
                "provider_attempt_id": attempt_id,
                "logical_call_id": f"lc_{role}",
                "mode": "test",
                "outcome": "completed",
                "provider_usage": USAGE,
            })

        for source, role in (
            ("PLANNER", "planner"),
            ("EXECUTOR", "executor"),
            ("DREDD", "dredd"),
        ):
            records = load_stream_records(
                self._testMethodName_root, "run", source
            )
            attempts = [
                item for item in records
                if item["event"].startswith("provider_attempt_")
            ]
            self.assertEqual(len(attempts), 2)
            self.assertEqual(attempts[0]["payload"]["role"], role)

        summary = load_run_summary(self._testMethodName_root, "run")
        self.assertEqual(summary["usage"]["total"]["calls"], 3)
        self.assertEqual(summary["usage"]["total"]["total_tokens"], 150)
        self.assertTrue(summary["usage"]["total"]["complete"])
        self.assertTrue(summary["provider_accounting"]["complete"])

    def setUp(self):
        import tempfile
        self._temp = tempfile.TemporaryDirectory()
        self._testMethodName_root = Path(self._temp.name)

    def tearDown(self):
        self._temp.cleanup()


if __name__ == "__main__":
    unittest.main()
