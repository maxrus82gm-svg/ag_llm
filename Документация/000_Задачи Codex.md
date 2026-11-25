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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-COLIBRI-REAL-CATALOG-001` · перенесено 2026-11-26 · SHA-256 копии `2eec389466cbcdcbaaa24ec7b8dbe579aa28e5beba8b87f5528105524aa16f35` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-COLIBRI-REAL-CATALOG-001/handoff_task.md` · отчёт `reports/CODEX-WUA-COLIBRI-REAL-CATALOG-001/report.md` · HISTORY ID `H-CODEX-000046` · запись `reports/CODEX-WUA-COLIBRI-REAL-CATALOG-001/task_record.json`

# Подключение реального каталога локальных LLM к EVM

**TASK ID:** `CODEX-WUA-COLIBRI-REAL-CATALOG-001`

**Приоритет:** P0.
**Исполнитель:** Codex.
**Координатор:** ChatGPT.
**Рабочая директория:** M:\GitHub\ag_llm

## 1. Режим выполнения

Архитектурный анализ выполнен координатором.

Не проводить повторное исследование всего проекта.
Не читать полные архивы предыдущих задач.

Использовать эту постановку как техническую инструкцию.
Читать только персональные правила Codex, применимые
правила изоляции и сдачи, указанные ниже функции
и непосредственно связанные с ними тесты.

Базовые версии, проверенные координатором:

WUA main:
861c7df4f48704eb9874a0bdaa0f30f6547ce21d

Colibri main:
8df5b5ec5cb363b1ad522516865fc7f4d2a8ebbe

Client Bridge API v1.0.0.
Контракт совместим с существующим адаптером WUA.

## 2. Цель

Добавить управляемый серверный режим подключения
к настоящему Client Bridge для чтения каталога.

В EVM, в колонке «Локальные LLM», должны
отображаться модели, полученные от Клиента Неополис.

На данном этапе только чтение health и models.

Реальную генерацию пока не активировать.

## 3. Файл colibri_bridge_transport.py

Путь:
web_alarm/colibri_bridge_transport.py

Координатор проверил:

- _windows_private_acl
- _private_temp_file
- _discover
- Discovery
- OfflineColibriTransport
- _fresh
- _json
- _health
- catalog

Ввести отдельный ReadOnlyColibriTransport.

Переиспользовать существующие механизмы:

- Чтение защищённого discovery.
- Проверку токена и идентификатора Bridge.
- Проверку Windows ACL.
- Проверку loopback origin.
- Contract.
- Проверку JSON и размеров ответа.
- Проверку target_id и instance_id.

Выделить общие операции чтения в общий внутренний
компонент, без дублирования HTTP-транспорта.

Существующий OfflineColibriTransport оставить
строго изолированным внутри TEMP.

ReadOnlyColibriTransport принимает явно переданные:

- Абсолютный путь профиля Client.
- Ожидаемый bridge_id.

Разрешены исключительно:

GET /bridge/v1/health
GET /bridge/v1/models

Любые POST, другие маршруты и наличие тела запроса
запрещать до сетевого обращения.

Не предоставлять методы генерации, отмены,
запуска или остановки моделей.

Не сканировать порты и директории.

Не разрешать редиректы, прокси, внешние адреса
и автоматический выбор другого Bridge.

Проверки защищённого чтения не ослаблять.
Оставшиеся ограничения защиты файлов явно указать
в отчёте как LIVE gate.

## 4. Файл ultra_connections.py

Путь:
web_alarm/ultra_connections.py

Использовать существующие функции:

- bind_offline_colibri
- registry_snapshot
- local_target
- catalog

Добавить отдельный серверный метод:

bind_readonly_colibri

Не менять защитные условия bind_offline_colibri.

Ввести явное различие режимов:

- NOT_CONNECTED
- OFFLINE
- READ_ONLY

Использовать существующий ModelRegistryView.

Не создавать второй реестр моделей.

При получении каталога сохранить:

- target_id
- instance_id
- model_id
- manager_name
- slot_id
- status
- execution_mode
- capabilities
- limits

При потере связи известные модели не удалять.
Отображать их как UNKNOWN с запрещёнными
операциями выполнения.

Состояние READY не считать доказательством
отсутствия активных или ожидающих запросов.

## 5. Файл launcher.py

Путь:
web_alarm/launcher.py

Точки изменения:

- main
- run_web_alarm

Добавить два явных аргумента запуска:

--colibri-readonly-profile
--colibri-bridge-id

Принимать только совместно, только в STANDARD,
без --require-test, --self-test и --live.

После создания WebAlarmApi использовать
bind_readonly_colibri до создания HTTP-сервера.

При отсутствии аргументов поведение STANDARD
должно оставаться прежним.

При недоступном Bridge показывать безопасную
диагностику, не блокируя работу облачного чата.

Не изменять постоянные CMD и ярлыки.
Не включать реальное подключение по умолчанию.

Физический запуск нового режима — отдельное
действие владельца после согласования preflight.

## 6. Файл model_cards.py

Путь:
web_alarm/model_cards.py

Использовать существующие функции:

- _context
- _card
- catalog

Добавить причину статуса:

LOCAL_CATALOG_ONLY

Локальные модели отображать в существующей
колонке EVM «Локальные LLM».

Сохранить текущую общую систему индикаторов H45.

Каталог и READY не являются подтверждением
успешного ответа нейросети.

Не устанавливать зелёную галочку только
на основании получения каталога.

## 7. Файл ui.py

Путь:
web_alarm/ui.py

Адресные точки:

- API_TEXT.
- Отображение local_target.
- Подпись READY (OFFLINE).
- Кнопка «Проверить чат» локальной карточки.

Для READ_ONLY отображать:

«Каталог подключён. Генерация пока недоступна».

Показывать имя Manager, слот и статус модели.
Не показывать обозначение OFFLINE для настоящего
каталога.

Запретить запуск диагностики локальной модели
в режиме READ_ONLY.

Не переделывать дизайн, навигацию или EVM H45.

## 8. Чат и Turn

Не расширять права выполнения в следующих файлах:

web_alarm/ordinary_provider.py
web_alarm/colibri_turn.py
web_alarm/turn_service.py

Существующие OFFLINE-ограничения сохранить.

Реальный каталог не должен автоматически давать
возможность выбирать модель для генерации.

Прямой HTTP-запрос локального Turn должен
по-прежнему отклоняться до отправки в Bridge.

История ранее сохранённых чатов доступна.

## 9. Проверки

Создать адресные тесты ReadOnlyColibriTransport
и подключения каталога через EVM.

Использовать существующие тестовые фикстуры.

Проверить:

1. По умолчанию сетевых обращений к Bridge нет.
2. Разрешены только два GET-маршрута.
3. POST и генерация отклоняются до сети.
4. Некорректный bridge_id отклоняется.
5. Небезопасный discovery, ACL и origin отклоняются.
6. Смена launch_identity отклоняется.
7. Каталог двух имитированных Manager отображается.
8. Потеря связи не удаляет известные модели.
9. STANDARD и TEST остаются изолированными.
10. Существующие тесты Colibri и H45 проходят.

Для регрессии использовать адресные тесты:

test_web_alarm_colibri_bridge_transport.py
test_web_alarm_model_cards.py
test_web_alarm_persistent_connection.py
test_web_alarm_launcher.py
test_web_alarm_evm_ui.js

Дополнительно применимые S1/S2.
Не ослаблять защиту ради прохождения тестов.

Реальные сетевые вызовы: 0.

## 10. Ограничения

Не использовать Git/GitHub.
Не менять проект local_LLM.
Не запускать и не останавливать Manager.
Не запускать реальные модели.
Не активировать Bridge самостоятельно.
Не изменять STANDARD-хранилище.
Не обращаться к платным API.
Не менять контракты v1.
Не устранять посторонние дефекты.

Если обнаружена необходимость архитектурного
расширения — сообщить координатору,
не реализовывать её самостоятельно.

## 11. Сдача

Отчёт и evidence:

reports/CODEX-WUA-COLIBRI-REAL-CATALOG-001/

Соблюдать WORKSPACE-ISOLATION-01.

Указать изменённые файлы, тесты, ограничения
и точную инструкцию будущего запуска READ_ONLY.

Выполнить штатный task_slot_rotate.py finish.
Получить HISTORY ID.

## 12. NEXT

Координатор проверяет исходники через GitHub.

После отдельного согласования производится
подключение настоящего Client Bridge.

Затем следующая задача:
реальный потоковый ответ локальной LLM
в существующем чате Нейрополис.
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
