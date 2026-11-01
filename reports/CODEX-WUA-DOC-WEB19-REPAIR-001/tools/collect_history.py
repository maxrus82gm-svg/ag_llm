"""Addressed historical provenance; records evidence without changing historical owners."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'reports/CODEX-WUA-DOC-WEB19-REPAIR-001'
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(name, obj):
    p = WORK / 'evidence' / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

tasks = {
    '457': 'CLAUDE-WUA-EVM-COMPACT-LAYOUT-001',
    '461': 'CLAUDE-DOC-TASK-SLOT-ROTATION-001',
    '464': 'CLAUDE-WUA-EVM-INTERACTION-DND-001',
    '467': 'CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001',
    '473': 'CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001',
    '475': 'CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001',
    '479': 'CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001',
    '482': 'ASTRA-DOC-CONTEXT-OPTIMIZATION-001',
}
histories = [ROOT / 'Документация/001_История выполненных задач Claude.md', ROOT / 'Документация/001_История выполненных задач Codex.md']
rows = []
for number, task in tasks.items():
    hp = histories[1] if number == '482' else histories[0]
    raw = hp.read_bytes(); ls = raw.decode('utf-8-sig').splitlines()
    found = []
    for i, line in enumerate(ls):
        if line.startswith('## ') and task in line:
            j = next((j for j in range(i+1, len(ls)) if ls[j].startswith('## ')), len(ls))
            value = '\n'.join(ls[i:j])
            found.append({'heading': line, 'first_line': i+1, 'last_line': j, 'excerpt': value, 'excerpt_sha256_utf8_lf': sha(value.encode())})
    assert len(found) == 1, (number, task, len(found))
    package = ROOT / 'reports' / task
    sources = []
    for name in ['report.md', 'manifest.json', 'handoff_task.md']:
        p = package / name
        if p.exists(): sources.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size})
    rows.append({'publication': number, 'task': task, 'history': hp.relative_to(ROOT).as_posix(), 'history_sha256': sha(raw), 'section': found[0], 'package_sources': sources})

p = ROOT / 'reports/CHATGPT-WEB19-S2-INDEPENDENT-WINDOWS-20261101.md'
rows.append({'publication': '481', 'task': tasks['479'], 'history': 'Документация/06_Журнал выполнения и отчёты.md', 'event_id': 'EVT-WEB19-S2-INDEP-WINDOWS-20261101', 'source': p.relative_to(ROOT).as_posix(), 'source_sha256': sha(p.read_bytes()), 'excerpt': p.read_text(encoding='utf-8-sig'), 'note': 'No separate WEB19 event in the addressed personal-history headings; retain journal and standalone report as owners. No invented №001 record.'})
dump('history_sources.json', rows)

manifest = json.loads((ROOT / 'reports' / tasks['479'] / 'manifest.json').read_text(encoding='utf-8'))
pins = []
for name, expected in manifest['changed_files'].items():
    raw = (ROOT / name).read_bytes()
    pins.append({'path': name, 'expected_sha256': expected['sha256'], 'actual_sha256': sha(raw), 'bytes': len(raw), 'matches': sha(raw) == expected['sha256'] and len(raw) == expected['bytes']})
assert all(x['matches'] for x in pins), 'SOURCE_STATE_UNCONFIRMED: engineering bytes differ from pinned №479'
dump('source_pins.json', {'declared_base': '№482 / 553d3746143c97102cc94edaa02549e010e41e04 from user B1', 'engineering_base': '№479 / 508cba49c8f21b0e8a9c451b84f1c0f1a8fb6a19', 'source': 'local Claude manifest and WEB19 report', 'engineering_pins': pins, 'limitation': 'Documentary state and pinned source bytes confirmed locally; Git object/clean status NOT CHECKED (prohibited). No competing Claude task; unsaved editor contents unknown.'})

reg = ROOT / 'Документация/18_Регламент сопровождения документации.md'
norm = reg.read_text(encoding='utf-8-sig')
rules = []
for rid in ['DOC-CONTEXT-OPS-01','DOC-CHANGE-01','DOC-GIT-01','DOC-BLOCK1-SLOT-01','DOC-READ-01','DOC-VERSION-01','DOC-PARALLEL-01']:
    m = re.search(r'^## ' + rid + r' —.*?(?=^## |\Z)', norm, re.M|re.S)
    assert m, rid
    rules.append({'rule_id': rid, 'source': reg.relative_to(ROOT).as_posix(), 'source_sha256': sha(reg.read_bytes()), 'text': m[0]})
dump('rule_scope.json', rules)
print(json.dumps({'history_cases': len(rows), 'addressed_personal_sections': 8, 'engineering_pins_matched': len(pins), 'rules_recorded': len(rules)}))
