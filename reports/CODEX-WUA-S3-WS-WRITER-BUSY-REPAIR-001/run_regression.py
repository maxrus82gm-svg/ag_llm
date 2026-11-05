"""Pinned-source, guarded offline regression; separate labels retain every outcome."""
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

REPORT=Path(__file__).resolve().parent;ROOT=REPORT.parents[1]
p=argparse.ArgumentParser();p.add_argument('suite',choices=['python','neighbors','lock']);p.add_argument('--label',required=True);a=p.parse_args()
assert a.label.isalnum();ev=REPORT/'evidence';label=a.suite+'_'+a.label;assert not (ev/(label+'.json')).exists()
prefix=[sys.executable,'-B','-X','utf8']
commands={
'python':prefix+['-m','unittest','-v','test_web_alarm_ultra_chat_storage','test_web_alarm_ultra_chat','test_web_alarm_ui','test_web_alarm_ui_ux','test_ultra_chat_storage','test_ultra_chat_read','test_web_alarm_workspace_registry','test_web_alarm_folder_picker'],
'neighbors':prefix+['-m','pytest','-q','-p','no:cacheprovider','test_run_store_v2.py','test_audit_v2_compatibility.py','test_audit_observability.py::AuditStorageTests','test_web_alarm_ultra_chat_turn_service.py','test_web_alarm_ultra_chat_turn_http.py','test_web_alarm_ultra_chat_turn.py'],
'lock':prefix+['-m','unittest','-v','test_ultra_chat_storage.ProcessDiagnosticTests','test_ultra_chat_storage.LockTests','test_ultra_chat_storage.ConcurrencyTests']}
names=['context_storage.py','test_ultra_chat_storage.py','run_store.py','web_alarm/turn_service.py','web_alarm/server.py','web_alarm/ultra_chat.py','web_alarm/ui.py']
source={name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest()) for name in names for data in [(ROOT/name).read_bytes()]}
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONPATH':str(REPORT/'guard')+os.pathsep+str(ROOT),'S3_GUARD_OUTPUT':str(ev/('guard_'+label))}
for key in ['WUA_BUSY_TRACE_DIR','WUA_BUSY_FSYNC_DELAY_MS','WUA_BUSY_LIVE_TRACE','S3_EVIDENCE_DIR']:env.pop(key,None)
start=time.perf_counter();r=subprocess.run(commands[a.suite],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=240)
raw=r.stdout+r.stderr;(ev/(label+'.txt')).write_text(raw,encoding='utf-8')
counts={}
if a.suite=='neighbors':
    for key in ['passed','failed','skipped','error']:
        m=re.search(r'(\d+) '+key,raw)
        if m:counts[key]=int(m[1])
else:
    m=re.search(r'Ran (\d+) tests?',raw);counts['tests']=int(m[1]) if m else 0
    for key in ['failures','errors','skipped']:
        m=re.search(key+r'=(\d+)',raw);counts[key]=int(m[1]) if m else 0
    counts['passed']=counts['tests']-sum(counts[k] for k in ['failures','errors','skipped'])
receipts=[json.loads(f.read_text()) for f in (ev/('guard_'+label)).glob('*.json')]
meta=dict(command=commands[a.suite],exit_code=r.returncode,seconds=round(time.perf_counter()-start,3),python=sys.version,platform=platform.platform(),counts=counts,source=source,
          source_unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==v['sha256'] for name,v in source.items()),
          guard_receipts=len(receipts),guard_denials=sum(len(v['denied']) for v in receipts))
(ev/(label+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(raw[-1600:]);print(json.dumps({k:v for k,v in meta.items() if k!='source'}))
assert receipts and meta['guard_denials']==0 and meta['source_unchanged']
raise SystemExit(r.returncode)
