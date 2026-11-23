"""Exact producer #108, WUA #660 ordinary HTTP/EVM synthetic readiness (M1-02).
Includes bounded stream performance observation; no actual Manager operation.
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-EVM-20261122-001"))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001"))
import joint_evm
from joint_transport import snapshot, PROFILES
from web_alarm.colibri_bridge_transport import BridgeFault
from web_alarm.ultra_chat import UltraChatError
from web_alarm.server import ApiError
import context_storage as core
import run_store as runs
from time import perf_counter
import unittest
import json

class Readiness(joint_evm.JointEVM):
    def test_two_managers_catalog_identity_and_independent_admission(self):
        """M1-02 subset: one Client Bridge, two fake Managers, *serial* requests."""
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"")  # only the disposable fixture
        t1=self.target
        t2=next(t for t in self.transport.catalog()["targets"] if t["manager_id"]=="m2")
        self.assertNotEqual(t1["target_id"],t2["target_id"])
        self.assertEqual(t1["instance_id"],t2["instance_id"]) # instance is NOT the target key
        local_caps={x["model_id"]:x for x in cap["models"] if x.get("is_local")}
        self.assertEqual(set(local_caps),{t1["target_id"],t2["target_id"]})
        for t in (t1,t2):
            self.assertEqual((local_caps[t["target_id"]]["manager_name"],
                              local_caps[t["target_id"]]["slot_id"]),
                             (t["manager_name"],t["slot_id"]))
        view=self.http(server,"GET","/ultra/connections")[1]["columns"]["local_llm"]
        self.assertEqual(view["state"],"AVAILABLE")
        self.assertEqual({x["model_id"] for x in view["connections"]},{t1["target_id"],t2["target_id"]})
        self.assertEqual({x["manager_name"] for x in view["connections"]},
                         {t1["manager_name"],t2["manager_name"]})
        self.assertTrue(all(x["selectable"] for x in view["connections"]))
        for t in (t1,t2):
            a=self.api.model_cards.card(t["target_id"])
            self.assertEqual(a["api"]["color"],"gray")  # discovery never == a LIVE success
        # No alternate model is chosen when m1 is BUSY; m2 remains READY.
        self.snapshots["m1"]=snapshot(PROFILES[0],ready="busy")
        view=self.http(server,"GET","/ultra/connections")[1]["columns"]["local_llm"]["connections"]
        state={x["model_id"]:(x["availability"],x["selectable"]) for x in view}
        self.assertEqual(state[t1["target_id"]],("BUSY",False))
        self.assertEqual(state[t2["target_id"]],("READY",True))
        self.assertNotEqual(self.http(server,"POST",base+"/model",
                {"model_ref":t1["target_id"]},write)[0],200)
        self.assertEqual(self.http(server,"POST",base+"/model",
                {"model_ref":t2["target_id"]},write)[0],200)
        visited=[]
        def attributed(profile,slot,model,messages,**kwargs):
            visited.append(profile["manager_id"])
            yield from self.fake_stream(profile,slot,model,messages,**kwargs)
        self.manager_stream=attributed
        b=self.body("Manager2 request",t2["target_id"])
        status,result=self.http(server,"POST",base+"/turns",b,write)
        self.assertEqual(status,200,result)
        self.assertEqual(result["state"],"SUCCEEDED")
        self.assertEqual(visited,["m2"])
        self.assertEqual(result["instance_id"],t2["instance_id"])
        self.assertEqual(self.http(server,"GET",base+"/model",headers=read)[1]["model_ref"],t2["target_id"])
        # Manager2 becomes unavailable: existing selection/history intact.
        self.snapshots["m2"]=snapshot(PROFILES[1],ready="busy")
        self.assertEqual(self.http(server,"GET",base+"/model",headers=read)[1]["model_ref"],t2["target_id"])
        self.assertEqual(self.http(server,"GET",base+"/model",headers=read)[1]["availability"],"UNAVAILABLE")
        self.assertNotEqual(self.http(server,"POST",base+"/turns",self.body("no fallback",t2["target_id"]),write)[0],200)
        self.assertEqual(visited,["m2"])  # neither manager called again
        page=self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]
        self.assertEqual([m["text"] for m in page["messages"]],["Manager2 request","Ответ"])
        # m1 comes back with a fresh instance. Target id remains stable.
        self.snapshots["m1"]=snapshot(PROFILES[0],identity="b"*32)
        cat=self.transport.catalog()["targets"]
        new=next(t for t in cat if t["manager_id"]=="m1")
        self.assertEqual(new["target_id"],t1["target_id"])
        self.assertEqual(new["instance_id"],"b"*32)
        self.assertNotEqual(new["instance_id"],t1["instance_id"])
        self.assertEqual(self.http(server,"GET",base+"/model",headers=read)[1]["model_ref"],t2["target_id"])
        status,selected=self.http(server,"POST",base+"/model",{"model_ref":t1["target_id"]},write)
        self.assertEqual(status,200,selected)
        status,r=self.http(server,"POST",base+"/turns",self.body("Now manager1",t1["target_id"]),write)
        self.assertEqual(status,200,r)
        self.assertEqual((r["instance_id"],visited),("b"*32,["m2","m1"]))
        self.assertEqual(self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]["history_state"],"complete")
        self.assertEqual(len(core.list_chats(root)),1)
        # EVM target toggle is scoped to its target ID, not all managers.
        rev=self.api.model_cards.catalog()["settings"]["revision"]
        status,off=self.http(server,"POST","/ultra/model-cards/"+t1["target_id"]+"/enabled",
                        {"base_revision":rev,"enabled":False},write)
        self.assertEqual(status,200)
        self.assertFalse(off["card"]["enabled"])
        self.assertTrue(self.api.model_cards.is_enabled(t2["target_id"]))
        self.assertEqual(len(visited),2)

    def test_bounded_stream_journal_performance_and_durable_replay(self):
        """Observation only: report physical journal cost, no artificial pass latency threshold."""
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"")
        self.assertEqual(self.http(server,"POST",base+"/model",
                {"model_ref":self.local},write)[0],200)
        timings={}
        for size in (8,24,48):
            expected="fragment-"*size
            def stream(profile,slot,model,messages,**kwargs):
                for item in self.fake_stream(profile,slot,model,messages,**kwargs):
                    if item["type"]=="delta":
                        for j in range(size):
                            yield {"type":"delta","text":"fragment-"}
                    else:yield item
            self.manager_stream=stream
            b=self.body("stream size "+str(size),self.local)
            start=perf_counter()
            # Avoid tiny 12-second test HTTP client's unrelated network timeout.
            result=server.web_alarm_ultra_chat.submit_turn(ws,cid,b)
            elapsed=round(perf_counter()-start,3)
            self.assertEqual(result["state"],"SUCCEEDED")
            self.assertEqual(result["answer"],expected)
            self.assertEqual(result["reasoning"],"Размышление 🌊")
            from web_alarm.turn_service import TurnService
            reader=TurnService(test_roots=[root])
            turn=reader._load(root,wid,cid,result["turn_id"])
            records=runs.load_stream_records(root,turn["run_id"],"SERVER")
            from web_alarm.colibri_turn import expand_packets
            packets=[e for e in expand_packets(records) if e["event"]=="turn_bridge_packet"]
            self.assertEqual(len(packets),size+6)
            batches=sum(e["event"]=="turn_bridge_batch" for e in records)
            self.assertGreater(batches,0)
            self.assertLess(batches,size+6)
            self.assertEqual(reader.lookup(root,wid,cid,b["idempotency_key"])["answer"],expected)
            self.assertEqual(len(self.calls),len(timings)+1)
            replay=server.web_alarm_ultra_chat.submit_turn(ws,cid,b)
            self.assertEqual(replay["turn_id"],result["turn_id"])
            self.assertEqual(len(self.calls),len(timings)+1)
            timings[str(size)]=dict(seconds=elapsed,journal_records=len(records),
                                    original_sse_packets=len(packets),batch_records=batches)
        self.assertEqual(len(core.list_chats(root)),1)
        print("LONG_STREAM_OBSERVATION="+json.dumps(timings),flush=True)

    def test_packet_batch_integrity_and_legacy_readback(self):
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"")
        self.assertEqual(self.http(server,"POST",base+"/model",
                {"model_ref":self.local},write)[0],200)
        def many(profile,slot,model,messages,**kwargs):
            for item in self.fake_stream(profile,slot,model,messages,**kwargs):
                if item["type"]=="delta":
                    for i in range(20): yield {"type":"delta","text":"x"}
                else:yield item
        self.manager_stream=many
        result=server.web_alarm_ultra_chat.submit_turn(ws,cid,self.body("batch verify",self.local))
        self.assertEqual(result["state"],"SUCCEEDED")
        from web_alarm.colibri_turn import evidence,expand_packets,MAX_BATCH_PACKETS
        from web_alarm.colibri_bridge_transport import BridgeFault
        from web_alarm.turn_service import TurnService
        reader=TurnService(test_roots=[root])
        turn=reader._load(root,wid,cid,result["turn_id"])
        original=runs.load_stream_records(root,turn["run_id"],"SERVER")
        self.assertTrue(any(r["event"]=="turn_bridge_batch" for r in original))
        projection=evidence(turn,original)
        self.assertEqual(projection["answer"],"x"*20)
        # Prior #659 per-packet format remains valid and semantically identical.
        legacy=list(expand_packets(original))
        self.assertTrue(all(rec["event"]!="turn_bridge_batch" for rec in legacy))
        self.assertEqual(evidence(turn,legacy),projection)
        import copy
        idx=next(i for i,rec in enumerate(original) if rec["event"]=="turn_bridge_batch")
        for defect in ("empty","too_many","missing","duplicate_sequence","bad_request"):
            bad=copy.deepcopy(original)
            p=bad[idx]["payload"]
            if defect=="empty":p["packets"]=[]
            if defect=="too_many":p["packets"] *= MAX_BATCH_PACKETS+1
            if defect=="missing":p["unknown"]=True
            if defect=="duplicate_sequence":
                e=p["packets"][0]
                p["packets"].insert(0,copy.deepcopy(e))
            if defect=="bad_request":
                p["packets"][0]["request_id"]="f"*32
            with self.subTest(defect=defect),self.assertRaises((BridgeFault,ValueError)):
                evidence(turn,bad)
        self.assertEqual(reader.lookup(root,wid,cid,turn["idempotency_key"])["answer"],"x"*20)
        self.assertEqual(len(self.calls),1)

    def test_truncated_stream_flushes_buffered_partial_without_reexecution(self):
        from joint_transport import ChatClientError
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"")
        self.assertEqual(self.http(server,"POST",base+"/model",
                {"model_ref":self.local},write)[0],200)
        def truncated(profile,slot,model,messages,**kwargs):
            for item in self.fake_stream(profile,slot,model,messages,**kwargs):
                if item["type"]=="delta":
                    for i in range(11):yield {"type":"delta","text":"p"}
                elif item["type"]=="done":
                    raise ChatClientError("stream_truncated",502)
                else:yield item
        self.manager_stream=truncated
        body=self.body("truncated pending batch",self.local)
        result=server.web_alarm_ultra_chat.submit_turn(ws,cid,body)
        self.assertEqual(result["state"],"UNKNOWN")
        self.assertIsNone(result["answer"])
        self.assertEqual(result["partial_answer"],"p"*11)
        self.assertEqual(result["reasoning"],"Размышление 🌊")
        from web_alarm.turn_service import TurnService
        from web_alarm.colibri_turn import expand_packets
        reader=TurnService(test_roots=[root])
        turn=reader._load(root,wid,cid,result["turn_id"])
        records=runs.load_stream_records(root,turn["run_id"],"SERVER")
        self.assertEqual(sum(r["event"]=="turn_bridge_batch" for r in records)>=2,True)
        self.assertEqual(sum(r["event"]=="turn_bridge_packet" for r in expand_packets(records)),16)
        self.assertEqual([m["text"] for m in
            self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]["messages"]],
                         ["truncated pending batch"])
        self.assertEqual(len(self.calls),1)
        replay=server.web_alarm_ultra_chat.submit_turn(ws,cid,body)
        self.assertEqual(replay["state"],"UNKNOWN")
        self.assertEqual(replay["partial_answer"],"p"*11)
        self.assertEqual(len(self.calls),1)

if __name__=="__main__":
    suite=unittest.TestSuite(Readiness(name) for name in (
        "test_two_managers_catalog_identity_and_independent_admission",
        "test_bounded_stream_journal_performance_and_durable_replay",
        "test_packet_batch_integrity_and_legacy_readback",
        "test_truncated_stream_flushes_buffered_partial_without_reexecution"))
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
