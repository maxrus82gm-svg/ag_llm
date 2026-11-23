"""Disposable #108 + ordinary application server for the actual Chrome smoke."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"CHATGPT-WUA-COLIBRI-MVP1-EVM-20261122-001"))
from joint_evm import JointEVM,core
f=JointEVM("test_local_evm_http_same_chat_disabled_recovery")
try:
 f.setUp()
 ws,cid,server,cap,read,write,base,root,wid=f.application()
 core.save_project_context(root,"")
 def slow(*a,**kw):
    for e in f.fake_stream(*a,**kw):
       if e["type"] in {"delta","done"}:time.sleep(2.2)
       yield e
 f.manager_stream=slow
 url=f"http://127.0.0.1:{server.server_address[1]}/#chat"
 print("ORDINARY_TEST_READY "+json.dumps(dict(url=url,local=f.local,workspace=ws,chat=cid)),flush=True)
 sys.stdin.readline()
finally:
 f.doCleanups()
