"""Expected one FAIL after removing Origin protection, production unchanged."""
from pathlib import Path
import hashlib, inspect, json, os, sys, tempfile, textwrap, unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
out=Path(sys.argv[1]).resolve()
if not out.is_relative_to(Path(tempfile.gettempdir()).resolve()) or out.exists():
    raise ValueError('new TEMP child required')
out.mkdir()
guard_log=out/'isolation.jsonl';guard_log.touch()
os.environ['WA4A_GUARD_LOG']=str(guard_log)
from wa4a_acceptance import GUARD
exec(compile(GUARD,'wa4a_acceptance.GUARD','exec'),{})
import web_alarm.server as server

source=textwrap.dedent(inspect.getsource(server._JsonHandler._folder_picker_request))
point="origins[0] != 'http://' + hosts[0]"
assert source.count(point)==1
namespace=dict(vars(server))
exec(compile(source.replace(point,'False'),'expected-origin-mutant','exec'),namespace)
server._JsonHandler._folder_picker_request=namespace['_folder_picker_request']
selector='test_web_alarm_folder_picker.PickerHttpTests.test_foreign_capability_get_does_not_disclose_token'
suite=unittest.defaultTestLoader.loadTestsFromName(selector)
with (out/'assertions.log').open('w',encoding='utf-8') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
passed=result.testsRun==1 and len(result.failures)==1 and not result.errors and guard_log.stat().st_size==0
evidence={'control':'foreign-origin-denial','outer_pass':passed,'expected_inner':'one FAIL: 200 != 403',
    'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'selector':selector,'isolation_violations':guard_log.stat().st_size,
    'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['web_alarm/server.py','test_web_alarm_folder_picker.py']},
    'assertions':(out/'assertions.log').read_text(encoding='utf-8')}
(out/'quality.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print('foreign-origin-denial', 'PASS' if passed else 'FAIL')
raise SystemExit(0 if passed else 1)
