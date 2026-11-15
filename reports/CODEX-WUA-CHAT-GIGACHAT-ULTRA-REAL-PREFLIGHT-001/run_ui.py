"""Capture actual Node exit/counts; optional SHA-pinned baseline must stay RED."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
PKG=Path(__file__).resolve().parent;ROOT=PKG.parents[1]
stage=sys.argv[1];baseline=len(sys.argv)>2 and sys.argv[2]=='baseline'
prefix=PKG/'evidence'/stage
assert not prefix.with_suffix('.result.json').exists()
cmd=['node']
if baseline:cmd+=['--require',str(PKG/'baseline_ui.cjs')]
cmd+=['--test']
if baseline:cmd+=['--test-name-pattern=TEST model choice:']
cmd+=['test_web_alarm_ultra_chat_ui.js']
run=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=60)
prefix.with_suffix('.stdout.txt').write_bytes(run.stdout);prefix.with_suffix('.stderr.txt').write_bytes(run.stderr)
output=run.stdout.decode('utf-8',errors='replace')
counts={k:int(v) for k,v in re.findall(r'^# (tests|pass|fail|skipped|cancelled) (\d+)',output,re.M)}
assert counts.get('tests',0)>0
result=dict(command=cmd,exit_code=run.returncode,counts=counts,baseline_negative_control=baseline,
 source_sha256=hashlib.sha256((PKG/'before_ui.py.txt' if baseline else ROOT/'web_alarm/ui.py').read_bytes()).hexdigest(),
 test_sha256=hashlib.sha256((ROOT/'test_web_alarm_ultra_chat_ui.js').read_bytes()).hexdigest())
prefix.with_suffix('.result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
assert (run.returncode==1 and counts.get('fail')==2) if baseline else (run.returncode==0 and counts.get('fail')==0)
