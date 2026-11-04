"""Read-only comparison with preserved baselines; writes receipts only in this report."""
from pathlib import Path
import argparse
from collections import Counter
import datetime as dt
import difflib
import hashlib
import json
import platform
import subprocess
import sys

REPORT = Path(__file__).resolve().parent
ROOT = REPORT.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True, choices=['before_finish', 'before_finish_reviewed', 'after_finish'])
args = parser.parse_args()
baseline = json.loads((REPORT/'evidence/baseline.json').read_text(encoding='utf-8'))
owned = {'run_store.py', 'test_run_store_v2.py', 'test_web_alarm_ultra_chat_turn.py'}
card = 'Документация/000_Задачи Codex.md'

def receipt(path):
    data = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), size=len(data), sha256=hashlib.sha256(data).hexdigest())

protected = [receipt(p) for folder in ['.ultra', 'Чат_pro', 'Чат_Pro_01', '.obsidian']
             for p in (ROOT/folder).rglob('*') if p.is_file()]
old = {p['path']: p for p in baseline['protected']}
new = {p['path']: p for p in protected}
changes = [dict(path=p, before=old.get(p), after=new.get(p)) for p in sorted(old.keys() | new.keys()) if old.get(p) != new.get(p)]
storage_changes = [p for p in changes if not p['path'].startswith('.obsidian/')]
editor_changes = [p for p in changes if p['path'].startswith('.obsidian/')]
readonly, backups = [], []
for ref in baseline['source']:
    path = ref['path']
    current = receipt(ROOT/path)
    backup = REPORT/'before'/(path + '.source.txt')
    backups.append(dict(path=path, matches=hashlib.sha256(backup.read_bytes()).hexdigest() == ref['sha256']))
    if path not in owned:
        readonly.append(dict(path=path, unchanged=current == ref,
                             expected_native_finish_change=path == card and args.label == 'after_finish'))
for name in owned:
    old_lines = (REPORT/'before'/(name + '.source.txt')).read_text(encoding='utf-8').splitlines(keepends=True)
    text = (ROOT/name).read_text(encoding='utf-8')
    compile(text, name, 'exec')
    diff = ''.join(difflib.unified_diff(old_lines, text.splitlines(keepends=True), fromfile='before/'+name, tofile='after/'+name))
    (REPORT/'evidence'/(name+'.diff.txt')).write_text(diff, encoding='utf-8')
config = json.loads((ROOT/'web_alarm/launch_config.json').read_text(encoding='utf-8'))
value = dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(), platform=platform.platform(), python=sys.version,
             node=subprocess.check_output(['node','--version'],text=True).strip(),
             protected_count=len(protected), protected_by_directory=dict(Counter(p['path'].split('/')[0] for p in protected)),
             protected_changes=changes, user_storage_changes=storage_changes, editor_state_changes=editor_changes,
             readonly_sources=readonly, backups=backups,
             in_memory_compile=dict(passed=3, failed=0, pyc_written=False), launcher_active=config['active'])
(REPORT/'evidence'/('conservation_'+args.label+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=False,indent=2))
assert not storage_changes, 'User storage changed; inspect evidence, do not restore user changes'
assert all(p['matches'] for p in backups), 'Baseline copy damaged'
assert all(p['unchanged'] or p['expected_native_finish_change'] for p in readonly), 'Out-of-scope source change'
assert config['active'] == 'standard', 'Launcher not STANDARD'
