"""H34 package hashes/readback only; no Git, network, credentials or task rotation."""
from pathlib import Path
import ast,difflib,hashlib,json
PKG=Path(__file__).resolve().parent;ROOT=PKG.parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
saved=json.loads((PKG/'preservation.json').read_text(encoding='utf-8'))
backup=Path(saved['backup'])
assert all(sha(backup/n)==h for n,h in saved['before'].items())
assert all(sha(ROOT/n)==h for n,h in saved['protected'].items())
engineering=[n for n,h in saved['before'].items() if n.endswith('.py') and sha(ROOT/n)!=h]
engineering+=['gigachat_admission.py','test_gigachat_admission.py']
matrix={n:dict(before=saved['before'].get(n),after=sha(ROOT/n)) for n in engineering}
patch=[]
for n in engineering:
    before=(backup/n).read_text(encoding='utf-8').splitlines(True) if n in saved['before'] else []
    after=(ROOT/n).read_text(encoding='utf-8').splitlines(True)
    ast.parse(''.join(after),filename=n)
    patch.extend(difflib.unified_diff(before,after,fromfile='before/'+n,tofile='after/'+n))
(PKG/'evidence/source_changes.patch.txt').write_text(''.join(patch),encoding='utf-8')
(PKG/'evidence/source_matrix.json').write_text(json.dumps(matrix,indent=2),encoding='utf-8')
stages=['clean_legacy','post_review','oracle_final','final_h33','post_s1','post_s2','post_quality','sealed_mutations','node','sealed_server_gates']
results={}
for stage in stages:
    value=json.loads((PKG/f'evidence/{stage}.result.json').read_text(encoding='utf-8'))
    assert value.get('exit_code',0)==0 and value.get('runner_exit_code',0)==0
    assert value.get('unexpected_guard_denials',0)==0
    assert not value.get('isolation_violations',[])
    if 'gate' in value:assert value['gate']['status']=='PASS'
    if stage=='sealed_mutations':
        assert len(value['cases'])==3 and all(c['observed']=='RED' and c['failures']>0 and c['errors']==0 for c in value['cases'])
        assert all(sha(ROOT/n)==h for n,h in value['source_files_unchanged'].items())
    if stage=='sealed_server_gates':assert value['compile']['ok'] and value['ui_smoke']['ok'] and value['guard_denials']==0
    results[stage]={k:value[k] for k in ('exit_code','pytest_exit_code','runner_exit_code','command','counts','gate','status',
        'guard_denials','expected_guard_denials','unexpected_guard_denials','elapsed_seconds') if k in value}
trace=json.loads((PKG/'evidence/post_s1.physical_trace.json').read_text())['admitted_requests']
assert len(trace)==20 and all(r['state']=='SENT' for r in trace)
assert len({r['route'] for r in trace})==9
history_path=PKG/'task_record.json'
history=json.loads(history_path.read_text(encoding='utf-8'))['history_id'] if history_path.exists() else None
files=[*engineering,*[n for n in saved['before'] if not n.endswith('.py')]]
files+=sorted(p.relative_to(ROOT).as_posix() for p in PKG.rglob('*') if p.is_file()
              and p.name!='manifest.json' and p.suffix!='.log' and '__pycache__' not in p.parts)
entries=[dict(path=n,bytes=(ROOT/n).stat().st_size,sha256=sha(ROOT/n),before_sha256=saved['before'].get(n),
              purpose='H34 report/evidence/repro/official submission' if n.startswith('reports/') else 'Scoped engineering or official task slot')
         for n in sorted(set(files))]
manifest=dict(task_id=PKG.name,status='SUBMITTED / REVIEW PENDING' if history else 'RESULT READY / AWAITING INDEPENDENT VERIFICATION',
    history_id=history,result='AUTHOR RESULT READY / BOUNDED OFFLINE PASS',
    assigned_base='main@f50d5432228fdfc5ad67999f7620b9fb64bf1a49 / coordinator claim; Git NOT RUN',
    source_before_after=matrix,tests=results,real_enabled=False,real_oauth_external_paid_http=0,Git='NOT RUN',
    backup=saved['backup'],backup_sha_readback='PASS / RETAIN UNTIL INDEPENDENT ACCEPTANCE',protected_unchanged=len(saved['protected']),
    physical_trace=dict(mock_posts=len(trace),logical_routes=9,source_sites=7,real_connections=0),
    warning='One existing combined Tk cleanup warning; physical GUI and independent H34 CI NOT RUN',
    historical_failures='Preserved initial/review_red/contracts1/s1_initial/timeout/legacy guard failures; not accepted PASS',files=entries,
    ignored_local_duplicates=[p.relative_to(ROOT).as_posix() for p in PKG.glob('evidence/*.log')],
    note='Manifest excludes its recursive self hash; raw unittest transcripts have publishable .txt copies')
(PKG/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=manifest['status'],history_id=history,files=len(entries),engineering_files=len(engineering),protected=len(saved['protected']))))
