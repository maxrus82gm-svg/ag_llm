"""12 bounded executions of the original oracle, ordinary vs short repeated extra acquisitions.

All monkeypatches are process-local observers/test-fixture lifecycle wrappers. No source, lock algorithm,
timeout, RAW retry, fsync delay or production data change. Original functional workload/assertions run unchanged.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest

START=time.monotonic();DEADLINE=START+300
REPORT=Path(__file__).resolve().parent;ROOT=REPORT.parents[1]
sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser();parser.add_argument('--label',default='series',help='New evidence directory; never overwrite an earlier series')
args=parser.parse_args();assert re.fullmatch(r'[A-Za-z0-9_-]{1,32}',args.label)
EVIDENCE=REPORT/'evidence';SERIES=EVIDENCE/args.label;SERIES.mkdir()
SELECTOR='test_ultra_chat_storage.ConcurrencyTests.test_two_processes_write_raw_create_and_rename_without_losing_anything'
os.environ['WUA_BUSY_TRACE_DIR']=str(SERIES/'setup_trace')
os.environ['WUA_BUSY_LIVE_TRACE']='1'
import writer_trace as trace
import test_ultra_chat_storage as tests

stop_watchdog=threading.Event();expired=threading.Event();tracked=[];tracked_lock=threading.Lock()
def watchdog():
    if stop_watchdog.wait(max(0,DEADLINE-time.monotonic())):return
    expired.set()
    with tracked_lock:children=list(tracked)
    for child in children:
        if child.poll() is None:child.kill()
watch=threading.Thread(target=watchdog,daemon=True);watch.start()
current={}
spawn=tests.Base.spawn;workspace=tests.Base.workspace;cleanup=tests.Base._cleanup

def save_child(child,out,err):
    prefix=current['folder']/('child_'+str(child.pid))
    prefix.with_suffix('.stdout.txt').write_text(out or '',encoding='utf-8')
    prefix.with_suffix('.stderr.txt').write_text(err or '',encoding='utf-8')
    current.setdefault('children',{})[str(child.pid)]=dict(pid=child.pid,exit_code=child.returncode,pulse=child is current.get('pulse'))

def spawn_observed(self,code,*args):
    assert time.monotonic()<DEADLINE,'diagnostic budget exhausted'
    child=spawn(self,code,*args)
    with tracked_lock:tracked.append(child)
    return child

def finish_observed(self,child,timeout=120):
    try:out,err=child.communicate(timeout=max(.01,min(timeout,DEADLINE-time.monotonic())))
    except subprocess.TimeoutExpired:
        expired.set();child.kill();out,err=child.communicate(timeout=5)
    save_child(child,out,err)
    self.assertEqual(child.returncode,0,err)
    return out

PULSE=r'''
from pathlib import Path
import json,sys,time
import context_storage as cs
root,ready,stop=map(Path,sys.argv[2:5]);ready.write_text('ready');acquisitions=0
while not stop.exists():
    try:
        with cs._workspace_writer_lock(cs._write_anchor(root)):
            acquisitions+=1;time.sleep(.020)
    except cs.WorkspaceBusyError:
        pass
    time.sleep(.002)
print(json.dumps(dict(acquisitions=acquisitions,hold_seconds=.020,free_sleep_seconds=.002)))
'''

def workspace_observed(self,*args,**kwargs):
    root,ws,chat=workspace(self,*args,**kwargs)
    assert root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
    current.update(root=root,workspace_id=ws,chat=chat)
    if current['condition']=='short_reacquire':
        ready=self.base/'pulse_ready';stop=self.base/'pulse_stop';current['pulse_stop']=stop
        current['pulse']=self.spawn(PULSE,root,ready,stop)
        end=min(DEADLINE,time.monotonic()+10)
        while not ready.exists():
            assert time.monotonic()<end and current['pulse'].poll() is None,'pulse did not start'
            time.sleep(.005)
    return root,ws,chat

def integrity(root,ws,chat):
    files=list((root/'.ultra/chats'/chat/'messages').glob('*.json'));records=[];damage=[]
    for path in files:
        try:
            value=json.loads(path.read_bytes())
            assert path.name==value['message_id']+'.json' and value['workspace_id']==ws and value['chat_id']==chat
            records.append(value)
        except (ValueError,KeyError,AssertionError) as error:damage.append(dict(file=path.name,error=type(error).__name__))
    expected={f'p{n}-{k}' for n in range(2) for k in range(25)}
    ordered=all([v['created_at'] for v in sorted((v for v in records if v['original_text'].startswith('p'+str(n)+'-')),key=lambda v:int(v['original_text'].split('-')[1]))]==sorted(v['created_at'] for v in records if v['original_text'].startswith('p'+str(n)+'-')) for n in range(2))
    inventory=[dict(path=p.relative_to(root).as_posix(),size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob('*') if p.is_file()]
    temporary=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.name.endswith('.tmp')]
    value=dict(raw_count=len(files),valid_records=len(records),damage=damage,unique_ids=len({v['message_id'] for v in records}),
               exact_expected_payloads={v['original_text'] for v in records}==expected,per_writer_order=ordered,
               temporary_files=temporary,staging_exists=(root/'.ultra/chat_staging').exists(),raw=records,inventory=inventory)
    value['complete_integrity_ok']=(len(files)==50 and not damage and value['unique_ids']==50 and value['exact_expected_payloads'] and ordered and not temporary and not value['staging_exists'])
    return value

def cleanup_observed(self):
    if current.get('pulse_stop'):current['pulse_stop'].write_text('stop')
    for child in self.children:
        if child.poll() is None:
            if child is current.get('pulse'):
                try:child.wait(timeout=1)
                except subprocess.TimeoutExpired:child.kill()
            else:child.kill()
        out,err=child.communicate(timeout=5);save_child(child,out,err)
    if 'root' in current:
        data=integrity(current['root'],current['workspace_id'],current['chat'])
        (current['folder']/'integrity.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        current['integrity_ok']=data['complete_integrity_ok']
    assert self.base.resolve().parent==Path(tempfile.gettempdir()).resolve(),'refuse cleanup outside owned TEMP'
    cleanup(self)

tests.Base.spawn=spawn_observed;tests.Base.finish=finish_observed
tests.Base.workspace=workspace_observed;tests.Base._cleanup=cleanup_observed
source_names=['context_storage.py','test_ultra_chat_storage.py']
results=[]
print(json.dumps(dict(selector=SELECTOR,planned_runs=12,hard_limit_runs=20,wall_budget_seconds=300,conditions=['ordinary','short_reacquire'],pulse_hold=.020,pulse_free_sleep=.002)),flush=True)
try:
    for number,condition in enumerate(['ordinary','short_reacquire']*6,1):
        if expired.is_set() or time.monotonic()>=DEADLINE:break
        folder=SERIES/str(number);folder.mkdir()
        current.clear();current.update(folder=folder,condition=condition)
        os.environ['WUA_BUSY_TRACE_DIR']=str(folder/'trace');trace.events.clear()
        before={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
        output=io.StringIO();start=time.perf_counter()
        result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(SELECTOR))
        trace.save()
        (folder/'unittest.txt').write_text(output.getvalue(),encoding='utf-8')
        records=[(v['pid'],event) for f in (folder/'trace').glob('*.json') for v in [json.loads(f.read_text())] for event in v['events']]
        locks=[dict(pid=pid,**e) for pid,e in records if e['kind']=='lock' and not e['nested']]
        sequence=sorted((v for v in locks if v['acquired'] is not None),key=lambda v:v['acquired'])
        fsync=[e['end']-e['start'] for _,e in records if e['kind']=='fsync']
        refusals=[e for _,e in records if e['kind']=='byte_refusal']
        row=dict(run=number,condition=condition,seconds=time.perf_counter()-start,tests=result.testsRun,
                 failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),passed=result.wasSuccessful(),
                 budget_aborted=expired.is_set(),children=list(current.get('children',{}).values()),integrity_ok=current.get('integrity_ok'),
                 wait_max=max((v['acquired']-v['start'] for v in sequence),default=0),
                 body_hold_max=max((v.get('released',v['end'])-v['acquired'] for v in sequence),default=0),
                 fsync_count=len(fsync),fsync_max=max(fsync,default=0),fsync_total=sum(fsync),
                 os_errno_counts={str(n):sum(e['errno']==n for e in refusals) for n in {e['errno'] for e in refusals}},
                 timeout_events=[v for v in locks if v.get('error')],acquisition_sequence=sequence,
                 source_before=before,source_unchanged=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in before.items()))
        (folder/'result.json').write_text(json.dumps(row,indent=2),encoding='utf-8');results.append(row)
        assert row['source_unchanged']
        if row['passed']:assert row['integrity_ok'],'independent RAW integrity oracle failed'
        print(json.dumps({k:v for k,v in row.items() if k not in ['acquisition_sequence','source_before','children']}),flush=True)
        with tracked_lock:tracked.clear()
        if row['budget_aborted']:break
finally:stop_watchdog.set();watch.join(2)
summary=dict(selector=SELECTOR,planned_runs=12,executed_runs=len(results),wall_seconds=time.monotonic()-START,budget_seconds=300,
             budget_expired=expired.is_set(),all_passed=all(r['passed'] for r in results),results=results)
(EVIDENCE/('diagnostic_summary.json' if args.label=='series' else 'diagnostic_summary_'+args.label+'.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(dict(executed_runs=len(results),wall_seconds=summary['wall_seconds'],all_passed=summary['all_passed'],budget_expired=summary['budget_expired'])),flush=True)
