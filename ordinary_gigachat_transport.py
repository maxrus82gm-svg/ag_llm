"""Byte-oriented GigaChat HTTP boundary; H33 permits synthetic HTTP ONLY.

No network transport, real token provider or REAL switch exists here. The existing
gigachat_transport remains the owner of real OAuth. A later reviewed REAL gate
must supply that authority; a receipt or an HTTP URL is not authority.
"""
import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import math

import httpx

from gigachat_transport import CHAT_URL
from ordinary_chat_service import PreSendDenied, ProviderResponse


@dataclass
class OfflineHTTPFixture:
    """Server-owned synthetic input, never reconstructed from browser/config.

    Observations deliberately omit headers, token and raw provider data. Test
    instrumentation can inspect the actual httpx request inside MockTransport.
    """
    body: bytes = b'{"choices":[{"message":{"role":"assistant","content":"TEST HTTP"}}]}'
    status: int = 200
    error: str | None = None
    delay: float = 0
    token_error: bool = False
    token_calls: int = field(default=0, init=False)
    requests: list = field(default_factory=list, init=False)

    async def token(self):
        # Explicit fake of the existing get_access_token boundary: no env,
        # credentials, OAuth, token cache, refresh or fallback.
        self.token_calls += 1
        if self.token_error:
            raise RuntimeError('synthetic_token_unavailable')
        return 'H33-SYNTHETIC-NON-CREDENTIAL'


class GigaChatTransport:
    """One POST of admitted immutable bytes, no serialization and no retry."""

    def __init__(self, fixture=None):
        if type(fixture) is not OfflineHTTPFixture:
            raise PreSendDenied('real_transport_disabled')
        self._fixture = fixture

    @property
    def endpoint(self):
        return CHAT_URL

    async def send_bytes(self, wire, *, timeout_seconds, max_response_bytes, admission=None):
        from web_alarm.turn_service import _TurnAdmission
        if (type(self) is not GigaChatTransport or type(self._fixture) is not OfflineHTTPFixture
                or type(admission) is not _TurnAdmission or type(wire) is not bytes
                or type(max_response_bytes) is not int or max_response_bytes <= 0
                or type(timeout_seconds) not in (int, float)
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
            raise PreSendDenied('server_turn_authority_required')
        # This checks the exact owner/transport/binding BEFORE any token call.
        admission.limits(timeout_seconds, max_response_bytes)
        admission.authorize(wire, self)
        fixture = self._fixture
        token = await fixture.token()
        if token != 'H33-SYNTHETIC-NON-CREDENTIAL':
            raise RuntimeError('synthetic_token_required')

        async def handle(request):
            # Final physical boundary: compare what httpx actually constructed,
            # after admission, after token acquisition, immediately before send.
            if (request.method != 'POST' or str(request.url) != self.endpoint
                    or request.content != wire or self._fixture is not fixture):
                from ordinary_chat_service import PreSendUncertain
                raise PreSendUncertain('http_wire_or_endpoint_changed')
            admission.check(wire, self, physical=True)
            fixture.requests.append(dict(method=request.method, endpoint=str(request.url),
                wire_bytes=len(request.content), wire_sha256=hashlib.sha256(request.content).hexdigest(),
                timeout=dict(request.extensions['timeout'])))
            if fixture.delay:
                await asyncio.sleep(fixture.delay)
            if fixture.error == 'timeout':
                raise httpx.ReadTimeout('synthetic_timeout')
            if fixture.error == 'transport':
                raise httpx.ConnectError('synthetic_transport_error')
            return httpx.Response(fixture.status, content=fixture.body)

        # Never instantiate a default/network HTTP transport. Disable proxy env
        # and redirects even though the only possible transport is MockTransport.
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False,
                    follow_redirects=False, timeout=httpx.Timeout(timeout_seconds)) as client:
                admission.check(wire, self)
                async with client.stream('POST', self.endpoint, content=wire, headers={
                        'Authorization': 'Bearer '+token, 'Accept': 'application/json',
                        'Content-Type': 'application/json; charset=utf-8'}) as response:
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(data) + len(chunk) > max_response_bytes:
                            return ProviderResponse(response.status_code, None, 'response_limit_exceeded')
                        data.extend(chunk)
                    try:
                        decoded = json.loads(data.decode('utf-8'))
                    except (ValueError, UnicodeError, RecursionError):
                        return ProviderResponse(response.status_code, None, 'invalid_json_response')
                    return ProviderResponse(response.status_code, decoded)
        except httpx.TimeoutException:
            raise TimeoutError("provider_timeout") from None
