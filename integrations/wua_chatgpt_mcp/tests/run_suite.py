"""Bounded fixture-only runner; no installers, native clients or network itself."""
from pathlib import Path
import ast,hashlib,importlib.metadata,json,os,re,subprocess,sys,time
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1];OUT=REPO/'reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    label=sys.argv[1];assert re.fullmatch(r'(?:security|mcp|mutant_route|mutant_owner)[0-9]{2}',label)
    run=OUT/'runs'/label;run.mkdir(parents=True);(run/'temp').mkdir()
    pins={p.relative_to(REPO).as_posix():sha(p) for p in PKG.rglob('*') if p.is_file()}
    for p in PKG.rglob('*.py'):ast.parse(p.read_bytes())
    env={k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ};env['TEMP']=env['TMP']=str(run/'temp')
    mode='route' if label.startswith('mutant_route') else 'owner' if label.startswith('mutant_owner') else None
    script='mcp_smoke.py' if label.startswith('mcp') else 'test_security_routes.py'
    args=[sys.executable,'-I','-X','utf8','-B',str(PKG/'tests'/script),str(run)]+([mode] if mode else [])
    start=time.monotonic();p=subprocess.run(args,cwd=PKG,env=env,capture_output=True,timeout=65)
    result=json.loads((run/'result.json').read_bytes());expected='test_control_plane_paths_and_receipt_correlation' if mode=='route' else 'test_v2ray_host_user_owner_mismatch_denied' if mode else None
    killed=bool(mode and p.returncode==1 and result['failed']==1 and result['errors']==0 and result['tests']==[{'name':expected,'status':'FAIL'}])
    success=(p.returncode==0 and not mode) or killed
    unchanged=all(sha(REPO/ref)==h for ref,h in pins.items());assert unchanged
    meta={'label':label,'exit_code':p.returncode,'counts':result.get('counts') or {k:result[k] for k in ['total','passed','failed','errors']},'mutant_killed':killed,'expected_mutant_failure':expected,'elapsed_seconds':round(time.monotonic()-start,3),'sources_before':pins,'sources_unchanged':unchanged,'python_version':sys.version.split()[0],'packages':{k:importlib.metadata.version(k) for k in ['mcp','httpx','pydantic']},'environment_keys':sorted(env),'stdout_summary':p.stdout.decode('utf-8',errors='replace').strip(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest(),'external_network_targets':0,'native_tunnel_or_WFP_executions':0}
    (run/'run_meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:meta[k] for k in ['label','exit_code','counts','mutant_killed','sources_unchanged']}));return 0 if success else 1
if __name__=='__main__':sys.exit(main())
