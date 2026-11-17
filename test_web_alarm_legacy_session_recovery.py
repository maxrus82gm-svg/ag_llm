"""Isolated, offline negative and recovery tests; never use STANDARD storage."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import context_storage as core
from ultra_budget_ledger import BudgetLedger
from tools.legacy_session_recovery import LegacyRecoveryDenied, recover_legacy_account


class LegacySessionRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="wa-legacy-recovery-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "workspace"
        self.root.mkdir()
        self.wid = core.ensure_workspace_storage(self.root)["workspace_id"]
        self.account_id = "offline-personal-gigachat-account"
        self.account_hash = hashlib.sha256(self.account_id.encode()).hexdigest()
        self.grant_id = "OldGigaChatGrant" + "a" * 18
        self.folder = self.root / core.ULTRA_DIRNAME / "provider_sessions"
        BudgetLedger(self.root, self.wid).initialize()
        account = {"schema": 1, "grant_id": self.grant_id, "state": "ACTIVE",
                   "confirmed_versions": {"gigachat_2": "GigaChat-2:2.0.30.01"}}
        grant = {"schema": 1, "grant_id": self.grant_id,
                 "workspace_id": self.wid, "account_sha256": self.account_hash,
                 "state": "ACTIVE",
                 "counts": {"oauth": 1, "catalog": 1, "inference": 1, "liability": 104}}
        self._store("account_" + self.account_hash + ".json", account)
        self._store(self.grant_id + ".json", grant)

    def _store(self, name, value):
        with core._existing_workspace_writer(self.root, self.wid) as writer:
            core._ensure_write_directory(writer.anchor, (core.ULTRA_DIRNAME, "provider_sessions"))
            core._replace_verified(writer.anchor,
                                   (core.ULTRA_DIRNAME, "provider_sessions", name),
                                   core._json_bytes(value))

    def _read(self, name):
        return (self.folder / name).read_bytes()

    def _recover(self, **kwargs):
        return recover_legacy_account(self.root, self.wid, self.account_id, **kwargs)

    def test_dry_run_is_read_only_and_detects_legacy(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        state = BudgetLedger(self.root, self.wid).recover()
        result = self._recover()
        self.assertEqual(result["status"], "ELIGIBLE_FOR_MANUAL_RECOVERY")
        self.assertEqual(result["ledger_events"], state.event_count)
        self.assertEqual({p.name: p.read_bytes() for p in self.folder.iterdir()}, before)
        self.assertEqual(BudgetLedger(self.root, self.wid).recover(), state)

    def test_manual_recovery_only_closes_account_and_is_not_repeatable(self):
        old_account = self._read("account_" + self.account_hash + ".json")
        old_grant = self._read(self.grant_id + ".json")
        ledger_before = BudgetLedger(self.root, self.wid).recover()
        with self.assertRaisesRegex(LegacyRecoveryDenied, "explicit_owner_go_required"):
            self._recover(apply=True)
        with self.assertRaisesRegex(LegacyRecoveryDenied, "legacy_owner_quiescence_unproven"):
            self._recover(apply=True, owner_authorized=True, owner_quiescent=lambda: False)
        self.assertEqual(self._read("account_" + self.account_hash + ".json"), old_account)
        result = self._recover(apply=True, owner_authorized=True, owner_quiescent=lambda: True)
        self.assertEqual(result["status"], "RECOVERED_ACCOUNT_ONLY")
        new_account = json.loads(self._read("account_" + self.account_hash + ".json"))
        self.assertEqual(new_account["state"], "CLOSED")
        self.assertEqual(new_account["confirmed_versions"]["gigachat_2"],
                         "GigaChat-2:2.0.30.01")
        evidence = json.loads(self._read("legacy_recovery_" + self.grant_id + ".json"))
        self.assertEqual(evidence["previous_account_raw_utf8"].encode(), old_account)
        self.assertEqual(evidence["previous_grant_sha256"], hashlib.sha256(old_grant).hexdigest())
        self.assertEqual(self._read(self.grant_id + ".json"), old_grant)
        self.assertEqual(BudgetLedger(self.root, self.wid).recover(), ledger_before)
        with self.assertRaises(LegacyRecoveryDenied):
            self._recover(apply=True, owner_authorized=True, owner_quiescent=lambda: True)

    def test_rejects_workspace_mismatch_before_mutation(self):
        with self.assertRaisesRegex(LegacyRecoveryDenied, "workspace_identity_mismatch"):
            recover_legacy_account(self.root, "unrelated-workspace", self.account_id)

    def test_rejects_grant_account_mismatch(self):
        self._store(self.grant_id + ".json",
                    {**json.loads(self._read(self.grant_id + ".json")),
                     "workspace_id": "different-workspace"})
        with self.assertRaisesRegex(LegacyRecoveryDenied, "legacy_grant_account_mismatch"):
            self._recover()

    def test_rejects_two_active_grants_same_account(self):
        another = "AnotherLegacyGrant" + "b" * 16
        self._store(another + ".json",
                    {**json.loads(self._read(self.grant_id + ".json")),
                     "grant_id": another})
        with self.assertRaisesRegex(LegacyRecoveryDenied, "concurrent_legacy_grant_unresolved"):
            self._recover()

    def test_competing_live_os_owner_refuses_without_touching_account(self):
        from tools.legacy_session_recovery import _account_lock
        from ordinary_chat_service import PreSendDenied
        old = self._read("account_" + self.account_hash + ".json")
        lock = _account_lock(self.account_id)
        lock.acquire()
        try:
            with self.assertRaisesRegex(PreSendDenied, "account_owner_live"):
                self._recover(apply=True, owner_authorized=True,
                              owner_quiescent=lambda: True)
        finally:
            lock.release()
        self.assertEqual(self._read("account_" + self.account_hash + ".json"), old)

    def test_rejects_existing_partial_recovery_evidence(self):
        self._store("legacy_recovery_" + self.grant_id + ".json", {"schema": 1})
        with self.assertRaisesRegex(LegacyRecoveryDenied, "legacy_recovery_evidence_exists"):
            self._recover()


if __name__ == "__main__":
    unittest.main()
