"""Preserve the dedicated S1/S2 acceptance runners and their own early isolation gates."""
from pathlib import Path
import json, os, subprocess, sys, time

ROOT=Path(__file__).resolve().parents[2]
PKG=Path(__file__).resolve().parent
stage, module=sys.argv[1:]
prefix=PKG/'evidence'/stage
assert module in ('test_rt002_s1_routes.py','test_rt002_s2_budget_policy.py')
assert not prefix.with_suffix('.result.json').exists()
env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIGACHAT_') and k.upper() not in ('PYTHONPATH','PYTHONSTARTUP')}
env['PYTHONDONTWRITEBYTECODE']='1'
cmd=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-X','utf8',module]
started=time.monotonic();run=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=180)
prefix.with_suffix('.stdout.txt').write_bytes(run.stdout);prefix.with_suffix('.stderr.txt').write_bytes(run.stderr)
output=run.stdout.decode('utf-8',errors='replace')
report,_=json.JSONDecoder().raw_decode(output)
log=Path(report['log']);prefix.with_suffix('.unittest.txt').write_bytes(log.read_bytes())
facts=dict(command=cmd,exit_code=run.returncode,elapsed_seconds=time.monotonic()-started,
           counts=report['counts'],gate=report['gate'],isolation_violations=report['isolation_violations'])
prefix.with_suffix('.result.json').write_text(json.dumps(facts,indent=2),encoding='utf-8')
print(output[-5000:]); print(run.stderr.decode('utf-8',errors='replace')[-1000:]);sys.exit(run.returncode)
