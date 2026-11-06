# Рабочая карточка исполнителя — Codex 007

**USER GO 04.11.2026 / история по ID:** порядок общего №000 и нового №18 имеет приоритет над старыми указаниями о полном №001. После итогового пакета исполнитель или пользователь запускает штатный `finish`: сохранение источников и HISTORY ID → проверка → перенос БЛОК 1 в 1.1. Номер и адрес записи видны в 1.1/протоколе; повтор не создаёт новый номер. Веб-координатор проверяет запись по этому ID и ведёт короткие индексы №001/05. Полные постановки в №001 больше не вставлять; последние десять строк не заменяют очередь всех OPEN. Для старой 1.1 без H-номера использовать точный TASK ID и протокол, не переписывать постановку.

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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001` · перенесено 2026-11-06 · SHA-256 копии `b0159a94acd82e6c3cd9d45c368961bb34529694e89d8ce320375c83c5827296` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/report.md` · HISTORY ID `H-CODEX-000019` · запись `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/task_record.json`

**TASK ID:** `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001`

# Web Alarm Ultra — Stage4: защита от ложного SUCCESS после внешней отмены

**Исполнитель:** Codex 007  
**Координатор и независимый verifier:** ChatGPT WEB24  
**Приоритет:** HIGH  
**Программа:** №37, этап 4  
**ARCH CLASS:** Ultra Chat / Ordinary Chat / Cancellation Safety  
**FOLLOWUP:** `FOLLOWUP-WUA-S4-CANCEL-SUPPRESSED-001`

## 1. Цель

Устранить обнаруженный независимым Windows CI дефект `ordinary_chat_service.py::execute_request()`.

**Воспроизведение:** после начала отправки вызывается `task.cancel()`. Тестовый транспорт перехватывает `asyncio.CancelledError` и возвращает валидный ответ с usage. Сервис ошибочно возвращает `Outcome.COMPLETED` вместо `Outcome.UNKNOWN_AFTER_START`.

**Доказательства:**
- GitHub Actions `42185342094`, job `127784232360`.
- GitHub Actions `42185590677`, job `127785025580`.
- Независимый отрицательный тест: `reports/CHATGPT-WEB24-CODEX-S4-DEADLINE-REVIEW-20261106/test_independent_deadline.py`.
- Оба независимых запуска: 1 FAIL этого сценария.
- При этом исправленный дедлайн H18 успешно выдержал 120 повторных проверок.

## 2. Разрешённый WRITE-scope

- `ordinary_chat_service.py` — минимальное исправление.
- `test_ordinary_chat_service.py` — новые отрицательные и регрессионные тесты.
- `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/` — отчёт, manifest, evidence.
- БЛОК 1/1.1 — исключительно штатным `finish` при сдаче.

Остальные исходники, в том числе `web_alarm/turn_service.py`, `run_store.py`, HTTP, Tkinter, UI, B2 и model registry — READ-ONLY.

## 3. Требуемый контракт

После внешней отмены, даже когда адаптер подавил `CancelledError` и вернул ответ:

- результат — консервативный `UNKNOWN_AFTER_START`;
- `Execution.RESPONSE_RECEIVED`, если ответ действительно получен;
- успешный текст ответа не публикуется;
- достоверный известный usage сохраняется;
- неизвестная стоимость не превращается в ноль;
- повторная физическая отправка не выполняется.

Не нарушить исправление H18: сработавший deadline всегда остаётся истёкшим, даже при неизменном тике часов Windows.

Обычный своевременный ответ без отмены остаётся `COMPLETED`. Отмена до отправки не вызывает транспорт. Исходный request/model binding сохраняется.

## 4. Проверка

Сначала воспроизвести RED на исходной ревизии, затем добиться GREEN на исправлении.

Обязательны адресные проверки внешней отмены с подавлением `CancelledError`, дедлайна с подавленной отменой, своевременного успеха, pre-send cancel, одного transport call, usage, отсутствия повторной отправки и сохранения UNKNOWN в Stage4B.

Выполнить всю релевантную регрессию: S4A, S4B, Stage3, RAW storage, Run Store. Сохранить отрицательные результаты, точные команды, exit codes, версии и SHA.

Работать только на синтетических Workspace. Реальные GigaChat, OAuth, Colibri, платные API и пользовательская история запрещены. Запускатель после тестов должен оставаться STANDARD.

## 5. Завершение

Если исправление выходит за разрешённый scope — остановиться с `PARTIAL / BLOCKED`, не менять чужие файлы.

Если пакет готов — сохранить полный отчёт, manifest, evidence и выполнить штатный `tools/task_slot_rotate.py finish` для данного TASK ID.

Codex не использует Git/GitHub без отдельного разрешения. После сдачи пользователь публикует результат, WEB24 независимо проверяет GitHub-исходники и Windows CI.

**Критерий приёмки:** внешний cancel не может стать ложным SUCCESS; исправленный дедлайн H18 и все соседние инварианты остаются исправными.
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Постоянный архив — №001 Codex и адресные `reports/<TASK-ID>/task_record.json`.

- **04.11 / `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001` / `H-CODEX-000012`:** опубликованное исправление audit path, same-RUN writer и explicit recovery; WEB23 bounded source+author-evidence PASS, independent Windows/CI NOT RUN; author 389 PASS/5 SKIP, Stage3 HOLD.
- **04.11 / `CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`:** diagnostic PARTIAL / прежние Run Store RED, WEB22 bounded diagnostic review.
- **04.11 / `CODEX-WUA-CHAT-UX-LIVE-FIX-001` AMENDMENT 01:** WEB22 bounded source+evidence PASS, user first/next Chat GUI accepted; independent runtime NOT RUN.
- **04.11 / `CODEX-WUA-CHAT-UI-INTEGRATION-001`:** WEB21 bounded UI source/evidence PASS, separate GUI/CI gates OPEN.
- **02.11 / `CODEX-WUA-LOCAL-LLM-DISCOVERY-001`:** bounded diagnostic PARTIAL; Colibri and adapter OPEN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **`CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001`:** native finish ROTATED/exit0, H-CODEX-000012; author RED 1 PASS/2 FAIL → 3 PASS; 62 Run Store + 166 Python + 158 JS PASS / 5 SKIP. WEB23 bounded source/evidence PASS, exact published test `test_run_store_v2.py` has one EOL-only hash delta; independent runtime/CI NOT RUN. Stage3 NOT IMPLEMENTED / HOLD.
- **`CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`:** Stage3 prerequisites diagnostic, authored RED for path/writer now addressed in successor bounded scope, Stage3 Turn still NOT IMPLEMENTED.
- **`CODEX-WUA-CHAT-UX-LIVE-FIX-001`:** first-chat consent/Workspace UX accepted by user for Windows happy path, other negative gates OPEN.
- **`CODEX-WUA-CHAT-UI-INTEGRATION-001`:** registration UI and catalog refresh bounded accepted, GUI/runtime gates OPEN.
- **`CODEX-WUA-LOCAL-LLM-DISCOVERY-001`:** Colibri/adapter unverified and not implemented.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB23 / 05.11.2026 — H-CODEX-000013 — Stage3 TEST PARTIAL

`CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001` published main@a3b44c6, author finish ROTATED (B1 WAITING/B1.1 exact). Independently Windows CI: 30 Turn/HTTP/prerequisites, 53 Run Store, 171 Python, 161 JS PASS at least once; repeated full Python **1/171 FAIL** `WorkspaceBusyError` in legacy two-process writer test, exact isolated replay **5/5 PASS**, still OPEN. **Verdict PARTIAL / TEST functional**, user GUI not yet run; no real LLM/Stage4 GO. Evidence `reports/CHATGPT-WEB23-CODEX-S3-TURN-REVIEW-20261105/review.md`, №05 `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001`, event `EVT-WEB23-CODEX-S3-TURN-REVIEW-20261105`. B1/B1.1 not changed by verifier.


## WEB23 / 04.11.2026 — H-CODEX-000012 — independent Windows CI 56 PASS

Independent GitHub Actions run `41885808568` (https://github.com/maxrus82gm-svg/ag_llm/actions/runs/41885808568), source GPT@e14222fb523acc558e57e31eebd1425829fc8651 (product inherited unchanged from main@e3253b4): **53 Run Store/audit + 3 original Stage3 oracles PASS, 0 FAIL/SKIP**. Verifier inspected decoded runner logs and completed job conclusion SUCCESS; verdict **PASS / TARGETED INDEPENDENT WINDOWS CI**. Full regression/real Workspace/picker NOT RUN; residual FOLLOWUP OPEN, separate Stage3 USER GO required. B1/B1.1 were not edited. Event `EVT-WEB23-RUNSTORE-S3-WINDOWS-CI-20261104` in №06.

## Previous — WEB23 / 04.11.2026 — H-CODEX-000012 — bounded source/author evidence

**Verifier:** ChatGPT WEB23. **Source:** main@e3253b41502ac2d76c61c0faf7a5b660e2cc7eb9, `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/`. Independently inspected source, negative/positive author oracles, logs, manifest, history and finish. **Verdict: PASS / BOUNDED SOURCE + AUTHOR EVIDENCE** for audit-path refusal, writer-lock serialization and explicit recovery; independent Windows/CI/restart runtime **NOT RUN**. Author 389 PASS/5 SKIP; WinError 10053 initial run remains unresolved despite successful retry. One `test_run_store_v2.py` source SHA mismatch traced exactly to single CRLF→LF at line 479 during publication; no semantic change, strict full-manifest SHA PASS not asserted.

**SLOT:** author finish ROTATED exit0, B1 WAITING, B1.1 exact assigned task and H-CODEX-000012; verifier did not alter either slot. **OPEN:** independent P9/Stage3 Windows regression, existing picker, Stage3 Turn not implemented, staging/Tk/portability and other FOLLOWUP. No Stage3/live/paid/Blueprint/Colibri/MCP GO. Full review `reports/CHATGPT-WEB23-CODEX-RUNSTORE-S3-GATE-REVIEW-20261104/review.md`, №06 `EVT-WEB23-RUNSTORE-S3-GATE-REVIEW-20261104`. Proposed GPT doc commit awaiting user merge.

## Previous — WEB22 / 04.11.2026 — Stage3 prerequisite diagnosis

`CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`: source+author-evidence diagnostic PASS, product Stage3 PARTIAL/NOT IMPLEMENTED; original RED 1 PASS/2 FAIL, bounded source review, independent runtime NOT RUN. Permanent review `reports/CHATGPT-WEB22-CODEX-S3-PREREQ-REVIEW-20261104/review.md`, event `EVT-WEB22-CODEX-S3-PREREQ-20261104`.

## Previous — WEB22 / 04.11.2026 — Workspace/Chat UX

`CODEX-WUA-CHAT-UX-LIVE-FIX-001` AMENDMENT 01: source+author-evidence PASS bounded, user accepted Windows GUI first/following chats; full independent runtime/negative GUI NOT RUN. Review `reports/CHATGPT-WEB22-CODEX-UX-LIVE-FIX-REVIEW-20261104/review.md`, event `EVT-WEB22-CODEX-UX-LIVE-FIX-20261104`. Earlier WEB21/LLM15 verdicts remain in exact published `main@e3253b4` card snapshot, their reports and №06; not deleted from history.

---

**CURRENT WEB23:** Run Store repair source+author-evidence bounded PASS; independent pinned Windows/CI NOT RUN. Stage3 Turn NOT IMPLEMENTED; user GO needed. B1 WAITING, B1.1 H-CODEX-000012.
