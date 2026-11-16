"""Strict in-app GigaChat activation is offline-tested, never contacts the provider."""
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from model_registry import list_model_specs
from gigachat_runtime import ModelContract, response_model_allowed
from web_alarm.server import WebAlarmApi
from web_alarm.standard_live import prepare_personal_chat
from web_alarm.ordinary_provider import OrdinaryApplicationChatService, OrdinaryProviderFactory
from web_alarm.ultra_chat import UltraChatError


class SyntheticSession:
    def __init__(self, root, wid, approval):
        self.root, self.workspace_id, self.approval = root, wid, approval
        self.synthetic = False
        self._available = frozenset()
        self.closed = False

    def check(self):
        if self.closed:
            from ordinary_chat_service import PreSendDenied
            raise PreSendDenied('inactive')

    async def discover_models(self):
        self._available = frozenset(m.provider_model_id for m in list_model_specs())
        return self._available

    def close(self):
        self.closed = True


class InAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = WebAlarmApi(Path(self.tmp.name)/'web')
        self.factory = OrdinaryProviderFactory()
        self.service = OrdinaryApplicationChatService(self.api.registry, self.factory, api=self.api)
        self.record, _, _ = prepare_personal_chat(self.api)

    def test_denies_without_explicit_confirmation_or_credentials(self):
        with self.assertRaises(UltraChatError):
            self.service.start_live({})
        with patch.dict(os.environ, {'GIGACHAT_CREDENTIALS':'', 'GIGACHAT_SCOPE':''}):
            with self.assertRaisesRegex(UltraChatError, 'Configure the existing GIGACHAT_CREDENTIALS'):
                self.service.start_live({'confirmation':'GIGACHAT 6'})
        self.assertIsNone(self.factory._session)

    def test_six_model_session_and_stop_do_not_send_turn_or_touch_old_workspaces(self):
        sessions = []
        def construct(root, wid, approval):
            session = SyntheticSession(root, wid, approval)
            sessions.append(session)
            return session
        with patch.dict(os.environ, {'GIGACHAT_CREDENTIALS':'SYNTHETIC', 'GIGACHAT_SCOPE':'GIGACHAT_API_PERS'}), \
             patch('gigachat_runtime.ProviderSession', side_effect=construct):
            code, payload = self.service.start_live({'confirmation':'GIGACHAT 6'})
            self.assertEqual(code, 200)
            self.assertEqual(payload['state'], 'ACTIVE')
            self.assertEqual(len(payload['models']), 6)
            self.assertTrue(all(m['availability']=='AVAILABLE' for m in payload['models']))
            self.assertEqual(len(sessions[0].approval.contracts),6)
            self.assertEqual(sessions[0].approval.max_inference,12)
            self.assertEqual(sessions[0].approval.max_answer_tokens,128)
            self.assertEqual(sessions[0].approval.max_request_bytes,4096)
            self.assertEqual(self.service.capability()['live_workspace_id'], self.record.workspace_id)
            self.assertEqual(self.service.stop_live({}), (200, {'state':'INACTIVE'}))
            self.assertTrue(sessions[0].closed)
            self.assertEqual(self.service.stop_live({}), (200, {'state':'INACTIVE'}))
        self.assertIsNone(self.factory._session)

    def test_same_origin_routes_not_exposed_to_test_or_plain_read(self):
        self.assertTrue(self.service.is_write_path('/ultra/chat/live/start'))
        self.assertTrue(self.service.is_write_path('/ultra/chat/live/stop'))
        self.assertFalse(self.service.is_write_path('/ultra/chat/live/wrong'))
        with self.assertRaises(UltraChatError):
            self.service.write_route('/ultra/chat/live/start','x=1')
        with self.assertRaises(UltraChatError):
            self.service.route('/ultra/chat/live/start','')

    def test_family_versions_are_specific_to_exact_model_not_arbitrary_suffix(self):
        models = list_model_specs()
        self.assertEqual(len(models),6)
        for m in models:
            if m.model_id=='gigachat_2':
                continue
            c=ModelContract(m.model_id,8192,128,(), 'bounded offline',version_mode='DISCOVER_FAMILY')
            c.validate()
            self.assertTrue(response_model_allowed(c,m.provider_model_id+':3.0.1.2'))
            self.assertTrue(response_model_allowed(c,m.provider_model_id))
            self.assertFalse(response_model_allowed(c,m.provider_model_id+':unverified'))
            self.assertFalse(response_model_allowed(c,'OtherModel:3.0.1.2'))
            self.assertFalse(response_model_allowed(c,'GigaChat-3-Other:3.0.1.2'))


if __name__ == '__main__':
    unittest.main()
