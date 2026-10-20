"""Create review artifacts only after frozen offline tests; no lab execution."""
from pathlib import Path
import ast,datetime as dt,hashlib,importlib.util,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(ref,v):
    p=ROOT/ref;p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_file():assert load(p)==v;return
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    spec=importlib.util.spec_from_file_location('gate',ROOT/'source/lab_gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    run=load(ROOT/'evidence/attempt08/run.json');assert run['test_counts']=={'total':52,'passed':52,'failed':0,'errors':0}
    frozen=['source/lab_gate.py','source/Signatures.cs','tests/test_gate.py','adapters/Collect-Host.ps1','adapters/Read-HyperVApproved.ps1','tools/run_checks.py']
    for ref in frozen:assert sha(ROOT/ref)==run['source_pins'][ref]
    for name,failures in [('mutant_nic03',2),('mutant_trust03',1)]:
        r=load(ROOT/'evidence'/name/'run.json');assert r['mutant_killed'] and r['test_counts']['failed']==failures and r['test_counts']['errors']==0
        for ref in frozen:assert r['source_pins'][ref]==run['source_pins'][ref]
    helper=ROOT/'evidence/attempt08/Signatures.exe';assert sha(helper)==run['helper_sha256']
    save('fixtures/unprovisioned.json',{'request':None})
    env={k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ}
    if not (ROOT/'gate_results.json').exists():
        p=subprocess.run([sys.executable,'-B',str(ROOT/'source/lab_gate.py'),'check','--bundle',str(ROOT/'fixtures/unprovisioned.json'),'--helper',str(helper),'--output',str(ROOT/'gate_results.json')],env=env,cwd=ROOT,capture_output=True,timeout=8);assert p.returncode==20
    actual=load(ROOT/'gate_results.json');assert actual['decision']=='BLOCKED' and len(actual['requirements'])==12 and all(r['status']=='BLOCKED' for r in actual['requirements']) and actual['evidence_digest']==gate.digest({'request':None})
    inv=load(ROOT/'host_readonly_inventory.json')
    names=['Identity, VM GUID, owner, backend/version and guest boot/baseline','Complete device census: zero NIC, NAT, bridge, host-only, forwarding','Guest-host integration, console, clipboard, relay and devices','Owned complete disk/media parent chain, local exclusive storage','Guest network/PnP/routes/DNS/proxy corroboration','Exact staged assets, origins, dependencies and startup closure','Disposable credentials/profile and no real tunnel/proxy secrets','Independent attempts observers, coverage, loss, heartbeat and correlation','Exact guest loopback receivers with positive/negative controls','Guest-contained approved process/descendant graph','Continuous config/observer watch and independent power control','Owned clean checkpoint, rollback, recovery and evidence retention']
    save('contracts/isolation_contract.json',{'schema':1,'contract':'I01-I12 executable snapshot validation','source_contract':'reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/isolation_preflight_contract.md','requirements':[{'id':i,'meaning':name,'required_signed_sources':gate.ROLES[i]+['review'],'current_real_status':'BLOCKED'} for i,name in zip(gate.IDS,names)],'limits':{'real_attestation_produced':False,'live_watch_implemented':False,'approval_activates_execution':False,'input_max_bytes':1048576,'input_max_depth':16,'request_ttl_seconds_max':300,'observation_age_seconds_max':60,'heartbeat_age_ms_max':1000,'max_approved_endpoints':8},'decision':'Missing proof -> BLOCKED; authenticated contradiction -> FAIL; all independent signed and approved snapshot conditions -> evidence-only PASS. NOT RUN is an adapter/test execution status. Synthetic PASS never authorizes a lab.'})
    proposed=gate.plan('55555555-5555-4555-8555-555555555555','C:\\ProposedLab\\owned-new','2'*64,inv)
    proposed['parameter_status']='SYNTHETIC EXAMPLE ONLY: owner/root/media digest NOT approved or discovered; not deployable'
    save('lab_build_plan.json',proposed)
    ps=load(ROOT/'evidence/ps51_syntax.json');assert len(ps['files'])==2 and all(x['parse_errors']==0 for x in ps['files'])
    allow={'ConvertTo-Json','ForEach-Object','Get-ChildItem','Get-CimInstance','Get-Module','Import-Module','Join-Path','LocalQuery','Split-Path','Where-Object','Write-Output','ConvertFrom-Json','Core','DigestText','Get-Command','Get-Content','Get-FileHash','Get-Item','Hyper-V\\Get-VM','Save'}
    for f in ps['files']:assert set(f['named_commands'])<=allow and sha(ROOT/f['source'])==f['sha256']
    for folder in ['source','tests','tools']:
        for path in (ROOT/folder).glob('*.py'):ast.parse(path.read_bytes())
    baseline=load(ROOT/'protected_inputs.json');changed=[]
    for f in baseline['files']:
        if sha(ROOT.parents[1]/f['ref'])!=f['sha256']:changed.append(f['ref'])
    assert not changed
    # Local file reads only: confirm old implementation barriers, never import them.
    old=ROOT.parent/'CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001'
    portable=[p for p in old.rglob('*.psm1') if '$script:BackendImplemented = $false' in p.read_text(encoding='utf-8-sig')]
    assert portable
    core=ROOT.parent/'CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/source/Core.cs'
    assert 'public static bool CanApply{get{return false;}}' in core.read_text(encoding='utf-8-sig')
    checks={'task_id':ROOT.name,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'offline_gate_logic':'OFFLINE_GATE_LOGIC_TESTED','final_suite':run['test_counts'],'final_suite_ref':'evidence/attempt08/run.json','frozen_source_refs':frozen,'mutations':[{'id':n,'ref':'evidence/'+n+'/run.json','mutant_killed':True,'expected_failed':f} for n,f in [('mutant_nic03',2),('mutant_trust03',1)]],'retained_genuine_red':{'ref':'evidence/attempt05/run.json','total':51,'passed':50,'failed':1,'errors':0,'case':'test_signed_negative_fact_dominates_missing_review','fix':'Signed contradiction evaluated even when independent review is missing; FAIL dominates BLOCKED'},'host_collector_runs':1,'host_snapshot_utc':inv['collected_utc'],'host_snapshot_sha256':sha(ROOT/'host_readonly_inventory.json'),'actual_gate_exit':20,'actual_gate_sha256':sha(ROOT/'gate_results.json'),'actual_gate_provenance':{'input':'fixtures/unprovisioned.json','input_sha256':sha(ROOT/'fixtures/unprovisioned.json'),'inventory':'host_readonly_inventory.json','inventory_link':'Context only, not a signed I01-I12 attestation','helper_sha256':sha(helper)},'ps51':{'runtime':ps['runtime'],'parsed_files':2,'errors':0,'named_command_allowlist':'PASS','adapter_invocations_in_parser':0,'initial_file_execution':'BLOCKED BY POLICY; no policy change; direct parser metadata command used'},'source_barriers':{'protected_total':len(baseline['files']),'unchanged_before_rotation':len(baseline['files']),'noncard_expected_after_rotation':sum(not r['card'] for r in baseline['files']),'portable_backend_flags_false_count':len(portable),'wfp_CanApply':False,'old_modules_imported_or_run':0},'real_operations':{'vm_queries':0,'vm_mutations':0,'feature_or_hypervisor_installs':0,'WFP_native_calls':0,'network_probes':0,'V2Ray_changes':0,'Git_GitHub_calls':0,'rights_or_policy_changes':0},'unverified':['Hyper-V adapter runtime and full channel/storage census','Trusted Windows media and ready owned VM','Host/guest attempts observers and real isolation','Future apply/stop/cleanup enforcement','Native WFP and client/network/E2E'], 'states':['OFFLINE_GATE_LOGIC_TESTED','LAB_PLATFORM_NOT_PROVISIONED','HOST_CONFIG_PROOF_PENDING','GUEST_ISOLATION_PROOF_PENDING','NATIVE_WFP_EXECUTION_BLOCKED']}
    save('checks.json',checks)
    print(json.dumps({'suite':run['test_counts'],'actual_gate':'BLOCKED 12/12','ps51_parse_errors':0,'protected_unchanged':len(baseline['files']),'portable_false_flags':len(portable)}))
if __name__=='__main__':main()
