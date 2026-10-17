### CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 — Durable State/Event Crash Consistency (AUD-02b-R + AUD-03) — результат

**TASK:** CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 (БЛОК 1, USER ASSIGNED). Назначение — стартовое сообщение пользователя 2026-10-17. Исполнитель — агент 008 (Claude); verifier — ChatGPT. AMENDMENT не было.

- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION — DESIGN PROPOSAL. Не REPAIR VERIFIED, LOCAL ONLY. Production-код, тесты, runner, CI и общая документация не менялись; WA4-R остаётся PARTIAL.
- **Source gate:** PASS — 104/104 исходника = итог прошлого ремонта (№354); повтор в конце — PASS.
- **Воспроизведено** (реальная гибель дочернего процесса после durable-записи с маркером фазы + fresh reopen непатченным процессом):
  - **AUD-02b-R (W1) — false-safe:** расхождение невидимо (projection без блокеров); после потерянного события VERIFIED closeout завершает TASK, хотя verification evidence нигде не сохранился; после потерянной активации mutation выполняется.
  - **AUD-03 (W2) — safe, но тупик:** get/resolve/recover недоступны (FAIL_CLOSED), одна сирота делает нечитаемыми все операции TASK; та же сирота возникает и при I/O-ошибке живого процесса (409 `state_error`).
  - **W3 (контроль):** потерянное событие DONE операции допускается по замыслу, replay не повторяет apply.
- **Пробы:**
  - `test_crash_windows` 13 проб × 3 прогона = 8 PASS (CONTROL/TRIGGER/SAFETY) + 5 FAIL (все INVARIANT — воспроизведённые дефекты), детерминированно;
  - `test_schema_compat` 4/4: новое поле в записи текущий код отвергает (откат ломается), новые типы событий игнорирует; `OPERATION_INTENT` выводится из записи 10/10;
  - изоляция 0; source map 104 = gate.
- **Варианты:** A (`pending_event_id`), B (write-ahead намерение в журнале), B' (sidecar WAL), C (только сверка), D (outbox в записи) — сравнены по 10 критериям.
- **Рекомендация (нужно утверждение пользователя):**
  - **R-OP** для операций — без схемы: сирота узкой формы = `INTENT_EVENT_PENDING`, событие детерминированно дописывается из записи под lock, блокер только для этой операции, ABORT возможен;
  - **R-MT** для микрозадач — `MICROTASK_TRANSITION_INTENT` до CAS, commit с `intent_id` после; разрешение по authoritative-статусу (abandon / roll-forward / оператор); evidence durable до статуса; откат безопасен.
  - Adversarial review — 15 атак.
- **OPEN / новые наблюдения:** HIST-POL (непоследовательная политика отставания истории), RC6-NOEVT (RC-6 меняет статусы без событий), PAY-ORPH, PWR-01 (`os.replace` без write-through), LOCK-T x AUD-03; AUD-01T-R, AUD-02c, AUD-04 — без изменений.
- **NEEDS USER DECISION:** R-OP; R-MT vs D; авто-разрешение vs только оператор; блок closeout на legacy-VERIFIED без evidence; RC-6/manifest-store в фазе 1; PWR-01 отдельно.
- **NOT RUN:** power loss, внешний писатель, W4/W5 пробами, полный suite (код не менялся), чистый CI (W1), preflight live storage (W3), Python 3.13.
- **Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001/report.md`; рядом `scope.md`, `manifest.json`, `evidence.json`, `source-gate.json`, `probes/`, `runs/` (очищенные сырые `results.json`), `tools/`.
- **DOC IMPACT** (предложения): 23 (authority/история, протоколы R-OP/R-MT после утверждения), 24 (implementation TASK), 25, 36.2 (crash-window пробы), 34/05/06; 18/36/36.1 — NO CHANGE.
- **NEXT:** независимая проверка ChatGPT → решения пользователя → отдельная implementation TASK.
