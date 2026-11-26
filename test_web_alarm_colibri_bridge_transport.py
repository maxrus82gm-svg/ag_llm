"""Independent WUA-side tests, no network or live profile."""
import hashlib
import json
import os
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

import httpx

from web_alarm.colibri_bridge_transport import (
    BridgeFault, Contract, SSEDecoder, OfflineColibriTransport, ReadOnlyColibriTransport,
    strict_json, canonical,
    _discover,
)


def windows_process_user():
    import win32api
    import win32con
    import win32security as acl

    token = acl.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return acl.GetTokenInformation(token, acl.TokenUser)[0]
    finally:
        token.Close()


def protect(path, *, public=False):
    """Make the actual fixture ACL match the consumer's production requirements."""
    if os.name != "nt":
        path.chmod((0o700 if path.is_dir() else 0o600) | (0o004 if public else 0))
        return
    import win32con
    import win32security as acl

    # Elevated Windows tokens may create files with a group as the default owner.
    # Discovery requires TokenUser both as owner and as the private DACL grantee.
    actor = windows_process_user()
    dacl = acl.ACL()
    dacl.AddAccessAllowedAce(acl.ACL_REVISION, win32con.GENERIC_ALL, actor)
    if public:
        everyone = acl.CreateWellKnownSid(acl.WinWorldSid, None)
        dacl.AddAccessAllowedAce(acl.ACL_REVISION, win32con.GENERIC_READ, everyone)
    acl.SetNamedSecurityInfo(str(path), acl.SE_FILE_OBJECT,
                             acl.OWNER_SECURITY_INFORMATION | acl.DACL_SECURITY_INFORMATION
                             | acl.PROTECTED_DACL_SECURITY_INFORMATION, actor, None, dacl, None)


class DecodeTests(unittest.TestCase):
    def test_split_utf8_multiline_comments_crlf(self):
        text = ': heartbeat\r\nevent: delta\r\nid: 1\r\ndata: {"type":"delta",\r\ndata: "text":"Привет 🌊","sequence":1}\r\n\r\n'
        dec = SSEDecoder()
        events = []
        for b in text.encode("utf-8"):
            events.extend(dec.feed(bytes([b])))
        dec.eof()
        self.assertEqual(events, [("delta", "1", {"type":"delta","text":"Привет 🌊","sequence":1})])

    def test_malformed_and_truncated_refuse(self):
        for raw in (b'event: meta\nevent: delta\nid: 0\ndata: {}\n\n',
                    b'event: delta\nid: 0\ndata: {"a":1,"a":2}\n\n',
                    b'event: delta\nid: 0\ndata: \xff\n\n',
                    b'event: delta\nid: 0\ndata: {}\n'):
            with self.subTest(raw=raw), self.assertRaises(BridgeFault):
                d = SSEDecoder()
                list(d.feed(raw))
                d.eof()

    def test_usage_raw_nullable_and_derived(self):
        c = Contract()
        u = dict(status="partial",source="provider_and_derived_total",prompt_basis="unknown",
                 prompt_tokens=0,completion_tokens=7,total_tokens=7,reasoning_tokens=None,cached_prompt_tokens=None)
        self.assertEqual(c.check("Usage",u),u)
        for bad in ({**u,"total_tokens":8}, {**u,"status":"reported"},
                    {**u,"reasoning_tokens":8}, {**u,"prompt_tokens":True}):
            with self.subTest(bad=bad), self.assertRaises(BridgeFault):
                c.check("Usage",bad)
        raw = {**u,"source":"unavailable","status":"unavailable",**{k:None for k in
            ("prompt_tokens","completion_tokens","total_tokens","reasoning_tokens","cached_prompt_tokens")}}
        self.assertEqual(c.check("Usage",raw),raw)

    def test_discovery_strict_loopback_and_expected_identity(self):
        with TemporaryDirectory() as td:
            p = Path(td).resolve()
            protect(p)
            token = p/"bridge-wua.token"
            token.write_text("X"*64,encoding="ascii")
            protect(token)
            d = p/"bridge-discovery.json"
            value=dict(bridge_id="a"*32,protocol_version="1.0.0",origin="http://127.0.0.1:12345",
                       credential_ref="bridge-wua.token",launch_identity="b"*32)
            for delta in ({"origin":"http://localhost:12345"},{"origin":"http://127.0.0.1:12345@evil.test"},
                          {"origin":"http://127.0.0.1:65536"},{"bridge_id":"c"*32},
                          {"protocol_version":"2.0.0"},{"credential_ref":"../token"},
                          {"launch_identity":"not-an-id"}):
                d.write_bytes(canonical({**value,**delta}));protect(d)
                with self.subTest(delta=delta),self.assertRaises(BridgeFault):
                    _discover(p,"a"*32)
            d.write_bytes(canonical(value))
            self.assertNotIn("X"*64,repr(_discover(p,"a"*32)))
        with self.assertRaises(BridgeFault):
            OfflineColibriTransport(Path(__file__).parent,expected_bridge_id="a"*32)


class ReadOnlyCatalogTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory(prefix="colcat_")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.profile = self.root / "profile"
        self.profile.mkdir()
        protect(self.profile)
        self.bridge_id = "a" * 32
        self.token = self.profile / "bridge-wua.token"
        self.token.write_text("X" * 64, encoding="ascii")
        protect(self.token)
        self.discovery = {"bridge_id": self.bridge_id, "protocol_version": "1.0.0",
                          "origin": "http://127.0.0.1:12345", "credential_ref": self.token.name,
                          "launch_identity": "b" * 32}
        self.write_discovery()
        self.transport = ReadOnlyColibriTransport(self.profile, expected_bridge_id=self.bridge_id)
        contract = Contract()
        schemas = contract.components["schemas"]
        self.targets = []
        for n in ("1", "2"):
            t = dict(bridge_id=self.bridge_id, manager_id="mgr" + n, manager_name="Manager " + n,
                     slot_id="slot-" + n, model_key="key-" + n, model_id="engine-" + n, instance_id=n * 32,
                     model_revision=None, display_name="Shared model", status="READY",
                     execution_mode="CPU", engine=None, engine_version=None, allowed_operations=["chat"],
                     capabilities={k: "unsupported" for k in schemas["Capabilities"]["required"]},
                     limits=dict.fromkeys(schemas["Limits"]["required"]),
                     launch_configuration=dict.fromkeys(schemas["LaunchConfiguration"]["required"]))
            t["capabilities"]["streaming"] = "supported"
            t["launch_configuration"]["configuration_lab"] = "unsupported"
            identity = [self.bridge_id, t["manager_id"], t["slot_id"], t["model_key"]]
            t["target_id"] = "tgt_" + hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
            contract.check("Target", t)
            self.targets.append(t)
        self.calls = []
        self.offline = False
        self.respond = None
        physical = httpx.Client

        def client(**kwargs):
            self.assertFalse(kwargs["follow_redirects"])
            self.assertFalse(kwargs["trust_env"])
            return physical(transport=httpx.MockTransport(self.handle), **kwargs)

        mock = patch("web_alarm.colibri_bridge_transport.httpx.Client", side_effect=client)
        self.addCleanup(mock.stop)
        mock.start()

    def write_discovery(self, **changes):
        path = self.profile / "bridge-discovery.json"
        path.write_bytes(canonical({**self.discovery, **changes}))
        protect(path)

    def handle(self, request):
        self.calls.append((request.method, request.url.path))
        self.assertEqual(request.url.host, "127.0.0.1")
        self.assertEqual(request.headers["Authorization"], "Bearer " + "X" * 64)
        self.assertEqual(request.read(), b"")
        self.assertEqual(request.method, "GET")
        if self.offline:
            raise httpx.ConnectError("synthetic disconnect")
        if self.respond is not None:
            return self.respond()
        common = dict(bridge_id=self.bridge_id, protocol_version="1.0.0", catalog_revision="mock-r1")
        if request.url.path == "/bridge/v1/health":
            value = {**common, "status": "READY", "permissions": ["read", "chat"],
                     "capabilities": dict.fromkeys(("detached_generation", "replay", "model_control"), "unsupported")}
        else:
            self.assertEqual(request.url.path, "/bridge/v1/models")
            value = {**common, "targets": self.targets}
        return httpx.Response(200, headers={"content-type": "application/json"},
                              stream=httpx.ByteStream(canonical(value)))

    def test_only_health_and_models_get_with_empty_body(self):
        for name in ("prepare", "run", "status", "cancel", "start", "stop"):
            self.assertFalse(hasattr(self.transport, name), name)
        for path, schema, body in (("/health", "Health", {}), ("/models", "Catalog", b""),
                                   ("/health?x=1", "Health", None),
                                   ("/requests/id", "RequestStatus", None), ("/chat/cancel", "CancelResponse", {}),
                                   ("/models", "Health", None), ("/chat/stream", "Event", None)):
            with self.subTest(path=path), self.assertRaisesRegex(BridgeFault, "readonly_route_refused"):
                self.transport._json(path, schema, body)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.transport.catalog()["targets"], self.targets)
        self.assertEqual(self.calls, [("GET", "/bridge/v1/health"), ("GET", "/bridge/v1/models")])

    @unittest.skipUnless(os.name == "nt", "Windows security descriptors")
    def test_windows_fixture_owner_and_protected_dacl_match_process_user(self):
        import win32security as acl

        actor = windows_process_user()
        flags = acl.OWNER_SECURITY_INFORMATION | acl.DACL_SECURITY_INFORMATION
        for path in (self.profile, self.profile / "bridge-discovery.json", self.token):
            with self.subTest(file=path.name):
                descriptor = acl.GetNamedSecurityInfo(str(path), acl.SE_FILE_OBJECT, flags)
                self.assertEqual(descriptor.GetSecurityDescriptorOwner(), actor)
                self.assertTrue(descriptor.GetSecurityDescriptorControl()[0] & acl.SE_DACL_PROTECTED)
                dacl = descriptor.GetSecurityDescriptorDacl()
                self.assertEqual(dacl.GetAceCount(), 1)
                ace, _, grantee = dacl.GetAce(0)
                self.assertEqual(ace, (acl.ACCESS_ALLOWED_ACE_TYPE, 0))
                self.assertEqual(grantee, actor)

    @unittest.skipUnless(os.name == "nt", "Windows security descriptors")
    def test_windows_foreign_owner_is_refused_with_an_otherwise_private_dacl(self):
        import win32security as acl

        foreign = acl.CreateWellKnownSid(acl.WinBuiltinAdministratorsSid, None)
        self.assertNotEqual(foreign, windows_process_user())
        read_security_info = acl.GetNamedSecurityInfo
        for subject in (self.profile, self.profile / "bridge-discovery.json", self.token):
            def read_with_foreign_owner(name, kind, flags):
                descriptor = read_security_info(name, kind, flags)
                if Path(name) != subject:
                    return descriptor
                # Restricted Windows accounts cannot assign a foreign owner to
                # a file. Change only the owner in a native descriptor with the
                # real on-disk DACL, leaving production's decisions intact.
                alternate = acl.SECURITY_DESCRIPTOR()
                alternate.SetSecurityDescriptorOwner(foreign, False)
                alternate.SetSecurityDescriptorDacl(True, descriptor.GetSecurityDescriptorDacl(), False)
                return alternate

            with self.subTest(file=subject.name), patch.object(
                    acl, "GetNamedSecurityInfo", side_effect=read_with_foreign_owner):
                with self.assertRaisesRegex(BridgeFault, "unsafe_discovery"):
                    self.transport.catalog()
                self.assertEqual(self.calls, [])

    def test_discovery_acl_origin_and_launch_identity_refuse_before_http(self):
        with self.assertRaisesRegex(BridgeFault, "unsafe_profile"):
            ReadOnlyColibriTransport("relative", expected_bridge_id=self.bridge_id)
        for changes, code in (({"bridge_id": "c" * 32}, "identity_mismatch"),
                              ({"origin": "http://10.1.2.3:12345"}, "unsafe_origin")):
            self.write_discovery(**changes)
            with self.assertRaisesRegex(BridgeFault, code):
                self.transport.catalog()
        self.write_discovery()
        protect(self.token, public=True)
        try:
            with self.assertRaisesRegex(BridgeFault, "unsafe_discovery"):
                self.transport.catalog()
        finally:
            protect(self.token)
        alias = self.profile / "duplicate-token"
        os.link(self.token, alias)
        try:
            with self.assertRaisesRegex(BridgeFault, "unsafe_discovery"):
                self.transport.catalog()
        finally:
            alias.unlink()
        self.assertEqual(self.calls, [])
        self.transport.catalog()
        self.calls.clear()
        self.write_discovery(launch_identity="c" * 32)
        with self.assertRaisesRegex(BridgeFault, "identity_mismatch"):
            self.transport.catalog()
        self.assertEqual(self.calls, [])

    def test_redirect_and_invalid_instance_are_refused(self):
        self.respond = lambda: httpx.Response(303, headers={"location": "http://127.0.0.1:1/bridge/v1/health"})
        with self.assertRaisesRegex(BridgeFault, "redirect_refused"):
            self.transport.catalog()
        self.assertEqual(self.calls, [("GET", "/bridge/v1/health")])
        self.calls.clear()
        self.respond = None
        self.targets[0]["instance_id"] = "not-an-instance"
        with self.assertRaisesRegex(BridgeFault, "protocol_error"):
            self.transport.catalog()
        self.assertEqual(len(self.calls), 2)

    def test_catalog_projection_is_read_only_and_keeps_stale_targets(self):
        from web_alarm.server import WebAlarmApi, create_server
        from web_alarm.standard_live import prepare_personal_chat
        import context_storage as core

        api = WebAlarmApi(self.root / "registry")
        self.assertEqual(api.dispatch("GET", "/ultra/connections")[1]["columns"]["local_llm"]["state"], "NOT_CONNECTED")
        api.dispatch("GET", "/ultra/model-cards")
        self.assertEqual(self.calls, [])
        api.ultra_connections.bind_readonly_colibri(self.transport)
        self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError):
            api.ultra_connections.bind_offline_colibri(self.transport)
        ws, local_root, _ = prepare_personal_chat(api)
        chat_id = core.list_chats_bounded(local_root)["chats"][0]["chat_id"]
        server = create_server(api, host="127.0.0.1", port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def request(method, path, body=None, headers=None):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                conn.request(method, path, body=json.dumps(body) if body is not None else None,
                             headers={"Content-Type": "application/json", **(headers or {})})
                response = conn.getresponse()
                return response.status, json.loads(response.read())
            finally:
                conn.close()

        cap = request("GET", "/ui/ultra-chat/capability")[1]["turn_test"]
        self.assertFalse(any(m.get("is_local") for m in cap["models"]))
        self.assertEqual(self.calls, [])
        column = request("GET", "/ultra/connections")[1]["columns"]["local_llm"]
        self.assertEqual(column["mode"], "READ_ONLY")
        self.assertEqual({m["manager_name"] for m in column["connections"]}, {"Manager 1", "Manager 2"})
        self.assertTrue(all(not m["selectable"] and m["availability"] == "READY" for m in column["connections"]))
        cards = [c for c in request("GET", "/ultra/model-cards")[1]["cards"] if c["is_local"]]
        self.assertEqual([c["api"]["reason"] for c in cards], ["LOCAL_CATALOG_ONLY"] * 2)
        self.assertEqual([c["api"]["indicator"] for c in cards], ["UNKNOWN"] * 2)
        for card, target in zip(cards, self.targets):
            for key in ("target_id", "instance_id", "model_id", "manager_name", "slot_id", "status",
                        "execution_mode", "capabilities", "limits"):
                self.assertEqual(card["local_target"][key], target[key])
        trace = list(self.calls)
        cap = request("GET", "/ui/ultra-chat/capability")[1]["turn_test"]
        self.assertFalse(any(m.get("is_local") for m in cap["models"]))
        write = request("GET", "/ui/ultra-chat/write-capability")[1]["ultra_chat_write"]
        headers = {write["header"]: write["token"], "Origin": f"http://127.0.0.1:{server.server_port}"}
        base = f"/ultra/chat/workspaces/{ws.workspace_id}/chats/{chat_id}"
        ref = self.targets[0]["target_id"]
        self.assertEqual(request("POST", base + "/model", {"model_ref": ref}, headers)[0], 400)
        self.assertEqual(request("POST", base + "/turns", {"model_ref": ref, "text": "synthetic",
                         "idempotency_key": uuid4().hex}, headers)[0], 403)
        self.assertEqual(request("POST", f"/ultra/model-cards/{ref}/check", {}, headers)[0], 409)
        self.assertEqual(self.calls, trace)
        self.offline = True
        column = request("GET", "/ultra/connections")[1]["columns"]["local_llm"]
        self.assertEqual((column["state"], column["reason"]), ("UNAVAILABLE", "transport_error"))
        self.assertEqual({m["model_id"] for m in column["connections"]}, {t["target_id"] for t in self.targets})
        self.assertTrue(all(m["availability"] == "UNKNOWN" and not m["selectable"] for m in column["connections"]))
        self.assertEqual(api.ultra_connections.enabled_local_targets(), set())


    def test_managed_binding_restart_stale_reconnect_and_disconnect(self):
        from web_alarm.ultra_connections import UltraConnections
        root = self.root / "studio"
        connections = UltraConnections(root)
        manager = connections.managed_client()
        self.assertIsNone(manager.status()["binding"])
        body = {"profile": str(self.profile), "bridge_id": self.bridge_id}
        self.assertEqual(manager.act("connect", body)["state"], "AVAILABLE")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(connections.catalog()["columns"]["local_llm"]["connections"]), 2)
        self.assertEqual(connections.enabled_local_targets(), set())
        self.assertEqual(len(self.calls), 2)
        saved = json.loads(manager.store.path.read_text(encoding="utf-8"))
        self.assertEqual(set(saved["binding"]), {"profile", "bridge_id", "origin", "launch_identity"})
        self.assertNotIn("X" * 64, manager.store.path.read_text(encoding="utf-8"))
        fresh = UltraConnections(root)
        restored = fresh.managed_client()
        self.assertEqual(restored.status()["reason"], "refresh_required")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(restored.act("refresh", {})["state"], "AVAILABLE")
        self.assertEqual(len(self.calls), 4)
        self.write_discovery(launch_identity="c" * 32)
        self.assertEqual(restored.act("refresh", {})["reason"], "identity_mismatch")
        self.assertEqual(len(self.calls), 4)
        local = fresh.catalog()["columns"]["local_llm"]
        self.assertEqual(len(local["connections"]), 2)
        self.assertTrue(all(m["availability"] == "UNKNOWN" and not m["selectable"] for m in local["connections"]))
        self.assertEqual(restored.act("connect", body)["state"], "AVAILABLE")
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(restored.act("disconnect", {})["state"], "NOT_CONNECTED")
        self.assertIsNone(UltraConnections(root).managed_client().status()["binding"])
        self.assertEqual(len(self.calls), 6)

    def test_failed_rebind_and_corrupt_store_never_overwrite(self):
        from web_alarm.colibri_binding import BindingError
        from web_alarm.ultra_connections import UltraConnections
        manager = UltraConnections(self.root / "studio").managed_client()
        body = {"profile": str(self.profile), "bridge_id": self.bridge_id}
        manager.act("connect", body)
        before = manager.store.path.read_bytes()
        self.offline = True
        with self.assertRaises(BridgeFault):
            manager.act("connect", body)
        self.assertEqual(manager.store.path.read_bytes(), before)
        manager.store.path.write_bytes(b'{"schema":1,"binding":null,"token":"bad"}')
        calls = list(self.calls)
        self.assertEqual(manager.status()["reason"], "binding_corrupt")
        with self.assertRaises(BindingError):
            manager.act("disconnect", {})
        self.assertEqual(self.calls, calls)
        self.assertIn(b'"token":"bad"', manager.store.path.read_bytes())

    def test_managed_http_requires_registered_standard_origin_and_write_token(self):
        from types import SimpleNamespace
        from web_alarm.server import WebAlarmApi, create_server
        api = WebAlarmApi(self.root / "registry")
        server = create_server(api, host="127.0.0.1", port=0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(method, path, body=None, headers=None):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                conn.request(method, path, body=json.dumps(body) if body is not None else None,
                             headers={"Content-Type": "application/json", **(headers or {})})
                response = conn.getresponse()
                return response.status, json.loads(response.read())
            finally:
                conn.close()
        cap = server.web_alarm_ultra_chat_write_access.capability()
        headers = {cap["header"]: cap["token"], "Origin": f"http://127.0.0.1:{server.server_port}"}
        body = {"profile": str(self.profile), "bridge_id": self.bridge_id}
        self.assertEqual(request("GET", "/ui/colibri")[1], {"available": False})
        self.assertEqual(request("POST", "/ui/colibri/connect", body, headers)[0], 403)
        server.web_alarm_launch = SimpleNamespace(standard=False)
        server.web_alarm_instance = {"profile": "test"}
        self.assertEqual(request("POST", "/ui/colibri/connect", body, headers)[0], 403)
        server.web_alarm_launch = SimpleNamespace(standard=True)
        server.web_alarm_instance = {"profile": "standard"}
        self.assertEqual(request("POST", "/ui/colibri/connect", body, {"Origin": headers["Origin"]})[0], 403)
        self.assertEqual(request("POST", "/ui/colibri/connect", body, {**headers, "Origin": "http://foreign.invalid"})[0], 403)
        self.assertEqual(request("POST", "/ui/colibri/connect", {**body, "token": "bad"}, headers)[0], 409)
        self.assertEqual(self.calls, [])
        self.assertEqual(request("POST", "/ui/colibri/connect", body, headers)[0], 200)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(request("GET", "/ui/colibri")[1]["state"], "AVAILABLE")
        self.assertEqual(len(request("GET", "/ultra/connections")[1]["columns"]["local_llm"]["connections"]), 2)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(request("POST", "/ui/colibri/disconnect", {}, headers)[0], 200)
        self.assertEqual(len(self.calls), 2)
