"""Per-chat read projections and preferences on synthetic shared Ultra storage."""
from pathlib import Path
import unittest
from unittest.mock import patch

import test_web_alarm_ultra_chat_s5 as s5
from test_web_alarm_ordinary_core_bridge import reply
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.turn_service import TurnService
from web_alarm.ultra_chat import OrdinaryCoreChatService
from web_alarm.ultra_chat import UltraChatError


class PerChatTests(s5.Fixture):
    def setUp(self):
        super().setUp()
        self.service = OrdinaryCoreChatService(self.registry, self.root)

    def usage(self, ws, chat):
        return self.service.messages(ws, chat, None, 50)["usage_summary"]

    def test_known_nested_usage_replay_reopen_and_chat_isolation(self):
        ws, chat = self.create_chat("A")
        ws2, other = self.create_chat("B")
        body = self.body("one")
        known = dict(prompt_tokens=7, completion_tokens=5, total_tokens=12,
                     completion_tokens_details={"reasoning_tokens": 3})
        with patch.object(_FixtureTransport, "send", return_value=reply(known)) as send:
            first = self.service.submit_turn(ws, chat, body)
            self.assertEqual(self.service.submit_turn(ws, chat, body), first)
        send.assert_awaited_once()
        self.service = OrdinaryCoreChatService(self.registry, self.root)
        summary = self.usage(ws, chat)
        self.assertEqual(summary["known"], dict(prompt_tokens=7, completion_tokens=5, reasoning_tokens=3, total_tokens=12))
        self.assertEqual(summary["attempts"], 1)
        self.assertTrue(summary["complete"])
        self.assertTrue(summary["synthetic"])
        self.assertEqual(self.usage(ws2, other)["attempts"], 0)

    def test_missing_usage_stays_unknown_and_partial_sum_is_explicit(self):
        ws, chat = self.create_chat("partial")
        with patch.object(_FixtureTransport, "send", return_value=reply(dict(prompt_tokens=2, completion_tokens=3, total_tokens=5))):
            self.service.submit_turn(ws, chat, self.body("known"))
        self.service.submit_turn(ws, chat, self.body("unknown"))
        summary = self.usage(ws, chat)
        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["known"]["total_tokens"], 5)
        self.assertEqual(summary["missing"]["total_tokens"], 1)
        self.assertFalse(summary["complete"])
        self.assertIsNone(summary["last"]["usage"]["total_tokens"])

    def test_error_is_unknown_not_zero_and_cancel_before_start_costs_no_attempt(self):
        ws, chat = self.create_chat("errors")
        with patch.object(_FixtureTransport, "send", side_effect=RuntimeError("synthetic")):
            self.assertEqual(self.service.submit_turn(ws, chat, self.body("error"))["state"], "UNKNOWN")
        summary = self.usage(ws, chat)
        self.assertEqual(summary["missing"]["total_tokens"], 1)
        body = self.body("cancel before send")
        with patch.object(TurnService, "_execute", lambda owner, *args: owner.get(*args)):
            ready = self.service.submit_turn(ws, chat, body)
        self.service._turn_request("cancel", ws, chat, ready["turn_id"], {})
        self.assertEqual(self.usage(ws, chat)["attempts"], 1)

    def test_preflight_rejection_is_not_an_unknown_paid_attempt(self):
        import ordinary_chat_service as chat_core
        from web_alarm.ordinary_chat_bridge import OrdinaryCoreAdapter
        ws, chat = self.create_chat("preflight refused")
        def refuse(adapter, prepared):
            return chat_core.ChatResult(chat_core.Outcome.REJECTED, chat_core.Execution.NOT_STARTED,
                                       prepared.model, prepared.request_ref, error_code="provider_admission_required")
        with patch.object(OrdinaryCoreAdapter, "execute", refuse):
            result = self.service.submit_turn(ws, chat, self.body("no admission"))
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(self.usage(ws, chat)["attempts"], 0)

    def test_late_cancel_preserves_known_usage_without_success_or_double_count(self):
        ws, chat = self.create_chat("late")
        body = self.body("cancel during fake send")
        async def cancel_then_reply(*args, **kwargs):
            active = self.service.latest_turn(ws, chat)["turn"]
            self.service._turn_request("cancel", ws, chat, active["turn_id"], {})
            return reply(dict(prompt_tokens=1, completion_tokens=2, total_tokens=3))
        with patch.object(_FixtureTransport, "send", cancel_then_reply):
            result = self.service.submit_turn(ws, chat, body)
        self.assertEqual((result["state"], result["answer"]), ("UNKNOWN", None))
        self.assertEqual(self.service.submit_turn(ws, chat, body), result)
        summary = self.usage(ws, chat)
        self.assertEqual((summary["attempts"], summary["known"]["total_tokens"]), (1, 3))

    def test_preferences_persist_in_existing_chat_metadata_and_are_not_provider_caps(self):
        import json
        ws, chat = self.create_chat("settings A")
        other_ws, other = self.create_chat("settings B")
        defaults = {"compression_threshold_tokens": 250000, "answer_tokens": 10000}
        self.assertEqual(self.service.chat_preferences(ws, chat)["settings"], defaults)
        changed = {"compression_threshold_tokens": 123456, "answer_tokens": 20000}
        self.service.chat_preferences(ws, chat, changed)
        self.service = OrdinaryCoreChatService(self.registry, self.root)
        read = self.service.chat_preferences(ws, chat)
        self.assertEqual(read["settings"], changed)
        self.assertFalse(read["applied_to_provider"])
        self.assertFalse(read["automatic_compression"])
        self.assertEqual(self.service.chat_preferences(other_ws, other)["settings"], defaults)
        root = Path(self.registry.get(ws).workspace_root)
        metadata = json.loads((root / ".ultra/chats" / chat / "metadata.json").read_bytes())
        self.assertEqual(metadata["chat_id"], chat)
        self.assertEqual(metadata["ordinary_chat_settings"], changed)
        result = self.service.submit_turn(ws, chat, self.body("different model", "gigachat_ultra"))
        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertEqual(self.service.chat_preferences(ws, chat)["settings"], changed)
        import run_store
        saved = run_store.load_run_summary(root, result["run_id"], chat)
        self.assertEqual(saved["turn"]["prepared"]["limits"]["max_output_tokens"], 128)

    def test_invalid_settings_do_not_write_or_reset_existing_values(self):
        ws, chat = self.create_chat("validation")
        good = {"compression_threshold_tokens": 250000, "answer_tokens": 10000}
        self.service.chat_preferences(ws, chat, good)
        for bad in [None, {}, {**good, "answer_tokens": True}, {**good, "answer_tokens": 0},
                    {**good, "answer_tokens": -1}, {**good, "answer_tokens": 1.5},
                    {**good, "answer_tokens": "20000"}, {**good, "answer_tokens": 2**60}, {**good, "real": True}]:
            with self.subTest(bad=bad), self.assertRaises(UltraChatError):
                self.service.chat_preferences(ws, chat, bad)
            self.assertEqual(self.service.chat_preferences(ws, chat)["settings"], good)


class PerChatHttpTests(unittest.TestCase):
    http = s5.HttpAndTkTests.http
    tokens = s5.HttpAndTkTests.tokens

    def test_settings_http_requires_write_capability_and_is_reopenable(self):
        import tempfile
        import threading
        from web_alarm.server import WebAlarmApi, create_server
        with tempfile.TemporaryDirectory(prefix="perchat_http_") as temp:
            root = Path(temp).resolve()
            api = WebAlarmApi(root / "registry")
            service = OrdinaryCoreChatService(api.registry, root)
            server = create_server(api, port=0, offline_chat=service)
            worker = threading.Thread(target=server.serve_forever); worker.start()
            try:
                _, read, write = self.tokens(server)
                _, ws = service.create_workspace({"title": "settings"})
                from uuid import uuid4
                chat = "chat_" + uuid4().hex
                service.create_chat(ws["wa_workspace_id"], {"chat_id": chat, "initialize_workspace": True})
                path = f'/ultra/chat/workspaces/{ws["wa_workspace_id"]}/chats/{chat}/settings'
                data = {"compression_threshold_tokens": 250000, "answer_tokens": 20000}
                self.assertEqual(self.http(server, "POST", path, data, read)[0], 403)
                self.assertEqual(self.http(server, "POST", path, data, write)[0], 200)
                self.assertEqual(self.http(server, "GET", path, headers=read)[1]["settings"], data)
                self.assertEqual(self.http(server, "POST", path, {**data, "answer_tokens": 0}, write)[0], 400)
                self.assertEqual(self.http(server, "GET", path + "?root=foreign", headers=read)[0], 400)
            finally:
                server.shutdown(); server.server_close(); worker.join(5)
