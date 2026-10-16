"""Independent CLI control/required pair. No persistent config or other MCP servers.

Normal Codex account auth is used in place; credentials are neither copied nor printed.
The user config/plugins are ignored only for each NEW test process. The same isolated
WUA copy and read-only sandbox are used in both; only required=true differs.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tomllib,time

D=Path(__file__).resolve().parent;CLI='C:/Users/REX/AppData/Local/OpenAI/Codex/bin/9614f1d9b40d9c4f/codex.exe'
config_file=Path('C:/Users/REX/.codex/config.toml');before=config_file.read_bytes()
config=tomllib.loads(before.decode('utf-8-sig'));original=config['mcp_servers']['wua_desktop_readonly']
root=D/'cli_pair';root.mkdir(exist_ok=False);plugin=root/'plugin';shutil.copytree(D.parent/'plugin',plugin)
prompt=('Use only the real native MCP tools of wua_desktop_readonly. Call ping, list_capabilities, '
        'read_synthetic_context with fixture_id synthetic_wua_desktop_001, and read_synthetic_context '
        'with fixture_id other_task. Use actual tool names exposed to you; do not require a dotted alias. '
        'No shell, SDK, file tools, network tools or code edits. Return session_id, nonce, context_sha256, '
        'proof_path and the real denial code. If tools are absent say unavailable without simulating calls. '
        'This is an isolated CLI test, not ordinary ChatGPT E2E.')
base=[CLI,'exec','--ephemeral','--sandbox','read-only','--ignore-user-config','--disable','plugins',
      '--skip-git-repo-check','--json','-C',str(root)]
if config.get('model'):base+=['-m',config['model']]
entry={'command':original['command'],'args':['-I','-X','utf8','-B',str(plugin/'server.py')],'cwd':str(plugin)}
for key,value in entry.items():base+=['-c','mcp_servers.wua_desktop_readonly.'+key+'='+json.dumps(value)]
summary={'kind':'REAL INDEPENDENT CODEX CLI RUNS; NOT SDK; NOT ORDINARY CHAT',
         'global_config_before_sha256':hashlib.sha256(before).hexdigest(),
         'isolation':'Ignore user config and plugins in NEW process; only one explicit WUA server; own copied candidate',
         'entry':entry,'cases':[]}
for label,extra in [('default',[]),('required',['-c','mcp_servers.wua_desktop_readonly.required=true'])]:
    stdout=root/(label+'.jsonl');stderr=root/(label+'.stderr.log')
    args=base+extra+[prompt];start=time.monotonic()
    env=os.environ.copy()
    env['RUST_LOG']='codex_mcp::connection_manager::tool_catalog=trace,codex_mcp::rmcp_client=info,rmcp::service=info'
    with stdout.open('wb') as out,stderr.open('wb') as err:
        process=subprocess.Popen(args,cwd=root,env=env,stdout=out,stderr=err)
        try:exit_code=process.wait(timeout=110)
        except subprocess.TimeoutExpired:
            process.terminate();exit_code=process.wait(timeout=10)
    events=[]
    for line in stdout.read_text(encoding='utf-8',errors='replace').splitlines():
        try:events.append(json.loads(line))
        except ValueError:pass
    calls=[];messages=[]
    for event in events:
        item=event.get('item',{})
        if item.get('type')=='mcp_tool_call':calls.append(item)
        if item.get('type')=='agent_message':messages.append(item.get('text',''))
    summary['cases'].append({'label':label,'exit_code':exit_code,'elapsed_seconds':round(time.monotonic()-start,3),
                             'mcp_call_event_items':calls,'agent_messages':messages,
                             'stdout':str(stdout),'stderr':str(stderr)})
    (D/'gate_d_pair.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'case':label,'exit_code':exit_code,'mcp_call_event_items':len(calls),'messages':messages},ensure_ascii=False),flush=True)
summary['global_config_unchanged']=config_file.read_bytes()==before
(D/'gate_d_pair.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
assert summary['global_config_unchanged']
