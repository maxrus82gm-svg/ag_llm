"""Opt-in process-local diagnostic wrappers. Only disposable tests; production files are not edited."""
import atexit
import contextlib
import json
import os
from pathlib import Path
import time

import context_storage as cs

events=[]
phase='setup'
delay=float(os.environ.get('WUA_BUSY_FSYNC_DELAY_MS','0'))/1000
assert 0<=delay<=.5
lock=cs._workspace_writer_lock
fsync=os.fsync

def live(kind, **fields):
    if not os.environ.get('WUA_BUSY_LIVE_TRACE'):return
    folder=Path(os.environ['WUA_BUSY_TRACE_DIR']);folder.mkdir(parents=True,exist_ok=True)
    with (folder/(str(os.getpid())+'.live.jsonl')).open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(dict(kind=kind,phase=phase,time=time.perf_counter(),**fields))+'\n')

@contextlib.contextmanager
def traced_lock(anchor):
    started=time.perf_counter()
    nested=bool(cs._held_writer_locks())
    acquired=None
    try:
        with lock(anchor):
            acquired=time.perf_counter()
            live('acquired',nested=nested)
            try:yield
            finally:
                released=time.perf_counter()
                live('body_end',nested=nested)
    except BaseException as exc:
        live('error',error=type(exc).__name__,nested=nested)
        events.append(dict(kind='lock',phase=phase,nested=nested,start=started,acquired=acquired,
                           end=time.perf_counter(),error=type(exc).__name__,code=getattr(exc,'code',None)))
        raise
    else:
        events.append(dict(kind='lock',phase=phase,nested=nested,start=started,acquired=acquired,
                           released=released,end=time.perf_counter(),error=None))

def traced_fsync(fd):
    start=time.perf_counter()
    if delay:time.sleep(delay)
    try:return fsync(fd)
    finally:events.append(dict(kind='fsync',phase=phase,start=start,end=time.perf_counter(),injected_delay=delay))

cs._workspace_writer_lock=traced_lock
os.fsync=traced_fsync

def wrap_operation(name):
    original=getattr(cs,name)
    def call(*args,**kwargs):
        global phase
        previous=phase;phase=name
        if name=='append_raw_message' and len(args)>3:phase+=':'+str(args[3])
        try:return original(*args,**kwargs)
        finally:phase=previous
    setattr(cs,name,call)
for name in ['append_raw_message','create_chat','rename_chat']:wrap_operation(name)
if os.name=='nt':
    byte_lock=cs.msvcrt.locking
    def traced_byte(fd,mode,count):
        start=time.perf_counter()
        try:return byte_lock(fd,mode,count)
        except OSError as exc:
            events.append(dict(kind='byte_refusal',phase=phase,start=start,end=time.perf_counter(),mode=mode,
                               errno=exc.errno,winerror=getattr(exc,'winerror',None)))
            raise
    cs.msvcrt.locking=traced_byte

def save():
    folder=Path(os.environ['WUA_BUSY_TRACE_DIR']);folder.mkdir(parents=True,exist_ok=True)
    (folder/(str(os.getpid())+'.json')).write_text(json.dumps(dict(pid=os.getpid(),events=events),indent=2),encoding='utf-8')
atexit.register(save)
