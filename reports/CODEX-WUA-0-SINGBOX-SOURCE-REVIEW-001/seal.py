"""Integrity for the explicit no-bundle fallback; never read an archive."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1]
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    required=['report.md','source_bundle_provenance.md','manual_engineering_review.md','next_user_decision.md','test_results.json','evidence/bundle_request.json','rotate_card.py']
    assert all((OUT/p).is_file() for p in required)
    assert not (OUT/'source/sing-box-v1.13.4.tar.gz').exists(),'SOURCE_INPUT_NOW_AVAILABLE_REASSESS_BLOCKER'
    initial=load(OUT/'evidence/initial_state.json');changed=[p for p,v in initial['inputs'].items() if sha(REPO/p)!=v['sha256'] or (REPO/p).stat().st_size!=v['bytes']];assert not changed,changed
    facts=load(OUT/'test_results.json');reg=facts['existing_pure_validator_regression'];assert reg['collected']==reg['passed']==19 and reg['failed']==reg['errors']==reg['skipped']==0
    assert facts['source_specific_tests']['collected']==facts['source_route_mutations']['executed']==0
    pins=load(OUT/facts['run']/'source_pins.json');assert all(sha(REPO/p)==v for p,v in pins.items())
    raw=(REPO/'Документация/000_Задачи Codex.md').read_bytes();b4=raw[raw.index('# БЛОК 4 —'.encode()):];assert hashlib.sha256(b4).hexdigest()==initial['block4_sha256']
    receipt=load(OUT/'evidence/card_rotation.json') if (OUT/'evidence/card_rotation.json').exists() else {'status':'PENDING FINAL ROTATION'}
    if receipt['status']=='CARD ROTATION VERIFIED':
        assert hashlib.sha256(raw).hexdigest()==receipt['card_after_sha256'] and receipt['archive_new_entry_readback']
        assert receipt['archive_old_bytes_read']==receipt['archive_previous_bytes_written']==0
        assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in raw
        for n in [2,3]:
            chunk=raw[raw.index(('# БЛОК '+str(n)+' —').encode()):raw.index(('# БЛОК '+str(n+1)+' —').encode())]
            assert sum(s.startswith(b'- **') for s in chunk.splitlines())==5
    sensitive={'password','private_key','api_key','access_token','refresh_token','client_secret','channel_key','grant_key','wua_grant'};hits=[]
    def walk(v,path):
        if type(v) is dict:
            for k,x in v.items():
                if k.lower() in sensitive and x not in [None,'',False,[],{}]:hits.append(path+'.'+k)
                walk(x,path+'.'+k)
        elif type(v) is list:
            for i,x in enumerate(v):walk(x,path+'['+str(i)+']')
    for p in OUT.rglob('*.json'):
        if p.name!='manifest.json':walk(load(p),p.relative_to(OUT).as_posix())
    assert not hits,hits
    put(OUT/'evidence/final_integrity.json',{'status':'BLOCKED / SOURCE_BUNDLE_REQUIRED','protected_files':len(initial['inputs']),'protected_unchanged':len(initial['inputs']),'changed':changed,'source_pins_current':True,'source_files_read':0,'source_tests_and_mutations_executed':0,'nonempty_sensitive_JSON_fields':hits,'card_rotation':receipt['status'],'block4_byte_identical':True,'block4_sha256':initial['block4_sha256'],'archive_old_bytes_read_by_sealer':0,'can_apply':False,'can_start_tunnel':False})
    paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p!=OUT/'manifest.json')
    assert all(not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400 for p in paths)
    assert not [p for p in paths if p.suffix.lower() in ['.pyc','.pyo','.pyd','.log','.tmp','.temp'] or '__pycache__' in p.parts]
    rows=[{'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    card=REPO/'Документация/000_Задачи Codex.md'
    put(OUT/'manifest.json',{'schema':1,'task':OUT.name,'status':'BLOCKED / SOURCE_BUNDLE_REQUIRED','root':'M:/GitHub/ag_llm','self_excluded':True,'files':rows,'active_card':{'path':card.relative_to(REPO).as_posix(),'bytes':card.stat().st_size,'sha256':sha(card)},'protected_inputs_reference':'evidence/initial_state.json','archive':'Never read or hashed by sealer. Only new append bytes checked by rotate_card.py.','can_apply':False,'can_start_tunnel':False,'independent_review':'NOT VERIFIED','publication':'LOCAL ONLY / USER HANDOFF'})
    assert all((REPO/x['path']).stat().st_size==x['bytes'] and sha(REPO/x['path'])==x['sha256'] for x in load(OUT/'manifest.json')['files'])
    print(json.dumps({'manifest_files':len(rows),'protected_unchanged':len(initial['inputs']),'rotation':receipt['status'],'block4_unchanged':True,'manifest_sha256':sha(OUT/'manifest.json')}))
if __name__=='__main__':main()
