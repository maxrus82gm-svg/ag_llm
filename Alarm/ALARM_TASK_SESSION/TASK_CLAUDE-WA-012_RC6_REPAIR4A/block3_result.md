**TASK:** CLAUDE-WA-012 / RC-6 — REPAIR #4A / PREPARING × ACCEPTED RECOVERY (прямой Chat-handoff, подтверждён пользователем; БЛОК 1 не использовался; исполнитель Claude; независимый verifier — ChatGPT по GitHub). ARCH CLASS: Web Alarm Workspace / Recovery Correctness; PRIMARY `23`, SECONDARY `24`. Продолжение CLAUDE-WA-011 / Repair #4.

- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.** Commit / push не выполнялись.
- **Baseline:** commit 164 = `47e5344ade57aaabca8ed5f782d5eb94f57ad464`; полный набор на baseline — 531 OK, skip 1.
- **Finding verifier — ПОДТВЕРЖДЁН и шире** (`probes/repro_preparing_x_recovery.py`, реальный краш процесса):
  - INTENT-операция до ACTIVE → prepare → краш W1 / W2 → принятый ABORT → `recover` ×3 и свежий процесс = вечный FAIL_CLOSED;
  - обратный порядок (сначала reconcile → BLOCKED_PREPARE / BACKUP_VERIFIED, потом ABORT) — тоже ловушка;
  - без краша — ABORT при PLANNED / BACKUP_VERIFIED / READY; принятый ADOPT по операции такой microtask — та же ловушка («cannot recovery-set it to DONE»).
- **Root cause:** правило settlement RC-6 знало только источники «после исполнения»; `_classify` выбирал settlement раньше reconcile прерванной подготовки.
- **Решение — только RC-6** (Resolver, RC-4, Projection, OperationStore, state machine не менялись):
  1. reconcile прерванной подготовки идёт первым для любого recovery-решения по операции PREPARING-microtask;
  2. ABORT-only disposition RECOVERY_REQUIRED допускается и из PLANNED / BACKUP_VERIFIED / READY / BLOCKED_PREPARE — microtask, никогда не бывшая ACTIVE, не могла иметь эффекта операции (гейт F-C). PREPARING — никогда, ROLLBACK в агрегате — прежние источники;
  3. принятые ADOPT / ROLLBACK / RETRY по такой операции — явная ручная граница: активировать microtask (после этого `recover` завершает решение; проверено) или ABORT; для ROLLBACK сессия RC-4 и claims не создаются;
  4. settlement, обнаруживший под блокировкой параллельно начавшуюся подготовку, уступает reconcile (`DEFERRED_BY_PREPARATION`) — найдено adversarial-пробой.

  Отклонено и откачено к 164: запрет в Resolver (69 падений и 2 ошибки на 135 тестах принятых RC-2 / RC-4 / RC-5; решения исполнимы после активации) и подмена NEXT в Projection (нарушала контракт RC-5).
- **Файлы:**
  - изменены `web_alarm/recovery_coordinator.py`, `web_alarm/microtask_gate.py`;
  - новый `test_web_alarm_recovery_coordinator_repair4a.py` (16 тестов);
  - существующие тесты не менялись.
- **Проверки:**
  - Repair #4A — 16/16, на 164 падают 16 из 16;
  - воспроизведение после — 0 ловушек из 16;
  - фокусно 23 модуля — 358/358;
  - полный набор (46 модулей) — **547 OK, skip 1**, дважды;
  - стресс-повторы — 27/27;
  - adversarial Repair #4A — 3/3 (20 раундов тройной гонки «подготовка / ABORT / recover», устаревший RETRY, испорченный restore point);
  - adversarial #4 — 5/5, #3 — 4/4, #2A — 5/5, #2 — 7 OK;
  - исходные пробы RC-6 — exit 0 / 0;
  - compileall и `git diff --check` — OK.
- **Безопасность:** всё во временном storage; живое storage только на чтение — 136 / 41, хеш до = после (`5961c00c…7cd2`).
- **Документация:**
  - DOC / ARCHITECTURE IMPACT — YES после PASS (владелец `23`);
  - устарели CURRENT-утверждения: `01` («RC-4 следующий»), `24` (строка 9 и статусная таблица), глобальный `000` (БЛОК 1 — Repair #1);
  - в `001` / `05` / `06` / `25` нет RC-5 и цепочки RC-6;
  - точный delta — §9 отчёта; синхронизирует verifier после PASS.
- **Остаточное:** отклонённое решение по операции без settlement остаётся вниманием Projection до ABORT (семантика RC-5, PROPOSAL); legacy `restore_microtask` (WA4-R); риски Repair #4 без изменений.
- **Рекомендация:** RC-6 готов к независимой проверке; блокеров перед WA4-E внутри scope RC-6 исполнитель не видит. Решение — за проверкой ChatGPT.
- **Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-012_RC6_REPAIR4A/rc6_repair4a_report.md`.
