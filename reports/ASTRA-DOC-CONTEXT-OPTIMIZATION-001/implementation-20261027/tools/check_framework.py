"""Check real documentation invariants and negative controls. No runtime/Git calls."""
from pathlib import Path
from collections import Counter
import json,re,sys
from doc_migration import WORK,ROOT,DOC,h,headings,graph,dump

base=json.loads((WORK/'evidence/baseline.json').read_text(encoding='utf-8'))
checks=[]
def test(name,value,detail): checks.append({'name':name,'pass':bool(value),'detail':detail})
def candidate(prefix):
    p=next(p for p in (WORK/'candidate').glob('*.txt') if p.name.startswith(prefix))
    return p.read_bytes().decode('utf-8-sig')

snapshot_ok=all(h((ROOT/x['snapshot']).read_bytes())==x['sha256'] for x in base['targets'])
test('Exact restorable snapshots',snapshot_ok,{'files':len(base['targets'])})
parity=[]
for x in base['targets']:
    n=Path(x['source']).name
    a=(ROOT/x['snapshot']).read_text(encoding='utf-8')
    b=(WORK/'candidate'/(n+'.txt')).read_text(encoding='utf-8')
    parity.append(graph(a)==graph(b) and not (Counter(headings(a))-Counter(headings(b))))
test('All original graph syntax and heading occurrences retained',all(parity),{'files':len(parity),'live_graph_export':'NOT RUN'})

for prefix in ['05_','06_']:
    x=next(x for x in base['targets'] if Path(x['source']).name.startswith(prefix))
    raw=(ROOT/x['snapshot']).read_bytes();draft=(WORK/'candidate'/(Path(x['source']).name+'.txt')).read_bytes()
    test('Original '+prefix+' bytes unchanged suffix',draft.endswith(raw),{'original_bytes':len(raw)})
cards=[]
for prefix in ['000_Задачи ChatGPT','000_Задачи Claude','000_Задачи Codex','000_Задачи Ultra']:
    x=next(x for x in base['targets'] if Path(x['source']).name.startswith(prefix))
    raw=(ROOT/x['snapshot']).read_bytes();draft=(WORK/'candidate'/(Path(x['source']).name+'.txt')).read_bytes();needle='# БЛОК 1'.encode()
    cards.append(raw[raw.index(needle):]==draft[draft.index(needle):])
test('All personal B1-B4 bytes unchanged',all(cards),{'cards':len(cards)})

sizes={p:len(candidate(p)) for p in ['08_','34_','000_Задачи для']}
test('Full document budgets',sizes['08_']<=16000 and 15000<=sizes['34_']<=25000,
     {**sizes,'08_target_8000_12000_met':8000<=sizes['08_']<=12000,'08_upper_limit':16000})

ops=candidate('18_');forms=candidate('07_');start=candidate('08_');route=candidate('000_Задачи для')
required_sections=['OPS-START','OPS-OWNERS','OPS-REVIEW','OPS-CLOSE','OPS-LOCATOR','OPS-RISK','OPS-BUDGET','OPS-EXIT']
test('Coordinator has explicit operating sections',all('### '+s+' —' in ops for s in required_sections),required_sections)
required_risk=['risk_id','FACT_DEFECT','RISK_HYPOTHESIS','VERIFICATION_GAP','impact','likelihood','confidence',
               'affected_gate','owner','verifier','action','closure_evidence','status','updated_at','next_review_trigger','residual_decision']
test('Risk form includes evidence, owners and closure conditions',all(x in forms for x in required_risk),required_risk)
test('Forms include review, archive and closeout',all(x in forms for x in ['Форма независимого verdict','Форма истории №06 и персональной №001','Форма closeout-проверки координатора','БЛОК 1 освобождается последним']) if 'БЛОК 1 освобождается последним' in forms else all(x in forms for x in ['Форма независимого verdict','Форма истории №06 и персональной №001','Форма closeout-проверки координатора','B1 последним']), 'Explicit forms; no executor self-rotation')
new_rule=ops[ops.index('## DOC-CONTEXT-OPS-01'):ops.index('## Нормативный индекс')]
requires=re.search(r'requires: \[([^\]]+)\]',new_rule)[1].split(', ')
definition_ids=re.findall(r'^## (DOC-[A-Z0-9-]+) —',ops,re.M)
missing=[r for r in requires if r.split('@')[0] not in definition_ids]
test('Every new direct DOC dependency has exact definition',not missing,{'requires':requires,'missing':missing})
test('New canonical rule has one definition',definition_ids.count('DOC-CONTEXT-OPS-01')==1,{'count':definition_ids.count('DOC-CONTEXT-OPS-01')})
test('Blind entry is before ordinary route',start.index('INDEPENDENT_PLAN')<start.index('## Обычный маршрут'), 'No automatic ordinary-route exposure')

records=json.loads((WORK/'evidence/registry_record_index.json').read_text(encoding='utf-8'))['records']
source=next((WORK/'preservation').glob('05_*.source.txt')).read_text(encoding='utf-8').splitlines()
ids=[r['record_id'] for r in records]
test('Registry record locators reproduce exact existing rows',len(ids)==len(set(ids)) and all(h(source[r['original_line']-1].encode('utf-8'))==r['row_sha256_utf8'] for r in records),{'records':len(records)})
test('Unusual final registry record indexed',any('CLAUDE-WA-017' in r['identity'] and r['original_line']==442 for r in records),'Original final record after links section')

# Negative controls verify that structural gate rejects real prohibited edits.
sample=next(x for x in base['targets'] if Path(x['source']).name.startswith('34_'))
old=(ROOT/sample['snapshot']).read_text(encoding='utf-8')
bad=old.replace('[[05_Реестр задач]]','[[08_Старт]]',1)
test('Negative control: redirecting existing edge detected',graph(old)!=graph(bad),'Same number of Wiki tokens, different directed target')
bad=old+'\n[[05_Реестр задач]]\n'
test('Negative control: duplicate edge occurrence detected',graph(old)!=graph(bad),'Multiset rather than count/set only')
header=headings(old)[0];bad=old.replace(header,'## Renamed protected heading',1)
test('Negative control: losing existing heading detected',bool(Counter(headings(old))-Counter(headings(bad))),header)
raw=next((WORK/'preservation').glob('06_*.source.txt')).read_bytes()
test('Negative control: archive byte loss detected',not (b'new intro\n'+raw[:-1]).endswith(raw),'One-byte loss at end')

# Bounded cross-workspace observation; mutable Obsidian workspace state is reported separately.
allowed={x['source'] for x in base['targets']}
changed=[];missing=[]
for path,value in base['files'].items():
    if path in allowed: continue
    p=ROOT/path
    if not p.exists(): missing.append(path)
    elif h(p.read_bytes())!=value['sha256']: changed.append(path)
unexpected=[p for p in changed if p!='.obsidian/workspace.json']
test('No unrelated stable file drift',not (unexpected or missing),{'changed':changed,'missing':missing,'workspace_state_exception_is_not_agent_write_proof':True})
test('Obsidian graph configuration unchanged',h((ROOT/'.obsidian/graph.json').read_bytes())==base['files']['.obsidian/graph.json']['sha256'],'graph.json')
history=[p for p in base['files'] if p.startswith('Документация/001_')]
test('Personal archives unchanged',all(h((ROOT/p).read_bytes())==base['files'][p]['sha256'] for p in history),{'archives':len(history)})

result={'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks),'checks':checks,
        'classification':'Author documentary checks, not independent acceptance; no product runtime/CI run'}
dump(WORK/'evidence/framework_checks.json',result)
print(json.dumps(result,ensure_ascii=False))
sys.exit(1 if result['failed'] else 0)
