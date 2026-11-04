"""Build the PARTIAL handoff manifest and verify no product/user-history changes. No Git."""
from pathlib import Path
import hashlib
import json
import sys

REPORT=Path(__file__).resolve().parent
ROOT=REPORT.parents[1]
baseline=json.loads((REPORT/'evidence/baseline.json').read_text(encoding='utf-8'))
def fp(path):
    data=path.read_bytes()
    return dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())
unchanged=[]
for row in baseline['source']:
    assert fp(REPORT/'before'/(row['path']+'.source.txt'))=={k:row[k] for k in ('size','sha256')}
    if row['path']!='Документация/000_Задачи Codex.md':
        assert fp(ROOT/row['path'])=={k:row[k] for k in ('size','sha256')}, 'Unexpected product edit: '+row['path']
        unchanged.append(row['path'])
counts={name:dict(checked=0,matching=0) for name in ['.ultra','Чат_pro','Чат_Pro_01','.obsidian']}
changes=[]
for row in baseline['protected']:
    name=row['path'].split('/')[0]; counts[name]['checked']+=1
    p=ROOT/row['path']; now=fp(p) if p.is_file() else None
    if now=={k:row[k] for k in ('size','sha256')}:
        counts[name]['matching']+=1
    else:
        changes.append(dict(path=row['path'],before={k:row[k] for k in ('size','sha256')},after=now))
known={row['path'] for row in baseline['protected']}
added=[p.relative_to(ROOT).as_posix() for name in counts for p in (ROOT/name).rglob('*')
       if p.is_file() and p.relative_to(ROOT).as_posix() not in known]
data=dict(counts=counts,changes=changes,added=added,obsidian_written_by_agent=False,
          history_unchanged=all(v['checked']==v['matching'] for k,v in counts.items() if k!='.obsidian'))
(REPORT/'evidence/user_data_readback.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
assert data['history_unchanged'] and not [p for p in added if not p.startswith('.obsidian/')]

sys.path.insert(0,str(ROOT/'tools'))
import task_slot_rotate as slots
card=ROOT/'Документация/000_Задачи Codex.md'
before=REPORT/'before/Документация/000_Задачи Codex.md.source.txt'
def outside(content):
    for begin,end in [(slots.B1_BEGIN,slots.B1_END),(slots.B11_BEGIN,slots.B11_END)]:
        head,found,rest=content.partition(begin.encode()); assert found
        _body,found_end,tail=rest.partition(end.encode()); assert found_end
        content=head+found+b'<SLOT>'+found_end+tail
    return content
card_result=dict(before=fp(before),after=fp(card),outside_slots_identical=outside(before.read_bytes())==outside(card.read_bytes()))
assert card_result['outside_slots_identical']
(REPORT/'evidence/card_readback.json').write_text(json.dumps(card_result,indent=2),encoding='utf-8')
for name,code in [('js_guarded.json',0),('python_guarded_final.json',0),('run_store_guarded_final_v3.json',0),('prerequisites_guarded_final.json',1)]:
    result=json.loads((REPORT/'evidence'/name).read_text(encoding='utf-8'))
    assert result['exit_code']==code and result['guard_denials']==0
    for path,row in result['source'].items():
        assert fp(ROOT/path)==row, 'Source drift after checks: '+path
summary=dict(product_files_unchanged=unchanged,user_data=data,card=card_result)
(REPORT/'evidence/package_readback.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
paths=[ROOT/r['path'] for r in baseline['source']]+[ROOT/'test_web_alarm_ultra_chat_turn.py']
paths+=sorted(p for p in REPORT.rglob('*') if p.is_file() and p!=REPORT/'manifest.json')
entries=[dict(path=p.relative_to(ROOT).as_posix(),**fp(p)) for p in dict.fromkeys(paths)]
manifest=dict(task_id='CODEX-WUA-CHAT-S3-TURN-RECOVERY-001',status='PARTIAL / RUN STORE BLOCKED / AWAITING INDEPENDENT REVIEW',
              source_basis='exact local bytes; reference revision in task is not Git-verified',files=entries,
              exclusions=['manifest.json self-reference'],git_used=False,provider_calls=0)
(REPORT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for row in entries: assert fp(ROOT/row['path'])=={k:row[k] for k in ('size','sha256')}
print(json.dumps(dict(manifest_entries=len(entries),**summary),ensure_ascii=False))
