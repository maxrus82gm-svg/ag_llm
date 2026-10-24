"""Assemble bounded factual evidence; no host discovery, archive reads or network."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1]
PKG=REPO/'integrations/wua_chatgpt_mcp';sys.path.insert(0,str(PKG))
import broker,common
FINAL='runs/suite-20261024-131413-2a8f10b2'
REGRESSION='runs/regression-20261024-130416-724b2ebc'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    final=load(OUT/FINAL/'result.json');reg=load(OUT/REGRESSION/'result.json')
    assert final['collected']==final['passed']==33 and final['failed']==final['errors']==final['skipped']==0
    assert reg['mcp01']['passed']==63 and reg['security01']['passed']==24 and reg['original_sources_unchanged']
    pins=load(OUT/FINAL/'source_pins.json')
    assert all(sha(REPO/p)==v for p,v in pins.items())
    initial=load(OUT/'evidence/initial_state.json')
    changed=[p for p,v in initial['inputs'].items() if sha(REPO/p)!=v['sha256'] or (REPO/p).stat().st_size!=v['bytes']]
    assert not changed,changed
    put(OUT/'evidence/protected_inputs_check.json',{'protected':len(initial['inputs']),'unchanged':len(initial['inputs']),'changed':changed,'current_suite_source_pins_match':True,'archive_read_for_this_check':False})
    old=REPO/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/v2ray_preflight_20261017/preflight.sanitized.json'
    inv=REPO/'reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/host_discovery_release/inventory.json'
    historical=load(old);inventory=load(inv)
    selected=[x for x in inventory['fields'] if x['id'] in ['broker.binary','broker.version','broker.schema','broker.route_graph']]
    put(OUT/'evidence/engine_cached_metadata.json',{'kind':'HISTORICAL_PROJECT_EVIDENCE_ONLY','not_current_process_discovery':True,'source_pins':{p.relative_to(REPO).as_posix():sha(p) for p in [old,inv]},'historical_processes':historical['processes'],'selected_inventory':selected,'current_V2Ray_binary_path':None,'verified_V2Ray_version':None,'native_engine_invocations_this_task':0,'working_profiles_read_this_task':0})
    contract=load(PKG/'configs/broker.v1.synthetic.example.json')
    put(OUT/'evidence/preflight.valid-example.json',broker.preflight(contract,common.digest(contract),broker.source_pin()))
    contract=load(PKG/'configs/v2ray.engine.disabled.contract.json')
    put(OUT/'evidence/preflight.unbound-template.json',broker.preflight(contract,common.digest(contract),broker.source_pin()))
    put(OUT/'evidence/runtime_dependencies.json',{'python':sys.version,'interpreter':sys.executable,'packages':{n:importlib.metadata.version(n) for n in ['jsonschema','mcp','httpx','pydantic']},'automatic_installs':0,'note':'Base Python312 isolated interpreter has no jsonschema distribution; use existing repository .venv. Missing dependencies BLOCK the run, never trigger install.'})
    attempts=[]
    for p in sorted((OUT/'runs').glob('suite-*/result.json')):
        v=load(p);attempts.append({'path':p.parent.relative_to(OUT).as_posix(),'collected':v['collected'],'passed':v['passed'],'failed':v['failed'],'errors':v['errors'],'skipped':v['skipped'],'failures':[x for x in v['tests'] if x['status']!='PASS']})
    mutations=[{'path':p.relative_to(OUT).as_posix(),**load(p)} for p in (OUT/FINAL).glob('*/mutation.json')]
    assert len(mutations)==2 and all(m['oracle'].startswith('FAIL') for m in mutations)
    put(OUT/'broker_test_results.json',{'task':broker.TASK,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11','final_suite_path':FINAL,'final_suite':final,'attempts':attempts,'initial_failure_classification':[{'attempt':attempts[0]['path'],'class':'CODE DEFECT','detail':'Isolated CLI could not import common; repaired explicit trusted own-package import root.'},{'attempt':attempts[1]['path'],'class':'TEST HARNESS DEFECT','detail':'Copied owner mutant had no __file__; supplied its real source path without weakening the owner oracle.'}],'mutations':mutations,'regression_path':REGRESSION,'regression':reg,'profile_status':'BROKER_PROFILE_STRUCTURALLY_VALID (bound synthetic example only)','gates':broker.GATES,'can_apply':False,'can_start_tunnel':False,'real_engine_runs':0,'native_WFP_calls':0,'new_accounts':0,'OpenAI_Platform_or_hosted_tunnel_calls':0,'Git_GitHub_operations':0,'external_targets_in_fixture':0,'independent_acceptance':'NOT VERIFIED'})
    print(json.dumps({'suite':final['collected'],'regression':[reg['mcp01']['passed'],reg['security01']['passed']],'protected_unchanged':len(initial['inputs']),'mutations_detected':len(mutations),'attempts_preserved':len(attempts)}))
if __name__=='__main__':main()
