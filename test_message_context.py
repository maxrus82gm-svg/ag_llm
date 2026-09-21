from __future__ import annotations

import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import server
from verifier_runtime import VerifierResult
from ultra_ui import get_message_display_text

from context_storage import (
    MESSAGE_CONTEXT_SCHEMA_VERSION,
    activate_message_context_variant,
    append_raw_message,
    create_chat,
    create_message_context_variant,
    ensure_workspace_storage,
    get_message_context_state,
    get_message_working_representation,
    load_chat_working_messages,
    load_context_variant,
    load_raw_message,
    restore_message_raw,
)


class MessageContextStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        self.workspace.mkdir()
        self.workspace_info = ensure_workspace_storage(self.workspace)
        self.chat = create_chat(self.workspace)
        self.chat_id = self.chat["chat_id"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def add(self, role: str, text: str) -> dict:
        return append_raw_message(self.workspace, self.chat_id, role, text)

    def raw_path(self, message_id: str) -> Path:
        return (
            self.workspace
            / ".ultra"
            / "chats"
            / self.chat_id
            / "messages"
            / f"{message_id}.json"
        )

    def state_path(self, message_id: str) -> Path:
        return (
            self.workspace
            / ".ultra"
            / "chats"
            / self.chat_id
            / "message_context"
            / message_id
            / "state.json"
        )

    def test_legacy_message_is_full_without_lazy_read_write(self) -> None:
        message = self.add("user", "AAA RAW")
        state = get_message_context_state(
            self.workspace, self.chat_id, message["message_id"]
        )
        working = get_message_working_representation(
            self.workspace, self.chat_id, message["message_id"]
        )
        self.assertEqual(state["active_representation"], "raw")
        self.assertIsNone(state["active_variant_id"])
        self.assertEqual(working["text"], "AAA RAW")
        self.assertFalse(self.state_path(message["message_id"]).exists())

    def test_raw_is_byte_immutable_through_create_edit_restore(self) -> None:
        message = self.add("assistant", "ORIGINAL LONG TEXT")
        message_id = message["message_id"]
        before = self.raw_path(message_id).read_bytes()
        first = create_message_context_variant(
            self.workspace,
            self.chat_id,
            message_id,
            "SHORT",
            source="llm_compression",
            compression={"run_id": "cmp_test"},
        )
        self.assertEqual(self.raw_path(message_id).read_bytes(), before)
        second = create_message_context_variant(
            self.workspace,
            self.chat_id,
            message_id,
            "BETTER SHORT",
            source="manual_edit",
            parent_variant_id=first["context_variant_id"],
            manually_edited=True,
        )
        restore_message_raw(self.workspace, self.chat_id, message_id)
        self.assertEqual(self.raw_path(message_id).read_bytes(), before)
        self.assertEqual(load_raw_message(self.workspace, self.chat_id, message_id)["original_text"], "ORIGINAL LONG TEXT")
        self.assertEqual(load_context_variant(self.workspace, self.chat_id, message_id, first["context_variant_id"])["text"], "SHORT")
        self.assertEqual(load_context_variant(self.workspace, self.chat_id, message_id, second["context_variant_id"])["text"], "BETTER SHORT")

    def test_visible_chat_body_follows_production_working_representation(self) -> None:
        message = self.add("user", "ORIGINAL LONG TEXT")
        message_id = message["message_id"]

        full = get_message_working_representation(
            self.workspace, self.chat_id, message_id
        )
        self.assertEqual(get_message_display_text(message, full), "ORIGINAL LONG TEXT")

        create_message_context_variant(
            self.workspace,
            self.chat_id,
            message_id,
            "ACTIVE SUMMARY",
            source="llm_compression",
        )
        compressed_after_reload = get_message_working_representation(
            self.workspace, self.chat_id, message_id
        )
        self.assertEqual(
            get_message_display_text(message, compressed_after_reload),
            "ACTIVE SUMMARY",
        )

        restore_message_raw(self.workspace, self.chat_id, message_id)
        restored = get_message_working_representation(
            self.workspace, self.chat_id, message_id
        )
        self.assertEqual(
            get_message_display_text(message, restored),
            "ORIGINAL LONG TEXT",
        )

    def test_accept_restart_restore_and_variant_survival(self) -> None:
        message = self.add("user", "X" * 100)
        message_id = message["message_id"]
        variant = create_message_context_variant(
            self.workspace,
            self.chat_id,
            message_id,
            "X" * 40,
            source="llm_compression",
        )
        reloaded = get_message_context_state(self.workspace, self.chat_id, message_id)
        self.assertEqual(reloaded["active_representation"], "summary")
        self.assertEqual(reloaded["active_variant_id"], variant["context_variant_id"])
        self.assertEqual(get_message_working_representation(self.workspace, self.chat_id, message_id)["text"], "X" * 40)
        restore_message_raw(self.workspace, self.chat_id, message_id)
        self.assertEqual(get_message_context_state(self.workspace, self.chat_id, message_id)["active_representation"], "raw")
        self.assertEqual(get_message_working_representation(self.workspace, self.chat_id, message_id)["text"], "X" * 100)
        self.assertEqual(load_context_variant(self.workspace, self.chat_id, message_id, variant["context_variant_id"])["text"], "X" * 40)

    def test_manual_edit_creates_revision_without_overwrite(self) -> None:
        message = self.add("assistant", "RAW")
        first = create_message_context_variant(
            self.workspace, self.chat_id, message["message_id"], "A", source="manual_edit"
        )
        first_bytes = Path(first["path"]).read_bytes()
        second = create_message_context_variant(
            self.workspace,
            self.chat_id,
            message["message_id"],
            "B",
            source="manual_edit",
            parent_variant_id=first["context_variant_id"],
            manually_edited=True,
        )
        self.assertEqual(Path(first["path"]).read_bytes(), first_bytes)
        self.assertEqual(second["parent_variant_id"], first["context_variant_id"])
        self.assertEqual(get_message_context_state(self.workspace, self.chat_id, message["message_id"])["active_variant_id"], second["context_variant_id"])

    def test_missing_active_variant_is_corruption(self) -> None:
        message = self.add("user", "RAW")
        message_id = message["message_id"]
        state = {
            "schema_version": MESSAGE_CONTEXT_SCHEMA_VERSION,
            "workspace_id": self.workspace_info["workspace_id"],
            "chat_id": self.chat_id,
            "message_id": message_id,
            "active_representation": "summary",
            "active_variant_id": "ctxv_0123456789abcdef",
            "updated_at": "test",
        }
        path = self.state_path(message_id)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "не найден"):
            get_message_context_state(self.workspace, self.chat_id, message_id)

    def test_cross_message_variant_empty_and_recompression_rejected(self) -> None:
        first = self.add("user", "FIRST RAW")
        second = self.add("assistant", "SECOND RAW")
        variant = create_message_context_variant(
            self.workspace,
            self.chat_id,
            first["message_id"],
            "FIRST SUMMARY",
            source="llm_compression",
        )
        with self.assertRaises(RuntimeError):
            activate_message_context_variant(
                self.workspace,
                self.chat_id,
                second["message_id"],
                variant["context_variant_id"],
            )
        with self.assertRaises(ValueError):
            create_message_context_variant(
                self.workspace,
                self.chat_id,
                second["message_id"],
                "   ",
                source="manual_edit",
            )
        with self.assertRaisesRegex(RuntimeError, "Повторное сжатие"):
            create_message_context_variant(
                self.workspace,
                self.chat_id,
                first["message_id"],
                "ANOTHER SUMMARY",
                source="llm_compression",
            )

    def test_working_chat_preserves_roles_and_order(self) -> None:
        first = self.add("user", "AAA RAW")
        second = self.add("assistant", "BBBBBBBB")
        third = self.add("user", "CCC")
        create_message_context_variant(
            self.workspace,
            self.chat_id,
            second["message_id"],
            "BBB",
            source="llm_compression",
        )
        working = load_chat_working_messages(self.workspace, self.chat_id)
        self.assertEqual(
            [(item["role"], item["content"]) for item in working],
            [("user", "AAA RAW"), ("assistant", "BBB"), ("user", "CCC")],
        )
        self.assertEqual(
            [item["message_id"] for item in working],
            [first["message_id"], second["message_id"], third["message_id"]],
        )
        restore_message_raw(self.workspace, self.chat_id, second["message_id"])
        restored = load_chat_working_messages(self.workspace, self.chat_id)
        self.assertEqual(
            [(item["role"], item["content"]) for item in restored],
            [
                ("user", "AAA RAW"),
                ("assistant", "BBBBBBBB"),
                ("user", "CCC"),
            ],
        )

    def test_server_request_uses_working_context_without_network(self) -> None:
        self.add("user", "AAA RAW")
        second = self.add("assistant", "BBBBBBBB")
        self.add("user", "CCC")
        create_message_context_variant(
            self.workspace,
            self.chat_id,
            second["message_id"],
            "BBB",
            source="llm_compression",
        )
        captured_bodies = []

        class FakeResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {
                    "choices": [
                        {
                            "message": {"content": "DONE"},
                            "finish_reason": "stop",
                        }
                    ]
                }

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, _url, *, headers, json):
                captured_bodies.append(json)
                return FakeResponse()

        compressed_events = []
        restored_events = []
        runtime_root = self.workspace.parent / "runtime"
        runtime_paths = {
            "backup_dir": str(runtime_root / "backup"),
            "log_dir": str(runtime_root / "logs"),
        }
        permissions = {
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
        final_audit = AsyncMock(
            return_value=VerifierResult(
                verdict="PASS",
                check_type="FINAL",
                violations=(),
                reason="Message-context fixture evidence accepted.",
                required_action="None.",
                verifier_run_id="ver_message_context_test",
                model_id="gigachat_3_pro",
                model_display_name="GigaChat 3 Pro",
                provider="gigachat",
                provider_model_id="GigaChat-3-Pro",
                task_id=None,
                checkpoint_id=None,
                operation_id=None,
            )
        )
        with (
            patch.object(server, "get_access_token", AsyncMock(return_value="token")),
            patch.object(server, "load_agent_global_context", return_value="ROLE"),
            patch.object(server, "ensure_workspace_runtime_dirs", return_value=runtime_paths),
            patch.object(server.httpx, "AsyncClient", return_value=FakeClient()),
            patch.object(server, "run_verifier_check", final_audit),
        ):
            compressed_result = asyncio.run(
                server.run_agent_task(
                    "CCC",
                    str(self.workspace),
                    chat_id=self.chat_id,
                    permissions=permissions,
                    on_event=compressed_events.append,
                )
            )
            restore_message_raw(
                self.workspace, self.chat_id, second["message_id"]
            )
            restored_result = asyncio.run(
                server.run_agent_task(
                    "CCC",
                    str(self.workspace),
                    chat_id=self.chat_id,
                    permissions=permissions,
                    on_event=restored_events.append,
                )
            )
        self.assertEqual(final_audit.await_count, 2)
        self.assertEqual(compressed_result, "DONE")
        self.assertEqual(restored_result, "DONE")
        compressed_request_messages = captured_bodies[0]["messages"][-3:]
        self.assertEqual(
            compressed_request_messages,
            [
                {"role": "user", "content": "AAA RAW"},
                {"role": "assistant", "content": "BBB"},
                {"role": "user", "content": "CCC"},
            ],
        )
        restored_request_messages = captured_bodies[1]["messages"][-3:]
        self.assertEqual(
            restored_request_messages,
            [
                {"role": "user", "content": "AAA RAW"},
                {"role": "assistant", "content": "BBBBBBBB"},
                {"role": "user", "content": "CCC"},
            ],
        )
        compressed_context_event = next(
            event
            for event in compressed_events
            if event["event"] == "chat_context_loaded"
        )
        restored_context_event = next(
            event
            for event in restored_events
            if event["event"] == "chat_context_loaded"
        )
        self.assertEqual(compressed_context_event["raw_messages"], 2)
        self.assertEqual(compressed_context_event["compressed_messages"], 1)
        self.assertEqual(compressed_context_event["chars"], 13)
        self.assertEqual(restored_context_event["raw_messages"], 3)
        self.assertEqual(restored_context_event["compressed_messages"], 0)
        self.assertEqual(restored_context_event["chars"], 18)

if __name__ == "__main__":
    unittest.main()
