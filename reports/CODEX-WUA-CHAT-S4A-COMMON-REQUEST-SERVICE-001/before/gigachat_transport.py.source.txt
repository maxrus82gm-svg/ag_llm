from __future__ import annotations

import os
import time
import uuid

import httpx


OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://api.giga.chat/v1/chat/completions"

_access_token: str | None = None
_access_token_valid_until = 0.0


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


async def get_access_token() -> str:
    global _access_token, _access_token_valid_until

    if _access_token and time.time() < _access_token_valid_until:
        return _access_token

    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

    if not credentials:
        raise RuntimeError("Не найдена переменная среды GIGACHAT_CREDENTIALS.")

    headers = {
        "Authorization": f"Basic {credentials}",
        "RqUID": str(uuid.uuid4()),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OAUTH_URL,
            headers=headers,
            data={"scope": scope},
        )
        response.raise_for_status()

    data = response.json()
    token = data.get("access_token")

    if not token:
        raise RuntimeError(f"GigaChat не вернул access_token: {data}")

    _access_token = token
    _access_token_valid_until = time.time() + 25 * 60
    return token
