"""User-approved STANDARD GigaChat onramp with a private personal-chat store.

The personal chat is backed by existing Ultra workspace identity/ledger internally,
but the user never has to choose or create a project Workspace. Creation is only
after explicit console consent; existing workspaces and chats are never adopted.
"""
from __future__ import annotations

import os
from pathlib import Path
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
MAX_SENDS = 12
MAX_WIRE_BYTES = 8192
MAX_ANSWER_TOKENS = 128
MAX_LIABILITY = MAX_SENDS * (MAX_WIRE_BYTES + MAX_ANSWER_TOKENS)
LIFETIME_SECONDS = 1800
PERSONAL_DIRNAME = "personal_chats"
PERSONAL_LABEL = "Личные чаты"


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


def prepare_personal_chat(api):
    """Only call after a fresh explicit owner consent, never on GET or launch.

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
        core.create_chat_record(root, title="Первый диалог", expected_workspace_id=wid)
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
        f"[LIVE] Только GigaChat-2 ({OBSERVED_MODEL}); максимум {MAX_SENDS} отправок, "
        f"{MAX_ANSWER_TOKENS} токенов ответа и {MAX_WIRE_BYTES} байт wire на отправку.\n"
        f"[LIVE] Консервативная liability до {MAX_LIABILITY} токенов, срок "
        f"{LIFETIME_SECONDS // 60} минут; тариф/остаток UNKNOWN.\n"
        "[LIVE] Внимание: настоящие вызовы API могут быть платными.\n"
    )
    try:
        consent = ask(f"Включить LIVE для личного чата? Введите LIVE {MAX_SENDS} (Enter = без LIVE): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if consent != f"LIVE {MAX_SENDS}":
        out.write("[LIVE] Отказ: STANDARD откроется без REAL.\n")
        return None
    record, root, wid = prepare_personal_chat(api)
    approval = LiveApproval(
        grant_id="StandardLive" + secrets.token_hex(16),
        user_go=f"interactive owner console confirmation: LIVE {MAX_SENDS}, personal {record.workspace_id}",
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
                     "GigaChat-2:2.0.30.01 on 2026-11-15; operator bound 128"),),
        max_oauth=1, max_catalog=1, max_inference=MAX_SENDS,
        max_liability_tokens=MAX_LIABILITY, max_request_bytes=MAX_WIRE_BYTES,
        max_answer_tokens=MAX_ANSWER_TOKENS,
    )
    session = ProviderSession(root, wid, approval)
    out.write("[LIVE] Разрешение для «Личные чаты» создано. Историю других Workspace не затрагиваем.\n")
    return session
