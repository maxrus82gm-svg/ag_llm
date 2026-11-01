"""Hash project inputs and extract addressed static definitions; never import application code."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT/'reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001'
def sha(b): return hashlib.sha256(b).hexdigest()
def save(name,obj):
    p=WORK/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

doc_prefixes=['08_','11_','18_','19_','34_','36.1_','36.3_','37_','40_']
docs=[p for p in (ROOT/'Документация').glob('*.md') if any(p.name.startswith(x) for x in doc_prefixes)]
docs += [ROOT/'Документация/Blueprint LLM.md',ROOT/'Документация/Blueprint LLM - тактический контекст.md',ROOT/'Документация/000_Задачи Codex.md',ROOT/'Документация/05_Реестр задач.md']
paths=list(ROOT.glob('*.py')) + [ROOT/'Start_WebAlarm.bat',ROOT/'web_alarm/launch_config.json']+docs
for folder in ['web_alarm','integrations','tools','.github']:
    paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo']]
records=[]
for p in sorted(set(paths)):
    if p.is_file():records.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
baseline=WORK/'evidence/source_baseline.json'
assert not baseline.exists(),'Do not overwrite baseline'
save('evidence/source_baseline.json',{'task':'CODEX-WUA-LOCAL-LLM-DISCOVERY-001','scope':'Explicit project sources/config and addressed documentation; excludes .git, live Workspace stores, environments and historical archives','files':records})
card=(ROOT/'Документация/000_Задачи Codex.md').read_text(encoding='utf-8-sig')
m=re.search(r'^###### [^\n]*TASK-SLOT:BLOCK-1:BEGIN[^\n]*\n(.*?)^###### [^\n]*TASK-SLOT:BLOCK-1:END',card,re.M|re.S)
assert m and 'CODEX-WUA-LOCAL-LLM-DISCOVERY-001' in m[1]
(WORK/'assignment_source.txt').write_text(m[1],encoding='utf-8',newline='\n')
selected={'model_registry.py':None,'web_alarm/ultra_connections.py':None,'web_alarm/model_cards.py':['Provider','ModelCards'],'web_alarm/ultra_chat.py':['UltraChatService','UltraChatAccess','UltraChatWriteAccess','_run_index'],'gigachat_transport.py':None,'context_storage.py':['commit_raw_message','create_chat_record','_existing_workspace_writer','_replace_verified'],'run_store.py':['audit_root','load_workspace_run_index','append_run_record','list_run_records','load_run_record','record_provider_attempt_started','record_provider_attempt_terminal'],'ultra_budget_policy.py':['AttemptRecord','reserve_attempt','mark_sent','mark_not_sent','apply_terminal','evaluate_request'],'server.py':['ask_gigachat','_request_audit_diagnostic']}
index=[]
for name,selectors in selected.items():
    p=ROOT/name;t=p.read_text(encoding='utf-8-sig');tree=ast.parse(t)
    symbols=[]
    for x in tree.body:
        if isinstance(x,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and (selectors is None or x.name in selectors):
            symbols.append({'symbol':x.name,'first_line':x.lineno,'last_line':x.end_lineno,'docstring':ast.get_docstring(x)})
    index.append({'path':name,'sha256':sha(p.read_bytes()),'symbols':symbols,'method':'AST static parse only, no application import'})
save('evidence/source_selectors.json',index)

reg=next(p for p in docs if p.name.startswith('18_'));t=reg.read_text(encoding='utf-8-sig')
definitions={m[1]:m[0] for m in re.finditer(r'^## (DOC-[A-Z0-9-]+) —.*?(?=^## |\Z)',t,re.M|re.S)}
todo=['DOC-GIT-01','DOC-PARALLEL-01','DOC-TASK-READ-SCOPE-01','DOC-LOCAL-REPORT-HANDOFF-01','DOC-WUA-LAUNCH-01'];rules={}
while todo:
    rid=todo.pop()
    if rid in rules:continue
    value=definitions.get(rid)
    if value is None: rules[rid]={'status':'SOURCE_UNAVAILABLE'};continue
    meta=value.split('```',2)[1] if '```' in value else ''
    deps=re.findall(r'DOC-[A-Z0-9-]+',meta)
    rules[rid]={'text':value,'requires':deps,'status':'EXTRACTED'}
    todo.extend(x for x in deps if x not in rules)
save('evidence/rule_scope.json',{'source':reg.relative_to(ROOT).as_posix(),'sha256':sha(reg.read_bytes()),'definitions':rules})
followup=(ROOT/'Документация/05_Реестр задач.md').read_text(encoding='utf-8-sig')
a=followup.index('## Очередь открытых продолжений');b=followup.find('\n## ',a+3)
(WORK/'evidence/followup_source.txt').write_text(followup[a:b],encoding='utf-8')
print(json.dumps({'baseline_files':len(records),'source_files_indexed':len(index),'rules_with_requires':len(rules),'unresolved_rules':[k for k,v in rules.items() if v['status']!='EXTRACTED']}))
