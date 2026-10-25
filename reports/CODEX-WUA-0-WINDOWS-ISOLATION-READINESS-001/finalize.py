"""Build/check report-only artifacts in this TASK, no system/Git/network actions.

--verify only reads this package and its addressed protected inputs.
"""
import ast, datetime, hashlib, json, re, sys
from pathlib import Path

TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[1]
ID=TASK.name
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp(p):
    raw=p.read_bytes();return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def manifest():
    paths=sorted(p for p in TASK.rglob('*') if p.is_file() and p!=TASK/'manifest.json')
    return {'schema':1,'task':ID,'root':'repository-relative','self_excluded':'manifest.json (no recursive self-hash)','files':[stamp(p) for p in paths]}
def verify():
    m=read(TASK/'manifest.json');rows=m['files']
    assert len({r['path'] for r in rows})==len(rows)
    actual={p.relative_to(ROOT).as_posix() for p in TASK.rglob('*') if p.is_file() and p!=TASK/'manifest.json'}
    assert {r['path'] for r in rows}==actual,'MANIFEST_COLLECTION'
    for row in rows:
        p=ROOT/row['path'];assert p.resolve().is_relative_to(TASK),'MANIFEST_SCOPE';assert stamp(p)==row,'MANIFEST_HASH'
    before=read(TASK/'evidence/protected_inputs_before.json')['files']
    for row in before: assert stamp(ROOT/row['path'])==row,'PROTECTED_INPUT_CHANGED'
    for p in TASK.rglob('*.json'): read(p)
    for p in TASK.glob('*.py'): ast.parse(p.read_text(encoding='utf-8'),filename=p.name)
    # Publication scan is a narrow heuristic, not a complete secret detector.
    forbidden=[r'C:\\Users\\',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)Bearer [A-Za-z0-9._~-]{12,}']
    # Exclude this validator's patterns themselves; no private material is input.
    for p in TASK.rglob('*'):
        if p.is_file() and p.name!='finalize.py':
            text=p.read_text(encoding='utf-8-sig')
            assert not any(re.search(pattern,text) for pattern in forbidden),'PUBLICATION_SCAN'
    result=read(TASK/'evidence/green_tests.json')
    assert (result['count'],result['pass'],result['fail'],result['error'],result['skip'],result['exit_code'])==(28,28,0,0,0,0)
    assert result['blocked_operation_attempts']==[]
    assert read(TASK/'native_plan.json')['native_tests_run']==0
    required=['report.md','readiness_matrix.md','windows_identity_design.md','wfp_policy_plan.md','native_test_plan.md','rollback_plan.md','checks.json','DOC_IMPACT.md','manual_engineering_review.md']
    assert all((TASK/n).is_file() for n in required)
    assert len(read(TASK/'native_plan.json')['families'])==18
    for p in TASK.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#'): assert (p.parent/target.split('#')[0]).exists(),'BROKEN_LINK'
    return {'status':'PASS','manifest_files':len(rows),'protected_inputs_unchanged':len(before),'json_files_parsed':len(list(TASK.rglob('*.json'))),'python_files_parsed':len(list(TASK.glob('*.py'))),'native_network_tests_run':0,'exit_code':0}

if __name__=='__main__':
    if sys.argv[1:]==['--verify']:
        print(json.dumps(verify()));raise SystemExit(0)
    assert not sys.argv[1:]
    e=TASK/'evidence'
    before=read(e/'protected_inputs_before.json')
    after={'files':[stamp(ROOT/r['path']) for r in before['files']], 'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    assert after['files']==before['files']
    write(e/'protected_inputs_after.json',after)
    write(e/'oracle_repair.json',{'first_run':'red_tests.json','actual_count':26,'pass':25,'fail':0,'error':1,'exit_code':1,
        'selector':'OracleTests.test_malformed_kind_returns_fixed_rejection','trigger':'kind=[] or {} in SYNTHETIC_OFFLINE_ONLY object',
        'observed_exception':'TypeError','cause':'Membership lookup in a set before type validation accepts unhashable input and raises.',
        'old_fragment':"if kind not in {'DENY','ALLOW','QUIESCENCE'}:",
        'new_fragment':"if type(kind) is not str or kind not in {'DENY','ALLOW','QUIESCENCE'}:",
        'source_capture_limitation':'Pre-fix complete source file not separately snapshotted. Fragments describe the actual patch; no pre-fix full-source hash claimed.',
        'green':'green_tests.json','native_impact':'None; synthetic evidence-consistency helper only.'})
    write(e/'engineering_review_repairs.json',{'scope':'offline synthetic oracle only','additional_tests':2,
        'findings':['Quiescence accepted deny_retained assertion without effective_readback','DENY sample accepted unrelated U/wrapper role instead of C/B'],
        'review_red':{'path':'review_red_tests.json','count':28,'pass':26,'fail':2,'error':0,'exit_code':1},
        'intermediate':{'path':'review_intermediate_tests.json','count':28,'pass':27,'fail':1,'error':0,'exit_code':1,
                        'cause':'New common role gate changed existing ALLOW wrong-owner fixed rejection code. Restrict role gate to DENY; ALLOW retains B_ROUTE_UNPROVED.'},
        'final':{'path':'green_tests.json','count':28,'pass':28,'fail':0,'error':0,'exit_code':0},
        'source_limitation':'Fragments/source fixes in this TASK; no independent red source-revision attestation.'})
    findings=[
        ('admission_boundary','integrations/wua_chatgpt_mcp/broker.py',"strict_admission_status='STRICT_ADMISSION_BLOCKED'"),
        ('upstream_secret_gate','integrations/wua_chatgpt_mcp/broker.py','UPSTREAM_SECRET_BOUNDARY_UNVERIFIED'),
        ('identity_shape_only','integrations/wua_chatgpt_mcp/security_contract.py','LOCAL_SID_REQUIRED'),
        ('loopback_http_route','integrations/wua_chatgpt_mcp/security_contract.py',"r['client_proxy_host']=='127.0.0.1'"),
        ('declared_child_roles','integrations/wua_chatgpt_mcp/security_contract.py','CHILD_ALLOWLIST'),
        ('pipe_same_user_only','integrations/wua_chatgpt_mcp/npfs/Gateway.cs','CURRENT_USER_FIXTURE_ONLY'),
        ('pipe_dacl_readback','integrations/wua_chatgpt_mcp/npfs/Gateway.cs','DACL_READBACK'),
        ('pipe_identification','integrations/wua_chatgpt_mcp/npfs/Gateway.cs','CLIENT_EFFECTIVE_TOKEN'),
        ('parent_token_process_creation','integrations/wua_chatgpt_mcp/npfs/Gateway.cs','SDK_CREATE_SUSPENDED'),
        ('job_before_run','integrations/wua_chatgpt_mcp/npfs/Gateway.cs','SDK_JOB_BEFORE_RUN'),
        ('held_peer_sid_image','integrations/wua_chatgpt_mcp/npfs/Shared.cs','PEER_PROCESS'),
        ('relay_server_pid','integrations/wua_chatgpt_mcp/npfs/Relay.cs','SERVER_PID_MISMATCH'),
        ('wfp_disabled_apply','reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/contracts/backend-contract.json','OfflineBackend.Apply: always BLOCKED'),
        ('wfp_complement','reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/contracts/backend-contract.json','unmatched by own denies'),
        ('wfp_foreign_arbitration','reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/contracts/backend-contract.json','foreign filters/callouts/hard permits remain UNVERIFIED'),
    ]
    source=[]
    for identity,path,needle in findings:
        p=ROOT/path;lines=p.read_text(encoding='utf-8-sig').splitlines()
        hits=[i+1 for i,line in enumerate(lines) if needle in line];assert hits,(identity,'LOCATOR_MISSING')
        source.append({'id':identity,'classification':'CODE_CONFIRMED','path':path,'lines':hits,'needle':needle,'sha256':stamp(p)['sha256']})
    write(e/'source_findings.json',{'findings':source,'limitations':'Source/fixture declarations, not native runtime proofs.'})
    write(e/'read_scope.json',{'matrix':'B1 §3; local content hashes in protected_inputs_before.json, no Git revision attestation',
        'addressed_sections':{'000_Задачи Codex.md':['Правила','БЛОК 1','БЛОК 4 latest verdict'],
        '08_Старт.md':['priority USER GO / authority'],
        '18_Регламент сопровождения документации.md':['DOC-TASK-CLOSEOUT-OWNER-01@1','DOC-TEST-LIFECYCLE-01@1','DOC-TASK-READ-SCOPE-01@1','DOC-GIT-01@1','DOC-LOCAL-REPORT-HANDOFF-01@1'],
        '19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md':['§7.7','§7.8'],
        '34_TACTICAL_CONTEXT.md':['latest WEB_12 CURRENT'],
        '36.1_Обязательный регламент тестирования для LLM.md':['TEST-ENG-01','TEST-DEV-01','TEST-COV-01','TEST-EXEC-01'],
        '36.2_Профиль тестирования Web Alarm Workspace.md':['test isolation/receipts and preservation of existing commands; no production suite run']},
        'other_addressed_sources':['previous strict report/admission matrix','broker/security/NPFS source','existing WFP backend contract/Core.cs because directly relevant to current WFP design'],
        'not_read':['personal 001 archive','other users/credentials','full Firewall/WFP rules','Git/.git/history','working proxy config/network connections'],
        'no_shared_documents_written':True})
    py=list(TASK.glob('*.py'))
    for p in py: ast.parse(p.read_text(encoding='utf-8'),filename=p.name)
    write(e/'python_syntax.json',{'parser':'Python ast.parse, no bytecode/build','files':len(py),'syntax_errors':0,'exit_code':0})
    host=read(e/'host_observations.json');api=read(e/'api_observations.json');green=read(e/'green_tests.json');red=read(e/'red_tests.json')
    observed=sum(r['status']=='OBSERVED' for r in host['observations'])
    symbols=sum(len(v) for v in api['exports'].values());present=sum(x is True for v in api['exports'].values() for x in v.values())
    assert (observed,len(host['observations']),symbols,present)==(14,14,14,14)
    command_base="& '.venv/Scripts/python.exe' -I -B 'reports/"+ID+"/"
    checks={'schema':1,'task':ID,'scope':'READ_ONLY_HOST_INSPECTION_AND_OFFLINE_ENGINEERING',
        'sync_gate':'USER_DECLARED, no Git query',
        'commands':[
            {'command':command_base+"capture_inputs.py'",'exit_code':0,'purpose':'Task snapshot/user sync statement +24 addressed input hashes'},
            {'command':"& './reports/"+ID+"/collect_readonly.ps1' | Set-Content -Encoding UTF8 '<TASK>/evidence/host_observations.json'",'exit_code':0,'query_groups':14,'observed':14,'blocked':0},
            {'command':command_base+"observe_apis.py' | Set-Content -Encoding UTF8 '<TASK>/evidence/api_observations.json'",'exit_code':0,'exports_present':14,'exports_checked':14,'current_token_elevated':api['current_token_elevated'],'wfp_npfs_invocations':0},
            {'command':command_base+"plan_data.py'",'exit_code':0,'future_native_families':18,'executed':0},
            {'command':command_base+"test_offline.py' red",'exit_code':red['exit_code'],'count':red['count'],'pass':red['pass'],'fail':red['fail'],'error':red['error'],'skip':red['skip']},
            {'command':command_base+"test_offline.py' review_red",'exit_code':1,'count':28,'pass':26,'fail':2,'error':0,'skip':0,'evidence':'evidence/review_red_tests.json'},
            {'command':command_base+"test_offline.py' green (intermediate)",'exit_code':1,'count':28,'pass':27,'fail':1,'error':0,'skip':0,'evidence':'evidence/review_intermediate_tests.json'},
            {'command':command_base+"test_offline.py' green",'exit_code':green['exit_code'],'count':green['count'],'pass':green['pass'],'fail':green['fail'],'error':green['error'],'skip':green['skip']},
            {'command':'System.Management.Automation.Language.Parser.ParseFile(<TASK>/collect_readonly.ps1); no script execution','exit_code':0,'files':1,'syntax_errors':read(e/'powershell_syntax.json')['syntax_errors']},
            {'command':command_base+"finalize.py' (ast.parse gate included)",'exit_code':0,'python_syntax_files':len(py),'syntax_errors':0},
        ],
        'counts_note':'28 unique final methods =25 ordinary +3 mutation controls. First RED had26, engineering review added2. Repeated runs overlap; do not add counts as distinct tests. Three inner expected assertion FAILs belong to mutation controls, not product failures.',
        'mutants':{'executed':3,'caught':3,'included_in_28':True,'inner_expected_failures':3,'inner_errors':0},
        'source_findings':len(source),'protected_inputs_unchanged':24,
        'python_guard':{'blocked_operation_attempts':green['blocked_operation_attempts'],'claim':'Python process guard only, not OS-level containment'},
        'native_tests':{'families_planned':18,'families_run':0,'probes_run':0,'status':'NOT RUN / NOT VERIFIED','not_collected_in_offline_suite':True},
        'prohibited_operations':{'git_github':0,'network_probes':0,'listeners':0,'account_acl_firewall_wfp_mutations_requested':0,'elevation_requests':0,'engine_runs':0,'tunnel_starts':0,'card_archive_edits':0},
        'limitations':['No exact Git revision independently verified','API/command availability not permissions or enforcement','No broad rules, user/connection enumeration or secret reads','Protected hashes cover24 addressed files only','No native receipt authentication or special-case observers implemented','Publication heuristic scan is not complete secret detection'],
        'packet_verification':None}
    write(TASK/'checks.json',checks)
    report=f'''# CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001 — factual report

**Исполнитель:** Codex 007. **Дата:** 2026-10-25. **Локальный итог:** PASS / BOUNDED READINESS. **Сдача:** RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_12. Это готовность отчётного плана, не готовность включить MCP или утверждение native security.

## Выполненный scope и основания

Пользователь подтвердил синхронизацию локальной копии: USER_DECLARED, Git revision независимо не проверялась. B1, собственные правила и последний независимый B4 прочитаны; адресный read set и source hashes сохранены. Предыдущая strict admission имеет независимую bounded offline приёмку по локальным №19/34/B4; это provenance документации, не новая Git-проверка.

Создан только настоящий TASK-каталог: report/plans, минимальные sanitized host observations, synthetic oracle checker/tests, manifest. Нет новой runtime admission-system, setup scripts или применяемых firewall rules. Содержимое программ, конфигураций, документации и карточки не изменялось. 24 адресных исходных файла совпали по bytes/SHA до/после; это не мониторинг всего workspace/Windows.

## A. Подтверждённые факты

- **OBSERVED_READ_ONLY:** {observed}/14 ограниченных query groups успешно. Windows10 Pro 10.0.19045 x64, PowerShell7.6.5 Core. Current token administrator_role=false, system=false, authenticated=true; отдельный TOKEN_QUERY: elevated=false. Это не полный inventory privileges и не попытка административного доступа.
- **OBSERVED_READ_ONLY:** Get-LocalUser по exact wua-client и wua-broker вернул отсутствие обеих локальных accounts. Другие пользователи/SID не собирались.
- **OBSERVED_READ_ONLY:** BFE/MpsSvc Running; три Firewall profiles enabled=True. Default inbound/outbound values = NotConfigured в выполненном запросе. Effective defaults/ActiveStore/GPO/filter arbitration UNKNOWN; не интерпретировались как allow/deny.
- **OBSERVED_READ_ONLY:** шесть management commands доступны как metadata; Get-NetFirewallRule/SecurityFilter не исполнялись. {present}/{symbols} выбранных System32 WFP/NPFS/ACL/token/launch exports доступны. WFP session не открывалась, pipe не создавался, impersonation/identity launch не выполнялись. Export availability не доказывает права или enforcement.
- **CODE_CONFIRMED:** existing broker strict API повторно проверен на полном synthetic intent и users=[]: VALID + RUNTIME_SECURITY_UNVERIFIED и AUTH_USERS_REQUIRED соответственно; оба оставляют can_apply/can_start_tunnel=false.

Сырые usernames других accounts, SID, privilege/group dumps, реальные connection addresses, passwords/tokens/secret-store bytes отсутствуют. Evidence: [host](evidence/host_observations.json), [API](evidence/api_observations.json), [source locators](evidence/source_findings.json), [матрица](readiness_matrix.md).

## B. Что готово и что ограничивает native переход

**CODE_CONFIRMED:** Python contract проверяет объявленные SID/role/tuple/hashes, не реальный process token. WFP offline backend Apply/Rollback BLOCKED; complement-deny candidate не проверен против actual arbitration. Firewall enabled и API присутствие не заменяют default-deny proof. Все исходные ограничения сохранены.

**CODE_CONFIRMED / существенное уточнение:** existing NPFS — C relay→U server-owned MCP gateway. Gateway содержит CURRENT_USER_FIXTURE_ONLY и child запускается с parent context. Это same-user fixture, не готовая C/B cross-user установка. Accepted C→B proxy path — exact loopback HTTP CONNECT. B-owned engine должен сам владеть внешним R:Q socket, а не wrapper перед U v2rayN.

**BLOCKED:** C→B proxy NPFS adapter не реализован рассмотренными integration/contracts. Требуется решение: оставить narrow loopback HTTP CONNECT + C→U NPFS либо отдельно разработать совместимый no-TCP proxy transport. Нельзя просто заменить endpoint на pipe или разрешить новый helper без review.

**UNKNOWN/BLOCKED:** реальные C/B accounts/launcher/token rights, protected source/secret store, cross-SID peer/DACL/access, engine binary/schema/runtime compatibility, B socket owner, WFP IPv4/IPv6/UDP/raw/DNS/loopback/delegation/existing flows/boot-time guarantees и exact rollback. Ранее обнаруженный sing-box не выбран движком этой TASK; engine.family=V2Ray не менялся. Upstream authentication/error-log secret leak остаётся SECURITY BLOCKER и не устранён Python contract.

## C. Подготовленные планы

[Identities](windows_identity_design.md) описывает minimal C/B tokens, actual socket ownership, server-owned U gateway, noninteractive launcher prerequisites, handle/child/delegation и cross-SID NPFS boundary. [WFP plan](wfp_policy_plan.md) содержит IPv4/IPv6/TCP/UDP/DNS/loopback/NPFS матрицу и complement-deny vs naive Block/Allow caveat; отмечены недоказанные layers/arbitration/boot gaps. Это требования, а не применяемая policy.

[Native plan](native_test_plan.md), machine-readable native_plan.json: **18 семейств**, каждое с independent observation source, ожиданием, negative control, false-PASS risk, preparation/rollback. **Все NOT RUN**, реальных probes=0. Варианты внутри семейства не выданы за выполненные тесты. Timeout/no receipt/CONNECT200/reported zero не считаются достаточными оракулами. Для NPFS/auth/config/boot требуются особые native observers; generic synthetic egress helper их не реализует.

[Rollback](rollback_plan.md): freeze admissions, independent zero processes/flows/handles/delegated work, trusted ownership/readback/CAS, exact owned cleanup, deny removal last. При unknown KEEP DENY. Нет global reset или восстановления рабочего proxy из массового snapshot. Реальное безопасное восстановление ещё BLOCKED; не обещана проверенная гарантия.

Разрешения разделены: READ_ONLY (текущее), LAB_SETUP, RULE_APPLY, NATIVE_EGRESS_TEST, TUNNEL_START. Одно не включает другое; lab setup не создаётся этим отчётом. Native probes требуют независимого outer containment и отдельного GO.

## D. Реальные проверки и counts

| Проверка | Фактический результат |
| --- | --- |
| Targeted Windows observations | 14/14 groups OBSERVED, 0 blocked query groups; exit0 |
| Selected DLL exports | 14/14 present; WFP/NPFS API calls0; current-token query read-only |
| Первый offline RED | 26 methods:25 PASS,0 FAIL,1 ERROR(TypeError),0 SKIP; exit1 |
| Engineering review RED | 28 methods:26 PASS,2 FAIL,0 ERROR/SKIP; exit1 |
| Review intermediate | 28 methods:27 PASS,1 FAIL(fixed rejection code),0 ERROR/SKIP; exit1 |
| Final offline GREEN | 28/28 PASS,0 FAIL/ERROR/SKIP; exit0 |
| Executed mutation controls | 3/3 caught, включены в28; каждый inner1 expected assertion FAIL,0 ERROR |
| Existing broker API reuse | 1 method внутри28: valid intent stays BLOCKED; empty users rejected |
| Syntax | {len(py)} Python files ast.parse +1 PowerShell AST; errors0 |
| Protected inputs | 24/24 bytes/SHA unchanged |
| Native network/NPFS/process probes | 0;18 planned families NOT RUN |

28 =25 ordinary checks +3 controls; первый RED имел26, после engineering review добавлены2. Прогоны перекрываются, counts не складывать как уникальные тесты; прошлые suites не перезапускались. Existing broker pure API повторён без legacy native Harness/import. [Checks](checks.json) содержит команды/exit/counts/limits. [RED](evidence/red_tests.json), [GREEN](evidence/green_tests.json), [repair](evidence/oracle_repair.json) сохранены. [Review repairs](evidence/engineering_review_repairs.json) фиксируют два дополнительных пробела oracle и промежуточный FAIL; они устранены без изменения runtime code.

Первый новый oracle принимал set-membership до type check поля kind, что давало TypeError на list/dict. Исправлен type guard, исходная failed evidence сохранена. Полный pre-fix source отдельно не snapshot-ился: сохранены точные фрагменты исправления, selector/trigger/exception; pre-fix hash не заявляется. Helper выдаёт только OFFLINE_CONSISTENT, native_verified=false, can_apply=false, can_start_tunnel=false; это не аутентификация native receipt.

Audit hook Python tests запрещает socket/registry/subprocess и запись вне TASK; blocked attempts0. Он не OS sandbox и не native fail-closed evidence. Publication scan — ограниченная эвристика приватных paths/keys, не полный secret detector. Manifest включает все файлы пакета кроме себя; bytes/SHA проверяются finalize.py --verify. [Manual engineering review](manual_engineering_review.md) выполнен отдельно от тестов.

## E. Статусы и следующий gate

```text
PASS / BOUNDED READINESS (report preparation only)
LOCAL ONLY / GITHUB NOT YET VERIFIED
AWAITING INDEPENDENT VERIFICATION WEB_12
engine.family=V2Ray
can_apply=false
can_start_tunnel=false
install_uninstall=BLOCKED
STRICT_ADMISSION_BLOCKED
HOSTED_TUNNEL_ON_HOLD_BY_USER
CROSS-SID NPFS NOT VERIFIED
WFP NATIVE ENFORCEMENT NOT VERIFIED
B EGRESS OWNER NOT VERIFIED
REAL CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
ROLLBACK EXECUTION BLOCKED / KEEP DENY
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

Пользователь публикует только эту TASK-папку и передаёт WEB_12 report/manifest для независимой проверки. Никаких Git/GitHub операций или отправки в другой чат исполнителем не выполнялось. [DOC IMPACT](DOC_IMPACT.md) содержит предложения №19/34/06; документы/карточка/001 не изменены и не ротированы по текущим правилам owner-closeout.

NEXT USER DECISION: transport C→B; отдельно approved isolated lab/outer containment; engine/source compatibility и исправление upstream secret boundary. Затем, если пользователь решит продолжать, отдельный ограниченный LAB_SETUP GO с конкретным ownership/rollback планом. Это **не запрос** на немедленную активацию и не разрешение native/tunnel tests. До новой разрешённой реализации и независимой приёмки security gates остаются закрытыми.
'''
    (TASK/'report.md').write_text(report,encoding='utf-8')
    write(TASK/'manifest.json',manifest())
    first=verify()
    checks['packet_verification']={**first,'command':command_base+"finalize.py' --verify",'coverage':'all TASK files except manifest itself;24 addressed protected inputs; JSON/syntax/required files/links/narrow publication scan'}
    write(TASK/'checks.json',checks)
    write(TASK/'manifest.json',manifest())
    print(json.dumps(verify()))
