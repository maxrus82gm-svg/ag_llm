# CLAUDE-WA-009 / RC-6 — REPAIR #2

**Исполнитель:** Claude Opus 5.5. **Независимый verifier:** ChatGPT / GPT-5.6 Sol (после commit/push пользователя).
**Дата:** 2026-10-06.
**Статус:** **RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE / VERIFIED. Commit / push не выполнялись. **WA4-E NOT STARTED.**

Исправлены R1, R2, R3, F-D, F-E. По F-A, F-B, F-C — анализ и предложения без правок кода (§7). Новых глобальных статусов microtask, переходов state machine и изменений модели действий Resolver нет.

---

## 1. Baseline

| Факт | Значение |
| --- | --- |
| GitHub `main` = локальный HEAD | `e551b919628bb0e1232d631f8d2637d9f6fa895c` (commit 161) |
| Runtime baseline | commit 160 `07c4667…`: `git diff --quiet 07c4667 e551b91 -- web_alarm test_web_alarm_*.py` → 0 (161 = только документация verifier) |
| Дрейф рабочего дерева на старте | нет; изменена только карточка (постановка в БЛОКЕ 1) |
| Baseline регрессия | 439 OK, skip 1 — прогон из `TASK_CLAUDE-RC6-REVERIFY/full_regression.txt` на тех же байтах runtime. Собственный стартовый прогон пересёкся с первыми правками, подробности в `baseline_regression.md`. |
| Safety copies, SHA-256 | `baseline.md`, `safety_copies/` |
| Живое storage до | 136 файлов / 41 каталог, `07298919…5920` / `2269f667…3a61` |

---

## 2. R1 — VERIFIED-этап физически не откатывается

**Причина.** Для `ROLLBACK_ACCEPTED`, `ROLLBACK_PREPARED`, `ROLLBACK_PRESERVED`, `ROLLBACK_AUTHORIZED` и `ROLLBACK_APPLYING` координатор шёл прямо в RC-4 `prepare`/`apply`. Статус microtask операции проверялся только в `SETTLE_ROLLBACK`, то есть уже после физического восстановления.

**Исправление: две независимые защиты.**
1. **Projection** (`_protect_stage`). Если следующий шаг продвигает разрушительный откат (состояния `ROLLBACK_DESTRUCTIVE_STATES`), а операция относится не к текущему этапу (`rollback_stage_protected`: microtask VERIFIED или не первая не-VERIFIED в плане), состояние становится `ROLLBACK_STAGE_PROTECTED` с честным NEXT. Исключение — APPLYING с уже записанным DRIFTED/FAILED (`needs_rc4_finalize`): RC-4 в этом случае только финализирует и ничего не восстанавливает.
2. **Координатор.** `_rollback_stage_preflight` перед `PREPARE_ROLLBACK` и `APPLY_ROLLBACK` заново проверяет то же правило по persistent-фактам под TASK-lock + `mutation_lock`. Пропускаются только шаги, в которых RC-4 ничего не восстанавливает: release-only сессии VERIFIED, finalize, apply под принятым ABORT. Классификатор переводит `ROLLBACK_STAGE_PROTECTED` в `RECOVERY_BLOCKED`.

**Результат:** ни записи в Workspace, ни сессии RC-4, ни claims, ни settlement.

**Почему правило — «не текущий этап», а не «статус из набора».** Первая версия требовала ещё и статус из списка `allowed_from` ROLLBACK settlement. Она сломала 3 теста RC-5, где операция лежит в текущей microtask со статусом BACKUP_VERIFIED. Постановка прямо запрещает механически расширять запрет на другие статусы (R1-C), поэтому правило сужено. Текущий этап в любом статусе ведёт себя как раньше. Защищены VERIFIED и ещё не начатые этапы.

**R1-C.** Откат текущей DONE-microtask работает как прежде: PREPARE → APPLY → SETTLE → `RECOVERY_REQUIRED` (тест `r1c`).

**Остаточное окно (связано с F-A) — закрыто в Repair #2A (§12).** Между preflight и захватом TASK-lock внутри RC-4 `apply` параллельный `ServerStateMachine.transition` может перевести microtask в VERIFIED. State machine не берёт TASK-lock операций и пишет статус без сравнения, поэтому никакой блокировкой внутри RC-6 это окно не закрыть. Закрывается вместе с F-A (§7).

---

## 3. R2 — одно решение по microtask вместо пинг-понга settlement

**Причина.** Признак «административная часть settlement завершена» считался для каждой операции отдельно: ADOPT требует DONE/VERIFIED, ABORT/ROLLBACK — RECOVERY_REQUIRED. Статус же у microtask общий, поэтому `FINISH_SETTLEMENT` разных операций переключали его туда-обратно до исчерпания бюджета шагов.

**Исправление (`projection.settlement_lifecycle_target`, `current_settlements_by_microtask`).**
- Settlement всех операций microtask сводятся в **одно решение**: есть хотя бы один ABORT или ROLLBACK → `RECOVERY_REQUIRED` (ручная граница); только ADOPT → `DONE` (или VERIFIED после штатной проверки). Порядок операций не важен: побеждает консервативное решение, а не «последний». ADOPT никогда не поднимает microtask с ручной границы, на которую её поставил ABORT/ROLLBACK соседа. Это прямо допускает §19 постановки («deterministic safe aggregation»).
- Учитываются только **текущие** settlement: если у операции появилось более новое авторитетное действие Resolver, её старый settlement не голосует. Иначе сломался бы P9: ROLLBACK закрыт, затем свежий RETRY той же операции → re-arm → READY.
- Projection, `_classify`, `_settle_resolution`, `_finish_settlement` и `_settle_verified_rollback` используют это одно правило. Координатор вычисляет его заново под блокировками из persistent-записей.
- Противоречие — решение требует `RECOVERY_REQUIRED`, а microtask уже VERIFIED (след F-A) → состояние `SETTLEMENT_CONTRADICTION` → `RECOVERY_BLOCKED` без записи.
- RETRY операции в microtask с ABORT/ROLLBACK-settlement соседа не поднимает её в ACTIVE: блок в `_classify`, в `_rearm_retry` и в RETRY-proof. Без этого пинг-понг переехал бы в пару REARM ↔ FINISH; сценарий достижим через публичный API (`explore`: RETRY_SAFE принят).

**Новая persistent-сущность не вводилась:** всё выводится из записей операций и Resolver, миграция не нужна.

**Ограничение для будущего.** Будущий механизм replan/lifecycle (V15, F-B) должен будет явно снимать доминирование ABORT/ROLLBACK. Сейчас выхода из RECOVERY_REQUIRED нет вообще, так что это правило его не отнимает.

---

## 4. R3 — READY привязан к доказанному базису

**Причина.** После защищённого proof координатор строил свежую projection и сравнивал только **тип** proof, но не то, что именно доказано.

**Исправление.**
- `_prove_normal_ready` и `_prove_retry_ready` возвращают идентичность доказанного состояния: `task_id`, `microtask_id`, статус и `updated_at` microtask, `manifest_id`, `restore_point_fingerprint`, `target_set_fingerprint`, для RETRY — `operation_id`, `operation_revision`, `resolution_id`.
- READY возвращается, только если свежая projection даёт тот же тип proof, **тот же `source_fingerprint`**, что у projection, по которой proof выбирали, и совпадающую идентичность (`_proof_matches`). Иначе — повторная классификация и **новый** proof для нового базиса.
- Результат `recover` получил поле `ready_proof` (идентичность + `source_fingerprint`; не READY → `None`). WA4-E по-прежнему обязан сам заново захватить и проверить authority.
- Если базис меняется после каждого proof, цикл ограничен и заканчивается FAIL_CLOSED («loop bound reached without … a stable READY basis»).

`source_fingerprint` покрывает весь жизненный цикл TASK: microtasks с `updated_at`, restore point, операции, резолюции со свежестью, сессии отката, собственные claims. Чужие claims в него не входят, их проверяет сам защищённый proof.

---

## 5. F-D — один порядок блокировок целей

- `target_claim_store.target_lock_order(keys)` (по `target_hash`) и `ordered_target_hashes(digests)` — одно определение порядка.
- RC-6 (`_lock_manifest_targets`, `_lock_resolution_targets`) переведён с порядка по physical key на этот порядок.
- RC-4 `_lock_targets` использует тот же хелпер. Порядок прежний (по хешу); дубликаты теперь отбрасываются, чтобы одна блокировка не захватывалась дважды.
- RC-3 берёт по одной цели; Resolver целей не блокирует.
- Регрессия: реальные процессы (RC-6 proof против RC-4 apply другой TASK на двух общих целях с противоположным порядком по ключу и по хешу, барьер «сосед начал захват»). Оба завершаются за < 6 с без таймаута. На старом runtime тот же тест падает — взаимная блокировка до таймаута.
- Старый probe n15 после исправления показывает DEFECT: его барьер ждёт, пока *сосед захватит* свою первую блокировку, а при общем порядке это одна и та же блокировка, так что probe ждёт сам себя. Probe оставлен как историческое evidence без изменений; ожидаемый новый результат закреплён постоянным тестом (§25 постановки).

---

## 6. F-E — отказанный шаг не повторяется в одном вызове

Если RC-4 вернул `BLOCKED` или `REJECTED`, шаг (действие + операция + сессия) запоминается. Если в том же вызове `recover` классификация снова выбирает тот же шаг, координатор останавливается: `RECOVERY_BLOCKED`, `error = RECOVERY_STEP_REFUSED`, в причине — код RC-4.

Сразу после первого BLOCKED цикл намеренно не останавливается. Под ABORT `apply` сначала сверяет цель в полёте и затем возвращает BLOCKED (RC-4 отказывается продолжать), а следующий шаг — штатный `CLOSE`. Это поведение сохранено (тест adversarial `aborted_in_flight…`, probe a11).

Регрессия: ровно один `APPLY_ROLLBACK` за вызов, по одному событию `ROLLBACK_BLOCKED` на вызов (было 8).

---

## 7. F-A / F-B / F-C — анализ и предложения (код не менялся)

### F-A — переход state machine без CAS

- **Факт.** `ServerStateMachine.transition` читает текущий статус без блокировки, проверяет переход по `_ALLOWED` и затем пишет `requested` через `TaskStore.set_microtask_status` под `mutation_lock`, не сравнивая с текущим значением. Параллельный settlement (RC-6, под тем же `mutation_lock`) затирается. Воспроизведено двумя процессами: n02b.
- **Минимальный CAS.**
  - Новый примитив `TaskStore.compare_and_set_microtask_status(task, mid, expected, new)` под `mutation_lock`; `transition` передаёт статус, по которому проверял переход. Несовпадение → `_reject("status changed concurrently")`. Граф переходов не меняется.
  - Проверку «другая microtask уже ACTIVE» и `set_current_microtask` тоже нужно выполнять под тем же lock.
- **Затронутые писатели статуса:**
  - `state_machine.transition`;
  - `manifest_store`: блокировка restore point → BLOCKED_PREPARE, подготовка, `restore_microtask`;
  - RC-6 уже пишет под lock с проверкой.
- **Регрессия:** n02b — переход state machine должен получить отказ, m1 остаётся RECOVERY_REQUIRED.
- **Классификация:** IN-SCOPE SAFE FIX по сути (граф не меняется, вызывающим только добавляется отказ при гонке). Но это глобальный lifecycle-примитив, поэтому по §15 постановки нужно **явное одобрение пользователя**. Рекомендую сделать до WA4-E; это закроет и остаточное окно R1.

### F-B — поздний ABORT / вечный FAIL_CLOSED

- **Достижимо через API:**
  - (а) ABORT по операции с ADOPT settlement (n03);
  - (б) ABORT по операции уже VERIFIED-этапа (P6, a10);
  - (в) ADOPT по такой операции (a10).
- Resolver принимает ABORT без требования к решению reconciliation. RC-6 ничего не пишет (второй settlement запрещён, preflight запрещает трогать VERIFIED), но фокус projection остаётся на этом действии, и `recover` всегда FAIL_CLOSED. TASK заклинивает.
- **Варианты:**
  - A. Resolver (RC-2) отклоняет новые действия по операции с recovery settlement (`RECOVERY_SETTLED`) и по операции VERIFIED-этапа (`HISTORICAL_STAGE`) — минимально;
  - B. projection считает такие действия историей с ручной границей и честным NEXT (TASK всё равно стоит, но понятно почему);
  - C. явный механизм replan/acknowledge (V15).
- **Рекомендация:** A + решение по V15. Это изменение модели принятия действий Resolver → **DECISION REQUIRED**.

### F-C — запрет мутации после ABORT не обеспечен сервером

- **Факт.**
  - `OperationStore.begin` проверяет только существование microtask, но не её статус.
  - RC-3 `acquire` выдаёт claim.
  - `mutation_boundary` даёт `mutation_authority = True` (`CAS_BASIS_HOLDS`) для новой операции в RECOVERY_REQUIRED- или DONE-microtask (n14, n13).
  - Именно этот пробел делал достижимым R2; после Repair #2 R2 безопасен независимо от него.
- **Правильный слой:** единственная точка выдачи authority — `TargetClaimService.mutation_boundary`. Предлагаю проверку жизненного цикла там: microtask операции — текущий этап и ACTIVE, иначе `mutation_authority = False`, код `MICROTASK_NOT_EXECUTABLE`. Плюс WA4-E обязан сверять `ready_proof` с базисом. Ограничение в `begin` (RC-1) — позже: на него опираются фикстуры RC-5.
- **Классификация:** опциональный локальный guard. Он меняет семантику принятого RC-3, поэтому **без решения пользователя не делается**. Рекомендую включить во вход WA4-E.

---

## 8. Изменённые файлы

| Файл | Изменение |
| --- | --- |
| `web_alarm/recovery_coordinator.py` | R1 preflight; R2 общее решение по microtask (settle / finish / rollback settle, RETRY guard); R3 идентичность proof, привязка READY, `ready_proof`; F-D порядок; F-E отказанный шаг; новые блок-состояния в `_classify` |
| `web_alarm/projection.py` | `rollback_stage_protected`, `ROLLBACK_DESTRUCTIVE_STATES`, `_protect_stage` (R1); `settlement_lifecycle_target`, `current_settlements_by_microtask`, `settlement_lifecycle_satisfied`, `SETTLEMENT_CONTRADICTION`, `lifecycle_target`, поле `microtask_disposition`, двухпроходный цикл операций (R2); docstring |
| `web_alarm/target_claim_store.py` | `ordered_target_hashes`, `target_lock_order` (F-D) |
| `web_alarm/rollback_service.py` | `_lock_targets` через общий хелпер (тот же порядок + без дублей) |
| `test_web_alarm_recovery_coordinator_repair2.py` | **новый**, 24 теста |

Ожидания существующих тестов не менялись.

**Новые машиночитаемые поля и состояния:**
- в результате `recover` — `ready_proof`, `error = RECOVERY_STEP_REFUSED`;
- состояния восстановления — `ROLLBACK_STAGE_PROTECTED`, `SETTLEMENT_CONTRADICTION`;
- в projection — `microtask_disposition` (у операций), `lifecycle_target` и `protected_state` (в recovery).

---

## 9. Проверки

| Набор | Результат |
| --- | --- |
| Repair #2 (новый) | **24/24 OK** |
| Чувствительность: Repair #2 на **исходном** runtime | 20 из 24 падают (`sensitivity_old_runtime.txt`). Проходят ожидаемо: юнит хелпера (с заглушкой), R2-C и R2-D (однотипные settlement работали и раньше), R1-C (законный откат текущего DONE-этапа сохранён) |
| Фокусные (16 модулей: RC-6 ×3, Repair #1, Repair #2, Projection ×2, Resolver ×2, RC-3 ×2, RC-4 ×2, State machine, Server, CLI) | **245/245 OK** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py` (42 модуля) | **463 OK, skip 1** (`full_regression.txt`; было 439 + 24 новых) |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK; новые неотслеживаемые файлы проверены отдельно: LF, без хвостовых пробелов |
| Исходные probe `TASK_CLAUDE-RC6-VERIFY/probes/` без изменений | exit 0 / exit 0, поведение как после Repair #1 |
| Probe повторной проверки (`TASK_CLAUDE-RC6-REVERIFY/probes/`) без изменений | n01, n01b, n13, n13b, n18, n19 → **OK**; остальные OK; DEFECT остались только n02/n02b (F-A, вне scope) и n15 (артефакт барьера, §5) |
| Adversarial pass исполнителя (`probes/repair2_adversarial.py`) | 8/8 OK: незавершённая очистка + соседний ABORT; две смены текущей microtask во время proof (3 отдельных proof); livelock ограничен; closeout после смешанной истории; падение между preflight и prepare (без записи; повтор отката проходит один раз); историческая VERIFIED-операция × RETRY/ADOPT/ABORT/ROLLBACK (нет READY, нет записи); ABORT с целью в полёте → reconcile → close; P9 сохранён |
| Живое storage (только чтение) | до и после всех прогонов: 136 / 41, `07298919…5920` / `2269f667…3a61`; read-only `recover` WA-3.6 / 3.7 → `TASK_COMPLETED`, 0 шагов |

Покрытие матрицы §22 постановки:
- R1: `r1a`, `r1b` (свежий процесс), `r1c`, `r1d`, открытая PRESERVED-сессия, preflight координатора;
- R2: `r2a`–`r2f`, RETRY при соседнем ABORT, противоречие с VERIFIED;
- R3: `r3a` / `r3b` (реальные процессы + барьер), `r3c`–`r3f`, идентичность `ready_proof`;
- F-D: многопроцессный тест + порядок совпадает с RC-4;
- F-E: один отказанный шаг за вызов.

---

## 10. Сохранено из Repair #1

- B1 (история settlement), B2 (глобальный foreign claim proof), B3 (microtask операции для RETRY/ABORT/ADOPT, теперь и для ROLLBACK);
- B4 (перезапуск RC-4, finalize DRIFTED, release-only), B5 (restore point в READY);
- F1 (правдивый NEXT RECOVERY_REQUIRED), F2 (PARTIAL/FAILED сохраняют ownership).

Подтверждено тестами Repair #1 (21/21) и исходными probe.

---

## 11. Вне scope / открыто

- F-A, F-B, F-C — решения пользователя (§7).
- F-F: `PROJECTION_VERSION` не поднят, хотя состав projection опять изменился (`microtask_disposition`, `lifecycle_target`). Checkpoint, собранный старым кодом, валидируется как INCONSISTENT — это безопасно, лечится `checkpoint rebuild`.
- После принятия этапов обязателен перезапуск процессов WEB-02.

**NEXT:** пользователь делает commit/push → ChatGPT независимо проверяет самый свежий commit → только после PASS RC-6 = DONE / VERIFIED → NEXT = WA4-E. **WA4-E NOT STARTED.**

---

## 12. Repair #2A (2026-10-07) — F-A CAS и закрытие окна R1

Подробности — в `repair2a/rc6_repair2a_report.md`.
- Переходы state machine стали compare-and-set (`TaskStore.compare_and_set_microtask_status`). Новый статус больше не затирается переходом, решённым по старому наблюдению; у `transition` и серверного endpoint появился необязательный `expected_status`.
- Перед разрушительным apply координатор под теми же блокировками, что и проверка этапа, переводит microtask в RECOVERY_REQUIRED. Во время отката RC-6 этап не может стать VERIFIED.
- Новые тесты — 12 (`test_web_alarm_state_machine_cas.py`; на коде до #2A 11 из 12 падают).
- Фокусно 278/278, полный набор — 475 OK (skip 1).
- F-B, F-C не менялись.
