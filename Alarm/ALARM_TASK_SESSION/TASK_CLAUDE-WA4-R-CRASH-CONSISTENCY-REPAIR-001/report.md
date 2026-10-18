# CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 — реализация R-MT (AUD-02b-R) и R-OP (AUD-03)

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE/VERIFIED. Публикация: LOCAL ONLY / NOT SYNCED — commit/push делает пользователь.

- Исполнитель: агент 008 (Claude), 2026-10-18. Verifier: ChatGPT.
- ARCH CLASS: Web Alarm Workspace / RT-001 / WA4-R Reliability. PRIMARY 23; PLAN 24; HISTORY 25; TEST PROFILE 36.2; правила 36/36.1.
- Назначение — БЛОК 1 (USER ASSIGNED) + стартовое сообщение пользователя. AMENDMENT во время работы не было.
- Правило пользователя (основа реализации): **результат без доказательства не VERIFIED; безопасная перепроверка допустима; неизвестный исход — fail-closed и оператор; повторная физическая мутация запрещена.**
- WA4-R остаётся PARTIAL; WARN / GATEWAY REQUIRED / STRICT / Final Audit не включались. Git/GitHub, live storage, MCP, runner, CI, общая документация не затрагивались.

## 1. Итог

| Часть | Что было (исследование, W1/W2) | Что стало | Доказательство |
|---|---|---|---|
| **R-MT (AUD-02b-R)** | Гибель между CAS статуса и событием → расхождение невидимо; VERIFIED закрывал TASK без сохранённого evidence | `MICROTASK_TRANSITION_INTENT` (from, to, evidence, `basis_updated_at`) **durable до CAS**; commit `MICROTASK_TRANSITION` с `intent_id`; незакрытое намерение разрешается только из durable фактов: commit из намерения / `ABANDONED` / противоречие → оператор | 5 исторических INVARIANT-проб исследования: FAIL → **PASS** без правки их oracle; новый модуль 25/25 |
| **AUD-02b** (legacy VERIFIED без evidence) | closeout допускал | closeout-блокер `MICROTASK_VERIFICATION_UNPROVEN`; безопасная перепроверка `POST /microtasks/{id}/reaffirm` (без мутации и смены статуса, отдельное событие `MICROTASK_VERIFICATION_REAFFIRMED`, `original_evidence_recorded: false`); при невозможности — отказ, оператор | тесты VerificationEvidence 5/5 |
| **R-OP (AUD-03)** | Потерянный `OPERATION_INTENT` → тупик, все операции TASK нечитаемы | Узкая форма (INTENT, rev 1, v2-контракт, без settlement/receipt, без progress-событий) = `INTENT_EVENT_PENDING`: TASK читаем, блокер только этой операции; событие восстанавливается из записи (`reconstructed_from_record: true`) под TASK-lock; **вызов, который восстановил, ничего не исполняет** (409 `operation_intent_reconciled`); любая другая форма — fail-closed | тесты OperationIntent 9/9; 0 физических apply во всех пробах восстановления |

Схема `MicrotaskRecord`/`OperationRecord` **не менялась**; новые сведения — только в payload новых событий. Изменено 6 production-файлов из 8 разрешённых (`closeout.py`, `manifest_store.py` — без изменений, SHA = baseline).

Прогоны (все — guarded runner `wa4a_acceptance.py`, изолированный TEMP, 0 isolation violations):
- **полный набор на финальных байтах (`full2`): 874 = 873 PASS / 0 FAIL / 0 ERROR / 1 SKIP** (SKIP — давний `test_symlink_target_fails_closed`); против прошлого full-final 849: удалённых 0, добавлено 25 (все PASS), смен статуса 0; source map прогона = `source-final.json` (105/105, расхождений 0);
- focused ×3 (7 модулей, 136 тестов): 136/136 ×3; ADV-пробы 7/7 ×2; пробы исследования на итоговом production 13/13;
- red-final (финальные тесты на точных исходных байтах production): 32 = 9 PASS (контроли) / 21 FAIL / 2 ERROR;
- мутанты: 7/7 убиты (после усиления тестов, §6).

## 2. Gate A — baseline / source

- `tools/source_gate.py` → `source-gate.json`: **PASS**, 104/104 файла = карта исследования (`source-gate.json` исследования `72547a89…`); drift/missing/unexpected — пусто. Ориентир координатора `main@e9f69a7…`; Git не использовался.
- Точные байты 8 файлов write-scope до правок — `baseline/web_alarm/` (SHA в `source-gate.json.scope_files`). Байты двух существующих тестов до адресной правки — `baseline/tests/` (SHA совпадают с `source-gate.json.source_sha256_all`).
- FAIL-first до первой правки: новый модуль на исходных байтах — 15 FAIL / 5 PASS (5 PASS — контроли: здоровые пути и «нет повторного apply», которые и до ремонта были безопасны); 13 проб исследования — 8 PASS / 5 INVARIANT FAIL (как в исследовании).
- Карта писателей статуса и событий составлена до кода (`scope.md`): единственный писатель VERIFIED — `_admit_verified`; RC-6 пишет статусы без событий; manifest-store пишет PREPARING/BACKUP_VERIFIED/BLOCKED_PREPARE/RECOVERY_REQUIRED, никогда VERIFIED.

## 3. Что изменено (каждое изменение — к инварианту)

| Файл | Изменение | Инвариант |
|---|---|---|
| `event_checkpoint_store.py` (+152) | `MicrotaskHistoryConflict`; константы событий; чистая функция `microtask_journal(events, statuses)` → pending / contradictions / unproven_verified; `microtask_statuses`; `resolve_microtask_intents_locked` (пишет только детерминированные commit/abandon, иначе `MicrotaskHistoryConflict`) | R-MT: разрешение только из durable фактов |
| `state_machine.py` (+193/−23) | `_journaled_cas_locked`: resolve → проверка статуса → INTENT (сбой → `TransitionJournalUnavailable`, статус не тронут) → CAS (конфликт → ABANDONED + stale) → commit с `intent_id`; `_admit_verified` и `_commit` идут через него под mutation lock; `transition()`/`prepare_microtask()` сначала разрешают намерения (`_resolve_entry`); `reaffirm_verification` | R-MT, AUD-02b |
| `operation_store.py` (+159/−23) | `_validate_history` → признак pending для узкой формы; `_intent_event_reconstructible`, `_intent_payload` (общий с `begin`), `intent_event_pending`, `_reconcile_intent_locked`; `begin`/`_transition_locked`/`_settle_recovery_locked` согласуют под TASK-lock; `OperationIntentReconciled`, `OperationHistoryPending` (не подклассы `OperationStoreError`, чтобы executor не сообщил «nothing was recorded») | R-OP |
| `projection.py` (+60/−3) | остаётся pure: блокер `MICROTASK_HISTORY_CONTRADICTION`; диагностики `MICROTASK_HISTORY_PENDING`, `MICROTASK_VERIFICATION_UNPROVEN`, `OPERATION_INTENT_PENDING` и одноимённые closeout-блокеры; `basis["history_integrity"]` только при наличии проблем (fingerprints здоровых TASK не меняются) | наблюдаемость, closeout gate |
| `recovery_coordinator.py` (+59) | RC-6 `_set_micro_locked` сначала закрывает намерения этой микрозадачи; шаг `RECONCILE_HISTORY` (index 0) в `recover()` — только commit/abandon/восстановление OPERATION_INTENT, `physical_mutation_performed: false`, неразрешимое → `left_for_operator` | R-MT/R-OP: каждый писатель статуса закрывает намерения |
| `server.py` (+30) | `POST /microtasks/{id}/reaffirm` {task_id, verification_evidence, operation_id?}; 409 `operation_intent_reconciled`, 409 `operation_history_pending` (`intent_persisted: true`, `physical_mutation_performed: false`) | API контракта |

Отклонение от плана (`scope.md`, раздел «Итог»): **closeout не согласует историю** — остался pure gate; согласование делают `recover` и вход следующего шага. Lock order не менялся: operations TASK-lock → mutation lock → events-lock.

## 4. Gate B — red → green

| Набор | До ремонта (исходные байты) | После |
|---|---|---|
| 5 INVARIANT-проб исследования (`test_crash_windows`, oracle не менялся) | FAIL ×5 | **PASS ×5** |
| 8 CONTROL/TRIGGER/SAFETY проб исследования | PASS | PASS |
| Новый модуль `test_web_alarm_crash_consistency.py` (25) + ADV (7) | 9 PASS / 21 FAIL / 2 ERROR (red-final-baseline-3) | 25/25 + 7/7 PASS |
| Предыдущие ремонтные модули (aud01t02b, aud010205, state_machine, state_machine_cas, repair3) | — | 100/100 PASS |

Red-final: финальные байты тестов на **точных исходных байтах production** (TEMP-зеркало, source map прогона отличается от итоговой ровно 6 production-файлами). 9 PASS на исходном коде — контроли, которые и до ремонта были безопасны: здоровый путь (`test_healthy_verified_closes_without_reaffirmation`), отсутствие повторного apply (`…lost_started…`, `…lost_executed…`), отказ при противоречащих progress-событиях (3 теста — исходный код ничего не реконструирует), ошибка fsync commit сообщается, completion-проба, повреждённая история (ADV). Остальные 23 — новые инварианты, на исходном коде FAIL/ERROR (ERROR — отсутствующий API, например `resolve_microtask_intents_locked`).

Ход работы честно: первые зелёные прогоны (green1/green2) имели 1 FAIL — две ошибки oracle нового теста (исправлены, причина в тесте) и один SAFETY-провал пробы исследования: replay сироты исполнял операцию в том же вызове — исправлено в production (`OperationIntentReconciled`), oracle пробы не менялся. Все попытки — в `runs/` и `evidence.json`.

Адресно адаптированы 2 существующих теста (байты до правки — `baseline/tests/`):

1. `test_web_alarm_aud01t02b_repair.py::…test_history_failure_after_commit_is_reported_as_committed`. **Причина:** по R-MT до CAS в историю пишется намерение, поэтому «история не изменилась» больше неверно. **Oracle сохранён строго:** прежний префикс истории байт-в-байт неизменен **и** добавлено ровно одно `MICROTASK_TRANSITION_INTENT`; остальные утверждения (статус записан, `event_recorded: false`) без изменений.
2. `test_web_alarm_recovery_coordinator_adversarial.py::…test_closeout_eligible_task_is_not_silently_completed`. **Причина:** фикстура пишет VERIFIED примитивом TaskStore без evidence — по правилу пользователя такой TASK не eligible (recover → `NO_ACTION_REQUIRED` с указанием блокера и пути `reaffirm`; так recover обрабатывает любой closeout-блокер). **Oracle сохранён:** после безопасной перепроверки (`reaffirm`, без мутации) — те же четыре исходных утверждения (`TASK_READY_TO_CLOSE`, TASK `PLANNED`, `performed_steps == []`, eligible). **Добавлено** (усиление): до перепроверки — не `TASK_READY_TO_CLOSE` и не eligible.

## 5. Gate C — adversarial (12 сценариев карточки)

Все пробы: реальная гибель дочернего процесса (`os._exit`) в точной фазе (маркер `phase.jsonl`) + повторное открытие **новым** процессом из реальных файлов; raw-факты (статусы, байты/хэши истории, число реальных apply через трассировку `applies.jsonl`, ответы) — в `facts` каждого теста в `runs/*/results.json`.

| № | Сценарий | Тесты (модуль `test_web_alarm_crash_consistency` = CC; `probes/test_adversarial_repair` = ADV) | Итог |
|---|---|---|---|
| 1 | Гибель до/после intent, CAS, append, fsync | CC `test_death_before_intent_changes_nothing`, `…after_intent_before_cas_is_abandoned…`, `…after_verified_cas_never_closes_without_evidence`, `test_lost_done_commit_is_restored…`, `test_commit_fsync_failure_is_reported_and_reconciled_once`; R-OP: `crash_intent` (до append `OPERATION_INTENT`), `test_live_intent_event_failure_is_reported_as_persisted_intent` | PASS |
| 2 | Fresh-process reopen | все CC-тесты с `child(...)` | PASS |
| 3 | Потеря VERIFIED event → closeout без evidence невозможен | CC `test_death_after_verified_cas_never_closes_without_evidence`, `test_legacy_verified_without_evidence_blocks_closeout` | PASS |
| 4 | Безопасная перепроверка без мутации | CC `test_reaffirmation_without_mutation_proves_and_allows_closeout` (0 apply, байты цели неизменны) | PASS |
| 5 | Перепроверка невозможна → fail-closed | CC `test_reaffirmation_is_refused_when_a_safe_recheck_is_impossible` (открытая операция STARTED → 409; пустое evidence → 400; closeout отказан; событий нет) | PASS |
| 6 | Нет OPERATION_INTENT rev1 → безопасный recover | CC `test_lost_intent_event_keeps_the_task_readable_and_is_reported`, `test_recover_reconstructs_the_intent_event_without_any_apply`, `test_reconciling_replay_executes_nothing_and_a_later_request_executes_once` | PASS |
| 7 | Дубликат intent/event | ADV `test_identical_duplicate_commit_is_tolerated…` (ничего не дописано), `test_conflicting_duplicate_commit_is_a_contradiction_and_blocks`, `test_two_open_intents_are_never_resolved_automatically` | PASS |
| 8 | Stale, гонки, посторонний писатель, RC-6, manifest-store | CC `test_foreign_update_after_an_intent_is_a_fail_closed_contradiction`, `test_recovery_status_write_closes_an_open_intent_first` (RC-6), `test_a_refused_step_that_blocks_the_restore_point_closes_the_open_intent_first` (manifest-store BLOCKED_PREPARE); ADV `test_rc6_status_write_closes_an_open_intent_first`; существующие `state_machine_cas` | PASS |
| 9 | Повреждённая история → отказ без порчи | ADV `test_damaged_history_with_an_open_intent_refuses_without_writes` (байты и статус неизменны, recover → requires_human); пробы исследования | PASS |
| 10 | Legacy: старые snapshots/records, legacy VERIFIED | CC VerificationEvidence; ADV `test_pre_repair_projection_and_operations_read_repaired_histories` (исходный код читает новые истории); полный набор на legacy-фикстурах | PASS |
| 11 | STARTED/UNKNOWN — ни одного повторного apply | CC `test_lost_started_event_never_starts_a_physical_apply`, `test_lost_executed_event_never_leads_to_a_second_apply`, три `…progress/replay event…is_not_reconstructed` | PASS, apply = 0 |
| 12 | Гонки projection/closeout, авария при completion | ADV `test_closeout_cannot_slip_between_intent_and_compare_and_set` (closeout ждёт mutation lock; хвост истории INTENT → TRANSITION → TASK_COMPLETED); CC `test_death_during_completion_leaves_a_proven_read_only_history` | PASS |

## 6. Качество тестов — мутанты и red-final

Каждый мутант — одна точная замена (ровно одно вхождение, `tools/build_mirror.py`) в TEMP-зеркале исправленного кода; цели — CC + ADV.

| Мутант | Что снято | Раунд 1 (CC 20 + ADV 7) | Раунд 2 (CC 24 + ADV 7) | Убивающие тесты (раунд 2) |
|---|---|---|---|---|
| M1 | намерение не пишется до CAS (событие другого типа) | убит (27 ERROR) | убит (30 ERROR + 1 FAIL) | все: commit ссылается на незаписанное намерение → противоречие (fail-closed) |
| M2 | нет разрешения намерений на входе шага | **выжил** | убит | CC `test_a_refused_step_that_blocks_the_restore_point…` |
| M3 | closeout игнорирует `MICROTASK_VERIFICATION_UNPROVEN` | убит | убит | CC `test_legacy_verified_without_evidence_blocks_closeout` |
| M4 | восстановивший replay исполняет в том же вызове | убит | убит | CC `test_reconciling_replay_executes_nothing…` |
| M5 | progress-события не исключают реконструкцию | **выжил** | убит | CC `…unvalidated_progress_event…`, `…replay_event…` |
| M6 | RC-6 не закрывает намерение до записи статуса | убит (только ADV) | убит | CC `test_recovery_status_write_closes…`, ADV `test_rc6…` |
| M7 | журнал не сообщает legacy VERIFIED без evidence | убит | убит | CC `test_legacy_verified…`, `test_reaffirmation_without_mutation…` |

Isolation violations во всех прогонах — 0.

Первый раунд выявил два выживших мутанта (M2, M5) — пробелы тестов, не кода; добавлены тесты, второй раунд их убивает:
- **M5** (`_PROGRESS_EVENTS` не проверяется): прежний тест использовал `OPERATION_TRANSITION` rev 2, которое отсекает и проверка ревизии. Добавлены пробы с `MUTATION_RETRY_EXECUTING` и `OPERATION_TRANSITION_REPLAY` — их не проверяет ничто, кроме правила progress-событий.
- **M2** (нет разрешения на входе шага): большинство шагов разрешает намерения и внутри `_journaled_cas_locked`. Реальное окно — шаг, отказанный проверкой restore point: manifest-store пишет BLOCKED_PREPARE **до** CAS; без входного разрешения открытое намерение превращается в вечное противоречие. Добавлен тест на этот путь.
- **M6** первоначально убивался только пробой в папке TASK; перенесён в накопительный модуль.

## 7. Gate D — regression

Команда каждого прогона: `tools/run_gate_batch.py <python> <batch> tools/spec-<batch>.json` → `tools/run_gate.py` → `wa4a_acceptance.py <targets>` (`-X utf8 -B`, TEMP-изоляция, guarded children); цели — в `tools/spec-*.json`.

| Прогон | Цели | Итог | Примечание |
|---|---|---|---|
| `full1` | `all` | 869 = 867 PASS / **1 FAIL** / 1 SKIP | FAIL — `test_closeout_eligible_task_is_not_silently_completed`: конфликт ожидания с новым контрактом (§4, п. 2); `runs/full1-vs-previous.json`: удалённых 0, единственная смена статуса — этот тест |
| `focused-r1..r3` | CC + aud01t02b + recovery_coordinator_adversarial (адаптированный) + aud010205 + state_machine + state_machine_cas + repair3 | 136/136 ×3 | повтор гонок (state_machine_cas, CloseoutRace) — стабильно; CC тогда — 20 тестов |
| `green4`, `green5` | CC после усиления | 24/24; completion-проба 1/1 | первый прогон completion-пробы FAIL: oracle «история не изменилась» был слишком строгим — reopen добавил `MICROTASK_TRANSITION_REJECTED` (pre-existing, F-3); oracle сужен до «R-MT/R-OP ничего не пишут в закрытый TASK», факт сохранён (`added_by_reopen`) |
| **`full2`** | `all` | **874 = 873 PASS / 0 FAIL / 0 ERROR / 1 SKIP** | `runs/full2-vs-previous.json`: удалённых 0, добавлено 25 PASS, смен статуса 0; source map = итоговые байты |

Сырые per-test `results.json` и `summary.json` всех прогонов (пути заменены на `<TEMP>/<REPO>/<USER>`) — `runs/<label>/`; SHA исходных и опубликованных копий, per-method census — `evidence.json`.

## 8. Gate E — пригодность к проверке

- `source-final.json` — карта всех исходников после ремонта; `diff/*.diff` + `diff/diff-summary.json` — точный unified diff baseline → итог и SHA before/after для каждого изменённого файла.
- **Rollback:** вернуть байты из `baseline/web_alarm/*` (6 изменённых файлов) и `baseline/tests/*` (2 теста), удалить `test_web_alarm_crash_consistency.py`. Данные откатывать не нужно: новые события исходный код игнорирует (ADV rollback-проба). **Ограничение отката:** исходный код не видит незакрытых намерений и не блокирует legacy VERIFIED — после отката fail-closed свойства R-MT/AUD-02b пропадают (возвращается поведение до ремонта).
- Byte integrity: `tools/byte_scan.py` — LF, без BOM, без U+2028/U+2029/U+0085 во всех изменённых и новых файлах, `compile()` в памяти OK (`runs/byte-scan.json`: 22 файла, находок 0; не-ASCII байты только в `projection.py` 14 и `server.py` 2 — столько же, сколько в baseline).
- Посторонних изменений нет: вне 6 production-файлов, 2 тестов, нового модуля, папки TASK и ротации карточки ничего не менялось: `source-final.json` против карты Gate A — drift ровно 8 файлов (6 production + 2 теста), unexpected ровно 1 (новый модуль), missing 0; `manifest.json` проверяет это утверждением при сборке.

## 9. Собственный adversarial review (MANUAL ENGINEERING REVIEW)

Попытки опровергнуть решение и вывод:

1. *Гибель между INTENT и CAS, затем посторонний писатель меняет статус.* Все писатели статуса (переход, prepare через вход, RC-6, manifest-store внутри перехода) сначала закрывают намерения; запись `TaskStore.set_plan`/`create_microtask` меняет `updated_at` → классификация `basis_updated_at` даёт противоречие (fail-closed), не неверный commit. Проверено CC `test_foreign_update…`.
2. *Закрытие commit по чужому статусу:* commit только при `status == to`; abandon только при `status == from` **и** неизменном `updated_at`; одинаковые from/to невозможны (переход в тот же статус отклоняется до намерения).
3. *Подделка evidence при восстановлении:* восстановленный commit берёт evidence **только** из durable намерения (`recovered_from_intent: true`); намерение без evidence для VERIFIED невозможно (проверяется до записи).
4. *Повторное исполнение операции через восстановление:* вызов, который восстановил `OPERATION_INTENT`, бросает `OperationIntentReconciled` до исполнения (мутант M4 убит); STARTED/UNKNOWN/EXECUTED не реконструируются (узкая форма, M5 убит); apply = 0 во всех пробах.
5. *Гонка closeout ↔ переход:* closeout берёт те же TASK-lock и mutation lock; пауза между INTENT и CAS не пропускает closeout (ADV CloseoutRace).
6. *Projection «чинит» историю:* нет — projection только сообщает; запись — recover/вход шага под lock.
7. *Fingerprints здоровых TASK:* ключ `history_integrity` появляется только при проблемах — полный набор (сравнение fingerprints в существующих тестах) без изменений.
8. *Reaffirm как обход доказательства:* reaffirm не меняет статус и не исполняет мутацию, проходит те же гейты VERIFIED (`verification_refusal`) под теми же lock, требует непустое evidence и только для «недоказанного» VERIFIED; событие явно помечено как поздняя перепроверка. **Остаточный риск:** evidence — утверждение вызывающего (та же модель доверия, что у перехода в VERIFIED); сервер не перепроверяет байты цели сам.

## 10. Findings, ограничения, остаточные риски

- **F-1 (наблюдение, вне scope, `mutation_executor.py`):** executor отвечает на любое `OperationStoreError` из `begin` фразой «nothing was recorded or written», хотя в некоторых до-ремонтных путях запись уже существует. Новые исключения R-OP намеренно не наследуют `OperationStoreError` и отображаются server в точные 409 — новая формулировка не ложная; прежняя — предлагается отдельной правкой.
- **F-2 (pre-existing, `closeout.py` не менялся):** гибель между переносом TASK в `completed` и `TASK_COMPLETED` оставляет TASK без этого события; повторное открытие его не дописывает. Для нового контракта безопасно (CC completion-проба: история доказана, R-MT/R-OP ничего не пишут в закрытый TASK).
- **F-3 (pre-existing):** отказанный шаг пишет `MICROTASK_TRANSITION_REJECTED` даже в историю завершённого TASK (наблюдено той же пробой).
- **F-4 (rollback):** исходный код не видит незакрытых намерений (ADV rollback-проба: исходная projection без блокеров при открытом намерении) — откат снимает защиту, данные остаются читаемыми.
- **AUD-01T-R, AUD-02c, AUD-04, PWR-01** — не трогались. PWR-01 (`os.replace` без fsync каталога) остаётся: R-MT защищает от гибели процесса, не от потери питания. Прямого блокирующего пересечения не найдено.
- **NOT RUN:** потеря питания / write-through каталога (PWR-01); внешний писатель вне API; чистый CI (W1) и preflight live storage (W3) — отдельные гейты; Python 3.13 (прогоны — `.venv`, версия в `results.json`); WARN/STRICT/Final Audit (запрещены).

## 11. DOC IMPACT / SHARED DOC DELTA (координатору; сам не правил)

- **23:** протоколы R-MT (INTENT → CAS → commit, правило разрешения, противоречие → оператор) и R-OP (`INTENT_EVENT_PENDING`, восстановление без исполнения); новые события, блокеры и коды 409; closeout — pure gate; ограничение отката.
- **24:** AUD-02b-R / AUD-03 — реализованы, ожидают независимой проверки; следующие гейты W1/W3; F-1 и F-2 — кандидаты в отдельные TASK.
- **25:** результат реализации (RESULT READY, не VERIFIED).
- **36.2:** crash-window регрессионный модуль `test_web_alarm_crash_consistency.py` (реальная гибель процесса + fresh reopen), мутанты как критерий качества.
- **34/05/06:** статус AUD-02b-R/AUD-03 «реализовано, на проверке»; новые API `POST /microtasks/{id}/reaffirm`, 409 `operation_intent_reconciled` / `operation_history_pending`.
- **18/36/36.1:** NO CHANGE.

## 12. Комплект для публикации

Репозиторий (6 + 3): `web_alarm/state_machine.py`, `web_alarm/operation_store.py`, `web_alarm/projection.py`, `web_alarm/recovery_coordinator.py`, `web_alarm/event_checkpoint_store.py`, `web_alarm/server.py`; `test_web_alarm_crash_consistency.py` (новый), `test_web_alarm_aud01t02b_repair.py`, `test_web_alarm_recovery_coordinator_adversarial.py`. Папка `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001/` целиком (`report.md`, `scope.md`, `manifest.json`, `evidence.json`, `source-gate.json`, `source-final.json`, `diff/`, `baseline/`, `probes/`, `runs/` с очищенными `results.json`, `tools/`). Плюс ротация `Документация/000_Задачи Claude.md`. Не публикуются: исходные TEMP-каталоги прогонов (их SHA — в `evidence.json`).

**NEXT:** пользователь публикует; ChatGPT независимо проверяет source, tests, evidence; W1 и отдельно разрешённый W3 остаются обязательными; до решения verifier — WA4-R PARTIAL, rollout не разрешён.
