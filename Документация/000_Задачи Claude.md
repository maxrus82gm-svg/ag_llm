# Рабочая карточка исполнителя — Claude 008

**Назначение:** персональная TASK и factual результаты Claude 008. Правила актуализированы 27.10.2026 по прямому поручению пользователя Astra/Codex о документационных каркасах. БЛОКИ 1–4 ниже сохранены без изменения: исторический verdict/фраза WAITING относится к своей дате и не отменяет текущего БЛОКА 1 или прямого поручения пользователя.

## Рабочий порядок

1. Действовать по конкретной утверждённой TASK/прямому поручению пользователя в разрешённом scope. Обычное новое назначение пользователь помещает в БЛОК 1; адресное поручение текущего чата не требует искусственного повторного GO. Старый NEXT не является запуском новой задачи. Уточнения привязывать к TASK/версии как AMENDMENT, не подменять исходную постановку.
2. Читать собственные Правила, относящиеся БЛОКИ 1/4; применимые разделы №08/34/профиля и тестовых контрактов по read matrix. Нормы №18 получать адресно со всеми requires при пробеле/конфликте. Общий №000 и весь №18/05 не загружать механически; архивы №001 не читать/искать рекурсивно. INDEPENDENT_PLAN сохраняет BLIND-START.
3. Git/GitHub запрещены без отдельного явного разрешения на операции и scope, включая чтение через CLI/UI/API/скрипты. Работать с локальными исходниками. Не менять чужие scope, live-storage, права, секреты, runtime/CI вне назначения. Публикация обычно за пользователем. Подробно: №18 → DOC-GIT-01/DOC-PARALLEL-01.
4. Исследовать причины и существующие механизмы; самостоятельно проверить релевантные edge cases и соседние инварианты. Исправлять подтверждённое внутри scope; находки вне scope сохранять с evidence и предложением. Не повторять одинаковые неудачные действия без новой диагностики. Проверки по риску и профилю №36.1/36.2/36.3; для чистой документации — смысл/сохранность/адреса/граф.
5. По каждой TASK, включая исследование/PARTIAL/FAIL/BLOCKED, сохранить внутри разрешённой публикуемой части проекта полный report, manifest и безопасные evidence. Указать версии, изменения, команды/exit/counts, исходные FAIL, NOT RUN, риски и DOC IMPACT. Не оставлять результат только в TEMP/переписке. Перед RESULT READY закончить обязательные проверки; незаконченный отчёт явно DRAFT.
6. Исполнитель не ротирует БЛОКИ 2–4 и не пишет №001 или общую документацию. Только исключение DOC-BLOCK1-SLOT-01@1 позволяет после финальной сдачи локально и дословно перенести свою завершённую TASK из БЛОКА 1 в один БЛОК 1.1 без Git, при подтверждённой сохранности старого слота. После пользовательской публикации ChatGPT независимо проверяет, сохраняет историю/readback и закрывает TASK. БЛОК 4 READ-ONLY для автора результата; self-PASS не является VERIFIED. Обнаруженный риск передать по форме №07; не объявлять его закрытым собственным предположением.
7. Для каждой технической TASK проверить launcher: один Start_WebAlarm.bat, штатный STANDARD; разрешённый TEST с TASK ID/целью; автор переключения возвращает STANDARD. При недоказанном восстановлении RESTORE_BLOCKED, без ложного зелёного. Не ослаблять backup/rollback или безопасность данных. №18 → DOC-WUA-LAUNCH-01.
8. Финал в чате — один самодостаточный копируемый text-блок: TASK, статус, изменения, проверки/NOT RUN, риски, DOC IMPACT, NEXT и отчётный путь. Полный фактический пакет остаётся в проекте. Прямая отправка другому чату/агенту требует разрешения на эту передачу; старый транспортный smoke не даёт постоянного права.

Локальный исполнитель не создаёт Remote-continuity сессии Alarm/ALARM_TASK_SESSION и пооперационные INTENT/DONE-журналы по привычке. Специальный аудит/защита — только если отдельно предусмотрены задачей; штатные runtime backup/rollback и существующая история при этом сохраняются.

**Исключение к п. 6 только после сданного финального пакета (№18 → DOC-BLOCK1-SLOT-01@1):** механически, без пересказа и без Git, перенести **свой** полный БЛОК 1 в единственный БЛОК 1.1 и перевести БЛОК 1 в `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Не затирать старый 1.1, пока его исходная TASK/AMENDMENT не подтверждены в №001 или опубликованном постоянном snapshot; выполнить readback/hash, сохранить `reports/<TASK-ID>/handoff_task.md`, отразить факт в отчёте. Если любой guard не пройден — NO ROTATE, не очищать БЛОК 1. Не трогать БЛОКИ 2–4, №001 или чужие документы. Пока новая TASK не назначена, БЛОК 1 может быть пустым.

**Скрипт и маркеры слотов (служебное поручение координатора 2026-10-29, `CLAUDE-DOC-TASK-SLOT-ROTATION-001`; канон — №18 → DOC-BLOCK1-SLOT-01@1):**
- Перенос БЛОК 1 → БЛОК 1.1 выполнять только скриптом `tools/task_slot_rotate.py`, без ручного копирования и пересказа. Порядок: `python -B tools/task_slot_rotate.py check --card "Документация/000_Задачи Claude.md"` → `rotate --card "Документация/000_Задачи Claude.md" --task-id <TASK-ID> --no-chat-amendment` (или `--chat-amendment <файл>` с точным текстом каждой принятой чат-поправки) — пробный прогон без записи → тот же вызов с `--apply`. Запускать только после всех обязательных тестов и сохранения финальных `report.md` + `manifest.json`.
- Результат `ROTATED` и JSON-протокол (TASK ID, SHA-256 до и после, copied exact, previous slot, статус `SUBMITTED / REVIEW PENDING`) приложить к отчёту TASK; снимок постановки скрипт сам сохраняет в `reports/<TASK-ID>/handoff_task.md`. Код выхода 3 = `NO ROTATE`: карточка не изменена, ничего не исправлять вручную, причину передать координатору.
- Скрипт сам проверяет маркеры и заголовки слотов, единственный TASK ID в БЛОКЕ 1 и его совпадение с `--task-id`, поправки к чужой TASK, двойную вставку и вставку целой карточки, текст вне маркеров, готовность отчётного пакета, сохранность прежнего БЛОКА 1.1 в №001 (или в опубликованном снимке: `--previous-archive` + `--previous-archive-ref`) и одновременную правку карточки.
- **Маркеры постоянные: не удалять и не копировать.** БЛОКИ 1 и 1.1 ограничены строками-заголовками `###### ▼ НАЧАЛО …` и `###### ▲ КОНЕЦ …`. Пользователь вставляет новую задачу только между маркерами БЛОКА 1 вместо строки `**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**` и может проверить вставку командой `check`. БЛОК 1.1 заполняет только скрипт. Полное служебное имя маркера в тексте карточки не писать: скрипт сочтёт такую строку повреждённым маркером.

**Канон сопровождения:** №18 → DOC-CONTEXT-OPS-01, DOC-TASK-CLOSEOUT-OWNER-01, DOC-LOCAL-REPORT-HANDOFF-01, DOC-HISTORY-ACCESS-01, DOC-VERIFIER-BLOCK4-01@2 и DOC-TEST-LIFECYCLE-01. Формы — №07. Новый координационный порядок не меняет технические статусы, B2/WA4-R/EVM/live/paid/MCP freeze и права предыдущих TASK.

# Задачи Claude

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

## Правила

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

[[000_Задачи для агента]]

[[001_История выполненных задач Claude]]

[[001_История выполненных задач Claude]]

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN
**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**
###### ▲ КОНЕЦ ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:END

---

# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА

###### ▼ НАЧАЛО КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:BEGIN
**SUBMITTED / REVIEW PENDING** · TASK ID `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001` · перенесено 2026-11-01 · SHA-256 копии `d1e2437c16166a71f26a9e734f4b424b4c166c8a343b9784d9e539a27a69dd2e` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001/handoff_task.md` · отчёт `reports/CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001/report.md`

# Задача: Усиление безопасной замены файлов общего хранилища Ultra Chat

**TASK ID:** `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001`

**Исполнитель:** Claude 008  
**Направление:** А — Ultra Chat / Shared Storage  
**Исходный FOLLOWUP:** `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001`  
**База:** `main@ffeb5d192924172f9ae6558cee961731b49295ce` после пользовательского принятия №476–477. До старта обязательно сверить фактический `main` и локальные исходники.

**Статус:** PROPOSED. Запуск только после назначения пользователем.

## 1. Цель

Усилить существующие операции замены файлов общего хранилища, которые используют атомарную запись, но пока не проверяют фактическое расположение временного файла через открытый дескриптор.

Затронутые операции:

- `rename_workspace()`;
    
- `save_project_context()`, включая сохранение предыдущей редакции;
    
- `rename_chat()`.
    

Необходимо применить уже разработанный в Stage2 механизм защищённой публикации там, где это оправдано, сохранив все действующие правила блокировки, версий, идентичности и совместимости.

Это **адресное усиление безопасности**, а не обещание абсолютной защиты от внешней программы того же пользователя, конкурентно подменяющей каталоги после последней проверки.

## 2. Обязательное чтение

До первой правки адресно изучить:

- №08, собственную карточку Claude, действующие определения №18;
    
- №03 — Workspace, Chat, Project Context и формат хранения;
    
- №37 — Stage2, переносимость §2.4;
    
- №36.1 и №36.3, применимые требования №36.2;
    
- №05 — `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001`;
    
- независимый протокол `reports/CHATGPT-WEB18-S2-REPAIR-REVIEW-20261031.md`;
    
- отчёты Stage2 №473 и ремонта №475;
    
- фактические реализации `_replace_verified`, `_publish_new_file`, `_atomic_write_text`, `_atomic_write_json`.
    

Архивы читать только адресно.

## 3. Pre-start

Проверить:

1. Актуальность локального исходного кода относительно опубликованной базы.
    
2. `Start_WebAlarm.bat` в STANDARD.
    
3. Отсутствие пересечения с активными задачами другого исполнителя.
    
4. Изолированное тестовое окружение без реальных Workspace и live API.
    
5. Сохранность исправления F‑01 из №475.
    

Git и GitHub со стороны Claude запрещены.

## 4. Реализация

Для каждой из трёх операций определить фактический путь чтения, временной записи, публикации и обратной проверки.

**Требования:**

1. Сохранять проверку Workspace identity и межпроцессную блокировку.
    
2. Проверять все необходимые родительские каталоги, их тип и фактическое расположение внутри разрешённого Workspace.
    
3. Проверять место открытия временного файла до записи его содержимого, используя существующий защищённый механизм либо обоснованную адресную адаптацию.
    
4. Отвергать заранее существующие junction/symlink/reparse point, способные вывести запись за пределы Workspace.
    
5. Для перезаписываемых файлов применять проверенную атомарную замену и последующее чтение байтов.
    
6. Для новых файлов истории PROJECT CONTEXT исключить перезапись уже существующей ревизии.
    
7. Не допускать потерю прежних полей Workspace/Chat, изменение идентичностей или пропуск проверки `expected_title`.
    
8. Сохранять прежние сигнатуры, форматы и корректные пользовательские сценарии.
    
9. При отказе явно возвращать ошибку, не выдавая неподтверждённую запись за успех.
    

Отдельно оценить `state.json`, исправленный №475, чтобы не сломать новый защищённый writer.

Сценарий конкурентной подмены **после** финальной проверки должен быть отдельно охарактеризован. Если полная защита на данной платформе не обеспечивается, честно оставить ограничение OPEN — не создавать ложную гарантию.

## 5. Разрешённый write-scope

**Код:** `context_storage.py` — только затронутые функции и необходимые общие вспомогательные механизмы.

**Тесты:** `test_ultra_chat_storage.py`; при обоснованной необходимости — адресные тесты `test_message_context.py` и `test_web_alarm_ultra_chat_storage.py`.

**Отчёт:** `reports/CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001/` с report, manifest, handoff snapshot, безопасными evidence и инструментами проверки.

**Карточка:** механическая ротация БЛОКА 1 → 1.1 исключительно после сдачи и проверки предыдущего архивного снимка.

Не менять `ultra_ui.py`, `web_alarm/server.py`, `web_alarm/ui.py`, launcher, другие подсистемы, общую документацию, CI/runners и реестры без отдельного разрешения.

## 6. Обязательные проверки

Работать только на одноразовых синтетических Workspace.

Проверить:

1. Обычное переименование Workspace и Chat, сохранение Project Context и истории предыдущих редакций.
    
2. Переименование с устаревшим `expected_title` — отказ без lost update.
    
3. Подмену родительского каталога заранее существующим Windows junction, включая каталоги истории.
    
4. Подмену после первой проверки и перед публикацией — результат и реальные побочные эффекты.
    
5. Неизменность внешнего синтетического каталога при ожидаемом безопасном отказе.
    
6. Ошибки `fsync`, `rename`, `replace`, заблокированный файл и контролируемое завершение процесса.
    
7. Конкурентную запись из двух процессов.
    
8. Сохранность RAW, Workspace/Chat ID, предыдущих Context Variant, F‑01 и всех корректных пользовательских операций.
    
9. Symlink при наличии платформенных прав; если нет — честный SKIP.
    
10. Compile, адресные negative/integration тесты, mutation controls и безопасную полную регрессию `all`.
    

Сохранять первоначальные RED результаты, raw exit/counts, аномалии и фактические ограничения. Проверить, что тесты не обращаются к реальной истории, Git, платным API и внешней сети.

## 7. Завершение

Перед финальным отчётом выполнить самостоятельный adversarial review всех изменённых writer-путей.

Отчёт обязан содержать:

- изменённые файлы и инженерное обоснование;
    
- первоначальные и финальные результаты тестов, включая ошибки;
    
- неизменность прежнего формата и идентичностей;
    
- точные гарантии и остаточные TOCTOU;
    
- SOURCE/TEST/EVIDENCE и SHA-256 манифест;
    
- состояние STANDARD launcher;
    
- DOC IMPACT и предложения для №03/05/06/34/37/40;
    
- явные NOT RUN и SKIP.
    

До завершения тестирования отчёт только DRAFT / ТЕСТЫ НЕ ЗАВЕРШЕНЫ.

Финальный статус: `RESULT READY / AWAITING INDEPENDENT VERIFICATION` либо честный PARTIAL/REVISE/BLOCKED.

Коммит и публикацию выполняет пользователь. Независимую приёмку и документальное закрытие выполняет ChatGPT.

**NEXT:** не начинать Stage3 автоматически. Перед ним отдельно разобраться с Run Store P9, оставшимися читателями Tk P1–P6 и необходимыми verification gates.
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Полный архив — [[001_История выполненных задач Claude]].

- **2026-11-01 / `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001`** — №479, **PASS / bounded source+evidence**, DOC ITERATION CLOSED. Проверенные replace writers и revision, финальные author mutants 9/9, full run2 1076 PASS/2 SKIP; independent runtime NOT RUN. №05 `REG-WEB18-S2-HARDEN-20261101`.
- **2026-10-31 / `CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001`** — №475 `5678414d`, PASS / SOURCE+AUTHOR-EVIDENCE (F-01); DOC ITERATION CLOSED. 9/9 отказ небезопасным ссылкам, focused 145 PASS/4 SKIP, full run2 1076 PASS/2 SKIP; independent runtime NOT RUN. №05 `REG-WEB18-S2-REPAIR-20261031`.
- **2026-10-31 / `CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001`** — №473 `c555312d`, **REVISE / DOC ITERATION CLOSED; PRODUCT NOT ACCEPTED**. Общий writer и Web create/rename опубликованы, но найден F-01: context variants/state могут писать через вложенный junction вне Workspace. Автор Python 1076 PASS/2 SKIP, JS 140/140, mutants 39/39; independent source/8 SHA и структуры evidence проверены, runtime НЕ перезапущен. №05 `REG-WEB18-S2-REVISE-20261031`, `FOLLOWUP-WUA-S2-CONTEXT-PATH-001`.
- **2026-10-31 / `CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001`** — №467 `f4597868`, **PASS / USER ACCEPTED; DOC ITERATION CLOSED**. Несколько независимых EVM-окон, сохранение после рестарта, Ctrl-preview выше окон, без дублей. Пользователь подтвердил обычную мышь и сенсорный ввод; авторские Python 1065 PASS/2 SKIP, JS 133/133, browser 198/198, mutants 38/38. Verifier source/evidence reviewed; independent rerun NOT RUN. №05 `REG-WEB17-EVM-PINS-20261031`, №06 `EVT-WEB17-EVM-PINS-ACCEPT-20261031`.
- **2026-10-30 / CLAUDE-WUA-EVM-INTERACTION-DND-001** — №464 `f9a375a`, **PASS / USER ACCEPTED; DOC ITERATION CLOSED**. Inline, Ctrl-preview, DnD и «Избранное» приняты пользователем; verifier independent rerun NOT RUN. №05 `REG-WEB17-EVM-DND-20261030`.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

**WEB18 01.11.2026 / №479 `508cba49`:** `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001` — **PASS / BOUNDED SOURCE+AUTHOR-EVIDENCE, DOC ITERATION CLOSED**. `rename_workspace`, `rename_chat`, `save_project_context` используют проверенную замену; Project Context revision — эксклюзивная публикация, старый текст читается с no-follow. Автор focused 166 = 161 PASS/5 SKIP; all run1 1075 PASS/1 ERROR/2 SKIP, run2 1076 PASS/2 SKIP; mutants run1 8/9 и финально 9/9 KILLED; baseline RED сохранён. Исходный код и raw JSON evidence проверены независимо по GitHub, **самостоятельный Python/Windows/CI запуск NOT RUN**. Same-user TOCTOU после final check остаётся вне защищённой границы; `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` CLOSED для оговорённого scope, `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED. Stage3/live/paid без USER GO; Run Store P9 и Tk readers P1–P6 OPEN. Подробнее `reports/CHATGPT-WEB18-S2-HARDEN-REVIEW-20261101.md`.
- **Stage2 repair №475:** `context_storage.py` теперь проверяет nested `message_context` и `variants` и пишет через проверенные операции. **Review WEB18 31.10.2026:** `CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001` №475 `5678414d` принят **PASS / SOURCE+AUTHOR-EVIDENCE** в ограниченном F-01 scope; full independent Python/Windows/CI NOT RUN. Автор F-01: 7/9 внешних записей до, 0/9 после; focused 145 PASS/4 SKIP, full run2 1076 PASS/2 SKIP, mutants 8 KILLED/1 SURVIVED (R01c). Первый full-run: **1075 PASS/1 ERROR/2 SKIP** (ошибка арифметики в отчёте Claude: 1077 PASS). `FOLLOWUP-WUA-S2-CONTEXT-PATH-001` CLOSED после №475, residual `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` OPEN/UNASSIGNED; Stage2 bounded SOURCE/EVIDENCE ACCEPTED, не FULL RUNTIME/PRODUCTION PASS. Исторический №473 REVISE неизменен; Stage3/live/paid без отдельного GO. Протокол: `reports/CHATGPT-WEB18-S2-REPAIR-REVIEW-20261031.md`.
- **Stage2 №473 / 31.10:** общий writer Workspace/Chat/RAW, межпроцессная блокировка, идемпотентный message_id и Web create/rename опубликованы; пользовательского/продуктового PASS нет. Verifier обнаружил F-01: невалидируемый вложенный `message_context` junction при записи state/variants. **REVISE**, продолжение `FOLLOWUP-WUA-S2-CONTEXT-PATH-001`, отдельное назначение. Полная регрессия и мутанты только author evidence; на точном SHA independent runtime NOT RUN.
- **EVM pinned windows №467:** `web_alarm/ui.py`, `model_cards.py`, `server.py` и тесты; отдельные закреплённые окна по `connection_id`, координаты и порядок в прежнем `ultra/evm_view.json`; Ctrl-preview выше окон, перенос/закрытие без дублей, восстановление после перезапуска. Новый самостоятельный реестр моделей/секретов не создан.
- **Проверки №467:** авторские Python 1065 PASS/2 SKIP, JS 133/133, trusted headless browser 198/198, mutants 38/38; physical Windows mouse author NOT RUN. Пользователь отдельно подтвердил мышь и сенсорный ввод в Ultra; verifier независимо не повторял тестовые команды, source/evidence проверены.
- **Связь с №464 и roadmap:** DnD/inline/Favorites сохранены; `FUTURE-EVM-PINNED-COMPARE-001` реализован и принят в UX scope, больше не BACKLOG. Широкие независимые platform/regression gates остаются адресными, но это не открытая реализационная задача. №37 Stage2 опубликован, но REVISE; Stage3/paid/live не разрешены.
- **Ранее:** №464 PASS/USER ACCEPTED, compact №457 REVISE, Stage1/исходная EVM terminal PARTIAL. История/verdict в №001, №05, №06.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER

## WEB18 / 2026-11-01 — `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001` — BOUNDED PASS

**WEB18 01.11.2026 / №479 `508cba49`:** `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001` — **PASS / BOUNDED SOURCE+AUTHOR-EVIDENCE, DOC ITERATION CLOSED**. `rename_workspace`, `rename_chat`, `save_project_context` используют проверенную замену; Project Context revision — эксклюзивная публикация, старый текст читается с no-follow. Автор focused 166 = 161 PASS/5 SKIP; all run1 1075 PASS/1 ERROR/2 SKIP, run2 1076 PASS/2 SKIP; mutants run1 8/9 и финально 9/9 KILLED; baseline RED сохранён. Исходный код и raw JSON evidence проверены независимо по GitHub, **самостоятельный Python/Windows/CI запуск NOT RUN**. Same-user TOCTOU после final check остаётся вне защищённой границы; `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` CLOSED для оговорённого scope, `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED. Stage3/live/paid без USER GO; Run Store P9 и Tk readers P1–P6 OPEN. Подробнее `reports/CHATGPT-WEB18-S2-HARDEN-REVIEW-20261101.md`. БЛОК 1 WAITING, БЛОК 1.1 с данной TASK и копией постановки; предыдущая №475 сохранена в пакете/истории. Исторические verdict №473/№475 не переписываются.

## WEB18 / 2026-10-31 — CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001 — BOUNDED PASS / DOC ITERATION CLOSED

**Review WEB18 31.10.2026:** `CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001` №475 `5678414d` принят **PASS / SOURCE+AUTHOR-EVIDENCE** в ограниченном F-01 scope; full independent Python/Windows/CI NOT RUN. Автор F-01: 7/9 внешних записей до, 0/9 после; focused 145 PASS/4 SKIP, full run2 1076 PASS/2 SKIP, mutants 8 KILLED/1 SURVIVED (R01c). Первый full-run: **1075 PASS/1 ERROR/2 SKIP** (ошибка арифметики в отчёте Claude: 1077 PASS). `FOLLOWUP-WUA-S2-CONTEXT-PATH-001` CLOSED после №475, residual `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` OPEN/UNASSIGNED; Stage2 bounded SOURCE/EVIDENCE ACCEPTED, не FULL RUNTIME/PRODUCTION PASS. Исторический №473 REVISE неизменен; Stage3/live/paid без отдельного GO. Протокол: `reports/CHATGPT-WEB18-S2-REPAIR-REVIEW-20261031.md`. Independent SHA-256/bytes 4/4 (code/test/card/task snapshot) и raw evidence пересчитаны, source path review выполнен. Авторский first-run ERROR folder-picker зарегистрирован, повтор модуля 16/16 ×3; 4 symlink SKIP, independent regression NOT RUN. БЛОК 1 WAITING, 1.1 exact repair сохранён.

**Автор:** ChatGPT / WEB17. Для Claude этот блок READ-ONLY. Исторические verdict находятся в №06.

## WEB18 / 2026-10-31 — CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001 — REVISE / DOC ITERATION CLOSED

**Verified source:** main №473 `c555312d`; дословная TASK `handoff_task.md` и БЛОК 1.1, авторский report/manifest/evidence сохранены. Independent SHA-256 **8/8** changed/new engineer files, пересчитаны авторские 1078/122 test-list и 39 unique KILLED. **Independent Python/JS/CI/Windows runtime NOT RUN.** F-01: `restore_message_raw`/`create_message_context_variant` используют `_atomic_write_json` в `message_context` без no-follow для вложенных каталогов; заранее существующий junction может направить запись вне Workspace. **PRODUCT NOT ACCEPTED; исправление + изолированный negative oracle до PASS.** №05 `REG-WEB18-S2-REVISE-20261031`, `FOLLOWUP-WUA-S2-CONTEXT-PATH-001` (OPEN, UNASSIGNED); №06 `EVT-WEB18-S2-REVISE-20261031`; независимый протокол `reports/CHATGPT-WEB18-S2-REVIEW-20261031.md`. Stage3/paid/live и другие риски не разрешены. БЛОК 1 WAITING, БЛОК 1.1 сохранить.

## 0. 2026-10-31 / CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001 — PASS / USER ACCEPTED

**TASK:** `CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001` (Claude 008). **Код и evidence:** №467 `main@f4597868ef3af6ef1f57f40c6993fbca76119e7d`, `reports/CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001/report.md`, `manifest.json`, `evidence/` (17 снимков), `handoff_task.md`, дословный БЛОК 1.1 (SHA-256 `99e2642ab902449287ffa760aeff0106258a2eb36f617b9e5b1600c1291f20ba`; безопасная ротация). **Функциональность:** несколько независимых закрепляемых окон EVM, одно окно на `connection_id`, сохранение позиций в `ultra/evm_view.json`, восстановление после обновления/рестарта, Ctrl-preview выше закреплённых, отсутствие дублей и сохранение DnD/«Избранного». **Авторские evidence:** Python 1065 PASS / 2 SKIP (из 1067), JS 133/133, trusted browser input 198/198 (headless Chrome с реальными событиями указателя), мутанты 38/38, final gates exit 0. **Reviewer:** GitHub source/report/manifest/evidence проверены адресно; независимый повтор Python/JS/CI/physical Windows run не проводился. **USER 2026-10-31:** лично проверил на Windows работу обычной мышью и сенсорным вводом, несколько окон, расположение и сохранность, подтвердил «всё работает» и прямо распорядился закрыть задачу/идти дальше. Это USER ACCEPTED UX, не доказательство теста на всех планшетах или альтернативных браузерах. **Итог:** **PASS / USER ACCEPTED (EVM pinned multiwindow UX scope); DOC ITERATION CLOSED**; остаточные широкие платформенные/independent REGRESSION проверки отслеживаются отдельно, Stage2/paid/live не разрешены автоматически. Источник идеи `FUTURE-EVM-PINNED-COMPARE-001` реализован в scope задачи, не дефект №464.

**Адреса:** №05 `REG-WEB17-EVM-PINS-20261031`; №06 `EVT-WEB17-EVM-PINS-ACCEPT-20261031`; №001 Claude — 2026-10-31. До пользовательского merge закрытие документируется только в ветке GPT.

## 1. 2026-10-30 / CLAUDE-WUA-EVM-INTERACTION-DND-001 — PASS / USER ACCEPTED

**Публикация:** `main@f9a375a47472375ce7e07ee82b490016e20e1922` (№464); `reports/CLAUDE-WUA-EVM-INTERACTION-DND-001/``report.md`, `manifest.json`, `evidence/**` и точная постановка в `handoff_task.md` + неизменённом БЛОКЕ 1.1 (копия SHA-256 `ba14a5f9efcf1af9c646251d7037df91e1e021169c1cc065268799fcd2a975cb`). **Выполнено verifier:** прочитаны источник, manifest, test evidence и адресный код/тест; сверено отсутствие изменений серверного authority. **Не выполнено verifier:** самостоятельные Python/JS/CI/Windows-GUI прогоны. **Авторские:** Python 1061 PASS/2 SKIP, JS 126/126, browser trusted input 125/125, mutants 35/35, restart PASS. **USER ACCEPTED:** пользователь на Windows через AnyDesk проверил основной UX и 2026-10-30 явно утвердил результат. **Verdict:** **PASS / USER ACCEPTED (EVM interaction scope), DOC ITERATION CLOSED** в границах назначенной UI-задачи, без ложного «независимый полный runtime PASS». Непроверенные платформы/платные операции остаются OPEN; `FUTURE-EVM-PINNED-COMPARE-001` — отдельная будущая возможность. №05 `REG-WEB17-EVM-DND-20261030`; №06 `EVT-WEB17-EVM-DND-ACCEPT-20261030`.

## 2. 2026-10-29 / CLAUDE-WUA-EVM-COMPACT-LAYOUT-001 — REVISE

**ITERATION DOC CLOSED / REVISE, PRODUCT NOT ACCEPTED** для ревизии №457: перекрывающий hover/неудобный drag. Последующая задача №464 принята пользователем; прежний отрицательный verdict исторически не переписывается. №05 `FOLLOWUP-EVM-457-*`, №06 `EVT-WEB16-EVM-COMPACT-REVISE-20261029`.

## 3. 2026-10-28 / CLAUDE-WUA-EVM-MODEL-CARD-UI-001 — TERMINAL PARTIAL

`main@55cc4477`; исходная EVM в ограниченной приёмке, полный independent Windows/CI NOT RUN. Полный источник №001 и №06 `EVT-WEB16-EVM-CLOSE-20261028`.

---

**NEXT WEB18 / 31.10:** ремонт №475 рассмотрен, Stage2 ограниченно SOURCE/EVIDENCE ACCEPTED. Новый кандидат FOLLOWUP-WUA-S2-REPLACE-HARDEN-001 — только по отдельному USER GO. Stage3/paid/live и Codex B не запускать.
