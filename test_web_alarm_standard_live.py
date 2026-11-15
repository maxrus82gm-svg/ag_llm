"""Offline, no-provider tests for the opt-in STANDARD onramp."""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as core
from ultra_budget_ledger import BudgetLedger
from web_alarm.server import WebAlarmApi
from web_alarm.standard_live import (
    eligible_workspaces, offer_standard_live, MAX_SENDS, MAX_LIABILITY,
    OBSERVED_MODEL, MODEL_ID,
)
from web_alarm.ordinary_provider import OrdinaryProviderFactory, OrdinaryApplicationChatService


class StandardLiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "new_workspace"
        self.root.mkdir()
        self.api = WebAlarmApi(self.base / "web")
        self.wa_id = self.api.registry.register("New LIVE workspace", self.root).workspace_id
        self.wid = core.ensure_workspace_storage(self.root)["workspace_id"]
        self.out = io.StringIO()
        self.env = patch.dict(os.environ, {
            "GIGACHAT_CREDENTIALS": "SYNTHETIC-NO-PROVIDER-I-O",
            "GIGACHAT_SCOPE": "GIGACHAT_API_PERS",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def attempt(self, *replies):
        iterator = iter(replies)
        return offer_standard_live(self.api, lambda _prompt: next(iterator), self.out)

    def test_unenrolled_workspace_does_not_initialize_ledger(self):
        self.assertEqual(eligible_workspaces(self.api), [])
        self.assertIsNone(self.attempt("1", "LIVE 12"))
        with self.assertRaises(Exception):
            BudgetLedger(self.root, self.wid).recover()

    def test_decline_and_malformed_consent_do_not_create_grant(self):
        BudgetLedger(self.root, self.wid).initialize()
        self.assertIsNone(self.attempt(""))
        self.assertIsNone(self.attempt("1", "LIVE"))
        self.assertIsNone(self.attempt("1", "LIVE 13"))
        self.assertFalse((self.root / ".ultra" / "provider_sessions").exists())

    def test_missing_credentials_cannot_activate(self):
        BudgetLedger(self.root, self.wid).initialize()
        with patch.dict(os.environ, {"GIGACHAT_CREDENTIALS": ""}):
            self.assertIsNone(self.attempt("1", "LIVE 12"))
        self.assertFalse((self.root / ".ultra" / "provider_sessions").exists())

    def test_exact_consent_creates_single_workspace_limited_grant_no_network(self):
        BudgetLedger(self.root, self.wid).initialize()
        with patch("gigachat_runtime.ProviderSession.discover_models",
                   side_effect=AssertionError("unexpected network")):
            session = self.attempt("1", "LIVE 12")
        self.assertIsNotNone(session)
        self.assertEqual(session.root, self.root)
        self.assertEqual(session.workspace_id, self.wid)
        self.assertEqual(session.approval.max_inference, MAX_SENDS)
        self.assertEqual(session.approval.max_oauth, 1)
        self.assertEqual(session.approval.max_catalog, 1)
        self.assertEqual(session.approval.max_liability_tokens, MAX_LIABILITY)
        self.assertEqual(tuple(c.model_id for c in session.approval.contracts), (MODEL_ID,))
        self.assertEqual(session.approval.contracts[0].response_models, (OBSERVED_MODEL,))
        self.assertEqual(session._counts["inference"], 0)
        self.assertEqual(session._counts["oauth"], 0)
        session.close()
        with self.assertRaises(Exception):
            session.check()

    def test_catalog_presence_without_contract_cannot_offer_other_models(self):
        BudgetLedger(self.root, self.wid).initialize()
        session = self.attempt("1", "LIVE 12")
        self.addCleanup(session.close)
        session._available = frozenset(("GigaChat-2", "GigaChat-3-Ultra"))
        app = OrdinaryApplicationChatService(
            self.api.registry, OrdinaryProviderFactory.for_session(self.api.registry, session))
        models = {m["model_id"]: m for m in app.capability()["models"]}
        self.assertEqual(models["gigachat_2"]["availability"], "AVAILABLE")
        self.assertEqual(models["gigachat_ultra"]["availability"], "NOT_APPROVED")


class LauncherIsolationTests(unittest.TestCase):
    """The real STANDARD entry never enables provider on unattended starts."""

    def test_noninteractive_standard_is_offline_even_with_environment(self):
        from unittest import mock
        from web_alarm import launcher
        fake_server = mock.Mock()
        fake_server.server_port = 8765
        with patch.object(launcher.sys.stdin, "isatty", return_value=False), \
             patch.object(launcher, "WebAlarmApi"), \
             patch.object(launcher, "create_server", return_value=fake_server), \
             patch("web_alarm.standard_live.offer_standard_live") as consent:
            result = launcher.run_web_alarm(launcher.standard_launch(),
                                            out=io.StringIO(), colors=False,
                                            open_browser=False, port=0)
        self.assertEqual(result, 0)
        consent.assert_not_called()
        fake_server.server_close.assert_called_once()

    def test_catalog_missing_keeps_the_browser_off_and_closes_grant(self):
        from unittest import mock
        from web_alarm import launcher
        fake_server = mock.Mock()
        fake_server.server_port = 8765
        session = mock.Mock()
        session.discover_models = mock.AsyncMock(return_value=frozenset())
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), \
             patch.object(launcher, "WebAlarmApi"), \
             patch.object(launcher, "create_server", return_value=fake_server), \
             patch("web_alarm.standard_live.offer_standard_live", return_value=session), \
             patch("web_alarm.ordinary_provider.OrdinaryProviderFactory.for_session",
                   return_value=object()):
            result = launcher.run_web_alarm(launcher.standard_launch(),
                                            out=io.StringIO(), colors=False,
                                            open_browser=False, port=0)
        self.assertEqual(result, 5)
        session.discover_models.assert_awaited_once()
        session.close.assert_called_once()
        fake_server.serve_forever.assert_not_called()
        fake_server.server_close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
