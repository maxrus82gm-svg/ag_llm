### CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 — Durable State/Event Recovery Implementation (AUD-02b-R + AUD-03) — результат

**TASK:** CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 (БЛОК 1, USER ASSIGNED). Назначение — стартовое сообщение пользователя 2026-10-18. Исполнитель — агент 008 (Claude); verifier — ChatGPT. AMENDMENT не было.

- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE/VERIFIED, LOCAL ONLY. WA4-R остаётся PARTIAL; WARN/STRICT/Final Audit не включались.
- **Реализовано** (правило пользователя: нет доказательства — нет VERIFIED; безопасная перепроверка допустима; неизвестный исход — fail-closed и оператор; повторная физическая мутация запрещена):
  - **R-MT (AUD-02b-R):** `MICROTASK_TRANSITION_INTENT` (from/to/evidence/`basis_updated_at`) durable до CAS → commit `MICROTASK_TRANSITION` с `intent_id`; незакрытое намерение: статус == to → commit из намерения; статус == from и запись не менялась → `ABANDONED`; иначе — противоречие, оператор. Разрешают вход шага, `recover` (шаг `RECONCILE_HISTORY`), RC-6 перед своей записью.
  - **AUD-02b:** legacy VERIFIED без evidence → closeout-блокер `MICROTASK_VERIFICATION_UNPROVEN`; безопасная перепроверка `POST /microtasks/{id}/reaffirm` — без мутации и смены статуса, событие `MICROTASK_VERIFICATION_REAFFIRMED` (`original_evidence_recorded: false`); при невозможности — отказ.
  - **R-OP (AUD-03):** потерянный `OPERATION_INTENT` узкой формы → `INTENT_EVENT_PENDING` (TASK читаем), событие восстанавливается из записи под TASK-lock; восстановивший вызов ничего не исполняет (409 `operation_intent_reconciled`); live-сбой после записи INTENT → 409 `operation_history_pending`.
  - Схема записей не менялась; closeout — pure gate.
- **Файлы:** production 6 из 8 разрешённых — `state_machine.py`, `operation_store.py`, `projection.py`, `recovery_coordinator.py`, `event_checkpoint_store.py`, `server.py` (`closeout.py`, `manifest_store.py` — без изменений); тесты — новый `test_web_alarm_crash_consistency.py` (25), адресно `test_web_alarm_aud01t02b_repair.py` и `test_web_alarm_recovery_coordinator_adversarial.py` (оракул и эквивалентность — в отчёте, байты до правки — `baseline/tests/`).
- **Проверки:**
  - Gate A: source gate PASS 104/104; FAIL-first на исходных байтах;
  - Gate B: 5 INVARIANT-проб исследования FAIL → PASS (oracle не менялся), 8 CONTROL/TRIGGER/SAFETY PASS; red-final 32 = 9 PASS (контроли) / 21 FAIL / 2 ERROR;
  - Gate C: 12 сценариев карточки — CC + 7 ADV-проб, реальная гибель процесса + fresh reopen, apply = 0;
  - мутанты 7/7 убиты (2 выживших в раунде 1 → тесты усилены);
  - Gate D: focused 136/136 ×3; **full2 874 = 873 PASS / 0 FAIL / 0 ERROR / 1 SKIP** (давний symlink SKIP), против прошлых 849: удалено 0, смен статуса 0; isolation 0 везде;
  - Gate E: diff + SHA before/after, rollback, byte scan 22 файла чисто, итоговая карта — меняются только 8 намеренных файлов + 1 новый.
- **Findings:** F-1 executor «nothing was recorded» для `OperationStoreError` из `begin` (вне scope); F-2 гибель между переносом TASK и `TASK_COMPLETED` (pre-existing); F-3 rejection-событие в историю завершённого TASK (pre-existing); F-4 откат снимает fail-closed R-MT/AUD-02b (данные читаемы). Остаточный риск: evidence `reaffirm` — утверждение вызывающего.
- **NOT RUN:** PWR-01 / потеря питания; внешний писатель; W1 (чистый CI), W3 (live preflight); WARN/STRICT.
- **Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001/report.md`; рядом `scope.md`, `manifest.json`, `evidence.json`, `source-gate.json`, `source-final.json`, `diff/`, `baseline/`, `probes/`, `runs/` (очищенные сырые `results.json`), `tools/`.
- **DOC IMPACT** (предложения): 23 (протоколы R-MT/R-OP, события, коды 409, ограничение отката), 24, 25, 36.2 (crash-window модуль, мутанты), 34/05/06 (статус, новые API); 18/36/36.1 — NO CHANGE.
- **NEXT:** пользователь публикует; независимая проверка ChatGPT; W1 и отдельно разрешённый W3; rollout не разрешён.
