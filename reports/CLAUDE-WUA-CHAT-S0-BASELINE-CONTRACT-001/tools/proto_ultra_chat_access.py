"""Isolated prototype of the Ultra Chat read capability (amendment to stage 0) and its HTTP test matrix.

NOT production code. It shows that the proposed boundary can be built on the existing Web Alarm handler without the
Windows folder picker, and fixes the tests stage 1 must pass. Part A records the current behaviour that motivated
the amendment: /ui/capabilities hands out a token only when the folder picker is available, which is off by default.
Part B swaps the request handler class of a real create_server() instance for a subclass that adds
GET /ui/ultra-chat/capability and GET /ultra/chat/* behind the same local-origin rules as the folder picker plus an
own token in its own header. The history route returns a synthetic marker; no storage, no network beyond loopback,
storage of WebAlarmApi only in TEMP. Run under the guarded runner (wa4a_acceptance.py via run_gate.py).
"""
from __future__ import annotations

import contextlib
import http.client
import io
import ipaddress
import json
import secrets
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from web_alarm.server import LOOPBACK_HOSTS, ApiError, WebAlarmApi, _JsonHandler, create_server

CAPABILITY_PATH = "/ui/ultra-chat/capability"
TOKEN_HEADER = "X-WebAlarm-Ultra-Chat-Token"
FOLDER_HEADER = "X-WebAlarm-Folder-Token"
MARKER = "SYNTHETIC-PRIVATE-HISTORY-MARKER"


class UltraChatAccess:
    """One scope: GET /ultra/chat/* of this server process. Token lives in memory only, new on every start."""

    def __init__(self, *, enabled: bool, bound_host: str) -> None:
        self.reason = None if enabled and bound_host in LOOPBACK_HOSTS else (
            "disabled" if not enabled else "non_loopback_bind")
        self._token = secrets.token_urlsafe(32) if self.reason is None else None

    def capability(self) -> dict:
        return {"available": self._token is not None, "reason": self.reason, "scope": "ultra_chat_read",
                "header": TOKEN_HEADER, "token": self._token}

    def require(self, headers) -> None:
        if self._token is None:
            raise ApiError(403, "ultra_chat_unavailable", "Ultra Chat reading is not available on this server")
        values = headers.get_all(TOKEN_HEADER, [])
        if (len(values) != 1 or not values[0] or len(values[0]) > 200 or not values[0].isascii()
                or not secrets.compare_digest(values[0], self._token)):
            raise ApiError(403, "ultra_chat_token_invalid", "A valid Ultra Chat read capability is required")


def require_local_ui_origin(handler) -> str:
    """Same rules as the folder picker gate (web_alarm/server.py, _folder_picker_request); stage 1 extracts one helper."""
    port = handler.server.server_port
    hosts = handler.headers.get_all("Host", [])
    peer = ipaddress.ip_address(handler.client_address[0])
    bound = ipaddress.ip_address(handler.server.server_address[0])
    if (not peer.is_loopback or not bound.is_loopback or len(hosts) != 1
            or hosts[0] not in {f"127.0.0.1:{port}", f"localhost:{port}"}):
        raise ApiError(403, "ultra_chat_forbidden", "Ultra Chat requires its exact local origin")
    origins = handler.headers.get_all("Origin", [])
    sites = handler.headers.get_all("Sec-Fetch-Site", [])
    if (len(origins) > 1 or (origins and origins[0] != "http://" + hosts[0])
            or len(sites) > 1 or (sites and sites[0] not in {"same-origin", "none"})):
        raise ApiError(403, "ultra_chat_forbidden", "Foreign or opaque origins are not allowed")
    return hosts[0]


class PrototypeHandler(_JsonHandler):
    def _run(self) -> None:
        path = urlsplit(self.path).path
        if path == CAPABILITY_PATH or path.startswith("/ultra/chat/"):
            try:
                self._ultra_chat(path)
            except ApiError as exc:
                self._send_json(exc.status, {"error": {"code": exc.code, "message": exc.message}})
            return
        super()._run()

    def _ultra_chat(self, path: str) -> None:
        require_local_ui_origin(self)
        if self.command != "GET":
            raise ApiError(405, "method_not_allowed", "Ultra Chat reading is GET only")
        query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
        access = self.server.ultra_chat_access
        if path == CAPABILITY_PATH:
            if query:
                raise ApiError(400, "invalid_ultra_chat_request", "Query parameters are not supported")
            self._send_json(200, {"ultra_chat": access.capability()})
            return
        if set(query) - {"before", "limit"} or any(len(v) != 1 for v in query.values()):
            raise ApiError(400, "invalid_ultra_chat_request", "Unsupported query parameters")
        access.require(self.headers)
        self._send_json(200, {"history_state": "complete", "messages": [{"role": "user", "text": MARKER}]})


class Server:
    def __init__(self, root: Path, *, picker: bool, ultra_chat: bool = True, prototype: bool = True):
        self.api = WebAlarmApi(root)
        self.server = create_server(self.api, port=0, enable_folder_picker=picker)
        if prototype:
            self.server.RequestHandlerClass = PrototypeHandler
            self.server.ultra_chat_access = UltraChatAccess(enabled=ultra_chat, bound_host="127.0.0.1")
        self.port = self.server.server_port
        self.host = f"127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)

    def request(self, method, path, headers=None, omit=(), extra=(), body=b""):
        sent = {"Host": self.host}
        sent.update(headers or {})
        for key in omit:
            sent.pop(key, None)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for key, value in [*sent.items(), *extra]:
                conn.putheader(key, value)
            if method in {"POST", "PUT", "PATCH"}:
                conn.putheader("Content-Length", str(len(body)))
            conn.endheaders(body if method in {"POST", "PUT", "PATCH"} else None)
            response = conn.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), raw
        finally:
            conn.close()

    def ultra_token(self):
        status, _, raw = self.request("GET", CAPABILITY_PATH)
        assert status == 200, status
        return json.loads(raw)["ultra_chat"]["token"]


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wa_s0_gate_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.native = patch("web_alarm.folder_picker.subprocess.run",
                            side_effect=AssertionError("native folder dialog must not start")).start()
        self.addCleanup(patch.stopall)

    def start(self, name, **kwargs):
        server = Server(self.root / name, **kwargs)
        self.addCleanup(server.stop)
        return server

    @staticmethod
    def picker_available(server):
        patch.object(server.server.web_alarm_folder_picker, "capabilities",
                     return_value={"available": True, "reason": None}).start()

    def assert_denied(self, status, raw, *secrets_):
        self.assertIn(status, (400, 403, 405))
        self.assertNotIn(MARKER.encode(), raw)
        for value in secrets_:
            if value:
                self.assertNotIn(value.encode(), raw)


class CurrentBehaviour(Base):
    def test_a1_existing_capabilities_hide_the_token_while_the_folder_picker_is_off_by_default(self):
        server = self.start("default", picker=False, prototype=False)
        status, _, raw = server.request("GET", "/ui/capabilities")
        value = json.loads(raw)["folder_picker"]
        self.assertEqual((status, value["available"], value["token"]), (200, False, None))

    def test_a2_existing_capabilities_hand_out_the_folder_token_only_when_the_picker_is_available(self):
        server = self.start("picker", picker=True, prototype=False)
        self.picker_available(server)
        value = json.loads(server.request("GET", "/ui/capabilities")[2])["folder_picker"]
        self.assertEqual(value["token"], server.server.web_alarm_folder_picker.token)


class Independence(Base):
    def test_b1_read_capability_exists_with_the_folder_picker_off_and_on(self):
        for picker in (False, True):
            with self.subTest(picker=picker):
                server = self.start(f"p{int(picker)}", picker=picker)
                if picker:
                    self.picker_available(server)
                status, headers, raw = server.request("GET", CAPABILITY_PATH)
                value = json.loads(raw)["ultra_chat"]
                self.assertEqual((status, value["available"], value["scope"]), (200, True, "ultra_chat_read"))
                self.assertEqual(headers.get("Cache-Control"), "no-store")
                status, _, raw = server.request("GET", "/ultra/chat/workspaces", {TOKEN_HEADER: value["token"]})
                self.assertEqual(status, 200)
                self.assertIn(MARKER.encode(), raw)
                folder = json.loads(server.request("GET", "/ui/capabilities")[2])["folder_picker"]["token"]
                self.assertEqual(folder is None, not picker)
                self.assertNotEqual(folder, value["token"])

    def test_b2_tokens_never_cross_scopes(self):
        server = self.start("both", picker=True)
        self.picker_available(server)
        ultra, folder = server.ultra_token(), server.server.web_alarm_folder_picker.token
        for label, headers in (("folder token in chat header", {TOKEN_HEADER: folder}),
                               ("folder token in folder header", {FOLDER_HEADER: folder}),
                               ("chat token in folder header", {FOLDER_HEADER: ultra})):
            with self.subTest(case=label):
                self.assert_denied(*server.request("GET", "/ultra/chat/workspaces", headers)[::2])
        status, _, raw = server.request("POST", "/ui/pick-workspace-folder",
                                        {"Origin": "http://" + server.host, "Content-Type": "application/json",
                                         FOLDER_HEADER: ultra}, body=b"{}")
        self.assertEqual(status, 403)
        self.native.assert_not_called()

    def test_b3_switching_chat_reading_off_leaves_the_folder_picker_alone(self):
        server = self.start("off", picker=True, ultra_chat=False)
        self.picker_available(server)
        value = json.loads(server.request("GET", CAPABILITY_PATH)[2])["ultra_chat"]
        self.assertEqual((value["available"], value["reason"], value["token"]), (False, "disabled", None))
        stale = secrets.token_urlsafe(32)
        self.assertEqual(server.request("GET", "/ultra/chat/workspaces", {TOKEN_HEADER: stale})[0], 403)
        folder = json.loads(server.request("GET", "/ui/capabilities")[2])["folder_picker"]
        self.assertEqual(folder["token"], server.server.web_alarm_folder_picker.token)

    def test_b4_non_loopback_bind_gives_no_capability_and_no_history(self):
        access = UltraChatAccess(enabled=True, bound_host="0.0.0.0")
        self.assertEqual((access.capability()["available"], access.reason), (False, "non_loopback_bind"))
        server = self.start("remote", picker=False)
        token = server.ultra_token()
        address = server.server.server_address
        try:
            server.server.server_address = ("0.0.0.0", address[1])
            self.assert_denied(*server.request("GET", CAPABILITY_PATH)[::2], token)
            self.assert_denied(*server.request("GET", "/ultra/chat/workspaces", {TOKEN_HEADER: token})[::2])
        finally:
            server.server.server_address = address


class TokenChecks(Base):
    def test_c1_invalid_tokens_are_refused(self):
        server = self.start("tokens", picker=False)
        token = server.ultra_token()
        other = self.start("other", picker=False).ultra_token()
        cases = [("missing", {}, ()), ("empty", {TOKEN_HEADER: ""}, ()),
                 ("wrong same length", {TOKEN_HEADER: ("A" if token[0] != "A" else "B") + token[1:]}, ()),
                 ("wrong short", {TOKEN_HEADER: "wrong"}, ()), ("non ascii", {TOKEN_HEADER: token[:-1] + "é"}, ()),
                 ("too long", {TOKEN_HEADER: token + "x" * 200}, ()),
                 ("two valid headers", {TOKEN_HEADER: token}, ((TOKEN_HEADER, token),)),
                 ("valid and wrong headers", {TOKEN_HEADER: token}, ((TOKEN_HEADER, "wrong"),)),
                 ("token of another server process", {TOKEN_HEADER: other}, ()),
                 ("token as cookie", {"Cookie": f"{TOKEN_HEADER}={token}"}, ())]
        for label, headers, extra in cases:
            with self.subTest(case=label):
                self.assert_denied(*server.request("GET", "/ultra/chat/workspaces", headers, extra=extra)[::2])
        status, _, raw = server.request("GET", "/ultra/chat/workspaces?token=" + token)
        self.assertEqual(status, 400)
        self.assert_denied(status, raw)
        self.assertEqual(server.request("GET", "/ultra/chat/workspaces?limit=50", {TOKEN_HEADER: token})[0], 200)


class OriginChecks(Base):
    def test_d1_foreign_or_opaque_origin_is_refused_on_capability_and_history(self):
        server = self.start("origin", picker=False)
        token = server.ultra_token()
        port, origin = str(server.port), "http://" + server.host
        cases = [("foreign host", {"Host": "foreign.example:" + port}, (), ()), ("other port", {"Host": "127.0.0.1:1"}, (), ()),
                 ("no host", {}, ("Host",), ()), ("two hosts", {}, (), (("Host", "foreign.example"),)),
                 ("foreign origin", {"Origin": "https://foreign.example"}, (), ()), ("null origin", {"Origin": "null"}, (), ()),
                 ("origin with slash", {"Origin": origin + "/"}, (), ()), ("two origins", {"Origin": origin}, (), (("Origin", origin),)),
                 ("cross-site", {"Sec-Fetch-Site": "cross-site"}, (), ()), ("same-site", {"Sec-Fetch-Site": "same-site"}, (), ()),
                 ("two fetch sites", {"Sec-Fetch-Site": "same-origin"}, (), (("Sec-Fetch-Site", "cross-site"),))]
        for route, base in ((CAPABILITY_PATH, {}), ("/ultra/chat/workspaces", {TOKEN_HEADER: token})):
            for label, change, omit, extra in cases:
                with self.subTest(route=route.rsplit("/", 1)[-1], case=label):
                    self.assert_denied(*server.request("GET", route, {**base, **change}, omit, extra)[::2], token)

    def test_d2_normal_same_origin_reads_pass(self):
        server = self.start("same", picker=False)
        token = server.ultra_token()
        for label, headers in (("localhost host", {"Host": "localhost:" + str(server.port)}),
                               ("fetch metadata only", {"Sec-Fetch-Site": "same-origin"}),
                               ("exact origin", {"Origin": "http://" + server.host})):
            with self.subTest(case=label):
                self.assertEqual(server.request("GET", "/ultra/chat/workspaces", {TOKEN_HEADER: token, **headers})[0], 200)

    def test_d3_other_methods_and_preflight_are_refused_without_cors(self):
        server = self.start("methods", picker=False)
        token = server.ultra_token()
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            for route in (CAPABILITY_PATH, "/ultra/chat/workspaces"):
                with self.subTest(method=method, route=route.rsplit("/", 1)[-1]):
                    status, headers, raw = server.request(method, route, {TOKEN_HEADER: token})
                    self.assertEqual(status, 405)
                    self.assert_denied(status, raw, token if route != CAPABILITY_PATH else None)
                    self.assertNotIn("Access-Control-Allow-Origin", headers)
        status, headers, _ = server.request("OPTIONS", "/ultra/chat/workspaces",
                                            {"Origin": "https://foreign.example", "Access-Control-Request-Method": "GET",
                                             "Access-Control-Request-Headers": TOKEN_HEADER})
        self.assertGreaterEqual(status, 400)
        self.assertNotIn("Access-Control-Allow-Origin", headers)


class Disclosure(Base):
    def test_e1_token_appears_only_in_the_capability_answer(self):
        server = self.start("disclosure", picker=False)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            token = server.ultra_token()
            bodies = [server.request("GET", path)[2] for path in ("/", "/ui", "/status", "/ui/capabilities",
                                                                  "/ultra/connections", "/ultra/chat/workspaces")]
            bodies.append(server.request("GET", "/ultra/chat/workspaces", {TOKEN_HEADER: token + "x"})[2])
            bodies.append(server.request("GET", "/ultra/chat/workspaces", {TOKEN_HEADER: token})[2])
        for index, raw in enumerate(bodies):
            with self.subTest(response=index):
                self.assertNotIn(token.encode(), raw)
        self.assertNotIn(token, captured.getvalue())


if __name__ == "__main__":
    unittest.main()
