# Рабочая карточка исполнителя — Codex 007

**Назначение:** персональная TASK и factual результаты Codex 007. Правила актуализированы 27.10.2026 по прямому поручению пользователя Astra/Codex о документационных каркасах. БЛОКИ 2–4 ниже содержат исторические результаты на свои даты. БЛОК 1 освобождён 01.11 по USER GO; исходная TASK Astra дословно сохранена в №001 и `reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/handoff_task.md`. Старый verdict не даёт новую задачу.

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

**Скрипт и маркеры слотов (служебное поручение координатора 2026-10-29, внедрено Claude 008 в `CLAUDE-DOC-TASK-SLOT-ROTATION-001`; канон — №18 → DOC-BLOCK1-SLOT-01@1):**
- Перенос БЛОК 1 → БЛОК 1.1 выполнять только скриптом `tools/task_slot_rotate.py`, без ручного копирования и пересказа. Порядок: `python -B tools/task_slot_rotate.py check --card "Документация/000_Задачи Codex.md"` → `rotate --card "Документация/000_Задачи Codex.md" --task-id <TASK-ID> --no-chat-amendment` (или `--chat-amendment <файл>` с точным текстом каждой принятой чат-поправки) — пробный прогон без записи → тот же вызов с `--apply`. Запускать только после всех обязательных тестов и сохранения финальных `report.md` + `manifest.json`; если пакет лежит не в `reports/<TASK-ID>/`, указать его через `--report-dir`.
- Результат `ROTATED` и JSON-протокол (TASK ID, SHA-256 до и после, copied exact, previous slot, статус `SUBMITTED / REVIEW PENDING`) приложить к отчёту TASK; снимок постановки скрипт сам сохраняет в `<папка отчёта>/handoff_task.md`. Код выхода 3 = `NO ROTATE`: карточка не изменена, ничего не исправлять вручную, причину передать координатору.
- Скрипт сам проверяет маркеры и заголовки слотов, единственный TASK ID в БЛОКЕ 1 и его совпадение с `--task-id`, поправки к чужой TASK, двойную вставку и вставку целой карточки, текст вне маркеров, готовность отчётного пакета, сохранность прежнего БЛОКА 1.1 в №001 (или в опубликованном снимке: `--previous-archive` + `--previous-archive-ref`) и одновременную правку карточки.
- **Маркеры постоянные: не удалять и не копировать.** БЛОКИ 1 и 1.1 ограничены строками-заголовками `###### ▼ НАЧАЛО …` и `###### ▲ КОНЕЦ …`. Пользователь вставляет новую задачу только между маркерами БЛОКА 1 вместо строки `**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**` и может проверить вставку командой `check`. БЛОК 1.1 заполняет только скрипт. Полное служебное имя маркера в тексте карточки не писать: скрипт сочтёт такую строку повреждённым маркером.

**Канон сопровождения:** №18 → DOC-CONTEXT-OPS-01, DOC-TASK-CLOSEOUT-OWNER-01, DOC-LOCAL-REPORT-HANDOFF-01, DOC-HISTORY-ACCESS-01, DOC-VERIFIER-BLOCK4-01@2 и DOC-TEST-LIFECYCLE-01. Формы — №07. Новый координационный порядок не меняет технические статусы, B2/WA4-R/EVM/live/paid/MCP freeze и права предыдущих TASK.

# Задачи Codex

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

## Правила

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

[[000_Задачи для агента]]

[[001_История выполненных задач Codex]]

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN
**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**
###### ▲ КОНЕЦ ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:END

---

# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА

###### ▼ НАЧАЛО КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:BEGIN
**НЕ ЗАПОЛНЕН — ПЕРВЫЙ ПЕРЕНОС ЕЩЁ НЕ ВЫПОЛНЕН.** После первого безопасного переноса здесь хранится ровно одна последняя дословная постановка из БЛОКА 1 с TASK ID и меткой `SUBMITTED / REVIEW PENDING`. Это не авторский отчёт и не решение о приёмке. Предыдущая запись заменяется только после подтверждённого постоянного архивирования.
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

**Исторический срез до 27.10.2026:** текущая ротация Astra отражена в №001/05/06; нижеприведённый список не обновлялся этой административной правкой.

Полный архив — [[001_История выполненных задач Codex]].

- **2026-10-26 / ASTRA-WUA-37-ROADMAP-REVISION-001** — документ №37, 0–7, H01–H23, R01–R11; independent bounded DOCUMENT PASS, 9/9 artifact hashes; программа ожидает USER PLAN APPROVAL.
- **2026-10-26 / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001** — rev2 Astra after Sol 6.1 rev1; 30/30 published source pins SHA/size independently checked at №436, R2-01…R2-08 source/reasoning review. **WEB_14 PASS / BOUNDED ARCHITECTURAL SOURCE REVIEW**, Windows/live NOT RUN; roadmap awaits user approval.
- **2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — admission policy inside existing broker/security pipeline; Codex 52/52 offline, 51/51 regression (19 overlap), 7/7 mutants, WEB_12 independent 53/53 manifest; **PASS / BOUNDED OFFLINE ACCEPTED**, native/WFP/Chat NOT VERIFIED.
- **2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — source-only exact sing dependency; Codex 51/51, WEB_12 87/87, six upstream files and 33 locators. **TERMINAL PARTIAL**, native blocked.
- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — source-only sing-box v1.13.4, defaults DIRECT/DNS/UoT; WEB_11 bounded source accepted, native not run.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **ASTRA-WUA-37-ROADMAP-REVISION-001** — `main@d15d026bf17c1184a004f8891186c0ea02f8887e`, №37 SHA256 `dd2520691cbddbe68157775b42c0373fa3a4009de4b93f008f60ceb180e1df45`, manifest `5cf52fb16438f59f798b633ea0a3f4d8a8456d892b7772e71d0408477b80ed34`, independent 9/9; авторские 21/21 не перезапускались, no runtime/CI/live; B2 V-13 unresolved.
- **ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001** — architecture rev2 `Документация/Дополнительная аналитика Астры.md`, `main@900f107fc89b3ca9e80e4f66b34ab0c9f4b32c30`, 137301 bytes, SHA256 `7cf81d95be92924dd62a6eb1e623882dd2fa69359c9e31032c19a35ee185d3f5`; independently source 30/30 pinned №436 and eight R2 corrections accepted; no runtime/CI/API. WUA-2A **NOT ASSIGNED**; frozen B1 archived verbatim in Codex 001.
- **CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — new `strict_preflight`, separated structural vs strict policy statuses; controller-owned canonical/source pins, opaque auth refs, CONNECT-only exact destination and deny DIRECT/fallback/secondary/DNS/UDP/UoT/IPv6/merge/reload. Codex 52/52 offline, 51/51 overlapping compatible tests, 7 mutants caught, preserved RED 19/21, WEB_12 53/53 manifest SHA. **OFFLINE PASS only**, upstream credentials in 407/error logs still SECURITY BLOCKER. Real C/B SID/NPFS, WFP, secret-store and ChatGPT E2E NOT VERIFIED. `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/report.md`.
- **CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — WEB_12 terminal bounded source-only PARTIAL, 87/87 files and 6/6 upstream SHA/33 locators; no native/real egress. `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/report.md`.
- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — WEB_11 bounded 30/30 Codex, sing-box defaults DIRECT/DNS/UoT/other conditional route risks. `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

**Verifier:** WEB_14 / ChatGPT; Codex READ-ONLY. Полный архив №001 и журнал №06.

## 1. Последний вердикт — WEB_14 / 2026-10-26 / ASTRA-WUA-37-ROADMAP-REVISION-001

**PASS / INDEPENDENT DOCUMENT & BOUNDED ARCHITECTURAL REVIEW.** Астра / Codex, результат `main@d15d026bf17c1184a004f8891186c0ea02f8887e`: №37 переработан в программу из восьми этапов 0–7, 23 изменения истории H01–H23 и 11 групп рекомендаций R01–R11. **WEB_14 independent PASS / DOCUMENT & BOUNDED ARCHITECTURAL REVIEW.** SHA256 №37 `dd2520691cbddbe68157775b42c0373fa3a4009de4b93f008f60ceb180e1df45` (71042 байта), manifest CRLF `5cf52fb16438f59f798b633ea0a3f4d8a8456d892b7772e71d0408477b80ed34`. Независимо сверены 9/9 артефактов по SHA256/размерам (четыре CRLF восстановлены), исходный №37 с прежней ревизией, кандидат с опубликованным текстом; без блокирующих противоречий в общем Python-ядре, RAW/Turn/RUN/TASK, бюджете, полномочиях Web Alarm и WA4-R. Авторские 21/21 документных проверок независимо не запускались. Windows/UI/runtime/live/paid/CI NOT RUN. №37 остаётся **ПРОГРАММА-КАНДИДАТ / USER PLAN APPROVAL PENDING**, отложенный B2 V-13 Ordinary Chat требует отдельного решения пользователя, исторический RT-002 и MCP freeze №39 не изменены.

**Не является:** USER PLAN APPROVAL, S3a/S3b implementation PASS, EVM Windows/visual PASS, разрешением paid GigaChat, изменением V-13 или запуском первого этапа. Новую TASK пользователь не назначал.

## 2. Предыдущий — WEB_14 / 2026-10-26 / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001

**PASS / BOUNDED ARCHITECTURAL SOURCE REVIEW**, source pins 30/30 at №436 and eight R2 corrections. Нет Windows/production/live.

## 3. Предыдущий — WEB_12 / 2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001

**PASS / BOUNDED OFFLINE SOURCE & EVIDENCE**, native Windows/WFP/ChatGPT Desktop E2E not verified.

---

**Статус 01.11.2026:** БЛОК 1 ожидает нового поручения; №37 утверждён 27.10, но Stage3 не запускать. Astra сохранена в архиве, независимая полная приёмка миграции всё ещё OPEN.
