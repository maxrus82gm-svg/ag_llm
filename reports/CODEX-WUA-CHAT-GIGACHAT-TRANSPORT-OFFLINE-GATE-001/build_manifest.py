"""Task-local hash manifest; no Git, network, provider calls or task rotation."""
from pathlib import Path
import difflib
import hashlib
import json

PKG=Path(__file__).resolve().parent
ROOT=PKG.parents[1]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

preserved=json.loads((PKG/'preservation.json').read_text(encoding='utf-8'))
backup=Path(preserved['backup'])
assert all(sha(backup/n)==v for n,v in preserved['before'].items())
assert all(sha(ROOT/n)==v for n,v in preserved['protected'].items())
engineering=[n for n in preserved['before'] if n.endswith('.py')]
engineering+=['ordinary_gigachat_transport.py','test_web_alarm_gigachat_transport.py']
patch=[]
for name in engineering:
    before=(backup/name).read_text(encoding='utf-8').splitlines(True) if name in preserved['before'] else []
    after=(ROOT/name).read_text(encoding='utf-8').splitlines(True)
    patch.extend(difflib.unified_diff(before,after,fromfile='before/'+name,tofile='after/'+name))
(PKG/'evidence/source_changes.patch.txt').write_text(''.join(patch),encoding='utf-8')
matrix={n:dict(before=preserved['before'].get(n),after=sha(ROOT/n)) for n in engineering}
(PKG/'evidence/source_fingerprints.json').write_text(json.dumps(matrix,indent=2),encoding='utf-8')
results={}
for name in ['final_http','regression','s1_confirm','s2_confirm','quality_confirm','mutations','node']:
    value=json.loads((PKG/f'evidence/{name}.result.json').read_text())
    results[name]={k:value[k] for k in ('exit_code','counts','gate','status','expected_guard_denials','guard_denials','unexpected_guard_denials','cases','command') if k in value and k!='cases'}
    assert value.get('exit_code',0)==0
    assert value.get('unexpected_guard_denials',0)==0
record=PKG/'task_record.json'
history=json.loads(record.read_text(encoding='utf-8')).get('history_id') if record.exists() else None
files=engineering+[n for n in preserved['before'] if not n.endswith('.py')]
files+=sorted(p.relative_to(ROOT).as_posix() for p in PKG.rglob('*') if p.is_file()
              and p.name!='manifest.json' and p.suffix!='.log' and '__pycache__' not in p.parts)
entries=[]
for name in sorted(set(files)):
    path=ROOT/name
    entries.append(dict(path=name,bytes=path.stat().st_size,sha256=sha(path),
        before_sha256=preserved['before'].get(name),purpose='Task evidence/report/helper' if name.startswith('reports/') else 'Scoped source/test or official task-slot rotation'))
manifest=dict(task_id=PKG.name,status='SUBMITTED / REVIEW PENDING' if history else 'RESULT READY / AWAITING INDEPENDENT VERIFICATION',
    history_id=history,assigned_base='main@72f2ff53051104fe9b084624a39be5f3dcc5a09a / assignment claim; Git NOT RUN',
    source_before_after=matrix,result='AUTHOR P0 P1 BOUNDED OFFLINE PASS',tests=results,
    real_enabled=False,real_network_oauth_paid_calls=0,independent_ci='NOT RUN',backup=preserved['backup'],
    protected_unchanged=len(preserved['protected']),files=entries,
    ignored_local_duplicates=[p.relative_to(ROOT).as_posix() for p in PKG.glob('evidence/*.log')],
    note='manifest excludes its own recursive hash; ignored .log transcripts have identical publishable .txt copies')
(PKG/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=manifest['status'],history_id=history,files=len(entries),protected=len(preserved['protected']))))
