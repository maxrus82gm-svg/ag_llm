"""Bounded report integrity and manifest; never opens a history archive."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1]
NEW=['integrations/wua_chatgpt_mcp/engine_snapshot.py','integrations/wua_chatgpt_mcp/tests/engine_snapshot_suite.py']
REQUIRED=['report.md','engine_inventory.md','source_provenance.md','engine_capabilities.md','singbox_vs_v2ray.md','compatibility_gates.json','tests.md','manual_engineering_review.md','next_user_decision.md','checks.json','rotate_card.py']
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    assert all((OUT/p).is_file() for p in REQUIRED)
    initial=load(OUT/'evidence/initial_state.json');changed=[p for p,v in initial['inputs'].items() if sha(REPO/p)!=v['sha256'] or (REPO/p).stat().st_size!=v['bytes']];assert not changed,changed
    facts=load(OUT/'checks.json');assert facts['final_suite']['collected']==facts['final_suite']['passed']==44
    pins=load(OUT/facts['final_suite_path']/'source_pins.json');assert all(sha(REPO/p)==v for p,v in pins.items())
    raw=(REPO/'Документация/000_Задачи Codex.md').read_bytes();b4=raw[raw.index('# БЛОК 4 —'.encode()):];assert hashlib.sha256(b4).hexdigest()==initial['block4_sha256']
    receipt=load(OUT/'evidence/card_rotation.json') if (OUT/'evidence/card_rotation.json').exists() else {'status':'PENDING FINAL ROTATION'}
    if receipt['status']=='CARD ROTATION VERIFIED':
        assert hashlib.sha256(raw).hexdigest()==receipt['card_after_sha256']
        assert receipt['archive_old_bytes_read']==receipt['archive_previous_bytes_written']==0 and receipt['archive_new_entry_readback']
        assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in raw
        for n in [2,3]:
            part=raw[raw.index(('# БЛОК '+str(n)+' —').encode()):raw.index(('# БЛОК '+str(n+1)+' —').encode())]
            assert sum(x.startswith(b'- **') for x in part.splitlines())==5
    sensitive={'password','private_key','api_key','access_token','refresh_token','client_secret','channel_key','grant_key','wua_grant'};hits=[]
    def walk(v,path):
        if type(v) is dict:
            for k,w in v.items():
                if k.lower() in sensitive and w not in [None,'',False,[],{}]:hits.append(path+'.'+k)
                walk(w,path+'.'+k)
        elif type(v) is list:
            for i,w in enumerate(v):walk(w,path+'['+str(i)+']')
    for p in OUT.rglob('*.json'):
        if p.name!='manifest.json':walk(load(p),p.relative_to(OUT).as_posix())
    assert not hits,hits
    put(OUT/'evidence/privacy_check.json',{'method':'bounded JSON sensitive-field scan plus manual review; not an exhaustive secret detector','nonempty_sensitive_fields':hits,'binary_path_redacted':True,'raw_config_commandline_environment_or_process_memory_exported':False,'raw_binary_or_dependency_dump_copied':False})
    put(OUT/'evidence/final_integrity.json',{'required_artifacts_present':True,'protected_files':len(initial['inputs']),'protected_unchanged':len(initial['inputs']),'changed':changed,'final_source_pins_current':True,'block4_byte_identical':True,'block4_sha256':initial['block4_sha256'],'card_rotation':receipt['status'],'old_archive_bytes_read_by_sealer':0,'can_apply':False,'can_start_tunnel':False,'independent_acceptance':'NOT VERIFIED'})
    paths=sorted([p for p in OUT.rglob('*') if p.is_file() and p!=OUT/'manifest.json']+[REPO/p for p in NEW])
    assert all(not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&0x400 for p in paths)
    assert not [p for p in paths if p.suffix.lower() in ['.log','.tmp','.temp','.pyc','.pyo','.pyd'] or '__pycache__' in p.parts]
    rows=[{'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    card=REPO/'Документация/000_Задачи Codex.md'
    put(OUT/'manifest.json',{'schema':1,'task':OUT.name,'self_excluded':True,'root':'M:/GitHub/ag_llm','files':rows,'active_card':{'path':card.relative_to(REPO).as_posix(),'bytes':card.stat().st_size,'sha256':sha(card)},'protected_inputs_reference':'evidence/initial_state.json','archive':'Never hashed/read by sealer; new append range only verified by rotate_card.py.','can_apply':False,'can_start_tunnel':False,'publication':'LOCAL ONLY / USER HANDOFF','independent_acceptance':'NOT VERIFIED'})
    assert all((REPO/x['path']).stat().st_size==x['bytes'] and sha(REPO/x['path'])==x['sha256'] for x in load(OUT/'manifest.json')['files'])
    print(json.dumps({'manifest_files':len(rows),'protected_unchanged':len(initial['inputs']),'rotation':receipt['status'],'block4_unchanged':True,'manifest_sha256':sha(OUT/'manifest.json')}))
if __name__=='__main__':main()
