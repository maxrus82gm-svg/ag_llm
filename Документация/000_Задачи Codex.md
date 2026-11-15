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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001` · перенесено 2026-11-15 · SHA-256 копии `783648c88bd6874cd5440b3a95231ccd378cda0f83f981b0379f6f8797e3abce` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001/report.md` · HISTORY ID `H-CODEX-000037` · запись `reports/CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001/task_record.json`

# CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001

**TASK ID:** `CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001`

**Название:** Web Alarm Ultra — подготовка защищённого REAL-подключения GigaChat 3 Ultra.

**Исполнитель:** Уважаемый агент 007 (Codex).

**Репозиторий:** `maxrus82gm-svg/ag_llm`

**Приоритет:** P0 — следующий шаг CHAT FIRST.

**Режим:** IMPLEMENTATION + STRICT OFFLINE VERIFICATION. Реальные API/OAuth/paid-запросы запрещены.

**Исходный ориентир:** `main@02e219f5fcecc046a42a5a34749ee4bb3e4ac067`. Перед работой сверить фактическую локальную базу и состояние БЛОКА 1.

## 1. Цель

Подготовить существующий Web Alarm Ultra к первому безопасному реальному диалогу через GigaChat 3 Ultra, сохранив архитектуру с одним Ultra Core.

Не создавать второе ядро, новый независимый Chat Core, параллельное хранилище, альтернативный механизм OAuth или новый контур учёта токенов.

Ожидаемый технический результат — готовый к последующей независимой проверке, но по умолчанию заблокированный REAL-маршрут с доказанными офлайн-сценариями.

**Никакие реальные запросы в рамках этой TASK не выполнять.**

## 2. Исходное состояние

Предыдущие задачи:

- H33 — синтетический GigaChat HTTP MockTransport.
- H34 — защита семи старых маршрутов отправки.
- H35 — STANDARD Ordinary Chat, история и настройки, одна разрешённая модель.
- H36 — сохранение выбора моделей отдельно для каждого TEST-чата.

H35/H36 прошли ограниченную независимую техническую и пользовательскую проверку, однако REAL factory, provider/account contract и полная safety-матрица остаются открытыми.

Проверить следующие существующие модули:

- `model_registry.py`
- `gigachat_transport.py`
- `ordinary_gigachat_transport.py`
- `gigachat_admission.py`
- `ordinary_chat_service.py`
- `provider_accounting.py`
- существующие Turn, Run Store, RAW/history и per-chat settings.

`model_registry.py` уже содержит `gigachat_ultra` → `GigaChat-3-Ultra`, но запись в реестре не является доказательством доступности модели через API.

## 3. REUSE CHECK — обязательный

До изменения кода провести адресную инвентаризацию:

1. Где фактически выбирается модель и формируется физический provider request.
2. Какие существующие функции выполняют авторизацию, сборку запроса, admission, учёт попытки, отправку, обработку ошибок и сохранение результата.
3. Какие проверки уже обеспечены S2/S3a/H33–H35.
4. Каких контрактов и ворот не хватает для REAL.
5. Какие функции можно переиспользовать без изменений, какие требуют минимальной адаптации.

Отразить найденные пути, функции и обоснование изменений в `REUSE CHECK` отчёта.

## 4. Provider REAL Contract

Проверить по доступным достоверным источникам без обращения к реальному аккаунту или отправки запросов:

- Точный API model ID для GigaChat 3 Ultra.
- Endpoint, OAuth и scope.
- Поддерживаемый способ отправки и потоковой выдачи.
- Достоверные пределы контекста и генерации.
- Форматы ответов, usage и ошибок.
- TLS и правила хранения/обновления токена.
- Условия проверки доступности модели для конкретного аккаунта.
- Ограничения, влияющие на резервирование и отмену попытки.

Для каждого параметра указать `VERIFIED`, `UNVERIFIED` или `UNKNOWN`, источник и дату проверки.

Публичная документация не доказывает entitlement конкретного аккаунта. Не выполнять `/models`, OAuth, chat completions или другие запросы к настоящему провайдеру без отдельного USER GO.

Нельзя подменять неизвестные provider caps настройками пользователя 250000/10000/20000.

## 5. Подготовка серверного REAL-маршрута

В пределах подтверждённых контрактов выполнить минимально необходимую реализацию или адаптацию существующих механизмов.

Обязательные свойства:

1. REAL-доступ управляется только серверной авторизацией, не браузерным флагом, параметром URL, переменной окружения или фактом наличия токена.
2. Без отдельного допуска `REAL HOLD` сохраняется и физическая отправка запрещена.
3. До потенциальной отправки выполняются проверка модели, допуск, проверка лимитов и долговечное резервирование попытки.
4. Неизвестные обязательные пределы, ошибка журнала или нарушение контракта приводят к безопасному отказу.
5. Одна разрешённая попытка не вызывает скрытых повторов, автоматического OAuth или дополнительного POST.
6. Timeout, cancel, crash/restart и неопределённый результат не превращаются в бесплатный повтор и не обнуляют возможный расход.
7. Реально полученные usage учитываются без удвоения reasoning; отсутствующие значения остаются `UNKNOWN`.
8. История, выбранная модель и настройки сохраняются за конкретным чатом.
9. Секреты и токены не попадают в отчёты, тестовые evidence, Git и обычные логи.
10. Существующие STANDARD и TEST не теряют функциональность.

Если подтверждённого контракта недостаточно для безопасной реализации, остановиться на проверяемой подготовке и зафиксировать `PARTIAL/BLOCKED`, не открывая REAL-доступ.

## 6. Write scope

Разрешены только необходимые изменения в существующих профильных модулях, названных в разделе 2, адресные тесты этих модулей и пакет отчёта:

`reports/CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001/`

Любое изменение общего Turn/Run Store, центрального HTTP-маршрутизатора, схемы хранилища, CI, общего архитектурного контракта или другого shared scope требует остановки и отдельного согласования.

Персональная карточка `Документация/000_Задачи Codex.md` допускается к записи только через штатную операцию сохранения/ротации собственной задачи после готовности отчёта.

Запрещено самостоятельно менять общие реестры, №34/40, чужие карточки, БЛОКИ 2–4 и пользовательские данные.

## 7. Не входит в задачу

- Реальные запросы GigaChat, OAuth, API и платные операции.
- Снятие REAL HOLD.
- Включение Ultra для физических запросов из STANDARD.
- Расширение списка моделей STANDARD без отдельного решения.
- Изменение интерфейса выбора моделей.
- Перестройка архитектуры Ultra Core.
- Разработка Workspace-less Chat.
- Подключение Colibri, локальных LLM или других провайдеров.
- Blueprint, инструменты агента, MCP, сжатие и общий бюджет Workspace.
- Merge, push или иные Git/GitHub-операции без отдельного разрешения.

## 8. Обязательные испытания

Провести авторские STRICT OFFLINE-тесты:

- Ожидаемый отказ REAL при отсутствии авторизации.
- Отказ до чтения секретов, кешированного токена или физического HTTP.
- Контроль неизвестной модели, неподтверждённых лимитов и отсутствующего provider contract.
- Положительный синтетический путь через HTTP MockTransport.
- Ровно одна синтетическая физическая попытка при успешном admission.
- Timeout, cancel, ошибочный ответ, неопределённый расход, повтор и restart.
- Сохранность per-chat истории, модели и настроек.
- Отсутствие доступа к реальному GigaChat из TEST.
- Отсутствие регрессии существующего STANDARD HOLD.
- Маскирование секретов и отсутствие внешних сетевых запросов во время испытаний.

При применимости использовать RED → GREEN и дополнительные негативные oracles.

Записать точные команды, exit codes, PASS/FAIL/ERROR/SKIP, версии и evidence. Не выдавать авторские тесты за независимую проверку.

Независимую проверку на GitHub-hosted Windows после опубликованной сдачи проводит ChatGPT-координатор.

## 9. Обязательные источники

Адресно прочитать:

- №08 — маршрут проекта.
- №34 — CURRENT и последние H33–H36.
- №37 §3а — CHAT FIRST, шаги 3–4.
- №20 §5а — RT-002/B2 и обязательные safety gates.
- №18 — назначение, сдача и ротация задачи.
- №36/36.1 — независимость и обязательные тестовые контракты.
- №36.2 — применимый профиль Web Alarm.
- №40 — пересечения с другими направлениями.
- H35 report/review — недостающий REAL factory/provider contract.
- Актуальные профильные FOLLOWUP в №05.

Не читать автоматически весь архив.

Перед началом выполнить `tools/task_slot_rotate.py check`, проверить точный TASK ID, свободный БЛОК 1 и отсутствие конфликтов локальной базы.

## 10. Сдача результата

В папке задачи сохранить:

- `report.md`
- `manifest.json`
- `evidence/` — тесты, первые RED, итоговые проверки
- `provider-contract.md` — модель, endpoint, возможности, источники, неизвестное
- `real-readiness.md` — чек-лист обязательных условий перед LIVE
- `next-live-procedure.md` — проект первого ограниченного пользовательского испытания без его выполнения.

В итоговом отчёте отдельно показать:

- Реализованное и подтверждённое.
- REUSE CHECK и список изменённых файлов.
- Точные тестовые результаты.
- Что остаётся `UNKNOWN`, `NOT RUN`, `PARTIAL` или `BLOCKED`.
- Какие safety-gates остаются незакрытыми.
- Готовность или неготовность к отдельной LIVE-задаче.
- Все FOLLOWUP, риски и предлагаемый NEXT.

После готовности полного пакета выполнить штатный `finish` с указанным TASK ID и проверить сохранность БЛОКА 1.1 и HISTORY ID.

**Критерий успеха:** защищённая офлайн-подготовка реального подключения GigaChat 3 Ultra с воспроизводимой проверкой всех реализованных ворот и точным перечнем оставшихся условий.

**Никаких заявлений REAL READY или LIVE PASS без отдельной независимой проверки и пользовательского разрешения.**
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Старые БЛОКИ 2–4 сохранены в `reports/CHATGPT-WEB29-H35-REVIEW-20261114/prior_closeout_snapshot.md`; B1/1.1 неизменны. Авторский `finish` H35 не означает полной REAL/UX-приёмки.

- **14.11 / H-CODEX-000035:** STANDARD → Ordinary Core per-chat model/settings/history, actual HTTP fixture; independent Windows 3 jobs PASS, author PARTIAL, REAL/USER UX HOLD.
- **14.11 / H-CODEX-000034:** seven legacy GigaChat send-site bounded independent Windows OFFLINE PASS; REAL HOLD.
- **13.11 / H-CODEX-000033:** GigaChat MockTransport exact bytes/Turn/usage bounded OFFLINE PASS.
- **13.11 / H-CODEX-000032:** Ordinary fake send S2/S3a/Turn/RAW bounded OFFLINE PASS.
- **12.11 / H-CODEX-000031:** launcher F-01 guard PASS, physical CMD NOT RUN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H36:** TEST each chat persists its own model across switch/F5; owner GUI PASS 15.11; independent CI 43635085454 2/2; REAL HOLD.
- **H35:** standard `create_server` now builds `OrdinaryApplicationChatService`; one `GigaChat 2 Pro` model, per-chat persisted preference/settings, history/usage UNKNOWN when not known, real HOLD fail-closed. Source18/18; CI 43598906253 3/3 PASS. **USER GUI BOUNDED ACCEPTED 15.11 (history/settings/F5); TECHNICAL REAL NOT READY**.
- **H34:** all seven legacy send-sites synthetic owner-gated through S2/S3a/H33; REAL blocked.
- **H33:** byte-accurate GigaChat HTTP mock→durable terminal/Turn/RAW accepted.
- **H32:** Ordinary fake one-send guard accepted.
- **H31:** launcher F-01 guard accepted; physical GUI still separate.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB30 / 15.11.2026 — H-CODEX-000036 — TEST per-chat model persistence owner+CI accepted

**TASK:** `CODEX-WUA-CHAT-TEST-PER-CHAT-MODEL-PERSIST-001`; original source `main@9dd93ba09408217781c9b8f423a9cecf5bd264aa`; [Windows run 43635085454](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43635085454) **SUCCESS 2/2**; old failing oracle expected RED, fixed code model/HTTP/UI + regression safety GREEN. **OWNER TEST GUI 15.11 BOUNDED ACCEPTED:** Lightning/Ultra remain assigned to separate chats after switches and F5; synthetic message handled. **H36 DOC CLOSED / BOUNDED INDEPENDENT OFFLINE + USER TEST GUI PASS.** All real/paid/S3b+ and independent historical S1 RAW remain HOLD/NOT RUN. `reports/CHATGPT-WEB30-H36-REVIEW-20261115/review.md`; H36 B1/1.1 already script-rotated, unchanged. H35 STANDARD owner GUI separately accepted for history/independent settings/F5 (`reports/CHATGPT-WEB30-H35-OWNER-GUI-20261115/review.md`); H35 author REAL BLOCKED remains.

## WEB29 / 14.11.2026 — H-CODEX-000035 — STANDARD Ordinary Core bounded independent review

**TASK:** `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001`, published source `main@cd0e4d943bb8d341baf07eef2a1d5c2a1619035a` №604; independent CI-only #605–607 `GPT@1c2930e0aedcebbcae01dd6455e8a6a532cf1d6e`. [Windows run 43598906253](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598906253) **SUCCESS / 3 jobs + 3 artifacts**: source18/18, actual STANDARD9+10, Core263+266, legacy244+110, S2 73, quality52+7, JS61, 4 expected RED, no unexpected guard; compile/Tk PASS. First CI RED from missing sparse history source, second from stale app count, both independently fixed in CI only; product code unchanged. **Verdict: PASS BOUNDED INDEPENDENT WINDOWS OFFLINE for STANDARD integration; author PARTIAL, TECHNICAL REAL NOT READY/FACTORY BLOCKED/RELEASE HOLD. USER UX PENDING; physical CMD/Chrome/F5, real OAuth/API/paid/provider caps, S1 historical RAW, full S3b/S3c/S9/S13a NOT RUN.** Separate global full smoke checkout long path FOLLOWUP. Review `reports/CHATGPT-WEB29-H35-REVIEW-20261114/review.md` and `reports/CHATGPT-WEB29-H35-REVIEW-20261114/independent_runs.json`. B1 WAITING, B1.1 H35 immutable; no automatic OWNER GO.

## WEB29 / 14.11.2026 — H-CODEX-000034 — seven legacy sends bounded independent PASS

TASK CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001, author source main #595 db34931753ad1a6af88434a4ffe6b1097032070f; CI-only #602 5eafbbe2a036738723dc7d2b9c1409f8f518c554. [Windows run 43576129606](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43576129606) **SUCCESS / 3 jobs** with artifacts 14106478799 / 14106388326 / 14106099308: source SHA16/16, legacy244+110, regression254+256, S2 73, quality52+6, 7-site denial1+7, UI57, 3 expected RED, guard0, compile/Tk smoke PASS. Initial CI #601 SHA LF/CRLF false RED preserved, corrected only CI. **VERDICT DOC CLOSED / PASS BOUNDED INDEPENDENT WINDOWS OFFLINE**; S1 historical RAW, physical CMD/browser/F5, real OAuth/API/paid, model caps, full S3b/S3c/S9/S13a NOT RUN/OPEN; REAL HOLD. Review reports/CHATGPT-WEB29-H34-REVIEW-20261114/review.md, receipts reports/CHATGPT-WEB29-H34-REVIEW-20261114/independent_runs.json. B1 WAITING / B1.1 H34 unchanged; no REAL authorization.

## WEB29 / 13.11.2026 — H-CODEX-000033 — GigaChat MockTransport bounded independent PASS

**TASK:** `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001`, source `main@56e7f33c351624de94db77e080767930b8cf3d38` №592; CI-only `GPT@397040862b63fb23f7f3b51e1e1e1d793fee5179` №593. Independent [Windows run 43478748679](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43478748679) **SUCCESS**, job 132069412034, artifact 14062849789 (29 files): H33 **18 PASS + 36 subtests**, H32/core regression **236 PASS + 220 subtests**, S2 **73 PASS**, isolation **52 PASS + 5 subtests**, Node UI **57 PASS**, **2 expected RED**, unexpected guards 0. Exact-wire/ledger/terminal/reopen verified in synthetic `httpx.MockTransport`, real_available=false. **VERDICT: PASS / H33 DOC CLOSED STRICTLY BOUNDED INDEPENDENT WINDOWS OFFLINE.** Historical S1 pinned RAW NOT RUN (author 69 is not independent), physical CMD/browser/F5 NOT RUN, real provider caps/OAuth/paid, all-route S3b/S3c/S9/S13a, old-audit migration/capacity and host fencing OPEN. **REAL/Stage6 full/Stage7 HOLD**, no user live GO. Review `reports/CHATGPT-WEB29-H33-REVIEW-20261113/review.md`, №06 `EVT-WEB29-H33-MOCK-HTTP-CLOSEOUT-20261113`. БЛОК 1 WAITING, БЛОК 1.1 immutable H33.

## WEB28 / 13.11.2026 — H-CODEX-000032 — прежний bounded independent OFFLINE PASS

Ordinary fake one-send; independent Windows runs 43417573566 and 43416113378 SUCCESS, 236/74/52/57 and two expected RED. Full `reports/CHATGPT-WEB28-H32-REVIEW-20261113/review.md`, №06; no REAL/full S3b.

## WEB29 / 12.11.2026 — H-CODEX-000031 — прежний bounded independent OFFLINE PASS

TEST launcher F-01 Windows independent 21 PASS, physical CMD/browser/F5 NOT RUN. Full `reports/CHATGPT-WEB29-H31-F01-REVIEW-20261112/review.md`, №06.

**Снимок вытесненной старой записи H30 и БЛОКОВ 2–4:** `reports/CHATGPT-WEB29-H33-REVIEW-20261113/prior_closeout_snapshot.md`; исходные evidence/№06 сохранены.
