# AGENT REPORT — CLAUDE-WA-012 / RC-6 Repair #4A / PREPARING × ACCEPTED RECOVERY

- **Исполнитель:** Claude (Opus 5.5). Независимый verifier — ChatGPT по GitHub.
- **Дата:** 2026-10-08.
- **Источник:** прямой Chat-handoff пользователя (подтверждён пользователем в чате; БЛОК 1 по постановке не используется). Полная постановка — `task_statement.md`; в карточке — отдельная запись БЛОКА 2 «CLAUDE-WA-012 — RC-6 Repair #4A — FOLLOW-UP».
- **ARCH CLASS:** Web Alarm Workspace / Recovery Correctness. **PRIMARY:** `23_Архитектура Web Alarm Workspace.md`. **SECONDARY:** `24_План реализации Web Alarm Workspace.md`.
- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.** Commit / push не выполнялись.
- **Baseline:** GitHub `main`, commit 164 = `47e5344ade57aaabca8ed5f782d5eb94f57ad464`. Полный набор на baseline — 531 OK, skip 1 (`baseline_full_regression.txt`); SHA-256 и копии — `baseline.md`, `safety_copies/`.
- **Маршрут:**
  - `08_Старт.md` → `18_Регламент сопровождения документации.md` → глобальный `000_Задачи для агента.md` (БЛОК 1 там устарел — §9);
  - `01` (строка Web Alarm);
  - `23` §6–§11 (restore point, жизненный цикл, обрыв, запрет слепого отката);
  - `24` (маршрут RC-0…RC-6, статусы);
  - отчёт Repair #4.

---

## 1. Итог

**Finding независимого verifier подтверждён и шире, чем описан.** Вечный FAIL_CLOSED возникает у **любого** принятого ABORT по операции microtask, которая ещё не была ACTIVE:
- PREPARING (W1 и W2);
- после reconcile: BLOCKED_PREPARE и BACKUP_VERIFIED;
- без всякого краша: PLANNED, BACKUP_VERIFIED, READY.

Принятый ADOPT по такой операции (BACKUP_VERIFIED, READY, PREPARING-W2) — тоже вечный FAIL_CLOSED.

**Корень один.** Правило settlement в RC-6 знало только источники «после исполнения» (ACTIVE, DONE, UNKNOWN, RECOVERY_REQUIRED, FAILED_VERIFICATION). Классификация к тому же выбирала settlement раньше, чем reconcile прерванной подготовки.

**Исправление — только в RC-6.** Resolver, RC-4, Projection, OperationStore и граф state machine не менялись.
1. Reconcile прерванной подготовки идёт первым для любого recovery-решения по операции PREPARING-microtask.
2. ABORT-only disposition RECOVERY_REQUIRED допускается и из состояний «до исполнения» (PLANNED, BACKUP_VERIFIED, READY, BLOCKED_PREPARE). PREPARING — никогда, а disposition с ROLLBACK — по-прежнему только из состояний после исполнения.
3. Принятые ADOPT / ROLLBACK / RETRY по операции такой microtask — явная ручная граница с реальным выходом: штатная активация (после неё `recover` завершает решение) или ABORT.
4. Settlement, который под блокировкой обнаружил, что параллельная подготовка перевела microtask в PREPARING, ничего не пишет и уступает очередь reconcile. Раньше это давало разовый FAIL_CLOSED.

---

## 2. Воспроизведение на baseline 164

Проба `probes/repro_preparing_x_recovery.py`, временное storage, краш реального процесса. Вывод — `probes/repro_baseline.txt`, после исправления — `probes/repro_after.txt`. ADOPT — `probes/repro_adopt_pre_execution_*.txt`.

| Сценарий | 164: Resolver | 164: `recover` ×3 + свежий процесс | Lifecycle |
| --- | --- | --- | --- |
| A1: INTENT при PLANNED → prepare → краш W1 → ABORT до reconcile | **ACCEPTED** | **FAIL_CLOSED ×4** («m1 is PREPARING; cannot recovery-set it to RECOVERY_REQUIRED») | PREPARING навсегда |
| A2: то же, W2 | **ACCEPTED** | **FAIL_CLOSED ×4** | PREPARING навсегда |
| A3: W1 → reconcile → BLOCKED_PREPARE → ABORT | ACCEPTED | **FAIL_CLOSED ×4** («m1 is BLOCKED_PREPARE …») | — |
| A3: W2 → reconcile → BACKUP_VERIFIED → ABORT | ACCEPTED | **FAIL_CLOSED ×4** («m1 is BACKUP_VERIFIED …») | — |
| Без краша: INTENT + ABORT при PLANNED / BACKUP_VERIFIED / READY | ACCEPTED | **FAIL_CLOSED ×4** | — |
| STARTED/UNKNOWN + пост-состояние + ADOPT при BACKUP_VERIFIED / READY / W2 | **ACCEPTED** | **FAIL_CLOSED ×4** («cannot recovery-set it to DONE») | — |
| INTENT + ADOPT / ROLLBACK при PLANNED…READY | REJECTED (decision mismatch) | MANUAL (ручная, не ловушка) | — |
| INTENT + RETRY при BACKUP_VERIFIED / READY | ACCEPTED | RECOVERY_BLOCKED («cannot re-arm»; выход неочевиден) | — |

**Доступность через публичный API.** `OperationStore.begin` не требует ACTIVE. Resolver принимает ABORT без требования к решению. ADOPT принимается при решении ADOPT_CURRENT_STATE: пост-состояние появилось вне сервера, а у такой операции не было authority. Мутации без authority не было ни в одном сценарии: гейт F-C отказывал (`MICROTASK_NOT_ACTIVE` / `RECOVERY_ABORTED`).

**Обратный порядок** (сначала reconcile, потом ABORT) тоже был ловушкой — строки A3. Простая перестановка шагов, как и предупреждала постановка, её не закрывает.

---

## 3. Root cause

- `RecoveryCoordinator._settlement_rule(RECOVERY_REQUIRED)` разрешал источники `_TO_RECOVERY_REQUIRED_FROM` = {ACTIVE, DONE, UNKNOWN, RECOVERY_REQUIRED, FAILED_VERIFICATION}. Принятый ABORT по операции microtask «до исполнения» не имел пути завершения, а повторный `recover` выбирал тот же шаг.
- `_settlement_rule(DONE)` разрешал {ACTIVE, UNKNOWN, RECOVERY_REQUIRED, DONE}: принятый ADOPT по такой операции тоже не завершался.
- `_classify` обрабатывал состояния Resolver раньше, чем PREPARING (`RECONCILE_PREPARATION` стоял только в ветке NORMAL).
- Между выбором шага (projection без блокировок) и settlement под блокировками параллельная подготовка может перевести PLANNED → PREPARING (найдено adversarial-пробой).

---

## 4. Выбранное решение и почему

**Инвариант:** у принятого recovery-решения всегда есть достижимый путь завершения или явно описанная безопасная ручная граница.

1. **Reconcile первым** (`_classify`, `_reconcile_preparation`): если операция в фокусе recovery принадлежит PREPARING-microtask, первым шагом идёт `RECONCILE_PREPARATION` для этой microtask. Это механизм Repair #4 по persistent evidence:
   - W2 → BACKUP_VERIFIED без переснятия;
   - W1 → BLOCKED_PREPARE;
   - испорченный restore point → fail-closed, evidence сохраняется;
   - живая подготовка → RECOVERY_IN_PROGRESS.
2. **ABORT из состояний «до исполнения»** (`_ABORT_FROM_PRE_EXECUTION`, `_settlement_rule(actions=…)`): disposition RECOVERY_REQUIRED, составленная **только из ABORT**, может начаться из PLANNED, BACKUP_VERIFIED, READY или BLOCKED_PREPARE. Обоснование:
   - такая microtask никогда не была ACTIVE — state machine доходит до этих статусов только до первого ACTIVE. По гейту F-C ни одна её операция не могла получить authority, то есть эффекта нет;
   - RECOVERY_REQUIRED строже любого из этих статусов: выхода нет, мутации нет;
   - это ровно R2-disposition ABORT;
   - PREPARING как источник исключён: сначала reconcile;
   - с ROLLBACK в агрегате источники прежние — откат этапа, который не исполнялся, RC-6 не делает;
   - граф переходов state machine не менялся: это правило записи settlement в RC-6, как и раньше.
3. **Ручная граница для ADOPT / ROLLBACK / RETRY по microtask «до исполнения»** (`_classify` + `microtask_gate.pre_execution_next_action`). Вместо шага, который вечно падает, `recover` останавливается с объяснением и реальным выходом:
   - ADOPT / ROLLBACK → MANUAL_DECISION_REQUIRED;
   - RETRY → RECOVERY_BLOCKED, как и раньше, но теперь причина называет выход.

   Выход: активировать microtask через state machine (после этого `recover` штатно завершает решение; проверено — SETTLE_ADOPT → DONE, RETRY → READY_FOR_EXECUTION) или записать ABORT (сработает п. 2). Для ROLLBACK сессия RC-4 и claims до остановки не создаются.
4. **Отложенный settlement** (`_deferred_by_preparation_locked`): `_settle_resolution` и `_finish_settlement` под блокировками проверяют, не стала ли microtask PREPARING. Если стала — `DEFERRED_BY_PREPARATION` без записи, цикл перестраивает projection и делает reconcile или останавливается как IN_PROGRESS.

**Рассмотрено и отклонено:** запрет ADOPT/ROLLBACK в Resolver для microtask «до исполнения» (направление «защита Resolver»). Проба на 135 тестах RC-2/RC-4/RC-5 дала **69 падений и 2 ошибки**: фикстуры принятых этапов законно моделируют операции при BACKUP_VERIFIED. Это меняет принятую семантику RC-2, а решения на самом деле **исполнимы** после штатной активации. Правка откачена к точной копии 164.

Попытка переписать NEXT в Projection для этих случаев тоже откачена: она нарушала принятый контракт RC-5 (NEXT берётся дословно из сохранённого решения Resolver). Явное объяснение остаётся в `reason` результата RC-6.

---

## 5. Изменения runtime

| Файл | Изменение |
| --- | --- |
| `web_alarm/recovery_coordinator.py` | `_PRE_EXECUTION`, `_ABORT_FROM_PRE_EXECUTION`; `_settlement_disposition_locked` (цель + действия); `_settlement_rule(…, actions)`; `_deferred_by_preparation_locked`; `_classify`: сначала reconcile PREPARING, ручная граница ADOPT/ROLLBACK/RETRY до исполнения; `_reconcile_preparation` — microtask операции в фокусе |
| `web_alarm/microtask_gate.py` | `PRE_EXECUTION_STATUSES`, `pre_execution_next_action` (одна формулировка ручной границы) |

Resolver, RC-4, Projection, OperationStore, state machine, manifest store — **без изменений** относительно 164 (проверено `git diff`).

## 6. Тесты

- **Новый** `test_web_alarm_recovery_coordinator_repair4a.py` — 16 тестов:
  - A1 / A2 (+A5 рестарт в свежем процессе, A9 целостность restore point и pre-state);
  - A3 ×2 (сначала reconcile W1 / W2);
  - A4 (повторный recover без петли);
  - A6 ×2 (краш реального процесса после reconcile до settlement; между записью settlement операции и статусом microtask);
  - A7 ×3 (живая подготовка + ABORT + recover; отложенный settlement при подготовке, начавшейся между выбором и записью; prepare после settlement ABORT отклонён);
  - A8 (нет authority во всех промежуточных состояниях);
  - ABORT без краша из PLANNED / BACKUP_VERIFIED / READY;
  - ADOPT — ручная граница → завершение после активации;
  - ROLLBACK — ручная граница без сессии RC-4, ABORT закрывает;
  - RETRY — причина называет активацию, после неё READY;
  - источники правила settlement.
- **Чувствительность** (`probes/sensitivity_pre_repair4a.py`): на runtime 164 падают **16 из 16**.
- **Существующие тесты не менялись.**

## 7. Проверки

| Набор | Результат |
| --- | --- |
| Baseline 164, полный набор | 531 OK, skip 1 |
| Repair #4A, новый модуль | **16/16 OK**; 5 повторов подряд OK |
| Чувствительность на 164 | **16 из 16** падают |
| Воспроизведение (`probes/repro_preparing_x_recovery.py`) | на 164 — 9 ловушек (A1, A2, A3 ×2, ABORT ×3 без краша) + ADOPT ×6 (`repro_adopt_pre_execution_baseline.txt`); после — **0 ловушек из 16**, ADOPT — ручная граница → завершение после активации (`repro_adopt_pre_execution_after.txt`) |
| Фокусно, 23 модуля (Repair #4A / #4 / #3 / #2 / #1, CAS, RC-6 ×3, state machine, task store, manifest store, projection ×2, Resolver ×2, RC-3 ×2, RC-4 ×2, operation store, server, CLI) | **358/358 OK** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py`, 46 модулей | прогон 1 — **547 OK, skip 1**; прогон 2 — **547 OK, skip 1** |
| Стресс-повторы гоночных модулей | **27/27 OK** (`stress_repeats.txt`): Repair #4A ×5, Repair #4 ×3, Repair #3 ×3, CAS ×3, Repair #2 ×3, RC-6 / RC-3 concurrency ×3, projection / RC-4 concurrency ×2 |
| Adversarial Repair #4A (`probes/repair4a_adversarial.py 20`) | **3/3 OK**:<br>Z1 — 20 раундов «подготовка ↔ ABORT ↔ recover» тремя процессами: ни одного FAIL_CLOSED; принятый ABORT всегда → RECOVERY_REQUIRED; устаревший ABORT честно отклонён, microtask остаётся подготовленной; нет authority, restore point целый;<br>Z2 — W2 + устаревший RETRY → reconcile, затем честное ручное состояние → ABORT закрывает;<br>Z3 — испорченный опубликованный restore point + ABORT → fail-closed подготовка, evidence сохранено, ABORT → RECOVERY_REQUIRED |
| Найдено adversarial-проходом и исправлено | разовый FAIL_CLOSED при подготовке, начавшейся между выбором шага и settlement → `DEFERRED_BY_PREPARATION` + регресс-тест |
| Adversarial / воспроизведение Repair #4 | 5/5 OK; 14/14 закрыто |
| Adversarial / воспроизведение Repair #3 | 4/4 OK; 11/11 закрыто |
| Adversarial #2A / Repair #2 | 5/5 OK / 7 OK (a10 — как раньше) |
| Исходные пробы RC-6 | exit 0 / exit 0 |
| Пробы повторной проверки | 18 OK; n02 / n03 / n19 — фикстура, n15 — артефакт барьера; без изменений с Repair #3 |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK (весь репозиторий); новые файлы — LF, без хвостовых пробелов |

## 8. Безопасность / живое storage

Все испытания — только во временном storage; живое `%LOCALAPPDATA%\WebAlarmWorkspace` только читалось.

| Живое storage | Файлов | Каталогов | SHA-256 (путь + содержимое) |
| --- | --- | --- | --- |
| до работы | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |
| после всех проверок | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |

Живое storage **не изменилось**.

---

## 9. Связь с Repair #4 и документационная непрерывность

**Цепочка RC-6 (все отчёты в `Alarm/ALARM_TASK_SESSION/`):**

| Шаг | Исполнитель | Ключевое | Итог проверки |
| --- | --- | --- | --- |
| CHATGPT-WA-008 / RC-6 + Repair #1 | ChatGPT | RecoveryCoordinator, B1–B5 | Claude: независимая проверка FAIL (RC6-VERIFY), повторная — FAIL (RC6-REVERIFY) |
| CLAUDE-WA-009 / Repair #2 + #2A | Claude | R1 / R2 / R3, F-D, F-E; CAS state machine | ChatGPT по 162: FAIL |
| CLAUDE-WA-010 / Repair #3 | Claude | гейт F-C, F-B, R3 confirm, F4 / F5, C1, поздний ABORT | ChatGPT по 163: целевые PASS, остались 2 блокера |
| CLAUDE-WA-011 / Repair #4 | Claude | прерванная подготовка W1/W2, политика settlement | ChatGPT по 164: основное PASS, static finding → этот #4A |
| **CLAUDE-WA-012 / Repair #4A** | Claude | PREPARING / «до исполнения» × принятое решение | **RESULT READY — ждёт проверки** |

**Repair #4A дополняет Repair #4, ничего не отменяя:**
- reconcile W1/W2 из #4 — механизм п. 1;
- политика settlement #4 (`SETTLEMENT_ADMITS`, отказ RC-4 во втором откате) не тронута;
- поздний ABORT Repair #3 сохранён.

### DOCUMENTATION IMPACT CHECK (регламент 18)

```text
DOC IMPACT: YES
CURRENT STATE IMPACT: YES — но только после independent PASS (до него статусы не меняются)
ARCHITECTURE IMPACT: YES — правила recovery RC-6 (см. delta 23)
CONTEXT LIBRARY IMPACT: NO
REGISTRY / ROUTING IMPACT: NO (новых документов нет; ответственность документов не меняется)
NEW DOCUMENT REQUIRED: NO
CANONICAL OWNER: 23_Архитектура Web Alarm Workspace.md (архитектура); 24 (статус этапов); 25 (профильная история)
AFFECTED DOCUMENTS: 23, 24, 25, 01, 05, 06, 001, 000 (глобальный), 000_Задачи Claude (сделано сейчас)
CONTRADICTION CHECK: REQUIRED — найдены устаревшие CURRENT-утверждения (ниже)
LOSS CHECK: NOT APPLICABLE (ничего не удалялось); предыдущие записи Repair #1…#4 сохранены
```

### Documentation delta (выполняет verifier / координатор после PASS)

**Устаревшие сейчас утверждения (факт по коду и Git ≠ документ):**
- `01` (строка Web Alarm): «RC-0…RC-3 DONE / VERIFIED; RC-4 следующий, ещё не запущен». По `24` и `000` RC-4 = DONE / VERIFIED 2026-10-04, RC-5 = RESULT READY (приёмка отложена пользователем), RC-6 в цикле repair.
- `24` строка 9: «RC-6 = ACTIVE / IN PROGRESS по утверждённой Chat TASK CHATGPT-WA-008» — маршрут RC-6 с тех пор прошёл Repair #2…#4A. Статусная таблица (строки ~809/812): «RC-4 next / not started» — устарело.
- Глобальный `000` БЛОК 1: «CHATGPT-WA-008 / RC-6 — REPAIR #1 — RESULT READY» — устарело; последняя точка — Repair #4A, ждёт проверки.
- `001`, `05`, `06`, `25`: история и реестр заканчиваются на RC-4 DONE / VERIFIED; RC-5 и цепочки RC-6 нет.

**Что должно появиться после PASS RC-6:**
- `23` — архитектурные правила RC-6, подтверждённые кодом:
  - гейт исполнения (только ACTIVE и текущий этап, без disposition ABORT/ROLLBACK, проверка внутри `mutation_boundary` под mutation lock);
  - допуск VERIFIED только без открытого recovery; поглощение неразрушающих settlement VERIFIED-этапом;
  - READY привязан к полному proof, повторно выведенному под блокировками;
  - перезапуск подготовки restore point (блокировка подготовки, W1/W2, reconcile, fail-closed для испорченного);
  - политика settlement (`SETTLEMENT_ADMITS`, история settlement неизменна);
  - recovery по microtask «до исполнения» (reconcile первым, ABORT → RECOVERY_REQUIRED, ручная граница ADOPT/ROLLBACK/RETRY до активации).

  В §6/§8 дополнить: PREPARING восстанавливается через `recover`; BLOCKED_PREPARE с сохранённым restore point — только ручной ремонт; RECOVERY_REQUIRED достижим и из состояний «до исполнения» через ABORT.
- `24` — RC-6 = DONE / VERIFIED (только после PASS), обновить строку 9 и статусную таблицу; RC-5 — по решению пользователя об отложенной приёмке; NEXT = WA4-E.
- `25` — записи RC-5 и RC-6 (CHATGPT-WA-008 + Repair #1; проверки Claude; Repair #2 / #2A / #3 / #4 / #4A с итогами проверок ChatGPT).
- `05` — строки RC-5 / RC-6 со статусами; `06` — хронология RC-5 / RC-6; `001` — CLAUDE-RC6-VERIFY, CLAUDE-RC6-REVERIFY, WA-009…WA-012 (append-only); `01` — краткая строка Web Alarm; глобальный `000` — project-level NEXT (WA4-E после PASS).

**Подтверждено сейчас (исполнителем, не verifier):** только исполнительские проверки этого отчёта. Ни один статус не объявлен DONE / VERIFIED.

**Сделано сейчас в пределах полномочий исполнителя:**
- карточка `000_Задачи Claude`: БЛОК 2 — отдельная запись FOLLOW-UP с полной постановкой; БЛОК 3 — отдельная запись результата; Repair #4 сохранён;
- task session (`task_statement.md`, `baseline.md`, пробы, этот отчёт).

## 10. Остаточные риски / findings

1. **Отклонённое решение по операции без settlement** (например, ADOPT / ROLLBACK с decision mismatch для INTENT-операции) остаётся фокусом Projection (MANUAL), пока его basis не устареет или не будет записан ABORT. Это принятая семантика RC-5 («свежий отказ хранит совет»), не ловушка: ABORT всегда доступен. Но ABORT переводит microtask в RECOVERY_REQUIRED. **PROPOSAL:** решить, должен ли отказ по закрытой операции оставаться вниманием — решение по RC-5.
2. **Legacy CLI WA-1 `restore_microtask`** может вернуть microtask в BACKUP_VERIFIED после ACTIVE (обход state machine). Тогда «до исполнения» по статусу не равно «никогда не исполнялась». Правило п. 2 даёт в этом случае лишь ручную границу RECOVERY_REQUIRED (строже, безопасно). Хвост **WA4-R**.
3. Остаточные риски Repair #4 (§10 там): переснятие W1, жизненный цикл повторного исполнения для WA4-E, инструмент ремонта испорченного restore point — без изменений.

## 11. Что требуется для independent PASS RC-6

- Проверка ChatGPT по новому коммиту: этот отчёт, тесты Repair #4A и регрессия Repair #2…#4.
- Отдельно оценить решение «ABORT из состояний до исполнения → RECOVERY_REQUIRED» и ручную границу для ADOPT/ROLLBACK/RETRY (§4) — это семантика, а не только код.
- После PASS — documentation delta §9 силами verifier / координатора; затем RC-6 = DONE / VERIFIED и NEXT = WA4-E.

**Блокеры перед WA4-E** — по оценке исполнителя, нет: внутри scope RC-6 известных ловушек не осталось. Решение за независимой проверкой.

## 12. Рекомендация

**RC-6 готов к независимой проверке.** Finding подтверждён и закрыт в обобщённой форме:
- у каждого принятого решения по операции microtask, которая не исполнялась, есть путь завершения или явная ручная граница;
- вечного FAIL_CLOSED нет ни в одном исследованном сочетании;
- инварианты Repair #2 / #2A / #3 / #4 сохранены.

**NEXT:** commit / push — пользователем → независимая проверка ChatGPT по новому коммиту → только после PASS RC-6 = DONE / VERIFIED → documentation delta §9 → WA4-E. **WA4-E NOT STARTED.**
