"""Readback of source, protected user data, launcher and exact card boundaries; build a SHA-256 manifest."""
from pathlib import Path
import hashlib
import json
import sys

REPORT = Path(__file__).resolve().parent
ROOT = REPORT.parents[1]
BASELINE = json.loads((REPORT / 'evidence/baseline_preservation.json').read_text(encoding='utf-8'))
def fingerprint(p):
    data = p.read_bytes()
    return dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())

by_root = {name: dict(checked=0,matching=0) for name in ['.obsidian','.ultra','Чат_pro','Чат_Pro_01']}
changed = []
for old in BASELINE['protected']:
    name = old['path'].split('/')[0]
    counts = by_root.setdefault(name, dict(checked=0, matching=0))
    counts['checked'] += 1
    p = ROOT / old['path']
    now = fingerprint(p) if p.is_file() else None
    if now == {k: old[k] for k in ('size', 'sha256')}:
        counts['matching'] += 1
    else:
        changed.append(dict(path=old['path'],before={k: old[k] for k in ('size','sha256')},after=now))
known = {r['path'] for r in BASELINE['protected']}
added = [p.relative_to(ROOT).as_posix() for name in by_root for p in (ROOT / name).rglob('*')
         if p.is_file() and p.relative_to(ROOT).as_posix() not in known]
out = dict(by_root=by_root,changed=changed,added=added,
           data_roots_match=all(v['checked']==v['matching'] for k,v in by_root.items() if k!='.obsidian'),
           obsidian_writes_by_agent=False,restore_of_external_changes=False)
(REPORT / 'evidence/user_data_readback_final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
assert out['data_roots_match'] and not added, 'Unexpected user-data drift'

card = ROOT / 'Документация/000_Задачи Codex.md'
before = REPORT / 'before/Документация/000_Задачи Codex.md.source.txt'
sys.path.insert(0,str(ROOT/'tools'))
import task_slot_rotate as slots
def outside(content):
    for start,end in [(slots.B1_BEGIN,slots.B1_END),(slots.B11_BEGIN,slots.B11_END)]:
        prefix,found,tail=content.partition(start.encode('utf-8'))
        assert found
        body,found_end,suffix=tail.partition(end.encode('utf-8'))
        assert found_end
        content=prefix+found+b'<BODY>'+found_end+suffix
    return content
card_result = dict(before=fingerprint(before),after=fingerprint(card),
                   outside_slots_identical=outside(before.read_bytes())==outside(card.read_bytes()))
(REPORT / 'evidence/card_boundaries_readback.json').write_text(json.dumps(card_result,indent=2),encoding='utf-8')
assert card_result['outside_slots_identical'], 'Card changed outside the two script-owned slot bodies'

for entry in BASELINE['source']:
    snapshot=REPORT/'before'/entry['path']
    if entry['path'].startswith('Документация/'):
        snapshot=snapshot.with_name(snapshot.name+'.source.txt')
    assert fingerprint(snapshot)=={k:entry[k] for k in ('size','sha256')}, 'Pre-fix snapshot drift'

for name in ['js_regression_final.json','python_core_regression_final.json']:
    checks=json.loads((REPORT/'evidence'/name).read_text(encoding='utf-8'))
    assert checks['exit_code']==0
    for path,row in checks['source'].items():
        assert fingerprint(ROOT/path)==dict(size=row['bytes'],sha256=row['sha256']), 'Source drift after final tests: '+path

paths = [ROOT/r['path'] for r in BASELINE['source']]
paths += sorted(p for p in REPORT.rglob('*') if p.is_file() and p.name!='manifest.json')
entries = [dict(path=p.relative_to(ROOT).as_posix(),**fingerprint(p)) for p in paths]
manifest = dict(task_id='CODEX-WUA-CHAT-UX-LIVE-FIX-001',status='PARTIAL / SLOT FINISH BLOCKED; UI FIX READY / AWAITING INDEPENDENT VERIFICATION',
                source_basis='exact local pre-fix bytes in before/; no Git read',
                hash='SHA-256',files=entries,
                exclusions=['manifest.json (self-reference)'],
                user_data_contents_in_package=False)
(REPORT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for entry in entries:
    assert fingerprint(ROOT/entry['path'])=={k:entry[k] for k in ('size','sha256')}
print(json.dumps(dict(manifest_entries=len(entries),user_data=out,card=card_result),ensure_ascii=False))
