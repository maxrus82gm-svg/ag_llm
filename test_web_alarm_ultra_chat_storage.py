"""Ultra Chat stage 2 over real HTTP: Chat create/rename through the shared writer (CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001).

The production create_server() and WebAlarmApi on disposable storage and Workspaces in TEMP. Checks the separate
write capability (never the read token), the local-origin gate, methods, sizes, registration, identity and
ownership, the absence of paths and tokens in answers, persistence after a server restart, and a concurrent Tk-style
writer in another process. Oracles are the files on disk, the stage-1 read routes and the Tk read functions.
Loopback only; no GigaChat, no credentials, no live data.
"""
from __future__ import annotations

import contextlib
import hashlib
import http.client
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as cs
from web_alarm import server as wa_server
from web_alarm import ultra_chat
from web_alarm.server import WebAlarmApi, build_parser, create_server

ROOT = Path(cs.__file__).resolve().parent
CAP = "/ui/ultra-chat/capability"
WCAP = "/ui/ultra-chat/write-capability"
READ = "X-WebAlarm-Ultra-Chat-Token"
WRITE = "X-WebAlarm-Ultra-Chat-Write-Token"


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
                    result[rel] = ("link",)
                elif entry.is_dir(follow_symlinks=False):
                    result[rel] = ("dir",)
                    stack.append(Path(entry.path))
                else:
                    result[rel] = ("file", st.st_size, st.st_mtime_ns, hashlib.sha256(Path(entry.path).read_bytes()).hexdigest())
    return result


def new_id(n: int) -> str:
    return "chat_" + f"{n:032x}"


class Server:
    def __init__(self, storage: Path, **kwargs):
        self.api = WebAlarmApi(storage)
        self.server = create_server(self.api, port=0, **kwargs)
        self.port = self.server.server_port
        self.host = f"127.0.0.1:{self.port}"
        self.origin = "http://" + self.host
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
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for key, value in [*sent.items(), *extra]:
                conn.putheader(key, value)
            if method in {"POST", "PUT", "PATCH", "DELETE"} and "Content-Length" not in omit:
                conn.putheader("Content-Length", str(len(body)))
            conn.endheaders(body if method in {"POST", "PUT", "PATCH", "DELETE"} else None)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def capability(self, path=WCAP, key="ultra_chat_write"):
        status, _, raw = self.request("GET", path)
        assert status == 200, status
        return json.loads(raw)[key]

    def read(self, path):
        status, _, raw = self.request("GET", path, {READ: self.capability(CAP, "ultra_chat")["token"]})
        return status, json.loads(raw)

    def post(self, path, payload, *, token=None, headers=None, omit=(), extra=(), raw_body=None):
        body = raw_body if raw_body is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sent = {"Origin": self.origin, "Content-Type": "application/json",
                WRITE: token if token is not None else self.capability()["token"], **(headers or {})}
        status, response_headers, raw = self.request("POST", path, sent, omit, extra, body)
        return status, response_headers, raw


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wa_s2_http_")).resolve()
        self.junctions: list[Path] = []
        self.children: list[subprocess.Popen] = []
        self.bodies: list[bytes] = []
        self.addCleanup(self._cleanup)
        patch("web_alarm.folder_picker.subprocess.run", side_effect=AssertionError("native folder dialog must not start")).start()
        self.addCleanup(patch.stopall)

    def _cleanup(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=30)
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

    def project(self, server: Server, name: str, *, history=True, title="Диалог"):
        root = self.base / name
        root.mkdir()
        chat = None
        if history:
            cs.ensure_workspace_storage(root)
            chat = cs.create_chat(root, title)["chat_id"]
        record = server.api.registry.register(name.capitalize(), root)
        return root, record.workspace_id, chat

    def junction(self, target: Path, link: Path) -> None:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        self.junctions.append(link)

    def post(self, server, path, payload, **kwargs):
        status, headers, raw = server.post(path, payload, **kwargs)
        self.bodies.append(raw)
        return status, json.loads(raw)

    def assert_no_leaks(self, *tokens):
        for raw in self.bodies:
            self.assertNotIn(str(self.base).encode(), raw)
            self.assertNotIn(str(self.base).replace("\\", "\\\\").encode(), raw)
            self.assertNotIn(self.base.name.encode(), raw)
            for token in tokens:
                self.assertNotIn(token.encode(), raw)


class CapabilityTests(Base):
    def test_w1_the_write_capability_is_separate_and_switchable(self):
        server = self.start()
        write, read = server.capability(), server.capability(CAP, "ultra_chat")
        self.assertEqual((write["available"], write["reason"], write["scope"], write["header"]),
                         (True, None, "ultra_chat_write", WRITE))
        self.assertGreaterEqual(len(write["token"]), 32)
        self.assertNotEqual(write["token"], read["token"])
        self.assertEqual(server.request("GET", WCAP)[1].get("Cache-Control"), "no-store")
        for label, kwargs, reason in (("write off", {"enable_ultra_chat_write": False}, "disabled"),
                                      ("reading off", {"enable_ultra_chat": False}, "disabled")):
            with self.subTest(case=label):
                off = self.start(label.replace(" ", "_"), **kwargs)
                value = off.capability()
                self.assertEqual((value["available"], value["reason"], value["token"]), (False, reason, None))
                _, wa_id, _ = self.project(off, "p_" + label.replace(" ", "_"))
                status, data = self.post(off, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(1)},
                                         token="x" * 43)
                self.assertEqual((status, data["error"]["code"]), (403, "ultra_chat_write_unavailable"))
        access = ultra_chat.UltraChatWriteAccess(enabled=True, loopback=False)
        self.assertEqual((access.capability()["available"], access.reason), (False, "non_loopback_bind"))
        self.assertTrue(build_parser().parse_args(["--disable-ultra-chat-write"]).disable_ultra_chat_write)
        seen = {}

        def fake_create_server(api, **kwargs):
            seen.update(kwargs)
            raise OSError("stop after capturing")
        with patch.object(wa_server, "create_server", fake_create_server), contextlib.redirect_stderr(io.StringIO()):
            wa_server.main(["--storage-root", str(self.base / "cli"), "--port", "0", "--disable-ultra-chat-write"])
        self.assertEqual((seen.get("enable_ultra_chat"), seen.get("enable_ultra_chat_write")), (True, False))

    def test_w2_tokens_never_cross_scopes(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        read, write = server.capability(CAP, "ultra_chat")["token"], server.capability()["token"]
        before = snapshot(root)
        for label, headers, omit in (("read token as write", {WRITE: read}, ()), ("no write token", {}, (WRITE,)),
                                     ("read token in read header only", {READ: read}, (WRITE,)),
                                     ("wrong write token", {WRITE: write[:-1] + ("A" if write[-1] != "A" else "B")}, ())):
            with self.subTest(case=label):
                sent = dict(headers)
                status, data = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(1)},
                                         token=sent.pop(WRITE, write), headers=sent, omit=omit)
                self.assertEqual(status, 403)
                self.assertIn(data["error"]["code"], {"ultra_chat_write_token_invalid"})
        status, _ = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(1)},
                              extra=((WRITE, write),))
        self.assertEqual(status, 403, "two write tokens")
        status, _, raw = server.request("GET", "/ultra/chat/workspaces", {READ: write})
        self.assertEqual((status, json.loads(raw)["error"]["code"]), (403, "ultra_chat_token_invalid"),
                         "the write token never reads history")
        self.assertEqual(snapshot(root), before)
        self.assert_no_leaks(read, write)


class WriteTests(Base):
    def test_w3_create_and_rename_are_seen_by_the_web_the_core_and_the_tk_readers_and_survive_a_restart(self):
        server = self.start()
        root, wa_id, first = self.project(server, "p")
        url = f"/ultra/chat/workspaces/{wa_id}/chats"
        status, data = self.post(server, url, {"chat_id": new_id(1), "title": "  Из веба  "})
        self.assertEqual((status, data["created"], data["chat"]["chat_id"], data["chat"]["title"], data["chat"]["status"]),
                         (201, True, new_id(1), "Из веба", "ok"))
        status, data = self.post(server, url, {"chat_id": new_id(2)})
        self.assertEqual((status, data["chat"]["title"]), (201, "Чат 1"), "an empty title gets the next free «Чат N»")
        status, again = self.post(server, url, {"chat_id": new_id(1), "title": "Из веба"})
        self.assertEqual((status, again["created"]), (200, False), "a repeated request creates nothing")
        status, data = self.post(server, url, {"chat_id": new_id(1), "title": "Иначе"})
        self.assertEqual((status, data["error"]["code"]), (409, "chat_id_conflict"))
        status, data = self.post(server, f"{url}/{new_id(1)}/title", {"title": "Переименован", "expected_title": "Из веба"})
        self.assertEqual((status, data["chat"]["title"]), (200, "Переименован"))
        card = json.loads((root / ".ultra" / "chats" / new_id(1) / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual((card["title"], card["workspace_id"], card["chat_id"]),
                         ("Переименован", cs.read_workspace_identity_bounded(root)["workspace_id"], new_id(1)))
        expected = {first: "Диалог", new_id(1): "Переименован", new_id(2): "Чат 1"}
        listing = server.read(url)[1]
        self.assertEqual({c["chat_id"]: c["title"] for c in listing["chats"]}, expected)
        self.assertEqual({c["chat_id"]: c["title"] for c in cs.list_existing_chats(root)}, expected, "the Tk listing")
        self.assertEqual(cs.load_chat_messages(root, new_id(1)), [])
        self.assertEqual(len(list((root / ".ultra" / "chats").iterdir())), 3)
        server.stop()
        again = self.start("storage")  # a new process of the same storage: new tokens, the same data
        listing = again.read(url)[1]
        self.assertEqual({c["chat_id"]: c["title"] for c in listing["chats"]}, expected)
        self.assert_no_leaks()

    def test_w4_rename_refuses_a_stale_title_and_a_repeat_is_free(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        url = f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/title"
        cs.rename_chat(root, chat, "Из Tk")  # renamed in the Tk window meanwhile
        card = root / ".ultra" / "chats" / chat / "metadata.json"
        raw = card.read_bytes()
        status, data = self.post(server, url, {"title": "Из веба", "expected_title": "Диалог"})
        self.assertEqual((status, data["error"]["code"]), (409, "title_changed"))
        self.assertEqual(card.read_bytes(), raw)
        status, data = self.post(server, url, {"title": "Из веба", "expected_title": "Из Tk"})
        self.assertEqual(status, 200)
        raw, mtime = card.read_bytes(), os.lstat(card).st_mtime_ns
        status, data = self.post(server, url, {"title": "Из веба", "expected_title": "Из Tk"})
        self.assertEqual((status, data["chat"]["title"]), (200, "Из веба"))
        self.assertEqual((card.read_bytes(), os.lstat(card).st_mtime_ns), (raw, mtime), "a repeat writes nothing")

    def test_w5_raw_of_the_shared_writer_reaches_the_web_byte_exact(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        texts = ["<script>alert(1)</script>\r\n\t«ёж» 😀", "x" * (1024 * 1024), "  пробелы по краям  "]
        ids = []
        for n, text in enumerate(texts):
            message_id = "msg_" + f"{n + 1:032x}"
            ids.append(cs.commit_raw_message(root, chat, message_id, "user", text)["message_id"])
            self.assertFalse(cs.commit_raw_message(root, chat, message_id, "user", text)["created"])
        before = snapshot(root)
        status, data = server.read(f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/messages?limit=200")
        self.assertEqual(status, 200)
        self.assertEqual([(m["message_id"], m["text"]) for m in data["messages"]], list(zip(ids, texts)))
        self.assertEqual(snapshot(root), before, "reading changed the storage")

    def test_w6_registration_identity_and_ownership_are_checked_and_nothing_is_created(self):
        server = self.start()
        other_root, _, other_chat = self.project(server, "other")
        root, wa_id, chat = self.project(server, "own")
        bare_root, bare_id, _ = self.project(server, "bare", history=False)
        linked_root = self.base / "linked"
        linked_root.mkdir()
        self.junction(other_root / ".ultra", linked_root / ".ultra")
        linked_id = server.api.registry.register("Linked", linked_root).workspace_id
        before = snapshot(self.base / "own")
        cases = [
            ("unknown workspace", f"/ultra/chat/workspaces/ws_{'0' * 32}/chats", {"chat_id": new_id(1)}, 404, "unknown_workspace", None),
            ("no history", f"/ultra/chat/workspaces/{bare_id}/chats", {"chat_id": new_id(1)}, 409, "workspace_unavailable", "missing_history"),
            ("linked storage", f"/ultra/chat/workspaces/{linked_id}/chats", {"chat_id": new_id(1)}, 409, "workspace_unavailable", "unsafe_storage_link"),
            ("chat of another workspace", f"/ultra/chat/workspaces/{wa_id}/chats/{other_chat}/title", {"title": "x", "expected_title": "Диалог"}, 404, "chat_not_found", None),
            ("unknown chat", f"/ultra/chat/workspaces/{wa_id}/chats/{new_id(9)}/title", {"title": "x", "expected_title": "y"}, 404, "chat_not_found", None),
        ]
        for label, url, payload, status_expected, code, reason in cases:
            with self.subTest(case=label):
                status, data = self.post(server, url, payload)
                self.assertEqual((status, data["error"]["code"]), (status_expected, code))
                self.assertEqual((data["error"].get("details") or {}).get("reason"), reason)
        self.assertEqual(list(bare_root.iterdir()), [], "nothing is created in a folder without history")
        self.assertEqual(snapshot(self.base / "own"), before)
        card = root / ".ultra" / "chats" / chat / "metadata.json"
        data = json.loads(card.read_text(encoding="utf-8"))
        meta = root / ".ultra" / "workspace.json"
        for label, change, code in (("foreign card", lambda: card.write_text(json.dumps({**data, "workspace_id": "ws_" + "e" * 32}), encoding="utf-8"), "foreign_identity"),
                                    ("damaged card", lambda: card.write_text("{", encoding="utf-8"), "chat_damaged"),
                                    ("newer card", lambda: card.write_text(json.dumps({**data, "schema_version": 2}), encoding="utf-8"), "unsupported_version")):
            with self.subTest(case=label):
                change()
                status, answer = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/title", {"title": "x", "expected_title": "Диалог"})
                self.assertEqual((status, answer["error"]["code"]), (409, code))
        card.write_text(json.dumps(data), encoding="utf-8")
        meta_raw = meta.read_bytes()
        meta.write_text(json.dumps({**json.loads(meta_raw), "schema_version": 2}), encoding="utf-8")
        status, answer = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(3)})
        self.assertEqual((status, answer["error"]["code"], answer["error"]["details"]["reason"]),
                         (409, "workspace_unavailable", "unsupported_version"))
        meta.write_bytes(meta_raw)
        with patch.object(cs, "MAX_CHATS_PER_WORKSPACE", 1):
            status, answer = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(4)})
        self.assertEqual((status, answer["error"]["code"]), (409, "chats_limit_reached"))
        self.assertFalse((root / ".ultra" / "chats" / new_id(4)).exists())
        self.assert_no_leaks()

    def test_w7_requests_are_refused_by_origin_method_size_type_and_shape_before_any_disk_access(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        create, rename = f"/ultra/chat/workspaces/{wa_id}/chats", f"/ultra/chat/workspaces/{wa_id}/chats/{chat}/title"
        token = server.capability()["token"]
        before = snapshot(self.base)
        port = str(server.port)
        refusals = [
            ("foreign origin", create, {"chat_id": new_id(1)}, {"headers": {"Origin": "https://foreign.example"}}, 403),
            ("null origin", create, {"chat_id": new_id(1)}, {"headers": {"Origin": "null"}}, 403),
            ("no origin", create, {"chat_id": new_id(1)}, {"omit": ("Origin",)}, 403),
            ("two origins", create, {"chat_id": new_id(1)}, {"extra": (("Origin", server.origin),)}, 403),
            ("foreign host", create, {"chat_id": new_id(1)}, {"headers": {"Host": "foreign.example:" + port, "Origin": "http://foreign.example:" + port}}, 403),
            ("cross-site", create, {"chat_id": new_id(1)}, {"headers": {"Sec-Fetch-Site": "cross-site"}}, 403),
            ("query", create + "?x=1", {"chat_id": new_id(1)}, {}, 400),
            ("text body", create, {"chat_id": new_id(1)}, {"headers": {"Content-Type": "text/plain"}}, 415),
            ("too large", create, None, {"raw_body": b"{" + b" " * 5000 + b"}"}, 413),
            ("not json", create, None, {"raw_body": b"{chat"}, 400),
            ("not utf8", create, None, {"raw_body": b"\xff\xfe"}, 400),
            ("array", create, None, {"raw_body": b"[]"}, 400),
            ("unknown key", create, {"chat_id": new_id(1), "path": "C:/x"}, {}, 400),
            ("no chat id", create, {"title": "x"}, {}, 400),
            ("upper hex", create, {"chat_id": "chat_" + "A" * 32}, {}, 400),
            ("short id", create, {"chat_id": "chat_" + "a" * 16}, {}, 400),
            ("traversal id", create, {"chat_id": "chat_../../x"}, {}, 400),
            ("title type", create, {"chat_id": new_id(1), "title": 5}, {}, 400),
            ("newline title", create, {"chat_id": new_id(1), "title": "a\nb"}, {}, 400),
            ("long title", create, {"chat_id": new_id(1), "title": "я" * 201}, {}, 400),
            ("rename without expected", rename, {"title": "x"}, {}, 400),
            ("rename empty", rename, {"title": "  ", "expected_title": "Диалог"}, {}, 400),
            ("bad chat in path", f"/ultra/chat/workspaces/{wa_id}/chats/chat_..%5Cx/title", {"title": "x", "expected_title": "y"}, {}, 400),
            ("bad workspace in path", "/ultra/chat/workspaces/bad%2Fid/chats", {"chat_id": new_id(1)}, {}, 400),
        ]
        for label, url, payload, kwargs, status_expected in refusals:
            with self.subTest(case=label):
                status, data = self.post(server, url, payload, token=token, **kwargs)
                self.assertEqual(status, status_expected, data)
        for method in ("PUT", "PATCH", "DELETE", "GET"):
            for url in (create.replace("/chats", "/chats/" + chat + "/title"), "/ultra/chat/workspaces", CAP, WCAP):
                if method == "GET" and url in {"/ultra/chat/workspaces", CAP, WCAP}:
                    continue
                with self.subTest(method=method, route=url.split("/")[-1]):
                    status, headers, raw = server.request(method, url, {"Origin": server.origin, WRITE: token,
                                                                        "Content-Type": "application/json"}, body=b"{}")
                    self.assertEqual(status, 405)
                    self.assertNotIn("Access-Control-Allow-Origin", headers)
                    self.bodies.append(raw)
        for url in (CAP, WCAP, "/ultra/chat/workspaces"):
            with self.subTest(post_to=url.split("/")[-1]):
                status, _, raw = server.request("POST", url, {"Origin": server.origin, WRITE: token}, body=b"{}")
                self.assertEqual(status, 405)
        with patch.object(ultra_chat, "_core", side_effect=AssertionError("disk touched")):
            for label, url, payload in (("query", create + "?a=b", {"chat_id": new_id(1)}),
                                        ("bad id", "/ultra/chat/workspaces/bad%2Fid/chats", {"chat_id": new_id(1)}),
                                        ("no token", create, {"chat_id": new_id(1)})):
                with self.subTest(no_disk=label):
                    status, _ = self.post(server, url, payload, token="" if label == "no token" else token)
                    self.assertIn(status, (400, 403))
        self.assertEqual(snapshot(self.base), before)
        self.assert_no_leaks(token)

    def test_w8_core_failures_reach_the_page_as_codes_without_paths(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        url = f"/ultra/chat/workspaces/{wa_id}/chats"
        secret = str(root) + "\\SECRET-PATH"
        for label, error, status_expected, code in (
                ("disk", OSError(28, "No space left " + secret), 503, "storage_write_failed"),
                ("busy", cs.WorkspaceBusyError(), 503, "workspace_busy"),
                ("unknown write code", cs.StorageWriteError("verify_failed", secret), 503, "storage_write_failed"),
                ("unexpected", RuntimeError(secret), 500, "internal_error")):
            with self.subTest(case=label):
                with patch.object(cs, "create_chat_record", side_effect=error), contextlib.redirect_stderr(io.StringIO()):
                    status, data = self.post(server, url, {"chat_id": new_id(1)})
                self.assertEqual((status, data["error"]["code"]), (status_expected, code))
        self.assert_no_leaks()


class ConcurrencyTests(Base):
    def test_w9_web_and_a_tk_writer_in_another_process_lose_nothing(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        go = self.base / "go"
        child = ("import sys, time\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport context_storage as cs\n"
                 "go = Path(sys.argv[4])\nwhile not go.exists():\n    time.sleep(0.002)\n"
                 "for n in range(30):\n    cs.append_raw_message(sys.argv[2], sys.argv[3], 'user', 'tk%d' % n)\n"
                 "    if n % 6 == 0:\n        cs.create_chat(sys.argv[2])\n"
                 "    if n % 5 == 0:\n        cs.rename_chat(sys.argv[2], sys.argv[3], 'tk-%d' % n)\n")
        writer = subprocess.Popen([sys.executable, "-B", "-c", child, str(ROOT), str(root), chat, str(go)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.children.append(writer)
        token = server.capability()["token"]
        url = f"/ultra/chat/workspaces/{wa_id}/chats"
        go.write_text("1")
        statuses = []
        for n in range(12):
            status, _ = self.post(server, url, {"chat_id": new_id(100 + n)}, token=token)
            statuses.append(status)
            if n % 3 == 0:
                status, data = self.post(server, f"{url}/{new_id(100 + n)}/title",
                                         {"title": f"web-{n}", "expected_title": data_title(root, new_id(100 + n))}, token=token)
                statuses.append(status)
        _, err = writer.communicate(timeout=180)
        self.assertEqual(writer.returncode, 0, err[-600:])
        self.assertEqual(set(statuses), {200, 201})
        messages = root / ".ultra" / "chats" / chat / "messages"
        texts = sorted(json.loads(p.read_text(encoding="utf-8"))["original_text"] for p in messages.iterdir())
        self.assertEqual(texts, sorted(f"tk{n}" for n in range(30)), "a Tk RAW was lost")
        cards = {p.name: json.loads((p / "metadata.json").read_text(encoding="utf-8")) for p in (root / ".ultra" / "chats").iterdir()}
        self.assertEqual(len(cards), 1 + 12 + 5)
        titles = [c["title"] for c in cards.values()]
        self.assertEqual(len(titles), len(set(titles)), "two writers chose the same default title")
        self.assertEqual([cards[new_id(100 + n)]["title"] for n in (0, 3, 6, 9)], ["web-0", "web-3", "web-6", "web-9"])
        self.assertEqual(sorted(str(p) for p in (root / ".ultra").rglob("*.tmp")), [])
        listing = server.read(url)[1]
        self.assertEqual((listing["state"], len(listing["chats"]), listing["excluded"]), ("ok", 18, {}))

    def test_w10_a_busy_workspace_is_a_visible_refusal_and_nothing_is_written(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        held = self.base / "held"
        hold = ("import sys, time\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport context_storage as cs\n"
                "with cs._workspace_writer_lock(cs._write_anchor(Path(sys.argv[2]))):\n"
                "    open(sys.argv[3], 'w').close()\n    time.sleep(60)\n")
        holder = subprocess.Popen([sys.executable, "-B", "-c", hold, str(ROOT), str(root), str(held)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.children.append(holder)
        deadline = time.monotonic() + 60
        while not held.exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        before = snapshot(root)
        with patch.object(cs, "WRITER_LOCK_TIMEOUT_SECONDS", 0.3):
            status, data = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(1)})
        self.assertEqual((status, data["error"]["code"]), (503, "workspace_busy"))
        self.assertEqual(snapshot(root), before)
        holder.kill()
        holder.communicate(timeout=30)
        status, _ = self.post(server, f"/ultra/chat/workspaces/{wa_id}/chats", {"chat_id": new_id(1)})
        self.assertEqual(status, 201, "the same request succeeds once the holder is gone")


class PortabilityTests(Base):
    def test_w11_a_copied_workspace_registered_anew_keeps_its_ids_and_history(self):
        server = self.start()
        root, wa_id, chat = self.project(server, "p")
        cs.commit_raw_message(root, chat, "msg_" + "1" * 32, "user", "до копии")
        copy = self.base / "copy"
        shutil.copytree(root, copy)
        copy_id = server.api.registry.register("Copy", copy).workspace_id
        original, copied = (server.read(f"/ultra/chat/workspaces/{w}/chats/{chat}/messages")[1] for w in (wa_id, copy_id))
        self.assertEqual((copied["chat"], copied["messages"]), (original["chat"], original["messages"]))
        before = snapshot(root)
        status, _ = self.post(server, f"/ultra/chat/workspaces/{copy_id}/chats", {"chat_id": new_id(7), "title": "В копии"})
        self.assertEqual(status, 201)
        self.assertEqual(snapshot(root), before, "a write to the copy changed the original")
        self.assertTrue((copy / ".ultra" / "chats" / new_id(7)).is_dir())


def data_title(root: Path, chat_id: str) -> str:
    return json.loads((root / ".ultra" / "chats" / chat_id / "metadata.json").read_text(encoding="utf-8"))["title"]


if __name__ == "__main__":
    unittest.main()
