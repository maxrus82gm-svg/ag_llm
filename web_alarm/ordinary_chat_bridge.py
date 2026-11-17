"""Ordinary Core bridge; no real provider admission exists in this revision.

The shared request service owns preparation, parsing and cancellation. Turn/RAW/
Run Store still own persistence. Only exact in-memory or HTTP fixtures execute;
TurnService additionally requires explicitly isolated TEMP roots.
Adding a provider requires a separately accepted S3b path, not a config flag.
"""
import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, replace
import hashlib

import ordinary_chat_service as chat
import ultra_budget_policy as policy
from ordinary_gigachat_transport import GigaChatTransport
from gigachat_runtime import RealGigaChatTransport
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


def admission_snapshot(prepared, *, endpoint=None):
    wire = policy.serialize_request_body(prepared.payload)
    raw = offline_policy()
    snapshot = policy.validate_policy(raw)
    return dict(endpoint=FIXTURE_ENDPOINT if endpoint is None else endpoint, wire_bytes=len(wire),
                wire_sha256=hashlib.sha256(wire).hexdigest(), policy=raw,
                policy_sha256=snapshot.revision_sha256)


@dataclass(frozen=True)
class BridgeUsage(chat.Usage):
    # Canonical bridge contract: reasoning is a SUBSET of completion, never
    # another addend to total. A future provider adapter must normalize it.
    reasoning_tokens: int | None = None


@dataclass(frozen=True)
class CachedBridgeUsage(BridgeUsage):
    precached_prompt_tokens: int | None = None


class OrdinaryCoreAdapter(OfflineTestAdapter):
    """Reuse the existing prepared snapshot and provider-neutral send protocol.

    context_loader is server-owned and runs inside Turn's existing writer lock,
    only when accepting a NEW request. Replay always restores the saved snapshot.
    The current constructor deliberately exposes no endpoint, credentials or
    arbitrary transport injection.
    """

    def __init__(self, *, context_ref, response, context_loader=None, http_fixture=None):
        super().__init__(context=(), context_ref=context_ref,
                         limits=chat.RequestLimits(32, 2048, 8192, 8192, 128, 8),
                         response=response)
        self._context_loader = context_loader
        self._evm_profile = None
        if http_fixture is not None:
            self._transport = GigaChatTransport(http_fixture)

    @classmethod
    def for_provider(cls, session, *, context_ref, model_id, context_loader=None, answer_tokens=128,
                     evm_profile=None):
        from ordinary_gigachat_transport import create_real_transport
        adapter = cls(context_ref=context_ref, response=None, context_loader=context_loader)
        contract = session.contract(model_id)
        if evm_profile is not None:
            if (type(evm_profile) is not dict or set(evm_profile) !=
                    {'profile_id', 'settings_version', 'timeout_seconds'}
                    or type(evm_profile['timeout_seconds']) is not int
                    or not 5 <= evm_profile['timeout_seconds'] <= 120):
                raise chat.PreSendDenied('evm_profile_invalid')
            adapter._evm_profile = dict(evm_profile)
        adapter._limits = chat.RequestLimits(32, 2048, session.approval.max_request_bytes,
            524288, min(answer_tokens, session.approval.max_answer_tokens, contract.output_tokens),
            evm_profile['timeout_seconds'] if evm_profile is not None else 8)
        adapter._transport = create_real_transport(model_id, authority=session)
        return adapter

    def admission_snapshot(self, prepared):
        if type(self._transport) is RealGigaChatTransport:
            session = self._transport.session
            wire = policy.serialize_request_body(prepared.payload)
            contract = next(c for c in session.approval.contracts if c.model_id == prepared.model.model_id)
            raw = offline_policy()
            raw['revision_label'] = 'Ordinary bounded provider '+session.approval.grant_id
            raw['ordinary'].update(max_request_bytes=session.approval.max_request_bytes,
                max_request_input_tokens_est=session.approval.max_request_bytes,
                max_scope_liability_tokens=session.approval.max_request_bytes+prepared.limits.max_output_tokens)
            return dict(endpoint=self._transport.endpoint, wire_bytes=len(wire),
                wire_sha256=hashlib.sha256(wire).hexdigest(), policy=raw,
                policy_sha256=policy.validate_policy(raw).revision_sha256,
                grant_id=session.approval.grant_id, model_contract={**vars(contract), 'response_models': list(contract.response_models)},
                provider_mode='PROTOCOL_TEST' if session.synthetic else 'REAL',
                **({'evm_profile': self._evm_profile} if self._evm_profile is not None else {}))
        endpoint = self._transport.endpoint if type(self._transport) is GigaChatTransport else None
        return admission_snapshot(prepared, endpoint=endpoint)

    def freeze(self, body):
        if body["context_ref"] != self._context_ref:
            raise chat.PreparationError("invalid_context_ref")
        if self._context_loader is not None:
            self._context = self._context_loader()
        return super().freeze(body)

    def execute(self, prepared):
        # No Boolean, config_ref or injected object can activate a real sender.
        if type(self._transport) not in (_FixtureTransport, GigaChatTransport, RealGigaChatTransport):
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
        normalized = BridgeUsage(**vars(result.usage), reasoning_tokens=reasoning) if capture.cached is None else CachedBridgeUsage(
            **vars(result.usage), reasoning_tokens=reasoning, precached_prompt_tokens=capture.cached)
        return replace(result, usage=normalized)

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
        self.cached = None

    async def send(self, payload, *, timeout_seconds):
        if self.used or type(self.transport) not in (_FixtureTransport, GigaChatTransport, RealGigaChatTransport):
            raise chat.PreSendDenied("fixture_admission_required")
        self.used = True
        wire = policy.serialize_request_body(payload)
        if type(self.transport) is _FixtureTransport:
            self.guard(wire)
        if self.adapter._transport is not self.transport:
            raise chat.PreSendDenied("fixture_transport_changed")
        if type(self.transport) in (GigaChatTransport, RealGigaChatTransport):
            response = await self.transport.send_bytes(wire, timeout_seconds=timeout_seconds,
                max_response_bytes=self.adapter._limits.max_response_bytes, admission=self.guard)
        else:
            response = await self.transport.send_bytes(wire, timeout_seconds=timeout_seconds)
        decoded = response.data if type(response) is chat.ProviderResponse else response
        if type(decoded) is dict and type(decoded.get("usage")) is dict:
            cached = decoded['usage'].get('precached_prompt_tokens')
            if type(cached) is int and cached >= 0:
                self.cached = cached
            details = decoded["usage"].get("completion_tokens_details")
            value = details.get("reasoning_tokens") if type(details) is dict else None
            if type(value) is int and value >= 0:
                self.reasoning = value
        return response
