"""Single exact binary read; no engine process or directory search. No network."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1]
sys.path.insert(0,str(REPO/'integrations/wua_chatgpt_mcp'))
import common,engine_snapshot as engine
def main():
    assert len(sys.argv)==2,'EXACT_BINARY_PATH_REQUIRED'
    path=Path(sys.argv[1]);value=engine.inspect_binary(path,path)
    target=OUT/'evidence/binary_snapshot.json'
    with target.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    prior=REPO/'reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/evidence/engine_cached_metadata.json'
    old=json.loads(prior.read_bytes());historical=next(p for p in old['historical_processes'] if p['name']=='sing-box.exe')
    receipt={'path_label':'ENGINE_BINARY_01','inventory_canonical_sha256':common.digest(value),'binary_sha256':value['sha256'],'historical_hash_matches':historical['executable_sha256']==value['sha256'],'historical_evidence_path':prior.relative_to(REPO).as_posix(),'historical_evidence_sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),'exact_adjacent_source_candidates':[{'name':name,'exists':(path.parent/name).is_file()} for name in ['go.mod','go.sum','README.md','LICENSE','config.schema.json']],'directory_scan':False,'engine_process_launches':0,'working_config_reads':0,'external_requests':0,'path_redacted_in_public_snapshot':True}
    with (OUT/'evidence/inventory_receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
    print(json.dumps({'binary_sha256':value['sha256'],'module_version_claim':value['go_build']['module_version_claim'],'historical_hash_matches':receipt['historical_hash_matches'],'engine_runs':0}))
if __name__=='__main__':main()
