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
from audit_storage import load_audit_thread
import ultra_ui
import verifier_runtime


SAFE_ALLOW_DECLARED_TARGET_TASK = (
    "Работай только с файлом:\n\n"
    "Документация/SAFE_ALLOW_TEST.md\n\n"
    "Текущее ожидаемое содержимое файла:\n\nTEST_2\n\n"
    "Нужно выполнить реальное изменение файла.\n\n"
    "Замени ТОЧНО:\n\nTEST_2\n\nна:\n\nTEST_3\n\n"
    "Не используй write_file.\n\n"
    "Не изменяй никакие другие файлы.\n"
    "Не изменяй Python runtime.\n"
    "Не изменяй tests.\n\n"
    "git_diff / git_status — только optional read-only diagnostics."
)


def verifier_result(
    verdict: str = "PASS",
    *,
    reason: str | None = None,
    violations: tuple[str, ...] | None = None,
    required_action: str | None = None,
    verifier_run_id: str = "ver_test_final",
    check_type: str = "FINAL",
) -> verifier_runtime.VerifierResult:
    failed = verdict == "FAIL"
    return verifier_runtime.VerifierResult(
        verdict=verdict,
        check_type=check_type,
        violations=(
            violations
            if violations is not None
            else (("Required evidence is missing.",) if failed else ())
        ),
        reason=(
            reason
            if reason is not None
            else ("Evidence is incomplete." if failed else "Evidence is sufficient.")
        ),
        required_action=(
            required_action
            if required_action is not None
            else ("Collect the missing evidence." if failed else "None.")
        ),
        verifier_run_id=verifier_run_id,
        model_id="gigachat_3_pro",
        model_display_name="GigaChat 3 Pro",
        provider="gigachat",
        provider_model_id="GigaChat-3-Pro",
        task_id="task-test",
        checkpoint_id=None,
        operation_id=None,
    )


def fail_result(label: str) -> verifier_runtime.VerifierResult:
    return verifier_result(
        "FAIL",
        reason=f"Reason {label}",
        violations=(f"Violation {label}",),
        required_action=f"Fix {label}",
        verifier_run_id=f"ver_{label.lower()}",
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


class BackupContextSnapshotTests(unittest.TestCase):
    def test_audit_namespace_is_excluded_but_other_context_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = base / "workspace"
            context = workspace / ".ultra"
            (context / "audit" / "chat").mkdir(parents=True)
            (context / "chats").mkdir()
            (context / "workspace.json").write_text('{"id":"ws_test"}', encoding="utf-8")
            (context / "project_context.md").write_text("PROJECT CONTEXT", encoding="utf-8")
            (context / "chats" / "raw.json").write_text("RAW HISTORY", encoding="utf-8")
            (context / "audit" / "chat" / "run.json").write_text("AUDIT THREAD", encoding="utf-8")
            policy = server._normalize_permissions({"auto_backup": True})
            session = server._create_backup_session(
                base, workspace, "run_with_audit", "task", policy,
                backup_base=base / "backups", workspace_id="ws_test", chat_id="chat",
            )
            snapshot = session["backup_dir"] / "context" / ".ultra"
            self.assertEqual(session["manifest"]["context_snapshot"], "context/.ultra")
            self.assertFalse((snapshot / "audit").exists())
            self.assertEqual((snapshot / "workspace.json").read_text(encoding="utf-8"), '{"id":"ws_test"}')
            self.assertEqual((snapshot / "project_context.md").read_text(encoding="utf-8"), "PROJECT CONTEXT")
            self.assertEqual((snapshot / "chats" / "raw.json").read_text(encoding="utf-8"), "RAW HISTORY")

            (context / "audit" / "chat" / "run.json").unlink()
            (context / "audit" / "chat").rmdir()
            (context / "audit").rmdir()
            session_without_audit = server._create_backup_session(
                base, workspace, "run_without_audit", "task", policy,
                backup_base=base / "backups", workspace_id="ws_test", chat_id="chat",
            )
            second_snapshot = session_without_audit["backup_dir"] / "context" / ".ultra"
            self.assertTrue((second_snapshot / "workspace.json").is_file())
            self.assertTrue((second_snapshot / "chats" / "raw.json").is_file())
            self.assertFalse((second_snapshot / "audit").exists())


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

    async def test_executor_prompt_keeps_required_checks_but_git_is_optional(self) -> None:
        _result, _verifier, client = await self.run_case(verifier_result("PASS"))
        system_prompt = client.bodies[0]["messages"][0]["content"]
        self.assertIn("обязательно успешно проверь", system_prompt)
        self.assertIn("через python_compile", system_prompt)
        self.assertIn("дополнительно ui_smoke_test", system_prompt)
        self.assertIn("git_status и git_diff доступны как read-only diagnostic tools", system_prompt)
        self.assertIn("Отсутствие Git-репозитория не является ошибкой задачи", system_prompt)
        self.assertIn("Отсутствие вызовов git_status/git_diff не блокирует SUCCESS", system_prompt)
        self.assertNotIn("обязательны git_diff и git_status", system_prompt)
        self.assertNotIn("После ПОСЛЕДНЕЙ записи/удаления обязательны git", system_prompt)

    async def run_case(
        self,
        verifier_side_effect,
        *,
        verifier_model_id: str = "gigachat_3_pro",
        fake_client: FakeClient | None = None,
        extra_patches: tuple = (),
        mock_git: bool = True,
        task_block_id: str | None = None,
        task: str = "ORIGINAL RAW TASK",
        permission_request_callback=None,
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
        backup_dir = self.runtime / "backup" / "run"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = {
            "backup_dir": backup_dir,
            "backed_up_paths": set(),
            "delete_backed_up_paths": set(),
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
            if mock_git:
                stack.enter_context(
                    patch.object(server, "_agent_git_status", return_value=dict(git_result))
                )
                stack.enter_context(
                    patch.object(server, "_agent_git_diff", return_value=dict(git_result))
                )
            stack.enter_context(
                patch.object(
                    server, "_request_audit_diagnostic",
                    AsyncMock(return_value="Краткое основание решения."),
                )
            )
            stack.enter_context(patch.object(server, "run_verifier_check", verifier))
            for item in extra_patches:
                stack.enter_context(item)
            result = await server.run_agent_task(
                task,
                str(self.workspace),
                permissions=self.permissions,
                on_event=self.events.append,
                verifier_model_id=verifier_model_id,
                task_block_id=task_block_id,
                permission_request_callback=permission_request_callback,
            )
        return result, verifier, client

    async def test_task_block_id_links_run_event_and_audit_without_context_pollution(self) -> None:
        from context_storage import new_task_block_id
        from audit_storage import AuditThreadRecorder

        task_id = new_task_block_id()
        previous_audit = AuditThreadRecorder(self.workspace, "ws_test", None, "old_run")
        previous_audit.observe({
            "event": "final_audit_failed", "reason": "AUDIT_ONLY_SENTINEL",
        })
        result, _verifier, client = await self.run_case(
            verifier_result("PASS"), task_block_id=task_id
        )
        self.assertEqual(result, "CANDIDATE FINAL")
        started = next(item for item in self.events if item["event"] == "run_started")
        self.assertEqual(started["task_block_id"], task_id)
        self.assertNotEqual(started["run_id"], task_id)
        thread = load_audit_thread(self.workspace, "ws_test", None, started["run_id"])
        self.assertEqual(thread["task_block_id"], task_id)
        self.assertNotIn(task_id, json.dumps(client.bodies[0]["messages"]))
        self.assertNotIn("AUDIT_ONLY_SENTINEL", json.dumps(client.bodies[0]["messages"]))

    async def test_direct_run_without_task_block_id_remains_supported(self) -> None:
        result, _verifier, _client = await self.run_case(verifier_result("PASS"))
        self.assertEqual(result, "CANDIDATE FINAL")
        started = next(item for item in self.events if item["event"] == "run_started")
        self.assertIsNone(started["task_block_id"])
        self.assertIsNone(load_audit_thread(
            self.workspace, "ws_test", None, started["run_id"]
        )["task_block_id"])

    async def test_non_git_workspace_mutation_reaches_final_pass(self) -> None:
        self.assertFalse((self.workspace / ".git").exists())
        self.permissions.update(allow_write=True, allow_verify=True, tool_limit=3)
        client = FakeClient([
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "write_file", "arguments": {"path": "result.txt", "content": "done"},
            }),
            FakeResponse("Done"),
        ])
        result, verifier, _ = await self.run_case(
            verifier_result("PASS"), fake_client=client, mock_git=False
        )
        self.assertEqual(result, "Done")
        self.assertEqual((self.workspace / "result.txt").read_text(encoding="utf-8"), "done")
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertFalse(context["fresh_git_status"]["available"])
        self.assertTrue(context["run_owned_filesystem_evidence"][0]["match"])
        self.assertTrue(context["evidence_completeness"]["complete"])
        self.assertFalse(context["evidence_completeness"]["critical_for_success"])

    async def test_precise_edit_tracks_run_and_reaches_final_audit(self) -> None:
        (self.workspace / "result.txt").write_text("old value", encoding="utf-8")
        expected = server._sha256_utf8("old value")
        self.permissions.update(allow_write=True, allow_verify=True, tool_limit=3)
        client = FakeClient([
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "replace_text", "arguments": {
                    "path": "result.txt", "old_text": "old", "new_text": "new",
                    "expected_content_sha256": expected,
                },
            }),
            FakeResponse("Done"),
        ])
        result, verifier, _ = await self.run_case(
            verifier_result("PASS"), fake_client=client, mock_git=False
        )
        self.assertEqual(result, "Done")
        self.assertEqual((self.workspace / "result.txt").read_text(encoding="utf-8"), "new value")
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(context["run_facts"]["write_revision"], 1)
        self.assertEqual(context["mutation_facts"]["changed_files"], ["result.txt"])
        self.assertTrue(context["run_owned_filesystem_evidence"][0]["match"])
        self.assertEqual(context["run_owned_filesystem_evidence"][0]["actual_content_sha256"],
                         server._sha256_utf8("new value"))

    async def test_non_git_workspace_hash_mismatch_blocks_verifier(self) -> None:
        self.permissions.update(allow_write=True, allow_verify=True, tool_limit=3)
        client = FakeClient([
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "write_file", "arguments": {"path": "result.txt", "content": "expected"},
            }),
            FakeResponse("Done"),
        ])
        original_write = server._agent_write_file

        def tampered_write(*args, **kwargs):
            result = original_write(*args, **kwargs)
            (self.workspace / "result.txt").write_text("external", encoding="utf-8")
            return result

        with self.assertRaisesRegex(RuntimeError, "FinalAuditEvidenceError.*"):
            await self.run_case(
                verifier_result("PASS"), fake_client=client, mock_git=False,
                extra_patches=(patch.object(server, "_agent_write_file", side_effect=tampered_write),),
            )
        self.last_verifier.assert_not_awaited()
        self.assertNotIn("run_completed", [event["event"] for event in self.events])

    def test_run_owned_delete_absent_and_reappeared(self) -> None:
        expected = {"deleted.txt": {"state": "absent"}}
        evidence, mismatches = server._verify_run_owned_filesystem(self.workspace, expected)
        self.assertTrue(evidence[0]["match"])
        self.assertEqual(mismatches, [])
        (self.workspace / "deleted.txt").write_text("external", encoding="utf-8")
        evidence, mismatches = server._verify_run_owned_filesystem(self.workspace, expected)
        self.assertFalse(evidence[0]["match"])
        self.assertEqual(mismatches, ["run_owned_filesystem_mismatch:deleted.txt"])
        policy = server._prepare_policy_for_workspace(
            self.workspace, server._normalize_permissions(self.permissions)
        )
        _context, metadata = server._collect_final_audit_evidence(
            root=self.workspace, candidate_final="Done", policy=policy,
            run_id="test", api_request_count=1, tool_call_count=1,
            verification_state={"write_revision": 1}, backup_session=None,
            run_owned_state=expected,
        )
        self.assertTrue(metadata["critical_for_success"])
        self.assertTrue(metadata["critical_for_mutating_run"])

    def test_run_owned_jsonl_uses_utf16_logical_content(self) -> None:
        content = '{"message": "Привет"}\n'
        (self.workspace / "messages.jsonl").write_bytes(content.encode("utf-16"))
        expected = {"messages.jsonl": {
            "state": "present", "content_sha256": server._sha256_utf8(content),
        }}
        evidence, mismatches = server._verify_run_owned_filesystem(self.workspace, expected)
        self.assertEqual(mismatches, [])
        self.assertTrue(evidence[0]["match"])

    def test_python_and_ui_gates_remain_required_without_git(self) -> None:
        state = {
            "write_revision": 1, "changed_python_paths": ["module.py"],
            "python_write_revision": 1, "python_verified_revision": None,
            "python_verified_paths": [], "ui_smoke_required": False,
        }
        missing = server._verification_missing_requirements(state)
        self.assertEqual([item["tool"] for item in missing], ["python_compile"])
        state.update(changed_python_paths=[], ui_smoke_required=True,
                     ui_smoke_write_revision=1, ui_smoke_verified_revision=None)
        missing = server._verification_missing_requirements(state)
        self.assertEqual([item["tool"] for item in missing], ["ui_smoke_test"])

    async def test_valid_pass_allows_normal_success(self) -> None:
        result, verifier, _client = await self.run_case(verifier_result("PASS"))
        self.assertEqual(result, "CANDIDATE FINAL")
        verifier.assert_awaited_once()
        self.assertIn("final_audit_passed", [item["event"] for item in self.events])
        self.assertNotIn(
            "final_audit_retry_evaluated",
            [item["event"] for item in self.events],
        )
        self.assertNotIn("run_failed", [item["event"] for item in self.events])
        self.assertEqual(self.events[-1]["event"], "run_finished")
        self.assertEqual(self.events[-1]["status"], "SUCCESS")

    async def test_no_tool_zero_revision_still_calls_final_audit(self) -> None:
        _result, verifier, _client = await self.run_case(verifier_result("PASS"))
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(context["run_facts"]["tool_call_count"], 0)
        self.assertEqual(context["run_facts"]["write_revision"], 0)
        verifier.assert_awaited_once()

    def test_mutation_intent_is_conservative(self) -> None:
        for task in ("Проанализируй server.py. Ничего не меняй.",
                     "не изменяй файл server.py", "Как дела?"):
            self.assertEqual(server._classify_mutation_intent(task)["mutation_intent"], "UNKNOWN")
        self.assertEqual(server._classify_mutation_intent(
            "Обнови только файл:\nДокументация/09_Обязательный регламент Ultra.md"
        )["mutation_intent"], "LIKELY_MUTATION")

    def test_mutation_intent_respects_local_negation_and_read_only_diagnostics(self) -> None:
        cases = (
            ("Проанализируй server.py. Ничего не меняй.", "UNKNOWN"),
            ("Не изменяй файл server.py.", "UNKNOWN"),
            ("Как дела?", "UNKNOWN"),
            ("Analyze server.py; do not modify anything.", "UNKNOWN"),
            ("Обнови только файл:\nДокументация/09_Обязательный регламент Ultra.md", "LIKELY_MUTATION"),
            ("Обнови только файл:\nДокументация/13_Архитектура оперативной верификации и контроля выполнения задач.md\nНе изменяй другие файлы.", "LIKELY_MUTATION"),
            ("Обнови document.md.\ngit_diff / git_status — только optional read-only diagnostics.", "LIKELY_MUTATION"),
            ("ИЗМЕНЯТЬ МОЖНО ТОЛЬКО ОДИН ФАЙЛ:\nДокументация/13_Архитектура оперативной верификации и контроля выполнения задач.md\nEDIT 1–8\nreplace_text\ninsert_before\nНЕ изменять Python runtime\nread-only diagnostics", "LIKELY_MUTATION"),
        )
        for task, expected in cases:
            with self.subTest(task=task[:55]):
                self.assertEqual(server._classify_mutation_intent(task)["mutation_intent"], expected)
        classified = server._classify_mutation_intent(cases[-1][0])
        self.assertTrue(any("13_архитектура" in reason for reason in classified["reasons"]))

    def test_mutation_intent_uses_only_explicit_declared_target_for_distant_edit(self) -> None:
        cases = (
            (SAFE_ALLOW_DECLARED_TARGET_TASK, "LIKELY_MUTATION", "safe_allow_test.md"),
            ("Работай только с файлом:\nfoo.md\n\nОписание.\nЕщё контекст.\nЗамени A на B.",
             "LIKELY_MUTATION", "foo.md"),
            ("Работай только с файлом:\nfoo.md\nПроанализируй содержимое. Ничего не меняй.",
             "UNKNOWN", None),
            ("Работай только с файлом:\nfoo.md\nНе изменяй этот файл.",
             "UNKNOWN", None),
            ("Работай только с файлом:\nfoo.md\nНе изменяй server.py.\nЗамени A на B.",
             "LIKELY_MUTATION", "foo.md"),
            ("Работай только с файлом:\nfoo.md\nЗамени A на B.\n"
             "git_diff / git_status — optional read-only diagnostics.",
             "LIKELY_MUTATION", "foo.md"),
            ("Изменять можно только один файл: foo.md\nВставь новый блок.",
             "LIKELY_MUTATION", "foo.md"),
            ("Целевой файл:\nfoo.md\nСоздай новый блок.",
             "LIKELY_MUTATION", "foo.md"),
            ("Target file: foo.md\nReplace A with B.",
             "LIKELY_MUTATION", "foo.md"),
            ("Work only with file:\nfoo.md\nReplace A with B.",
             "LIKELY_MUTATION", "foo.md"),
            ("Работай с файлом:\nfoo.md\nНе изменяй его.",
             "UNKNOWN", None),
        )
        for task, expected, target in cases:
            with self.subTest(task=task[:80]):
                result = server._classify_mutation_intent(task)
                self.assertEqual(result["mutation_intent"], expected)
                if target:
                    self.assertTrue(any(target in reason for reason in result["reasons"]))
                    self.assertIn("target_source:declared", result["reasons"])
                    self.assertNotIn("target:server.py", result["reasons"])

    async def test_mutation_intent_is_diagnostic_only_for_declared_target_and_fix_title(self) -> None:
        for task in (SAFE_ALLOW_DECLARED_TARGET_TASK, "TASK — fix report.txt\\nOnly explain the blocker."):
            with self.subTest(task=task[:32]):
                self.events.clear()
                client = FakeClient([FakeResponse("No change was made.")])
                result, verifier, _ = await self.run_case(
                    verifier_result("PASS"), fake_client=client, task=task,
                )
                self.assertEqual(result, "No change was made.")
                self.assertEqual(client.post_count, 1)
                self.assertEqual([call.kwargs["check_type"] for call in verifier.await_args_list], ["FINAL"])
                self.assertFalse(any(event["event"].startswith("execution_consistency_")
                                     for event in self.events))
                classified = next(event for event in self.events
                                  if event["event"] == "mutation_intent_classified")
                self.assertEqual(classified["mutation_intent"], "LIKELY_MUTATION")

    async def test_read_only_zero_tool_task_uses_only_final(self) -> None:
        _result, verifier, client = await self.run_case(
            verifier_result("PASS"), task="Проанализируй server.py. Ничего не меняй.",
        )
        verifier.assert_awaited_once()
        self.assertEqual(verifier.await_args.kwargs["check_type"], "FINAL")
        self.assertEqual(client.post_count, 1)

    @staticmethod
    def denied_call(name: str) -> FakeResponse:
        args = {"path": "result.txt", "expected_content_sha256": "0" * 64}
        if name == "replace_text":
            args.update(old_text="old", new_text="new")
        elif name == "insert_after":
            args.update(marker="old", content="new")
        elif name == "delete_file":
            args = {"path": "result.txt"}
        return FakeResponse("", finish_reason="function_call",
                            function_call={"name": name, "arguments": args})

    async def test_first_write_denial_is_physical_and_does_not_review(self) -> None:
        target = self.workspace / "result.txt"
        target.write_text("old", encoding="utf-8")
        client = FakeClient([self.denied_call("replace_text"), FakeResponse("Cannot edit.")])
        result, verifier, _ = await self.run_case(verifier_result("PASS"),
            fake_client=client, task="Replace old in result.txt")
        self.assertEqual(result, "Cannot edit.")
        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        denied = [e for e in self.events if e["event"] == "permission_denied"]
        self.assertEqual([(e["capability"], e["attempt"]) for e in denied], [("WRITE", 1)])
        self.assertIn("permission.denied", str(client.bodies[1]["messages"]))
        self.assertEqual([c.kwargs["check_type"] for c in verifier.await_args_list], ["FINAL"])
        self.assertFalse(any(e["event"] == "permission_review_started" for e in self.events))
        thread = load_audit_thread(self.workspace, "ws_test", None, denied[0]["run_id"])
        self.assertEqual(thread["permission_escalation"]["attempts"][0]["tool"], "replace_text")

    async def test_write_review_pass_grant_continues_same_run_without_replaying_denial(self) -> None:
        self.permissions["allow_verify"] = True
        target = self.workspace / "result.txt"
        target.write_text("old", encoding="utf-8")
        client = FakeClient([
            self.denied_call("replace_text"), self.denied_call("insert_after"),
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "write_file", "arguments": {"path": "result.txt", "content": "done"},
            }), FakeResponse("Done"),
        ])
        requests = []
        def grant(payload):
            requests.append(payload)
            self.assertEqual(target.read_text(encoding="utf-8"), "old")
            return True
        result, verifier, _ = await self.run_case([
            verifier_result("PASS", check_type="PERMISSION"), verifier_result("PASS"),
        ], fake_client=client, task="Update result.txt", permission_request_callback=grant)
        self.assertEqual(result, "Done")
        self.assertEqual(target.read_text(encoding="utf-8"), "done")
        self.assertEqual([c.kwargs["check_type"] for c in verifier.await_args_list],
                         ["PERMISSION", "FINAL"])
        self.assertEqual([a["tool"] for a in requests[0]["attempts"]],
                         ["replace_text", "insert_after"])
        self.assertEqual(len({e["run_id"] for e in self.events}), 1)
        self.assertEqual(len([e for e in self.events if e["event"] == "permission_review_started"]), 1)
        self.assertEqual(len([e for e in self.events if e["event"] == "permission_granted"]), 1)
        self.assertIn("Capability WRITE", str(client.bodies[2]["messages"]))
        review_context = json.loads(verifier.await_args_list[0].kwargs["verification_context"])
        self.assertFalse(review_context["denied_calls_executed"])
        self.assertEqual(review_context["write_revision"], 0)
        self.assertEqual(review_context["run_owned_mutation_state"], {})
        self.assertNotIn("WRITE", review_context["allowed_capabilities"])
        thread = load_audit_thread(self.workspace, "ws_test", None, requests[0]["run_id"])
        self.assertEqual(thread["permission_escalation"]["status"], "GRANTED")
        self.assertEqual(thread["permission_escalation"]["user_decision"], "GRANTED")

    async def test_write_review_pass_user_deny_blocks_without_mutation(self) -> None:
        self.permissions["allow_verify"] = True
        target = self.workspace / "result.txt"
        target.write_text("old", encoding="utf-8")
        client = FakeClient([self.denied_call("replace_text"), self.denied_call("insert_after")])
        result, verifier, _ = await self.run_case(
            verifier_result("PASS", check_type="PERMISSION"),
            fake_client=client, task="Update result.txt",
            permission_request_callback=lambda _: False,
        )
        self.assertIn("permission_not_granted", result)
        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        self.assertEqual(client.post_count, 2)
        self.assertEqual([c.kwargs["check_type"] for c in verifier.await_args_list], ["PERMISSION"])
        self.assertEqual(self.events[-1]["status"], "BLOCKED")

    async def test_write_review_fail_has_no_prompt_and_repeat_blocks(self) -> None:
        client = FakeClient([self.denied_call("replace_text"),
                             self.denied_call("insert_after"),
                             self.denied_call("replace_text")])
        callback = Mock(return_value=True)
        result, verifier, _ = await self.run_case(
            verifier_result("FAIL", check_type="PERMISSION"),
            fake_client=client, task="Explain result.txt",
            permission_request_callback=callback,
        )
        self.assertIn("permission_escalation_not_justified_repeat", result)
        callback.assert_not_called()
        self.assertEqual(verifier.await_count, 1)
        self.assertEqual(client.post_count, 3)
        self.assertEqual(self.events[-1]["status"], "BLOCKED")

    async def test_callback_unavailable_fails_closed(self) -> None:
        self.permissions["allow_verify"] = True
        client = FakeClient([self.denied_call("replace_text"), self.denied_call("insert_after")])
        result, verifier, _ = await self.run_case(
            verifier_result("PASS", check_type="PERMISSION"),
            fake_client=client, task="Update result.txt",
        )
        self.assertIn("permission_callback_unavailable", result)
        self.assertEqual(verifier.await_count, 1)
        self.assertEqual(self.events[-1]["status"], "BLOCKED")

    async def test_grant_cannot_bypass_verify_dependency(self) -> None:
        client = FakeClient([self.denied_call("replace_text"), self.denied_call("insert_after")])
        callback = Mock(return_value=True)
        result, verifier, _ = await self.run_case(
            verifier_result("PASS", check_type="PERMISSION"),
            fake_client=client, task="Update result.txt",
            permission_request_callback=callback,
        )
        self.assertIn("permission_policy_validation_failed", result)
        callback.assert_not_called()
        self.assertEqual(verifier.await_count, 1)

    async def test_permission_review_protocol_error_blocks_without_prompt(self) -> None:
        client = FakeClient([self.denied_call("replace_text"), self.denied_call("insert_after")])
        callback = Mock(return_value=True)
        result, verifier, _ = await self.run_case(
            verifier_runtime.VerifierProtocolError("malformed"),
            fake_client=client, task="Update result.txt",
            permission_request_callback=callback,
        )
        self.assertIn("permission_review_error", result)
        callback.assert_not_called()
        self.assertEqual(verifier.await_count, 1)

    async def test_delete_capability_is_independent(self) -> None:
        self.permissions["allow_verify"] = True
        target = self.workspace / "result.txt"
        target.write_text("old", encoding="utf-8")
        client = FakeClient([self.denied_call("delete_file"), self.denied_call("delete_file")])
        result, verifier, _ = await self.run_case(
            verifier_result("PASS", check_type="PERMISSION"),
            fake_client=client, task="Delete result.txt",
            permission_request_callback=lambda _: False,
        )
        self.assertIn("permission_not_granted", result)
        self.assertTrue(target.exists())
        self.assertEqual([e["capability"] for e in self.events
                          if e["event"] == "permission_denied"], ["DELETE", "DELETE"])
        self.assertEqual(verifier.await_count, 1)

    async def test_scope_denial_does_not_widen_scope(self) -> None:
        (self.workspace / "inside").mkdir()
        self.permissions["write_scope"] = "inside"
        client = FakeClient([self.denied_call("replace_text")])
        callback = Mock(return_value=True)
        result, verifier, _ = await self.run_case(
            verifier_result("PASS"), fake_client=client,
            task="Update result.txt", permission_request_callback=callback,
        )
        self.assertIn("permission_scope_blocked", result)
        callback.assert_not_called()
        verifier.assert_not_awaited()
        self.assertEqual(self.events[-1]["status"], "BLOCKED")

    async def test_exact_repeated_error_detector_remains_active(self) -> None:
        call = FakeResponse("", finish_reason="function_call", function_call={
            "name": "read_file", "arguments": {"path": "missing.txt"},
        })
        client = FakeClient([call, call, call])
        with self.assertRaisesRegex(RuntimeError, "LOOP DETECTED"):
            await self.run_case(verifier_result("PASS"), fake_client=client,
                                task="Read missing.txt")
        self.assertEqual(client.post_count, 3)
        self.assertEqual(self.events[-1]["reason"], "loop_detected")

    async def test_immediate_mutation_has_no_consistency_overhead(self) -> None:
        self.permissions.update(allow_write=True, allow_verify=True)
        client = FakeClient([
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "write_file", "arguments": {"path": "result.txt", "content": "done"},
            }), FakeResponse("Done"),
        ])
        _result, verifier, _ = await self.run_case(verifier_result("PASS"),
            fake_client=client, task="Update file result.txt")
        verifier.assert_awaited_once()
        self.assertFalse(any(item["event"].startswith("execution_consistency_")
                             for item in self.events))

    def test_candidate_fingerprint_is_conservative_nfc(self) -> None:
        baseline = server._candidate_final_fingerprint("Café\r\n  code  \r\n")
        equivalent = server._candidate_final_fingerprint(
            "Cafe\u0301\n  code\n\n"
        )
        self.assertEqual(baseline, equivalent)
        self.assertNotEqual(
            baseline,
            server._candidate_final_fingerprint("café\n  code"),
        )
        self.assertNotEqual(
            baseline,
            server._candidate_final_fingerprint("Café\n code"),
        )

    def test_failure_signatures_are_deterministic_and_distinct(self) -> None:
        first = server._final_audit_failure_signatures(
            check_type="FINAL",
            reason="  REASON   A ",
            violations=("Path X", "Section 2"),
            required_action="Fix now",
        )
        reordered = server._final_audit_failure_signatures(
            check_type="final",
            reason="reason a",
            violations=(" section 2 ", "PATH X"),
            required_action=" FIX   NOW ",
        )
        self.assertEqual(first, reordered)

        changed_action = server._final_audit_failure_signatures(
            check_type="FINAL",
            reason="Reason A",
            violations=("Path X", "Section 2"),
            required_action="Different action",
        )
        self.assertNotEqual(first[0], changed_action[0])
        self.assertEqual(first[1], changed_action[1])

        no_violations_a = server._final_audit_failure_signatures(
            check_type="FINAL",
            reason="Reason A",
            violations=(),
            required_action="One",
        )
        no_violations_b = server._final_audit_failure_signatures(
            check_type="FINAL",
            reason="Reason B",
            violations=(),
            required_action="One",
        )
        self.assertNotEqual(no_violations_a[1], no_violations_b[1])

    def test_repeated_identical_write_is_not_run_owned_progress(self) -> None:
        state = {}
        empty = server._run_owned_state_fingerprint(state)
        server._record_run_owned_mutation(
            state,
            function_name="write_file",
            relative_path="folder/file.txt",
            content="same content",
        )
        first = server._run_owned_state_fingerprint(state)
        self.assertNotEqual(empty, first)

        server._record_run_owned_mutation(
            state,
            function_name="write_file",
            relative_path="folder\\file.txt",
            content="same content",
        )
        self.assertEqual(first, server._run_owned_state_fingerprint(state))

        server._record_run_owned_mutation(
            state,
            function_name="write_file",
            relative_path="folder/file.txt",
            content="different content",
        )
        changed = server._run_owned_state_fingerprint(state)
        self.assertNotEqual(first, changed)

        server._record_run_owned_mutation(
            state,
            function_name="delete_file",
            relative_path="folder/file.txt",
        )
        self.assertNotEqual(changed, server._run_owned_state_fingerprint(state))

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
        error = next(
            item for item in self.events if item["event"] == "final_audit_error"
        )
        self.assertEqual(error["final_audit_attempt_count"], 0)

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
            "final_audit_retry_evaluated",
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
        self.assertEqual(len({item["run_id"] for item in self.events}), 1)
        self.assertEqual(self.events[-1]["status"], "SUCCESS")

    async def test_diagnostic_question_includes_verifier_findings(self) -> None:
        diagnostic = AsyncMock(return_value="Краткое основание решения.")
        result, _verifier, client = await self.run_case(
            [fail_result("A"), verifier_result("PASS")],
            fake_client=FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")]),
            extra_patches=(patch.object(server, "_request_audit_diagnostic", diagnostic),),
        )
        self.assertEqual(result, "Candidate B")
        self.assertEqual(diagnostic.await_count, 1)
        args = diagnostic.await_args.args
        self.assertEqual(args[2], server.MODEL)
        self.assertEqual(args[4], "Candidate A")
        self.assertIn("REASON:\nReason A", args[5])
        self.assertIn("VIOLATIONS:\n- Violation A", args[5])
        self.assertIn("REQUIRED ACTION:\nFix A", args[5])
        self.assertIn("Кратко объясни", args[5])
        event = next(item for item in self.events if item["event"] == "audit_diagnostic_question")
        self.assertEqual(event["text"], args[5])
        self.assertFalse(any("REASON:\nReason A" in str(item.get("content"))
                             for item in client.bodies[1]["messages"]))

    async def test_audit_thread_persists_real_fail_diagnostic_tools_and_resolution(self) -> None:
        (self.workspace / "sample.txt").write_text("sample", encoding="utf-8")
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "read_file", "arguments": {"path": "sample.txt"},
            }),
            FakeResponse("Candidate B"),
        ])
        result, _verifier, _ = await self.run_case(
            [fail_result("A"), verifier_result("PASS")], fake_client=client
        )
        self.assertEqual(result, "Candidate B")
        run_id = next(item["run_id"] for item in self.events if item["event"] == "run_started")
        thread = load_audit_thread(self.workspace, "ws_test", None, run_id)
        self.assertEqual(len(thread["issues"]), 1)
        issue = thread["issues"][0]
        self.assertEqual(issue["reason"], "Reason A")
        self.assertEqual(issue["violations"], ["Violation A"])
        self.assertEqual(issue["required_action"], "Fix A")
        self.assertEqual(issue["diagnostic_answer"], "Краткое основание решения.")
        self.assertEqual(issue["correction_activity"][0]["tool_name"], "read_file")
        self.assertEqual(issue["result"], "RESOLVED")
        self.assertEqual(thread["final_audit"], "PASS")
        correction_messages = client.bodies[1]["messages"]
        self.assertFalse(any(server.AUDIT_DIAGNOSTIC_QUESTION in str(item.get("content")) for item in correction_messages))
        self.assertFalse(any("Краткое основание решения." in str(item.get("content")) for item in correction_messages))

    async def test_diagnostic_failure_does_not_block_correction(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate B")])
        result, verifier, _ = await self.run_case(
            [fail_result("A"), verifier_result("PASS")], fake_client=client,
            extra_patches=(patch.object(
                server, "_request_audit_diagnostic",
                AsyncMock(side_effect=TimeoutError("diagnostic timeout")),
            ),),
        )
        self.assertEqual(result, "Candidate B")
        self.assertEqual(verifier.await_count, 2)
        run_id = next(item["run_id"] for item in self.events if item["event"] == "run_started")
        thread = load_audit_thread(self.workspace, "ws_test", None, run_id)
        self.assertIn("TimeoutError", thread["issues"][0]["diagnostic_error"])
        self.assertEqual(thread["issues"][0]["result"], "RESOLVED")
        self.assertIn("final_audit_feedback_delivered", [item["event"] for item in self.events])

    async def test_terminal_audit_issue_has_no_extra_diagnostic(self) -> None:
        client = FakeClient([FakeResponse("Same"), FakeResponse("Same")])
        with self.assertRaises(server.FinalAuditSemanticError):
            await self.run_case([fail_result("A"), fail_result("B")], fake_client=client)
        run_id = next(item["run_id"] for item in self.events if item["event"] == "run_started")
        thread = load_audit_thread(self.workspace, "ws_test", None, run_id)
        self.assertEqual([issue["result"] for issue in thread["issues"]], ["UNRESOLVED", "UNRESOLVED"])
        self.assertIsNone(thread["issues"][1]["diagnostic_question"])
        self.assertEqual(thread["final_audit"], "FAIL")

    async def test_two_corrections_then_pass(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Candidate B"),
            FakeResponse("Candidate C"),
        ])
        result, verifier, _client = await self.run_case(
            [fail_result("A"), fail_result("B"), verifier_result("PASS")],
            fake_client=client,
        )
        self.assertEqual(result, "Candidate C")
        self.assertEqual(verifier.await_count, 3)
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_feedback_created"), 2)
        self.assertEqual(names.count("final_audit_feedback_delivered"), 2)
        self.assertEqual(names.count("final_audit_correction_started"), 2)
        self.assertEqual(names.count("final_audit_retry_evaluated"), 2)
        self.assertNotIn("run_failed", names)
        self.assertEqual(self.events[-1]["event"], "run_finished")
        self.assertEqual(len({item["run_id"] for item in self.events}), 1)
        for audit_call in verifier.await_args_list:
            self.assertEqual(audit_call.kwargs["raw_task"], "ORIGINAL RAW TASK")
            self.assertEqual(
                audit_call.kwargs["task_id"],
                verifier.await_args_list[0].kwargs["task_id"],
            )
            self.assertNotIn("messages", audit_call.kwargs)

        retry_events = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ]
        self.assertEqual(
            [item["correction_count"] for item in retry_events],
            [0, 1],
        )
        delivered = [
            item
            for item in self.events
            if item["event"] == "final_audit_feedback_delivered"
        ]
        self.assertEqual(
            [item["correction_count"] for item in delivered],
            [1, 2],
        )
        self.assertEqual(
            [item["remaining_corrections"] for item in delivered],
            [1, 0],
        )
        self.assertEqual(
            self.events[-2]["audit_attempt"],
            3,
        )

        third_messages = client.bodies[2]["messages"]
        self.assertEqual(third_messages[-2]["content"], "Candidate B")
        second_feedback = third_messages[-1]["content"]
        facts = json.loads(
            second_feedback.split(
                "SERVER FACTS — NOT TEMPLATE CONTROLLED:\n", 1
            )[1]
        )
        self.assertEqual(facts["correction_cycle"], 2)
        self.assertEqual(facts["correction_count"], 2)
        self.assertEqual(facts["correction_limit"], 2)
        self.assertEqual(facts["remaining_corrections"], 0)

    async def test_candidate_only_progress_allows_second_handoff(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Candidate B"),
            FakeResponse("Candidate C"),
        ])
        await self.run_case(
            [fail_result("A"), fail_result("B"), verifier_result("PASS")],
            fake_client=client,
        )
        retry_events = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ]
        self.assertEqual(retry_events[1]["progress_class"], "MATERIAL_PROGRESS")
        self.assertTrue(retry_events[1]["candidate_changed"])
        self.assertFalse(retry_events[1]["run_owned_state_changed"])
        self.assertEqual(
            [
                item["event"]
                for item in self.events
                if item["event"] == "final_audit_feedback_delivered"
            ].count("final_audit_feedback_delivered"),
            2,
        )

    async def test_run_owned_mutation_is_material_progress(self) -> None:
        self.permissions.update(allow_write=True, allow_verify=True, tool_limit=6)
        client = FakeClient([
            FakeResponse("Same Candidate"),
            FakeResponse(
                "",
                finish_reason="function_call",
                function_call={
                    "name": "write_file",
                    "arguments": {
                        "path": "result.txt",
                        "content": "version one",
                    },
                },
            ),
            FakeResponse("Same Candidate"),
            FakeResponse("Final Candidate"),
        ])
        result, verifier, _client = await self.run_case(
            [fail_result("A"), fail_result("B"), verifier_result("PASS")],
            fake_client=client,
            extra_patches=(
                patch.object(
                    server,
                    "_verification_missing_requirements",
                    return_value=[],
                ),
            ),
        )
        self.assertEqual(result, "Final Candidate")
        self.assertEqual(verifier.await_count, 3)
        retry_events = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ]
        self.assertFalse(retry_events[1]["candidate_changed"])
        self.assertTrue(retry_events[1]["run_owned_state_changed"])
        self.assertEqual(retry_events[1]["progress_class"], "MATERIAL_PROGRESS")

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
        self.assertEqual(facts["correction_count"], 1)
        self.assertEqual(facts["correction_limit"], 2)
        self.assertEqual(facts["remaining_corrections"], 1)

    async def test_one_correction_allows_multiple_api_and_tool_calls(self) -> None:
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
        self.assertEqual(client.post_count, 4)
        self.assertEqual(verifier.await_count, 2)
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_feedback_created"), 1)
        self.assertEqual(names.count("tool_finished"), 2)

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
        retry_events = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ]
        self.assertEqual(len(retry_events), 1)
        self.assertEqual(retry_events[0]["correction_count"], 0)

    async def test_no_progress_is_terminal_and_exposes_details(self) -> None:
        client = FakeClient([FakeResponse("Candidate A"), FakeResponse("Candidate A")])
        with self.assertRaises(server.FinalAuditSemanticError) as raised:
            await self.run_case(
                [fail_result("A"), fail_result("B")],
                fake_client=client,
            )
        self.assertIn("NO_PROGRESS", str(raised.exception))
        self.assertIn("Reason B", str(raised.exception))
        self.assertIn("Violation B", str(raised.exception))
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_failed"), 2)
        self.assertEqual(names.count("final_audit_retry_evaluated"), 2)
        self.assertEqual(names.count("final_audit_feedback_created"), 1)
        self.assertEqual(names.count("final_audit_feedback_delivered"), 1)
        self.assertEqual(names.count("final_audit_correction_started"), 1)
        self.assertEqual(names.count("run_failed"), 1)
        self.assertNotIn("final_audit_passed", names)
        self.assertFalse(
            any(item["event"] == "run_finished" for item in self.events)
        )
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_retry_no_progress")
        self.assertEqual(failure["audit_attempt"], 2)
        self.assertEqual(failure["semantic_fail_count"], 2)
        self.assertEqual(failure["correction_count"], 1)
        second_failed = [
            item for item in self.events if item["event"] == "final_audit_failed"
        ][-1]
        self.assertNotIn("correction_cycle", second_failed)
        self.assertEqual(self.last_verifier.await_count, 2)
        self.assertEqual(client.post_count, 2)

    async def test_external_git_change_is_not_material_progress(self) -> None:
        client = FakeClient([
            FakeResponse("Same Candidate"),
            FakeResponse("Same Candidate"),
        ])
        git_before = {
            "ok": True,
            "exit_code": 0,
            "stdout": " M external-before.txt",
            "stderr": "",
            "truncated": False,
        }
        git_after = {
            **git_before,
            "stdout": " M external-after.txt",
        }
        with self.assertRaises(server.FinalAuditSemanticError):
            await self.run_case(
                [fail_result("A"), fail_result("B")],
                fake_client=client,
                extra_patches=(
                    patch.object(
                        server,
                        "_agent_git_status",
                        side_effect=[dict(git_before), dict(git_after)],
                    ),
                    patch.object(
                        server,
                        "_agent_git_diff",
                        side_effect=[dict(git_before), dict(git_after)],
                    ),
                ),
            )
        retry = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ][-1]
        self.assertEqual(retry["progress_class"], "NO_PROGRESS")
        self.assertFalse(retry["candidate_changed"])
        self.assertFalse(retry["run_owned_state_changed"])
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_retry_no_progress")

    async def test_deterministic_ping_pong_is_terminal(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Candidate B"),
            FakeResponse("Candidate C"),
        ])
        with self.assertRaisesRegex(
            server.FinalAuditSemanticError, "PING_PONG"
        ):
            await self.run_case(
                [fail_result("A"), fail_result("B"), fail_result("A")],
                fake_client=client,
            )
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_feedback_delivered"), 2)
        self.assertEqual(names.count("final_audit_retry_evaluated"), 3)
        self.assertEqual(names.count("run_failed"), 1)
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_retry_ping_pong")
        self.assertEqual(failure["audit_attempt"], 3)
        self.assertEqual(failure["semantic_fail_count"], 3)
        self.assertEqual(failure["correction_count"], 2)
        third_failed = [
            item for item in self.events if item["event"] == "final_audit_failed"
        ][-1]
        self.assertNotIn("correction_cycle", third_failed)

    async def test_repeated_core_failure_threshold_is_terminal(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Candidate B"),
            FakeResponse("Candidate C"),
        ])
        repeated = [
            verifier_result(
                "FAIL",
                reason=f"wording {index}",
                violations=("Same core violation",),
                required_action=f"Action {index}",
            )
            for index in range(3)
        ]
        with self.assertRaisesRegex(
            server.FinalAuditSemanticError, "REPEATED_FAILURE"
        ):
            await self.run_case(repeated, fake_client=client)
        retry = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ][-1]
        self.assertEqual(retry["same_core_failure_streak"], 3)
        self.assertFalse(retry["ping_pong_detected"])
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(
            failure["reason"], "final_audit_retry_repeated_failure"
        )
        self.assertEqual(
            [item["event"] for item in self.events].count(
                "final_audit_feedback_delivered"
            ),
            2,
        )

    async def test_pure_correction_budget_exhaustion_is_terminal(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Candidate B"),
            FakeResponse("Candidate C"),
        ])
        with self.assertRaisesRegex(
            server.FinalAuditSemanticError, "CORRECTION_EXHAUSTED"
        ):
            await self.run_case(
                [fail_result("A"), fail_result("B"), fail_result("C")],
                fake_client=client,
            )
        retry = [
            item
            for item in self.events
            if item["event"] == "final_audit_retry_evaluated"
        ][-1]
        self.assertEqual(retry["progress_class"], "MATERIAL_PROGRESS")
        self.assertFalse(retry["ping_pong_detected"])
        self.assertEqual(retry["same_core_failure_streak"], 1)
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_correction_exhausted")
        self.assertEqual(failure["audit_attempt"], 3)
        self.assertEqual(failure["semantic_fail_count"], 3)
        self.assertEqual(failure["correction_count"], 2)
        self.assertEqual(
            [item["event"] for item in self.events].count(
                "final_audit_feedback_delivered"
            ),
            2,
        )

    async def test_runtime_error_is_fail_closed_and_distinct(self) -> None:
        error = verifier_runtime.VerifierRuntimeError("transport unavailable")
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_case(error)
        names = [item["event"] for item in self.events]
        self.assertIn("final_audit_error", names)
        self.assertNotIn("final_audit_failed", names)
        failure = next(item for item in self.events if item["event"] == "run_failed")
        self.assertEqual(failure["reason"], "final_audit_runtime_error")
        self.assertEqual(failure["final_audit_attempt_count"], 1)

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

    async def test_protocol_error_after_two_corrections_is_terminal(self) -> None:
        client = FakeClient([
            FakeResponse("Candidate A"),
            FakeResponse("Candidate B"),
            FakeResponse("Candidate C"),
        ])
        with self.assertRaisesRegex(RuntimeError, "VerifierProtocolError"):
            await self.run_case(
                [
                    fail_result("A"),
                    fail_result("B"),
                    verifier_runtime.VerifierProtocolError("malformed response"),
                ],
                fake_client=client,
            )
        names = [item["event"] for item in self.events]
        self.assertEqual(names.count("final_audit_feedback_delivered"), 2)
        self.assertEqual(names.count("final_audit_retry_evaluated"), 2)
        self.assertEqual(names.count("final_audit_error"), 1)
        self.assertEqual(names.count("run_failed"), 1)
        self.assertNotIn("run_finished", names)
        error = next(item for item in self.events if item["event"] == "final_audit_error")
        self.assertEqual(error["final_audit_attempt_count"], 3)

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

    def test_v5_handoffs_do_not_persist_chat_messages(self) -> None:
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

    async def test_final_fact_conflict_blocks_fabricated_zero_tool_pass(self) -> None:
        client = FakeClient([FakeResponse(
            "Файл изменён через replace_text; read_file выполнен; readback выполнен."
        )])
        with self.assertRaisesRegex(RuntimeError, "FINAL AUDIT ERROR"):
            await self.run_case(verifier_result("PASS"), fake_client=client,
                                task="Explain the architecture")
        verifier = self.last_verifier
        verifier.assert_awaited_once()
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(context["run_facts"]["tool_call_count"], 0)
        self.assertEqual(context["run_facts"]["write_revision"], 0)
        self.assertEqual(context["mutation_facts"],
                         {"changed_files": [], "new_files": [], "deleted_files": []})
        self.assertEqual(context["run_owned_filesystem_evidence"], [])
        self.assertEqual(context["observed_executor_tools"]["names"], [])
        self.assertIn("candidate_claims_unobserved_physical_mutation",
                      context["evidence_completeness"]["candidate_fact_conflicts"])
        self.assertIn("candidate_claims_unobserved_tools:read_file,replace_text",
                      context["evidence_completeness"]["candidate_fact_conflicts"])
        self.assertEqual(self.events[-1]["reason"], "final_audit_evidence_incomplete")

    async def test_final_zero_tool_truthful_answer_can_pass(self) -> None:
        client = FakeClient([FakeResponse("Архитектура использует независимый verifier.")])
        result, verifier, _ = await self.run_case(verifier_result("PASS"),
            fake_client=client, task="Объясни архитектуру")
        self.assertIn("verifier", result)
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(context["evidence_completeness"]["candidate_fact_conflicts"], [])

    def test_final_fact_conflict_detector_does_not_treat_negation_as_a_write(self) -> None:
        facts = dict(tool_call_count=0, write_revision=0, run_owned_state={},
                     mutation_facts={"changed_files": [], "new_files": [], "deleted_files": []},
                     observed_tool_names=set())
        for candidate in ("Файл не изменён.", "Файл уже изменён до этого RUN.",
                          "Completed explanation. replace_text is an available tool."):
            with self.subTest(candidate=candidate):
                self.assertEqual(server._candidate_fact_conflicts(candidate, **facts), [])

    async def test_final_actual_mutation_report_has_no_fact_conflict(self) -> None:
        self.permissions.update(allow_write=True, allow_verify=True)
        client = FakeClient([
            FakeResponse("", finish_reason="function_call", function_call={
                "name": "write_file", "arguments": {"path": "result.txt", "content": "done"},
            }),
            FakeResponse("Файл result.txt изменён; write_file выполнен."),
        ])
        result, verifier, _ = await self.run_case(verifier_result("PASS"),
            fake_client=client, task="Update file result.txt")
        self.assertIn("изменён", result)
        context = json.loads(verifier.await_args.kwargs["verification_context"])
        self.assertEqual(context["observed_executor_tools"]["names"], ["write_file"])
        self.assertEqual(context["evidence_completeness"]["candidate_fact_conflicts"], [])

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
        new_file.write_bytes(b"VALUE = 42\n")
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
        self.assertEqual(failure["final_audit_attempt_count"], 0)

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
        self.assertIn("READ is disabled", payload["fresh_git_status"]["reason"])
        self.assertTrue(metadata["complete"])
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
