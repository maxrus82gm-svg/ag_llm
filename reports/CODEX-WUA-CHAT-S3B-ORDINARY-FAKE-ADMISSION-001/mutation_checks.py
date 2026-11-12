"""Two in-memory weakening controls; expected RED, no source-file edits or real sender."""
from pathlib import Path
import hashlib, io, json, os, runpy, sys, unittest
from dataclasses import replace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];PKG=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
stage=sys.argv[1] if len(sys.argv)>1 else 'mutations'
assert stage.isidentifier()
prefix=PKG/'evidence'/stage
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT),ORDINARY_GUARD_NETWORK='loopback',
                  ORDINARY_GUARD_LOG=str(prefix.with_suffix('.guard.jsonl')))
runpy.run_path(str(ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py'))
import ultra_budget_policy as policy
from web_alarm.turn_service import TurnService
from test_web_alarm_ordinary_admission import AdmissionTests

assert not prefix.with_suffix('.result.json').exists()
files=['ultra_budget_policy.py','web_alarm/turn_service.py','web_alarm/launcher.py']
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}
original=policy.evaluate_request
def weakened(snapshot,*args):
    return original(replace(snapshot,ordinary=policy.ScopeLimits('BUDGET',8192,8192,8320,1)),*args)
cases=[('s2_deny_bypassed',patch.object(policy,'evaluate_request',weakened),
        'test_s2_deny_is_zero_send_failed_zero_usage_attempts'),
       ('terminal_verification_bypassed',patch.object(TurnService,'_ordinary_terminal',lambda *args:None),
        'test_terminal_fake_ack_cannot_publish_success')]
observations=[]
for name,mutation,test in cases:
    stream=io.StringIO()
    with mutation:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite([AdmissionTests(test)]))
    (PKG/f'evidence/{stage}_{name}.txt').write_text(stream.getvalue(),encoding='utf-8')
    observations.append(dict(mutation=name,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                             expected='RED',observed='RED' if result.failures else 'UNEXPECTED GREEN'))
    assert result.testsRun==1 and len(result.failures)==1 and not result.errors,stream.getvalue()
assert before=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}
artifact=dict(status='PASS: both weakening controls expected RED',cases=observations,source_files_unchanged=before)
prefix.with_suffix('.result.json').write_text(json.dumps(artifact,indent=2),encoding='utf-8')
print(json.dumps(artifact))
