"""Opt-in STANDARD GigaChat onramp. One trusted console consent; no browser/env grant.

Only the previously observed GigaChat-2 version is admitted in this first
production-adjacent slice. Additional registered models remain visible but
cannot infer until individually reviewed. No historical Workspace enrollment.
"""
from __future__ import annotations

import os
import secrets
import time

from gigachat_runtime import LiveApproval, ModelContract, ProviderSession
from .live_bootstrap import _verified_workspace

# Conservative OPERATOR ceilings, not asserted GigaChat provider maxima/prices.
MODEL_ID = "gigachat_2"
OBSERVED_MODEL = "GigaChat-2:2.0.30.01"
MAX_SENDS = 12
MAX_WIRE_BYTES = 8192
MAX_ANSWER_TOKENS = 128
MAX_LIABILITY = MAX_SENDS * (MAX_WIRE_BYTES + MAX_ANSWER_TOKENS)
LIFETIME_SECONDS = 1800


def eligible_workspaces(api):
    """Read-only discovery: only previously enrolled, registered, verified roots."""
    ready = []
    try:
        registered = api.registry.list()
    except Exception:
        return ready
    for record in registered:
        try:
            root, wid = _verified_workspace(api, record.workspace_id)
        except Exception:
            continue  # A missing/corrupt old ledger is NEVER migrated on launch.
        ready.append((record, root, wid))
    return ready


def offer_standard_live(api, ask, out):
    """Construct a server-only grant only after exact physical console confirmation.

    No command line flag, environment switch, HTTP request or browser input
    can mint a LiveApproval. Declining preserves existing STANDARD OFFLINE.
    """
    out.write("\n[STANDARD] История и настройки доступны без GigaChat LIVE.\n")
    if (not os.environ.get("GIGACHAT_CREDENTIALS")
            or os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS") != "GIGACHAT_API_PERS"):
        out.write("[LIVE] Учётные данные не доступны процессу. Продолжаем без LIVE.\n")
        return None
    ready = eligible_workspaces(api)
    if not ready:
        out.write("[LIVE] Нет зарегистрированных Workspace с подготовленным аудитом; "
                  "историю автоматически не изменяем. Продолжаем без LIVE.\n")
        return None
    out.write("[LIVE] Workspace с проверенным хранилищем и журналом учёта:\n")
    for n, (record, _root, _wid) in enumerate(ready, 1):
        out.write(f"  {n}. {record.display_name} [{record.workspace_id}]\n")
    try:
        raw = ask("Введите номер Workspace для LIVE (Enter = без LIVE): ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not raw or not raw.isascii() or not raw.isdigit() or not 1 <= int(raw) <= len(ready):
        out.write("[LIVE] Не выбран Workspace. STANDARD запущен без LIVE.\n")
        return None
    record, root, wid = ready[int(raw)-1]
    out.write(
        f"[LIVE] Только GigaChat-2 ({OBSERVED_MODEL}); максимум {MAX_SENDS} отправок, "
        f"{MAX_ANSWER_TOKENS} токенов ответа и {MAX_WIRE_BYTES} байт wire на отправку.\n"
        f"[LIVE] Лимит консервативной liability: {MAX_LIABILITY} токенов; "
        f"срок {LIFETIME_SECONDS // 60} минут. Тариф и реальный остаток неизвестны.\n"
        "[LIVE] Это физические вызовы API, они могут расходовать оплачиваемые токены.\n"
    )
    try:
        consent = ask(f"Для включения на Workspace {record.display_name!r} введите LIVE {MAX_SENDS}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if consent != f"LIVE {MAX_SENDS}":
        out.write("[LIVE] Включение отклонено; STANDARD остаётся без LIVE.\n")
        return None
    approval = LiveApproval(
        grant_id="StandardLive" + secrets.token_hex(16),
        user_go=f"interactive owner console confirmation: LIVE {MAX_SENDS}, selected {record.workspace_id}",
        independent_review="H38 bounded offline Windows review; first GigaChat-2 REAL proof 2026-11-15; "
                           "this STANDARD adapter needs independent CI and physical GUI acceptance",
        account_id="existing-windows-gigachat-pers-account",
        scope="GIGACHAT_API_PERS",
        expires_at=time.time() + LIFETIME_SECONDS,
        contracts=(ModelContract(
            model_id=MODEL_ID, context_tokens=128000, output_tokens=MAX_ANSWER_TOKENS,
            response_models=(OBSERVED_MODEL,), provider_output_cap_tokens=None,
            version_mode="EXACT",
            evidence="GigaChat 2 Lite 128k official documentation; observed REAL exact model "
                     "GigaChat-2:2.0.30.01 on 2026-11-15; operator output bound 128"),),
        max_oauth=1, max_catalog=1, max_inference=MAX_SENDS,
        max_liability_tokens=MAX_LIABILITY, max_request_bytes=MAX_WIRE_BYTES,
        max_answer_tokens=MAX_ANSWER_TOKENS,
    )
    session = ProviderSession(root, wid, approval)
    out.write("[LIVE] Подтверждено. Создан одноразовый ограниченный grant; "
              "при закрытии окна сеанс завершается.\n")
    return session
