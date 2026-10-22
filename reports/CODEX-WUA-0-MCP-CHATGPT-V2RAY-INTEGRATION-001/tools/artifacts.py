"""TASK artifacts and bounded input baseline; no Git/network or activation."""
from pathlib import Path
import ast,hashlib,json,os,re,sys,time
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1];PKG=ROOT/'integrations/wua_chatgpt_mcp';CARD=ROOT/'Документация/000_Задачи Codex.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(ref,obj):
    p=OUT/ref;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def prepare():
    assert not PKG.exists(),'PACKAGE_SCOPE_CONFLICT';PKG.mkdir(parents=True)
    prev=ROOT/'reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001'
    paths={ROOT/r['ref'] for r in load(prev/'protected_inputs.json')['files']};paths.update(p for p in prev.rglob('*') if p.is_file())
    paths.update((ROOT/'web_alarm').glob('*.py'));paths.update(p for p in (ROOT/'reports/CODEX-WUA-0-MCP-FEASIBILITY-001').rglob('*') if p.is_file())
    paths.update([ROOT/'Документация/37_Старт перехода - Web Alarm Ultra.md',ROOT/'Документация/11_Мультимодельная архитектура и назначение LLM.md',ROOT/'.gitignore'])
    save('protected_inputs.json',{'files':[{'ref':p.relative_to(ROOT).as_posix(),'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes()),'card':p==CARD} for p in sorted(paths)]})
    b=CARD.read_bytes();a=b.index('# БЛОК 1'.encode());z=b.index('# БЛОК 2'.encode(),a+1);assert OUT.name.encode() in b[a:z]
    (OUT/'assignment.md').write_bytes(b[a:z]);save('card_initial.json',{'before':sha(b),'prefix_bytes':a,'prefix':sha(b[:a]),'assignment':sha(b[a:z]),'history_bytes':len(b[z:]),'history':sha(b[z:])})
    print(json.dumps({'prepared':True,'protected_files':len(paths),'package_new':True}))
def package_files():return sorted([p for base in [PKG,OUT] for p in base.rglob('*') if p.is_file()])
def protected(card_expected=None):
    rows=load(OUT/'protected_inputs.json')['files'];changed=[]
    for r in rows:
        expected=card_expected if r['card'] and card_expected else r['sha256']
        if sha((ROOT/r['ref']).read_bytes())!=expected:changed.append(r['ref'])
    return rows,changed
def review():
    runs={name:load(OUT/'runs'/name/'run_meta.json') for name in ['mcp06','security03','mutant_route02','mutant_owner02']}
    assert runs['mcp06']['counts']=={'total':63,'passed':63,'failed':0}
    assert runs['security03']['counts']=={'total':24,'passed':24,'failed':0,'errors':0}
    current={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in PKG.rglob('*') if p.is_file()}
    for r in runs.values():assert r['sources_before']==current and r['sources_unchanged']
    for name in ['mutant_route02','mutant_owner02']:assert runs[name]['mutant_killed'] and runs[name]['counts']=={'total':1,'passed':0,'failed':1,'errors':0}
    assert load(OUT/'runtime_compatibility.json')['candidate_single_edge_conflict']
    assert not load(OUT/'diagnostic_cli.json')['can_apply'] and not load(OUT/'diagnostic_cli.json')['can_start_tunnel']
    assert not list(OUT.rglob('bootstrap.json')) and not list(OUT.rglob('*.pending'))
    for p in package_files():
        if p.suffix=='.py':ast.parse(p.read_bytes())
        if p.suffix=='.json':load(p)
    rows,changed=protected();assert not changed,'PROTECTED_INPUT_DRIFT'
    core=ROOT/'reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/source/Core.cs';portable=ROOT/'reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/toolkit/WuaMcp.psm1'
    assert 'public static bool CanApply{get{return false;}}' in core.read_text(encoding='utf-8-sig') and '$script:BackendImplemented = $false' in portable.read_text(encoding='utf-8-sig')
    patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}',r'(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{20,}',r'(?i)(?:https?|socks5)://[^\s/]+:[^\s/@]+@',r'C:[\\/]+Users[\\/]+[A-Za-z0-9_]',r'\bDESKTOP-[A-Z0-9]{6,}\b']
    findings=[];text_count=0
    for p in package_files():
        if p==Path(__file__) or p.suffix not in ['.py','.json','.md','.txt','.yaml']:continue
        text=p.read_text(encoding='utf-8-sig');text_count+=1
        if any(re.search(pattern,text) for pattern in patterns):findings.append(p.relative_to(ROOT).as_posix())
        if p.suffix=='.json':
            def walk(x):
                if isinstance(x,dict):
                    assert 'channel_key' not in x,'EPHEMERAL_KEY_LEFT_IN_PUBLIC_JSON'
                    for v in x.values():walk(v)
                elif isinstance(x,list):
                    for v in x:walk(v)
            walk(load(p))
    assert not findings,'PUBLICATION_REDACTION_REQUIRED:'+','.join(findings)
    states=['LOCAL_MCP_INTEGRATION_VERIFIED','STRICT_ROUTE_SYNTHETIC_TESTED','TWO_WINDOWS_IDENTITIES_NOT_PROVISIONED','OS_WFP_EGRESS_NOT_VERIFIED','V2RAY_LIVE_ROUTE_NOT_VERIFIED','SECURE_TUNNEL_NOT_ACTIVATED','ORDINARY_CHATGPT_E2E_NOT_VERIFIED','HOSTED_TUNNEL_ON_HOLD_BY_USER']
    save('checks.json',{'task_id':OUT.name,'result':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','states':states,'MCP_named_checks':runs['mcp06']['counts'],'security_unittest_methods':runs['security03']['counts'],'targeted_mutants_killed':2,'each_mutant':{'total':1,'expected_fail':1,'errors':0},'source_pins':current,'protected_total_unchanged_before_card_rotation':len(rows),'protected_noncard_expected':sum(not r['card'] for r in rows),'old_barriers':{'portable_BackendImplemented':False,'WFP_CanApply':False,'old_modules_or_native_executions':0},'runtime_blocker':'Actual Python Proactor dynamic TCP selfpipe differs from reserved P; not native WFP verdict','real_actions':{'Windows_account_mutations':0,'WFP_Firewall_BFE_mutations':0,'system_ACL_rights_services_mutations':0,'V2Ray_or_working_network_changes':0,'VM_HyperV_changes':0,'native_tunnel_Cloudflared_executions':0,'external_OpenAI_or_model_API_requests':0,'API_keys_or_tunnels_created':0,'Git_GitHub_operations':0,'messages_to_other_chats':0},'network_scope':'Own literal IPv4 loopback fixtures, STDIO and own runtime compatibility probe only; Python observer is not whole-host/native containment','publication_review':{'text_files':text_count,'pattern_findings':findings,'ephemeral_bootstrap_files_remaining':0,'channel_keys_in_JSON':0,'scope':'Pattern scan plus manual source/provenance review; not a universal secret detector'},'original_failures':['runs/mcp01/result.json','runs/mcp02/result.json'],'native_and_ordinary_chat_tests':'NOT RUN / BLOCKED','independent_WEB_11_verdict':'PENDING'})
    print(json.dumps({'review':'PASS','protected':len(rows),'source_files':len(current),'public_text_files':text_count}))
def seal():
    rows=[]
    for p in package_files():
        if p==OUT/'manifest.json':continue
        assert p.suffix not in ['.pending','.pyc']
        b=p.read_bytes();rows.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)})
    (OUT/'manifest.json').write_text(json.dumps({'task_id':OUT.name,'scope_root':'repository root; both authorized new directories','status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','files':rows,'self_hash':'excluded; external digest in handoff','card':'Current canonical own card not copied; before/stage/final hashes and guarded reconstruction in card_rotation.json','publication':'LOCAL ONLY; no Git/GitHub used'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in rows:
        b=(ROOT/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    print(json.dumps({'entries':len(rows),'manifest_sha256':sha((OUT/'manifest.json').read_bytes())}))
def images(original,assignment,result):
    first=load(OUT/'card_initial.json');n=first['prefix_bytes'];h=first['history_bytes'];prefix=original[:n];history=original[-h:]
    assert sha(original)==first['before'] and sha(prefix)==first['prefix'] and sha(history)==first['history'] and sha(assignment)==first['assignment']
    assert original==prefix+assignment+history
    tail=('# БЛОК 2 — АРХИВ ПОЛНЫХ ПОСТАНОВОК\n\n## 2026-10-21 — '+OUT.name+'\n\nПолная постановка byte-exact UTF-8:\n\n```markdown\n').encode()+assignment+b'```\n\n'+('# БЛОК 3 — ФАКТИЧЕСКИЕ РЕЗУЛЬТАТЫ\n\n## 2026-10-21 — '+OUT.name+'\n\n').encode()+result.encode()+('\n\n---\n\n## Предыдущая история (byte-exact)\n\n').encode()+history
    stage=prefix+assignment+tail;final=prefix+'# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n'.encode()+tail
    assert assignment in final and final.endswith(history) and sha(prefix+assignment+final[-h:])==first['before']
    return stage,final
def replace_card(data,expected,events):
    assert sha(CARD.read_bytes())==expected,'CARD_CHANGED'
    pending=OUT/'.card.pending';assert not pending.exists()
    with pending.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    assert pending.read_bytes()==data
    import ctypes
    fn=ctypes.WinDLL('kernel32',use_last_error=True).ReplaceFileW;fn.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p];fn.restype=ctypes.c_int
    for attempt in range(2):
        assert sha(CARD.read_bytes())==expected,'CARD_CHANGED'
        if fn(str(CARD),str(pending),None,0,None,None):break
        err=ctypes.get_last_error();events.append({'error':err,'retry':attempt})
        if err not in [5,32] or attempt==1:raise OSError('CARD_ROTATION_BLOCKED_'+str(err))
        time.sleep(.15)
    assert not pending.exists() and CARD.read_bytes()==data
def rotate():
    first=load(OUT/'card_initial.json');original=CARD.read_bytes();assignment=(OUT/'assignment.md').read_bytes();assert sha(original)==first['before'],'CARD_ROTATION_BLOCKED_DRIFT'
    assert (OUT/'report.md').is_file() and (OUT/'checks.json').is_file() and (OUT/'manifest.json').is_file()
    with (OUT/'manifest.pre_rotation.json').open('xb') as f:f.write((OUT/'manifest.json').read_bytes())
    result=(OUT/'card_result.txt').read_text(encoding='utf-8');stage,final=images(original,assignment,result);negative=0
    for b,a in [(original+b'foreign',assignment),(original,assignment+b'changed')]:
        try:images(b,a,result)
        except AssertionError:negative+=1
    assert negative==2
    events=[];replace_card(stage,first['before'],events);assert CARD.read_bytes()==stage and stage.endswith(original[-first['history_bytes']:]) and assignment in stage
    replace_card(final,sha(stage),events)
    save('card_rotation.json',{'status':'ROTATED / READBACK VERIFIED','before_sha256':first['before'],'stage_sha256':sha(stage),'final_sha256':sha(final),'prefix_bytes':first['prefix_bytes'],'prefix_sha256':first['prefix'],'previous_history_bytes':first['history_bytes'],'previous_history_sha256':first['history'],'full_assignment_sha256':sha(assignment),'B2_full_assignment_saved':True,'B3_factual_result_saved':True,'readback_before_B1_clear':True,'B1':'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ','old_history_byte_exact':True,'rules_prefix_unchanged':True,'guard_controls':{'total':2,'rejected':negative},'pre_rotation_manifest_sha256':sha((OUT/'manifest.pre_rotation.json').read_bytes()),'report_before_rotation_sha256':sha((OUT/'report.md').read_bytes()),'replacement':'ReplaceFileW existing own card; preserves existing destination metadata, no ACL policy changes','events':events,'rollback':'Only after separate authorization and exact final hash guard: original = current first prefix_bytes + assignment.md + current last previous_history_bytes; reconstructed SHA must equal before_sha256. Never overwrite later edits.'})
    print(json.dumps({'rotation':'PASS','history_bytes':first['history_bytes'],'negative_guards':negative,'retries':len(events)}))
def post():
    first=load(OUT/'card_initial.json');r=load(OUT/'card_rotation.json');b=CARD.read_bytes();assignment=(OUT/'assignment.md').read_bytes()
    assert sha(b)==r['final_sha256'] and sha(b[:first['prefix_bytes']])==first['prefix'] and sha(b[-first['history_bytes']:])==first['history']
    assert sha(b[:first['prefix_bytes']]+assignment+b[-first['history_bytes']:])==first['before']
    rows,changed=protected(r['final_sha256']);assert not changed,'POST_ROTATION_INPUT_DRIFT';count=sum(not row['card'] for row in rows)
    with (OUT/'report.md').open('a',encoding='utf-8',newline='\n') as f:
        f.write('\n\n## 7. Фактическая ротация и финальная целостность\n\nПолная постановка B2 и factual result B3 записаны и прочитаны до очистки B1; теперь B1=`ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Сохранены byte-exact '+str(first['history_bytes'])+' байт старой истории и '+str(first['prefix_bytes'])+' байт правил/prefix. Два in-memory negative controls отклоняют чужую правку карточки и подмену постановки. Conditional exact rollback проверен реконструкцией before SHA из prefix+assignment+history suffix. Сырая старая карточка в публикационную папку не копировалась; pending отсутствует.\n\nПосле ротации '+str(count)+'/'+str(count)+' protected non-card files неизменны; вне новых package/report scope изменена только разрешённая собственная карточка. `card_rotation.json`/`integrity.json` содержат hashes/readback/guards; финальный manifest включает оба новых каталога и все evidence кроме собственного self-hash. Независимая приёмка WEB_11 и публикация остаются pending.\n')
    save('integrity.json',{'status':'PASS','protected_total':len(rows),'noncard_total':count,'noncard_unchanged':count,'changed':changed,'only_own_card_rotated':True,'rules_prefix_byte_exact':True,'history_byte_exact':True,'before_reconstruction_verified':True,'card_final_sha256':sha(b),'package_source_pins':'checks.json, match all four final runs','limits':'Bounded selected files and own scopes, not a Git/full-disk diff or whole-host write monitor'})
    print(json.dumps({'integrity':'PASS','noncard_unchanged':count,'card':'ROTATED'}))
if __name__=='__main__':{'prepare':prepare,'review':review,'seal':seal,'rotate':rotate,'post':post}[sys.argv[1]]()
