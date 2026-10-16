# CLAUDE-WA4-R-AUD010205-REPAIR-001 — ремонт AUD-01, AUD-02, AUD-05 (WA4-R)

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE/VERIFIED. Публикация: LOCAL ONLY / NOT SYNCED — Git не использовался, commit/push делает пользователь.

- Исполнитель: агент 008 (Claude), 2026-10-16. Verifier: ChatGPT.
- ARCH CLASS: Web Alarm Workspace / RT-001 / WA4-R Reliability. PRIMARY PROFILE 23; TEST PROFILE 36.2.
- Основание: `CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001` (находки AUD-01, AUD-02, AUD-05).
- Назначение — БЛОК 1 карточки (опубликован пользователем, коммит №350) и стартовое сообщение пользователя. AMENDMENT не было.
- WARN, GATEWAY REQUIRED и STRICT не включались. **WA4-R остаётся PARTIAL.**

## 1. Итог

| Находка | Статус | Коротко |
|---|---|---|
| **AUD-01** — разделение JSONL при U+0085/U+2028/U+2029 | **PASS** | Reader режет записи только по физическому LF (CRLF совместим), writer экранирует три символа. Старые журналы с «сырыми» символами снова читаются; новые журналы читает и старый код. |
| **AUD-02** — INTENT/payload до проверки истории | **PASS** (для нечитаемой истории на момент admission) | `begin()` под теми же lock проверяет историю до первой durable-записи. При отказе не остаётся ни INTENT, ни payload, ни событий; ответ «nothing was written» теперь правдив. Окно crash между INTENT и событием — это AUD-03, вне ремонта (§7). |
| **AUD-05** — закрытие TASK с нечитаемой историей без операций | **PASS** | Новый блокер projection `HISTORY_UNREADABLE` → в gate closeout `PROJECTION_HISTORY_UNREADABLE`. Отказ происходит до move, без единого записанного байта и виден в inspect/verdict. Путь `MOVED_STATUS_PENDING` не тронут; `STATUS_WRITTEN_NOT_MOVED` требует читаемой истории до move. |
| Регрессии R-006 / F1–F3 | **не обнаружены** | См. §5 (Gate B/C). |

**Новые находки (вне scope, без правки кода):**
- **AUD-01T** — тот же дефект framing в `transport_event_store` плюс отсутствие проверки оборванного хвоста. Хранилище глобальное: одно событие из `POST /transport/events` делает нечитаемым всё transport-evidence и блокирует любые последующие добавления. **STOP / требуется согласование.**
- **AUD-02b** — тот же класс, что AUD-02, в переходах микрозадач: статус сохраняется, а событие истории отклоняется.

## 2. Baseline gate (до правок)

- 102/102 pinned-исходника R-006 совпали побайтно. Новых файлов в `web_alarm/` и `test_web_alarm*.py` нет.
- Пакет R-006: 64/64 файла манифеста; `manifest.json` = `b14c3664…` — тот же, что при аудите.
- Целевые файлы не менялись с момента аудита: `event_checkpoint_store.py` `7d094e81…`, `operation_store.py` `bb7eaf40…`, `projection.py` `1d788d21…`.
- Точные исходные байты сохранены в `baseline/web_alarm/`, границы изменений — в `scope.md`. Обе записи сделаны до первой правки.
- **Пересечение с Codex 007.** БЛОК 1 `CODEX-WUA-0-DESKTOP-MCP-E2E-001` прямо запрещает Codex изменять `web_alarm/*.py` и материалы WA4-R. Его рабочую область я не читал и не трогал. Пересечения по записи нет.
- Прочитаны: БЛОК 1, 18 (полностью), 23, 24, 25, 36.2 (полностью), отчёт, evidence и probes аудита.

## 3. Что исправлено и почему (байты и состояния)

Полный diff: `source-changes.diff` (+33 / −4 строки, только три файла). Все файлы LF, без «сырых» разделителей.

### AUD-01 — `web_alarm/event_checkpoint_store.py` (`7d094e81…` → `7342b221e6663bee65bef116f57507b0de84b74269cb7541f4955b527eb91304`)

- **Причина.** `json.dumps(ensure_ascii=False)` оставляет U+0085/U+2028/U+2029 «сырыми» внутри строк, а `bytes.decode().splitlines()` режет по ним запись. Обычная запись (например, target или `verification_evidence` из HTTP) делала историю нечитаемой.
- **Reader.** Разбор только по физическому `b"\n"`; один завершающий `\r` (CRLF) снимается; каждая строка декодируется отдельно.
  - Проверка оборванного хвоста R006-F02, отказы на пустой строке, невалидном JSON/UTF-8/схеме и чужом `task_id` сохранены.
  - Новое: одиночный `\r` внутри строки больше не считается разделителем записей. Наш writer его никогда не пишет, поэтому такая строка — порча, и она отклоняется.
- **Writer.** После `json.dumps` три символа транслируются в `\u0085`/`\u2028`/`\u2029`. Это та же JSON-строка, поэтому значения при чтении идентичны. Записи без этих символов остаются побайтно прежними.
- **Совместимость.**
  - Старые корректные журналы читаются так же.
  - Записи старого writer'а с «сырыми» символами теперь читаются.
  - Журналы нового writer'а читает и код до ремонта — откат безопасен. Проверено отдельно: `probes/test_rollback_compatibility.py` — baseline-reader (RAM, байты из `baseline/`) прочитал 3/3 записи с U+0085/U+2028/U+2029, сделанные исправленным writer'ом; 1/1 PASS.
  - Автоматического «лечения» повреждённых байтов нет.

### AUD-02 — `web_alarm/operation_store.py` (`bb7eaf40…` → `acb1e4c9ccc6a9ee70684f852c48cf8ba815ea67548781f2e1e53e535468826a`)

- **Причина.** В `begin()` для новой операции порядок был такой: `payloads.put` → `_persist_record(INTENT)` → `append_event`. Историю читали только позже, в `_load_path`. При оборванной или нечитаемой истории оставались payload и INTENT без события, а клиент получал «nothing was written» или 409.
- **Исправление.** Сразу после проверок TASK/microtask, внутри уже удерживаемых `_serialized` + `mutation_lock`, до ветвления replay/new: `self.events.read_events(task_id)`. При ошибке — `OperationStoreError("operation admission refused: TASK event history is unreadable: …")`. Порядок lock не меняется, новых lock нет.
  - Executor отвечает `REFUSED` с причиной про историю; HTTP — 409.
  - Replay существующей операции на нечитаемой истории тоже отказывает до любой записи (раньше для legacy-операций он мог дописать событие в повреждённый журнал).

### AUD-05 — `web_alarm/projection.py` (`1d788d21…` → `e4503ce955a41d8e9891bc429db4f145b32027a838334081688a4d662426f4e1`)

- **Причина.** Projection читала историю только косвенно, через `_validate_history` операций. Поэтому TASK без операций с оборванной или нечитаемой историей проходила closeout как COMPLETED.
- **Исправление.** `ProjectionService.build` читает историю одним вызовом. При ошибке добавляется блокер `HISTORY_UNREADABLE`, а в basis — `history: ["UNREADABLE", …]`; это тот же шаблон, что `OPERATIONS_UNREADABLE`/`MICROTASKS_UNREADABLE`.
  - Gate closeout выдаёт `PROJECTION_HISTORY_UNREADABLE`.
  - Projection переходит в `PROJECTION_BLOCKED`, RC-6 `recover` — в FAIL_CLOSED.
  - Сохранённый checkpoint становится не VALID.
  - **При читаемой истории в basis не появляется новый ключ**, поэтому source/projection fingerprint и все существующие checkpoint не меняются.
  - Блокер добавляется после существующих, поэтому для TASK с операциями первым по-прежнему идёт `OPERATIONS_UNREADABLE`.
- **Путь `MOVED_STATUS_PENDING`** (commit point пройден). `CloseoutService.complete` по-прежнему игнорирует eligibility и дописывает только статус: `COMPLETED` с `event_recorded=false`, байты истории не меняются.
- **Путь `STATUS_WRITTEN_NOT_MOVED`** (до move). Блокер отклоняет move до ремонта истории.
- Лок-порядок и код `closeout.py` не изменены.

## 4. Независимые тесты ремонта

Новый модуль `test_web_alarm_aud010205_repair.py` (`f0b1c492f38d711e135f571fff2cefa7781f87827b5a43781e0ac69ff4d543ba`): 20 тестов, своя фикстура и байты PRE/POST.
- **Оракулы.** Байты всех файлов storage (кроме `locks/`), разбор журнала только по LF, байты цели, флаги active/completed.
- **Символы.** Настоящие U+0085/U+2028/U+2029 (через `chr()`), а не escape-строки.
- **Пути.** Реальный HTTP-путь (`WebAlarmApi.dispatch`) для P1/P1c/P2. Реальная гибель процесса (`os._exit(77)`) сразу после move для `MOVED_STATUS_PENDING`.

| Группа | Тесты |
|---|---|
| AUD-01 (6) | round-trip трёх символов + отсутствие сырых байтов в журнале; старые записи с сырыми символами читаемы; CRLF ≡ LF; оборванный хвост / невалидный JSON / пустая строка / невалидный UTF-8 / две записи через одиночный CR — отказ без изменения байтов и без append; HTTP P1 (target с U+2028); HTTP P1c (`verification_evidence` с U+2029 и U+0085) + закрытие COMPLETED с ровно одним `TASK_COMPLETED` |
| AUD-02 (6) | оборванный хвост → REFUSED, storage побайтно прежний; невалидная строка истории → то же; `begin()` → `OperationStoreError` без записи; HTTP → 409 без артефактов; контроль: здоровая admission EXECUTED с прежней последовательностью событий; replay на оборванной истории ничего не пишет |
| AUD-05 (8) | оборванный хвост / невалидная строка без операций → REJECTED с `PROJECTION_HISTORY_UNREADABLE`, байты прежние, inspect совпадает; projection `PROJECTION_BLOCKED` с причиной; checkpoint перестаёт быть VALID; после ручного восстановления разделителя — COMPLETED с одним `TASK_COMPLETED`; контроль: здоровое закрытие и basis без ключа `history`; `STATUS_WRITTEN_NOT_MOVED` → REJECTED, после ремонта COMPLETED; `MOVED_STATUS_PENDING` → COMPLETED (`event_recorded=false`), байты истории прежние |

**FAIL-first на baseline** (до правок, тот же модуль в версии на 19 тестов): 19 выполнено — **5 PASS / 13 FAIL / 1 ERROR**.
- PASS — пять контрольных сценариев: здоровая admission, replay на оборванной истории, здоровое закрытие, `MOVED_STATUS_PENDING`, CRLF.
- ERROR — `begin()` бросал `EventCheckpointStoreError` уже после записи.
- Все дефектные сценарии красные. Тест `STATUS_WRITTEN_NOT_MOVED` добавлен позже, при adversarial-разборе.

**Quality-контроли ремонта** (`probes/quality_controls_aud010205.py`, только RAM). Четыре мутанта, каждый возвращает **один** метод из `baseline/` побайтно (AST-срез; сверено, что он отличается от текущего): `read_events`, `append_event`, `begin`, `build`. **4/4 outer PASS**: каждый мутант даёт ровно 1 внутренний FAIL с ожидаемым сообщением. Значит, тесты ловят откат каждой части ремонта по отдельности.

## 5. Прогоны (guarded runner `wa4a_acceptance.py`, Windows 10 19045, `.venv` Python 3.12.10)

Изоляция поверх guard runner: `LOCALAPPDATA`/`APPDATA` и `PYTHONPYCACHEPREFIX` → disposable TEMP, `-B`.

«Финальные байты» — `event_checkpoint_store.py` `7342b221…`, `operation_store.py` `acb1e4c9…`, `projection.py` `e4503ce9…`, тест `f0b1c492…`. «Промежуточные» — `event_checkpoint_store.py` `47d3453a…` с «сырыми» U+2028/U+2029 (AST идентичен финальному; см. §8), тест — версия на 19 методов.

| Попытка | Байты | Цели | Выполнено | P / F / E / S | Exit | Изол. | с | `results.json` SHA-256 |
|---|---|---|---:|---|---:|---:|---:|---|
| red-baseline | **исходные pinned** | новый модуль (19) | 19 | 5 / 13 / 1 / 0 | 1 | 0 | 11.2 | `34aef799390030abe6f942d84e9db2b9cb67289cd6e6e89115dda9cab1ad75b5` |
| green1 | промежуточные | новый модуль (19) | 19 | 19 / 0 / 0 / 0 | 0 | 0 | 11.4 | `d2b09239…` |
| r006mod, quality, auditprobes | промежуточные | Gate B | 11 / 12 / 14 | 11/0/0/0; 12/0/0/0; 12/2/0/0 | 0 / 0 / 1 | 0 | — | `a0372ab8…`, `ec35d8c2…`, `c6ca7c1b…` |
| **repair-final** | финальные | новый модуль (20) | 20 | **20 / 0 / 0 / 0** | 0 | 0 | 13.5 | `fa2b2e725d82d00b046272113d4aeff11dec61652b4b79beb7ab5289d7a1e7bf` |
| **repair-quality** | финальные | 4 RAM-мутанта ремонта | 4 | **4 / 0 / 0 / 0** | 0 | 0 | 1.8 | `832615686ebf935c11ddbc5c0b3340b94dbace09903168f69ba2800343f226d2` |
| rollback-compat | финальные | старый reader ← новый writer | 1 | 1 / 0 / 0 / 0 | 0 | 0 | — | `b4672cbe7f8ce0a33dfdd12e107d01b8aebe6ccbc9a2ab298df083e84e729790` |
| findings | финальные | AUD-01T (2) + AUD-02b (1) | 3 | 0 / 3 / 0 / 0 (= дефекты подтверждены) | 1 | 0 | 1.5 | `2652ce4281196b5e19e7835d055763d8519beb66518cd3f1cc3c80554be9d597` |
| **full-final** | финальные | `all` | **822** | **821 / 0 / 0 / 1** | 0 | 0 | 951.9 | `fd731612c1b6ba43b8fb81ea81fb6c4d3bcabfe218ee1aed1e3fae549afb742e` |
| focused1–3 | финальные | 11 модулей (172) ×3 | 516 | 516 / 0 / 0 / 0 | 0 | 0 | 362.5 / 357.8 / 360.9 | `1a326d95…`, `7512d176…`, `a50e7d87…` |
| bounded1–5 | финальные | 2 race-селектора ×5 | 10 | 10 / 0 / 0 / 0 | 0 | 0 | 12.6–14.0 | `72bd6fe3…`, `0e146ad2…`, `81946cc0…`, `973cfcfa…`, `02c8154c…` |
| **r006mod-final** | финальные | модуль R-006 | 11 | **11 / 0 / 0 / 0** | 0 | 0 | 28.3 | `d057d2abf0925bbf92eb9c414527a32f2098b6e3a17a94df975817bcce6724fb` |
| **quality-final** | финальные | quality R-006 + R-004 | 12 | **12 / 0 / 0 / 0** | 0 | 0 | 28.3 | `764f18c30c06bb1e7c159ddb51b93fc74840a4e1b00bf70fa024ea1abd8782b7` |
| **auditprobes-final** | финальные | мои probes аудита | 14 | 12 / 2 / 0 / 0 (P3, P4 вне ремонта) | 1 | 0 | 30.5 | `46221a2792708a1630483e5a5bf742f4f385b1cb9c2626c5e3a1cbf79f20e062` |

Focused-набор: `operation_store_concurrency`, `projection_concurrency`, `reliability_wa017`, `mutation_executor`, `wa4r002_diagnostics`, `wa4r006_local_gate`, `target_claims_concurrency`, `task_store`, `lost_response`, `new_invariants`, `aud010205_repair`.

**Gate B (совместимость с R-006):**
- модуль R-006 — 11/11;
- quality R-006 + R-004 — 12/12 (мутанты R-006 по-прежнему ловятся);
- мои probes аудита: P1, P1b, P1c, P2, P6 теперь **PASS** (ранее FAIL); P5 (Windows-алиасы) PASS; 6/6 gate-проверок F1 (нативный WinError 5 до/после move), F2 (direct close ↔ executor, гибель после DONE) и F3 (crash после commit point) PASS;
- P3 и P4 падают, как и ожидалось: это AUD-03 и AUD-04, вне ремонта.

**Gate C (полный набор, финальные байты):** **822 выполнено — 821 PASS / 0 FAIL / 0 ERROR / 1 SKIP**, exit 0, изоляция 0, 951.9 с.
- Все 802 test ID R-006 присутствуют с теми же статусами; добавлены ровно 20 новых.
- SKIP прежний: `test_symlink_target_fails_closed`, symlink недоступен.
- 103 адресных теста R-006 — 103/103 PASS.
- Source map отличается от pin R-006 ровно на 4 файла ремонта.
- Сравнение со 791 с у Codex некорректно: у меня отключён байткод-кэш.

**Bounded-повторы изменённых concurrency-путей (финальные байты):**
- focused-набор из 11 модулей ×3 — 3 × 172/172 PASS;
- оба race-селектора F2/F3 ×5 — 5 × 2/2 PASS.
- Внутренних раундов гонок: 40 в bounded-повторах + 24 в focused + 8 в полном прогоне = **72 раунда**, все PASS.
- Новый модуль выполнен 5 раз на финальных байтах (repair-final, full-final, focused ×3): все 100 выполнений PASS.

**Прерванная попытка.** Первый полный прогон (`claude-aud010205-full-vvgtqdtf`) я остановил вручную после 150 тестов: все `ok`, FAIL/ERROR нет. Причина — после его старта я дописал тест и заменил в исходнике «сырые» символы (§8). Результата и exit у него нет; он **не засчитан**.

## 6. Gate D — adversarial и failure injection (ручной разбор + тесты)

- **Оборванный хвост, невалидная строка, невалидный UTF-8, пустая строка, одиночный CR.** Чтение отказывает, байты не меняются, append на оборванном хвосте отказывает (тесты AUD-01/02/05).
- **Отказ записи события.** При нечитаемой истории `begin()` отказывает раньше; `append_event` на оборванном хвосте отказывает без записи.
  - Остаётся I/O-отказ append уже **после** записи INTENT (диск, права) — это то же окно, что AUD-03 (§7).
- **Отсутствие физического apply при отказе.** Байты цели прежние во всех AUD-02/05-тестах; цепочка executor до `_apply` не доходит.
- **Отсутствие ложного clean completion.** ACTIVE и `STATUS_WRITTEN_NOT_MOVED` с нечитаемой историей → REJECTED. `MOVED_STATUS_PENDING` завершает только статус и честно возвращает `event_recorded=false`. Так и было до ремонта: commit point уже пройден.
- **Порядок lock.** Новые проверки не берут lock: в `begin()` — под уже удерживаемыми; в projection — без lock, как и прежнее чтение операций.
- **Lock-free чтение projection** (UI/inspect) может кратковременно увидеть недописанную строку. Переходы микрозадач, кроме ACTIVE-admission, пишут события вне TASK-lock. Тогда read-only view на мгновение покажет `HISTORY_UNREADABLE`.
  - Раньше то же было возможно для TASK с операциями (`OPERATIONS_UNREADABLE`).
  - Под lock (closeout) возможен лишь безопасный повторяемый отказ.
  - Дополнительное чтение `events.jsonl` в lock-free projection немного повышает вероятность безопасного нативного отказа move (см. O2 аудита).
- **Производительность.** Каждая `begin()` и каждая `build()` читают историю целиком ещё один раз. Для TASK с операциями история и раньше читалась N раз, бенчмарка больших историй нет.
- **Совместимость fingerprint.** При читаемой истории basis/fingerprint не меняются (тест). Существующие сохранённые checkpoint не становятся STALE из-за обновления.

## 7. Почему AUD-03 и AUD-04 вне ремонта

- **AUD-03** (crash между `_persist_record(INTENT)` и `OPERATION_INTENT`). Закрыть его без изменения lifecycle/reconciliation нельзя: запись INTENT без события по контракту WA4-A — «fail-closed, не automatic healing» (23).
  - AUD-02 закрывает только **детерминированный** случай: история уже нечитаема на входе.
  - Окно сбоя процесса или I/O между записью и событием остаётся, как и требует постановка («не пытаться самостоятельно решить AUD-03»).
  - Ремонт AUD-02 от AUD-03 не зависит.
  - Остаётся и сирота-payload, если сбой между `payloads.put` и `_persist_record` (content-addressed, давний).
- **AUD-04** (lock prepare до валидации `..` в `ManifestSnapshotStore`/CLI): отдельный модуль, не назначен.

## 8. FINDINGS (вне scope, код не менялся)

### AUD-01T · HIGH (availability transport-evidence) · `web_alarm/transport_event_store.py` — STOP / нужно согласование

- **Воспроизведено** (`probes/test_aud01t_transport_finding.py`, 2/2 FAIL = дефект):
  - (a) `POST /transport/events` с U+2028 в payload → 201. Затем `GET` → 409 `transport_evidence_error`, и **любой следующий POST** → 409: `append()` сначала читает все события. Одна запись блокирует всё transport-evidence всех TASK.
  - (b) Оборванный хвост: следующий `append()` принимается и склеивает записи (`}{`) — дефект класса R006-F02, не исправленный там.
- **Предлагаемый ремонт** (отдельная TASK/AMENDMENT): тот же LF-framing и экранирование, что в AUD-01, плюс проверка хвоста до записи (binary `a+b`, как в R006-F02).
- Почему STOP: другой модуль и глобальное хранилище; постановка требует согласования перед расширением.

### AUD-02b · MEDIUM · `web_alarm/state_machine.py` — тот же класс, что AUD-02

- **Воспроизведено** (`probes/test_aud02b_microtask_finding.py`, 1/1 FAIL): при оборванном хвосте `POST /microtasks/m1/transition` (ACTIVE → DONE) возвращает 409 `state_error`, но статус m1 **уже сохранён как DONE**, а события нет.
- После ремонта AUD-05 такая TASK не закроется, пока история нечитаема. Но после ручного восстановления разделителя в истории будет не хватать события перехода.
- **Предложение:** в `ServerStateMachine.transition` проверять читаемость истории до CAS. Вне write-scope.

### Наблюдение о собственном инструменте

Редактор при записи превратил escape-текст `\u2028`/`\u2029` в «сырые» символы в production-файле. Обнаружено байтовым сканом и исправлено скриптом `tools/fix_raw_separators.py` с проверкой идентичности AST.
- В финальных файлах таких символов нет: проверка на non-ASCII в изменённых модулях и тестах.
- В уже сданном probe аудита (`TASK_CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001/probes/test_claude_r006_independent.py`) есть 2 «сырых» U+2029 в строковых литералах P1c. Он работает корректно, но его SHA закреплён в отчёте аудита, поэтому файл не менялся.

## 9. Gate E — итоговая целостность (`tools/gate_e_integrity.py` → `gate-e.json`: **PASS**)

- 99/102 pinned-файла не изменены; изменены ровно 3 разрешённых. Новых файлов кроме `test_web_alarm_aud010205_repair.py` нет.
- Baseline-копии = before-pin. Восстановление в TEMP даёт точно pin R-006 — откат проверен.
- Пакет R-006 64/64 не изменён.
- Вне scope ничего не менялось: общие документы, CI, runner'ы, `server.py`, `closeout.py`, `mutation_executor.py`, `transport_event_store.py`, `state_machine.py`, рабочая область Codex, live storage.

**Откат:** скопировать `baseline/web_alarm/{event_checkpoint_store,operation_store,projection}.py` в `web_alarm/` и удалить `test_web_alarm_aud010205_repair.py`. SHA после отката: `7d094e81…`, `bb7eaf40…`, `1d788d21…`.

## 10. Ограничения

- Та же физическая машина, что у Codex и моего аудита; чистого CI нет.
- Bounded-повторы — 3 focused-круга и 72 раунда гонок; это не доказательство отсутствия гонок. Исторический CI делал 80 раундов на тест.
- Не проверялись: отключение питания, нехватка диска, внешние писатели, антивирус.
- Миграции существующих журналов нет, и она не нужна: новый reader читает и старые записи.
- **Live storage не сканировался.** Журналы, которые уже реально повреждены (оборванный хвост, невалидная строка), теперь блокируют closeout/admission до ручного восстановления — это и есть цель ремонта. Масштаб неизвестен; preflight live storage остаётся условием W3.
- Код результата executor при отказе по истории — `REQUEST_REJECTED`. Причина в тексте правдива, но код не специфичен; править `mutation_executor.py` вне scope.

## 11. DOC IMPACT, полномочия, NEXT

**DOC IMPACT** (предложения координатору; сам ничего не правил):
- **23** — контракт истории: одна запись = один физический LF (CRLF допустим); U+0085/U+2028/U+2029 пишутся экранированными; одиночный CR не разделитель. Блокер `HISTORY_UNREADABLE` / `PROJECTION_HISTORY_UNREADABLE`. Admission проверяет историю до первой durable-записи.
- **36.2** — новый модуль (20) и quality-контроли (4).
- **25 / 05 / 06 / 34 / общий 000** — статусы AUD-01/02/05, новые AUD-01T и AUD-02b.
- **24** — без изменений: WA4-R PARTIAL, WARN не включён.
- **18 / 36 / 36.1** — NO CHANGE.

**Полномочия.**
- Git/GitHub, сеть и платные вызовы не использовались.
- Production storage и live Workspace не затронуты.
- MCP, `C:\Users\REX\.codex\config.toml`, рабочая область Codex, VPN/proxy не затронуты.
- WARN/GATEWAY/STRICT не включались.

**NEXT:**
1. Независимая проверка ChatGPT: diff, тесты, quality-контроли, полный прогон.
2. Решение пользователя по AUD-01T (transport) и AUD-02b (state machine) — отдельная TASK/AMENDMENT.
3. AUD-03 и AUD-04 — по ранее предложенному порядку.
4. Чистый CI на точных байтах (W1) и read-only preflight live storage (W3) до любого решения о WARN.
