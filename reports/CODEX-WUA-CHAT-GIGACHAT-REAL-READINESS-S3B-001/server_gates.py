"""Run existing server compile/UI-smoke gates with guard BEFORE child imports.

The standard helper uses -E and removes PYTHONPATH. Instrument only the test
child bootstrap to explicitly install the unchanged H27 guard. The actual
compile/UI helper, UltraApp constructor and assertions run normally. UI cwd and
LOCALAPPDATA are disposable; the copied UI source is byte-identical.
"""
from pathlib import Path
import hashlib, json, os, runpy, sys, tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];PKG=Path(__file__).resolve().parent
stage=sys.argv[1] if len(sys.argv)>1 else 'server_gates'
assert stage.isidentifier()
prefix=PKG/'evidence'/stage
assert not prefix.with_suffix('.result.json').exists()
sys.path.insert(0,str(ROOT))
# Remove credential variable names without retrieving their values. The legacy
# verification helper copies its environment; its test child must receive none.
for key in tuple(os.environ):
    if key.upper().startswith('GIGACHAT_'):del os.environ[key]
with tempfile.TemporaryDirectory(prefix='h34_gates_') as directory:
    folder=Path(directory)
    os.environ['LOCALAPPDATA']=str(folder/'appdata')
    os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT),ORDINARY_GUARD_NETWORK='loopback',
                      ORDINARY_GUARD_LOG=str(prefix.with_suffix('.guard.jsonl')))
    guard=ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py'
    runpy.run_path(str(guard))
    import server
    original=server._run_verify_process
    commands=[]
    def guarded(args,**kwargs):
        args=list(args);index=args.index('-c')+1
        # -E suppresses environment-based Python bootstrapping; install explicitly.
        bootstrap=f'import runpy,sys;runpy.run_path({str(guard)!r});sys.path.append({str(ROOT)!r})\n'
        args[index]=bootstrap+args[index]
        commands.append(dict(args=args,cwd=str(kwargs['cwd'])))
        return original(args,**kwargs)
    paths=['server.py','planner_runtime.py','verifier_runtime.py','compressor_runtime.py',
           'gigachat_transport.py','ordinary_gigachat_transport.py','gigachat_admission.py','ordinary_chat_service.py']
    def permissions(root):
        return server._prepare_policy_for_workspace(root,server._normalize_permissions(dict(
            allow_read=True,allow_write=False,allow_delete=False,allow_verify=True,
            read_scope='.',write_scope='.',delete_scope='.',tool_limit=1,auto_backup=True)))
    ui=folder/'ui';ui.mkdir()
    (ui/'ultra_ui.py').write_bytes((ROOT/'ultra_ui.py').read_bytes())
    assert hashlib.sha256((ui/'ultra_ui.py').read_bytes()).digest()==hashlib.sha256((ROOT/'ultra_ui.py').read_bytes()).digest()
    with patch.object(server,'_run_verify_process',guarded):
        compile_result=server._agent_python_compile(ROOT,paths,permissions(ROOT))
        ui_result=server._agent_ui_smoke_test(ui,permissions(ui))
    log=prefix.with_suffix('.guard.jsonl')
    denials=len(log.read_text().splitlines()) if log.exists() else 0
    result=dict(compile=compile_result,ui_smoke=ui_result,guard_denials=denials,commands=commands,
                ui_source_sha256=hashlib.sha256((ROOT/'ultra_ui.py').read_bytes()).hexdigest(),
                ui_cwd='explicit synthetic TEMP',guard_before_runtime_imports=True)
    ok=bool(compile_result['ok'] and ui_result['ok'] and not denials)
    result['exit_code']=0 if ok else 1
    prefix.with_suffix('.result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));sys.exit(result['exit_code'])
