"""Operator-only recovery of pre-OS-lock GigaChat ACTIVE account records.

No HTTP endpoint, automatic launch hook, OAuth, catalog, inference or grant reset.
Real storage requires a separate explicit owner authorization and a documented
quiescent-owner check. Dry-run and disposable fixtures are the default.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import context_storage as core
from gigachat_runtime import _AccountOwnerLock
from ultra_budget_ledger import BudgetLedger

_SESSIONS = (core.ULTRA_DIRNAME, "provider_sessions")
_GRANT_ID = re.compile(r"[A-Za-z0-9_-]{16,80}\Z", re.ASCII)


class LegacyRecoveryDenied(RuntimeError):
    """Stable diagnostic code. No automatic retry or silent fallback."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(writer, parts):
    raw = core._read_file_bounded(writer.anchor, parts, 65536)
    value = json.loads(raw)
    if type(value) is not dict:
        raise LegacyRecoveryDenied("legacy_record_invalid")
    return value, raw


def _account_lock(account_id: str) -> _AccountOwnerLock:
    name = hashlib.sha256((account_id + ":False").encode()).hexdigest()
    return _AccountOwnerLock(Path(tempfile.gettempdir()) /
                             ("web-alarm-gigachat-owner-" + name + ".lock"))


def _local_owner_scan() -> bool:
    """Fail closed if Windows cannot establish a clean local legacy process scan.

    This scan cannot prove the state of other machines. The operator must still
    place all old installations in a maintenance window before any apply.
    """
    if os.name != "nt":
        return False
    script = r'''$ErrorActionPreference='Stop';
$p=Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='py.exe' OR Name='cmd.exe'";
$busy=@($p | Where-Object {$_.CommandLine -match 'web_alarm.+launcher|Start_WebAlarm_(Standard|Test)\\.cmd|gigachat_live_cli|live_bootstrap'});
@{ok=$true;busy=$busy.Count} | ConvertTo-Json -Compress'''
    try:
        found = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=8, check=True)
        row = json.loads(found.stdout)
        return (type(row) is dict and row.get("ok") is True
                and type(row.get("busy")) is int and row["busy"] == 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def recover_legacy_account(root, workspace_id, account_id, *,
                           apply=False, owner_authorized=False,
                           owner_quiescent=None):
    """Inspect or explicitly recover exactly one legacy account.

    A successful apply creates immutable evidence *before* atomically closing
    only the account record. The original grant and ledger are never edited.
    A failed/ambiguous interrupted migration refuses a retry for manual review.
    owner_quiescent is a trusted maintenance callback, never an HTTP input.
    """
    if (not isinstance(root, (str, Path)) or type(workspace_id) is not str
            or not workspace_id or type(account_id) is not str or not account_id
            or type(apply) is not bool or type(owner_authorized) is not bool):
        raise LegacyRecoveryDenied("recovery_arguments_invalid")
    root = Path(root).absolute()
    if root.resolve(strict=True) != root:
        raise LegacyRecoveryDenied("workspace_path_unverified")
    identity = core.read_workspace_identity_bounded(root)
    if identity.get("status") != "ok" or identity.get("workspace_id") != workspace_id:
        raise LegacyRecoveryDenied("workspace_identity_mismatch")
    if apply and not owner_authorized:
        raise LegacyRecoveryDenied("explicit_owner_go_required")

    account_sha = hashlib.sha256(account_id.encode()).hexdigest()
    account_parts = _SESSIONS + ("account_" + account_sha + ".json",)
    lock = _account_lock(account_id)
    lock.acquire()  # Fences ALL post-H43 owners, including other workspaces.
    try:
        with core._existing_workspace_writer(root, workspace_id) as writer:
            before = BudgetLedger(root, workspace_id).recover()
            previous, previous_raw = _read(writer, account_parts)
            grant_id = previous.get("grant_id")
            if (previous.get("schema") != 1 or previous.get("state") != "ACTIVE"
                    or "owner_lock" in previous or type(grant_id) is not str
                    or _GRANT_ID.fullmatch(grant_id) is None):
                raise LegacyRecoveryDenied("not_an_unowned_legacy_active")
            pinned = previous.get("confirmed_versions", {})
            if (type(pinned) is not dict or
                    any(type(k) is not str or type(v) is not str
                        for k, v in pinned.items())):
                raise LegacyRecoveryDenied("confirmed_versions_unreadable")
            grant_parts = _SESSIONS + (grant_id + ".json",)
            grant, grant_raw = _read(writer, grant_parts)
            if (grant.get("schema") != 1 or grant.get("grant_id") != grant_id
                    or grant.get("state") != "ACTIVE"
                    or grant.get("workspace_id") != workspace_id
                    or grant.get("account_sha256") != account_sha):
                raise LegacyRecoveryDenied("legacy_grant_account_mismatch")
            counts = grant.get("counts")
            if (type(counts) is not dict
                    or set(counts) != {"oauth", "catalog", "inference", "liability"}
                    or any(type(v) is not int or v < 0 for v in counts.values())):
                raise LegacyRecoveryDenied("legacy_grant_counts_invalid")
            recovery_parts = _SESSIONS + ("legacy_recovery_" + grant_id + ".json",)
            old_recovery_parts = _SESSIONS + ("recovery_" + grant_id + ".json",)
            if (core._read_existing_raw(writer, recovery_parts) is not None
                    or core._read_existing_raw(writer, old_recovery_parts) is not None):
                raise LegacyRecoveryDenied("legacy_recovery_evidence_exists")

            # Other ACTIVE grants for this account are evidence of an
            # unresolved concurrent or older owner: do not select one blindly.
            for name, kind, _ in core._scan_directory(
                    writer.anchor, _SESSIONS, 1024):
                if (name == grant_id + ".json" or not name.endswith(".json")
                        or name.startswith(("account_", "recovery_", "legacy_recovery_"))):
                    continue
                if kind != "file":
                    raise LegacyRecoveryDenied("legacy_session_directory_unsafe")
                other, _ = _read(writer, _SESSIONS + (name,))
                if (other.get("account_sha256") == account_sha
                        and other.get("state") == "ACTIVE"):
                    raise LegacyRecoveryDenied("concurrent_legacy_grant_unresolved")

            outcome = {
                "status": "ELIGIBLE_FOR_MANUAL_RECOVERY",
                "workspace_id": workspace_id,
                "grant_id": grant_id,
                "account_sha256": account_sha,
                "account_sha256_bytes": _sha(previous_raw),
                "grant_sha256_bytes": _sha(grant_raw),
                "confirmed_versions": dict(pinned),
                "ledger_revision": before.revision,
                "ledger_events": before.event_count,
                "ledger_records": len(before.attempts),
                "evidence": "/".join(recovery_parts),
            }
            if not apply:
                return outcome
            if not callable(owner_quiescent) or owner_quiescent() is not True:
                raise LegacyRecoveryDenied("legacy_owner_quiescence_unproven")
            isolated_fixture = Path(tempfile.gettempdir()).resolve() in root.parents
            if not isolated_fixture and not _local_owner_scan():
                raise LegacyRecoveryDenied("legacy_local_owner_scan_unproven")
            if BudgetLedger(root, workspace_id).recover() != before:
                raise LegacyRecoveryDenied("legacy_ledger_changed")
            if _read(writer, account_parts)[1] != previous_raw:
                raise LegacyRecoveryDenied("legacy_account_changed")
            if _read(writer, grant_parts)[1] != grant_raw:
                raise LegacyRecoveryDenied("legacy_grant_changed")
            evidence = {
                "schema": 1, "kind": "LEGACY_ACCOUNT_RECOVERY",
                "reason": "manual_quiescent_owner_review",
                "workspace_id": workspace_id, "grant_id": grant_id,
                "account_sha256": account_sha,
                "previous_account_raw_utf8": previous_raw.decode("utf-8"),
                "previous_grant_sha256": _sha(grant_raw),
                "ledger_revision": before.revision,
                "ledger_events": before.event_count,
                "ledger_records": len(before.attempts),
                "owner_authorized": True,
            }
            # Publish-only, never replace an existing evidence record.
            core._publish_new_file(writer.anchor, recovery_parts, core._json_bytes(evidence))
            closed = {**previous, "state": "CLOSED",
                      "legacy_recovery": "MANUAL_EVIDENCE_V1"}
            core._replace_verified(writer.anchor, account_parts, core._json_bytes(closed))
            if (_read(writer, account_parts)[0] != closed
                    or _read(writer, grant_parts)[1] != grant_raw
                    or BudgetLedger(root, workspace_id).recover() != before):
                raise LegacyRecoveryDenied("legacy_recovery_readback_failed")
            return {**outcome, "status": "RECOVERED_ACCOUNT_ONLY"}
    finally:
        lock.release()
