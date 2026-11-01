"""Use the existing authorized slot tool; save protocol, then verify untouched card areas."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'reports/CODEX-WUA-DOC-WEB19-REPAIR-001'
CARD = ROOT / 'Документация/000_Задачи Codex.md'
TASK = 'CODEX-WUA-DOC-WEB19-REPAIR-001'

def save(name, obj):
    (WORK / 'evidence' / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def run(name, args):
    command = [sys.executable, '-B', str(ROOT / 'tools/task_slot_rotate.py')] + args
    p = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', errors='strict')
    protocol = json.loads(p.stdout)
    save(name, {'command': ['python', '-B', 'tools/task_slot_rotate.py'] + args, 'exit_code': p.returncode, 'protocol': protocol, 'stderr': p.stderr})
    print(json.dumps({'step': name, 'exit_code': p.returncode, 'result': protocol.get('result'), 'problems': protocol.get('problems', [])}, ensure_ascii=False))
    if p.returncode != 0: sys.exit(p.returncode)
    return protocol

before = CARD.read_bytes()
assert before == (WORK / 'assignment_source.txt').read_bytes(), 'CARD_CHANGED before rotation; do not overwrite'
run('slot_check.json', ['check', '--card', 'Документация/000_Задачи Codex.md'])
args = ['rotate', '--card', 'Документация/000_Задачи Codex.md', '--task-id', TASK, '--no-chat-amendment', '--date', '2026-11-01']
run('rotation_dry_run.json', args)
proto = run('rotation.json', args + ['--apply'])
after = CARD.read_bytes()
old, new = before.decode('utf-8'), after.decode('utf-8')
def outside_slots(t):
    return re.sub(r'(^###### [^\n]*TASK-SLOT:BLOCK-1(?:\.1)?:BEGIN[^\n]*\n).*?(?=^###### [^\n]*TASK-SLOT:BLOCK-1(?:\.1)?:END)', r'\1<SLOT CONTENT>\n', t, flags=re.M|re.S)
assert outside_slots(old) == outside_slots(new), 'OUTSIDE_SLOTS_CHANGED'
assert proto['copied_exact'] and proto['outside_slots_unchanged'] and proto['block1_after'] == 'WAITING'
assert hashlib.sha256(after).hexdigest() == proto['new_card_sha256']
save('card_readback.json', {'before_sha256': hashlib.sha256(before).hexdigest(), 'after_sha256': hashlib.sha256(after).hexdigest(), 'outside_slots_exact': True, 'blocks_2_4_exact': old[old.index('# БЛОК 2'): ] == new[new.index('# БЛОК 2'): ], 'task_snapshot_sha256': hashlib.sha256((WORK / 'handoff_task.md').read_bytes()).hexdigest(), 'result': 'ROTATED / SUBMITTED / REVIEW PENDING'})
(WORK / 'card_after.txt').write_bytes(after)
(WORK / 'card_slots.patch').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile='before/Документация/000_Задачи Codex.md', tofile='after/Документация/000_Задачи Codex.md', n=3)), encoding='utf-8', newline='\n')
