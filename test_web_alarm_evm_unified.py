"""No-network checks for the EVM to existing Ordinary Turn handoff."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ordinary_chat_service import PreSendDenied
from web_alarm.model_cards import CheckRequest, CheckRefusedError
from web_alarm.ordinary_provider import _OrdinaryTurnChecker


class EvmTurnHandoff(TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix='evm_turn_')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.session = SimpleNamespace(synthetic=False, check=Mock(), _available={'GigaChat-2'},
            approval=SimpleNamespace(contracts=(SimpleNamespace(model_id='gigachat_2'),)), root=self.root)
        self.factory = SimpleNamespace(_session=self.session, require_real=Mock())
        self.service = SimpleNamespace(_factory=self.factory, registry=object(),
            create_chat=Mock(), chat_model=Mock(), submit_turn=Mock(return_value={
                'execution_mode': 'REAL', 'state': 'SUCCEEDED', 'answer': 'Готово'}))
        self.request = CheckRequest('api:gigachat:gigachat_2', 'gigachat_2', 'gigachat',
            'GigaChat-2', 'https://api.giga.chat/v1/chat/completions', 30, 'Тест.')
        self.checker = _OrdinaryTurnChecker(self.service)

    def test_one_explicit_check_uses_one_visible_ordinary_turn(self):
        record = SimpleNamespace(workspace_id='personal', workspace_root=str(self.root))
        with patch('web_alarm.standard_live.personal_chat_registration', return_value=record):
            result = self.checker.check(self.request)
        self.assertTrue(result.ok and result.live)
        self.assertEqual(result.reply, 'Готово')
        self.service.create_chat.assert_called_once()
        self.service.chat_model.assert_called_once()
        self.service.submit_turn.assert_called_once()
        self.assertEqual(self.service.submit_turn.call_args.args[2]['text'], 'Тест.')
        self.factory.require_real.assert_called_once()

    def test_no_live_authority_or_foreign_workspace_denies_before_turn(self):
        self.session.synthetic = True
        with self.assertRaises(CheckRefusedError):
            self.checker.check(self.request)
        self.service.submit_turn.assert_not_called()
        self.session.synthetic = False
        with patch('web_alarm.standard_live.personal_chat_registration', return_value=
                   SimpleNamespace(workspace_id='foreign', workspace_root=str(self.root/'other'))):
            with self.assertRaises(CheckRefusedError):
                self.checker.check(self.request)
        self.service.submit_turn.assert_not_called()
        self.session.check = Mock(side_effect=PreSendDenied('closed'))
        self.assertFalse(self.checker.authorized)
        self.assertEqual(self.checker.reason, 'Провайдер не подключён. Подключите GigaChat в EVM.')

    def test_unknown_turn_is_reported_uncertain_without_retry(self):
        self.service.submit_turn.return_value = {'execution_mode': 'REAL', 'state': 'UNKNOWN',
            'turn_id': 'turn_1', 'diagnostic_code': 'transport_unknown'}
        record = SimpleNamespace(workspace_id='personal', workspace_root=str(self.root))
        with patch('web_alarm.standard_live.personal_chat_registration', return_value=record):
            result = self.checker.check(self.request)
        self.assertFalse(result.ok)
        self.assertTrue(result.uncertain)
        self.assertEqual(result.turn_id, 'turn_1')
        self.service.submit_turn.assert_called_once()

    def test_expired_authority_refuses_before_creating_a_check_chat(self):
        self.factory.require_real.side_effect = PreSendDenied('expired')
        with self.assertRaises(CheckRefusedError):
            self.checker.check(self.request)
        self.service.create_chat.assert_not_called()
        self.service.submit_turn.assert_not_called()
