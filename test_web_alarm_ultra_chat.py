"""Ultra Chat stage 1 over real HTTP (CLAUDE-WUA-CHAT-S1-READONLY-UI-001, programme No.37 stage 1).

The production create_server() and WebAlarmApi on disposable storage and Workspaces in TEMP: the own read
capability (independent of the folder picker), the local-origin gate shared with the folder picker, and the
read-only history routes with their data states, legacy outcomes, limits, privacy and no-write guarantees.
Loopback only; no GigaChat, no credentials, no live data.
"""
from __future__ import annotations

import contextlib
import functools
import hashlib
import http.client
import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as cs
import run_store
from web_alarm import server as wa_server
from web_alarm import ultra_chat
from web_alarm.server import WebAlarmApi, build_parser, create_server

ROOT = Path(cs.__file__).resolve().parent
CAP = "/ui/ultra-chat/capability"
HEADER = "X-WebAlarm-Ultra-Chat-Token"
FOLDER_HEADER = "X-WebAlarm-Folder-Token"


def snapshot(base: Path) -> dict[str, tuple]:
    result: dict[str, tuple] = {}
    stack = [base]
    while stack:
        folder = stack.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                st = os.lstat(entry.path)
                rel = Path(entry.path).relative_to(base).as_posix()
                if cs._is_link_or_reparse(st):
                    result[rel] = ("link", st.st_mtime_ns)
                elif entry.is_dir(follow_symlinks=False):
                    result[rel] = ("dir", st.st_mtime_ns)
                    stack.append(Path(entry.path))
                else:
                    result[rel] = ("file", st.st_size, st.st_mtime_ns,
                                   hashlib.sha256(Path(entry.path).read_bytes()).hexdigest())
    return result


class Server:
    def __init__(self, storage: Path, **kwargs):
        self.api = WebAlarmApi(storage)
        self.server = create_server(self.api, port=0, **kwargs)
        self.port = self.server.server_port
        self.host = f"127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def request(self, method, path, headers=None, omit=(), extra=(), body=b""):
        sent = {"Host": self.host, **(headers or {})}
        for key in omit:
            sent.pop(key, None)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for key, value in [*sent.items(), *extra]:
                conn.putheader(key, value)
            if method in {"POST", "PUT", "PATCH"}:
                conn.putheader("Content-Length", str(len(body)))
            conn.endheaders(body if method in {"POST", "PUT", "PATCH"} else None)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def token(self):
        status, _, raw = self.request("GET", CAP)
        assert status == 200, status
        return json.loads(raw)["ultra_chat"]["token"]

    def get(self, path, token=None):
        status, headers, raw = self.request("GET", path, {HEADER: token or self.token()})
        return status, json.loads(raw)


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_s1_http_")).resolve()
        self.junctions: list[Path] = []
        self.addCleanup(self._cleanup)
        self.native = patch("web_alarm.folder_picker.subprocess.run",
                            side_effect=AssertionError("native folder dialog must not start")).start()
        self.addCleanup(patch.stopall)
        self.bodies: list[bytes] = []

    def _cleanup(self):
        for link in reversed(self.junctions):
            try:
                os.rmdir(link)
            except OSError:
                pass
        shutil.rmtree(self.base, ignore_errors=True)

    def start(self, name="storage", **kwargs) -> Server:
        server = Server(self.base / name, **kwargs)
        self.addCleanup(server.stop)
        return server

    def junction(self, target: Path, link: Path) -> None:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        self.junctions.append(link)

    def project(self, server: Server, name: str, *, title="Диалог", history=True):
        root = self.base / name
        root.mkdir()
        chat = None
        if history:
            cs.ensure_workspace_storage(root)
            chat = cs.create_chat(root, title)["chat_id"]
        record = server.api.registry.register(name.capitalize(), root)
        return root, record.workspace_id, chat

    def call(self, server, path, token=None):
        status, headers, raw = server.request("GET", path, {HEADER: token or server.token()})
        self.bodies.append(raw)
        return status, json.loads(raw)

    def assert_denied(self, status, raw, *secrets_):
        self.assertIn(status, (400, 403, 404, 405))
        for value in secrets_:
            if value:
                self.assertNotIn(value.encode(), raw)


class CapabilityTests(Base):
    def test_c1_read_capability_works_with_the_folder_picker_off_by_default_and_on(self):
        for picker in (False, True):
            with self.subTest(picker=picker):
                server = self.start(f"s{int(picker)}", enable_folder_picker=picker)
                if picker:
                    patch.object(server.server.web_alarm_folder_picker, "capabilities",
                                 return_value={"available": True, "reason": None}).start()
                status, headers, raw = server.request("GET", CAP)
                value = json.loads(raw)["ultra_chat"]
                self.assertEqual((status, value["available"], value["reason"], value["scope"], value["header"]),
                                 (200, True, None, "ultra_chat_read", HEADER))
                self.assertGreaterEqual(len(value["token"]), 32)
                self.assertEqual(headers.get("Cache-Control"), "no-store")
                status, _ = server.get("/ultra/chat/workspaces", value["token"])
                self.assertEqual(status, 200)
                folder = json.loads(server.request("GET", "/ui/capabilities")[2])["folder_picker"]["token"]
                self.assertEqual(folder is None, not picker)
                self.assertNotEqual(folder, value["token"])

    def test_c2_tokens_never_cross_scopes(self):
        server = self.start(enable_folder_picker=True)
        patch.object(server.server.web_alarm_folder_picker, "capabilities",
                     return_value={"available": True, "reason": None}).start()
        chat_token, folder_token = server.token(), server.server.web_alarm_folder_picker.token
        for label, headers in (("folder token in chat header", {HEADER: folder_token}),
                               ("folder token in folder header", {FOLDER_HEADER: folder_token}),
                               ("chat token in folder header", {FOLDER_HEADER: chat_token})):
            with self.subTest(case=label):
                status, _, raw = server.request("GET", "/ultra/chat/workspaces", headers)
                self.assertEqual(status, 403)
                self.assertEqual(json.loads(raw)["error"]["code"], "ultra_chat_token_invalid")
        status, _, _ = server.request("POST", "/ui/pick-workspace-folder",
                                      {"Origin": "http://" + server.host, "Content-Type": "application/json",
                                       FOLDER_HEADER: chat_token}, body=b"{}")
        self.assertEqual(status, 403)
        self.native.assert_not_called()

    def test_c3_switched_off_chat_reading_leaves_picker_evm_and_operator_working(self):
        server = self.start(enable_folder_picker=True, enable_ultra_chat=False)
        patch.object(server.server.web_alarm_folder_picker, "capabilities",
                     return_value={"available": True, "reason": None}).start()
        value = json.loads(server.request("GET", CAP)[2])["ultra_chat"]
        self.assertEqual((value["available"], value["reason"], value["token"]), (False, "disabled", None))
        status, _, raw = server.request("GET", "/ultra/chat/workspaces", {HEADER: secrets.token_urlsafe(32)})
        self.assertEqual((status, json.loads(raw)["error"]["code"]), (403, "ultra_chat_unavailable"))
        folder = json.loads(server.request("GET", "/ui/capabilities")[2])["folder_picker"]
        self.assertEqual(folder["token"], server.server.web_alarm_folder_picker.token)
        for path in ("/status", "/workspaces", "/ultra/connections", "/"):
            with self.subTest(path=path):
                self.assertEqual(server.request("GET", path)[0], 200)

    def test_c4_non_loopback_bind_gives_no_capability_and_no_history(self):
        access = ultra_chat.UltraChatAccess(enabled=True, loopback=False)
        self.assertEqual((access.capability()["available"], access.reason, access.capability()["token"]),
                         (False, "non_loopback_bind", None))
        server = self.start()
        token = server.token()
        address = server.server.server_address
        try:
            server.server.server_address = ("0.0.0.0", address[1])
            for path in (CAP, "/ultra/chat/workspaces"):
                with self.subTest(path=path):
                    status, _, raw = server.request("GET", path, {HEADER: token})
                    self.assert_denied(status, raw, token)
                    self.assertEqual(status, 403)
        finally:
            server.server.server_address = address

    def test_c5_command_line_switch_reaches_create_server(self):
        self.assertTrue(build_parser().parse_args(["--disable-ultra-chat"]).disable_ultra_chat)
        self.assertFalse(build_parser().parse_args([]).disable_ultra_chat)
        seen = {}

        def fake_create_server(api, **kwargs):
            seen.update(kwargs)
            raise OSError("stop after capturing")
        with patch.object(wa_server, "create_server", fake_create_server), \
                contextlib.redirect_stderr(io.StringIO()):
            code = wa_server.main(["--storage-root", str(self.base / "cli"), "--port", "0", "--disable-ultra-chat"])
        self.assertEqual((code, seen.get("enable_ultra_chat")), (2, False))

    def test_c6_token_of_a_restarted_or_other_server_process_is_refused(self):
        first = self.start("one")
        old = first.token()
        first.stop()
        second = self.start("two")
        status, _, raw = second.request("GET", "/ultra/chat/workspaces", {HEADER: old})
        self.assertEqual((status, json.loads(raw)["error"]["code"]), (403, "ultra_chat_token_invalid"))
        self.assertEqual(second.get("/ultra/chat/workspaces")[0], 200)


class TokenTests(Base):
    def test_t1_invalid_tokens_are_refused_and_query_tokens_are_not_accepted(self):
        server = self.start()
        token = server.token()
        other = self.start("other").token()
        cases = [("missing", {}, ()), ("empty", {HEADER: ""}, ()),
                 ("wrong same length", {HEADER: ("A" if token[0] != "A" else "B") + token[1:]}, ()),
                 ("short", {HEADER: "wrong"}, ()), ("non ascii", {HEADER: token[:-1] + "é"}, ()),
                 ("too long", {HEADER: token + "x" * 200}, ()),
                 ("two valid headers", {HEADER: token}, ((HEADER, token),)),
                 ("valid and wrong", {HEADER: token}, ((HEADER, "wrong"),)),
                 ("other server process", {HEADER: other}, ()),
                 ("cookie", {"Cookie": f"{HEADER}={token}"}, ())]
        for label, headers, extra in cases:
            with self.subTest(case=label):
                status, _, raw = server.request("GET", "/ultra/chat/workspaces", headers, extra=extra)
                self.assertEqual(status, 403)
                self.assertNotIn(b"workspaces\"", raw)
        status, _, raw = server.request("GET", "/ultra/chat/workspaces?token=" + token)
        self.assertEqual((status, json.loads(raw)["error"]["code"]), (400, "invalid_ultra_chat_request"))
        self.assertEqual(server.request("GET", CAP + "?x=1")[0], 400)


class OriginTests(Base):
    def test_o1_foreign_or_opaque_origin_is_refused_on_every_route(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        token = server.token()
        port, origin = str(server.port), "http://" + server.host
        cases = [("foreign host", {"Host": "foreign.example:" + port}, (), ()), ("other port", {"Host": "127.0.0.1:1"}, (), ()),
                 ("no host", {}, ("Host",), ()), ("two hosts", {}, (), (("Host", "foreign.example"),)),
                 ("foreign origin", {"Origin": "https://foreign.example"}, (), ()), ("null origin", {"Origin": "null"}, (), ()),
                 ("origin with slash", {"Origin": origin + "/"}, (), ()), ("two origins", {"Origin": origin}, (), (("Origin", origin),)),
                 ("cross-site", {"Sec-Fetch-Site": "cross-site"}, (), ()), ("same-site", {"Sec-Fetch-Site": "same-site"}, (), ()),
                 ("two fetch sites", {"Sec-Fetch-Site": "same-origin"}, (), (("Sec-Fetch-Site", "cross-site"),))]
        routes = (CAP, "/ultra/chat/workspaces", f"/ultra/chat/workspaces/{wa_id}/chats",
                  f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages")
        for route in routes:
            for label, change, omit, extra in cases:
                with self.subTest(route=route.split("/")[-1], case=label):
                    status, _, raw = server.request("GET", route, {HEADER: token, **change}, omit, extra)
                    self.assertEqual(status, 403)
                    self.assert_denied(status, raw, token, "Диалог")

    def test_o2_normal_same_origin_reads_pass(self):
        server = self.start()
        token = server.token()
        for label, headers in (("localhost host", {"Host": "localhost:" + str(server.port)}),
                               ("fetch metadata only", {"Sec-Fetch-Site": "same-origin"}),
                               ("navigation metadata", {"Sec-Fetch-Site": "none"}),
                               ("exact origin", {"Origin": "http://" + server.host})):
            with self.subTest(case=label):
                self.assertEqual(server.request("GET", "/ultra/chat/workspaces", {HEADER: token, **headers})[0], 200)

    def test_o3_other_methods_and_preflight_are_refused_without_cors(self):
        server = self.start()
        token = server.token()
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            for route in (CAP, "/ultra/chat/workspaces"):
                with self.subTest(method=method, route=route.split("/")[-1]):
                    status, headers, raw = server.request(method, route, {HEADER: token})
                    self.assertEqual(status, 405)
                    self.assertNotIn("Access-Control-Allow-Origin", headers)
                    if route != CAP:
                        self.assertNotIn(token.encode(), raw)
        status, headers, _ = server.request("OPTIONS", "/ultra/chat/workspaces",
                                            {"Origin": "https://foreign.example", "Access-Control-Request-Method": "GET",
                                             "Access-Control-Request-Headers": HEADER})
        self.assertGreaterEqual(status, 400)
        self.assertNotIn("Access-Control-Allow-Origin", headers)


class DataTests(Base):
    def test_d1_workspaces_are_named_with_their_history_state_and_never_with_paths(self):
        server = self.start()
        ok_root, ok_id, _ = self.project(server, "alpha")
        _, bare_id, _ = self.project(server, "bare", history=False)
        gone_root, gone_id, _ = self.project(server, "gone")
        shutil.rmtree(gone_root)
        bad_root, bad_id, _ = self.project(server, "broken")
        (bad_root / ".ultra" / "workspace.json").write_text("{", encoding="utf-8")
        status, data = self.call(server, "/ultra/chat/workspaces")
        states = {w["wa_workspace_id"]: w["history"] for w in data["workspaces"]}
        self.assertEqual((status, data["state"]), (200, "ok"))
        self.assertEqual(states, {ok_id: "ok", bare_id: "missing_history", gone_id: "missing_path",
                                  bad_id: "invalid_metadata"})
        self.assertEqual({w["display_name"] for w in data["workspaces"]}, {"Alpha", "Bare", "Gone", "Broken"})
        self.assertFalse((self.base / "bare" / ".ultra").exists())
        self.assert_no_paths()

    def test_d2_chats_list_shows_damaged_and_link_entries_and_hides_foreign_ones(self):
        server = self.start()
        other_root, _, other_chat = self.project(server, "other")
        root, wa_id, good = self.project(server, "own")
        broken = cs.create_chat(root, "Сломан")["chat_id"]
        foreign = cs.create_chat(root, "Чужой")["chat_id"]  # before the damage: the Tk create_chat lists all chats (P1)
        (root / ".ultra" / "chats" / broken / "metadata.json").write_text("{", encoding="utf-8")
        meta = root / ".ultra" / "chats" / foreign / "metadata.json"
        meta.write_text(json.dumps({**json.loads(meta.read_text(encoding="utf-8")), "workspace_id": "ws_" + "f" * 32}),
                        encoding="utf-8")
        self.junction(other_root / ".ultra" / "chats" / other_chat, root / ".ultra" / "chats" / other_chat)
        status, data = self.call(server, f"/ultra/chat/workspaces/{wa_id}/chats")
        self.assertEqual((status, data["state"], data["display_name"]), (200, "ok", "Own"))
        self.assertEqual({c["chat_id"]: c["status"] for c in data["chats"]},
                         {good: "ok", broken: "damaged", other_chat: "unsafe_storage_link"})
        self.assertEqual(data["excluded"], {"foreign_identity": 1})
        _, bare_id, _ = self.project(server, "bare", history=False)
        status, data = self.call(server, f"/ultra/chat/workspaces/{bare_id}/chats")
        self.assertEqual((status, data["state"], data["reason"]), (200, "unavailable", "missing_history"))
        self.assert_no_paths()

    def test_d3_pages_walk_the_whole_history_once_and_bad_requests_stay_off_the_disk(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        written = [cs.append_raw_message(root, chat, "user" if n % 2 == 0 else "assistant", f"m{n}")["message_id"]
                   for n in range(7)]
        base = f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages"
        seen, before = [], None
        for _ in range(10):  # bounded: a broken cursor must fail the test, not hang it
            status, data = self.call(server, base + "?limit=3" + (f"&before={before}" if before else ""))
            self.assertEqual(status, 200)
            seen = [m["message_id"] for m in data["messages"]] + seen
            if not data["page"]["has_more"]:
                break
            before = data["page"]["next_before"]
        self.assertEqual(seen, written)
        self.assertEqual(data["total_messages"], 7)
        token = server.token()
        with patch.object(ultra_chat, "_core", side_effect=AssertionError("disk touched")):
            for path in (base + "?limit=0", base + "?limit=201", base + "?limit=x", base + "?before=../x",
                         base + "?limit=3&limit=4", base + "?foo=1", "/ultra/chat/workspaces/bad%2Fid/chats",
                         f"/ultra/chat/workspaces/{wa_id}/chats/chat_..%5C..%5Cx/messages",
                         f"/ultra/chat/workspaces/{wa_id}/chats/notachat/messages", "/ultra/chat/workspaces/?x"):
                with self.subTest(path=path[-24:]):
                    status, _, raw = server.request("GET", path, {HEADER: token})
                    self.assertIn(status, (400, 404))
        for path, code in ((base + "?before=msg_" + "0" * 32, "cursor_not_found"),
                           (f"/ultra/chat/workspaces/{wa_id}/chats/chat_{'a' * 32}/messages", "chat_not_found"),
                           (f"/ultra/chat/workspaces/ws_{'0' * 32}/chats", "unknown_workspace"),
                           ("/ultra/chat/unknown", "not_found")):
            with self.subTest(code=code):
                status, data = self.call(server, path, token)
                self.assertEqual((status, data["error"]["code"]), (404, code))

    def test_d4_legacy_outcomes_are_classified_without_rewriting_raw(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        ws = cs.read_workspace_identity_bounded(root)["workspace_id"]

        def block(user_text, answer, status, *, producer_run=False):
            tb = cs.new_task_block_id()
            run_id = "run_" + tb[3:15]
            cs.append_raw_message(root, chat, "user", user_text, task_block_id=tb)
            if status:
                run_store.create_run_summary(root, ws, chat, tb, run_id)
                run_store.update_run_summary_index(root, run_id, {"run_status": status})
            if answer is not None:
                producer = {"kind": "llm", "role_id": "main_chat", "run_id": run_id, "model_id": "m",
                            "model_display_name": "Model X", "provider": "p", "provider_model_id": "P"} if producer_run else None
                cs.append_raw_message(root, chat, "assistant", answer, task_block_id=tb, producer=producer)
        block("ok?", "fine", "SUCCESS", producer_run=True)
        block("tk failure", "RUN STATUS: FAILED\nRuntimeError: boom", "FAILED")
        block("failed by index", "partial text", "FAILED", producer_run=True)
        block("no answer", None, None)
        block("crashed", None, "RUNNING")
        cs.append_raw_message(root, chat, "assistant", "very old answer")
        cs.append_raw_message(root, chat, "assistant", "RUN STATUS: FAILED\nOSError: before Run Store existed")
        before = snapshot(root)
        status, data = self.call(server, f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages")
        self.assertEqual(snapshot(root), before)
        got = [(m["role"], m["outcome"], m.get("model")) for m in data["messages"]]
        self.assertEqual(got, [("user", "request", None), ("assistant", "completed", "Model X"),
                               ("user", "request", None), ("assistant", "failed", None),
                               ("user", "request", None), ("assistant", "failed", "Model X"),
                               ("user", "no_answer", None), ("user", "interrupted", None),
                               ("assistant", "legacy", None), ("assistant", "failed", None)])
        self.assertEqual(data["outcome_source"], "run_index")
        self.assertEqual(data["messages"][3]["text"], "RUN STATUS: FAILED\nRuntimeError: boom")

    def test_d5_partial_empty_too_large_and_unavailable_histories_are_told_apart(self):
        server = self.start()
        other_root, _, other_chat = self.project(server, "other")
        root, wa_id, chat = self.project(server, "p")
        empty = cs.create_chat(root, "Пусто")["chat_id"]
        linked = cs.create_chat(root, "Связан")["chat_id"]
        cs.append_raw_message(root, chat, "user", "<script>alert(1)</script>")
        (root / ".ultra" / "chats" / chat / "messages" / ("msg_" + "1" * 32 + ".json")).write_text("{", encoding="utf-8")
        shutil.rmtree(root / ".ultra" / "chats" / linked / "messages")
        self.junction(other_root / ".ultra" / "chats" / other_chat / "messages",
                      root / ".ultra" / "chats" / linked / "messages")
        url = f"/ultra/chat/workspaces/{wa_id}/chats/%s/messages"
        status, data = self.call(server, url % chat)
        self.assertEqual((data["history_state"], data["excluded"]), ("partial", {"damaged": 1}))
        self.assertEqual(data["messages"][0]["text"], "<script>alert(1)</script>")
        self.assertEqual(self.call(server, url % empty)[1]["history_state"], "empty")
        data = self.call(server, url % linked)[1]
        self.assertEqual((data["history_state"], data["reason"], data["messages"]), ("unavailable", "unsafe_storage_link", []))
        small = functools.partial(cs.read_chat_history_bounded, limits=cs.ReadLimits(max_message_files=1))
        with patch.object(cs, "read_chat_history_bounded", small):
            data = self.call(server, url % chat)[1]
        self.assertEqual((data["history_state"], data["reason"], data["messages"]), ("too_large", "history_too_large", []))
        self.assert_no_paths()

    def test_d6_page_is_cut_between_messages_at_the_byte_limit(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        ids = [cs.append_raw_message(root, chat, "user", "x" * 300)["message_id"] for _ in range(5)]
        big = cs.append_raw_message(root, chat, "user", "y" * 3000)["message_id"]
        url = f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages?limit=200"
        everything = ids + [big]
        with patch.object(ultra_chat, "MAX_PAGE_BYTES", 2000):
            status, headers, raw = server.request("GET", url, {HEADER: server.token()})
            data = json.loads(raw)
            returned = [m["message_id"] for m in data["messages"]]
            self.assertEqual(returned, everything[len(everything) - len(returned):], "not a contiguous newest tail")
            self.assertLess(len(returned), len(everything), "the byte limit did not cut the page")
            self.assertEqual(data["messages"][-1]["text"], None)
            self.assertEqual((data["messages"][-1]["too_large_for_page"], data["messages"][-1]["message_id"]), (True, big))
            self.assertGreater(data["messages"][-1]["size_bytes"], 2000)
            self.assertTrue(all(m["text"] == "x" * 300 for m in data["messages"][:-1]))
            self.assertLessEqual(len(raw), 2000 + 1024, "response grew past the page budget")
            self.assertEqual((data["page"]["has_more"], data["page"]["next_before"]), (True, returned[0]))
            seen, before = returned, returned[0]
            for _ in range(10):  # bounded: a broken cursor must fail the test, not hang it
                if not before:
                    break
                page = self.call(server, url + "&before=" + before)[1]
                seen = [m["message_id"] for m in page["messages"]] + seen
                before = page["page"]["next_before"]
            self.assertEqual(seen, everything)

    def test_d7_every_get_leaves_storage_and_workspaces_unchanged(self):
        server = self.start()
        other_root, _, other_chat = self.project(server, "other")
        root, wa_id, chat = self.project(server, "p")
        cs.append_raw_message(root, chat, "user", "text")
        self.junction(other_root / ".ultra" / "chats" / other_chat, root / ".ultra" / "chats" / other_chat)
        _, bare_id, _ = self.project(server, "bare", history=False)
        before = snapshot(self.base)
        token = server.token()
        for path in ("/ultra/chat/workspaces", f"/ultra/chat/workspaces/{wa_id}/chats", f"/ultra/chat/workspaces/{bare_id}/chats",
                     f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages", f"/ultra/chat/workspaces/{wa_id}/chats/{other_chat}/messages",
                     f"/ultra/chat/workspaces/{bare_id}/chats/{chat}/messages", "/ultra/chat/workspaces?x=1", CAP):
            server.request("GET", path, {HEADER: token})
        self.assertEqual(snapshot(self.base), before)

    def test_d8_adapter_imports_no_transport_and_core_errors_never_reach_the_browser(self):
        import ast
        tree = ast.parse((ROOT / "web_alarm" / "ultra_chat.py").read_text(encoding="utf-8"))
        imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imported |= {(node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(imported & {"gigachat_transport", "httpx", "socket", "requests", "urllib", "ultra_ui", "server",
                                     "model_registry", "os", "subprocess"}, set())
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "environ"])
        # Popen, not subprocess.run: setUp replaces subprocess.run to prove the native folder dialog never starts.
        probe = subprocess.Popen([sys.executable, "-B", "-c",
                                  "import sys, web_alarm.ultra_chat as m; m._core();"
                                  "print(sorted(n for n in ('gigachat_transport', 'httpx', 'ultra_ui', 'server') if n in sys.modules))"],
                                 cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = probe.communicate(timeout=60)
        self.assertEqual((probe.returncode, out.strip()), (0, "[]"), err[-400:])
        server = self.start()
        root, wa_id, _ = self.project(server, "p")
        secret = str(root) + "\\SECRET-PATH-IN-EXCEPTION"
        captured = io.StringIO()
        with patch.object(cs, "list_chats_bounded", side_effect=RuntimeError(secret)), contextlib.redirect_stderr(captured):
            status, _, raw = server.request("GET", f"/ultra/chat/workspaces/{wa_id}/chats", {HEADER: server.token()})
        self.assertEqual(status, 500)
        self.assertNotIn(b"SECRET-PATH", raw)
        self.assertNotIn(str(self.base).encode(), raw)

    def test_d9_token_appears_only_in_the_capability_answer(self):
        server = self.start()
        _, wa_id, chat = self.project(server, "p")
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            token = server.token()
            bodies = [server.request("GET", path)[2] for path in ("/", "/ui", "/status", "/ui/capabilities", "/ultra/connections",
                                                                  "/workspaces", "/ultra/chat/workspaces")]
            bodies += [server.request("GET", path, {HEADER: token})[2]
                       for path in ("/ultra/chat/workspaces", f"/ultra/chat/workspaces/{wa_id}/chats",
                                    f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages", "/ultra/chat/nope")]
            bodies.append(server.request("GET", "/ultra/chat/workspaces", {HEADER: token + "x"})[2])
        for index, raw in enumerate(bodies):
            with self.subTest(response=index):
                self.assertNotIn(token.encode(), raw)
        self.assertNotIn(token, captured.getvalue())

    def test_d10_reading_over_http_while_the_tk_writer_appends_in_another_process(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        child = ("import sys\nsys.path.insert(0, sys.argv[1])\nimport context_storage as cs\n"
                 "for n in range(40):\n    cs.append_raw_message(sys.argv[2], sys.argv[3], 'user', 'w%d' % n)\n")
        writer = subprocess.Popen([sys.executable, "-B", "-c", child, str(ROOT), str(root), chat],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        token, statuses, counts = server.token(), [], []
        url = f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages?limit=200"
        while writer.poll() is None:
            status, data = server.get(url, token)
            statuses.append(status)
            counts.append((data["history_state"], data["total_messages"]))
        _, err = writer.communicate(timeout=120)
        self.assertEqual(writer.returncode, 0, err[-400:])
        self.assertEqual(set(statuses) | {200}, {200})
        self.assertTrue(all(state in {"complete", "empty"} for state, _ in counts))
        self.assertEqual([n for _, n in counts], sorted(n for _, n in counts))
        self.assertEqual(server.get(url, token)[1]["total_messages"], 40)

    def run_block(self, root, chat, *, status, answer):
        ws = cs.read_workspace_identity_bounded(root)["workspace_id"]
        tb = cs.new_task_block_id()
        run_id = "run_" + tb[3:15]
        cs.append_raw_message(root, chat, "user", "q", task_block_id=tb)
        run_store.create_run_summary(root, ws, chat, tb, run_id)
        run_store.update_run_summary_index(root, run_id, {"run_status": status})
        producer = {"kind": "llm", "role_id": "main_chat", "run_id": run_id, "model_id": "m",
                    "model_display_name": "M", "provider": "p", "provider_model_id": "P"}
        cs.append_raw_message(root, chat, "assistant", answer, task_block_id=tb, producer=producer)
        return run_id

    def test_d11_damaged_or_oversized_run_index_leaves_history_readable(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        self.run_block(root, chat, status="FAILED", answer="RUN STATUS: FAILED\nRuntimeError: x")
        index = root / ".ultra" / "audit" / "index.json"
        url = f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages"
        for label, payload in (("damaged", b"{"), ("not an index", b"[]"),
                               ("oversized", b" " * (ultra_chat.MAX_RUN_INDEX_BYTES + 1))):
            with self.subTest(index=label):
                index.write_bytes(payload)
                status, data = self.call(server, url)
                self.assertEqual((status, data["history_state"], data["outcome_source"]),
                                 (200, "complete", "run_index_unavailable"))
                self.assertEqual([m["outcome"] for m in data["messages"]], ["request", "failed"],
                                 "the exact Tk marker must still mark the failure without the index")
        index.unlink()
        self.assertEqual(self.call(server, url)[1]["outcome_source"], "no_run_index")

    def test_d12_newer_index_generation_wins_as_in_run_store(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        run_id = self.run_block(root, chat, status="FAILED", answer="plain text answer")
        index = root / ".ultra" / "audit" / "index.json"
        value = json.loads(index.read_text(encoding="utf-8"))
        url = f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages"
        self.assertEqual(self.call(server, url)[1]["messages"][1]["outcome"], "failed")
        newer = {**value, "revision": value["revision"] + 1,
                 "runs": {**value["runs"], run_id: {**value["runs"][run_id], "run_status": "SUCCESS"}}}
        folder = root / ".ultra" / "audit" / "index_generations"
        folder.mkdir()
        (folder / f"index-{newer['revision']:020d}-{'a' * 32}.json").write_text(json.dumps(newer), encoding="utf-8")
        self.assertEqual(run_store.load_workspace_run_index(root)["runs"][run_id]["run_status"], "SUCCESS")
        data = self.call(server, url)[1]
        self.assertEqual((data["outcome_source"], data["messages"][1]["outcome"], data["messages"][1]["run_status"]),
                         ("run_index", "completed", "SUCCESS"))

    def assert_no_paths(self):
        for raw in self.bodies:
            self.assertNotIn(str(self.base).encode(), raw)
            self.assertNotIn(str(self.base).replace("\\", "\\\\").encode(), raw)
            self.assertNotIn(self.base.name.encode(), raw)


if __name__ == "__main__":
    unittest.main()
