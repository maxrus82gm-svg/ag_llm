"""Explicit S4B fixture adapter. Its only transport returns in-memory data."""
import asyncio
from copy import deepcopy
from dataclasses import asdict

import ordinary_chat_service as chat


class _FixtureTransport:
    def __init__(self, response):
        self.response = response

    async def send(self, payload, *, timeout_seconds):
        return deepcopy(self.response)


class OfflineTestAdapter:
    def __init__(self, *, context, context_ref, limits, response, refuse=False):
        if (type(limits) is not chat.RequestLimits or limits.max_request_bytes > 8192
                or limits.max_response_bytes > 8192 or limits.max_messages > 32
                or limits.max_message_bytes > 2048 or limits.timeout_seconds > 10
                or type(refuse) is not bool):
            raise ValueError("Expected bounded offline fixture limits")
        self._context = deepcopy(context)
        self._context_ref = context_ref
        self._limits = limits
        self._transport = _FixtureTransport(deepcopy(response))
        self._refuse = refuse

    def freeze(self, body):
        if body["context_ref"] != self._context_ref:
            raise chat.PreparationError("invalid_context_ref")
        prepared = chat.prepare_request(model_id=body["model_ref"], context=self._context,
                                        user_text=body["text"], context_ref=self._context_ref,
                                        limits=self._limits)
        return {"model": asdict(prepared.model), "limits": asdict(prepared.limits),
                "context": [asdict(message) for message in prepared.messages[:-1]],
                "request_ref": prepared.request_ref}

    @staticmethod
    def restore(snapshot, references, text):
        # The Turn authenticates this snapshot against its durable binding.
        # S4A rechecks the prepared request against its registry before dispatch.
        try:
            return chat.PreparedRequest(
                model=chat.ModelSpec(**snapshot["model"]),
                messages=tuple(chat.Message(**message) for message in snapshot["context"])
                + (chat.Message("user", text),),
                context_ref=references["context_ref"],
                limits=chat.RequestLimits(**snapshot["limits"]),
                request_ref=snapshot["request_ref"],
            )
        except (TypeError, KeyError, ValueError):
            raise ValueError("Invalid offline prepared snapshot") from None

    def execute(self, prepared):
        if self._refuse:
            return chat.ChatResult(chat.Outcome.REJECTED, chat.Execution.NOT_STARTED,
                                   prepared.model, prepared.request_ref, error_code="fixture_refused")
        return asyncio.run(chat.execute_request(prepared, transport=self._transport))
