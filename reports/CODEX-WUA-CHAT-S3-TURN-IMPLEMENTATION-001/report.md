# CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001

**RESULT READY / AWAITING INDEPENDENT VERIFICATION** · Codex 007 · 05.11.2026. Независимая приёмка: **ChatGPT WEB23**, ещё не выполнена.

Реализована отправка в явно обозначенный локальный **TEST-имитатор**: устойчивый Turn, user/assistant RAW, scoped idempotency, чтение и отмена, восстановление после прерывания через существующий Run Store. В браузере проверены отправка кнопкой и Enter, ответ и история после reload. Отдельный HTTP smoke проверяет фактический перезапуск сервера и неизменность RAW.

STANDARD сохраняет отключённый composer. Реальных LLM, Colibri/Ollama/GigaChat, paid routes, MCP и `run_agent_task()` здесь нет. Stage 4+ не реализованы и не разрешены.

## Назначение / база / shared scope

Назначение подтверждено точным TASK ID в БЛОКЕ 1. Прочитаны действующие правила карточки, адресный №08/34/40, §2.2–2.4/Stage 3 №37, предыдущие `turn_contract.md` и `risk_test_matrix.md`, применимые №18/36/36.1/36.2 и реальные контракты `context_storage`/Run Store/Ultra Chat HTTP/UI. GitHub Actions ID/предыдущий verdict взяты из локальных документов; Git/GitHub локально не открывались.

№40 содержит подтверждение WEB23 Windows prerequisites и прежний HOLD до нового USER GO. Этот USER GO и нынешний БЛОК 1 разрешают только текущий TEST Stage 3. Карточка Claude адресно проверена: прежний P9 / PROPOSED / SLOT HOLD; нового пересекающегося назначения на UI/server/Ultra Chat не обнаружено. Корневой shared storage не менялся. Нужды в расширении scope или блокера за его границей для этого TEST-контракта не установлено.

Перед изменениями сохранены 11 исходных файлов `.source.txt`, их sizes/SHA-256 и baseline 605 защищённых файлов. Незакоммиченная база сохранена как существовала; reset/checkout/перезаписи чужих правок не выполнялись. Прежние report/evidence использовались только для чтения; guard скопирован в текущий пакет.

Изменённые исходники:

- `web_alarm/turn_service.py` — новый компактный сервис поверх существующего storage/RUN; не новый store.
- `web_alarm/ultra_chat.py` — Turn routes и делегирование с прежней регистрацией/ownership.
- `web_alarm/server.py` — опциональный локальный TEST allowlist и capability; прежние HTTP gates сохранены.
- `web_alarm/ui.py` — TEST composer/status/retry/cancel без переделки Workspace/Chat панели.
- `test_web_alarm_ultra_chat_turn_service.py`, `test_web_alarm_ultra_chat_turn_http.py` — 27 новых Python cases с дополнительными fault/platform subcases.
- `test_web_alarm_ultra_chat_ui.js` — 3 новых S3 cases; прежние 37 сохранены.

`context_storage.py`, `run_store.py`, `audit_storage.py`, launcher/config и скрипт finish read-only; hashes совпадают с baseline. Отдельных attempts/turn journals, провайдерного адаптера, реестра моделей или Web Alarm TASK не добавлено.

## Реализованный контракт

Полный контракт — `turn_contract.md`; матрица рисков/оракулов — `risk_test_matrix.md`.

Turn имеет детерминированные IDs от Workspace ID + Chat ID + retry key. Компактная запись лежит в `turn` существующего RUN summary и содержит fingerprint, IDs, frozen references, state/cancel flag. Все execution events — в SERVER stream того же RUN через Run Store. RAW публикуется только через `commit_raw_message()` с теми же постоянными ID. Полного текста запроса в summary нет. Ответ имитатора фиксирован: **`TEST: сообщение принято.`**

Frozen references ограничены `local-test:v1`, `empty:v1`, `test-only:v1`. Это разрешённая конфигурация test double с пустым контекстом; произвольные/реальные модельные ссылки отвергаются. EVM preference не вызывает модель и не меняет принятый Turn. Реальная сборка контекста/transport относится к последующим этапам, не подменяется тестовой реализацией.

Порядок: ACCEPTING intent → idempotent user RAW → READY → повторная проверка фактов → ATTEMPTING + durable start → один вызов имитатора вне lock → verified RUN result → idempotent assistant RAW → SUCCEEDED. Один Workspace shared OS lock ядра сериализует изменяющие операции. Результат возвращается только после необходимых устойчивых записей и проверки связки. Разные ключи при одинаковом тексте дают разные сообщения; прежний ключ с другим fingerprint получает 409 без перезаписи.

GET только читает/проверяет факты, не ремонтирует и не исполняет. Для согласованного чтения Turn используется существующий lock, поэтому busy/read-inaccessible lock даёт явный 503. Без локально известного активного владельца ATTEMPTING проецируется UNKNOWN; отдельный процесс также может видеть консервативный UNKNOWN до завершения первого. Это не разрешает новый вызов.

Явный replay того же POST может вызвать безопасный `recover_run_records()` и завершить публикацию уже durable result/assistant RAW. Начатая попытка без результата повторно не запускается. ACCEPTING после сбоя требует первоначального тела; тот же message ID не дублируется. Отмена READY → CANCELLED; отмена после старта → UNKNOWN/cancel_requested. Поздний результат записывается как discarded и не публикует assistant RAW. Проекция сверяется с execution facts; повреждённое READY не может разрешить новый вызов.

HTTP маршруты находятся под прежним `/ultra/chat/workspaces/{wa_id}/chats/{chat_id}/turns`: POST accept/replay, GET `/{turn_id}`, GET `/by-key/{key}`, POST `/{turn_id}/cancel`. Сохранены отдельные read/write tokens, single Origin для POST, host/fetch metadata, query/method/body/content-type и ownership проверки. Общий body ≤4096 bytes, text ≤2048 UTF-8 bytes. Tokens и filesystem paths в Turn-ответах не раскрываются.

UI хранит в браузере только scoped retry key, без текста/токенов. Busy guard защищает двойной click; перед ручным повтором читается прежний Turn. После reload выполняется GET lookup без POST. При неопределённости ключ не теряется; новый отдельный запрос требует отдельной явной кнопки. Enter отправляет, Shift+Enter/IME не отправляют. STANDARD не получает отправку через новый маршрут: TEST root allowlist по умолчанию пуст и не меняется через HTTP.

## Тесты / среда / исходные отрицательные результаты

Среда: Windows 10 build 19045, Python 3.12.10 x64, pytest 9.1.1, Node v22.20.0. Exact commands, durations, source sizes/SHA, exits/counts и полные stdout/stderr: `evidence/*final*.json/.txt`. Новые suites запускались стандартными unittest/pytest/Node runners, без indiscriminate discovery.

| Прогон | Фактический итог | Exit |
| --- | --- | --- |
| `initial_red` до реализации | 2 ERROR: отсутствующий модуль (test-first контракт новой функции) | 1 |
| `iteration01` | 2 ERROR: пропущен обязательный `max_bytes` в bounded core read; исправлено в новом сервисе | 1 |
| `http_iteration01` | 5 PASS / 1 ERROR: неверное имя тестового helper `.get`; исправлено на `.read` | 1 |
| `stale_projection_red` | 1 FAIL: повреждённое READY повторно вызвало имитатор; исправлена сверка с facts | 1 |
| Turn/HTTP final1, final2 | 23 PASS каждый | 0 |
| Turn/HTTP final3 | 26 PASS | 0 |
| **Turn/HTTP final4** | **27 PASS / 0 FAIL/ERROR/SKIP** | **0** |
| Run Store + compatibility + AuditStorageTests | **62 PASS** | **0** |
| Три исходных Stage3 prerequisite oracle | **3 PASS** | **0** |
| Python regression final1/final2/final3 | **166 PASS / 5 SKIP** каждый, 171 tests | **0** |
| JS regression final1/final2 | **161 PASS** каждый | **0** |
| In-memory Python compile | **6 PASS**, pyc не создавались | 0 |
| Финальный TEST demo smoke | Create → send → server restart → те же два RAW/история | **0** |

Без сложения повторов итог **424 tests = 419 PASS / 5 SKIP / 0 FAIL / 0 ERROR**. Compile, GUI и smoke — дополнительные проверки, не прибавлены к этому числу. Первые отрицательные результаты сохранены и не заменены зелёными логами. Новый real product RED имеет вызов mock как trigger, затем новый test проверяет отсутствие вызова и byte-identical snapshot.

Покрыты: обычная отправка; same/different key/body; два HTTP клиента; два процесса/два service instance; fault до/после user RAW; реальные process exits 71/72/73/74 по фазам; durable result lost ACK; реальная потеря HTTP reply; restart; отмена до старта/после старта с barrier; late result; ошибка имитатора; повреждение RAW/RUN/проекции; неверные refs/Unicode; чужие Workspace/Chat; неallowlisted root; методы/query/token/Origin/oversized body; Windows junction с неизменным внешним synthetic marker; сохранность прежнего RAW.

Guard ставится до Python runtime imports и наследуется children: внешние sockets/DNS, Git metadata/executables и неразрешённые executables блокируются. Во всех сохранённых guard receipts **0 denials**. Дочерний `os._exit` намеренно не пишет atexit receipt. Loopback разрешён для fixtures; это не OS firewall. Node VM tests используют mocked fetch, Python guard не инструментирует сам браузер/Node. Физическая отправка к провайдерам отсутствует по source review константного имитатора и фактическим execution paths; никакого provider/OAuth/MCP dispatch не реализовано/не вызывалось.

Повторить из корня с новым label:

```powershell
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/run_checks.py turn --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/run_checks.py prerequisites --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/run_checks.py runstore --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/run_checks.py python --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/run_checks.py js --label review1
```

## Проверяемый TEST-сценарий / браузер

```powershell
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/demo_turn_chat.py --seconds 600
```

Открыть напечатанный loopback URL. Будет отдельный синтетический Workspace/Chat, можно создать ещё один Chat кнопкой «+». Ввести сообщение, нажать «Отправить» или Enter, увидеть фиксированный ответ, перезагрузить страницу и увидеть ту же историю. TEMP удаляется после ограниченной длительности/завершения; никакой пользовательский Workspace не используется. Для автоматического сценария с **настоящим server restart**: тот же script с `--smoke`.

Это адресный TASK TEST harness внутри разрешённого отчётного scope. Новый профиль launcher не добавлялся, `Start_WebAlarm.bat`/`launch_config.json` всё время **STANDARD**. Ни пользовательский сервер, ни его настройки не переключались.

Реальная браузерная проверка выполнена через `computer-use` / in-app browser на Windows-хосте, на двух собственных TEMP servers: отправка кнопкой, затем отдельная отправка Enter; после reload видны user text и ответ. Final screenshot/AX: `evidence/browser_final.png`, `browser_final_ax.txt`, метаданные `browser_evidence.json`. Браузер нашёл оставшиеся старые подписи «сообщения не отправляются»/«модель не выбрана» в TEST: они исправлены только для TEST; STANDARD копия/поведение сохранены. Браузерный happy path предшествует последней service-only сверке stale READY; итоговый UI byte-identical, финальный сервис после сверки проверен `turn_final4` и `demo_final`. Не заявляется GUI coverage всех негативных случаев/desktop Chrome/Tk. Оба TEST server остановлены, TEMP cleanup подтверждён.

## MANUAL ENGINEERING REVIEW

1. Прослежены последовательности summary intent → user RAW → attempt start → result → assistant RAW → terminal projection. Отвергнут автоматический повтор ATTEMPTING: он был бы небезопасен после потери владельца. Возобновляется только публикация уже доказанного результата; до user RAW принятие не подтверждается.
2. Вместо нового chat/attempt store использован компактный Turn field текущего RUN summary и существующие API/OS lock. Начальный пустой RUN после crash не считается принятым request; тело/ключ фиксируются до RAW. `create_run_summary` не вызывается поверх существующего summary, чтобы не сбрасывать Turn.
3. Проверены гонки двух владельцев и cancel/result: shared lock резервирует единственное исполнение; имитатор выполняется вне lock; завершение заново читает cancel/state. Поздний result не получает assistant RAW. Другой процесс может консервативно видеть UNKNOWN, не пытаясь стать новым владельцем.
4. Проверены повреждения, filenames/ownership и fail-closed readback. Дополнительная adversarial гипотеза «READY summary противоречит уже сохранённому start» подтверждена отдельным RED и устранена до сдачи. Перед execution проверяются RAW и event facts; terminal success также зависит от result/RAW, не только enum/callback.
5. Просмотрены client races: key записывается до POST; double-click закрыт busy guard; переключение Chat защищено epoch; потерянный ответ сохраняет key; reload не делает POST; ручной retry сначала GET. Plaintext и capabilities не пишутся в localStorage. Для UNKNOWN новый ключ требует явного действия.
6. Проверены границы TEST: только локально заданные roots, default empty, loopback/read/write flags; body refs не дают transport или произвольный context path. Реальные EVM/model предпочтения не активируют отправку. Отдельные read/write capabilities не взаимозаменяемы.

## Сохранность / OPEN / NOT RUN

- **595/595 файлов текущего пользовательского storage baseline неизменны**: `.ultra` 586 и `Чат_pro` 9. Сравнивались набор имён, размеры и SHA. Папка `Чат_Pro_01` в текущей исходной базе отсутствовала; число из вчерашней задачи не переносилось по памяти. Synthetic tests дополнительно доказывают неизменность старого RAW при новом Turn/replay.
- Из 10 editor-state файлов изменился `.obsidian/workspace.json`; агент туда не писал, процесс не атрибутирован, изменение не откатывалось. Receipt отдельно показывает user storage и editor delta; нельзя заявлять совпадение всех 605 файлов.
- Все 11 baseline source copies сохранны; read-only core/audit/launcher/config/finish sources совпадают. Существующие UX fixes, первый Chat, rename/save и их evidence не переписывались.
- 5 SKIP — прежние native file/directory symlink tests из-за отсутствующего Windows privilege; реальные junction/hardlink prerequisites выполнены. Права ОС не изменялись.
- Shared-core final same-user TOCTOU residual, старый staging crash gate, полный P9 runtime/portability и `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001` остаются OPEN. В этих трёх текущих Python прогонах picker прошёл; прежний intermittent отказ этим не закрывается.
- GET Turn требует доступного shared lock и может вернуть busy/503. Active-owner visibility между server processes консервативна (UNKNOWN); собственного фонового recovery/очереди/автореплея нет. Corrupt/orphan сверх возможностей существующего Run Store не ремонтируется произвольно.
- TEST ограничен пустым frozen context и фиксированным имитатором. Реальная модель/контекстная сборка, provider accounting/budget/streaming/cost/cancel относятся к отдельным утверждённым этапам. Нельзя распространить этот author result на provider sending.
- **NOT RUN:** hardware power loss/сетевые файловые системы, clean-machine portability, native Tk/picker GUI, independent CI/runtime, весь Ultra/Web Alarm discovery и Git-dependent `test_final_audit*`, live Workspace write, реальные LLM/OAuth/Colibri/GigaChat/paid/MCP. Браузер проверен bounded happy path, не полный отрицательный GUI matrix.

## DOC IMPACT / SHARED DOC DELTA / сдача

Локальные `turn_contract.md`, risk matrix, manifests/evidence документируют только текущий TEST v1. Общая документация руками не менялась. WEB23 после независимой проверки/публикации должен адресно обновить историю/№05/06/34/37/40, оценить `FOLLOWUP-WUA-S3-TURN-IMPLEMENTATION-001`, сохранить перечисленные OPEN и точно отделить TEST Stage 3 от Stage 4+/live GO. Авторский PASS tests не является independent VERIFIED.

Штатный `task_slot_rotate.py finish --no-chat-amendment --apply --headless` выполняется после готового пакета. Его фактический протокол/HISTORY ID/readback сохраняются отдельно: `evidence/finish.json`, `evidence/finish_result.json`, `finish_receipt.md`, native `task_record.json`. Этот report после регистрации остаётся неизменным; manifest обновляется отдельно.

NEXT: пользователь публикует безопасный пакет; **ChatGPT WEB23** независимо проверяет source/manifest/negative controls/Windows results и принимает в bounded scope. Реальная LLM отправка этим не разрешается.
