from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import compressor_runtime
import compressor_settings
import ui_state
import agent_global_context
from context_storage import (
    append_raw_message,
    create_chat,
    create_message_context_variant,
    ensure_workspace_storage,
    get_message_context_state,
    restore_message_raw,
)


class CompressorPureTests(unittest.TestCase):
    def test_role_context_storage_is_independent_from_main_chat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agents_root = Path(temp_dir) / "agents"
            with patch.object(
                agent_global_context,
                "AGENTS_ROOT",
                agents_root,
            ):
                agent_global_context.save_agent_global_context(
                    "MAIN CHAT ROLE",
                    "ultra",
                )
                agent_global_context.save_agent_global_context(
                    "COMPRESSOR ROLE",
                    "compressor",
                )
                self.assertEqual(
                    agent_global_context.load_agent_global_context("ultra"),
                    "MAIN CHAT ROLE",
                )
                self.assertEqual(
                    agent_global_context.load_agent_global_context(
                        "compressor"
                    ),
                    "COMPRESSOR ROLE",
                )
                self.assertNotEqual(
                    agent_global_context.get_agent_global_context_path("ultra"),
                    agent_global_context.get_agent_global_context_path(
                        "compressor"
                    ),
                )

    def test_assignments_and_ui_state_persist_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"
            state = ui_state.default_ui_state()
            state.update(
                {
                    "main_chat_model_id": "gigachat_ultra",
                    "compressor_model_id": "gigachat_3_pro",
                    "compressor_reduction_percent": 50,
                    "compressor_final_check_enabled": True,
                }
            )
            with patch.object(ui_state, "STATE_PATH", state_path):
                ui_state.save_ui_state(state)
                loaded = ui_state.load_ui_state()

            self.assertEqual(loaded["main_chat_model_id"], "gigachat_ultra")
            self.assertEqual(loaded["compressor_model_id"], "gigachat_3_pro")
            self.assertEqual(loaded["compressor_reduction_percent"], 50)
            self.assertIs(loaded["compressor_final_check_enabled"], True)

    def test_template_persistence_and_all_placeholder_occurrences(self) -> None:
        rendered = compressor_runtime.render_message_compression_template(
            "A={{REDUCTION_PERCENT}}\n"
            "B={{REMAINING_PERCENT}}\n"
            "C={{REDUCTION_PERCENT}}",
            50,
        )
        self.assertEqual(rendered, "A=50\nB=50\nC=50")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "message_compression_template.md"
            with patch.object(
                compressor_settings,
                "MESSAGE_COMPRESSION_TEMPLATE_PATH",
                path,
            ):
                compressor_settings.save_message_compression_template(rendered)
                self.assertEqual(
                    compressor_settings.load_message_compression_template(),
                    rendered,
                )

            final_path = Path(temp_dir) / "final_check_template.md"
            with patch.object(
                compressor_settings,
                "FINAL_CHECK_TEMPLATE_PATH",
                final_path,
            ):
                compressor_settings.save_final_check_template(
                    "Check {{REDUCTION_PERCENT}}%."
                )
                self.assertEqual(
                    compressor_settings.load_final_check_template(),
                    "Check {{REDUCTION_PERCENT}}%.",
                )

    def test_placeholders_render_in_all_editable_prompt_blocks(self) -> None:
        blocks = compressor_runtime.build_compressor_prompt_blocks(
            source_text="SOURCE {{REDUCTION_PERCENT}}",
            role_context=(
                "Role reduction={{REDUCTION_PERCENT}} "
                "remaining={{REMAINING_PERCENT}}"
            ),
            project_context="PROJECT {{REMAINING_PERCENT}}",
            message_template="Message {{REDUCTION_PERCENT}}",
            final_check_template="Final {{REMAINING_PERCENT}}",
            reduction_percent=40,
            final_check_enabled=True,
        )
        by_id = {block["id"]: block["content"] for block in blocks}
        self.assertEqual(by_id["role_context"], "Role reduction=40 remaining=60")
        self.assertEqual(by_id["message_template"], "Message 40")
        self.assertEqual(by_id["final_check"], "Final 60")
        self.assertIn("PROJECT {{REMAINING_PERCENT}}", by_id["project_context"])
        self.assertEqual(
            by_id["source_text"],
            "SOURCE {{REDUCTION_PERCENT}}",
        )

    def test_default_target_mentions_follow_final_check_switch(self) -> None:
        common = {
            "source_text": "SOURCE",
            "role_context": "COMPRESSOR ROLE",
            "project_context": "REFERENCE",
            "message_template": (
                compressor_settings.DEFAULT_MESSAGE_COMPRESSION_TEMPLATE
            ),
            "final_check_template": (
                compressor_settings.DEFAULT_FINAL_CHECK_TEMPLATE
            ),
            "reduction_percent": 50,
        }
        prompt_without_check = compressor_runtime.render_compressor_prompt(
            compressor_runtime.build_compressor_prompt_blocks(
                **common,
                final_check_enabled=False,
            )
        )
        self.assertEqual(prompt_without_check.count("50%"), 1)

        prompt_with_check = compressor_runtime.render_compressor_prompt(
            compressor_runtime.build_compressor_prompt_blocks(
                **common,
                final_check_enabled=True,
            )
        )
        self.assertEqual(prompt_with_check.count("50%"), 2)

    def test_server_fallback_and_conscious_multiple_mentions(self) -> None:
        fallback_prompt = compressor_runtime.render_compressor_prompt(
            compressor_runtime.build_compressor_prompt_blocks(
                source_text="SOURCE",
                role_context="ROLE WITHOUT TARGET",
                project_context="REFERENCE",
                message_template="Compress while preserving meaning.",
                final_check_template=(
                    compressor_settings.DEFAULT_FINAL_CHECK_TEMPLATE
                ),
                reduction_percent=50,
                final_check_enabled=False,
            )
        )
        self.assertEqual(fallback_prompt.count("50%"), 1)
        self.assertIn("Requested approximate reduction: 50%", fallback_prompt)

        experimental_prompt = compressor_runtime.render_compressor_prompt(
            compressor_runtime.build_compressor_prompt_blocks(
                source_text="SOURCE",
                role_context=(
                    "Role {{REDUCTION_PERCENT}}% and "
                    "{{REDUCTION_PERCENT}}%."
                ),
                project_context="REFERENCE",
                message_template="Message {{REDUCTION_PERCENT}}%.",
                final_check_template="Unused.",
                reduction_percent=40,
                final_check_enabled=False,
            )
        )
        self.assertEqual(experimental_prompt.count("40%"), 3)
        self.assertNotIn(
            "Requested approximate reduction: 40%",
            experimental_prompt,
        )

    def test_prompt_blocks_and_request_are_isolated(self) -> None:
        blocks = compressor_runtime.build_compressor_prompt_blocks(
            source_text="SOURCE_ONLY",
            role_context="COMPRESSOR_ROLE_ONLY",
            project_context="PROJECT_REFERENCE_ONLY",
            message_template="Reduce {{REDUCTION_PERCENT}} / keep {{REMAINING_PERCENT}}",
            reduction_percent=50,
            final_check_enabled=True,
        )
        self.assertEqual(
            [block["id"] for block in blocks],
            list(compressor_runtime.COMPRESSOR_PROMPT_BLOCK_ORDER),
        )
        prompt = compressor_runtime.render_compressor_prompt(blocks)
        self.assertIn("SOURCE TEXT is the source of truth", prompt)
        self.assertIn("PROJECT_REFERENCE_ONLY", prompt)
        self.assertNotIn("MAIN_CHAT", prompt)
        body = compressor_runtime.build_compressor_request_body(
            "gigachat_3_pro",
            prompt,
        )
        self.assertEqual(body["model"], "GigaChat-3-Pro")
        self.assertEqual(
            set(body),
            {"model", "messages", "temperature", "max_tokens", "stream"},
        )
        self.assertNotIn("tools", body)
        self.assertNotIn("functions", body)
        self.assertNotIn("function_call", body)
        self.assertNotIn("permissions", body)
        self.assertEqual(len(body["messages"]), 1)

        without_final_check = compressor_runtime.build_compressor_prompt_blocks(
            source_text="SOURCE_ONLY",
            role_context="COMPRESSOR_ROLE_ONLY",
            project_context="PROJECT_REFERENCE_ONLY",
            message_template="Reduce.",
            reduction_percent=50,
            final_check_enabled=False,
        )
        self.assertNotIn(
            "final_check",
            [block["id"] for block in without_final_check],
        )

    def test_soft_guard_accepts_broad_reductions_and_rejects_noops(self) -> None:
        source = "x" * 100
        for output_length in (30, 50, 65):
            self.assertEqual(
                compressor_runtime.evaluate_compression_guard(
                    source,
                    "y" * output_length,
                ),
                compressor_runtime.GUARD_ACCEPT,
            )
        self.assertEqual(
            compressor_runtime.evaluate_compression_guard(source, "y" * 98),
            compressor_runtime.GUARD_REJECT_INSUFFICIENT_REDUCTION,
        )
        self.assertEqual(
            compressor_runtime.evaluate_compression_guard(source, ""),
            compressor_runtime.GUARD_REJECT_EMPTY,
        )
        self.assertEqual(
            compressor_runtime.evaluate_compression_guard(
                "One   TWO\nthree",
                " one two THREE ",
            ),
            compressor_runtime.GUARD_REJECT_UNCHANGED,
        )
        self.assertEqual(
            compressor_runtime.evaluate_compression_guard(source, "y" * 101),
            compressor_runtime.GUARD_REJECT_NOT_SHORTER,
        )


class CompressorRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_message_compressor_reloads_raw_after_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            ensure_workspace_storage(workspace)
            chat = create_chat(workspace)
            raw_text = "R" * 1000
            message = append_raw_message(
                workspace, chat["chat_id"], "user", raw_text
            )
            create_message_context_variant(
                workspace,
                chat["chat_id"],
                message["message_id"],
                "S" * 300,
                source="llm_compression",
            )
            restore_message_raw(
                workspace, chat["chat_id"], message["message_id"]
            )
            expected = compressor_runtime.CompressorRunResult(
                text="S" * 250,
                run_id="cmp_test",
                model_id="gigachat_3_pro",
                model_display_name="GigaChat 3 Pro",
                provider="gigachat",
                provider_model_id="GigaChat-3-Pro",
                target_reduction_percent=50,
                actual_reduction_percent=75.0,
                source_chars=1000,
                output_chars=250,
                attempts=1,
                final_check_enabled=True,
            )
            detailed = AsyncMock(return_value=expected)
            with patch.object(
                compressor_runtime,
                "run_compressor_task_detailed",
                detailed,
            ):
                actual = await compressor_runtime.run_message_compressor_task_detailed(
                    workspace,
                    chat["chat_id"],
                    message["message_id"],
                    compressor_model_id="gigachat_3_pro",
                )
            self.assertIs(actual, expected)
            self.assertEqual(detailed.await_args.args[0], raw_text)
            self.assertNotEqual(detailed.await_args.args[0], "S" * 300)
            self.assertEqual(
                get_message_context_state(
                    workspace, chat["chat_id"], message["message_id"]
                )["active_representation"],
                "raw",
            )

    async def test_detailed_result_preserves_compatibility_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            ensure_workspace_storage(workspace)
            with (
                patch.object(
                    compressor_runtime,
                    "_request_gigachat",
                    AsyncMock(return_value="z" * 50),
                ),
                patch.object(
                    compressor_runtime,
                    "COMPRESSOR_LOG_ROOT",
                    Path(temp_dir) / "logs",
                ),
            ):
                result = await compressor_runtime.run_compressor_task_detailed(
                    "x" * 100,
                    workspace,
                    role_context="COMPRESSOR ROLE",
                    message_template="Reduce {{REDUCTION_PERCENT}}%.",
                    project_context="REFERENCE",
                    final_check_template="Check meaning.",
                )
            self.assertEqual(result.text, "z" * 50)
            self.assertEqual(result.source_chars, 100)
            self.assertEqual(result.output_chars, 50)
            self.assertEqual(result.actual_reduction_percent, 50.0)
            self.assertEqual(result.model_id, "gigachat_3_pro")
            self.assertRegex(result.run_id, r"^cmp_")

    async def test_exactly_one_corrective_retry_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            ensure_workspace_storage(workspace)
            events = []
            request = AsyncMock(side_effect=["y" * 98, "z" * 50])
            with (
                patch.object(compressor_runtime, "_request_gigachat", request),
                patch.object(
                    compressor_runtime,
                    "COMPRESSOR_LOG_ROOT",
                    Path(temp_dir) / "logs",
                ),
            ):
                result = await compressor_runtime.run_compressor_task(
                    "x" * 100,
                    workspace,
                    role_context="COMPRESSOR ROLE",
                    message_template="Reduce {{REDUCTION_PERCENT}}%.",
                    project_context="REFERENCE",
                    final_check_template="Check meaning.",
                    on_event=events.append,
                )

            self.assertEqual(result, "z" * 50)
            self.assertEqual(request.await_count, 2)
            attempts = [
                event
                for event in events
                if event["event"] == "compressor_attempt_finished"
            ]
            self.assertEqual(len(attempts), 2)
            self.assertEqual(
                attempts[0]["guard_status"],
                compressor_runtime.GUARD_REJECT_INSUFFICIENT_REDUCTION,
            )
            self.assertEqual(
                attempts[1]["guard_status"],
                compressor_runtime.GUARD_ACCEPT,
            )
            self.assertRegex(events[0]["run_id"], r"^cmp_\d{8}_\d{6}_[0-9a-f]{6}$")

    async def test_guard_failure_stops_after_second_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            ensure_workspace_storage(workspace)
            request = AsyncMock(side_effect=["y" * 98, "z" * 98])
            with (
                patch.object(compressor_runtime, "_request_gigachat", request),
                patch.object(
                    compressor_runtime,
                    "COMPRESSOR_LOG_ROOT",
                    Path(temp_dir) / "logs",
                ),
            ):
                with self.assertRaises(compressor_runtime.CompressorGuardError):
                    await compressor_runtime.run_compressor_task(
                        "x" * 100,
                        workspace,
                        role_context="COMPRESSOR ROLE",
                        message_template="Reduce {{REDUCTION_PERCENT}}%.",
                        project_context="REFERENCE",
                        final_check_template="Check meaning.",
                    )
            self.assertEqual(request.await_count, 2)


if __name__ == "__main__":
    unittest.main()
