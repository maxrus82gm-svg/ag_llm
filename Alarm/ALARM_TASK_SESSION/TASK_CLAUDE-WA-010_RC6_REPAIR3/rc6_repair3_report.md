# AGENT REPORT — CLAUDE-WA-010 / RC-6 Repair #3 / Final Safety Closure

- **Исполнитель:** Claude (Opus 5.5). Независимый verifier — ChatGPT по GitHub.
- **Даты:** 2026-10-07 — 2026-10-08.
- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.**
- **Baseline:** GitHub `main`, commit 162 = `2f1f8780367fd5a2a2c44d10182002197f64e9bb`. Полный набор на baseline — 475 OK, skip 1 (`baseline_full_regression.txt`). SHA-256 всех `web_alarm/*.py`, тестов и карточки — `baseline.md`, копии — `safety_copies/`.

---

## 1. Итог в одном абзаце

Все пять finding подтверждены на 162 и закрыты. Добавлен один общий модуль правил `web_alarm/microtask_gate.py`.
- **F-C:** серверная mutation authority теперь проходит тот же lifecycle/recovery gate, что и READY в RC-6. Пока authority выдана, жизненный цикл TASK заморожен.
- **F-B:** VERIFIED допускается только при закрытом recovery всех операций microtask. Решение, принятое после VERIFIED, либо поглощается им административно (ADOPT/ABORT), либо остаётся явной ручной границей (ROLLBACK/RETRY), которую закрывает явный ABORT.
- **R3:** READY выдаётся, только если повторный вывод proof под теми же блокировками совпал полностью.
- **F4:** окно при краше активации оказалось допустимым восстановимым состоянием; это доказано тестом, а активация дополнительно усилена.
- **F5:** блокировка restore point стала проверкой и записью под одной блокировкой.

Попутно найдены и исправлены два небольших связанных дефекта:
- **C1** — ABORT по FAILED/VERIFIED-операции давал вечный FAIL_CLOSED;
- **n03** — поздний ABORT поверх существующего settlement тоже давал вечный FAIL_CLOSED.

Одно дополнительное finding (краш при подготовке restore point) вынесено отдельно, без исправления: оно в WA-1, требует решения и на безопасность не влияет.

---

## 2. Воспроизведение на baseline 162

Проба `probes/repro_findings.py`, временное storage; вывод — `probes/repro_findings_baseline.txt`, после Repair #3 — `probes/repro_findings_after.txt`.

| ID | Сценарий | 162 | После Repair #3 |
| --- | --- | --- | --- |
| F1a | новая операция в microtask, ставшей RECOVERY_REQUIRED после ABORT: `begin → acquire → authorize` | **AUTHORIZED / CAS_BASIS_HOLDS** | DENIED / MICROTASK_NOT_ACTIVE |
| F1b | старая соседняя операция (claim до ABORT) | **AUTHORIZED** | DENIED / MICROTASK_NOT_ACTIVE |
| F1c | соседняя операция, пока принятый ABORT ещё не settled (microtask ещё ACTIVE) | **AUTHORIZED** | DENIED / MICROTASK_RECOVERY_REQUIRED |
| F1d | новая операция в VERIFIED microtask | **AUTHORIZED** | DENIED / MICROTASK_NOT_ACTIVE |
| F2a | принятый ABORT → VERIFIED → settlement | VERIFIED принят; `recover` ×3 = **FAIL_CLOSED** | VERIFIED отклонён; settlement → RECOVERY_REQUIRED |
| F2b | VERIFIED, затем ABORT принят позже | `recover` ×3 = **FAIL_CLOSED** | ABORT settled административно, m1 VERIFIED |
| F3 | после proof переписаны метаданные restore point (`manifest.json` и его id/updated_at не тронуты, чистая проверка проходит) | **READY с proof `7abac391…` при фактическом `9e91d6ef…`** | READY только для повторно доказанного basis (proof = факт) |
| F4 | краш процесса между записью указателя плана и статуса ACTIVE | указатель CORROBORATED, блокеров нет, повторная активация проходит — **состояние уже восстановимо** | то же (доказано тестом) + усиление |
| F5 | устаревшая и неудачная проверка snapshot против microtask, которая уже ушла вперёд | **microtask VERIFIED + manifest BLOCKED_PREPARE** | manifest остаётся VERIFIED |
| C1 | принятый ABORT по FAILED-операции | `recover` ×2 = **FAIL_CLOSED** (вечно) | settlement ABORT, microtask → RECOVERY_REQUIRED |

Поздний ABORT поверх ADOPT settlement (n03) воспроизведён пробой повторной проверки `TASK_CLAUDE-RC6-REVERIFY/probes/reverify_probes.py`. На 162 `recover` даёт вечный FAIL_CLOSED («already has recovery settlement ADOPT; cannot settle it as ABORT»). После Repair #3 — `FINISH_SETTLEMENT` → RECOVERY_REQUIRED.

---

## 3. Root cause

- **F-C.** Authority в `TargetClaimService._cas` проверяла только операцию (claim, ревизию, контракт, `_eligibility`, байты цели). Состояние microtask и решения по соседним операциям не проверялись. Кроме того, `mutation_boundary` не держал блокировку жизненного цикла, и state machine мог сменить статус microtask во время уже выданной authority.
- **F-B.** Допуск DONE → VERIFIED ничего не знал о recovery. Проверка статуса (Repair #2A) шла под `mutation_lock`, а приём решения Resolver — под TASK-lock операций, поэтому они не были сериализованы. После VERIFIED любой settlement упирался в правило «settlement не трогает VERIFIED» и падал fail-closed без выхода.
- **R3.** `_proof_matches` сравнивал только поверхностные идентификаторы. `restore_point_fingerprint` и `target_set_fingerprint` в проверку свежести не входили. `source_fingerprint` покрывает манифест только как `(manifest_id, updated_at)`, а не содержимое записей и snapshot. Защищённое множество целей после блокировки повторно не сверялось.
- **F4.** Две записи (`plan.json`, затем microtask) атомарными быть не могут. Указатель плана по RC-5 не является источником истины, поэтому краш между записями оставляет корректное состояние «активация ещё не сделана». Отдельно была слабость: «все предыдущие VERIFIED» проверялось без блокировки.
- **F5.** `_block_restore_point` писал BLOCKED_PREPARE в manifest без условий и только потом пытался сделать CAS статуса microtask.
- **C1.** `_settle_recovery_locked` разрешал ABORT только из INTENT/STARTED/DONE/UNKNOWN, а Resolver принимает ABORT для операции в любом статусе.
- **n03.** У операции одно поле `recovery_settlement`, а Resolver после settlement может принять ABORT, который становится authority операции. Второй settlement запрещён, поэтому шаг падал навсегда.

---

## 4. Выбранная архитектурная семантика

Граф переходов state machine, набор статусов, модель действий Resolver и схемы записей **не менялись**.

### 4.1 Один gate для мутации — `microtask_gate.execution_refusal` (F-C)

Нормальная физическая мутация разрешена только при всех условиях:
- microtask **ACTIVE**;
- она текущий этап: все предыдущие в плане VERIFIED;
- у её операций нет disposition ABORT/ROLLBACK — ни settled, ни принятого, но ещё не settled, ни открытой сессии RC-4.

Если факты не читаются — отказ (fail-closed). Одно правило применяют:
- RC-3 `mutation_boundary` / `authorize`;
- RC-6 READY (NORMAL и RETRY);
- RC-6 RETRY re-arm (через `disposition_actions`).

`mutation_boundary` теперь держит блокировки в глобальном порядке: TASK-lock → `mutation_lock` → target-lock. Пока authority выдана, ни одна запись жизненного цикла этого TASK не проходит. Внутри boundary нельзя вызывать переходы жизненного цикла: WA4-E пишет файл, а жизненный цикл фиксирует после выхода.

Claim (владение) по-прежнему выдаётся. Это не authority, и разделение RC-3 сохранено.

### 4.2 F-B: VERIFIED — терминальная disposition

1. **Допуск.** `ServerStateMachine._admit_verified` под TASK-lock + `mutation_lock` строит каноническую projection и пишет VERIFIED через CAS в той же секции. Отказ, если у какой-либо операции microtask:
   - открыта судьба мутации (STARTED/UNKNOWN без settlement);
   - или recovery ещё имеет следствие для жизненного цикла: принятое действие, сессия RC-4, settlement в работе к RECOVERY_REQUIRED, `ROLLBACK_STAGE_PROTECTED`, противоречие.

   Не блокируют: только советы Resolver по закрытой операции (`*_REJECTED`, `RESOLUTION_STALE`) и административный остаток ADOPT (снятие claim). Так приём ABORT Resolver и VERIFIED одной microtask сериализованы: побеждает первое, второе видит результат.
2. **Решение, принятое после VERIFIED** (`effective_settlement_target`):
   - неразрушающий settlement (ADOPT, ABORT) по операции VERIFIED-microtask — административный: settlement записан, ownership снят, microtask остаётся VERIFIED. Физически этап измениться не мог: по 4.1 у операций не-ACTIVE microtask нет authority;
   - ROLLBACK VERIFIED-этапа не поглощается: R1 — `ROLLBACK_STAGE_PROTECTED`, а уже существующий ROLLBACK settlement — `SETTLEMENT_CONTRADICTION`;
   - ROLLBACK и RETRY по VERIFIED-этапу останавливаются на явной ручной границе. Детерминированный выход — явный ABORT: он поглощается, этап не трогается.
3. **Поздний ABORT поверх существующего settlement** (n03, `late_abort`):
   - запись операции и её settlement остаются неизменной историей;
   - ABORT считается в disposition microtask;
   - RC-6 завершает его через `FINISH_SETTLEMENT`: RECOVERY_REQUIRED, а для VERIFIED-этапа — поглощение;
   - состояние projection — `ABORT_OVER_SETTLEMENT`.

### 4.3 R3: READY = повторно доказанный basis

- После proof `recover` вызывает `_confirm_ready`: те же TASK + mutation + target locks, полный повторный вывод proof тем же кодом и финальная projection в той же секции.
- READY выдаётся, только если одновременно:
  - повторно выведенный proof **полностью равен** доказанному: fingerprint содержимого restore point, защищённое множество целей, статус и `updated_at` microtask, ревизия операции, resolution;
  - `source_fingerprint` равен basis той projection, что выбрала proof;
  - `_proof_matches` сверяет все поля proof, которые есть в projection.
- Внутри proof множество целей после блокировки сверяется с повторно прочитанным restore point / basis Resolver.
- Любое расхождение или исключение при подтверждении — новый проход классификации. READY для этого basis не выдаётся. Цикл ограничен.
- ABA, вернувшийся к тем же поверхностным значениям, ловится по `updated_at` и fingerprint содержимого. ABA, вернувшийся к идентичному содержимому, — тот же basis, и READY для него корректен.

### 4.4 Краш-согласованность

- **F4.** Порядок записей «указатель, затем статус» оставлен намеренно. После краша указатель стоит на microtask, которая ещё READY. Это не блокер: RC-5 считает указатель лишь подтверждением, и он совпадает с текущей по жизненному циклу microtask. NEXT — «transition to ACTIVE», повторная активация завершает её. Дополнительно `compare_and_set_microtask_status_locked(activate=True)` под блокировкой перепроверяет, что все предыдущие VERIFIED.
- **F5.** С `expected_status` (путь state machine) обе записи идут под `mutation_lock` и только если статус microtask всё ещё тот, на котором решала проверка. Устаревшая проверка restore point ушедшей вперёд microtask не трогает: чистая проверка всё равно продолжит показывать настоящую порчу. Краш между записью manifest и статуса оставляет manifest BLOCKED_PREPARE при прежнем статусе. Тогда restore point везде NOT_VERIFIED, authority нет, и следующий переход, которому он нужен, завершает блокировку.

---

## 5. Изменённые файлы

| Файл | Изменение |
| --- | --- |
| `web_alarm/microtask_gate.py` | **новый**: правила R2 перенесены сюда без изменений (projection реэкспортирует); `verified_absorbs`, `effective_settlement_target`, `authoritative_action`, `late_abort`, `disposition_actions`, `execution_refusal`, `verification_refusal` |
| `web_alarm/target_claim_service.py` | gate в `_cas`; `mutation_boundary` держит `mutation_lock`; docstring |
| `web_alarm/state_machine.py` | `_admit_verified` (допуск VERIFIED под блокировками с CAS), `_stale_reason`; docstring |
| `web_alarm/recovery_coordinator.py` | R3: `_manifest_target_set` / `_resolution_target_set`, `_normal_basis_locked` / `_retry_basis_locked`, `_confirm_ready`, полный `_proof_matches`, gate в proof; F-B: действующая цель settlement, поглощение VERIFIED, `ABORT_OVER_SETTLEMENT`; RETRY re-arm по правилу gate |
| `web_alarm/projection.py` | использует `microtask_gate`; действующая цель; `SETTLEMENT_CONTRADICTION` только с ROLLBACK; ветка `ABORT_OVER_SETTLEMENT`; docstring |
| `web_alarm/task_store.py` | `compare_and_set_microtask_status_locked`; активация перепроверяет предыдущие VERIFIED под блокировкой; семантика краша в docstring |
| `web_alarm/manifest_store.py` | `_block_restore_point`: проверка и запись под `mutation_lock` (путь state machine), `_write_blocked_manifest` |
| `web_alarm/operation_store.py` | C1: ABORT settlement для операции в любом статусе (ROLLBACK — прежнее ограничение) |
| `test_web_alarm_recovery_coordinator_repair3.py` | **новый**, 34 теста |
| 7 существующих тест-модулей | см. §6.2 |

---

## 6. Тесты

### 6.1 Новый модуль `test_web_alarm_recovery_coordinator_repair3.py` (34)

- **F-C (11):**
  - новая/старая/соседняя операция после ABORT, принятого или settled;
  - открытая сессия RC-4;
  - VERIFIED и ещё не ACTIVE microtask;
  - ACTIVE, но не текущий этап;
  - жизненный цикл заморожен, пока authority выдана (реальный процесс ждёт);
  - READY RC-6 и authority RC-3 согласованы;
  - RETRY READY / re-arm отклонён при отложенном ABORT соседа;
  - нечитаемые факты → отказ.
- **F-B + C1 + n03 (12):**
  - VERIFIED отклонён при принятом ABORT и при открытой судьбе операции;
  - поздний ABORT/ADOPT после VERIFIED поглощается;
  - ROLLBACK VERIFIED-этапа ждёт явного ABORT, который его закрывает;
  - гонка «VERIFIED держит блокировку ↔ приём ABORT» в обоих порядках (реальные процессы);
  - ABORT по FAILED-операции;
  - поздний ABORT поверх ADOPT / поверх ROLLBACK, вытесненного RETRY;
  - ABORT после ADOPT на VERIFIED-этапе;
  - чистые правила.
- **R3 (5):**
  - смена содержимого restore point при тех же поверхностных id;
  - ABA к тому же статусу;
  - чужой claim после proof;
  - полнота `_proof_matches` (NORMAL и RETRY).
- **Краш (6):**
  - F4: краш реального процесса между записями + повторная активация;
  - F4: перепроверка предыдущих VERIFIED под блокировкой;
  - F5: устаревшая неудачная проверка;
  - F5: актуальная неудачная проверка по-прежнему блокирует обе записи;
  - F5: краш реального процесса между записями + завершение следующим переходом;
  - окно краша не открывает мутацию.
- **Порядок блокировок (1):** boundary против чужого proof RC-6 на общей цели — без deadlock.

**Чувствительность** (`probes/sensitivity_pre_repair3.py` → `sensitivity_pre_repair3.txt`): на runtime 162 падают **28 из 34** тестов (`FAILED (failures=29, errors=1)`). Проходят на 162 (так и ожидалось):
- F4-краш — состояние было восстановимо и до Repair #3;
- F5 «актуальная порча блокирует» — неизменное поведение;
- порядок блокировок;
- позитивная согласованность RETRY READY;
- ABA к тому же статусу — его уже ловил `source_fingerprint` (`updated_at`).

### 6.2 Изменения существующих тестов

**Только фикстуры** (ожидания те же). Новое правило «authority только для ACTIVE microtask», и фикстуры получили это предусловие:
- `test_web_alarm_target_claims.py` — m1 ACTIVE в `setUp` и после `prepare`;
- `test_web_alarm_rollback.py` — `task_b` (чужой RC-3 писатель) ACTIVE;
- `test_web_alarm_rollback_concurrency.py` — задачи-конкуренты ACTIVE;
- `test_web_alarm_projection.py`, тест N — `task_other` ACTIVE.

`test_web_alarm_projection.py`, тест P/Q: операция переведена в DONE **до** VERIFIED, ожидания блокеров прежние.

**Фикстура «легаси-VERIFIED»** (VERIFIED при открытом recovery через слепой примитив хранения): state machine такое теперь отклоняет.
- `test_web_alarm_recovery_coordinator_repair2.py` — `legacy_verify` для фикстур R1;
- `test_web_alarm_recovery_coordinator_repair1.py` — `legacy_verify_m1` для B3.

Защита R1 / #2A остаётся, ожидания R1 прежние.

**Ожидания изменены сознательно — новая семантика F-B:**
- `repair1.test_b3_abort_verified_microtask_fails_before_persisting_settlement` → `…_settles_administratively_without_moving_it`. Раньше фиксировался вечный FAIL_CLOSED. Теперь ABORT settled полностью (без «полу-settlement»), M1 VERIFIED, READY — только для текущего этапа M2. Это вариант «settlement без изменения microtask», предложенный в B3 исходной проверки.
- `repair2.test_r2_abort_settled_microtask_found_verified_is_a_zero_write_contradiction` → `…_is_absorbed_without_writes`. Добавлен новый `…rollback_settlement_found_verified_stays_a_zero_write_contradiction`.
- `state_machine_cas` A1 → «верификация при ожидающем откате отклоняется, откат идёт». Добавлен `A1-legacy` с прежним ожиданием RECOVERY_BLOCKED.
- `state_machine_cas` A2: причина отказа — «stale transition» **или** «open recovery»; исход прежний.
- `SM_CHILD` в `state_machine_cas` ставит барьер и на `_admit_verified`: решение VERIFIED теперь принимается в заблокированной секции.

---

## 7. Проверки

| Набор | Результат |
| --- | --- |
| Baseline 162, полный набор | 475 OK, skip 1 (`baseline_full_regression.txt`) |
| Repair #3, новый модуль | **34/34 OK**; 5 повторов подряд OK |
| Чувствительность на 162 | 28 из 34 падают; 6 инвариантных/позитивных проходят (§6.1) |
| Фокусно, 21 модуль (Repair #3, CAS #2A, Repair #2/#1, RC-6 ×3, state machine, task store, manifest store, projection ×2, Resolver ×2, RC-3 ×2, RC-4 ×2, operation store, server, CLI) | **322/322 OK** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py`, 44 модуля | прогон 1 — **511 OK, skip 1**; прогон 2 — **511 OK, skip 1** (`full_regression_run1.txt`, `full_regression_run2.txt`). Редких падений Windows не было |
| Стресс-повторы гоночных модулей | **21/21 OK** (`stress_repeats.txt`): Repair #3 ×5, CAS ×3, Repair #2 ×3, RC-6 concurrency ×3, RC-3 concurrency ×3, projection concurrency ×2, RC-4 concurrency ×2 |
| Adversarial Repair #3 (`probes/repair3_adversarial.py 24`) | **4/4 OK**:<br>X1 — 24 раунда «VERIFIED ↔ ABORT» на реальных процессах со сдвигом; оба порядка встретились (13 / 11), исход всегда согласован, вечного FAIL_CLOSED нет;<br>X2 — authority держится, приём ABORT соседа и settlement RC-6 ждут (1,03 с), после — MICROTASK_NOT_ACTIVE;<br>X3 — отклонённый VERIFIED ничего не пишет;<br>X4 — 24 READY при постоянной смене чужих claim, все привязаны к своему basis |
| Воспроизведение (`probes/repro_findings.py`) | на 162 — 9 GAP (F1a–d, F2a/b, F3, F5, C1), F4 — восстановимо; после — 11/11 закрыто |
| Adversarial Repair #2 (`repair2_adversarial.py`) | 7 OK; a10 — фикстура VERIFIED при открытом recovery теперь отклоняется; для легаси-формы — `probes/a10_after_repair3.py`, **4/4 OK** |
| Adversarial #2A (`repair2a_adversarial.py`) | **5/5 OK** |
| Исходные пробы `TASK_CLAUDE-RC6-VERIFY` | exit 0 / exit 0 |
| Пробы повторной проверки | 18 OK; n02 / n03 / n19 — исключение на фикстуре (§10, п. 8); n15 — прежний артефакт барьера |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK для кода и тестов. До ротации карточки — только хвостовые пробелы в тексте постановки БЛОКА 1, после ротации — чисто (§12). Новые файлы — LF, без хвостовых пробелов |

---

## 8. Безопасность / живое storage

- Все пробы, тесты и гонки — только во временном storage / `tempfile`.
- Живое `%LOCALAPPDATA%\WebAlarmWorkspace` только читалось (`probes/live_storage_hash.py`).
- Файлы проекта вне репозитория не трогались. `.obsidian/*` и `22_Техническая информация.md` изменены не мной и не трогались.

| Живое storage | Файлов | Каталогов | SHA-256 (путь + содержимое) |
| --- | --- | --- | --- |
| до работы | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |
| после всех проверок | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |

Живое storage **не изменилось**. Схема хеша новая (`probes/live_storage_hash.py`), поэтому значение не сравнимо с хешем из отчёта #2A; количество файлов и каталогов (136 / 41) совпадает с ним.

---

## 9. Что закрыто

| Finding | Статус | Где доказано |
| --- | --- | --- |
| 1 F-C mutation authority после ABORT | **закрыт** | F1a–d; 11 тестов F-C; adversarial X2 |
| 2 F-B поздний ABORT против VERIFIED | **закрыт** (оба порядка + поздние ADOPT/ABORT/ROLLBACK/RETRY) | F2a/b; тесты гонки на реальных процессах; X1 (оба порядка, без вечного FAIL_CLOSED) |
| 3 R3 неполный proof basis | **закрыт** | F3; 5 тестов R3; X4 (READY под чужой сменой claim) |
| 4 краш активации | **подтверждено как допустимое восстановимое состояние** + усиление | тест F4 с реальным крашем |
| 5 блокировка restore point | **закрыт** (гонка и краш) | F5; 4 теста |
| C1 ABORT по FAILED/VERIFIED-операции | **найден и закрыт** | тест C1 |
| n03 поздний ABORT поверх settlement | **найден (ранее F-B(а)) и закрыт** | 3 теста; reverify n03 |

Сохранённые свойства Repair #2/#2A перепроверены их собственными модулями:
- R1 / R2 / R3 / F-D / F-E — `…repair2`, 25;
- CAS и RECOVERY_REQUIRED перед APPLY — `…state_machine_cas`, 13;
- adversarial-пробы Repair #2 и #2A.

---

## 10. Дополнительные findings и остаточные риски

1. **FINDING (новый, не исправлен) — краш при подготовке restore point (WA-1.4).** Проба `probes/finding_prepare_crash.py`. Краш после записи PREPARING (W1) или после публикации restore point до BACKUP_VERIFIED (W2) оставляет microtask в PREPARING:
   - выхода у PREPARING в state machine нет;
   - `prepare` разрешён только из PLANNED/BLOCKED_PREPARE;
   - RC-6 → NO_ACTION_REQUIRED;
   - мутации нет (gate F-C), то есть безопасно, но выход только ручной.

   **Proposal:** путь «возобновить подготовку» из PREPARING — проверить опубликованный restore point → BACKUP_VERIFIED, либо убрать stage и снять заново под CAS PREPARING. Это меняет предусловия подготовки жизненного цикла → **DECISION REQUIRED**. Отдельная небольшая задача до или на входе WA4-E.
2. **Остаточный риск — несколько settlement одной операции.** У операции одно поле `recovery_settlement`. Поздний ABORT теперь корректен. Поздний ADOPT/ROLLBACK поверх существующего settlement по-прежнему отклоняется на settlement (FAIL_CLOSED): например, ADOPT после RETRY, повторённого после ROLLBACK, — это будущий поток WA4-E. Жизненный цикл операции после отката с повтором нужно определить в дизайне WA4-E (история settlement).
3. **Целостность restore point не входит в gate RC-3.** Её доказывает READY в RC-6 (B5). WA4-E обязан получать READY перед boundary. Proposal для WA4-E: добавить чистую проверку restore point в boundary. Без неё сейчас — из-за цены (чтение snapshot на каждую выдачу authority) и влияния на фикстуры RC-3.
4. **Операцию VERIFIED-microtask всё ещё можно перевести INTENT → STARTED** (`OperationStore.transition`, RC-1). Физического эффекта быть не может: authority нет. Projection покажет RECONCILIATION_REQUIRED (ручное), выход — явный ABORT (поглощается).
5. **Фокус projection по активности.** Если RETRY одной операции свежее отложенного ABORT соседней, RC-6 сначала упрётся в отказ re-arm / gate (RECOVERY_BLOCKED, ручное) и не settled ABORT соседа. Безопасно, путь человека — ABORT.
6. **Legacy CLI WA-1** (`snapshot prepare` / `restore`) по-прежнему пишет статус вслепую — хвост **WA4-R**.
7. **Windows `os.replace` sharing violation** в старых гоночных тестах RC-4/RC-5 (FINDING из #2A). В этой сессии не проявилось: 2 полных прогона + стресс-повторы RC-4 concurrency, всё чисто. FINDING / proposal из #2A остаётся в силе.
8. **Устаревшие исторические пробы.** Пробы повторной проверки n02 / n19 и a10 из Repair #2 верифицируют m1 при открытом recovery. С Repair #3 state machine это отклоняет, и пробы завершаются исключением. Инварианты соблюдены: m1 не VERIFIED при ABORT; для легаси-формы — `probes/a10_after_repair3.py`, всё OK. Проба n03 тоже падает — уже в своём последнем шаге (VERIFIED из RECOVERY_REQUIRED). Её содержательная часть теперь проходит: `FINISH_SETTLEMENT` → RECOVERY_REQUIRED. n15 — прежний артефакт барьера, его заменил постоянный тест F-D. Исторические пробы не менялись.

---

## 11. Рекомендация

**RC-6 готов снова к независимой проверке.**
- Все пять finding постановки закрыты или (F4) доказаны тестом как допустимое восстановимое состояние.
- Два связанных дефекта (C1, n03) закрыты.
- Свойства Repair #2/#2A сохранены; полный набор, стресс-повторы и adversarial чисты.

До разрешения WA4-E verifier стоит отдельно оценить:
- семантику F-B (поглощение неразрушающих settlement после VERIFIED; ROLLBACK/RETRY остаются явной ручной границей);
- изменённые ожидания трёх тестов (§6.2);
- дополнительное FINDING про подготовку restore point (§10, п. 1) и остаточные риски п. 2–3 — они относятся к входу WA4-E, а не к RC-6.

**NEXT:** commit / push — пользователем, по регламенту → независимая проверка ChatGPT по GitHub → только после PASS RC-6 = DONE / VERIFIED → NEXT = WA4-E. **WA4-E NOT STARTED.**

---

## 12. Артефакты

- `baseline.md`, `baseline_full_regression.txt`, `safety_copies/` (web_alarm, тесты и карточка до работы)
- `focused_regression.txt`, `full_regression_run1.txt`, `full_regression_run2.txt`, `stress_repeats.txt`
- `probes/`:
  - `repro_findings.py` + `_baseline.txt` / `_after.txt`;
  - `sensitivity_pre_repair3.py` + `.txt`;
  - `repair3_adversarial.py` + `_output.txt`;
  - `a10_after_repair3.py` + `_output.txt`;
  - `finding_prepare_crash.py` + `_output.txt`;
  - `live_storage_hash.py`, `live_storage_before.txt` / `live_storage_after.txt`;
  - `original_*_after_r3.txt`, `reverify_probes_after_r3.txt`, `repair2_adversarial_after_r3.txt`, `repair2a_adversarial_after_r3.txt`.
- Ротация карточки: постановка дословно перенесена в БЛОК 2 (хвостовые пробелы сняты), результат записан в БЛОК 3, БЛОК 1 очищен. Записи Repair #2 сохранены следом: в `001` их нет.
