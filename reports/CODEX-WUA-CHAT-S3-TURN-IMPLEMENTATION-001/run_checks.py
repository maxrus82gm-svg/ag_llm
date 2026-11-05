"""Bounded offline suites. New label preserves each raw result and source receipt."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time

REPORT=Path(__file__).resolve().parent
ROOT=REPORT.parents[1]
p=argparse.ArgumentParser();p.add_argument('suite',choices=['turn','python','js','runstore','prerequisites']);p.add_argument('--label',required=True)
a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_]+',a.label)
python=[sys.executable,'-B','-X','utf8']
commands={
 'turn':python+['-m','unittest','-v','test_web_alarm_ultra_chat_turn_service','test_web_alarm_ultra_chat_turn_http'],
 'prerequisites':python+['-m','unittest','-v','test_web_alarm_ultra_chat_turn'],
 'runstore':python+['-m','pytest','-q','-p','no:cacheprovider','test_run_store_v2.py','test_audit_v2_compatibility.py','test_audit_observability.py::AuditStorageTests'],
 'python':python+['-m','unittest','-v','test_web_alarm_ultra_chat_storage','test_web_alarm_ultra_chat','test_web_alarm_ui','test_web_alarm_ui_ux','test_ultra_chat_storage','test_ultra_chat_read','test_web_alarm_workspace_registry','test_web_alarm_folder_picker'],
 'js':['node','--test','test_web_alarm_ultra_chat_ui.js','test_web_alarm_operator_ui.js','test_web_alarm_evm_ui.js']}
label=a.suite+'_'+a.label;ev=REPORT/'evidence';guard=ev/('guard_'+label)
assert not (ev/(label+'.json')).exists()
names=['web_alarm/turn_service.py','web_alarm/ultra_chat.py','web_alarm/server.py','web_alarm/ui.py','context_storage.py','run_store.py','audit_storage.py','test_web_alarm_ultra_chat_turn_service.py','test_web_alarm_ultra_chat_turn_http.py','test_web_alarm_ultra_chat_ui.js']
source={name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest()) for name in names for data in [(ROOT/name).read_bytes()]}
env={**os.environ,'PYTHONPATH':str(REPORT/'guard')+os.pathsep+str(ROOT),'S3_GUARD_OUTPUT':str(guard),'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONUTF8':'1'}
env.pop('S3_EVIDENCE_DIR',None)
start=time.monotonic();r=subprocess.run(commands[a.suite],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=240)
raw=r.stdout+r.stderr
(ev/(label+'.txt')).write_text(raw,encoding='utf-8')
counts={}
if a.suite=='js':
 for key in ['tests','pass','fail','skipped','cancelled']:
  found=re.search(r'^# '+key+r' (\d+)$',raw,re.M)
  if found:counts[key]=int(found[1])
elif a.suite=='runstore':
 for key in ['passed','failed','skipped','error']:
  found=re.search(r'(\d+) '+key,raw)
  if found:counts[key]=int(found[1])
else:
 found=re.search(r'Ran (\d+) tests?',raw);counts['tests']=int(found[1]) if found else 0
 for key in ['failures','errors','skipped']:
  found=re.search(key+r'=(\d+)',raw);counts[key]=int(found[1]) if found else 0
 counts['passed']=counts['tests']-sum(counts[k] for k in ['failures','errors','skipped'])
receipts=[json.loads(f.read_text(encoding='utf-8')) for f in guard.glob('*.json')]
meta=dict(command=commands[a.suite],exit_code=r.returncode,seconds=round(time.monotonic()-start,2),python=sys.version,platform=platform.platform(),counts=counts,source=source,guard_receipts=len(receipts),guard_denials=sum(len(v['denied']) for v in receipts))
(ev/(label+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(raw[-1600:]);print(json.dumps({k:v for k,v in meta.items() if k!='source'}))
assert a.suite=='js' or receipts,'Guard inactive'
assert meta['guard_denials']==0,'Forbidden attempt detected'
raise SystemExit(r.returncode)
