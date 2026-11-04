# Рабочая карточка исполнителя — Codex 007

**Назначение:** персональная TASK и factual результаты Codex 007. Текущее состояние определяется только фактическими БЛОКАМИ1/1.1 ниже и штатной проверкой скрипта; пролог не дублирует статус. БЛОКИ2–4 содержат историю и независимые verdict. Правила скриптовой сдачи уточнены USER GO 2026-11-04; новых implementation GO этот пролог не даёт.

## Рабочий порядок

1. Действовать по конкретной утверждённой TASK/прямому поручению пользователя в разрешённом scope. Обычное новое назначение пользователь помещает в БЛОК 1; адресное поручение текущего чата не требует искусственного повторного GO. Старый NEXT не является запуском новой задачи. Уточнения привязывать к TASK/версии как AMENDMENT, не подменять исходную постановку.
2. Читать собственные Правила, относящиеся БЛОКИ 1/4; применимые разделы №08/34/профиля и тестовых контрактов по read matrix. Нормы №18 получать адресно со всеми requires при пробеле/конфликте. Общий №000 и весь №18/05 не загружать механически; архивы №001 не читать/искать рекурсивно. INDEPENDENT_PLAN сохраняет BLIND-START.
3. Git/GitHub запрещены без отдельного явного разрешения на операции и scope, включая чтение через CLI/UI/API/скрипты. Работать с локальными исходниками. Не менять чужие scope, live-storage, права, секреты, runtime/CI вне назначения. Публикация обычно за пользователем. Подробно: №18 → DOC-GIT-01/DOC-PARALLEL-01.
4. Исследовать причины и существующие механизмы; самостоятельно проверить релевантные edge cases и соседние инварианты. Исправлять подтверждённое внутри scope; находки вне scope сохранять с evidence и предложением. Не повторять одинаковые неудачные действия без новой диагностики. Проверки по риску и профилю №36.1/36.2/36.3; для чистой документации — смысл/сохранность/адреса/граф.
5. По каждой TASK, включая исследование/PARTIAL/FAIL/BLOCKED, сохранить внутри разрешённой публикуемой части проекта полный report, manifest и безопасные evidence. Указать версии, изменения, команды/exit/counts, исходные FAIL, NOT RUN, риски и DOC IMPACT. Не оставлять результат только в TEMP/переписке. Перед RESULT READY закончить обязательные проверки; незаконченный отчёт явно DRAFT.
6. Исполнитель не ротирует БЛОКИ 2–4 и не пишет №001 или общую документацию. Только исключение DOC-BLOCK1-SLOT-01@2 позволяет после финальной сдачи локально и дословно перенести свою завершённую TASK из БЛОКА 1 в один БЛОК 1.1 без Git, при подтверждённой сохранности старого слота. После пользовательской публикации ChatGPT независимо проверяет, сохраняет историю/readback и закрывает TASK. БЛОК 4 READ-ONLY для автора результата; self-PASS не является VERIFIED. Обнаруженный риск передать по форме №07; не объявлять его закрытым собственным предположением.
7. Для каждой технической TASK проверить launcher: один Start_WebAlarm.bat, штатный STANDARD; разрешённый TEST с TASK ID/целью; автор переключения возвращает STANDARD. При недоказанном восстановлении RESTORE_BLOCKED, без ложного зелёного. Не ослаблять backup/rollback или безопасность данных. №18 → DOC-WUA-LAUNCH-01.
8. Финал в чате — один самодостаточный копируемый text-блок: TASK, статус, изменения, проверки/NOT RUN, риски, DOC IMPACT, NEXT и отчётный путь. Полный фактический пакет остаётся в проекте. Прямая отправка другому чату/агенту требует разрешения на эту передачу; старый транспортный smoke не даёт постоянного права.

Локальный исполнитель не создаёт Remote-continuity сессии Alarm/ALARM_TASK_SESSION и пооперационные INTENT/DONE-журналы по привычке. Специальный аудит/защита — только если отдельно предусмотрены задачей; штатные runtime backup/rollback и существующая история при этом сохраняются.

**Обязательная сдача слота / №18 → DOC-BLOCK1-SLOT-01@2:** после финального пакета запустить одну команду:

```powershell
python -B tools/task_slot_rotate.py finish --card "Документация/000_Задачи Codex.md" --task-id TASK-ID --no-chat-amendment --apply
```

При отдельных поправках вместо --no-chat-amendment передать --chat-amendment FILE для каждой. Скрипт сам делает check/dry-run/apply/readback, находит точный предыдущий снимок по ссылке в 1.1, переиспользует его или сначала сохраняет отсутствующую копию. Прежние snapshots не перезаписываются. Утраченные поправки, разные тексты одного ID, конфликт/ошибка записи — NO ROTATE. Никаких ручных переносов/очистки. JSON и handoff_task.md сохранить в пакете, затем актуализировать manifest. ALREADY_ROTATED — успешный повтор без записи; ожидание никогда не переносится в 1.1. Локальное сохранение не доказывает публикацию/независимую приёмку.

Окно: tools/task_slot_debug.json, enabled true/false; --monitor на один запуск, --headless без окна. Ярлык «Карточка Codex — статус» открывает наблюдение, обновление30 минут/по кнопке. Пользователь может завершить TASK через finish либо назначить новую через «Новая задача…» справа вверху, только когда БЛОК1 WAITING; форма запускает проверенный assign и не запускает агента автоматически. Только пользователь назначает следующую TASK между постоянными маркерами БЛОКА1. БЛОК1.1 заполняет только скрипт; БЛОКИ2–4/001 не затрагивать.

**Канон сопровождения:** №18 → DOC-CONTEXT-OPS-01, DOC-TASK-CLOSEOUT-OWNER-01, DOC-LOCAL-REPORT-HANDOFF-01, DOC-HISTORY-ACCESS-01, DOC-VERIFIER-BLOCK4-01@2 и DOC-TEST-LIFECYCLE-01. Формы — №07. Новый координационный порядок не меняет технические статусы, B2/WA4-R/EVM/live/paid/MCP freeze и права предыдущих TASK.

# Задачи Codex

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

## Правила

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

[[000_Задачи для агента]]

[[001_История выполненных задач Codex]]

**USER GO 2026-11-04 / обязательный автоматизм:** после финального пакета запускать `tools/task_slot_rotate.py finish` (check→dry-run→apply→readback). Ручной перенос и очистка БЛОКОВ1/1.1 запрещены. Канон @2 разрешает скрипту сначала создать/проверить отсутствующий локальный снимок прежнего 1.1, не объявляя публикацию. Старые требования опубликованного snapshot/ручного previous-archive ниже уступают @2. Повторный запуск не переносит ожидание и не дублирует сданную TASK. Watch/ярлык открывает локальное наблюдение, обновление каждые30 минут; отдельные кнопки запускают finish/назначение пользователем через assign. Новая TASK допускается только в WAITING, без замены занятого слота.

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN
**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**
###### ▲ КОНЕЦ ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:END

---

# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА

###### ▼ НАЧАЛО КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:BEGIN
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-UX-LIVE-FIX-001` · перенесено 2026-11-04 · SHA-256 копии `c0301361b6bb8055d46b3ef66aae023900ec831b9f14415998f7c08e3a086ae0` · CHAT-ONLY AMENDMENT: 1 в снимке · снимок `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/report.md`


**TASK ID:** `CODEX-WUA-CHAT-UX-LIVE-FIX-001`

**Название:** Ultra Chat — устранение дефектов нового интерфейса по результатам Windows-проверки.

**Исполнитель:** Codex 007  
**Координатор:** ChatGPT WEB21  
**Приоритет:** HIGH  
**Проект:** `ag_llm / Web Alarm Ultra`

## 1. Цель

Проверить и исправить ошибки в новой UX-реализации Ultra Chat, созданной ChatGPT по прямому поручению пользователя.

**Не разрабатывать интерфейс заново.** Сохранить существующие локальные изменения, выявить причины дефектов и исправить их минимально необходимыми правками.

## 2. Исходное состояние

В рабочем каталоге `M:\GitHub\ag_llm` имеются **неопубликованные изменения**:

- `web_alarm/ui.py`
    
- `web_alarm/ultra_chat.py`
    
- `web_alarm/workspace_registry.py`
    
- `test_web_alarm_ultra_chat_ui.js`
    
- `test_web_alarm_ultra_chat_storage.py`
    

Предыдущий отчёт ChatGPT:

`reports/CHATGPT-WEB21-ULTRA-CHAT-UX-20261104/`

Он содержит авторские результаты: **145 JS PASS, 44 Python PASS**. Это не независимая приёмка. В реальном браузере пользователь обнаружил ошибки.

**Важно:** не выполнять `git reset`, `git clean`, checkout, откат или замену локальных файлов их версиями из GitHub. Git/GitHub не использовать без отдельного разрешения. Защитить исходное состояние локальными контрольными суммами и адресными резервными копиями.

Не трогать `.obsidian`, реальную папку `Чат_pro`, её `.ultra`, пользовательские диалоги, другие Workspace и их данные.

## 3. Подтверждённые пользовательские дефекты

### 3.1. Ложная ошибка создания Workspace

Пользователь нажал **«+ Создать Workspace»**, выбрал или создал папку через системное окно Windows, подтвердил действие.

После этого:

- Новый Workspace появился в списке.
    
- Интерфейс одновременно показал красное сообщение «Не удалось создать Workspace».
    
- Сообщение сохранялось до обновления.
    

**Требуется:** установить точную причину. Разделить успешную регистрацию, ошибку регистрации и сбой последующей загрузки истории. Не выдавать успех за ошибку и наоборот. Не выполнять автоматическую повторную регистрацию при неопределённом результате. Проверить отсутствие дублей.

Пустая папка без истории Ultra должна честно показывать `missing_history`. Не создавать историю Ultra самовольно.

### 3.2. Появление `nullnullnullnull`

При раскрытии нового Workspace в списке отображается буквальный текст:

`nullnullnullnull`

**Требуется:** воспроизвести, установить источник некорректного DOM-вывода, исправить и добавить регрессионный тест.

Проверить пустой Workspace, Workspace с одним и несколькими диалогами, переключение и сворачивание.

### 3.3. Не работает переименование

После обновления интерфейса появились карандаши, но пользователь сообщил, что переименование не работает.

**Требуется проверить оба действия:**

- Переименование отображаемого названия Workspace.
    
- Переименование конкретного диалога.
    

Проверить открытие формы, ввод, сохранение, обработку ошибок, повторное открытие и соответствие выбранному объекту.

При переименовании Workspace менять только отображаемое имя в существующем реестре, не путь, ID и не данные старой Ultra.

## 4. Проверить новый UX

Сохранить утверждённое пользователем расположение элементов:

- Workspace раскрывается и сворачивается нажатием.
    
- Чаты вложены в свой Workspace.
    
- У Workspace видимые карандаш и плюс.
    
- У диалога собственный карандаш.
    
- Выбранные Workspace и чат постоянно подсвечиваются.
    
- «+ Создать Workspace» открывает существующий системный выбор папки без перехода в операторскую панель.
    
- При регистрации по умолчанию используется имя выбранной папки.
    
- Отдельные старые кнопки «Новый диалог» и «Переименовать» не показываются.
    
- Отправка сообщений по-прежнему отключена.
    

Не добавлять удаление или архивирование. Не запускать Stage 3, Turn, inference и реальные LLM-запросы.

## 5. Технический scope

**Разрешено изменять только:**

- `web_alarm/ui.py`
    
- `web_alarm/ultra_chat.py`
    
- `web_alarm/workspace_registry.py`
    
- `test_web_alarm_ultra_chat_ui.js`
    
- `test_web_alarm_ultra_chat_storage.py`
    
- `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/`
    

**Только читать:** сервер, launcher, существующее ядро Ultra, документацию и остальные тесты.

Если причина требует изменений `web_alarm/server.py`, `context_storage.py` или файлов вне scope — остановиться в этой части, сохранить воспроизведение и запросить отдельное разрешение.

Существующие механизмы безопасности и авторизации сохранять.

## 6. Обязательная проверка

Сначала изучить локальные файлы и отчёт предыдущей UX-работы. Прочитать применимые правила №08, №18 (`DOC-BLOCK1-SLOT-01@2`), №37, №34, №40 и профиль тестирования №36.3.

До исправления по возможности получить воспроизводимый RED для каждого обнаруженного дефекта.

Затем выполнить:

1. JavaScript-тесты Ultra Chat, операторской панели и EVM.
    
2. Python-тесты Ultra Chat, общего хранения и UI.
    
3. Отрицательные сценарии: отмена выбора папки, отсутствие истории, повторная регистрация, повреждённые данные, конфликт переименования, ошибка сервера.
    
4. Проверку отсутствия `null` и исполняемого HTML в DOM.
    
5. Проверку сохранности существующих диалогов и общего хранилища.
    
6. Проверку пользовательского сценария **в реальном Windows Chromium/Chrome**, если доступен безопасный способ управления браузером. Если нет — честное `NOT RUN`, без подмены синтетическим тестом.
    

Использовать только изолированные синтетические Workspace и локальный сервер, не текущие пользовательские данные. Не запускать второй сервер на занятом порту. Не перезапускать пользовательский Web Alarm без согласования.

Если запускались режимы тестирования, восстановить и подтвердить STANDARD. При неподтверждённом восстановлении — `RESTORE_BLOCKED`.

## 7. Отчёт и сдача

Создать пакет:

`reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/`

Включить:

- `report.md` — причины каждого дефекта, изменения, оставшиеся ограничения, итоговый статус;
    
- `manifest.json` — адресные файлы, размеры и SHA-256;
    
- evidence — исходные RED, итоговые PASS, команды, exit codes, readback;
    
- результаты проверки Windows GUI либо точное `NOT RUN`;
    
- подтверждение, что пользовательские данные не затронуты.
    

Не редактировать общий реестр, историю выполненных задач и БЛОКИ 2–4 карточки Codex.

**После полного итогового пакета** выполнить штатную сдачу слота:

```
python -B tools/task_slot_rotate.py finish --card "Документация/000_Задачи Codex.md" --task-id CODEX-WUA-CHAT-UX-LIVE-FIX-001 --no-chat-amendment --apply --headless
```

Если появятся отдельно принятые поправки, вместо `--no-chat-amendment` передать соответствующие файлы `--chat-amendment`. Сохранить JSON результата и обновить manifest. При `NO ROTATE` ничего не переносить вручную.

**Git/GitHub запрещены. Публикация — за пользователем.**

Итог: `RESULT READY / AWAITING INDEPENDENT VERIFICATION` или честный `PARTIAL / BLOCKED`. Собственные тесты не являются независимым PASS.
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Постоянный архив — №001 Codex и снимки `reports/<TASK-ID>/`.

- **04.11 / `CODEX-WUA-CHAT-UX-LIVE-FIX-001` AMENDMENT 01:** WEB22 bounded source+author-evidence PASS, user Windows first/next chat GUI ACCEPTED; author 158 JS PASS / 166 Python PASS/5 SKIP, verifier runtime NOT RUN; slot ROTATED; №05 `REG-WEB22-CODEX-UX-LIVE-FIX-20261104`.
- **04.11 / `CODEX-WUA-CHAT-UI-INTEGRATION-001`:** WEB21 PASS / BOUNDED SOURCE+EVIDENCE, author 66 JS / 57 Python, verifier runtime NOT RUN; №05 `REG-WEB21-CODEX-UI-INTEGRATION-20261104`.
- **02.11 / `CODEX-WUA-LOCAL-LLM-DISCOVERY-001`:** bounded diagnostic PASS / TASK PARTIAL; Colibri not verified, adapter NOT IMPLEMENTED.
- **01.11 / `CODEX-WUA-DOC-WEB19-REPAIR-001`, №483:** bounded document PASS, DOC CLOSED.
- **01.11 / `ASTRA-DOC-CONTEXT-OPTIMIZATION-001`, №482:** USER SLOT RELEASE; semantic/graph checks OPEN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **`CODEX-WUA-CHAT-UX-LIVE-FIX-001`:** прямое поручение WEB21 + AMENDMENT 01; исправления Workspace registration/DOM/rename, first chat in safe `missing_history` only after confirmation through shared core. Author 158 JS, 166 Python PASS/5 SKIP; GUI first/next chats USER ACCEPTED; independent runtime/negative Windows NOT RUN. `finish` ROTATED, 1.1 preserved; followups №05.
- **`CODEX-WUA-CHAT-UI-INTEGRATION-001`:** existing Workspace registration shortcut + catalog refresh, source+author evidence accepted WEB21, independent runtime NOT RUN.
- **`CODEX-WUA-LOCAL-LLM-DISCOVERY-001`:** Ollama reachable, Colibri .77 NOT VERIFIED, adapter missing; research closed partial.
- **`CODEX-WUA-DOC-WEB19-REPAIR-001`:** six docs, WEB19 bounded PASS.
- **`ASTRA-DOC-CONTEXT-OPTIMIZATION-001`:** archive preserved, independent cold-start/semantic/graph OPEN.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB22 / 04.11.2026 — `CODEX-WUA-CHAT-UX-LIVE-FIX-001` + AMENDMENT 01 — BOUNDED PASS / USER GUI ACCEPTED

**Verifier:** ChatGPT WEB22. **Source:** main@2e57cf2d2e59e225ab7c0d5aa7fd7097d15039ef (№501; проверенная публикация; технический пакет до документационного коммита), report `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/report.md`; original task+one amendment fully recoverable from exact script snapshot. **Verdict:** **PASS / BOUNDED SOURCE + AUTHOR EVIDENCE** for inspected UI/adapter deltas, test cases, report and slot evidence. Original RED preserved; author 158 JS PASS, 166 Python PASS/5 SKIP, mandatory HTTP/UI 51 PASS, all author runs exit 0; reviewer independent Node/Python/full CI/GUI **NOT RUN**. User on Windows confirmed creation of Workspace and first/following chats (**USER GUI ACCEPTED** for this happy path; earlier user rename/save acknowledged in amendment). Verified source logic: no registration/read auto-init; first chat with exact consent through shared core; reparse/orphan/foreign refusals in source+author tests. Full safety negative runtime, Windows accessibility and crash-atomicity are not asserted.

**SLOT:** author `finish --chat-amendment` ROTATED exit0, snapshot and one amendment readback; B1 WAITING, B1.1 exact TASK; БЛОКИ1/1.1 здесь не менялись. **OPEN:** `FOLLOWUP-WUA-CHAT-UX-INDEP-RUNTIME-001`, `FOLLOWUP-WUA-CHAT-UX-CRASH-001`, `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001`, previously UI GUI/independent, P9/Run Store, staging/Tk; intermittent WinError 10053 remains inconclusive. Stage3/inference/paid/live/MCP FROZEN. Review `reports/CHATGPT-WEB22-CODEX-UX-LIVE-FIX-REVIEW-20261104/review.md`, №05 `REG-WEB22-CODEX-UX-LIVE-FIX-20261104`, №06 `EVT-WEB22-CODEX-UX-LIVE-FIX-20261104`; DOC CLOSED IN GPT / USER MERGE PENDING.

## Предыдущее — WEB21 / 04.11.2026 — CODEX-WUA-CHAT-UI-INTEGRATION-001

BOUNDED SOURCE+AUTHOR EVIDENCE PASS, 13/13 manifest, author 66 JS/57 Python; independent runtime/Tk/CI NOT RUN. Report `reports/CHATGPT-WEB21-CODEX-UI-INTEGRATION-REVIEW-20261104/review.md`, №06 `EVT-WEB21-CODEX-UI-INTEGRATION-20261104`. Original full verifier verdict archived in №06/№001.

## Предыдущее — LLM15 / 02.11.2026 — CODEX-WUA-LOCAL-LLM-DISCOVERY-001

Bounded diagnostic PASS / TASK PARTIAL / DOC CLOSED; independently checked 28/28 published package, Colibri remote unknown; details №001 Codex, №05 `REG-LLM15-LOCAL-LLM-DISCOVERY-20261102`, №06.

---

**Статус 04.11.2026 / WEB22:** `CODEX-WUA-CHAT-UX-LIVE-FIX-001` bounded accepted, user GUI first/next Chat ACCEPTED; full independent runtime NOT RUN. БЛОК 1 ожидает новую задачу, БЛОК 1.1 содержит последнюю UX TASK с одним AMENDMENT. Новая задача — только по USER GO. Stage3/live/paid HOLD.
