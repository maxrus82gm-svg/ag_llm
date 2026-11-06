"""Independent WEB24 S4 deadline/cancellation oracles; no real provider or user storage."""
import asyncio
import hashlib
from pathlib import Path
import unittest
from ordinary_chat_service import Execution, Outcome, execute_request
from test_ordinary_chat_service import limits, reply, request

class DeadlineSafetyReviewer(unittest.IsolatedAsyncioTestCase):
    async def test_external_cancel_swallowed_by_adapter_is_not_success(self):
        """An explicit Task.cancel after send entry cannot publish SUCCESS."""
        entered = asyncio.Event()
        cancelled = asyncio.Event()
        calls = []
        class Suppresses:
            async def send(self, payload, *, timeout_seconds):
                calls.append(payload)
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cancelled.set()
                    return reply(usage={"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3})
        task = asyncio.create_task(execute_request(request(limits=limits(timeout_seconds=2)), transport=Suppresses()))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        result = await asyncio.wait_for(task, 1)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(len(calls), 1)
        self.assertEqual((result.outcome, result.execution), (Outcome.UNKNOWN_AFTER_START, Execution.RESPONSE_RECEIVED))
        self.assertIsNone(result.text)
        self.assertEqual(result.usage.total_tokens, 3)

    async def test_deadline_swallowed_cancellation_repeats_no_success(self):
        for i in range(16):
            calls = []
            class Suppresses:
                async def send(self, payload, *, timeout_seconds):
                    calls.append(payload)
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        return reply(usage={"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3})
            result = await execute_request(request(limits=limits(timeout_seconds=0.005)), transport=Suppresses())
            with self.subTest(i=i):
                self.assertEqual(len(calls), 1)
                self.assertEqual((result.outcome, result.execution), (Outcome.UNKNOWN_AFTER_START, Execution.RESPONSE_RECEIVED))
                self.assertIsNone(result.text)
                self.assertEqual(result.usage.total_tokens, 3)

    async def test_bounded_instant_success_still_succeeds(self):
        sent = []
        class Instant:
            async def send(self, payload, *, timeout_seconds):
                sent.append(payload)
                return reply(usage={"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3})
        result = await execute_request(request(limits=limits(timeout_seconds=2)), transport=Instant())
        self.assertEqual(result.outcome, Outcome.COMPLETED)
        self.assertEqual(result.execution, Execution.RESPONSE_RECEIVED)
        self.assertEqual(len(sent), 1)
        self.assertEqual(result.usage.total_tokens, 3)

    async def test_before_send_cancel_never_sends(self):
        class Forbidden:
            async def send(self, *_args, **_kwargs):
                self.fail("transport must not be reached")
        result = await execute_request(request(), transport=Forbidden(), cancelled=lambda: True)
        self.assertEqual((result.outcome, result.execution), (Outcome.CANCELLED_BEFORE_START, Execution.NOT_STARTED))

    def test_source_pinned_to_published_h18(self):
        project=Path(__file__).resolve().parents[2]
        hashes={
            "ordinary_chat_service.py":"f74dcd873bb533d36d5c72a6c29b453e4093d0cda0725139ff93762225156e3b",
            "test_ordinary_chat_service.py":"af70ac23b0c922c52a7ec0da5515f19a9525adc0bab0daf7800f3927ee54b05c",
        }
        for filename,want in hashes.items():
            with self.subTest(filename=filename):
                raw=(project/filename).read_bytes().replace(b"\r\n",b"\n")
                self.assertEqual(hashlib.sha256(raw).hexdigest(),want)
