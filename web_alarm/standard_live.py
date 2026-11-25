"""User-approved STANDARD GigaChat onramp with a private personal-chat store.

The personal chat is backed by existing Ultra workspace identity/ledger internally,
but the user never has to choose or create a project Workspace. Creation is only
after explicit console consent; existing workspaces and chats are never adopted.
"""
from __future__ import annotations

import os
import hashlib
import hmac
from dataclasses import asdict
from pathlib import Path
import platform
import secrets
import stat
import time

import context_storage as core
from ordinary_chat_service import PreSendDenied
from ultra_budget_ledger import BudgetLedger
from gigachat_runtime import LiveApproval, ModelContract, ProviderSession
from .live_bootstrap import _verified_workspace
from .workspace_registry import WorkspaceRegistryError

MODEL_ID = "gigachat_2"
OBSERVED_MODEL = "GigaChat-2:2.0.30.01"
MAX_WIRE_BYTES = 8192
MAX_ANSWER_TOKENS = 20000  # user preference ceiling, not a provider output claim
LIFETIME_SECONDS = 86400  # runtime grant only
PERSONAL_DIRNAME = "personal_chats"
PERSONAL_LABEL = "Личные чаты"
_CONSENT = (core.ULTRA_DIRNAME, "provider_sessions", "gigachat_standard_consent.json")
_SCOPE = "GIGACHAT_API_PERS"
_ACCOUNT = "existing-windows-gigachat-pers-account"
_REQUEST_BYTES = 4096


def standard_approval():
    """Use the same six-model contract for explicit consent and runtime renewal."""
    from model_registry import list_model_specs
    contracts = tuple(
        ModelContract(m.model_id, 128000 if m.model_id.startswith("gigachat_2") or m.model_id == "gigachat_ultra" else 32768,
                      MAX_ANSWER_TOKENS, (OBSERVED_MODEL,) if m.model_id == MODEL_ID else (),
                      "STANDARD six-model admission and bounded operator output preference",
                      version_mode="EXACT" if m.model_id == MODEL_ID else "DISCOVER_FAMILY")
        for m in list_model_specs() if m.enabled and m.provider == "gigachat" and not m.is_local
    )
    if len(contracts) != 6:
        raise PreSendDenied("live_registry_changed")
    return LiveApproval(
        grant_id="InAppGigaChat" + secrets.token_hex(16),
        user_go="local owner GIGACHAT 6 consent bound to the STANDARD provider profile",
        independent_review="Bounded offline verification required before owner merge; general release HOLD",
        account_id=_ACCOUNT, scope=_SCOPE, expires_at=time.time() + LIFETIME_SECONDS,
        contracts=contracts, max_oauth=None, max_catalog=1, max_inference=None,
        max_liability_tokens=None, max_request_bytes=_REQUEST_BYTES,
        max_answer_tokens=MAX_ANSWER_TOKENS, user_turn_mode=True,
    )


def _consent_binding(approval):
    from gigachat_runtime import MODELS_URL
    from gigachat_transport import CHAT_URL, OAUTH_URL
    from model_registry import get_model_spec

    host = platform.node()
    if not host:
        raise PreSendDenied("consent_host_unverifiable")
    policy = asdict(approval)
    for runtime_field in ("grant_id", "expires_at", "user_go", "independent_review"):
        del policy[runtime_field]
    policy["provider_models"] = [get_model_spec(c.model_id).provider_model_id for c in approval.contracts]
    policy["endpoints"] = [OAUTH_URL, MODELS_URL, CHAT_URL]
    policy["host_installation"] = [host, str(Path.home())]
    return hashlib.sha256(core._json_bytes(policy)).hexdigest()


def standard_credentials():
    value = os.environ.get("GIGACHAT_CREDENTIALS", "")
    if (not 0 < len(value) <= 8192 or any(not 33 <= ord(c) <= 126 for c in value)
            or os.environ.get("GIGACHAT_SCOPE", _SCOPE) != _SCOPE):
        raise PreSendDenied("credentials_or_scope_invalid")
    return value


def _credential_binding(salt, credential):
    return hashlib.sha256(bytes.fromhex(salt) + credential.encode("ascii")).hexdigest()


def read_standard_consent(root, wid, approval):
    try:
        consent = core.read_ultra_json_bounded(root, _CONSENT[1:], max_bytes=4096)
        if (type(consent) is not dict or consent.get("schema") != 1
                or consent.get("workspace_id") != wid):
            raise ValueError
        if consent.get("state") == "REVOKED":
            return None
        salt = consent["salt"]
        if consent.get("state") != "ALLOWED" or type(salt) is not str or len(salt) != 64:
            raise ValueError
        if consent["policy"] != _consent_binding(approval):
            raise PreSendDenied("consent_policy_changed")
        if not hmac.compare_digest(consent["credential_binding"], _credential_binding(salt, standard_credentials())):
            raise PreSendDenied("consent_credentials_changed")
        return consent
    except core.StorageReadError as exc:
        if exc.code == "missing":
            return None
        raise PreSendDenied("consent_storage_unavailable") from None
    except PreSendDenied:
        raise
    except (KeyError, TypeError, ValueError):
        raise PreSendDenied("consent_storage_unavailable") from None


def save_standard_consent(root, wid, approval=None, *, credential=None):
    consent = {"schema": 1, "workspace_id": wid, "state": "REVOKED"}
    if approval is not None:
        salt = secrets.token_hex(32)
        consent.update(state="ALLOWED", salt=salt, policy=_consent_binding(approval),
                       credential_binding=_credential_binding(salt, credential))
    with core._existing_workspace_writer(root, wid) as writer:
        core._ensure_write_directory(writer.anchor, _CONSENT[:-1])
        core._replace_verified(writer.anchor, _CONSENT, core._json_bytes(consent))
    return consent


def eligible_workspaces(api):
    """Legacy read-only discovery; never adopt an existing ledger or project."""
    ready = []
    try:
        registered = api.registry.list()
    except Exception:
        return ready
    for record in registered:
        try:
            root, wid = _verified_workspace(api, record.workspace_id)
        except Exception:
            continue
        ready.append((record, root, wid))
    return ready


def personal_chat_registration(registry):
    """Read only. An arbitrary existing directory is NOT a personal chat."""
    root = registry.storage_root / PERSONAL_DIRNAME
    if not os.path.lexists(root):
        return None
    try:
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or core._is_link_or_reparse(info):
            return None
        return registry.find_by_root(root)
    except (OSError, ValueError, WorkspaceRegistryError):
        return None


def prepare_personal_chat(api, *, initial_chat_id=None):
    """Create the private local chat store only after an explicit owner action.

    A browser personal-create POST or optional operator LIVE consent can create
    local storage, but neither grants real provider authority by itself.
    Refuse to adopt an unregistered or unverified preexisting directory,
    including incomplete enrollment. Leave any incomplete data for review.
    """
    registry = api.registry
    root = registry.storage_root / PERSONAL_DIRNAME
    if os.path.lexists(root):
        record = personal_chat_registration(registry)
        if record is None:
            raise PreSendDenied("personal_storage_existing_unregistered")
        verified, wid = _verified_workspace(api, record.workspace_id)
        if verified != root:
            raise PreSendDenied("personal_storage_identity_changed")
        return record, verified, wid

    try:
        root.mkdir(mode=0o700)
        if root.resolve(strict=True) != root:
            raise PreSendDenied("personal_storage_link_refused")
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or core._is_link_or_reparse(info):
            raise PreSendDenied("personal_storage_link_refused")
        identity = core.ensure_workspace_storage(root)
        wid = identity["workspace_id"]
        BudgetLedger(root, wid).initialize()
        if initial_chat_id is None:
            core.create_chat_record(root, title="Первый диалог", expected_workspace_id=wid)
        else:
            core.create_chat_record(root, title="Новый чат", chat_id=initial_chat_id,
                                    expected_workspace_id=wid, auto_title=True)
        record = registry.register(PERSONAL_LABEL, root)
        verified, saved_id = _verified_workspace(api, record.workspace_id)
        if verified != root or saved_id != wid:
            raise PreSendDenied("personal_storage_enrollment_not_verified")
        return record, verified, wid
    except PreSendDenied:
        raise
    except Exception:
        # Never delete an uncertain root, mint a replacement identity or
        # reinterpret partial writes as a new blank personal conversation.
        raise PreSendDenied("personal_storage_preparation_failed") from None


def offer_standard_live(api, ask, out):
    """No Workspace number: one explicit console consent for personal chats.

    Console consent remains the only new-grant authority. Browser GET/F5 and
    environment variables cannot mint a grant or create a personal chat.
    """
    out.write("\n[STANDARD] Доступ к истории сохраняется без LIVE.\n")
    if (not os.environ.get("GIGACHAT_CREDENTIALS")
            or os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS") != "GIGACHAT_API_PERS"):
        out.write("[LIVE] Учётные данные не доступны процессу. Продолжаем без LIVE.\n")
        return None
    out.write(
        "[LIVE] Личные чаты: отдельный внутренний каталог, без выбора Workspace.\n"
        "[LIVE] Старые проекты, Workspace и история не меняются и не переносятся.\n"
        f"[LIVE] Только GigaChat-2 ({OBSERVED_MODEL}); каждая отправка требует действия в чате.\n"
        f"[LIVE] Предпочтительный максимум ответа до {MAX_ANSWER_TOKENS} токенов; "
        f"технический предел запроса {MAX_WIRE_BYTES} байт.\n"
        f"[LIVE] Срок подключения {LIFETIME_SECONDS // 3600} часа; тариф/остаток UNKNOWN.\n"
        "[LIVE] Внимание: настоящие вызовы API могут быть платными.\n"
    )
    try:
        consent = ask("Включить LIVE для личного чата? Введите LIVE CHAT (Enter = без LIVE): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if consent != "LIVE CHAT":
        out.write("[LIVE] Отказ: STANDARD откроется без REAL.\n")
        return None
    record, root, wid = prepare_personal_chat(api)
    approval = LiveApproval(
        grant_id="StandardLive" + secrets.token_hex(16),
        user_go=f"interactive owner console confirmation: LIVE CHAT, personal {record.workspace_id}",
        independent_review="H38 bounded offline Windows review; first GigaChat-2 REAL proof 2026-11-15; "
                           "personal-onramp requires independent Windows CI and physical GUI acceptance",
        account_id="existing-windows-gigachat-pers-account",
        scope="GIGACHAT_API_PERS",
        expires_at=time.time() + LIFETIME_SECONDS,
        contracts=(ModelContract(
            model_id=MODEL_ID, context_tokens=128000, output_tokens=MAX_ANSWER_TOKENS,
            response_models=(OBSERVED_MODEL,), provider_output_cap_tokens=None,
            version_mode="EXACT",
            evidence="GigaChat 2 Lite 128k official docs; observed real "
                     "GigaChat-2:2.0.30.01 on 2026-11-15; operator output preference ceiling 20000"),),
        max_oauth=None, max_catalog=1, max_inference=None,
        max_liability_tokens=None, max_request_bytes=MAX_WIRE_BYTES,
        max_answer_tokens=MAX_ANSWER_TOKENS, user_turn_mode=True,
    )
    session = ProviderSession(root, wid, approval)
    out.write("[LIVE] Разрешение для «Личные чаты» создано. Историю других Workspace не затрагиваем.\n")
    return session
