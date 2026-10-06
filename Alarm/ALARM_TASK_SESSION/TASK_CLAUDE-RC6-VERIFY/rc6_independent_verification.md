# RC-6 INDEPENDENT VERIFICATION — CHATGPT-WA-008 (Project-level Recovery Closure)

**Verifier:** Claude Opus 5.5 (Claude Code, desktop), независимо от исполнителя (ChatGPT / GPT-5.6 Sol).
**Дата:** 2026-10-06.
**Вердикт: VERIFICATION FAILED / REPAIR REQUIRED.** Найдено 5 воспроизводимых блокеров (§4). **WA4-E НЕ начинать.** Permanent closeout / history и глобальный router verifier не обновлял: это делается только после PASS.

---

## 1. Фактический baseline

| Факт | Значение |
| --- | --- |
| GitHub `main` (`git ls-remote origin`) | `5d40e496b7443122725f76df2fcff995c99a26ab` |
| Локальный HEAD | `5d40e496…` (commit 158) — совпадает с GitHub |
| Проверяемый commit | **158** — последний commit пользователя с RC-6 (M1 в 157, M2/M3 в 158) |
| Dirty tree | только `.obsidian/workspace.json` и `000_Задачи Claude.md` (БЛОК 1 этой проверки) |
| Runtime-код и тесты | `git diff --quiet HEAD -- web_alarm test_web_alarm_*.py` → совпадают с HEAD |

Модули RC-2/3/4 (`resolver_service`, `target_claim_service`, `rollback_service`) с RC-5 не менялись. RC-6 затронул `recovery_coordinator.py` (новый), `operation_store` / `operation_contract` / `models` (settlement), `projection.py` (repair #1 RC-5 в commit 156 и правка RC-6 в 157), `task_store`, `server`, `cli`, `__init__`.

**Статус RC-5 по каноническим документам** (`24`): «RESULT READY, отдельная независимая приёмка отложена явным решением пользователя». RC-5 **не** DONE / VERIFIED. Блокер B4 ниже частично лежит в логике projection из RC-5 repair #1.

---

## 2. Что проверено архитектурно (чтение кода, не отчёта)

- `RecoveryCoordinator.recover` — ограниченный цикл: `range(limit + 1)` → classify → не более `limit` шагов → иначе `FAIL_CLOSED / RECOVERY_STEP_BUDGET_EXHAUSTED`. Бесконечного цикла нет.
- **Блокировки** везде в одном порядке: операционный TASK-lock → `TaskStore.mutation_lock` → target locks (общее пространство имён RC-3/RC-4) в порядке physical key. Обратного порядка ни в одном пути нет. Взаимоблокировок с RC-3 acquire, RC-4 apply и Closeout по ревью нет.
- **Settlement** (`_settle_recovery_locked`) — отдельный путь, который держат под блокировкой. Идемпотентен для того же action и resolution; CAS по `expected_revision`. ADOPT заново наблюдает основную цель (`_done_receipt`) и требует точного post; вторичные цели защищены пересчётом freshness под target locks.
- **RETRY re-arm** только переводит microtask в ACTIVE. Физической записи нет; авторитетность конкретного `resolution_id` проверяется дважды (до и после target locks).
- **ROLLBACK** использует только RC-4 prepare / apply / close. Второго механизма восстановления нет.
- **Server / CLI:** `POST /tasks/{id}/recover` и `task recover` валидируют `max_recovery_steps` (`0`, `true`, `"3"` → 400). Старая заглушка «advisory» удалена.

---

## 3. Проверки (запущены независимо)

| Набор | Результат |
| --- | --- |
| RC-6 focused + adversarial + concurrency (`test_web_alarm_recovery_coordinator*.py`) | **35/35 OK** |
| Resolver focused (+ concurrency) | 25/25 OK |
| RC-3 / RC-4 (claims, rollback + concurrency) | 63/63 OK |
| Server / CLI | 19/19 OK |
| Projection (+ concurrency) | 50/50 OK |
| **Полный** `python -B -m unittest test_web_alarm_*.py` | **416/416 OK** (skip 1) — `full_regression.txt` |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK |
| Живое storage, только чтение (`probes/rc6_live_probe.py`) | `recover` на WA-3.6 / WA-3.7 → `TASK_COMPLETED`, 0 шагов (страховка: `_perform` падает при любом шаге). 136 файлов / 41 каталог, хеш дерева до и после одинаковый (`2269f667…3a61`; только файлы — `07298919…5920`) |

**Штатные тесты зелёные, но покрывают не все границы.** Блокеры ниже найдены собственными probe и в существующих тестах не воспроизводятся.

---

## 4. Блокеры (воспроизведение → причина → минимальный repair scope)

Все воспроизведения запускаются на временном storage: `probes/rc6_probes.py` (вывод — `probes/rc6_probes_output.txt`) и `probes/rc6_probe_interrupted.py` (вывод — `probes/rc6_probe_interrupted_output.txt`).

### B1 — settled-операция навсегда захватывает фокус: после обычного ADOPT → verify → следующая microtask `recover` всегда FAIL_CLOSED

**Воспроизведение (P1, P1b):**
1. m1 ACTIVE, `op_1` STARTED, эффект лёг, m1 → UNKNOWN; accepted ADOPT → `recover` → `READY_FOR_VERIFICATION`, m1 DONE. Пока всё верно.
2. Обычная state machine: m1 DONE → VERIFIED; m2 prepare → READY → ACTIVE.
3. Projection: `authority_source = recovery_settlement`, `recovery = ADOPT_SETTLED`. NEXT по-прежнему «finish/verify the microtask through normal verification» — застрял.
4. `recover` → **FAIL_CLOSED**: «FINISH_SETTLEMENT failed closed: microtask m1 is VERIFIED; cannot recovery-set it to DONE». Ожидалось `READY_FOR_EXECUTION` для m2.
5. Довести m2 до VERIFIED: closeout eligible = true, но `recover` всё равно FAIL_CLOSED вместо `TASK_READY_TO_CLOSE`.

**Причина:**
- (a) `projection._operation_recovery` возвращает `X_SETTLED`, пока авторитетная резолюция совпадает с settlement. После ADOPT / ABORT / ROLLBACK так остаётся всегда, поэтому settled-операция навсегда в `attention` и в фокусе.
- (b) `_classify` для `*_SETTLED` сравнивает `position.current_status` (lifecycle-current microtask, здесь m2) с ожидаемым статусом **microtask операции** (m1) и шлёт `FINISH_SETTLEMENT` в уже VERIFIED m1.

**Repair scope:**
- projection: settlement — история, а не вечное внимание. ADOPT_SETTLED, у которого microtask уже прошла DONE (VERIFIED), не должен быть фокусом и NEXT;
- coordinator: решения по settlement принимать по статусу microtask **самой операции** (`view["microtask_id"]`).
- Нужны regression-тесты полного пути ADOPT → verify → следующая microtask → closeout.

### B2 — ложный READY при повторе: чужой RC-3 владелец основной цели не мешает `READY_FOR_EXECUTION`

**Воспроизведение (P4):** accepted RETRY → `recover` (re-arm, READY) → другая TASK делает `acquire` на `one.txt` (ACQUIRED) → `recover` снова → **`READY_FOR_EXECUTION`**.

**Причина:** проверка чужого владения есть только в шаге `REARM_RETRY` (`_lock_resolution_targets`). Ветка `RETRY_ACCEPTED` + microtask уже ACTIVE смотрит только на claims своей TASK (`_unexpected_claims` по `projection.ownership`). Итог: одно и то же persistent-состояние даёт разный ответ в зависимости от того, был ли re-arm. Это противоречит «claim safe / false READY impossible» и заявлению исполнителя «RETRY блокируется чужим claim на любом target».

**Repair scope:** в ветке READY для RETRY (и, по смыслу, перед любым READY по resolution) чисто, без записи, проверять активные claims на affected target set резолюции → `RECOVERY_BLOCKED`.

### B3 — решения по microtask принимаются по lifecycle-current, а не по microtask операции: ложный READY и записанный «полу-settlement»

**Воспроизведение:**
- **P5:** m1 VERIFIED, но `op_1` (m1) остался STARTED; accepted RETRY для `op_1`; m2 ACTIVE → `recover` → **`READY_FOR_EXECUTION`**, фокус `op_1`. READY выдан на повторное исполнение операции уже VERIFIED-этапа на основании статуса m2.
- **P6:** та же ситуация с accepted ABORT → `recover#1` → FAIL_CLOSED. При этом **settlement ABORT уже записан** в операцию, а m1 остался VERIFIED. `recover#2` и все последующие → FAIL_CLOSED («FINISH_SETTLEMENT … cannot recovery-set it to RECOVERY_REQUIRED»). Вечный FAIL_CLOSED поверх наполовину применённого действия.

**Причина:**
- `_classify` использует `position["current_status"]` для решений об операции, у которой своя microtask;
- в `_settle_resolution` / `_settle_verified_rollback` допустимость перехода microtask (`_set_micro_locked`) проверяется **после** `_settle_recovery_locked`, который уже сохранил запись.

**Repair scope:**
- везде брать статус microtask операции;
- до любой записи доказать, что переход microtask допустим, иначе fail-closed без записи;
- явно определить поведение для операции в уже VERIFIED microtask: например, settlement без изменения microtask или ручной разбор.

### B4 — прерванный собственный RC-4 rollback принимается за «stale»: координатор бросает откат на полпути или блокируется вместо штатного resume RC-4

**Воспроизведение (`probes/rc6_probe_interrupted.py`):** accepted ROLLBACK, две цели WRITE_RESTORE и одна NOOP; RC-4 apply прерван реальным `os._exit`:

| Прерывание | Projection | `recover` | Итог |
| --- | --- | --- | --- |
| после первой восстановленной цели, до второй | `ROLLBACK_STALE_OPEN` | `CLOSE_ROLLBACK` → `ROLLBACK_CLOSED` → MANUAL | откат **брошен на полпути**: `b.txt` восстановлен, `a.txt` нет; ownership снят |
| внутри второй записи, запись легла | `ROLLBACK_STALE_IN_FLIGHT` | `RECOVERY_BLOCKED` | нужен ручной разбор |
| внутри второй записи, запись не легла | `ROLLBACK_STALE_IN_FLIGHT` | `RECOVERY_BLOCKED` | нужен ручной разбор |

RC-4 сам продолжает такие сессии: «modulo own receipts», цель в полёте сверяется по байтам. Это закреплено в RC-4, инвариант 35 `23`, тесты D / interrupted RC-4.

**Причина:** projection (RC-5 repair #1, `_operation_recovery`) объявляет открытую сессию stale по сырой свежести её резолюции. После собственных восстановлений эта свежесть **всегда** теряется — evidence меняет сам откат. Различия «до собственных эффектов / после» (как в `RollbackService._session_basis`) нет. RC-6 полагается на эту классификацию. Нарушены §17 постановки RC-6 (после meaningful phase fresh process продолжает из persistent facts) и пункт атаки 24.

**Repair scope:**
- в projection для открытой сессии **с собственными эффектами** (любая цель RESTORED / APPLYING / DRIFTED, статус APPLYING) состояние = `ROLLBACK_<status>`, а не STALE; staleness по сырому fingerprint — только до собственных эффектов, как в RC-4;
- coordinator → `APPLY_ROLLBACK`: RC-4 сам доказывает цели в полёте и всё остальное;
- то же для VERIFIED с незавершённым release (P14 сейчас идёт через «stale → close»: результат корректный, ярлык нет).

### B5 — ложный READY при испорченном restore point

**Воспроизведение (P2):** m1 ACTIVE штатно; испорчен snapshot m1 → projection `restore_point = NOT_VERIFIED` → `recover` → **`READY_FOR_EXECUTION`**.

**Причина:** ветка NORMAL / ACTIVE в `_classify` не проверяет `projection.restore_point`. Нарушен инвариант 4 `23` («нет подтверждённого snapshot — нет мутации»). `ready_for_execution: true` — это новый машиночитаемый контракт RC-6 для WA4-E; RC-3 `mutation_boundary` snapshot не проверяет. При RETRY до re-arm испорченный snapshot ловится через свежесть (P3 → `RESOLUTION_STALE`), а для обычной ACTIVE microtask — нет.

**Repair scope:** READY_FOR_EXECUTION только при `restore_point.status == VERIFIED` для той microtask, которая будет исполняться, иначе `RECOVERY_BLOCKED`. Нужен regression-тест.

---

## 5. Подтверждено независимо (без блокеров)

- Clean ACTIVE → READY без записи; unresolved STARTED → MANUAL, сервер сам ничего не выбирает (их тесты + ревью).
- RETRY: только re-arm, физической записи нет (P9: после ROLLBACK settlement свежий RETRY → re-arm → READY).
- Гонка «старый RETRY → новый ABORT»: авторитетность `resolution_id` перепроверяется под блокировками (ревью + их многопроцессный тест).
- Чужой claim на основной и вторичной цели при **первом** re-arm / ADOPT → блок (их тесты + ревью `_lock_resolution_targets`).
- Rollback: несколько открытых сессий → `RECOVERY_BLOCKED` без молчаливого выбора; superseded / stale с целью в полёте → блок; ABORT при открытой сессии → close / reconcile без продолжения разрушительной фазы.
- VERIFIED с прерванным release (P14) → claims сняты, повторного восстановления нет (restore events: 1).
- Повторы и гонки: settlement идемпотентен. Две параллельные попытки ADOPT (P8) — второй шаг fail-closed (`OPERATION_REVISION_CHANGED`), двойного эффекта нет.
- Corrupt checkpoint и stale Recovery Report не управляют `recover`; completed TASK → без записи; closeout-eligible не завершается молча (их тесты; в B1 есть исключение).
- Исчерпание бюджета шагов → FAIL_CLOSED, затем безопасный resume.

---

## 6. FINDINGS (не блокеры, для решения)

- **F1 — ABORT ведёт в тупик** (P7). После ABORT-settlement microtask = RECOVERY_REQUIRED, а у state machine нет выходов из этого статуса. Плюс B1: settled-операция навсегда в фокусе. TASK больше нельзя закрыть, а NEXT «manual review or a new operation» исполнить нечем. Это тот же открытый хвост V15 / F1 из RC-5 → **DECISION REQUIRED**: жизненный цикл после ABORT / ROLLBACK.
- **F2 — авто-close PARTIAL / FAILED / stale-сессий** снимает claims rollback с частично восстановленного набора целей **до** решения человека; RC-4 советует обратный порядок (сначала решение, потом close). Нужно явное policy-решение.
- **F3 — исключения вне перехваченного набора** (`TargetClaimStoreError`, `WorkspaceRegistryError`, `TargetIdentityError` из claims / registry) выходят из `recover` как есть, а не как `FAIL_CLOSED`-результат. Неизвестная TASK → 409 вместо 404. Мелочь.
- **F4 — самоотчёт по RC-5 (мой код):** lifecycle NEXT projection для ACTIVE при `restore_point = NOT_VERIFIED` говорит «perform scoped implementation». Это та же дыра, что B5, на уровне RC-5. Чинится вместе с B5.

---

## 7. Почему вывод независим от отчёта исполнителя

- Факты взяты из `git ls-remote`, кода commit 158 и собственных прогонов. Отчёт `rc6_report.md` использован только как карта утверждений.
- Все тестовые наборы запущены самостоятельно; цифры совпали с заявленными (416 / 35), но PASS штатных тестов блокеры не опровергает.
- Блокеры B1–B5 найдены **моими** probe на чистом временном storage, с реальным `os._exit` для прерываний. Ни один из этих сценариев не покрыт тестами исполнителя.
- Живое storage проверено со страховкой против любых шагов и сравнением хеша дерева.

---

## 8. Рекомендованный следующий шаг

Repair RC-6 (B1–B5, с regression-тестами на каждый) — исполнителю RC-6. Затем повторная независимая проверка.

Отдельно — решения пользователя / координатора по F1 (lifecycle после ABORT / ROLLBACK) и F2 (порядок close / decision).

Перевод router в `000_Задачи для агента.md` на REPAIR REQUIRED — на усмотрение координатора; verifier его не менял, по постановке router обновляется только при PASS.

**RC-6: VERIFICATION FAILED / REPAIR REQUIRED. WA4-E NOT STARTED.**
