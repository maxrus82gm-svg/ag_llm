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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001` · перенесено 2026-11-10 · SHA-256 копии `e70835a08e79dee0cfbb91d9656c5428e7c2f0eecfbf4b0d620e201f2447cfc2` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/report.md` · HISTORY ID `H-CODEX-000030` · запись `reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/task_record.json`

# CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001

**TASK ID:** `CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001`  
**Исполнитель:** Codex 007  
**Тип:** MICRO / READ-ONLY PREFLIGHT + optional one OFFLINE negative test  
**База:** `main@3acd5b240ea856496bcb446fdfecaa165de0c172` (№571)  
**Режим:** STRICT OFFLINE / NO LIVE / NO PAID

## 1. Цель

Подготовить небольшую часть будущего S3b: определить точное место обязательной проверки перед физической отправкой LLM-запроса.

**Не реализовывать весь S3b. Не создавать новое ядро, новый транспорт или новый бюджетный механизм.**

Основная стратегия — перенос существующего Ultra Core в Web Alarm Ultra с максимальным переиспользованием готового кода.

## 2. P0 — обязательно

Адресно прочитать №08, №000, актуальные №34 и №40, №37 §3а (шаг 3), №20 §5а, относящиеся пункты №05: `S3B-S3C-S9`, `STATIC-DYNAMIC-COVERAGE`, `ORDINARY-CHAT-POLICY`.

Изучить существующие файлы:

- `web_alarm/ordinary_chat_bridge.py`
- `ordinary_chat_service.py`
- `web_alarm/turn_service.py`
- `ultra_budget_policy.py`
- `ultra_budget_ledger.py`

Установить, где уже выполняются подготовка запроса, фиксация Turn, проверка транспорта и сохранение неизвестного исхода.

Составить небольшую схему:

`Prepared request → Pre-send guard → Allow/Deny → Transport`

Указать точные существующие функции, которые следует переиспользовать, и недостающие связи.

Проверить, что TEST нельзя переключить в REAL простой конфигурацией или подстановкой стороннего транспорта.

## 3. P1 — только если хватает лимита

Найти существующий отрицательный тест запрета неподтверждённой отправки.

Если подходящий тест уже существует — указать его имя и результат запуска. **Не дублировать.**

Если теста нет — разрешается добавить не более одного небольшого OFFLINE-теста в `test_web_alarm_ordinary_core_bridge.py`, проверяющего, что неподтверждённый транспорт не вызывается и не создаётся успешный Turn.

Production-код не изменять.

## 4. Временная резервная копия

Перед изменением любого существующего файла:

1. Создать уникальную временную папку вне репозитория в системном TEMP.
2. Скопировать только файлы, которые необходимо изменить.
3. Зафиксировать пути и исходные SHA-256.
4. Не копировать секреты, пользовательские Workspace и настоящие чаты.

Резервную копию **сохранить до независимой приёмки**.

После закрытия задачи удалить только созданную для неё временную папку и проверить очистку. Если работа прервана — указать `CLEANUP PENDING` и точный путь.

Если изменений существующих файлов не было, указать `BACKUP NOT REQUIRED / READ ONLY`.

## 5. Ограничения

Не менять STANDARD, Tkinter, Blueprint, Colibri, OAuth, реальные адаптеры провайдеров, настройки ОС и общие нормативные документы.

Запрещены реальные LLM-запросы, платные API, включение REAL, полный CI и самостоятельные Git commit/push.

**S3b целиком остаётся OPEN.**

При нехватке лимита не расширять работу: сохранить честный `PARTIAL`, выполненную карту и незакрытые вопросы.

## 6. Результат

Создать:

`reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/report.md`

Зафиксировать карту существующих механизмов, найденный pre-send стык, проведённые проверки с counts, изменённые файлы либо READ ONLY, статус TEMP, ограничения, NOT RUN и следующий минимальный шаг.

После завершения отчёта выполнить штатную сдачу `tools/task_slot_rotate.py finish`. Сообщить HISTORY ID и фактический статус.

**Критерий приёмки:** понятен безопасный следующий шаг S3b без дублирования Ultra Core. Реальный GigaChat остаётся выключенным.
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Постоянный архив — №001 Codex и адресные `reports/<TASK-ID>/task_record.json`.

- **08.11 / H-CODEX-000024 / `CODEX-RT002-B2-S1-INVENTORY-RECON-001`:** independent Windows S1 69 PASS + 23 extra PASS/18 mutations; separate S2 72 PASS/1 FAIL; task PARTIAL, S1 bounded PASS, S3b HOLD.
- **08.11 / H-CODEX-000023 / `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`:** S3a ledger 35/35 author PASS, Run Store 51; independent S3a runtime NOT RUN, privacy/fencing OPEN.
- **07.11 / H-CODEX-000022 / `CODEX-WUA-S5-TURN-UX-RECOVERY-001`:** bounded Windows GUI smoke PASS; RAW cancel, Tcl, 480px residual OPEN.
- **07.11 / H-CODEX-000021 / `CODEX-WUA-S5-TURN-CHECK-DIAG-001`:** Turn diagnostic PARTIAL, historical cancellation RAW cause OPEN.
- **07.11 / H-CODEX-000020 / `CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001`:** Stage5 fake UI+Turn, independent Windows 387 PASS, live NOT RUN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H24 S1:** changed only `test_rt002_s1_routes.py`; initial 67/69 RED, author+independent 69/69 PASS, 23/23 guarded negative/fake checks PASS, full 18 source mutations detected. Independent S2 exact 72/73 FAIL: old isolation test includes OFFLINE S3a ledger. No real provider / full repo CI.
- **H23 S3a:** Offline durable ledger and 35 authored PASS; independent runtime gate still OPEN; historical adoption, privacy/RAW, durability/fencing require separate actions.
- **H22 Stage5:** Windows user F5, Turn check and two independent Chat histories bounded PASS, residual OPEN.
- **H21 Stage5:** Turn check diagnosis PARTIAL; original canceled RAW issue unproven.
- **H20 Stage5:** independent Windows fake UI 387 PASS, no real GigaChat or clean portability proof.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB28 / 10.11.2026 — H-CODEX-000029 — per-chat usage/settings BOUNDED OFFLINE + USER GUI PASS

`CODEX-WUA-CHAT-PERCHAT-USAGE-SETTINGS-001`, main №570 `0aa3846e`; авторские 8 Python + 57 JS PASS, TEST CMD PASS, ранее независимые Windows 65/65 PASS по сохранённому контексту. Пользовательский GUI/F5: 2 Workspace/4 чата; `01_01` сохраняет 150000/15000, другие — 250000/10000. TEST `UNKNOWN` корректен при отсутствующем fake usage. **VERDICT: DOC CLOSED / P0+P1 BOUNDED OFFLINE PASS**, без реального provider cap и live. Не подтверждены реальный usage/20k-кнопка отдельным GUI тестом, broad CI/clean Windows. S3b/Stage7/paid HOLD. Review: `reports/CHATGPT-WEB28-H29-PERCHAT-REVIEW-20261110/review.md`. БЛОК 1 и БЛОК 1.1 не изменять.


## WEB25 / 08.11.2026 — H-CODEX-000024 — S1 inventory OFFLINE independent PASS / product PARTIAL

Source main@`a455d97f` №542, Codex H24/finish ROTATED exit0, B1 WAITING and B1.1 H24 untouched. Independent Remote Desktop Windows SHA matched exact `test_rt002_s1_routes.py`; guarded **S1 69/69 PASS** (exit0 guard0) and **23/23 extra PASS**, 18 in-memory mutation cases. Independent **S2 72/73 (1 FAIL)** due old `test_no_production_module_imports_the_policy_yet` discovering intentionally standalone `ultra_budget_ledger.py`; source-level mismatch, not evidence of live HTTP dispatch. S3a independent test NOT RUN; three author weakening controls not independently replayed. **Verdict S1 TARGETED INDEPENDENT OFFLINE PASS; H24 OVERALL PARTIAL**, S2 remedy separately authorized; S3b/Stage6/Stage7 live HOLD. Report `reports/CHATGPT-WEB25-CODEX-RT002-S1-REVIEW-20261108/review.md`.

## WEB25 / 08.11.2026 — H-CODEX-000023 — RT-002/B2 S3a OFFLINE PARTIAL

Source main@`53d7ce91` №539; Codex finish ROTATED exit0, БЛОК1 WAITING, БЛОК1.1 H23 без вмешательства verifier. Новые два исходника + author evidence: S3a 35 PASS, Run Store 51, S2 73, mutants 3/3 red; S1 67 PASS / **2 FAIL** source inventory. WEB25 проверил 16 источников включая пять CRLF→LF Git normalizations, source state machine, lock and error paths; **NO independent S3a runtime**. **Verdict: PARTIAL / BOUNDED SOURCE+AUTHOR EVIDENCE**, не independent S3a acceptance или S3b readiness. Ordinary Chat policy, historical adoption, RAW wire retention, 4096-events cap, power-loss/fencing и S1 repair OPEN. Review `reports/CHATGPT-WEB25-CODEX-RT002-S3A-REVIEW-20261108/review.md`. Next только отдельная S1 reconcile/independent S3a gate по USER GO; live/paid/Colibri/MCP HOLD.

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
