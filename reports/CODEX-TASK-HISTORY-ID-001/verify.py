"""Final local source-integrity and index check; no product/runtime assertions."""
from pathlib import Path
import hashlib
import json
import os
import re
import sys

root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
sys.path.insert(0,str(Path(os.environ['TEMP'])/'ag_llm_token_audit_deps'))
import tiktoken
from tools import task_history as h,task_slot_rotate as s

def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def wiki(text):
    result=set();fence=None
    for line in text.splitlines():
        m=re.match(r'^\s*(`{3,}|~{3,})',line)
        if m:
            mark=m.group(1)
            if fence is None:fence=(mark[0],len(mark))
            elif mark[0]==fence[0] and len(mark)>=fence[1]:fence=None
            continue
        if fence is None:result.update(re.findall(r'\[\[.*?\]\]',re.sub(r'`[^`]*`','',line)))
    return result

def section(t,heading):
    a=t.index(heading);m=re.search(r'^## ',t[a+len(heading):],re.M)
    return t[a:] if not m else t[a:a+len(heading)+m.start()]

migration=json.loads((out/'migration.json').read_text(encoding='utf-8'))
enc=tiktoken.get_encoding('o200k_base');stats={};graph={};slots={}
for name,entry in migration['sources'].items():
    p=root/'Документация'/name;before=root/entry['snapshot']
    assert hashfile(before)==entry['before_sha256']
    old=before.read_text(encoding='utf-8-sig');new=p.read_text(encoding='utf-8-sig')
    stats[name]={'tokens_before':len(enc.encode(old)),'tokens_after':len(enc.encode(new)),
                 'bytes':p.stat().st_size,'sha256':hashfile(p)}
    if wiki(old)!=wiki(new):graph[name]={'removed':sorted(wiki(old)-wiki(new)),'added':sorted(wiki(new)-wiki(old))}
    if name in ('000_Задачи Codex.md','000_Задачи Claude.md'):
        a,b=s.parse(before.read_bytes()),s.parse(p.read_bytes())
        slots[name]=all(a.body(*pair)[0]==b.body(*pair)[0] for pair in [('b1b','b1e'),('b11b','b11e')])
        assert slots[name]
assert not graph,graph
old05=(out/'preservation/05_Реестр задач.md').read_text(encoding='utf-8-sig')
new05=(root/'Документация/05_Реестр задач.md').read_text(encoding='utf-8')
for heading in ['## Очередь открытых продолжений (FOLLOWUP)','## Оперативные риск-карточки']:
    assert section(old05,heading).rstrip()==section(new05,heading).rstrip(),heading
counts={}
for agent,name in h.CARDS.items():
    text=(root/'Документация'/name).read_text(encoding='utf-8')
    count=len(re.findall(r'^\| \d{4}-',text,re.M));assert count<=10;counts[agent]=count
records=h.all_records(root)
assert len({r['history_id'] for r in records})==len(records)
for r in records:
    for ref in r['sources'].values():h.source_text(root,ref)
verification={'encoding':'o200k_base','source_snapshots_verified':len(migration['sources']),
    'active_slots_unchanged':slots,'followup_and_risk_bodies_unchanged':True,
    'effective_wiki_edges_unchanged':True,'index_rows':counts,'records':len(records),
    'unique_history_ids':True,'source_hashes':'VERIFIED','documents':stats}
(out/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
artifacts=[root/'tools'/f for f in ['task_history.py','test_task_history.py','task_slot_rotate.py','task_slot_monitor.py','TASK_SLOT_ROTATION.md']]
artifacts += [root/'Документация'/name for name in migration['sources']]
artifacts += list((root/'Документация/Правила').glob('*.md'))
artifacts += list(out.rglob('*'))
artifacts += [root/'reports/task_history_sequences.json']+[h.record_path(root,r['id']) for r in records]
files=sorted({p for p in artifacts if p.is_file() and p.name!='manifest.json'},key=str)
manifest={'status':'RESULT READY / LOCAL; INDEPENDENT REVIEW PENDING',
    'task_id':'CODEX-TASK-HISTORY-ID-001','history_id':h.load_record(root,'CODEX-TASK-HISTORY-ID-001')['history_id'],
    'validation':{'tests_run':123,'pass':122,'fail':1,'preexisting_failure':'Claude active task has NO_TASK_ID'},
    'files':[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashfile(p)} for p in files]}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(hashfile(root/entry['path'])==entry['sha256'] for entry in manifest['files'])
print(json.dumps({'verified_snapshots':len(migration['sources']),'indexes':counts,'records':len(records),
 'manifest_files':len(files),'source_integrity':'PASS','graph':'PASS','active_slots':'UNCHANGED'},ensure_ascii=False))
