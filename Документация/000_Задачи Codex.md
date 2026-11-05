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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001` · перенесено 2026-11-05 · SHA-256 копии `6ad32e2e68c145bca38a04429b94ab54f67172430d4b369491210b5b7edd75bd` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/report.md` · HISTORY ID `H-CODEX-000013` · запись `reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/task_record.json`

**TASK ID:** `CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001`

**Название:** Web Alarm Ultra — Stage 3: первая отправка сообщения, устойчивый Turn и восстановление

**Исполнитель:** Codex 007  
**Координатор / независимый verifier:** ChatGPT WEB23  
**Приоритет:** HIGH  
**Режим:** реализация Stage 3 в изолированном TEST, без реальных LLM-запросов.

## 1. Основание и цель

Продолжить реализацию утверждённого этапа 3 документа №37 после устранения блокеров Run Store.

Подтверждённые зависимости:

- `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001`, `H-CODEX-000012` — исправление Run Store.
- Независимый Windows CI `41885808568` — 53 Run Store/audit + 3 Stage3 prerequisite PASS.
- `CODEX-WUA-CHAT-S3-TURN-RECOVERY-001` — предыдущее диагностическое поручение, завершённое без реализации Turn.
- `FOLLOWUP-WUA-S3-TURN-IMPLEMENTATION-001` — действующее открытое продолжение.

**Цель:** пользователь вводит сообщение в Ultra Chat, отправляет его в TEST-режиме, получает детерминированный ответ от локального имитатора и видит сохранённый диалог после перезапуска.

Реализация не должна создавать вторую систему хранения, обходить общий Run Store или менять архитектуру Web Alarm TASK.

## 2. Матрица чтения

| Источник | Точный раздел / назначение | Объём |
|---|---|---|
| Персональная `000_Задачи Codex.md` | Правила, назначенный БЛОК 1, относящийся БЛОК 4 | Обязательно |
| №08 | Действующий старт, без архивных адресов | Обязательно |
| №34 | Текущий контекст Stage 3, NEXT и ограничения | Адресно |
| №40 | Текущая занятость направлений, shared scope | Обязательно перед записью |
| №37 | §2.2–2.4, «Этап 3. Отправка сообщений и восстановление» | Обязательно |
| `reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/turn_contract.md` | Кандидат контракта Turn | Полностью |
| `reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/risk_test_matrix.md` | Негативные тесты и риски | Полностью |
| №18 | `finish`, сохранение истории, передача и ограничения | Применимые разделы |
| №36, №36.1, №36.2 | Контракты тестирования Web Alarm | Применимые разделы |
| №36.3 | Только если затронут корневой Ultra runtime | По условию |

Не перечитывать полные архивы №001, №05, №06 и все старые `reports`.

## 3. Реализовать устойчивый Turn

Использовать существующие Workspace/Chat ID и `context_storage.commit_raw_message()`.

Минимальные требования:

1. Постоянные `turn_id`, `message_id`, `idempotency_key`.
2. Один пользовательский запрос — один устойчиво принятый Turn.
3. Повтор с тем же ключом и содержимым возвращает прежний результат.
4. Тот же ключ с другим содержимым вызывает конфликт без записи.
5. Два одинаковых текста с разными ключами являются разными сообщениями.
6. Фиксированные ссылки на модель, контекст и разрешённую конфигурацию. Тестовый имитатор должен быть явно обозначен; неизвестная ссылка — безопасный отказ.
7. Явные состояния принятия, выполнения, завершения, ошибки, отмены и неопределённого результата.
8. После перезапуска не появляются дубли RAW или ложные успешные ответы.

RUN и события попытки хранить только через существующий `run_store.py`.

Не добавлять независимый `attempts.jsonl` или параллельный RUN store.

## 4. HTTP и локальный TEST-имитатор

Добавить минимальный локальный маршрут принятия сообщения, чтения Turn и явной отмены с использованием существующей авторизации Ultra Chat.

Требования:

- Проверка Workspace/Chat ownership.
- Отдельные права чтения и записи.
- Защита Origin, токена, метода, размера и схемы запроса.
- Безопасная работа при двух конкурентных HTTP-клиентах.
- GET не запускает выполнение.
- Потерянный HTTP-ответ не приводит к повторному исполнению.
- Локальный имитатор возвращает фиксированный проверяемый ответ, не обращаясь к LLM.
- Неопределённость выполнения не превращается автоматически в SUCCESS.

Не использовать `run_agent_task()` как обычную отправку чата.

## 5. Подключить отправку в Ultra Chat UI

В TEST-режиме:

1. Пользователь открывает существующий Chat.
2. Вводит сообщение в поле ввода.
3. Нажимает «Отправить» либо Enter с предусмотренной обработкой многострочного текста.
4. Видит собственное сообщение и ответ имитатора.
5. Видит явный статус ожидания, ошибки или неопределённости.
6. После закрытия и повторного открытия восстанавливается та же история.

Повторный клик или сетевой retry не создаёт второе пользовательское сообщение.

**STANDARD не должен незаметно получить возможность отправки реальным моделям.** До отдельного разрешения провайдерная отправка остаётся отключённой. TEST должен иметь явную маркировку.

Не выполнять редизайн панели Workspace/Chat в этой задаче.

## 6. Разрешённый write-scope

Допускаются минимально необходимые изменения:

- `web_alarm/ultra_chat.py`
- `web_alarm/server.py`
- `web_alarm/ui.py`
- новый `web_alarm/turn_service.py`, если отдельный модуль оправдан архитектурой
- относящиеся `test_web_alarm_ultra_chat_*.py` и JS-тесты Ultra Chat
- `reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/`

`context_storage.py`, `run_store.py`, `audit_storage.py`, корневой runtime Ultra, EVM и реестры моделей — READ-ONLY по умолчанию.

Если для корректной реализации необходимо изменить общий storage или Run Store, сначала представить точный блокер, ожидаемую правку и минимальное расширение scope. Без согласования не изменять.

## 7. Обязательные тесты

На изолированных синтетических Workspace:

- обычная отправка и получение ответа имитатора;
- повтор, двойной клик, два клиента, конфликт idempotency key;
- перезапуск и восстановление истории;
- сбой до/после RAW, потеря HTTP-ответа;
- два конкурентных writer;
- поздний результат после отмены;
- ошибка диска, повреждённая запись, неверные ссылки;
- чужой Workspace/Chat, недействительный токен, Origin и oversized body;
- проверка отсутствия любых физических обращений к провайдерам;
- неизменность ранее существовавших RAW и истории;
- регрессия исходных трёх Stage3 prerequisite tests;
- применимые Python, JS, HTTP/UI и Windows-проверки.

Не скрывать SKIP, ERROR, flaky и первые неудачные результаты.

Все данные тестов — в disposable TEMP. Не использовать пользовательские Workspace, реальные секреты, OAuth и платные API.

## 8. Ограничения

Запрещено без нового USER GO:

- Подключать Ollama, Colibri или GigaChat.
- Выполнять реальные LLM-запросы.
- Реализовывать Stage 4 и выше.
- Изменять Blueprint LLM или EVM.
- Активировать MCP или платные маршруты.
- Изменять живое хранилище и пользовательские настройки.
- Выполнять Git/GitHub операции, включая чтение, от лица локального исполнителя.

При использовании TEST соблюдать действующий регламент и проверенный возврат к STANDARD.

## 9. Сдача

Подготовить `report.md`, манифест, исходные и финальные тестовые результаты, evidence, список изменённых файлов, точные FAIL/SKIP/NOT RUN и все оставшиеся OPEN.

Показать проверяемый сценарий:

`Создать тестовый Chat → отправить сообщение → получить ответ имитатора → перезапустить → увидеть тот же диалог`.

После полного завершения тестов исполнитель штатно запускает `tools/task_slot_rotate.py finish`, получает HISTORY ID, проверяет запись и освобождение БЛОКА 1. Не назначать HISTORY ID вручную.

Итоговый пакет пользователь публикует в GitHub, затем передаёт WEB23 на независимую приёмку. Координатор обновляет короткие индексы, FOLLOWUP, №06, №34, №37 и №40 по фактическим результатам.

**PASS Stage 3 не означает разрешение реальной отправки LLM.**
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
