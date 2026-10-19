"""Local file/hash/excerpt tools only. No subprocess, network, Windows query or policy API."""
from pathlib import Path
import hashlib
import json
import os
import sys
import ast
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
CARD=ROOT/'Документация/000_Задачи Codex.md'
CLAUDE=ROOT/'reports/CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001'
SDK=Path(r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.19041.0')
NET=Path(r'C:\Windows\System32\WindowsPowerShell\v1.0\Modules\NetSecurity')

def sha(data):return hashlib.sha256(data).hexdigest()
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
def save(name,obj):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def pathrow(p):
    b=p.read_bytes()
    try:name=p.relative_to(ROOT).as_posix()
    except ValueError:name=str(p)
    return {'path':name,'bytes':len(b),'sha256':sha(b),'authorized_change':p.resolve()==CARD.resolve()}

def collect():
    paths=set()
    old=ROOT/'reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001'
    for x in json.loads((old/'inputs_before.json').read_text())['inputs']:
        p=Path(x['path']);paths.add(p if p.is_absolute() else ROOT/p)
    for base in [old,CLAUDE]:paths.update(p for p in base.rglob('*') if p.is_file())
    # Cached local CLI docs, not new native invocations or private configuration copies.
    base=ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/secure_tunnel_preparation'
    paths.update(base/x for x in ['run_help.txt','cli_help.txt','version.txt','start_tunnel.py'])
    selectors={
      NET/'NetFirewallRule.cmdletDefinition.cdxml':['cim:OperationOption:LocalUser','cim:OperationOption:Authentication','cim:OperationOption:OverrideBlockRules'],
      NET/'NetFirewallSecurityFilter.cmdletDefinition.cdxml':['PropertyName="LocalUsers"'],
      SDK/'um/fwpmu.h':['FWPM_LAYER_ALE_AUTH_CONNECT_V4','FWPM_LAYER_ALE_AUTH_CONNECT_V6','FWPM_LAYER_ALE_AUTH_RECV_ACCEPT_V4','FWPM_LAYER_ALE_RESOURCE_ASSIGNMENT_V4','FWPM_LAYER_ALE_AUTH_LISTEN_V4','FWPM_CONDITION_ALE_USER_ID','FWPM_CONDITION_ALE_REMOTE_USER_ID','FWPM_CONDITION_IP_REMOTE_ADDRESS','FWPM_CONDITION_IP_REMOTE_PORT','FwpmFilterAdd0','FwpmTransactionCommit0','FwpmGetAppIdFromFileName0'],
      SDK/'shared/fwpmtypes.h':['FWPM_FILTER_FLAG_PERSISTENT','FWPM_FILTER_FLAG_BOOTTIME','FWPM_FILTER_FLAG_CLEAR_ACTION_RIGHT','FWPM_SESSION_FLAG_DYNAMIC'],
      SDK/'shared/fwptypes.h':['FWP_ACTRL_MATCH_FILTER','FWP_ACTION_BLOCK','FWP_ACTION_PERMIT','FWP_CONDITION_FLAG_IS_LOOPBACK','FWP_MATCH_NOT_EQUAL','FWP_SECURITY_DESCRIPTOR_TYPE'],
      SDK/'um/processthreadsapi.h':['CreateProcessAsUserW('],
      SDK/'um/WinBase.h':['CreateProcessWithLogonW(','LOGON_NETCREDENTIALS_ONLY'],
      SDK/'um/taskschd.h':['TASK_LOGON_PASSWORD','TASK_LOGON_S4U','TASK_RUNLEVEL_LUA'],
      SDK/'um/winnt.h':['JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE']}
    excerpts=[]
    for p,needles in selectors.items():
        b=p.read_bytes();ls=b.decode('utf-8-sig').splitlines();paths.add(p)
        hits=[]
        for needle in needles:
            matches=[i for i,s in enumerate(ls) if needle in s]
            hits.append({'selector':needle,'matches':[{'line':i+1,'excerpt':'\n'.join(ls[max(0,i-1):min(len(ls),i+3)])} for i in matches[:3]]})
        excerpts.append({**pathrow(p),'selectors':hits,'meaning':'Declaration/schema existence only, no live enforcement test'})
    save('windows_static_evidence.json',{'files':excerpts,
        'no_policy_or_service_query':True,'windows_api_calls':0,
        'not_proven':['LocalUser outgoing non-IPsec semantics','Firewall Block/Allow runtime','WFP arbitration and loopback coverage','BFE crash/boot persistence'],
        'source_search_access_denied':{'path':r'C:\Windows\System32\wbem\MOF','action':'bounded filename discovery','result':'access denied, no escalation or bypass'},
        'local_firewallapi_mof_inspection':'Contains WPP EventTrace metadata, not operational rule precedence documentation'})
    rows=[pathrow(p) for p in sorted(paths)]
    save('inputs_before.json',{'task_id':OUT.name,'created_utc':datetime.now(timezone.utc).isoformat(),
        'source_pin_coordinator_only':'25f62e33e9e094e1c4613818ce168890863b3431',
        'inputs':rows,'raw_private_config_copies':False})
    b=CARD.read_bytes()
    with (OUT/'card_before.md').open('xb') as f:f.write(b)
    a=b.index('# БЛОК 1'.encode());z=b.index('# БЛОК 2'.encode(),a+1)
    with (OUT/'assignment.md').open('xb') as f:f.write(b[a:z])
    m=json.loads((CLAUDE/'manifest.json').read_text());files=m['files'];results=[]
    assert isinstance(files,dict)
    for name,x in files.items():
        p=CLAUDE/name
        assert p.resolve().is_relative_to(CLAUDE.resolve())
        b=p.read_bytes();results.append({'path':name,'bytes_match':len(b)==x['bytes'],'sha256_match':sha(b)==x['sha256']})
    prior=json.loads((ROOT/'reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/rules_read.json').read_text())['rules']
    rules=[]
    for x in prior:
        p=ROOT/x['source'];s=p.read_text(encoding='utf-8-sig');a=s.index(x['selector']);z=s.find('\n## ',a+1);block=s[a:z if z>=0 else len(s)].strip()
        rules.append({'id':x['rule_id'],'path':x['source'],'source_sha256':sha(p.read_bytes()),'definition_sha256_LF':sha(block.encode()),
            'same_normalized_definition_as_prior':block==x['current_definition'].replace('\r\n','\n').strip()})
    source_name='tunnel-client-runtime-source-v0.0.16.tar.gz'
    locations=[old/'source_input'/source_name,base/'downloads'/source_name]
    docs={name:(ROOT/'Документация'/name).read_text(encoding='utf-8-sig') for name in ['19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md','34_TACTICAL_CONTEXT.md']}
    save('review_evidence.json',{'claude_manifest_validation':results,
        'all_claude_manifest_entries_match':all(x['bytes_match'] and x['sha256_match'] for x in results),
        'rules':rules,'source_archive_addressed_paths':[{'path':str(p),'exists':p.is_file()} for p in locations],
        'separate_claude_WEB10_review_found_in_local_19_34':any('CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001' in s for s in docs.values()),
        'WEB10_firewall_concern_source':'approved current B1 section 4; separate current local review not found',
        'preliminary_read_failure_retained':{'operation':'inspect Claude manifest first entry','error':'KeyError: 0','cause':'files is a dict, not a list','resolution':'inspect schema and iterate named entries; no system/runtime execution'},
        'evidence_classes':{'L':'local bytes/static declarations/help','C':'coordinator statement','K':'known documented semantics recalled, not fresh official-document read','P':'design/inference','N':'requires native/system verification'},
        'network_native_or_system_tests_executed':0})
    print(json.dumps({'protected_files':len(rows),'claude_manifest_entries':len(results),'all_match':all(x['sha256_match'] and x['bytes_match'] for x in results),
         'rule_definitions':len(rules),'changed_normalized_rules':[x['id'] for x in rules if not x['same_normalized_definition_as_prior']]},ensure_ascii=False))

def seal():
    # Initial complete report/manifest precede rotation; later seal adds rotation receipt.
    rows=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name!='manifest.json':
            data=p.read_bytes()
            if p.suffix=='.json':json.loads(data.decode('utf-8-sig'))
            if p.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
            rows.append({'path':p.name,'bytes':len(data),'sha256':sha(data)})
    manifest={'task_id':OUT.name,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','kind':'analysis only; 0 runtime/network/system tests',
      'created_utc':datetime.now(timezone.utc).isoformat(),'files':rows,'self_hash':'excluded from own file list','publication':'LOCAL ONLY / USER PUBLICATION NOT VERIFIED'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in rows:
        b=(OUT/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
    print(json.dumps({'manifest_entries_verified':len(rows),'total_files':len(rows)+1,'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'report_sha256':sha((OUT/'report.md').read_bytes())}))

def integrity():
    rows=[]
    for x in read('inputs_before.json')['inputs']:
        p=Path(x['path']);p=p if p.is_absolute() else ROOT/p;h=sha(p.read_bytes())
        rows.append({**x,'final_sha256':h,'unchanged':h==x['sha256']})
    ordinary=[x for x in rows if not x['authorized_change']]
    assert all(x['unchanged'] for x in ordinary),'Protected input drift; investigate, never overwrite'
    save('integrity.json',{'protected_noncard':len(ordinary),'unchanged_noncard':len(ordinary),
        'own_card_authorized_rotation':True,'files':rows})
    print(json.dumps({'noncard_unchanged':len(ordinary),'authorized_card_changed':sum(not x['unchanged'] for x in rows if x['authorized_change'])}))

def rotate():
    if (OUT/'card_rotation.json').exists():raise RuntimeError('Do not repeat recorded rotation')
    before=(OUT/'card_before.md').read_bytes()
    assert CARD.read_bytes()==before,'CARD DRIFT: stop only rotation'
    initial_manifest=read('manifest.json')
    for x in initial_manifest['files']:
        b=(OUT/x['path']).read_bytes();assert sha(b)==x['sha256'] and len(b)==x['bytes']
    protected=[x for x in read('inputs_before.json')['inputs'] if not x['authorized_change']]
    for x in protected:
        p=Path(x['path']);p=p if p.is_absolute() else ROOT/p
        assert sha(p.read_bytes())==x['sha256'],'Protected source drift'
    a=before.index('# БЛОК 1'.encode());z=before.index('# БЛОК 2'.encode(),a+1)
    prefix=before[:a];assignment=before[a:z];history=before[z:]
    assert assignment==(OUT/'assignment.md').read_bytes()
    nl='\r\n' if b'\r\n' in before else '\n'
    def enc(s):return s.replace('\n',nl).encode()
    full_b2=enc('# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА\n\n')+assignment+enc('\nПринятые AMENDMENT: отсутствуют; команда запуска соответствует полной постановке.\n\n---\n\n')
    factual=f'''# БЛОК 3 — FACTUAL RESULT / HANDOFF

TASK: CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001; Codex 007; 2026-10-19.
**RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
Вердикт: принять SID/background-launch как архитектурные принципы; P1 недостаточен,
P2 не доказан. Кандидат T1 без VM: два SID, непересекающиеся user-mode WFP deny
predicates, exact loopback endpoint, dedicated HTTP CONNECT broker с remote pin.
Требуют проверки SID/layer/loopback/arbitration, BFE/boot/existing flows,
receiver/port takeover, DNS/system delegation; для T2 стандартной учётки мало.
Обязательность VM для эксплуатации не утверждается; ordinary UI остаётся
отдельным process/network scope. Health :0 означает ephemeral listener.

Факты: 9/9 Claude manifest file size/hash matches; 9 Windows SDK/CDXML source
files прочитаны статически, не Windows API tests. 17 rule definitions сверены,
16 без текстовых изменений и одна уточнённая норма own-card rotation.
Fresh protected baseline 207 files; {len(protected)}/{len(protected)} noncard hashes сверены до ротации,
конечная сверка — integrity.json. Новых runtime/system/network/native tests 0;
старые suites не повторялись. Git/GitHub, Windows/V2Ray/ACL/VM mutations 0.

OS-ENFORCED EGRESS ISOLATION NOT VERIFIED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED

Report/manifest/evidence: reports/CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001/
report.md, manifest.json, windows_static_evidence.json, review_evidence.json,
inputs_before.json, integrity.json, card_rotation.json. Полная постановка выше
в B2, прежняя история ниже сохранена дословно; B1 очищается после staged readback.
DOC IMPACT: task folder + own rotation only. SHARED DOC DELTA для 19/34 включена
в report section J, общие документы и Claude/LLM12 не изменены.
NEXT/PROPOSAL: один bounded implementation/proof package в независимой offline
лаборатории после exact source handoff и отдельного USER GO; native/live/E2E
имеют отдельные gates. Публикует и передаёт WEB_10 пользователь, не агент.

---

'''
    full_b3=enc(factual)
    tail=full_b2+full_b3+enc('# АРХИВ ПРЕЖНИХ БЛОКОВ 2–3 — сохранено дословно при CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001\n\n')+history
    result={'task_id':OUT.name,'status':'CARD ROTATION BLOCKED','before_sha256':sha(before),
        'report_saved_before_rotation_sha256':sha((OUT/'report.md').read_bytes()),
        'manifest_saved_before_rotation_sha256':sha((OUT/'manifest.json').read_bytes()),
        'authority':'assignment.md sections 11/14; latest user startup instruction',
        'card_rules_modified':False}
    def replace(expected,new):
        if sha(CARD.read_bytes())!=expected:raise RuntimeError('CARD DRIFT BEFORE REPLACE')
        pending=OUT/'card_rotation.pending'
        with pending.open('xb') as f:f.write(new);f.flush();os.fsync(f.fileno())
        if sha(CARD.read_bytes())!=expected:raise RuntimeError('CARD DRIFT AT COMMIT')
        os.replace(pending,CARD)
        assert CARD.read_bytes()==new,'Readback failure'
    try:
        stage=prefix+assignment+tail
        replace(sha(before),stage)
        check=CARD.read_bytes()
        assert check.endswith(history) and full_b2 in check and full_b3 in check
        assert check[len(prefix):len(prefix)+len(assignment)]==assignment
        result.update(b2_b3_readback_before_b1_clear=True,staged_sha256=sha(stage),
            previous_history_bytes=len(history),previous_history_sha256=sha(history))
        final=prefix+enc('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n')+tail
        replace(sha(stage),final)
        check=CARD.read_bytes();aa=check.index('# БЛОК 1'.encode());zz=check.index('# БЛОК 2'.encode(),aa+1)
        assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in check[aa:zz] and OUT.name.encode() not in check[aa:zz]
        assert check.endswith(history) and full_b2 in check and full_b3 in check and check[:len(prefix)]==prefix
        result.update(status='CARD ROTATION VERIFIED',final_sha256=sha(check),
            full_assignment_preserved=True,previous_history_byte_exact=True,b1_waiting=True,
            prefix_rules_byte_exact=True,limitation='Hash-guarded atomic replaces; not a universal lock against unrelated editors')
    except Exception as exc:
        result.update(error=type(exc).__name__,reason=str(exc),actual_card_sha256=sha(CARD.read_bytes()))
        raise
    finally:save('card_rotation.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    {'collect':collect,'seal':seal,'integrity':integrity,'rotate':rotate}[sys.argv[1]]()
