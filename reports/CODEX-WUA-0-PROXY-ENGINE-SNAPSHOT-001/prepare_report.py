"""Seal factual metadata/gates for this one TASK; no engine/host/network calls."""
from pathlib import Path
import hashlib,importlib.metadata,json,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1];PKG=REPO/'integrations/wua_chatgpt_mcp';sys.path.insert(0,str(PKG))
import broker,common,engine_snapshot as engine
FINAL='runs/suite-20261024-175139-adb7977b'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    s=load(OUT/'evidence/binary_snapshot.json');receipt=load(OUT/'evidence/inventory_receipt.json');process=load(OUT/'evidence/process_link.json')
    assert common.digest(s)==receipt['inventory_canonical_sha256'] and s['path_sha256']==process['core']['path_sha256']
    result=load(OUT/FINAL/'result.json');assert result['collected']==result['passed']==44 and result['failed']==result['errors']==result['skipped']==0
    pins=load(OUT/FINAL/'source_pins.json');assert all(sha(REPO/p)==v for p,v in pins.items())
    initial=load(OUT/'evidence/initial_state.json');changed=[p for p,v in initial['inputs'].items() if sha(REPO/p)!=v['sha256'] or (REPO/p).stat().st_size!=v['bytes']];assert not changed,changed
    c=load(PKG/'configs/broker.v1.synthetic.example.json')
    gates={'task':engine.TASK,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11','ENGINE_BINARY':'IDENTIFIED (exact local file, static metadata; family/release are embedded claims)','ENGINE_RELEASE_PROVENANCE':'BLOCKED','ENGINE_NATIVE_CONFIG_SCHEMA':'BLOCKED','STRICT_CONNECT_COMPATIBILITY':'UNVERIFIED','ENGINE_SELECTION':'PENDING_USER','B_IDENTITY':'NOT_PROVISIONED','B_EGRESS_OWNER':'NOT_VERIFIED','WFP_NATIVE_ENFORCEMENT':'NOT_VERIFIED','HOSTED_TUNNEL':'ON_HOLD_BY_USER','ORDINARY_CHATGPT_E2E':'NOT_VERIFIED','can_apply':False,'can_start_tunnel':False,'native_config':None,'inventory_pin':common.digest(s),'observed_V2Ray_selection':engine.evaluate(s,common.digest(s),c,common.digest(c),broker.source_pin(),'V2Ray'),'hypothetical_singbox_selection':engine.evaluate(s,common.digest(s),c,common.digest(c),broker.source_pin(),'sing-box'),'authentic_native_schema_check':'NOT RUN / NO MATCHING SOURCE OR SCHEMA','working_engine_modified':False}
    put(OUT/'compatibility_gates.json',gates)
    attempts=[{'path':p.parent.relative_to(OUT).as_posix(),**{k:load(p)[k] for k in ['collected','passed','failed','errors','skipped']}} for p in sorted((OUT/'runs').glob('suite-*/result.json'))]
    mutants=[{'path':p.relative_to(OUT).as_posix(),**load(p)} for p in (OUT/FINAL).glob('mutant-*/result.json')]
    assert len(mutants)==2 and all(x['inner_failures']==1 and x['inner_errors']==0 for x in mutants)
    put(OUT/'checks.json',{'task':engine.TASK,'final_suite_path':FINAL,'final_suite':result,'mutations':mutants,'attempts':attempts,'unexpected_initial_failures':0,'manual_review_test_gap_repaired':'Duplicate-module fixture initially changed file length and could trip PE bounds before module oracle. Preserved initial PASS; final test preserves byte length and demands GO_DUPLICATE_MODULE.','protected_unchanged':len(initial['inputs']),'changed':changed,'inventory_path_association_matches':True,'engine_runs':0,'native_network_tests':0,'working_config_reads':0,'Windows_or_network_mutations':0,'Git_GitHub_operations':0,'can_apply':False,'can_start_tunnel':False})
    put(OUT/'evidence/runtime_dependencies.json',{'python':sys.version,'interpreter':sys.executable,'packages':{'jsonschema':importlib.metadata.version('jsonschema')},'new_installs':0,'Go_tool_or_engine_execution':False})
    print(json.dumps({'tests':result['collected'],'new':result['new_metadata_tests'],'legacy_regression':result['legacy_pure_contract_regression'],'mutants':len(mutants),'protected_unchanged':len(initial['inputs']),'can_apply':False}))
if __name__=='__main__':main()
