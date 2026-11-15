"""Seal only this authorized package and verify protected local source hashes."""
from pathlib import Path
import hashlib
import json

PKG = Path(__file__).resolve().parent
ROOT = PKG.parents[1]
TASK = PKG.name


def sha(data):
    return hashlib.sha256(data).hexdigest()


before = json.loads((PKG / 'evidence/protected_before.json').read_text('utf-8'))
changed = [name for name, digest in before.items() if sha((ROOT / name).read_bytes()) != digest]
allowed = {'gigachat_transport.py', 'ordinary_gigachat_transport.py', 'Документация/000_Задачи Codex.md'}
assert not set(changed) - allowed, changed
card = ROOT / 'Документация/000_Задачи Codex.md'
old_card = (PKG / 'before/Документация__000_Задачи Codex.md.txt').read_bytes()
tail = '# БЛОК 2 — '.encode()
assert old_card.split(tail, 1)[1] == card.read_bytes().split(tail, 1)[1]
record = PKG / 'task_record.json'
history = json.loads(record.read_text('utf-8')).get('history_id') if record.exists() else None
preserved = dict(checked=len(before), changed=changed, unexpected_changes=[],
                 blocks_2_to_4_unchanged=True, live_requests=0, git_operations=0)
(PKG / 'evidence/preservation_final.json').write_text(json.dumps(preserved, ensure_ascii=False, indent=2), encoding='utf-8')
sources = {}
for name in ('gigachat_transport.py', 'ordinary_gigachat_transport.py', 'test_web_alarm_gigachat_ultra_preflight.py'):
    saved = PKG / 'before' / (name + '.txt')
    sources[name] = dict(before=sha(saved.read_bytes()) if saved.exists() else None,
                         after=sha((ROOT / name).read_bytes()))
results = {f.name: json.loads(f.read_text('utf-8')) for f in (PKG / 'evidence').glob('*.result.json')}
for stage in ('target_revised', 's1_final', 's2_final', 'quality', 'ui'):
    assert results[stage + '.result.json']['exit_code'] == 0, stage
for stage in ('red_contract', 'accounting_expected_red', 'authority_mutation_revised_red'):
    assert results[stage + '.result.json']['exit_code'] == 1, stage
artifacts = {f.relative_to(PKG).as_posix(): dict(bytes=f.stat().st_size, sha256=sha(f.read_bytes()))
             for f in sorted(PKG.rglob('*')) if f.is_file() and f.name != 'manifest.json'}
manifest = dict(task_id=TASK, status='AUTHOR RESULT READY / PARTIAL-BLOCKED / REAL HOLD',
                history_id=history, independent='NOT RUN / REVIEW PENDING', real='HOLD / NOT RUN',
                git='NOT RUN', sources=sources, preservation=preserved,
                evidence_results={name: {k: v for k, v in result.items() if k not in ('cases', 'guard_events')}
                                  for name, result in results.items()}, artifacts=artifacts)
(PKG / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(task_id=TASK, history_id=history, status=manifest['status'], artifacts=len(artifacts),
                      unexpected_changes=preserved['unexpected_changes']), ensure_ascii=False))
