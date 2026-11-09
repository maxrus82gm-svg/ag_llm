"""Ordinary Core bridge; no real provider admission exists in this revision.

The shared request service owns preparation, parsing and cancellation. Turn/RAW/
Run Store still own persistence. Only the exact in-memory fixture transport can
execute, and TurnService additionally requires explicitly isolated TEMP roots.
Adding a provider requires a separately accepted S3b path, not a config flag.
"""
import asyncio
from dataclasses import dataclass, replace

import ordinary_chat_service as chat
from .ordinary_chat_test_adapter import OfflineTestAdapter, _FixtureTransport


@dataclass(frozen=True)
class BridgeUsage(chat.Usage):
    # Canonical bridge contract: reasoning is a SUBSET of completion, never
    # another addend to total. A future provider adapter must normalize it.
    reasoning_tokens: int | None = None


class OrdinaryCoreAdapter(OfflineTestAdapter):
    """Reuse the existing prepared snapshot and provider-neutral send protocol.

    context_loader is server-owned and runs inside Turn's existing writer lock,
    only when accepting a NEW request. Replay always restores the saved snapshot.
    The current constructor deliberately exposes no endpoint, credentials or
    arbitrary transport injection.
    """

    def __init__(self, *, context_ref, response, context_loader=None):
        super().__init__(context=(), context_ref=context_ref,
                         limits=chat.RequestLimits(32, 2048, 8192, 8192, 128, 8),
                         response=response)
        self._context_loader = context_loader

    def freeze(self, body):
        if body["context_ref"] != self._context_ref:
            raise chat.PreparationError("invalid_context_ref")
        if self._context_loader is not None:
            self._context = self._context_loader()
        return super().freeze(body)

    def execute(self, prepared):
        # No Boolean, config_ref or injected object can activate a real sender.
        if type(self._transport) is not _FixtureTransport:
            return chat.ChatResult(chat.Outcome.REJECTED, chat.Execution.NOT_STARTED,
                                   prepared.model, prepared.request_ref,
                                   error_code="provider_admission_required")
        capture = _UsageCapture(self._transport)
        result = asyncio.run(chat.execute_request(prepared, transport=capture))
        reasoning = capture.reasoning
        if (result.usage.status == "invalid" or result.usage.completion_tokens is None
                or reasoning is not None and reasoning > result.usage.completion_tokens):
            reasoning = None
        return replace(result, usage=BridgeUsage(**vars(result.usage), reasoning_tokens=reasoning))


class _UsageCapture:
    """Extract only an explicitly nested numeric metric, never retain raw data."""
    def __init__(self, transport):
        self.transport = transport
        self.reasoning = None

    async def send(self, payload, *, timeout_seconds):
        response = await self.transport.send(payload, timeout_seconds=timeout_seconds)
        if type(response) is dict and type(response.get("usage")) is dict:
            details = response["usage"].get("completion_tokens_details")
            value = details.get("reasoning_tokens") if type(details) is dict else None
            if type(value) is int and value >= 0:
                self.reasoning = value
        return response
