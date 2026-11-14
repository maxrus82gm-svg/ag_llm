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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001` · перенесено 2026-11-14 · SHA-256 копии `df167b0de0c377f420b33c48ffce54398b5583664c87703632b3f91ffc1da9f2` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001/report.md` · HISTORY ID `H-CODEX-000034` · запись `reports/CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001/task_record.json`

# CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001

**TASK ID:** `CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001`

**Рабочее обозначение:** H34 — GigaChat REAL Readiness / S3b Physical Send Protection

**Исполнитель:** Codex 007

**Тип:** LARGE IMPLEMENTATION + INTEGRATION + ADVERSARIAL OFFLINE TESTS

**Приоритет:** HIGH / CHAT FIRST / GIGACHAT MVP

**База:** `main@f50d5432228fdfc5ad67999f7620b9fb64bf1a49`, рабочий коммит №594.

**Предшественник:** H33 / `H-CODEX-000033` — документально закрыта, независимая Windows OFFLINE-проверка принята.

**Режим:** STRICT OFFLINE / NO REAL GIGACHAT / NO REAL OAUTH / NO PAID / NO EXTERNAL NETWORK / NO PRODUCTION WRITES.

Постоянный HISTORY ID назначается исключительно штатным `finish`. Не присваивать его вручную.

---

## 1. Главная цель

Уважаемый агент 007 (Codex)!

Продолжите разработку Web Alarm Ultra после успешно принятой H33.

Наша ближайшая продуктовая цель — **первый настоящий безопасный диалог пользователя с GigaChat через веб-интерфейс**.

H32 реализовала защищённую цепочку:

`Ordinary Chat → final bytes → S2/S3a → SENT → fake send → durable terminal → Turn/RAW/usage/reopen`

H33 добавила GigaChat-shaped HTTP `MockTransport`, проверку точных байтов, HTTP-ошибок, usage и восстановления.

Независимый GitHub Actions Windows run:

`43478748679` — SUCCESS.

Однако настоящая отправка GigaChat всё ещё заблокирована. Отсутствуют полный физический контроль S3b, проверенный REAL provider contract и надёжный серверный механизм разрешения реальных вызовов.

**Задача H34 — закрыть максимальный технически обоснованный объём этих препятствий, не выполняя никаких настоящих API-вызовов.**

Не разрабатывать новую систему чатов, не начинать заново транспорт и не создавать параллельное ядро.

## 2. Обязательные документы

Перед изменениями адресно изучить:

- `Документация/08_Старт.md`
- `Документация/000_Задачи Codex.md`
- №34 — актуальный тактический контекст.
- №40 — текущая координация.
- №37 — особенно §2.1–2.2 и §3а.
- №20 — особенно §5а RT-002/B2.
- №05 — открытые FOLLOWUP.
- №18 — актуальный регламент сдачи.
- №22 — GitHub Actions Windows.
- №36.1 и №36.3 — правила тестирования.
- `DOC-WUA-LAUNCH-01` и правила собственного БЛОКА 1.

Обязательно изучить опубликованные результаты:

- H32: `CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001`
- H33: `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001`
- `reports/CHATGPT-WEB29-H33-REVIEW-20261113/review.md`
- H33 `route_inventory.md` и `provider_contract.md`.

Использовать актуальное состояние GitHub, указанное в постановке, как базовый ориентир. Самостоятельных Git/GitHub-операций без отдельного разрешения нет.

## 3. REUSE-FIRST — обязательный архитектурный принцип

Сохраняем **одно существующее Python-ядро Ultra**.

До написания нового кода провести REUSE CHECK.

В первую очередь проверить и повторно использовать:

- `ordinary_chat_service.py`
- `ordinary_gigachat_transport.py`
- `web_alarm/ordinary_chat_bridge.py`
- `web_alarm/turn_service.py`
- `ultra_budget_policy.py`
- `ultra_budget_ledger.py`
- `gigachat_transport.py`
- `run_store.py`
- существующие Model Registry, OAuth, Turn, RAW, context storage и usage extraction.

Никакого второго OAuth-клиента, второго ledger, второго Ordinary Chat core, альтернативного хранилища истории или дублирующего реестра моделей.

Новый общий адаптер допускается, если существующие функции объективно нельзя переиспользовать без нарушения безопасности. Причину документировать.

## 4. P0 — S3b: защита всех физических LLM-отправок

H33 защитила только узкую Ordinary Chat HTTP fixture.

Необходимо исследовать и адресно интегрировать защиту физических отправок GigaChat во всех семи ранее инвентаризированных LLM POST-sites:

1. `server.ask_gigachat`
2. `server._run_agent_task_impl`
3. `server._request_audit_diagnostic`
4. `planner_runtime.PlannerSession.call`
5. `planner_runtime.run_planner`
6. `verifier_runtime._request_gigachat`
7. `compressor_runtime._request_gigachat`

Дополнительно проверить динамические Ordinary Chat transport paths, возможные injected clients/checkers и остальные классифицированные S1 boundaries.

OAuth POST учитывать отдельно от семи LLM POST.

Для каждого физического LLM-send требуется проверяемый контракт:

- окончательное тело запроса известно до admission;
- S2 оценивает именно те байты и параметры, которые будут отправлены;
- до физического HTTP существует durable S3a reserve;
- подтверждается переход SENT, привязанный к правильным Workspace/Chat/Run/Turn/attempt;
- проверяются авторитетный endpoint, модель, policy revision, owner и актуальность попытки;
- после admission не допускается скрытая повторная JSON-сериализация с изменением body;
- повторная отправка без нового законного admission запрещена;
- DENY, повреждённый журнал или неизвестная политика дают ноль физических POST.

Исходные legacy call-sites используют `json=body`. Не считать их автоматически защищёнными только потому, что H33 использует `content=wire`.

**Особое требование:** сохранить совместимость существующих сценариев, состояние STANDARD/Tkinter и первоначальные контракты ошибок. Нельзя оставлять скрытый обход S3b ради совместимости.

Если полный перенос конкретного legacy-маршрута нельзя доказать безопасным в рамках данной задачи, сохранить fail-closed, показать блокер и не объявлять полный S3b PASS.

## 5. P1 — серверный REAL admission GigaChat

Подготовить следующий слой серверного допуска для будущего настоящего GigaChat.

Требования:

- Разрешение будущего REAL-запроса принадлежит только доверенной серверной логике.
- Browser, JavaScript, JSON config, `.env`, URL-параметр, TEST launcher либо переданный пользователем Boolean не дают полномочий включать REAL.
- Существующий OAuth переиспользуется, не копируется.
- Реальный endpoint и модель требуют проверенного provider profile.
- Неизвестные возможности модели или недостоверные caps приводят к отказу либо отдельному явно проверяемому ограниченному решению, а не к выдуманному лимиту.
- UI-предпочтения 250000/10000/20000 не считаются подтверждёнными провайдерскими пределами.
- Нельзя допускать реальную попытку, если отсутствует авторитетная политика её максимальной ответственности или невозможен durable reserve.
- Отсутствующий, просроченный или неподтверждённый OAuth не должен запускать неконтролируемую повторную цепочку.
- Секреты, Authorization headers и содержимое ответов авторизации не должны попадать в диагностические ошибки или технические логи.

В рамках H34 **REAL остаётся запрещённым**.

Разрешается создать проверяемую server-only структуру будущего допуска и полностью испытать её на синтетических данных, но запрещается создавать способ включения настоящей сети обычной настройкой или недоверенным вызовом.

Не выполнять OAuth даже для проверки доступности аккаунта.

## 6. P2 — модель, лимиты и учёт

Проверить, какие реальные свойства GigaChat необходимы для безопасного допуска:

- model ID и endpoint;
- размер контекстного окна;
- ограничение генерации;
- поддержка и семантика reasoning;
- входные, выходные, cached/processed токены;
- неполный или отсутствующий usage;
- timeout, HTTP errors, rate limits;
- возможность проверить стоимость или максимальную ответственность попытки.

Отделить документально подтверждённые сведения от предположений.

При отсутствии надёжного источника записывать `UNVERIFIED` / `UNKNOWN`.

Не запускать внешние запросы для уточнения возможностей провайдера. Подготовить перечень конкретных сведений, которые координатор должен подтвердить перед LIVE.

Переиспользовать текущий per-chat usage H29 и S9-контракты там, где они уже реализованы.

Не создавать общий финансовый кошелёк Workspace: он отложен решением владельца.

## 7. P3 — аварии, отмена и восстановление

Проверить отрицательные сценарии:

- cancel до reserve;
- cancel после reserve;
- cancel после SENT;
- timeout до подтверждения отправки;
- timeout после возможной отправки;
- потеря соединения;
- restart после SENT;
- два параллельных запроса;
- повторный Turn ID;
- replay после F5;
- смена модели;
- смена policy revision;
- повреждённый ledger;
- ошибка terminal write;
- запоздалый HTTP-ответ;
- неизвестный usage;
- отсутствие доступа к старому ledger.

Принцип: **UNKNOWN не равен нулю**.

Не освобождать резерв и не отправлять повторно платный запрос только потому, что ответ не был получен.

При устаревшем engine fingerprint нельзя автоматически сбрасывать историю учёта или переоформлять старый audit как новый пустой.

Отдельно оценить влияние `S3A-ADOPTION-UPGRADE`, `S3A-DURABILITY-FENCING`, `S3A-RAW-WIRE-RETENTION` и capacity limit. Не выполнять произвольную миграцию production-данных.

## 8. P4 — тестирование

**ARCH CLASS:** Web Alarm Ultra / GigaChat / S3b transport and admission.

Работать исключительно в OFFLINE-режиме с синтетическими Workspace.

Использовать существующие guarded test fixtures и дополнять общую тестовую базу проекта.

Обязательная матрица:

| Группа | Требование |
|---|---|
| S3b routes | Все семь физических sites проверены адресно |
| Exact bytes | Body/hash до и на границе отправки совпадают |
| DENY | Ноль фактических send |
| Forged authority | Поддельные разрешения отвергаются |
| Replay | Ноль незапрошенных повторов |
| Recovery | Restart/cancel/UNKNOWN не обнуляют liability |
| Provider caps | Непроверенная модель/профиль не допускаются |
| OAuth | Нет настоящей авторизации, secrets не раскрываются |
| Regression | H29/H31/H32/H33/Turn/Run Store/S2/S3a |
| Negative controls | Ослабление ключевой защиты вызывает ожидаемый RED |
| Isolation | Нет внешней сети и записи в рабочие Workspace |

Защитный сетевой guard должен устанавливаться **до импортов runtime**.

Выполнить адресные Python/HTTP/Node проверки, соответствующую широкую регрессию, ручной adversarial source review и негативные тесты.

Предоставить точные команды, версии, SHA, exit codes, PASS/FAIL/ERROR/SKIP и raw evidence.

Не изменять тестовые оракулы ради искусственного PASS.

Исторические pinned RAW, отсутствующие на проверочной машине, отмечать NOT RUN. Не заменять их синтетикой для доказательства исторической эквивалентности.

Независимую Windows-проверку после публикации выполнит ChatGPT-координатор через GitHub Actions.

## 9. Разрешённый write scope

Разрешены только необходимые изменения в подсистемах Web Alarm Ultra, относящихся к этой задаче:

- существующие GigaChat/Ordinary transport и admission modules;
- семь перечисленных LLM call-sites — только минимальные адресные изменения для S3b;
- серверные адаптеры, относящиеся к проверяемому REAL admission;
- необходимые общие функции S2/S3a/Run Store при доказанной необходимости и с сохранением обратной совместимости;
- релевантные тесты и synthetic fixtures;
- `reports/<TASK-ID>/` — отчёт, manifest, evidence и сохранённая постановка;
- собственная карточка Codex — только для разрешённой штатной операции `finish`.

Изменения иных компонентов требуют отдельного согласования.

**Запрещено:**

- редактировать STANDARD/Tkinter ради новой архитектуры;
- создавать новые пользовательские CMD/BAT;
- менять или ослаблять `Start_WebAlarm_Standard.cmd` и `Start_WebAlarm_Test.cmd`;
- менять рабочие Workspace;
- использовать настоящие ключи;
- запускать реальные OAuth/API;
- выполнять внешние сетевые запросы;
- вмешиваться в Colibri Ultra, Blueprint LLM или другие репозитории;
- переписывать №05/06/08/18/20/34/37/40 или БЛОК 4;
- самостоятельно выполнять Git/GitHub read/write без отдельного разрешения;
- создавать production REAL bypass.

До правок — безопасный backup и fingerprint исходных файлов. После — readback и сохранение доказательств. Старые TEMP backup не удалять автоматически.

## 10. Критерии завершения

Успешная авторская сдача H34 требует:

1. Проверяемой актуальной карты всех физических GigaChat LLM-отправок.
2. Реализации или строго обоснованного блокирующего результата по каждому S3b site.
3. Действующего защищённого OFFLINE-контракта pre-send, SENT, one-shot и terminal.
4. Подготовленного server-only REAL authority без доступного LIVE-переключателя.
5. Честного provider contract с разделением VERIFIED и UNVERIFIED.
6. Проверок recovery, cancel, duplicate, UNKNOWN и crash.
7. Подтверждения сохранности Ordinary Chat H32/H33 и штатных launcher.
8. Полной матрицы тестов и отрицательных контролей.
9. Инженерного source review по TEST-ENG-01.
10. Отчёта о том, что действительно готово к первому LIVE, а что осталось обязательным gate.

Если пункт не выполнен, честно указать `PARTIAL`, `BLOCKED` или `NOT RUN`. Нельзя объявлять всеобъемлющий S3b PASS на основании одного Ordinary Chat.

**H34 сама по себе не закрывает автоматически S3c/S9/S13a, Stage 6 или Stage 7.**

Вопросы, выходящие за её scope, остаются OPEN с конкретными successor recommendations.

## 11. FOLLOWUP, которые нельзя потерять

Сопоставить результаты с действующей очередью №05:

- `S3B-S3C-S9`
- `STATIC-DYNAMIC-COVERAGE`
- `S2-STATIC-IMPORT-COVERAGE`
- `S3A-ADOPTION-UPGRADE`
- `S3A-CAPACITY`
- `S3A-DURABILITY-FENCING`
- `S3A-RAW-WIRE-RETENTION`
- `FOLLOWUP-WUA-H32-S1-RAW-CI-001`
- `FOLLOWUP-WUA-H32-REAL-CONTRACT-001`
- `FOLLOWUP-WUA-H33-SERVER-REAL-AUTHORITY-001`
- `FOLLOWUP-WUA-H31-PHYSICAL-SMOKE-001`

Исполнитель сохраняет известные OPEN и NEXT в своём итоговом отчёте. Координатор актуализирует общую очередь после независимой проверки.

## 12. Отчёт и завершение

Подготовить:

- `report.md` — итог реализации.
- `manifest.json` — изменённые файлы, версии и hashes.
- `route_inventory.md` — итоговый physical send census.
- `provider_contract.md` — реальные и неподтверждённые ограничения.
- `real_readiness.md` — проверенные условия будущего LIVE.
- `evidence/` — тесты, команды, логи, отрицательные сценарии и readback.
- `DOC IMPACT` — адресные рекомендации координатору.

Отдельно указать `REUSE CHECK`, сохранность STANDARD/TEST, исходные ошибки, ограничения и следующий безопасный шаг.

После готовности полного factual-пакета выполнить штатную сдачу:

`python -B tools/task_slot_rotate.py finish --card "Документация/000_Задачи Codex.md" --task-id CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001`

Выполнить check/dry-run/apply/readback согласно действующему регламенту, не вручную переносить БЛОК 1.

Новый HISTORY ID берётся только из результата `finish`.

**Финальный статус:** `AUTHOR RESULT READY / AWAITING INDEPENDENT VERIFICATION` с честным PASS/PARTIAL/BLOCKED по фактическим проверкам.

Не коммитить и не публиковать самостоятельно.

---

## 13. Главный результат для владельца

После H34 мы должны чётко понимать, насколько Web Alarm Ultra приблизилась к настоящему GigaChat.

Приоритет — работоспособный безопасный чат, а не создание очередной вспомогательной архитектуры.

Действовать инженерно: находить существующие механизмы, переиспользовать их, закрывать реальные препятствия и доказывать результат тестами.

**Никакого LIVE до независимой приёмки обязательных ворот и отдельного OWNER GO.**
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Предыдущие БЛОКИ 2–4 сохранены в reports/CHATGPT-WEB29-H34-REVIEW-20261114/prior_closeout_snapshot.md. B1/1.1 неизменны.

- **14.11 / H-CODEX-000034:** семь legacy GigaChat send-site, guarded admission, independent Windows 244+110 / 254+256 PASS; REAL HOLD.
- **13.11 / H-CODEX-000033:** GigaChat MockTransport immutable bytes Windows PASS.
- **13.11 / H-CODEX-000032:** Ordinary fake one-send S2/S3a/Turn/RAW PASS.
- **12.11 / H-CODEX-000031:** launcher F-01 guard 21 PASS, physical CMD NOT RUN.
- **10.11 / H-CODEX-000030:** READ-ONLY pre-send PASS, all S3b OPEN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H34:** shared server owner only OFFLINE, seven legacy sends protected; SHA16/16; CI run43576129606 SUCCESS. REAL OAuth gate DENY, full S3b/S3c/S9/S13a and physical user smoke OPEN.
- **H33:** GigaChat MockTransport immutable bytes → S2/S3a → terminal/Turn/RAW/reopen PASS.
- **H32:** Ordinary synthetic one-send accepted, real transport absent.
- **H31:** TEST launcher guard accepted; physical GUI NOT RUN.
- **H30:** READ-ONLY preflight accepted; full S3b OPEN.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB29 / 14.11.2026 — H-CODEX-000034 — seven legacy sends bounded independent PASS

TASK CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001, author source main #595 db34931753ad1a6af88434a4ffe6b1097032070f; CI-only #602 5eafbbe2a036738723dc7d2b9c1409f8f518c554. [Windows run 43576129606](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43576129606) **SUCCESS / 3 jobs** with artifacts 14106478799 / 14106388326 / 14106099308: source SHA16/16, legacy244+110, regression254+256, S2 73, quality52+6, 7-site denial1+7, UI57, 3 expected RED, guard0, compile/Tk smoke PASS. Initial CI #601 SHA LF/CRLF false RED preserved, corrected only CI. **VERDICT DOC CLOSED / PASS BOUNDED INDEPENDENT WINDOWS OFFLINE**; S1 historical RAW, physical CMD/browser/F5, real OAuth/API/paid, model caps, full S3b/S3c/S9/S13a NOT RUN/OPEN; REAL HOLD. Review reports/CHATGPT-WEB29-H34-REVIEW-20261114/review.md, receipts reports/CHATGPT-WEB29-H34-REVIEW-20261114/independent_runs.json. B1 WAITING / B1.1 H34 unchanged; no REAL authorization.

## WEB29 / 13.11.2026 — H-CODEX-000033 — GigaChat MockTransport bounded independent PASS

**TASK:** `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001`, source `main@56e7f33c351624de94db77e080767930b8cf3d38` №592; CI-only `GPT@397040862b63fb23f7f3b51e1e1e1d793fee5179` №593. Independent [Windows run 43478748679](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43478748679) **SUCCESS**, job 132069412034, artifact 14062849789 (29 files): H33 **18 PASS + 36 subtests**, H32/core regression **236 PASS + 220 subtests**, S2 **73 PASS**, isolation **52 PASS + 5 subtests**, Node UI **57 PASS**, **2 expected RED**, unexpected guards 0. Exact-wire/ledger/terminal/reopen verified in synthetic `httpx.MockTransport`, real_available=false. **VERDICT: PASS / H33 DOC CLOSED STRICTLY BOUNDED INDEPENDENT WINDOWS OFFLINE.** Historical S1 pinned RAW NOT RUN (author 69 is not independent), physical CMD/browser/F5 NOT RUN, real provider caps/OAuth/paid, all-route S3b/S3c/S9/S13a, old-audit migration/capacity and host fencing OPEN. **REAL/Stage6 full/Stage7 HOLD**, no user live GO. Review `reports/CHATGPT-WEB29-H33-REVIEW-20261113/review.md`, №06 `EVT-WEB29-H33-MOCK-HTTP-CLOSEOUT-20261113`. БЛОК 1 WAITING, БЛОК 1.1 immutable H33.

## WEB28 / 13.11.2026 — H-CODEX-000032 — прежний bounded independent OFFLINE PASS

Ordinary fake one-send; independent Windows runs 43417573566 and 43416113378 SUCCESS, 236/74/52/57 and two expected RED. Full `reports/CHATGPT-WEB28-H32-REVIEW-20261113/review.md`, №06; no REAL/full S3b.

## WEB29 / 12.11.2026 — H-CODEX-000031 — прежний bounded independent OFFLINE PASS

TEST launcher F-01 Windows independent 21 PASS, physical CMD/browser/F5 NOT RUN. Full `reports/CHATGPT-WEB29-H31-F01-REVIEW-20261112/review.md`, №06.

**Снимок вытесненной старой записи H30 и БЛОКОВ 2–4:** `reports/CHATGPT-WEB29-H33-REVIEW-20261113/prior_closeout_snapshot.md`; исходные evidence/№06 сохранены.
