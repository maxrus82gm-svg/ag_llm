"""Offline input hashes, single explicitly authorized card backup; no subprocess/network."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CARD = ROOT / 'Документация/000_Задачи Codex.md'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write_json(name, data):
    p = OUT / name
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

def main():
    old = ROOT / 'reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001'
    rows = json.loads((old / 'inputs_before.json').read_text(encoding='utf-8-sig'))['inputs']
    paths = {str(x['path']) for x in rows}
    paths.update(str(p.relative_to(ROOT)).replace('\\', '/') for p in old.iterdir() if p.is_file())
    for name in ['05_Реестр задач.md', '06_Журнал выполнения и отчёты.md']:
        paths.add('Документация/' + name)
    result = []
    for name in sorted(paths):
        p = Path(name) if Path(name).is_absolute() else ROOT / name
        b = p.read_bytes()
        result.append({'path': name, 'bytes': len(b), 'sha256': sha(b),
                       'authorized_change': p.resolve() == CARD.resolve()})
    b = CARD.read_bytes()
    # One own-card backup, explicitly authorized, not a mass backup.
    with (OUT / 'card_before.md').open('xb') as f:
        f.write(b)
    lines = b.decode('utf-8-sig').splitlines(keepends=True)
    a = next(i for i, s in enumerate(lines) if s.startswith('# БЛОК 1'))
    z = next(i for i in range(a + 1, len(lines)) if lines[i].startswith('# БЛОК 2'))
    with (OUT / 'assignment.md').open('x', encoding='utf-8', newline='') as f:
        f.write(''.join(lines[a:z]))
    write_json('inputs_before.json', {'task_id': OUT.name, 'created_utc': datetime.now(timezone.utc).isoformat(),
               'source_pin_user_supplied_not_git_verified': '795e1fddf6741169f006caf8ba9430e4d22fca0f',
               'inputs': result, 'raw_private_configs_exported': False})
    prior_rules = json.loads((old / 'rules_read.json').read_text(encoding='utf-8-sig'))['rules']
    rules = []
    for x in prior_rules:
        p = ROOT / x['source']; data = p.read_bytes(); text = data.decode('utf-8-sig')
        a = text.index(x['selector']); z = text.find('\n## ', a + 1)
        block = text[a:z if z >= 0 else len(text)]
        rules.append({'id': x['rule_id'], 'source': x['source'], 'source_sha256': sha(data),
                      'selector': x['selector'], 'definition_sha256': sha(block.encode()),
                      'same_source_as_preceding_task': sha(data) == x['current_source_sha256']})
    write_json('rules_read.json', {'rules': rules, 'rotation_addition': 'user_go_card_rotation.md',
               'doc18_rotation_lines': [340, 346, 362, 437],
               'profile_read': ['08', '000', '34', '18', '01', '19', '23', '36', '36.1', '36.2', '37', '05', '06'],
               'prior_tests_rerun': 0})
    print(json.dumps({'protected_inputs': len(result), 'card_sha256': sha(b), 'rules': len(rules)}))

if __name__ == '__main__':
    main()
