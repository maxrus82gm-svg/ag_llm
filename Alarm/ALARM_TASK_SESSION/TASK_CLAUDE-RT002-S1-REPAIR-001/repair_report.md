# CLAUDE-RT002-S1-REPAIR-001 — Independent Engineering Repair of S1

**Исполнитель:** агент 008 (Claude, Opus 5.5). **Независимый verifier:** ChatGPT / LLM_11.
**Статус:** REPAIR RESULT READY / AWAITING INDEPENDENT VERIFICATION. S1 самостоятельно не объявляется принятой; S2 не начат.
**Дата:** 2026-10-14. **Назначение:** пользователь переслал в чат стартовую команду. Постановка — БЛОК 1 карточки, исправлен пользователем в 10:55, после того как в 10:49 туда по ошибке попала копия чата S1. Работа начата только по корректной постановке.

## 1. Baseline и provenance

- **Production runtime не менялся:** хеши до и после совпадают.

  | Файл | SHA-256 (начало) |
  | --- | --- |
  | server.py | `44d8cc8affaf…` |
  | planner_runtime.py | `ab6c12c3fb02…` |
  | task_planner.py | `c2ad7723b0ec…` |
  | verifier_runtime.py | `7db030fee149…` |
  | compressor_runtime.py | `c69ab1d9594b…` |
  | provider_accounting.py | `dd83dbf7a221…` |
  | run_store.py | `a57a250a20ea…` |
  | audit_storage.py | `5d91a6f9842b…` |
  | gigachat_transport.py | `ee1db75ed04e…` |
  | context_storage.py | `8cf90ad41afb…` |
  | ultra_ui.py | `7bd32cad56c6…` |

  Полные значения — в `s1_report.md` §1.
- **Тесты S0 не менялись:** `test_rt002_s0_kernel.py` `cf9b1d771e7e…` (совпадает с runner hash в 20 §5а), `test_rt002_s0_repair.py` `860f723f4c86…`.
- **Модуль до ремонта:** `test_rt002_s1_routes.py` SHA-256 `20a54a0ea9d3f5dad8ab33533d319d8b5e778fcab8ceec6d18f652afa24a86c0` (39 тестов).
- **Модуль после ремонта:** SHA-256 `58dffff06014a8e813148c2ebe76fea8b183979221e79ebb1fb06eaf1ad37967`, 1 706 строк, LF, 63 теста.
- **Source baseline координатора** `main@0d06384…` локально не сверялся: Git запрещён, `.git` не читался.
- **Прочитано:** маршрут `08 → 000 → 34 → 18 → 01 → 20 §5а → 36 → 36.1 → 36.3` — адресно; правила известны по S1. Также `s1_report.md`, `recon_report.md`, исходники модуля и транспорта.

## 2. Root cause исходных замечаний

**F1 — тестовый gate мог дать ложный PASS.** [Ф, код модуля до ремонта]
- `_require_evidence` при отсутствии данных или SHA mismatch выбрасывал `unittest.SkipTest` (стр. 94–100).
- Код выхода считался как `0 if result.wasSuccessful() and not violations else 1` (стр. 1357). `wasSuccessful()` считает SKIP успехом, а `evidence_problems` в условие не входили. Поэтому отсутствие RAW давало exit 0.
- Манифеста collection не было: пропавший или переименованный тест, ошибка импорта класса или пустая выборка не обнаруживались.
- Запуск с селекторами давал exit 0. Это неотличимо от полной приёмки.
- Нераспознанный селектор рядом с валидными тихо отбрасывался.

**F2 — статическая инвентаризация теряла кратность и варианты отправки.** [Ф]
- Результат сводился в `set` (стр. 854), поэтому второй `client.post` в той же функции исчезал.
- Учитывались только атрибуты `post/send/stream/request` и только у получателя с текстом `client.`. Не видны:
  - алиасы (`c = client`, `p = client.post`);
  - `get/put/patch/delete/head/options`;
  - модульные `httpx.post(...)`;
  - `getattr(client, "post")`, `functools.partial(client.post, …)`;
  - transport-методы `handle_async_request/handle_request`;
  - `urlopen`, `requests`, `aiohttp`;
  - синхронный `httpx.Client`.
- LLM и OAuth различались только комментарием, без проверки URL. Переопределение `CHAT_URL` в модуле не обнаруживалось.
- Динамическая сторона: OAuth везде подменялся mock-ом, поэтому LLM и OAuth динамически не различались. Синхронный транспорт httpx не перехватывался.

## 3. Выбранная техническая стратегия

**F1 — один чистый gate с явными кодами выхода.**
- `evaluate_gate(...)` — чистая функция без побочных эффектов. FAIL (exit 1) при любом из условий:
  - пустой MANIFEST;
  - COLLECTION_MISSING / UNEXPECTED / DUPLICATE (сравнение с точным `MANIFEST` из 63 `Class.method`);
  - SELECTOR_UNRESOLVED;
  - ZERO_TESTS;
  - NOT_RUN (фактически стартовавшие тесты пишет `_RecordingResult.startTest`);
  - FAILURES, ERRORS, UNEXPECTED_SKIP, EXPECTED_FAILURE_FORBIDDEN, UNEXPECTED_SUCCESS;
  - EVIDENCE;
  - ISOLATION_VIOLATIONS.
- Запуск с селекторами без нарушений — `PARTIAL_SELECTION`, exit 3: никогда не приёмка. **Exit 0 — только для полного MANIFEST без единого нарушения.**
- Обязательные RAW-данные: `_require_evidence` теперь выбрасывает `AssertionError` (ошибка класса, не SKIP). Отдельный тест проверяет полноту снимка и SHA копий.
- `snapshot_evidence(root, base, pins)` — проверяемая функция. `RT002_S1_EVIDENCE_ROOT` позволяет направить снимок на другой корень; используется только для негативных проверок.
- В `result.json` пишутся `gate`, `counts`, `manifest_size`, `selected`, `evidence_root`.

**F2 — две независимые статические сети и динамическое разграничение.**
1. **`scan_send_sites`** — консервативный AST-инвентарь с сохранением кратности; сравнивается мультимножество `(module, owner, kind, traffic) → count`.
   - Привязки клиентов: `with/async with httpx.AsyncClient|Client(...) as x`, присваивания, `from httpx import AsyncClient as AC`, параметры `client` или аннотации `*Client`. Алиасы клиентов и методов — по fixpoint.
   - Виды отправки: `client.<verb>` для всех HTTP-глаголов, `alias.<verb>`, `httpx.<fn>`, `transport.handle_*`, `getattr.<verb>`, `method-ref.<verb>`, `urlopen/create_connection/HTTP(S)Connection/ClientSession/build_opener`, а также импорт других сетевых стеков.
   - Владелец — внешняя функция или метод класса; вложенные функции относятся к владельцу.
   - Класс трафика: LLM / OAUTH — только если URL-аргумент является каноническим `CHAT_URL` / `OAUTH_URL`, импортированным из `gigachat_transport` (или реэкспортом `server`) и не переопределённым в модуле. Иначе UNKNOWN.
2. **`unexplained_endpoint_reads`** — сеть, не зависящая от получателя: любое чтение `CHAT_URL/OAUTH_URL` в production должно быть URL-аргументом учтённой LLM/OAuth-отправки. Ловит отправку через параметр с другим именем и даже упоминание эндпоинта вне вызова.
3. **Эталон кратности:**
   - production — 7 LLM + 1 OAUTH, каждое ×1;
   - вне production — `probe_gigachat_models.main client.get` ×1 и `wa4o_ui_launcher.verify_response urlopen` ×2;
   - production не импортирует модули вне production;
   - `CHAT_URL/OAUTH_URL` определены только в `gigachat_transport.py` и нигде не переопределяются.
4. **Динамика.** `WireCapture` маршрутизирует по фактическому URL (`LLM` / `OAUTH` / прочее отклоняется) и запрещает синхронный `httpx.HTTPTransport.handle_request`. Новый тест проходит реальный `get_access_token`: один POST на `OAUTH_URL`, форм-тело `scope=…`, ни одного LLM-запроса, повторный вызов берётся из кеша.

**Production не менялся:** качественное решение потребовало только тестов (БЛОК 1, §5).

## 4. Изменения (реальный перечень)

| Файл | Изменение |
| --- | --- |
| `test_rt002_s1_routes.py` | F1 gate + MANIFEST + recording result + `snapshot_evidence` + обязательные данные как FAIL; F2 `scan_send_sites` + `unexplained_endpoint_reads` + эталоны с кратностью; OAuth и sync-transport в `WireCapture`; новые и усиленные тесты. 39 → 63 тестов. SHA `58dffff0…37967` |
| `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S1-REPAIR-001/repair_report.md` | новый (этот отчёт) |
| `Документация/000_Задачи Claude.md` | регламентная ротация |

Production runtime, S0, Web Alarm, файлы Codex, общие документы и CI не менялись.

## 5. Дополнительные дефекты (найдены собственным review, исправлены в scope)

- **D1.** Нераспознанные селекторы рядом с валидными тихо отбрасывались → `SELECTOR_UNRESOLVED`.
- **D2.** Запуск с селекторами возвращал 0 → exit 3 `PARTIAL_SELECTION`.
- **D3.** `test_direct_run_planner_has_no_production_caller` видел только `Name`-вызовы → теперь все ссылки `run_planner`: Name-load и Attribute, вызовы и не-вызовы. Единственная ссылка — `server.py:4366`, вызов с `session=planner_session`.
- **D4.** `test_ask_gigachat_is_reached_only_from_mcp_tools` считал только вызовы → теперь все Name-load по владельцам. Ровно по одному в `gigachat_ask` и `gigachat_file_task`, оба `@mcp.tool()`.
- **D5.** Синхронный транспорт httpx не был перехвачен → отклоняется и регистрируется как violation; есть негативный тест.
- **D6.** Отправка через клиент под другим именем параметра была невидима для receiver-скана → закрыта сетью `unexplained_endpoint_reads`; есть негативный тест.
- **D7.** OAuth динамически не отличался от LLM → отдельный динамический тест.

В production-коде новых дефектов в пределах S1 не найдено. Findings S1-F1…F8 из `s1_report.md` (best-effort accounting, потеря usage verifier, хеш wire и др.) относятся к S2/S3a/S3b/S9 и здесь **не исправлялись**: это был бы запуск следующих этапов B2.

## 6. Тесты и негативные проверки

**Основной прогон:** `.venv/Scripts/python.exe -B test_rt002_s1_routes.py`
- Окружение: Python 3.12.10, httpx 0.28.1.
- **63 / 63 PASS, 0 FAIL, 0 ERROR, 0 SKIP, 0 expectedFailure, 0 unexpectedSuccess.**
- Gate: `PASS`, **exit 0**, MANIFEST 63; isolation_violations 0; evidence_problems 0; 11.967 с.
- Лог: `claude-rt002-s1-iknndb1a/unittest.log`, SHA-256 `ed50cca51a2b15ee45daa48ee3b38fe5634b64ba102530086eaf0d3ce4ce8907`.

| Класс | Тестов |
| --- | --- |
| R031RawMatrixTests | 5 |
| R026RawAccountingTests | 3 |
| AccountingSemanticsTests | 5 |
| WireEvidenceTests | 4 |
| RouteTransportTests | 13 |
| StaticRouteInventoryTests | 16 |
| GuardNegativeControlTests | 4 |
| GateLogicTests | 9 |
| EvidenceGateTests | 4 |

**Сквозные негативные прогоны F1** (на финальном модуле `58dffff0…`, без правок репозитория):

| Сценарий | Exit | Gate / причины | Счётчики |
| --- | --- | --- | --- |
| `RT002_S1_EVIDENCE_ROOT` = пустой каталог | **1** | FAIL: NOT_RUN, FAILURES, ERRORS, EVIDENCE | run 55, F1 E2 S0 |
| `RT002_S1_EVIDENCE_ROOT` = те же пути с мусором (SHA mismatch) | **1** | FAIL: NOT_RUN, FAILURES, ERRORS, EVIDENCE | run 55, F1 E2 S0 |
| 2 валидных селектора | **3** | PARTIAL_SELECTION | run 2 |
| валидный + нераспознанный селектор | **1** | FAIL: SELECTOR_UNRESOLVED | run 1 |
| только нераспознанный селектор | **1** | FAIL: SELECTOR_UNRESOLVED, ZERO_TESTS | run 0 |
| MANIFEST без одной записи (scratch) | **1** | FAIL: COLLECTION_UNEXPECTED, FAILURES | run 63, F1 |
| httpx кодирует с `sort_keys` (scratch, 4 селектора) | **1** | FAIL: FAILURES | run 4, F3 |

Без данных 8 тестов R-031/R-026 не стартуют (ошибка `setUpClass`), а тест полноты снимка падает. SKIP не возникает ни в одном сценарии.

**Негативные контроли F2 внутри suite:**
- синтетическая база и второй POST в той же функции → кратность 2;
- 10 вариантов: `c = client`, `p = client.post`, цепочка алиасов, `client.send(build_request)`, `client.stream`, `client.request(url=…)`, `getattr`, `functools.partial`, `_transport.handle_async_request`, `client.get`;
- 8 вариантов модульного уровня: `httpx.post`, sync `httpx.Client` + чужой URL, `from httpx import AsyncClient as AC` + `server.CHAT_URL`, `urlopen` + импорт, `requests`, переопределённый `CHAT_URL` → UNKNOWN, `OAUTH_URL` → OAUTH, вложенная функция в методе класса;
- **мутации реального `server.py` в памяти:** второй POST, `send`-обёртка, алиас, переопределение `CHAT_URL` — каждая меняет мультимножество;
- чтение эндпоинта через неизвестный получатель и вне вызова;
- дрейф эталона;
- 4 нарушения guard;
- неожиданный адрес; синхронный транспорт.

**Связанная регрессия S0:** `.venv/Scripts/python.exe -B test_rt002_s0_kernel.py` — **166 / 166 PASS, 0 FAIL / ERROR / SKIP, 0 isolation violations, exit 0**, 102.85 с; лог SHA-256 `6fb5427a0653357316c0444a4afad9765aebbbb88b62b441a7c88eb587b41eb6`.

**Discovery для сравнения:** `.venv/Scripts/python.exe -B -m unittest test_rt002_s1_routes` → `Ran 0 tests … OK (skipped=1)`, exit 0. Это задокументированный путь «не приёмка» (так же устроен принятый S0), см. §8.

**NOT RUN:**
- `test_final_audit` целиком — Git-зависимые сценарии;
- live / paid;
- kill процесса во время HTTP.

## 7. MANUAL ENGINEERING REVIEW

| Claim | Source | Independent oracle | Result | Remaining uncertainty |
| --- | --- | --- | --- | --- |
| Exit 0 невозможен без полного чистого MANIFEST | `evaluate_gate`, `main` | 9 юнит-тестов gate + 7 сквозных негативных прогонов | подтверждено | discovery-путь (§8) |
| RAW-данные обязательны | `_require_evidence`, `snapshot_evidence` | пустой и мусорный корень → exit 1; юнит-тест snapshot | подтверждено | данные локальны: на машине без `.ultra` S1 всегда FAIL — так и задумано |
| Кратность сохраняется | `site_multiset` | второй POST (синтетика и реальный server.py) → 2 | подтверждено | — |
| Алиасы / `send` / `stream` / обёртки видны | `scan_send_sites` | 18 синтетических вариантов + мутации реального кода | подтверждено | динамический `eval`, `importlib`, сторонний SDK формально не исключены; закрываются динамическим guard (сеть запрещена) и сетью эндпоинтов |
| LLM ≠ OAuth ≠ прочее | классификация URL + проверка переопределения + динамический OAuth | статика + реальный `get_access_token` через транспорт | подтверждено | URL, собранный вне констант (f-string), → UNKNOWN и требует явного решения — так и задумано |
| Отправка через неизвестного получателя не скрыта | `unexplained_endpoint_reads` | синтетика `http.post(CHAT_URL)` + реальные модули → 0 unexplained | подтверждено | эндпоинт, заданный литералом-строкой, ловится только как UNKNOWN-сайт известного клиента или сетевым guard |
| Изоляция не ослаблена | `_install_guards` (без изменений по сути) | 4 негативных контроля; 0 violations | подтверждено | — |
| S0 совместим | runtime не менялся | S0 suite 166 / 166 | подтверждено | — |

**Рассмотренные альтернативы:**
- Межмодульный type-flow анализ — избыточен и хрупок; вместо него вторая сеть по чтению эндпоинтов.
- Перехват на уровне `socket` — уже есть guard: сеть запрещена. Перехват на уровне httpx нужен для фиксации байтов.
- Перевод discovery-skip в FAIL отвергнут: это ломает общий `unittest discover` для всего репозитория и расходится с принятым паттерном S0.

**Ложноположительные результаты:**
- каждый новый тест имеет свой негативный контроль или проверку чувствительности;
- эталоны сравниваются целиком, а не через `assertIn`.

## 8. Ограничения, риски, рекомендации

- **Остаточный риск — путь discovery.** `python -m unittest test_rt002_s1_routes` даёт exit 0 при нуле выполненных тестов. Приёмкой S1 считается только standalone-команда с `gate.status = PASS` в `result.json`.
  - [Р] В 36.3 указывать только standalone-команду и критерий gate PASS.
- **Статический анализатор** внутримодульный. Межмодульная передача клиентов покрыта сетью эндпоинтов и динамическим guard, но не формальным type-flow.
- **RAW-данные** зависят от локального `.ultra`; при их ротации или удалении S1 падает (FAIL, не SKIP). Пины надо обновлять осознанно.
- **Production findings S1-F1…F8** остаются входом для S2: единый узел перед HTTP, долговечный резерв, обязательные события попыток, хеш wire, UNKNOWN, cached.

## 9. Архитектурные инварианты

- Не менялись B2 и его predecessors, S0, production runtime, Web Alarm, файлы Codex, общая документация.
- Git не использовался.
- Платных и live-вызовов не было; реальные RAW-данные только читались.
- Песочница, network guard и запрет `.git` / `.ultra` сохранены.

## 10. DOC IMPACT (для координатора)

- **`36.3`** — S1 acceptance-команда, коды выхода 0 / 1 / 3, критерий `gate.status = PASS`; discovery-skip — не приёмка.
- **`21`** — запись ремонта S1: F1 / F2 root cause, 63 / 63, негативные прогоны, S0 166 / 166.
- **`20` §5а** — статус S1 после независимой проверки.

## 11. Итог

**REPAIR RESULT READY / AWAITING INDEPENDENT VERIFICATION.** F1 и F2 устранены в тестовой системе; найдены и исправлены ещё 7 связанных дефектов тестов; production не менялся. S1 не объявляется принятой; S2 и следующие этапы не начинаются без отдельного назначения.

**NEXT:** независимая инженерная проверка ChatGPT → решение пользователя.
