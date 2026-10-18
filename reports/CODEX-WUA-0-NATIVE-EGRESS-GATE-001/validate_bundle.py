"""Offline evidence/source/hash validation; only writes this TASK report folder."""
import ast
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]


def load(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    target=OUT/name
    assert target.parent==OUT
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    before=load('inputs_before.json');rows=[]
    for item in before['inputs']:
        path=Path(item['path']);path=path if path.is_absolute() else ROOT/path
        current=sha(path) if path.is_file() else None
        rows.append({'path':item['path'],'before_sha256':item['sha256'],
                     'after_sha256':current,'unchanged':current==item['sha256']})
    assert len(rows)==122 and all(x['unchanged'] for x in rows),'PROTECTED INPUT DRIFT'
    prior=[x for x in rows if any('/'+p+'/' in x['path'] for p in ('v2ray_preflight_20261017','native_client_offline_20261017','http_socks_adapter_20261018'))]
    assert len(prior)==105
    save('integrity.json',{'protected_files':len(rows),'unchanged':122,'drift':[],'files':rows,
                           'scope':'File-hash evidence; not whole-OS/process/network attestation.'})
    config=next(x for x in rows if x['path'].endswith('config.toml'))
    assert config['after_sha256']=='2a1745afe7818f69f564ea36d58f17adb1653edec9e711e3e1c8f8ee97565aa2'
    card=next(x for x in rows if x['path'].endswith('000_Задачи Codex.md'))
    assert card['after_sha256']=='7d2e8a1ef2d5943cc2e289aacaa5a4075d37d0f68cd65fc1c1fbf3cb79328576'
    old=ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001'
    assert 'HOSTED_TUNNEL_ON_HOLD_BY_USER' in (old/'secure_tunnel_preparation/start_tunnel.py').read_text(encoding='utf-8')
    assert sha(old/'secure_tunnel_preparation/tools/tunnel-client.exe')=='4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571'
    result=load('attempt01_results.json');checks=load('checks.json');sdk=load('windows_source_evidence.json')
    assert result['collected']==result['executed']==result['counts']['PASS']==22
    assert result['counts']=={'PASS':22,'FAIL':0,'ERROR':0,'SKIP':0}
    assert not result['ports_remaining'] and not result['worker_leaks'] and result['unexpected_guard_denials']==0
    assert result['expected_guard_denials']==len(result['guard_denials'])==2
    assert {x['event'] for x in result['guard_denials']}=={'socket.connect','subprocess.Popen'}
    assert len(result['socket_trace'])==18 and sum(x['allowed'] for x in result['socket_trace'])==17
    assert all(x['host']=='127.0.0.1' and x['port'] not in (10808,10813,10814) for x in result['socket_trace'])
    assert collections.Counter(x['event'] for x in result['api_events'])=={'socket.connect':18,'subprocess.Popen':1}
    assert all(not r['observed']['fixture_errors'] and r['observed']['gate_sockets_remaining']==0 for r in result['cases'])
    assert result['actual_native_processes_created']==result['native_tunnel_client_runs']==0 and not result['prior_suites_rerun']
    for file,digest in result['source_sha256'].items():assert sha(OUT/file)==digest
    for file,digest in result['fixture_dependency_sha256'].items():assert sha(old/'http_socks_adapter_20261018'/file)==digest
    assert sum(len(h['selectors']) for h in sdk['sdk_headers'])==22
    for header in sdk['sdk_headers']:
        assert sha(Path(header['path']))==header['sha256']
        assert all(s['present'] for s in header['selectors'])
    python=sdk['subprocess_python_source']
    assert sha(Path(python['path']))==python['sha256'] and python['audit_precedes_create']
    assert checks['check_rows']==27 and checks['counts']==dict(collections.Counter(x['status'] for x in checks['checks']))=={'PASS':15,'BLOCKED':6,'NOT RUN':6}
    for item in checks['checks']:
        assert all((OUT/name).is_file() for name in item['evidence'].split(';'))
    assert load('source_pack_search.json')['status']=='SOURCE PACK BLOCKED'
    assert load('native_gate_decision.json')['status']=='BLOCKED' and not load('native_gate_decision.json')['native_executor_implemented']
    report=(OUT/'report.md').read_text(encoding='utf-8')
    assert all(status in report for status in checks['statuses'])
    syntax=[];jsons=[];scanned=[];issues=[]
    for path in sorted(OUT.iterdir()):
        assert path.is_file() and not path.is_symlink(),'Unexpected directory or symlink'
        assert path.suffix in ('.md','.json','.py','.txt'),'Unexpected artifact extension'
        text=path.read_text(encoding='utf-8-sig');scanned.append(path.name)
        if path.suffix=='.py':
            ast.parse(text,filename=str(path));syntax.append({'path':path.name,'sha256':sha(path),'status':'PASS'})
        if path.suffix=='.json':json.loads(text);jsons.append(path.name)
        for pattern in (r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}',r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'):
            if re.search(pattern,text):issues.append(path.name)
    assert not issues,'Potential secret pattern in artifacts'
    ignore=[]
    for parent in (ROOT,ROOT/'reports',OUT):
        path=parent/'.gitignore'
        if path.is_file():ignore.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path),'text':path.read_text(encoding='utf-8')})
    save('publication_precheck.json',{'method':'Plain project ignore-file read only; no Git/status/index/global excludes',
                                     'project_ignore_files':ignore,'known_rules_review':'New report folder and text/source extensions not excluded by observed project rules',
                                     'local_only':True,'user_prepublication_check_required':True})
    save('artifact_validation.json',{'status':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     'protected_inputs_unchanged':122,'previous_am05_am06_am07_preserved':105,
                                     'json_parsed':jsons,'syntax':syntax,'text_scans':len(scanned),'secret_pattern_issues':issues,
                                     'secret_scan_limit':'Bounded pattern scan + manual review, not a general DLP guarantee',
                                     'tests':'22/22 new reference only','socket_attempts':18,'expected_python_denials':2,
                                     'native_runs':0,'sdk_header_sources_stable':True,'manifest_self_hash_excluded':True})
    files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.iterdir()) if p.name!='manifest.json']
    save('manifest.json',{'task_id':'CODEX-WUA-0-NATIVE-EGRESS-GATE-001','date':'2026-10-18',
                          'scope':'reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/',
                          'status':'RESEARCH PARTIAL / RESULT READY / NATIVE EXECUTION BLOCKED / AWAITING INDEPENDENT REVIEW',
                          'statuses':checks['statuses'],'source_pack':'SOURCE PACK BLOCKED','publication':'LOCAL ONLY / NOT PUBLISHED BY CODEX',
                          'source_revision':'Local byte hashes; coordinator statements only; no agent Git/GitHub verification',
                          'fixture_dependencies':result['fixture_dependency_sha256'],'manifest_self_hash':'Excluded; handed off separately','files':files})
    sealed=load('manifest.json')
    assert {p.name for p in OUT.iterdir() if p.name!='manifest.json'}=={x['path'] for x in sealed['files']}
    for item in sealed['files']:
        path=OUT/item['path'];assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
    print(json.dumps({'status':'PASS','files_covered':len(files),'total_files':len(files)+1,
                      'report_sha256':sha(OUT/'report.md'),'manifest_sha256':sha(OUT/'manifest.json'),
                      'protected_unchanged':122,'prior_artifacts_unchanged':105,'new_reference_tests':'22/22 PASS',
                      'native_execution':'BLOCKED / 0 RUNS','card_rotation':'NOT APPLIED (report-only write_scope)'}))


if __name__=='__main__':main()
