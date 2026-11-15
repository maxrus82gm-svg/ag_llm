"""Seal the H37 review correction; preserve prior evidence and shared sources."""
from pathlib import Path
import hashlib
import json

REV = Path(__file__).resolve().parent
PKG = REV.parent
ROOT = PKG.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


baseline = json.loads((REV / 'package_before.json').read_text('utf-8'))
changed = {name for name, digest in baseline.items() if sha((PKG / name).read_bytes()) != digest}
allowed = {'accounting_oracle.py', 'report.md', 'provider-contract.md', 'real-readiness.md',
           'manual-review.md', 'safety-matrix.md', 'task_record.json', 'manifest.json'}
assert not changed - allowed, sorted(changed - allowed)
for name in changed - {'manifest.json'}:
    saved = REV / 'before' / (name + '.txt')
    assert sha(saved.read_bytes()) == baseline[name], name
protected = json.loads((REV / 'protected_before.json').read_text('utf-8'))
assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in protected.items())
record = json.loads((PKG / 'task_record.json').read_text('utf-8'))
assert record['history_id'] == 'H-CODEX-000037'
for version in [record, *record['previous']]:
    for ref in version['sources'].values():
        assert sha((ROOT / ref['path']).read_bytes()) == ref['sha256']
for name in ('accounting_corrected_final', 'accounting_s2_recheck', 'accounting_hold_recheck'):
    result = json.loads((PKG / 'evidence' / (name + '.result.json')).read_text('utf-8'))
    assert result['exit_code'] == 0
    assert result.get('unexpected_guard_denials', 0) == 0
assert json.loads((PKG / 'evidence/accounting_expected_red.result.json').read_text('utf-8'))['exit_code'] == 1
compile((PKG / 'accounting_oracle.py').read_text('utf-8'), 'accounting_oracle.py', 'exec')
status = dict(task_id=PKG.name, history_id=record['history_id'],
              correction='AUTHOR CORRECTION READY / INDEPENDENT REVIEW PENDING',
              cached_accounting='COMPATIBLE; previous blocker WITHDRAWN',
              ordinary_cached_forwarding='optional field not forwarded; conservative reservation fallback',
              real='HOLD / NOT RUN', git='READ ONLY USER GO / correction UNCOMMITTED',
              git_readback=json.loads((REV / 'git-readback.json').read_text('utf-8')),
              protected_files=len(protected), shared_runtime_changes=[],
              original_artifacts_unchanged=len(baseline) - len(changed),
              previous_report_hash_verified=True, slot_and_sequence_unchanged=True,
              changed_package_files=sorted(changed), original_red_retained=True)
(PKG / 'correction_closeout.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
manifest = json.loads((REV / 'before/manifest.json.txt').read_text('utf-8'))
manifest['review_clarification_20261115'] = {**status, 'report': 'accounting-clarification.md',
    'source_urls': ['https://developers.sber.ru/docs/ru/gigachat/guides/counting-tokens',
                    'https://developers.sber.ru/docs/files/openapi/gigachat/api.yml'],
    'historical_accounting_red_classification': 'incorrect original oracle; not a shared formula defect'}
for file in (PKG / 'evidence').glob('accounting_*.result.json'):
    result = json.loads(file.read_text('utf-8'))
    manifest['evidence_results'][file.name] = {k:v for k,v in result.items() if k not in ('cases','guard_events')}
manifest['artifacts'] = {f.relative_to(PKG).as_posix(): dict(bytes=f.stat().st_size, sha256=sha(f.read_bytes()))
    for f in sorted(PKG.rglob('*')) if f.is_file() and f != PKG / 'manifest.json'}
(PKG / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
for name, entry in manifest['artifacts'].items():
    assert sha((PKG / name).read_bytes()) == entry['sha256']
print(json.dumps(dict(history_id=record['history_id'], artifacts=len(manifest['artifacts']),
    shared_runtime_unchanged=len(protected), cached_blocker='WITHDRAWN', real='HOLD'), ensure_ascii=False))
