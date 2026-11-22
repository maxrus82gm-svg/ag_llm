"""Actual ordinary HTTP routes and EVM backed by exact isolated Colibri #108."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001"))
import joint_transport as producer
from unittest.mock import patch
import unittest
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import httpx
import context_storage as core
from web_alarm.ordinary_provider import OrdinaryProviderFactory
from test_web_alarm_ordinary_application import ApplicationTests
from ultra_budget_ledger import BudgetLedger
from web_alarm.colibri_bridge_transport import BridgeFault

class JointEVM(ApplicationTests):
    fake_stream=producer.Joint.fake_stream
    fake_cancel=producer.Joint.fake_cancel
    stop=producer.Joint.stop

    def setUp(self):
        super().setUp()
        producer.Joint.setUp(self)
        self.local=self.target["target_id"]
        self.factory=OrdinaryProviderFactory.offline_application(self.api.registry,self.root,self.fixture,
                                                                 colibri_transport=self.transport)

    def test_local_evm_http_same_chat_disabled_recovery(self):
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"") # explicit TEST fixture, no silent drop
        local=self.local
        conn="local:colibri:"+local
        models={m["model_id"]:m for m in cap["models"]}
        self.assertIn(local,models);self.assertTrue(models[local]["is_local"])
        self.assertEqual(models[local]["availability"],"AVAILABLE")
        self.assertFalse(cap["real_available"])
        col=self.http(server,"GET","/ultra/connections")[1]["columns"]["local_llm"]
        self.assertEqual(col["state"],"AVAILABLE")
        self.assertIn(conn,{m["connection_id"] for m in col["connections"]})
        card=self.api.model_cards.card(local)
        self.assertEqual(card["connection_id"],conn)
        self.assertEqual(card["api"]["color"],"gray")
        self.assertTrue(card["enabled"])
        writes=[]
        original=httpx.MockTransport.handle_async_request
        async def observe(mock,request):
            if "chat/completions" in str(request.url):writes.append(json.loads(request.content))
            return await original(mock,request)
        def select(mid):
            status,result=self.http(server,"POST",base+"/model",{"model_ref":mid},write)
            self.assertEqual(status,200,result);self.assertEqual(result["model_ref"],mid)
        def send(txt,mid):
            body=self.body(txt,mid)
            status,result=self.http(server,"POST",base+"/turns",body,write)
            self.assertEqual(status,200,result);self.assertEqual(result["state"],"SUCCEEDED",result)
            return body,result
        with patch.object(httpx.MockTransport,"handle_async_request",observe):
            select("gigachat_2_pro");_,a=send("cloud first","gigachat_2_pro")
            previous=BudgetLedger(root,wid).recover().attempts
            cloud_tokens_before=self.fixture.token_calls
            select(local);b_body,b=send("local second",local)
            self.assertEqual(b["execution_mode"],"COLIBRI_OFFLINE")
            self.assertEqual(b["mode"],"ORDINARY")
            self.assertEqual(b["answer"],"Ответ")
            self.assertEqual(b["reasoning"],"Размышление 🌊")
            self.assertEqual(BudgetLedger(root,wid).recover().attempts,previous)
            self.assertEqual(self.fixture.token_calls,cloud_tokens_before)
            self.assertEqual(self.calls[0],[{"role":"user","content":"cloud first"},
              {"role":"assistant","content":a["answer"]},{"role":"user","content":"local second"}])
            # Actual shared EVM HTTP write, same stored preference.
            rev=self.api.model_cards.catalog()["settings"]["revision"]
            status,toggled=self.http(server,"POST","/ultra/model-cards/"+local+"/enabled",
                                      {"base_revision":rev,"enabled":False},write)
            self.assertEqual(status,200,toggled)
            self.assertFalse(toggled["card"]["enabled"])
            cap2=self.tokens(server)[0]
            self.assertNotIn(local,{m["model_id"] for m in cap2["models"]})
            saved=self.http(server,"GET",base+"/model",headers=read)[1]
            self.assertEqual(saved["model_ref"],local);self.assertFalse(saved["enabled"])
            self.assertEqual(self.http(server,"POST",base+"/turns",self.body("blocked",local),write)[0],403)
            status,replay=self.http(server,"POST",base+"/turns",b_body,write)
            self.assertEqual(status,200,replay);self.assertEqual(replay["turn_id"],b["turn_id"])
            self.assertEqual(len(self.calls),1)
            self.assertEqual(self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]["history_state"],"complete")
            select("gigachat_2_max");_,c=send("cloud third","gigachat_2_max")
        self.assertEqual([m["content"] for m in writes[-1]["messages"]],
            ["cloud first",a["answer"],"local second","Ответ","cloud third"])
        page=self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]
        self.assertEqual([m["text"] for m in page["messages"]],
            ["cloud first",a["answer"],"local second","Ответ","cloud third",c["answer"]])
        self.assertEqual(len(core.list_chats(root)),1)
        self.assertEqual(self.fixture.token_calls,2)
        self.assertEqual(len(BudgetLedger(root,wid).recover().attempts),2)
        # New server service, same registry storage, no local transport:
        # local preference/history and accepted result must survive.
        rev=self.api.model_cards.catalog()["settings"]["revision"]
        self.assertEqual(self.http(server,"POST","/ultra/model-cards/"+local+"/enabled",
                                    {"base_revision":rev,"enabled":True},write)[0],200)
        select(local)
        from web_alarm.server import WebAlarmApi,create_server
        api2=WebAlarmApi(self.root/"registry")
        other_factory=OrdinaryProviderFactory.offline_application(api2.registry,self.root,self.fixture)
        reopened=create_server(api2,port=0,ordinary_factory=other_factory)
        thread=threading.Thread(target=reopened.serve_forever,daemon=True);thread.start()
        self.addCleanup(thread.join,5);self.addCleanup(reopened.server_close);self.addCleanup(reopened.shutdown)
        cap3,r3,w3=self.tokens(reopened)
        self.assertNotIn(local,{m["model_id"] for m in cap3["models"]})
        saved=self.http(reopened,"GET",base+"/model",headers=r3)[1]
        self.assertEqual(saved["model_ref"],local);self.assertEqual(saved["availability"],"UNAVAILABLE")
        self.assertEqual(self.http(reopened,"GET",base+"/messages?limit=50",headers=r3)[1]["messages"],page["messages"])
        status,reply=self.http(reopened,"POST",base+"/turns",b_body,w3)
        self.assertEqual(status,200,reply);self.assertEqual(reply["turn_id"],b["turn_id"])
        self.assertEqual(self.http(reopened,"POST",base+"/turns",self.body("new local",local),w3)[0],403)
        self.assertEqual(len(self.calls),1)

    def test_availability_identity_and_system_refusal(self):
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        local=self.local
        select=lambda:self.http(server,"POST",base+"/model",{"model_ref":local},write)
        self.assertEqual(select()[0],200)
        status,result=self.http(server,"POST",base+"/turns",self.body("actual default system",local),write)
        self.assertEqual(status,409,result);self.assertEqual(result["error"]["code"],"unsupported_capability")
        # Current actual catalogue detects stale/missing instance separately.
        core.save_project_context(root,"")
        before=self.api.model_cards.card(local)["local_target"]["instance_id"]
        with patch.object(self.transport,"catalog",side_effect=BridgeFault("transport_error")):
            cap2=self.tokens(server)[0]
            m=next(m for m in cap2["models"] if m["model_id"]==local)
            self.assertEqual(m["availability"],"UNAVAILABLE")
            self.assertFalse(self.api.model_cards.card(local)["registry_enabled"])
            saved=self.http(server,"GET",base+"/model",headers=read)[1]
            self.assertEqual(saved["model_ref"],local);self.assertEqual(saved["availability"],"UNAVAILABLE")
            self.assertNotEqual(self.http(server,"POST",base+"/turns",self.body("unavailable",local),write)[0],200)
        self.assertEqual(self.calls,[])
        self.snapshots["m1"]=producer.snapshot(producer.PROFILES[0],identity="b"*32)
        card=self.api.model_cards.card(local)
        self.assertEqual(card["model_id"],local);self.assertNotEqual(card["local_target"]["instance_id"],before)
        self.assertEqual(card["local_target"]["instance_id"],"b"*32)
        self.assertEqual(self.http(server,"GET",base+"/model",headers=read)[1]["model_ref"],local)
        # Refuse global/agent selection and local profile mutations; readiness isn't green.
        self.assertEqual(card["api"]["color"],"gray")
        from web_alarm.server import ApiError
        with self.assertRaises(ApiError):
            self.api.dispatch("POST","/ultra/connections/selection",{"role":"chat","connection_id":card["connection_id"]})

if __name__=="__main__":
    suite=unittest.TestSuite(JointEVM(name) for name in
        ["test_local_evm_http_same_chat_disabled_recovery","test_availability_identity_and_system_refusal"])
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
