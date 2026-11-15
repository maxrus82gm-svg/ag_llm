"""H37 corrected oracle: billed tokens differ from full processed input.

The 2026-07-17 counting-tokens guide says prompt_tokens is already uncached.
The historical 7/5/cached2/total10 RED is preserved as a mistaken oracle, not a
shared accounting defect. This suite uses synthetic data under OFFLINE guards.
"""
import json
import unittest
from ordinary_chat_service import _usage
import ultra_budget_policy as policy
from ultra_budget_ledger import BudgetLedger
import context_storage as core
import test_web_alarm_gigachat_transport as h33
from ordinary_gigachat_transport import OfflineHTTPFixture
from web_alarm.ultra_chat import OrdinaryCoreChatService


class CachedUsageContract(unittest.TestCase):
    @staticmethod
    def sent():
        measure = policy.RequestMeasure('executor', 'GigaChat-3-Ultra', 400, '0' * 64, 50)
        reserved = policy.reserve_attempt('h37_cached', measure,
            policy.TokenEstimate(100, policy.EST_CALIBRATED, None, ''), 'h37_scope')
        return policy.mark_sent(reserved)

    def test_documented_example_preserves_billing_and_full_input(self):
        # Published usage example: net input 1, output 4, cached input 37.
        raw = dict(prompt_tokens=1, completion_tokens=4, precached_prompt_tokens=37, total_tokens=5)
        parsed = _usage({'usage': raw})
        self.assertEqual((parsed.status, parsed.total_tokens), ('complete', 5))
        status, usage, _ = policy.validate_usage(raw)
        self.assertEqual(status, 'KNOWN')
        self.assertEqual((usage.prompt_tokens, usage.completion_tokens, usage.precached_prompt_tokens), (1, 4, 37))
        settled = policy.apply_terminal(self.sent(), 'completed', raw)
        self.assertEqual(settled.state, policy.KNOWN_TERMINAL)
        self.assertEqual(settled.known_input_tokens, 38)
        self.assertEqual(settled.liability_tokens, 42)  # processed load, not billable 5

    def test_corrected_synthetic_vectors_do_not_subtract_cache_twice(self):
        for prompt, completion, cached, total, full_input, processed in (
            (7, 5, 2, 12, 9, 14),  # prompt=7 is already net of cache
            (5, 5, 2, 10, 7, 12),  # if original gross input was 7, net prompt must be 5
            (7, 5, 0, 12, 7, 12),
        ):
            with self.subTest(prompt=prompt, cached=cached):
                raw = dict(prompt_tokens=prompt, completion_tokens=completion,
                           precached_prompt_tokens=cached, total_tokens=total)
                self.assertEqual(_usage({'usage': raw}).total_tokens, total)
                self.assertEqual(policy.validate_usage(raw)[0], 'KNOWN')
                settled = policy.apply_terminal(self.sent(), 'completed', raw)
                self.assertEqual(settled.state, policy.KNOWN_TERMINAL)
                self.assertEqual(settled.known_input_tokens, full_input)
                self.assertEqual(settled.liability_tokens, processed)

    def test_old_vector_is_invalid_in_both_existing_parsers(self):
        raw = dict(prompt_tokens=7, completion_tokens=5, precached_prompt_tokens=2, total_tokens=10)
        self.assertEqual(_usage({'usage': raw}).status, 'invalid')
        self.assertEqual(policy.validate_usage(raw)[0], 'INVALID')
        settled = policy.apply_terminal(self.sent(), 'completed', raw)
        self.assertEqual(settled.state, policy.ANOMALY)
        self.assertGreaterEqual(settled.liability_tokens, self.sent().reserved_liability_tokens)

    def test_missing_cached_preserves_unknown_and_conservative_reservation(self):
        raw = dict(prompt_tokens=7, completion_tokens=5, total_tokens=12)
        self.assertEqual(_usage({'usage': raw}).total_tokens, 12)
        status, usage, _ = policy.validate_usage(raw)
        self.assertEqual(status, 'KNOWN')
        self.assertIsNone(usage.precached_prompt_tokens)
        settled = policy.apply_terminal(self.sent(), 'completed', raw)
        # Missing cache does not prove exact gross context; current liability
        # retains max(reported net input, reserved estimate), then output.
        self.assertEqual(settled.known_input_tokens, 100)
        self.assertEqual(settled.liability_tokens, 105)
        self.assertIsNone(settled.usage.precached_prompt_tokens)


class CachedTurnContract(h33.s5.Fixture):
    def test_turn_preserves_billing_and_conservative_missing_cache_liability(self):
        raw = dict(prompt_tokens=7, completion_tokens=5, precached_prompt_tokens=2, total_tokens=12)
        fixture = OfflineHTTPFixture(body=json.dumps(h33.reply(raw)).encode())
        self.service = OrdinaryCoreChatService(self.registry, self.root, http_fixture=fixture)
        ws, cid = self.create_chat('H37 cache correction OFFLINE')
        root = h33.Path(self.registry.get(ws).workspace_root)
        wid = core.read_workspace_identity_bounded(root)['workspace_id']
        ledger = BudgetLedger(root, wid)
        body = self.body('synthetic cached request', 'gigachat_ultra')
        result = self.service.submit_turn(ws, cid, body)
        self.assertEqual(result['state'], 'SUCCEEDED')
        records = ledger.recover().attempts
        self.assertEqual(len(records), 1)
        # Existing Ordinary Usage does not forward the optional cached field.
        # Do not invent exact gross context 9 at this layer: ledger retains the
        # reserved estimate as a conservative fallback, not a billed total.
        self.assertIsNone(records[0].usage.precached_prompt_tokens)
        reserved_input = records[0].reserved_input_tokens_est
        self.assertGreaterEqual(reserved_input, 9)
        self.assertEqual(records[0].known_input_tokens, reserved_input)
        self.assertEqual(records[0].liability_tokens, reserved_input + 5)
        known = self.service.messages(ws, cid, None, 50)['usage_summary']['known']
        self.assertEqual((known['prompt_tokens'], known['completion_tokens'], known['total_tokens']), (7, 5, 12))
        self.service = OrdinaryCoreChatService(self.registry, self.root, http_fixture=fixture)
        self.assertEqual(self.service.submit_turn(ws, cid, body), result)
        self.assertEqual(ledger.recover().attempts, records)
        self.assertEqual((fixture.token_calls, len(fixture.requests)), (1, 1))
