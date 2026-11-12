# CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001

13.11.2026 · Codex 007 · **AUTHOR RESULT READY / P0+P1 BOUNDED OFFLINE PASS.** Независимая приёмка не выполнена. Окончательный HISTORY ID назначает штатный finish; фактическая запись — `task_record.json`.

Реализована цепочка **Web Chat → Turn snapshot → final UTF-8 bytes → S2 Ordinary → durable S3a reserve/SENT → один fake byte send → durable terminal → Turn/RAW/history/per-chat usage/reopen**. Ни REAL transport, ни OAuth, ни новые провайдерские HTTP endpoints не добавлены. Полные S3b/S3c/S9/S13a и Stage6/7 не объявляются завершёнными; LIVE READY не заявляется.

## Источники и REUSE CHECK

База `main@97b37f776ce77488961b30da9ec066e84e173b1d` / №576 взята из БЛОКА 1. **Git HEAD независимо не проверялся:** текущая TASK не даёт отдельного Git/GitHub полномочия. Git, commit/push и публикация не использовались. Локальная версия связана с raw SHA-256 before/after и точными AST pins Python 3.12.10, а не с неподтверждённым заявлением о HEAD.

Прочитаны адресные №08/34/40, №37 §3а шаги 3–4, №20 §5а и hard safety contract, указанные FOLLOWUP №05, H30 report, независимый WEB28 H30 review, H31 report и действующие исходники. Актуальные статусы источников: H30 — bounded read-only map, H31 — bounded launcher fix; H31 physical smoke остаётся отдельным OPEN. H32 не заменяет эти границы собственной самооценкой.

**Переиспользованы без изменений:** shared Workspace/RAW/Context writers (`context_storage.py`), Run Store и reentrant workspace writer lock (`run_store.py`), Model Registry, `gigachat_transport.extract_usage`, существующие HTTP capability/Host/Origin/token проверки, H29 per-chat projection/UI/settings и H31 TEST launcher. Существующий Ordinary core по-прежнему готовит/проверяет запрос, парсит ответ и описывает outcome; существующий Turn по-прежнему единственный владелец идемпотентности, RAW и lifecycle. Общий ledger не заменён: добавлен только readback его уже хранимого envelope.

До изменений сохранены 11 планируемых существующих файлов в отдельной TEMP-копии с SHA/readback. Девять из них изменены инженерно; карточка и HISTORY sequence изменяются только штатной сдачей. Новый корневой тест — `test_web_alarm_ordinary_admission.py`; остальные новые файлы — данный отчётный пакет. Нормативные документы, №001/05/06/34/40 и БЛОК 4 не редактировались.

## Изменения и причины

| Файл / функции | Изменение |
| --- | --- |
| `ordinary_chat_service.py` / `execute_request` | Два статических outcome-контракта от доверенного pre-send guard: PreSendDenied → REJECTED/NOT_STARTED; неопределённый admission commit → UNKNOWN/MAY_HAVE_EXECUTED. Сама подготовка, формат запросов, deadline, парсинг и отсутствие retry сохранены. |
| `web_alarm/ordinary_chat_bridge.py` / `offline_policy`, `admission_snapshot`, `execute_turn`, `execute`, `_UsageCapture.send` | Синтетическая политика, exact wire metadata, server-owned guard через ContextVar для изоляции потоков/задач; точный тип fixture transport, одноразовый capture, неизменяемые bytes перед отправкой. Обычный direct execute без Turn admission отказывает; произвольный transport не разрешён. |
| `web_alarm/ordinary_chat_test_adapter.py` / `_FixtureTransport.send_bytes` | Внутренняя fake-граница получает bytes. Внутри она декодирует их только для совместимости со старым fake `send`, который возвращает deepcopy фиксированного ответа. Сетевого I/O здесь нет; старый Stage5 `send` сохранён. |
| `web_alarm/turn_service.py` / `submit`, `_ordinary_envelope`, `_ordinary_admit`, `_ordinary_terminal`, `_execute_offline` | Admission metadata включены в durable binding нового Ordinary Turn. Перед send проверяются сохранённые RAW/snapshot/model/владелец/cancel, reserve/readback и fresh SENT; после ответа — точное durable terminal readback до публикации результата. Старые классы OfflineTestAdapter и imitated TEST не подключаются к Ordinary policy автоматически. |
| `ultra_budget_policy.py` / `ROUTES`, `PolicySnapshot`, `validate_policy`, `evaluate_request` | Добавлены отдельные роль `ordinary`, route `ordinary_chat`, scope `ORDINARY_ATTEMPT`, reachability `OFFLINE_ONLY`. Необязательная секция policy.ordinary использует уже имеющийся ScopeLimits; при её отсутствии — DENY. Агентные RUN/Final Audit ограничения не переносятся на Ordinary скрыто. |
| `ultra_budget_ledger.py` / `_replay`, `reservation` | Для Ordinary scope_id обязан совпасть с provider_attempt_id, а binding содержать Turn/RUN. `reservation()` под тем же shared lock возвращает copy точного committed envelope и record/revision. Reserve/mark_sent/terminal/initialize/recover не заменены новым механизмом. |
| `web_alarm/ultra_chat.py` / Ordinary `_writable_workspace` | Только явное `initialize_workspace:true` при создании чата может сначала создать штатное workspace storage и enroll S3a **до** первого Audit. Существующий enrollment восстанавливается/проверяется; send/get/usage не создают пустой ledger. |
| `test_rt002_s1_routes.py`, `test_rt002_s2_budget_policy.py` | Адресное согласование существующих sealed inventory/isolation oracles с разрешённой H32-интеграцией; точные pins и negative quality tests сохранены/усилены, подробности ниже. |

## От финальных bytes до fake send

1. При новом принятии существующий `freeze` собирает разрешённый контекст под shared writer lock. Turn сохраняет prepared snapshot и `ordinary_admission`: fixture endpoint identity, wire length/SHA, полную synthetic policy и её revision SHA. Эти поля входят в существующий `binding_sha256`; idempotency conflict и durable RAW binding сохраняются.
2. Общий `execute_request` повторно валидирует PreparedRequest против registry. Непосредственно в `_UsageCapture.send` существующий `serialize_request_body(payload)` создаёт **один immutable bytes object**. `PreparedRequest.request_ref` не используется как wire SHA.
3. Server-owned Turn callback под существующим `_session`/writer lock проверяет ATTEMPTING, active owner, отсутствие отмены, start identity, RAW, восстановленный PreparedRequest, текущую модель и сохранённый admission snapshot. Final bytes должны точно совпасть с сериализацией этого snapshot.
4. `BudgetLedger.recover()` требует действующий enrollment. `reserve()` делает S2 evaluation и durable commit под тем же lock. Binding содержит run_id/chat_id/turn_id; logical_call_id хеширует endpoint/policy/wire metadata, Workspace/Chat/attempt, model и Turn binding. В envelope S3a хранит точные wire bytes как UTF-8 и policy, что позволяет независимо воспроизвести hash.
5. Guard требует exact Receipt, **replayed=False**, RESERVED и точный readback record/revision/envelope. Затем делает `mark_sent`, требует fresh SENT и повторно сверяет durable proof и Turn binding/cancel. Отсутствующая запись, forged ACK, чужие bytes, replay или подмена endpoint/policy/snapshot не разрешают вызов fake.
6. После возврата из guard capture повторно проверяет, что transport не подменён, и вызывает **один** `_FixtureTransport.send_bytes(wire)`. Передаётся тот же bytes object; новый словарь для физической границы не сериализуется. Повторный вызов capture запрещён. Никакой пользовательский HTTP body или launcher config не передаёт callback/transport.
7. До `turn_result` существующий ledger получает terminal. Его record сравнивается с ожидаемым pure `apply_terminal` и повторным durable envelope/state/revision readback. Простого ACK недостаточно. Только после этого существующий Turn публикует результат и assistant RAW. H29 читает тот же Turn и не получает нового счётчика.

`mark_sent` — устойчивое потребление права на отправку, **не доказательство удалённого исполнения**. Между этим commit и fake call возможен crash с нулём calls: SENT/UNKNOWN liability сохраняется, send автоматически не повторяется. Гарантия ограничена локальным допуском одной попытки; end-to-end exactly-once внешнего провайдера не обещается. Callback и PreSendDenied — внутренний доверенный контракт, не Python sandbox для произвольного кода; будущий REAL transport требует отдельного допуска и собственной проверки before/after-send taxonomy.

## Политика, enrollment и UNKNOWN

Synthetic policy имеет явную метку `H32 SYNTHETIC OFFLINE ONLY`. Для Ordinary: final body до 8192 bytes, input estimate до 8192, per-attempt liability до 8320, одна попытка scope; output параметр существующего fixture — 128. Используется прежнее **HARD_BOUND assumption tokens<=bytes**, без утверждения эмпирической калибровки или настоящих GigaChat caps. В полном policy остаются обязательные поля RUN по существующей схеме, но Ordinary не является executor/mcp/RUN и не расходует Final Audit reserve.

Scope каждой попытки равен attempt_id. Это **не новый накопительный потолок Workspace**, не денежный баланс и не лимит числа чатов. Общий workspace index остаётся только существующим durable местом хранения независимых попыток. UI-предпочтения H29 `250000/10000/20000` сохраняются, но не применяются к fake provider и не объявляются подтверждёнными лимитами модели.

Если marker/ledger отсутствует, повреждён, недоступен или связан с другой версией engine — ZERO send и отказ/UNKNOWN согласно границе неопределённости. `initialize()` не вызывается при отправке. Historical Audit без enrollment не принимает автоматическую adoption; даже создание нового чата с initialize получает `ordinary_enrollment_required`, старые факты не стираются. Marker-first interrupted initialization тоже не «исправляется» обнулением.

**Изменение pure S2 кода меняет существующий S3a engine fingerprint.** Ранее enrolled ledger со старым fingerprint будет fail-closed до отдельно утверждённой migration; H32 его не переписывает. Это ожидаемая граница совместимости, а не заявление о миграции старых данных. Новый synthetic Workspace enroll проходит, существующий корректный H32 enrollment/recover проверяется.

После reserve denial/readback failure могут остаться conservative RESERVED obligations; они не освобождаются автоматически. После неопределённого mark_sent или transport error/timeout остаются SENT/UNKNOWN с ненулевой liability. Доказанный PreSendDenied не создаёт успешного Turn; при неопределённости хранилища сохранённый резерв не превращается в ноль. Потерянный owner ATTEMPTING проецируется в UNKNOWN и не пересылается; новый ключ того же Chat может требовать дальнейшего verified recovery, если сохранился незавершённый durable ATTEMPTING. Автоматическое fencing/repair не выдумано.

Known usage нормализуется существующим S2, missing/invalid/partial остаётся неизвестным обязательством. Неизвестный precached не подменяется нулём: S2 может удерживать консервативную оценку input даже при известных отдельных полях. Reasoning остаётся подмножеством completion и не прибавляется к total. Поздний известный ответ после cancel уточняет ledger usage, но Turn остаётся UNKNOWN, assistant RAW не публикуется. `transport_error`, timeout и неопределённый admission commit не смешиваются с успешным ответом; локальная ошибка commit классифицируется как no-response transport uncertainty.

## Регрессия S1/S2 без ослабления защит

S1 сохраняет полный census, семь физических LLM POST и один OAuth POST. Обновлены **только reviewed AST/reference pins** изменённого общего execute, fixture byte entry и нового Ordinary caller. Для уже существовавшего H31 main согласован старый pin и дополнительно закреплены `_require_offline_test` и trusted allowlist. Launcher source не изменён. Внутренняя делегация fake send_bytes→send учтена как один дополнительный **UNKNOWN dynamic.send**, а не как принятая новая REAL HTTP-route; full dynamic coverage остаётся OPEN.

S2 сохраняет весь import graph и консервативное обнаружение неизвестных прямых/транзитивных consumers. Разрешены только exact AST-pinned ingress edges от трёх H32 fake gate modules к policy/ledger; произвольный новый consumer по-прежнему RED. Сам ledger остаётся sealed capsule. Изменение любого gate также RED. Отдельно согласована существующая H28 установка guard через runpy: whole-module pin fixture и SHA неизменённого H27 guard, а не разрешение произвольных loaders. Проверены прежние **47 quality cases** и **5 новых**, включая подмену bootstrap script. Старые тестовые ID/MANIFEST сохранены для адресной истории; историческое имя `test_no_production_module_imports_the_policy_yet` теперь означает отсутствие непроверенного policy ingress.

Pins рассчитаны на acceptance Python **3.12.10**. Первая генерация через системный Python 3.13 дала другие AST dumps (пустые поля); это выявлено тестами и исправлено расчётом на 3.12. Никаких AST-check отключений или blanket whitelist entrypoints нет. Все обновления pins и причины сохранены в `evidence/*reconciliation*.json`, `*review_pin.json`, исходный diff — `source_diff.txt`.

## Реальные запуски тестов

Все результаты ниже — локальные Windows author tests, не GitHub CI и не независимая приёмка. Точные argv, exit codes, per-case records и raw stdout/stderr сохранены рядом. Stage-name runner не перезаписывает уже существующее evidence.

| Набор / финальные artifacts | Факт |
| --- | --- |
| `final_regression.*` — Ordinary bridge, H29, S3a, common Ordinary service, Turn Service/S4b/HTTP/Stage5, Run Store, H31 StableEntry и два activation tests | **235 PASS + 220 subtests PASS**, 0 failures/errors/skips, pytest и runner exit 0, 145.41 s. |
| `post_review.*` — вся затронутая Ordinary/S3a цепочка после финальной проверки terminal taxonomy и добавления отдельного oracle | **74 PASS + 32 subtests PASS**, 0 failures/errors/skips, exit 0, 59.93 s. В составе: 17 новых H32 методов, 14 bridge, 8 H29, 35 S3a. Это повтор части предыдущего набора, числа не складываются как уникальные проверки. |
| `s1_final.*` — штатный S1 runner | **69/69 PASS**, manifest/gate PASS, 0 fail/error/skip/isolation, exit 0. |
| `s2_final.*` — штатный S2 core runner | **73/73 PASS**, manifest/gate PASS, 0 fail/error/skip/isolation, exit 0. Provenance extraction из новых RAW не запускалась; embedded dataset SHA сохранён. |
| `isolation_final.*` — H25 quality + новые gate/loader mutation cases | **52 PASS + 5 subtests PASS**, 0 fail/error/skip, exit 0, guard0. |
| `ui.*` — `node --test test_web_alarm_ultra_chat_ui.js` | **57/57 PASS**, 0 fail/skip, exit 0; Node VM/fake fetch, без настоящего браузера. |
| `http_final.result.json` | Guarded loopback HTTP: **2 Workspace / 4 Chat / 4 fake calls**, replay +0 calls, request REAL body 400, per-chat totals 14/7/7/0 и reasoning 4/2/2/0. На каждой byte-границе прочитан durable SENT и точный envelope; безопасные hash/binding/policy/endpoint metadata сохранены в trace. |
| `mutations_final.result.json` | Две намеренные **in-memory** поломки: bypass S2 DENY и bypass terminal verification. Каждая дала ровно **1 expected RED failure / 0 errors** в соответствующем настоящем тесте. Исходники не менялись; H31 не ослаблялся даже для этих контролей. |

Критические cases: exact wire identity, separate per-chat usage/reasoning, replay/reopen, S2 DENY, corrupt/missing/old-engine enrollment, unavailable reserve, forged receipt, replayed receipt, wrong wire, endpoint/policy/Turn/transport change после SENT, crash до/после reserve и после SENT, mark_sent commit+I/O error, terminal failure/fake ACK, конкурентные владельцы/два ключа, cancel before admission, late known response, timeout/transport error, missing usage и historical Audit refusal. Fake responses и Workspace во всех execution tests синтетические.

H27 guard установлен до runtime imports; Python children наследуют его через PYTHONPATH. Credentials/environment values, внешняя сеть/DNS, `.git` и repository live storage блокируются. В полном прогоне есть **9 ожидаемых blocked probes** от трёх штатных guard-negative tests (по одному connect/DNS/credential на тест); они привязаны к точным test IDs, фазе call и PASS и сохранены в `guard_events`. **Unexpected denials = 0.** Отдельный controls1 повтор подтвердил 3/3 PASS и те же 9 отказов. H32 feature, HTTP, quality и mutation runs имеют 0 неожиданных/несанкционированных событий. У S1/S2 собственные ранее проверенные early guards и изолированные fake HTTP transports; их финальные isolation lists пусты. S1 по своему прежнему контракту читает pinned исторические source snapshots до runtime imports; реальных Workspace он не изменяет. Реального GigaChat/OAuth/paid трафика не было.

### Исходные неудачи сохранены

- `policy0`: обычный pytest discovery дал 35 S3a PASS и **143 SKIP S1/S2**. Это **не** acceptance S1/S2; затем использованы их штатные standalone gate runners.
- `adversarial0`: два ошибочных oracle/API обращения в новом тесте (несуществующий cancel method, неверная форма latest response) дали FAIL; исправлены тесты, не production-защита. Дополнительно устранён скрытый неправильный helper записи summary в mutation case и добавлен assertion фактического применения мутации.
- S1/S2 первые запуски обнаружили несогласованные AST/caller/route/isolation pins, существующий H31 main drift относительно старого S1, Python 3.13 dump и различие raw/LF SHA H27 guard. Эти failures не скрыты: `s1_0…s1_4`, `s2_0…s2_3` и reconciliation evidence сохранены.
- `isolation0`: collision имён двух report test modules; исправлен runner `--import-mode=importlib`. `isolation1`: преждевременная guard SHA assertion помешала заполнить observations; `isolation2`: два collector cases не получили свой standalone SANDBOX при pytest import. Исправлен только test runner, предоставляющий synthetic SANDBOX; H25 файл не менялся. Последующие quality runs 52/52 PASS.
- `regression0`: pytest 162 PASS, runner exit 1 из-за учёта девяти намеренных guard probes как unexpected. Добавлена строгая per-test attribution без отключения guard; полный финальный повтор прошёл с 9 expected / 0 unexpected.
- Первый запуск дополнительного HTTP helper не видел repository import path и завершился ModuleNotFoundError до сервера; исправлен только путь импорта тестового helper. Это не product failure. Финальный HTTP smoke PASS.

## Границы NOT RUN и риски

**NOT RUN:** REAL GigaChat, OAuth, платные запросы, реальные credentials/Workspace; Git/публикация; full CI; all-physical-route S3b, S3c/S9/S13a acceptance; реальные provider caps/calibration/reasoning support; historical ledger adoption/migration; host power-loss/clone fencing guarantees; физические CMD/browser/F5/clean Windows/второй ПК. H31 physical smoke FOLLOWUP не закрывается. Браузерный визуальный результат не приписывается HTTP/Node тестам.

Сохраняется существующий S3a capacity bound **MAX_EVENTS=4096** (обычно три ledger events на нормальную попытку). При исчерпании — DENY, без автоматического compaction/reset. Это форматный предел хранилища, не финансовый Workspace budget и не доказательство неограниченной production-масштабируемости. Полный wire хранится существующим S3a как и прежде; H32 использует только synthetic TEMP, production RAW retention/privacy требует отдельного решения. Между известным ответом и недоступным terminal storage Turn может остаться UNKNOWN/SENT; успешный ответ в этом окне намеренно не публикуется, пока нельзя подтвердить durable факты.

## Сохранность, backup и rollback

88 protected source/document pins сверены: `server.py`, `gigachat_transport.py`, web server, H31 launcher/его тесты/config, оба постоянных CMD, `Start_Ultra.cmd`, core storage/Run Store и нормативные документы **не изменены**. Backend Turn/bridge расширены только для точного OrdinaryCoreAdapter в явных TEMP roots; прежние имитаторы Stage5 и STANDARD/Tk пути сохранили контракты и регрессию. БЛОКИ 2–4 сохраняются; после finish проверяется их raw tail SHA.

Новый backup: **`C:\Users\REX\AppData\Local\Temp\codex-h32-backup-jvprazgr`** — SHA/readback PASS, **RETAINED / CLEANUP PENDING UNTIL INDEPENDENT ACCEPTANCE**. Состав и исходные хеши — `evidence/backup.json`. TEMP-копии H30/H31 не открывались, не изменялись и не удалялись. Никаких изменений самостоятельного `local_LLM` в этой задаче.

Rollback исходников — после решения владельца восстановить только перечисленные девять изменённых source/test файлов из этой копии, сверив SHA; сохранить пакет evidence, не откатывать чужие изменения и не удалять нормативные данные. Тестовые Workspace не являются пользовательскими; H32 не мигрировал production ledger, поэтому нет скрытой data-conversion, которую надо «обнулить» при rollback. Никакие неизвестные/исторические Audit или обязательства не удалять. Карточка/HISTORY sequence возвращаются только своим штатным координационным порядком, не простым откатом старого счётчика.

**DOC IMPACT:** этот engineering report/evidence/manifest и штатная сдача своего БЛОКА 1 через finish. Не выполнялся независимый документальный closeout №001/05/06/34/40/БЛОКА 4. После проверки координатору отметить bounded Ordinary fake admission, точные counts, новый route/per-attempt scope, old-engine migration HOLD, H31 physical gap и сохранение запрета REAL. Отчёт после HISTORY регистрации не дописывать; фактические receipt/readback/HISTORY ID — в `finish_receipt.json`, `task_record.json`, `closeout.json`.

## Конкретный NEXT перед первым GigaChat

Независимо воспроизвести H32 на опубликованном SHA с guards, включая exact-byte/receipt/terminal mutations и согласованные S1/S2 oracles. Затем отдельно согласовать минимальный REAL provider contract: подтверждённые endpoint/model caps, output/reasoning semantics, policy/calibration/profile, final content-bytes HTTP без повторного json=, явный enrollment/adoption сценарий и applicable predecessors №20 §5а. Не включать REAL флагом конфигурации. Только после независимых gates — отдельный USER GO на конкретные endpoint/model/данные/число попыток/stop limits. Эта сдача такого допуска не даёт.
