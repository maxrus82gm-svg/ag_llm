# Scope — CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001

Реализация R-MT (AUD-02b-R) и R-OP (AUD-03) по утверждённому пользователем правилу: **нет доказательства — нет VERIFIED; безопасная перепроверка допустима; неизвестный исход — fail-closed и оператор; повторная физическая мутация запрещена.** Файл записан **до первой правки production-кода**; итоговый раздел дописывается после результата.

## Gate A — source / baseline (до правок)

- `tools/source_gate.py` → `source-gate.json`: **PASS**. 104/104 файла = карта `CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001` (`source-gate.json` `72547a89…`). Дрейфа, лишних и отсутствующих нет.
- Точные байты восьми файлов write-scope до правок — в `baseline/web_alarm/`; SHA в `source-gate.json.scope_files`.
- Ориентир координатора `main@e9f69a7…`; Git не использовался. Совпадение с картой исследования и отсутствие изменений `web_alarm/` по 23/24/25/36.2 (ревью №6256ac0) согласуются.

## Карта писателей (до реализации)

| Писатель | Что пишет | VERIFIED? | Путь в новом протоколе |
|---|---|---|---|
| `ServerStateMachine._commit` (READY/DONE/FAILED_VERIFICATION/UNKNOWN/RECOVERY_REQUIRED, ACTIVE через `_admit_active`) | статус (+ указатель плана для ACTIVE) | нет | **R-MT**: намерение → CAS → commit под mutation lock |
| `ServerStateMachine._admit_verified` | статус VERIFIED | **единственный писатель VERIFIED** | **R-MT** + evidence в намерении до CAS |
| `ServerStateMachine.prepare_microtask` → `manifest_store` (PREPARING, BACKUP_VERIFIED, BLOCKED_PREPARE) | статус + restore point | нет | отдельный инвариант: restore point — самоописывающая authority (как W3); на входе разрешаются незакрытые намерения |
| `manifest_store._block_restore_point` (под mutation lock, из проверок перехода) | BLOCKED_PREPARE | нет | вызывается внутри перехода после его входного разрешения намерений; в худшем случае — противоречие → fail-closed |
| `manifest_store.reconcile_interrupted_preparation` (RC-6) | PREPARING → BACKUP_VERIFIED / BLOCKED_PREPARE | нет | RC-6 разрешает намерения шагом `RECONCILE_HISTORY` до своих шагов |
| `manifest_store.restore_microtask` (legacy primitive, без server API) | RECOVERY_REQUIRED, BACKUP_VERIFIED | нет | не меняется; не достижим из API |
| `RecoveryCoordinator._set_micro_locked` (DONE, RECOVERY_REQUIRED, ACTIVE re-arm) | статус, событие не пишется (RC6-NOEVT) | **никогда** (цель VERIFIED поглощается без записи) | под своим mutation lock сначала разрешает намерения этой микрозадачи |
| `TaskStore.create_microtask` / `set_plan` / `set_current_microtask` | записи без смены статуса | нет | статус не меняют; классификация по статусу + `basis_updated_at` даёт fail-closed при постороннем изменении |
| `CloseoutService.complete` | move TASK | — | под своими lock разрешает намерения, затем повторно доказывает eligibility; VERIFIED без доказательства — блокер |
| `OperationStore.begin` | payload → INTENT rev1 → `OPERATION_INTENT` | — | **R-OP**: потерянное событие узкой формы = `INTENT_EVENT_PENDING`, восстановление из записи под TASK-lock |
| `OperationStore._transition_locked` / `_settle_recovery_locked` | запись операции → событие | — | перед записью согласует pending INTENT (под TASK-lock); исполнение (STARTED) только после этого |
| `ResolverService.apply`, target claims | информационные события с `operation_id` | — | не противоречат INTENT rev1 (не входят в «progress events») |

Lock order не меняется: operations TASK-lock → mutation lock → events-lock (leaf).

## Решения в рамках утверждённого контракта

- Схема `MicrotaskRecord`/`OperationRecord` **не меняется**. Новые события: `MICROTASK_TRANSITION_INTENT`, `MICROTASK_TRANSITION_ABANDONED`, `MICROTASK_VERIFICATION_REAFFIRMED`; в `MICROTASK_TRANSITION` добавлено поле `intent_id`; в восстановленном `OPERATION_INTENT` — пометка `reconstructed_from_record`. Текущий код их игнорирует (проба совместимости исследования).
- Автоматически разрешено только детерминированное:
  - статус == `to` → commit из durable-намерения (с исходным evidence, пометка `recovered_from_intent`);
  - статус == `from` и `updated_at` не менялся с намерения → `ABANDONED` с аудит-записью.
  - Всё прочее → `MICROTASK_HISTORY_CONTRADICTION` / оператор.
- Legacy VERIFIED без события с evidence → closeout-блокер `MICROTASK_VERIFICATION_UNPROVEN`; безопасная перепроверка без мутации — `reaffirm` (те же гейты VERIFIED, новое явно помеченное событие, статус не меняется). Completed TASK и старые события не переписываются.
- Projection остаётся pure: только сообщает; новые блокеры и ключ появляются лишь при наличии проблем (fingerprints здоровых TASK не меняются).

## Write-scope

- **Production** (только при необходимости, каждое изменение — к инварианту): `web_alarm/state_machine.py`, `operation_store.py`, `projection.py`, `closeout.py`, `recovery_coordinator.py`, `event_checkpoint_store.py`, `server.py`. `manifest_store.py` — изменение **не планируется** (см. инвариант выше).
- **Тесты:** новый `test_web_alarm_crash_consistency.py`; адресные правки существующих `test_web_alarm_*.py`, только если новый контракт меняет их ожидание (оракул и причина фиксируются).
- **Evidence:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001/**`.
- **Карточка:** только ротация.

## Не входит

AUD-01T-R, AUD-02c, AUD-04, PWR-01; `mutation_executor.py`, `task_store.py`, `models.py`; runner/CI; общая документация; MCP/V2Ray/WEB_10/Codex; live storage; WARN/STRICT.
