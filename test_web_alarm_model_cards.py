"""EVM model cards (CLAUDE-WUA-EVM-MODEL-CARD-UI-001): card data, real role assignments, one server API status.

Oracles are independent of the code under test: a hand-written role table for a Tk ``ui_state.json`` fixture,
``ui_state.load_ui_state`` itself for the Tk reading rules, explicit clock values for the 30-day boundary, the raw
bytes of the stores under a disposable root, raw HTTP bodies and ``sys.modules``. No network and no credentials:
a sentinel secret in the environment must never appear in any answer, store or page.
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from unittest import mock

import model_registry
import ui_state
from model_registry import ModelSpec
from web_alarm import model_cards as mc
from web_alarm.server import ApiError, WebAlarmApi, create_server
from web_alarm.ui import INDEX_HTML

SECRET = "SENTINEL-KEY-7c1d9e0a2b"
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
ROLES = ["chat", "planner", "verifier", "compressor", "doctor_dredd", "executor", "final_review", "context"]
TK = {"main_chat_model_id": "gigachat_2_pro", "planner_model_id": "gigachat_2", "verifier_model_id": "gigachat_3_lightning",
      "compressor_model_id": "gigachat_2", "planner_enabled": True, "final_audit_enabled": False}
EXPECTED_ROLES = {  # hand-written from TK + the web chat choice gigachat_2_max
    "gigachat_2": {"planner": "assigned", "compressor": "assigned"},
    "gigachat_2_max": {"chat": "assigned_pending"},  # chosen, but Ultra Chat sends nothing yet
    "gigachat_2_pro": {"executor": "assigned"},
    "gigachat_3_lightning": {"verifier": "assigned", "doctor_dredd": "assigned", "final_review": "assigned_off"},
    "gigachat_3_pro": {},
    "gigachat_ultra": {},
}


def tree(root: Path) -> dict[str, tuple[int, int, bytes]]:
    return {p.relative_to(root).as_posix(): (os.lstat(p).st_mtime_ns, os.lstat(p).st_size, p.read_bytes())
            for p in sorted(root.rglob("*")) if p.is_file()}


class Clock:
    def __init__(self, value: datetime = T0):
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class FakeChecker:
    """Test double of a future authorised checker; ``live`` decides whether an answer may confirm a model."""

    authorized = True
    reason = None

    def __init__(self, *results):
        self.results = list(results)
        self.requests: list[mc.CheckRequest] = []

    def check(self, request):
        self.requests.append(request)
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


OK = mc.CheckResult(ok=True, live=True, reply="Получено.")


class NoCredentialRead(dict):
    """An environment whose key value cannot be read: presence is the only allowed question."""

    def __getitem__(self, key):
        if key == "GIGACHAT_CREDENTIALS":
            raise AssertionError("the credential value was read")
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key == "GIGACHAT_CREDENTIALS":
            raise AssertionError("the credential value was read")
        return super().get(key, default)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wa_cards_")
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.storage = self.root / "state"
        self.tk = self.root / "tk" / "ui_state.json"
        self.tk.parent.mkdir()
        self.tk.write_text(json.dumps(TK), encoding="utf-8")
        self.env = NoCredentialRead({"GIGACHAT_CREDENTIALS": SECRET, "GIGACHAT_SCOPE": "GIGACHAT_API_PERS"})
        self.clock = Clock()
        self.api = self.make()

    def make(self, checker=None, tk=..., storage=None):
        api = WebAlarmApi(storage or self.storage, tk_state_path=self.tk if tk is ... else tk, api_checker=checker)
        api.model_cards.environ = self.env
        api.model_cards.now = self.clock
        return api

    def cards(self, api=None) -> dict[str, dict]:
        status, data = (api or self.api).dispatch("GET", "/ultra/model-cards")
        self.assertEqual(status, 200)
        return {c["model_id"]: c for c in data["cards"]}

    def card(self, model_id="gigachat_2", api=None):
        return self.cards(api)[model_id]

    def save(self, model_id="gigachat_2", api=None, **body):
        api = api or self.api
        body.setdefault("base_revision", api.dispatch("GET", "/ultra/model-cards")[1]["settings"]["revision"])
        return api.dispatch("POST", f"/ultra/model-cards/{model_id}/settings", body)[1]["card"]

    def check(self, model_id="gigachat_2", api=None):
        return (api or self.api).dispatch("POST", f"/ultra/model-cards/{model_id}/check", {})[1]

    def refused(self, method, path, body=None, api=None):
        with self.assertRaises(ApiError) as caught:
            (api or self.api).dispatch(method, path, body)
        return caught.exception


class CatalogAndRoles(Fixture):
    def test_m01_cards_follow_the_shared_registry_and_reading_writes_nothing(self):
        self.api.dispatch("POST", "/ultra/connections/selection", {"connection_id": "api:gigachat:gigachat_2_max"})
        before, tk_before = tree(self.storage), os.lstat(self.tk)
        sys.modules.pop("gigachat_transport", None)
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
            status, data = self.api.dispatch("GET", "/ultra/model-cards")
        self.assertEqual(status, 200)
        self.assertNotIn("gigachat_transport", sys.modules)
        self.assertEqual([c["model_id"] for c in data["cards"]], [s.model_id for s in model_registry.list_model_specs()])
        self.assertEqual(data["network_calls"], 0)
        self.assertEqual(tree(self.storage), before)
        self.assertEqual((os.lstat(self.tk).st_mtime_ns, os.lstat(self.tk).st_size), (tk_before.st_mtime_ns, tk_before.st_size))
        self.assertEqual([r["role"] for r in data["role_definitions"]], ROLES)
        self.assertTrue(all(r["hint"] for r in data["role_definitions"]))
        self.assertEqual(data["live_check"]["authorized"], False)
        for card in data["cards"]:
            self.assertEqual((card["api"]["color"], card["api"]["reason"]), ("red", "NEVER_CONFIRMED"))
            self.assertEqual((card["description"], card["params_billion"], card["params_source"]), ("", None, "unknown"))

    def test_m02_role_marks_are_the_real_assignments_and_nothing_else(self):
        self.api.dispatch("POST", "/ultra/connections/selection", {"connection_id": "api:gigachat:gigachat_2_max"})
        cards = self.cards()
        for model_id, expected in EXPECTED_ROLES.items():
            with self.subTest(model=model_id):
                states = {r["role"]: r["state"] for r in cards[model_id]["roles"]}
                want = {role: expected.get(role, "not_in_runtime" if role == "context" else "not_assigned") for role in ROLES}
                self.assertEqual(states, want)
        # several roles on one model; Dredd follows the Verifier model and the Planner switch
        self.tk.write_text(json.dumps({**TK, "planner_enabled": False, "final_audit_enabled": True}), encoding="utf-8")
        states = {r["role"]: r["state"] for r in self.card("gigachat_3_lightning")["roles"]}
        self.assertEqual((states["verifier"], states["doctor_dredd"], states["final_review"]), ("assigned", "assigned_off", "assigned"))
        self.assertEqual({r["role"]: r["state"] for r in self.card("gigachat_2")["roles"]}["planner"], "assigned_off")

    def test_m03_tk_reading_mirrors_ui_state_and_the_tk_fallback(self):
        fixtures = {
            "valid": json.dumps(TK).encode(),
            "bom": b"\xef\xbb\xbf" + json.dumps(TK).encode(),
            "wrong_types": json.dumps({"main_chat_model_id": 5, "planner_model_id": "gigachat_2_max", "planner_enabled": "yes",
                                       "final_audit_enabled": False}).encode(),
            "partial": json.dumps({"verifier_model_id": "gigachat_2"}).encode(),
        }
        for name, raw in fixtures.items():
            with self.subTest(fixture=name):
                self.tk.write_bytes(raw)
                with mock.patch.object(ui_state, "STATE_PATH", self.tk):
                    reference = ui_state.load_ui_state()
                ours = mc.read_tk_assignments(self.tk, model_registry)
                self.assertEqual(ours["state"], "SAVED")
                self.assertEqual(ours["values"], {k: reference[k] for k in mc.TK_MODEL_FIELDS + mc.TK_SWITCHES})
        # a saved model the registry does not know (or has disabled): Tk itself falls back to its default
        self.tk.write_text(json.dumps({**TK, "verifier_model_id": "gone_model", "planner_model_id": "gigachat_2"}), encoding="utf-8")
        ours = mc.read_tk_assignments(self.tk, model_registry)
        self.assertEqual(ours["values"]["verifier_model_id"], ui_state.default_ui_state()["verifier_model_id"])
        self.assertEqual(ours["fallbacks"], [{"field": "verifier_model_id", "saved": "gone_model"}])
        disabled = {k: v for k, v in model_registry.MODEL_REGISTRY.items()}
        disabled["gigachat_2"] = ModelSpec("gigachat_2", "GigaChat 2", "gigachat", "GigaChat-2", enabled=False)
        with mock.patch.object(model_registry, "MODEL_REGISTRY", MappingProxyType(disabled)):
            ours = mc.read_tk_assignments(self.tk, model_registry)
        self.assertEqual(ours["values"]["planner_model_id"], ui_state.default_ui_state()["planner_model_id"])

    def test_m04_tk_defaults_and_provider_facts_match_their_owners(self):
        # Read as text: the runtimes and the transport are not imported (they would pull in the network stack).
        repo = Path(model_registry.__file__).resolve().parent
        defaults = ui_state.default_ui_state()
        for module, constant, key in (("compressor_runtime", "DEFAULT_COMPRESSOR_MODEL_ID", "compressor_model_id"),
                                      ("planner_runtime", "DEFAULT_PLANNER_MODEL_ID", "planner_model_id"),
                                      ("verifier_runtime", "DEFAULT_VERIFIER_MODEL_ID", "verifier_model_id")):
            self.assertIn(f'{constant} = "{defaults[key]}"', (repo / f"{module}.py").read_text(encoding="utf-8"))
        transport = (repo / "gigachat_transport.py").read_text(encoding="utf-8")
        provider = mc.BUILTIN_PROVIDERS["gigachat"]
        self.assertIn(f'OAUTH_URL = "{provider.oauth_url}"', transport)
        self.assertIn(f'CHAT_URL = "{provider.api_url}"', transport)
        self.assertIn(f'os.getenv("{provider.credential_env}")', transport)
        self.assertIn(f'os.getenv("{provider.scope_env}", "{provider.default_scope}")', transport)

    def test_m05_unreadable_missing_or_unconnected_tk_settings_never_give_a_check_mark(self):
        for name, prepare in (("not_json", lambda: self.tk.write_bytes(b"{nope")),
                              ("not_object", lambda: self.tk.write_text("[1]", encoding="utf-8")),
                              ("too_large", lambda: self.tk.write_bytes(b" " * (mc.MAX_TK_STATE_BYTES + 1))),
                              ("directory", lambda: (self.tk.unlink(), self.tk.mkdir()))):
            with self.subTest(case=name):
                if self.tk.is_dir():
                    self.tk.rmdir()
                prepare()
                data = self.api.dispatch("GET", "/ultra/model-cards")[1]
                self.assertEqual(data["roles_source"]["state"], "UNREADABLE")
                for card in data["cards"]:
                    marks = {r["role"]: r["state"] for r in card["roles"]}
                    self.assertTrue(all(marks[r] == "unknown" for r in ROLES if r not in ("chat", "context")), marks)
        self.tk.rmdir()
        defaults = self.cards()  # a missing file: Tk runs with its defaults, and says so
        status = self.api.dispatch("GET", "/ultra/model-cards")[1]["roles_source"]["state"]
        self.assertEqual(status, "DEFAULTS")
        ultra = {r["role"]: r["state"] for r in defaults[ui_state.default_ui_state()["main_chat_model_id"]]["roles"]}
        self.assertEqual(ultra["executor"], "assigned")
        unconnected = self.make(tk=None)
        data = unconnected.dispatch("GET", "/ultra/model-cards")[1]
        self.assertEqual(data["roles_source"]["state"], "NOT_CONNECTED")
        self.assertFalse(any(r["state"].startswith("assigned") for c in data["cards"] for r in c["roles"] if r["role"] != "chat"))

    def test_m06_an_instance_on_its_own_storage_reads_tk_settings_only_from_a_given_file(self):
        self.assertIsNone(WebAlarmApi(self.root / "own").model_cards.tk_state_path)
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.root / "la"), "APPDATA": str(self.root / "la")}):
            standard = WebAlarmApi(None)
        self.assertEqual(standard.model_cards.tk_state_path, Path(ui_state.STATE_PATH))
        self.assertTrue(standard.storage_root.is_relative_to(self.root))


class ApiStatus(Fixture):
    def test_m07_thirty_day_boundary_restart_and_the_same_status_everywhere(self):
        api = self.make(FakeChecker(OK))
        self.assertEqual(self.check(api=api)["outcome"], "CONFIRMED")
        for delta, color in ((timedelta(0), "green"), (timedelta(days=30), "green"), (timedelta(days=30, seconds=1), "orange"),
                             (timedelta(days=400), "orange"), (timedelta(minutes=-4), "green"), (timedelta(minutes=-10), "red")):
            with self.subTest(delta=str(delta)):
                self.clock.value = T0 + delta
                restarted = self.make()  # a new server over the same storage
                card = self.card(api=restarted)
                self.assertEqual(card["api"]["color"], color)
                self.assertEqual(card["api"]["last_success_at"], T0.isoformat())
                self.assertEqual(self.check(api=restarted)["card"]["api"], card["api"], "check answer and card disagree")
        self.assertEqual(self.card()["api"]["reason"], "TIMESTAMP_INVALID")

    def test_m08_card_text_and_profile_limits_never_reset_the_status_but_settings_do(self):
        api = self.make(FakeChecker(OK))
        self.check(api=api)
        self.save(description="Сильная", params_billion=390, profile={"timeout_seconds": 90, "diagnostic_limit_chars": 300})
        self.assertEqual(self.card()["api"]["color"], "green")
        self.clock.value = T0 + timedelta(days=11)
        self.assertEqual(self.card()["api"]["color"], "green")
        self.save(profile={"freshness_days": 10})
        self.assertEqual((self.card()["api"]["color"], self.card()["api"]["reason"]), ("orange", "STALE"))
        self.save(profile={"freshness_days": 30})
        changes = {
            "credential_removed": lambda: self.env.pop("GIGACHAT_CREDENTIALS"),
            "scope_changed": lambda: self.env.__setitem__("GIGACHAT_SCOPE", "GIGACHAT_API_B2B"),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                saved = dict(self.env)
                change()
                self.assertEqual((self.card()["api"]["color"], self.card()["api"]["reason"]), ("red", "SETTINGS_CHANGED"))
                self.env.clear(); self.env.update(saved)
                self.assertEqual(self.card()["api"]["color"], "green")
        moved = dict(model_registry.MODEL_REGISTRY)
        moved["gigachat_2"] = ModelSpec("gigachat_2", "GigaChat 2", "gigachat", "GigaChat-2-New")
        with mock.patch.object(model_registry, "MODEL_REGISTRY", MappingProxyType(moved)):
            self.assertEqual(self.card()["api"]["reason"], "SETTINGS_CHANGED")
        settings = json.loads((self.storage / "ultra" / "model_settings.json").read_text(encoding="utf-8"))
        settings["profiles"]["gigachat-work"] = {"provider": "gigachat", "title": "Рабочий", "credential_revision": 0}
        settings["revision"] += 1
        (self.storage / "ultra" / "model_settings.json").write_text(json.dumps(settings), encoding="utf-8")
        self.save(profile_id="gigachat-work")
        self.assertEqual(self.card()["api"]["reason"], "SETTINGS_CHANGED")
        self.assertEqual(self.card("gigachat_2_max")["api"]["reason"], "NEVER_CONFIRMED", "each model is confirmed separately")
        self.save(profile_id="gigachat-default")
        self.assertEqual(self.card()["api"]["color"], "green", "the confirmed settings are back")

    def test_m09_failures_simulations_and_checker_errors(self):
        failed = mc.CheckResult(ok=False, live=True, error_code="http_401", error_message="Authorization: Basic " + SECRET)
        api = self.make(FakeChecker(OK, failed, mc.CheckResult(ok=True, live=False, reply="Имитация"), RuntimeError(SECRET), OK))
        self.check(api=api)
        self.clock.value = T0 + timedelta(minutes=1)
        answer = self.check(api=api)
        self.assertEqual((answer["outcome"], answer["card"]["api"]["reason"]), ("FAILED", "LAST_CHECK_FAILED"))
        self.assertNotIn(SECRET, json.dumps(answer, ensure_ascii=False))
        self.assertIn("[скрыто]", answer["text"])
        self.clock.value = T0 + timedelta(minutes=2)
        stored = (self.storage / "ultra" / "api_checks.json").read_bytes()
        simulated = self.check(api=api)
        self.assertEqual((simulated["outcome"], simulated["card"]["api"]["color"]), ("SIMULATED", "red"))
        self.assertEqual((self.storage / "ultra" / "api_checks.json").read_bytes(), stored, "a simulation was recorded")
        crashed = self.check(api=api)
        self.assertEqual((crashed["outcome"], crashed["card"]["api"]["last_failure"]["code"]), ("FAILED", "checker_error"))
        self.assertNotIn(SECRET, json.dumps(crashed, ensure_ascii=False))
        self.clock.value = T0 + timedelta(minutes=3)
        self.assertEqual(self.check(api=api)["card"]["api"]["color"], "green", "a newer confirmation wins")
        request = api.model_cards.checker.requests[0]
        self.assertEqual((request.message, request.provider_model_id, request.timeout_seconds),
                         (mc.TEST_MESSAGE, "GigaChat-2", mc.DEFAULT_TIMEOUT_SECONDS))

    def test_m10_unauthorised_default_sends_nothing_and_refusals(self):
        before = tree(self.storage)
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
            answer = self.check()
        self.assertEqual((answer["outcome"], answer["network_calls"]), ("LIVE_CHECK_NOT_AUTHORIZED", 0))
        self.assertEqual(answer["card"]["api"]["reason"], "NEVER_CONFIRMED")
        self.assertEqual(tree(self.storage), before)
        disabled = dict(model_registry.MODEL_REGISTRY)
        disabled["gigachat_2"] = ModelSpec("gigachat_2", "GigaChat 2", "gigachat", "GigaChat-2", enabled=False)
        with mock.patch.object(model_registry, "MODEL_REGISTRY", MappingProxyType(disabled)):
            self.assertEqual(self.card()["api"]["reason"], "REGISTRY_DISABLED")
            self.assertEqual(self.refused("POST", "/ultra/model-cards/gigachat_2/check", {}).code, "check_refused")
        with mock.patch.object(mc.importlib.util, "find_spec", return_value=None):
            self.assertEqual(self.card()["api"]["reason"], "ADAPTER_MISSING")
            self.assertEqual(self.refused("POST", "/ultra/model-cards/gigachat_2/check", {}).code, "check_refused")
        self.assertEqual(self.refused("POST", "/ultra/model-cards/nope/check", {}).code, "unknown_model")
        self.assertEqual(self.refused("POST", "/ultra/model-cards/gigachat_2/check", {"message": "hi"}).code, "invalid_model_card_request")
        self.assertEqual(self.refused("GET", "/ultra/model-cards/gigachat_2/check").status, 405)

    def test_m11_damaged_checks_are_red_kept_for_diagnosis_and_replaced_by_the_next_answer(self):
        path = self.storage / "ultra" / "api_checks.json"
        path.parent.mkdir(parents=True)
        for damaged in (b"{not json", json.dumps({"schema": "other", "version": 1, "checks": {}}).encode(),
                        json.dumps({"schema": mc.CHECKS_SCHEMA, "version": 1, "checks": []}).encode()):
            with self.subTest(damaged=damaged[:20]):
                path.write_bytes(damaged)
                cards = self.cards()
                self.assertTrue(all(c["api"]["reason"] == "STATE_CORRUPT" for c in cards.values()))
        bad_time = {"schema": mc.CHECKS_SCHEMA, "version": 1, "checks": {"api:gigachat:gigachat_2": {
            "settings_version": self.card()["settings_version"], "last_success_at": "yesterday"}}}
        path.write_text(json.dumps(bad_time), encoding="utf-8")
        self.assertEqual(self.card()["api"]["reason"], "TIMESTAMP_INVALID")
        path.write_bytes(b"{not json")
        self.check(api=self.make(FakeChecker(OK)))
        kept = [p for p in path.parent.iterdir() if p.name.startswith("api_checks.json.corrupt-")]
        self.assertEqual([p.read_bytes() for p in kept], [b"{not json"])
        self.assertEqual(self.card()["api"]["color"], "green")

    def test_m12_an_ordinary_answer_refreshes_only_with_the_exact_settings(self):
        cards = self.api.model_cards
        version = self.card()["settings_version"]
        self.assertFalse(cards.record_chat_success("gigachat_2", "0" * 16))
        self.assertFalse((self.storage / "ultra" / "api_checks.json").exists())
        self.assertTrue(cards.record_chat_success("gigachat_2", version))
        api = self.card()["api"]
        self.assertEqual((api["color"], api["last_success_source"]), ("green", "chat"))


class Settings(Fixture):
    def test_m13_card_data_is_validated_persisted_and_kept_apart_from_status_and_secrets(self):
        text = "Строка 1\r\nСтрока 2 — " + "я" * 400
        card = self.save(description=text[:500], params_billion=390)
        self.assertEqual((card["description"], card["params_billion"], card["params_source"]), (text[:500].replace("\r\n", "\n"), 390, "user"))
        self.assertEqual(self.card(api=self.make())["description"], text[:500].replace("\r\n", "\n"), "lost after restart")
        self.save(description="я" * 500)
        for body, field in (({"description": "я" * 501}, "description"), ({"description": "a\x00b"}, "control"),
                            ({"description": 5}, "description"), ({"params_billion": 0}, "params"), ({"params_billion": -1}, "params"),
                            ({"params_billion": True}, "params"), ({"params_billion": float("nan")}, "params"),
                            ({"params_billion": "390"}, "params"), ({"params_billion": 100001}, "params"),
                            ({"profile": {"freshness_days": 0}}, "freshness"), ({"profile": {"timeout_seconds": 999}}, "timeout"),
                            ({"profile": {"api_url": "http://evil"}}, "profile"), ({"api_url": "http://evil"}, "unknown"),
                            ({"profile_id": "nope"}, "profile_id")):
            with self.subTest(field=field, body=str(body)[:40]):
                revision = self.api.dispatch("GET", "/ultra/model-cards")[1]["settings"]["revision"]
                error = self.refused("POST", "/ultra/model-cards/gigachat_2/settings", {"base_revision": revision, **body})
                self.assertEqual((error.status, error.code), (400, "invalid_model_card_request"))
        stored = (self.storage / "ultra" / "model_settings.json").read_text(encoding="utf-8")
        self.assertNotIn(SECRET, stored)
        self.assertNotIn("last_success", stored)
        self.assertFalse((self.storage / "ultra" / "api_checks.json").exists(), "card data went into the status store")

    def test_m14_concurrent_saves_lose_nothing_silently(self):
        revision = self.api.dispatch("GET", "/ultra/model-cards")[1]["settings"]["revision"]
        barrier, results = threading.Barrier(2), []

        def save(text):
            api = self.make()
            barrier.wait()
            try:
                api.dispatch("POST", "/ultra/model-cards/gigachat_2/settings", {"base_revision": revision, "description": text})
                results.append(("ok", text))
            except ApiError as exc:
                results.append((exc.code, text))

        threads = [threading.Thread(target=save, args=(t,)) for t in ("первый", "второй")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        self.assertEqual(sorted(r[0] for r in results), ["ok", "settings_revision_conflict"])
        winner = next(t for s, t in results if s == "ok")
        self.assertEqual(self.card()["description"], winner)

    def test_m15_damaged_settings_are_reported_kept_and_replaced_only_on_purpose(self):
        path = self.storage / "ultra" / "model_settings.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\xff\xfe broken")
        data = self.api.dispatch("GET", "/ultra/model-cards")[1]
        self.assertEqual((data["settings"]["state"], data["settings"]["revision"]), ("CORRUPT", None))
        self.assertEqual(self.refused("POST", "/ultra/model-cards/gigachat_2/settings", {"base_revision": 0, "description": "x"}).code,
                         "settings_revision_conflict")
        self.api.dispatch("POST", "/ultra/model-cards/gigachat_2/settings", {"base_revision": None, "description": "x"})
        kept = [p.read_bytes() for p in path.parent.iterdir() if p.name.startswith("model_settings.json.corrupt-")]
        self.assertEqual(kept, [b"\xff\xfe broken"])
        self.assertEqual((self.card()["description"], self.api.dispatch("GET", "/ultra/model-cards")[1]["settings"]["revision"]), ("x", 1))
        settings = json.loads(path.read_text(encoding="utf-8"))
        settings["models"]["gigachat_3_pro"] = {"description": 7}
        settings["providers"]["deepvendor"] = {"display_name": "Другой провайдер", "country": "Китай", "adapter": "os"}
        path.write_text(json.dumps(settings), encoding="utf-8")
        data = self.api.dispatch("GET", "/ultra/model-cards")[1]
        self.assertEqual(data["settings"]["ignored"], 1, "an invalid entry is skipped, not trusted")
        provider = next(p for p in data["providers"] if p["provider_id"] == "deepvendor")
        self.assertEqual((provider["adapter"], provider["adapter_state"], provider["source"]), (None, "MISSING", "user"),
                         "a manual entry never names an adapter module")


API_IDS = [f"api:{s.provider}:{s.model_id}" for s in model_registry.list_model_specs()]


class BoardView(Fixture):
    """CLAUDE-WUA-EVM-COMPACT-LAYOUT-001: manual order of the EVM columns and favourites, kept apart from everything else."""

    def view(self, api=None):
        return (api or self.api).dispatch("GET", "/ultra/model-cards")[1]["view"]

    def put(self, section, order, api=None, revision=...):
        api = api or self.api
        base = self.view(api)["revision"] if revision is ... else revision
        return api.dispatch("POST", "/ultra/model-cards/view", {"base_revision": base, "section": section, "order": order})[1]["view"]

    def extra_columns(self, mcp=(), local=()):
        from web_alarm.ultra_connections import UltraConnections
        real = UltraConnections.catalog

        def catalog(this):
            data = real(this)
            data["columns"]["mcp_agents"] = {"state": "AVAILABLE", "connections": [{"connection_id": x} for x in mcp]}
            data["columns"]["local_llm"] = {"state": "AVAILABLE", "connections": [{"connection_id": x} for x in local]}
            return data
        patcher = mock.patch.object(UltraConnections, "catalog", catalog)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_m18_order_and_favourites_persist_and_touch_nothing_else(self):
        self.api.dispatch("POST", "/ultra/connections/selection", {"connection_id": "api:gigachat:gigachat_2_max"})
        self.save(description="Описание")
        first = self.view()
        self.assertEqual((first["state"], first["revision"], first["sections"]["api"], first["sections"]["favorites"]),
                         ("EMPTY", 0, API_IDS, []))
        others = {name: (self.storage / "ultra" / name).read_bytes() for name in ("model_settings.json", "connections.json")}
        tk_before = (os.lstat(self.tk).st_mtime_ns, self.tk.read_bytes())
        order = list(reversed(API_IDS))
        self.put("api", order)
        self.put("favorites", [API_IDS[2], API_IDS[0]])
        restarted = self.make()
        view = self.view(restarted)
        self.assertEqual((view["state"], view["revision"], view["sections"]["api"], view["sections"]["favorites"]),
                         ("SAVED", 2, order, [API_IDS[2], API_IDS[0]]))
        self.assertEqual({name: (self.storage / "ultra" / name).read_bytes() for name in others}, others)
        self.assertFalse((self.storage / "ultra" / "api_checks.json").exists())
        self.assertEqual((os.lstat(self.tk).st_mtime_ns, self.tk.read_bytes()), tk_before)
        self.assertEqual([c["model_id"] for c in self.cards(restarted).values()], [s.model_id for s in model_registry.list_model_specs()],
                         "the registry order of the cards is not changed by the board order")
        stored = json.loads((self.storage / "ultra" / "evm_view.json").read_text(encoding="utf-8"))
        self.assertEqual(set(stored), {"schema", "version", "revision", "sections"}, "only references are stored")
        self.assertNotIn(SECRET, json.dumps(stored))

    def test_m19_requests_are_checked_before_anything_is_written(self):
        for body, code in (({"section": "api", "order": API_IDS, "extra": 1}, "invalid_model_card_request"),
                           ({"section": "nope", "order": []}, "invalid_model_card_request"),
                           ({"section": "api", "order": "x"}, "invalid_model_card_request"),
                           ({"section": "api", "order": ["not an id"]}, "invalid_model_card_request"),
                           ({"section": "api", "order": API_IDS + [API_IDS[0]]}, "invalid_model_card_request"),
                           ({"section": "api", "order": ["local:gigachat:gigachat_2"] + API_IDS[1:]}, "invalid_model_card_request"),
                           ({"section": "api", "order": API_IDS[:-1]}, "settings_revision_conflict"),
                           ({"section": "api", "order": API_IDS[:-1] + ["api:gigachat:gone_model"]}, "settings_revision_conflict"),
                           ({"section": "favorites", "order": ["api:gigachat:gone_model"]}, "settings_revision_conflict")):
            with self.subTest(code=code, body=str(body)[:60]):
                error = self.refused("POST", "/ultra/model-cards/view", {"base_revision": 0, **body})
                self.assertEqual(error.code, code)
        self.assertFalse((self.storage / "ultra" / "evm_view.json").exists())
        self.put("api", API_IDS)
        error = self.refused("POST", "/ultra/model-cards/view", {"base_revision": 0, "section": "favorites", "order": []})
        self.assertEqual(error.code, "settings_revision_conflict", "a stale revision is refused")
        self.assertEqual(self.refused("GET", "/ultra/model-cards/view").status, 405)

    def test_m20_new_and_removed_entries_keep_preferences_and_never_duplicate(self):
        self.put("api", list(reversed(API_IDS)))
        self.put("favorites", [API_IDS[1]])
        reduced = {k: v for k, v in model_registry.MODEL_REGISTRY.items() if k != "gigachat_2_max"}
        with mock.patch.object(model_registry, "MODEL_REGISTRY", MappingProxyType(reduced)):
            view = self.view()
            self.assertNotIn(API_IDS[1], view["sections"]["api"])
            self.assertEqual((view["sections"]["favorites"], view["hidden"]), ([], 2))
            self.put("api", view["sections"]["api"])  # saving while the model is absent keeps its stored place
            self.put("favorites", [API_IDS[0]])  # editing the favourites meanwhile must not drop the absent one
        grown = dict(model_registry.MODEL_REGISTRY)
        grown["zz_new_model"] = ModelSpec("zz_new_model", "New", "gigachat", "New-1")
        with mock.patch.object(model_registry, "MODEL_REGISTRY", MappingProxyType(grown)):
            view = self.view()
            self.assertEqual(view["sections"]["api"][-1], "api:gigachat:zz_new_model", "a new model is appended")
            self.assertEqual(len(view["sections"]["api"]), len(set(view["sections"]["api"])), "no duplicates")
            self.assertIn(API_IDS[1], view["sections"]["api"], "a model that came back is shown again")
            self.assertEqual(view["sections"]["favorites"], [API_IDS[0], API_IDS[1]], "its favourite came back too")
        self.extra_columns(mcp=["mcp:prov:gigachat_2"], local=["local:prov:gigachat_2", "local:prov:other"])
        view = self.view()
        self.assertEqual((view["sections"]["mcp"], view["sections"]["local"]), (["mcp:prov:gigachat_2"], ["local:prov:gigachat_2", "local:prov:other"]))
        self.put("local", ["local:prov:other", "local:prov:gigachat_2"])
        self.put("favorites", [API_IDS[1], "local:prov:gigachat_2", "mcp:prov:gigachat_2"])
        view = self.view()
        self.assertEqual(view["sections"]["local"], ["local:prov:other", "local:prov:gigachat_2"])
        self.assertEqual(view["sections"]["favorites"], [API_IDS[1], "local:prov:gigachat_2", "mcp:prov:gigachat_2"],
                         "the same tail under different kinds is three different entries")
        self.assertEqual(self.refused("POST", "/ultra/model-cards/view", {"base_revision": view["revision"], "section": "mcp",
                                                                           "order": ["local:prov:other"]}).code, "invalid_model_card_request")

    def test_m21_concurrent_saves_and_a_damaged_file(self):
        base, barrier, results = self.view()["revision"], threading.Barrier(2), []

        def save(order):
            api = self.make()
            barrier.wait()
            try:
                api.dispatch("POST", "/ultra/model-cards/view", {"base_revision": base, "section": "api", "order": order})
                results.append(("ok", order))
            except ApiError as exc:
                results.append((exc.code, order))
        threads = [threading.Thread(target=save, args=(o,)) for o in (list(reversed(API_IDS)), API_IDS[1:] + API_IDS[:1])]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        self.assertEqual(sorted(r[0] for r in results), ["ok", "settings_revision_conflict"])
        self.assertEqual(self.view()["sections"]["api"], next(o for s, o in results if s == "ok"))
        path = self.storage / "ultra" / "evm_view.json"
        for damaged in (b"{nope", json.dumps({"schema": mc.VIEW_SCHEMA, "version": 1, "revision": True, "sections": {}}).encode(),
                        json.dumps({"schema": mc.VIEW_SCHEMA, "version": 1, "revision": 3, "sections": {"api": [API_IDS[0], API_IDS[0]]}}).encode(),
                        json.dumps({"schema": mc.VIEW_SCHEMA, "version": 1, "revision": 3, "sections": {"favorites": ["../../x"]}}).encode()):
            with self.subTest(damaged=damaged[:30]):
                path.write_bytes(damaged)
                view = self.view()
                self.assertEqual((view["state"], view["revision"], view["sections"]["api"], view["sections"]["favorites"]),
                                 ("CORRUPT", None, API_IDS, []))
        self.assertEqual(self.refused("POST", "/ultra/model-cards/view", {"base_revision": 3, "section": "api", "order": API_IDS}).code,
                         "settings_revision_conflict")
        self.put("favorites", [API_IDS[0]], revision=None)
        kept = [p.read_bytes() for p in path.parent.iterdir() if p.name.startswith("evm_view.json.corrupt-")]
        self.assertEqual(len(kept), 1, "the damaged file is kept for diagnosis")
        self.assertEqual((self.view()["state"], self.view()["revision"], self.view()["sections"]["favorites"]), ("SAVED", 1, [API_IDS[0]]))


class BoardLayout(Fixture):
    """CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001: pinned EVM windows, one per entry, kept in the view file with their own
    revision; the column order, the favourites and their base_revision behave exactly as before."""

    view, put, extra_columns = BoardView.view, BoardView.put, BoardView.extra_columns

    def win(self, connection_id, x=None, y=None, api=None):
        window = None if x is None else {"x": x, "y": y}
        return (api or self.api).dispatch("POST", "/ultra/model-cards/layout", {"connection_id": connection_id, "window": window})[1]["view"]

    def stored(self):
        return json.loads((self.storage / "ultra" / "evm_view.json").read_text(encoding="utf-8"))

    def test_m22_windows_persist_restart_and_touch_nothing_else(self):
        first = self.view()["layout"]
        self.assertEqual(first, {"state": "EMPTY", "revision": 0, "windows": [], "hidden": 0})
        self.put("favorites", [API_IDS[0]])  # an order saved before any window: the old schema exactly
        self.assertEqual(set(self.stored()), {"schema", "version", "revision", "sections"}, "no layout until a window is saved")
        others = {name: (self.storage / "ultra" / name).read_bytes() for name in ("connections.json",) if (self.storage / "ultra" / name).exists()}
        tk_before = (os.lstat(self.tk).st_mtime_ns, self.tk.read_bytes())
        self.win(API_IDS[0], 100, 200)
        self.win(API_IDS[1], 500, 120)
        view = self.win(API_IDS[2], 900, 300)
        self.assertEqual((view["state"], view["revision"]), ("SAVED", 1), "a window never moves the board revision")
        self.assertEqual(view["layout"]["windows"], [{"connection_id": API_IDS[0], "x": 100, "y": 200},
                                                     {"connection_id": API_IDS[1], "x": 500, "y": 120},
                                                     {"connection_id": API_IDS[2], "x": 900, "y": 300}])
        self.assertEqual(view["layout"]["revision"], 3)
        view = self.win(API_IDS[0], -40, 75)  # a move raises the window: the last one is on top
        self.assertEqual([(w["connection_id"], w["x"], w["y"]) for w in view["layout"]["windows"]],
                         [(API_IDS[1], 500, 120), (API_IDS[2], 900, 300), (API_IDS[0], -40, 75)])
        view = self.win(API_IDS[1])  # closed with its own «×»
        self.assertEqual([w["connection_id"] for w in view["layout"]["windows"]], [API_IDS[2], API_IDS[0]])
        before = (self.storage / "ultra" / "evm_view.json").read_bytes()
        self.assertEqual(self.win(API_IDS[1])["layout"]["revision"], 5, "closing a closed window changes nothing")
        self.assertEqual((self.storage / "ultra" / "evm_view.json").read_bytes(), before)
        restarted = self.make()
        again = self.view(restarted)
        self.assertEqual((again["layout"], again["sections"]["favorites"]),
                         ({"state": "SAVED", "revision": 5, "hidden": 0, "windows": [{"connection_id": API_IDS[2], "x": 900, "y": 300},
                                                                                       {"connection_id": API_IDS[0], "x": -40, "y": 75}]},
                          [API_IDS[0]]))
        self.put("api", list(reversed(API_IDS)), api=restarted)  # an order change keeps the windows and their revision
        stored = self.stored()
        self.assertEqual((stored["revision"], stored["layout"]["revision"], len(stored["layout"]["windows"])), (2, 5, 2))
        self.assertEqual(set(stored), {"schema", "version", "revision", "sections", "layout"})
        self.assertEqual(set(stored["layout"]), {"revision", "windows"})
        self.assertTrue(all(set(w) == {"connection_id", "x", "y"} for w in stored["layout"]["windows"]), "only references and pixels")
        text = json.dumps(stored, ensure_ascii=False)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("GigaChat", text, "no copy of registry records (names, provider model ids)")
        self.assertEqual({name: (self.storage / "ultra" / name).read_bytes() for name in others}, others)
        self.assertFalse((self.storage / "ultra" / "model_settings.json").exists())
        self.assertEqual((os.lstat(self.tk).st_mtime_ns, self.tk.read_bytes()), tk_before)

    def test_m23_layout_requests_are_checked_before_anything_is_written(self):
        cases = (({"connection_id": API_IDS[0], "window": {"x": 1, "y": 2}, "extra": 1}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0]}, "invalid_model_card_request"),
                 ({"window": None}, "invalid_model_card_request"),
                 ({"connection_id": "not an id", "window": None}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": "x"}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": 1}}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": 1, "y": 2, "z": 3}}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": 1.5, "y": 2}}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": True, "y": 2}}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": "10", "y": 2}}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": 100_001, "y": 2}}, "invalid_model_card_request"),
                 ({"connection_id": API_IDS[0], "window": {"x": 0, "y": -100_001}}, "invalid_model_card_request"),
                 ({"connection_id": "api:gigachat:gone_model", "window": {"x": 1, "y": 2}}, "settings_revision_conflict"))
        for body, code in cases:
            with self.subTest(code=code, body=str(body)[:70]):
                self.assertEqual(self.refused("POST", "/ultra/model-cards/layout", body).code, code)
        self.assertEqual(self.refused("POST", "/ultra/model-cards/layout", ["x"]).status, 400)
        self.assertEqual(self.refused("GET", "/ultra/model-cards/layout").status, 405)
        self.assertFalse((self.storage / "ultra" / "evm_view.json").exists(), "nothing was written")
        self.assertEqual(self.win("api:gigachat:gone_model")["layout"]["windows"], [], "closing an unknown window is harmless")
        self.assertFalse((self.storage / "ultra" / "evm_view.json").exists())
        many = [f"mcp:prov:m{i:02d}" for i in range(mc.MAX_WINDOWS + 1)]
        self.extra_columns(mcp=many)
        for i, connection_id in enumerate(many[:-1]):
            self.win(connection_id, i, i)
        self.assertEqual(self.refused("POST", "/ultra/model-cards/layout", {"connection_id": many[-1], "window": {"x": 0, "y": 0}}).code,
                         "invalid_model_card_request", "at most MAX_WINDOWS windows")
        self.assertEqual(len(self.view()["layout"]["windows"]), mc.MAX_WINDOWS)
        self.assertEqual(len(self.win(many[0], 5, 5)["layout"]["windows"]), mc.MAX_WINDOWS, "moving an open one is still possible")

    def test_m24_two_pages_and_concurrent_writes_lose_no_window(self):
        page_a, page_b = self.make(), self.make()
        board = self.view(page_b)["revision"]
        self.win(API_IDS[0], 10, 10, api=page_a)
        self.win(API_IDS[1], 20, 20, api=page_b)
        self.win(API_IDS[0], 30, 30, api=page_a)
        view = self.win(API_IDS[0], 40, 40, api=page_b)  # the same window from the other page: the last move wins
        self.assertEqual([(w["connection_id"], w["x"]) for w in view["layout"]["windows"]], [(API_IDS[1], 20), (API_IDS[0], 40)])
        self.put("api", list(reversed(API_IDS)), api=page_b, revision=board)  # the order revision page B read is still valid
        barrier, errors = threading.Barrier(len(API_IDS)), []

        def open_window(i):
            api = self.make()
            barrier.wait()
            try:
                self.win(API_IDS[i], 100 * i, 50, api=api)
            except ApiError as exc:
                errors.append(exc.code)
        threads = [threading.Thread(target=open_window, args=(i,)) for i in range(len(API_IDS))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        self.assertEqual(errors, [])
        windows = self.view()["layout"]["windows"]
        self.assertEqual(sorted(w["connection_id"] for w in windows), sorted(API_IDS), "every page kept its window")
        self.assertEqual({w["connection_id"]: w["x"] for w in windows}, {c: 100 * i for i, c in enumerate(API_IDS)})
        self.assertEqual(self.view()["layout"]["revision"], 4 + len(API_IDS))

    def test_m25_damaged_or_absent_windows_never_break_the_board(self):
        order = list(reversed(API_IDS))
        self.put("api", order)
        path = self.storage / "ultra" / "evm_view.json"
        good = self.stored()
        for layout in ("x", {"revision": -1, "windows": []}, {"revision": 1, "windows": [], "extra": 1}, {"revision": True, "windows": []},
                       {"revision": 1, "windows": [{"connection_id": "../x", "x": 1, "y": 1}]},
                       {"revision": 1, "windows": [{"connection_id": API_IDS[0], "x": 1.5, "y": 1}]},
                       {"revision": 1, "windows": [{"connection_id": API_IDS[0], "x": 1, "y": 1, "name": "GigaChat"}]},
                       {"revision": 1, "windows": [{"connection_id": API_IDS[0], "x": 1, "y": 1}] * 2},
                       {"revision": 1, "windows": [{"connection_id": f"mcp:p:{i}", "x": 1, "y": 1} for i in range(mc.MAX_WINDOWS + 1)]}):
            with self.subTest(layout=str(layout)[:50]):
                path.write_text(json.dumps({**good, "layout": layout}), encoding="utf-8")
                view = self.view()
                self.assertEqual((view["state"], view["revision"], view["sections"]["api"]), ("SAVED", 1, order), "the board stays")
                self.assertEqual(view["layout"], {"state": "CORRUPT", "revision": None, "windows": [], "hidden": 0})
        view = self.win(API_IDS[2], 7, 8)  # the next window starts the layout again; the damaged file is kept aside
        self.assertEqual((view["sections"]["api"], view["revision"], view["layout"]["revision"], view["layout"]["state"]), (order, 1, 1, "SAVED"))
        self.assertEqual(len([p for p in path.parent.iterdir() if p.name.startswith("evm_view.json.corrupt-")]), 1)
        path.write_text(json.dumps({**self.stored(), "layout": "x"}), encoding="utf-8")
        self.put("favorites", [API_IDS[0]])  # an order save over a damaged layout keeps the file aside too
        self.assertEqual((len([p for p in path.parent.iterdir() if p.name.startswith("evm_view.json.corrupt-")]), "layout" in self.stored()), (2, False))
        self.win(API_IDS[1], 1, 1)
        self.win(API_IDS[3], 2, 2)
        reduced = {k: v for k, v in model_registry.MODEL_REGISTRY.items() if k != API_IDS[1].rsplit(":", 1)[1]}
        with mock.patch.object(model_registry, "MODEL_REGISTRY", MappingProxyType(reduced)):
            layout = self.view()["layout"]
            self.assertEqual(([w["connection_id"] for w in layout["windows"]], layout["hidden"]), ([API_IDS[3]], 1), "no window of an absent model")
            self.assertEqual(self.refused("POST", "/ultra/model-cards/layout", {"connection_id": API_IDS[1], "window": {"x": 0, "y": 0}}).code,
                             "settings_revision_conflict")
            self.win(API_IDS[4], 3, 3)  # changing another window meanwhile keeps the absent one
        self.assertEqual([w["connection_id"] for w in self.view()["layout"]["windows"]], [API_IDS[1], API_IDS[3], API_IDS[4]], "it comes back")
        path.write_bytes(b"{nope")
        self.assertEqual((self.view()["state"], self.view()["layout"]["state"]), ("CORRUPT", "CORRUPT"))
        view = self.win(API_IDS[0], 9, 9)
        self.assertEqual((view["state"], view["revision"], [w["connection_id"] for w in view["layout"]["windows"]]), ("SAVED", 0, [API_IDS[0]]))
        self.assertEqual(len([p for p in path.parent.iterdir() if p.name.startswith("evm_view.json.corrupt-")]), 3)


class Http(Fixture):
    def serve(self):
        server = create_server(self.api, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.port = server.server_address[1]
        self.host = f"127.0.0.1:{self.port}"

    def request(self, method, path, headers=None, body=b""):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for key, value in {"Host": self.host, **(headers or {})}.items():
                conn.putheader(key, value)
            if method == "POST":
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Content-Length", str(len(body)))
            conn.endheaders(body if method == "POST" else None)
            response = conn.getresponse()
            return response.status, response.read().decode("utf-8")
        finally:
            conn.close()

    def test_m16_http_only_for_the_local_page_and_no_secret_anywhere(self):
        self.serve()
        origin = {"Origin": "http://" + self.host}
        cases = [
            ("GET", "/ultra/model-cards", {}, b"", 200, None),
            ("GET", "/ultra/model-cards", {"Origin": "http://evil.example"}, b"", 403, "model_cards_forbidden"),
            ("GET", "/ultra/model-cards", {"Host": "evil.example"}, b"", 403, "model_cards_forbidden"),
            ("GET", "/ultra/model-cards", {"Sec-Fetch-Site": "cross-site"}, b"", 403, "model_cards_forbidden"),
            ("POST", "/ultra/model-cards/gigachat_2/check", {}, b"{}", 403, "model_cards_forbidden"),
            ("POST", "/ultra/model-cards/gigachat_2/check", origin, b"{}", 200, None),
            ("POST", "/ultra/model-cards/gigachat_2/settings", origin, json.dumps({"base_revision": 0, "description": "Быстрая"}).encode(), 200, None),
            ("GET", "/ultra/model-cards?x=1", {}, b"", 400, "invalid_model_card_request"),
            ("POST", "/ultra/model-cards", origin, b"{}", 405, "method_not_allowed"),
            ("POST", "/ultra/model-cards/nope/settings", origin, b'{"base_revision": 1}', 404, "unknown_model"),
            ("POST", "/ultra/model-cards/view", {}, b'{"base_revision": 0, "section": "favorites", "order": []}', 403, "model_cards_forbidden"),
            ("POST", "/ultra/model-cards/view", {"Origin": "http://evil.example"}, b'{"base_revision": 0, "section": "favorites", "order": []}', 403, "model_cards_forbidden"),
            ("POST", "/ultra/model-cards/view", origin, b'{"base_revision": 0, "section": "favorites", "order": []}', 200, None),
            ("POST", "/ultra/model-cards/layout", {}, b'{"connection_id": "api:gigachat:gigachat_2", "window": {"x": 1, "y": 2}}', 403, "model_cards_forbidden"),
            ("POST", "/ultra/model-cards/layout", {"Origin": "http://evil.example"}, b'{"connection_id": "api:gigachat:gigachat_2", "window": {"x": 1, "y": 2}}', 403, "model_cards_forbidden"),
            ("POST", "/ultra/model-cards/layout", origin, b'{"connection_id": "api:gigachat:gigachat_2", "window": {"x": 1, "y": 2}}', 200, None),
            ("GET", "/ultra/model-cards/layout", {}, b"", 405, "method_not_allowed"),
        ]
        bodies = []
        for method, path, headers, body, status, code in cases:
            with self.subTest(method=method, path=path, headers=sorted(headers)):
                got, text = self.request(method, path, headers, body)
                self.assertEqual(got, status, text[:200])
                if code:
                    self.assertEqual(json.loads(text)["error"]["code"], code)
                bodies.append(text)
        self.assertEqual(json.loads(bodies[5])["outcome"], "LIVE_CHECK_NOT_AUTHORIZED")
        self.assertEqual(json.loads(bodies[6])["card"]["description"], "Быстрая")
        status, text = self.request("GET", "/ultra/model-cards")
        credential = json.loads(text)["providers"][0]["credential"]
        self.assertEqual(credential, {"source": "переменная среды GIGACHAT_CREDENTIALS", "present": True})
        stores = "".join(p.read_text(encoding="utf-8") for p in (self.storage / "ultra").glob("*.json"))
        for where in (*bodies, text, stores, INDEX_HTML, self.request("GET", "/")[1]):
            self.assertNotIn(SECRET, where)
        self.assertIn("ultra_model_cards", json.loads(self.request("GET", "/status")[1])["capabilities"])
        self.assertEqual(self.request("GET", "/ultra/connections")[0], 200, "the EVM catalog keeps its own route")

    def test_m17_the_module_cannot_send_or_read_a_key(self):
        source = Path(mc.__file__).read_text(encoding="utf-8").split('"""', 2)[2]
        for forbidden in ("import httpx", "gigachat_transport import", "import gigachat_transport", "import socket",
                          "urllib", "getenv", "os.environ.get", "save_ui_state(", "load_ui_state("):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('"GIGACHAT_CREDENTIALS"'), 1, "the key is named once, in the provider entry")


if __name__ == "__main__":
    unittest.main()
