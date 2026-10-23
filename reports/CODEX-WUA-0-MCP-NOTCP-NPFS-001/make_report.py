"""Seal this local TASK, without Git, network or personal archive reads."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
REPO=OUT.parents[1]
PKG=REPO/'integrations/wua_chatgpt_mcp'
TASK=OUT.name
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rel(p):return p.relative_to(REPO).as_posix()

def manifest():
    files={p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
    files.update(p for p in PKG.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Explicit immutable runtime dependencies from the bounded initial inventory.
    initial=load(OUT/'evidence/initial_state.json')
    files.update(REPO/p for p in initial['inputs'])
    files.add(REPO/'Документация/000_Задачи Codex.md')
    rows=[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    put(OUT/'manifest.json',{'task':TASK,'schema':1,'source':'local file bytes, no Git operations','self_excluded':True,'personal_archive_whole_file_excluded':True,'archive_new_range_locator':'evidence/card_rotation.json','files':rows})
    for row in rows:
        p=REPO/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    return len(rows)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest-only',action='store_true');args=parser.parse_args()
    if args.manifest_only:
        print({'manifest_entries':manifest()});return
    finals=[]
    for p in (OUT/'runs').glob('attempt-*/results.json'):
        v=load(p)
        if v['collected']==24 and v['passed']==24 and v['failed']==v['errors']==v['skipped']==0:finals.append(p)
    final=sorted(finals)[-1];run=final.parent;v=load(final)
    regression=sorted((OUT/'runs').glob('regression-*/results.json'))[-1];reg=load(regression)
    assert reg['sdk']=={'total':63,'passed':63,'failed':0}
    assert reg['security']['total']==reg['security']['passed']==24 and reg['security']['failed']==reg['security']['errors']==0
    source=load(run/'source_pins.json')
    assert all(sha(REPO/p)==s for p,s in source.items()),'FINAL_SOURCE_DRIFT'
    binary=load(run/'binary_pins.json')
    assert all(sha(OUT/'build'/name)==value['sha256']==sha(REPO/value['snapshot']) for name,value in binary.items())
    osobs=load(run/'os_network_samples.json');wrong=load(run/'wrong_peer_mutation.json')
    normal,mutant=osobs['observations'];assert normal['rows']==[] and normal['children']==[] and mutant['rows']
    assert wrong['mutant_policy_oracle']=='FAIL'
    statuses=['LOCAL_STDIO_NPFS_MCP_TESTED','C_RELAY_NO_TCP_SOURCE_REVIEWED','RUNTIME_NETWORK_OBSERVATION_NOT_VERIFIED','REAL_CROSS_SID_AUTH_PENDING','WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED','B_V2RAY_EGRESS_OWNER_NOT_VERIFIED','HOSTED_TUNNEL_ON_HOLD_BY_USER','ORDINARY_CHATGPT_E2E_NOT_VERIFIED']
    facts={'task':TASK,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11','publication':'LOCAL ONLY / GITHUB NOT USED','npfs':{k:v[k] for k in ['collected','passed','failed','errors','skipped']},'npfs_evidence':rel(final),'regression':{'sdk':reg['sdk'],'security':{k:reg['security'][k] for k in ['total','passed','failed','errors']},'evidence':rel(regression)},'statuses':statuses,'network_observations':{'normal_samples':normal['samples'],'normal_endpoint_rows':len(normal['rows']),'normal_children':normal['children'],'mutant_samples':mutant['samples'],'mutant_endpoint_rows':len(mutant['rows']),'complete_process_lifetime_proof':False,'OS_enforced':False},'security_controls':{'tcp_dial':'DETECTED','wrong_peer':'DETECTED: inner policy oracle FAIL','shortened_lifetime':'owned process termination observed'},'source_pins':rel(run/'source_pins.json'),'binary_pins':rel(run/'binary_pins.json'),'can_apply':False,'install_uninstall':'BLOCKED','real_cross_sid_tests':'NOT RUN','WFP_calls':0,'Go_tunnel_client_runs':0,'real_V2Ray_requests':0,'OpenAI_requests':0,'ordinary_ChatGPT_calls':0,'independent_acceptance':'NOT VERIFIED','rotation':'see evidence/card_rotation.json'}
    put(OUT/'checks.json',facts)
    rotation_path=OUT/'evidence/card_rotation.json'
    rotation=load(rotation_path) if rotation_path.exists() else None
    rotation_text=('**Фактическая ротация:** '+rotation['status']+'; '+str(rotation.get('archive_appended_bytes',0))+' новых байт, archive_old_bytes_read='+str(rotation['archive_old_bytes_read'])+'; БЛОК4 byte-exact сохранён.\n' if rotation and rotation['status']=='CARD ROTATION VERIFIED' else '**Фактическая ротация:** см. evidence/card_rotation.json; до её успешной записи не считать выполненной.\n')
    if rotation:
        facts['rotation']=rotation['status'];put(OUT/'checks.json',facts)
    attempts=[]
    for p in sorted((OUT/'runs').glob('attempt-*/results.json')):
        result=load(p);attempts.append({'path':rel(p),'collected':result['collected'],'passed':result['passed'],'failed':result['failed'],'errors':result['errors']})
    put(OUT/'evidence/attempt_catalog.json',{'attempts':attempts,'prep':'evidence/prep01.json','initial_fail_preserved':True,'classifications':{'SDK aliases':'HARNESS_DEFECT; SDK2 snake_case attributes','CreateNamedPipe WinError87':'PRODUCT DEFECT in new candidate; unsupported dwOpenMode flag removed, narrow DACL retained','fake peer image':'HARNESS_DEFECT: venv launcher hash versus real Python process image; guard correctly refused','startup job race':'SOURCE REVIEW FINDING; fixed with suspended creation before job assign/resume','terminal error race':'SOURCE REVIEW FINDING; first terminal event retained'},'early_intermediate_full_source_snapshots':'NOT AVAILABLE; hashes and diagnostics retained; final full snapshot available'})
    selectors='\n'.join('- `'+x['id'].replace('__main__.','')+'` — '+x['status'] for x in v['selectors'])
    (OUT/'tests.md').write_text(f'''# Проверки и точная collection

Финальный Windows-run: `{rel(run)}`. **24 collected / 24 PASS / 0 FAIL / 0 ERROR / 0 SKIP**. Сборки Relay/Gateway: exit0, warnings-as-errors. Финальные исходники и бинарники скопированы в source_snapshot и сверены SHA-256; compiler argv — build.json. SDK2 установленный, тесты не вызывают handlers напрямую.

Команды: см. README.md. Baseline regression: `{rel(regression)}` — **63/63 MCP checks; 24/24 security methods**, без переписывания старого отчёта. Common fixture path guard расширен ровно на текущую TASK/runs; прежние default/interface сохранены.

## Exact selectors

{selectors}

## Oracle / риск / предел

| Проверки | Риск и независимое следствие |
|---|---|
| 01–02 | Official SDK initialize/list/four tools; ошибки foreign TASK/unknown tool/types/extra/replay; canonical response hashes, nonce, actual seed JSON и receipt; restart и ambient proxy environment |
| 03–08, 11–12, 20–21 | Missing/remote/wrong name; peer PID/SID/image; DACL exclusive instance; bad key/session/protocol/source pin; authority-session binding; before-auth state absent |
| 09, 13, 16, 18 | JSON duplicates/types/size, partial input/output, response bounds/correlation, wire replay, unresponsive/slow peer; bounded stop |
| 10, 15, 22 | Gateway crash, own worker OS wait/job descendant cleanup, idle/EOF; shortened hard deadline control |
| 14 | OS TCP/UDP v4/v6 PID sampling + Toolhelp C children; normal {normal['samples']} samples / zero endpoint rows, mutant {mutant['samples']} samples / {len(mutant['rows'])} observed rows; independent owned loopback accept. Finite sampling only |
| 17, 23–24 | Twelve concurrent SDK requests retain correlation; real SDK ping through Unicode image path; SDK cancellation reaches an intentionally stalled independent pipe peer with the matching requestId |
| 19 | Source/syntax gate; C path excludes Python/network/child launch, fresh fixture scope remains strict |

Security controls: TCP dial mutant and wrong-peer mutant are deliberately unsafe copied sources under this attempt only. Normal policy oracle PASS; mutated policy oracle **FAIL** is the required detection result. They are not production flags. A shortened-watchdog executable checks a lifecycle branch. Nested negative fault cases are assertions inside methods, not extra inflated test counts.

Unknown cross-SID/Windows WFP/Go/V2Ray/ordinary Chat: NOT RUN / NOT VERIFIED. Remote-name rejection occurs before connect; no real SMB request. Cancellation test is a transport fault probe against a scoped owned fake peer, not WebAlarmApi/Chat E2E. The four successful tools use the complete real SDK/API chain in 01/02.

Initial failures and all later runs: evidence/attempt_catalog.json and original result files. Early aliases, WinError87 and bad launcher image pins are classified; they were not hidden by final PASS. Early full intermediate source snapshots are missing; final source/binary snapshot and initial hash diagnostics retained. No CI or independent verifier execution claimed.
''',encoding='utf-8')
    (OUT/'report.md').write_text(f'''# {TASK} — реальный локальный MCP через Named Pipe

Codex 007, 2026-10-24. **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.** Координаторский reference `main@a547092f74d6ee4f2a32982b8c7c067c61e160da` не проверялся через Git. Фактическая версия — local source/binary hashes и manifest.

Реализованы и реально испытаны Windows C# STDIO↔NPFS relay и отдельный U-side server-owned read-only SDK/API gateway. Официальный SDK client через оба executable и настоящий Named Pipe вызывает четыре прежних инструмента; данные происходят из настоящего WebAlarmApi на новом synthetic хранилище. C relay не использует Python asyncio и не требует добавления TCP endpoint. Это закрывает зависимость нового C frontend от найденного Python selfpipe; полная C/Go/WFP egress-гарантия ещё не доказана.

## Раздельные обязательные статусы

```text
{chr(10).join(statuses)}
```

`RUNTIME_NETWORK_OBSERVATION_NOT_VERIFIED` означает отсутствие полного continuous process-wide доказательства: реальный независимый от relay PID sampler Windows TCP/UDP IPv4/IPv6 и Toolhelp дал {normal['samples']} нормальных samples без endpoints/children и заметил intentional native TCP mutation ({len(mutant['rows'])} rows). Выборка может пропустить startup/transient/failed dial; ETW/WFP enforcement не запускались. Нельзя читать source review или Python audit как абсолютный запрет любой сети.

## Реализация и scope

Новая цепочка: `official MCP ClientSession → STDIO → WuaRelay.exe → authenticated local NPFS → WuaGateway.exe → U SDK worker → server.make_server → synthetic WebAlarmApi.dispatch`.

Новые исходники: `npfs/Shared.cs`, `Relay.cs`, `Gateway.cs`, `gateway_worker.py`; тесты `tests/run_npfs.py`, `tests/npfs_regression.py`; config `configs/npfs.fixture.contract.json`. Три адресных совместимых изменения: common.py разрешает fixtures текущей TASK/runs, README и gateway.ipc.contract описывают новый bounded candidate. Существующие четыре tool schemas/handlers не переписаны; baseline STDIO API worker сохранён.

Local NPFS endpoint создаётся сервером: exact name, first/one instance, reject remote clients, protected narrow DACL с фактическим readback. Клиент проверяет server PID/primary SID/image; сервер отдельно проверяет client process primary SID и эффективный Identification token через RunAsClient, image и fresh grant. Session/direction/sequence/length/payload защищены HMAC; RPC duplicate/correlation/limits проверены с обеих сторон. MAC/PID/nonce не названы заменой Windows SID.

Current-user-only fixture намеренно не выдаётся за разные C/B/U tokens. Gateway запускает только фиксированный U SDK child: suspended, explicit three-handle list, job assignment до ResumeThread; crash gateway завершает его реальные descendants. C relay не запускает helpers. Frame deadline2.5s, bridge30s, hard process watchdog40s, 8192/32768 bytes, bounded IDs/queues. Python self-sockets у U/test client не объявлены исчезнувшими.

Подробности процессов: topology.md; auth/ACL/TCB: pipe_security.md; воспроизведение: README.md.

## Настоящие проверки и исправления

Финальный run `{rel(run)}`: **24/24 PASS, 0 FAIL/ERROR/SKIP**, две C# сборки exit0, Python syntax PASS. Source/binary pins и immutable final snapshot сохранены. Четыре tools: ping, list_capabilities, read_synthetic_context, get_status. Независимые fixture nonce/canonical content hash, server receipt и actual JSON seed/tree hash сверены; read не меняет storage. Дополнительно двенадцать concurrent запросов, Unicode executable path и real SDK cancellation fault probe.

Регрессия `{rel(regression)}`: **63/63 MCP checks и 24/24 security methods**, новые outputs только в этой TASK. Это новые прогоны исполнителя, не independent PASS и не Desktop E2E.

Отрицательные проверки охватывают missing/remote/occupied/wrong peer/name/owner/session/MAC/protocol, foreign TASK, unknown tool/type/extra, oversize/partial/slow/unresponsive, replay/duplicate/correlation, EOF/crash и owned cleanup. TCP mutant замечен OS sampler и owned accept; wrong-peer mutant действительно передал запрос постороннему controlled endpoint, что дало ожидаемый inner policy FAIL. Exact selectors и пределы — tests.md.

Сохранены первоначальные FAIL: неверные SDK snake_case aliases в harness; неподдерживаемый CreateNamedPipe dwOpenMode (WinError87) в новом коде; ошибочный pin Python venv launcher вместо реального peer image в fault harness. Guard при последнем правильно отказал и не ослаблялся. Source review также исправил startup job race, выбор первого terminal event, привязку authority session и Unicode image lookup. Все старые результаты остаются в evidence/attempt_catalog.json. Ранние полные intermediate source snapshots отсутствуют; их hashes/diagnostics есть, полный финальный snapshot есть.

## MANUAL ENGINEERING REVIEW и ограничения

Отдельный разбор — manual_engineering_review.md: duplex/deadlock/partial IO, identification impersonation/revert, ACL startup race, peer replacement/no reconnect, environment/secret inheritance, job-before-run, EOF/crash/watchdog, correlation/grant replay и portability. Финальный review прочитал actual final Relay/Native peer и сохранил конкретные открытые границы.

Не доказаны hostile same-user isolation, signing/loaded dependency closure, реальные cross-SID права, полный native Go graph и постоянный OS no-network observer. Pipe не закрывает все прочие IPC/BITS/COM/DNS delegation. Current-user config/grant delivery не является production credential boundary. У gateway фиксирован fixture layout, короткая bounded session и x64 Windows prerequisites; это не системный installer.

**F2 остаётся отдельным обязательным gate:** выделенный B-owned V2Ray HTTP CONNECT process должен владеть настоящим внешним socket → только approved literal R:Q, без DIRECT/fallback. Пользовательский V2Ray/SOCKS за B-wrapper не подходит. Код брокера/V2Ray, accounts, WFP/firewall, tunnel, системная сеть, production/Claude/LLM12 и старые отчёты не изменялись. 0 Go-client runs, 0 WFP calls, 0 real V2Ray/OpenAI requests, 0 ordinary ChatGPT calls. CanApply=false, Install/Uninstall BLOCKED, hosted HOLD.

## Provenance, документация и ротация

Windows10 build19045 x64, Python3.12.10/MCP2.2.0, existing Framework64 C#5. Начальная bounded inventory: 68 files; 65 unchanged, ровно три предусмотренных package edits. Секреты grant не записывались; named-field scan outputs выполнен. Никаких установок, повышения прав, network settings, Git/GitHub или внешних запросов.

Чтение адресное: правила собственной карточки/B1/B4; 08 актуальный маршрут; 34 current/MCP security; 01 runtime boundary; 19 §3–5/7.1–7.3 и профильные MCP findings; 37§9; 36/36.1 обязательные TEST-*; 36.2/36.3 изоляция/runtime gates; точные DOC-* в18 и зависимости; предыдущий MCP report/topology/gates/manual-review и затронутый код. Личные исторические архивы не читались и не индексировались. Source reference координатора не считается checked commit.

Ротация выполняется после сохранения report/checks/manifest отдельным single-use rotate_card.py: exclusive append к своему001, bounded readback только добавленного диапазона, exclusive card lock/readback/rollback, окно пяти TASK и byte-exact БЛОК4. Фактический статус, offset/length/new-entry digest и B4 before/after — evidence/card_rotation.json; manifest обновляется после ротации. Старые байты архива не читаются и не перезаписываются. При drift ротация блокируется, БЛОК1 не очищается.

{rotation_text}

**DOC IMPACT / SHARED DOC DELTA: DOC CLOSEOUT INCOMPLETE (общий контур координатора).** Общие документы не изменены. WEB_11 после независимой проверки предлагается обновить19/34 о bounded NPFS candidate, 36.1/профильный каталог о selectors; сохранить F2 и все live gates. Общий18 ещё описывает старый full B2/B3, собственная карточка имеет приоритетный USER GO2026-10-23 на001+пять summary rows; требуется координируемое уточнение18 и устаревших ссылок@1 на verifier@2. Самостоятельно общий регламент не правил. Полный DOC CLOSEOUT остаётся за координатором.

**NEXT SAFE ACTION:** пользователь передаёт/публикует комплект WEB_11 для независимого source/evidence review. Дальнейшие lab/cross-SID/WFP/B-egress/hosted/ordinary Chat этапы — отдельные адресные USER GO, см. next_user_go.md. Автоматической независимой приёмки или прямой доставки в другой чат не заявлено.
''',encoding='utf-8')
    framework=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319')
    put(OUT/'evidence/toolchain.json',{'platform':platform.platform(),'python':sys.version,'mcp':v['mcp'],'csc_sha256':sha(framework/'csc.exe'),'framework_references':{name:sha(framework/name) for name in ['mscorlib.dll','System.dll','System.Core.dll','System.Web.Extensions.dll']},'sources':source,'binary_pins':binary,'no_downloads':True,'no_Git':True})
    print({'npfs':facts['npfs'],'regression':facts['regression'],'manifest_entries':manifest()})

if __name__=='__main__':main()
