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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001` · перенесено 2026-11-06 · SHA-256 копии `7bcad5bb37ca2d64392e53ab574d3010afc90a4dae3f0cfd76f69bf90744147c` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001/handoff_task.md` · отчёт `reports/CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001/report.md` · HISTORY ID `H-CODEX-000017` · запись `reports/CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001/task_record.json`


**TASK ID:** `CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001`

## Web Alarm Ultra — Stage 4B: безопасная интеграция общего сервиса с Turn (OFFLINE)

**Исполнитель:** Codex 007  
**Координатор / independent verifier:** ChatGPT  
**Приоритет:** HIGH  
**ARCH CLASS:** Ultra Chat / Turn Integration / Offline Provider Adapter  
**Программа:** №37, этап 4  
**Исходная ревизия:** `main@3b9dbec3923de839ce1020df997f4df6ff826c19`  
**Связанный FOLLOWUP:** `FOLLOWUP-WUA-S4A-INTEGRATION-001`

### 1. Цель

Соединить созданный на Stage 4A сервис `ordinary_chat_service.py` с существующим механизмом `web_alarm/turn_service.py`.

Проверить полный цикл на синтетическом Workspace:

**Сообщение → Turn → подготовленный запрос → fake LLM → ответ → RAW/Run Store → восстановление после перезапуска.**

Подключение должно быть только в явно включаемом тестовом контуре. Существующий Stage 3 TEST и STANDARD должны продолжить работать без изменений.

**Настоящий GigaChat, OAuth, интернет и платные запросы запрещены.**

### 2. Исходное состояние

Stage 4A, `H-CODEX-000016`, принят ограниченно: реализованы проверка моделей, формирование запросов, immutable prepared request, mock transport, обработка ошибок и usage.

Stage 3, `H-CODEX-000013`, уже обеспечивает durable Turn, RAW, RUN, idempotency и восстановление. Однако его ответ сейчас фиксированный: `TEST: сообщение принято.`

В текущей реализации Turn имеются жёсткие проверки постоянного TEST-ответа и ссылок `local-test:v1`. Их нельзя просто отключить ради интеграции.

Исторический `WorkspaceBusyError` остаётся отдельным открытым риском.

### 3. Разрешённые файлы

**WRITE:**
- `web_alarm/turn_service.py` — только минимальная поддержка нового явно включаемого offline-сценария;
- новый `web_alarm/ordinary_chat_test_adapter.py` — при необходимости;
- новый `test_web_alarm_ultra_chat_turn_s4b.py`;
- отчёт и evidence в `reports/CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001/`;
- персональная карточка — исключительно штатным `finish`.

**READ-ONLY:**
- `ordinary_chat_service.py`;
- `test_ordinary_chat_service.py`;
- `context_storage.py`;
- `run_store.py`;
- `model_registry.py`;
- `gigachat_transport.py`;
- `web_alarm/ultra_chat.py`;
- существующие тесты Stage 3;
- №37, №18, №36/36.1/36.3 и профильные контракты хранения.

**Не менять** HTTP routes, UI/JavaScript, Tkinter, B2, production transport, реальные секреты, CI workflow и настройки запуска.

Если для безопасной реализации обязательно потребуется изменение вне WRITE-scope, остановить соответствующую часть, показать доказательство и запросить отдельное расширение задачи.

### 4. Реализация

**A. Контракт подключения**

Сначала определить минимальный интерфейс между Turn и S4A.

Сохранить одного владельца жизненного цикла Turn: его идентичности, состояния, RAW, RUN, события и восстановление.

`ordinary_chat_service.py` не должен становиться второй машиной состояний и не должен самостоятельно писать в Workspace.

**B. Явное включение OFFLINE**

Новый путь доступен только:
- для одноразовых синтетических Workspace из allowlist;
- при явной передаче тестового адаптера;
- с fake/mock transport;
- без физической сети, OAuth и credentials.

При отсутствии адаптера старое поведение Stage 3 должно остаться прежним.

Изменение глобального выбора модели не должно менять уже принятый Turn.

**C. Подготовка и исполнение**

Использовать существующие `prepare_request()` и `execute_request()`.

Фиксировать модель, контекст, ограничения и ссылку на подготовленный запрос до разрешения попытки. После записи события начала попытки нельзя незаметно пересобрать запрос по новым настройкам.

Вызывать fake transport только после устойчивой фиксации необходимых фактов Turn, вне длительной блокировки Workspace.

Не создавать новых конкурирующих писателей и не вводить автоматические повторы отправки.

**D. Результат и восстановление**

Проверить фиксацию полученного текста, идентичности попытки и доступного usage через существующие механизмы.

Нельзя просто убрать проверки `ANSWER`, `REFERENCES` или RAW integrity. Для нового режима необходимо обеспечить собственный проверяемый durable-контракт, сохранив совместимость со старыми Turn и RAW.

Если новый формат требует версии схемы, вводить её явно и без переписывания прежних записей.

После сбоя:
- второй user RAW не создаётся;
- второй assistant RAW не создаётся;
- начатая попытка не исполняется автоматически повторно;
- неизвестный результат остаётся `UNKNOWN`;
- поздний ответ после отмены не становится успешным;
- неправильные данные приводят к безопасному отказу.

**E. Ошибки**

Отдельно обработать:
- invalid request/model/context;
- отказ fake transport до выполнения;
- ошибку или timeout после начала;
- некорректный ответ;
- отсутствие или повреждение usage;
- отмену и восстановление.

Успешный результат допускается только при согласованности durable evidence и RAW. Неизвестный расход не превращать в ноль.

### 5. Проверки

Создать адресные тесты, которые доказывают:

1. Новая цепочка действительно вызывает общий S4A-сервис, а не старый `_imitate()` с фиксированным ответом.
2. Конкретная зарегистрированная модель превращается в правильный `provider_model_id`.
3. Fake-ответ сохраняется и читается после повторного открытия.
4. Два одинаковых запроса с одним idempotency key не дают двух попыток или RAW.
5. Конфликт ключа отклоняется.
6. Два параллельных писателя не создают два успешных исполнения.
7. После restart/controlled crash отсутствует скрытый replay.
8. Отмена и поздний ответ не порождают ложный SUCCESS.
9. Несоответствие RAW, RUN, модели, ссылки на запрос или результата выявляется.
10. Неверный ответ, missing/partial usage и ошибка транспорта безопасно классифицируются.
11. Существующий Stage 3 TEST полностью сохраняет свой контракт.
12. STANDARD и недопущенные Workspace не получают возможности отправки.
13. Реальных network/OAuth/credential operations — 0, с отрицательными контролями.

Тесты — на временных Workspace, с точными oracle и сравнением исходных данных до/после.

Запустить новые тесты, существующие Stage 3 и S4A regressions, а также применимые проверки общего хранилища. Полную дополнительную регрессию выбирать по реальному риску; исторический intermittent FAIL не скрывать повторным PASS.

Отчёт должен содержать команды, версию Python/OS, source SHA, PASS/FAIL/ERROR/SKIP, первые отрицательные результаты, фактический coverage и `NOT RUN`.

### 6. Критерии сдачи

**READY FOR INDEPENDENT VERIFICATION**, если:
- OFFLINE Turn использует настоящий общий S4A-сервис;
- fake-запрос и ответ устойчиво проходят через существующее хранилище;
- восстановление и защита от повторного исполнения работают;
- все старые Stage 3 TEST-контракты сохранены;
- runtime без нового адаптера не меняет поведения;
- физическая сеть, OAuth и реальные провайдеры не задействованы;
- тесты и доказательства опубликованы в отчётном пакете.

**PARTIAL / BLOCKED**, если интеграция потребует изменения общего Run Store, B2, HTTP или других файлов вне разрешённого scope. В таком случае сохранить диагностику, ничего небезопасного не включать и передать конкретный NEXT.

Не объявлять весь этап 4 завершённым. Браузерная и Tkinter-интеграция, реальный sender и бюджетные ворота остаются отдельными решениями.

### 7. Сдача и документация

Подготовить `report.md`, `manifest.json` с SHA-256 и evidence. В отчёте указать:
- фактически изменённые файлы и архитектурный контракт;
- результат интеграции и регрессии;
- ограничения и OPEN;
- влияние на переносимость;
- какие проверки не выполнялись;
- следующий безопасный шаг.

Выполнить штатный `tools/task_slot_rotate.py finish` по точному TASK ID, подтвердить ROTATED/readback и получить HISTORY ID от скрипта.

**Одна TASK — один итоговый коммит пользователя.**

Не выполнять Git/GitHub, включая чтение, без отдельного разрешения. Не изменять БЛОКИ 2–4, общий №001/05/06/34/40. Не включать настоящие LLM, Colibri, MCP, платную отправку, STANDARD sending, Stage 5+ или Blueprint execution.

**Итог:** работоспособный ограниченный OFFLINE Turn → S4A → fake transport → durable response, с тестами и безопасным восстановлением, либо документально доказанный блокер интеграции.
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
