"""Offline contract oracles; no installed sender or live provider is required."""
import asyncio
from dataclasses import FrozenInstanceError, replace
import importlib
import json
import os
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gigachat_transport
import model_registry
import ordinary_chat_service
from model_registry import ModelSpec

from ordinary_chat_service import (
    Execution, Outcome, PreparationError, RequestLimits, execute_request,
    parse_response, prepare_request,
)


def limits(**overrides):
    values = dict(max_messages=9, max_message_bytes=1024, max_request_bytes=8192,
                  max_response_bytes=4096, max_output_tokens=64, timeout_seconds=0.1)
    values.update(overrides)
    return RequestLimits(**values)


def request(**overrides):
    values = dict(model_id="gigachat_2_pro", context=(), user_text="Привет",
                  context_ref="synthetic-snapshot-1", limits=limits())
    values.update(overrides)
    return prepare_request(**values)


class PreparationContract(unittest.TestCase):
    def test_explicit_registered_model_and_wire_payload(self):
        prepared = request(context=({"role": "system", "content": "Кратко"},))
        self.assertEqual(prepared.model.model_id, "gigachat_2_pro")
        self.assertEqual(prepared.payload, {
            "model": "GigaChat-2-Pro", "stream": False, "max_tokens": 64,
            "messages": [{"role": "system", "content": "Кратко"},
                         {"role": "user", "content": "Привет"}],
        })

    def test_unknown_model_has_no_fallback(self):
        with self.assertRaises(PreparationError) as caught:
            request(model_id="unknown-provider-secret")
        self.assertEqual(caught.exception.code, "model_unavailable")
        self.assertNotIn("secret", str(caught.exception))

    def test_tool_context_rejected(self):
        with self.assertRaises(PreparationError) as caught:
            request(context=({"role": "tool", "content": "not permitted"},))
        self.assertEqual(caught.exception.code, "invalid_context")

    def test_every_registered_model_resolves_from_canonical_registry(self):
        for model in model_registry.list_model_specs():
            with self.subTest(model=model.model_id):
                prepared = request(model_id=model.model_id)
                self.assertEqual(prepared.model, model)
                self.assertEqual(prepared.payload["model"], model.provider_model_id)

    def test_missing_coerced_and_padded_model_ids_rejected(self):
        for model_id in (None, "", 2, " gigachat_ultra", "gigachat_ultra "):
            with self.subTest(model_id=model_id), self.assertRaises(PreparationError) as caught:
                request(model_id=model_id)
            self.assertEqual(caught.exception.code, "model_unavailable")

    def test_disabled_and_unsupported_registry_entries_rejected(self):
        original = model_registry.get_model_spec("gigachat_2_pro")
        for change in (dict(enabled=False), dict(provider="other"), dict(is_local=True),
                       dict(provider_model_id=""), dict(provider_model_id=" wrong ")):
            with self.subTest(change=change), patch.dict(
                model_registry._MODEL_REGISTRY, {original.model_id: replace(original, **change)}
            ), self.assertRaises(PreparationError):
                request()

    def test_complete_context_order_and_exact_text(self):
        context = [{"role": "system", "content": "Правила"},
                   {"role": "user", "content": " Был вопрос "},
                   {"role": "assistant", "content": "Ответ\n"}]
        expected = context + [{"role": "user", "content": "Привет"}]
        self.assertEqual(request(context=context).payload["messages"], expected)

    def test_corrupt_context_matrix_is_refused(self):
        contexts = (None, {}, "text", [None], [{}],
                    [{"role": "user", "content": "x", "secret": "x"}],
                    [{"role": "assistant", "content": "x"}],
                    [{"role": "user", "content": "x"}],
                    [{"role": "system", "content": "x"}] * 2,
                    [{"role": "user", "content": "x"}, {"role": "user", "content": "y"}],
                    [{"role": "function", "content": "x"}],
                    [{"role": [], "content": "x"}],
                    [{"role": "system", "content": []}],
                    [{"role": "system", "content": "  "}],
                    [{"role": "system", "content": "\ud800"}])
        for context in contexts:
            with self.subTest(context=context), self.assertRaises(PreparationError) as caught:
                request(context=context)
            self.assertEqual(caught.exception.code, "invalid_context")

    def test_invalid_current_user_or_context_reference(self):
        for name in ("user_text", "context_ref"):
            for value in (None, 1, "", "  ", "\ud800"):
                with self.subTest(name=name, value=value), self.assertRaises(PreparationError):
                    request(**{name: value})

    def test_invalid_limits_are_explicit_errors(self):
        for name in ("max_messages", "max_message_bytes", "max_request_bytes",
                     "max_response_bytes", "max_output_tokens"):
            for value in (0, -1, True, 1.5, "2"):
                with self.subTest(name=name, value=value), self.assertRaises(PreparationError):
                    limits(**{name: value})
        for value in (0, -1, True, "2", float("nan"), float("inf"), 10**1000):
            with self.subTest(timeout=value), self.assertRaises(PreparationError):
                limits(timeout_seconds=value)
        with self.assertRaises(PreparationError):
            request(limits={})

    def test_message_count_includes_current_user_and_system(self):
        context = [{"role": "system", "content": "s"}]
        self.assertEqual(len(request(context=context, limits=limits(max_messages=2)).messages), 2)
        with self.assertRaises(PreparationError) as caught:
            request(context=context, limits=limits(max_messages=1))
        self.assertEqual(caught.exception.code, "limit_exceeded")

    def test_message_utf8_boundary(self):
        # The context ref is also subject to this bound; use a short synthetic ref.
        self.assertEqual(request(user_text="я", context_ref="r", limits=limits(max_message_bytes=2)).messages[-1].content, "я")
        with self.assertRaises(PreparationError):
            request(user_text="я", context_ref="r", limits=limits(max_message_bytes=1))

    def test_wire_byte_boundary_uses_entire_json(self):
        prepared = request()
        # Independent exact wire bytes, no serializer helper from the implementation.
        wire = json.dumps(prepared.payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertEqual(request(limits=limits(max_request_bytes=len(wire))).payload, prepared.payload)
        with self.assertRaises(PreparationError):
            request(limits=limits(max_request_bytes=len(wire)-1))

    def test_determinism_and_provenance_binding(self):
        self.assertEqual(request(), request())
        a = request()
        for b in (request(context_ref="other"), request(user_text="other"),
                  request(model_id="gigachat_ultra"), request(limits=limits(max_output_tokens=65))):
            self.assertNotEqual(a.request_ref, b.request_ref)

    def test_snapshot_deep_freeze_and_shell_choice_change(self):
        context = [{"role": "system", "content": "keep"}]
        shell_selection = "gigachat_2_pro"
        prepared = request(model_id=shell_selection, context=context)
        original = prepared.payload
        context[0]["content"] = "changed"
        context.append({"role": "tool", "content": "changed"})
        prepared.payload["messages"][0]["content"] = "changed"
        shell_selection = "gigachat_ultra"
        other = request(model_id=shell_selection)
        self.assertEqual(prepared.payload, original)
        self.assertEqual(prepared.payload["model"], "GigaChat-2-Pro")
        self.assertEqual(other.payload["model"], "GigaChat-3-Ultra")
        with self.assertRaises(FrozenInstanceError):
            prepared.model.model_id = "changed"
        with self.assertRaises(FrozenInstanceError):
            prepared.messages[0].content = "changed"


def reply(**overrides):
    value = {"model": "GigaChat-2-Pro", "created": 123,
             "choices": [{"message": {"role": "assistant", "content": " Ответ\n"},
                          "finish_reason": "stop"}]}
    value.update(overrides)
    return value


class ResponseContract(unittest.TestCase):
    def test_answer_and_safe_metadata(self):
        prepared = request()
        result = parse_response(prepared, reply(secret="DO-NOT-EXPOSE"))
        self.assertEqual(result.outcome, Outcome.COMPLETED)
        self.assertEqual(result.execution, Execution.RESPONSE_RECEIVED)
        self.assertEqual(result.text, " Ответ\n")
        self.assertEqual(result.request_ref, prepared.request_ref)
        self.assertEqual(result.model, prepared.model)
        self.assertEqual(result.metadata.created, 123)
        self.assertEqual(result.metadata.finish_reason, "stop")
        self.assertNotIn("DO-NOT-EXPOSE", repr(result))

    def test_usage_complete_zero_partial_missing_and_extra_fields(self):
        for usage, expected in (
            ({"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7, "secret": "DO-NOT-EXPOSE"}, ("complete", 5, 2, 7)),
            ({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, ("complete", 0, 0, 0)),
            ({"total_tokens": 7}, ("partial", None, None, 7)),
            ({}, ("partial", None, None, None)),
            (None, ("missing", None, None, None)),
        ):
            with self.subTest(usage=usage):
                result = parse_response(request(), reply(usage=usage))
                self.assertEqual(tuple(vars(result.usage).values()), expected)
                self.assertNotIn("DO-NOT-EXPOSE", repr(result))
        missing = parse_response(request(), reply()).usage
        self.assertIsNone(missing.total_tokens)
        self.assertEqual(missing.status, "missing")

    def test_existing_usage_parser_is_reused(self):
        from gigachat_transport import extract_usage
        with patch("ordinary_chat_service.extract_usage", wraps=extract_usage) as parser:
            parse_response(request(), reply(usage={"total_tokens": 7}))
        parser.assert_called_once()

    def test_invalid_answer_retains_valid_supplied_usage(self):
        response = reply(usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7})
        response["choices"][0]["message"]["role"] = "tool"
        result = parse_response(request(), response)
        self.assertEqual(result.outcome, Outcome.INVALID_RESPONSE)
        self.assertIsNone(result.text)
        self.assertEqual((result.usage.status, result.usage.total_tokens), ("complete", 7))

    def test_invalid_usage_does_not_become_zero_or_known_cost(self):
        for usage in ([], "secret", 1, {"total_tokens": -1}, {"total_tokens": True},
                      {"total_tokens": 1.5}, {"total_tokens": "7"}, {"total_tokens": None},
                      {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 8}):
            with self.subTest(usage=usage):
                result = parse_response(request(), reply(usage=usage))
                self.assertEqual(result.outcome, Outcome.COMPLETED)
                self.assertEqual(result.usage.status, "invalid")
                self.assertIsNone(result.usage.total_tokens)

    def test_malformed_responses_are_typed_and_redacted(self):
        malformed = (None, "SECRET", [], {}, {"error": {"message": "SECRET"}},
                     reply(choices=None), reply(choices=[]), reply(choices=[{}, {}]),
                     reply(choices=["SECRET"]), reply(choices=[{}]),
                     reply(choices=[{"message": {"role": "user", "content": "SECRET"}}]),
                     reply(choices=[{"message": {"role": "assistant", "content": []}}]),
                     reply(choices=[{"message": {"role": "assistant", "content": " "}}]),
                     reply(model="wrong-SECRET"), reply(created=True), reply(created=-1),
                     reply(created="SECRET"), reply(extra=object()), reply(extra=float("nan")),
                     reply(extra="\ud800"))
        for response in malformed:
            with self.subTest(response=response):
                result = parse_response(request(), response)
                self.assertEqual(result.outcome, Outcome.INVALID_RESPONSE)
                self.assertEqual(result.execution, Execution.RESPONSE_RECEIVED)
                self.assertIsNone(result.text)
                self.assertIsNone(result.usage.total_tokens)
                self.assertNotIn("SECRET", repr(result))

    def test_incomplete_choice_or_tool_invocation_not_success(self):
        for finish in ("length", "tool_calls", "function_call", "SECRET", {}, []):
            with self.subTest(finish=finish):
                response = reply()
                response["choices"][0]["finish_reason"] = finish
                self.assertEqual(parse_response(request(), response).outcome, Outcome.INVALID_RESPONSE)
        for key in ("tool_calls", "function_call"):
            response = reply()
            response["choices"][0]["message"][key] = None
            self.assertEqual(parse_response(request(), response).outcome, Outcome.INVALID_RESPONSE)

    def test_missing_optional_fields_and_eos_compatibility(self):
        response = reply()
        del response["model"], response["created"], response["choices"][0]["finish_reason"]
        self.assertEqual(parse_response(request(), response).outcome, Outcome.COMPLETED)
        response["choices"][0]["finish_reason"] = "eos"
        self.assertEqual(parse_response(request(), response).outcome, Outcome.COMPLETED)

    def test_response_utf8_limit_and_cycle(self):
        response = reply()
        size = len(json.dumps(response, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(parse_response(request(limits=limits(max_response_bytes=size)), response).outcome, Outcome.COMPLETED)
        result = parse_response(request(limits=limits(max_response_bytes=size-1)), response)
        self.assertEqual(result.error_code, "response_limit_exceeded")
        cycle = {}
        cycle["cycle"] = cycle
        self.assertEqual(parse_response(request(), cycle).outcome, Outcome.INVALID_RESPONSE)


class FakeTransport:
    def __init__(self, response=None):
        self.response = reply() if response is None else response
        self.calls = []

    async def send(self, payload, *, timeout_seconds):
        self.calls.append((payload, timeout_seconds))
        return self.response


class ExecutionContract(unittest.IsolatedAsyncioTestCase):
    async def test_preparation_and_fake_execution_open_no_storage(self):
        with patch("builtins.open", side_effect=AssertionError("storage forbidden")) as opened:
            prepared = request(context_ref="synthetic/opaque/reference")
            result = await execute_request(prepared, transport=FakeTransport())
            self.assertEqual(result.outcome, Outcome.COMPLETED)
            opened.assert_not_called()
            with self.assertRaises(AssertionError):
                open("synthetic/opaque/reference")

    async def test_one_call_exact_wire_and_explicit_timeout(self):
        prepared, fake = request(), FakeTransport()
        result = await execute_request(prepared, transport=fake)
        self.assertEqual(result.outcome, Outcome.COMPLETED)
        self.assertEqual(fake.calls, [(prepared.payload, 0.1)])

    async def test_no_sender_default_or_missing_sender(self):
        with self.assertRaises(TypeError):
            await execute_request(request())
        result = await execute_request(request(), transport=None)
        self.assertEqual((result.outcome, result.execution), (Outcome.REJECTED, Execution.NOT_STARTED))

    async def test_revoked_or_changed_model_does_not_dispatch(self):
        prepared = request()
        for model in (replace(prepared.model, enabled=False),
                      replace(prepared.model, provider_model_id="different")):
            fake = FakeTransport()
            with patch.dict(model_registry._MODEL_REGISTRY, {model.model_id: model}):
                result = await execute_request(prepared, transport=fake)
            self.assertEqual(result.outcome, Outcome.REJECTED)
            self.assertEqual(result.execution, Execution.NOT_STARTED)
            self.assertEqual(fake.calls, [])

    async def test_forged_payload_binding_is_rejected_without_call(self):
        original = request()
        for prepared in (replace(original, request_ref="forged"), replace(original, messages=()),
                         replace(original, model=replace(original.model, provider="other"))):
            fake = FakeTransport()
            result = await execute_request(prepared, transport=fake)
            self.assertEqual(result.outcome, Outcome.REJECTED)
            self.assertEqual(fake.calls, [])

    async def test_adapter_mutation_cannot_change_prepared_request(self):
        prepared = request()
        snapshot = prepared.payload
        class Mutator:
            async def send(self, payload, **kwargs):
                payload["model"] = "mutated"
                payload["messages"].clear()
                return reply()
        self.assertEqual((await execute_request(prepared, transport=Mutator())).outcome, Outcome.COMPLETED)
        self.assertEqual(prepared.payload, snapshot)

    async def test_transport_error_is_redacted_uncertain_and_not_retried(self):
        class Broken(FakeTransport):
            async def send(self, payload, **kwargs):
                self.calls.append(payload)
                raise RuntimeError("Authorization: SECRET https://secret.invalid")
        fake = Broken()
        result = await execute_request(request(), transport=fake)
        self.assertEqual(result.outcome, Outcome.TRANSPORT_ERROR)
        self.assertEqual(result.execution, Execution.MAY_HAVE_EXECUTED)
        self.assertIsNone(result.usage.total_tokens)
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn("SECRET", repr(result))

    async def test_cancel_before_start_proves_no_call(self):
        fake = FakeTransport()
        result = await execute_request(request(), transport=fake, cancelled=lambda: True)
        self.assertEqual(result.outcome, Outcome.CANCELLED_BEFORE_START)
        self.assertEqual(result.execution, Execution.NOT_STARTED)
        self.assertEqual(fake.calls, [])
        self.assertIsNone(result.usage.total_tokens)

    async def test_cancel_after_response_preserves_known_usage_without_answer(self):
        flag = False
        class CancelOnReply:
            async def send(self, payload, **kwargs):
                nonlocal flag
                flag = True
                return reply(usage={"total_tokens": 7})
        result = await execute_request(request(), transport=CancelOnReply(), cancelled=lambda: flag)
        self.assertEqual(result.outcome, Outcome.UNKNOWN_AFTER_START)
        self.assertEqual(result.execution, Execution.RESPONSE_RECEIVED)
        self.assertEqual(result.usage.total_tokens, 7)
        self.assertIsNone(result.text)

    async def test_explicit_task_cancellation_after_entry_is_unknown(self):
        entered = asyncio.Event()
        class Waiting:
            async def send(self, payload, **kwargs):
                entered.set()
                await asyncio.Event().wait()
        task = asyncio.create_task(execute_request(request(), transport=Waiting()))
        await entered.wait()
        task.cancel()
        result = await task
        self.assertEqual(result.outcome, Outcome.UNKNOWN_AFTER_START)
        self.assertEqual(result.execution, Execution.MAY_HAVE_EXECUTED)

    async def test_external_cancel_suppressed_by_transport_cannot_publish_success(self):
        for clear_cancellation, total in ((False, 7), (True, None)):
            with self.subTest(clear_cancellation=clear_cancellation):
                prepared = request(limits=limits(timeout_seconds=5))
                entered = asyncio.Event()
                calls = []
                cancellations = []

                class Fake:
                    async def send(self, payload, *, timeout_seconds):
                        calls.append((payload, timeout_seconds))
                        entered.set()
                        try:
                            await asyncio.Event().wait()
                        except asyncio.CancelledError:
                            cancellations.append(True)
                            if clear_cancellation:
                                asyncio.current_task().uncancel()
                            return reply(usage={"total_tokens": total}) if total is not None else reply()

                task = asyncio.create_task(execute_request(prepared, transport=Fake()))
                await asyncio.wait_for(entered.wait(), timeout=5)
                self.assertTrue(task.cancel())
                result = await task
                self.assertEqual(cancellations, [True])
                self.assertEqual(calls, [(prepared.payload, 5)])
                self.assertEqual((result.outcome, result.execution),
                                 (Outcome.UNKNOWN_AFTER_START, Execution.RESPONSE_RECEIVED))
                self.assertIsNone(result.text)
                self.assertEqual(result.usage.total_tokens, total)
                self.assertEqual((result.model, result.request_ref), (prepared.model, prepared.request_ref))

    async def test_previous_cancel_count_does_not_reject_timely_success(self):
        fake = FakeTransport()

        async def run_after_handled_cancellation():
            task = asyncio.current_task()
            task.cancel()
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                pass
            self.assertEqual(task.cancelling(), 1)
            return await execute_request(request(), transport=fake)

        result = await asyncio.create_task(run_after_handled_cancellation())
        self.assertEqual(result.outcome, Outcome.COMPLETED)
        self.assertEqual(len(fake.calls), 1)

    async def test_timeout_is_unknown_and_one_attempt(self):
        class Slow(FakeTransport):
            async def send(self, payload, **kwargs):
                self.calls.append(payload)
                await asyncio.Event().wait()
        fake = Slow()
        result = await execute_request(request(limits=limits(timeout_seconds=0.01)), transport=fake)
        self.assertEqual((result.outcome, result.execution), (Outcome.UNKNOWN_AFTER_START, Execution.MAY_HAVE_EXECUTED))
        self.assertEqual(len(fake.calls), 1)

    async def test_swallowed_timeout_cannot_publish_late_success(self):
        class SwallowsCancellation:
            async def send(self, payload, **kwargs):
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    return reply()
        result = await execute_request(request(limits=limits(timeout_seconds=0.01)), transport=SwallowsCancellation())
        self.assertEqual((result.outcome, result.execution), (Outcome.UNKNOWN_AFTER_START, Execution.RESPONSE_RECEIVED))
        self.assertIsNone(result.text)

    async def test_timeout_fired_inside_one_clock_tick_remains_unknown(self):
        loop = asyncio.get_running_loop()
        start = loop.time()

        def clock():
            return start

        prepared = request(limits=limits(timeout_seconds=0.01))
        calls = []
        cancellations = []

        class Fake:
            async def send(self, payload, *, timeout_seconds):
                calls.append((payload, timeout_seconds))
                # Keep the next selector poll nonblocking. The real asyncio
                # timer is due within its lookahead, but clock() stays fixed.
                # Release the waiter two turns later if lookahead changes.
                release = asyncio.Event()
                loop.call_soon(loop.call_soon, release.set)
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    cancellations.append(loop.time())
                return reply(usage={"total_tokens": 7})

        with (patch.object(loop, "time", clock),
              patch.object(loop, "_clock_resolution", 0.015625),
              patch.object(ordinary_chat_service, "time", SimpleNamespace(monotonic=clock), create=True)):
            result = await execute_request(prepared, transport=Fake())
        self.assertEqual(cancellations, [start])
        self.assertEqual(calls, [(prepared.payload, 0.01)])
        self.assertEqual((result.outcome, result.execution), (Outcome.UNKNOWN_AFTER_START, Execution.RESPONSE_RECEIVED))
        self.assertIsNone(result.text)
        self.assertEqual(result.usage.total_tokens, 7)
        self.assertEqual((result.model, result.request_ref), (prepared.model, prepared.request_ref))

    async def test_immediate_reply_within_one_clock_tick_still_succeeds(self):
        loop = asyncio.get_running_loop()
        start = loop.time()
        prepared = request(limits=limits(timeout_seconds=0.01))
        fake = FakeTransport()
        with (patch.object(loop, "time", return_value=start),
              patch.object(loop, "_clock_resolution", 0.015625)):
            result = await execute_request(prepared, transport=fake)
        self.assertEqual(result.outcome, Outcome.COMPLETED)
        self.assertEqual(result.text, reply()["choices"][0]["message"]["content"])
        self.assertEqual(fake.calls, [(prepared.payload, 0.01)])

    async def test_absolute_deadline_checked_even_before_timer_callback(self):
        loop = asyncio.get_running_loop()
        for advance, expected in ((0.5, Outcome.COMPLETED), (1.0, Outcome.UNKNOWN_AFTER_START),
                                  (1.5, Outcome.UNKNOWN_AFTER_START)):
            with self.subTest(advance=advance):
                now = loop.time()

                def clock():
                    return now
                prepared = request(limits=limits(timeout_seconds=1.0))
                calls = []

                class Fake:
                    async def send(self, payload, *, timeout_seconds):
                        nonlocal now
                        calls.append(payload)
                        now += advance
                        # No yield before return, so the timer callback cannot run.
                        return reply(usage={"total_tokens": 7})

                with (patch.object(loop, "time", clock),
                      patch.object(ordinary_chat_service, "time", SimpleNamespace(monotonic=clock), create=True)):
                    result = await execute_request(prepared, transport=Fake())
                self.assertEqual(result.outcome, expected)
                self.assertEqual(result.execution, Execution.RESPONSE_RECEIVED)
                self.assertEqual(result.text, reply()["choices"][0]["message"]["content"] if expected is Outcome.COMPLETED else None)
                self.assertEqual(result.usage.total_tokens, 7)
                self.assertEqual(calls, [prepared.payload])

    async def test_bad_cancellation_predicate_fails_closed(self):
        fake = FakeTransport()
        result = await execute_request(request(), transport=fake, cancelled=lambda: "SECRET")
        self.assertEqual(result.outcome, Outcome.REJECTED)
        self.assertEqual(fake.calls, [])
        self.assertNotIn("SECRET", repr(result))


class OfflineBoundary(unittest.IsolatedAsyncioTestCase):
    async def test_import_and_execution_do_not_touch_network_oauth_or_credentials(self):
        import httpx
        original_getitem = os._Environ.__getitem__
        def deny_secret(self, key):
            if str(key).startswith("GIGACHAT_"):
                raise AssertionError("credential read forbidden")
            return original_getitem(self, key)
        def deny(*args, **kwargs):
            raise AssertionError("forbidden external boundary")
        with (patch.object(socket.socket, "connect", side_effect=deny) as network,
              patch.object(socket, "getaddrinfo", side_effect=deny) as dns,
              patch.object(httpx, "AsyncClient", side_effect=deny) as http,
              patch.object(gigachat_transport, "get_access_token", side_effect=deny) as oauth,
              patch.object(os._Environ, "__getitem__", deny_secret)):
            import ordinary_chat_service
            # Execute a fresh module namespace without changing identities in
            # the main suite. Boundaries are vetoed before its imports execute.
            name = "_ordinary_offline_probe"
            spec = importlib.util.spec_from_file_location(name, ordinary_chat_service.__file__)
            fresh = importlib.util.module_from_spec(spec)
            sys.modules[name] = fresh
            try:
                spec.loader.exec_module(fresh)
                fresh_limits = fresh.RequestLimits(**vars(limits()))
                prepared = fresh.prepare_request(model_id="gigachat_2_pro", context=(),
                    user_text="synthetic", context_ref="r", limits=fresh_limits)
                result = await fresh.execute_request(prepared, transport=FakeTransport())
            finally:
                del sys.modules[name]
            self.assertEqual(result.outcome.value, "completed")
            network.assert_not_called()
            dns.assert_not_called()
            http.assert_not_called()
            oauth.assert_not_called()
            # Vetoes have independent positive controls: no real request is made.
            def connect_probe():
                with socket.socket() as sock:
                    sock.connect(("192.0.2.1", 443))
            for probe in (connect_probe,
                          lambda: socket.getaddrinfo("offline.invalid", 443),
                          lambda: httpx.AsyncClient(),
                          lambda: os.environ.get("GIGACHAT_CREDENTIALS")):
                with self.assertRaises(AssertionError):
                    probe()
            with self.assertRaises(AssertionError):
                await gigachat_transport.get_access_token()

    def test_early_process_guard_negative_controls(self):
        if "ORDINARY_GUARD_LOG" not in os.environ:
            self.skipTest("early guard is installed by the task evidence runner")
        with socket.socket() as sock, self.assertRaises(PermissionError):
            sock.connect(("192.0.2.1", 443))
        with self.assertRaises(PermissionError):
            socket.getaddrinfo("offline.invalid", 443)
        with self.assertRaises(PermissionError):
            os.environ.get("GIGACHAT_CREDENTIALS")


if __name__ == "__main__":
    unittest.main()
