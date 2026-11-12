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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001` · перенесено 2026-11-13 · SHA-256 копии `70c5dc089835b097b59270e874506ad8b252768c7dc45094b52dae75283173c3` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001/report.md` · HISTORY ID `H-CODEX-000032` · запись `reports/CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001/task_record.json`

# CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001

**TASK ID:** `CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001`

**Рабочее обозначение:** H32 — следующий слот Codex. Окончательный HISTORY ID назначается только штатным `finish`.

**Исполнитель:** Codex 007  
**Тип:** MEDIUM-LARGE IMPLEMENTATION + INTEGRATION + ADVERSARIAL OFFLINE TESTS  
**Приоритет:** HIGH / CHAT FIRST / GIGACHAT MVP  
**База:** `main@97b37f776ce77488961b30da9ec066e84e173b1d`, коммит №576  
**Предыдущие результаты:** H29, H30, H31 — приняты в своих ограниченных объёмах.  
**Режим:** STRICT OFFLINE / NO REAL LLM / NO OAUTH / NO PAID / NO EXTERNAL NETWORK

## 1. Цель

Реализовать законченный, проверяемый в OFFLINE-режиме механизм допуска и исполнения **одной физической попытки Ordinary Chat**, который станет технической основой первого настоящего диалога GigaChat.

Нужно связать существующие:

- `ordinary_chat_service.py` — подготовка запроса и общий интерфейс исполнения;
- `web_alarm/ordinary_chat_bridge.py` — адаптер веб-чата;
- `web_alarm/turn_service.py` — устойчивый жизненный цикл Turn;
- `ultra_budget_policy.py` — S2 policy, сериализация и оценка запроса;
- `ultra_budget_ledger.py` — S3a durable reserve/mark_sent/terminal;
- существующие Workspace, RAW, Run Store, Model Registry, Context и учёт usage.

**Принцип REUSE-FIRST обязателен.**

Это не создание второго сервиса LLM, бюджета, истории или OAuth. Предстоит интегрировать уже готовые и проверенные механизмы старой Ultra с веб-чатом.

**Целевой результат:** реальный по структуре путь исполнения, в котором внешний HTTP-транспорт пока заменён строгим fake transport, без возможности включить настоящего провайдера через пользовательскую конфигурацию.

## 2. Обязательные исходные материалы

Перед правками адресно прочитать:

- `Документация/08_Старт.md`;
- актуальные верхние разделы №34 и №40;
- №37, особенно §3а, шаги 3–4;
- №20, особенно §5а, действующие S2/S3a/S3b predecessors и hard safety contract;
- №05 — FOLLOWUP Ordinary policy, S3b/S3c/S9, static/dynamic coverage и H31 physical smoke;
- `reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/report.md`;
- `reports/CHATGPT-WEB28-H30-REVIEW-20261112/review.md`;
- результаты H31 по исправлению TEST launcher F-01.

Проверить актуальные сигнатуры и действующий код, не полагаться исключительно на номера строк в H30.

В первую очередь инвентаризировать существующие методы `prepare_request`, `execute_request`, `serialize_request_body`, `BudgetLedger.reserve`, `mark_sent`, `terminal`, `recover`, а также Turn freeze/restore/cancel/settle.

**Не реализовывать заново функциональность, которая уже существует.**

## 3. P0 — Final wire bytes и проверяемая идентичность попытки

Реализовать безопасное формирование окончательного тела запроса.

Обязательные свойства:

1. Сообщения, модель, разрешённая история, контекст, параметры и ограничения принадлежат серверному сохранённому снимку Turn.
2. Создаётся финальный payload, сериализованный существующим `serialize_request_body`.
3. Фиксируются точные UTF-8 bytes, длина и SHA-256.
4. Параметры `turn_id`, `attempt_id`, Workspace/Chat, выбранная модель, endpoint identity, policy revision и wire hash согласованно связываются с попыткой.
5. После успешной проверки и резервирования fake transport получает **те же байты**, а не заново созданный словарь.
6. Другая сериализация, изменение модели, payload, endpoint, настроек или hash после допуска не может незаметно попасть в отправку.

Не использовать `PreparedRequest.request_ref` вместо SHA окончательных wire bytes: это разные идентичности.

Если понадобится внутренний byte-oriented интерфейс транспорта, сделать минимальную совместимую адаптацию. Не открывать пользовательскую возможность передавать произвольный transport.

## 4. P0 — Интеграция с S2 и S3a

Реализовать обязательный admission непосредственно перед fake send через существующий бюджетный механизм.

Принципы:

- Подключить **отдельный корректный маршрут Ordinary Chat** к общей S2 policy, если действующая схема это поддерживает.
- Не маскировать Ordinary под `executor`, `mcp_chat` или другую агентную роль.
- Не вводить общий накопительный финансовый потолок Workspace: он отложен решением пользователя.
- Не выдумывать реальные числовые лимиты GigaChat и не считать настройки 250000/10000/20000 подтверждёнными пределами провайдера.
- Использовать явно тестовый, ограниченный policy/profile для синтетического OFFLINE-сценария.
- Не разрешать будущую реальную отправку, если профиль модели или обязательные реальные пределы не подтверждены.

В существующем S3a `reserve` уже обеспечивает policy evaluation под блокировкой. Не создавать отдельную гонку `check → reserve` или параллельный бюджетный журнал.

Обязательная последовательность:

1. Проверить действующий Turn, владельца попытки, отмену, права и неизменность снимка.
2. Сформировать окончательные wire bytes.
3. Получить разрешение через **durable S3a reserve**, используя S2.
4. Проверить успешный receipt, отсутствие replay/конфликта и актуальность допущенной попытки.
5. Устойчиво отметить отправку перед выходом на транспортную границу.
6. Выполнить не более одного вызова fake transport для данной попытки.
7. Корректно зафиксировать результат или неопределённость.

Если запись обязательного состояния не удалась — **DENY / ZERO SEND**.

При сбое между `mark_sent` и фактическим вызовом fake transport нельзя автоматически освобождать резерв или повторять отправку как будто ничего не произошло.

**Важная особенность:** `BudgetLedger.initialize` сейчас рассчитан на fresh enrollment. Существующая история Audit не должна молча превращаться в пустой бюджетный журнал.

Для H32 требуется:

- безопасный путь первичной инициализации нового синтетического Workspace до платных попыток;
- проверка существующего enrollment/recover;
- явный безопасный отказ для старого Audit, если достоверная adoption/migration не реализована;
- отсутствие обнуления прежних попыток, UNKNOWN или обязательств.

Если безопасная adoption старого хранилища требует отдельной миграции, не проводить её скрыто. Зафиксировать точный blocker, сохранённое состояние и необходимое продолжение.

## 5. P1 — Cancel, Retry, Crash, Reopen

Переиспользовать действующую машину состояний Turn, не создавать вторую.

Проверить и при необходимости интегрировать:

- отмену до допуска: отсутствует отправка;
- отмену после начала: сохраняется возможное обязательство;
- повтор того же idempotency key: без нового платного send;
- другой payload с прежним ключом: конфликт;
- повторное открытие и перезапуск: восстанавливается старый Turn;
- сбой до reserve;
- сбой после reserve;
- сбой после mark_sent;
- timeout, ошибка транспорта и неизвестный ответ;
- поздний response после отмены;
- два конкурирующих клиента одного Chat/Workspace;
- некорректный, отсутствующий или повреждённый бюджетный журнал.

**Гарантировать локальную защиту от неконтролируемых повторов, а не недоказуемое end-to-end exactly-once у внешнего провайдера.**

В исходе UNKNOWN система не должна автоматически отправлять повторный запрос или списывать возможный расход в ноль.

## 6. P1 — Результат, статистика и история

Связать результат OFFLINE-попытки с существующим хранением Turn/RAW/Run Store и счётчиками конкретного Chat.

Проверить:

- успешный fake ответ сохраняется один раз;
- после F5/reopen результат не дублируется;
- неуспешный ввод не включается автоматически в успешный контекст следующей модели;
- input/output/total usage учитываются без двойного начисления;
- known reasoning отображается отдельно, не прибавляется второй раз к completion;
- отсутствующий или непроверенный usage остаётся `UNKNOWN`;
- результат отменённой попытки не становится успешным из-за позднего ответа;
- резерв и исход попытки переживают рестарт.

Не создавать новый счётчик поверх уже существующего per-chat usage H29.

Если отдельная часть H29 является только сохраняемой настройкой, а не реально применяемым ограничением, показывать это в evidence явно.

## 7. P1 — Сквозной OFFLINE-сценарий Web Chat

Получить работающий синтетический сценарий:

`Web Chat → Turn → PreparedRequest → S2/S3a admission → fake byte transport → Turn settlement → RAW/history/usage → reopen`

Сохранить существующие возможности нескольких Workspace и Chat.

При этом:

- `Start_WebAlarm_Test.cmd` сохраняет две штатные разрешённые offline-конфигурации;
- H31 F-01 не регрессирует;
- `Start_WebAlarm_Standard.cmd` не изменяется;
- `Start_Ultra.cmd` и Tkinter Ultra не изменяются;
- активная реальная отправка GigaChat не добавляется;
- никакая пользовательская настройка, model_ref, launcher config или HTTP body не переключает TEST в REAL;
- текущие Stage5 TEST и rollback остаются работоспособными.

Для интеграционных проверок использовать только внутренний тестовый fake transport с доказанной изоляцией, а не произвольную инъекцию транспорта из браузера.

Не добавлять новый публичный HTTP endpoint для реального GigaChat.

## 8. Независимо проверяемые критерии PASS

Разработать адресные положительные и отрицательные тесты:

| Проверка | Требуемый результат |
| --- | --- |
| S2 DENY | 0 fake sends; нет ложного SUCCESS |
| S3a недоступен/повреждён | DENY, 0 sends |
| Корректный reserve | Один receipt, проверяемые данные и hash |
| Разрешённая попытка | Ровно 1 fake send |
| Wire bytes | Точное равенство проверенных и отправленных bytes |
| Повтор того же Turn | 0 дополнительных sends |
| Изменение после допуска | Запрет, без незаметной отправки |
| Отмена до начала | 0 sends |
| Отмена/timeout после начала | UNKNOWN или подтверждённый исход, без скрытого повтора |
| Crash/reopen | Сохранённые факты и обязательства |
| Конкуренция | Нет двух отправок одной и той же попытки |
| Исторический Audit без принятой migration | Fail-closed, не нулевой баланс |
| Недоступная модель или неподтверждённые real caps | Нет REAL-допуска |
| Запрос на внешний transport из TEST | REJECTED, 0 external calls |
| STANDARD и старые offline fixtures | Отсутствие регрессий |

Провести также релевантные регрессионные наборы:

- Ordinary Core Bridge;
- Turn Service и Stage5;
- H29 per-chat settings/usage;
- H31 launcher guard;
- RT-002 S1/S2/S3a;
- Run Store/Writer Lock по затронутым сценариям.

Использовать существующий guarded OFFLINE runner с защитой от network/DNS/OAuth/секретов. Разрешены только синтетические Workspace и явно допустимые локальные тестовые механизмы.

Отдельно включить тесты на ослабление защиты: намеренно изменённый payload, повторный receipt, недоступный ledger и попытка конфигурационного перехода на REAL должны приводить к отказу.

Не заявлять PASS без запуска.

## 9. Граница изменений

Приоритетные модули:

- `ordinary_chat_service.py`;
- `web_alarm/ordinary_chat_bridge.py`;
- `web_alarm/ordinary_chat_test_adapter.py`;
- `web_alarm/turn_service.py`;
- `ultra_budget_policy.py`;
- `ultra_budget_ledger.py`;
- минимально необходимые смежные adapter/fixture/test-модули.

`web_alarm/ultra_chat.py` разрешается затрагивать только для необходимой OFFLINE-интеграции с сохранением действующих защит и контрактов.

Общие `server.py`, `gigachat_transport.py`, Tkinter UI, launcher, пользовательские CMD и активный REAL путь не менять без отдельного согласования; если обнаружено, что обязательная часть действительно требует их изменения, документировать blocker и минимальное предложение, не расширяя scope молча.

**Запрещено:**

- второе ядро Ultra;
- новая параллельная система Turn/Run/RAW;
- новый OAuth или Model Registry;
- второй бюджетный ledger;
- REAL API, OAuth, платные запросы, внешние модели;
- секреты в GitHub, отчётах или логах;
- расширение общего бюджета Workspace, Статиста, сжатия, памяти и Blueprint;
- изменение самостоятельного проекта `local_LLM`;
- изменение нормативных документов, истории №001, №05/06/34/40 или БЛОКА 4.

Исходные TEMP-копии H30/H31 не удалять.

## 10. Приоритет при ограничении времени

Это одна расширенная задача, а не разрешение на бесконтрольную переработку архитектуры.

Работать в таком порядке:

**P0:** final bytes, Ordinary policy, durable reserve, replay protection, fake one-send.

**P1:** crash/cancel/reopen, usage, интеграция с Turn и адресная регрессия.

**P2 только при устойчивом P0/P1:** дополнительные UI/CMD/browser OFFLINE smoke и расширенные негативные тесты в пределах уже разрешённого scope.

Если возникнет реальное противоречие существующему B2/S3a или требование непроверенной миграции, остановить затронутую часть и оформить `PARTIAL/BLOCKED`. Нельзя ослаблять защиту, чтобы искусственно получить зелёный результат.

Отдельная реализация всех физических отправок S3b во всём Ultra **не входит в H32**. В полном объёме S3b/S3c/S9/S13a и его предшественники сохраняют самостоятельные обязательные gates №20. Приёмка Ordinary fake path не считается автоматически завершением всей программы B2.

## 11. Сдача

Сохранить результат в:

`reports/CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001/`

Обязательный состав:

- `report.md` — факты реализации, границы и найденные проблемы;
- `manifest.json` — изменённые файлы, source/after SHA, назначение;
- `evidence/` — результаты тестов, команды, exit codes, guard и raw test outputs без секретов;
- `handoff_task.md`, `task_record.json` и штатные артефакты сдачи согласно №18.

В отчёте отдельно назвать:

1. Что удалось переиспользовать без изменений.
2. Что пришлось изменить и почему.
3. Точный участок от финальных bytes до fake send.
4. Как обеспечиваются durable reserve, replay, cancel и UNKNOWN.
5. Что происходит с существующим Audit/ledger enrollment.
6. Реальные тестовые результаты PASS/FAIL/ERROR/SKIP и исходные неудачи.
7. Что НЕ запускалось: REAL, OAuth, paid, full S3b и любые непроведённые проверки.
8. Риски, безопасный rollback и конкретный NEXT перед первым GigaChat.

После финального отчёта выполнить штатный `tools/task_slot_rotate.py finish` с данным TASK ID, затем проверить HISTORY ID, snapshot, task_record и readback.

Git/GitHub Codex не использует без отдельного полномочия. Публикация результатов производится через установленный пользовательский процесс.

**Условие успешной сдачи:** реализованный и протестированный OFFLINE Ordinary pre-send механизм, без обхода S2/S3a, без повторной неконтролируемой отправки, без изменения STANDARD/Tkinter и без реальных обращений к GigaChat.

**Следующий этап:** независимая проверка ChatGPT; только после неё отдельное решение о готовности и разрешении первого ограниченного REAL GigaChat.

**Нельзя объявлять `STAGE6 COMPLETE`, `FULL S3b VERIFIED` или `LIVE READY` на основании одних авторских тестов H32.**
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

## WEB28 / 12.11.2026 — H-CODEX-000030 — pre-send READ-ONLY independent bounded PASS

`CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001` / `H-CODEX-000030`, main №574 `d26c4ad9380b2bb1a0ccd1dd88bdf2facd3c954c`: independent Windows Python 3.12 7/7 OFFLINE PASS, guard0; four H30 cases + 3 adjacent tests, source SHA and author report SHA verified. Three initial synthetic TEMP attempts failed from Windows MAX_PATH; clean rerun in short TEMP all PASS without product edits. **VERDICT: H30 DOC CLOSED, P0/P1 PREFLIGHT RESEARCH ONLY**. Author PARTIAL at submission and separate H31 correction F-01 faithfully preserved. Not full S3b; GitHub dedicated H30 CI pending on same atomic GPT push, H31 physical CMD/browser/full CI/real/OAuth/paid/TEMP cleanup NOT RUN. Review `reports/CHATGPT-WEB28-H30-REVIEW-20261112/review.md`, evidence `reports/CHATGPT-WEB28-H30-REVIEW-20261112/independent_runs.json`. Next only with USER GO narrow Ordinary fake final-wire/S2/S3a one-send; B1/1.1 unchanged.

## WEB29 / 12.11.2026 — H-CODEX-000031 — F-01 TEST launcher independent bounded PASS

`CODEX-WUA-CHAT-S3B-F01-LAUNCH-GUARD-001`; source main №573 `a26b3157`; [GitHub Windows run 43264689001](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43264689001): **18 existing + 3 reviewer = 21/21 PASS, guard violations 0**. Fail-closed для неподтверждённых script/args/kind под `--require-test`; два approved offline профиля сохранены, STANDARD и CMD не изменены. **VERDICT: PASS / H31 DOC CLOSED в BOUNDED INDEPENDENT OFFLINE scope.** Физический CMD/browser/F5, общий S3b, full CI, real/paid НЕ ПРОВЕРЕНЫ. H30 REVIEW PENDING. Local H30/H31 TEMP cleanup PENDING. Review `reports/CHATGPT-WEB29-H31-F01-REVIEW-20261112/review.md`. USER HARD GATE: независимый зелёный CI → полное обновление регистров/БЛОК4 → единый нумерованный GPT commit → merge пользователем. БЛОКИ 1/1.1 не менялись.


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
