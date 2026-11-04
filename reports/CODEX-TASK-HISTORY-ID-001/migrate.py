"""One-time, lossless document migration authorized in the current user chat.
Preserve originals first; verify source versions before replacing any working page.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools import task_history as h
OUT=Path(__file__).resolve().parent
DOC=ROOT/'Документация'
PRES=OUT/'preservation'

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    if (OUT/'migration.json').exists():
        raise SystemExit('Migration already applied; do not rewrite concurrent/new data.')
    names=['08_Старт.md','000_Задачи для агента.md','18_Регламент сопровождения документации.md',
           '05_Реестр задач.md','34_TACTICAL_CONTEXT.md','07_Шаблоны задач, отчётов и решений.md',
           *h.CARDS.values(),'000_Задачи Codex.md','000_Задачи Claude.md',
           '000_Задачи Ultra Desktop.md','000_Задачи ChatGPT.md']
    originals={name:(DOC/name).read_bytes() for name in names}
    PRES.mkdir(parents=True,exist_ok=True)
    for name,data in originals.items():
        p=PRES/name
        if p.exists() and p.read_bytes()!=data:raise ValueError('Snapshot conflict: '+name)
        if not p.exists():
            with p.open('xb') as f:f.write(data)
        assert p.read_bytes()==data
    old={name:data.decode('utf-8-sig').replace('\r\n','\n') for name,data in originals.items()}
    # Explicitly reviewed bounds; validate the expected ID inside each selection.
    selections={
    'codex':[
      ('CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001',9520,9538,'2026-10-25','Проверка зависимостей sing и завершение исследования'),
      ('CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001',9539,9557,'2026-10-25','Контракт строгого допуска Desktop MCP'),
      ('ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001',9558,10073,'2026-10-26','Архитектурная проверка миграции Ultra Chat'),
      ('ASTRA-WUA-37-ROADMAP-REVISION-001',10074,10223,'2026-10-26','Переработка программы перехода Web Alarm Ultra'),
      ('ASTRA-DOC-CONTEXT-OPTIMIZATION-001',10224,10233,'2026-11-01','Оптимизация контекста документации и закрытие слота'),
      ('CODEX-WUA-DOC-WEB19-REPAIR-001',10234,10243,'2026-11-01','Согласование документации после проверки WEB19'),
      ('CODEX-WUA-LOCAL-LLM-DISCOVERY-001',10263,10332,'2026-11-02','Исследование локальных серверов Ollama и Colibri'),
      ('CODEX-WUA-CHAT-UI-INTEGRATION-001',39,45,'2026-11-04','Подключение регистрации Workspace к Ultra Chat'),
      ('CODEX-WUA-CHAT-UX-LIVE-FIX-001',32,38,'2026-11-04','Исправление создания и переименования чатов'),
      ('CODEX-WUA-CHAT-S3-TURN-RECOVERY-001',24,31,'2026-11-04','Проверка условий восстановления Turn и Run Store')],
    'claude':[
      ('CLAUDE-WUA-CHAT-S1-READONLY-UI-001',12039,12332,'2026-10-28','Первый экран Ultra Chat и безопасное чтение истории'),
      ('CLAUDE-WUA-EVM-MODEL-CARD-UI-001',12333,12338,'2026-10-28','Интерфейс карточек моделей EVM'),
      ('CLAUDE-WUA-EVM-COMPACT-LAYOUT-001',12393,12398,'2026-10-29','Компактное расположение карточек EVM'),
      ('CLAUDE-DOC-TASK-SLOT-ROTATION-001',12399,12403,'2026-10-29','Скриптовая сдача и ротация слота задачи'),
      ('CLAUDE-WUA-EVM-INTERACTION-DND-001',12404,12411,'2026-10-30','Раскрытие карточек, предварительный просмотр и перетаскивание'),
      ('CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001',12412,12419,'2026-10-31','Закреплённые независимые окна карточек моделей'),
      ('CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001',12420,12427,'2026-10-31','Общее хранилище Workspace и Chat'),
      ('CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001',12428,12434,'2026-10-31','Защита путей контекста от вложенных junction'),
      ('CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001',12435,12441,'2026-11-01','Безопасная замена файлов общего хранилища'),
      ('CLAUDE-WUA-CHAT-RUNSTORE-P9-001',12442,12448,'2026-11-03','Защита Run Store от конкурентных изменений')]
    }
    for agent,rows in selections.items():
        source=(PRES/h.CARDS[agent]).relative_to(ROOT).as_posix()
        for order,(task,a,b,date,title) in enumerate(rows,1):
            ref=h.source_ref(ROOT,source,a,b)
            text=h.source_text(ROOT,ref)
            if task not in text.splitlines()[0]:raise ValueError('Source boundaries changed: '+task)
            refs={'legacy':ref}
            for key,file in [('assignment','handoff_task.md'),('report','report.md')]:
                p=ROOT/'reports'/task/file
                if p.is_file():refs[key]=h.source_ref(ROOT,p.relative_to(ROOT).as_posix())
            value=h.register(ROOT,task,agent,title,date,refs,status='HISTORICAL — результат в источнике')
            value['review']='исторический verdict сохранён; заново не проверен'
            value['order']=order
            h.save_record(ROOT,value)
    # Preserve exact normative definitions; startup need not load their whole volume.
    text18=old['18_Регламент сопровождения документации.md']
    lines=text18.splitlines(keepends=True)
    heads=[i for i,s in enumerate(lines) if re.match(r'^#{1,2} ',s)]
    core={'DOC-BLOCK1-SLOT-01','DOC-CONTEXT-OPS-01','DOC-TASK-CLOSEOUT-OWNER-01',
          'DOC-HISTORY-ACCESS-01','DOC-PLAN-TASK-INDEX-01','DOC-READ-01'}
    rules=[]
    for pos,start in enumerate(heads):
        m=re.match(r'^## (DOC-[A-Z0-9-]+)',lines[start])
        if not m or m.group(1) in core:continue
        rid=m.group(1);end=heads[pos+1] if pos+1<len(heads) else len(lines)
        p=DOC/'Правила'/f'{rid}.md';p.parent.mkdir(exist_ok=True)
        body=''.join(lines[start:end])
        prefix=('> Читать только перед соответствующим действием. USER GO 04.11.2026: хранение истории, ID, '
                'порядок чтения и ротации определяет новый №18; старые формулировки об этих действиях ниже ему уступают. '
                'Остальные условия и ограничения сохранены дословно.\n\n')
        if p.exists():raise ValueError('Rule target already exists: '+rid)
        p.write_text(prefix+body,encoding='utf-8')
        rules.append(f'| `{rid}` | `Документация/Правила/{rid}.md` |')
    new18=(OUT/'new18.md').read_text(encoding='utf-8').replace('<!-- ADDITIONAL-RULES -->',
          '| Правило | Точный файл |\n| --- | --- |\n'+'\n'.join(rules))
    changes={'18_Регламент сопровождения документации.md':new18}
    for agent,name in h.CARDS.items():
        changes[name]=(f'# История задач {h.AGENTS[agent]} — последние 10 ID\n\n'
          'USER GO 04.11.2026. Это короткий индекс, а не место для полных поручений и отчётов. '
          'Новый HISTORY ID выдаёт скрипт при сохранении; TASK ID сохраняется. '
          'Координатор после независимой проверки обновляет существующую запись и запускает `task_history.py render --apply`.\n\n'
          'Полные источники — в `reports/<TASK-ID>/`; адреса и SHA — в `task_record.json`. '
          'По умолчанию читать одну запись: `python -B -X utf8 tools/task_history.py read --id H-'+agent.upper()+'-000001`. '
          'Список: `python -B -X utf8 tools/task_history.py list --agent '+agent+' --last 10`. '
          'Команды чтения имеют общий лимит вывода; подробности и порядок веб-планировщика — №18.\n\n'
          f'{h.BEGIN}\n{h.END}\n\n'
          'Старый полный текст сохранён побайтово: `reports/CODEX-TASK-HISTORY-ID-001/preservation/'+name+'`. '
          'Снимок не читать целиком на старте. Старые статусы относятся к своим датам; перенос не является новым PASS. '
          'Старше десяти — вне рабочего окна, но не удалено из архива.\n\n'
          '[[000_Задачи '+h.AGENTS[agent]+']]\n')
    # Keep FOLLOWUP and risk bodies byte-for-byte after newline normalization.
    old05=old['05_Реестр задач.md']
    def section(text,heading):
        start=text.index(heading)
        end=re.search(r'^## ',text[start+len(heading):],re.M)
        return text[start:] if not end else text[start:start+len(heading)+end.start()]
    followup=section(old05,'## Очередь открытых продолжений (FOLLOWUP)')
    risks=section(old05,'## Оперативные риск-карточки')
    changes['05_Реестр задач.md']=('# Реестр задач: ID и открытые вопросы\n\n'
        'USER GO 04.11.2026. Сначала читать все актуальные FOLLOWUP ниже; исторические подробности — только по ID. '
        'HISTORY ID выдаёт скрипт, TASK ID остаётся идентификатором поручения. Полные источники — в папке задачи. '
        'Координатор добавляет независимый verdict в существующую запись; индексы обновляет `task_history.py render --apply`. '
        'Вопросы OPEN/UNASSIGNED не удаляются при выходе из последних десяти задач.\n\n'+followup+risks+
        '\n## Последние десять задач каждого исполнителя\n\n'+h.BEGIN+'\n'+h.END+'\n\n'
        '## Прежние записи\n\nСтарый реестр со всеми REG/TASK/risk-адресами сохранён без потерь: '
        '`reports/CODEX-TASK-HISTORY-ID-001/preservation/05_Реестр задач.md`. '
        'Для старого REG-ID обращаться к точному фрагменту снимка, не загружать весь архив. '
        'Новые события используют HISTORY ID + TASK ID; порядки — №18.\n')
    old08=old['08_Старт.md']
    tail08=old08[old08.index('## Сохранённые адреса прежней редакции'):]
    changes['08_Старт.md']=(OUT/'new08.md').read_text(encoding='utf-8')+'\n'+tail08
    old000=old['000_Задачи для агента.md']
    tail000=old000[old000.index('## Сохранённые адреса прежней редакции'):]
    changes['000_Задачи для агента.md']=(OUT/'new000.md').read_text(encoding='utf-8')+'\n'+tail000
    note=('\n## USER GO 04.11.2026 — история по ID и автоматическая сдача\n\n'
       'Веб-планировщик ведёт документацию по общему №000 и новой редакции №18. '
       '`finish` сохраняет дословную постановку, создаёт/переиспользует HISTORY ID и `reports/<TASK-ID>/task_record.json`, '
       'проверяет сохранность, затем освобождает БЛОК 1. Новая строка БЛОКА 1.1 и протокол содержат ID/адрес. '
       'Запускает исполнитель после итогового пакета либо пользователь через программу; веб без Python поручает запуск, не имитирует его. '
       'Авторская сдача не означает independent PASS. Проверяющий читает запись по ID, добавляет свой verdict, '
       'обновляет короткие №001/05, событие №06 и текущие OPEN/NEXT здесь. №001 показывает последние десять названий, полные источники сохранены отдельно. '
       'Все FOLLOWUP остаются до доказанного закрытия; старые архивы не являются стартовым контекстом. '
       'Пакет внедрения: `reports/CODEX-TASK-HISTORY-ID-001/`; локальная проверка не доказывает публикацию/независимую приёмку.\n')
    t=old['34_TACTICAL_CONTEXT.md'];first=t.index('\n')
    changes['34_TACTICAL_CONTEXT.md']=t[:first+1]+note+t[first+1:]
    template=('\n## Новый формат истории — USER GO 04.11.2026\n\n'
      'Полные постановки и отчёты не помещать в №001/05. Строка индекса: '
      '`дата | HISTORY ID / TASK ID | понятное название | авторский статус; independent verdict/scope | reports/<TASK-ID>/task_record.json`. '
      'HISTORY ID выдаёт `finish` или `task_history.py register`, повтор сохраняет номер. '
      'Веб-проверяющий берёт номер из 1.1/протокола, открывает одну запись, проверяет sources/SHA и добавляет review. '
      'Исходные задания, AMENDMENT, report и evidence сохраняются отдельно; шаблоны полных записей ниже применяются к папке задачи/профильному реестру, не к №001. '
      'Подробный порядок, команды, ошибки и роли — новая редакция №18.\n')
    t=old['07_Шаблоны задач, отчётов и решений.md'];first=t.index('\n')
    changes['07_Шаблоны задач, отчётов и решений.md']=t[:first+1]+template+t[first+1:]
    for name in ['000_Задачи Codex.md','000_Задачи Claude.md','000_Задачи Ultra Desktop.md','000_Задачи ChatGPT.md']:
        t=old[name];first=t.index('\n')
        note=('\n**USER GO 04.11.2026 / история по ID:** порядок общего №000 и нового №18 имеет приоритет над старыми указаниями о полном №001. '
          'После итогового пакета исполнитель или пользователь запускает штатный `finish`: сохранение источников и HISTORY ID → проверка → перенос БЛОК 1 в 1.1. '
          'Номер и адрес записи видны в 1.1/протоколе; повтор не создаёт новый номер. Веб-координатор проверяет запись по этому ID и ведёт короткие индексы №001/05. '
          'Полные постановки в №001 больше не вставлять; последние десять строк не заменяют очередь всех OPEN. '
          'Для старой 1.1 без H-номера использовать точный TASK ID и протокол, не переписывать постановку.\n')
        # Keep active slots, original EOL and all other bytes intact.
        nl=b'\r\n' if b'\r\n' in originals[name] else b'\n'
        raw=originals[name];at=raw.index(b'\n')+1
        changes[name]=raw[:at]+note.replace('\n',nl.decode()).encode('utf-8')+raw[at:]
    # Only commit prepared replacements if no concurrent source changed.
    for name,data in originals.items():
        if (DOC/name).read_bytes()!=data:raise ValueError('Concurrent document changed: '+name)
    for name,text in changes.items():
        if (DOC/name).read_bytes()!=originals[name]:raise ValueError('Concurrent edit: '+name)
        h.atomic(DOC/name,text if isinstance(text,bytes) else text.encode('utf-8'))
    h.render_indexes(ROOT)
    assert section((DOC/'05_Реестр задач.md').read_text(encoding='utf-8'),'## Очередь открытых продолжений (FOLLOWUP)')==followup
    proof={'status':'LOCAL MIGRATION APPLIED / INDEPENDENT REVIEW PENDING','sources':{},'records':sum(map(len,selections.values()))}
    for name,data in originals.items():
        assert (PRES/name).read_bytes()==data
        proof['sources'][name]={'before_bytes':len(data),'before_sha256':sha(data),
          'after_bytes':(DOC/name).stat().st_size,'after_sha256':sha((DOC/name).read_bytes()),
          'snapshot':(PRES/name).relative_to(ROOT).as_posix()}
    (OUT/'migration.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'preserved':len(originals),'records':proof['records'],'status':proof['status']},ensure_ascii=False))

if __name__=='__main__':main()
