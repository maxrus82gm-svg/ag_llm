"""WUA-1 EVM tab: connections read model over the shared Ultra model registry (offline only).

Oracles: the shared ``model_registry`` itself (never a list copied into the test), the bytes of the saved choice
under a disposable storage root, the full storage tree, ``sys.modules`` (no transport import) and the raw HTTP
bodies. No network, no credentials: a sentinel secret in the environment must never appear in any output.
"""
from __future__ import annotations

import io
import json
import logging
import os
import socket
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import model_registry
from model_registry import ModelSpec, get_model_spec, list_model_specs
from web_alarm import ultra_connections as uc
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ui import INDEX_HTML

SECRET = "SENTINEL-SECRET-0f1e2d3c4b5a"


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def cid(spec: ModelSpec) -> str:
    return f"api:{spec.provider}:{spec.model_id}"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wa_wua1_")
        self.addCleanup(self.tempdir.cleanup)
        self.storage = Path(self.tempdir.name) / "state"
        self.api = WebAlarmApi(self.storage)
        self.saved = self.storage / "ultra" / "connections.json"

    def get(self, path):
        return self.api.dispatch("GET", path)

    def post(self, body):
        return self.api.dispatch("POST", "/ultra/connections/selection", body)

    def refused(self, method, path, body=None):
        from web_alarm.server import ApiError
        with self.assertRaises(ApiError) as caught:
            self.api.dispatch(method, path, body)
        return caught.exception


class CatalogTests(Fixture):
    def test_catalog_is_exactly_the_shared_registry_and_the_page_copies_no_model(self):
        status, data = self.get("/ultra/connections")
        self.assertEqual(status, 200)
        api = data["columns"]["api"]
        self.assertEqual(api["state"], "AVAILABLE")
        specs = list_model_specs()
        self.assertEqual([c["model_id"] for c in api["connections"]], [s.model_id for s in specs])
        for c, spec in zip(api["connections"], specs):
            self.assertEqual((c["connection_id"], c["display_name"], c["provider"], c["provider_model_id"]),
                             (cid(spec), spec.display_name, spec.provider, spec.provider_model_id))
            self.assertEqual((c["status"], c["verification"], c["selected"]), ("REGISTERED", "UNVERIFIED", False))
        # the six GigaChat models of the shared registry are all offered (WUA-1 acceptance)
        self.assertEqual({s.model_id for s in specs} >= {"gigachat_2", "gigachat_2_max", "gigachat_2_pro",
                                                         "gigachat_3_lightning", "gigachat_3_pro", "gigachat_ultra"},
                         True)
        for spec in specs:  # no model identity is hard-coded in the shipped page
            self.assertNotIn(spec.model_id, INDEX_HTML)
            self.assertNotIn(spec.provider_model_id, INDEX_HTML)
        self.assertEqual((data["columns"]["mcp_agents"], data["columns"]["local_llm"]),
                         ({"state": "NOT_CONNECTED", "connections": []}, {"state": "NOT_CONNECTED", "connections": []}))
        self.assertEqual(data["network_calls"], 0)
        self.assertEqual(data["selection"]["chat"]["state"], "NOT_SELECTED")

    def test_registry_changes_are_seen_without_any_copy_in_web_alarm(self):
        extra = ModelSpec("test_model_x", "Test X", "gigachat", "Test-X", enabled=True)
        with mock.patch.dict(model_registry._MODEL_REGISTRY, {"test_model_x": extra}):
            ids = [c["model_id"] for c in self.get("/ultra/connections")[1]["columns"]["api"]["connections"]]
            self.assertIn("test_model_x", ids)
        ids = [c["model_id"] for c in self.get("/ultra/connections")[1]["columns"]["api"]["connections"]]
        self.assertNotIn("test_model_x", ids)

    def test_viewing_writes_nothing_and_opens_no_network_or_transport(self):
        before = tree(self.storage)
        sys.modules.pop("gigachat_transport", None)
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network used")), \
                mock.patch.object(socket, "create_connection", side_effect=AssertionError("network used")):
            for _ in range(3):
                self.get("/ultra/connections")
                self.get("/ultra/connections/selection")
        self.assertEqual(tree(self.storage), before, "a read created or changed storage")
        self.assertFalse((self.storage / "ultra").exists())
        self.assertNotIn("gigachat_transport", sys.modules)

    def test_an_unavailable_shared_registry_is_reported_and_invents_nothing(self):
        before = tree(self.storage)
        with mock.patch.object(uc, "_registry", side_effect=uc.RegistryUnavailableError("not importable")):
            api = self.get("/ultra/connections")[1]["columns"]["api"]
            self.assertEqual((api["state"], api["connections"]), ("REGISTRY_UNAVAILABLE", []))
            error = self.refused("POST", "/ultra/connections/selection", {"connection_id": "api:gigachat:gigachat_ultra"})
            self.assertEqual((error.status, error.code), (503, "model_registry_unavailable"))
        self.assertEqual(tree(self.storage), before)
        self.post({"connection_id": "api:gigachat:gigachat_ultra"})  # a saved choice, then the registry goes away
        with mock.patch.object(uc, "_registry", side_effect=uc.RegistryUnavailableError("not importable")):
            status, data = self.get("/ultra/connections")
            self.assertEqual(status, 200)
            s = data["selection"]["chat"]
            self.assertEqual((s["state"], s["connection_id"], s["provider_model_id"]),
                             ("REGISTRY_UNAVAILABLE", "api:gigachat:gigachat_ultra", None))

    def test_status_lists_the_capability_and_wrong_methods_are_refused(self):
        self.assertIn("ultra_connections", self.get("/status")[1]["capabilities"])
        for method, path in (("POST", "/ultra/connections"), ("PUT", "/ultra/connections"),
                             ("DELETE", "/ultra/connections/selection"), ("PUT", "/ultra/connections/selection")):
            with self.subTest(method=method, route=path.rsplit("/", 1)[-1]):
                self.assertEqual(self.refused(method, path, {}).status, 405)


class SelectionTests(Fixture):
    def test_every_registry_model_selects_and_resolves_to_its_own_provider_model_id(self):
        for spec in list_model_specs():
            with self.subTest(model=spec.model_id):
                status, data = self.post({"role": "chat", "connection_id": cid(spec)})
                self.assertEqual(status, 200)
                s = data["selection"]
                self.assertEqual((s["state"], s["connection_id"], s["model_id"], s["provider_model_id"]),
                                 ("SAVED", cid(spec), spec.model_id, get_model_spec(spec.model_id).provider_model_id))
                self.assertEqual(self.api.ultra_connections.resolve_provider_model_id("chat"), spec.provider_model_id)
                marked = [c for c in self.get("/ultra/connections")[1]["columns"]["api"]["connections"] if c["selected"]]
                self.assertEqual([c["model_id"] for c in marked], [spec.model_id])

    def test_pro_and_ultra_choice_survives_a_restart_and_is_stored_only_as_a_reference(self):
        for model_id, provider_model_id in (("gigachat_2_pro", "GigaChat-2-Pro"), ("gigachat_ultra", "GigaChat-3-Ultra")):
            with self.subTest(model=model_id):
                self.post({"connection_id": f"api:gigachat:{model_id}"})
                restarted = WebAlarmApi(self.storage)  # a new server process reads the same storage
                s = restarted.dispatch("GET", "/ultra/connections/selection")[1]["selection"]
                self.assertEqual((s["state"], s["model_id"], s["provider_model_id"]), ("SAVED", model_id, provider_model_id))
                raw = json.loads(self.saved.read_text(encoding="utf-8"))
                self.assertEqual(raw["schema"], "web_alarm.ultra_connections")
                self.assertEqual(set(raw["roles"]["chat"]), {"connection_id", "model_id", "selected_at"},
                                 "the saved file must reference the registry, not copy its catalogue")
        self.assertEqual(sorted(p.name for p in self.saved.parent.iterdir()), ["connections.json"], "temp leftovers")

    def test_unknown_malformed_and_disabled_connections_are_refused_without_writing(self):
        before = tree(self.storage)
        cases = {"unknown_model": ("api:gigachat:no_such_model", 404), "wrong_provider": ("api:openai:gigachat_ultra", 404),
                 "wrong_kind": ("mcp:gigachat:gigachat_ultra", 400), "bare_model_id": ("gigachat_ultra", 400),
                 "extra_part": ("api:gigachat:gigachat_ultra:x", 400), "empty_part": ("api::gigachat_ultra", 400),
                 "not_ascii": ("api:gigachat:гигачат", 400), "too_long": ("api:gigachat:" + "x" * 300, 400),
                 "not_string": (["api:gigachat:gigachat_ultra"], 400), "missing": (None, 400)}
        for name, (value, code) in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refused("POST", "/ultra/connections/selection", {"connection_id": value}).status, code)
        self.assertEqual(self.refused("POST", "/ultra/connections/selection",
                                      {"role": "planner", "connection_id": "api:gigachat:gigachat_ultra"}).status, 400)
        self.assertEqual(self.refused("GET", "/ultra/connections/selection?role=verifier").status, 400)
        disabled = ModelSpec("gigachat_off", "Off", "gigachat", "GigaChat-Off", enabled=False)
        with mock.patch.dict(model_registry._MODEL_REGISTRY, {"gigachat_off": disabled}):
            error = self.refused("POST", "/ultra/connections/selection", {"connection_id": "api:gigachat:gigachat_off"})
            self.assertEqual((error.status, error.code), (409, "connection_disabled"))
            row = next(c for c in self.get("/ultra/connections")[1]["columns"]["api"]["connections"]
                       if c["model_id"] == "gigachat_off")
            self.assertEqual((row["status"], row["selectable"]), ("DISABLED", False))
        self.assertEqual(tree(self.storage), before, "a refused selection wrote something")

    def test_a_saved_model_that_later_disappears_or_is_disabled_is_reported_not_used(self):
        extra = ModelSpec("gigachat_temp", "Temp", "gigachat", "GigaChat-Temp", enabled=True)
        with mock.patch.dict(model_registry._MODEL_REGISTRY, {"gigachat_temp": extra}):
            self.post({"connection_id": "api:gigachat:gigachat_temp"})
            with mock.patch.dict(model_registry._MODEL_REGISTRY,
                                 {"gigachat_temp": ModelSpec("gigachat_temp", "Temp", "gigachat", "GigaChat-Temp",
                                                             enabled=False)}):
                s = self.get("/ultra/connections/selection")[1]["selection"]
                self.assertEqual((s["state"], s["provider_model_id"]), ("INVALID_REFERENCE", None))
        s = self.get("/ultra/connections/selection")[1]["selection"]  # removed from the registry
        self.assertEqual((s["state"], s["connection_id"]), ("INVALID_REFERENCE", "api:gigachat:gigachat_temp"))
        with self.assertRaises(uc.UnknownConnectionError):
            self.api.ultra_connections.resolve_provider_model_id()
        self.assertFalse(any(c["selected"] for c in self.get("/ultra/connections")[1]["columns"]["api"]["connections"]))

    def test_damaged_saved_choice_is_reported_kept_aside_and_replaced_only_by_an_explicit_choice(self):
        damage = {"garbage": b"{not json", "not_utf8": b"\xff\xfe\x00", "wrong_schema": b'{"schema":"x","version":1,"roles":{}}',
                  "wrong_version": json.dumps({"schema": uc.SCHEMA, "version": 99, "roles": {}}).encode(),
                  "roles_not_object": json.dumps({"schema": uc.SCHEMA, "version": 1, "roles": []}).encode(),
                  "entry_without_id": json.dumps({"schema": uc.SCHEMA, "version": 1, "roles": {"chat": {}}}).encode(),
                  "empty": b""}
        for name, raw in damage.items():
            with self.subTest(name):
                for old in self.saved.parent.glob("*") if self.saved.parent.exists() else []:
                    old.unlink()
                self.saved.parent.mkdir(parents=True, exist_ok=True)
                self.saved.write_bytes(raw)
                s = self.get("/ultra/connections/selection")[1]["selection"]
                self.assertEqual((s["state"], s["provider_model_id"]), ("CORRUPT", None))
                catalog = self.get("/ultra/connections")[1]
                self.assertEqual(len(catalog["columns"]["api"]["connections"]), len(list_model_specs()))
                self.assertEqual(self.saved.read_bytes(), raw, "a read repaired or replaced the damaged file")
                self.post({"connection_id": "api:gigachat:gigachat_3_pro"})
                self.assertEqual(self.get("/ultra/connections/selection")[1]["selection"]["state"], "SAVED")
                kept = [p for p in self.saved.parent.iterdir() if p.name.startswith("connections.json.corrupt-")]
                self.assertEqual([p.read_bytes() for p in kept], [raw], "the damaged original was not kept")

    def test_roles_of_a_newer_version_are_kept_when_chat_is_saved(self):
        self.saved.parent.mkdir(parents=True)
        self.saved.write_text(json.dumps({"schema": uc.SCHEMA, "version": 1, "roles": {
            "planner": {"connection_id": "api:gigachat:gigachat_2"}}}), encoding="utf-8")
        self.post({"connection_id": "api:gigachat:gigachat_ultra"})
        roles = json.loads(self.saved.read_text(encoding="utf-8"))["roles"]
        self.assertEqual(roles["planner"], {"connection_id": "api:gigachat:gigachat_2"})
        self.assertEqual(roles["chat"]["model_id"], "gigachat_ultra")

    def test_concurrent_choices_leave_one_valid_file(self):
        choices = [cid(s) for s in list_model_specs()]
        errors = []

        def choose(value):
            try:
                WebAlarmApi(self.storage).dispatch("POST", "/ultra/connections/selection", {"connection_id": value})
            except Exception as exc:  # noqa: BLE001 - recorded, asserted below
                errors.append(type(exc).__name__)
        threads = [threading.Thread(target=choose, args=(choices[i % len(choices)],)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        self.assertEqual(errors, [])
        s = self.get("/ultra/connections/selection")[1]["selection"]
        self.assertEqual(s["state"], "SAVED")
        self.assertIn(s["connection_id"], choices)
        self.assertEqual(sorted(p.name for p in self.saved.parent.iterdir()), ["connections.json"])

    def test_the_tkinter_ultra_state_and_the_transport_are_never_touched(self):
        import ui_state
        sys.modules.pop("gigachat_transport", None)
        with mock.patch.object(ui_state, "save_ui_state", side_effect=AssertionError("Tkinter state written")), \
                mock.patch.object(ui_state, "load_ui_state", side_effect=AssertionError("Tkinter state read")):
            self.post({"connection_id": "api:gigachat:gigachat_2_max"})
            self.get("/ultra/connections")
        self.assertNotIn("gigachat_transport", sys.modules)
        self.assertTrue(self.saved.is_relative_to(self.storage))
        source = Path(uc.__file__).read_text(encoding="utf-8")
        for forbidden in ("gigachat_transport", "ui_state", "httpx", "GIGACHAT_CREDENTIALS", "getenv", "os.environ"):
            self.assertNotIn(forbidden, source.split('"""', 2)[2])


class HttpTests(Fixture):
    def serve(self):
        server = create_server(self.api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        host, port = server.server_address[:2]
        return f"http://{host}:{port}"

    @staticmethod
    def call(url, method="GET", body=None, content_type="application/json"):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def test_real_http_round_trip_never_carries_a_secret_or_a_log_line(self):
        url = self.serve()
        records = []
        handler = logging.Handler()
        handler.emit = records.append
        logging.getLogger().addHandler(handler)
        self.addCleanup(logging.getLogger().removeHandler, handler)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"GIGACHAT_CREDENTIALS": SECRET, "GIGACHAT_SCOPE": SECRET}), \
                redirect_stdout(out), redirect_stderr(err):
            bodies = [self.call(url + "/ultra/connections"),
                      self.call(url + "/ultra/connections/selection", "POST",
                                {"role": "chat", "connection_id": "api:gigachat:gigachat_ultra"}),
                      self.call(url + "/ultra/connections/selection"),
                      self.call(url + "/ultra/connections/selection", "POST", {"connection_id": "api:gigachat:nope"}),
                      self.call(url + "/ultra/connections/selection", "POST", {"connection_id": 7})]
        self.assertEqual([status for status, _ in bodies], [200, 200, 200, 404, 400])
        for _, text in bodies:
            self.assertNotIn(SECRET, text)
        self.assertNotIn(SECRET, out.getvalue() + err.getvalue())
        self.assertFalse(any(SECRET in str(r.getMessage()) for r in records))
        selection = json.loads(bodies[2][1])["selection"]
        self.assertEqual((selection["state"], selection["provider_model_id"]), ("SAVED", "GigaChat-3-Ultra"))
        self.assertNotIn(SECRET, "".join(p.read_text(encoding="utf-8", errors="replace")
                                         for p in self.storage.rglob("*") if p.is_file()))

    def test_selection_requires_json_and_the_page_offers_the_evm_entry_and_a_way_back(self):
        url = self.serve()
        status, _ = self.call(url + "/ultra/connections/selection", "POST", {"connection_id": "api:gigachat:gigachat_ultra"},
                              content_type="text/plain")
        self.assertEqual(status, 415)
        self.assertFalse(self.saved.exists())
        status, html = self.call(url + "/")
        self.assertEqual(status, 200)
        for needle in ('id="viewEvm"', 'id="viewOperator"', 'id="evmView"', ">API<", ">MCP / Агенты<",
                       ">Локальные LLM<", "+ Добавить — следующий этап", "API не проверено"):
            self.assertIn(needle, html)
        self.assertIn(".evm-columns{grid-template-columns:1fr}", html, "no narrow-screen layout for the EVM columns")
        self.assertNotIn("innerHTML", html)


if __name__ == "__main__":
    unittest.main()
