from pathlib import Path
import json,re
from doc_migration import WORK, DOC, headings, h

def old(prefix):
    p=next(p for p in (WORK/'preservation').glob('*.source.txt') if p.name.startswith(prefix))
    return p.name.removesuffix('.source.txt'), p.read_text(encoding='utf-8')

def content(name): return (WORK/'drafts'/name).read_text(encoding='utf-8').strip()+'\n'
def write(name,text):
    p=WORK/'candidate'/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(text,bytes): p.write_bytes(text)
    else: p.write_text(text,encoding='utf-8')

def legacy(name,text,new):
    """Retain old selectors/anchors and same-source Wiki syntax, without repeating old narratives."""
    index=json.loads((WORK/'evidence/preservation_index.json').read_text(encoding='utf-8'))
    entry=next(x for x in index if Path(x['source']).name==name)
    result='\n## Сохранённые адреса прежней редакции\n\n'
    result+='Эта область сохраняет прежние заголовки и графовые конструкции для адресной совместимости. '+\
            'Старые CURRENT/NEXT здесь являются историческими названиями, а не действующими инструкциями. '+\
            'На обычном старте область пропускается. Полный исходный текст: `'+entry['snapshot']+'`. '+\
            'Границы записей Snnn и SHA-256: `reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/implementation-20261027/evidence/preservation_index.json`. '+\
            'Исторический текст читать только по нужному Snnn/TASK, не целиком.\n\n'
    lines=text.splitlines(keepends=True)
    for part in entry['parts']:
        frag=''.join(lines[part['first_line']-1:part['last_line']])
        title=part['heading']
        if title.startswith('#'):
            # All old headings remain in original order and with original level.
            result+=title+'\n\n'
            result+='История `'+part['record_id']+'`; текущий вход — начало файла.\n\n'
        for token in re.findall(r'!?\[\[[^\]\n]+\]\]',frag):
            # Reviewed source files have active Wiki tokens only in this rewritten subset.
            result+=token+'\n\n'
    return new.rstrip()+'\n'+result

def replace_section(text, header, body):
    start=text.index(header)
    after=start+len(header)
    nxt=re.search(r'(?m)^#{1,2} ',text[after:])
    end=after+nxt.start() if nxt else len(text)
    return text[:start]+header+'\n\n'+body.strip()+'\n\n'+text[end:]

def build():
    # Short operative documents retain selector/graph compatibility; exact former bytes live in snapshots.
    for prefix, draft in [('08_','start.txt'),('34_','tactical.txt'),('000_Задачи для','coordinator.txt'),('07_','templates.txt')]:
        name,text=old(prefix)
        write(name,legacy(name,text,content(draft)))

    # Personal task/verification blocks are immutable in this framework-only change.
    for prefix,role in [('000_Задачи ChatGPT','ChatGPT'),('000_Задачи Claude','Claude 008'),('000_Задачи Codex','Codex 007'),('000_Задачи Ultra','Ultra Desktop')]:
        name,text=old(prefix);boundary=text.index('# БЛОК 1') if '# БЛОК 1' in text else len(text)
        pre,suffix=text[:boundary],text[boundary:]
        if role=='ChatGPT':
            new=content('chatgpt_rules.txt')
        else:
            new=content('executor_rules.txt').replace('{ROLE}',role)
            if role=='Ultra Desktop':
                a=pre.index('## Специальный рабочий протокол Ultra Desktop')
                new+='\n'+pre[a:]
        # Preserve prior prefix headings as addresses, but never reproduce their outdated instructions.
        for header in headings(pre):
            if header not in headings(new): new+='\n'+header+'\n\nДействующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.\n'
        # Original prefix Wiki links remain on the same source, same raw token and multiplicity.
        for token in re.findall(r'!?\[\[[^\]\n]+\]\]',pre): new+='\n'+token+'\n'
        raw=(WORK/'preservation'/(name+'.source.txt')).read_bytes()
        raw_boundary=raw.index('# БЛОК 1'.encode('utf-8')) if '# БЛОК 1' in text else len(raw)
        write(name,(new.rstrip()+'\n\n').encode('utf-8')+raw[raw_boundary:])

    # Normative owner: explicit operational protocol and surgical removal of obsolete self-rotation.
    name,text=old('18_')
    # Give the already binding handoff override an exact normative selector without copying it.
    override=re.search(r'(?m)^\*\*ОБЯЗАТЕЛЬНОЕ ПРАВИЛО / USER GO 2026-10-25 / DOC-TASK-HANDOFF-USER-01@1.*$',text)
    assert override
    formal=('## DOC-TASK-HANDOFF-USER-01 — Пользователь назначает TASK, координатор закрывает\n\n'
            '```rule-meta\ncontract: 1\nstatus: ACTIVE\nrequires: [DOC-TASK-CLOSEOUT-OWNER-01@1, DOC-GIT-01@1]\n```\n\n')
    text=text[:override.start()]+formal+override[0]+text[override.end():]
    text=text.replace('### DOC-TEST-START-01@1 —', '## Действующий маршрут чтения и тестов\n\n### DOC-TEST-START-01@1 —',1)
    needle='## Нормативный индекс — правила и состояния'
    text=text.replace(needle,content('operations_rule.txt')+'\n'+needle,1)
    # Add index row immediately before launcher rule definition, outside previous table if unknown layout.
    index_head='## Нормативный индекс — правила и состояния'
    pos=text.index(index_head)+len(index_head)
    text=text[:pos]+'\n\nНовый действующий контракт: `DOC-CONTEXT-OPS-01@1` → раздел выше. Он задаёт рабочую процедуру, не расширяя Git/production права.\n'+text[pos:]
    text=text.replace('| `DOC-WUA-LAUNCH-01`', '| `DOC-CONTEXT-OPS-01` | Оперативная память, навигация, риски и закрытие | 1 | ACTIVE |\n| `DOC-TASK-HANDOFF-USER-01` | Назначение пользователем, закрытие координатором | 1 | ACTIVE |\n| `DOC-WUA-LAUNCH-01`',1)
    text=re.sub(r'Для Claude текущий персональный контур:.*?(?=\n\nПерсональные карточки ChatGPT)',
                'Для Claude используется его персональная карточка и №001. БЛОКИ 2–3 — до пяти кратких задач/итогов; полная постановка и AMENDMENT сохраняются в №001 либо проверенном постоянном snapshot. Исполнитель не ротирует карточку. Публикация пользователем → независимая проверка → архив/readback → документационная дельта координатора → БЛОК 1 освобождается последним. Канон: DOC-TASK-CLOSEOUT-OWNER-01 и DOC-CONTEXT-OPS-01. При REVISE/FAIL или недоказанной сохранности БЛОК 1 остаётся.',text,flags=re.S)
    text=replace_section(text,'## Живой Tactical Context 34 — обязательный delta-handoff',
       '№34 содержит текущую рабочую картину, обязательные ориентиры, действующие решения, OPEN/gates и короткое окно последних результатов. Обновлять после проверенного события заменой соответствующих полей. Каноническая процедура и лимиты — DOC-CONTEXT-OPS-01; каркас — №07 → Форма оперативной памяти №34. Историю сохранять прежде вытеснения; не добавлять очередную большую главу handoff.\n\n### Перспективная сверка Blueprint LLM — только ChatGPT (уточнение пользователя 2026-10-18)\n\nПериодическая оценка Blueprint LLM остаётся обязанностью ChatGPT при релевантном архитектурном планировании. Предложения из тактического журнала идей не становятся разрешённой реализацией; основной Blueprint изменяется после решения пользователя. Это не обязательная загрузка всей библиотеки на каждом старте.')
    # Rule is current authority; stale automatic full-file reading remains disallowed.
    text=replace_section(text,'## Cold start и профиль активной ветки',content('profile_route.txt'))
    text=text.replace('разрешённый узкий порядок собственной ротации', 'порядок передачи технического пакета и координаторского закрытия')
    write(name,text)

    name,text=old('05_');write(name,(content('registry_intro.txt')+'\n'+registry_index(text)+'\n').encode('utf-8')+(WORK/'preservation'/(name+'.source.txt')).read_bytes())
    name,text=old('06_');write(name,(content('journal_intro.txt')+'\n').encode('utf-8')+(WORK/'preservation'/(name+'.source.txt')).read_bytes())

    name,text=old('40_')
    # Keep existing content/headers and sole Wiki relation; correct misleading ownership/status wording only.
    text=text.replace('итоговая история — в №05/06/34.', 'итоговый реестр — №05, история — №06/профильные журналы/№001; №34 хранит текущую картину.')
    text=text.replace('Старые детали остаются в карточках, №05/06/34.', 'Старые детали остаются у исторических владельцев №06/профильных журналов/№001 и в отчётах; №34 обновляется без накопления истории.')
    text=text.replace('**WAITING / новой TASK в БЛОКЕ 1 нет** (по опубликованной карточке).', '**WAITING / новая техническая TASK Core не подтверждена этим снимком**. Это не означает, что Codex свободен: текущее документационное поручение пользователя в чате выполняется отдельно; его рабочая картина — №34.')
    text+='\n## Обслуживание этой сводки\n\nКанон — №18 → DOC-CONTEXT-OPS-01; форма — №07 → Форма координации №40. Одна текущая строка на направление: чат/исполнитель, TASK или отсутствие назначения, execution/review, write-scope, пересечения, NEXT, дата/источник. При смене состояния заменить строку, не дописывать историю. Технический scope и занятость агента — разные поля. Проверки, риски и требования не выводить из слова WAITING; указать exact record-id №05 и risk-id, если они назначены.\n'
    write(name,text)

    name,text=old('36_Единая')
    text=text.replace('08 → 000 → 34 → 18 → 36 → 36.1 → 36.2/36.3','08 → 000 → 40 → 34 → 18 → 01/профиль → 36 → 36.1 → 36.2/36.3')
    text=text.replace('ChatGPT — координатор/verifier/редактор общей документации, НЕ автор production/test/runner/CI code;', 'ChatGPT — координатор/verifier/редактор документации; безопасные временные тесты разрешены, инженерные изменения — только по прямому USER GO согласно DOC-ENGINEERING-ROLES-01@2;')
    text=text.replace('исходники и тесты не редактирую, их изменение поручаю Claude/Codex по действующему регламенту;', 'постоянные исходники/тесты/CI меняю только по прямому USER GO, собственную правку не принимаю независимо;')
    text=text.replace('(`DOC-ENGINEERING-ROLES-01@1`, 18)', '(`DOC-ENGINEERING-ROLES-01@2`, 18)')
    text=text.replace('**ChatGPT не меняет код или тесты**', '**ChatGPT меняет постоянный код/тесты/CI только по прямому USER GO; своё исправление не принимает независимо**')
    text=text.replace('DOC-ENGINEERING-ROLES-01@1', 'DOC-ENGINEERING-ROLES-01@2')
    text=text.replace('Если необходим новый диагностический код или тест, поручить его Claude/Codex по отдельной TASK, дождаться результатов и публикации; ChatGPT не создаёт тестовый код или фиктивные коммиты ради CI.', 'Безопасный временный диагностический тест ChatGPT может подготовить самостоятельно по DOC-ENGINEERING-ROLES-01@2. Постоянный код/тесты/CI — только по прямому USER GO; при поручении инженеру дождаться пакета и публикации. Не создавать фиктивные изменения ради CI.')
    text+='\n## Адресный вход и документационная приёмка\n\nМаршрут и роли — №08; процедура координатора — №18 → DOC-CONTEXT-OPS-01. Читать точные определения с requires, не все исторические главы. INDEPENDENT_PLAN сохраняет BLIND-START. Для изменения только Markdown — проверка прав, смысловой сохранности, адресов и графа; full suite/runtime/CI не нужны без влияния на код. Авторская проверка документации не заменяет независимый verdict.\n'
    write(name,text)

def registry_index(text):
    lines=text.splitlines(); rows=[]; heading='Преамбула'; cols=[]; n=0
    for i,line in enumerate(lines):
        if re.match(r'^#{1,6} ',line): heading=re.sub(r'^#+ ','',line)
        if not line.startswith('|'): continue
        cells=[x.strip() for x in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r'[:\s-]*',x) for x in cells):
            cols=[x.strip() for x in lines[i-1].strip().strip('|').split('|')];continue
        if i+1<len(lines) and re.match(r'^\|[ :\-]+\|',lines[i+1]): continue
        n+=1;first=cells[0].replace('`','').replace('|',' / ')
        key=f'REG-LEGACY-{n:03d}'
        task=re.findall(r'\b(?:CLAUDE|CODEX|ASTRA|CHATGPT|ULTRA)[A-Z0-9._-]+',line)
        # No inferred verifier/executor or abbreviated PASS claims in the navigation projection.
        identity=', '.join(dict.fromkeys(task)) if task else first
        rows.append({'record_id':key,'heading':heading,'original_line':i+1,'first_cell':cells[0],
                     'row_sha256_utf8':h(line.encode('utf-8')),'identity':identity})
    dump={'source':'Документация/05_Реестр задач.md','basis':'original pre-migration snapshot; row hashes independent of prepended line count',
          'records':rows,'note':'Navigation IDs identify existing rows, not newly assigned TASKs. Whole historical registry retained as suffix.'}
    (WORK/'evidence/registry_record_index.json').write_text(json.dumps(dump,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Compact topic index remains in Markdown; exhaustive IDs and byte-bound locators are on-demand JSON.
    return ('## Адресный индекс существующих записей\n\n'+
            f'Найдено {len(rows)} существующих строк записей, включая направления и составные задачи; это не число уникальных TASK. '+
            'Устойчивые ключи REG-LEGACY-001 и далее назначены строкам без изменения их содержимого. '+
            'Точный индекс: `reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/implementation-20261027/evidence/registry_record_index.json` → records → record_id/identity. '+
            'Для чтения: выбрать ключ/TASK → exact heading + first_cell → сверить row_sha256_utf8. original_line относится только к исходному snapshot и не является адресом текущей строки. '+
            'Индекс охватывает существующие строки; новые записи добавляются координатором с собственным record_id прямо в запись. Статус, executor, result_kind и review извлекаются из выбранной полной записи, не угадываются по префиксу или чату. При отсутствии поля — UNKNOWN/уточнить.\n\n'+
            'Ниже весь прежний реестр сохранён в исходном порядке. Датированные CURRENT и статусы в нём принадлежат своим датам/ревизиям; актуальность устанавливается по TASK + событию + независимому verdict.\n')

if __name__=='__main__': build()
