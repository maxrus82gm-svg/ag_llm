"""Pinned-source wrapper for disposable controlled/stress probes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

REPORT=Path(__file__).resolve().parent;ROOT=REPORT.parents[1]
p=argparse.ArgumentParser();p.add_argument('probe',choices=['controlled_wait','stress_writers']);p.add_argument('--label',required=True);a=p.parse_args()
assert a.label.isalnum();label=a.probe+'_'+a.label;ev=REPORT/'evidence';assert not (ev/(label+'.json')).exists()
command=[sys.executable,'-B','-X','utf8',str(REPORT/(a.probe+'.py'))]
source={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['context_storage.py','test_ultra_chat_storage.py']}
env={**os.environ,'PYTHONPATH':str(REPORT/'guard')+os.pathsep+str(ROOT),'S3_GUARD_OUTPUT':str(ev/('guard_'+label)),
     'WUA_BUSY_TRACE_DIR':str(ev/('trace_'+label)),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'}
env.pop('WUA_BUSY_FSYNC_DELAY_MS',None);env.pop('WUA_BUSY_LIVE_TRACE',None)
start=time.perf_counter();r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
(ev/(label+'.txt')).write_text(r.stdout+r.stderr,encoding='utf-8')
value=dict(command=command,exit_code=r.returncode,seconds=time.perf_counter()-start,source=source,
           source_unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in source.items()))
(ev/(label+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value));print((r.stdout+r.stderr)[-700:]);assert value['source_unchanged'];raise SystemExit(r.returncode)
