"""Reproducible offline checks; logs and source digests belong to this task only."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time

REPORT = Path(__file__).resolve().parent
ROOT = REPORT.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('suite', choices=['prerequisites', 'js', 'python', 'run_store'])
parser.add_argument('--label', default='')
args = parser.parse_args()
assert re.fullmatch(r'[A-Za-z0-9_]*', args.label)
suffix = ('_' + args.label) if args.label else ''
if args.suite == 'prerequisites':
    command = [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', '-v', 'test_web_alarm_ultra_chat_turn']
elif args.suite == 'js':
    command = ['node', '--test', 'test_web_alarm_ultra_chat_ui.js', 'test_web_alarm_operator_ui.js', 'test_web_alarm_evm_ui.js']
elif args.suite == 'run_store':
    command = [sys.executable, '-B', '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               'test_run_store_v2.py', 'test_audit_v2_compatibility.py', 'test_audit_observability.py::AuditStorageTests']
else:
    command = [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', '-v',
               'test_web_alarm_ultra_chat_storage', 'test_web_alarm_ultra_chat', 'test_web_alarm_ui',
               'test_web_alarm_ui_ux', 'test_ultra_chat_storage', 'test_ultra_chat_read',
               'test_web_alarm_workspace_registry', 'test_web_alarm_folder_picker']
names = ['run_store.py', 'test_run_store_v2.py', 'test_web_alarm_ultra_chat_turn.py',
         'context_storage.py', 'audit_storage.py', 'web_alarm/ultra_chat.py', 'web_alarm/server.py', 'web_alarm/ui.py']
source = {name: dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())
          for name in names for data in [(ROOT/name).read_bytes()]}
guard = REPORT/'evidence'/('guard_' + args.suite + suffix)
assert not guard.exists(), 'Choose a new label instead of overwriting guard receipts'
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
       'PYTHONPATH': str(REPORT/'guard') + os.pathsep + str(ROOT), 'S3_GUARD_OUTPUT': str(guard),
       'S3_EVIDENCE_DIR': str(REPORT/'evidence'/('oracles' + suffix))}
started = time.monotonic()
result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=240)
output = result.stdout + result.stderr
receipts = [json.loads(p.read_text(encoding='utf-8')) for p in guard.glob('*.json')] if guard.exists() else []
counts = {}
if args.suite == 'js':
    for key in ['tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo']:
        found = re.search(r'^# ' + key + r' (\d+)$', output, re.MULTILINE)
        if found: counts[key] = int(found[1])
elif args.suite == 'run_store':
    for key in ['passed', 'failed', 'skipped', 'error']:
        found = re.search(r'(\d+) ' + key, output)
        if found: counts[key] = int(found[1])
else:
    found = re.search(r'Ran (\d+) tests?', output)
    if found: counts['tests'] = int(found[1])
    if found:
        for key in ['failures', 'errors', 'skipped']:
            detail = re.search(key + r'=(\d+)', output)
            counts[key] = int(detail[1]) if detail else 0
        counts['passed'] = counts['tests'] - sum(counts[k] for k in ['failures', 'errors', 'skipped'])
meta = dict(command=command, exit_code=result.returncode, seconds=round(time.monotonic()-started, 2),
            platform=platform.platform(), python=sys.version, counts=counts, source=source,
            guard_receipts=len(receipts), guard_denials=sum(len(p['denied']) for p in receipts),
            network_guard='Python children: loopback only; Node suites use mocked fetch/VM, no Python network instrumentation')
for extension, value in [('txt', output), ('json', json.dumps(meta, ensure_ascii=False, indent=2))]:
    (REPORT/'evidence'/(args.suite + suffix + '.' + extension)).write_text(value, encoding='utf-8')
print(output[-1800:])
print(json.dumps({k: v for k, v in meta.items() if k != 'source'}, ensure_ascii=False))
assert not any(p['denied'] for p in receipts), 'Unexpected forbidden attempt; see receipts'
if args.suite != 'js': assert receipts, 'Python guard inactive'
raise SystemExit(result.returncode)
