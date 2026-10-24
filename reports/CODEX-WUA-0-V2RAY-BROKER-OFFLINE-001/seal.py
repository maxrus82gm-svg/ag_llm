"""Seal this TASK and new broker files, never read a history archive."""
from pathlib import Path
import hashlib
import json
import sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1]
TASK=OUT.name;PKG=REPO/'integrations/wua_chatgpt_mcp'
NEW=['broker.py','broker_fixture.py','configs/broker.v1.schema.json','configs/broker.v1.synthetic.example.json','configs/v2ray.engine.disabled.contract.json','tests/broker_suite.py','tests/broker_regression.py']
REQUIRED=['report.md','README.md','engine_compatibility.md','strict_broker_topology.md','security_boundary.md','broker_test_results.json','manual_engineering_review.md','next_user_go.md','rotate_card.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    assert all((OUT/p).is_file() for p in REQUIRED)
    initial=load(OUT/'evidence/initial_state.json');changed=[]
    for path,expected in initial['inputs'].items():
        p=REPO/path
        if sha(p)!=expected['sha256'] or p.stat().st_size!=expected['bytes']:changed.append(path)
    assert not changed,changed
    facts=load(OUT/'broker_test_results.json');assert facts['final_suite']['collected']==facts['final_suite']['passed']==33
    pins=load(OUT/facts['final_suite_path']/'source_pins.json')
    assert all(sha(REPO/p)==v for p,v in pins.items())
    sensitive={'api_key','apikey','access_token','refresh_token','client_secret','password','private_key','channel_key','grant_key','wua_grant'}
    hits=[];parsed=0
    def walk(value,path):
        if type(value) is dict:
            for k,v in value.items():
                if k.lower() in sensitive and v not in [None,'',False,[],{}]:hits.append(path+'.'+k)
                walk(v,path+'.'+k)
        elif type(value) is list:
            for i,v in enumerate(value):walk(v,path+'['+str(i)+']')
    for p in OUT.rglob('*.json'):
        if p.name=='manifest.json':continue
        walk(load(p),p.relative_to(OUT).as_posix());parsed+=1
    assert not hits,hits # field names only; never print any secret value
    put(OUT/'evidence/privacy_check.json',{'method':'bounded JSON sensitive-field scan plus source/manual engineering review; not a general secret detector','json_files_parsed':parsed,'nonempty_sensitive_fields':hits,'synthetic_nonce_and_receipt_hmac_allowed':True,'real_credentials_supplied':False,'working_V2Ray_profiles_read':False})
    card=REPO/'Документация/000_Задачи Codex.md';raw=card.read_bytes();marker='# БЛОК 4 —'.encode();block4=raw[raw.index(marker):]
    assert hashlib.sha256(block4).hexdigest()==initial['block4_sha256']
    rotation_path=OUT/'evidence/card_rotation.json'
    rotation=load(rotation_path) if rotation_path.exists() else {'status':'PENDING FINAL ROTATION'}
    if rotation['status']=='CARD ROTATION VERIFIED':
        assert sha(card)==rotation['card_after_sha256']
        assert rotation['archive_old_bytes_read']==rotation['archive_previous_bytes_written']==0
        assert rotation['archive_new_entry_readback']
        assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in raw
        for n in [2,3]:
            chunk=raw[raw.index(('# БЛОК '+str(n)+' —').encode()):raw.index(('# БЛОК '+str(n+1)+' —').encode())]
            assert sum(x.startswith(b'- **') for x in chunk.splitlines())==5
    put(OUT/'evidence/final_integrity.json',{'task':TASK,'required_artifacts_present':True,'protected_files':len(initial['inputs']),'protected_unchanged':len(initial['inputs']),'changed':changed,'final_source_pins_current':True,'block4_byte_identical':True,'block4_sha256':initial['block4_sha256'],'card_rotation':rotation['status'],'archive_old_bytes_read_by_sealer':0,'new_package_files':NEW,'can_apply':False,'can_start_tunnel':False,'independent_acceptance':'NOT VERIFIED','publication':'LOCAL ONLY / USER HANDOFF'})
    paths=sorted([p for p in OUT.rglob('*') if p.is_file() and p!=OUT/'manifest.json']+[PKG/p for p in NEW])
    assert len(paths)==len(set(paths))
    assert all(not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400 for p in paths)
    rows=[{'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    ignored=[r['path'] for r in rows if Path(r['path']).suffix.lower() in ['.pyc','.pyo','.pyd','.log','.tmp','.temp'] or '__pycache__' in Path(r['path']).parts]
    assert not ignored,ignored
    manifest={'schema':1,'task':TASK,'self_excluded':True,'hash_algorithm':'SHA-256','root':'M:/GitHub/ag_llm','status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11','files':rows,'active_card':{'path':card.relative_to(REPO).as_posix(),'bytes':card.stat().st_size,'sha256':sha(card)},'protected_inputs_reference':'evidence/initial_state.json','archive':'Not read or hashed. Only new append range verified by rotate_card.py; receipt in evidence/card_rotation.json.','exclusions':['manifest.json itself'],'publication':'LOCAL ONLY / NOT VERIFIED','can_apply':False,'can_start_tunnel':False}
    put(OUT/'manifest.json',manifest)
    assert all((REPO/x['path']).stat().st_size==x['bytes'] and sha(REPO/x['path'])==x['sha256'] for x in load(OUT/'manifest.json')['files'])
    print(json.dumps({'manifest_files':len(rows),'protected_unchanged':len(initial['inputs']),'rotation':rotation['status'],'block4_unchanged':True,'manifest_sha256':sha(OUT/'manifest.json')}))
if __name__=='__main__':main()
