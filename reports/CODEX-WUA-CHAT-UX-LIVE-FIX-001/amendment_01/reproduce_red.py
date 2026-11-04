"""Reproduce the two amendment REDs against saved pre-amendment sources; never replace working files."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

AMEND = Path(__file__).resolve().parent
ROOT = AMEND.parents[2]
sys.path.insert(0,str(ROOT))
mirror=AMEND/'red_repro'
(mirror/'web_alarm').mkdir(parents=True,exist_ok=True)
tests=mirror/'test_web_alarm_ultra_chat_ui.js'
for src,dst in [(AMEND/'before/web_alarm/ui.py',mirror/'web_alarm/ui.py'),
                (tests if tests.exists() else ROOT/'test_web_alarm_ultra_chat_ui.js',tests)]:
    data=src.read_bytes()
    if dst.exists() and dst.read_bytes()!=data:
        raise RuntimeError('Refusing to overwrite a different RED fixture')
    dst.write_bytes(data)
cmd=['node','--test','--test-name-pattern=AMENDMENT first chat: missing_history allows',str(tests)]
r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=30)
(AMEND/'evidence/red_reproduced_ui.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
from web_alarm import server as wa
spec=importlib.util.spec_from_file_location('web_alarm.amendment_baseline',AMEND/'before/web_alarm/ultra_chat.py')
baseline=importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
suite=unittest.defaultTestLoader.loadTestsFromName('test_web_alarm_ultra_chat_storage.FirstChatAmendmentTests.test_a01_explicit_first_chat_uses_shared_core_and_survives_replay_and_restart')
stream=io.StringIO()
with patch.object(wa,'UltraChatService',baseline.UltraChatService), patch.object(wa,'UltraChatError',baseline.UltraChatError):
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
(AMEND/'evidence/red_reproduced_http.txt').write_text(stream.getvalue(),encoding='utf-8')
meta=dict(ui_command=cmd,ui_exit_code=r.returncode,http_tests_run=result.testsRun,http_expected_baseline_status=400,
          http_failures=len(result.failures),http_errors=len(result.errors),working_files_replaced=False,
          source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [AMEND/'before/web_alarm/ui.py',AMEND/'before/web_alarm/ultra_chat.py',tests,ROOT/'test_web_alarm_ultra_chat_storage.py']})
(AMEND/'evidence/red_reproduced.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
assert r.returncode==1 and result.testsRun==1 and len(result.failures)==1 and not result.errors
assert '(400, None)' in result.failures[0][1], 'Baseline must reach its original 400 refusal, not a harness error'
