"""Synthetic proof that the cancelled reply cannot become durable Turn success."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import context_storage as core
import ordinary_chat_service as ordinary
import run_store as runs
from web_alarm.ordinary_chat_test_adapter import OfflineTestAdapter, _FixtureTransport
from web_alarm.turn_service import TurnService


class DurableExternalCancellation(unittest.TestCase):
    def test_cancelled_reply_remains_unknown_after_reopen(self):
        with tempfile.TemporaryDirectory(prefix="cancel_s4_") as directory:
            root = Path(directory)
            ws = core.ensure_workspace_storage(root)["workspace_id"]
            chat = core.create_chat(root)["chat_id"]
            body = dict(idempotency_key="cancel_probe_00001", text="Synthetic question",
                        model_ref="gigachat_2_pro", context_ref="fixture:v1", config_ref="s4b-offline:v1")
            reply = {"choices": [{"message": {"role": "assistant", "content": "Must not publish"}}],
                     "usage": {"total_tokens": 7}}
            adapter = OfflineTestAdapter(context=(), context_ref=body["context_ref"],
                                         limits=ordinary.RequestLimits(9, 2048, 8192, 8192, 64, 5),
                                         response=reply)
            calls, cancellations = [], []
            execute = ordinary.execute_request

            async def execute_observed(*args, **kwargs):
                owner = asyncio.current_task()

                async def fake_send(_fake, payload, *, timeout_seconds):
                    calls.append(payload["model"])
                    asyncio.get_running_loop().call_soon(owner.cancel)
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        cancellations.append(True)
                        asyncio.current_task().uncancel()
                        return reply

                with patch.object(_FixtureTransport, "send", fake_send):
                    return await execute(*args, **kwargs)

            service = TurnService(test_roots=[root], offline_adapter=adapter)
            with patch.object(ordinary, "execute_request", execute_observed):
                result = service.submit(root, ws, chat, body)
                reopened = TurnService(test_roots=[root], offline_adapter=adapter)
                self.assertEqual(reopened.get(root, ws, chat, result["turn_id"]), result)
                self.assertEqual(reopened.submit(root, ws, chat, body), result)
            self.assertEqual(cancellations, [True])
            self.assertEqual(calls, ["GigaChat-2-Pro"])
            self.assertEqual((result["state"], result["answer"]), ("UNKNOWN", None))
            self.assertEqual(result["usage"]["total_tokens"], 7)
            events = runs.load_stream_records(root, result["run_id"], "SERVER")
            self.assertEqual([event["event"] for event in events], ["turn_started", "turn_uncertain"])
            terminal = events[-1]["payload"]
            self.assertEqual(terminal["attempt_id"], result["attempt_id"])
            self.assertEqual(terminal["request_ref"], result["request_ref"])
            self.assertEqual(terminal["execution"], "response_received")
            self.assertEqual(runs.load_run_summary(root, result["run_id"])["turn"]["state"], "UNKNOWN")
            raw = root / ".ultra/chats" / chat / "messages"
            self.assertEqual({p.name for p in raw.glob("*.json")}, {result["user_message_id"] + ".json"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
