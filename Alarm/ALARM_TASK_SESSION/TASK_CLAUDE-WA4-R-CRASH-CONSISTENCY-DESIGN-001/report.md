# CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 — аварийная согласованность состояния и истории (AUD-02b-R + AUD-03)

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION — DESIGN PROPOSAL.** Не REPAIR VERIFIED. Production-код не менялся. Публикация: LOCAL ONLY / NOT SYNCED — commit/push делает пользователь.

- Исполнитель: агент 008 (Claude), 2026-10-17. Verifier: ChatGPT.
- ARCH CLASS: Web Alarm Workspace / RT-001 / WA4-R Reliability. PRIMARY 23; PLAN 24; HISTORY 25; TEST PROFILE 36.2; правила 36/36.1.
- Назначение — БЛОК 1 (USER ASSIGNED) + стартовое сообщение пользователя. AMENDMENT не было.
- WA4-R остаётся PARTIAL; WARN / GATEWAY REQUIRED / STRICT / Final Audit не включались.

## 1. Итог

| Окно | Что воспроизведено (реальная гибель дочернего процесса + fresh reopen) | Класс риска |
|---|---|---|
| **W1 — AUD-02b-R** (CAS статуса микрозадачи → смерть → нет `MICROTASK_TRANSITION`) | Расхождение **невидимо**: projection чистая, блокеров нет. После потерянного события **VERIFIED closeout завершает TASK** (COMPLETED), хотя текст verification evidence нигде не сохранился — он жил только в payload события. После потерянной активации mutation выполняется (EXECUTED). | **false-safe** (ложно-чистое закрытие, утрата доказательства) |
| **W2 — AUD-03** (запись INTENT → смерть → нет `OPERATION_INTENT`) | Fail-closed, но **тупик**: ни один API не читает, не урегулирует и не отменяет операцию; recover → FAIL_CLOSED. Одна сирота делает нечитаемыми **все операции TASK**. Та же сирота остаётся и при обычной I/O-ошибке живого процесса: ответ 409 `state_error`, запись на диске. | safe, но потеря доступности (manual-only) |
| W3 — сравнение (DONE операции записан → смерть → нет `OPERATION_TRANSITION`) | Допускается **по замыслу**: `_validate_history` признаёт отставание истории после INTENT, replay → REPLAYED, повторного apply нет. | контроль: уже действующий прецедент «запись — authority, история может отставать, но не противоречить» |

**Рекомендация (§6):**
- **Операции (AUD-03) — R-OP**, без изменения схемы. Событие `OPERATION_INTENT` полностью выводится из записи (проба: совпадение 10/10 полей). Поэтому сироту узкой формы (`INTENT`, revision 1, ни одного события операции) читать как `INTENT_EVENT_PENDING` и детерминированно дописывать событие под lock, а не превращать в тупик.
- **Микрозадачи (AUD-02b-R) — R-MT, write-ahead намерение в журнале.** До CAS в журнал пишется `MICROTASK_TRANSITION_INTENT` с from/to/evidence, после CAS — commit `MICROTASK_TRANSITION` с тем же `intent_id`. Незакрытое намерение разрешается по authoritative-статусу: дописать commit или `ABANDONED`. Evidence становится durable **раньше** статуса.
  - Изменения схемы записей нет: проба показала, что текущий код отвергает любое новое поле в записи, но игнорирует новые типы событий. Поэтому вариант безопасен для отката.
- Обе части требуют **утверждения пользователя**; ни одна строка production-кода не изменена.

Прогоны: 13 проб × 3 раза — по 8 PASS (CONTROL/TRIGGER/SAFETY) + 5 FAIL (все INVARIANT = воспроизведённые дефекты), детерминированно; совместимость 4/4; изоляция 0; все прогоны на точных исходниках (source map 104/104 = source gate).

## 2. Вход и чтение

- `source-gate.json` (`72547a89…`): **PASS**, 104/104 файла = итог `CLAUDE-WA4-R-AUD01T02B-REPAIR-001` (опубликован в №354 по данным 34/23/36.2). Git не использовался. Повтор в конце — PASS.
- **Прочитано:** БЛОК 1 полностью; CURRENT 2026-10-17 в 34, 23, 36.2, 000, 08; правило `DOC-LOCAL-REPORT-HANDOFF-01` (18). 01/24/25/36/36.1 — читал целиком в этой сессии днём раньше (16.10), CURRENT-разделы 17.10 сверены.
  - Отчёт, scope, manifest, evidence, gate-e и `probes/test_aud02b_residual_window.py` прошлой TASK — мои собственные, сверены по SHA.
  - Код: `state_machine.py`, `operation_store.py` (begin/`_validate_history`/transition/settle), `event_checkpoint_store.py`, `task_store.py`, `projection.py` (блокеры/closeout), `closeout.py`, `recovery_coordinator.py` (`_set_micro_locked`, recover), `microtask_gate.py`, `models.py`, `server.py` (маршруты), `resolver_service.apply`, `manifest_store` (места записи статуса).
- **Учтены замечания verifier'а к прошлой сдаче:** сырые `results.json` теперь опубликованы (очищенные от машинных путей, исходные SHA сохранены); manifest перечисляет все файлы.

## 3. Карта durable commit points и окон «запись → событие»

Все записи — атомарная замена файла: temp + fsync + `os.replace`, **без fsync каталога**. Все события — append в `events.jsonl` под leaf events-lock + fsync. Порядок lock: operations TASK-lock → mutation lock → events-lock (leaf).

| # | Писатель (код) | Durable запись (commit point) | Событие после | Как обнаруживается отсутствие события сейчас |
|---|---|---|---|---|
| W1 | `ServerStateMachine._commit` / `_admit_verified` / `_admit_active` (`state_machine.py`) | `microtasks/<id>.json` (status; для ACTIVE раньше пишется `plan.json`) под mutation lock | `MICROTASK_TRANSITION` {from,to,verification_evidence} в той же секции | **никак**: ни один читатель не сверяет событие со статусом; evidence существует только в событии |
| W1p | `prepare_microtask` → `manifest_store` (8 мест записи статуса) | restore point + PREPARING → BACKUP_VERIFIED / BLOCKED_PREPARE | `MICROTASK_PREPARED` / `_PREPARE_FAILED` (от state machine) | никак |
| W1r | `RecoveryCoordinator._set_micro_locked` (RECOVERY_REQUIRED, RETRY re-arm → ACTIVE) | статус микрозадачи | **событие не пишется вообще** (по замыслу) | n/a — журнал не полная история статусов |
| W2 | `OperationStore.begin` | payload (content-addressed) → `operations/<op>.json` INTENT rev 1 | `OPERATION_INTENT` | `_validate_history`: «missing durable intent history» → запись **нечитаема**; `list()` падает → `OPERATIONS_UNREADABLE` на всю TASK |
| W3 | `_transition_locked`, `_settle_recovery_locked` | запись операции (revision+1, receipt/settlement) | `OPERATION_TRANSITION` / `OPERATION_RECOVERY_SETTLED` | допускается: события после INTENT могут отставать, но не противоречить |
| W4 | `CloseoutService.complete` | `os.replace` active→completed (+ статус COMPLETED) | `TASK_COMPLETED` после снятия lock | `event_recorded=false` в ответе; на диске признака нет |
| W5 | `ResolverService.apply` (`store.write_new`) | resolution record | событие резолвера | не исследовалось пробой (code-read) |

**Выводы фазы A.**
1. Политика непоследовательна. Для операций INTENT-событие обязательно (сирота = фатально), последующие допускаются отсутствующими. Для микрозадач события не проверяются вовсе. RC-6 и manifest-store пишут статус совсем без событий.
2. **Authority** — файлы записей (RC-5: lifecycle is authority). Журнал — история и доказательства. Единственное место, где журнал несёт **уникальное** содержимое, — `verification_evidence` в событии VERIFIED.
3. **Вывести статус из журнала невозможно** (вариант C для микрозадач): журнал по замыслу неполон (W1r, W1p).
4. **Payload-сирота** при W2 — content-addressed файл без операции (видно в пробах), безвреден, но не собирается.
5. **Power loss** (не воспроизводился): у `os.replace` нет write-through, fsync каталога нет. После отключения питания запись статуса может пропасть, а уже fsync'нутое событие — остаться. Получится история «впереди» authority. В текущем коде порядок «запись → событие» делает это возможным только на границе W1/W2 (событие после записи).

## 4. Пробы (фаза B)

**Механика.**
- `probes/crash_worker.py` (`499f7f66…`) — дочерний процесс, один production-вызов через реальный `WebAlarmApi.dispatch`. Перед нужным append он перечитывает запись **с диска**: это доказывает, что durable-фаза достигнута. Затем пишет fsync'нутый маркер и делает `os._exit(70/78/79)`; режим `raise_*` вместо смерти бросает injected-исключение.
- `probes/reopen_inspector.py` (`df354f75…`) — второй, **непатченный** процесс. Снимает raw-оракулы (JSON-файлы, журнал по физическому LF, байты цели) и server views (`OperationStore.list`, `ProjectionService.build`, `validate_checkpoint`, `CloseoutService.inspect`), затем выполняет follow-up шаги.
- Каждый физический apply трассируется (`apply_enter`).
- `probes/test_crash_windows.py` (`0e794fa1…`) — 13 проб. Префикс означает ожидание: CONTROL/TRIGGER/SAFETY должны проходить; INVARIANT формулирует контракт будущего ремонта, и FAIL = воспроизведённый дефект.

| Проба | Итог (×3) | Факт |
|---|---|---|
| W1 `CONTROL_healthy_steps_record_events_and_close` | PASS | DONE → VERIFIED → COMPLETED, события с evidence |
| W1 `TRIGGER_process_dies_after_durable_DONE_before_its_event` | PASS | exit 70; маркер: на диске DONE; события нет; журнал цел |
| W1 `INVARIANT_reopen_reports_a_status_without_its_event` | **FAIL** | projection: блокеров `[]`, диагностик `[]`, authority `lifecycle`; единственный косвенный признак — checkpoint `STALE` |
| W1 `INVARIANT_verified_without_recorded_evidence_never_closes` | **FAIL** | VERIFIED на диске, событий VERIFIED 0 → closeout inspect eligible → **COMPLETED** (`event_recorded=true` — это про `TASK_COMPLETED`) |
| W1 `TRIGGER_activation_dies_after_durable_ACTIVE_and_plan_pointer` | PASS | ACTIVE + `plan.current=m1`, события нет; затем mutation → **EXECUTED** (авторизация законна, но история не доказывает выдачу ACTIVE) |
| W1 `CONTROL_injected_exception_is_reported…` | PASS | процесс жив: 200, `event_recorded=false`; на диске то же расхождение |
| W2 `CONTROL_healthy_mutation…` | PASS | EXECUTED, 1 apply, `OPERATION_INTENT` есть |
| W2 `TRIGGER_process_dies_after_durable_INTENT…` | PASS | exit 78; на диске INTENT rev 1; `OPERATION_INTENT` нет; apply 0 |
| W2 `SAFETY_reopen_never_turns_the_orphan_into_a_mutation…` | PASS | replay → 409 `mutation_refused`; recover → FAIL_CLOSED (`requires_human`); ACTIVE→DONE 200; DONE→VERIFIED → 409 (`RECOVERY_FACTS_UNAVAILABLE`); closeout → REJECTED; apply 0, цель не изменилась |
| W2 `INVARIANT_orphan_intent_has_a_server_recovery_path` | **FAIL** | get → «missing durable intent history»; resolve ABORT → `ResolverError: operation state unavailable`; recover → FAIL_CLOSED: **тупик** |
| W2 `INVARIANT_a_lost_intent_event_does_not_blind_the_rest_of_the_task` | **FAIL** | здоровая `op_a` (EXECUTED) + сирота `op_b` → `list()` падает, `OPERATIONS_UNREADABLE` на всю TASK |
| W2 `INVARIANT_injected_intent_event_failure_leaves_no_unreadable_orphan` | **FAIL** | живой процесс: 409 `state_error`, но INTENT записан → та же нечитаемая сирота |
| W3 `TRIGGER_and_SAFETY_lost_DONE_event_is_tolerated…` | PASS | exit 79 после apply и durable DONE; `list()` OK; replay → REPLAYED / KNOWN_RECEIPT; apply ровно 1 |

**Совместимость** (`probes/test_schema_compat.py`, `9572525d…`, 4/4 PASS):
- новое поле в `microtasks/<id>.json` → текущий `TaskStore` отвергает запись, projection: `MICROTASKS_UNREADABLE`;
- новое поле в записи операции → `OperationRecord.__init__() got an unexpected keyword argument`;
- `OPERATION_INTENT` выводится из записи INTENT точно (10/10 полей);
- новые типы событий (`MICROTASK_TRANSITION_INTENT`, `_ABANDONED`) и лишние поля в `MICROTASK_TRANSITION`, даже с `operation_id` существующей операции, текущий код **игнорирует**: блокеры projection и closeout до и после совпадают.

**Не воспроизводилось:** power loss (W1/W2 после отключения питания), внешние писатели, W5 (резолвер) и W4 (closeout) пробами — только чтение кода. Injected-исключение и реальная гибель процесса разделены явно (оба дают одно и то же состояние на диске; отличается только ответ вызывающему).

## 5. Варианты контракта (фаза C)

| Критерий | **A.** `pending_event_id` в записи | **B.** write-ahead намерение в журнале | **B'.** sidecar WAL-файл | **C.** только сверка (reconciliation) | **D.** single-slot outbox в записи (A+B) |
|---|---|---|---|---|---|
| Суть | запись хранит id ещё не записанного события; reopen ищет его в журнале | до CAS — `…_INTENT` событие (from/to/evidence/intent_id), после — commit; незакрытое разрешается по статусу | отдельный файл намерения рядом с записью, удаляется после события | без новых фактов: противоречия ищутся по существующим данным | запись хранит полный текст события; доставка — после |
| Crash-consistency | обнаружение — да; восстановить evidence нельзя (тела нет) | **да**: evidence durable до статуса; любая фаза детерминированно classified | да, но 3 файла и больше состояний | для операций — да (INTENT выводим); для микрозадач — **нет** (журнал неполон, evidence не восстановить) | да, один атомарный файл |
| Safety vs availability | fail-closed без авто-ремонта | авто roll-forward/abandon по authority, противоречие → оператор | как B | для ops — авто roll-forward | как B |
| Совместимость старых записей / откат | **ломает откат**: новое поле → старый код отвергает запись (проба) | **безопасно**: старый код игнорирует новые события (проба) | безопасно, если файл вне путей, которые сканируют | безопасно | ломает откат, как A; нужен двухфазный выпуск (tolerant reader → writer) |
| Миграция schema | нужна (+ двухфазный выпуск) | нет | нет | нет | нужна |
| Lock / deadlock | под mutation lock, leaf events-lock — без новых | то же + 1 доп. append | доп. файловые записи под тем же lock | без новых | как A |
| Replay / idempotency | по id | по `intent_id`, разрешение идемпотентно | по файлу | по содержимому (ops) | по id |
| Projection / closeout / RC-6 | новый блокер | новый блокер pending/противоречие; closeout разрешает до проверки; шаг RC-6 | как B | блокер + шаг RC-6 | как B |
| Размер будущего diff | средний + модели | средний (без моделей) | средний-большой | малый (ops), не решает W1 | средний + модели |
| Rollback | граница отката после первой записи | полный | полный | полный | граница отката |
| Опровергающие оракулы | смерть до/после записи; потерянный id | смерть после INTENT, после CAS, после commit; power loss «commit есть, статус нет» | гонки файлов; сирота sidecar | сирота INTENT; другие операции читаемы | как A + атомарность |

**Отвергнуто:**
- **«Событие до статуса» без commit-маркера.** Сбой даёт ложную историю о несостоявшемся переходе.
- **Сравнение по digest записи.** Рассматривал как базу «зафиксирован ли CAS», но `set_plan` и `create_microtask` переписывают записи микрозадач (sequence/updated_at) без смены статуса — получились бы ложные противоречия. Классифицировать нужно по статусу при обязательном участии всех писателей статуса.
- **Чистый C для микрозадач.** Невозможен: журнал неполон по замыслу, evidence не восстановить.

## 6. Рекомендуемый контракт (фаза D) — R-OP + R-MT

### 6.1 Общие правила

- **Authority:** записи (`microtasks/*.json`, `operations/*.json`) — как сейчас. Журнал — доказательство: может **отставать** от authority в определённых классифицированных состояниях, но **не может противоречить** и не может молча терять доказательство.
- **Разрешение (resolve)** выполняют только писатели, удерживающие lock соответствующего объекта (mutation lock для микрозадачи; operations TASK-lock + mutation lock для операции), через leaf events-lock. Projection остаётся **pure**: только сообщает.
- **Автоматически разрешено только детерминированное:** дописать событие, тело которого целиком определено authoritative-записью или ранее durable-намерением, либо закрыть незафиксированное намерение. Все такие записи помечены (`late: true` / тип `_ABANDONED`). Остальное — оператор.
- Физическая mutation возможна только из STARTED (WA4-E). R-OP разрешает лишь форму INTENT (никогда не STARTED), поэтому повторный physical apply исключён конструкцией.

### 6.2 R-OP (AUD-03, операции, без изменения схемы)

1. **Классификация в `_validate_history`.** Нет `OPERATION_INTENT` **и** `status == INTENT` **и** `revision == 1` **и** нет ни одного события этой операции → `INTENT_EVENT_PENDING`. Запись читаема с флагом; `get/list` её возвращают. Любая другая форма отсутствия INTENT → противоречие, fail-closed, как сейчас.
2. **Projection.** Блокер `OPERATION_INTENT_PENDING` (closeout) — только для этой операции, без TASK-wide `OPERATIONS_UNREADABLE`.
3. **Roll-forward.** Дописать `OPERATION_INTENT`, вычисленный из записи (те же 10 полей + `late: true`), под теми же lock. Кто: replay того же `operation_id` (`begin`/executor) **до** STARTED; closeout перед повторной проверкой; RC-6 ограниченный шаг `DELIVER_PENDING_HISTORY` (`physical_mutation_performed=false`).
4. **Оператор** может ABORT — запись читаема, резолвер работает.
5. **Честный ответ живого процесса.** Сбой append после INTENT → `operation_history_pending` (409) с текстом «INTENT persisted», а не «state_error».
6. Payload-сирота — отдельное предложение GC (не в этой TASK).

### 6.3 R-MT (AUD-02b-R, микрозадачи, write-ahead в журнале)

Протокол одного шага под mutation lock (внутри уже существующих `_commit` / `_admit_verified` / `_admit_active`; порядок lock не меняется):

0. `resolve_pending(task, m)` — если есть незакрытое намерение по этой микрозадаче, сначала разрешить его.
1. Решение и CAS-база — как сейчас.
2. Append `MICROTASK_TRANSITION_INTENT` {intent_id, from, to, verification_evidence, operation_id} — fsync. Полномочий не даёт.
3. CAS записи (атомарная замена).
4. Append commit `MICROTASK_TRANSITION` {from, to, verification_evidence, intent_id} — формат прежний + поле `intent_id`.

Живой сбой:
- между 2 и 3 (CAS conflict / I/O) → append `MICROTASK_TRANSITION_ABANDONED` {intent_id, reason}, отказ как сейчас;
- между 3 и 4 → `event_recorded=false` (как сейчас), намерение остаётся pending.

Правило разрешения незакрытого намерения I (детерминированное, под mutation lock):
- статус == `I.from` → CAS не случился → `ABANDONED` (авто);
- статус == `I.to` → CAS случился → commit с телом из I + `late: true` (авто; evidence из I);
- статус ∉ {from, to}, либо для I уже есть commit, а статус == `from` (power loss: commit durable, запись потеряна) → `MICROTASK_HISTORY_CONTRADICTS_RECORD` → блокер, оператор.

Projection и closeout:
- блокеры `MICROTASK_TRANSITION_PENDING` (незакрытое намерение) и `…_CONTRADICTS_RECORD`;
- closeout разрешает pending под своими lock и затем повторно доказывает eligibility; противоречие блокирует.

Инвариант доказательства VERIFIED: для микрозадачи, переведённой в VERIFIED по новому протоколу, текст evidence durable **до** статуса (в `…_INTENT`) и после разрешения присутствует в commit. Legacy-VERIFIED без намерений — `LEGACY_UNJOURNALED_VERIFIED` (диагностика; блокировать ли — **решение пользователя**).

**Обязательное участие писателей статуса.** Классификация по статусу корректна, только если **каждый** писатель статуса микрозадачи сначала вызывает `resolve_pending` под своим mutation lock: state machine, prepare/manifest-store, RC-6 `_set_micro_locked`. Иначе — fail-closed противоречие. Фаза 1 — state machine + RC-6 + prepare-обёртка; manifest-store — внутри prepare (уже под state machine).

### 6.4 Durable до и после commit

| Момент | Микрозадача (R-MT) | Операция (R-OP) |
|---|---|---|
| До commit | `…_INTENT` событие (from/to/evidence) | payload + запись INTENT (как сейчас) |
| Commit point | атомарная замена записи (статус) | атомарная замена записи INTENT |
| После commit | commit-событие с `intent_id` | `OPERATION_INTENT` (или позже roll-forward из записи) |
| Гибель процесса в любой фазе | детерминированно: abandon / roll-forward / оператор | детерминированно: roll-forward / оператор |

### 6.5 Что изменит будущая implementation TASK (оценка)

- `state_machine.py` (~+80 строк): `resolve_pending`, протокол 0–4, ответы.
- `operation_store.py` (~+60): классификация pending, roll-forward, честный код ошибки.
- `projection.py` (~+60): поиск pending/противоречий для ops и микрозадач, блокеры.
- `closeout.py` (~+15): resolve под lock до повторной проверки.
- `recovery_coordinator.py` (~+50): шаг `DELIVER_PENDING_HISTORY`; `resolve_pending` перед `_set_micro_locked`.
- `server.py` (~+5): код `operation_history_pending`.
- `models.py`, `task_store.py`, `event_checkpoint_store.py` — **без изменений** (нет новой схемы; events-lock уже есть).
- **Тесты:** новый модуль (~30): этот набор проб, переведённый в регрессию + RAM/source-мутанты; существующие 849 — без изменений ожидаемых статусов.

### 6.6 Совместимость, откат, развёртывание

- Формат записей не меняется. Новые события — новые типы и одно доп. поле; текущий код их игнорирует (проба).
- **Откат на текущий код безопасен.** Незакрытое намерение старым кодом просто не разрешается: возвращается сегодняшнее поведение «событие потеряно», не хуже.
- Legacy-история без намерений: инварианты R-MT к ней не применяются. R-OP превращает существующие сироты INTENT (если они есть в live storage) из тупика в разрешимое состояние — W3 preflight покажет их число.
- Миграции нет; live storage читается как есть.

## 7. Adversarial review рекомендуемого контракта (MANUAL ENGINEERING REVIEW)

| Атака | Исход по R-MT / R-OP |
|---|---|
| Смерть после `…_INTENT`, до CAS | статус == from → abandon; evidence не потерян, но переход не состоялся — честно |
| Смерть после CAS, до commit | статус == to → roll-forward из намерения с evidence (W1 закрыт, включая VERIFIED-evidence) |
| Смерть во время append (оборванный хвост) | весь журнал fail-closed (AUD-01/05), ручной ремонт хвоста — как сейчас; ничего не теряется молча |
| Двойная доставка | resolve идемпотентен: проверка commit/abandon по `intent_id` под mutation lock + events-lock; два resolver'а сериализованы |
| Stale revision / устаревшее решение | CAS не меняется: решение принимается на наблюдённом статусе, запись — под lock; намерение stale-шага закрывается abandon |
| Повреждённое / отсутствующее событие | нечитаемая история блокирует всё (AUD-01/02/05); отсутствующее намерение = legacy-путь |
| Конкурентный писатель-не-участник | статус ∉ {from, to} → противоречие → fail-closed (не ложный успех). Требование участия — часть контракта |
| Поздний closeout | closeout под теми же lock разрешает pending до проверки; вклиниться между CAS и commit не может (событие под lock — ремонт AUD-02b) |
| Fresh reopen | projection показывает pending/противоречие; разрешение — следующий писатель под lock или RC-6 шаг |
| Replay старой операции | pending INTENT → roll-forward, затем обычный путь (STARTED ещё не было — первый apply); STARTED+ не классифицируются как pending → «неизвестный исход» не повторяется |
| Ошибка fsync | append намерения не удался → отказ, ничего не изменено; CAS не удался → abandon; commit не удался → pending + `event_recorded=false` |
| Устаревшая проекция | projection pure; closeout повторно доказывает под lock; checkpoint STALE — как сейчас |
| Power loss «commit durable, запись потеряна» | противоречие → оператор (fail-closed). Снижается write-through rename (PWR-01) |
| Ложный блокер из-за `set_plan` | исключён: классификация по статусу, а не по digest записи |
| Атака на R-OP: подмена INTENT-записи вручную | roll-forward выводит событие из записи; содержимое контракта/fingerprint проверяется `validate_record`; чужая форма → противоречие |

**Остаточные риски контракта:**
1. Обязательное участие всех писателей статуса. Новый писатель без `resolve_pending` даёт fail-closed противоречия (безопасно, но доступность).
2. На каждый переход микрозадачи +1 fsync'нутое событие (намерение). Объём и время не измерялись (NOT RUN).
3. Power loss без write-through rename остаётся ручным.
4. Legacy-VERIFIED без evidence уже в live storage неотличим от нового (решение 6.3).

## 8. Тестовая матрица

Guarded runner `wa4a_acceptance.py` через `tools/run_gate_batch.py` (копия обёртки прошлой TASK: LOCALAPPDATA/APPDATA/pycache → TEMP, `-B`). Windows 10 19045, Python 3.12.10. Сырые результаты: `runs/<label>/results.json` (пути заменены), исходные и опубликованные SHA — в `evidence.json`.

| Попытка | Цель | Тестов | PASS / FAIL / ERROR / SKIP | Exit | Изол. | Source map |
|---|---|---:|---|---:|---:|---|
| probes1 | `test_crash_windows` (ранняя версия: 12 проб, без W3, resolve с невалидным fingerprint) | 12 | 7 / 5 / 0 / 0 | 1 | 0 | 104 = gate |
| probes2a / 2b / 2c | `test_crash_windows` (финальная, 13) | 13 ×3 | 8 / 5 / 0 / 0 ×3 | 1 | 0 | 104 = gate |
| compat1 | `test_schema_compat` (3) | 3 | 3 / 0 / 0 / 0 | 0 | 0 | 104 = gate |
| compat2 | `test_schema_compat` (финальная, 4) | 4 | 4 / 0 / 0 / 0 | 0 | 0 | 104 = gate |

- **Exit 1** у probes — ожидаемый: 5 INVARIANT-проб формулируют ещё не реализованный контракт. Это не регрессия.
- Fault trigger доказан маркером фазы (запись перечитана с диска перед `os._exit`) и кодом выхода 70/78/79. Negative controls: CONTROL- и SAFETY-пробы.
- **NOT RUN:** полный `wa4a_acceptance.py all` (production не менялся — не требуется), power loss, внешний писатель, W4/W5 пробами, чистый CI (W1), preflight live storage (W3), Python 3.13.

## 9. OPEN findings и решения пользователя

**Воспроизведено:**
- **AUD-02b-R HIGH** — false-safe: потерянный `MICROTASK_TRANSITION` невидим, VERIFIED без evidence закрывается closeout'ом.
- **AUD-03 MEDIUM** — fail-closed тупик, TASK-wide `OPERATIONS_UNREADABLE`, та же сирота при живой I/O-ошибке (409 `state_error`).

**Новые наблюдения:**
- **HIST-POL** — непоследовательная политика «история может отставать» (ops после INTENT — да, INTENT — нет, микрозадачи — не проверяется).
- **RC6-NOEVT** — RC-6 меняет статусы микрозадач без событий.
- **PAY-ORPH** — payload-сирота без GC.
- **PWR-01** — `os.replace` без write-through и fsync каталога; power loss не проверялся.
- **LOCK-T x AUD-03** — таймаут events-lock (прошлый ремонт) тоже ведёт к сироте INTENT в живом процессе. R-OP это закрывает.

**Без изменений:** AUD-01T-R, AUD-02c, AUD-04.

**NEEDS USER DECISION:**
1. Утвердить R-OP (AUD-03) — да/нет.
2. Утвердить R-MT (write-ahead в журнале) вместо D (outbox в записи с двухфазным выпуском) — рекомендую R-MT.
3. Разрешить автоматическое детерминированное разрешение (roll-forward/abandon) или оставить только операторское.
4. Блокировать ли closeout на legacy-VERIFIED без evidence (`LEGACY_UNJOURNALED_VERIFIED`).
5. Включать ли RC-6 и manifest-store в фазу 1.
6. PWR-01 (write-through rename) — отдельной TASK.

## 10. DOC IMPACT / SHARED DOC DELTA (координатору; сам не правил)

- **23:** раздел «durable commit points и история» — authority записей, допустимое отставание журнала, классификации pending/противоречие, протоколы R-OP/R-MT (после утверждения); факты W1/W2/W3, RC6-NOEVT, PWR-01.
- **24:** план implementation TASK по §6.5 и порядок (R-OP → R-MT фаза 1 → RC-6/manifest), гейты W1/W3 без изменений.
- **25:** результат исследования (DESIGN PROPOSAL, не ремонт).
- **36.2:** crash-window пробы (реальная гибель процесса + fresh reopen, маркер фазы), будущий регрессионный набор.
- **34/05/06:** статус AUD-02b-R/AUD-03 «воспроизведено, предложен контракт».
- **18/36/36.1:** NO CHANGE.

**Публиковать** (весь каталог `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001/`, вне `.gitignore`, без `*.log`/`*.tmp`/`logs/`): `report.md`, `scope.md`, `manifest.json`, `evidence.json`, `source-gate.json`, `probes/*.py`, `runs/**` (очищенные `results.json`/`summary.json` и сводки), `tools/*`. Плюс ротация `Документация/000_Задачи Claude.md`. Не опубликовано: исходные TEMP-каталоги прогонов (их SHA — в `evidence.json`).

**Подтверждение:** `web_alarm/*.py`, корневые тесты, runner, CI, MCP, общая документация, live storage, рабочая область Codex и чужие TASK не изменялись (повторный source gate PASS).

**NEXT:** независимая проверка ChatGPT → решения пользователя §9 → отдельная implementation TASK.
