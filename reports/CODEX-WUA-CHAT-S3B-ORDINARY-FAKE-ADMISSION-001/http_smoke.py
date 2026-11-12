"""One guarded loopback Web → byte fake → ledger → RAW/usage/reopen scenario."""
from pathlib import Path
import hashlib, json, os, runpy, tempfile, threading, sys
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]; PKG=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
stage=sys.argv[1] if len(sys.argv)>1 else 'http_smoke'
assert stage.isidentifier()
prefix=PKG/'evidence'/stage
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT),ORDINARY_GUARD_NETWORK='loopback',
                  ORDINARY_GUARD_LOG=str(prefix.with_suffix('.guard.jsonl')))
runpy.run_path(str(ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py'))
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ultra_chat import OrdinaryCoreChatService
from web_alarm.ordinary_chat_test_adapter import _FixtureTransport
from test_web_alarm_ordinary_core_bridge import CoreBridgeHttpTests, reply
import context_storage as core
import run_store as runs
from ultra_budget_ledger import BudgetLedger

assert not prefix.with_suffix('.result.json').exists()
trace=[]
with tempfile.TemporaryDirectory(prefix='h32_web_') as directory:
    root=Path(directory).resolve();api=WebAlarmApi(root/'registry')
    service=OrdinaryCoreChatService(api.registry,root)
    server=create_server(api,port=0,offline_chat=service)
    helper=CoreBridgeHttpTests(); worker=threading.Thread(target=server.serve_forever);worker.start()
    def http(method,path,body=None,headers=None):
        return helper.http(server,method,path,body,headers)
    async def fake(sender,wire,**kwargs):
        proofs=[]
        for project in service.projects.iterdir():
            identity=core.read_workspace_identity_bounded(project)
            if identity['status']!='ok':continue
            ledger=BudgetLedger(project,identity['workspace_id'])
            for attempt in ledger.recover().attempts:
                receipt,envelope=ledger.reservation(attempt.attempt_id)
                if receipt.record.state=='SENT' and envelope['wire_utf8'].encode()==wire:
                    turn=runs.load_run_summary(project,envelope['binding']['turn_id'],envelope['binding']['chat_id'])['turn']
                    proofs.append(dict(binding=envelope['binding'],workspace_id=identity['workspace_id'],
                        turn_binding_sha256=turn['binding_sha256'],policy_sha256=turn['ordinary_admission']['policy_sha256'],
                        endpoint=turn['ordinary_admission']['endpoint'],provider_model_id=json.loads(wire)['model']))
        assert len(proofs)==1
        trace.append(dict(wire_sha256=hashlib.sha256(wire).hexdigest(),wire_bytes=len(wire),
                          **proofs[0],ledger_state_at_send='SENT'))
        return reply({'prompt_tokens':3,'completion_tokens':4,'total_tokens':7,
                      'completion_tokens_details':{'reasoning_tokens':2}})
    try:
        cap,read,write=helper.tokens(server);assert cap['core_bridge'] and not cap['real_available']
        bases=[]
        for title in ('Web A','Web B'):
            code,ws=http('POST','/ultra/chat/workspaces',{'title':title},write);assert code==201
            for index in range(2):
                cid='chat_'+uuid4().hex
                base=f'/ultra/chat/workspaces/{ws["wa_workspace_id"]}/chats'
                code,_=http('POST',base,{'chat_id':cid,'initialize_workspace':True},write);assert code==201
                bases.append(base+'/'+cid)
        with patch.object(_FixtureTransport,'send_bytes',fake):
            results=[]
            for index in (0,1,0,2):
                body={'idempotency_key':uuid4().hex,'model_ref':'gigachat_2_pro','text':'HTTP synthetic '+str(len(results))}
                code,result=http('POST',bases[index]+'/turns',body,write)
                assert code==200 and result['state']=='SUCCEEDED'
                assert http('POST',bases[index]+'/turns',body,write)==(200,result)
                assert http('GET',bases[index]+'/turns/latest',headers=read)[1]['turn']==result
                results.append(result)
            assert len(trace)==4
            bad={**body,'config_ref':'REAL'}
            assert http('POST',bases[2]+'/turns',bad,write)[0]==400
            assert len(trace)==4
        summaries=[]
        for base,expected in zip(bases,(2,1,1,0)):
            code,page=http('GET',base+'/messages',headers=read);assert code==200
            assert len(page['messages'])==expected*2
            assert page['usage_summary']['attempts']==expected
            assert page['usage_summary']['known']['total_tokens']==expected*7
            assert page['usage_summary']['known']['reasoning_tokens']==expected*2
            summaries.append(dict(attempts=expected,total=expected*7,reasoning=expected*2))
        assert http('GET','/')[0]==200
    finally:
        server.shutdown();server.server_close();worker.join(5)
    artifact=dict(status='PASS',workspaces=2,chats=4,physical_fake_calls=4,
                  replays_added_calls=0,real_body_status=400,per_chat=summaries,trace=trace,
                  browser_visual='NOT RUN',external_requests=0)
    prefix.with_suffix('.result.json').write_text(json.dumps(artifact,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in artifact.items() if k!='trace'}))
