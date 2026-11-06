"""Independent WEB24 Stage5 offline boundary checks; disposable root only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from web_alarm.ultra_chat import OfflineUltraChatService, UltraChatError
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.workspace_registry import WorkspaceRegistry

class ReviewerStage5(unittest.TestCase):
    def setUp(self):
        item = tempfile.TemporaryDirectory(prefix="web24_s5_review_")
        self.addCleanup(item.cleanup)
        self.root = Path(item.name)
        self.registry = WorkspaceRegistry(self.root / "registry")
        self.service = OfflineUltraChatService(self.registry, self.root)

    def new_chat(self, title):
        _, project = self.service.create_workspace({"title":title})
        ws = project["wa_workspace_id"]
        chat = "chat_" + uuid4().hex
        self.service.create_chat(ws, {"chat_id":chat,"initialize_workspace":True})
        return ws,chat

    def test_same_key_in_two_workspaces_does_not_mix_history_or_deduplicate(self):
        left,lchat=self.new_chat("A synthetic")
        right,rchat=self.new_chat("B synthetic")
        self.assertNotEqual(left,right)
        key=uuid4().hex
        original=_FixtureTransport.send
        payloads=[]
        async def track(fake, payload, **kwargs):
            payloads.append(payload)
            return await original(fake,payload,**kwargs)
        with patch.object(_FixtureTransport,"send",track):
            a=self.service.submit_turn(left,lchat,{"idempotency_key":key,"text":"Left only","model_ref":"gigachat_2_pro"})
            b=self.service.submit_turn(right,rchat,{"idempotency_key":key,"text":"Right only","model_ref":"gigachat_ultra"})
            self.assertEqual(a["state"],"SUCCEEDED")
            self.assertEqual(b["state"],"SUCCEEDED")
            again=self.service.submit_turn(left,lchat,{"idempotency_key":key,"text":"Left only","model_ref":"gigachat_2_pro"})
        self.assertEqual(again,a)
        self.assertEqual(len(payloads),2)
        self.assertEqual(len(self.service.messages(left,lchat,None,50)["messages"]),2)
        self.assertEqual(len(self.service.messages(right,rchat,None,50)["messages"]),2)
        self.assertNotIn("Right only",repr(self.service.messages(left,lchat,None,50)))
        self.assertNotIn("Left only",repr(self.service.messages(right,rchat,None,50)))

    def test_bad_model_ref_fails_without_fake_send_or_stored_message(self):
        ws,chat=self.new_chat("Model negative")
        body={"idempotency_key":uuid4().hex,"text":"No model should run","model_ref":"some_invalid_model_777"}
        with patch.object(_FixtureTransport,"send",side_effect=AssertionError("unexpected fake invocation")) as fake:
            with self.assertRaises(UltraChatError):
                self.service.submit_turn(ws,chat,body)
        fake.assert_not_called()
        self.assertEqual(self.service.messages(ws,chat,None,50)["messages"],[])

    def test_reopened_service_reuses_persisted_result_without_transport(self):
        ws,chat=self.new_chat("No replay")
        body={"idempotency_key":uuid4().hex,"text":"S5 repeated","model_ref":"gigachat_2_pro"}
        first=self.service.submit_turn(ws,chat,body)
        fresh=OfflineUltraChatService(self.registry,self.root)
        with patch.object(_FixtureTransport,"send",side_effect=AssertionError("duplicate transport")) as fake:
            second=fresh.submit_turn(ws,chat,body)
        fake.assert_not_called()
        self.assertEqual(first,second)
        self.assertEqual(len(fresh.messages(ws,chat,None,50)["messages"]),2)

if __name__ == "__main__":
    unittest.main()
