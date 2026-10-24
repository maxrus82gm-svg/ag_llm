"""Current amendment manifest + all source-tree pins, no archive history reads."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent;OUT=A.parent;REPO=OUT.parents[1]
NEW=['integrations/wua_chatgpt_mcp/singbox_source_review.py','integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    required=['report.md','source_bundle_provenance.md','http_connect_review.md','route_and_fallback_review.md','network_egress_review.md','config_loader_review.md','compatibility_matrix.md','test_results.json','manual_engineering_review.md','next_user_decision.md']
    assert all((OUT/p).is_file() for p in required)
    state=load(A/'evidence/initial_state.json');changed=[p for p,v in state['inputs'].items() if sha(REPO/p)!=v['sha256'] or (REPO/p).stat().st_size!=v['bytes']];assert not changed,changed
    facts=load(OUT/'test_results.json');assert facts['final_result']['collected']==facts['final_result']['passed']==30 and facts['source_tests']==11 and facts['existing_pure_regression']==19
    run=OUT/facts['final_run'];pins=load(run/'local_source_pins.json');assert all(sha(REPO/p)==v for p,v in pins.items())
    source=load(A/'evidence/source_tree_manifest.json');root=Path(source['source_root']);archive=Path(source['archive_path']);assert sha(archive)==source['archive_sha256']==facts['source_archive_sha256']
    assert source['zip_comment_revision']==facts['source_revision'] and len(source['files'])==1013
    assert all((root.parent/x['path']).stat().st_size==x['bytes'] and sha(root.parent/x['path'])==x['sha256'] for x in source['files'])
    upstream=load(run/'upstream_source_pins.json');assert all(sha(root/p)==v for p,v in upstream.items())
    card=REPO/'Документация/000_Задачи Codex.md';raw=card.read_bytes();b4=raw[raw.index('# БЛОК 4 —'.encode()):];assert hashlib.sha256(b4).hexdigest()==state['block4_sha256']
    receipt=load(A/'evidence/card_rotation.json') if (A/'evidence/card_rotation.json').exists() else {'status':'PENDING AMENDMENT ROTATION'}
    if receipt['status']=='CARD ROTATION VERIFIED':
        assert sha(card)==receipt['card_after_sha256'] and receipt['archive_new_entry_readback'] and receipt['archive_old_bytes_read']==receipt['archive_previous_bytes_written']==0
        for n in [2,3]:
            part=raw[raw.index(('# БЛОК '+str(n)+' —').encode()):raw.index(('# БЛОК '+str(n+1)+' —').encode())]
            rows=[s for s in part.splitlines() if s.startswith(b'- **')];assert len(rows)==5 and sum(OUT.name.encode() in s for s in rows)==1
    put(A/'evidence/final_integrity.json',{'required_artifacts_present':True,'protected_files_unchanged':len(state['inputs']),'changed':changed,'archive_sha256':sha(archive),'external_source_tree_files_unchanged':1013,'local_and_upstream_pins_current':True,'card_rotation':receipt['status'],'block4_byte_identical':True,'block4_sha256':state['block4_sha256'],'old_archive_bytes_read_by_sealer':0,'can_apply':False,'can_start_tunnel':False,'native_runs':0,'dependency_downloads':0})
    paths=sorted([p for p in OUT.rglob('*') if p.is_file() and p!=OUT/'manifest.json']+[REPO/p for p in NEW])
    assert all(not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400 for p in paths)
    assert not [p for p in paths if p.suffix.lower() in ['.pyc','.pyo','.pyd','.log','.tmp','.temp'] or '__pycache__' in p.parts]
    rows=[{'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    put(OUT/'manifest.json',{'schema':1,'task':OUT.name,'amendment':1,'status':'PARTIAL / AWAITING INDEPENDENT VERIFICATION WEB_11','root':'M:/GitHub/ag_llm','self_excluded':True,'files':rows,'external_source_archive':{'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'publication':'EXTERNAL / NOT AUTOMATICALLY INCLUDED IN REPOSITORY','source_tree_ledger':'amendment_01/evidence/source_tree_manifest.json'},'active_card':{'path':card.relative_to(REPO).as_posix(),'bytes':card.stat().st_size,'sha256':sha(card)},'can_apply':False,'can_start_tunnel':False,'publication':'PROJECT REPORT LOCAL ONLY / USER HANDOFF','independent_acceptance':'NOT VERIFIED'})
    assert all((REPO/x['path']).stat().st_size==x['bytes'] and sha(REPO/x['path'])==x['sha256'] for x in load(OUT/'manifest.json')['files'])
    print(json.dumps({'manifest_files':len(rows),'protected_unchanged':len(state['inputs']),'external_source_files_unchanged':1013,'rotation':receipt['status'],'block4_unchanged':True,'manifest_sha256':sha(OUT/'manifest.json')}))
if __name__=='__main__':main()
