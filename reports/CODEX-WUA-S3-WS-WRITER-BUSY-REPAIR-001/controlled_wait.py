"""Measure a genuine bounded busy refusal, release and explicit idempotent continuation on TEMP only."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import context_storage as cs

def snapshot(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

with tempfile.TemporaryDirectory(prefix='wua_busy_control_') as temp:
    base=Path(temp);root=base/'workspace';root.mkdir();ws=cs.ensure_workspace_storage(root)['workspace_id'];chat=cs.create_chat(root)['chat_id']
    ready=base/'ready';release=base/'release'
    code=r'''
import json,sys,time
from pathlib import Path
import context_storage as cs
root,ready,release=map(Path,sys.argv[1:4])
with cs._existing_workspace_writer(root):
    acquired=time.perf_counter();ready.write_text(str(acquired));deadline=time.monotonic()+25
    while not release.exists():
        if time.monotonic()>deadline:raise RuntimeError('bounded holder control expired')
        time.sleep(.01)
print(json.dumps(dict(acquired=acquired,released=time.perf_counter())))
'''
    child=subprocess.Popen([sys.executable,'-B','-c',code,str(root),str(ready),str(release)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+5
        while not ready.exists():
            assert child.poll() is None and time.monotonic()<deadline
            time.sleep(.01)
        before=snapshot(root);start=time.perf_counter()
        try:cs.commit_raw_message(root,chat,'msg_'+'7'*32,'user','explicit continuation',expected_workspace_id=ws)
        except cs.WorkspaceBusyError as exc:failure=dict(type=type(exc).__name__,code=exc.code,seconds=time.perf_counter()-start)
        else:raise AssertionError('simultaneous writer was incorrectly admitted')
        assert 9.8<=failure['seconds']<15,failure
        assert before==snapshot(root),'busy refusal changed Workspace data'
    finally:
        release.write_text('release')
        try:out,err=child.communicate(timeout=8)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=5)
    assert child.returncode==0,err
    holder=json.loads(out)
    result=cs.commit_raw_message(root,chat,'msg_'+'7'*32,'user','explicit continuation',expected_workspace_id=ws)
    assert result['created'] is True
    same=cs.commit_raw_message(root,chat,'msg_'+'7'*32,'user','explicit continuation',expected_workspace_id=ws)
    assert same['created'] is False
    raw=list((root/'.ultra/chats'/chat/'messages').glob('*.json'));assert len(raw)==1
    assert json.loads(raw[0].read_bytes())['original_text']=='explicit continuation'
    print(json.dumps(dict(default_timeout=cs.WRITER_LOCK_TIMEOUT_SECONDS,visible_failure=failure,holder=holder,
                         before_after_busy_equal=True,explicit_continuation_created_once=True,raw_count=1,temporary_only=True)))
