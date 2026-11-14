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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001` · перенесено 2026-11-14 · SHA-256 копии `0b8c557896c0102b48bcf46c34212a7761f18559677df8516b3ccfad6342ffe7` · CHAT-ONLY AMENDMENT: 1 в снимке · снимок `reports/CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001/report.md` · HISTORY ID `H-CODEX-000035` · запись `reports/CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001/task_record.json`

# CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001

**TASK ID:** `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001`

**Название:** Web Alarm Ultra — подготовка одного реального GigaChat через штатный веб-чат

**Исполнитель:** Codex 007  
**Тип:** LARGE IMPLEMENTATION + INTEGRATION + SECURITY REVIEW  
**Приоритет:** HIGH / CHAT FIRST  
**Предшественник:** H34 — `H-CODEX-000034`  
**Режим:** STRICT OFFLINE при разработке и авторских испытаниях. NO REAL API / OAUTH / PAID / PRODUCTION WRITES.

## 1. Цель

Подготовить штатный Web Alarm Ultra к первому настоящему, ограниченному диалогу с одной моделью GigaChat.

Результат должен находиться внутри существующего приложения, а не в отдельной демонстрационной программе.

Целевая цепочка:

**Ordinary Web Chat → выбор разрешённой модели → серверная авторизация → final bytes → S2/S3a → HTTP transport → terminal → Turn/RAW/history/usage → F5/reopen.**

Первый реальный запрос в рамках данной TASK **НЕ выполнять**. Он потребует отдельного решения владельца после независимой проверки и выполнения применимых технических ворот.

## 2. Обязательные источники

Адресно изучить:

- №08 — Старт.
- Собственную карточку Codex и применимые правила.
- №34 и №40 — текущее состояние.
- №37 §3а — CHAT FIRST.
- №20 §5а — RT-002/B2 и обязательные predecessor gates.
- №36/36.1/36.3 — тестирование и независимая приёмка.
- H32, H33, H34 — реализации, отчёты и evidence.
- `reports/CHATGPT-WEB29-H34-REVIEW-20261114/review.md`.

Перед работой проверить применимые source SHA и текущее состояние проекта. Git/GitHub для локального исполнителя остаются запрещёнными без отдельного разрешения.

## 3. P0 — один проверенный provider contract

Использовать существующий `model_registry.py`. Не создавать второй каталог моделей.

Подготовить контракт **одной модели** GigaChat, указывая отдельно:

- внутренний ID и точный provider model ID;
- актуальный endpoint и версию API;
- тип аккаунта и scope;
- доступность модели для данного аккаунта;
- контекстное окно и максимальный output;
- semantics usage/cached/reasoning, если подтверждены;
- ограничения стоимости, частоты и числа попыток;
- требования TLS, сертификатов и прокси.

Опора — датированная первичная документация провайдера. Если индивидуальные характеристики аккаунта нельзя проверить без авторизации, обозначить `ACCOUNT / MODEL AVAILABILITY UNVERIFIED`.

Не подменять реальные ограничения UI-предпочтениями 250000/10000/20000 или синтетическими профилями H34.

Официальные источники для сверки:

- https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api
- https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/get-models
- https://developers.sber.ru/docs/ru/gigachat/guides/selecting-a-model
- https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat

Документировать, какие сведения ещё должен подтвердить владелец перед LIVE. Не извлекать credentials и не делать сетевых запросов ради этой проверки.

## 4. P1 — доверенный серверный REAL factory

На базе существующих `gigachat_admission.py`, `gigachat_transport.py` и H33 HTTP-границы подготовить технический маршрут реального провайдера.

Требования:

1. Только сервер может создавать реальный authority после всех обязательных проверок.
2. Настройка браузера, флаг в JSON, env, cache token, URL или произвольный Python-клиент не дают право на REAL.
3. Сохранить все проверки H34: owner, identity, модель, exact bytes, endpoint, immutable policy, reserve/SENT/readback и terminal.
4. Не создавать второй OAuth cache, ledger, request serializer, Run Store или Chat core.
5. Никаких автоматических повторных отправок после SENT/UNKNOWN.
6. Cancellation, timeout, 401/403/429/5xx, оборванный поток, ошибка terminal и неопределённый результат обрабатываются fail-closed.
7. TLS-проверку не отключать. Прокси допускается только по явно утверждённому контракту.
8. Секреты не попадут в stdout, repr, UI, RAW-диагностику или GitHub evidence.
9. При незавершённых обязательных S3b/S3c/S9/S13a или неутверждённом provider contract реальная отправка остаётся заблокированной.

Если безопасная реализация определённой части требует отдельного решения по §5а, представить точный blocker и минимальный successor. Не обходить его ради формального READY.

## 5. P2 — настоящий пользовательский маршрут

Проверять интеграцию именно в штатном Web Alarm Ultra с существующими STANDARD/TEST точками запуска. Не переименовывать CMD или ярлыки.

Обеспечить сохранность:

- выбора модели внутри конкретного чата;
- пользовательского сообщения и ответа;
- фактического состояния отправки;
- различия между подтверждённым usage и UNKNOWN;
- истории после F5/повторного открытия;
- корректного отказа без REAL authorization;
- независимости соседних чатов и Workspace.

Не менять без отдельной необходимости визуальную компоновку, размеры и порядок кнопок.

Если пользовательское взаимодействие меняется, подготовить короткую инструкцию для личной GUI-проверки владельца. Самостоятельно не присваивать `USER UX ACCEPTED`.

## 6. P3 — проверки и доказательства

Самостоятельно выполнить инженерный review и подходящие независимые от реализации oracle:

- один разрешённый synthetic путь через настоящий application entrypoint;
- неправильная модель, неподтверждённые caps, неподходящий scope;
- подмена body/endpoint после admission;
- недопустимый owner и forged authority;
- повторный attempt, cancel и timeout;
- UNKNOWN после SENT;
- сбой OAuth, HTTP, terminal и сохранения;
- restart/reopen и сохранность liability;
- отсутствие внешних запросов без OWNER GO;
- регрессия H29–H34, S1/S2/S3a по применимости;
- негативные мутации ключевых защит.

Проверки должны включать фактический application path, а не только новые искусственные функции.

Сохранить первые FAIL, точные counts, команды, логи, исходные SHA и ограничения. Не объявлять REAL PASS по результатам MockTransport.

Независимые GitHub Actions Windows испытания выполняет затем ChatGPT-координатор.

## 7. Приёмочные статусы

Разделить:

- `TECHNICAL READY / NOT READY`
- `PROVIDER CONTRACT VERIFIED / PARTIAL / UNKNOWN`
- `REAL FACTORY GUARDED / BLOCKED`
- `REAL APPLICATION OFFLINE PASS / NOT RUN`
- `USER UX PENDING`
- `LIVE NOT RUN`
- `RELEASE HOLD`

До отдельного OWNER GO реальные запросы запрещены, даже если подготовлена вся инфраструктура.

## 8. Результат сдачи

Передать в отчёте:

1. Что реализовано и какие файлы изменены.
2. Один сквозной путь по штатному приложению.
3. Подтверждённый и неподтверждённый provider contract.
4. Server REAL authority и доказательства невозможности обхода.
5. Все тесты, первый RED, evidence и MANUAL ENGINEERING REVIEW.
6. Какие predecessor gates приняты, а какие остаются OPEN.
7. Минимальный план реального пользовательского smoke: сборка, 2–6 действий, ожидаемый отклик, ограничения, остановка и rollback.
8. Точные условия, при которых можно будет запросить OWNER GO на первый короткий LIVE.
9. DOC IMPACT и NEXT.

Завершение — только через штатный `finish`, без Git-операций, без изменения чужих задач и без самостоятельного обновления общих документов.

**Главная цель:** не ещё один синтетический макет, а технически подготовленная возможность получить **первый настоящий ответ GigaChat внутри Web Alarm Ultra**, сохранив обязательную безопасность и контроль владельца.
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
