"""Exact Colibri #108 source + WUA consumer HTTP boundary, no actual engines.
Run from WUA repository with explicitly extracted isolated Colibri source path.
"""
import argparse
from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
import sys

# invoked from repo root with Python -m or explicit script path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from web_alarm.colibri_bridge_transport import OfflineColibriTransport,BridgeFault

p=argparse.ArgumentParser()
p.add_argument("--producer-source",required=True)
args,remaining=p.parse_known_args()
sys.argv=[sys.argv[0],*remaining]
producer=Path(args.producer_source).resolve()
assert tempfile.gettempdir().casefold() in str(producer).casefold()
sys.path.insert(0,str(producer/"Client_Ultra_LLM"))
from bridge_runtime import ClientBridge
from chat_client import ChatClientError
from test_client_bridge import snapshot, PROFILES, POLICY
import web_client

class Joint(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory(prefix="wua-bridge-profile-")
    self.addCleanup(self.tmp.cleanup)
    self.folder=Path(self.tmp.name).resolve()
    self.calls=[];self.cancels=[]
    self.snapshots={p["manager_id"]:snapshot(p) for p in PROFILES}
    self.manager_stream=self.fake_stream
    def stream(*a,**kw):return self.manager_stream(*a,**kw)
    self.bridge=ClientBridge(self.folder,snapshot=lambda p:deepcopy(self.snapshots[p["manager_id"]]),
        stream=stream,cancel=self.fake_cancel,profiles=lambda:PROFILES)
    holder={"port":0}
    self.server=ThreadingHTTPServer(("127.0.0.1",0),web_client.make_handler(self.folder,lambda:holder["port"],"csrf",bridge=self.bridge))
    holder["port"]=self.server.server_address[1];self.server.daemon_threads=True
    self.bridge.publish(holder["port"])
    self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    self.addCleanup(self.stop)
    self.transport=OfflineColibriTransport(self.folder,expected_bridge_id=self.bridge.bridge_id)
    self.target=next(t for t in self.transport.catalog()["targets"] if t["manager_id"]=="m1")
 def stop(self):
    self.server.shutdown();self.server.server_close();self.thread.join(2);self.bridge.unpublish()
 def fake_cancel(self,profile,slot,request):
    self.cancels.append(request);return True
 def fake_stream(self,profile,slot,model,messages,**kw):
    self.calls.append(deepcopy(messages))
    yield {"type":"meta","manager_id":profile["manager_id"],"slot_id":slot,"model_id":model,
           "instance_id":kw["instance_id"],"execution_mode":"cuda","transport_policy":POLICY,
           "engine_limits":{"context_tokens":65536}}
    yield {"type":"reasoning","text":"Размышление 🌊"}
    yield {"type":"delta","text":"Ответ"}
    yield {"type":"done","usage":{"prompt_tokens":0,"completion_tokens":23},"finish_reason":"stop"}
 def prepare(self,**kw):
    request=dict(request_id=uuid.uuid4().hex,target_id=self.target["target_id"],
        messages=[{"role":"user","content":"старый облачный вопрос"},{"role":"assistant","content":"старый облачный ответ"},
                  {"role":"user","content":"локальный вопрос"}],conversation_id="chat_same_id",turn_id="turn_existing_id",
        enabled_targets={self.target["target_id"]})
    request.update(kw);return self.transport.prepare(**request)
 def test_actual_http_five_operations_split_events_usage_duplicate(self):
    f=self.prepare();seen=[]
    result=self.transport.run(f,on_event=seen.append)
    self.assertEqual(result.state,"SUCCEEDED");self.assertTrue(result.complete)
    self.assertEqual(result.answer,"Ответ");self.assertEqual(result.reasoning,"Размышление 🌊")
    self.assertEqual([x["type"] for x in seen],["meta","status","reasoning","delta","usage","telemetry","done"])
    self.assertEqual(self.calls,[json.loads(f.wire)["messages"]])
    self.assertEqual(result.usage["source"],"provider_and_derived_total")
    self.assertEqual(result.usage["status"],"partial")
    self.assertEqual(result.usage["prompt_tokens"],0);self.assertIsNone(result.usage["reasoning_tokens"])
    self.assertEqual(result.usage["total_tokens"],23);self.assertIsNotNone(result.ttft_ms)
    self.assertEqual(self.transport.status(f)["state"],"SUCCEEDED")
    self.assertFalse(self.transport.cancel(f)["stop_confirmed"])
    repeat=self.transport.run(f)
    self.assertEqual(repeat.error_code,"request_already_attempted")
    self.assertEqual(repeat.state,"UNKNOWN");self.assertFalse(repeat.complete)
    self.assertEqual(repeat.remote_state["state"],"SUCCEEDED")
    self.assertEqual(len(self.calls),1)
 def test_refusal_disabled_system_stale_and_bad_token(self):
    for kw in ({"enabled_targets":set()},{"messages":[{"role":"system","content":"Do not drop"},{"role":"user","content":"a"}]},
               {"expected_instance_id":"b"*32},{"options":{"thinking":"on"}}):
       with self.subTest(kw=kw),self.assertRaises(BridgeFault):self.prepare(**kw)
    self.assertEqual(self.calls,[])
    f=self.prepare()
    self.snapshots["m1"]=snapshot(PROFILES[0],identity="b"*32)
    why=self.transport.run(f)
    self.assertEqual((why.state,why.error_code),("REJECTED","stale_instance"))
    self.assertEqual(self.calls,[])
    token=self.folder/"bridge-wua.token";old=token.read_text(encoding="ascii")
    # Producer reads its own token file, so simulate a wrong token at the WUA
    # HTTP boundary without changing the producer credential.
    from unittest.mock import patch
    with patch.object(self.transport,"_headers",return_value={"Authorization":"Bearer "+"X"*64,"Content-Type":"application/json"}):
       with self.assertRaises(BridgeFault) as err:self.transport.catalog()
       self.assertEqual(err.exception.code,"unauthorized")
    self.assertEqual(token.read_text(encoding="ascii"),old)
 def test_partial_unknown_never_reissued(self):
    def truncated(profile,slot,model,messages,**kw):
       for e in self.fake_stream(profile,slot,model,messages,**kw):
          if e["type"]=="done":
             raise ChatClientError("stream_truncated",502)
          yield e
    self.manager_stream=truncated;f=self.prepare()
    result=self.transport.run(f)
    self.assertEqual(result.state,"UNKNOWN");self.assertFalse(result.complete)
    self.assertEqual(result.answer,"Ответ");self.assertEqual(result.reasoning,"Размышление 🌊")
    self.assertEqual(self.transport.status(f)["state"],"UNKNOWN")
    again=self.transport.run(f)
    self.assertEqual(again.error_code,"request_already_attempted");self.assertEqual(len(self.calls),1)
 def test_active_cancel_ack_not_stop_and_completion_wins(self):
    ready=threading.Event();release=threading.Event();done=[]
    def blocking(profile,slot,model,messages,**kw):
       for e in self.fake_stream(profile,slot,model,messages,**kw):
          if e["type"]=="reasoning":
             ready.set()
             if not release.wait(5):raise RuntimeError("test barrier timed out")
          yield e
    self.manager_stream=blocking;f=self.prepare()
    t=threading.Thread(target=lambda:done.append(self.transport.run(f)),daemon=True)
    t.start()
    try:
       self.assertTrue(ready.wait(5))
       status=self.transport.cancel(f);self.assertTrue(status["cancel_accepted"])
       self.assertFalse(status["stop_confirmed"]);self.assertEqual(status["state"],"CANCEL_REQUESTED")
       self.assertEqual(self.transport.status(f)["state"],"CANCEL_REQUESTED")
    finally:
       release.set();t.join(10)
    self.assertEqual(len(done),1);self.assertEqual(done[0].state,"SUCCEEDED")
    self.assertEqual(len(self.calls),1)
 def test_discovery_launch_drift_refused(self):
    f=self.prepare()
    self.bridge.launch_id=uuid.uuid4().hex
    self.bridge.publish(self.server.server_address[1])
    with self.assertRaises(BridgeFault) as err:self.transport.run(f)
    self.assertEqual(err.exception.code,"identity_mismatch");self.assertEqual(self.calls,[])
    # New bound transport may query original durable ID, but never resend old frozen wire.
    renewed=OfflineColibriTransport(self.folder,expected_bridge_id=self.bridge.bridge_id)
    with self.assertRaises(BridgeFault):renewed.run(f)

 def test_corrupt_eof_and_terminal_from_actual_packets(self):
    # First capture actual valid producer packets; then independently mutate
    # the received wire at the WUA HTTP boundary. No second Manager invocation.
    from unittest.mock import patch
    import httpx
    from web_alarm.colibri_bridge_transport import canonical
    f=self.prepare();events=[];success=self.transport.run(f,on_event=events.append)
    self.assertTrue(success.complete)
    health=self.transport._health();remote=self.transport.status(f)
    def frame(e):
       return b'event: '+e["type"].encode()+b'\nid: '+str(e["sequence"]).encode()+b'\ndata: '+canonical(e)+b'\n\n'
    malformed=[
      (events[:-1],"stream_truncated"),
      ([{**events[0],"instance_id":"b"*32},*events[1:]],"identity_mismatch"),
      ([events[0],{**events[1],"sequence":3},*events[2:]],"protocol_error"),
      ([*events,{**events[2],"sequence":len(events)}],"protocol_error"),
    ]
    for packets,expected in malformed:
       posts=[];seen=[]
       def handler(req):
          if req.url.path.endswith("/health"):return httpx.Response(200,headers={"content-type":"application/json"},stream=Chunks(canonical(health)))
          if "/requests/" in req.url.path:return httpx.Response(200,headers={"content-type":"application/json"},stream=Chunks(canonical(remote)))
          posts.append(str(req.url.path))
          return httpx.Response(200,headers={"content-type":"text/event-stream"},stream=Chunks(b"".join(frame(e) for e in packets)))
       class Chunks(httpx.SyncByteStream):
          def __init__(self,b):self.b=b
          def __iter__(self):
             # small fragments cut UTF-8 codepoints and line boundaries.
             for i in range(0,len(self.b),7):yield self.b[i:i+7]
       with self.subTest(expected=expected),patch.object(self.transport,"_client",side_effect=lambda _:httpx.Client(transport=httpx.MockTransport(handler),follow_redirects=False,trust_env=False)):
          result=self.transport.run(f,on_event=seen.append)
          self.assertEqual((result.state,result.complete,result.error_code),("UNKNOWN",False,expected))
          self.assertEqual(result.remote_state["state"],"SUCCEEDED")
          self.assertEqual(posts,["/bridge/v1/chat/stream"])
          self.assertFalse(any(x["type"]=="done" for x in seen))
          if expected=="stream_truncated":self.assertEqual(result.answer,"Ответ")
    self.assertEqual(len(self.calls),1)
 def test_restart_status_without_redispatch(self):
    f=self.prepare();self.assertTrue(self.transport.run(f).complete)
    self.bridge.launch_id=uuid.uuid4().hex
    self.bridge.publish(self.server.server_address[1])
    renewed=OfflineColibriTransport(self.folder,expected_bridge_id=self.bridge.bridge_id)
    self.assertEqual(renewed.status(f)["state"],"SUCCEEDED")
    with self.assertRaises(BridgeFault):renewed.run(f)
    self.assertEqual(len(self.calls),1)

if __name__=="__main__":unittest.main(verbosity=2)
