"""Independent WEB24 H19 cancellation and deadline tests; synthetic only."""
import asyncio
import hashlib
from pathlib import Path
import unittest
from ordinary_chat_service import Execution, Outcome, execute_request
from test_ordinary_chat_service import limits, reply, request

USAGE={"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}

class H19Reviewer(unittest.IsolatedAsyncioTestCase):
    async def check_external(self, undo):
        entered=asyncio.Event()
        calls=[]
        class Fake:
            async def send(self,payload,*,timeout_seconds):
                calls.append(payload)
                entered.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    if undo:
                        asyncio.current_task().uncancel()
                    return reply(usage=USAGE)
        task=asyncio.create_task(execute_request(
            request(limits=limits(timeout_seconds=2)),transport=Fake()))
        await asyncio.wait_for(entered.wait(),1)
        task.cancel()
        result=await asyncio.wait_for(task,1)
        self.assertEqual(len(calls),1)
        self.assertEqual((result.outcome,result.execution),
                         (Outcome.UNKNOWN_AFTER_START,Execution.RESPONSE_RECEIVED))
        self.assertIsNone(result.text)
        self.assertEqual(result.usage.total_tokens,3)

    async def test_external_cancel_swallowed(self):
        await self.check_external(False)

    async def test_external_cancel_and_child_uncancel(self):
        await self.check_external(True)

    async def test_prior_cancel_baseline_not_false_unknown(self):
        async def worker():
            owner=asyncio.current_task()
            owner.cancel()
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                pass
            class Fake:
                async def send(self,payload,*,timeout_seconds):
                    return reply(usage=USAGE)
            return await execute_request(request(limits=limits(timeout_seconds=2)),transport=Fake())
        result=await asyncio.create_task(worker())
        self.assertEqual((result.outcome,result.execution),
                         (Outcome.COMPLETED,Execution.RESPONSE_RECEIVED))

    async def test_immediate_answer_remains_completed(self):
        calls=[]
        class Fake:
            async def send(self,payload,*,timeout_seconds):
                calls.append(payload)
                return reply(usage=USAGE)
        result=await execute_request(request(limits=limits(timeout_seconds=2)),transport=Fake())
        self.assertEqual(result.outcome,Outcome.COMPLETED)
        self.assertEqual(len(calls),1)

    async def test_timeout_suppressed_always_unknown(self):
        for i in range(12):
            calls=[]
            class Fake:
                async def send(self,payload,*,timeout_seconds):
                    calls.append(payload)
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        return reply(usage=USAGE)
            result=await execute_request(request(limits=limits(timeout_seconds=.005)),transport=Fake())
            with self.subTest(i=i):
                self.assertEqual(len(calls),1)
                self.assertEqual((result.outcome,result.execution),
                                 (Outcome.UNKNOWN_AFTER_START,Execution.RESPONSE_RECEIVED))
                self.assertIsNone(result.text)
                self.assertEqual(result.usage.total_tokens,3)

    def test_pinned_h19_source_sha256(self):
        root=Path(__file__).resolve().parents[2]
        for path,expected in {
            "ordinary_chat_service.py":"0d0050807ab6b0c9277334e4f89010fee424f2750eaf6f1be3f9d7f6927a8843",
            "test_ordinary_chat_service.py":"9a3d95470c78a93daff07535320a63b72806ef9186c3adfa7bb945bb5adfde74",
        }.items():
            with self.subTest(path=path):
                raw=(root/path).read_bytes().replace(b"\r\n",b"\n")
                self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)
