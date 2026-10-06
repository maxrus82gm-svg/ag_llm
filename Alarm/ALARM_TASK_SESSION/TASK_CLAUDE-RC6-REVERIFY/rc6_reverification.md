# RC-6 RE-VERIFICATION AFTER REPAIR #1 — CHATGPT-WA-008

**Verifier:** Claude Opus 5.5 (Claude Code, desktop), независимо от исполнителя (ChatGPT / GPT-5.6 Sol).
**Дата:** 2026-10-06.
**Вердикт: VERIFICATION FAILED / REPAIR REQUIRED.** Исходные блокеры B1, B2, B4 и B5 в проверенных сценариях устранены. Но найдено три новых блокера (§5):
- **R1** — `recover` физически откатывает уже VERIFIED-этап;
- **R2** — `recover` бесконечно переключает статус microtask, если у двух её операций settlement разных типов;
- **R3** — READY возвращается не для той microtask, которую доказывали (узкая гонка).

**WA4-E НЕ начинать.** Permanent closeout, история и глобальный router не менялись: по постановке их обновляют только при PASS.

---

## 1. Фактический baseline

| Факт | Значение |
| --- | --- |
| GitHub `main` (`git ls-remote origin`) | `07c4667dd131b34d970e78488a68c2107913de85` (commit 160) |
| Локальный HEAD | тот же — совпадает с GitHub |
| Проверяемый commit | **160** — Repair #1 (база repair: commit 159 `26111c9…`) |
| Dirty tree на старте | только `Документация/000_Задачи Claude.md` (постановка в БЛОКЕ 1) |
| Runtime-код и тесты | `git diff HEAD -- web_alarm test_web_alarm_*.py` пусто, дрейфа нет |
| Хеши файлов | `baseline.md` |

В ходе проверки Obsidian сам изменил `.obsidian/workspace.json`. Я его не трогал.

---

## 2. Что изменил Repair #1 (diff 159 → 160, прочитан полностью)

- **`rollback_service.py` (RC-4), +39.**
  - Правило `touched` вынесено в `rollback_own_effects_started()` без изменения смысла.
  - Добавлены чистые предикаты `rollback_needs_rc4_finalize()` и `rollback_resume_via_rc4_required()`, а в `rollback_session_facts` — три новых поля.
  - Разрушительный жизненный цикл RC-4 не изменился. Наборы RC-4 41 + 2 проходят.
- **`projection.py` (RC-5), +194.**
  - Settlement становится историей, когда административная часть завершена: ADOPT — microtask DONE/VERIFIED и нет собственного claim; ABORT/ROLLBACK — RECOVERY_REQUIRED и нет claim.
  - У каждой операции есть `microtask_status` её собственной microtask.
  - Новые состояния для ABORT/SUPERSEDED: `*_RELEASE_PENDING`, `*_NEEDS_FINALIZE`, `*_UNSAFE_FINAL`, `*_AFTER_EFFECTS`.
  - Открытую сессию с собственными эффектами больше не объявляют stale.
  - Blocker `RESTORE_POINT_NOT_VERIFIED` для ACTIVE (закрывает мой F4 из RC-5).
  - Честный lifecycle NEXT после ABORT/ROLLBACK settlement.
- **`recovery_coordinator.py` (RC-6), +428.**
  - Решения принимаются по `view["microtask_status"]`.
  - Preflight статуса microtask перед записью settlement ADOPT/ABORT/ROLLBACK.
  - Чистые защищённые READY-proof: `_prove_retry_ready` (claims RC-3 по набору целей резолюции) и `_prove_normal_ready` (все цели restore point, любой активный владелец = блок).
  - Release-only для сессий VERIFIED без release, finalize-only для DRIFTED, PARTIAL/FAILED/after-effects → BLOCKED.

**Проверка запретов §23 постановки:**
- свежесть резолюций Resolver не ослаблена — RC-4 после собственных эффектов по-прежнему проверяет `_authority`, ревизию операции, fingerprint запроса и restore point;
- обхода RC-3 claims нет;
- второго механизма отката нет;
- новых глобальных переходов state machine нет;
- обычной физической мутации нет;
- небезопасного auto-close нет (n16, n17);
- projection не стала путём записи (n11: повторный READY не пишет ничего);
- глобального серверного lock нет.

Нарушение правила «не изменил глобальный lifecycle молча» найдено косвенно — это R1 и R2 ниже.

---

## 3. Проверки (запущены независимо)

| Набор | Результат |
| --- | --- |
| RC-6 Coordinator / adversarial / concurrency | 15 / 16 / 6 — OK |
| Repair #1 (`…_repair1.py`) | **21/21 OK** |
| Projection / + concurrency | 47 / 3 — OK |
| Resolver / + concurrency | 24 / 1 — OK |
| RC-3 claims / + concurrency | 18 / 2 — OK |
| RC-4 rollback / + concurrency | 41 / 2 — OK |
| State machine / Server / CLI | 6 / 12 / 7 — OK |
| Итого фокусно | **221/221 OK** (`focused_regression.txt`) |
| **Полный** `python -B -m unittest` по всем 41 `test_web_alarm_*.py` | **439 OK, skip 1** (`full_regression.txt`) |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK |
| Исходные probe `TASK_CLAUDE-RC6-VERIFY/probes/` без изменений | `rc6_probes.py` exit 0, `rc6_probe_interrupted.py` exit 0 (`probes/original_*_output.txt`) |
| Новые probe верификатора | 23 сценария — `probes/reverify_probes.py`, вывод `probes/reverify_probes_output.txt` |
| Живое storage (только чтение) | до: 136 файлов / 41 каталог, `07298919…5920` / `2269f667…3a61`; после всех прогонов — то же. Read-only `recover` на WA-3.6 / WA-3.7 (страховка: `_perform` падает) → `TASK_COMPLETED`, 0 шагов, хеш не изменился (`probes/live_readonly_probe_output.txt`) |

Цифры исполнителя (439 / 21) совпали. Штатные тесты зелёные, но новые блокеры найдены только собственными probe.

---

## 4. Матрица B1–B5, F1/F2

| Пункт | Итог | Доказательство |
| --- | --- | --- |
| **B1** settlement не захватывает фокус | **исходный сценарий FIXED**; расширение из §5 постановки («несколько historical settlements разных operations») — **FAIL → R2** | P1, P1b, n04, n09 — OK; n13 / n13b — дефект |
| **B2** чужой владелец перед READY | **FIXED** для постоянного состояния; остаточная гонка идентичности READY — **R3** | P4, n05 (псевдоним `ONE.TXT`), n06 (владелец ROLLBACK), concurrency-тесты исполнителя; n01 / n01b — дефект |
| **B3** microtask операции ≠ текущая | **ЧАСТИЧНО**: RETRY / ABORT / ADOPT — FIXED (без записи до preflight); **ROLLBACK — НЕ исправлен, разрушительно → R1** | P5, P6, n03 — OK; n19 — дефект |
| **B4** перезапуск RC-4 | **FIXED** | исходные 3 прерывания (exit 18/17/17) → resume, 2 restore events, без двойной записи; n17 (свой `os._exit` между DRIFTED и finalize) → PARTIAL один раз, claims сохранены; P14, n10 → release-only |
| **B5** restore point | **FIXED** | P2, n07 (нет snapshot, битый manifest, подмена до proof, подмена после proof), n07b (подмена внутри RETRY-proof) — ни одного READY |
| **F1** ABORT / RECOVERY_REQUIRED | **формулировка правдива**, но **механически не обеспечена** → FINDING F-C | n08, n12, n14 |
| **F2** PARTIAL / FAILED | **SAFE** | n16 (PARTIAL, затем ABORT → BLOCKED, 3 claims сохранены), n17, тесты repair, ревью `_classify` |

---

## 5. Блокеры

### R1 — `recover` физически откатывает уже VERIFIED-этап (недоделанный класс B3, разрушительный)

**Воспроизведение (`probes/reverify_probes.py n19`):**
1. Подготовка, как в B3-тестах исполнителя:
   - m1 объявляет `a.txt` edit, `b.txt` delete, `c.txt` delete;
   - `op_1` STARTED, `a.txt` записан, `b.txt` удалён;
   - затем m1 DONE → VERIFIED (state machine это позволяет), m2 ACTIVE, `two.txt` изменён работой m2.
2. Reconciliation для `op_1` даёт `ROLLBACK_CURRENT_MICROTASK (PARTIAL_KNOWN_STATE)`, хотя m1 не текущая. Resolver принимает ROLLBACK.
3. Один `recover` → шаги `PREPARE_ROLLBACK`, `APPLY_ROLLBACK`:
   - **`a.txt` возвращён к `a-before`, `b.txt` восстановлен** — проверенная работа m1 уничтожена;
   - затем `SETTLE_ROLLBACK` → FAIL_CLOSED «microtask m1 is VERIFIED».

**Нарушено:**
- инвариант 5 и §11 документа `23` («VERIFIED-этапы не откатываются из-за ошибки текущего этапа»);
- правило B3 постановки («Recovery action может управлять lifecycle только operation.microtask_id; историческая операция не может стать исполнимой из-за более поздней ACTIVE»);
- «no silent rollback selection».

**Причина:**
- `_classify`: `ROLLBACK_ACCEPTED` → `PREPARE_ROLLBACK`, а `ROLLBACK_PREPARED/PRESERVED/AUTHORIZED` → `APPLY_ROLLBACK`. Ни `view["microtask_status"]`, ни текущую позицию эти ветки не проверяют.
- Preflight статуса microtask для ROLLBACK есть только в `_settle_verified_rollback`, то есть **после** разрушительного `RollbackService.apply`.
- RC-4 и Resolver статус microtask не проверяют, а reconciliation называет нетекущую microtask «current».
- Repair #1 добавил preflight для RETRY, ABORT и ADOPT, но не для ROLLBACK.

**Состояние после сбоя:**
- rollback-сессия VERIFIED;
- файлы m1 в pre-state;
- m1 VERIFIED, m2 ACTIVE;
- settlement нет, каждый следующий `recover` → FAIL_CLOSED.

**Влияние на RC-4/RC-5:** сам RC-4 не изменился. Дефект в том, что RC-6 автоматически запускает RC-4 там, где этого делать нельзя.

**Почему тесты не поймали:** B3-тесты repair покрывают только RETRY и ABORT, а в моей первой проверке B3 был сформулирован тоже только для RETRY/ABORT. Дефект был и в исходном RC-6 — я его тогда не нашёл.

**Минимальный repair scope:**
- до `PREPARE_ROLLBACK` и до первого `APPLY_ROLLBACK` сессии без собственных эффектов, под теми же блокировками, доказать:
  - microtask операции — текущая;
  - её статус в допустимом наборе (тот же `allowed_from`, что у ROLLBACK settlement);
  - иначе `RECOVERY_BLOCKED` без записи;
- regression-тесты: n19 и вариант с уже PREPARED/PRESERVED-сессией.

Отдельно (вне RC-6, нужно решение): защита в глубину — RC-4 prepare/apply и reconciliation не должны считать нетекущую microtask «current».

### R2 — две операции одной microtask с settlement разных типов: `recover` бесконечно переключает её статус

**Воспроизведение (`n13`, `n13b`):**
- **n13:**
  - ADOPT `op_a` → m1 DONE;
  - в m1 начата `op_b` (`OperationStore.begin` разрешает это для DONE-microtask), затем ABORT `op_b` (ABORT не требует решения reconciliation);
  - `recover` → `SETTLE_ABORT` и затем 7 × `FINISH_SETTLEMENT`: m1 переключается DONE ↔ RECOVERY_REQUIRED, каждое переключение — запись authoritative-статуса;
  - итог FAIL_CLOSED «step budget exhausted»;
  - каждый следующий `recover` снова делает 8 переключений;
  - m1 остаётся **DONE**, хотя `op_b` получила ABORT. Обычная state machine переводит её в VERIFIED, после чего `recover` навсегда FAIL_CLOSED.
- **n13b:**
  - ABORT `op_a` → m1 RECOVERY_REQUIRED;
  - новая `op_b` записана, ADOPT принят;
  - `recover` переводит **ABORT-microtask в DONE**, затем переключения продолжаются (budget 3 → m1: DONE, затем RECOVERY_REQUIRED).

**Нарушено:**
- §17 постановки — историческое settlement снова захватывает операционное внимание и управляет записями;
- идемпотентность повторного `recover`;
- «no hidden second authority» — координатор сам пишет противоречивые факты lifecycle.

**Причина:**
- в projection (`_operation_recovery`) условие «административная часть завершена» считается для каждой операции отдельно, а статус microtask общий: ADOPT требует DONE/VERIFIED, ABORT/ROLLBACK — RECOVERY_REQUIRED;
- `_finish_settlement` разрешает и RECOVERY_REQUIRED→DONE (ADOPT), и DONE→RECOVERY_REQUIRED (ABORT).

**Минимальный repair scope:**
- если в одной microtask есть settlement с противоречащими требованиями к её статусу → ручная граница (`RECOVERY_BLOCKED` / `MANUAL_DECISION_REQUIRED`) **без единой записи**;
- ADOPT никогда не переводит в DONE microtask, у которой есть ABORT/ROLLBACK settlement другой операции;
- правило «ABORT/ROLLBACK сильнее ADOPT» — это уже решение по жизненному циклу (V15), его не нужно изобретать в repair;
- regression-тесты: n13, n13b.

### R3 — READY возвращается для microtask, по которой защищённая проверка не выполнялась (узкая гонка)

**Воспроизведение:**
- **n01:** in-process чередование;
- **n01b:** два **реальных процесса** с барьером сразу после proof.

Сценарий:
1. `two.txt` принадлежит чужой TASK ещё до вызова.
2. `recover` выполняет защищённый `_prove_normal_ready` для m1 и отпускает блокировки.
3. Другой процесс проверяет m1 и активирует m2 на `two.txt`.
4. `recover` строит свежую projection, снова классифицирует её как `NORMAL_READY` и возвращает **`READY_FOR_EXECUTION` с текущей m2**.
5. Прямой защищённый proof для m2 → BLOCKED («two.txt owned by task_foreign»); следующий `recover` → RECOVERY_BLOCKED.

**Нарушено:**
- §14 постановки — нужно доказать точную microtask исполнения и отсутствие чужого владения;
- §15 — чужой владелец существовал во время последнего защищённого proof, но proof был про другую microtask.

Это **не** допустимая «поздняя гонка», при которой владелец появляется после proof той же идентичности.

**Причина:** `recover` сравнивает только **тип** proof (`after.get("proof") == proof`), а не его идентичность: microtask, restore point, операцию или резолюцию.

**Минимальный repair scope:**
- `_prove_*` возвращают идентичность (`microtask_id`, `restore_point_fingerprint`, для RETRY — `operation_id` + `resolution_id`);
- READY только если свежая projection указывает на ту же идентичность, иначе повторная классификация или proof;
- regression-тест: n01b.

Вероятность низкая, но это путь к READY без доказательства.

---

## 6. FINDINGS (не блокеры; для решения)

- **F-A — переход state machine без CAS ломает ABORT settlement (две реальные гонки: n02, n02b).**
  - `ServerStateMachine.transition` читает статус без блокировки, а потом записывает под `mutation_lock` вслепую.
  - Параллельная проверка DONE→VERIFIED затирает RECOVERY_REQUIRED, записанный ABORT settlement.
  - Итог: ABORT-microtask VERIFIED, `recover` навсегда FAIL_CLOSED.
  - Сам RC-6 корректен. Это давний F2 из RC-5 («переходы ServerStateMachine не атомарны»), теперь с конкретным последствием.
  - **Proposal:** CAS статуса под `mutation_lock` в `transition`, до WA4-E. Файл `state_machine.py` вне scope RC-6 → решение координатора.
- **F-B — TASK заклинивает навсегда (все варианты fail-closed без записи).**
  - Поздний ABORT по операции с ADOPT settlement (n03): Resolver принимает, `recover` → FAIL_CLOSED даже после VERIFIED m1 и ACTIVE m2; NEXT показывает фразу Resolver.
  - ABORT по операции VERIFIED-microtask (P6): то же самое.
  - Выхода нет ни в API, ни в state machine.
  - **Proposal:** Resolver отклоняет действия по операциям с settlement или в VERIFIED microtask, либо projection считает их историей с ручной границей. Связано с V15 → **DECISION**.
- **F-C — F1: формулировка правдива, но не обеспечена механически.**
  - После окончательного ABORT NEXT честно говорит «normal mutation is forbidden … explicit replan/lifecycle decision» и не обещает «новую операцию».
  - Resolver отклоняет RETRY, ROLLBACK и ADOPT; выходов из RECOVERY_REQUIRED в state machine нет.
  - Но `OperationStore.begin` + RC-3 `acquire` (ACQUIRED) + `mutation_boundary` (`mutation_authority = True`, `CAS_BASIS_HOLDS`) для новой операции в этой microtask проходят (n14). То же для DONE-microtask (n13).
  - Именно этот пробел делает достижимым R2.
  - **Вход для WA4-E:** исполнитель обязан требовать ACTIVE и подтверждённую идентичность READY. Нужна ли проверка жизненного цикла в `begin`/`acquire` (RC-1/RC-3) — **DECISION**.
- **F-D — инверсия порядка блокировок RC-6 ↔ RC-4 между разными TASK (n15, два реальных процесса).**
  - RC-6 (`_lock_manifest_targets`, `_lock_resolution_targets`) сортирует блокировки целей по physical key, RC-4 `_lock_targets` — по `target_hash`. Файлы блокировок общие.
  - Две TASK с ≥2 общими целями (READY-proof / ADOPT / re-arm против RC-4 apply) взаимно блокируются до таймаута 10 с; координатор → FAIL_CLOSED.
  - Безопасно (таймаут, без эффекта), но это настоящая инверсия.
  - Есть с исходного RC-6. **Самокоррекция:** в первом отчёте я ошибочно написал, что порядок везде один.
  - **Proposal:** в RC-6 сортировать по `target_hash(physical_key)` (2 строки).
- **F-E — RC-4 BLOCKED не останавливает цикл (n18).**
  - Сессия с собственным эффектом и испорченным restore point: RC-4 `apply` → BLOCKED `RESTORE_POINT_INVALID`.
  - Координатор повторяет `APPLY_ROLLBACK` до конца бюджета: 8 событий `ROLLBACK_BLOCKED` и 8 перезаписей сессии за вызов, итог FAIL_CLOSED «budget» вместо RECOVERY_BLOCKED с причиной RC-4.
  - Физических эффектов нет.
  - **Proposal:** результат RC-4 `BLOCKED`/`REJECTED` → стоп `RECOVERY_BLOCKED`.
- **F-F — `PROJECTION_VERSION` остался 1, хотя содержимое projection изменилось** (новые поля). Checkpoint, собранный кодом ≤159, кодом 160 валидируется как `INCONSISTENT` (выглядит как подмена). Fail-safe, лечится `checkpoint rebuild`. Мелочь.
- **F-G — перенесено без изменений:** неизвестная TASK → 409 (P18); после принятия этапов — обязательный перезапуск процессов WEB-02.

---

## 7. Подтверждено без замечаний

- Падение после settlement + micro, до release claim, затем проверка m1 и m2 ACTIVE → release-only, VERIFIED не откатывается, READY для m2 (n04).
- ABORT с собственным claim: падение до release → release-only, статус операции сохранён (STARTED), повтор без шагов (n08).
- ADOPT settlement против параллельной проверки в двух процессах — сходится (n09).
- Rollback VERIFIED с незавершённым release + более новый RETRY → только release, затем re-arm → READY; restore events 1 → 1 (n10).
- Повторный READY `recover` не пишет ни одного байта в storage и Workspace (n11).
- Владелец через псевдоним пути (`ONE.TXT`) и владелец типа ROLLBACK блокируют READY (n05, n06).
- Все варианты испорченного restore point, в том числе подмена внутри окна proof, не дают READY (n07, n07b).
- PARTIAL из-за внешнего дрейфа: ни без нового действия, ни после ABORT не закрывается и не снимает claims (n16).
- Свой `os._exit` между DRIFTED и finalize → finalize один раз, повторного restore нет, claims сохранены, RECOVERY_BLOCKED (n17).
- Порядок «TASK-lock → `mutation_lock` → блокировки целей» во всех путях RC-6 / closeout / RC-4 одинаковый, вложенных обратных захватов нет (кроме порядка между целями, F-D).

---

## 8. Почему вывод независим от отчёта исполнителя

- Факты взяты из `git ls-remote`, кода commit 160, diff 159→160 и собственных прогонов. `rc6_repair1_report.md`, `final_verification_v3.md` и `claude_probes_replay.txt` использованы только как карта изменений.
- Все наборы тестов и исходные probe запущены заново, результаты сохранены в этой папке. Цифры совпали, но блокеры это не опровергает.
- R1–R3 и F-A…F-E найдены **моими** новыми probe на временном storage, в том числе с реальными процессами (n01b, n02b, n09, n15) и `os._exit` (n17). Ни один из этих сценариев не покрыт тестами исполнителя.
- Живое storage — только чтение, со страховкой против любых шагов и сравнением хеша дерева до и после.

---

## 9. Рекомендованный следующий шаг

**RC-6 Repair #2** (исполнитель RC-6), минимальный scope:
1. R1 — проверка статуса microtask для ROLLBACK до PREPARE/APPLY;
2. R2 — противоречивые settlement одной microtask → ручная граница без записи;
3. R3 — READY привязан к идентичности proof;
4. дёшево и в том же scope: F-D (порядок по `target_hash`), F-E (BLOCKED от RC-4 = стоп).

Каждый пункт — с regression-тестом; сценарии n19, n13, n13b, n01b, n15, n18 можно взять как основу.

**Решения пользователя / координатора:**
- F-A (CAS в state machine, вне файлов RC-6);
- F-B / F-C (жизненный цикл после settlement и его механическое обеспечение — V15).

Затем повторная независимая проверка.

**RC-6: VERIFICATION FAILED / REPAIR REQUIRED. WA4-E NOT STARTED.**
