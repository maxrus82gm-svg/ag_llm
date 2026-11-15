"""Expected RED proves the authority-before-contract oracle detects a bypass."""
import unittest
from unittest.mock import patch
from test_web_alarm_gigachat_ultra_preflight import RealPreflightTests


class MutatedAuthority(unittest.TestCase):
    def test_real_authority_bypass_is_detected(self):
        # In-memory mutation only; runtime source and durable records unchanged.
        with patch('gigachat_admission.require_real_authority', return_value=None):
            RealPreflightTests('test_real_factory_denies_before_contract_token_or_http').test_real_factory_denies_before_contract_token_or_http()
