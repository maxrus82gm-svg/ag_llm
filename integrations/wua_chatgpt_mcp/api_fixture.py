"""Server-owned API fixture over bounded JSONL stdio; never opens production.

Only this worker imports WebAlarmApi and owns its new disposable state. This is
NOT an IPC shim installed into a running Ultra server or a production authority.
"""
from pathlib import Path
import hashlib,hmac,json,sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def reply(value):
    raw=canonical(value);require(len(raw)<=MAX_RESPONSE,'OUTPUT_LIMIT');sys.stdout.buffer.write(raw+b'\n');sys.stdout.buffer.flush()
def run(path):
    b=bootstrap(path);root=owned_path(b['root'],False);require(not root.exists(),'NEW_ROOT_REQUIRED');root.mkdir()
    install_fixture_guard(root)
    sys.path.insert(0,str(REPO))
    from web_alarm.server import WebAlarmApi
    project=root/'workspace';project.mkdir();api=WebAlarmApi(root/'state')
    code,_=api.dispatch('POST','/workspaces',{'workspace_id':'synthetic_integration_ws','display_name':'Disposable integration fixture','workspace_root':str(project)})
    require(code==201,'SETUP_FAILED')
    code,_=api.dispatch('POST','/tasks',{'workspace_id':'synthetic_integration_ws','task_id':FIXTURE,'title':'Synthetic MCP integration','raw_task':'Synthetic read-only scope only','goal':'synthetic nonce: '+b['nonce']})
    require(code==201,'SETUP_FAILED');baseline=tree_hash(root);reads=0;seen=set();audit=[]
    reply({'ready':True,'protocol':'wua-api-jsonl-v1','session_id':b['session_id'],'baseline_sha256':baseline})
    while True:
        raw=sys.stdin.buffer.readline(MAX_REQUEST+2)
        if not raw:return
        rid=None
        try:
            require(raw.endswith(b'\n'),'INPUT_FRAME');q=parse(raw);exact(q,['body','mac']);body=q['body'];exact(body,['schema','session_id','request_id','operation','task_id'])
            rid=request_id(body['request_id']);require(type(body['schema']) is int and body['schema']==1 and body['session_id']==b['session_id'],'SESSION_DENIED')
            require(type(q['mac']) is str and hmac.compare_digest(q['mac'],mac(body,b['channel_key'])),'AUTH_DENIED')
            require(body['task_id']==FIXTURE and body['operation'] in ['status','context'],'SCOPE_DENIED')
            require(rid not in seen and len(seen)<64,'REPLAY_OR_QUOTA');seen.add(rid)
            route='/status' if body['operation']=='status' else '/tasks/'+FIXTURE+'/context'
            code,data=api.dispatch('GET',route);reads+=1;require(code==200,'API_READ_FAILED')
            if body['operation']=='status':value={k:data[k] for k in ['status','service','api_version','mode']}
            else:
                value={'TASK':{k:data['TASK'][k] for k in ['task_id','title','status']},'GOAL':data['GOAL'],'CURRENT_STATUS':data['CURRENT_STATUS'],'NEXT_SAFE_ACTION':data['NEXT_SAFE_ACTION'],'AUTHORITY_SOURCE':data['AUTHORITY_SOURCE'],'CHECKPOINT':{k:data['CHECKPOINT'][k] for k in ['status','authoritative']}}
            current=tree_hash(root);require(current==baseline,'READ_MUTATED_STORAGE');audit.append({'request_id':rid,'operation':body['operation'],'result':'OK'})
            reply({'ok':True,'request_id':rid,'session_id':b['session_id'],'nonce':b['nonce'],'api_reads':reads,'api_route':route,'value':value,'value_sha256':digest(value),'baseline_sha256':baseline,'current_sha256':current,'audit':audit[-8:]})
        except (Denied,KeyError,ValueError,TypeError):
            reply({'ok':False,'request_id':rid,'code':'API_REQUEST_DENIED'})
            if len(raw)>MAX_REQUEST or not raw.endswith(b'\n'):return
if __name__=='__main__':
    try:
        require(len(sys.argv)==2,'FIXTURE_BOOTSTRAP_REQUIRED');run(sys.argv[1])
    except BaseException as exc:
        sys.stderr.write('API_FIXTURE_STOPPED:'+type(exc).__name__+(':'+str(exc) if isinstance(exc,Denied) else '')+'\n');sys.exit(20)
