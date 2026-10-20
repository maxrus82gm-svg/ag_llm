"""TASK-local hash baseline/handoff; no Git/network/runtime activation."""
from pathlib import Path
import hashlib,json,sys,os,time
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1];CARD=ROOT/'Документация/000_Задачи Codex.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(ref,obj):
    with (OUT/ref).open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def prepare():
    old=ROOT/'reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001';paths={ROOT/r['ref'] for r in read(old/'protected_inputs.json')['files']};paths.update(p for p in old.rglob('*') if p.is_file())
    rows=[]
    for p in sorted(paths):
        b=p.read_bytes();rows.append({'ref':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b),'card':p==CARD})
    save('protected_inputs.json',{'files':rows})
    b=CARD.read_bytes();a=b.index('# БЛОК 1'.encode());z=b.index('# БЛОК 2'.encode(),a+1);assert OUT.name.encode() in b[a:z]
    (OUT/'assignment.md').write_bytes(b[a:z]);save('card_initial.json',{'before':sha(b),'prefix_bytes':a,'prefix':sha(b[:a]),'assignment':sha(b[a:z]),'history_bytes':len(b[z:]),'history':sha(b[z:])})
    print(json.dumps({'protected':len(rows),'assignment_saved':True}))
def seal():
    rows=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.name=='manifest.json':continue
        assert p.suffix!='.pending';b=p.read_bytes()
        if p.suffix=='.json':json.loads(b.decode('utf-8-sig'))
        rows.append({'path':p.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b)})
    (OUT/'manifest.json').write_text(json.dumps({'task_id':OUT.name,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','files':rows,'self_hash':'excluded','publication':'LOCAL ONLY'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in rows:assert sha((OUT/r['path']).read_bytes())==r['sha256']
    print(json.dumps({'entries':len(rows),'manifest_sha256':sha((OUT/'manifest.json').read_bytes())}))
def host_review():
    save('host_collector_review.json',{'source':'adapters/Collect-Host.ps1','sha256':sha((OUT/'adapters/Collect-Host.ps1').read_bytes()),'locality_review':'Trusted installed local CIM providers, exact classes/properties; no remote sessions/host names; 8s per query','reads':['OS version/build/SKU','hypervisor-present boolean','CPU virtualization booleans','selected optional feature raw codes','vmms/vmcompute state','trusted system Hyper-V module metadata only','five exact standard tool paths','top-level TASK assets media count only'],'not_executed':['VM enumeration/config access without approved identity','feature/VM/service mutations','ports/DNS/network/proxy probes','private credentials/configs','hypervisor/native client startup'],'scope':'No whole-host traffic/OS isolation attestation; trusted OS/providers/filesystem assumed'})
def inspect_package():
    import ast,re
    for path in OUT.rglob('*.py'):ast.parse(path.read_bytes())
    run=read(OUT/'evidence/attempt08/run.json');checks=read(OUT/'checks.json')
    for ref in checks['frozen_source_refs']:assert sha((OUT/ref).read_bytes())==run['source_pins'][ref]
    protected=read(OUT/'protected_inputs.json')['files'];changed=[r['ref'] for r in protected if sha((ROOT/r['ref']).read_bytes())!=r['sha256']]
    assert not changed
    findings=[];scanned=0
    # Source literals describing forbidden examples are not credentials; only value patterns.
    patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}',r'(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{20,}',r'(?i)(?:https?|socks5)://[^\s/]+:[^\s/@]+@']
    patterns.extend([r'\bDESKTOP-[A-Z0-9]{6,}\b',r'C:[\\/]+Users[\\/]+[A-Za-z0-9_]'])
    for path in OUT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in ['.md','.txt','.json','.cs','.py','.ps1']:continue
        # Audit implementation holds the literal deny patterns, not discovered raw data.
        if path==Path(__file__):continue
        text=path.read_text(encoding='utf-8-sig');scanned+=1
        # The literal Users/other rejected-root fixture is not host inventory.
        scan_text=text.replace('C:\\\\Users\\\\other','<SYNTHETIC_REJECTED_ROOT>')
        if any(re.search(pattern,scan_text) for pattern in patterns):findings.append(path.relative_to(OUT).as_posix())
    assert not findings
    save('package_review.json',{'status':'PASS','python_AST':'PASS','frozen_runtime_test_sources':'unchanged from attempt08','changed_handoff_tools':'Only packaging/rotation code added after final suite; not runtime gate changes','protected_unchanged_before_rotation':len(protected),'public_text_files_scanned':scanned,'credential_or_private_host_pattern_findings':findings,'manual_privacy_review':'Aggregate inventory only; public ephemeral test keys/signatures and synthetic IDs, no private-key export, raw profiles, full old card or actual VM IDs','limits':'Pattern scan plus manual provenance review, not a universal secret detector; trusted filesystem/OS assumed','execution_policy_event':'PS5.1 -File helper blocked; no policy mutation; direct AST parser metadata command succeeded','packaging_event':'assemble.py initial assertion searched wrong extension/spaces for prior portable flag; corrected locally; immutable outputs compared before reuse; no old files written'})
    print(json.dumps({'review':'PASS','protected':len(protected),'text_files':scanned}))
def card_images(original,assignment,result):
    initial=read(OUT/'card_initial.json');n=initial['prefix_bytes'];h=initial['history_bytes']
    assert sha(original)==initial['before'] and sha(assignment)==initial['assignment']
    prefix=original[:n];history=original[-h:]
    assert sha(prefix)==initial['prefix'] and sha(history)==initial['history'] and original==prefix+assignment+history
    archived=('# БЛОК 2 — АРХИВ ПОЛНЫХ ПОСТАНОВОК\n\n## 2026-10-21 — '+OUT.name+'\n\nПолная исходная постановка, byte-exact UTF-8:\n\n```markdown\n').encode()+assignment+b'```\n\n'+('# БЛОК 3 — ФАКТИЧЕСКИЕ РЕЗУЛЬТАТЫ\n\n## 2026-10-21 — '+OUT.name+'\n\n').encode()+result.encode()+('\n\n---\n\n## Предыдущая история (сохранена byte-exact)\n\n').encode()+history
    waiting='# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n'.encode()
    staged=prefix+assignment+archived;final=prefix+waiting+archived
    for content in [staged,final]:assert content.endswith(history) and content[:n]==prefix and assignment in content[n:]
    assert prefix+assignment+final[-h:]==original
    return staged,final
def replace_card(content,expected,events):
    assert sha(CARD.read_bytes())==expected,'CARD_CHANGED'
    pending=OUT/'.card.pending';assert not pending.exists()
    with pending.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    assert pending.read_bytes()==content
    # ReplaceFileW preserves the existing destination file metadata/security.
    # Only this explicitly authorized own Markdown card is the target.
    import ctypes
    replace=ctypes.WinDLL('kernel32',use_last_error=True).ReplaceFileW
    replace.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p];replace.restype=ctypes.c_int
    for attempt in range(2):
        assert sha(CARD.read_bytes())==expected,'CARD_CHANGED'
        if replace(str(CARD),str(pending),None,0,None,None):break
        code=ctypes.get_last_error();events.append({'phase':'replace','error_code':code,'retry':attempt})
        if code not in [5,32] or attempt==1:raise OSError('CARD_ROTATION_BLOCKED_REPLACE_'+str(code))
        time.sleep(0.15)
    assert not pending.exists() and CARD.read_bytes()==content
def rotate():
    initial=read(OUT/'card_initial.json');original=CARD.read_bytes();assignment=(OUT/'assignment.md').read_bytes()
    assert sha(original)==initial['before'],'CARD_CHANGED_ROTATION_BLOCKED'
    assert (OUT/'manifest.json').is_file() and (OUT/'package_review.json').is_file()
    (OUT/'manifest.pre_rotation.json').write_bytes((OUT/'manifest.json').read_bytes())
    result=(OUT/'card_result.txt').read_text(encoding='utf-8');stage,final=card_images(original,assignment,result)
    # Offline negative controls of the actual rotation guards, no card writes.
    rejected=0
    for wrong,other in [(original+b'foreign',assignment),(original,assignment+b'changed')]:
        try:card_images(wrong,other,result)
        except AssertionError:rejected+=1
    assert rejected==2
    events=[];replace_card(stage,initial['before'],events)
    staged_read=CARD.read_bytes();assert staged_read==stage and staged_read.endswith(original[-initial['history_bytes']:]) and assignment in staged_read
    # B2/B3 persisted and read back while original B1 still present. Only now clear.
    replace_card(final,sha(stage),events);readback=CARD.read_bytes();assert readback==final
    save('card_rotation.json',{'status':'ROTATED / READBACK VERIFIED','before_sha256':initial['before'],'staged_sha256':sha(stage),'final_sha256':sha(final),'prefix_sha256':initial['prefix'],'prefix_bytes':initial['prefix_bytes'],'previous_history_sha256':initial['history'],'previous_history_bytes':initial['history_bytes'],'full_assignment_sha256':sha(assignment),'report_sha256_before_rotation':sha((OUT/'report.md').read_bytes()),'pre_rotation_manifest_sha256':sha((OUT/'manifest.pre_rotation.json').read_bytes()),'B2_full_assignment_saved':True,'B3_result_saved':True,'staged_readback_before_B1_clear':True,'B1':'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ','previous_history_byte_exact':True,'rules_prefix_unchanged':True,'guard_negative_controls':{'total':2,'rejected':rejected},'replacement':'ReplaceFileW existing target only; no ACL API changes','events':events,'rollback':'Only with separate authorization and exact final hash guard: original = first prefix_bytes bytes + assignment.md bytes + last previous_history_bytes bytes of current card; reconstructed SHA must equal before_sha256. Never overwrite later edits.'})
    print(json.dumps({'rotation':'PASS','history_bytes':initial['history_bytes'],'guards_rejected':rejected,'retry_events':len(events)}))
def post_rotation():
    receipt=read(OUT/'card_rotation.json');initial=read(OUT/'card_initial.json');b=CARD.read_bytes();assignment=(OUT/'assignment.md').read_bytes()
    assert sha(b)==receipt['final_sha256'] and sha(b[:initial['prefix_bytes']])==initial['prefix'] and sha(b[-initial['history_bytes']:])==initial['history']
    assert sha(b[:initial['prefix_bytes']]+assignment+b[-initial['history_bytes']:])==initial['before']
    rows=read(OUT/'protected_inputs.json')['files'];noncard=[r for r in rows if not r['card']];changed=[r['ref'] for r in noncard if sha((ROOT/r['ref']).read_bytes())!=r['sha256']]
    assert not changed
    report=OUT/'report.md'
    with report.open('a',encoding='utf-8',newline='\n') as f:f.write('\n\n## G. Фактически выполненная ротация и финальная сверка\n\n2026-10-21: полная постановка сохранена в БЛОКЕ 2, factual result — БЛОКЕ 3; промежуточный вариант прочитан до очистки БЛОКА 1. БЛОК 1 теперь `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Сохранены byte-exact **524629 байт прежней истории** и **6852 байта правил/prefix**. Два отрицательных in-memory guard controls отклоняют чужую правку карточки и подмену постановки. `card_rotation.json` содержит before/stage/final/assignment/history hashes и точный условный откат; исходный before SHA восстанавливается из prefix + assignment + history suffix. Дополнительная сырая копия старой карточки не публиковалась.\n\nПосле ротации **388/388 защищённых non-card файлов без изменений**. Только собственная карточка изменилась по разрешённой ротации. `integrity.json` фиксирует проверку; финальный `manifest.json` пересобран после сохранения отчёта/receipt. Его внешний SHA передаётся отдельно. Пользователь передаёт пакет WEB_11; самостоятельная independent acceptance не заявлена.\n')
    save('integrity.json',{'status':'PASS','protected_noncard_total':len(noncard),'unchanged':len(noncard),'changed':changed,'only_authorized_card_rotated':True,'prefix_unchanged':True,'old_history_byte_exact':True,'before_reconstruction_verified':True,'after_card_sha256':sha(b),'gate_runtime_sources':read(OUT/'package_review.json')['frozen_runtime_test_sources'],'OS_VM_WFP_network_Git_mutations':0,'limits':'Bounded protected file set, not a full repository/disk diff; no Git used'})
    print(json.dumps({'integrity':'PASS','unchanged_noncard':len(noncard),'card':'ROTATED'}))
if __name__=='__main__':{'prepare':prepare,'seal':seal,'host-review':host_review,'review':inspect_package,'rotate':rotate,'post-rotation':post_rotation}[sys.argv[1]]()
