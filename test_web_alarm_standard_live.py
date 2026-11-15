"""Offline checks: personal chats without Workspace selection and STANDARD LIVE fences."""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import context_storage as core
from ordinary_chat_service import PreSendDenied
from ultra_budget_ledger import BudgetLedger
from web_alarm.server import WebAlarmApi
from web_alarm.standard_live import (
    eligible_workspaces, personal_chat_registration, prepare_personal_chat,
    offer_standard_live, MAX_SENDS, MAX_LIABILITY, OBSERVED_MODEL, MODEL_ID,
    PERSONAL_DIRNAME, PERSONAL_LABEL,
)
from web_alarm.ordinary_provider import OrdinaryProviderFactory, OrdinaryApplicationChatService


class PersonalChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "legacy_workspace"
        self.root.mkdir()
        self.api = WebAlarmApi(self.base / "web")
        self.wa_id = self.api.registry.register("Legacy Workspace", self.root).workspace_id
        self.wid = core.ensure_workspace_storage(self.root)["workspace_id"]
        self.out = io.StringIO()
        self.env = patch.dict(os.environ, {
            "GIGACHAT_CREDENTIALS": "SYNTHETIC-NO-PROVIDER-I-O",
            "GIGACHAT_SCOPE": "GIGACHAT_API_PERS",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    @property
    def personal_path(self):
        return self.api.registry.storage_root / PERSONAL_DIRNAME

    def attempt(self, *replies):
        iterator = iter(replies)
        return offer_standard_live(self.api, lambda _: next(iterator), self.out)

    def test_legacy_unenrolled_unchanged_on_decline(self):
        self.assertEqual(eligible_workspaces(self.api), [])
        self.assertIsNone(self.attempt(""))
        self.assertIsNone(self.attempt("1"))
        self.assertIsNone(self.attempt("LIVE 13"))
        self.assertFalse(self.personal_path.exists())
        self.assertIsNone(personal_chat_registration(self.api.registry))
        with self.assertRaises(Exception):
            BudgetLedger(self.root, self.wid).recover()

    def test_missing_credentials_does_not_create_personal_root(self):
        with patch.dict(os.environ, {"GIGACHAT_CREDENTIALS": ""}):
            self.assertIsNone(self.attempt("LIVE 12"))
        self.assertFalse(self.personal_path.exists())

    def test_new_personal_chat_durable_single_chat_and_zero_provider_calls(self):
        before = self.api.registry.list()
        with patch("gigachat_runtime.ProviderSession.discover_models",
                   side_effect=AssertionError("unexpected provider request")):
            session = self.attempt("LIVE 12")
        self.assertIsNotNone(session)
        self.assertEqual(session.root, self.personal_path)
        self.assertEqual(session.approval.max_inference, MAX_SENDS)
        self.assertEqual(session.approval.max_oauth, 1)
        self.assertEqual(session.approval.max_catalog, 1)
        self.assertEqual(session.approval.max_liability_tokens, MAX_LIABILITY)
        self.assertEqual(session.approval.contracts[0].response_models, (OBSERVED_MODEL,))
        self.assertEqual(tuple(c.model_id for c in session.approval.contracts), (MODEL_ID,))
        self.assertEqual(session._counts["oauth"], 0)
        self.assertEqual(session._counts["catalog"], 0)
        self.assertEqual(session._counts["inference"], 0)
        personal = personal_chat_registration(self.api.registry)
        self.assertIsNotNone(personal)
        self.assertEqual(personal.display_name, PERSONAL_LABEL)
        self.assertEqual(personal.workspace_root, str(self.personal_path))
        self.assertEqual(self.api.registry.get(self.wa_id), before[0])
        self.assertEqual(core.read_workspace_identity_bounded(self.root)["workspace_id"], self.wid)
        with self.assertRaises(Exception):
            BudgetLedger(self.root, self.wid).recover()
        listing = core.list_chats_bounded(self.personal_path)["chats"]
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["title"], "Первый диалог")
        self.assertEqual(BudgetLedger(self.personal_path, session.workspace_id).recover().event_count, 0)
        session.close()

    def test_reopen_preserves_personal_identity_and_chat(self):
        first = self.attempt("LIVE 12")
        first_reg = self.api.registry.get(personal_chat_registration(self.api.registry).workspace_id)
        first_chats = core.list_chats_bounded(self.personal_path)["chats"]
        first.close()
        second = self.attempt("LIVE 12")
        self.assertEqual(second.workspace_id, first.workspace_id)
        self.assertNotEqual(second.approval.grant_id, first.approval.grant_id)
        self.assertEqual(self.api.registry.get(first_reg.workspace_id), first_reg)
        self.assertEqual(core.list_chats_bounded(self.personal_path)["chats"], first_chats)
        self.assertEqual(BudgetLedger(self.personal_path, second.workspace_id).recover().event_count, 0)
        second.close()

    def test_unregistered_preexisting_directory_refuses_adoption(self):
        self.personal_path.mkdir()
        self.assertIsNone(personal_chat_registration(self.api.registry))
        with self.assertRaisesRegex(PreSendDenied, "personal_storage_existing_unregistered"):
            self.attempt("LIVE 12")
        self.assertEqual(list(self.personal_path.iterdir()), [])
        self.assertEqual(len(self.api.registry.list()), 1)

    def test_preexisting_file_refuses_adoption_and_is_not_deleted(self):
        self.personal_path.write_text("UNTOUCHED", encoding="utf-8")
        with self.assertRaisesRegex(PreSendDenied, "personal_storage_existing_unregistered"):
            self.attempt("LIVE 12")
        self.assertEqual(self.personal_path.read_text(encoding="utf-8"), "UNTOUCHED")

    def test_registered_personal_root_with_missing_audit_refuses_reset(self):
        self.personal_path.mkdir()
        core.ensure_workspace_storage(self.personal_path)
        self.api.registry.register(PERSONAL_LABEL, self.personal_path)
        with self.assertRaises(Exception):
            self.attempt("LIVE 12")
        self.assertIsNone((self.personal_path / ".ultra" / "audit" / "ledger_marker.json").is_file() or None)

    def test_unapproved_model_is_visible_but_cannot_be_sent(self):
        session = self.attempt("LIVE 12")
        self.addCleanup(session.close)
        session._available = frozenset(("GigaChat-2", "GigaChat-3-Ultra"))
        app = OrdinaryApplicationChatService(self.api.registry,
            OrdinaryProviderFactory.for_session(self.api.registry, session))
        models = {m["model_id"]: m for m in app.capability()["models"]}
        self.assertEqual(models["gigachat_2"]["availability"], "AVAILABLE")
        self.assertEqual(models["gigachat_ultra"]["availability"], "NOT_APPROVED")
        self.assertEqual(app.capability()["personal_workspace_id"], personal_chat_registration(self.api.registry).workspace_id)
        self.assertEqual(app.capability()["live_workspace_id"], personal_chat_registration(self.api.registry).workspace_id)


class LauncherIsolationTests(unittest.TestCase):
    def test_noninteractive_standard_never_asks_for_live(self):
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

    def test_missing_catalog_closes_live_before_browser(self):
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
