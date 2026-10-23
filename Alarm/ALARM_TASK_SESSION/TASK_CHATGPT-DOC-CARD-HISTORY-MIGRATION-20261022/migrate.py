from pathlib import Path
from collections import OrderedDict
import re, hashlib, json
ROOT=Path(r'M:\GitHub\ag_llm')
DOC=ROOT/'Документация'
SESS=ROOT/'Alarm'/'ALARM_TASK_SESSION'/'TASK_CHATGPT-DOC-CARD-HISTORY-MIGRATION-20261022'
PRE=SESS/'preview'
AR='reports/AGENT-CARD-HISTORY-MIGRATION-20261022'
C='000_Задачи Codex.md'
L='000_Задачи Claude.md'
HC='001_История выполненных задач Codex.md'
HL='001_История выполненных задач Claude.md'
Q=chr(96)
def orig(n):return (SESS/'originals'/n).read_text(encoding='utf-8-sig')
def short(s,maxlen=380):
    s=re.sub(r'\s+',' ',s.strip())
    return s if len(s)<=maxlen else s[:maxlen].rsplit(' ',1)[0]+'…'
def taskids(txt,kind):
    ret=OrderedDict()
    for i,line in enumerate(txt.splitlines(),1):
        if not line.startswith('#'):continue
        m=re.search(r'\b'+kind+r'-(?:[A-Z0-9]+-)+[A-Z0-9]+\b',line)
        if m and m.group() not in ret:
            title=line[m.end():].strip(' —:-/')
            title=re.sub(r'\s+—\s+(?:результат|factual.*)$','',title,flags=re.I)
            ret[m.group()]=(i,short(title,155))
    return ret
def result(txt,tid,kind):
    if kind=='CLAUDE':
        m=re.search(r'^# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ',txt,re.M)
        src=txt[m.end():] if m else txt
        pattern=r'(?m)^### [^\n]*'+re.escape(tid)+r'[^\n]*результат[^\n]*$'
    else:
        src=txt
        pattern=r'(?m)^## [^\n]*'+re.escape(tid)+r'[^\n]*$'
    m=None
    if kind=='CODEX':
        for block in re.finditer(r'(?m)^# БЛОК 3[^\n]*$',txt):
            part=txt[block.end():block.end()+550]
            match=re.search(r'(?m)^## [^\n]*'+re.escape(tid)+r'[^\n]*$',part)
            if match:
                src=txt[block.end():]
                m=match
                break
    if not m:m=re.search(pattern,src,re.I)
    if not m and kind=='CLAUDE':m=re.search(r'(?m)^#{1,3} [^\n]*'+re.escape(tid)+r'[^\n]*$',src)
    if not m:return '','',''
    piece=src[m.end():m.end()+3100]
    if kind=='CLAUDE':piece=re.split(r'\n(?:---\s*\n)?### (?:CLAUDE-|Предыдущий результат)',piece)[0]
    else:piece=re.split(r'\n(?:---\s*\n)?(?:# БЛОК [234]|## (?:20\d\d-|CODEX-|ARCHIVED)|## Предыдущая история)',piece)[0]
    lines=piece.splitlines()
    status=''
    fact=''
    for ln in lines[:24]:
        if re.search(r'\*\*Статус:|RESULT READY|DONE / VERIFIED',ln,re.I):
            status=short(ln.lstrip('- ').strip(),245);break
    for ln in lines[:70]:
        if re.match(r'^\s*-\s+\*\*(?:Сделано|Реализовано|Главный вывод|Причина|Исправлено|Реальный пакет|Файлы|Проверки)\b',ln,re.I):
            fact=short(ln.lstrip('- ').strip(),380);break
        if kind=='CODEX' and 90<len(ln)<550 and not ln.startswith(('-', '#','*','|')):
            fact=short(ln,380);break
    f=re.search(r'(?:reports/|Alarm/ALARM_TASK_SESSION/)[A-Za-z0-9_./-]+',piece)
    return status,fact,(f.group().rstrip('/.,') if f else '')
def b4(txt,kind):
    x=txt.index('# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER')
    y=txt.find('\n## Предыдущая история',x) if kind=='CODEX' else len(txt)
    return txt[x:y].rstrip()
def make_card(txt,kind,idx):
    first=txt.index('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА')
    pre=txt[:first]
    if kind=='CLAUDE':
        patterns=[
            (r'- После фактического завершения исполнения Claude \*\*сам\*\* выполняет безопасную ротацию без отдельной команды:[^\n]+','- После TASK Claude сохраняет полный БЛОК 1/AMENDMENT и полный factual report в разрешённом task-report внутри ag_llm, затем безопасно ротирует БЛОКИ 1–3 в кратком формате (до пяти TASK). БЛОК 4 READ-ONLY.'),
            (r'- БЛОК 2 хранит полную последнюю выполненную постановку;[^\n]+','- БЛОК 2 — до пяти кратких последних TASK, БЛОК 3 — краткий factual результат последней, полные материалы отдельно.'),
            (r'- До перезаписи БЛОКОВ 2–3 предыдущая независимо подтверждённая TASK должна уже иметь постоянную append-only историю\.','- До вытеснения шестой TASK координатор сверяет отдельный полный архив и 001 с исходным статусом, без самовольного повышения до VERIFIED.'),
            (r'- Claude сам ведёт оперативную ротацию своей персональной карточки [^\n]+','- Claude ведёт только свои БЛОКИ 1–3; 001, 06 и БЛОК 4 ведёт независимый verifier.')
        ]
    else:
        patterns=[
            (r'- После каждого завершённого исполнения TASK, включая PARTIAL/BLOCKED с готовым полным итоговым отчётом, обязательна безопасная ротация собственной карточки:[^\n]+','- После TASK Codex сохраняет полный БЛОК 1/AMENDMENT и factual report внутри ag_llm, БЛОК 2 пополняет краткой строкой (до пяти TASK), БЛОК 3 — краткий factual результат; только после проверки архивов освобождает БЛОК 1. БЛОК 4 READ-ONLY. 001 и 06 ведёт independent verifier; при сбое ротации CARD ROTATION BLOCKED.')
        ]
    for p,v in patterns:
        pre,k=re.subn(p,v,pre,count=1)
        if k!=1:raise ValueError('No rule '+kind+' '+p)
    pre=pre.replace(Q+'DOC-VERIFIER-BLOCK4-01@1'+Q,Q+'DOC-VERIFIER-BLOCK4-01@2'+Q)
    if kind=='CODEX':
        pre=pre.replace('Codex и Claude не используют общие TASK ID','История: [[001_История выполненных задач Codex]]. Codex и Claude не используют общие TASK ID')
    rule=('**DOC-AGENT-CARD-HISTORY-01@1:** БЛОК 1 — целая актуальная постановка; БЛОК 2 — не более пяти кратких последних TASK; БЛОК 3 — краткий factual результат последней; БЛОК 4 — только независимая приёмка. Полная история — [[001_История выполненных задач '+kind.capitalize()+']]. Оригиналы TASK и отчётов — отдельно. Исполнитель не объявляет себе DONE/VERIFIED.\n\n')
    pre=pre.replace('## Правила\n','## Правила\n\n'+rule,1)
    m=re.search(r'# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\s*\n(.+?)(?=\n---\s*\n)',txt[first:],re.S)
    if not m or 'ОЖИДАНИЕ' not in m.group(1):raise ValueError('BLOCK1 not WAITING '+kind)
    s=pre.rstrip()+'\n\n---\n\n# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\n'+m.group(1).strip()+'\n\n---\n\n# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КРАТКО)\n\n'
    s+='Подробно — [[001_История выполненных задач '+kind.capitalize()+']]; оригинал всех прежних блоков — '+Q+AR+'/full_000_Задачи '+kind.capitalize()+'.md'+Q+'.\n\n'
    for tid,(line,title) in list(idx.items())[:5]:
        status,fact,path=result(txt,tid,kind)
        s+='## '+tid+' — '+(title or 'см. историю')+'\n'
        if fact:s+='- **Факт из отчёта:** '+fact+'\n'
        s+='- **Статус источника:** '+(status or 'сверить с отчётом / 06')+'\n'
        if path:s+='- **Источник:** '+Q+path+Q+'\n'
        s+='\n'
    tid=next(iter(idx))
    status,fact,path=result(txt,tid,kind)
    s+='---\n\n# БЛОК 3 — КРАТКИЙ FACTUAL RESULT / HANDOFF\n\n**TASK:** '+tid+'\n\n'
    if fact:s+='**Результат:** '+fact+'\n\n'
    s+='**Статус исходника:** '+(status or 'нужна сверка')+'\n\n'
    if path:s+='**Отчёт:** '+Q+path+Q+'\n\n'
    s+='**Полный архив:** '+Q+AR+'/full_000_Задачи '+kind.capitalize()+'.md'+Q+'. Независимый verdict — БЛОК 4 и 06.\n\n---\n\n'+b4(txt,kind)+'\n'
    return s
def entries(txt,kind,idx,exclude=set()):
    resultlines=[]
    for tid,(line,title) in idx.items():
        if tid in exclude:continue
        status,fact,path=result(txt,tid,kind)
        v='### '+tid+' — '+(title or 'историческая задача')+'\n'
        v+='- **Суть / факт:** '+(fact or title or 'см. полный архив')+'\n'
        v+='- **Статус источника:** '+(status or 'по этой выписке не установлен — см. 06')+'\n'
        if path:v+='- **Отчёт:** '+Q+path+Q+' (сверять фактическое наличие).\n'
        v+='- **Полные постановки, AMENDMENT и результаты:** '+Q+AR+'/full_000_Задачи '+kind.capitalize()+'.md'+Q+', строка '+str(line)+'.\n'
        v+='- **Независимая проверка:** этот перенос не является PASS; см. журнал 06 и verifier.\n\n'
        resultlines.append(v)
    return ''.join(resultlines)
def build():
    codex=orig(C);claude=orig(L);old_hist=orig(HL)
    ci=taskids(codex,'CODEX');cl=taskids(claude,'CLAUDE')
    oldids=set(re.findall(r'(?m)^## 2026-\d\d-\d\d — (CLAUDE-[A-Z0-9-]+)',old_hist))
    assert len(ci)>=20 and len(cl)>=25 and len(oldids)>=10
    result_docs={C:make_card(codex,'CODEX',ci),L:make_card(claude,'CLAUDE',cl)}
    result_docs[HC]=('# История выполненных задач Codex\n\n'
      'Связанный личный handoff: [[000_Задачи Codex]]. Этот файл — расширенный сжатый указатель задач агента 007; это НЕ автоматический список VERIFIED. Полные оригиналы — '+Q+AR+'/full_000_Задачи Codex.md'+Q+' (SHA-256 в архивном manifest). Авторитетные independent verdict — в 06.\n\n'
      '## Независимые ограниченные выводы из исходного БЛОКА 4\n\n'
      '- **CODEX-WUA-0-WINDOWS-LAB-GATE-001:** 2026-10-21 PARTIAL / bounded offline accepted: 215/215 inventory, 13/13 SHA; I01–I12 BLOCKED, native and ChatGPT E2E NOT VERIFIED.\n'
      '- **CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001:** bounded source review 87 путей, 10/10 SHA; реальная установка BLOCKED.\n'
      '- **CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001:** результат исполнителя RESULT READY; independent PASS не предоставлен. Hosted tunnel не активирован.\n\n'
      '## Указатель всех исторических TASK из карточки\n\n'
      'Ниже переданы факты из исходной карточки, без выполнения новой проверки. Статусы проверять в 06 и связанных отчётах.\n\n'+entries(codex,'CODEX',ci))
    result_docs[HL]=old_hist.rstrip()+'\n\n---\n\n## Дополнительные исторические TASK Claude — без независимо утверждённого PASS в этой части истории\n\n'
    result_docs[HL]+=('Это операционная история, а не повышение статусов. Старый подтверждённый независимый раздел выше сохранён без изменения. Полные тексты — '+Q+AR+'/full_000_Задачи Claude.md'+Q+'; вердикты — 06.\n\n'+entries(claude,'CLAUDE',cl,oldids))
    for n,kind in [(C,'CODEX'),(L,'CLAUDE')]:
        assert result_docs[n].count('# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА')==1
        assert result_docs[n].count('# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER')==1
        assert len(result_docs[n].encode('utf-8'))<22000
        assert b4(orig(n),kind) in result_docs[n]
    assert old_hist.rstrip() in result_docs[HL]
    assert all(t in result_docs[HC] for t in ci)
    assert all(t in result_docs[HL] for t in cl)
    return result_docs, {'Codex':len(ci),'Claude':len(cl),'Already in Claude 001':len(oldids)}
if __name__=='__main__':
    docs,counts=build()
    dest=PRE/'Документация';dest.mkdir(parents=True,exist_ok=True)
    for n,t in docs.items():
        data=t.encode('utf-8')
        (dest/n).write_bytes(data)
        print('PREVIEW',n.encode('ascii','backslashreplace').decode(),len(data),hashlib.sha256(data).hexdigest()[:10])
    print('COUNTS',json.dumps(counts))
