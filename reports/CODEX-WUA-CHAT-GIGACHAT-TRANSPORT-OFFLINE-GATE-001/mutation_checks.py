"""Run actual negative tests with two in-memory weakenings; require expected RED."""
from pathlib import Path
import ast, copy, hashlib, io, json, os, runpy, sys, unittest
from dataclasses import replace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];PKG=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
stage=sys.argv[1] if len(sys.argv)>1 else 'mutations'
assert stage.isidentifier()
prefix=PKG/'evidence'/stage
assert not prefix.with_suffix('.result.json').exists()
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT),ORDINARY_GUARD_NETWORK='loopback',
                  ORDINARY_GUARD_LOG=str(prefix.with_suffix('.guard.jsonl')))
runpy.run_path(str(ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py'))
import ultra_budget_policy as policy
import ordinary_gigachat_transport as transport
from test_web_alarm_gigachat_transport import HTTPTransportTests

files=['ordinary_gigachat_transport.py','web_alarm/turn_service.py','ultra_budget_policy.py','web_alarm/launcher.py']
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}
original=policy.evaluate_request
def weakened(snapshot,*args):
    return original(replace(snapshot,ordinary=policy.ScopeLimits('BUDGET',8192,8192,8320,1)),*args)

tree=ast.parse((ROOT/'ordinary_gigachat_transport.py').read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GigaChatTransport')
method=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='send_bytes'))
removed=[]
class RemoveWireCheck(ast.NodeTransformer):
    def visit_BoolOp(self,node):
        self.generic_visit(node)
        retained=[]
        for value in node.values:
            if ast.unparse(value)=='request.content != wire':removed.append(True)
            else:retained.append(value)
        node.values=retained
        return node
RemoveWireCheck().visit(method);assert removed==[True]
scope=dict(vars(transport))
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])), '<H33 IN-MEMORY MUTATION>', 'exec'),scope)
cases=[('presend_s2_disabled',patch.object(policy,'evaluate_request',weakened),
        'test_budget_denials_and_invalid_enrollment_zero_token_http'),
       ('http_wire_check_disabled',patch.object(transport.GigaChatTransport,'send_bytes',scope['send_bytes']),
        'test_post_admission_http_byte_substitution_is_zero_http')]
observations=[]
for name,mutation,test in cases:
    stream=io.StringIO()
    with mutation:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite([HTTPTransportTests(test)]))
    (PKG/f'evidence/{stage}_{name}.txt').write_text(stream.getvalue(),encoding='utf-8')
    observations.append(dict(mutation=name,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        expected='RED',observed='RED' if result.failures else 'UNEXPECTED GREEN'))
    assert result.testsRun==1 and result.failures and not result.errors,stream.getvalue()
assert before=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}
log=prefix.with_suffix('.guard.jsonl')
assert not log.exists() or not log.read_text().strip()
artifact=dict(status='PASS: two weakening controls expected RED',cases=observations,source_files_unchanged=before,
              guard_denials=0)
prefix.with_suffix('.result.json').write_text(json.dumps(artifact,indent=2),encoding='utf-8')
print(json.dumps(artifact))
