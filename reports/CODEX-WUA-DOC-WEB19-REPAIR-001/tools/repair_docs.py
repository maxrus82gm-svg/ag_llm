"""Bounded documentation repair. No Git, network, application execution or code edits."""
from pathlib import Path
from collections import Counter
import difflib
import hashlib
import json
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'reports/CODEX-WUA-DOC-WEB19-REPAIR-001'
TASK = 'CODEX-WUA-DOC-WEB19-REPAIR-001'
NAMES = ['03_Чаты, проекты и контекст.md', '05_Реестр задач.md', '06_Журнал выполнения и отчёты.md',
         '34_TACTICAL_CONTEXT.md', '37_Старт перехода - Web Alarm Ultra.md', '40_Оперативная координация направлений.md']
CARD = 'Документация/000_Задачи Codex.md'
OLDPACK = ROOT / 'reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/implementation-20261027'
RESTORED_EDGE = '[[000_Задачи для агента|Координаторский маршрутизатор]]'


def sha(b): return hashlib.sha256(b).hexdigest()
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def rel(p): return p.relative_to(ROOT).as_posix()
def text(p): return p.read_bytes().decode('utf-8-sig').replace('\r\n', '\n')
def source(name): return WORK / 'before' / (name + '.source.txt')
def replace_one(t, old, new):
    assert t.count(old) == 1, ('ambiguous replacement', old[:100], t.count(old))
    return t.replace(old, new, 1)
def line_replace(t, prefix, new):
    lines = [l for l in t.splitlines() if l.startswith(prefix)]
    assert len(lines) == 1, (prefix, len(lines))
    return replace_one(t, lines[0], new)
def block(t, heading):
    start = t.index(heading)
    end = t.find('\n## ', start + len(heading))
    return t[start:end if end != -1 else len(t)]


def scope_inventory():
    # Bounded inventory of project code, documentation, tools/config and used source packages.
    # The earlier broad scan was stopped before producing a baseline or modifying sources.
    skip = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache'}
    roots = [ROOT / s for s in ['Документация', 'web_alarm', 'integrations', 'tools', '.github', '.obsidian']]
    roots += [ROOT / 'reports' / s for s in ['CLAUDE-WUA-EVM-COMPACT-LAYOUT-001', 'CLAUDE-DOC-TASK-SLOT-ROTATION-001', 'CLAUDE-WUA-EVM-INTERACTION-DND-001', 'CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001', 'CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001', 'CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001', 'CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001', 'ASTRA-DOC-CONTEXT-OPTIMIZATION-001']]
    paths = [p for p in ROOT.iterdir() if p.is_file()]
    paths += list((ROOT / 'reports').glob('*.md'))
    for top in roots:
        for root, dirs, files in os.walk(top):
            dirs[:] = sorted(d for d in dirs if d not in skip and not (Path(root) / d).is_symlink())
            paths += [Path(root) / n for n in files]
    result = {}
    for p in sorted(set(paths)):
        if p.is_symlink() or p.suffix in {'.pyc', '.pyo'} or p.is_relative_to(WORK): continue
        raw = p.read_bytes()
        result[rel(p)] = {'bytes': len(raw), 'sha256': sha(raw)}
    return result


def baseline():
    assert not (WORK / 'evidence/baseline.json').exists(), 'Immutable baseline exists'
    files = scope_inventory()
    targets = []
    for name in NAMES:
        p = ROOT / 'Документация' / name
        raw = p.read_bytes()
        dest = source(name); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
        targets.append({'path': rel(p), 'snapshot': rel(dest), 'sha256': sha(raw), 'bytes': len(raw)})
    card = text(ROOT / CARD)
    m = re.search(r'^###### .*TASK-SLOT:BLOCK-1:BEGIN[^\n]*\n(.*?)^###### .*TASK-SLOT:BLOCK-1:END', card, re.M | re.S)
    assert m and TASK in m[1] and '553d3746143c97102cc94edaa02549e010e41e04' in m[1]
    (WORK / 'assignment_source.txt').write_bytes((ROOT / CARD).read_bytes())
    (WORK / 'task_scope.txt').write_text(m[1], encoding='utf-8', newline='\n')
    signals = {
        '482_registry': 'REG-WEB19-ASTRA-SLOT-20261101' in text(source(NAMES[1])),
        '482_journal': 'EVT-WEB19-ASTRA-SLOT-20261101' in text(source(NAMES[2])),
        '481_focused_windows': 'REG-WEB19-S2-INDEP-WINDOWS-20261101' in text(source(NAMES[1])),
        'claude_waiting': '**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**' in text(ROOT / 'Документация/000_Задачи Claude.md').split('TASK-SLOT:BLOCK-1:END')[0],
        'astra_permanent_task': (ROOT / 'reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/handoff_task.md').is_file(),
        'reported_defects_present': 'STATE## 20.2.' in text(source(NAMES[0])) and 'review## 2026-' in text(source(NAMES[2])),
    }
    assert all(signals.values()), ('SOURCE_STATE_UNCONFIRMED', signals)
    dump(WORK / 'evidence/baseline.json', {'task': TASK, 'date': '2026-11-01', 'declared_base': '№482 / 553d3746143c97102cc94edaa02549e010e41e04', 'source_state': 'USER-DECLARED BASE / LOCAL DOCUMENTARY MARKERS MATCH', 'limitation': 'No independent Git revision or dirty-state proof; disk hashes and card states only; unsaved editor changes unobserved.', 'signals': signals, 'targets': targets, 'files': files,
         'inventory_exclusions': ['.git (not opened)', 'unlisted directories: Alarm/live stores/logs/labs/dev archives/sandbox', 'unrelated historical report packages', 'venv/.venv', 'node_modules', '__pycache__/.pytest_cache', 'symlinks', 'own report package'], 'scan_note': 'Initial broad inventory process was stopped, exit 1, before producing a baseline or writing any target document. This bounded inventory is the actual comparison scope.'})
    old40 = next((OLDPACK / 'preservation').glob('40_*.source.txt'))
    expected = next(x for x in load(OLDPACK / 'manifest.json')['entries'] if x['path'] == rel(old40))
    assert sha(old40.read_bytes()) == expected['sha256'] and RESTORED_EDGE in text(old40)
    assert (ROOT / 'Документация/000_Задачи для агента.md').is_file()
    dump(WORK / 'evidence/graph_restoration_basis.json', {'source': expected, 'exact_edge': RESTORED_EDGE, 'current_before_count': text(source(NAMES[5])).count(RESTORED_EDGE), 'old_snapshot_count': text(old40).count(RESTORED_EDGE), 'target_exists': True, 'authority': 'Current B1 §4 / №40 conditional restoration; historical rule already states this single relation', 'expected_delta': '40 → 000_Задачи для агента, one restored occurrence; no other graph syntax delta; live graph export NOT RUN'})
    print(json.dumps({'baseline_files': len(files), 'snapshots': 6, 'source_signals': signals}))


def build():
    result = {name: text(source(name)) for name in NAMES}
    # 03: keep both historical additions intact, ordered under §20, restore the §21 boundary.
    t = result[NAMES[0]]
    start = t.index('# 21. MESSAGE CONTEXT STATE## 20.2.')
    mid = t.index('## 20.1. Правило записи Context State/Variants', start)
    end = t.index('`state.json` определяет', mid)
    harden = t[start + len('# 21. MESSAGE CONTEXT STATE'):mid].strip()
    repair = t[mid:end].strip()
    note = 'Эти дополнения фиксируют исторические verdict WEB18. Последующая независимая адресная Windows-проверка №479: №05 `REG-WEB19-S2-INDEP-WINDOWS-20261101`; full regression/CI и Stage3 gates остаются NOT RUN/HOLD.'
    result[NAMES[0]] = t[:start] + repair + '\n\n' + harden + '\n\n' + note + '\n\n# 21. MESSAGE CONTEXT STATE\n\n' + t[end:]
    # 05: contiguous table, no status edits; put each exact header by its own record.
    t = result[NAMES[1]]
    section = block(t, '## 2026-11-01 — Astra: освобождение рабочего БЛОКА 1 Codex')
    # The navigation preamble is not part of this event.
    event, nav = section.split('**Редакция навигации:**', 1)
    t = replace_one(t, section, '**Редакция навигации:**' + nav)
    a = t.index('| FOLLOWUP-ID |'); b = t.index('## WEB18 / 2026-10-31 — Stage2 №473', a)
    rows = [l for l in t[a:b].splitlines() if l.startswith('|')]
    assert len(rows) == 9
    followup_note = 'Новые пункты добавляются только по фактическому review/closeout. До назначения пользовательской TASK значение successor_task_id = UNASSIGNED, а пункт остаётся OPEN. Закрытие пункта требует evidence/независимой проверки либо явного принятия остаточного риска пользователем. Новая постановка обязана перечислить относящиеся к ней FOLLOWUP-ID.'
    t = t[:a] + '\n'.join(rows) + '\n\n' + followup_note + '\n\n' + t[b:]
    h473 = '## WEB18 / 2026-10-31 — Stage2 №473 — независимый verdict REVISE'
    t = replace_one(t, h473 + '\n', '')
    t = replace_one(t, '**record_id:** `REG-WEB18-S2-REVISE-20261031`', h473 + '\n\n**record_id:** `REG-WEB18-S2-REVISE-20261031`')
    windows = block(t, '## WEB19 / 2026-11-01 — independent focused Windows test, №479')
    t = replace_one(t, windows, '')
    h479 = '## WEB18 / 2026-11-01 — Stage2 replace hardening №479'
    t = replace_one(t, h479, event.strip() + '\n\n' + windows.strip() + '\n\n' + h479)
    result[NAMES[1]] = t
    # 06: retain event paragraphs exactly; only move headings and the 482 event below the preamble.
    t = result[NAMES[2]]
    a = t.index('## 2026-11-01 — WEB19 / административное'); b = t.index('**Вход обновлён', a)
    event = t[a:b]; t = t[:a] + t[b:]
    hwin = '## 2026-11-01 — WEB19 / independent focused Windows verification of №479'
    t = replace_one(t, hwin, event.strip() + '\n\n' + hwin)
    glued = next(l for l in t.splitlines() if l.startswith('## 2026-10-31 — WEB18 / Stage2 №473'))
    heads = ['## ' + s for s in glued[3:].split('## ')]
    assert len(heads) == 3
    t = replace_one(t, glued + '\n', '')
    for head, eid in zip(heads, ['EVT-WEB18-S2-REVISE-20261031', 'EVT-WEB18-S2-REPAIR-PASS-20261031', 'EVT-WEB18-S2-HARDEN-PASS-20261101']):
        t = replace_one(t, '**event_id:** `' + eid + '`', head + '\n\n**event_id:** `' + eid + '`')
    result[NAMES[2]] = t
    # 34: only current fields; compatibility appendix and historical result rows stay intact.
    t = result[NAMES[3]]
    t = line_replace(t, '| Документационные каркасы', '| Документация / Codex 007 | Astra архивирована по №482; миграция PARTIAL, semantic/graph/cold-start OPEN. Текущая сдача `CODEX-WUA-DOC-WEB19-REPAIR-001`: ремонт шести документов, LOCAL RESULT READY / review WEB19 PENDING | №05 `REG-WEB19-ASTRA-SLOT-20261101`; №001 Codex / Astra; `reports/CODEX-WUA-DOC-WEB19-REPAIR-001/`; `RISK-DOC-CURRENT-001` OPEN |')
    t = line_replace(t, 'Направление Б ожидает', 'Направление Б ждёт технического назначения. По №482 Astra архивирована и слот Codex был освобождён; затем пользователь назначил текущий документационный ремонт. Это не запуск Core. Остаточные проверки миграции OPEN; пересечения — №40.')
    t = line_replace(t, '| Stage2/F-01:', '| Stage2 / F-01 и replace hardening | F-01 №473 исправлен №475: `FOLLOWUP-WUA-S2-CONTEXT-PATH-001` CLOSED в bounded scope; `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` CLOSED по №479. Исторический REVISE №473 сохранён | WEB19 независимо выполнил focused Windows-проверки №479; full independent regression/CI NOT RUN. `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED; Run Store P9 и Tk readers P1–P6 OPEN, Stage3/live/paid HOLD |')
    t = replace_one(t, 'до этого не открывать Stage2/paid.', 'новые этапы/live/paid требуют USER GO.')
    t = replace_one(t, 'Платный live-check и Stage2 не разрешены; идея FUTURE реализована в №467.', 'Платный live-check и новые этапы требуют USER GO; идея FUTURE реализована в №467.')
    t = replace_one(t, 'Stage1 БЛОК 1 очищать только после readback и сохранения истории', 'архивирование Astra по №482 не закрыло эти проверки')
    t = line_replace(t, '3. №467 ранее', '3. №467 USER ACCEPTED сохраняется. F-01 закрыт №475 в bounded scope; REPLACE-HARDEN закрыт №479. WEB19 добавил focused Windows PASS; full independent regression/CI, Tk readers P1–P6 и Stage3 prerequisites OPEN. №05/06 дают точные record/event ID.')
    t = line_replace(t, '4. Следующая рекомендуемая', '4. Run Store P9 — следующий технический приоритет для рассмотрения после USER GO. `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED; закрытый REPLACE-HARDEN повторно не назначать. Stage3/live/paid пока не начинать.')
    result[NAMES[3]] = t
    # 37: relocate historical Stage2 additions above Stage3, preserve the Stage3 contract verbatim.
    t = result[NAMES[4]]
    h3 = '### Этап 3. Отправка сообщений и восстановление'
    a = t.index(h3 + '**Техническое дополнение'); mid = t.index('**Дополнение WEB18 / Stage2 Repair №475:**', a)
    end = t.index('**Зачем:** пользователь должен понимать', mid)
    harden = t[a + len(h3):mid].strip(); repair = t[mid:end].strip()
    t = t[:a] + repair + '\n\n' + harden + '\n\nПоследующая адресная Windows-проверка WEB19: №06 `EVT-WEB19-S2-INDEP-WINDOWS-20261101`; полная independent regression/CI NOT RUN. Stage3/live/paid остаются без USER GO.\n\n' + h3 + '\n\n' + t[end:]
    result[NAMES[4]] = t
    # 40: distinguish WEB18 source-only from later WEB19 execution and Core from documentation activity.
    t = result[NAMES[5]]
    t = replace_one(t, 'Claude idle, Codex B on hold.', 'Claude idle; Codex сдаёт документационный ремонт, техническое направление Б на паузе.')
    t = replace_one(t, 'Не менять Stage1 PARTIAL; Stage2 №473 опубликована, но REVISE, не запускать Stage3.', 'Stage1 PARTIAL сохраняется. №473 — исторический REVISE; F-01 исправлен №475, replace hardening принят №479 в bounded scope, WEB19 добавил focused Windows PASS. Stage3 HOLD.')
    t = replace_one(t, 'independent runtime NOT RUN; source/report/raw evidence reviewed.', 'WEB18 проверил source/report/raw evidence без своего runtime; позднее WEB19 выполнил focused Windows storage tests (64 PASS/4 SKIP из 68 на Python 3.12 и 3.13, probes 4/4 PASS). Full independent regression/CI NOT RUN.')
    t = line_replace(t, '- **NEXT:**', '- **NEXT:** Run Store P9 — следующий технический приоритет для рассмотрения; staging остаётся OPEN/UNASSIGNED, Tk readers P1–P6 OPEN. Новая техническая TASK только по USER GO. Источники: №05 `REG-WEB19-S2-INDEP-WINDOWS-20261101`, `REG-WEB18-S2-HARDEN-20261101`; №06 `EVT-WEB19-S2-INDEP-WINDOWS-20261101`; отчёты WEB18/WEB19 по №479.')
    t = line_replace(t, '- **Оперативный статус:**', '- **Оперативный статус:** технический Core **WAITING / NOT ASSIGNED**. Astra архивирована и слот Codex освобождён по №482; текущая сдача `CODEX-WUA-DOC-WEB19-REPAIR-001` — документационная, LOCAL RESULT READY / review WEB19 PENDING. Миграция PARTIAL/OPEN и WA4-R gates сохраняются. Состояние слота после сдачи сверять по карточке и её `БЛОК 1.1`; ротация не означает независимую приёмку.')
    t = line_replace(t, '- **Файлы активной задачи:**', '- **Файлы текущего документационного ремонта:** №03/05/06/34/37/40 и `reports/CODEX-WUA-DOC-WEB19-REPAIR-001/`. Общий №40 менять последовательно с guard по hash. Программный код вне scope; `web_alarm/server.py` и `web_alarm/ui.py` не заняты этой TASK. БЛОК 1 → 1.1 — только по действующему механизму после сдачи.')
    t = replace_one(t, '## Обслуживание этой сводки', RESTORED_EDGE + '\n\n## Обслуживание этой сводки')
    result[NAMES[5]] = t
    for name, t in result.items():
        raw = source(name).read_bytes()
        # These inputs use LF; preserve their original convention in the applied candidate.
        newline = '\r\n' if raw.count(b'\r\n') == raw.count(b'\n') and b'\n' in raw else '\n'
        new = t.replace('\n', newline).encode('utf-8')
        p = WORK / 'after' / (name + '.txt'); p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(new)
    print(json.dumps({'candidates': 6, '34_chars_lf': len(result[NAMES[3]])}))


def apply():
    base = load(WORK / 'evidence/baseline.json')
    for item in base['targets']:
        assert sha((ROOT / item['path']).read_bytes()) == item['sha256'], ('SOURCE_CHANGED', item['path'])
    verify(False)
    for name in NAMES:
        (ROOT / 'Документация' / name).write_bytes((WORK / 'after' / (name + '.txt')).read_bytes())
    verify(True)


def graph(t):
    # Preserve literal syntax including code examples as a deliberately conservative comparison.
    return {'wiki': Counter(re.findall(r'!?\[\[[^\]\n]+\]\]', t)),
            'md': Counter(re.findall(r'!?\[[^\]\n]*\]\(([^\n]*?)\)', t)),
            'block_ids': Counter(re.findall(r'(?m)\^[A-Za-z0-9-]+\s*$', t)),
            'tags': Counter(re.findall(r'(?<![\w/\\])#([\w/-]+)', t))}


def verify(applied=True):
    checks = []
    def check(name, ok, detail=None): checks.append({'name': name, 'pass': bool(ok), 'detail': detail})
    old = {n: text(source(n)) for n in NAMES}
    new = {n: text(ROOT / 'Документация' / n) if applied else text(WORK / 'after' / (n + '.txt')) for n in NAMES}
    for n in NAMES:
        before, after = graph(old[n]), graph(new[n])
        if n == NAMES[5]: before['wiki'][RESTORED_EDGE] += 1
        check('graph syntax: ' + n, before == after)
        h_old = Counter(re.findall(r'^#{1,6} .+$', old[n], re.M))
        for h in list(h_old):
            if 'STATE## 20.2.' in h or 'review## 2026-' in h or 'восстановление**Техническое дополнение' in h:
                del h_old[h]
        h_new = Counter(re.findall(r'^#{1,6} .+$', new[n], re.M))
        check('all originally valid headings retained: ' + n, not (h_old - h_new))
        # All original paragraphs survive in structure-only documents except the intentionally repaired glued headers/table fragments.
        if n in [NAMES[0], NAMES[1], NAMES[2], NAMES[4]]:
            paras = [s.strip() for s in re.split(r'\n\s*\n', old[n]) if s.strip() and not s.lstrip().startswith('#')]
            excluded = ['Новые пункты добавляются', 'До назначения пользовательской TASK', '= UNASSIGNED,']
            missing = [s[:100] for s in paras if not any(s.startswith(x) for x in excluded) and s not in new[n]]
            check('original content paragraphs retained: ' + n, not missing, missing)
    for n, token in [(NAMES[1], 'record_id'), (NAMES[2], 'event_id')]:
        pat = r'\*\*' + token + r':(?:\*\*\s*`|\s*`)([^`]+)`'
        check(token + ' multiplicity preserved', Counter(re.findall(pat, old[n])) == Counter(re.findall(pat, new[n])))
    # Every original event body, including all negative verdicts, is byte-for-byte retained after newline normalization.
    event_lines = [l for l in old[NAMES[2]].splitlines() if l.startswith('**event_id')]
    check('all historical event payloads unchanged', all(new[NAMES[2]].count(l) == old[NAMES[2]].count(l) for l in event_lines), {'events': len(event_lines)})
    oldrows = [l for l in old[NAMES[1]].splitlines() if l.startswith('| `FOLLOWUP-')]
    check('all registry table rows preserved exactly', Counter(l for l in old[NAMES[1]].splitlines() if l.startswith('|')) == Counter(l for l in new[NAMES[1]].splitlines() if l.startswith('|')))
    for n, marker in [(NAMES[1], '## WEB17 / 2026-10-31 — EVM pinned multiwindow'), (NAMES[2], '## 2026-10-31 — WEB17 / EVM pinned multiwindow')]:
        check('entire earlier history suffix unchanged: ' + n, old[n][old[n].index(marker):] == new[n][new[n].index(marker):])
    check('all FOLLOWUP rows unchanged', all(l in new[NAMES[1]].splitlines() for l in oldrows), {'rows': len(oldrows)})
    table = new[NAMES[1]].split('| FOLLOWUP-ID |', 1)[1].split('\n\n', 1)[0]
    check('FOLLOWUP is one table with seven data rows', len([l for l in table.splitlines() if l.startswith('| `FOLLOWUP-')]) == 7 and all(len(l.split('|')) == 8 for l in table.splitlines()[1:]))
    check('FOLLOWUP explanation restored', 'successor_task_id = UNASSIGNED, а пункт остаётся OPEN.' in new[NAMES[1]])
    for n, idkind in [(NAMES[1], 'record_id'), (NAMES[2], 'event_id')]:
        for eid, key in [('S2-REVISE', '№473'), ('S2-REPAIR', '№475'), ('S2-HARDEN', '№479')]:
            pos = new[n].index('**' + idkind + ':** `'+('REG' if idkind == 'record_id' else 'EVT')+'-WEB18-'+eid)
            h = [l for l in new[n][:pos].splitlines() if l.startswith('## ')][-1]
            check(n[:2] + ' header owns ' + eid, key in h, h)
    check('06 intro precedes 482 event', new[NAMES[2]].index('Этот вход не является событием') < new[NAMES[2]].index('EVT-WEB19-ASTRA-SLOT'))
    check('03 historical additions ordered before state', new[NAMES[0]].index('## 20.1.') < new[NAMES[0]].index('## 20.2.') < new[NAMES[0]].index('# 21. MESSAGE CONTEXT STATE\n'))
    check('37 Stage2 history before Stage3', new[NAMES[4]].index('**Дополнение WEB18 / Stage2 Repair') < new[NAMES[4]].index('**Техническое дополнение Stage2 / №479') < new[NAMES[4]].index('### Этап 3. Отправка сообщений и восстановление\n'))
    check('37 Stage3 architecture unchanged', old[NAMES[4]][old[NAMES[4]].index('**Зачем:** пользователь должен понимать'):] == new[NAMES[4]][new[NAMES[4]].index('**Зачем:** пользователь должен понимать'):])
    check('34 historical appendix unchanged', old[NAMES[3]].split('## Сохранённые адреса прежней редакции', 1)[1] == new[NAMES[3]].split('## Сохранённые адреса прежней редакции', 1)[1])
    check('34 target budget', len(new[NAMES[3]]) <= 25000, {'before': len(old[NAMES[3]]), 'after': len(new[NAMES[3]])})
    check('34 no obsolete replacement assignment', 'Следующая рекомендуемая техническая задача — `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001`' not in new[NAMES[3]] and '| Stage2/F-01:' not in new[NAMES[3]])
    for token in ['FOLLOWUP-WUA-S2-CHAT-STAGING-001', 'Run Store P9', 'P1–P6', 'Stage3', 'RISK-DOC-CURRENT-001', 'B2', 'WA4-R']:
        check('34 key boundary retained: ' + token, token in new[NAMES[3]])
    check('40 distinguishes independent focused execution and full suite gap', '64 PASS/4 SKIP' in new[NAMES[5]] and 'Full independent regression/CI NOT RUN' in new[NAMES[5]])
    check('40 exactly one restored graph edge', new[NAMES[5]].count(RESTORED_EDGE) == 1 and len(graph(new[NAMES[5]])['wiki']) == 1)
    # Four negative controls: the checks must detect real loss or status/edge expansion.
    check('negative control: event loss detectable', not all(l in old[NAMES[2]].replace(event_lines[0], '') for l in event_lines))
    check('negative control: FOLLOWUP status change detectable', oldrows[0] not in new[NAMES[1]].replace(oldrows[0], oldrows[0].replace('ACCEPTED_BY_USER', 'CLOSED')))
    check('negative control: unauthorized graph edge detectable', graph(new[NAMES[5]]) != graph(new[NAMES[5]] + '\n[[34_TACTICAL_CONTEXT]]\n'))
    check('negative control: Stage3 contract loss detectable', new[NAMES[4]] != new[NAMES[4]].replace('Автоматическая повторная платная отправка в таком случае запрещена;', '', 1))
    if applied:
        base = load(WORK / 'evidence/baseline.json')
        changed, missing = [], []
        allow = {rel(ROOT / 'Документация' / n) for n in NAMES} | {CARD}
        for p, val in base['files'].items():
            if not (ROOT / p).is_file(): missing.append(p)
            elif sha((ROOT / p).read_bytes()) != val['sha256'] and p not in allow: changed.append(p)
        unexpected = [p for p in changed if p != '.obsidian/workspace.json']
        check('unrelated inventory stable', not (unexpected or missing), {'changed': changed, 'missing': missing, 'workspace_json_is_observed_not_attributed': True})
        check('applied readback matches all six candidates', all((ROOT / 'Документация' / n).read_bytes() == (WORK / 'after' / (n + '.txt')).read_bytes() for n in NAMES))
    result = {'task': TASK, 'kind': 'AUTHOR DOCUMENTARY CHECKS / INDEPENDENT REVIEW PENDING', 'applied': applied, 'passed': sum(c['pass'] for c in checks), 'failed': sum(not c['pass'] for c in checks), 'checks': checks}
    dump(WORK / ('evidence/checks_applied.json' if applied else 'evidence/checks_candidate.json'), result)
    print(json.dumps({'applied': applied, 'passed': result['passed'], 'failed': result['failed'], 'failures': [{'name': c['name'], 'detail_preview': str(c['detail'])[:600]} for c in checks if not c['pass']]}, ensure_ascii=False))
    assert result['failed'] == 0, 'Verification failed'


def package():
    diffs, metrics = [], []
    for name in NAMES:
        before = source(name).read_bytes(); after = (ROOT / 'Документация' / name).read_bytes()
        diff = ''.join(difflib.unified_diff(text(source(name)).splitlines(keepends=True), text(ROOT / 'Документация' / name).splitlines(keepends=True), fromfile='before/Документация/' + name, tofile='after/Документация/' + name, n=3))
        diffs.append(diff)
        metrics.append({'path': 'Документация/' + name, 'before_sha256': sha(before), 'after_sha256': sha(after), 'before_bytes': len(before), 'after_bytes': len(after), 'before_chars_lf': len(text(source(name))), 'after_chars_lf': len(text(ROOT / 'Документация' / name))})
    (WORK / 'changes.patch').write_text(''.join(diffs), encoding='utf-8', newline='\n')
    dump(WORK / 'evidence/change_metrics.json', metrics)
    paths = [ROOT / 'Документация' / n for n in NAMES] + [ROOT / CARD] + [p for p in WORK.rglob('*') if p.is_file() and p.name != 'manifest.json']
    entries = [{'path': rel(p), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(set(paths))]
    dump(WORK / 'manifest.json', {'task': TASK, 'status': 'LOCAL RESULT READY / INDEPENDENT WEB19 REVIEW PENDING', 'path_base': 'M:/GitHub/ag_llm', 'self_excluded': True, 'entries': entries})
    for item in entries:
        raw = (ROOT / item['path']).read_bytes(); assert sha(raw) == item['sha256'] and len(raw) == item['bytes']
    print(json.dumps({'diff_bytes': (WORK / 'changes.patch').stat().st_size, 'manifest_entries_verified': len(entries), 'metrics': [{'path': x['path'], 'chars': x['after_chars_lf']} for x in metrics]}, ensure_ascii=False))


if __name__ == '__main__':
    {'baseline': baseline, 'build': build, 'apply': apply, 'verify': verify, 'package': package}[sys.argv[1]]()
