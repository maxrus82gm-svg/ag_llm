"""Offline evidence sealing for this TASK; no Git/network/card mutation."""
from pathlib import Path
import ast,datetime,hashlib,json,sys

TASK=Path(__file__).resolve().parent;REPO=TASK.parents[1]
CHANGED=['integrations/wua_chatgpt_mcp/broker.py','integrations/wua_chatgpt_mcp/security_contract.py',
         'integrations/wua_chatgpt_mcp/configs/broker.v1.schema.json','integrations/wua_chatgpt_mcp/tests/admission_suite.py']
def guard(event,args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):
        raise PermissionError('OFFLINE_METADATA_ONLY')
sys.addaudithook(guard)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
    assert p.resolve().is_relative_to(TASK)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    old=json.loads((TASK/'evidence/inputs_before.json').read_bytes())['files']
    unchanged=[];changes=[]
    for row in old:
        p=REPO/row['path'];now=sha(p)
        if row['path'] in CHANGED:
            changes.append({'path':row['path'],'before_sha256':row['sha256'],'after_sha256':now})
        else:
            assert now==row['sha256'],row['path'];unchanged.append(row['path'])
    assert len(changes)==3
    changes.append({'path':CHANGED[-1],'before_sha256':None,'after_sha256':sha(REPO/CHANGED[-1])})
    before_map={r['path']:r for r in old}
    for name in ['broker.py','security_contract.py','configs/broker.v1.schema.json','tests/broker_suite.py']:
        assert sha(TASK/'source_before'/name)==before_map['integrations/wua_chatgpt_mcp/'+name]['sha256']
    focus=TASK/'runs/admission-20261025-135342-16add776'
    regression=TASK/'runs/source-regression-20261025-135559-d6c08e21'
    for run,count in [(focus,52),(regression,51)]:
        result=json.loads((run/'result.json').read_bytes())
        assert result['collected']==result['passed']==count
        assert result['failed']==result['errors']==result['skipped']==result['exit_code']==0
        for name,pin in json.loads((run/'source_pins.json').read_bytes()).items():assert sha(REPO/name)==pin,name
    red=json.loads((TASK/'runs/admission-20261025-134958-2caf5be1/result.json').read_bytes())
    assert (red['collected'],red['passed'],red['failed'],red['errors'],red['exit_code'])==(40,19,21,0,1)
    mutants=sorted(focus.glob('mutant-*.json'));assert len(mutants)==7
    for p in mutants:
        m=json.loads(p.read_bytes());assert (m['inner_collected'],m['inner_failures'],m['inner_errors'])==(1,1,0)
    attempts=[]
    for p in sorted((TASK/'runs').glob('*/result.json')):
        r=json.loads(p.read_bytes());attempts.append({'path':p.relative_to(TASK).as_posix(),
            'collected':r['collected'],'pass':r['passed'],'fail':r['failed'],'error':r['errors'],'skip':r['skipped'],'exit_code':r['exit_code']})
    # The public example is unchanged and remains structurally valid/blocked.
    sys.path.insert(0,str(REPO/'integrations/wua_chatgpt_mcp'))
    import broker,common
    p=json.loads((REPO/'integrations/wua_chatgpt_mcp/configs/broker.v1.synthetic.example.json').read_bytes())
    example=broker.preflight(p,common.digest(p),broker.source_pin())
    assert example['profile_status']=='BROKER_PROFILE_STRUCTURALLY_VALID'
    assert example['strict_admission_status']=='STRICT_ADMISSION_BLOCKED'
    assert not example['can_apply'] and not example['can_start_tunnel'] and example['install_uninstall']=='BLOCKED'
    put(TASK/'evidence/legacy_fixture_result.json',example)
    # All actual new source/tests and report-side Python are parsed, never native compiled.
    syntax=[]
    for name in CHANGED:
        f=REPO/name
        if f.suffix=='.py':ast.parse(f.read_bytes());syntax.append(name)
        elif f.suffix=='.json':json.loads(f.read_bytes())
    ast.parse(Path(__file__).read_bytes())
    card=(REPO/'Документация/000_Задачи Codex.md').read_text(encoding='utf-8')
    snapshot=card.split('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n',1)[1].split('# БЛОК 2 —',1)[0]
    assert snapshot==(TASK/'evidence/task_snapshot.md').read_text(encoding='utf-8')
    put(TASK/'evidence/final_integrity.json',{'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'selected_read_only_inputs_unchanged':len(unchanged),'read_only_paths':unchanged,
        'authorized_changes':changes,'source_before_copies_preserved':4,
        'final_run_source_pins_match':True,'task_snapshot_matches_current_B1':True,
        'card_all_blocks_unchanged':True,'personal_001_read_or_written':False,
        'syntax_paths':syntax,'limit':'Local selected files, not Git HEAD or whole-host attestation'})
    put(TASK/'evidence/test_quality.json',{'first_red':'runs/admission-20261025-134958-2caf5be1/result.json',
        'first_red_meaning':'Old code lacked explicit strict API/status; not live network exploitation',
        'first_red_preserved':True,'expected_codes_not_weakened':True,
        'mutants':[{k:json.loads(m.read_bytes())[k] for k in ['label','inner_collected','inner_failures','inner_errors','source_sha256','mutant_sha256']} for m in mutants],
        'mutation_execution':'In-memory Python copies, no disk source substitution, subprocess or Go/native',
        'counts_overlap':'19 pure ContractTests occur in focus and source regression; do not add as unique tests',
        'secret_handling':'Only deliberately synthetic markers/opaque UUID refs in tests; no real credentials/store/profile/logs accessed',
        'native_gaps':['Go HTTP/JSON/auth boundary','credential-store/config ACL','real C/B SID/WFP/socket owner','runtime route and policy loss','hosted/ordinary Chat E2E']})
    rules=['DOC-GIT-01@1','DOC-LOCAL-REPORT-HANDOFF-01@1','DOC-TASK-CLOSEOUT-OWNER-01@1',
           'DOC-TASK-READ-SCOPE-01@1','DOC-TASK-HANDOFF-USER-01@1','TEST-COLLAB-01@2',
           'TEST-ENG-01@1','TEST-COV-01@1','TEST-EXEC-01@1','TEST-QA-01@1','TEST-EVID-01@1','TEST-SCOPE-01@1']
    put(TASK/'evidence/read_set.json',{'rule_set_ref':rules,'normative_inputs':[r for r in old if r['path'].startswith('Документация/')],
        'read_sections':{'card':'Rules/B1/B4','08':'Priority handoff and rights','34':'WEB_12 CURRENT',
          '19':'STRICT_V2RAY_BROKER,7.6/7.7','18':'Addressed Git/report/closeout/read-scope rules and dependencies',
          '36.1':'Applicable mandatory TEST rules','36.2':'Offline isolation/evidence invariants'},
        'technical_sources':'Broker/security/schema/example/ContractTests and prior accepted sing report/graph/gap matrix; source validator read-only',
        'sync_evidence':'evidence/sync_gate.json; user confirmation, not Git verification'})
    put(TASK/'checks.json',{'task':TASK.name,'status':'OFFLINE ADMISSION CONTRACT PASS / AWAITING INDEPENDENT VERIFICATION',
        'primary_command':'.\\.venv\\Scripts\\python.exe -B integrations/wua_chatgpt_mcp/tests/admission_suite.py',
        'attempts':attempts,'primary_final':{'collected':52,'pass':52,'fail':0,'error':0,'skip':0,'exit_code':0},
        'primary_components':{'legacy_pure':19,'admission':26,'executed_python_mutants':7},
        'source_compatibility':{'collected':51,'pass':51,'fail':0,'error':0,'skip':0,'exit_code':0},
        'source_compatibility_command':'exec_command Python stdin selector: existing SourceTests+DependencyTests+19 pure ContractTests, module RUN/OUT rebound to this TASK; never original main which writes old TASK',
        'source_regression_runner':regression.relative_to(TASK).as_posix(),
        'overlap':'19 legacy pure methods; counts not additive as unique coverage',
        'mutants_detected':7,'syntax_ast_passed':True,'offline_guard_violations':0,
        'native_network_go_install_tests':'NOT RUN / FORBIDDEN','legacy_RouteTests':'NOT COLLECTED / NETWORK PROHIBITED',
        'legacy_two_contract_tests_not_collected':['test_cli_always_exit20_and_output_scope','test_remote_schema_reference_is_refused_without_dial'],
        'downloads':0,'git_operations':0,'windows_proxy_wfp_engine_changes':0,'can_apply':False,'can_start_tunnel':False,
        'install_uninstall':'BLOCKED','strict_admission_status':'STRICT_ADMISSION_BLOCKED','native_security':'NOT VERIFIED',
        'upstream_secret_boundary':'SECURITY BLOCKER / UNVERIFIED','independent_verification':'PENDING WEB_12',
        'publication':'LOCAL ONLY / NOT SYNCED'})
    entries=[]
    for p in sorted(TASK.rglob('*')):
        if p.is_file() and p!=TASK/'manifest.json':
            assert not p.is_symlink() and p.suffix.lower() not in ('.zip','.exe','.pyc')
            entries.append({'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    for name in CHANGED:
        p=REPO/name;entries.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
    put(TASK/'manifest.json',{'task':TASK.name,'status':'OFFLINE ADMISSION CONTRACT PASS / AUTHOR TESTED',
        'independent_verification':'PENDING WEB_12','publication':'LOCAL ONLY / NOT SYNCED',
        'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'path_base':'repository root M:/GitHub/ag_llm',
        'files':entries,'excludes':['reports/'+TASK.name+'/manifest.json (self hash)'],
        'task_snapshot':'reports/'+TASK.name+'/evidence/task_snapshot.md','amendments':['User sync confirmation before source edits'],
        'source_reference':'User-declared synchronized main after GPT@37ef710cf0ba34f4988cba46a28595d6ce7801a5; Git not queried',
        'can_apply':False,'can_start_tunnel':False,'install_uninstall':'BLOCKED','native_security':'NOT VERIFIED'})
    print(json.dumps({'manifest_entries':len(entries),'unchanged_inputs':len(unchanged),'primary_tests':52,'source_regression':51,'mutants_killed':7,'card_unchanged':True}))
if __name__=='__main__':main()
