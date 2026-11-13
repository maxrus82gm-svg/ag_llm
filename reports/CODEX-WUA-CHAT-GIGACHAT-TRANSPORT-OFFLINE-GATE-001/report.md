# H33 — GigaChat transport OFFLINE gate

TASK ID: `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001`.
Результат автора: **P0+P1 BOUNDED OFFLINE PASS / RESULT READY / AWAITING INDEPENDENT VERIFICATION**.
Дата: 2026-11-13. Исполнитель: Codex 007. Локальный проект: `M:\GitHub\ag_llm`.
HISTORY ID и результат штатного finish: адресная запись [task_record.json](task_record.json), [closeout.json](closeout.json) и [handoff_task.md](handoff_task.md). Эти файлы создаются штатной сдачей; настоящий report после регистрации не изменяется, его SHA проверяется readback.

Подготовлен HTTP-адаптер формы GigaChat поверх принятой H32-цепочки. Проверены точные HTTP bytes, допуск S2/S3a, единичная отправка через MockTransport, результат/ошибки, Turn/RAW/usage/reopen. **REAL выключен; полноценный S3b и независимая приёмка не объявляются завершёнными.**

## Основание и инвентаризация

Работа по БЛОКУ 1, №08/18, №20 §5а и №37 §3а шагам 3–4; учтены текущие №34/40, релевантные FOLLOWUP №05, Windows-инструкция №22, авторская и независимая сдачи H32, ограничения H30/H31. Нормативные документы не исправлялись. Штатная ротация собственной карточки — отдельное разрешённое исключение.

База `main@72f2ff53051104fe9b084624a39be5f3dcc5a09a` / №591 взята из назначения. Git не разрешён и не запускался; HEAD/ветка/чистота всего checkout независимо не подтверждены. Перед изменениями **9/9 исходных H32 SHA совпали** с принятым manifest: [base_fingerprints.json](evidence/base_fingerprints.json). Чужие изменения не перезаписывались.

До инженерных правок сохранена [карта физических отправок](route_inventory.md). Она охватывает семь старых GigaChat chat-completion sites, OAuth, динамические Ordinary/fixture dispatch, model checker, loopback и ручные инструменты. S1 подтвердил полный ожидаемый census. Новый `client.stream` оставлен в консервативной категории UNKNOWN и явно внесён в additional inventory; он не добавлен к семи принятым legacy LLM-sites. Возврат endpoint-property разрешён только для точного pinned AST нового адаптера, остальные endpoint flows по-прежнему проверяются.

Старые server/planner/verifier/compressor отправки используют `json=body`, собственные тайм-ауты/учёт и не получили H33-защиту автоматически. Весь S3b остаётся OPEN. Legacy OAuth способен включить ответ провайдера в ошибку отсутствующего токена; исправление вне текущего OFFLINE-пути, обязательный gate перед REAL.

## REUSE CHECK и изменения

Использованы существующие Model Registry, PreparedRequest/execute_request/parse_response, S2 serializer/policy, S3a BudgetLedger, shared writer, Turn, RAW, Run Store, H29 настройки/usage и существующий веб-сервис. Policy, ledger, OAuth/cache, Registry и storage не дублированы и не изменены.

| Файл | Изменение и причина |
|---|---|
| `ordinary_gigachat_transport.py` — новый | Отсутствовала byte-oriented HTTP-граница для Ordinary; старые функции отправляли заново сериализованный dict. Добавлен один минимальный адаптер, использующий существующий CHAT_URL и общую обработку результата. Только точный OfflineHTTPFixture, только встроенный MockTransport, без network transport factory |
| `ordinary_chat_service.py` | Малый ProviderResponse envelope передаёт bounded decoded JSON и статус в существующий parser. HTTP error не превращается в успешный текст, корректный supplied usage сохраняется |
| `web_alarm/ordinary_chat_bridge.py` | Разрешены два точных OFFLINE-типа: прежний in-memory и новый HTTP fixture. Endpoint входит в сохранённый admission snapshot; ответ/usage проходит общий core |
| `web_alarm/turn_service.py` | Эфемерный server-only `_TurnAdmission` связывает точный owner/transport/limits с существующим durable admission. Добавлен повторный readback SENT/binding/cancel непосредственно у HTTP-границы; provider status имеет существующую terminal-категорию provider_error |
| `web_alarm/ultra_chat.py` | Внутренний параметр exact synthetic fixture; browser/config/env и launcher его не принимают. REAL capability остаётся false; по умолчанию прежний H32 transport |
| `test_web_alarm_gigachat_transport.py` — новый | Adversarial и loopback Web API проверки полной цепочки |
| S1/S2 test contracts | Адресно согласованы новый stream site/importer, exact AST/reference census и три ingress AST. Граф не исключён из проверки, неизвестные consumers/изменённые gates остаются RED |

В [source_changes.patch.txt](evidence/source_changes.patch.txt) находится локальный diff без Git. [manifest.json](manifest.json) содержит SHA и полный перечень файлов. Не добавлены второе ядро, ledger, OAuth cache, реестр моделей, глобальный бюджет Workspace или новый пользовательский launcher.

## Транспорт и сохранность допуска

1. Общий core готовит запрос. S2 serializer формирует неизменяемые UTF8 bytes; snapshot связывает bytes/hash/model/endpoint/policy revision и существующий Turn binding.
2. Только capability точного активного TurnService с точным adapter/transport и prepared limits может вызвать reserve → readback → fresh SENT → readback. Dict/receipt/lambda/Boolean, чужой owner, повтор capability и прямой вызов без capability отвергаются до token boundary и HTTP.
3. После допуска вызывается фиксированный synthetic token-provider вместо существующего real get_access_token. Чтения credentials, OAuth, cache/refresh/fallback нет. При подмене synthetic token значение не уходит в HTTP.
4. HTTPX получает `content=wire`, доверенный CHAT_URL и Bearer/Accept/Content-Type headers. `trust_env=False`, redirects=False, явные connect/read/write/pool timeout. В коде нет создания сетевого HTTP transport; без точного fixture конструктор отказывает.
5. Непосредственно в MockTransport boundary повторно сравниваются фактические method/URL/content с допущенными bytes и проверяются текущие Turn owner/cancel/model/policy/SENT. Capability одноразовый. После token await повторный readback закрывает окно отмены или изменения binding.
6. Ответ читается с лимитом bytes, JSON/status переводятся в общий sanitized outcome. Только 200 может дать успешный assistant text. Timeout/ошибка после SENT, crash/потерянный terminal readback сохраняют консервативный unknown/liability; нет refresh/retry/автоматического освобождения резерва.
7. Существующий durable terminal readback предшествует публикации Turn/RAW/usage. Повтор ключа и reopen не создают новую отправку. Новый capability не является отдельной persistent системой разрешений: вся проверяемая история и авторитет остаются в существующем ledger/Turn.

Произвольное исполнение Python с доступом к приватным объектам не является моделью изоляции приложения. Проверенные границы — browser/config/env, неподтверждённый transport и прямые вызовы публичного byte entry без серверных полномочий. Защита процесса и exact-type checks не объявляются sandbox для вредоносного Python-кода.

## Проверки и evidence

Авторская Windows-проверка: Python 3.12.10, pytest 9.1.1, httpx 0.28.1, Node 22.20.0; [environment.json](evidence/environment.json). Плагин subtests отдельно не установлен, используется доступная реализация pytest. Точные команды, exit codes, cases и raw stdout/stderr сохранены в evidence. Применён существующий H27 process guard **до runtime imports**, без изменения его исходника. Тесты используют только synthetic TEMP roots; внешняя сеть, DNS, credentials и live-storage запрещены.

| Набор | Результат | Основное evidence |
|---|---|---|
| H33 HTTP/adversarial, final source | **18 PASS + 36 subtests PASS**, exit 0, без FAIL/ERROR/SKIP | `final_http.result.json`, `final_http.cases.json`, stdout/stderr |
| H29/H31/H32/common core/Turn/Run Store/S3a regression | **236 PASS + 220 subtests PASS**, exit 0 | `regression.result.json`, cases, stdout/stderr |
| S1 dedicated acceptance | **69/69 PASS**, exit 0, isolation violations 0; historical RAW pins доступны и совпали | `s1_confirm.result.json`, stdout и `s1_confirm.unittest.txt` |
| S2 dedicated core acceptance | **73/73 PASS**, exit 0, dataset pin/guard сохранены | `s2_confirm.result.json`, stdout и `s2_confirm.unittest.txt` |
| Isolation quality: существующие 47 + адресные 5 | **52 PASS + 5 subtests PASS**, exit 0 | `quality_confirm.result.json` и cases |
| JS usage/settings/UI | **57/57 PASS**, exit 0 | `node.stdout.txt`, `node.result.json` |
| Два weakening controls | **2 ожидаемых RED**, outer exit 0; ошибок 0, source files не менялись | `mutations.result.json` и два failure transcript `.txt` |

Суммы разных/повторных прогонов не складываются. S3a включён в регрессию; S1/S2 выполнены своими штатными runner-ами, не заменены pytest discovery. После финального косметического перемещения docstring и добавления safe HTTP trace повторены затронутые H33/S1/S2/quality проверки. Изменений поведения после успешной широкой регрессии не внесено.

Проверены: admitted bytes/hash/headers/timeout, valid usage/reasoning/reopen, отсутствующее/повреждённое/старое enrollment, S2 DENY/caps, forged/replayed/wrong-wire/неподтверждённый SENT, изменение endpoint/model/policy/transport, подмена фактического HTTP content и URL после admission, cancel во время token wait, HTTP 401/429/500/302, invalid JSON/UTF8/oversize/schema, timeout/transport/token error, terminal disk failure, crash после SENT и после HTTP, два владельца и duplicate, deadline после HTTP, missing/partial/invalid/reasoning usage, unknown model/config/env REAL denial. Старые критические H32 crash/terminal/recovery cases также проходят регрессию.

[HTTP trace](evidence/final_http.http_trace.json): **2 Workspace, 4 чата, 4 MockTransport POST, replay добавил 0**, по 12 supplied total tokens на чат, REAL false. Endpoint здесь — адрес в объекте httpx Request; внешнего соединения не было. Trace содержит только synthetic IDs/метод/endpoint/размер/hash/timeout, без Authorization, токенов, raw provider data или пользовательских RAW.

Guard: в полном regression ровно **9 ожидаемых отказов** от трёх исторических negative-control tests; каждый атрибутирован node ID и boundary. В остальных проверках отказов 0. **Неожиданных отказов 0**. Real OAuth tripwire не вызван.

Expected RED: отключение S2 pre-send DENY/caps вызывает failures в настоящем negative test (5 assertion failures, включая последующие проверки накопившихся synthetic counters); отключение проверки actual HTTP bytes вызывает 1 failure. Оба изменения только в памяти, 0 ошибок; исходники до/после совпали. Это отдельно от положительных PASS.

Первоначальный `initial` exit 1 сохранён: 15 base tests PASS, 29 subtests PASS, 1 subtest FAIL. Тест ошибочно требовал обычный FAILED при поддельном SENT ACK; корректный fail-closed 503 и 0 token/HTTP учитываются исправленной проверкой. Защита не ослаблялась. Один повторно собранный импортированный старый HTTP-test удалён из H33 collection во избежание дублирования; он остаётся в широкой регрессии. При сборе environment metadata исправлено предположение об отдельном pytest-subtests package; это не runtime/test failure.

## Launcher, backup и публикационная сохранность

До правок создана SHA-256-проверяемая копия 8 затрагиваемых существующих файлов, включая карточку/counter: `C:\Users\REX\AppData\Local\Temp\codex-h33-backup-9q64puzp`. [preservation.json](preservation.json), [preservation_before_finish.json](evidence/preservation_before_finish.json). Копия сохраняется до независимой приёмки; H30/H31/H32 TEMP backups не трогались. 92 отдельно зафиксированных защищённых файла, включая нормативы/legacy senders/policy/ledger/launcher, проверены без изменений.

STANDARD config остаётся active=standard; постоянный TEST — ordinary-core-offline с существующим stage5-offline rollback. H31 exact-profile guard не редактировался. Профили, CMD и ярлыки не переключались; физический launcher не запускался. Временные Web API сервера тестов штатно остановлены. Доступа к рабочему серверу, чужим проектам/Workspace и записи production данных не было. S1 читал только предусмотренные его контрактом pinned исторические RAW, без модификации.

Проверены локальные ignore-правила без Git: `*.log` исключён, поэтому raw unittest transcripts дополнительно сохранены как `.unittest.txt`. Игнорируемые `.log` — только дубликаты, не единственное evidence. Full report/manifest/JSON/TXT/Python исходники доступны в пакете; Git tracking/push независимо не проверялись.

Штатный finish выполняет check → dry-run → apply → readback, сохраняет assignment/HISTORY ID и переносит только свою задачу БЛОК 1 → 1.1. Его JSON/protocol и адресный history readback — в evidence/closeout. Прочие блоки карточки и report SHA сверяются после finish. Независимая документационная приёмка и публикация автором не выполняются.

## NOT RUN, риски и NEXT

**NOT RUN:** REAL GigaChat/OAuth/paid/external requests; независимый GitHub Windows CI/run ID; Git status/HEAD/commit/push/API; физический CMD/browser/manual F5/GUI smoke; S2 provenance mode; historical ledger adoption/upgrade; полный S3b/S3c/S9/S13a и real provider capability verification. Это закрытые ворота следующего разрешённого шага, а не скрытый PASS.

Риски: legacy physical sends всё ещё требуют собственного S3b; provider caps/reasoning/billing неизвестны; синтетический HARD_BOUND не является real calibration; H29 preferences не равны provider caps. Existing ledger engine marker fail-closed при upgrade, old Audit не усыновляется; рост append-only ledger и RAW retention остаются отдельными решениями. Утраченный owner/SENT остаётся UNKNOWN с liability до проверяемого recovery, без автоматического resend. H33 не содержит REAL client factory, поэтому будущий шаг не сводится к включению флага.

См. подробные [provider contract и REAL gates](provider_contract.md), [инструкции Windows](windows_reproduce.md) и route inventory.

**NEXT:** пользователь публикует один согласованный комплект; независимый verifier запускает точные OFFLINE-наборы в GitHub-hosted Windows с source SHA/run ID/artifact и hash readback. Затем координатор фиксирует bounded verdict, сохраняет все REAL OPEN и назначает отдельную узкую задачу по верифицированному provider contract/server REAL gate. Реальная отправка — только после принятия необходимых gates и отдельного OWNER GO. Backup пока сохранять.

**DOC IMPACT / SHARED DOC DELTA:** координатору после независимой приёмки — №001/05 и FOLLOWUP-WUA-H32-REAL-CONTRACT-001, FOLLOWUP-WUA-H32-S1-RAW-CI-001, FOLLOWUP-WUA-H31-PHYSICAL-SMOKE-001; №34/40 и БЛОК 4: отметить только bounded Ordinary HTTP OFFLINE evidence. №20 S3b/S3c/S9/S13a, S3A-ADOPTION-UPGRADE, S3A-RAW-WIRE-RETENTION и STATIC-DYNAMIC-COVERAGE остаются OPEN. Порядок №37 §3а не меняется. Сам автор эти нормативы/индексы/БЛОК 4 не закрывал.
