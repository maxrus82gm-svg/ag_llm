from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import compressor_runtime
import compressor_settings
import ui_state
import agent_global_context
from context_storage import ensure_workspace_storage


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
                    )
            self.assertEqual(request.await_count, 2)


if __name__ == "__main__":
    unittest.main()
