"""Existing WUA OrdinaryCoreChatService/Turn/RAW + exact Colibri #108."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001"))
# Same actual isolated producer HTTP handler and fake Manager as #657.
from joint_transport import Joint, ChatClientError
import context_storage as core
import run_store as runs
import unittest
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import test_web_alarm_ultra_chat_s5 as s5
from web_alarm.ultra_chat import OrdinaryCoreChatService, UltraChatError
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from web_alarm.turn_service import TurnService
from ultra_budget_ledger import BudgetLedger

class Unified(s5.Fixture):
    stop=Joint.stop
    fake_stream=Joint.fake_stream
    fake_cancel=Joint.fake_cancel

    def setUp(self):
        super().setUp()
        Joint.setUp(self)
        self.enabled={self.target["target_id"]}
        self.service=OrdinaryCoreChatService(self.registry,self.root,
            colibri_transport=self.transport,colibri_enabled=lambda:set(self.enabled))
        self.ws,self.chat=self.create_chat("Unified chat")
        self.project=Path(self.registry.get(self.ws).workspace_root)
        self.wid=core.read_workspace_identity_bounded(self.project)["workspace_id"]
        self.local=self.target["target_id"]
        # Explicitly empty fixture only; production project context never discarded.
        core.save_project_context(self.project,"")

    def submit(self,text,model="gigachat_2_pro"):
        return self.service.submit_turn(self.ws,self.chat,self.body(text,model))

    def test_cloud_local_cloud_single_chat_raw_usage_reopen(self):
        wires=[]
        original=_FixtureTransport.send
        async def trace(fake,payload,**kw):
            wires.append(payload)
            return await original(fake,payload,**kw)
        with patch.object(_FixtureTransport,"send",trace):
            a=self.submit("Cloud first")
            before=BudgetLedger(self.project,self.wid).recover()
            local_body=self.body("Local second",self.local)
            try:b=self.service.submit_turn(self.ws,self.chat,local_body)
            except UltraChatError as e:raise AssertionError(e.code) from e
            self.assertEqual(b["state"],"SUCCEEDED")
            self.assertEqual(b["reasoning"],"Размышление 🌊")
            self.assertEqual(b["answer"],"Ответ")
            self.assertEqual(b["usage"]["status"],"partial")
            self.assertIsNone(b["usage"]["reasoning_tokens"])
            after=BudgetLedger(self.project,self.wid).recover()
            self.assertEqual((after.event_count,after.attempts),(before.event_count,before.attempts))
            self.assertEqual(self.calls,[[{"role":"user","content":"Cloud first"},
                {"role":"assistant","content":a["answer"]},{"role":"user","content":"Local second"}]])
            c=self.submit("Cloud third","gigachat_2_max")
        self.assertEqual(c["state"],"SUCCEEDED")
        self.assertEqual([m["content"] for m in wires[-1]["messages"]],
            ["Cloud first",a["answer"],"Local second","Ответ","Cloud third"])
        self.assertEqual(len(core.list_chats(self.project)),1)
        history=core.read_chat_history_bounded(self.project,self.chat)["messages"]
        self.assertEqual([m["text"] for m in history],
            ["Cloud first",a["answer"],"Local second","Ответ","Cloud third",c["answer"]])
        reader=TurnService(test_roots=[self.project])
        local_turn=reader._load(self.project,self.wid,self.chat,b["turn_id"])
        self.assertEqual(local_turn["schema_version"],3)
        self.assertEqual(local_turn["chat_id"],self.chat)
        wire=json.loads(local_turn["prepared"]["wire_utf8"])
        self.assertEqual(wire["conversation_id"],self.chat);self.assertEqual(wire["turn_id"],b["turn_id"])
        self.assertNotIn("Authorization",local_turn["prepared"]["wire_utf8"])
        self.assertEqual(len(BudgetLedger(self.project,self.wid).recover().attempts),2)
        page=self.service.messages(self.ws,self.chat,None,50)
        self.assertEqual(len(page["messages"]),6)
        metric=next(m["metrics"] for m in page["messages"] if m["message_id"]==b["assistant_message_id"])
        self.assertEqual(metric["usage"],b["usage"])
        self.assertFalse(page["usage_summary"]["complete"])
        # A disabled target does not hide history or replay the existing request.
        self.enabled.clear()
        self.assertEqual(self.service.submit_turn(self.ws,self.chat,local_body),b)
        with self.assertRaises(UltraChatError) as exc:self.submit("blocked",self.local)
        self.assertEqual(exc.exception.code,"model_disabled")
        self.service=OrdinaryCoreChatService(self.registry,self.root) # no Colibri at all
        self.assertEqual(self.service.submit_turn(self.ws,self.chat,local_body),b)
        self.assertEqual(self.service.messages(self.ws,self.chat,None,50)["messages"],page["messages"])
        self.assertEqual(len(self.calls),1)

    def test_partial_unknown_durable_no_second_dispatch_and_context_excluded(self):
        def truncated(*a,**kw):
            for e in self.fake_stream(*a,**kw):
                if e["type"]=="done":raise ChatClientError("stream_truncated",502)
                yield e
        self.manager_stream=truncated
        body=self.body("unfinished",self.local)
        try:b=self.service.submit_turn(self.ws,self.chat,body)
        except UltraChatError as e:raise AssertionError(e.code) from e
        self.assertEqual(b["state"],"UNKNOWN")
        self.assertIsNone(b["answer"]);self.assertEqual(b["partial_answer"],"Ответ")
        self.assertEqual(b["reasoning"],"Размышление 🌊")
        self.assertEqual(self.service.submit_turn(self.ws,self.chat,body),b)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(core.read_chat_history_bounded(self.project,self.chat)["messages"]),1)
        with patch.object(_FixtureTransport,"send",return_value={"choices":[{"message":{"role":"assistant","content":"cloud"}}]}) as send:
            c=self.submit("next")
        self.assertEqual(c["state"],"SUCCEEDED")
        self.assertEqual(send.call_args.args[0]["messages"],[{"role":"user","content":"next"}])

    def test_system_refused_and_disabled_before_dispatch(self):
        core.save_project_context(self.project,"A real system directive")
        with self.assertRaises(UltraChatError) as e:self.submit("unsupported",self.local)
        self.assertEqual(e.exception.code,"unsupported_capability")
        self.assertEqual(self.calls,[])
        self.assertEqual(core.read_chat_history_bounded(self.project,self.chat)["messages"],[])
        self.assertIsNone(self.service.latest_turn(self.ws,self.chat)["turn"])

    def test_cancel_ack_not_stop_with_partial_and_completion_wins(self):
        ready=threading.Event();release=threading.Event()
        def blocking(*a,**kw):
            for e in self.fake_stream(*a,**kw):
                if e["type"]=="delta":
                    # Reasoning has already been sent; wait until WUA journal read.
                    ready.set()
                    if not release.wait(15):raise RuntimeError("test barrier")
                yield e
        self.manager_stream=blocking
        with ThreadPoolExecutor() as pool:
            job=pool.submit(self.submit,"cancel race",self.local)
            try:
                self.assertTrue(ready.wait(10))
                import time
                deadline=time.monotonic()+10
                while True:
                    active=self.service.latest_turn(self.ws,self.chat)["turn"]
                    if active["reasoning"]:break
                    if time.monotonic()>deadline:self.fail("Reasoning not durably visible")
                    time.sleep(.05)
                ack=self.service._turn_request("cancel",self.ws,self.chat,active["turn_id"],{})
                self.assertEqual(ack["state"],"ATTEMPTING")
                self.assertTrue(ack["cancel_requested"])
                self.assertTrue(ack["cancel_ack"]["cancel_accepted"])
                self.assertFalse(ack["cancel_ack"]["stop_confirmed"])
            finally:release.set()
            final=job.result(timeout=25)
        self.assertEqual(final["state"],"SUCCEEDED")
        self.assertTrue(final["cancel_requested"])
        self.assertEqual(len(self.calls),1)

    def test_lost_raw_ack_replays_only_durable_result(self):
        body=self.body("recover saved result",self.local)
        original=TurnService._commit
        def fail_assistant(root,turn,role,text):
            if role=="assistant":
                raise OSError("simulated loss before RAW publication")
            return original(root,turn,role,text)
        with patch.object(TurnService,"_commit",side_effect=fail_assistant),self.assertRaises(UltraChatError):
            self.service.submit_turn(self.ws,self.chat,body)
        self.assertEqual(len(self.calls),1)
        self.service=OrdinaryCoreChatService(self.registry,self.root)
        b=self.service.submit_turn(self.ws,self.chat,body)
        self.assertEqual(b["state"],"SUCCEEDED")
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(core.read_chat_history_bounded(self.project,self.chat)["messages"]),2)

    def test_cancel_before_dispatch_and_readonly_ready(self):
        entered=threading.Event();release=threading.Event()
        original=self.transport.run
        def pause(f,**opts):
            guard=opts["before_dispatch"]
            def delayed():
                entered.set()
                if not release.wait(15):raise RuntimeError("test barrier")
                guard()
            return original(f,**{**opts,"before_dispatch":delayed})
        with patch.object(self.transport,"run",side_effect=pause),ThreadPoolExecutor() as pool:
            pending=pool.submit(self.submit,"cancel before wire",self.local)
            try:
                self.assertTrue(entered.wait(10))
                active=self.service.latest_turn(self.ws,self.chat)["turn"]
                self.assertEqual(active["state"],"ATTEMPTING")
                ack=self.service._turn_request("cancel",self.ws,self.chat,active["turn_id"],{})
                self.assertTrue(ack["cancel_requested"])
                self.assertIsNone(ack["cancel_ack"])
            finally:release.set()
            final=pending.result(timeout=25)
        self.assertEqual(final["state"],"CANCELLED")
        self.assertEqual(self.calls,[])
        self.assertEqual(self.cancels,[])
        records=runs.load_stream_records(self.project,final["run_id"],"SERVER")
        self.assertNotIn("turn_bridge_dispatch",[e["event"] for e in records])
        self.assertEqual(len(core.read_chat_history_bounded(self.project,self.chat)["messages"]),1)
        self.assertEqual(self.service.chat_usage(self.ws,self.chat)["attempts"],0)

if __name__=="__main__":unittest.main(verbosity=2)
