"""Three semantic weakening controls against real H34 tests; require RED."""
from pathlib import Path
import ast,copy,hashlib,io,json,os,runpy,sys,unittest
from dataclasses import replace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];PKG=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
stage=sys.argv[1] if len(sys.argv)>1 else 'mutations'
assert stage.isidentifier()
prefix=PKG/'evidence'/stage;assert not prefix.with_suffix('.result.json').exists()
for key in tuple(os.environ):
    if key.upper().startswith('GIGACHAT_'):del os.environ[key]
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT),ORDINARY_GUARD_NETWORK='loopback',
                  ORDINARY_GUARD_LOG=str(prefix.with_suffix('.guard.jsonl')))
runpy.run_path(str(ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py'))
import ultra_budget_policy as policy
import ordinary_gigachat_transport as transport
import gigachat_admission as admission
from test_gigachat_admission import ServerAdmissionTests
files=['gigachat_admission.py','ordinary_gigachat_transport.py','ultra_budget_policy.py','ultra_budget_ledger.py']
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}
original=policy.evaluate_request
def weakened(snapshot,*args):
    return original(replace(snapshot,run=replace(snapshot.run,max_request_bytes=2_000_000)),*args)
tree=ast.parse((ROOT/'ordinary_gigachat_transport.py').read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GigaChatTransport')
method=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='send_bytes'))
removed=[]
class RemoveWireCheck(ast.NodeTransformer):
    def visit_BoolOp(self,node):
        self.generic_visit(node)
        keep=[]
        for value in node.values:
            if ast.unparse(value)=='request.content != wire':removed.append(True)
            else:keep.append(value)
        node.values=keep;return node
RemoveWireCheck().visit(method);assert removed==[True]
scope=dict(vars(transport))
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<H34 IN-MEMORY MUTATION>','exec'),scope)
cases=[('presend_budget_disabled',patch.object(policy,'evaluate_request',weakened),'test_s2_real_denial_zero_http'),
       ('wire_check_disabled',patch.object(transport.GigaChatTransport,'send_bytes',scope['send_bytes']),'test_post_admission_wire_substitution_is_blocked'),
       ('terminal_check_disabled',patch.object(admission._ServerAttempt,'terminal',lambda *args:None),'test_terminal_fake_ack_and_owner_tamper_cannot_publish')]
observations=[]
for name,mutation,test in cases:
    stream=io.StringIO()
    with mutation:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite([ServerAdmissionTests(test)]))
    prefix.with_name(stage+'_'+name).with_suffix('.txt').write_text(stream.getvalue(),encoding='utf-8')
    observations.append(dict(mutation=name,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),expected='RED',observed='RED' if result.failures else 'UNEXPECTED GREEN'))
    assert result.testsRun==1 and result.failures and not result.errors,stream.getvalue()
assert before=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}
log=prefix.with_suffix('.guard.jsonl');assert not log.exists() or not log.read_text().strip()
artifact=dict(status='PASS / 3 expected RED controls',cases=observations,source_files_unchanged=before,guard_denials=0,exit_code=0)
prefix.with_suffix('.result.json').write_text(json.dumps(artifact,indent=2),encoding='utf-8');print(json.dumps(artifact))
