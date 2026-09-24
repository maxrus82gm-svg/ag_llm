from __future__ import annotations

import ast
import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import AsyncMock, patch

import compressor_runtime
import gigachat_transport
import server
import verifier_runtime
from model_registry import ModelSpec


def verifier_json(
    *,
    result: str = "PASS",
    check_type: str = "FINAL",
    violations: object = None,
    reason: object = "All requested evidence is present.",
    required_action: object = "None.",
) -> str:
    if violations is None:
        violations = []
    return json.dumps(
        {
            "result": result,
            "check_type": check_type,
            "violations": violations,
            "reason": reason,
            "required_action": required_action,
        }
    )


class VerifierRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_root = Path(self.temp_dir.name) / "verifier_logs"
        self.log_patch = patch.object(
            verifier_runtime, "VERIFIER_LOG_ROOT", self.log_root
        )
        self.log_patch.start()

    def tearDown(self) -> None:
        self.log_patch.stop()
        self.temp_dir.cleanup()

    async def call(
        self,
        response: str,
        *,
        check_type: str = "FINAL",
        verifier_model_id: str = verifier_runtime.DEFAULT_VERIFIER_MODEL_ID,
        raw_task: str = "Implement the requested change.",
        verification_context: str = "Tests passed and diff was inspected.",
        **metadata,
    ):
        request = AsyncMock(return_value=response)
        with patch.object(verifier_runtime, "_request_gigachat", request):
            result = await verifier_runtime.run_verifier_check(
                verifier_model_id=verifier_model_id,
                check_type=check_type,
                raw_task=raw_task,
                verification_context=verification_context,
                **metadata,
            )
        return result, request

    async def test_default_verifier_model_resolves_to_gigachat_3_pro(self) -> None:
        result, request = await self.call(verifier_json())
        self.assertEqual(
            verifier_runtime.DEFAULT_VERIFIER_MODEL_ID, "gigachat_3_pro"
        )
        self.assertEqual(result.model_id, "gigachat_3_pro")
        self.assertEqual(result.provider_model_id, "GigaChat-3-Pro")
        self.assertEqual(
            request.await_args.args[0]["model"], "GigaChat-3-Pro"
        )

    async def test_explicit_gigachat_3_pro_resolves(self) -> None:
        result, _request = await self.call(
            verifier_json(), verifier_model_id="gigachat_3_pro"
        )
        self.assertEqual(result.model_display_name, "GigaChat 3 Pro")
        self.assertEqual(result.provider, "gigachat")

    async def test_other_enabled_model_changes_provider_model_id(self) -> None:
        result, request = await self.call(
            verifier_json(), verifier_model_id="gigachat_3_lightning"
        )
        body = request.await_args.args[0]
        self.assertEqual(result.model_id, "gigachat_3_lightning")
        self.assertEqual(body["model"], "GigaChat-3-Lightning")

    async def test_unsupported_provider_is_rejected_without_model_call(self) -> None:
        unsupported = ModelSpec(
            model_id="other_model",
            display_name="Other Model",
            provider="other",
            provider_model_id="other-1",
        )
        request = AsyncMock()
        with (
            patch.object(verifier_runtime, "get_model_spec", return_value=unsupported),
            patch.object(verifier_runtime, "_request_gigachat", request),
        ):
            with self.assertRaisesRegex(
                verifier_runtime.VerifierRuntimeError,
                "provider не поддерживается",
            ):
                await verifier_runtime.run_verifier_check(
                    verifier_model_id="other_model",
                    check_type="FINAL",
                    raw_task="Task",
                    verification_context="Evidence",
                )
        request.assert_not_awaited()

    async def test_unknown_model_is_rejected_without_fallback(self) -> None:
        request = AsyncMock()
        with patch.object(verifier_runtime, "_request_gigachat", request):
            with self.assertRaisesRegex(
                verifier_runtime.VerifierRuntimeError,
                "model недоступна",
            ):
                await verifier_runtime.run_verifier_check(
                    verifier_model_id="missing_verifier_model",
                    check_type="FINAL",
                    raw_task="Task",
                    verification_context="Evidence",
                )
        request.assert_not_awaited()

    async def test_valid_pass_returns_immutable_typed_result(self) -> None:
        result, _request = await self.call(verifier_json(result="PASS"))
        self.assertIsInstance(result, verifier_runtime.VerifierResult)
        self.assertEqual(result.verdict, "PASS")
        self.assertEqual(result.violations, ())
        with self.assertRaises(FrozenInstanceError):
            result.verdict = "FAIL"

    async def test_valid_fail_is_semantic_result_not_runtime_error(self) -> None:
        result, _request = await self.call(
            verifier_json(
                result="FAIL",
                violations=["Missing required verification."],
                reason="Evidence is incomplete.",
                required_action="Run the missing verification.",
            )
        )
        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.violations, ("Missing required verification.",))

    async def test_malformed_json_is_protocol_error_and_no_retry(self) -> None:
        request = AsyncMock(return_value="not-json")
        with patch.object(verifier_runtime, "_request_gigachat", request):
            with self.assertRaises(verifier_runtime.VerifierProtocolError):
                await verifier_runtime.run_verifier_check(
                    check_type="FINAL",
                    raw_task="Task",
                    verification_context="Evidence",
                )
        self.assertEqual(request.await_count, 1)

    async def test_unknown_result_values_are_rejected(self) -> None:
        for invalid in ("OK", "SUCCESS", "TRUE", "APPROVED", "DENY", "ERROR"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(verifier_runtime.VerifierProtocolError):
                    await self.call(verifier_json(result=invalid))

    async def test_invalid_response_check_type_is_rejected(self) -> None:
        with self.assertRaises(verifier_runtime.VerifierProtocolError):
            await self.call(verifier_json(check_type="UNKNOWN"))

    async def test_mismatched_response_check_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            verifier_runtime.VerifierProtocolError, "не совпадает"
        ):
            await self.call(
                verifier_json(check_type="PREFLIGHT"), check_type="FINAL"
            )

    async def test_consistency_mode_has_distinct_hard_context_and_fail_closed_protocol(self) -> None:
        result, request = await self.call(
            verifier_json(check_type="CONSISTENCY", result="FAIL",
                          reason="No observed action", violations=["No tools"],
                          required_action="Read the target and apply the requested edit"),
            check_type="CONSISTENCY", raw_task="Update file result.txt",
        )
        self.assertEqual(result.check_type, "CONSISTENCY")
        self.assertEqual(result.required_action, "Read the target and apply the requested edit")
        prompt = request.await_args.args[0]["messages"][0]["content"]
        self.assertIn("repeated execution inconsistency", prompt)
        self.assertIn("Do not assume mutation is mandatory", prompt)
        self.assertIn("RAW TASK is the source of truth", prompt)
        with self.assertRaises(verifier_runtime.VerifierProtocolError):
            await self.call("not-json", check_type="CONSISTENCY")
        with self.assertRaises(verifier_runtime.VerifierProtocolError):
            await self.call(verifier_json(check_type="FINAL"), check_type="CONSISTENCY")
        passed, _ = await self.call(verifier_json(check_type="CONSISTENCY"),
                                    check_type="CONSISTENCY")
        self.assertEqual(passed.verdict, "PASS")

    async def test_permission_protocol_pass_fail_and_malformed_fail_closed(self) -> None:
        for verdict in ("PASS", "FAIL"):
            with self.subTest(verdict=verdict):
                result, request = await self.call(
                    verifier_json(check_type="PERMISSION", result=verdict),
                    check_type="PERMISSION", raw_task="Update result.txt",
                )
                self.assertEqual(result.verdict, verdict)
                prompt = request.await_args.args[0]["messages"][0]["content"]
                self.assertIn("disabled WRITE or DELETE capability", prompt)
                self.assertIn("Denied calls did not execute", prompt)
        with self.assertRaises(verifier_runtime.VerifierProtocolError):
            await self.call("not-json", check_type="PERMISSION")
        with self.assertRaises(verifier_runtime.VerifierProtocolError):
            await self.call(verifier_json(check_type="FINAL"), check_type="PERMISSION")

    async def test_final_prompt_requires_fail_on_candidate_server_fact_conflict(self) -> None:
        result, request = await self.call(
            verifier_json(check_type="FINAL", result="FAIL",
                          violations=["Claimed replace_text was not observed"],
                          reason="Candidate conflicts with server facts",
                          required_action="Correct the report"),
            raw_task="Измени file.md",
            verification_context=json.dumps({
                "run_facts": {"tool_call_count": 0, "write_revision": 0},
                "mutation_facts": {"changed_files": [], "new_files": [], "deleted_files": []},
                "run_owned_filesystem_evidence": [],
                "candidate_final_response": {"content": "Файл изменён через replace_text"},
            }, ensure_ascii=False),
        )
        prompt = request.await_args.args[0]["messages"][0]["content"]
        self.assertEqual(result.verdict, "FAIL")
        self.assertIn("HARD EVIDENCE RULE", prompt)
        self.assertIn("tool_call_count=0", prompt)
        self.assertIn("write_revision=0", prompt)
        self.assertIn("direct Candidate-versus-Server contradiction", prompt)
        self.assertIn("Zero tools or zero writes by themselves are not a failure", prompt)

    async def test_invalid_violations_type_is_rejected(self) -> None:
        for invalid in ("none", ["valid", 7], {"problem": "x"}):
            with self.subTest(invalid=invalid):
                with self.assertRaises(verifier_runtime.VerifierProtocolError):
                    await self.call(verifier_json(violations=invalid))

    async def test_invalid_reason_and_required_action_types_are_rejected(self) -> None:
        invalid_payloads = (
            verifier_json(reason=["not", "a", "string"]),
            verifier_json(required_action={"not": "a string"}),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(verifier_runtime.VerifierProtocolError):
                    await self.call(payload)

    async def test_non_object_and_missing_fields_are_rejected(self) -> None:
        invalid_payloads = (
            json.dumps([{"result": "PASS"}]),
            json.dumps({"result": "PASS", "check_type": "FINAL"}),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(verifier_runtime.VerifierProtocolError):
                    await self.call(payload)

    async def test_empty_model_response_is_protocol_error(self) -> None:
        for invalid in ("", "   "):
            with self.subTest(invalid=invalid):
                with self.assertRaises(verifier_runtime.VerifierProtocolError):
                    await self.call(invalid)

    async def test_request_body_has_no_tools_or_function_declarations(self) -> None:
        _result, request = await self.call(verifier_json())
        body = request.await_args.args[0]
        self.assertEqual(
            set(body),
            {"model", "messages", "temperature", "max_tokens", "stream"},
        )
        for forbidden in ("functions", "function_call", "tools", "tool_choice"):
            self.assertNotIn(forbidden, body)

    async def test_each_call_has_clean_messages_without_previous_context(self) -> None:
        responses = AsyncMock(
            side_effect=[
                verifier_json(check_type="PREFLIGHT"),
                verifier_json(check_type="MUTATION"),
            ]
        )
        with patch.object(verifier_runtime, "_request_gigachat", responses):
            await verifier_runtime.run_verifier_check(
                check_type="PREFLIGHT",
                raw_task="FIRST_RAW_MARKER",
                verification_context="FIRST_CONTEXT_MARKER",
            )
            await verifier_runtime.run_verifier_check(
                check_type="MUTATION",
                raw_task="SECOND_RAW_MARKER",
                verification_context="SECOND_CONTEXT_MARKER",
            )
        first_body = responses.await_args_list[0].args[0]
        second_body = responses.await_args_list[1].args[0]
        first_text = json.dumps(first_body, ensure_ascii=False)
        second_text = json.dumps(second_body, ensure_ascii=False)
        self.assertIn("FIRST_RAW_MARKER", first_text)
        self.assertNotIn("FIRST_RAW_MARKER", second_text)
        self.assertIn("SECOND_RAW_MARKER", second_text)
        self.assertNotIn("SECOND_RAW_MARKER", first_text)
        self.assertNotIn("EXECUTOR_HISTORY_SHOULD_NEVER_APPEAR", second_text)
        self.assertEqual(len(first_body["messages"]), 2)
        self.assertEqual(len(second_body["messages"]), 2)

    async def test_caller_metadata_is_returned(self) -> None:
        result, _request = await self.call(
            verifier_json(check_type="MUTATION"),
            check_type="MUTATION",
            task_id="task-1",
            checkpoint_id="checkpoint-2",
            operation_id="operation-3",
        )
        self.assertEqual(result.task_id, "task-1")
        self.assertEqual(result.checkpoint_id, "checkpoint-2")
        self.assertEqual(result.operation_id, "operation-3")
        self.assertRegex(result.verifier_run_id, r"^ver_\d{8}_\d{6}_[0-9a-f]{8}$")

    async def test_logs_do_not_persist_raw_task_or_context(self) -> None:
        raw_marker = "RAW_TASK_SECRET_MARKER_79A1"
        context_marker = "VERIFICATION_CONTEXT_SECRET_MARKER_42B8"
        await self.call(
            verifier_json(),
            raw_task=raw_marker,
            verification_context=context_marker,
        )
        log_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.log_root.glob("*.jsonl")
        )
        self.assertTrue(log_text)
        self.assertNotIn(raw_marker, log_text)
        self.assertNotIn(context_marker, log_text)
        self.assertIn('"raw_task_chars"', log_text)
        self.assertIn('"verification_context_chars"', log_text)
        self.assertIn('"verdict": "PASS"', log_text)

    def test_dependency_boundaries_and_backward_compatibility(self) -> None:
        source = Path(verifier_runtime.__file__).read_text(encoding="utf-8")
        imports = {
            node.module
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imports.update(
            alias.name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        self.assertNotIn("server", imports)
        self.assertNotIn("ui_state", imports)

        server_source = Path(server.__file__).read_text(encoding="utf-8")
        server_imports = {
            node.module
            for node in ast.walk(ast.parse(server_source))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        self.assertIn("verifier_runtime", server_imports)
        self.assertEqual(server.CHAT_URL, gigachat_transport.CHAT_URL)
        self.assertEqual(server.OAUTH_URL, gigachat_transport.OAUTH_URL)
        self.assertIs(server.get_access_token, gigachat_transport.get_access_token)
        self.assertTrue(callable(compressor_runtime.get_access_token))
        self.assertEqual(compressor_runtime.CHAT_URL, server.CHAT_URL)
        self.assertIsInstance(server.TEMPERATURE, float)
        self.assertIsInstance(server.MAX_TOKENS, int)

    async def test_input_validation_rejects_unknown_check_and_empty_payloads(self) -> None:
        request = AsyncMock()
        with patch.object(verifier_runtime, "_request_gigachat", request):
            invalid_cases = (
                {"check_type": "UNKNOWN", "raw_task": "Task", "verification_context": "Context"},
                {"check_type": "FINAL", "raw_task": " ", "verification_context": "Context"},
                {"check_type": "FINAL", "raw_task": "Task", "verification_context": ""},
            )
            for kwargs in invalid_cases:
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        await verifier_runtime.run_verifier_check(**kwargs)
        request.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
