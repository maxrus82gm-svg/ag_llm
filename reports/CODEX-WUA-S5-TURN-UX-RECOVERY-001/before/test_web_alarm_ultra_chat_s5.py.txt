"""Stage 5 integration on disposable Windows Workspaces."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import context_storage as core
import run_store as runs
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ultra_chat import OfflineUltraChatService, UltraChatError
from web_alarm.workspace_registry import WorkspaceRegistry


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="s5_чат_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.registry = WorkspaceRegistry(self.root / "registry")
        self.service = OfflineUltraChatService(self.registry, self.root)

    def create_chat(self, name):
        _, workspace = self.service.create_workspace({"title": name})
        ws = workspace["wa_workspace_id"]
        chat = "chat_" + uuid4().hex
        self.service.create_chat(ws, {"chat_id": chat, "initialize_workspace": True})
        return ws, chat

    @staticmethod
    def body(text, model="gigachat_2_pro"):
        return {"idempotency_key": uuid4().hex, "model_ref": model, "text": text}


class OfflineChatTests(Fixture):

    def test_two_messages_save_fake_answers(self):
        ws, chat = self.create_chat("Синтетический Workspace")
        for word in ("первое", "второе"):
            result = self.service.submit_turn(ws, chat, {"idempotency_key": uuid4().hex,
                "model_ref": "gigachat_2_pro", "text": word})
            self.assertEqual(result["state"], "SUCCEEDED")
            self.assertIn(word, result["answer"])
            self.assertTrue(result["answer"].startswith("TEST"))
        self.assertEqual(len(self.service.messages(ws, chat, None, 50)["messages"]), 4)

    def test_context_isolation_model_binding_restart_and_conflict(self):
        ws, first = self.create_chat("Проект")
        second = "chat_" + uuid4().hex
        self.service.create_chat(ws, {"chat_id": second, "title": "Второй"})
        payloads = []
        original = _FixtureTransport.send

        async def trace(fake, payload, **kwargs):
            payloads.append(payload)
            return await original(fake, payload, **kwargs)

        body = self.body("Первый A")
        with patch.object(_FixtureTransport, "send", trace):
            a = self.service.submit_turn(ws, first, body)
            self.service.submit_turn(ws, second, self.body("Только B", "gigachat_ultra"))
            self.service.submit_turn(ws, first, self.body("Второй A", "gigachat_2_max"))
            self.service = OfflineUltraChatService(self.registry, self.root)
            self.assertEqual(self.service.submit_turn(ws, first, body), a)
            with self.assertRaises(UltraChatError) as conflict:
                self.service.submit_turn(ws, first, {**body, "model_ref": "gigachat_ultra"})
        self.assertEqual(conflict.exception.code, "idempotency_conflict")
        self.assertEqual([p["model"] for p in payloads], ["GigaChat-2-Pro", "GigaChat-3-Ultra", "GigaChat-2-Max"])
        self.assertEqual([m["role"] for m in payloads[2]["messages"]], ["system", "user", "assistant", "user"])
        self.assertEqual(payloads[2]["messages"][1]["content"], "Первый A")
        self.assertNotIn("Только B", repr(payloads[2]))
        self.assertNotIn("Первый A", repr(payloads[1]))
        self.assertNotEqual(payloads[0]["messages"][0], payloads[1]["messages"][0])
        self.assertEqual(a["references"]["model_ref"], "gigachat_2_pro")
        self.assertEqual(len(self.service.messages(ws, first, None, 50)["messages"]), 4)

    def test_explicit_repeat_recovers_pending_result(self):
        ws, chat = self.create_chat("Потерянное подтверждение")
        body = self.body("Сохранённый ответ")
        clear = runs._clear_pending
        original = _FixtureTransport.send
        calls = []

        def fail_after_result(path):
            if json.loads(path.read_bytes())["record"]["event"] == "turn_result":
                raise OSError("lost acknowledgement")
            return clear(path)

        async def trace(fake, payload, **kwargs):
            calls.append(payload)
            return await original(fake, payload, **kwargs)

        with patch.object(_FixtureTransport, "send", trace):
            with patch.object(runs, "_clear_pending", side_effect=fail_after_result), self.assertRaises(UltraChatError):
                self.service.submit_turn(ws, chat, body)
            self.service = OfflineUltraChatService(self.registry, self.root)
            recovered = self.service.submit_turn(ws, chat, body)
        self.assertEqual(recovered["state"], "SUCCEEDED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.service.messages(ws, chat, None, 50)["messages"]), 2)

    def test_new_process_reuses_original_key_without_transport(self):
        ws, chat = self.create_chat("Перезапуск")
        body = self.body("До перезапуска")
        result = self.service.submit_turn(ws, chat, body)
        code = """
import json, sys
from pathlib import Path
from unittest.mock import patch
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.ultra_chat import OfflineUltraChatService
from web_alarm.workspace_registry import WorkspaceRegistry
root = Path(sys.argv[1])
service = OfflineUltraChatService(WorkspaceRegistry(root / "registry"), root)
with patch.object(_FixtureTransport, "send", side_effect=AssertionError("unexpected replay")) as fake:
    result = service.submit_turn(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
    fake.assert_not_called()
print(json.dumps(result))
"""
        child = subprocess.run([sys.executable, "-B", "-c", code, str(self.root), ws, chat, json.dumps(body)],
                               capture_output=True, timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(json.loads(child.stdout), result)
        self.assertEqual(len(self.service.messages(ws, chat, None, 50)["messages"]), 2)

    def test_error_and_unavailable_storage(self):
        ws, chat = self.create_chat("Отказ")
        body = self.body("Отказ fake")

        async def broken(*args, **kwargs):
            raise RuntimeError("synthetic exception")

        with patch.object(_FixtureTransport, "send", side_effect=broken) as send:
            result = self.service.submit_turn(ws, chat, body)
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertIsNone(result["answer"])
            self.assertIsNone(result["usage"]["total_tokens"])
            self.assertEqual(self.service.submit_turn(ws, chat, body), result)
        send.assert_awaited_once()
        root = Path(self.registry.get(ws).workspace_root)
        identity = root / ".ultra" / "workspace.json"
        identity.write_bytes(b"{broken")
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        with patch.object(_FixtureTransport, "send") as send, self.assertRaises(UltraChatError) as denied:
            self.service.submit_turn(ws, chat, self.body("Заблокировано"))
        self.assertEqual(denied.exception.code, "workspace_unavailable")
        send.assert_not_called()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_refuses_foreign_registered_path_before_reading_history(self):
        with tempfile.TemporaryDirectory(prefix="foreign_") as foreign:
            ws = self.registry.register("Foreign fixture", foreign).workspace_id
            with patch.object(core, "read_workspace_identity_bounded") as read, self.assertRaises(UltraChatError) as denied:
                self.service.submit_turn(ws, "chat_" + uuid4().hex, self.body("No"))
            read.assert_not_called()
            self.assertEqual(denied.exception.code, "offline_scope_invalid")
            self.assertEqual(list(Path(foreign).iterdir()), [])

    def test_model_refusal_leaves_no_turn_or_raw(self):
        ws, chat = self.create_chat("Модель недоступна")
        with patch.object(_FixtureTransport, "send") as send, self.assertRaises(UltraChatError):
            self.service.submit_turn(ws, chat, self.body("No", "unknown-model"))
        send.assert_not_called()
        self.assertEqual(self.service.messages(ws, chat, None, 50)["messages"], [])
        self.assertIsNone(self.service.latest_turn(ws, chat)["turn"])

    def test_tampered_assistant_is_not_projected_as_success(self):
        ws, chat = self.create_chat("Повреждённый RAW")
        result = self.service.submit_turn(ws, chat, self.body("Исходный текст"))
        raw = Path(self.registry.get(ws).workspace_root) / ".ultra/chats" / chat / "messages" / (result["assistant_message_id"] + ".json")
        value = json.loads(raw.read_bytes())
        value["original_text"] = "Подмена"
        raw.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(UltraChatError) as refused:
            self.service.messages(ws, chat, None, 50)
        self.assertEqual(refused.exception.code, "offline_history_invalid")
        with patch.object(_FixtureTransport, "send") as send, self.assertRaises(UltraChatError):
            self.service.submit_turn(ws, chat, self.body("Не передавать подмену"))
        send.assert_not_called()


class HttpAndTkTests(Fixture):
    def setUp(self):
        super().setUp()
        self.api = WebAlarmApi(self.root / "registry")
        self.service = OfflineUltraChatService(self.api.registry, self.root)

    def serve(self, **options):
        server = create_server(self.api, port=0, **options)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def http(self, server, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=12)
        try:
            wire = None if body is None else json.dumps(body).encode("utf-8")
            conn.request(method, path, wire, {"Content-Type": "application/json", **(headers or {})})
            reply = conn.getresponse()
            data = reply.read().decode("utf-8")
            return reply.status, json.loads(data) if reply.getheader("Content-Type", "").startswith("application/json") else data
        finally:
            conn.close()

    def tokens(self, server):
        _, cap = self.http(server, "GET", "/ui/ultra-chat/capability")
        _, write = self.http(server, "GET", "/ui/ultra-chat/write-capability")
        read = cap["ultra_chat"]
        write = write["ultra_chat_write"]
        origin = f"http://127.0.0.1:{server.server_address[1]}"
        return cap["turn_test"], {read["header"]: read["token"]}, {write["header"]: write["token"], "Origin": origin}

    def test_http_cancel_reopen_usage_and_standard_gate(self):
        server = self.serve(offline_chat=self.service)
        cap, read, write = self.tokens(server)
        self.assertEqual(cap["mode"], "TEST_OFFLINE")
        self.assertTrue(cap["models"])
        self.assertIn('data-stage5-offline="true"', self.http(server, "GET", "/")[1])
        self.assertEqual(self.http(server, "GET", "/ultra/model-cards")[0], 404)
        self.assertEqual(self.http(server, "POST", "/ultra/chat/workspaces", {"title": "No token"})[0], 403)
        status, workspace = self.http(server, "POST", "/ultra/chat/workspaces", {"title": "HTTP TEST"}, write)
        self.assertEqual(status, 201)
        ws, chat = workspace["wa_workspace_id"], "chat_" + uuid4().hex
        chats = f"/ultra/chat/workspaces/{ws}/chats"
        self.assertEqual(self.http(server, "POST", chats, {"chat_id": chat, "initialize_workspace": True}, write)[0], 201)
        base = f"{chats}/{chat}/turns"
        body = self.body("Отмена HTTP")
        entered, release = threading.Event(), threading.Event()
        wires = []

        async def delayed(_fake, payload, **kwargs):
            wires.append(payload)
            entered.set()
            if not release.wait(8):
                raise TimeoutError()
            return {"choices": [{"message": {"role": "assistant", "content": "Late response"}}],
                    "usage": {"total_tokens": 7}}

        with patch.object(_FixtureTransport, "send", delayed), ThreadPoolExecutor() as pool:
            future = pool.submit(self.http, server, "POST", base, body, write)
            try:
                self.assertTrue(entered.wait(5))
                _, active = self.http(server, "GET", base + "/latest", headers=read)
                self.assertEqual(active["turn"]["state"], "ATTEMPTING")
                tid = active["turn"]["turn_id"]
                self.assertEqual(self.http(server, "POST", base, {**body, "model_ref": "gigachat_ultra"}, write)[0], 409)
                self.assertEqual(self.http(server, "POST", base + "/" + tid + "/cancel", {}, write)[1]["state"], "UNKNOWN")
            finally:
                release.set()
            status, done = future.result(timeout=10)
            self.assertEqual(status, 200)
            self.assertEqual((done["state"], done["answer"], done["usage"]["total_tokens"]), ("UNKNOWN", None, 7))
            reopened = self.serve(offline_chat=OfflineUltraChatService(self.api.registry, self.root))
            _, read2, write2 = self.tokens(reopened)
            self.assertEqual(self.http(reopened, "GET", base + "/latest", headers=read2)[1]["turn"], done)
            self.assertEqual(self.http(reopened, "POST", base, body, write2), (200, done))
        self.assertEqual(len(wires), 1)
        self.assertEqual([m["role"] for m in self.service.messages(ws, chat, None, 50)["messages"]], ["user"])
        standard = self.serve()
        cap, _, write = self.tokens(standard)
        self.assertFalse(cap["available"])
        self.assertNotIn('data-stage5-offline="true"', self.http(standard, "GET", "/")[1])
        self.assertEqual(self.http(standard, "POST", base, body, write)[0], 400)
        from web_alarm.turn_service import REFERENCES
        self.assertEqual(self.http(standard, "POST", base, {**body, **REFERENCES}, write)[0], 403)

    def test_http_reply_disconnect_does_not_replace_success_with_500_or_repeat(self):
        from web_alarm.server import _JsonHandler
        server = self.serve(offline_chat=self.service)
        _, _, write = self.tokens(server)
        ws, chat = self.create_chat("Отключение браузера")
        base = f"/ultra/chat/workspaces/{ws}/chats/{chat}/turns"
        body = self.body("Ответ уже сохранён")
        send_json = _JsonHandler._send_json
        attempted = []

        def drop(handler, status, payload):
            attempted.append(status)
            if payload.get("state") == "SUCCEEDED":
                disconnect = ConnectionAbortedError("synthetic client disconnect")
                disconnect.winerror = 10053
                with patch.object(handler, "end_headers", side_effect=disconnect):
                    return send_json(handler, status, payload)
            return send_json(handler, status, payload)

        with patch.object(_JsonHandler, "_send_json", drop):
            with self.assertRaises(http.client.RemoteDisconnected):
                self.http(server, "POST", base, body, write)
        self.assertEqual(attempted, [200])
        with patch.object(_FixtureTransport, "send") as send:
            status, result = self.http(server, "POST", base, body, write)
        self.assertEqual((status, result["state"]), (200, "SUCCEEDED"))
        send.assert_not_called()
        self.assertEqual(len(self.service.messages(ws, chat, None, 50)["messages"]), 2)

    def test_tk_controls_and_history_shared_with_web(self):
        import ultra_ui
        server = self.serve(offline_chat=self.service)
        _, read, write = self.tokens(server)
        with patch.object(ultra_ui, "load_ui_state", side_effect=AssertionError("live UI state")):
            app = ultra_ui.UltraApp(offline_chat=self.service)
        self.addCleanup(app.destroy)
        app.withdraw()
        panel = app.offline_chat_panel
        self.assertIn("TEST", app.title())
        self.assertEqual(str(panel.send_button["state"]), "disabled")
        with patch.object(ultra_ui.simpledialog, "askstring", side_effect=["Tk TEST", "Диалог A"]):
            panel.workspace_new.invoke()
            panel.chat_new.invoke()
        self.assertEqual(str(panel.send_button["state"]), "normal")
        panel.model_pick.current(2)
        panel.input_box.insert("1.0", "Сообщение Tk")
        panel.send_button.invoke()
        deadline = time.monotonic() + 8
        while panel.inflight and time.monotonic() < deadline:
            app.update()
            time.sleep(0.01)
        self.assertEqual(panel.state, "SUCCEEDED", panel.status.get())
        self.assertIn("Ответ на: Сообщение Tk", panel.history.get("1.0", "end"))
        ws, chat = panel.workspace, panel.chat
        base = f"/ultra/chat/workspaces/{ws}/chats/{chat}"
        body = self.body("Продолжение Web", "gigachat_ultra")
        self.assertEqual(self.http(server, "POST", base + "/turns", body, write)[1]["state"], "SUCCEEDED")
        panel.check_button.invoke()
        self.assertIn("Ответ на: Продолжение Web", panel.history.get("1.0", "end"))
        status, history = self.http(server, "GET", base + "/messages", headers=read)
        self.assertEqual(status, 200)
        self.assertEqual([m["role"] for m in history["messages"]], ["user", "assistant", "user", "assistant"])

    def test_tk_cancel_control_and_reopen_unknown(self):
        import ultra_ui
        ws, chat = self.create_chat("Tk cancel")
        app = ultra_ui.UltraApp(offline_chat=self.service)
        app.withdraw()
        self.addCleanup(app.destroy)
        panel = app.offline_chat_panel
        self.assertEqual((panel.workspace, panel.chat), (ws, chat))
        entered, release = threading.Event(), threading.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(8):
                raise TimeoutError()
            return {"choices": [{"message": {"role": "assistant", "content": "Late Tk"}}],
                    "usage": {"total_tokens": 11}}

        with patch.object(_FixtureTransport, "send", side_effect=delayed) as fake:
            panel.input_box.insert("1.0", "Отменяемый Tk")
            panel.send_button.invoke()
            try:
                self.assertTrue(entered.wait(5))
                panel.check_button.invoke()
                self.assertEqual(panel.state, "ATTEMPTING")
                self.assertEqual(str(panel.cancel_button["state"]), "normal")
                panel.cancel_button.invoke()
                self.assertEqual(panel.state, "UNKNOWN")
            finally:
                release.set()
            deadline = time.monotonic() + 8
            while panel.inflight and time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)
            self.assertFalse(panel.inflight)
            self.assertIn("usage 11", panel.status.get())
            self.assertNotIn("Late Tk", panel.history.get("1.0", "end"))
            reopened = ultra_ui.UltraApp(offline_chat=OfflineUltraChatService(self.api.registry, self.root))
            reopened.withdraw()
            self.addCleanup(reopened.destroy)
            self.assertEqual(reopened.offline_chat_panel.state, "UNKNOWN")
            self.assertIn("usage 11", reopened.offline_chat_panel.status.get())
        fake.assert_awaited_once()

    def test_guard_and_provider_controls(self):
        import gigachat_transport
        import httpx
        ws, chat = self.create_chat("Guard")
        with (patch.object(gigachat_transport, "get_access_token", side_effect=AssertionError("OAuth denied")) as oauth,
              patch.object(httpx, "AsyncClient", side_effect=AssertionError("HTTP denied")) as http):
            self.assertEqual(self.service.submit_turn(ws, chat, self.body("Synthetic"))["state"], "SUCCEEDED")
            oauth.assert_not_called()
            http.assert_not_called()
            with self.assertRaises(AssertionError):
                httpx.AsyncClient()
            import asyncio
            with self.assertRaises(AssertionError):
                asyncio.run(gigachat_transport.get_access_token())
        if "ORDINARY_GUARD_LOG" not in os.environ:
            self.skipTest("Requires the task guard for physical negative probes")
        with socket.socket() as sock, self.assertRaises(PermissionError):
            sock.connect(("192.0.2.1", 443))
        with self.assertRaises(PermissionError):
            socket.getaddrinfo("offline.invalid", 443)
        with self.assertRaises(PermissionError):
            os.getenv("GIGACHAT_CREDENTIALS")
