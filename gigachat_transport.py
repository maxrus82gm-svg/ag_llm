from __future__ import annotations

import os
import time
import uuid
import hashlib
import threading

import httpx


OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://api.giga.chat/v1/chat/completions"

_access_token: str | None = None
_access_token_valid_until = 0.0
_token_binding = None
_token_lock = threading.Lock()


def real_preflight(model_id: str) -> dict:
    """Read-only Ultra preparation, never account evidence or send authority.

    Public sources checked 2026-11-15: developers.sber.ru/docs/ru/gigachat/
    models/gigachat-3-ultra and models/updates. The reported "128 thousand"
    context is not promoted to an exact, calibrated admission bound. No proven
    Ultra output/reasoning cap or account entitlement exists in this revision.
    Caller preferences and verified-looking dictionaries cannot supply them.
    """
    from model_registry import get_model_spec
    from ordinary_chat_service import PreSendDenied

    try:
        if type(model_id) is not str or model_id != 'gigachat_ultra':
            raise ValueError
        model = get_model_spec(model_id)
        if (model.provider != 'gigachat' or model.is_local
                or model.provider_model_id != 'GigaChat-3-Ultra'):
            raise ValueError
    except (KeyError, ValueError, RuntimeError):
        # Never echo untrusted model text or exception data into diagnostics.
        raise PreSendDenied('real_model_contract_unavailable') from None

    return dict(model_id=model.model_id, provider_model_id=model.provider_model_id,
                contract_status='PARTIAL', checked_on='2026-11-15',
                context_tokens=None, reported_context='128 thousand tokens', output_tokens=None,
                account_availability='UNVERIFIED', real_available=False,
                holds=['server_authority_unavailable', 'provider_context_bound_uncalibrated',
                       'provider_output_cap_unknown', 'reasoning_usage_contract_unverified',
                       'account_scope_availability_unverified', 'tls_cache_contract_unverified',
                       'production_recovery_unverified', 'independent_acceptance_pending',
                       'owner_go_required'])


def extract_usage(data: object) -> dict:
    """Return provider-reported token usage without estimating missing values."""
    empty = {"prompt_tokens": None, "completion_tokens": None,
             "total_tokens": None, "raw": None}
    if not isinstance(data, dict) or not isinstance(data.get("usage"), dict):
        return empty
    raw = dict(data["usage"])
    result = {"raw": raw}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = raw.get(key)
        result[key] = value if isinstance(value, int) and not isinstance(value, bool) else None
    return result


async def get_access_token(*, authority=None) -> str:
    from gigachat_admission import require_real_authority
    require_real_authority(authority)  # Before cache, credentials or I/O.
    global _access_token, _access_token_valid_until, _token_binding
    from ordinary_chat_service import PreSendDenied
    # Nonblocking across event loops/threads: never wait on a lock held by a
    # suspended coroutine. One account stream is enforced by the session too.
    if not _token_lock.acquire(blocking=False):
        raise PreSendDenied('oauth_busy')
    try:
        credentials, scope = authority.credentials()
        binding = (hashlib.sha256(credentials.encode()).digest(), scope, authority.account_id,
                   authority.trust_identity)
        if _access_token and binding == _token_binding and time.time() + 30 < _access_token_valid_until:
            return _access_token
        _access_token = None
        _access_token_valid_until = 0
        _token_binding = None
        reply = await authority.request('oauth', OAUTH_URL, method='POST',
            headers={'Authorization': 'Basic '+credentials, 'RqUID': str(uuid.uuid4()),
                     'Accept': 'application/json'}, data={'scope': scope}, maximum=16384)
        token, expires = reply.get('access_token'), reply.get('expires_at')
        if (type(token) is not str or not token or len(token) > 8192
                or any(ord(c) < 33 or ord(c) > 126 for c in token)
                or type(expires) is not int or not time.time()+30 < expires/1000 <= time.time()+3600):
            raise PreSendDenied('oauth_response_invalid')
        _access_token, _access_token_valid_until, _token_binding = token, expires/1000, binding
        return token
    finally:
        _token_lock.release()
