"""Independent official MCP SDK client; only own staged API fixture state."""
import asyncio,hashlib,json,os,secrets,sys,uuid
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
PACKAGE=Path(__file__).resolve().parents[1];REPO=PACKAGE.parents[1]
REPORT=REPO/'reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001'
def h(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode('ascii')).hexdigest()
def tree(root):return h({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()})
class OwnProcessWait:
    def __init__(self,pid):
        assert os.name=='nt','Windows process lifecycle gate NOT RUN on this platform'
        import ctypes
        self.k=ctypes.WinDLL('kernel32',use_last_error=True);self.k.OpenProcess.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_uint];self.k.OpenProcess.restype=ctypes.c_void_p;self.k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];self.k.WaitForSingleObject.restype=ctypes.c_uint;self.k.CloseHandle.argtypes=[ctypes.c_void_p]
        self.handle=self.k.OpenProcess(0x100000,False,pid);assert self.handle,'Own fixture process observation unavailable'
    def stopped(self):return self.k.WaitForSingleObject(self.handle,2000)==0
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None
async def exercise(run):
    checks=[];sessions=[];wire=[]
    def check(name,ok):
        checks.append({'name':name,'status':'PASS' if ok else 'FAIL'})
        if not ok:raise AssertionError(name)
    for restart in range(2):
        owned=run/('session'+str(restart));owned.mkdir();boot=owned/'bootstrap.json';nonce=secrets.token_hex(32);session=str(uuid.uuid4());key=secrets.token_hex(32)
        data={'schema':1,'mode':'synthetic_fixture_only','fixture_id':'synthetic_wua_integration_001','root':str(owned/'owned-api-state'),'session_id':session,'nonce':nonce,'channel_key':key,'client_role':'wua-client'}
        boot.write_text(json.dumps(data),encoding='utf-8');last=None;own_process=None
        env={k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ};(owned/'temp').mkdir();env['TMP']=env['TEMP']=str(owned/'temp')
        try:
            with (owned/'stderr.txt').open('w+',encoding='utf-8') as err:
                params=StdioServerParameters(command=sys.executable,args=['-I','-X','utf8','-B',str(PACKAGE/'server.py'),str(boot)],env=env,cwd=str(PACKAGE))
                async with stdio_client(params,errlog=err) as (read,write):
                    async with ClientSession(read,write,read_timeout_seconds=5) as sdk:
                        init=await sdk.initialize();check(f'{restart}:SDK_initialize',init.server_info.name=='WUA ChatGPT Integration Synthetic');wire.append({'initialize':init.model_dump(mode='json',by_alias=True,exclude_none=True)})
                        tools=await sdk.list_tools();check(f'{restart}:exact_tools',set(t.name for t in tools.tools)=={'ping','list_capabilities','read_synthetic_context','get_status'})
                        check(f'{restart}:readonly_annotations',all(t.annotations.read_only_hint and not t.annotations.destructive_hint and t.input_schema['additionalProperties'] is False for t in tools.tools))
                        async def call(name,args=None):
                            rid=str(uuid.uuid4());q={'request_id':rid};q.update(args or {});r=await sdk.call_tool(name,q,read_timeout_seconds=5)
                            wire.append({'tool':name,'is_error':r.is_error,'request_id':rid,'structured_response':r.structured_content})
                            return r
                        for tool in ['ping','list_capabilities','get_status','read_synthetic_context']:
                            r=await call(tool,{'task_id':'synthetic_wua_integration_001'} if tool=='read_synthetic_context' else None)
                            check(f'{restart}:{tool}:success',not r.is_error);v=r.structured_content
                            check(f'{restart}:{tool}:API_provenance',v['proof']['session_id']==session and v['proof']['nonce']==nonce and v['proof']['api_reads']>0)
                            if own_process is None:own_process=OwnProcessWait(v['proof']['mcp_process_id'])
                            check(f'{restart}:{tool}:hash',v['content_sha256']==h(v['value']))
                            check(f'{restart}:{tool}:actual_storage_unchanged',v['proof']['baseline_sha256']==v['proof']['current_sha256']==tree(owned/'owned-api-state'))
                            if tool=='read_synthetic_context':
                                check(f'{restart}:server_owned_context',v['value']['TASK']['task_id']=='synthetic_wua_integration_001' and nonce in v['value']['GOAL'] and v['value']['AUTHORITY_SOURCE']=='lifecycle')
                                last=v['content_sha256']
                        repeated=await call('read_synthetic_context',{'task_id':'synthetic_wua_integration_001'});check(f'{restart}:repeat_content',repeated.structured_content['content_sha256']==last)
                        for n,q in [('foreign',{'task_id':'other_task'}),('traversal',{'task_id':'../../.ultra'}),('wrong_type',{'task_id':True}),('extra',{'task_id':'synthetic_wua_integration_001','command':'write'})]:
                            r=await call('read_synthetic_context',q);check(f'{restart}:deny_{n}',r.is_error)
                        r=await call('execute');check(f'{restart}:unknown_tool_denied',r.is_error)
                        r=await sdk.call_tool('ping',{'request_id':7});check(f'{restart}:strict_request_type',r.is_error)
                        r=await call('get_status');check(f'{restart}:errors_do_not_leak_private_paths',not r.is_error and 'storage_root' not in json.dumps(r.structured_content))
                err.seek(0);stderr=err.read();check(f'{restart}:clean_sdk_stop','MCP_INTEGRATION_STOPPED' not in stderr and 'Traceback' not in stderr)
                stopped=json.loads((owned/'owned-api-state/owned-api-stop.json').read_bytes());check(f'{restart}:owned_api_process_exited',stopped['api_exit_code']==0 and stopped['reader_stopped'] and stopped['session_id']==session)
                check(f'{restart}:owned_MCP_process_exited',own_process is not None and own_process.stopped())
        finally:
            # Exact own ephemeral bootstrap only; never publish channel MAC keys.
            assert boot.parent==owned and owned.is_relative_to(run);boot.unlink()
            if own_process:own_process.close()
        sessions.append({'session_id':session,'nonce_sha256':hashlib.sha256(nonce.encode()).hexdigest(),'context_sha256':last})
    check('restart_fresh_session_and_context',sessions[0]['session_id']!=sessions[1]['session_id'] and sessions[0]['context_sha256']!=sessions[1]['context_sha256'])
    return {'checks':checks,'sessions':sessions,'wire_calls':wire,'counts':{'total':len(checks),'passed':sum(x['status']=='PASS' for x in checks),'failed':sum(x['status']=='FAIL' for x in checks)},'scope':'real MCP SDK stdio -> integration -> separate real WebAlarmApi dispatch fixture; synthetic data only','OS_security_proof':False}
if __name__=='__main__':
    run=Path(sys.argv[1]);assert run.is_relative_to(REPORT/'runs') and (not run.exists() or {p.name for p in run.iterdir()}<={'temp'});run.mkdir(parents=True,exist_ok=True)
    try:
        result=asyncio.run(exercise(run));code=0
    except BaseException as exc:
        import traceback
        diagnostic=traceback.format_exc().replace(str(REPO),'<REPO>').replace(REPO.as_posix(),'<REPO>').replace(sys.base_prefix,'<PYTHON>')
        result={'status':'FAIL','error_class':type(exc).__name__,'diagnostic':diagnostic};code=1
    (run/'result.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='utf-8');print(json.dumps({'exit':code,'counts':result.get('counts'),'error_class':result.get('error_class')}));sys.exit(code)
