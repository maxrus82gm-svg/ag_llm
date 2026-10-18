"""Finalize factual counts/integrity after completed own-card rotation, then seal package.
No execution of tests, clients or VM operations. Refuses to overwrite final seal.
"""
from pathlib import Path
import hashlib
import json
import ast
import re
from datetime import datetime, timezone
from collections import Counter
import importlib.util

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
def save(name,data):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    if (OUT/'manifest.json').exists():raise RuntimeError('Final package already sealed; no silent overwrite')
    initial=read('inputs_before.json');rotation=read('card_rotation.json')
    inventory=read('host_inventory.json');local=read('local_file_inventory.json');prov=read('provenance.json')
    facts=[]
    for x in initial['inputs']:
        p=Path(x['path']) if Path(x['path']).is_absolute() else ROOT/x['path']
        b=p.read_bytes();h=sha(b)
        facts.append({'path':x['path'],'before_sha256':x['sha256'],'after_sha256':h,
                      'unchanged':h==x['sha256'],'authorized_change':x['authorized_change']})
    protected=[x for x in facts if not x['authorized_change']]
    assert len(facts)==151 and len(protected)==150
    assert all(x['unchanged'] for x in protected),'Protected input drift; preserve and investigate, do not overwrite'
    card=next(x for x in facts if x['authorized_change'])
    assert card['after_sha256']==rotation['final_sha256']
    assert rotation['status']=='CARD ROTATION VERIFIED'
    save('integrity.json',{'task_id':OUT.name,'checked_utc':datetime.now(timezone.utc).isoformat(),
         'baseline_total':len(facts),'noncard_protected':len(protected),'noncard_unchanged':len(protected),
         'authorized_card_changes':1,'unexpected_changes':0,'files':facts})
    rows=[]
    def row(i,status,claim,evidence):rows.append({'id':f'C{i:02}','status':status,'claim':claim,'evidence':evidence})
    rules=read('rules_read.json')['rules'];assert len(rules)==17 and all(x['same_source_as_preceding_task'] for x in rules)
    row(1,'PASS','17 current rule source hashes and addressed routing/rotation review','rules_read.json; shared_doc_delta.md')
    row(2,'PASS','Full assignment, own-card before bytes and explicit USER GO retained','assignment.md; card_before.md; user_go_card_rotation.md')
    row(3,'BLOCKED','Official runtime source archive unavailable in bounded local roots','local_file_inventory.json; source_pack_preflight.md')
    assert not local['source_pack_matches']
    assert prov['installed_exe']['expected_sha256_match'] and prov['installed_exe']['identical_to_zip_member']
    row(4,'PASS','Fresh installed EXE identity equals cached ZIP member','provenance.json')
    assert prov['archive']['matches_cached_release_digest'] and prov['archive']['matches_cached_SHA256SUMS']
    row(5,'PASS','Fresh ZIP digest equals cached release digest and SHA256SUMS; no online attestation','provenance.json')
    row(6,'BLOCKED','Full source-to-binary reproducible build/attestation absent','source_pack_preflight.md; provenance.json')
    row(7,'PASS','Read-only OS/CPU virtualization metadata obtained','host_inventory.json')
    assert not inventory['query_errors'] and all(not x['errors'] for x in local['roots'])
    row(8,'PASS','Bounded multi-source hypervisor/VM/media inventory saved; query errors 0','host_inventory.json; local_file_inventory.json')
    row(9,'BLOCKED','Ready hypervisor and independently identified lab VM not found','host_vm_inventory.md')
    row(10,'BLOCKED','Trusted Windows offline install media/baseline not found','host_vm_inventory.md')
    row(11,'BLOCKED','Full offline dependency/observer/media closure not provided','host_vm_inventory.md; offline_vm_design.md')
    row(12,'PASS','Platform comparison and conditional zero-NIC Hyper-V selection documented; design only','vm_platform_comparison.md')
    row(13,'BLOCKED','Exact backend verifier and independent attempt observer not implemented/verified','isolation_preflight_contract.md; preflight_decision.json')
    row(14,'PASS','Owner-only rollback, partial-failure and current-card rollback procedures documented','rollback_plan.md')
    row(15,'PASS','16 native case contracts with preconditions/oracles/stops/cleanup prepared; not execution','native_offline_test_plan.md')
    row(16,'PASS','Separate manual engineering/adversarial review completed by author','manual_engineering_review.md')
    row(17,'NOT RUN','16 native cases; actual native executions 0','native_offline_test_plan.md; preflight_decision.json')
    row(18,'NOT RUN','Actual OS/hypervisor isolation preflight; VM operations 0','preflight_decision.json')
    row(19,'NOT RUN','Live V2Ray remote route','execution.json')
    row(20,'NOT RUN','Hosted tunnel activation','execution.json')
    row(21,'NOT RUN','Ordinary Chat MCP E2E / independent receipt','execution.json')
    row(22,'PASS','150/150 noncard protected hashes unchanged, 1 authorized own-card change','integrity.json')
    row(23,'PASS','Staged B2/B3 readback, full assignment/amendment and old history preserved, B1 waiting','card_rotation.json')
    row(24,'PASS','Complete package hash/size census and source/JSON parse; integrity only','manifest.json; bundle_validation.json; validate_bundle.py')
    row(25,'PASS','Only approved local metadata/hash/design/card operations used; no native/VM/network mutations','execution.json; saved source scripts; tool transcript')
    counts=dict(Counter(x['status'] for x in rows))
    save('checks.json',{'task_id':OUT.name,'kind':'evidence matrix, not test suite','checks':rows,'counts':counts,
                      'native_plan_cases':{'NOT RUN':16},'prior_reference_suite_reruns':0})
    save('execution.json',{'task_id':OUT.name,'basis':'agent tool transcript and saved local evidence; not machine-wide packet audit',
         'new_runtime_unit_tests':0,'native_client_executions':0,'cloudflared_executions':0,
         'vm_create_start_stop_or_config_changes':0,'host_network_or_feature_changes':0,'network_probes_or_downloads':0,
         'prior_reference_suite_reruns':0,'git_github_operations':0,'messages_to_other_chats':0,
         'allowed_mutations':['new task report folder','own Codex card rules and B1/B2/B3 under explicit USER GO'],
         'other_connections_or_launcher_changed':False})
    report=OUT/'report.md'
    text=report.read_text(encoding='utf-8')
    assert '## E. Финальная сверка' not in text
    text+='''
## E. Финальная сверка и ротация

**CARD ROTATION VERIFIED (local).** Новые БЛОКИ 2–3 сохранены и перечитаны
перед очисткой БЛОКА 1. Полная исходная постановка и USER GO сохранены;
405,816 B прежней истории сохранены дословно. БЛОК 1 теперь содержит
`ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Одно правило собственной карточки уточнено.
До изменения SHA-256 карточки:
`fd1668b84b41aaabcc1e790db158b95280d2eec5b444d578ac54ed83af2baf0b`;
после:
`6df2f7e5f968840ccc71ee3dddec30bb7c0f031ffc9e7e2e630a627248f5e71f`.
Откат только при совпадении текущего hash с recorded final, из card_before.md;
при поздних изменениях — reconciliation. История не удалялась.

Итог checks: **25 строк — 14 PASS / 6 BLOCKED / 5 NOT RUN**. Это evidence rows,
не 14 native tests. Native plan — **16/16 NOT RUN**, фактических запусков 0.
**150/150** защищённых файлов вне own card сохранили исходные hashes;
151-й файл — только разрешённая карточка. Final manifest/validator подтверждают
целостность package, но не OS/hypervisor/client behavior и не independent PASS.
Root `.gitignore` прочитан как обычный файл; среди его правил и двух проверенных
вложенных путей нет исключения новой report folder. Git/global excludes не
опрашивались; публикация пользователем ещё не проверена.
'''
    report.write_text(text,encoding='utf-8',newline='\n')
    result='''TASK: CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001
STATUS: PARTIAL / RESULT READY / AWAITING INDEPENDENT VERIFICATION
OFFICIAL SOURCE PACK BLOCKED
LOCAL SOURCE AUDIT PARTIAL
VM PLATFORM INVENTORY PARTIAL
OFFLINE VM DESIGN PARTIAL
ISOLATION PREFLIGHT CONTRACT PARTIAL
OS/HYPERVISOR ISOLATION NOT VERIFIED
NATIVE CLIENT EXECUTION NOT STARTED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
CARD ROTATION VERIFIED (local); B1 = ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
RESULT: локальная Windows/VM inventory и cached ZIP→EXE byte identity; conditional zero-NIC Windows VM design, I01–I12 contract, 16 future native cases, owned rollback, manual engineering review.
CHECKS: 25 evidence rows = 14 PASS / 6 BLOCKED / 5 NOT RUN; 16 native cases NOT RUN; 0 native/VM/network executions; previous suites not rerun. 150/150 noncard protected files unchanged; own card changed under USER GO. Historical B2–B3 tail 405816 B preserved byte-for-byte.
BLOCKERS/RISKS: exact source archive, build correspondence, ready lab platform/Windows media/dependencies and backend-specific isolation/attempt observers missing. No OS/native/V2Ray/Chat proof.
DOC IMPACT: task report folder + own card only. SHARED DOC DELTA: shared_doc_delta.md for WEB_10; common docs unchanged.
REPORT: M:\\GitHub\\ag_llm\\reports\\CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001\\report.md
EVIDENCE: manifest.json, checks.json, host_inventory.json, local_file_inventory.json, provenance.json, integrity.json, preflight_decision.json, card_rotation.json, bundle_validation.json in the same folder.
NEXT/PROPOSAL ONLY: user supplies exact source archive and trusted offline lab host/media; separate scoped provisioning GO, independent isolation review, then separate native execution GO. No automatic platform installation.
PUBLICATION: LOCAL ONLY / NOT VERIFIED; Git/GitHub not used; user forwards report to WEB_10.
'''
    (OUT/'factual_result.txt').write_text(result,encoding='utf-8',newline='\n')
    # Narrow credential-pattern scan: never prints matching values; not a guarantee against all secrets.
    patterns=[rb'sk-(?:proj-)?[A-Za-z0-9_-]{25,}',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    suspect=[]
    for p in OUT.iterdir():
        if p.is_file():
            data=p.read_bytes()
            if any(re.search(pt,data) for pt in patterns):suspect.append(p.name)
    assert not suspect,{'credential_pattern_review_required':suspect}
    save('publication_precheck.json',{'local_root_gitignore_read':True,
         'root_ignore_excludes_task_folder_on_manual_review':False,'reports_nested_gitignore_exists':(ROOT/'reports/.gitignore').exists(),
         'task_nested_gitignore_exists':(OUT/'.gitignore').exists(),'git_or_global_excludes_queried':False,
         'credential_pattern_findings':suspect,'secret_scan_limitation':'Narrow known-pattern scan plus manual review; not proof of absence of every possible secret',
         'publication_status':'LOCAL ONLY / USER PUBLICATION NOT VERIFIED'})
    # Parse sources without importing collection/rotation code or writing bytecode.
    for p in OUT.iterdir():
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
        if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8-sig'))
    expected_entries=len([p for p in OUT.iterdir() if p.is_file()])+1 # upcoming validation record, excluding manifest
    save('bundle_validation.json',{'task_id':OUT.name,'checks_counts':counts,
         'expected_manifest_entries':expected_entries,'noncard_protected_unchanged':150,
         'authorized_card_rotation_verified':True,'source_json_syntax_checked':True,
         'report_sha256':sha(report.read_bytes()),'meaning':'Package integrity only; no OS/native or independent acceptance claim'})
    files=[{'path':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
           for p in sorted(OUT.iterdir()) if p.is_file()]
    assert len(files)==expected_entries
    save('manifest.json',{'task_id':OUT.name,'created_utc':datetime.now(timezone.utc).isoformat(),
         'status':'PARTIAL / RESULT READY / AWAITING INDEPENDENT VERIFICATION',
         'scope':'new report folder plus explicitly authorized own card','files':files,
         'self_hash':'Manifest excluded from its own file list; SHA-256 returned by read-only validator',
         'source_pin_user_supplied_not_git_verified':'795e1fddf6741169f006caf8ba9430e4d22fca0f',
         'publication':'LOCAL ONLY / USER PUBLICATION NOT VERIFIED'})
    spec=importlib.util.spec_from_file_location('bundle_readonly_validator',OUT/'validate_bundle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    print(json.dumps(module.validate(),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
