"""Bounded local regression with exact commands, output, exits and source hashes. No Git."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'evidence'
parser = argparse.ArgumentParser()
parser.add_argument('suite', choices=['js', 'python', 'python_core', 'picker_diagnostic'])
parser.add_argument('--label', default='')
args = parser.parse_args()
if args.suite == 'js':
    cmd = ['node', '--test', 'test_web_alarm_ultra_chat_ui.js', 'test_web_alarm_operator_ui.js', 'test_web_alarm_evm_ui.js']
elif args.suite == 'picker_diagnostic':
    cmd = [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', '-v',
           'test_web_alarm_folder_picker.PickerHttpTests.test_remote_bind_metadata_is_rejected_even_for_loopback_client']
else:
    cmd = [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', '-v',
           'test_web_alarm_ultra_chat_storage', 'test_web_alarm_ultra_chat',
           'test_web_alarm_ui', 'test_web_alarm_ui_ux',
           'test_ultra_chat_storage', 'test_ultra_chat_read',
           'test_web_alarm_workspace_registry']
    if args.suite == 'python':
        cmd.append('test_web_alarm_folder_picker')
source = {}
for name in ['web_alarm/ui.py', 'web_alarm/ultra_chat.py', 'web_alarm/workspace_registry.py',
             'test_web_alarm_ultra_chat_ui.js', 'test_web_alarm_ultra_chat_storage.py']:
    data = (ROOT / name).read_bytes()
    source[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
started = time.monotonic()
result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=300,
                        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'})
suffix = ('_' + args.label) if args.label else ''
assert all(c.isalnum() or c == '_' for c in suffix)
(OUT / (args.suite + '_regression' + suffix + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
meta = dict(command=cmd, exit_code=result.returncode, seconds=round(time.monotonic() - started, 2),
            platform=platform.platform(), python=sys.version, source=source)
(OUT / (args.suite + '_regression' + suffix + '.json')).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print(result.stdout[-800:] + result.stderr[-1800:])
print(json.dumps({k: v for k, v in meta.items() if k != 'source'}, ensure_ascii=False))
raise SystemExit(result.returncode)
