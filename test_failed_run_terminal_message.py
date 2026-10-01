from __future__ import annotations

import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ultra_ui
from context_storage import (
    append_raw_message,
    create_chat,
    ensure_workspace_storage,
    load_chat_messages,
    new_task_block_id,
)


class _WorkerHarness:
    def __init__(self) -> None:
        self.events = queue.Queue()
        self.trace_events = queue.Queue()


class FailedRunTerminalMessageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        self.workspace.mkdir()
        ensure_workspace_storage(self.workspace)
        self.chat = create_chat(self.workspace)
        self.task_block_id = new_task_block_id()
        append_raw_message(
            self.workspace,
            self.chat["chat_id"],
            "user",
            "FAIL ME",
            task_block_id=self.task_block_id,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_worker(self, fake_run) -> tuple[str, dict]:
        harness = _WorkerHarness()
        with patch.object(ultra_ui, "run_agent_task", fake_run):
            ultra_ui.UltraApp._worker(
                harness,
                "FAIL ME",
                str(self.workspace),
                {},
                self.chat["chat_id"],
                "gigachat_ultra",
                "gigachat_ultra",
                "gigachat_3_pro",
                True,
                True,
                self.task_block_id,
            )
        return harness.events.get_nowait()

    def test_exception_after_run_started_persists_terminal_assistant_with_provenance(self) -> None:
        async def failing_run(*_args, on_event=None, **_kwargs):
            on_event(
                {
                    "event": "run_started",
                    "run_id": "run_terminal_test",
                    "model_id": "gigachat_ultra",
                    "model_display_name": "GigaChat 3 Ultra",
                    "provider": "gigachat",
                    "provider_model_id": "GigaChat-3-Ultra",
                }
            )
            raise RuntimeError("boom")

        event_type, payload = self.run_worker(failing_run)
        messages = load_chat_messages(self.workspace, self.chat["chat_id"])

        self.assertEqual(event_type, "error")
        self.assertTrue(payload["terminal_persisted"])
        self.assertIsNone(payload["terminal_storage_error"])
        self.assertIsNone(payload["provenance_warning"])
        self.assertEqual(len(messages), 2)
        assistant = messages[-1]
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["task_block_id"], self.task_block_id)
        self.assertEqual(
            assistant["original_text"],
            "RUN STATUS: FAILED\nRuntimeError: boom",
        )
        self.assertEqual(assistant["producer"]["run_id"], "run_terminal_test")
        self.assertEqual(assistant["producer"]["role_id"], "main_chat")

    def test_exception_before_run_started_still_persists_terminal_assistant(self) -> None:
        async def failing_run(*_args, **_kwargs):
            raise ValueError("early failure")

        event_type, payload = self.run_worker(failing_run)
        messages = load_chat_messages(self.workspace, self.chat["chat_id"])

        self.assertEqual(event_type, "error")
        self.assertTrue(payload["terminal_persisted"])
        self.assertIn("run_started", payload["provenance_warning"])
        assistant = messages[-1]
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["task_block_id"], self.task_block_id)
        self.assertNotIn("producer", assistant)
        self.assertEqual(
            assistant["original_text"],
            "RUN STATUS: FAILED\nValueError: early failure",
        )

    def test_terminal_storage_failure_remains_visible_in_error_payload(self) -> None:
        async def failing_run(*_args, **_kwargs):
            raise RuntimeError("executor failed")

        with patch.object(
            ultra_ui,
            "append_raw_message",
            side_effect=OSError("storage unavailable"),
        ):
            event_type, payload = self.run_worker(failing_run)

        self.assertEqual(event_type, "error")
        self.assertFalse(payload["terminal_persisted"])
        self.assertIn("storage unavailable", payload["terminal_storage_error"])


if __name__ == "__main__":
    unittest.main()
