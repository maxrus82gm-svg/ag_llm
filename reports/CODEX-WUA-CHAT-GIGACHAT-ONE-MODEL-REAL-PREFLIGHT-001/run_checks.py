"""Guarded reproducible H35 pytest runner. Every invocation preserves its evidence."""
from pathlib import Path
import json, os, subprocess, sys, tempfile, time

ROOT = Path(__file__).resolve().parents[2]
PKG = Path(__file__).resolve().parent
if __name__ == '__main__':
    stage, *selected = sys.argv[1:]
    if stage == '--child':
        import runpy
        guard=ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py'
        if 'sitecustomize' in sys.modules:
            assert Path(sys.modules['sitecustomize'].__file__).resolve() == guard.resolve()
        else:
            runpy.run_path(str(guard))
        import pytest
        class Results:
            def __init__(self):
                self.counts = {}; self.cases = []; self.offset = 0; self.expected_denials = 0; self.guard_events = []
            def pytest_runtest_logstart(self,nodeid,location):
                Path(os.environ['H35_CASES']).with_suffix('.current.json').write_text(json.dumps(
                    dict(current=nodeid,counts=self.counts,completed_reports=len(self.cases))),encoding='utf-8')
            def pytest_collection_modifyitems(self, config, items):
                # The existing H25 quality runner normally provides this under __main__.
                # Supply only its synthetic fixture root when using pytest collection.
                target=ROOT/'reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/isolation_checks.py'
                for item in items:
                    if Path(item.module.__file__).resolve()==target.resolve():
                        item.module.SANDBOX=Path(config.option.basetemp)/'quality'
            def pytest_runtest_logreport(self, report):
                log=Path(os.environ['ORDINARY_GUARD_LOG'])
                entries=[json.loads(s) for s in log.read_text().splitlines()] if log.exists() else []
                new=entries[self.offset:];self.offset=len(entries)
                if new:
                    controls={
                        'test_ordinary_chat_service.py::OfflineBoundary::test_early_process_guard_negative_controls',
                        'test_web_alarm_ultra_chat_turn_s4b.py::OfflineTurnTests::test_no_oauth_http_or_credentials_and_guard_controls',
                        'test_web_alarm_ultra_chat_s5.py::HttpAndTkTests::test_guard_and_provider_controls',
                    }
                    expected=(report.nodeid in controls and report.when=='call' and report.passed and
                              [(e['event'],e['boundary']) for e in new]==[
                                  ('socket.connect','physical_network'),('socket.getaddrinfo','dns'),('credential_read','credentials')])
                    if expected:self.expected_denials+=len(new)
                    self.guard_events.append(dict(test=report.nodeid,phase=report.when,expected=expected,events=new))
                if report.when == 'call' or report.failed or report.skipped:
                    kind='subtest' if type(report).__name__ == 'SubtestReport' else 'test'
                    key=kind+':'+report.outcome
                    self.counts[key] = self.counts.get(key, 0) + 1
                    self.cases.append(dict(test=report.nodeid, phase=report.when, outcome=report.outcome,kind=kind))
        result = Results()
        rc = pytest.main(selected + ['-q', '--tb=short'], plugins=[result])
        Path(os.environ['H35_CASES']).write_text(json.dumps({'exit_code':int(rc),'counts':result.counts,'cases':result.cases,
            'expected_guard_denials':result.expected_denials,'guard_events':result.guard_events},indent=2),encoding='utf-8')
        sys.exit(rc)
    prefix = PKG/'evidence'/stage
    assert not prefix.with_suffix('.result.json').exists(), 'Preserve earlier evidence'
    env = {k:os.environ[k] for k in os.environ if not k.upper().startswith('GIGACHAT_') and k.upper() not in ('PYTHONPATH','PYTHONSTARTUP')}
    env.update(PYTHONPATH=str(ROOT/'reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard')+os.pathsep+str(ROOT), PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               ORDINARY_GUARD_ROOT=str(ROOT), ORDINARY_GUARD_NETWORK='loopback',
               ORDINARY_GUARD_LOG=str(prefix.with_suffix('.guard.jsonl')),H35_CASES=str(prefix.with_suffix('.cases.json')),
               H35_TRACE=str(prefix.with_suffix('.http_trace.json')))
    with tempfile.TemporaryDirectory(prefix='h35_') as directory:
        env['LOCALAPPDATA'] = directory
        cmd = [str(ROOT/'.venv/Scripts/python.exe'),'-B','-X','utf8',str(Path(__file__).resolve()),'--child',*selected,'--basetemp',str(Path(directory)/'p')]
        started = time.monotonic()
        try:run = subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=600)
        except subprocess.TimeoutExpired as error:
            prefix.with_suffix('.stdout.txt').write_bytes(error.stdout or b'')
            prefix.with_suffix('.stderr.txt').write_bytes(error.stderr or b'')
            prefix.with_suffix('.result.json').write_text(json.dumps(dict(command=cmd,exit_code=124,
                status='TIMEOUT / INCOMPLETE',elapsed_seconds=time.monotonic()-started,
                next='Inspect .cases.current.json and partial output; do not claim suite PASS'),indent=2),encoding='utf-8')
            raise SystemExit(124)
    prefix.with_suffix('.stdout.txt').write_bytes(run.stdout); prefix.with_suffix('.stderr.txt').write_bytes(run.stderr)
    cases = prefix.with_suffix('.cases.json'); result = json.loads(cases.read_text()) if cases.exists() else {}
    result.update(command=cmd, exit_code=run.returncode,elapsed_seconds=time.monotonic()-started)
    log=prefix.with_suffix('.guard.jsonl'); result['guard_denials']=len(log.read_text().splitlines()) if log.exists() else 0
    result['unexpected_guard_denials']=result['guard_denials']-result.get('expected_guard_denials',0)
    result['pytest_exit_code']=run.returncode
    result['runner_exit_code']=run.returncode or int(bool(result['unexpected_guard_denials']))
    prefix.with_suffix('.result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(run.stdout.decode('utf-8',errors='replace')[-4500:]); print(run.stderr.decode('utf-8',errors='replace')[-1200:])
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','guard_events')},indent=2)); sys.exit(result['runner_exit_code'])
