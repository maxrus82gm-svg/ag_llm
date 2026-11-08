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
**TASK ID:** `CODEX-RT002-B2-S1-INVENTORY-RECON-001`

# Web Alarm Ultra — Stage 6: исправление инвентаризации сетевых маршрутов RT-002/B2 S1

**Исполнитель:** Codex 007  
**Координатор / независимый verifier:** ChatGPT WEB25  
**Приоритет:** HIGH  
**ARCH CLASS:** Ultra Runtime / RT-002 B2 / S1 Route Inventory  
**Режим:** STRICT OFFLINE  
**Тип:** узкая корректирующая задача  
**База:** `main@87edc6c1537722981b5016fa2c33b8bc59cc580c` (№541)

## 1. Основание

В предыдущей задаче `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`, HISTORY `H-CODEX-000023`, создан долговременный бюджетный ledger S3a.

Его авторские проверки:

- S3a: 35 PASS.
- Run Store: 51 PASS.
- S2: 73 PASS.
- S1: 67 PASS / **2 FAIL**.

Независимый review WEB25: `reports/CHATGPT-WEB25-CODEX-RT002-S3A-REVIEW-20261108/review.md`.

S3a получил ограниченную приёмку по исходникам и авторским доказательствам. Полная независимая исполняемая проверка S3a остаётся OPEN.

**Настоящая задача устраняет исключительно `S1-INVENTORY-DRIFT`.** Она не реализует S3b и не разрешает реальные запросы к провайдерам.

## 2. Обязательные источники

Прочитать адресно:

1. `Документация/08_Старт.md`, собственную карточку Codex, применимые правила.
2. №20 §5а — RT-002/B2, S1 и условия перехода к S3b.
3. №21 — результаты S1 и S2.
4. №37 — Stage 6.
5. №36.1 и №36.3 — режимы обязательного тестирования.
6. Отчёт WEB25 по H23.
7. `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/amendment_request_s1.md`.
8. `test_rt002_s1_routes.py`, относящиеся исходники и точные вызывающие участки.

Не загружать целиком архивы и огромные реестры. №05 читать только адресно по `S1-INVENTORY-DRIFT` и зависимым OPEN.

## 3. Подтверждённые ошибки

### FAIL 1 — Static Route Inventory

Тест:

`test_production_send_sites_match_inventory_with_multiplicity`

Обнаружены новые участки:

- `web_alarm/launcher.py` — импорт `urllib.request`, строка 29.
- `web_alarm/launcher.py` — `_get → urlopen`, строка 248.
- `ordinary_chat_service.py` — `execute_request → transport.send`, строка 308.

Требуется разобраться в физической роли каждого вызова.

### FAIL 2 — Endpoint Inventory

Тест:

`test_every_endpoint_constant_read_is_an_inventoried_send_url`

Обнаружены два URL:

- `web_alarm/model_cards.py:128` — OAuth.
- `web_alarm/model_cards.py:129` — GigaChat Chat API.

Необходимо доказать, что это исключительно метаданные, если это действительно так, и учесть их без ослабления контроля над реальными сетевыми отправками.

## 4. Основное задание

### A. Разобрать маршруты

Для `web_alarm/launcher.py`:

- Проследить `_get`, `_already_running`, `_self_test` и всех фактических callers.
- Проверить формирование host/port и допустимых URL.
- Разделить локальный HTTP-запрос к Web Alarm и физическое обращение к внешнему провайдеру.
- Подтвердить классификацию исходниками и OFFLINE fake-тестами.

Для `ordinary_chat_service.py`:

- Проследить `ChatTransport.send`, вызывающие участки и возможные адаптеры.
- Не объявлять injected transport заведомо безопасным: будущий адаптер может выполнять физический LLM-запрос.
- Сохранить видимость этого участка как потенциальной границы сетевой отправки, обязательной для будущего S3b.
- Не менять сам `execute_request`.

Для `web_alarm/model_cards.py`:

- Проверить использование двух endpoint literals.
- Подтвердить, что чтение метаданных не выполняет HTTP.
- Не создавать общего исключения для всех URL провайдера.

### B. Исправить S1 oracle

Разрешено изменить инвентаризацию и тестовые функции в `test_rt002_s1_routes.py`.

Требования:

- Сохранить точный учёт известных семи LLM POST и одного OAuth POST.
- Явно классифицировать дополнительные обнаруженные участки.
- Сохранить контроль кратности физических send sites.
- Не исключать целые модули или категории UNKNOWN из сканирования.
- Не добавлять широкие allowlist по имени файла, URL, функции или HTTP-методу.
- Не маскировать будущие изменения исходников.

Если существующий oracle не позволяет корректно различать metadata, local HTTP и potentially physical LLM send, разрешено **минимально уточнить тестовый анализатор** с адресными проверками. Его общая защитная функция должна сохраниться.

### C. Обязательные отрицательные проверки

Создать детерминированные OFFLINE mutation/negative tests, подтверждающие, что oracle снова обнаруживает:

1. Дополнительный LLM POST.
2. Дополнительный OAuth POST.
3. Сетевой вызов через alias или `getattr`.
4. Попытку классифицировать внешний URL как локальный health-check.
5. Превращение metadata endpoint в фактический сетевой вызов.
6. Вторую физическую отправку внутри известного участка.
7. Новый неизвестный transport/caller без доказанной классификации.

Негативные тесты должны становиться красными при внесении нарушения. Их нельзя превращать в PASS отключением проверок.

## 5. Разрешённая область изменений

**WRITE:**

- `test_rt002_s1_routes.py` — минимальное исправление тестового анализатора, инвентаризации и негативных тестов.
- `reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/` — отчёт, манифест, исходные и итоговые доказательства, негативные тесты, OPEN/NEXT.
- БЛОК 1 собственной карточки — только штатная сдача через `finish`.

**READ ONLY:**

- `web_alarm/launcher.py`
- `web_alarm/model_cards.py`
- `ordinary_chat_service.py`
- `ultra_budget_policy.py`
- `ultra_budget_ledger.py`
- `run_store.py`
- `gigachat_transport.py`
- `server.py`
- `web_alarm/turn_service.py`
- `web_alarm/ultra_chat.py`
- `test_rt002_s2_budget_policy.py`
- относящиеся тесты и документы.

**ЗАПРЕЩЕНО:**

- Редактировать production transport, UI, бюджетную политику и S3a ledger.
- Менять числовые лимиты.
- Подключать GigaChat, OAuth, Colibri или MCP.
- Выполнять реальные внешние сетевые/платные запросы.
- Изменять CI/workflows, STANDARD, реальные Workspace, пользовательские данные или `.obsidian/workspace.json`.
- Использовать локальный Git/GitHub без отдельного разрешения.

Если исправление требует production-изменений — **STOP / новый адресный AMENDMENT**.

## 6. Тестирование

Все тесты выполнять с OFFLINE guard, установленным **до импорта тестируемых модулей**, используя существующий guarded S1 runner.

Обязательно:

1. Сохранить исходный RED: 67 PASS / 2 FAIL, с точными именами и причинами.
2. Исправить оба FAIL.
3. Выполнить **полный guarded S1 selector**, все 69 исходных методов.
4. Дополнительно выполнить новые негативные сценарии, отдельно от точного baseline manifest, если его формат закреплён.
5. Проверить наличие и SHA pinned fixtures.
6. Проверить, что не было внешних сетевых запросов, чтения секретов и нарушений изоляции.
7. Выполнить релевантные S2/S3a smoke/regression, если они доступны в разрешённом OFFLINE-режиме, не меняя соответствующие исходники.
8. Проверить Python compile/syntax и отсутствие изменений READ ONLY файлов.

Критерий S1: **69 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, gate PASS / exit 0 / isolation violations 0; все новые негативные тесты выявляют внесённые нарушения.

Не объявлять успех при частичном прогоне или `unittest` discovery, обошедшем точный guarded selector.

## 7. Отчёт и независимая приёмка

Создать:

- `report.md`
- `manifest.json`
- `evidence/` — исходные FAIL, итоговые stdout/stderr, результат guarded selector, SHA, негативные проверки и exit codes.
- `route_reconciliation.md` — таблица прежних и новых site identities, класса трафика, callers, endpoint origins и доказательств.
- `followups.json` — все оставшиеся проблемы и зависимости.

Отдельно подтвердить:

- Старые семь LLM и один OAuth send site не потеряны.
- Динамический Ordinary Chat transport остаётся видимой потенциальной physical-send границей.
- Новые неизвестные сетевые вызовы не проходят молча.
- Production source и S3a ledger не изменялись.
- Реальных provider calls — 0.

При успешном локальном прогоне статус **AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING**, а не самостоятельный VERIFIED.

Если две ошибки не удаётся устранить без ослабления oracle или изменения production-кода — сохранить `PARTIAL/BLOCKED` и запросить ограниченный AMENDMENT.

## 8. Сдача и дальнейшая работа

После полного отчётного пакета выполнить штатный:

`tools/task_slot_rotate.py finish`

С точным TASK ID, подтверждением `ROTATED`, exit 0, HISTORY ID и readback.

БЛОК 1 должен стать `WAITING`; БЛОК 1.1 должен содержать дословную сданную задачу.

**Git/GitHub локально не использовать.** Пользователь публикует результаты одним атомарным нумерованным коммитом.

ChatGPT после публикации самостоятельно проверяет исходники, тесты и доказательства, записывает вердикт и обновляет документацию по протоколу.

**NEXT (не выполнять в этой задаче):** независимая исполняемая проверка S3a, утверждение Ordinary Chat policy и подготовка S3b после выполнения всех обязательных predecessors.

**Начинай только S1 inventory reconciliation.**
###### ▲ КОНЕЦ ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:END

---

# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА

###### ▼ НАЧАЛО КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:BEGIN
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001` · перенесено 2026-11-08 · SHA-256 копии `f37ae9093b86217baed7094e7bb157614ab6ea0b5ee7a4e786df5c67ba141427` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/handoff_task.md` · отчёт `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/report.md` · HISTORY ID `H-CODEX-000023` · запись `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/task_record.json`

**TASK ID:** `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`

# Web Alarm Ultra — Stage 6A: долговременный журнал бюджетных резервов RT-002/B2 S3a

**Исполнитель:** Codex 007  
**Координатор и независимый verifier:** ChatGPT WEB  
**Приоритет:** HIGH  
**ARCH CLASS:** Ultra Runtime / RT-002 B2 / Web Alarm Ultra Stage 6  
**Режим:** OFFLINE ONLY  
**Тип:** ограниченная инженерная реализация узла S3a  
**База назначения:** `main@ce1e71cd01e64758273259848cad250f08171b94` (№538)

## 1. Основание

Пользователь завершил Stage 5 OFFLINE с ограниченным положительным результатом. Программа №37 разрешает переход к Stage 6 по отдельному назначению, но не позволяет включать реальные сетевые запросы.

Текущее состояние:

- Stage 5: BOUNDED ACCEPTED; пользовательский Windows smoke PASS.
- S0: independently ACCEPTED offline.
- S1: bounded source/evidence acceptance.
- S2: bounded source-review acceptance, без подключения к production.
- S3a: не реализован и не принят.
- S3b/S3c/S9: не приняты для нового Ordinary Chat.
- Реальные GigaChat/OAuth/paid-запросы запрещены.

**Цель задачи:** реализовать S3a — долговременное, конкурентно-безопасное хранение бюджетных резервов и результатов попыток, опираясь на утверждённый RT-002/B2 и существующий `ultra_budget_policy.py`.

Это **первая часть Stage 6**, а не полная приёмка этапа.

## 2. Обязательные источники

Прочитать локально и адресно:

1. `Документация/08_Старт.md`, собственную карточку Codex и применимые правила.
2. `Документация/37_Старт перехода - Web Alarm Ultra.md` — Stage 6, §2.4, §4.
3. `Документация/20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md` — §5а, S2→S3a→S3b, §14.
4. №21 — относящиеся к S0/S1/S2 записи и независимые ограничения.
5. `Документация/36.1_Обязательный регламент тестирования для LLM.md`.
6. `Документация/36.3_Профиль тестирования Ultra.md`.
7. `ultra_budget_policy.py`, `run_store.py`, соответствующие тесты и участки кода Ordinary Chat.

Не загружать всю историческую документацию или архив задач. Git/GitHub для локального Codex запрещены без отдельного адресного разрешения.

## 3. Техническая задача

### A. Единый владелец бюджетного состояния

Исследовать существующий `run_store.py`, его сохранение, блокировки, восстановление и учёт provider attempts.

Разработать долговременный ledger как часть **единой архитектуры Ultra**.

Не создавать независимый бюджетный механизм специально для Web Alarm и не дублировать логику B2. Существующий `usage summary` может оставаться проекцией для отображения, но не должен подменять авторитетный ledger при принятии решения о новой попытке.

### B. Атомарный резерв

Предусмотреть операции:

- `reserve`: проверить политику и доступный остаток, затем атомарно зафиксировать резерв.
- `mark_sent`: зафиксировать факт начала физической отправки.
- `mark_not_sent`: освободить резерв только при доказанном отсутствии отправки.
- `terminal`: сохранить результат и provider usage.
- `recover`: прочитать и проверить сохранённое состояние после перезапуска.

Названия API можно выбрать после изучения кода; смысл операций обязателен.

Использовать существующие состояния и функции S2: `AttemptRecord`, `reserve_attempt`, `mark_sent`, `mark_not_sent`, `apply_terminal`, `evaluate_request`, `budget_view`.

Одна физическая попытка — одна идентичность `provider_attempt_id`. Повтор того же идентичного события идемпотентен; повтор с конфликтующими данными должен быть отклонён либо переведён в безопасную аномалию, а не создавать второй расход или освобождать резерв.

### C. Сохранность и конкурентность

Проверить и обеспечить:

- резерв сохраняется до потенциальной физической отправки;
- два одновременных процесса не обходят общий лимит;
- сбой записи, повреждённый ledger, неизвестная версия, unsafe path или недоступная блокировка дают **DENY / FAIL-CLOSED**;
- рестарт не обнуляет зарезервированный и неизвестный расход;
- `UNKNOWN` не трактуется как бесплатная попытка;
- поздний terminal/usage привязывается к исходному attempt;
- противоречивые terminal-события не уменьшают обязательство;
- изменения совместимы с существующим Run Store и не повреждают старые summaries;
- отсутствие данных не подменяется фиктивным нулём.

Не создавать второй несогласованный lock-owner. Если общий механизм Run Store не позволяет обеспечить атомарность, представить доказанный BLOCKER и предложить минимальный необходимый amendment вместо рискованного обхода.

### D. Контракт Ordinary Chat

Подготовить точную схему включения обычного чата в B2:

- отдельная роль/маршрут Ordinary Chat, не `executor` и не `mcp_chat`;
- связь Workspace → Chat → Turn → provider attempt → ledger;
- immutable policy/request snapshot и идентичность final wire body;
- общий ledger для Tkinter и Web;
- соответствие S1/S2/S3a/S3b/S9;
- учёт отмены, неизвестного исхода и повторного открытия чата.

**Важно:** название нового route, scope и изменения структуры политики оформить как предложение к утверждению. Не включать новый production route и не редактировать утверждённые числовые настройки без отдельного USER GO.

### E. Границы интеграции

Эта TASK создаёт рабочий и проверяемый **OFFLINE S3a ledger**, пригодный для последующей интеграции.

Не подключать его к настоящим HTTP-вызовам, не менять transport dispatch и не утверждать завершение S3b. Без S3b физическая защита всех provider routes ещё отсутствует.

## 4. Разрешённая файловая область

**READ/WRITE:**

- `ultra_budget_ledger.py` — новый модуль S3a, если обоснован выбранной архитектурой;
- `run_store.py` — только минимальные изменения для совместимого хранения/блокировки S3a;
- `test_rt002_s3a_ledger.py` — новые OFFLINE contract, restart, fault, concurrent tests;
- `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/` — отчёты, manifest, evidence, сценарии;
- собственный БЛОК 1 Codex — только штатная механическая сдача через `task_slot_rotate.py finish`.

**READ ONLY:**

`ultra_budget_policy.py`, `test_rt002_s2_budget_policy.py`, `test_rt002_s1_routes.py`, `web_alarm/turn_service.py`, `web_alarm/ultra_chat.py`, `server.py`, `ultra_ui.py`, №20/21/37, действующие правила и чужие тесты.

Иные изменения требуют отдельного AMENDMENT. Запрещено трогать реальные Workspace, `.obsidian/workspace.json`, пользовательские данные, секреты, системные права, штатные CMD, CI/workflows и другие активные задачи.

## 5. Обязательные OFFLINE-тесты

На синтетических временных Workspace создать проверяемую матрицу:

1. Резерв зафиксирован, затем прочитан новым экземпляром процесса.
2. Повтор одного attempt не создаёт второй резерв.
3. Одинаковый attempt ID с другими данными даёт отказ.
4. Два процесса конкурируют за последний разрешённый резерв: максимум один проходит.
5. Падение до/после durable commit — нет потери подтверждённого резерва и нет ложного разрешения.
6. `SENT + timeout/UNKNOWN` сохраняет обязательство.
7. Доказанный `NOT_SENT` допускает освобождение; неподтверждённый — нет.
8. Поздний terminal уточняет прежнюю попытку, не создавая новую.
9. Дубли terminal и противоречащие usage не уменьшают расход.
10. Повреждённый JSON, неизвестная версия, junction/symlink и ошибка fsync/lock дают консервативный отказ без внешней записи.
11. Неизвестная/испорченная policy, missing profile и отсутствие оценочной информации — DENY, без обращения к провайдеру.
12. Перенос синтетического Workspace с сохранёнными резервами не обнуляет ledger; несовместимые пути отказывают безопасно.
13. Совместимость со старым Run Store: существующие records и summaries читаются, их исходные данные не меняются неожиданно.

Тестовые цифры — только специально заданные синтетические значения; не превращать их в реальные лимиты пользователя.

Использовать отдельный TEMP, физически блокировать реальные сетевые/платные вызовы. Проверить Python syntax/compile, профильный S2 guarded selector и необходимые Run Store regressions. Если точный S1/S2 selector требует недоступный архивный RAW, указать **NOT RUN / BLOCKED**, не подменять его пустым `unittest`.

Сохранить raw logs, exit codes, counts PASS/FAIL/ERROR/SKIP, подтверждение network isolation и первый RED, если он возник.

## 6. Критерии приёмки

Результат готов к независимой проверке только при наличии:

- работающего OFFLINE S3a API;
- долговременного ledger с проверенной идентичностью попыток;
- безопасной конкурентной и аварийной записи;
- строгой защиты от уменьшения UNKNOWN liability;
- доказанных negative/fail-closed tests;
- отсутствия изменений live/provider/Standard;
- сохранённой совместимости с Run Store;
- точной схемы будущего Ordinary Chat route;
- отчёта с отдельным `MANUAL ENGINEERING REVIEW` — анализом гонок, partial I/O, recovery, совместимости, аномалий и альтернатив.

**Нельзя заявлять:** Stage 6 DONE, B2 S3a INDEPENDENT VERIFIED, S3b READY FOR LIVE, оплату/стоимость проверенной, готовность Stage 7.

## 7. Отчётность и сдача

В `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/` сохранить:

- `report.md` — сделано, не сделано, ограничения и NEXT;
- `manifest.json` — все изменённые/новые файлы и SHA-256;
- `evidence/` — raw результаты тестов и отрицательные проверки;
- `ordinary_chat_contract.md` — предлагаемые route/scope/identity и точки будущей интеграции;
- `followups.json` — все OPEN, blockers, owner и необходимые решения пользователя.

При исходном FAIL или незавершённых проверках — честный `PARTIAL/BLOCKED`, не `FINAL PASS`.

После полной подготовки отчёта выполнить штатный `tools/task_slot_rotate.py finish` с **точным TASK ID**, проверить `ROTATED`, постоянный HISTORY ID, readback и освобождение БЛОКА 1. Не переносить текст вручную.

**Git/GitHub локально не использовать.** Пользователь публикует итог одним атомарным нумерованным коммитом. После этого ChatGPT независимо проверяет пакет, источники, тесты, безопасность и обновляет документацию по протоколу.

## 8. Следующий этап (не выполнять сейчас)

После независимой приёмки S3a и отдельного решения по Ordinary Chat policy подготовить **Stage 6B / S3b** — обязательный pre-HTTP guard, охватывающий физические маршруты LLM без обходов, затем S9 usage reconciliation. Только после всех необходимых gates Stage 6 может претендовать на завершение.

**Стартуй исключительно в указанном OFFLINE scope.**
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Постоянный архив — №001 Codex и адресные `reports/<TASK-ID>/task_record.json`.

- **08.11 / H-CODEX-000023 / `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`:** S3a OFFLINE ledger, 35/35 author PASS, Run Store 51, S2 73; S1 67/69 (2 FAIL). WEB25 PARTIAL/BOUNDED source-review, independent runtime NOT RUN; S3b HOLD.
- **07.11 / H-CODEX-000022 / `CODEX-WUA-S5-TURN-UX-RECOVERY-001`:** Turn UX recovery, bounded USER GUI smoke PASS; cancellation/RAW, Tcl and 480px residual OPEN.
- **07.11 / H-CODEX-000021 / `CODEX-WUA-S5-TURN-CHECK-DIAG-001`:** Turn diagnostic PARTIAL, historical RAW/F5 loss root-cause OPEN.
- **07.11 / H-CODEX-000020 / `CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001`:** Stage5 fake Web/Tk accepted bounded; independent Windows CI 387 PASS, live NOT RUN.
- **06.11 / H-CODEX-000019 / `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001`:** Stage4 offline cancellation bounded PASS, no production/live GO.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H23 S3a:** `ultra_budget_ledger.py`/35 new tests; shared Run Store index lock; documented ledger readback/replay, UNKNOWN/late, synthetic race/crash. WEB25 checked published source/hashes, independent runtime NOT RUN. S1 2 FAIL; historical adoption, policy, RAW retention, fencing OPEN; S3b blocked.
- **H22 Stage5:** WEB25 USER Windows TEST confirmed fake reply, Turn check, independent Chat 01/02 and F5; bounded only.
- **H21 Stage5:** diagnostic PARTIAL, source/author evidence; historical canceled RAW disappearance not conclusively recovered.
- **H20 Stage5:** author OFFLINE E2E implementation + independent Windows 387 PASS; no real paid provider or clean-Windows portability.
- **H19 Stage4:** guarded cancellation/deadline bounded repair; no blanket live authorization.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

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
