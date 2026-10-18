"""One explicitly authorized own-card rotation. No Git, network, subprocess or native client.

Two atomic replacements, each preceded by a byte-hash guard. B1 is cleared only
after B2+B3+historic tail readback. This is not a cross-editor distributed lock.
"""
from pathlib import Path
import hashlib
import json
import os
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
CARD=ROOT/'Документация/000_Задачи Codex.md'
TASK=OUT.name
STATUSES=[
 'OFFICIAL SOURCE PACK BLOCKED','LOCAL SOURCE AUDIT PARTIAL','VM PLATFORM INVENTORY PARTIAL',
 'OFFLINE VM DESIGN PARTIAL','ISOLATION PREFLIGHT CONTRACT PARTIAL','OS/HYPERVISOR ISOLATION NOT VERIFIED',
 'NATIVE CLIENT EXECUTION NOT STARTED','NATIVE CLIENT FAIL-CLOSED NOT VERIFIED',
 'V2RAY REMOTE ROUTE NOT VERIFIED','HOSTED TUNNEL NOT STARTED','ORDINARY CHAT E2E NOT VERIFIED']

def sha(b):return hashlib.sha256(b).hexdigest()
def replace_guarded(expected,data):
    assert CARD.resolve()==(ROOT/'Документация/000_Задачи Codex.md').resolve()
    if sha(CARD.read_bytes())!=expected:raise RuntimeError('CARD_DRIFT: stop only rotation')
    pending=OUT/'card_rotation.pending'
    with pending.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    if sha(CARD.read_bytes())!=expected:raise RuntimeError('CARD_DRIFT_BEFORE_REPLACE')
    # Source and destination are on the same workspace volume; only own card is replaced.
    os.replace(pending,CARD)
    if CARD.read_bytes()!=data:raise RuntimeError('CARD_READBACK_MISMATCH')

def main():
    record=OUT/'card_rotation.json'
    if record.exists():raise RuntimeError('Refuse to rerun completed/recorded rotation')
    before=(OUT/'card_before.md').read_bytes()
    expected=next(x['sha256'] for x in json.loads((OUT/'inputs_before.json').read_text())['inputs'] if x['authorized_change'])
    assert sha(before)==expected
    report=(OUT/'report.md').read_bytes()
    assert b'RESULT READY' in report and all(s.encode() in report for s in STATUSES)
    for name in ['source_pack_preflight.md','host_vm_inventory.md','vm_platform_comparison.md','offline_vm_design.md',
                 'isolation_preflight_contract.md','native_offline_test_plan.md','rollback_plan.md','manual_engineering_review.md','preflight_decision.json']:
        assert (OUT/name).is_file(), name
    result={'task_id':TASK,'created_utc':datetime.now(timezone.utc).isoformat(),
            'backup':'card_before.md','before_sha256':expected,
            'completed_report_saved_before_rotation_sha256':sha(report),
            'authority':'user_go_card_rotation.md','status':'CARD ROTATION BLOCKED'}
    try:
        if CARD.read_bytes()!=before:raise RuntimeError('CARD_DRIFT_SINCE_BASELINE')
        b1=b'# '+ 'БЛОК 1'.encode();b2=b'# '+ 'БЛОК 2'.encode()
        a=before.index(b1);z=before.index(b2,a+len(b1))
        prefix=before[:a];assignment=before[a:z];history=before[z:]
        assert assignment.decode('utf-8-sig').replace('\r\n','\n')==(OUT/'assignment.md').read_text(encoding='utf-8-sig').replace('\r\n','\n')
        nl='\r\n' if b'\r\n' in before else '\n'
        def enc(s):return s.replace('\n',nl).encode('utf-8')
        old='- После исполнения: сохранить полную утверждённую постановку в БЛОКЕ 2, factual result — в БЛОКЕ 3; только затем очистить БЛОК 1 до ожидания. Канонические журналы обновляются после независимого PASS, не на основании самопроверки Codex.'
        new='- После каждого завершённого исполнения TASK, включая PARTIAL/BLOCKED с готовым полным итоговым отчётом, обязательна безопасная ротация собственной карточки: сохранить полную утверждённую постановку и все AMENDMENT в БЛОКЕ 2, factual result, статусы, проверки и evidence — в БЛОКЕ 3; проверить сохранность обоих блоков и прежней истории, только затем очистить БЛОК 1 до `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Для текущей CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001 адресная запись в собственную карточку сверх основного write_scope разрешена прямым USER GO; для следующих TASK явно закреплять это право при выдаче scope. При невозможности безопасной ротации сохранить отчёт и явно указать `CARD ROTATION BLOCKED`; не маскировать незавершённое исполнение под завершённое. Канонические журналы обновляются после независимого PASS, не на основании самопроверки Codex.'
        assert prefix.count(old.encode())==1
        newprefix=prefix.replace(old.encode(),new.encode(),1)
        amendment=(OUT/'user_go_card_rotation.md').read_text(encoding='utf-8').rstrip()+'\n'
        newb2=enc('# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА\n\n')+assignment+enc('\n## Принятые дополнения к постановке\n\n'+amendment+'\n---\n\n')
        factual=f'''# БЛОК 3 — FACTUAL RESULT / HANDOFF

TASK: `{TASK}`; Codex 007; 2026-10-18.
**PARTIAL / RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
Разрешённая offline-подготовка завершена; внешний native/VM gate BLOCKED.

```text
'''+ '\n'.join(STATUSES)+'''
```

Read-only inventory: Windows 10 Pro x64 build 19045; CPU virtualization/SLAT=true;
HypervisorPresent=false. В bounded sources не найдены ready VM platform,
Windows media и exact source archive. Fresh ZIP/cached checksums/EXE identity
совпали; source→binary build proof остаётся OPEN. Сохранены conditional zero-NIC
Hyper-V VM design, I01–I12 contract, 16 NOT RUN native cases, owned rollback и
manual adversarial review. Native executions/VM creation/network probes = 0.
Previous 19/19, 5/5, 36/36, 22/22 suites не повторялись. Fresh protected baseline
151 файл; кроме авторизованной own card изменения не предусмотрены, конечная
сверка и точные evidence counts — checks.json/integrity.json/bundle_validation.json.

Report/evidence: `reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/report.md`,
`manifest.json`, `host_inventory.json`, `local_file_inventory.json`,
`provenance.json`, `preflight_decision.json`, `card_rotation.json` в той же папке.
Прямое USER GO разрешает own-card rule clarification/rotation; исходная карточка
сохранена в card_before.md; полная B1 + дополнение — выше в B2; прежняя история
ниже сохранена дословно. B1 очищается только после readback B2/B3.
DOC IMPACT: own card + task report only; shared delta для WEB_10 подготовлена,
общие документы не изменены. Git/GitHub и прямая отправка в чаты не выполнялись.
NEXT/PROPOSAL: передача exact source archive и trusted offline lab platform/media;
отдельный provisioning scope, independent isolation review, затем отдельный
USER GO на exact native cases. Самостоятельная независимая приёмка не объявлена.

---

'''
        newb3=enc(factual)
        historic_marker=enc('# АРХИВ ПРЕЖНИХ БЛОКОВ 2–3 — сохранено дословно при '+TASK+'\n\n')
        tail=newb2+newb3+historic_marker+history
        staged=newprefix+assignment+tail
        replace_guarded(expected,staged)
        observed=CARD.read_bytes()
        assert observed==staged and observed.endswith(history)
        assert newb2 in observed and newb3 in observed
        assert observed[len(newprefix):len(newprefix)+len(assignment)]==assignment
        result.update(staged_sha256=sha(staged),b2_b3_saved_and_read_back_before_b1_clear=True,
                      history_bytes=len(history),history_sha256=sha(history),assignment_sha256=sha(assignment))
        final=newprefix+enc('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n')+tail
        replace_guarded(sha(staged),final)
        after=CARD.read_bytes()
        first_b1=after.index(b1);first_b2=after.index(b2,first_b1+len(b1))
        active=after[first_b1:first_b2].decode('utf-8')
        assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ' in active and TASK not in active
        assert after.endswith(history) and newb2 in after and newb3 in after
        assert assignment in newb2 and enc(amendment) in newb2
        result.update(status='CARD ROTATION VERIFIED',final_sha256=sha(after),
                      full_assignment_and_amendment_preserved=True,previous_history_byte_exact=True,
                      b1_waiting=True,own_rules_changes=1,other_cards_touched=False,
                      note='Verified local rotation, not independent task acceptance; hash guards are not a universal cross-editor lock.')
    except Exception as e:
        result.update(error_type=type(e).__name__,reason=str(e),actual_card_sha256=sha(CARD.read_bytes()))
        raise
    finally:
        with record.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
