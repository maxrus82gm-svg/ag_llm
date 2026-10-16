# CLAUDE-WA4-R-AUD01T02B-REPAIR-001 — ремонт AUD-01T (transport evidence) и AUD-02b (переходы микрозадач)

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE/VERIFIED. Публикация: LOCAL ONLY / NOT SYNCED — Git не использовался, commit/push делает пользователь.

- Исполнитель: агент 008 (Claude), 2026-10-16. Verifier: ChatGPT.
- ARCH CLASS: Web Alarm Workspace / RT-001 / WA4-R Reliability. PRIMARY PROFILE 23; TEST PROFILE 36.2.
- Основание: находки AUD-01T и AUD-02b из `CLAUDE-WA4-R-AUD010205-REPAIR-001`.
- Назначение — БЛОК 1 карточки (USER-DIRECTED) и стартовое сообщение пользователя 2026-10-16. AMENDMENT не было.
- WARN, GATEWAY REQUIRED, STRICT и Final Audit не включались. **WA4-R остаётся PARTIAL.**

## 1. Итог

| Пункт | Класс | Коротко |
|---|---|---|
| **AUD-01T** — framing, хвост, параллельные писатели глобального transport-журнала | **FIXED / VERIFIED LOCALLY** | Одна запись = один физический LF (CRLF допустим); U+0085/U+2028/U+2029 пишутся экранированными; оборванный хвост — отказ, без склейки и «лечения»; read-check-append под межпроцессным lock; неудачная запись откатывается; невалидный UTF-8 → 409, а не 400 |
| **AUD-02b** — статус сохранялся, событие отклонялось | **FIXED / VERIFIED LOCALLY** (для отказа до commit) | История проверяется до любой записи (в том числе до REJECTED-события) и ещё раз под тем же lock, что CAS; статус и событие пишутся в одной секции; все пути: обычные переходы, READY→ACTIVE, DONE→VERIFIED, prepare |
| Связанный дефект: потеря событий TASK при параллельных писателях | **FIXED / VERIFIED LOCALLY** | `append_event` сериализован leaf-lock'ом на TASK (`event_checkpoint_store.py`, обоснование — `scope.md`) |
| Связанный дефект: текст с непарным суррогатом | **FIXED / VERIFIED LOCALLY** | Раньше VERIFIED/DONE сохранялись, а ответ был 400. Теперь 400 до любой записи (transition, prepare, transport) |
| Связанный дефект: closeout между статусом и событием | **FIXED / VERIFIED LOCALLY** | Событие VERIFIED пишется до снятия lock; closeout больше не вклинивается |
| Остаточное окно: гибель процесса между CAS и событием | **OPEN FINDING / NEEDS USER DECISION** | Воспроизведено (`probes/test_aud02b_residual_window.py`), см. §9 |

**Главные числа** (финальные байты, guarded runner, изоляция 0 во всех прогонах):
- полный набор: **849 — 848 PASS / 0 FAIL / 0 ERROR / 1 SKIP** (прежний symlink), exit 0, 1047 с. Все 822 прежних test ID — с прежними статусами, добавлено ровно 27 новых;
- новый модуль 27/27; FAIL-first на исходных байтах: 27 → 2 PASS (контроли) / 21 FAIL / 4 ERROR;
- мутанты 15/15 пойманы;
- R-006 11/11, quality R-006/R-004 12/12, quality AUD-01/02/05 4/4; прежние probes находок AUD-01T/AUD-02b теперь 3/3 PASS (были 3/3 FAIL);
- focused (24 модуля) 3 × 320/320; гонки 5 × 9/9;
- предварительный полный прогон `full1` (не на финальных байтах): 2 FAIL из-за перенесённого шва, §5/§7.

## 2. Baseline gate (до правок)

- `tools/baseline_gate.py` → `baseline-gate.json`: **PASS**. 103 файла ожидаемой карты (pin R-006 + 3 файла и тест ремонта AUD-01/02/05 с их итоговыми SHA) совпали побайтно. Лишних, отсутствующих и изменённых нет.
- Пакет R-006: 64/64, `manifest.json` = `b14c3664…`.
- Целевые файлы равны pin R-006: `transport_event_store.py` `107a8e89…`, `state_machine.py` `0bec1f27…`. `event_checkpoint_store.py` = итог прошлого ремонта `7342b221…`.
- Точные исходные байты — в `baseline/web_alarm/` и `baseline/tests/`. Границы — в `scope.md`; обе записи сделаны до первой правки соответствующего файла.
- Git не использовался. Ориентир постановки `main@3482216…` / №352 `7778c9e…` сверен только косвенно: байты совпали с картой прошлого ремонта, который вошёл в №352.
- **Codex 007.** Его активная TASK `CODEX-WUA-0-DESKTOP-MCP-E2E-001` запрещает ему менять `web_alarm/*.py`. Его рабочую область я не читал и не трогал. Пересечения по записи нет.
- **Прочитано:** БЛОК 1; 08 (вход и реестр); 000 общий (CURRENT); 34 (WEB_09 CURRENT); 18 — `DOC-PARALLEL-01`, `DOC-GIT-01`, `DOC-ENGINEERING-ROLES-01`, `DOC-TASK-BLOCK1-01`; 01 — Web Alarm CURRENT; 23 — шапка WA4-R, §21.1, §22, RC-6; 24 — WA-3.5; 25 — WA-3.5.A–D; 36, 36.1, 36.2 полностью; отчёт и probes прошлого ремонта.
- **Порядок работы.** Черновик `transport_event_store.py` я один раз записал до красного прогона, потом сразу вернул байты baseline (SHA `107a8e89…` проверен) и только после этого получил красный baseline. Ни один тест на черновике не запускался.

## 3. Root cause

### AUD-01T — `web_alarm/transport_event_store.py` (глобальный журнал)

1. **Framing.** Writer: `json.dumps(ensure_ascii=False)` оставляет U+0085/U+2028/U+2029 «сырыми». Reader: `read_text().splitlines()` режет по ним запись. Одно принятое событие (payload или `error_class` с U+2028) → любой следующий GET и POST дают 409: `append()` сначала читает весь журнал. Хранилище глобальное — теряется transport-evidence всех TASK.
2. **Оборванный хвост.** Reader не требовал завершающего LF, writer дописывал в текстовом режиме без проверки хвоста → запись без LF склеивалась со следующей (`}{`).
3. **Параллельные писатели (новое, измерено).** Чтение → проверка повтора → `open("a")` без lock.
   - `probes/probe_append_atomicity.py`: 8 процессов × 250 записей без lock. Выжило 826 из 2000 (text) и 616 из 2000 (binary), плюс 4 и 2 испорченные строки (`runs/append-atomicity-*.json`).
   - O_APPEND на этой Windows/Python 3.12.10 **не атомарен между процессами**.
   - Проверка `event_id` была TOCTOU: один `event_id` мог записаться дважды.
4. **Невалидный UTF-8.** `UnicodeDecodeError` (подкласс `ValueError`) уходил в HTTP 400 `invalid_value` вместо 409 `transport_evidence_error`.
5. **Сбой durable append.** `write` прошёл, `fsync` упал → ошибка вызывающему, но байты остаются. Частичная запись оставляет хвост, блокирующий всё.
6. **Непарный суррогат.** Текстовый `open("a")` успевал создать пустой журнал до ошибки кодирования.

### AUD-02b — `web_alarm/state_machine.py`

Порядок был: проверки → CAS (статус сохранён под mutation lock) → lock снят → `append_event` без lock → checkpoint. Разведка до ремонта (`probes/explore_aud02b_paths.py` → `runs/explore-aud02b-baseline.json`, реальный HTTP-путь):

| Случай | HTTP | Что осталось на диске |
|---|---|---|
| оборванный хвост: ACTIVE→DONE / READY→ACTIVE / DONE→VERIFIED / BACKUP_VERIFIED→READY | 409 `state_error` | новый статус сохранён (для ACTIVE — и указатель плана) |
| оборванный хвост: prepare | 409 `state_error` | restore point (manifest, snapshot) + BACKUP_VERIFIED |
| невалидная строка в середине: ACTIVE→DONE | **200** | статус DONE и событие **дописано в испорченный журнал** (append проверяет только последний байт) |
| невалидная строка в середине: запрещённый переход | 409 `transition_rejected` | REJECTED-событие и checkpoint записаны в испорченный журнал |
| непарный суррогат в `verification_evidence` / `operation_id` | 400 `invalid_value` | **VERIFIED / DONE сохранены** без события |
| `POST …/report` при невалидной строке в середине | 201 | событие дописано (server.py, вне scope — §9) |

Ещё две причины:
- **Closeout между статусом и событием.** Событие писалось после снятия lock. Closeout мог завершить TASK в этот промежуток, а событие VERIFIED попадало в `completed/` после `TASK_COMPLETED` (красный тест на baseline).
- **Потеря событий при параллельных писателях.** Писатели истории одной TASK держат разные lock: OperationStore — TASK-lock; state machine, report и closeout после снятия lock — никакого. На baseline 6×30 REPORT дали 82 разобранные записи + 3 испорченные строки вместо ≥180.

Блокер `HISTORY_UNREADABLE` (AUD-05) не входит в `microtask_gate._FACTS_UNREADABLE`, поэтому проверка projection в пути VERIFIED его не останавливала.

## 4. Решение и почему оно такое

### AUD-01T

- **Reader** — тот же контракт, что AUD-01: разбор только по `b"\n"`, один завершающий `\r` снимается. Обязателен завершающий LF, иначе отказ `unterminated transport event log`. Каждая строка декодируется отдельно; невалидный UTF-8 → `TransportEventStoreError` (409). Пустая строка, невалидный JSON, чужая схема и одиночный CR внутри строки → отказ. Ничего не исправляется.
- **Writer** — запись кодируется **до** lock и до открытия файла. Три разделителя транслируются в `\u0085`/`\u2028`/`\u2029` — это та же JSON-строка, значения при чтении идентичны. Непарный суррогат → `ValueError` (HTTP 400), файл не создаётся.
- **Сериализация** — `locks/transport/transport_events.lock` (тот же `InterProcessLock`, что у остальных хранилищ). Под ним: полное строгое чтение → replay/conflict по `event_id` → дозапись.
  - Lock — leaf: внутри других lock не берётся.
  - Reader без lock: одна запись = один вызов `write`. Измерено: 3992 чтения во время дозаписей одного писателя, 0 разорванных (`runs/read-during-append.json`). Поэтому GET ничего не создаёт.
- **Дозапись** — `open("a+b", buffering=0)`; проверка последнего байта (защита от писателя без lock, например старой версии кода). При `OSError` в `write`/`fsync` — `truncate` до прежнего размера + `fsync`, затем ошибка с исходом отката. Если откат не удался, ошибка прямо говорит, что журнал закрыт до ручного ремонта.
- Появился параметр `lock_timeout` (по умолчанию общий `DEFAULT_LOCK_TIMEOUT_SECONDS`); превышение → `TransportEventStoreError` (409).

### AUD-02b

- **Вход в `transition()`**: (1) `_require_encodable(verification_evidence, operation_id)` → `ValueError` (HTTP 400); (2) `_require_readable_history` → `HistoryUnreadable(ServerStateMachineError)` (HTTP 409 `state_machine_error`, «…; nothing was written»).
  - Обе проверки стоят **до** любых `_reject`. Отказ из-за повреждённой истории больше не дописывает REJECTED в испорченный журнал.
- **Commit** — одна заблокированная секция:
  - обычные переходы и ACTIVE → новый `_commit()`: `mutation_lock` → повторная проверка истории → `compare_and_set_microtask_status_locked` (для ACTIVE `activate=True` — правила F4 и указатель плана) → событие;
  - ACTIVE вызывает `_commit` внутри TASK-lock после `activation_refusal`, как раньше;
  - VERIFIED → `_admit_verified`: TASK-lock + mutation lock → проверка истории → projection → refusal → CAS → событие.
- **Сбой события после CAS** — commit point пройден, поэтому это не отказ. Ответ 200 с `event_recorded: false`, `history_error`; `next_safe_action`: «transition IS persisted… do not repeat… repair or reconcile the history». Это тот же приём, что у closeout (`event_recorded`).
- **prepare** — те же проверки на входе (до restore point). Сбой `MICROTASK_PREPARED` после записи restore point → `event_recorded: false` вместо 409.
- **Новое поле `event_recorded`** во всех ответах transition/prepare — аддитивно.

### Связанное изменение — `event_checkpoint_store.py`

- Leaf-lock `locks/events/<task_id>.lock` на время одной `append_event` (после валидации `task_id` через `_events_path`). Кодирование — до lock.
- `read_events` без lock: projection/inspect по контракту «pure, no lock, no write».

### Рассмотренные и отвергнутые альтернативы

- **Событие до статуса.** Сбой оставил бы ложную запись о несостоявшемся переходе — история «впереди» authority. Статус — authority (RC-5), и недостающая запись честнее ложной.
- **Откат статуса при сбое события.** `append_event` может упасть уже после того, как байты легли (`fsync`). Откат статуса дал бы обратное расхождение. Нужен отдельный транзакционный контракт (§9).
- **Lock на чтение.** Нарушил бы «pure, no lock, no write» projection/inspect и создавал бы lock-файлы при GET. Измерение показывает, что это не нужно.
- **Полная проверка истории в каждом `append_event`.** O(история) на каждую запись у всех писателей и широкая смена поведения. Пошаговых проверок (state machine, AUD-02 `begin()`, AUD-05 projection) достаточно; REPORT остаётся находкой.
- **Срезать незавершённый хвост при чтении.** Запрещено постановкой (инвариант 4).
- **Оставить шов `TaskStore.compare_and_set_microtask_status`.** Тогда невозможны проверка истории под lock, порядок событий и защита от вклинивания closeout.

## 5. Изменённые файлы

| Файл | SHA-256 до | SHA-256 после | Байт |
|---|---|---|---:|
| `web_alarm/transport_event_store.py` | `107a8e89cff2ffaae2a6eb899d0028e1c2a46788e12edfc3de5b9448a3b020cf` | `cbd74a2526932f2063fef4ea73bf31b53fdab3504abe5ff6ac5a611769a91d95` | 11 736 |
| `web_alarm/state_machine.py` | `0bec1f270ac957fff279d3cf1de13201421600b6b173ef0f17b983c57bfac2fb` | `3164383a1a881c6dfcac86678b746d01c038f1b4ccb988fbda5a6074a262f408` | 31 246 |
| `web_alarm/event_checkpoint_store.py` | `7342b221e6663bee65bef116f57507b0de84b74269cb7541f4955b527eb91304` | `9cf9e3ed45a415bfcab139bdb24fc88af65c7ece8723f1f5192c3e9a0ab8bf45` | 10 479 |
| `test_web_alarm_state_machine_cas.py` | `7a2ce35e5342667d490c3494666fbec0b43af4d883f815f23a472f6d092e1dff` | `e00c5f1bbce9c5900887b767bc52195737a783f3cac15baa8f84459e55ca7e77` | 17 567 |
| `test_web_alarm_recovery_coordinator_repair3.py` | `bf316497034a0f28f211ad27e25e079dc2bf3f3dd575a72aeff08c7e2d983811` | `76244e276ffeb53737723a361c26b52479c39302b3d93ce68f22e074dc3b3016` | 37 339 |
| `test_web_alarm_aud01t02b_repair.py` | новый | `b96c2b0cec62b05998075e068a4c13edb0969dadfa6210d20aecd53b25ff0ef3` | 41 845 |

Полный diff: `source-changes.diff` (`4842f8a2e1fa78c82a375fd8fc84594e455523de7ebd33ba6d74bbba9e8508ca`; +325 / −104 строки, пять файлов). Все файлы LF, без «сырых» U+0085/U+2028/U+2029, `compile()` в памяти — OK.

**Два существующих теста, только точка инъекции** (`scope.md`, записано до правки; исходные байты — `baseline/tests/`):
- `test_web_alarm_state_machine_cas.py` (`SM_CHILD`) — добавлен барьер на `ServerStateMachine._commit`, старый барьер на `TaskStore.compare_and_set_microtask_status` остался;
- `test_web_alarm_recovery_coordinator_repair3.py::test_f4…` — инъекция «параллельный replan» перенесена с `TaskStore.compare_and_set_microtask_status` на `ServerStateMachine._commit`.

Причина: оба теста ставили барьер на нелоковый CAS, который state machine больше не вызывает. В `full1` оба упали (§7), после переноса шва проходят. Что они по-прежнему ловят свой дефект, доказано мутантами S3 и S9 (§6).

## 6. Тесты

**Новый модуль `test_web_alarm_aud01t02b_repair.py`** (`b96c2b0c…`): 27 тестов, свои TEMP-фикстуры.
- **Оракулы.** Байты всех файлов storage вне `locks/`, журналы по физическому LF (`lf_records` / `tolerant_records`), байты цели.
- **Символы** — `chr()`, не escape-строки.
- **Пути.** Реальный `WebAlarmApi.dispatch` для HTTP. Отдельные Python-процессы на файловом барьере для гонок. `os._exit` в residual-probe.

| Группа | Тесты |
|---|---|
| TransportFramingTests (8) | HTTP с U+0085/U+2028/U+2029 в payload, ключе и `error_class` → 201, GET 200, второй POST 201, в файле ровно 2 LF-записи без «сырых» байтов; старые «сырые» и CRLF-записи читаются и дописываются, префикс цел; оборванный хвост (полный JSON без LF и частичный JSON) → чтение, append, GET и POST отказывают (409), байты прежние; невалидный JSON / пустая строка / невалидный UTF-8 / две записи через CR / BOM → то же; replay/conflict после переоткрытия; запись и чтение в свежих процессах; непарный суррогат → 400 без файла; GET на пустом storage ничего не создаёт (контроль) |
| TransportDurabilityTests (4) | 6 процессов × 40 POST → 240 уникальных записей, порядок каждого писателя сохранён; 5 процессов × 6 replay одного `event_id` → одна запись, все ответы — она; `fsync` падает → ошибка и байты прежние, следующий append работает; lock у другого процесса → отказ без записи |
| MicrotaskHistoryTests (6) | оборванный хвост: ACTIVE→DONE; ещё 7 переходов (BACKUP_VERIFIED→READY, READY→ACTIVE, ACTIVE→UNKNOWN, DONE→VERIFIED, DONE→FAILED_VERIFICATION, FAILED_VERIFICATION→ACTIVE, UNKNOWN→RECOVERY_REQUIRED) → 409 `state_machine_error`, storage побайтно прежний; невалидная строка в середине: разрешённый, запрещённый и stale-переход → ни статуса, ни REJECTED; prepare → нет restore point; история рвётся между входной проверкой и lock (ACTIVE→DONE, READY→ACTIVE, DONE→VERIFIED) → отказ; непарный суррогат → 400 без записи |
| MicrotaskCommitTests (7) | здоровые DONE и VERIFIED: события и `event_recorded=true`; stale `expected_status` → 409 с REJECTED (контроль); детерминированный stale CAS (статус меняется до lock) → 409, новее статус не перезаписан; сбой события после CAS → 200, `event_recorded=false`, статус DONE, история прежняя; то же для prepare → 200, BACKUP_VERIFIED + restore point; events-lock у другого процесса → отказ записи без байтов, после освобождения запись проходит; closeout вклинивается между статусом и событием VERIFIED → не может, порядок `MICROTASK_TRANSITION(VERIFIED)`, `TASK_COMPLETED` |
| HistoryConcurrencyTests (2) | 6 процессов × 30 REPORT → все 180 событий, журнал цел; 6 циклов DONE→FAILED_VERIFICATION→ACTIVE в одном процессе против 4×25 REPORT в других → все 18 событий переходов в точном порядке и все 100 REPORT |

**FAIL-first.**
- **На репозитории до правок** (pin-байты, промежуточные версии модуля): `red-baseline` — 24 теста: 2 PASS / 17 FAIL / 5 ERROR; `red-baseline2` — 24: 2 PASS / 19 FAIL / 3 ERROR (`runs/red-baseline2.census.json`).
- **Финальный модуль на точных исходных байтах** (`red-final`, TEMP-зеркало `tools/make_baseline_mirror.py`: 107a8e89 / 0bec1f27 / 7342b221 + тест b96c2b0c) — 27: **2 PASS / 21 FAIL / 4 ERROR**.
  - PASS — только контроли: stale `expected_status` и «GET на пустом storage».
  - ERROR — по сути те же дефекты: `lock_timeout` нет в старом конструкторе; старый reader бросает исключение на собственных записях; `_commit` в старом коде отсутствует.
- На baseline гонки показали реальную потерю:
  - 6×30 REPORT → 82 разобранные записи + 3 испорченные строки;
  - transport — сотни 409 из-за framing.

**Зелёные прогоны на финальных байтах:** `green3` 27/27; `full-final` 27/27 в составе 849; focused 3 × 27/27. Итого 135 выполнений нового модуля, все PASS.

**Quality-контроли** (`probes/quality_mutants_aud01t02b.py` → `runs/quality-mutants.json`):
- Каждый мутант — одна замена фрагмента одного файла в отдельном TEMP-зеркале. Тест — в свежем процессе, поэтому межпроцессные мутанты настоящие.
- Мутант CAUGHT, если тест не прошёл и в выводе есть ожидаемое сообщение. Контроль: те же селекторы на немутированном зеркале проходят.

| Мутант | Тест | Итог |
|---|---|---|
| T1 reader на `str.splitlines` | `test_pre_repair_raw_separator_and_crlf…` | CAUGHT |
| T2 reader принимает хвост без LF | `test_unterminated_tail_is_refused_never_spliced` | CAUGHT |
| T3 writer пишет разделители «сырыми» | `test_http_separator_text_keeps…` | CAUGHT |
| T4 transport-append без lock | `test_concurrent_processes_lose_no_transport_event` (процессы) | CAUGHT |
| T5 без отката неудачной записи | `test_failed_durable_append_is_rolled_back_and_reported` | CAUGHT |
| E1 `append_event` без events-lock | `test_concurrent_reports_from_processes_lose_no_event` (процессы) | CAUGHT |
| S1 нет проверки истории на входе | `test_invalid_line_history_refuses_steps_and_rejections…` | CAUGHT |
| S2 нет проверки под lock в `_commit` | `test_history_turning_unreadable_before_the_commit_lock…` | CAUGHT |
| S3 `activate=False` (нет правил F4 под lock) | существующий `test_f4_activation_rechecks…` | CAUGHT |
| S9 `_commit` без CAS | `test_plain_step_decided_on_a_stale_status…` | CAUGHT |
| S4 нет проверки под lock в `_admit_verified` | `test_history_turning_unreadable…` [DONE->VERIFIED] | CAUGHT |
| S5 событие VERIFIED после снятия lock | `test_closeout_cannot_interleave…` | CAUGHT |
| S6 сбой события после CAS как отказ | `test_history_failure_after_commit_is_reported_as_committed` | CAUGHT |
| S7 нет проверки кодируемости | `test_unencodable_text_is_refused_before_any_write` (state machine) | CAUGHT |
| S8 prepare без проверки истории | `test_prepare_on_unreadable_history_writes_no_restore_point` | CAUGHT |

- **Итог: 15/15 CAUGHT**, контроль 14/14 селекторов PASS (`runs/quality-mutants2.json`, `53ffeb55…`).
- **Первая попытка** (`runs/quality-mutants.json`, `14397e36…`) — 12/15 по строгому текстовому критерию. S1, S2 и S7 там тоже упали (failures=2 у каждого), но первым срабатывал assertion на HTTP-код, а его текста не было в списке ожидаемых. Это дефект критерия, не тестов: ожидаемые сообщения дополнены, тесты не менялись. Первый результат сохранён.
- **Не покрыто мутантом:** проверка последнего байта в `_append_locked` (transport). Это защита от писателя без lock — например, старой версии кода между чтением и записью. Строгое чтение под lock срабатывает раньше, поэтому из тестов эта ветка недостижима.

## 7. Прогоны

Guarded runner `wa4a_acceptance.py`, Windows 10 19045, `.venv` Python 3.12.10. Изоляция поверх guard: `LOCALAPPDATA`/`APPDATA` и `PYTHONPYCACHEPREFIX` → TEMP, `-B`.

Все попытки с `results.json` SHA-256, census по методам, source map и non-PASS — в `evidence.json`. Исходные `results.json` остаются в TEMP. Свои JSON/MD/TXT в папке TASK приведены к LF, UTF-8 без BOM, U+0085/U+2028/U+2029 — escape-текстом (`tools/normalize_task_files.py`, содержимое JSON эквивалентно). Хеши в отчёте — после нормализации. Census считает по методам: счётчик `passed` у runner уходит в минус при упавших subTest — известный дефект ASTRA.

| Попытка | Байты | Цели | Методов | P / F / E / S | Exit | Изол. | с |
|---|---|---|---:|---|---:|---:|---:|
| red-baseline, red-baseline2 | pin (до правок) | новый модуль (24, промежуточный) | 24 / 24 | 2/17/5/0; 2/19/3/0 | 1 / 1 | 0 | 23.5 / 26.7 |
| green1 | ремонт, промежуточный тест | новый модуль | 24 | 22/2/0/0 — ошибка оракула теста: API обрезает пробельные символы (U+0085/U+2028) в текстовых полях | 1 | 0 | 31.6 |
| green2 | то же, оракул исправлен | новый модуль | 24 | 24/0/0/0 | 0 | 0 | 32.0 |
| **full1 (предварительный)** | промежуточные | `all` | 846 | **843/2/0/1** — FAIL: `test_c…` (state_machine_cas) и `test_f4…` (repair3): шов `TaskStore.compare_and_set_microtask_status` | 1 | 0 | 974.6 |
| seam1 | после переноса шва | cas, repair3, state_machine, новый (24) | 77 | 77/0/0/0 | 0 | 0 | 87.9 |
| green3 | **финальные** | новый модуль (27) | 27 | 27/0/0/0 | 0 | 0 | 40.4 |
| **full-final** | **финальные** | `all` | **849** | **848/0/0/1** | 0 | 0 | 1047.0 |
| r006mod-final | финальные | модуль R-006 | 11 | 11/0/0/0 | 0 | 0 | 33.4 |
| quality-r006-r004 | финальные | Sensitivity R-006 + R-004 | 12 | 12/0/0/0 | 0 | 0 | 29.1 |
| quality-aud010205 | финальные | RAM-мутанты прошлого ремонта | 4 | 4/0/0/0 | 0 | 0 | 1.9 |
| prior-findings | финальные | probes AUD-01T (2) + AUD-02b (1) | 3 | **3/0/0/0** (раньше 0/3) | 0 | 0 | 1.5 |
| auditprobes-final | финальные | probes аудита R-006 | 14 | 12/2/0/0 — P3, P4 = AUD-03/04, вне ремонта | 1 | 0 | 32.0 |
| own-probes | финальные | rollback-compat (3) + residual (1) | 4 | 2/0/2/0 — дефект probe: модуль не в `sys.modules` | 1 | 0 | 1.4 |
| own-probes2 | финальные | то же, probe исправлен | 4 | 4/0/0/0 | 0 | 0 | 2.5 |
| focused1–3 | финальные | 24 модуля (11 прежних + transport ×4 + recovery report ×4 + event store + state_machine + cas + repair3 + новый) | 320 ×3 | 320/0/0/0 ×3 | 0 | 0 | 472.7 / 477.8 / 473.3 |
| bounded1–5 | финальные | 2 race-селектора F2/F3 + TransportDurability + HistoryConcurrency + closeout-interleave | 9 ×5 | 9/0/0/0 ×5 | 0 | 0 | 25.4–28.3 |
| red-final | **исходные** (зеркало) | финальный новый модуль | 27 | 2/21/4/0 | 1 | 0 | 32.9 |

- **Гонки на финальных байтах.** Межпроцессные тесты нового модуля (4 шт.) и closeout-interleave прошли по 9 раз: full + focused ×3 + bounded ×5. Оба race-селектора F2/F3 тоже по 9 раз; внутренних раундов 72, все PASS.
- **Сверка с полным прогоном прошлого ремонта** (`runs/full-final.vs-aud010205.json`, предыдущий `results.json` `fd731612…`): 0 пропавших ID, 0 сменивших статус, +27 — все из нового модуля.
- **Платформенные probes** (вне runner, только TEMP):
  - `probe_append_atomicity` — 8 × 250 без lock: text 826/2000 уникальных + 4 испорченные строки; binary 616/2000 + 2;
  - `probe_read_during_append` — 3992 чтения, 0 разорванных;
  - `explore_aud02b_paths` — 10 случаев (§3).

## 8. Gate D — MANUAL ENGINEERING REVIEW

**Проверенные гипотезы:**

| # | Гипотеза | Итог |
|---|---|---|
| H1 | AUD-01T = `splitlines` + «сырые» разделители | подтверждено (красные тесты на baseline) |
| H2 | оборванный хвост склеивается | подтверждено |
| H3 | параллельные писатели теряют записи (transport и история TASK) | подтверждено: платформенный probe и красные тесты |
| H4 | читатель без lock видит частичную запись при одном писателе | **отвергнуто** на этой платформе (0/3992) → читатели остаются без lock |
| H5 | AUD-02b на всех путях перехода | подтверждено (10 случаев разведки) |
| H6 | тот же класс через непарный суррогат | подтверждено, новая находка, исправлено |
| H7 | тот же класс в prepare | подтверждено, исправлено |
| H8 | невалидная строка в середине не видна append'у | подтверждено, исправлено для state machine (REPORT — §9) |
| H9 | closeout вклинивается между статусом и событием | подтверждено (красный тест), исправлено |
| H10 | VERIFIED-путь останавливается projection'ом на `HISTORY_UNREADABLE` | **отвергнуто**: блокер не входит в `_FACTS_UNREADABLE` |
| H11 | невалидный UTF-8 transport → 400 | подтверждено, исправлено (409) |
| H12 | `fsync`-сбой оставляет байты | подтверждено, исправлено (откат) |

**Порядок lock и взаимоблокировки.**
- Новые lock — leaf: внутри `append_event` и transport-append других lock не берётся.
- Порядок state machine прежний: TASK-lock → mutation lock (VERIFIED, ACTIVE) или только mutation lock.
- Событие пишется под этими lock, events-lock берётся последним. Циклов нет.
- Closeout (TASK → mutation) ждёт на TASK-lock и mutation lock — это и нужно (тест вклинивания).

**Crash/restart.**
- Гибель процесса между CAS и событием — остаточное окно (§9, воспроизведено).
- Гибель во время transport-append (после `write`, до `fsync`) может оставить оборванный хвост → глобальный fail-closed до ручного ремонта (§9).
- Откат при `OSError` закрывает только I/O-ошибки живого процесса.

**Replay/idempotency.**
- Transport: проверка `event_id` теперь под lock — межпроцессный replay даёт одну запись (тест).
- Сравнение identity прежнее (Python-равенство словарей). Особенности `1 == 1.0 == True` и `NaN != NaN` унаследованы — LOW, §9.

**Stale CAS.**
- Сохранён: `compare_and_set_microtask_status_locked` под тем же lock.
- Детерминированный тест: статус меняется перед входом в lock → REJECTED, новый статус не перезаписан. Мутант S9 ловится.
- Правила активации F4 под lock сохранены (`test_f4`, мутант S3).

**Неполный fsync / I/O.**
- Transport: откат + честная ошибка (тест с инъекцией).
- История TASK: `append_event` не откатывается (прежнее поведение `event_checkpoint_store`). Сбой после CAS → `event_recorded=false`.

**Read-only inspect.**
- GET `/transport/events` и projection/inspect lock не берут и ничего не пишут.
- GET на пустом storage не создаёт ни журнала, ни lock (тест).

**Расхождение статуса и события.**
- До commit — невозможно на детерминированных путях (повреждённая история, некодируемый текст): отказ до любой записи.
- После commit — только I/O или гибель процесса; первое возвращается как `event_recorded=false`, второе — §9.

**Независимые оракулы.** Байты storage и журналов по LF, а не production projection. Projection используется только как вторичное наблюдение в residual-probe.

**Совместимость.**
- Формат журналов не изменился (только экранирование трёх символов в transport — та же JSON-строка).
- Старый reader читает новые журналы, смешанная запись старым и новым кодом читается (rollback-probe).
- Новые lock-файлы старым кодом игнорируются.

**Производительность.**
- Каждый transition читает историю 2 раза (VERIFIED — 3, вместе с projection); transport-append — весь журнал под lock (как и раньше, но теперь последовательно).
- Бенчмарка больших журналов нет (NOT RUN).

## 9. Классификация

**FIXED / VERIFIED LOCALLY:** AUD-01T (framing, хвост, параллельные писатели, UTF-8 → 409, откат неудачной записи, суррогаты); AUD-02b (отказ до записи на всех путях, включая prepare и REJECTED); потеря событий TASK при параллельных писателях; суррогаты в transition/prepare; вклинивание closeout.

**OPEN FINDING:**
- **AUD-02b-R** (MEDIUM, остаточное окно) — гибель процесса после CAS, до события: статус сохранён, события нет, ни closeout, ни projection это не замечают (`probes/test_aud02b_residual_window.py`). Полное закрытие требует нового транзакционного/reconciliation-контракта (см. NEEDS USER DECISION). Тот же класс, что AUD-03.
- **AUD-01T-R** (MEDIUM, availability) — гибель процесса посреди transport-append оставляет оборванный хвост → всё transport-evidence закрыто до ручного ремонта (так и требует инвариант fail-closed). Нужен штатный ручной ремонт.
- **AUD-02c** (LOW-MEDIUM, `server.py`, вне scope) — `POST /microtasks/{id}/report` дописывает событие в историю с невалидной строкой в середине (append проверяет только хвост). Сериализация теперь общая, но полной проверки нет. Похожее у прочих писателей OperationStore после `begin()` (класс AUD-03).
- **AUD-01T-P** (LOW, производительность) — каждая transport-запись разбирает весь глобальный журнал под lock; журнал не ротируется.
- **AUD-01T-I** (LOW) — identity replay сравнивается Python-равенством (`1 == 1.0 == True`, `NaN != NaN`).
- **LOCK-T** (LOW) — повисший писатель держит events-lock > 10 с → у остальных отказ записи события; после CAS это `event_recorded=false`.
- AUD-03, AUD-04 — без изменений, OPEN.

**NOT RUN:** чистый CI на точных байтах (W1); read-only preflight live storage (W3); бенчмарк больших журналов; отключение питания и нехватка диска (кроме инъекции `fsync`); другие ФС и ОС (атомарность чтения измерена только здесь); Python 3.13.

**NEEDS USER DECISION:**
1. **Контракт для AUD-02b-R / AUD-03.** Вариант: в записи микрозадачи (или операции) хранить `pending_event_id` до записи события, а projection/closeout проверять, что событие с этим id есть. Расхождение «статус впереди истории» видно и сверяется явно, без автоматического «лечения».
2. **Ремонт глобального transport-журнала после crash (AUD-01T-R).** Ручная процедура или инструмент: перенести оборванный хвост в отдельный evidence-файл с журналом действия, не удаляя байты.
3. Ремонт AUD-02c (`server.py`) — отдельной TASK или AMENDMENT.

## 10. Gate E — итоговая целостность

`tools/gate_e_integrity.py` → `gate-e.json` (`8bb8eac3…`): **PASS**.
- Из 103 файлов карты до ремонта 98 не изменены. Изменены ровно 5 разрешённых: 3 модуля и 2 теста (только точка инъекции).
- Новый файл — только `test_web_alarm_aud01t02b_repair.py`.
- Все шесть файлов LF, без «сырых» разделителей.
- Копии baseline равны байтам до ремонта. Восстановление в TEMP воспроизводит их точно — откат проверен.
- Пакет R-006 64/64 не изменён.
- Вне scope ничего не менялось: общая документация (кроме ротации своей карточки), CI, runner'ы, `server.py`, `closeout.py`, `operation_store.py`, `projection.py`, `task_store.py`, рабочая область Codex и live storage.

**Откат:** скопировать `baseline/web_alarm/{transport_event_store,state_machine,event_checkpoint_store}.py` в `web_alarm/`, `baseline/tests/*.py` — в корень, удалить `test_web_alarm_aud01t02b_repair.py`. Lock-файлы `locks/transport/`, `locks/events/` старым кодом не используются; удалять не обязательно.

## 11. Ограничения

- Одна машина (та же, что у прошлых прогонов и у Codex); чистого CI нет.
- Bounded-повторы — не доказательство отсутствия гонок.
- Атомарность чтения без lock измерена только на этой NTFS. На другой ФС возможен кратковременный безопасный 409.
- Live storage не сканировался. Журналы, которые уже повреждены, теперь блокируют переходы, prepare и transport-evidence до ручного восстановления — это и есть цель ремонта; масштаб неизвестен (W3).
- Изменение API: в ответах transition/prepare новое поле `event_recorded` (+ `history_error`). Отказ по истории — 409 `state_machine_error` (раньше 409 `state_error` с уже сохранённым статусом).

## 12. DOC IMPACT, полномочия, NEXT

**DOC IMPACT** (предложения координатору, сам не правил):
- **23** — контракт transport-evidence:
  - LF-framing, экранирование, оборванный хвост → fail-closed;
  - запись под lock, откат неудачной записи, читатели без lock.

  Контракт истории TASK:
  - запись событий одной TASK сериализована (`locks/events/<task>.lock`);
  - переход микрозадачи — статус и событие в одной секции;
  - отказ до записи (409 `state_machine_error` / 400);
  - сбой истории после commit → 200 `event_recorded=false`;
  - остаточное окно AUD-02b-R.
- **36.2** — новый модуль (27), мутанты (15), перенос шва в двух существующих тестах.
- **25 / 05 / 06 / 34 / общий 000** — статусы AUD-01T/AUD-02b (RESULT READY), новые находки AUD-02b-R, AUD-01T-R, AUD-02c и др.
- **24** — без изменений: WA4-R PARTIAL, WARN не включён.
- **18 / 36 / 36.1** — NO CHANGE.

**Полномочия.**
- Git/GitHub, сеть и платные вызовы не использовались.
- Production storage и live Workspace не затронуты.
- MCP, рабочая область Codex и общая документация не затронуты.
- WARN/GATEWAY/STRICT не включались.

**NEXT:**
1. Независимая проверка ChatGPT.
2. Решения пользователя по §9: контракт AUD-02b-R/AUD-03, ремонт transport-журнала, AUD-02c, AUD-04.
3. Чистый CI на точных байтах (W1) и read-only preflight live storage (W3) до любого решения о WARN.
