"""Ordinary Web/Core integration: real shared storage, isolated fake transport."""
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import context_storage as core
import ordinary_chat_service as ordinary
import run_store as runs
import test_web_alarm_ultra_chat_s5 as s5
from web_alarm.ordinary_chat_bridge import OrdinaryCoreAdapter
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ultra_chat import OrdinaryCoreChatService, UltraChatError
from web_alarm.turn_service import TurnService


def reply(usage=None):
    value = {"choices": [{"message": {"role": "assistant", "content": "Synthetic answer"}}]}
    if usage is not None:
        value["usage"] = usage
    return value


class CoreBridgeTests(s5.Fixture):
    def setUp(self):
        super().setUp()
        self.service = OrdinaryCoreChatService(self.registry, self.root)

    def project(self):
        ws, chat = self.create_chat("Bridge fixture")
        root = Path(self.registry.get(ws).workspace_root)
        core.save_project_context(root, "System rule: keep the selected Chat isolated.")
        return ws, chat, root

    def test_complete_history_and_system_context_use_existing_core(self):
        ws, chat, root = self.project()
        wires = []
        original = _FixtureTransport.send

        async def trace(fake, payload, **kwargs):
            wires.append(payload)
            return await original(fake, payload, **kwargs)

        with patch.object(_FixtureTransport, "send", trace), patch.object(
                ordinary, "execute_request", wraps=ordinary.execute_request) as execute:
            for text in ("first", "second", "third"):
                self.service.submit_turn(ws, chat, self.body(text))
        self.assertEqual(execute.call_count, 3)
        self.assertEqual([m["role"] for m in wires[-1]["messages"]],
                         ["system", "user", "assistant", "user", "assistant", "user"])
        self.assertEqual([m["content"] for m in wires[-1]["messages"] if m["role"] == "user"],
                         ["first", "second", "third"])
        self.assertEqual(wires[-1]["messages"][0]["content"], "System rule: keep the selected Chat isolated.")
        self.assertEqual(len(core.read_chat_history_bounded(root, chat)["messages"]), 6)

    def test_many_chats_and_model_selection_are_independent(self):
        ws, first, root = self.project()
        second = "chat_" + uuid4().hex
        self.service.create_chat(ws, {"chat_id": second})
        ws2, third, _ = self.project()
        wires = []
        original = _FixtureTransport.send

        async def trace(fake, payload, **kwargs):
            wires.append(payload)
            return await original(fake, payload, **kwargs)

        with patch.object(_FixtureTransport, "send", trace):
            self.service.submit_turn(ws, first, self.body("private-A"))
            self.service.submit_turn(ws, second, self.body("private-B", "gigachat_2_max"))
            self.service.submit_turn(ws2, third, self.body("private-C", "gigachat_ultra"))
        self.assertEqual([w["model"] for w in wires], ["GigaChat-2-Pro", "GigaChat-2-Max", "GigaChat-3-Ultra"])
        self.assertNotIn("private-A", repr(wires[1:]))
        self.assertNotIn("private-B", repr(wires[2]))
        self.assertEqual(len(core.list_chats(root)), 2)

    def test_usage_reasoning_is_nested_and_survives_reopen_and_replay(self):
        ws, chat, root = self.project()
        body = self.body("usage")
        usage = {"prompt_tokens": 7, "completion_tokens": 5, "total_tokens": 12,
                 "completion_tokens_details": {"reasoning_tokens": 3}}
        with patch.object(_FixtureTransport, "send", return_value=reply(usage)) as send:
            first = self.service.submit_turn(ws, chat, body)
            self.service = OrdinaryCoreChatService(self.registry, self.root)
            self.assertEqual(self.service.submit_turn(ws, chat, body), first)
        send.assert_awaited_once()
        self.assertEqual(first["usage"], dict(status="complete", prompt_tokens=7,
            completion_tokens=5, total_tokens=12, reasoning_tokens=3))
        self.assertEqual(self.service.latest_turn(ws, chat)["turn"], first)
        terminal = runs.load_stream_records(root, first["run_id"], "SERVER")[-1]
        self.assertEqual(terminal["payload"]["usage"], first["usage"])
        self.assertEqual(len(core.read_chat_history_bounded(root, chat)["messages"]), 2)

    def test_usage_missing_invalid_and_unsupported_reasoning_remain_unknown(self):
        for usage in (None, {"total_tokens": True}, {"prompt_tokens": 1, "completion_tokens": 2,
                    "total_tokens": 3, "completion_tokens_details": {"reasoning_tokens": 9}}):
            with self.subTest(usage=usage):
                ws, chat, _ = self.project()
                with patch.object(_FixtureTransport, "send", return_value=reply(usage)):
                    result = self.service.submit_turn(ws, chat, self.body("unknown usage"))
                self.assertIsNone(result["usage"]["reasoning_tokens"])
                if usage is None or usage.get("total_tokens") is True:
                    self.assertIsNone(result["usage"]["total_tokens"])

    def test_transport_failure_does_not_replay_or_enter_next_context(self):
        ws, chat, _ = self.project()
        body = self.body("failed input must be excluded")
        with patch.object(_FixtureTransport, "send", side_effect=RuntimeError("PRIVATE_SENTINEL")) as send:
            result = self.service.submit_turn(ws, chat, body)
            self.assertEqual(self.service.submit_turn(ws, chat, body), result)
        send.assert_awaited_once()
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertNotIn("PRIVATE_SENTINEL", json.dumps(result))
        original = _FixtureTransport.send
        wires = []

        async def trace(fake, payload, **kwargs):
            wires.append(payload)
            return await original(fake, payload, **kwargs)
        with patch.object(_FixtureTransport, "send", trace):
            self.service.submit_turn(ws, chat, self.body("fresh input"))
        self.assertNotIn(body["text"], repr(wires))

    def test_invalid_response_is_failed_and_not_reexecuted(self):
        ws, chat, _ = self.project()
        body = self.body("invalid response")
        with patch.object(_FixtureTransport, "send", return_value={"choices": []}) as send:
            result = self.service.submit_turn(ws, chat, body)
            self.assertEqual(result["state"], "FAILED")
            self.assertEqual(self.service.submit_turn(ws, chat, body), result)
        send.assert_awaited_once()

    def test_ready_replay_keeps_original_system_and_does_not_rebuild_context(self):
        ws, chat, root = self.project()
        body = self.body("freeze")
        with patch.object(TurnService, "_execute", lambda owner, *args: owner.get(*args)):
            ready = self.service.submit_turn(ws, chat, body)
        self.assertEqual(ready["state"], "READY")
        core.save_project_context(root, "CHANGED AFTER ACCEPTANCE")
        self.service = OrdinaryCoreChatService(self.registry, self.root)
        original = _FixtureTransport.send
        wires = []

        async def trace(fake, payload, **kwargs):
            wires.append(payload)
            return await original(fake, payload, **kwargs)
        with patch.object(_FixtureTransport, "send", trace), patch.object(
                self.service, "_chat_context", side_effect=AssertionError("rebuild on replay")):
            result = self.service.submit_turn(ws, chat, body)
        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertEqual(result["request_ref"], ready["request_ref"])
        self.assertEqual(wires[0]["messages"][0]["content"], "System rule: keep the selected Chat isolated.")

    test_tampered_assistant_is_not_projected_as_success = s5.OfflineChatTests.test_tampered_assistant_is_not_projected_as_success

    def test_late_cancel_retains_usage_but_never_success(self):
        ws, chat, _ = self.project()
        entered, release = threading.Event(), threading.Event()
        body = self.body("cancel")

        async def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(8):
                raise TimeoutError()
            return reply({"prompt_tokens": 1, "completion_tokens": 4, "total_tokens": 5,
                          "completion_tokens_details": {"reasoning_tokens": 2}})
        with patch.object(_FixtureTransport, "send", delayed), ThreadPoolExecutor() as pool:
            pending = pool.submit(self.service.submit_turn, ws, chat, body)
            try:
                self.assertTrue(entered.wait(5))
                active = self.service.latest_turn(ws, chat)["turn"]
                cancelled = self.service._turn_request("cancel", ws, chat, active["turn_id"], {})
                self.assertEqual(cancelled["state"], "UNKNOWN")
            finally:
                release.set()
            result = pending.result(12)
        self.assertEqual((result["state"], result["answer"]), ("UNKNOWN", None))
        self.assertEqual(result["usage"]["reasoning_tokens"], 2)
        self.service = OrdinaryCoreChatService(self.registry, self.root)
        self.assertEqual(self.service.submit_turn(ws, chat, body), result)

    def test_cross_owner_new_turn_is_refused_during_send(self):
        ws, chat, _ = self.project()
        entered, release = threading.Event(), threading.Event()
        other = OrdinaryCoreChatService(self.registry, self.root)

        async def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(8):
                raise TimeoutError()
            return reply()
        with patch.object(_FixtureTransport, "send", delayed) as send, ThreadPoolExecutor() as pool:
            pending = pool.submit(self.service.submit_turn, ws, chat, self.body("active"))
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises(UltraChatError) as denied:
                    other.submit_turn(ws, chat, self.body("stale concurrent context"))
                self.assertEqual(denied.exception.code, "test_chat_busy")
            finally:
                release.set()
            self.assertEqual(pending.result(12)["state"], "SUCCEEDED")

    def test_context_limit_refuses_whole_request_without_silent_truncation(self):
        ws, chat, _ = self.project()
        for _ in range(4):
            self.service.submit_turn(ws, chat, self.body("x" * 1500))
        before = self.service.latest_turn(ws, chat)
        with patch.object(_FixtureTransport, "send") as send, self.assertRaises(UltraChatError):
            self.service.submit_turn(ws, chat, self.body("x" * 1500))
        send.assert_not_called()
        self.assertEqual(self.service.latest_turn(ws, chat), before)

    def test_real_transport_object_is_never_dispatched(self):
        adapter = OrdinaryCoreAdapter(context_ref="server-context", response=reply())
        request = ordinary.prepare_request(model_id="gigachat_2_pro", context=(), user_text="fake",
            context_ref="server-context", limits=ordinary.RequestLimits(4, 2048, 8192, 8192, 64, 2))
        class Forbidden:
            async def send(self, *args, **kwargs):
                raise AssertionError("Real transport must never be reached")
        adapter._transport = Forbidden()
        result = adapter.execute(request)
        self.assertEqual((result.outcome, result.execution, result.error_code),
                         (ordinary.Outcome.REJECTED, ordinary.Execution.NOT_STARTED, "provider_admission_required"))

    def test_bad_ids_model_and_config_cannot_read_or_send(self):
        ws, chat, root = self.project()
        for workspace, chat_id, body in (("ws_" + "0" * 32, chat, self.body("no")),
                (ws, "chat_" + "0" * 32, self.body("no")),
                (ws, chat, self.body("no", "not-in-registry")),
                (ws, chat, {**self.body("no"), "config_ref": "REAL"})):
            with self.subTest(workspace=workspace, chat=chat_id, body=body), patch.object(
                    _FixtureTransport, "send") as send, self.assertRaises(UltraChatError):
                self.service.submit_turn(workspace, chat_id, body)
            send.assert_not_called()
        self.assertEqual(core.read_chat_history_bounded(root, chat)["messages"], [])


class CoreBridgeHttpTests(unittest.TestCase):
    # Reuse the existing real-loopback HTTP helpers without inheriting Tk tests.
    http = s5.HttpAndTkTests.http
    tokens = s5.HttpAndTkTests.tokens

    def test_existing_web_page_routes_and_standard_denial(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="ordinary_bridge_http_") as temp:
            root = Path(temp).resolve()
            api = WebAlarmApi(root / "registry")
            service = OrdinaryCoreChatService(api.registry, root)
            server = create_server(api, port=0, offline_chat=service)
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                cap, read, write = self.tokens(server)
                self.assertTrue(cap["core_bridge"])
                self.assertFalse(cap["real_available"])
                self.assertIn('data-stage5-offline="true"', self.http(server, "GET", "/")[1])
                _, ws = self.http(server, "POST", "/ultra/chat/workspaces", {"title": "HTTP fixture"}, write)
                chat = "chat_" + uuid4().hex
                base = f'/ultra/chat/workspaces/{ws["wa_workspace_id"]}/chats'
                self.assertEqual(self.http(server, "POST", base, {"chat_id": chat, "initialize_workspace": True}, write)[0], 201)
                path = f"{base}/{chat}/turns"
                body = dict(idempotency_key=uuid4().hex, model_ref="gigachat_2_pro", text="HTTP bridge")
                code, result = self.http(server, "POST", path, body, write)
                self.assertEqual((code, result["state"]), (200, "SUCCEEDED"))
                self.assertEqual(self.http(server, "GET", path + "/latest", headers=read)[1]["turn"], result)
                self.assertEqual(self.http(server, "POST", path, body, write), (200, result))
                code, _ = self.http(server, "POST", path, {**body, "config_ref": "REAL"}, write)
                self.assertEqual(code, 400)
                with self.assertRaises(ValueError):
                    create_server(api, port=0, offline_chat=service, allow_non_loopback=True)
            finally:
                server.shutdown(); server.server_close(); worker.join(5)
            standard = create_server(api, port=0)
            worker = threading.Thread(target=standard.serve_forever); worker.start()
            try:
                cap, _, write = self.tokens(standard)
                self.assertFalse(cap["available"])
                self.assertIn(self.http(standard, "POST", path, body, write)[0], (400, 403))
            finally:
                standard.shutdown(); standard.server_close(); worker.join(5)
