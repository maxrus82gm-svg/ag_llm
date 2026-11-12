"""Ordinary Core bridge; no real provider admission exists in this revision.

The shared request service owns preparation, parsing and cancellation. Turn/RAW/
Run Store still own persistence. Only the exact in-memory fixture transport can
execute, and TurnService additionally requires explicitly isolated TEMP roots.
Adding a provider requires a separately accepted S3b path, not a config flag.
"""
import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, replace
import hashlib

import ordinary_chat_service as chat
import ultra_budget_policy as policy
from .ordinary_chat_test_adapter import OfflineTestAdapter, _FixtureTransport

FIXTURE_ENDPOINT = "fixture://ordinary/v1"
_ADMISSION = ContextVar("ordinary_fake_admission", default=None)


def offline_policy():
    """Explicit synthetic caps ONLY. No empirical/real model calibration claim."""
    return dict(schema_version=1, revision_label="H32 SYNTHETIC OFFLINE ONLY",
        run=dict(max_request_bytes=8192, max_request_input_tokens_est=8192,
                 max_verification_request_bytes=8192, max_verification_request_input_tokens_est=8192,
                 max_run_liability_tokens=8320, max_run_attempts=1,
                 max_attempts_per_role={"planner": None, "executor": None, "dredd": None},
                 verification_reserve_tokens=0, verification_reserve_attempts=0),
        estimation={"profiles": [], "missing_profile": "HARD_BOUND"}, output_reserve="MAX_TOKENS",
        compressor={"mode": "DENY"}, mcp={"mode": "DENY"}, read={"max_full_read_bytes": 2048},
        ordinary=dict(mode="BUDGET", max_request_bytes=8192, max_request_input_tokens_est=8192,
                      max_scope_liability_tokens=8320, max_scope_attempts=1))


def admission_snapshot(prepared):
    wire = policy.serialize_request_body(prepared.payload)
    raw = offline_policy()
    snapshot = policy.validate_policy(raw)
    return dict(endpoint=FIXTURE_ENDPOINT, wire_bytes=len(wire),
                wire_sha256=hashlib.sha256(wire).hexdigest(), policy=raw,
                policy_sha256=snapshot.revision_sha256)


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
        guard = _ADMISSION.get()
        if guard is None:
            return chat.ChatResult(chat.Outcome.REJECTED, chat.Execution.NOT_STARTED,
                                   prepared.model, prepared.request_ref, error_code="turn_admission_required")
        capture = _UsageCapture(self, guard)
        result = asyncio.run(chat.execute_request(prepared, transport=capture))
        reasoning = capture.reasoning
        if (result.usage.status == "invalid" or result.usage.completion_tokens is None
                or reasoning is not None and reasoning > result.usage.completion_tokens):
            reasoning = None
        return replace(result, usage=BridgeUsage(**vars(result.usage), reasoning_tokens=reasoning))

    def execute_turn(self, prepared, guard):
        # Thread/task-local binding; concurrent Turns never share mutable callbacks.
        token = _ADMISSION.set(guard)
        try:
            return self.execute(prepared)
        finally:
            _ADMISSION.reset(token)


class _UsageCapture:
    """Extract only an explicitly nested numeric metric, never retain raw data."""
    def __init__(self, adapter, guard):
        self.adapter = adapter
        self.transport = adapter._transport
        self.guard = guard
        self.used = False
        self.reasoning = None

    async def send(self, payload, *, timeout_seconds):
        if self.used or type(self.transport) is not _FixtureTransport:
            raise chat.PreSendDenied("fixture_admission_required")
        self.used = True
        wire = policy.serialize_request_body(payload)
        self.guard(wire)
        if self.adapter._transport is not self.transport or type(self.transport) is not _FixtureTransport:
            raise chat.PreSendDenied("fixture_transport_changed")
        response = await self.transport.send_bytes(wire, timeout_seconds=timeout_seconds)
        if type(response) is dict and type(response.get("usage")) is dict:
            details = response["usage"].get("completion_tokens_details")
            value = details.get("reasoning_tokens") if type(details) is dict else None
            if type(value) is int and value >= 0:
                self.reasoning = value
        return response
