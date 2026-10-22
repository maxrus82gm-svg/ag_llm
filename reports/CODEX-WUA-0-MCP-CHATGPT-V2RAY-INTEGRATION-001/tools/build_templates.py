"""Render disabled portable contracts from locally cached official evidence."""
from pathlib import Path
import copy,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];PKG=ROOT/'integrations/wua_chatgpt_mcp';OUT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PKG))
from common import digest
from security_contract import synthetic_profile,preflight
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    if p.name=='gateway.ipc.contract.json':
        v.update(selected_target_chain='C: official Go -> STDIO -> no-TCP synchronous C relay -> local authenticated pipe -> server-owned MCP SDK + WebAlarmApi authority U',mcp_role_in_identity_contract='C-owned stdio pipe relay, not installed Python asyncio server',runtime_blocker='Current Python3.12 ProactorEventLoop opens dynamic TCP selfpipe; do not launch it under C-only broker-port WFP intent',new_relay_implemented=False)
    if p.name=='tunnel.launch.contract.json':
        v['mcp_entrypoint']='Future independently reviewed C-owned synchronous STDIO-to-local-pipe relay with no TCP runtime, leading to server-owned SDK gateway; current fixture-only Python entry must NOT be placed under C-only broker-port policy'
        v['missing'].append('Current Python asyncio selfpipe conflict; selected no-TCP C relay and server-owned MCP peer not yet implemented')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    cache=ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/secure_tunnel_preparation';help=(cache/'run_help.txt').read_text(encoding='utf-8-sig');sample=(cache/'stdio_sample.txt').read_text(encoding='utf-8-sig')
    flags=['config','http-proxy','control-plane.http-proxy','mcp.http-proxy','harpoon.http-proxy','health.listen-addr']
    assert all(re.search(r'--'+re.escape(flag)+r'\s',help) for flag in flags)
    assert 'mcp:' in sample and 'commands:' in sample and 'channel: main' in sample
    cfg=PKG/'configs';cfg.mkdir()
    example=synthetic_profile();save(cfg/'strict.synthetic.example.json',example)
    template=copy.deepcopy(example);template['owner']=None;template['identities']={k:None for k in template['identities']};template['processes']={'tunnel':None,'mcp':None,'gateway':'SERVER_OWNED_AUTHORITY','v2ray':None};template['route'].update(client_proxy_port=None,egress_ip=None,egress_port=None)
    for child in template['children']:child.update(owner_sid=None,sha256=None)
    save(cfg/'strict.template.json',template)
    save(cfg/'tunnel.launch.contract.json',{'schema':1,'state':'DISABLED / DO NOT EXECUTE','official_client_candidate':'0.0.16+5f99daabd4aa4a77049e6d81d54a0d8c18335397','source_binary_attestation':'NOT VERIFIED','executable':'${INDEPENDENTLY_VERIFIED_TUNNEL_CLIENT_EXE}','argv':['run','--config','${SEALED_CONFIG_FILE}','--http-proxy','http://127.0.0.1:${BROKER_PORT}','--control-plane.http-proxy','http://127.0.0.1:${BROKER_PORT}','--mcp.http-proxy','http://127.0.0.1:${BROKER_PORT}','--harpoon.http-proxy','http://127.0.0.1:${BROKER_PORT}','--health.listen-addr','127.0.0.1:0'],'argv_is_data_only':True,'environment_policy':{'inherit_user_environment':False,'baseline_keys':['SystemRoot','WINDIR','COMSPEC'],'separate_secret_delivery':'Approved private runtime reference only, not supplied or opened here','deny_ambient':['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','TUNNEL_CLIENT_PROFILE','TUNNEL_CLIENT_PROFILE_FILE','TUNNEL_CLIENT_PROFILE_DIR','TUNNEL_CLIENT_CONFIG','CONTROL_PLANE_BASE_URL','CA_BUNDLE','CLOUDFLARED_TUNNEL_TOKEN','CLOUDFLARED_MANAGED','HARPOON_TARGETS','HARPOON_ADDITIONAL_TRANSPORTS'],'full_native_env_graph':'PENDING SOURCE AUDIT; list is not exhaustive enforcement proof'},'mcp_transport':'STDIO','mcp_entrypoint':'Future reviewed server-owned IPC connector; current fixture-only entry must not be used as a production authority','health_listener':'Own ephemeral loopback H, separate bind/UI/accepted-flow proof needed; no automatic C outbound exception','cloudflared':'NOT CONFIGURED / MUST REMAIN ABSENT; native child proof pending','Harpoon_OAuth':'No HTTP MCP OAuth discovery intended under stdio; no configured Harpoon targets; full native branch audit pending','can_start':False,'missing':['Approved source pack and source-to-binary proof','Real local SID/token/ACL/startup and effective WFP/IPC containment','Dedicated V2Ray ownership/config/remote-only evidence','Reviewed API gateway connector, private runtime auth, workspace entitlement and tunnel resource','Independent acceptance and exact separate USER GO']})
    yaml='''# Disabled v0.0.16 cached-sample template; placeholders MUST NOT be executed.
# Proxy settings are explicit argv in tunnel.launch.contract.json, not guessed YAML keys.
config_version: 1
control_plane:
  base_url: "https://api.openai.com"
  tunnel_id: ""
  api_key: "env:WUA_TUNNEL_RUNTIME_KEY"
health:
  listen_addr: "127.0.0.1:0"
admin_ui:
  open_browser: false
log:
  level: info
  format: json
mcp:
  commands:
    - channel: main
      command: "${SIGNED_PRODUCTION_MCP_ENTRY_COMMAND}"
'''
    with (cfg/'tunnel-client.v0.0.16.disabled.yaml').open('x',encoding='utf-8') as f:f.write(yaml)
    save(cfg/'broker.contract.json',{'schema':1,'profile':'STRICT_V2RAY_BROKER','target_layout':'DEDICATED_V2RAY_CONNECT_INBOUND','state':'DISABLED','process_owner':'new locally provisioned wua-broker SID, equal V2Ray actual effective token SID','client_identity':'new distinct local wua-client SID','inbound':{'interface':'literal127.0.0.1','port':'assigned owned P, no hardcoded default','protocol':'verified HTTP CONNECT support of selected dedicated V2Ray build','owner_bind':'Native bind/listener and peer ownership proof required; port number alone insufficient'},'outbound':{'remote':'approved literal R:Q TCP','no_DIRECT':True,'secondary_proxy':False,'host_resolver':False,'fallback':False,'secrets':'private approved broker-only upstream credential store; absent here'},'existing_V2Ray':'No profile/listener/process ownership inspection or mutation in this TASK','reference_adapter':'reference_connect.py is synthetic-only CONNECT -> owned SOCKS5; it is not selected for live topology because local S and external owner require additional policy proof','upstream_config_format':'NOT GENERATED: exact V2Ray implementation/version/schema must be selected and independently reviewed','can_apply':False})
    save(cfg/'gateway.ipc.contract.json',{'schema':1,'protocol':'wua-api-jsonl-v1','current_executable':'api_fixture.py, synthetic STDIO worker, fresh owned state only','future_transport':'local Windows named pipe, under existing server-owned authority; not TCP API to production','future_requirements':['Local NPFS namespace only, reject remote SMB/UNC access','Server-created exclusive pipe instance with versioned DACL and no broad Everyone/anonymous access','Server validates client process/token SID C; client validates server PID/token and signed executable identity','Bounded frames, challenge/session-bound capability, exact read-only TASK grant, replay and deadline limits','No arbitrary method/path/storage-root or model credentials; server dispatch only approved status/context','No network delegation, writes or code execution via IPC; negative tests for other host IPC/services still required'],'current_Windows_pipe_created':False,'ACL_or_impersonation_proven':False,'TCP_exception_added':False,'production_connector':'BLOCKED / NOT IMPLEMENTED IN THIS FIXTURE PACKAGE'})
    save(cfg/'health.contract.json',{'schema':1,'source':'get_status MCP tool -> server-owned /status dispatch','public_fields':['status','service','api_version','mode'],'proof_fields':['session_id','nonce','api_reads','api_route','baseline_sha256','current_sha256'],'do_not_return':['storage_root','raw profiles','secrets','full environment','host usernames'],'route_state':'UNVERIFIED until real OS/owner/observer evidence; MCP ok cannot imply WFP/V2Ray ok','startup_decision':'BLOCKED if any identity, broker, pipe, observer, source/config/hash or approval is unknown or lost','on_failure':'No retry to DIRECT/secondary proxy; stop owned chain only under approved supervisor authority; no auto-resume or weakening','native_stop_supervisor':'NOT IMPLEMENTED; future separate reviewed component'})
    save(OUT/'source_evidence.json',{'status':'VERSION-PINNED CACHED EVIDENCE / LIVE UPSTREAM NOT FETCHED','official_references':['https://developers.openai.com/api/docs/guides/secure-mcp-tunnels','https://github.com/openai/tunnel-client/blob/master/docs/configuration.md'],'cached_sources':[{'ref':str(p.relative_to(ROOT).as_posix()),'sha256':sha(p)} for p in [cache/'run_help.txt',cache/'stdio_sample.txt',cache/'version.txt',ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/http_socks_adapter_20261018/source_audit.md']],'verified_cached_flags':flags,'client_executions_in_this_TASK':0,'network_or_Git_fetches':0,'limits':'Cached sample/help corroborate version-specific names and STDIO, not complete native config precedence, fallback, source-to-EXE identity or current service entitlement. No API key or tunnel ID supplied.'})
    save(OUT/'diagnostic_preflight.json',preflight(example,digest(example),{'verified':True}))
    print(json.dumps({'templates':len(list(cfg.iterdir())),'cached_flags':len(flags),'preflight_can_apply':False}))
if __name__=='__main__':main()
