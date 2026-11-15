"""Expected RED: published cached-token billing versus the sealed current contract.

This is a diagnostic acceptance oracle; do not weaken it to make LIVE look ready.
Source: public api.yml Usage schema checked 2026-11-15, no provider request.
"""
import unittest
from ordinary_chat_service import _usage


class CachedUsageContract(unittest.TestCase):
    def test_documented_billable_total_can_be_preserved(self):
        # Exact synthetic example under the documented subtract-cache semantics.
        # Current policy instead requires 7+5=12 and therefore reports invalid.
        result = _usage({'usage': dict(prompt_tokens=7, completion_tokens=5,
                                      precached_prompt_tokens=2, total_tokens=10)})
        self.assertEqual(result.status, 'complete', 'REAL BLOCKER: shared accounting contract mismatch')
        self.assertEqual(result.total_tokens, 10)
