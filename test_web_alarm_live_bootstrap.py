"""Offline checks for the operator composition; no provider credentials or I/O."""
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import context_storage as core
from gigachat_runtime import LiveApproval
from ordinary_chat_service import PreSendDenied
from ultra_budget_ledger import BudgetLedger
from web_alarm.live_bootstrap import _verified_workspace, catalog_probe, serve_one_inference
from web_alarm.server import WebAlarmApi


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "fresh"
        self.root.mkdir()
        self.api = WebAlarmApi(Path(self.temp.name) / "web")
        self.wa_id = self.api.registry.register("LIVE fixture", self.root).workspace_id
        self.wid = core.ensure_workspace_storage(self.root)["workspace_id"]

    def approval(self, *, inference=0, contracts=()):
        return LiveApproval("OfflineProbeGrant0001", "offline-owner-fixture",
            "offline-review-fixture", "offline-account-fixture", "GIGACHAT_API_PERS",
            time.time()+60, contracts, 1, 1, inference, 1024,
            max_answer_tokens=32)

    def test_existing_ledger_required_and_preserved(self):
        with self.assertRaises(Exception):
            _verified_workspace(self.api, self.wa_id)
        before = BudgetLedger(self.root, self.wid).initialize()
        self.assertEqual(_verified_workspace(self.api, self.wa_id), (self.root, self.wid))
        after = BudgetLedger(self.root, self.wid).recover()
        self.assertEqual((before.ledger_id, before.event_count),
                         (after.ledger_id, after.event_count))

    def test_probe_refuses_inference_grant_before_session(self):
        with mock.patch("web_alarm.live_bootstrap.ProviderSession") as session:
            with self.assertRaises(PreSendDenied):
                catalog_probe(self.api, self.wa_id, self.approval(inference=1))
            session.assert_not_called()

    def test_probe_closes_session_and_has_one_discovery(self):
        BudgetLedger(self.root, self.wid).initialize()
        fake = mock.Mock()
        fake.discover_models = mock.AsyncMock(return_value=frozenset({"GigaChat-2"}))
        with mock.patch("web_alarm.live_bootstrap.ProviderSession", return_value=fake):
            self.assertEqual(catalog_probe(self.api, self.wa_id, self.approval()),
                             frozenset({"GigaChat-2"}))
        fake.discover_models.assert_awaited_once()
        fake.close.assert_called_once()

    def test_inference_entry_refuses_probe_grant(self):
        with mock.patch("web_alarm.live_bootstrap.ProviderSession") as session:
            with self.assertRaises(PreSendDenied):
                serve_one_inference(self.api, self.wa_id, self.approval())
            session.assert_not_called()

    def test_first_reply_refuses_broad_grants_before_session(self):
        with mock.patch("web_alarm.live_bootstrap.ProviderSession") as session:
            candidates = (
                replace(self.approval(), expires_at=time.time()+601),
                replace(self.approval(inference=1, contracts=(object(), object())),
                        max_answer_tokens=32),
                replace(self.approval(inference=1, contracts=(object(),)),
                        max_answer_tokens=33),
            )
            with self.assertRaises(PreSendDenied):
                catalog_probe(self.api, self.wa_id, candidates[0])
            for grant in candidates[1:]:
                with self.assertRaises(PreSendDenied):
                    serve_one_inference(self.api, self.wa_id, grant)
            session.assert_not_called()

    def test_server_binds_before_catalog_and_closes_on_failed_discovery(self):
        BudgetLedger(self.root, self.wid).initialize()
        events = []
        fake_session = mock.Mock()

        async def fail_discovery():
            events.append("catalog")
            raise PreSendDenied("offline_catalog_failure")

        fake_session.discover_models = fail_discovery
        fake_session.close.side_effect = lambda: events.append("session_closed")
        fake_server = mock.Mock()
        fake_server.server_close.side_effect = lambda: events.append("server_closed")

        def bind(*args, **kwargs):
            events.append("server_bound")
            return fake_server

        with mock.patch("web_alarm.live_bootstrap.ProviderSession", return_value=fake_session), \
             mock.patch("web_alarm.live_bootstrap.OrdinaryProviderFactory.for_session", return_value=object()), \
             mock.patch("web_alarm.live_bootstrap.create_server", side_effect=bind):
            with self.assertRaises(PreSendDenied):
                serve_one_inference(self.api, self.wa_id, self.approval(inference=1,
                    contracts=(object(),)))
        self.assertEqual(events, ["server_bound", "catalog", "server_closed", "session_closed"])
        fake_server.serve_forever.assert_not_called()


if __name__ == "__main__":
    unittest.main()
