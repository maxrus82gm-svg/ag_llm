"""Run the unmodified published selector, bounded repetitions, retained results and timing trace."""
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import hashlib

REPORT=Path(__file__).resolve().parent;ROOT=REPORT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--rounds',type=int,default=5);p.add_argument('--delay-ms',type=int,default=0)
a=p.parse_args();assert a.label.isalnum() and 1<=a.rounds<=8 and 0<=a.delay_ms<=500
ev=REPORT/'evidence';target=ev/a.label;target.mkdir();results=[]
selector='test_ultra_chat_storage.ConcurrencyTests.test_two_processes_write_raw_create_and_rename_without_losing_anything'
command=[sys.executable,'-B','-X','utf8','-m','unittest','-v',selector]
for i in range(a.rounds):
    folder=target/str(i+1);folder.mkdir()
    source_before={}
    for name in ['context_storage.py','test_ultra_chat_storage.py']:
        data=(ROOT/name).read_bytes();source_before[name]=hashlib.sha256(data).hexdigest()
        (folder/(name+'.source.txt')).write_bytes(data)
    env={**os.environ,'PYTHONPATH':str(REPORT/'guard')+os.pathsep+str(ROOT),'PYTHONDONTWRITEBYTECODE':'1',
         'S3_GUARD_OUTPUT':str(folder/'guard'),'WUA_BUSY_TRACE_DIR':str(folder/'trace'),'WUA_BUSY_FSYNC_DELAY_MS':str(a.delay_ms),
         'PYTHONUTF8':'1'}
    t=time.perf_counter();r=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=150)
    (folder/'output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
    events=[e for f in (folder/'trace').glob('*.json') for e in json.loads(f.read_text())['events']]
    locks=[e for e in events if e['kind']=='lock' and not e['nested']]
    waits=[e['acquired']-e['start'] for e in locks if e['acquired'] is not None]
    holds=[e['released']-e['acquired'] for e in locks if e.get('released')]
    counts={}
    for e in events:
        if e['kind']=='byte_refusal':counts[str(e['errno'])]=counts.get(str(e['errno']),0)+1
    result=dict(round=i+1,command=command,exit_code=r.returncode,seconds=round(time.perf_counter()-t,3),
                lock_operations=len(locks),wait_max=max(waits,default=0),hold_max=max(holds,default=0),
                lock_errors=[e for e in locks if e['error']],byte_refusal_errno_counts=counts,fsync_delay_ms=a.delay_ms,
                source_before=source_before,source_unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in source_before.items()))
    results.append(result);(folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
meta=dict(platform=platform.platform(),python=sys.version,results=results,
          source={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['context_storage.py','test_ultra_chat_storage.py']})
(target/'summary.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print('Results retained; failures are not overwritten',flush=True)
