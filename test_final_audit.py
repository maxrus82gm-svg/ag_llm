from __future__ import annotations

import asyncio
import copy
import inspect
import json
import queue
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import server
import ultra_ui
import verifier_runtime


def verifier_result(verdict: str = "PASS") -> verifier_runtime.VerifierResult:
    failed = verdict == "FAIL"
    return verifier_runtime.VerifierResult(
        verdict=verdict,
        check_type="FINAL",
        violations=("Required evidence is missing.",) if failed else (),
        reason="Evidence is incomplete." if failed else "Evidence is sufficient.",
        required_action="Collect the missing evidence." if failed else "None.",
        verifier_run_id="ver_test_final",
        model_id="gigachat_3_pro",
        model_display_name="GigaChat 3 Pro",
        provider="gigachat",
        provider_model_id="GigaChat-3-Pro",
        task_id="task-test",
        checkpoint_id=None,
        operation_id=None,
    )


class FakeResponse:
    status_code = 200

    def __init__(
        self,
        content: str = "CANDIDATE FINAL",
        *,
        finish_reason: str = "stop",
        function_call: dict | None = None,
    ) -> None:
        self.content = content
        self.finish_reason = finish_reason
        self.function_call = function_call

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        message = {"content": self.content}
        if self.function_call is not None:
            message["function_call"] = self.function_call
        return {
            "choices": [
                {
                    "message": message,
                    "finish_reason": self.finish_reason,
                }
            ]
        }


class FakeClient:
    def __init__(self, responses: list[FakeResponse] | None = None) -> None:
        self.responses = list(responses or [FakeResponse()])
        self.post_count = 0
        self.bodies: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, _url, *, headers, json):
        self.post_count += 1
        self.bodies.append(copy.deepcopy(json))
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse()


class FinalAuditRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        self.workspace.mkdir()
        self.runtime = Path(self.temp_dir.name) / "runtime"
        self.events: list[dict] = []
        self.permissions = {
            "allow_read": True,
            "allow_write": False,
            "allow_delete": False,
            "allow_verify": False,
            "allow_guard_p1": False,
            "read_scope": ".",
            "write_scope": ".",
            "delete_scope": ".",
            "tool_limit": 5,
            "auto_backup": False,
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    async def run_case(
        self,
        verifier_side_effect,
        *,
        verifier_model_id: str = "gigachat_3_pro",
        fake_client: FakeClient | None = None,
        extra_patches: tuple = (),
    ):
        client = fake_client or FakeClient()
        if isinstance(verifier_side_effect, BaseException):
            verifier = AsyncMock(side_effect=verifier_side_effect)
        elif isinstance(verifier_side_effect, (list, tuple)):
            verifier = AsyncMock(side_effect=list(verifier_side_effect))
        else:
            verifier = AsyncMock(return_value=verifier_side_effect)
        self.last_verifier = verifier
        self.last_client = client
        backup = {
            "backup_dir": self.runtime / "backup" / "run",
            "manifest": {
                "core_files": [],
                "changed_files": [],
                "new_files": [],
                "deleted_files": [],
            },
        }
        workspace_info = {
            "workspace_id": "ws_test",
            "storage_created": False,
            "workspace_created": False,
            "project_context_created": False,
        }
        git_result = {
            "ok": True,
            "exit_code": 0,
            "stdout": " M server.py",
            "stderr": "",
            "truncated": False,
            "stdout_bytes": 12,
            "stderr_bytes": 0,
        }
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(server, "get_access_token", AsyncMock(return_value="token"))
            )
            stack.enter_context(
                patch.object(server, "ensure_workspace_storage", return_value=workspace_info)
            )
            stack.enter_context(patch.object(server, "load_project_context", return_value=""))
            stack.enter_context(
                patch.object(server, "load_agent_global_context", return_value="ROLE")
            )
            stack.enter_context(
                patch.object(
                    server,
                    "ensure_workspace_runtime_dirs",
                    return_value={
                        "backup_dir": str(self.runtime / "backup"),
                        "log_dir": str(self.runtime / "logs"),
                    },
                )
            )
            stack.enter_context(
                patch.object(server, "_create_backup_session", return_value=backup)
            )
            stack.enter_context(
                patch.object(server.httpx, "AsyncClient", return_value=client)
            )
            stack.enter_context(
                patch.object(server, "_agent_git_status", return_value=dict(git_result))
            )
            stack.enter_context(
                patch.object(server, "_agent_git_diff", return_value=dict(git_result))
            )
            stack.enter_context(patch.object(server, "run_verifier_check", verifier))
            for item in extra_patches:
                stack.enter_context(item)
            result = await server.run_agent_task(
                "ORIGINAL RAW TASK",
                str(self.workspace),
                permissions=self.permissions,
                on_event=self.events.append,
                verifier_model_id=verifier_model_id,
            )
        return result, verifier, client

    async def test_valid_pass_allows_normal_success(self) -> None:
        result, verifier, _client = await self.run_case(verifier_result("PASS"))
        self.assertEqual(result, "CANDIDATE FINAL")
        verifier.assert_awaited_once()
        self.assertIn("final_audit_passed", [item["event"] for item in self.events])
        self.assertEqual(self.events[-1]["event"], "run_finished")
        self.assertEqual(self.events[-1]["status"], "SUCCESS")

    async def test_no_tool_zero_revision_still_calls_final_audit(self) -> None:
        _result, verifier, _client = await self.run_case(verifier_result("PASS"))
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(context["run_facts"]["tool_call_count"], 0)
        self.assertEqual(context["run_facts"]["write_revision"], 0)
        verifier.assert_awaited_once()

    async def test_non_mutating_truncated_candidate_blocks_before_verifier(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_case(
                verifier_result("PASS"),
                extra_patches=(
                    patch.object(server, "MAX_VERIFY_OUTPUT_BYTES", 4),
                ),
            )
        self.last_verifier.assert_not_awaited()
        names = [item["event"] for item in self.events]
        self.assertIn("final_audit_error", names)
        self.assertNotIn("final_audit_passed", names)
        self.assertNotIn("run_finished", names)
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_evidence_incomplete")

    async def test_first_fail_hands_off_and_second_pass_returns_correction(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        result, verifier, _client = await self.run_case(
            [verifier_result("FAIL"), verifier_result("PASS")],
            fake_client=client,
        )
        self.assertEqual(result, "Candidate B")
        self.assertNotEqual(result, "Candidate A")
        self.assertEqual(verifier.await_count, 2)
        self.assertEqual(client.post_count, 2)

        names = [item["event"] for item in self.events]
        expected = [
            "final_audit_started",
            "final_audit_failed",
            "final_audit_feedback_created",
            "final_audit_feedback_delivered",
            "final_audit_correction_started",
            "final_audit_started",
            "final_audit_passed",
            "run_finished",
        ]
        positions = []
        search_from = 0
        for name in expected:
            position = names.index(name, search_from)
            positions.append(position)
            search_from = position + 1
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("run_failed", names)
        self.assertEqual(
            len({item["run_id"] for item in self.events}),
            1,
        )
        self.assertEqual(self.events[-1]["status"], "SUCCESS")

    async def test_rejected_candidate_and_feedback_reach_second_request(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        await self.run_case(
            [verifier_result("FAIL"), verifier_result("PASS")],
            fake_client=client,
        )
        second_messages = client.bodies[1]["messages"]
        self.assertEqual(second_messages[-2], {
            "role": "assistant",
            "content": "Candidate A",
        })
        feedback = second_messages[-1]
        self.assertEqual(feedback["role"], "user")
        self.assertIn("SERVER FINAL VERIFIER FEEDBACK", feedback["content"])
        self.assertIn("НЕ новая пользовательская задача", feedback["content"])
        self.assertIn("RAW TASK", feedback["content"])

    async def test_server_facts_survive_custom_feedback_template(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        with patch.object(
            server,
            "resolve_server_context_message",
            return_value="CUSTOM EDITABLE TEMPLATE",
        ):
            await self.run_case(
                [verifier_result("FAIL"), verifier_result("PASS")],
                fake_client=client,
            )
        feedback = client.bodies[1]["messages"][-1]["content"]
        self.assertTrue(feedback.startswith("CUSTOM EDITABLE TEMPLATE"))
        marker = "SERVER FACTS — NOT TEMPLATE CONTROLLED:\n"
        facts = json.loads(feedback.split(marker, 1)[1])
        self.assertEqual(facts["event_id"], "final_audit.feedback")
        self.assertEqual(
            facts["message_kind"], "SERVER_FINAL_VERIFIER_FEEDBACK"
        )
        self.assertFalse(facts["is_new_user_task"])
        self.assertEqual(facts["raw_task_authority"], "SOURCE_OF_TRUTH")
        self.assertEqual(
            facts["decision"], "SUCCESS_BLOCKED_CORRECTION_REQUESTED"
        )
        self.assertEqual(facts["verdict"], "FAIL")
        self.assertEqual(facts["reason"], "Evidence is incomplete.")
        self.assertEqual(facts["correction_cycle"], 1)
        self.assertEqual(facts["correction_limit"], 1)

    async def test_one_correction_allows_multiple_api_calls_and_a_tool(self) -> None:
        (self.workspace / "sample.txt").write_text("sample", encoding="utf-8")
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse(
                "",
                finish_reason="function_call",
                function_call={
                    "name": "read_file",
                    "arguments": {"path": "sample.txt"},
                },
            ),
            FakeResponse("Candidate B"),
        ])
        result, verifier, _client = await self.run_case(
            [verifier_result("FAIL"), verifier_result("PASS")],
            fake_client=client,
        )
        self.assertEqual(result, "Candidate B")
        self.assertEqual(client.post_count, 3)
        self.assertEqual(verifier.await_count, 2)
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_feedback_created"), 1)
        self.assertEqual(names.count("tool_finished"), 1)

    async def test_verification_required_is_independent_of_correction(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Premature correction"),
            FakeResponse("Candidate B"),
        ])
        calls = 0

        def missing_requirements(_state):
            nonlocal calls
            calls += 1
            if calls == 3:
                return [{"tool": "git_status", "reason": "required"}]
            return []

        result, verifier, _client = await self.run_case(
            [verifier_result("FAIL"), verifier_result("PASS")],
            fake_client=client,
            extra_patches=(
                patch.object(
                    server,
                    "_verification_missing_requirements",
                    side_effect=missing_requirements,
                ),
            ),
        )
        self.assertEqual(result, "Candidate B")
        self.assertEqual(verifier.await_count, 2)
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("verification_required"), 1)
        self.assertEqual(names.count("final_audit_feedback_created"), 1)

    async def test_second_semantic_fail_is_terminal_and_exposes_details(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        with self.assertRaises(server.FinalAuditSemanticError) as raised:
            await self.run_case(
                [verifier_result("FAIL"), verifier_result("FAIL")],
                fake_client=client,
            )
        self.assertIn("Evidence is incomplete", str(raised.exception))
        self.assertIn("Required evidence is missing", str(raised.exception))
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_failed"), 2)
        self.assertEqual(names.count("final_audit_feedback_created"), 1)
        self.assertEqual(names.count("final_audit_feedback_delivered"), 1)
        self.assertEqual(names.count("final_audit_correction_started"), 1)
        self.assertEqual(names.count("run_failed"), 1)
        self.assertNotIn("final_audit_passed", names)
        self.assertFalse(
            any(item["event"] == "run_finished" for item in self.events)
        )
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_correction_exhausted")
        self.assertEqual(self.last_verifier.await_count, 2)
        self.assertEqual(client.post_count, 2)

    async def test_runtime_error_is_fail_closed_and_distinct(self) -> None:
        error = verifier_runtime.VerifierRuntimeError("transport unavailable")
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_case(error)
        names = [item["event"] for item in self.events]
        self.assertIn("final_audit_error", names)
        self.assertNotIn("final_audit_failed", names)
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_runtime_error")

    async def test_protocol_error_is_fail_closed(self) -> None:
        error = verifier_runtime.VerifierProtocolError("malformed response")
        with self.assertRaisesRegex(RuntimeError, "VerifierProtocolError"):
            await self.run_case(error)
        names = [item["event"] for item in self.events]
        self.assertIn("final_audit_error", names)
        self.assertNotIn("run_finished", names)

    async def test_runtime_error_after_feedback_is_terminal(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_case(
                [
                    verifier_result("FAIL"),
                    verifier_runtime.VerifierRuntimeError("transport unavailable"),
                ],
                fake_client=client,
            )
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_feedback_created"), 1)
        self.assertEqual(names.count("run_failed"), 1)
        self.assertEqual(
            next(item for item in self.events if item["event"] == "run_failed")["reason"],
            "final_audit_runtime_error",
        )

    async def test_explicit_model_assignment_reaches_verifier(self) -> None:
        _result, verifier, _client = await self.run_case(
            verifier_result("PASS"),
            verifier_model_id="gigachat_3_lightning",
        )
        self.assertEqual(
            verifier.await_args.kwargs["verifier_model_id"],
            "gigachat_3_lightning",
        )

    async def test_original_raw_task_reaches_verifier(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        _result, verifier, _client = await self.run_case(
            [verifier_result("FAIL"), verifier_result("PASS")],
            fake_client=client,
        )
        self.assertEqual(verifier.await_count, 2)
        for audit_call in verifier.await_args_list:
            self.assertEqual(
                audit_call.kwargs["raw_task"], "ORIGINAL RAW TASK"
            )
            self.assertEqual(audit_call.kwargs["task_id"],
                             verifier.await_args_list[0].kwargs["task_id"])
        self.assertNotEqual(
            verifier.await_args_list[-1].kwargs["raw_task"], "Candidate B"
        )
        self.assertNotIn("messages", verifier.await_args_list[0].kwargs)
        self.assertNotIn("messages", verifier.await_args_list[1].kwargs)

    def test_v4_handoff_does_not_persist_chat_messages(self) -> None:
        source = inspect.getsource(server.run_agent_task)
        self.assertNotIn("append_raw_message", source)

    async def test_deterministic_gate_blocks_before_final_audit(self) -> None:
        verifier = AsyncMock(return_value=verifier_result("PASS"))
        missing = [{"tool": "git_status", "reason": "required"}]
        with (
            patch.object(server, "_verification_missing_requirements", return_value=missing),
            patch.object(server, "MAX_VERIFICATION_GATE_RETRIES", 0),
            patch.object(server, "run_verifier_check", verifier),
        ):
            with self.assertRaisesRegex(RuntimeError, "VERIFICATION GATE STUCK"):
                await self.run_case(
                    verifier_result("PASS"),
                    extra_patches=(patch.object(server, "run_verifier_check", verifier),),
                )
        verifier.assert_not_awaited()
        self.assertNotIn(
            "final_audit_started", [item["event"] for item in self.events]
        )

    async def test_context_contains_candidate_policy_and_fresh_server_facts(self) -> None:
        _result, verifier, _client = await self.run_case(verifier_result("PASS"))
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(
            context["candidate_final_response"]["content"], "CANDIDATE FINAL"
        )
        self.assertFalse(context["permission_policy"]["allow_verify"])
        self.assertEqual(
            context["deterministic_verification"]["missing_requirements"], []
        )
        self.assertEqual(context["fresh_git_status"]["stdout"], " M server.py")
        self.assertEqual(context["fresh_git_diff"]["stdout"], " M server.py")

    async def test_evidence_semantics_separates_run_mutations_from_git_state(self) -> None:
        _result, verifier, _client = await self.run_case(verifier_result("PASS"))
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        semantics = context["evidence_semantics"]
        self.assertIn("Source of truth", semantics["raw_task"])
        self.assertIn("not an authoritative fact", semantics["candidate_final_response"])
        self.assertIn("current RUN", semantics["mutation_facts"])
        self.assertIn("pre-existing or external", semantics["fresh_git_state"])
        self.assertIn("corroborated by mutation_facts", semantics["git_attribution_rule"])
        self.assertEqual(
            context["mutation_facts"],
            {"changed_files": [], "new_files": [], "deleted_files": []},
        )
        self.assertEqual(context["fresh_git_status"]["stdout"], " M server.py")

    def test_new_file_evidence_includes_current_content(self) -> None:
        new_file = self.workspace / "new_module.py"
        new_file.write_text("VALUE = 42\n", encoding="utf-8")
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        state = {"write_revision": 1, "changed_python_paths": ["new_module.py"]}
        backup = {
            "manifest": {
                "changed_files": [],
                "new_files": ["new_module.py"],
                "deleted_files": [],
            }
        }
        git_result = {
            "ok": True,
            "stdout": "?? new_module.py",
            "stderr": "",
            "truncated": False,
        }
        with (
            patch.object(server, "_agent_git_status", return_value=dict(git_result)),
            patch.object(server, "_agent_git_diff", return_value=dict(git_result)),
        ):
            context, metadata = server._collect_final_audit_evidence(
                root=self.workspace,
                candidate_final="Done",
                policy=policy,
                run_id="run-test",
                api_request_count=2,
                tool_call_count=3,
                verification_state=state,
                backup_session=backup,
            )
        payload = json.loads(context)
        self.assertEqual(
            payload["new_file_evidence"][0]["content"], "VALUE = 42\n"
        )
        self.assertTrue(payload["new_file_evidence"][0]["complete"])
        self.assertFalse(metadata["critical_for_mutating_run"])
        self.assertFalse(metadata["critical_for_success"])

    def test_truncated_new_file_is_marked_critical_for_mutating_run(self) -> None:
        new_file = self.workspace / "large.txt"
        new_file.write_text("0123456789", encoding="utf-8")
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        backup = {
            "manifest": {
                "changed_files": [],
                "new_files": ["large.txt"],
                "deleted_files": [],
            }
        }
        git_result = {"ok": True, "stdout": "", "stderr": "", "truncated": False}
        with (
            patch.object(server, "MAX_FINAL_AUDIT_NEW_FILE_BYTES", 4),
            patch.object(server, "_agent_git_status", return_value=dict(git_result)),
            patch.object(server, "_agent_git_diff", return_value=dict(git_result)),
        ):
            _context, metadata = server._collect_final_audit_evidence(
                root=self.workspace,
                candidate_final="Done",
                policy=policy,
                run_id="run-test",
                api_request_count=1,
                tool_call_count=1,
                verification_state={"write_revision": 1},
                backup_session=backup,
            )
        self.assertTrue(metadata["truncated"])
        self.assertTrue(metadata["critical_for_mutating_run"])
        self.assertTrue(metadata["critical_for_success"])
        self.assertIn("new_file_content_truncated:large.txt", metadata["reasons"])

    async def test_critical_incomplete_evidence_blocks_even_mocked_pass(self) -> None:
        incomplete = {
            "complete": False,
            "truncated": True,
            "reasons": ["fresh_git_diff_truncated"],
            "critical_for_success": True,
            "critical_reasons": ["fresh_git_diff_truncated"],
            "critical_for_mutating_run": True,
        }
        verifier = AsyncMock(return_value=verifier_result("PASS"))
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_case(
                verifier_result("PASS"),
                extra_patches=(
                    patch.object(
                        server,
                        "_collect_final_audit_evidence",
                        return_value=("{}", incomplete),
                    ),
                    patch.object(server, "run_verifier_check", verifier),
                ),
            )
        verifier.assert_not_awaited()
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_evidence_incomplete")

    async def test_trace_outcomes_are_distinct(self) -> None:
        await self.run_case(verifier_result("PASS"))
        self.assertIn("final_audit_passed", [item["event"] for item in self.events])

        self.events.clear()
        with self.assertRaises(server.FinalAuditSemanticError):
            await self.run_case(verifier_result("FAIL"))
        self.assertIn("final_audit_failed", [item["event"] for item in self.events])

        self.events.clear()
        with self.assertRaises(RuntimeError):
            await self.run_case(verifier_runtime.VerifierRuntimeError("down"))
        self.assertIn("final_audit_error", [item["event"] for item in self.events])

    def test_read_disabled_is_explicit_and_does_not_read_git(self) -> None:
        permissions = dict(self.permissions, allow_read=False)
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(permissions)
        )
        with (
            patch.object(server, "_agent_git_status") as status,
            patch.object(server, "_agent_git_diff") as diff,
        ):
            context, metadata = server._collect_final_audit_evidence(
                root=self.workspace,
                candidate_final="Done",
                policy=policy,
                run_id="run-test",
                api_request_count=1,
                tool_call_count=0,
                verification_state={"write_revision": 0},
                backup_session=None,
            )
        payload = json.loads(context)
        status.assert_not_called()
        diff.assert_not_called()
        self.assertFalse(payload["fresh_git_status"]["available"])
        self.assertIn("read_disabled", metadata["reasons"][0])
        self.assertFalse(metadata["critical_for_success"])

    def test_context_hard_size_limit_is_critical_for_success(self) -> None:
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        git_result = {"ok": True, "stdout": "", "stderr": "", "truncated": False}
        with (
            patch.object(server, "MAX_FINAL_AUDIT_CONTEXT_BYTES", 1),
            patch.object(server, "_agent_git_status", return_value=dict(git_result)),
            patch.object(server, "_agent_git_diff", return_value=dict(git_result)),
        ):
            _context, metadata = server._collect_final_audit_evidence(
                root=self.workspace,
                candidate_final="Done",
                policy=policy,
                run_id="run-test",
                api_request_count=1,
                tool_call_count=0,
                verification_state={"write_revision": 0},
                backup_session=None,
            )
        self.assertTrue(metadata["critical_for_success"])
        self.assertIn(
            "verification_context_size_limit_exceeded",
            metadata["critical_reasons"],
        )


class FinalAuditUiFlowTests(unittest.TestCase):
    def test_worker_passes_verifier_model_to_run_agent_task(self) -> None:
        app = object.__new__(ultra_ui.UltraApp)
        app.trace_events = queue.Queue()
        app.events = queue.Queue()
        run = AsyncMock(return_value="DONE")
        with (
            patch.object(ultra_ui, "run_agent_task", run),
            patch.object(
                ultra_ui,
                "append_raw_message",
                return_value={"producer": None},
            ),
        ):
            app._worker(
                "Task",
                "C:/workspace",
                {},
                "chat-1",
                "gigachat_ultra",
                "gigachat_3_lightning",
            )
        self.assertEqual(
            run.await_args.kwargs["verifier_model_id"],
            "gigachat_3_lightning",
        )

    def test_send_captures_current_verifier_selection(self) -> None:
        source = inspect.getsource(ultra_ui.UltraApp._send)
        self.assertIn("self.verifier_model_id_var.get()", source)
        self.assertIn("get_model_spec(verifier_model_id)", source)
        self.assertIn("verifier_model_id", source)


if __name__ == "__main__":
    unittest.main()
