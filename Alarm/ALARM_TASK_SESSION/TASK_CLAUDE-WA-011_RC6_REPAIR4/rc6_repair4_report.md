# AGENT REPORT — CLAUDE-WA-011 / RC-6 Repair #4 / Final Recovery Liveness Closeout

- **Исполнитель:** Claude (Opus 5.5). Независимый verifier — ChatGPT по GitHub.
- **Дата:** 2026-10-08.
- **ARCH CLASS:** Web Alarm Workspace / Recovery Closure. **PRIMARY PROFILE:** `23_Архитектура Web Alarm Workspace.md`. **SECONDARY PROFILE:** `24_План реализации Web Alarm Workspace.md`.
- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.** Commit / push не выполнялись (по постановке).
- **Baseline:** GitHub `main`, commit 163 = `ce5e1799ab4a08157c779680711bebaf29d686dd`. Полный набор на baseline — 511 OK, skip 1 (`baseline_full_regression.txt`). SHA-256 всех `web_alarm/*.py`, тестов и карточки — `baseline.md`, копии — `safety_copies/`.
- **Маршрут:** `08_Старт.md` → `18_Регламент сопровождения документации.md` → карточка (полная постановка уже была в БЛОКЕ 1) → профиль `23` (§6–§11: restore point, жизненный цикл, обрыв, запрет слепого отката).

---

## 1. Итог

**Blocker A.** Краш в PREPARING больше не оставляет TASK без выхода.
- Вся подготовка restore point держит отдельную блокировку подготовки microtask; ОС снимает её при смерти процесса.
- Свободная блокировка при статусе PREPARING однозначно означает прерванную подготовку, а не идущую.
- Новый шаг RC-6 `RECONCILE_PREPARATION` решает по persistent evidence:
  - **W2** — restore point опубликован: перепроверка, затем BACKUP_VERIFIED. Снятое исходное pre-состояние сохраняется и не переснимается. Если restore point испорчен — fail-closed BLOCKED_PREPARE.
  - **W1** — ничего не опубликовано: неопубликованный захват (stage) отбрасывается, microtask → BLOCKED_PREPARE, после чего штатно готовится заново.

**Blocker B.** Одна политика «что допускает существующий settlement» (`SETTLEMENT_ADMITS`) для Resolver, Projection, RC-6, гейта и физического исполнителя RC-4.
- После ADOPT допустим только ABORT (поздний ABORT Repair #3).
- После ROLLBACK — ABORT и RETRY (повторный re-arm).
- После ABORT — ничего.
- Всё остальное Resolver отклоняет **до** ACCEPTED (`RECOVERY_ALREADY_SETTLED`).
- Отклонённые и устаревшие решения после settlement, а также недопустимые легаси-записи больше не становятся authority и recovery attention.

Граф переходов state machine, набор статусов и схемы записей не менялись.

---

## 2. Воспроизведение на baseline 163

Проба `probes/repro_blockers.py`, временное storage. Вывод — `probes/repro_blockers_baseline.txt`, после Repair #4 — `probes/repro_blockers_after.txt`.

**Blocker A** (краш реального процесса через `os._exit`):

| Окно | Evidence после краша | 163: `recover` ×2 | 163: повторный prepare | 163: NEXT |
| --- | --- | --- | --- | --- |
| W1 (PREPARING, захват в stage) | PREPARING, restore point не опубликован, 1 stage-каталог | NO_ACTION_REQUIRED ×2 | REJECTED (только из PLANNED/BLOCKED_PREPARE) | «finish restore-point preparation» — исполняемого действия нет |
| W2 (опубликован, BACKUP_VERIFIED не записан) | PREPARING, restore point опубликован | NO_ACTION_REQUIRED ×2 | REJECTED | то же |

**Blocker B** (матрица «settlement → позднее действие»; ключевые строки, вся матрица — в файле):

| Settlement → позднее | 163: Resolver | 163: `recover` ×2 | Дефект |
| --- | --- | --- | --- |
| ADOPT → ADOPT | **ACCEPTED** | **FAIL_CLOSED ×2** (second settlement refused) | неисполнимая authority |
| ROLLBACK → ADOPT | **ACCEPTED** | **FAIL_CLOSED ×2** | неисполнимая authority |
| ROLLBACK → ROLLBACK | **ACCEPTED** | **второй физический откат** (2 сессии RC-4, восстановлено 4 цели), затем **FAIL_CLOSED ×2** | второй side effect + ловушка |
| ADOPT → ROLLBACK / RETRY | REJECTED (decision mismatch) | **MANUAL_DECISION_REQUIRED навсегда** (`ROLLBACK_REJECTED` / `RETRY_REJECTED`) | отклонённое решение стало вечным recovery attention |
| ROLLBACK → ROLLBACK (без нового частичного эффекта) | REJECTED (decision mismatch) | MANUAL навсегда (`ROLLBACK_REJECTED`) | то же |
| ABORT → ADOPT / ROLLBACK / RETRY / ABORT | REJECTED (`RECOVERY_ABORTED` / `ALREADY_ABORTED`) | стабильно | уже закрыто (существующая политика ABORT) |
| ADOPT → ABORT, ROLLBACK → ABORT | ACCEPTED | RECOVERY_REQUIRED | уже корректно (Repair #3) |
| ROLLBACK → RETRY | ACCEPTED | READY_FOR_EXECUTION (re-arm) | корректно (P9) |

---

## 3. Root cause

- **A.** `prepare_microtask` пишет PREPARING до публикации restore point и BACKUP_VERIFIED — после неё. Ни state machine (prepare только из PLANNED/BLOCKED_PREPARE, у PREPARING нет переходов), ни RC-6 (PREPARING попадал в NO_ACTION) не знали, как продолжить. Отличить «идёт» от «умерла» было нечем: блокировки на всю подготовку не было.
  - Связанный дефект того же окна: сбой записи статуса **после** публикации шёл в общий except и вслепую ставил BLOCKED_PREPARE поверх валидного опубликованного restore point. Получалась мёртвая точка: prepare отказывает, потому что каталог уже существует.
- **B.** `recovery_settlement` у операции одно (неизменяемая история). При этом:
  - Resolver принимал любое действие после settlement, если сходилось решение reconciliation;
  - выбор authority (`report_facts` → `_authoritative_next_action`) ничего не знал о settlement: свежий отклонённый или поздний принятый record затмевал сам settlement;
  - RC-4 `_authority` проверял только саму resolution, поэтому мог начать второй физический откат.

---

## 4. Выбранный дизайн

### 4.1 Blocker A — блокировка подготовки + reconcile из evidence

- `ManifestSnapshotStore.prepare_microtask` держит `locks/prepare/<task>/<microtask>.lock` на всю подготовку (`_prepare_locked`). В начале, под блокировкой, отбрасываются оставшиеся stage-каталоги прерванных попыток: они никогда не публиковались. На пути state machine запись BACKUP_VERIFIED теперь CAS от PREPARING.
- После публикации restore point является authority: сбой записи статуса оставляет PREPARING (W2, доводится reconcile), а не слепой BLOCKED_PREPARE. Сбой проверки только что записанного BACKUP_VERIFIED блокирует обе записи обычным `_block_restore_point`.
- `ManifestSnapshotStore.reconcile_interrupted_preparation` работает под той же блокировкой с коротким ожиданием:
  - занята → `PREPARATION_IN_PROGRESS`, ничего не трогается;
  - статус не PREPARING → `NOT_INTERRUPTED` (идемпотентность);
  - restore point опубликован (W2) → чистая перепроверка: успех → CAS PREPARING → BACKUP_VERIFIED (`PREPARATION_COMPLETED`); порча или нечитаемость → fail-closed BLOCKED_PREPARE, restore point остаётся как evidence (`PREPARATION_BLOCKED`);
  - не опубликован (W1) → stage-каталоги отбрасываются, CAS PREPARING → BLOCKED_PREPARE (`PREPARATION_DISCARDED`). Из BLOCKED_PREPARE state machine штатно готовит заново.
- **RC-6:**
  - текущая PREPARING → шаг `RECONCILE_PREPARATION`; итог пишется событием `RESTORE_POINT_PREPARATION_RECONCILED`, так что отбрасывание никогда не бывает незаметным;
  - идущая подготовка → остановка `RECOVERY_IN_PROGRESS` (без человека, без записи);
  - BLOCKED_PREPARE с сохранённым restore point → MANUAL_DECISION_REQUIRED: prepare там невозможен.
- **NEXT** (state machine): PREPARING → «Run recover: …» с описанием W1/W2. BLOCKED_PREPARE различает, есть ли сохранённый restore point (ручной ремонт) или нет (подготовить заново). NEXT всегда указывает на реально доступное действие.
- **Почему так:**
  - переходы PREPARING → BACKUP_VERIFIED и PREPARING → BLOCKED_PREPARE — те же записи, что делает сама подготовка; граф state machine и предусловия prepare не менялись;
  - W2 сохраняет снятый pre-state (не переснимает);
  - W1 переснимает. Это безопасно: microtask не была ACTIVE, и по гейту F-C ни одна операция не могла её изменить через сервер. Изменение вне сервера неотличимо от любой задержки между PLANNED и prepare — см. §10.

### 4.2 Blocker B — направление A: детерминированный отказ до ACCEPTED

- `resolver_service.SETTLEMENT_ADMITS` / `settlement_admits()` — одна таблица:
  - ADOPT → {ABORT};
  - ABORT → {} (существующие `RECOVERY_ABORTED` / `RECOVERY_ALREADY_ABORTED`);
  - ROLLBACK → {ABORT, RETRY}.
- **Приём** (`ResolverService.apply` → `_evaluate`, под TASK-lock, сериализован с settlement RC-6): недопустимое действие → REJECTED `RECOVERY_ALREADY_SETTLED` с объяснением. Проверка идёт до проверки свежести и решения, поэтому исход детерминирован.
- **Authority** (`report_facts`, единственный источник для Projection, RC-6 и гейта): при settlement authority — принятый ABORT, иначе последний принятый из {resolution самого settlement + более поздние допустимые}, свежие первыми. Отклонённые и устаревшие решения после settlement и недопустимые легаси-ACCEPTED — только история. Флаг `authority` в `resolver_actions` это отражает.
- **Физический исполнитель:** `RollbackService._authority` отказывает (`RECOVERY_ALREADY_SETTLED`) в откате по resolution, отличной от resolution settlement, если settlement её не допускает. Второй физический откат невозможен даже через прямой API RC-4 из легаси-записи.
- **OperationStore** по-прежнему отказывает во втором settlement; теперь до этого места ничего не доходит.
- **Сохранено:**
  - поздний ABORT Repair #3 (`ABORT_OVER_SETTLEMENT`);
  - P9: RETRY после проверенного отката;
  - история settlement неизменна;
  - VERIFIED не двигается назад;
  - защита R1.
- **Почему не история settlement (B):** нужна схема записей, миграция и новая семантика завершения второго settlement. Политика A закрывает все ловушки без изменения модели, а жизненный цикл повторного исполнения после отката — тема WA4-E (§10).

---

## 5. Изменённые файлы

| Файл | Изменение |
| --- | --- |
| `web_alarm/manifest_store.py` | блокировка подготовки, `_prepare_locked`, отбрасывание stage, CAS BACKUP_VERIFIED, «после публикации — не блокировать вслепую», `reconcile_interrupted_preparation` |
| `web_alarm/recovery_coordinator.py` | шаг `RECONCILE_PREPARATION` + событие; классификация PREPARING / BLOCKED_PREPARE; остановка `RECOVERY_IN_PROGRESS` |
| `web_alarm/state_machine.py` | NEXT для PREPARING; NEXT для BLOCKED_PREPARE с учётом evidence; `_restore_point_exists` |
| `web_alarm/resolver_service.py` | `SETTLEMENT_ADMITS`, `settlement_admits`; отказ `RECOVERY_ALREADY_SETTLED`; authority с учётом settlement; `_stale_advice` |
| `web_alarm/rollback_service.py` | `_authority` подчиняется политике settlement |
| `test_web_alarm_recovery_coordinator_repair4.py` | **новый**, 20 тестов |

Существующие тесты не менялись: ни ожидания, ни фикстуры.

---

## 6. Новые тесты (`test_web_alarm_recovery_coordinator_repair4.py`, 20)

- **A — прерванная подготовка (12):**
  - W1-краш → новый процесс → BLOCKED_PREPARE → NEXT исполним → подготовка → READY;
  - W2-краш → перепроверка → BACKUP_VERIFIED без переснятия (файл изменён после краша, snapshot прежний);
  - идемпотентность;
  - испорченный и нечитаемый опубликованный restore point → fail-closed, NEXT «manual repair»;
  - нет authority всё время;
  - живая подготовка не трогается (RECOVERY_IN_PROGRESS);
  - краш внутри reconcile → чистый рестарт;
  - сбой записи статуса после публикации → W2, а не мёртвая точка;
  - два конкурентных recover → ровно один reconcile и одно событие;
  - остатки stage до PREPARING отбрасываются.
- **B — политика settlement (8):**
  - матрица отказов (8 комбинаций): REJECTED до ACCEPTED, нет FAIL_CLOSED, нет attention, settlement неизменен, микрозадача не сдвинута, нет второго физического эффекта;
  - разрешённые (ADOPT → ABORT, ROLLBACK → ABORT, ROLLBACK → RETRY) доводятся до конца после рестарта;
  - отклонённое решение после settlement — история;
  - легаси-ACCEPTED поверх settlement — не authority;
  - RC-4 отказывает во втором откате по легаси-записи;
  - VERIFIED не двигается назад;
  - RETRY после ROLLBACK остаётся authority над поздним отказом;
  - единая политика у Resolver / Projection / RC-6 / гейта (в том числе в свежем процессе);
  - таблица политики.

**Чувствительность** (`probes/sensitivity_pre_repair4.py`): на runtime 163 падают **17 из 20**. На 163 проходят (так и ожидалось):
- разрешённые комбинации — они работали и до Repair #4;
- отсутствие authority — гейт Repair #3;
- таблица политики — шим.

---

## 7. Проверки

| Набор | Результат |
| --- | --- |
| Baseline 163, полный набор | 511 OK, skip 1 (`baseline_full_regression.txt`) |
| Repair #4, новый модуль | **20/20 OK**; 5 повторов подряд OK |
| Чувствительность на 163 | 17 из 20 падают; 3 ожидаемо проходят (§6) |
| Воспроизведение (`probes/repro_blockers.py`) | на 163 — W1 и W2 «вечный PREPARING», ловушки ADOPT → ADOPT, ROLLBACK → ADOPT, ROLLBACK → ROLLBACK (второй физический откат), вечное attention после отклонения; после — **14/14 закрыто** |
| Фокусно, 22 модуля (Repair #4/#3/#2/#1, CAS, RC-6 ×3, state machine, task store, manifest store, projection ×2, Resolver ×2, RC-3 ×2, RC-4 ×2, operation store, server, CLI) | **342/342 OK** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py`, 45 модулей | прогон 1 — **531 OK, skip 1**; прогон 2 — **531 OK, skip 1** (`full_regression_run1.txt`, `full_regression_run2.txt`) |
| Стресс-повторы гоночных модулей | **24/24 OK** (`stress_repeats.txt`): Repair #4 ×5, Repair #3 ×3, CAS ×3, Repair #2 ×3, RC-6 / RC-3 concurrency ×3, projection / RC-4 concurrency ×2 |
| Adversarial Repair #4 (`probes/repair4_adversarial.py 16`) | **5/5 OK**:<br>Y1 — 16 раундов «settlement ADOPT ↔ параллельный поздний ROLLBACK» на реальных процессах: нет FAIL_CLOSED, нет физического отката, повторный recover пуст;<br>Y2 — два конкурентных recover после W2 / W1: reconcile ровно один, одно событие;<br>Y3 — легаси-ACCEPTED ROLLBACK поверх settlement: RC-4 `REJECTED / RECOVERY_ALREADY_SETTLED`, восстановлений 2 → 2;<br>Y4 — 16 recover при живой подготовке: всегда RECOVERY_IN_PROGRESS, подготовка завершилась штатно |
| Adversarial Repair #3 (`repair3_adversarial.py 12`) | **4/4 OK**; воспроизведение Repair #3 — 11/11 закрыто; a10 на легаси-форме — OK |
| Adversarial #2A / Repair #2 | 5/5 OK / 7 OK; a10 — как в Repair #3, фикстура отклоняется state machine |
| Исходные пробы RC-6 | exit 0 / exit 0 |
| Пробы повторной проверки | 18 OK; n02 / n03 / n19 — исключение на фикстуре, n15 — артефакт барьера. Без изменений относительно Repair #3 |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK для кода и тестов. После ротации карточки — OK целиком. Новые файлы — LF, без хвостовых пробелов |

В ходе собственного adversarial pass найдено и исправлено:
- Y2 — лишнее событие при `NOT_INTERRUPTED`;
- Y3 — RC-4 принимал откат по легаси-записи поверх settlement; теперь подчиняется политике.

На оба добавлены регресс-тесты.

---

## 8. Безопасность / живое storage

- Все пробы, тесты и краши — только во временном storage.
- Живое `%LOCALAPPDATA%\WebAlarmWorkspace` только читалось (`probes/live_storage_hash.py`).
- `.obsidian/*` не трогался.
- Осиротевший дочерний процесс одного прогона чувствительности (он ждал флага во временной папке теста) остановлен, его временная папка удалена. Тест исправлен: всегда освобождает свой дочерний процесс.

| Живое storage | Файлов | Каталогов | SHA-256 (путь + содержимое) |
| --- | --- | --- | --- |
| до работы | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |
| после всех проверок | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |

Живое storage **не изменилось**.

---

## 9. Documentation Impact Check (по `18`)

```text
DOC IMPACT: YES
CURRENT STATE IMPACT: NO (до independent PASS)
ARCHITECTURE IMPACT: YES — перезапуск прерванной подготовки restore point; политика settlement
CONTEXT LIBRARY IMPACT: NO
REGISTRY / ROUTING IMPACT: NO
NEW DOCUMENT REQUIRED: NO
CANONICAL OWNER: 23_Архитектура Web Alarm Workspace.md
AFFECTED DOCUMENTS: 23 (§6/§8/§9: PREPARING восстанавливается через recover; политика settlement), 24/25 — по итогам проверки
CONTRADICTION CHECK: REQUIRED после PASS (в 23 нет утверждения, что PREPARING восстановим)
LOSS CHECK: NOT APPLICABLE
```

Канонические `23` / `24` / `25` / `05` / `06` / `001` не менялись. Их синхронизирует verifier после PASS, по регламенту.

---

## 10. Что вне scope / новые findings / остаточные риски

1. **Изменение файлов вне сервера между крашем W1 и повторной подготовкой** становится новым pre-состоянием. Так же было и при любой задержке до prepare. Исходные байты из неопубликованной stage не сохраняются (stage никогда не был restore point), но отбрасывание фиксируется событием. Если нужен forensic-слепок, можно перемещать stage в `discarded/` вместо удаления — PROPOSAL.
2. **Жизненный цикл операции после повторного исполнения по RETRY-после-отката (WA4-E).** По политике A поздний ADOPT поверх ROLLBACK settlement отклоняется. Если повторное исполнение операции в UNKNOWN_AFTER_DISCONNECT нельзя закрыть переходом STARTED → DONE, путь — поздний ABORT → RECOVERY_REQUIRED. WA4-E должен определить, как повторно исполненная операция получает финальный исход (например, отдельный settlement исполнения или история settlement — направление B). **FINDING / PROPOSAL для дизайна WA4-E.**
3. **BLOCKED_PREPARE с сохранённым испорченным restore point** — ручной ремонт (fail-closed по постановке). Штатного инструмента ремонта нет; NEXT и классификация RC-6 это честно показывают. PROPOSAL: отдельный инструмент «архивировать испорченный restore point и подготовить заново» — решение пользователя.
4. **Legacy CLI WA-1** (`snapshot prepare` / `restore`) — хвост WA4-R. Prepare через CLI теперь тоже берёт блокировку подготовки.
5. Остаточные риски из Repair #3 §10 (целостность restore point вне гейта RC-3, фокус projection по активности) — без изменений.

---

## 11. Рекомендация

**RC-6 готов к независимой проверке.** Условия выхода постановки (§8) выполнены:
- краш в PREPARING больше не даёт неразрешимого TASK; восстановление после W1 и W2 доказано на реальных крашах и в свежем процессе;
- Resolver не создаёт ACCEPTED-authority, которую RC-6 не может завершить; политика одна у Resolver, Projection, RC-6, гейта, RC-4 и OperationStore;
- инварианты Repair #2 / #2A / #3 сохранены: их модули зелёные, adversarial чист;
- фокусные и полный наборы зелёные, adversarial pass выполнен, отчёт заполнен, карточка ротирована.

Verifier стоит оценить:
- выбор направления A для Blocker B и PROPOSAL §10 п. 2 — жизненный цикл повторного исполнения для WA4-E;
- семантику W1: переснятие после отбрасывания неопубликованного stage (§10 п. 1).

**NEXT:** commit / push — пользователем → независимая проверка ChatGPT по GitHub → только после PASS RC-6 = DONE / VERIFIED → WA4-E. **WA4-E NOT STARTED.**

---

## 12. Артефакты

- `baseline.md`, `baseline_full_regression.txt`, `safety_copies/`
- `focused_regression.txt`, `full_regression_run1.txt`, `full_regression_run2.txt`, `stress_repeats.txt`
- `probes/`:
  - `repro_blockers.py` + `_baseline.txt` / `_after.txt`;
  - `sensitivity_pre_repair4.py` + `.txt`;
  - `repair4_adversarial.py` + `_output.txt`;
  - `live_storage_hash.py`, `live_storage_before.txt` / `live_storage_after.txt`;
  - `*_after_r4.txt` — прежние adversarial и исходные пробы на финальном коде.
