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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001` · перенесено 2026-11-04 · SHA-256 копии `b6399d2c9e353ac91dfbfbc69e79b1bd8a95bd0e39ecaba9e8a830429e21c0bb` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/handoff_task.md` · отчёт `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/report.md` · HISTORY ID `H-CODEX-000012` · запись `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/task_record.json`

**TASK ID:** `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001`

**Название:** Web Alarm Ultra — защита Run Store v2 перед реализацией Stage 3

**Исполнитель:** Codex 007  
**Координатор / независимый verifier:** ChatGPT WEB 23  
**Приоритет:** HIGH  
**Тип:** адресное исправление подтверждённых блокеров

## 1. Цель

Устранить две воспроизводимые проблемы общего Run Store v2, препятствующие безопасной реализации Stage 3 Ultra Chat.

Основание: `CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`, опубликованные отрицательные оракулы и открытые FOLLOWUP:

- `FOLLOWUP-WUA-P9-AUDIT-PATH-001`
- `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001`

Эта задача не реализует Turn, отправку сообщений или интеграцию провайдеров.

## 2. Разрешённый write-scope

- `run_store.py`
- `test_run_store_v2.py`
- `test_web_alarm_ultra_chat_turn.py`
- `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/`

Другие исходники, включая `context_storage.py`, `audit_storage.py`, Web UI, server, provider transport и модельные реестры, — READ-ONLY. При необходимости расширения scope сначала вернуть обоснование координатору.

Перед началом проверить №40 и отсутствие параллельного владельца записи в общий Run Store.

## 3. Проблема A — безопасность audit-path

Подтверждено, что Windows junction в `.ultra/audit` может перенаправлять запись `index.json` и `summary.json` за пределы синтетического Workspace.

Требуется:

1. Безопасно проверять корень аудита и необходимые вложенные пути перед операциями записи.
2. Переиспользовать существующие механизмы безопасного хранения и блокировок, не создавать независимую параллельную систему.
3. При обнаружении junction/symlink/reparse-point обеспечивать явный безопасный отказ.
4. Проверить обычную запись, перезапуск, негативные подмены путей и неизменность внешнего синтетического каталога.
5. Не заявлять абсолютную защиту от TOCTOU без соответствующего доказательства.

## 4. Проблема B — единственный writer одного RUN

Подтверждено: два Python-процесса могут одновременно записать событие одного RUN с одинаковым `sequence=1`.

Требуется:

1. Обеспечить межпроцессную синхронизацию операций записи конкретного RUN либо явно контролируемый безопасный отказ.
2. Гарантировать уникальную последовательность подтверждённых записей.
3. Сохранить согласованность `records.idx.jsonl`, stream-файлов, offsets, lengths и SHA-256.
4. Проверить повторные запуски, ошибки записи, завершение процесса, восстановление и конкурентную нагрузку.
5. Не маскировать частично завершённую операцию как полностью успешную.

## 5. Обязательная стратегия тестирования

Сначала воспроизвести опубликованные RED-оракулы на изолированном синтетическом Workspace. Затем внести минимальные исправления.

После реализации выполнить адресные Windows-проверки, существующие P9/Run Store тесты, Stage 3 prerequisite-оракулы и применимую регрессию.

Исходные FAIL сохранять. Отчёт должен содержать команды, версии Python, exit codes, PASS/FAIL/SKIP, повторяемость и точные ограничения.

Запрещены реальные провайдерные запросы, изменение живых Workspace, переключение пользовательского launcher и побочные изменения безопасности ОС.

## 6. Приёмочные критерии

- Негативный audit-path oracle не создаёт внешних файлов.
- Два конкурентных writer не создают одинаковых подтверждённых последовательностей.
- Нормальная запись, чтение и восстановление RUN работают.
- Повреждения/частичные операции диагностируются, а не скрываются.
- Существующие функции Run Store и P9 не деградировали.
- Исходники, тесты, отчёт и evidence доступны по точным адресам.

## 7. Документация и сдача

Читать адресно актуальные №08, №18 (применимые правила), №37 (Stage 3), №40, указанные FOLLOWUP и действующие профильные тестовые контракты. Не загружать исторические архивы.

Сохранить полный итоговый пакет с `report.md`, `manifest.json`, evidence, исходными RED и результатами после исправления.

После готового пакета выполнить штатный `tools/task_slot_rotate.py finish`, сохранить HISTORY ID, точный протокол и readback. Авторский PASS не является независимой приёмкой.

Git/GitHub локальному исполнителю без отдельного пользовательского разрешения запрещены. Публикация осуществляется пользователем.

**После задачи Stage 3 остаётся HOLD до независимой приёмки исправления и отдельного USER GO.**
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Постоянный архив — №001 Codex и снимки reports/<TASK-ID>/.

- **04.11 / `CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`:** diagnostic PARTIAL / Stage3 blocked by Run Store; author Windows 2 RED/1 PASS, JS 158 PASS, Python 166 PASS/5 SKIP, P9 21 PASS. WEB22 bounded source/evidence diagnostic PASS, independent runtime NOT RUN; script ROTATED; №05 REG-WEB22-CODEX-S3-PREREQ-20261104.
- **04.11 / `CODEX-WUA-CHAT-UX-LIVE-FIX-001` AMENDMENT 01:** WEB22 bounded source/evidence PASS, user GUI first/next chat ACCEPTED; 158 JS / 166 Python PASS/5 SKIP; independent runtime NOT RUN.
- **04.11 / `CODEX-WUA-CHAT-UI-INTEGRATION-001`:** WEB21 bounded PASS, 66 JS/57 Python author; runtime NOT RUN.
- **02.11 / `CODEX-WUA-LOCAL-LLM-DISCOVERY-001`:** diagnostic PARTIAL, Colibri unavailable/unverified, adapter missing.
- **01.11 / `CODEX-WUA-DOC-WEB19-REPAIR-001`:** bounded document PASS / DOC CLOSED.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **`CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`:** Stage3 not implemented due to shared Run Store blockers; author raw RED audit junction and duplicate [1,1] RUN event sequences; no product source changes, negative test and evidence only; script ROTATED/exit0 after user TASK ID format correction; bounded verifier PASS for diagnostic; independent runtime NOT RUN.
- **`CODEX-WUA-CHAT-UX-LIVE-FIX-001`:** Workspace/chat UX fixes and first-Chat consent; user Windows GUI accepted, other negative GUI gates OPEN.
- **`CODEX-WUA-CHAT-UI-INTEGRATION-001`:** Workspace registration UI and catalog refresh, bounded accepted.
- **`CODEX-WUA-LOCAL-LLM-DISCOVERY-001`:** local LLM investigation PARTIAL; Colibri not verified.
- **`CODEX-WUA-DOC-WEB19-REPAIR-001`:** bounded doc repairs PASS.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB22 / 04.11.2026 — CODEX-WUA-CHAT-S3-TURN-RECOVERY-001: BOUNDED DIAGNOSTIC PASS, PRODUCT STAGE3 PARTIAL

**Source:** main@5088d307defdf3b6b92d4f119c45fc29863a6bb5; factual report reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/report.md, manifest, negative test and raw evidence. Verifier ChatGPT WEB22 examined published run_store.py against saved source, two RED oracles/audit/sequence JSON and author logs. Author prerequisite 1 PASS / 2 intentionally RED FAIL, JS 158 PASS, Python 166 PASS/5 SKIP, P9 21 PASS. **Verdict:** PASS / BOUNDED SOURCE+AUTHOR-EVIDENCE for identified defects and safe stop, **NOT Stage3 implementation acceptance**. Independent Windows/Node/Python/CI and physical user-file integrity NOT RUN. Product source unchanged; Stage3 Turn/HTTP/TEST mock NOT IMPLEMENTED.

**SLOT:** user corrected TASK ID declaration after original NO_TASK_ID exit3, normal finish script ROTATED exit0; 383-line task snapshot reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/handoff_task.md, receipt reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/slot_finish_1793806731834391500.json; B1 WAITING, B1.1 exact Stage3 assignment, previous UX task snapshot still published. No manual rotation. **OPEN:** P9 audit junction, same RUN writer duplicate sequence, independent P9 runtime, Stage3 implementation, other pre-existing UX/storage issues. User GO required to repair Run Store with its own writer and path safety, then independently accept, then separately resume Stage3; Stage4/live/paid/Colibri/Blueprint/MCP not assigned. Review reports/CHATGPT-WEB22-CODEX-S3-PREREQ-REVIEW-20261104/review.md, №05 REG-WEB22-CODEX-S3-PREREQ-20261104, №06 EVT-WEB22-CODEX-S3-PREREQ-20261104. DOC CLOSED IN GPT / USER MERGE PENDING.

## WEB22 / 04.11.2026 — `CODEX-WUA-CHAT-UX-LIVE-FIX-001` + AMENDMENT 01 — BOUNDED PASS / USER GUI ACCEPTED

**Verifier:** ChatGPT WEB22. **Source:** main@2e57cf2d2e59e225ab7c0d5aa7fd7097d15039ef (№501; проверенная публикация; технический пакет до документационного коммита), report `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/report.md`; original task+one amendment fully recoverable from exact script snapshot. **Verdict:** **PASS / BOUNDED SOURCE + AUTHOR EVIDENCE** for inspected UI/adapter deltas, test cases, report and slot evidence. Original RED preserved; author 158 JS PASS, 166 Python PASS/5 SKIP, mandatory HTTP/UI 51 PASS, all author runs exit 0; reviewer independent Node/Python/full CI/GUI **NOT RUN**. User on Windows confirmed creation of Workspace and first/following chats (**USER GUI ACCEPTED** for this happy path; earlier user rename/save acknowledged in amendment). Verified source logic: no registration/read auto-init; first chat with exact consent through shared core; reparse/orphan/foreign refusals in source+author tests. Full safety negative runtime, Windows accessibility and crash-atomicity are not asserted.

**SLOT:** author `finish --chat-amendment` ROTATED exit0, snapshot and one amendment readback; B1 WAITING, B1.1 exact TASK; БЛОКИ1/1.1 здесь не менялись. **OPEN:** `FOLLOWUP-WUA-CHAT-UX-INDEP-RUNTIME-001`, `FOLLOWUP-WUA-CHAT-UX-CRASH-001`, `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001`, previously UI GUI/independent, P9/Run Store, staging/Tk; intermittent WinError 10053 remains inconclusive. Stage3/inference/paid/live/MCP FROZEN. Review `reports/CHATGPT-WEB22-CODEX-UX-LIVE-FIX-REVIEW-20261104/review.md`, №05 `REG-WEB22-CODEX-UX-LIVE-FIX-20261104`, №06 `EVT-WEB22-CODEX-UX-LIVE-FIX-20261104`; DOC CLOSED IN GPT / USER MERGE PENDING.

## Предыдущее — WEB21 / 04.11.2026 — CODEX-WUA-CHAT-UI-INTEGRATION-001

BOUNDED SOURCE+AUTHOR EVIDENCE PASS, 13/13 manifest, author 66 JS/57 Python; independent runtime/Tk/CI NOT RUN. Report `reports/CHATGPT-WEB21-CODEX-UI-INTEGRATION-REVIEW-20261104/review.md`, №06 `EVT-WEB21-CODEX-UI-INTEGRATION-20261104`. Original full verifier verdict archived in №06/№001.

## Предыдущее — LLM15 / 02.11.2026 — CODEX-WUA-LOCAL-LLM-DISCOVERY-001

Bounded diagnostic PASS / TASK PARTIAL / DOC CLOSED; independently checked 28/28 published package, Colibri remote unknown; details №001 Codex, №05 `REG-LLM15-LOCAL-LLM-DISCOVERY-20261102`, №06.

---

**Статус 04.11.2026 / WEB22:** CODEX-WUA-CHAT-S3-TURN-RECOVERY-001 diagnostic PARTIAL, Stage3 NOT IMPLEMENTED; B1 WAITING, B1.1 latest Stage3 task, old UX archived. Next Run Store repair only by USER GO; independent full runtime NOT RUN; Stage4/live/paid/MCP HOLD.
