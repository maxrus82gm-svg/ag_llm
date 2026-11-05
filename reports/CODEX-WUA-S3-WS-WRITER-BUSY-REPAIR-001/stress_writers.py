"""Bounded real multiprocess storage stress with independent file/payload/ordering/exclusion oracles."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import context_storage as cs

CODE=r'''
import contextlib,json,os,sys,time
from pathlib import Path
import context_storage as cs
root,base=Path(sys.argv[1]),Path(sys.argv[2]);worker=int(sys.argv[5]);count=int(sys.argv[6]);chat=sys.argv[4]
original=cs._workspace_writer_lock
@contextlib.contextmanager
def checked(anchor):
    nested=bool(cs._held_writer_locks())
    with original(anchor):
        if nested:yield;return
        gate=base/'exclusive'
        fd=os.open(gate,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
        try:yield
        finally:os.close(fd);gate.unlink()
cs._workspace_writer_lock=checked
(base/('ready'+str(worker))).write_text('ready')
deadline=time.monotonic()+15
while not (base/'go').exists():
    assert time.monotonic()<deadline
    time.sleep(.005)
made=[];ids=[];started=time.perf_counter()
for k in range(count):
    mid='msg_'+format(10000*worker+k,'032x')
    result=cs.commit_raw_message(root,chat,mid,'user','writer %d record %d ёж 😀'%(worker,k),expected_workspace_id=sys.argv[3])
    assert result['created'];ids.append(mid)
    if k%10==0:made.append(cs.create_chat(root,expected_workspace_id=sys.argv[3])['chat_id'])
    if k%4==0 or k==count-1:cs.rename_chat(root,chat,'writer-%d-%d'%(worker,k),expected_workspace_id=sys.argv[3])
print(json.dumps(dict(worker=worker,ids=ids,made=made,seconds=time.perf_counter()-started)))
'''

with tempfile.TemporaryDirectory(prefix='wua_writer_stress_') as temp:
    base=Path(temp);root=base/'workspace';root.mkdir();ws=cs.ensure_workspace_storage(root)['workspace_id'];chat=cs.create_chat(root)['chat_id']
    old=cs.commit_raw_message(root,chat,'msg_'+'f'*32,'user','preexisting RAW',expected_workspace_id=ws)
    old_sha=hashlib.sha256(Path(old['path']).read_bytes()).hexdigest()
    count,workers=40,4
    children=[subprocess.Popen([sys.executable,'-B','-c',CODE,str(root),str(base),ws,chat,str(n),str(count)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8') for n in range(workers)]
    try:
        deadline=time.monotonic()+15
        while not all((base/('ready'+str(n))).exists() for n in range(workers)):
            assert time.monotonic()<deadline and all(c.poll() is None for c in children)
            time.sleep(.005)
        (base/'go').write_text('go')
        outcomes=[]
        for child in children:
            out,err=child.communicate(timeout=90);assert child.returncode==0,err;outcomes.append(json.loads(out))
    finally:
        for child in children:
            if child.poll() is None:child.kill()
            child.communicate(timeout=5)
    messages=[json.loads(p.read_bytes()) for p in (root/'.ultra/chats'/chat/'messages').glob('*.json')]
    assert len(messages)==workers*count+1
    by_id={m['message_id']:m for m in messages};assert len(by_id)==len(messages)
    for outcome in outcomes:
        w=outcome['worker'];times=[]
        for k,mid in enumerate(outcome['ids']):
            value=by_id[mid];assert value['original_text']=='writer %d record %d ёж 😀'%(w,k)
            assert value['workspace_id']==ws and value['chat_id']==chat;times.append(value['created_at'])
        assert times==sorted(times),'per-writer RAW commit order changed'
    made=[c for r in outcomes for c in r['made']]
    titles=[json.loads((root/'.ultra/chats'/c/'metadata.json').read_bytes())['title'] for c in made]
    assert len(made)==16 and len(set(titles))==16
    final=json.loads((root/'.ultra/chats'/chat/'metadata.json').read_bytes())['title']
    assert final in {'writer-%d-39'%w for w in range(workers)}
    assert hashlib.sha256(Path(old['path']).read_bytes()).hexdigest()==old_sha
    assert not (base/'exclusive').exists() and not (root/'.ultra/chat_staging').exists()
    assert not [p for p in root.rglob('*') if p.name.endswith('.tmp')]
    print(json.dumps(dict(workers=workers,records_per_worker=count,raw_count=len(messages),created_chats=len(made),unique_ids=True,
                         exact_text_identity_and_order=True,exclusive_critical_section_marker=True,old_raw_sha_unchanged=True,
                         final_title=final,no_staging_or_temporary_files=True,child_results=outcomes),ensure_ascii=False))
