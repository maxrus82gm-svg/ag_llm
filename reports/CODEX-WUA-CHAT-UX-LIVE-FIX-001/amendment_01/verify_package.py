"""Readback/manifest for the first-chat amendment. Older sources, evidence and snapshots remain preserved."""
from pathlib import Path
import hashlib
import json
import sys

AMEND=Path(__file__).resolve().parent
REPORT=AMEND.parent
ROOT=REPORT.parents[1]
baseline=json.loads((AMEND/'evidence/baseline.json').read_text(encoding='utf-8'))
def fp(p):
    data=p.read_bytes()
    return dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())

for entry in baseline['source']:
    assert fp(AMEND/'before'/entry['path'])=={k:entry[k] for k in ('size','sha256')}, 'Amendment input snapshot drift'
for entry in baseline['source'][:5]:
    if entry['path']=='web_alarm/workspace_registry.py':
        assert fp(ROOT/entry['path'])=={k:entry[k] for k in ('size','sha256')}, 'Registry source changed'

# Every pre-existing evidence file stays byte-identical; mutable source/report files have explicit phase snapshots.
old_manifest=json.loads((AMEND/'before/reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/manifest.json').read_text(encoding='utf-8'))
mutable={e['path'] for e in baseline['source']}
mutable.update(['Документация/000_Задачи Codex.md','reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/reproduce_red.py'])
preserved=0
for entry in old_manifest['files']:
    if entry['path'] not in mutable:
        assert fp(ROOT/entry['path'])=={k:entry[k] for k in ('size','sha256')}, 'Previous evidence drift: '+entry['path']
        preserved+=1

counts={name:dict(checked=0,matching=0) for name in baseline['protected_roots']}
changes=[]
for row in baseline['protected']:
    counts[row['path'].split('/')[0]]['checked']+=1
    p=ROOT/row['path']; now=fp(p) if p.is_file() else None
    if now=={k:row[k] for k in ('size','sha256')}:
        counts[row['path'].split('/')[0]]['matching']+=1
    else:
        changes.append(dict(path=row['path'],before={k:row[k] for k in ('size','sha256')},after=now))
known={r['path'] for r in baseline['protected']}
added=[p.relative_to(ROOT).as_posix() for name in counts for p in (ROOT/name).rglob('*')
       if p.is_file() and p.relative_to(ROOT).as_posix() not in known]
user_data=dict(counts=counts,changes=changes,added=added,
               data_roots_match=all(v['checked']==v['matching'] for name,v in counts.items() if name!='.obsidian'),
               obsidian_written_by_agent=False)
(AMEND/'evidence/user_data_readback.json').write_text(json.dumps(user_data,ensure_ascii=False,indent=2),encoding='utf-8')
assert user_data['data_roots_match'] and not added, 'Unexpected protected data drift'

for name in ['js_regression_amendment_01_final.json','python_regression_amendment_01_final.json']:
    result=json.loads((REPORT/'evidence'/name).read_text(encoding='utf-8'))
    assert result['exit_code']==0
    for path,row in result['source'].items():
        assert fp(ROOT/path)==dict(size=row['bytes'],sha256=row['sha256']), 'Source drift after tests'
sys.path.insert(0,str(ROOT/'tools'))
import task_slot_rotate as slots
def outside(content):
    for start,end in [(slots.B1_BEGIN,slots.B1_END),(slots.B11_BEGIN,slots.B11_END)]:
        prefix,found,tail=content.partition(start.encode('utf-8')); assert found
        _body,found_end,suffix=tail.partition(end.encode('utf-8')); assert found_end
        content=prefix+found+b'<SLOT>'+found_end+suffix
    return content
card=ROOT/'Документация/000_Задачи Codex.md'
old_card=AMEND/'before/Документация/000_Задачи Codex.md.source.txt'
card_result=dict(before=fp(old_card),after=fp(card),outside_slots_identical=outside(old_card.read_bytes())==outside(card.read_bytes()))
assert card_result['outside_slots_identical']
(AMEND/'evidence/card_readback.json').write_text(json.dumps(card_result,indent=2),encoding='utf-8')
snapshot=AMEND/'handoff_task.md'
amendment=REPORT/'chat_amendment_01.md'
if snapshot.exists():
    parts=slots.snapshot_parts(snapshot.read_bytes())
    assert parts and len(parts[1])==1 and parts[1][0]==amendment.read_bytes().replace(b'\r\n',b'\n'), 'Amendment bytes not preserved in snapshot'

summary=dict(previous_immutable_artifacts_verified=preserved,user_data=user_data,card=card_result,amendment_sha256=fp(amendment)['sha256'])
(AMEND/'evidence/package_readback.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
status='RESULT READY / AWAITING INDEPENDENT VERIFICATION'
finish=AMEND/'evidence/finish.json'
if finish.exists() and json.loads(finish.read_text(encoding='utf-8')).get('result') not in ['ROTATED','ALREADY_ROTATED','CLEARED_DUPLICATE_BLOCK1']:
    status='PARTIAL / SLOT FINISH BLOCKED; AMENDMENT IMPLEMENTED'
sources=[ROOT/e['path'] for e in baseline['source'][:5]]+[card]
sources += [ROOT/name for name in ['context_storage.py','web_alarm/server.py','Start_WebAlarm.bat','web_alarm/launcher.py','web_alarm/launch_config.json','tools/task_slot_rotate.py']]
files=sources+sorted(p for p in REPORT.rglob('*') if p.is_file() and p not in [REPORT/'manifest.json',AMEND/'manifest.json'])
entries=[dict(path=p.relative_to(ROOT).as_posix(),**fp(p)) for p in dict.fromkeys(files)]
manifest=dict(task_id='CODEX-WUA-CHAT-UX-LIVE-FIX-001',status=status,latest_amendment='reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/chat_amendment_01.md',
              latest_report='reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/report.md',hash='SHA-256',files=entries,
              exclusions=['root manifest.json and amendment_01/manifest.json (same generated manifest; no cyclic self-hash)'],
              git_used=False,user_conversation_contents_copied=False)
for path in [REPORT/'manifest.json',AMEND/'manifest.json']:
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for row in entries:
    assert fp(ROOT/row['path'])=={k:row[k] for k in ('size','sha256')}
print(json.dumps(dict(status=status,manifest_entries=len(entries),**summary),ensure_ascii=False))
