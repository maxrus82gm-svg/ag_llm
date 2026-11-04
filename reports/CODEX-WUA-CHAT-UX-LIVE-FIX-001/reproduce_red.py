"""Run the five original defect oracles against the immutable local pre-fix UI, without replacing working code."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import time

REPORT = Path(__file__).resolve().parent
ROOT = REPORT.parents[1]
mirror = REPORT / 'red_repro'
(mirror / 'web_alarm').mkdir(parents=True, exist_ok=True)
saved_tests = mirror / 'test_web_alarm_ultra_chat_ui.js'
for src, dst in [(REPORT / 'before/web_alarm/ui.py', mirror / 'web_alarm/ui.py'),
                 (saved_tests if saved_tests.exists() else ROOT / 'test_web_alarm_ultra_chat_ui.js', saved_tests)]:
    content = src.read_bytes()
    if dst.exists() and dst.read_bytes() != content:
        raise RuntimeError('Refusing to overwrite a different RED fixture: ' + str(dst))
    dst.write_bytes(content)
cmd = ['node', '--test', '--test-name-pattern=LIVE RED:|Workspace selection nests', str(mirror / 'test_web_alarm_ultra_chat_ui.js')]
started = time.monotonic()
r = subprocess.run(cmd, capture_output=True, encoding='utf-8', text=True, timeout=30)
(REPORT / 'evidence/red_reproduced.txt').write_text(r.stdout + r.stderr, encoding='utf-8')
meta = dict(command=cmd, exit_code=r.returncode, expected_exit_code=1,
            seconds=round(time.monotonic() - started, 2),
            ui_sha256=hashlib.sha256((mirror / 'web_alarm/ui.py').read_bytes()).hexdigest(),
            test_sha256=hashlib.sha256((mirror / 'test_web_alarm_ultra_chat_ui.js').read_bytes()).hexdigest(),
            working_ui_replaced=False)
(REPORT / 'evidence/red_reproduced.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print('\n'.join(s for s in r.stdout.splitlines() if s.startswith(('not ok', '# tests', '# fail', '# pass'))))
print(json.dumps(meta, ensure_ascii=False))
assert r.returncode == 1 and re.search(r'^# fail 5$', r.stdout, re.M), 'RED reproduction did not reach all five known failures'
