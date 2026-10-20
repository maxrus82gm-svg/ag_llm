"""TASK-local metadata, manifest and guarded own-card handoff. No network/Git."""
from pathlib import Path
import hashlib,json,sys,os,time
OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
CARD=ROOT/'Документация/000_Задачи Codex.md'
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(ref,obj):
    with (OUT/ref).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def prepare():
    previous=ROOT/'reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001'
    paths={ROOT/r['ref'] for r in load(previous/'protected_inputs.json')['files']}
    paths.update(p for p in previous.rglob('*') if p.is_file())
    paths.add(ROOT/'Документация/000_Задачи Claude.md')
    rows=[]
    for p in sorted(paths):
        b=p.read_bytes();rows.append({'ref':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b),'authorized_card':p==CARD})
    save('protected_inputs.json',{'files':rows,'external_configs_not_read':True})
    b=CARD.read_bytes();a=b.index('# БЛОК 1'.encode());z=b.index('# БЛОК 2'.encode(),a+1)
    assert OUT.name.encode() in b[a:z]
    (OUT/'assignment.md').write_bytes(b[a:z])
    save('card_initial.json',{'before_sha256':sha(b),'prefix_bytes':a,'prefix_sha256':sha(b[:a]),'assignment_sha256':sha(b[a:z]),'history_bytes':len(b[z:]),'history_sha256':sha(b[z:])})
    print(json.dumps({'protected':len(rows),'assignment_saved':True,'raw_card_copy':False}))
def integrity():
    rows=[]
    for row in load(OUT/'protected_inputs.json')['files']:
        h=sha((ROOT/row['ref']).read_bytes());rows.append({**row,'final_sha256':h,'unchanged':h==row['sha256']})
    other=[r for r in rows if not r['authorized_card']]
    assert all(r['unchanged'] for r in other),'Protected input drift; do not overwrite'
    save('integrity.json',{'noncard_unchanged':len(other),'files':rows})
    print(json.dumps({'noncard_unchanged':len(other)}))
def seal():
    rows=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.name=='manifest.json':continue
        assert p.suffix!='.pending','Unresolved card staging'
        b=p.read_bytes()
        if p.suffix=='.json':json.loads(b.decode('utf-8-sig'))
        rows.append({'path':p.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b)})
    (OUT/'manifest.json').write_text(json.dumps({'task_id':OUT.name,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','files':rows,'self_hash':'excluded','publication':'LOCAL ONLY / NOT VERIFIED'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in rows:assert sha((OUT/r['path']).read_bytes())==r['sha256']
    print(json.dumps({'entries':len(rows),'manifest_sha256':sha((OUT/'manifest.json').read_bytes())}))
def rotate():
    assert not (OUT/'card_rotation.json').exists(),'Rotation already attempted; reconcile receipt'
    initial=load(OUT/'card_initial.json');before=CARD.read_bytes();assert sha(before)==initial['before_sha256'],'Own card drift'
    a=initial['prefix_bytes'];assignment=(OUT/'assignment.md').read_bytes();prefix=before[:a];history=before[-initial['history_bytes']:]
    assert prefix+assignment+history==before and sha(history)==initial['history_sha256']
    checks=load(OUT/'checks_final.json');assert checks['final_managed_suite']['passed']==62
    for r in load(OUT/'protected_inputs.json')['files']:
        if not r['authorized_card']:assert sha((ROOT/r['ref']).read_bytes())==r['sha256'],'Protected input drift'
    report=(OUT/'report.md').read_bytes();pre_manifest=(OUT/'manifest.json').read_bytes()
    for r in json.loads(pre_manifest)['files']:
        b=(OUT/r['path']).read_bytes();assert sha(b)==r['sha256'] and len(b)==r['bytes'],'Stale premanifest'
    b2=('# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА\n\n## '+OUT.name+' / 2026-10-20\n\nПолный исходный БЛОК 1 ниже сохранён без изменения байтов. Дополнительных AMENDMENT к постановке нет.\n\n').encode()
    b3=f'''\n# БЛОК 3 — FACTUAL RESULT / HANDOFF

## {OUT.name} / Codex 007 / 2026-10-20

RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_11).
Prepared and built typed policy/managed ABI/readback/native source candidate.
Core/Abi/OfflineTests have zero P/Invoke; separate internal NativePreview DLL
has 15 Fwpm declarations, no exported types/entrypoint/runtime reference.
Native metadata inspected reflection-only; actual WFP calls 0. CanApply=false.

Final source-pinned managed tests 62/62 PASS, 0 FAIL (attempt05). One finite
oracle matrix 73,728 points, not Windows tests. Seven behavior mutants killed.
Compiled port-readback mutant: 61 PASS / 1 EXPECTED FAIL (mutant_port04),
exact regression trigger; negative red evidence preserved. Four managed
outputs built, zero compile errors/warnings; 22 independent SDK C++ static
assertions (/Zs only). Three SDK versions, 9 primary header hashes, 6 GUIDs,
15 prototypes. Previous toolkit 3 pure gates PASS, Apply/Rollback still BLOCKED;
its Install/Uninstall/collector not invoked and prior files untouched.
PS5.1 new guard AST 1/1, 0 errors; runtime suite not run. Initial shell-selector
parse actually ran on PS7 and was not credited as PS5 evidence. No Bypass/
Unblock/ExecutionPolicy/elevation. Final compiler env allowlisted, no inherited
CL/_CL_/CSC or proxy/API credentials. No product test FAIL/compile ERROR;
44->55->58->61->62 historical suites retained, not cumulative native proof.

NATIVE WFP ENFORCEMENT NOT RUN / NOT VERIFIED. REAL HOST SECURITY / V2RAY
REMOTE ROUTE / ORDINARY CHAT MCP E2E NOT VERIFIED; HOSTED TUNNEL NOT STARTED.
Install/live rollback BLOCKED. Native stage/readback compiled but never called;
native delete remains blocked, trusted lineage/ACL/effective graph/loopback/
children/DNS/BFE/boot/flow/quiescence gates open. Source visibility is not a
sandbox against deliberate reflection/admin execution. No real accounts,
rights/ACL/WFP/firewall/V2Ray/network mutations, native subjects or Git/GitHub.

Artifacts: reports/{OUT.name}/
report.md, manifest.json, checks_final.json, source/, native/, contracts/,
evidence/attempt05/, evidence/mutant_port04/, evidence/previous_toolkit_guard.json,
evidence/ps51_syntax_actual.json, security_boundary.md, lab_gate.md,
integration_plan.md, manual_engineering_review.md, privacy_review.json,
card_rotation.json, integrity.json, factual_result.txt.

DOC IMPACT: own TASK directory + own-card rotation only. Protected baseline:
298 project files, 297 noncard checked unchanged before rotation. Other
cards/old toolkit/shared docs/Claude/LLM12/production untouched. Full old
history and own rules prefix byte-exact; report/evidence/manifest saved before
B2/B3 readback, only then B1 WAITING. No raw historic card copied to bundle.
SHARED DOC DELTA for 19/34 is proposal in report only. Source pin from TASK
not Git-verified; publication/independent acceptance pending. User forwards
result to WEB_11. NEXT: independent review then separately authorized proven
isolated Windows lab + reviewed adapter, not live activation on working host.

---

## Архив прежних БЛОКОВ 2–3 — исходные байты сохранены

'''.encode()
    tail=b2+assignment+b3+history;stage=prefix+assignment+tail
    waiting='# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n'.encode();final=prefix+waiting+tail
    pending=OUT/'.card.pending';assert not pending.exists() and pending.resolve().parent==OUT.resolve();events=[]
    def replace(expected,desired,phase):
        assert CARD.read_bytes()==expected,'Card drift before replace'
        with pending.open('xb') as f:f.write(desired);f.flush();os.fsync(f.fileno())
        for attempt in range(2):
            assert CARD.read_bytes()==expected and pending.read_bytes()==desired,'Concurrent change'
            try:os.replace(pending,CARD);break
            except PermissionError as e:
                events.append({'phase':phase,'attempt':attempt+1,'class':type(e).__name__,'winerror':e.winerror})
                if attempt==1:raise
                time.sleep(0.15)
        assert CARD.read_bytes()==desired,'Card readback mismatch'
    try:
        replace(before,stage,'save_B2_B3');assert CARD.read_bytes().endswith(history)
        replace(stage,final,'clear_B1_after_readback');assert CARD.read_bytes()==final
    except Exception as e:
        current=CARD.read_bytes()
        if pending.exists() and current in (before,stage,final):
            assert current.endswith(history) and pending.read_bytes() in (stage,final)
            pending.unlink() # exact verified owned staging file only, never recursive
        save('card_rotation.json',{'status':'CARD ROTATION BLOCKED','error_class':type(e).__name__,'current_sha256':sha(current),'history_preserved':current.endswith(history),'events':events})
        raise
    save('card_rotation.json',{'status':'CARD ROTATION SAVED / B1 WAITING','before_sha256':sha(before),'stage_sha256':sha(stage),'final_sha256':sha(final),'prefix_bytes':len(prefix),'prefix_sha256':sha(prefix),'assignment_sha256':sha(assignment),'old_history_bytes':len(history),'old_history_sha256':sha(history),'B2_B3_readback_before_B1_clear':True,'B1_waiting':True,'old_history_preserved':True,'report_before_rotation_sha256':sha(report),'premanifest_sha256':sha(pre_manifest),'retry_events':events,'rollback':'With separate authorization and matching final SHA only: reconstruct unchanged prefix + assignment.md + exact old-history suffix; verify before SHA before replacing. Stop on drift.'})
    print(json.dumps({'rotation':'SAVED / B1 WAITING','history_bytes':len(history),'events':events}))
def finalize():
    receipt=load(OUT/'card_rotation.json');initial=load(OUT/'card_initial.json');data=CARD.read_bytes()
    assert sha(data)==receipt['final_sha256'],'Card drift after rotation'
    prefix=data[:receipt['prefix_bytes']];history=data[-receipt['old_history_bytes']:];assignment=(OUT/'assignment.md').read_bytes()
    assert sha(prefix)==initial['prefix_sha256'] and sha(history)==initial['history_sha256']
    assert sha(prefix+assignment+history)==initial['before_sha256'],'Before reconstruction failed'
    active=data[len(prefix):data.index('# БЛОК 2'.encode(),len(prefix))]
    assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in active and OUT.name.encode() not in active
    assert load(OUT/'integrity.json')['noncard_unchanged']==297
    save('handoff_verification.json',{'B1_waiting':True,'B2_full_assignment_saved':True,'old_history_bytes':len(history),'old_history_byte_exact':True,'before_card_reconstructs_exactly':True,'final_card_sha256':sha(data),'noncard_unchanged':297,'independent_acceptance':'PENDING WEB_11'})
    text=f'''\n## Фактический итог ротации и локальной сохранности

`card_rotation.json` / independent readback `handoff_verification.json`:
БЛОК 2 содержит полную постановку, БЛОК 3 factual result; только после их
readback БЛОК 1 стал **ОЖИДАНИЕ НОВОЙ ЗАДАЧИ**. Все **{len(history):,} bytes**
прежней истории и rules prefix byte-exact. Реконструкция prefix + assignment +
history suffix совпала с первоначальным SHA. Raw historic card copy не создана.
Recorded file-replace retry events: **{len(receipt['retry_events'])}**; сохраняются
коды/фазы без raw paths. Никаких permission overrides или остановки приложений.

`integrity.json`: **297/297 protected noncard файлов неизменны**; own card —
единственное разрешённое изменение baseline. Финальные source pins/runtime
numbers — `checks_final.json`; список всего пакета/размеры/SHA — `manifest.json`.
Receipt связывает **предротационные** report/manifest hashes; final manifest
пересоздан после добавления closing evidence, это разные контрольные снимки.
Privacy pattern/manual review — `privacy_review.json`; исходные старые files не
перезаписывались. Git/global excludes/index/publication/independent acceptance
не проверялись. Root ignore patterns не исключают текущие отчёты/source/evidence.
'''
    report=OUT/'report.md';old=report.read_text(encoding='utf-8');assert '## Фактический итог ротации' not in old
    report.write_text(old+text,encoding='utf-8',newline='\n')
    factual=f'''TASK: {OUT.name}
RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_11).
Готовы исходники typed policy, managed ABI/readback и отдельный неактивный Fwpm preview.
Build: 4 managed outputs, 0 errors/warnings; 22 SDK C++ static assertions PASS.
Offline tests: 62/62 PASS; 73 728 model points; 7 behavior mutants killed.
Compiled readback mutant: 61 PASS / 1 EXPECTED FAIL, ровно нужный regression.
Прежний toolkit: 3/3 pure gates PASS, Apply/Rollback остаются BLOCKED.
Native WFP calls 0; OS/network tests NOT RUN. Host security/V2Ray route/Chat E2E NOT VERIFIED.
CanApply=false. Native source не запускался; real rollback delete BLOCKED.
Windows/WFP/V2Ray/сеть/учётные записи не менялись; Git/GitHub не использовались.
PS5.1: AST 1/1, runtime suite NOT RUN; исходное PS7 shell-selector наблюдение сохранено, не зачтено за PS5.
DOC IMPACT: reports/{OUT.name}/ + own-card rotation; 297/297 прочих protected файлов неизменны.
Карточка: постановка B2, factual result B3, B1 ОЖИДАНИЕ НОВОЙ ЗАДАЧИ, история сохранена.
Полный отчёт report.md, manifest.json, checks_final.json, source/native/tests/evidence в TASK folder.
NEXT: независимый source/evidence review WEB_11; затем новый USER GO на доказанно изолированную lab и reviewed adapter. Working-host Apply запрещён.
'''
    with (OUT/'factual_result.txt').open('x',encoding='utf-8',newline='\n') as f:f.write(factual)
    print(json.dumps({'card_readback':'PASS','noncard_unchanged':297,'history_bytes':len(history)}))
if __name__=='__main__':{'prepare':prepare,'integrity':integrity,'seal':seal,'rotate':rotate,'finalize':finalize}[sys.argv[1]]()
