from pathlib import Path
import re, json, hashlib
root=Path(r'M:\GitHub\ag_llm')
doc=root/'Документация'
task=root/'Alarm'/'ALARM_TASK_SESSION'/'TASK_CHATGPT-DOC-CARD-HISTORY-MIGRATION-20261022'
names=['000_Задачи Codex.md','000_Задачи Claude.md','001_История выполненных задач Claude.md']
result={}
for name in names:
    text=(task/'originals'/name).read_text(encoding='utf-8-sig')
    lines=text.splitlines()
    marker=[]
    headings=[]
    refs={}
    for i,line in enumerate(lines,1):
        if re.match(r'^# БЛОК [1-4]\b',line):
            marker.append({'line':i,'heading':line[:150]})
        if re.match(r'^#{1,4} ',line) and (('CODEX-' in line) or ('CLAUDE-' in line) or ('ARCHIVED' in line) or ('Архив' in line)):
            headings.append({'line':i,'heading':line[:240]})
        if line.startswith('#'):
            for taskid in re.findall(r'\b(?:CODEX|CLAUDE)-(?:[A-Z0-9]+-)+[A-Z0-9]+\b',line):
                refs.setdefault(taskid,[]).append(i)
    result[name]={'size':len(text.encode('utf-8')),'lines':len(lines),'blocks':marker,'headings':headings,'unique_heading_ids':len(refs),'heading_ids':refs}
(task/'card_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for n,v in result.items():
    print(n.encode('ascii','backslashreplace').decode(), 'lines',v['lines'],'markers',len(v['blocks']),'headings',len(v['headings']),'idcount',v['unique_heading_ids'])
    print('BLOCK POS',[(x['line'],x['heading'].encode('ascii','backslashreplace').decode()) for x in v['blocks'][:30]])
    print('HEADINGS',[(x['line'],x['heading'][:95].encode('ascii','backslashreplace').decode()) for x in v['headings'][:30]])
    print('TAIL',[(x['line'],x['heading'][:100].encode('ascii','backslashreplace').decode()) for x in v['headings'][-12:]])