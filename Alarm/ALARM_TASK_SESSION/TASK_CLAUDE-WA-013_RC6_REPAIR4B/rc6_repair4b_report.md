# AGENT REPORT — CLAUDE-WA-013 / RC-6 Repair #4B / PRE-EXECUTION ABORT × SIBLING ROLLBACK

- **Исполнитель:** Claude (Opus 5.5). Независимый verifier — ChatGPT по GitHub.
- **Дата:** 2026-10-08.
- **Источник:** прямой Chat-handoff пользователя, подтверждён его словами («вот тебе еще одна задача»). БЛОК 1 по постановке не используется. Полная постановка — `task_statement.md`; в карточке — отдельная запись БЛОКА 2 «CLAUDE-WA-013 — RC-6 Repair #4B — FOLLOW-UP».
- **ARCH CLASS:** Web Alarm Workspace / Recovery Safety. **PRIMARY:** `23_Архитектура Web Alarm Workspace.md`. **SECONDARY:** `24_План реализации Web Alarm Workspace.md`.
- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.** Commit / push не выполнялись.
- **Baseline:** GitHub `main`, commit 165 = `32bdf9635afcf81a9e6f1090a3bcba54b907c126`. Полный набор на baseline — 547 OK, skip 1 (`baseline_full_regression.txt`); SHA-256 и копии 84 файлов — `baseline.md`, `safety_copies/`.
- **Маршрут:**
  - `08_Старт.md` → `18_Регламент сопровождения документации.md` → глобальный `000_Задачи для агента.md` (БЛОК 1 там устарел — §12);
  - `Alarm/ALARM_TASK_SESSION/00_INSTRUCTION.md` (ведутся `session.jsonl`, `context.md`, `history.md`);
  - `01` (строка Web Alarm);
  - `23` §4–§11, §17, §22 (restore point, rollback только текущей microtask, завершённые этапы не откатываются, инварианты 5 / 26 / 34 / 35);
  - `24` (маршрут RC-0…RC-6, таблица exit-proof RC-4 / RC-6);
  - отчёты Repair #4A (полностью), #4 и #3 (итоги и риски).

---

## 1. Итог

**Дефект подтверждён, и он шире, чем описан.** Реальный destructive rollback воспроизведён (только во временном storage) — файлы физически восстановлены поверх изменений, сделанных вне сервера, у microtask, которая **ни разу не была ACTIVE**.

Два независимых пути:

1. **RC-6 `recover` (регрессия Repair #4A).** ABORT `op1` до исполнения → RC-6 переводит microtask в RECOVERY_REQUIRED → принятый ROLLBACK соседней `op2` проходит PREPARE → APPLY → SETTLE и восстанавливает restore point. На 164 этого пути не было: ABORT `op1` уходил в вечный FAIL_CLOSED, а APPLY отклонялся preflight'ом.
2. **Прямой вход RC-4** (`RollbackService.prepare/apply` и HTTP `POST /tasks/{id}/rollbacks[…/apply]`) — **пробел со времён приёмки RC-4 (commit 154)**. RC-4 вообще не проверял жизненный цикл microtask:
   - откатывал microtask, никогда не бывшую ACTIVE, даже без соседнего ABORT (BACKUP_VERIFIED / READY);
   - откатывал **VERIFIED-этап**, в том числе не текущий. Это прямое нарушение инварианта 4 задачи и `23` §11 / §22.5; защита R1 была только в RC-6.

**Исправление — одно общее правило отката** (`microtask_gate.rollback_refusal`), которое применяют и RC-4 (создание сессии и каждый destructive apply), и RC-6 (preflight). Плюс один новый persisted факт: settlement хранит статус microtask, на котором он был решён (`recovery_settlement.microtask_status`). Откат исполнявшегося этапа работает как прежде.

---

## 2. Воспроизведение (до исправления)

Пробы — временное storage; изменения файлов делает сама проба «извне»: microtask не ACTIVE, RC-3 `mutation_boundary` не вызывался, авторизованного исполнителя не было. `op2` STARTED — только запись lifecycle через публичный `OperationStore.transition` (он не требует ACTIVE). Многоцелевой partial-known-state: `a.txt` в пост-состоянии `op2`, `keep.txt` в пре-состоянии → Resolver `ROLLBACK_CURRENT_MICROTASK / PARTIAL_KNOWN_STATE` → ROLLBACK ACCEPTED.

`probes/repro_sibling_rollback.py` (+ `[code_root]` для старых коммитов). Выводы: `probes/repro_baseline_165.txt`, `probes/repro_on_164.txt`, `probes/repro_on_154.txt`.

| Сценарий | 154 | 164 | **165** |
| --- | --- | --- | --- |
| B1 RC-6: m1 BACKUP_VERIFIED / READY / W2, ABORT `op1` → RR, ROLLBACK `op2`; цели WRITE / DELETE (файл удалён извне → создаётся снова) / CREATE (созданный извне файл удаляется) | RC-6 ещё нет | ABORT `op1` — FAIL_CLOSED; PREPARE создал сессию, APPLY отклонён preflight («m1 is READY»), **байты не тронуты** | **DESTRUCTIVE** ×7: шаги PREPARE_ROLLBACK, APPLY_ROLLBACK, SETTLE_ROLLBACK; сессия VERIFIED; claims сняты; `op2` settlement ROLLBACK; свежий процесс — MANUAL (без повторного действия) |
| Контроль: m1 ACTIVE / UNKNOWN (реально исполнялась) | — | DESTRUCTIVE (законно) | DESTRUCTIVE (законно) |
| B2 прямой RC-4, после соседнего ABORT (сервис и API) | — | **DESTRUCTIVE** | **DESTRUCTIVE** |
| B2 прямой RC-4 без ABORT, m1 READY / BACKUP_VERIFIED (сервис и API) | **DESTRUCTIVE** | **DESTRUCTIVE** | **DESTRUCTIVE** |
| R1 прямой RC-4: m1 VERIFIED (последний этап и при текущем m2), сервис и API (`probes/repro_rc4_protected_stage.py`) | **DESTRUCTIVE** | **DESTRUCTIVE** | **DESTRUCTIVE** |

Resolver authority во всех строках: ROLLBACK `op2` — ACCEPTED / BASIS_FRESH_ACTION_ALLOWED (свежий); ABORT `op1` — ACCEPTED. Target claims после отката — сняты (RC-4 штатно), во время apply — у сессии отката. Повтор в свежем процессе — тот же итог, без повторного эффекта.

---

## 3. Root cause

1. **RC-6 (Repair #4A).** RECOVERY_REQUIRED перестал означать «microtask исполнялась»: Repair #4A разрешил его из PLANNED / BACKUP_VERIFIED / READY / BLOCKED_PREPARE для ABORT-only disposition. Остальной RC-6 по-прежнему считал RR статусом после исполнения:
   - `_rollback_stage_preflight` пускал APPLY из `_TO_RECOVERY_REQUIRED_FROM` (там RR);
   - ручная граница Repair #4A для ROLLBACK смотрела только на текущий статус «до исполнения», а он уже RR.
2. **RC-4.** `RollbackService._authority` проверял resolution, ABORT, контракт и settlement policy, но не жизненный цикл: ни R1 (VERIFIED / не текущий этап), ни факт исполнения. R1 жил только в RC-6, поэтому прямой вход RC-4 (сервис и HTTP) его обходил.
3. **Нет persisted факта**, отличающего «RR после исполнения» от «RR из-за ABORT до исполнения». У `MicrotaskRecord` нет истории; events пишутся после CAS (окно краша) и являются историей, а не authority; settlement, resolution basis и evidence статус microtask не содержат.

---

## 4. Выбранное решение и почему

**Инвариант:** откат восстанавливает restore point только **текущего этапа, который действительно исполнялся (был ACTIVE)**. Любое сомнение — отказ без единого изменения байтов.

### 4.1. Новый persisted факт — статус microtask в settlement

`OperationStore._settle_recovery_locked(…, microtask_status=…)` записывает в settlement статус, который RC-6 наблюдал **в той же секции под TASK-lock + mutation lock**. Запись атомарна вместе с settlement. Пишется во всех settlement RC-6: `_settle_resolution` (ADOPT / ABORT) и `_settle_verified_rollback` (ROLLBACK).

- Схема (`operation_contract.validate_record`): поле необязательное, значение — только допустимый `MicrotaskStatus`; любое другое лишнее поле по-прежнему отклоняется. Старые записи без поля читаются как раньше.
- Факт не входит в replay-идентичность settlement: повтор с тем же action / resolution — REPLAYED, первый факт сохраняется.
- **Почему его достаточно.** Settlement со статусом «до исполнения» может быть только ABORT (ADOPT / ROLLBACK до исполнения — ручная граница #4A и не settle'ятся). Принятый ABORT постоянен (`SETTLEMENT_ADMITS["ABORT"] = {}`) и навсегда лишает microtask mutation authority (`execution_refusal`). Значит, у такой microtask не может быть авторизованного эффекта — при любом её текущем статусе.

### 4.2. Общее правило `microtask_gate.rollback_refusal`

Порядок отказов:

1. Факты не читаются → `LIFECYCLE_STATE_UNAVAILABLE` (fail-closed).
2. VERIFIED или не текущий этап → `ROLLBACK_STAGE_PROTECTED` (R1; `rollback_stage_protected` перенесён из projection в `microtask_gate` и реэкспортирован).
3. Есть settlement, записанный до первого ACTIVE → `MICROTASK_NEVER_EXECUTED` (при любом текущем статусе).
4. ACTIVE / DONE / UNKNOWN_AFTER_DISCONNECT / FAILED_VERIFICATION → разрешено: по графу state machine они достижимы только через ACTIVE.
5. RECOVERY_REQUIRED → разрешено, кроме случая, когда есть ABORT settlement без факта (записан до Repair #4B) → `MICROTASK_EXECUTION_UNPROVEN`.
6. Иначе (PLANNED / PREPARING / BACKUP_VERIFIED / READY / BLOCKED_PREPARE) → `MICROTASK_NEVER_EXECUTED`.

### 4.3. Где применяется

| Место | Как |
| --- | --- |
| RC-4 `_authority` | при создании сессии (`prepare` → REJECTED, сессия не создаётся, событие ROLLBACK_REJECTED; API → 409 `rollback_rejected`) и перед каждой destructive фазой `apply` (`_session_basis` → BLOCKED, ничего не восстановлено, claims не захвачены). Finalize (DRIFTED / FAILED) и release-only не блокируются |
| RC-6 `_rollback_stage_preflight` | то же правило вместо прежнего R1-only; для APPLY по-прежнему сначала RR (Repair #2A) |
| RC-6 `_classify` | ROLLBACK_ACCEPTED у microtask с settlement «до исполнения» → MANUAL_DECISION_REQUIRED с причиной и выходом (ABORT операции или replan); стоит раньше ручной границы #4A, чтобы в окне краша не советовать «активируй» |

### 4.4. Изменения фикстур

Ровно 5 строк в трёх существующих тестовых файлах. Фикстуры RC-4 / RC-5 откатывали microtask, никогда не бывшую ACTIVE (BACKUP_VERIFIED + STARTED op) — ровно то, что теперь запрещено. Каждая получила одну строку «m1 ACTIVE» (тот же storage-примитив, что с Repair #3 используется для внешнего writer'а). Смысл и проверки тестов не менялись.

### 4.5. Рассмотрено и отклонено

- **События (MICROTASK_TRANSITION → ACTIVE) как доказательство исполнения.** Пишутся после CAS (окно краша без события), это история, а не authority (`23` §22.10). Фикстуры с прямой записью статуса событий не имеют.
- **Отказ в Resolver.** Тот же путь, что отклонён в #4A: меняет принятую семантику RC-2. Исполнитель (RC-4) — правильное место; прецедент — Repair #4 (политика settlement тоже продублирована в RC-4).
- **Не писать RR при ABORT до исполнения** (оставить статус «до исполнения»). Меняет семантику #4A, принятую статически. Microtask READY с вечным ABORT могла бы быть активирована и откатана — та же дыра.
- **Запрет активации microtask с принятым ABORT в state machine.** Это изменение графа / предусловий state machine → только PROPOSAL (§10).

---

## 5. Изменения runtime

| Файл | Изменение |
| --- | --- |
| `web_alarm/microtask_gate.py` | `EXECUTED_STATUSES`, `rollback_stage_protected` (перенесён), `pre_execution_settlement`, `rollback_refusal` |
| `web_alarm/rollback_service.py` | `_authority`: `rollback_refusal` (prepare + каждый destructive apply); docstring |
| `web_alarm/recovery_coordinator.py` | settlement с `microtask_status` (ADOPT / ABORT / ROLLBACK); `_rollback_stage_preflight` на общем правиле; `_classify` — ручная граница для ROLLBACK при settlement «до исполнения»; `_never_executed_rollback_reason`; удалён ставший неиспользуемым `_current_microtask_locked` |
| `web_alarm/operation_store.py` | `_settle_recovery_locked(…, microtask_status=None)` |
| `web_alarm/operation_contract.py` | схема settlement: необязательное `microtask_status` (только допустимые статусы) |
| `web_alarm/projection.py` | `rollback_stage_protected` реэкспортируется из `microtask_gate` (определение перенесено), комментарий |

Не менялись: Resolver, state machine (граф и предусловия), ManifestStore, RC-3, TaskStore, server, Recovery Report, Context Pack.

Тесты:
- **новый** `test_web_alarm_recovery_coordinator_repair4b.py` — 22 теста;
- `test_web_alarm_rollback.py` (+3 строки), `test_web_alarm_projection.py` (+2 строки), `test_web_alarm_rollback_concurrency.py` (+2 строки) — только фикстура «m1 ACTIVE» (§4.4).

---

## 6. Тесты Repair #4B (22)

| Группа | Тесты |
| --- | --- |
| B1 / B8 | RC-6 не восстанавливает ни для WRITE / DELETE / CREATE, ни для BACKUP_VERIFIED / READY; storage digest и байты неизменны, сессий и claims нет, `op2` без settlement; preflight отказывает и при выбранном шаге (PREPARE и APPLY сессии старой сборки); ABORT `op2` закрывает без восстановления |
| B2 / R1 | прямой RC-4 (сервис + HTTP 409) после соседнего ABORT и без ABORT; сессия старой сборки — apply BLOCKED, claim не взят, recover RECOVERY_BLOCKED, close работает; VERIFIED-этап (последний и при текущем m2) не откатывается |
| B3 | откат после ACTIVE → UNKNOWN восстанавливает все три вида целей точными байтами; соседний ABORT, settled из ACTIVE, откату не мешает; прямой RC-4 на ACTIVE |
| B4 | recover ×3 + свежий процесс — MANUAL, ничего не записано; краш между записью settlement и статусом → активация в окне краша → прямой RC-4 и recover всё равно отказывают; ABORT `op2` закрывает |
| B5 | W2 + ABORT + соседний ROLLBACK — отказ; W1 + ABORT — restore point отброшен, ROLLBACK не принимается (откатывать нечего) |
| B6 | stale ROLLBACK — ничего не восстановлено; ABORT settlement старого формата (без факта) → `MICROTASK_EXECUTION_UNPROVEN`; факт валидируется и не входит в replay; каждый settlement RC-6 пишет статус |
| B7 | реальные процессы: ABORT ↔ recover ×2 ↔ прямой RC-4 (3 раунда) — ни одного восстановления, без ошибок, без FAIL_CLOSED в итоге |
| Таблица правила | все `MicrotaskStatus`; не текущий этап; нечитаемые факты; settlement «до исполнения» отказывает при RR / ACTIVE / UNKNOWN |

**Чувствительность** (`probes/sensitivity_pre_repair4b.py`): на runtime 165 падают **20 из 22**.
- Проходят 2: прямой RC-4 на ACTIVE (контроль) и stale.
- Контрольные B3 ×2 и B5-W1 на 165 падают только на утверждении о новом факте settlement; их поведение отката то же.

---

## 7. Проверки

| Набор | Результат |
| --- | --- |
| Baseline 165, полный набор | 547 OK, skip 1 (`baseline_full_regression.txt`) |
| Repair #4B, новый модуль | **22/22 OK**; в стресс-повторах ещё 5 раз подряд OK |
| Чувствительность на 165 | **20 из 22** падают (`probes/sensitivity_pre_repair4b.txt`) |
| Воспроизведение после исправления (`probes/repro_after.txt`, `probes/repro_rc4_protected_stage_after.txt`) | все 12 сценариев с microtask без исполнения — **REFUSED, байты не тронуты**; DESTRUCTIVE только 3 контроля с реально исполнявшимся этапом (RC-6 ACTIVE / UNKNOWN, прямой RC-4 на ACTIVE); R1 ×3 — REFUSED (`ROLLBACK_STAGE_PROTECTED`, API 409) |
| Фокусно, 27 модулей (Repair #4B / #4A / #4 / #3 / #2 / #1, CAS, RC-6 ×3, RC-4 ×2, RC-5 ×2, Resolver ×2, RC-3 ×2, RC-1 контракт, operation store ×2, state machine, task store, manifest store, report acceptance, server, CLI) | **414 тестов, 27/27 модулей exit 0** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py`, 47 модулей, финальный код | прогон 1 — **569 OK, skip 1**; прогон 2 — **569 OK, skip 1** (`full_regression_run1.txt`, `full_regression_run2.txt`). До финальной правки комментария в `projection.py` — ещё два прогона по 569 OK, skip 1 (`full_regression_interim*.txt`) |
| Стресс-повторы гоночных модулей | **27/27 OK** (`stress_repeats.txt`): Repair #4B ×5, RC-4 concurrency ×3, Repair #4A ×3, Repair #4 ×3, Repair #3 ×2, Repair #2 ×2, RC-6 concurrency ×3, CAS ×2, RC-3 concurrency ×2, projection concurrency ×2 |
| Adversarial Repair #4B (`probes/repair4b_adversarial.py 24`) | Z1 24 раунда — 0 нарушений; Z2 OK; Z3 — downgrade fail-closed (§9) |
| Конкуренция RC-6 ↔ прямой RC-4 на исполнявшемся этапе, текущий код и 165 | 100 / 100 вызовов recover — MANUAL; одинаково |
| Прежние пробы (11 наборов: исходные RC-6 ×2, повторная проверка, #2, #2A, #3 ×2, #4 ×2, #4A ×2) | все exit 0; **сигнатуры вердиктов совпадают с состоянием после #4A** (`probes/*_after_r4b.txt`): повторная проверка — 18 OK, n02 / n03 / n19 — фикстура, n15 — артефакт барьера (как раньше); #4A — 3/3 и 16 «no trap» |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK; новые `.py` / `.md` — LF, без хвостовых пробелов (захваченные выводы консоли `.txt` — CRLF рабочего дерева, git хранит LF, как в прошлых сессиях) |

---

## 8. Безопасность / живое storage

Все испытания — только во временном storage; живое `%LOCALAPPDATA%\WebAlarmWorkspace` только читалось (в том числе одна read-only выборка: 2 операции, 0 settlement, 0 microtask в RECOVERY_REQUIRED — новая строгость для старых записей реальные данные не затрагивает).

| Живое storage | Файлов | Каталогов | SHA-256 (путь + содержимое) |
| --- | --- | --- | --- |
| до работы | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |
| после всех проверок | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |

Живое storage **не изменилось**.

---

## 9. Собственный adversarial review

| Атака / вопрос | Результат |
| --- | --- |
| Гонка активации ↔ settlement ABORT ↔ ROLLBACK + прямой RC-4 ↔ recover ×2 (Z1, реальные процессы, случайные задержки) | **24 раунда, 0 нарушений**: 14 — ABORT закреплён при READY → активация отклонена → ничего не восстановлено; 4 — сначала активация, settlement из ACTIVE → откат (законный); 6 — активация, затем RC-6 откатил уже ACTIVE-этап (законный). Инварианты проверены построчно: восстановление ⇒ активация успешна и факт не «до исполнения»; факт «до исполнения» ⇒ активация отклонена |
| Сессия старой сборки для microtask без исполнения, apply двумя процессами + recover (Z2) | оба apply — BLOCKED `MICROTASK_NEVER_EXECUTED`, recover — RECOVERY_BLOCKED, claims не взяты, close — CLOSED, файл не тронут |
| Откат версии назад (Z3) | код 165 не читает запись с новым фактом («recovery_settlement has unexpected fields») — fail-closed; downgrade после #4B не поддерживается (§10) |
| Конкуренция RC-6 ↔ прямой RC-4 на исполнявшемся этапе (`probes/rc6_vs_direct_rc4_contention.py`), текущий код и 165 | по 25 раундов: 50 / 50 вызовов recover — MANUAL, итог MANUAL, откат выполнен; поведение одинаковое |
| Рестарт / краш | правило без состояния; факт пишется атомарно с settlement до статуса microtask; окно краша между ними покрыто B4 |
| Повторный recover | без записи (digest неизменен), без петли |
| Устаревший Resolver basis | stale → отказ / MANUAL, ничего не восстановлено (B6) |
| Исторические операции / старые записи | settlement без факта: ADOPT / ROLLBACK — после исполнения по построению старых версий; ABORT — `MICROTASK_EXECUTION_UNPROVEN` (fail-closed) |
| Старые restore points | правило их не касается; проверки RC-4 (fingerprint, целостность) не менялись |
| Прямой вызов RC-4 | закрыт в `_authority` (сервис и HTTP) |
| Порядок блокировок | новых блокировок нет: чтение под уже удерживаемой TASK-lock (RC-4) или TASK-lock + mutation lock (RC-6) |
| Соседний ADOPT после ABORT до исполнения | RC-6 закрепляет ADOPT административно (`op2` VERIFIED, microtask остаётся RR), байты не меняются — неразрушающе; §10 |
| Прежние adversarial-пробы (§7) | вердикты совпадают с состоянием после #4A |

Найдено adversarial-проходом и учтено в коде:
- факт «до исполнения» проверяется раньше статусов исполнения: иначе прямой RC-4 до FINISH_SETTLEMENT (microtask активирована в окне краша) и после него давал бы разные ответы;
- в `_classify` проверка факта стоит раньше ручной границы #4A, чтобы та не советовала «активируй»;
- формулировка причины корректна и при текущем статусе ACTIVE.

---

## 10. Остаточные риски / findings / proposals

1. **DECISION / PROPOSAL — активация microtask с уже принятым ABORT.** State machine разрешает READY → ACTIVE при принятом (ещё не закреплённом) ABORT соседней операции. После этого microtask «исполнялась» по статусу и откат её этапа разрешён, хотя mutation authority у неё не было (`execution_refusal`). Так было и на 164; ровно этот выход («активируй, потом recover») описан в Repair #4A. Закрыть полностью можно двумя путями:
   - (а) state machine отказывает в активации при ABORT / ROLLBACK disposition — изменение предусловий графа;
   - (б) persisted факт выдачи mutation authority (RC-3 / WA4-E).

   Оба — вне scope; решение за пользователем / verifier.
2. **PROPOSAL — соседний ADOPT после ABORT до исполнения** закрепляется административно (операция VERIFIED, microtask остаётся RR). Это неразрушающе. Для единообразия с ручной границей #4A можно останавливать и его — семантика RC-5 / RC-6, решение verifier.
3. **Downgrade.** Записи settlement с новым полем не читаются кодом ≤ 165 (строгая схема) — fail-closed. Откат версии после появления таких записей требует ручной миграции.
4. **ABORT settlement старого формата у RR microtask** → `MICROTASK_EXECUTION_UNPROVEN`: откат не выполняется, только ручной разбор. В живом storage таких записей нет (0 settlement). Сессия отката, начатая старой сборкой на такой microtask, при продолжении остановится BLOCKED (receipts сохраняются, close доступен).
5. **NEXT в Projection** для ROLLBACK_ACCEPTED у такой microtask — дословно из Resolver (контракт RC-5). Объяснение отказа — в `reason` результата RC-6, как и в #4A.
6. **Разовый FAIL_CLOSED одного конкурентного recover** наблюдался один раз в первом прогоне Z1 (старая схема гонки). Причина не записана; итоговый recover — MANUAL, байты по правилу. Не воспроизвёлся в 228 последующих конкурентных вызовах (40 + 40 + 48 в Z1 и его повторе старой схемы, 100 в пробе конкуренции, включая код 165). Не разрушающий; отмечен честно.
7. **Хвосты прежних этапов без изменений:**
   - legacy CLI `restore_microtask` может вернуть BACKUP_VERIFIED после ACTIVE — правило тогда строже, безопасно (WA4-R);
   - `set_plan` без проверки статусов — экзотическая гонка с R1, существовала и для RC-6;
   - риски Repair #4 / #4A (переснятие W1, повторное исполнение после RETRY, ремонт испорченного restore point).

---

## 11. Связь с прежними Repair и документационная непрерывность

| Шаг | Исполнитель | Ключевое | Итог проверки |
| --- | --- | --- | --- |
| CHATGPT-WA-008 / RC-6 + Repair #1 | ChatGPT | RecoveryCoordinator, B1–B5 | Claude: FAIL (RC6-VERIFY), FAIL (RC6-REVERIFY) |
| CLAUDE-WA-009 / Repair #2 + #2A | Claude | R1 / R2 / R3, F-D, F-E; CAS state machine | ChatGPT по 162: FAIL |
| CLAUDE-WA-010 / Repair #3 | Claude | гейт F-C, F-B, R3 confirm, F4 / F5, C1, поздний ABORT | ChatGPT по 163: целевые PASS, 2 блокера |
| CLAUDE-WA-011 / Repair #4 | Claude | прерванная подготовка W1/W2, политика settlement | ChatGPT по 164: основное PASS, static finding → #4A |
| CLAUDE-WA-012 / Repair #4A | Claude | PREPARING / «до исполнения» × принятое решение | ChatGPT по 165: основное PASS статически, static finding → этот #4B |
| **CLAUDE-WA-013 / Repair #4B** | Claude | откат только исполнявшегося текущего этапа (RC-4 + RC-6), факт статуса в settlement | **RESULT READY — ждёт проверки** |

**Влияние на прежние Repair:**
- #4A — ABORT до исполнения по-прежнему достижим и закрепляется в RR (инвариант 5); ручная граница ADOPT / ROLLBACK / RETRY сохранена; добавлено только «такая microtask никогда не откатывается».
- #4 — W1/W2 reconcile и `SETTLEMENT_ADMITS` не тронуты; отказ RC-4 во втором откате (`RECOVERY_ALREADY_SETTLED`) проверяется раньше нового правила.
- #3 — гейт F-C, поздний ABORT, VERIFIED-поглощение не менялись.
- #2 / #2A — R1 стал строже (теперь и в RC-4); RR до APPLY сохранён.

### DOCUMENTATION IMPACT CHECK (регламент 18)

```text
DOC IMPACT: YES
CURRENT STATE IMPACT: YES — только после independent PASS (до него статусы не меняются)
ARCHITECTURE IMPACT: YES — правило отката (RC-4 + RC-6) и новый факт settlement (см. delta 23)
CONTEXT LIBRARY IMPACT: NO
REGISTRY / ROUTING IMPACT: NO (новых документов нет; ответственность документов не меняется)
NEW DOCUMENT REQUIRED: NO
CANONICAL OWNER: 23 (архитектура); 24 (статус этапов); 25 (профильная история)
AFFECTED DOCUMENTS: 23, 24, 25, 01, 05, 06, 001, 000 (глобальный); 08 — без изменений от #4B; 000_Задачи Claude (сделано сейчас)
CONTRADICTION CHECK: REQUIRED — устаревшие CURRENT-утверждения (ниже, как в отчёте #4A §9, плюс RC-4)
LOSS CHECK: NOT APPLICABLE (ничего не удалялось); записи Repair #1…#4A в карточке сохранены
```

### Documentation delta (выполняет verifier / координатор после PASS; по решению пользователя — ChatGPT, вместе с историей WEB_03, RC-5 / RC-6 и протоколом GitHub-first / Desktop-for-actions)

**Сверено сейчас (факт ≠ документ):**
- `23` §22 п. 35 (RC-4) не говорит, что RC-4 проверяет жизненный цикл; R1 описан только для RC-6 / Projection; RC-5 / RC-6 в `23` почти не отражены.
- `24` строка 9 и таблица §9 (стр. ~809 / 812): «RC-6 = ACTIVE по CHATGPT-WA-008», «RC-4 next / not started» — устарело. Exit-proof RC-4 (стр. 56) не упоминает R1 / «только исполнявшийся этап».
- `25`, `05`, `06`, `001` заканчиваются на RC-4 DONE / VERIFIED; RC-5 и цепочки RC-6 нет (в `25` последняя строка — «RC-5 not started»).
- `01` строка Web Alarm: «RC-4 следующий, ещё не запущен» — устарело.
- Глобальный `000` БЛОК 1: «CHATGPT-WA-008 / RC-6 — REPAIR #1 — RESULT READY» — устарело.
- `08` — Repair #4B его не затрагивает (протокол GitHub-first / Desktop-for-actions — отдельное решение пользователя).

**Что должно появиться после PASS RC-6 (сверх delta отчёта #4A §9):**
- `23`:
  - §10–§11 / §22 — «rollback восстанавливает только текущий этап, который был ACTIVE; VERIFIED и не текущие этапы, а также microtask без исполнения не откатываются; правило одно для RC-4 (включая прямой API) и RC-6»;
  - п. 35 дополнить: RC-4 сам проверяет жизненный цикл при создании сессии и перед каждым destructive apply;
  - добавить: settlement хранит статус microtask, на котором был решён; ABORT, закреплённый до первого ACTIVE, делает microtask навсегда неоткатываемой; ABORT settlement старого формата — откат не доказан → ручной разбор.
- `24` — exit-proof RC-4 / RC-6 дополнить тем же; RC-6 = DONE / VERIFIED только после PASS.
- `25` / `05` / `06` / `001` — запись CLAUDE-WA-013 / Repair #4B в цепочке RC-6 (append-only); в `25` отдельно отметить пробел RC-4 со времён commit 154 (откат VERIFIED-этапа и microtask без исполнения через прямой API), закрытый здесь.
- `01`, глобальный `000` — как в #4A §9.

**Сделано сейчас в пределах полномочий исполнителя:** карточка `000_Задачи Claude` (БЛОК 2 и БЛОК 3 — отдельные записи FOLLOW-UP, прежние сохранены), task session (`task_statement.md`, `baseline.md`, `session.jsonl`, `context.md`, `history.md`, пробы, этот отчёт). Ни один статус не объявлен DONE / VERIFIED.

---

## 12. Что требуется для independent PASS RC-6 и блокеры перед WA4-E

- Проверка ChatGPT по новому коммиту: этот отчёт, `test_web_alarm_recovery_coordinator_repair4b.py`, правки фикстур (§4.4), регрессия Repair #2…#4A.
- Отдельно оценить семантику:
  - «откат только исполнявшегося текущего этапа» теперь и в RC-4 (меняет принятое поведение RC-4: раньше он откатывал microtask без исполнения и VERIFIED-этап);
  - новое поле settlement (схема контракта, отсутствие downgrade).
- DECISION по §10 п. 1 (активация при принятом ABORT) — не блокер безопасности Repair #4B, но решение нужно до WA4-E, если требуется authority-точность, а не только «был ACTIVE».

**Блокеры перед WA4-E внутри scope RC-6** — по оценке исполнителя, нет: путь отката microtask без исполнения закрыт в обоих исполнителях. §10 п. 1 — вопрос дизайна (вне scope). Решение за независимой проверкой.

## 13. Рекомендация

**RC-6 готов к независимой проверке.**
- Static finding verifier подтверждён экспериментом и закрыт.
- Найден и закрыт более старый пробел прямого входа RC-4: microtask без исполнения и VERIFIED / не текущий этап.
- Откат действительно исполнявшегося этапа сохранён.
- Инварианты Repair #2…#4A не нарушены.

**NEXT:** commit / push — пользователем → независимая GitHub-only проверка ChatGPT → только после PASS: синхронизация постоянной документации (ChatGPT) и решение о WA4-E. **WA4-E NOT STARTED.**
