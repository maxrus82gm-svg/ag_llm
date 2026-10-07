# CLAUDE-WA-009 / RC-6 — REPAIR #2A: F-A CAS / lifecycle race closure

**Исполнитель:** Claude Opus 5.5. **Дата:** 2026-10-07. Продолжение Repair #2 (та же TASK).
**Статус всего Repair #2 (вместе с #2A):** **RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE / VERIFIED. Commit / push не выполнялись. **WA4-E NOT STARTED.** F-B и F-C не исправлялись.

---

## 1. Baseline

- HEAD = GitHub `main` = commit 161 `e551b91`.
- **Repair #2 не закоммичен**: #2A строится поверх незакоммиченного рабочего дерева Repair #2 (SHA файлов — `baseline.md`).
- Safety copies пяти изменяемых файлов — `safety_copies/`.
- Живое storage до: 136 файлов / 41 каталог, `07298919…5920` / `2269f667…3a61`.

---

## 2. Почему одного CAS мало для R1

Постановка описывает гонку «RC-6 проверил этап → state machine перевёл его в VERIFIED → RC-4 откатил VERIFIED-этап» и предлагает CAS в `transition`. Но эта гонка — **не устаревшая запись**:
- координатор проверил: m1 — текущий этап, DONE;
- state machine прочитал DONE;
- под `mutation_lock` статус по-прежнему DONE, поэтому CAS пропускает запись VERIFIED, и она законна;
- после этого RC-4 восстанавливает уже VERIFIED-этап.

CAS защищает только от записи поверх **изменившегося** статуса. Здесь статус не менялся, проверка и действие просто лежат в разных блокировках. Поэтому R1 закрыт двумя частями, обе без новых статусов и переходов:

1. **CAS всех переходов state machine** (§3): ни один переход, решённый по наблюдённому статусу, не перезапишет более новый.
2. **Отметка этапа до разрушительного шага** (§4): координатор в том же защищённом участке, где доказывает этап, переводит microtask в `RECOVERY_REQUIRED` — тот статус, который ROLLBACK settlement всё равно даёт после отката. Выходов из `RECOVERY_REQUIRED` у state machine нет, а устаревший `DONE → VERIFIED` теперь отклоняется по CAS. Пока RC-4 восстанавливает файлы, этап не может стать VERIFIED.

---

## 3. CAS переходов

- **`TaskStore.compare_and_set_microtask_status(task, mid, *, expected, status, activate=False)`** — новый примитив. Под существующим `mutation_lock` перечитывает статус; если он не входит в `expected`, ничего не пишет и бросает `MicrotaskStatusConflict` (подкласс `TaskStoreError`). При `activate` проверка «нет другой ACTIVE» и перенос указателя текущей microtask выполняются в той же блокировке (раньше указатель переносился отдельной записью до смены статуса).
- **`ServerStateMachine.transition(..., expected_status=None)`.**
  - Прочитанный статус — основание всех проверок, финальная запись идёт через CAS с этим основанием.
  - Конфликт превращается в обычный `TransitionRejected` с причиной «stale transition …»: тот же контракт, событие `MICROTASK_TRANSITION_REJECTED`, сервер отдаёт 409 `transition_rejected`.
  - Необязательный `expected_status` позволяет вызывающему закрепить своё более раннее наблюдение (повтор после обрыва, клиент после задержки).
  - Граф переходов (`_ALLOWED`) не менялся.
- **Snapshot-проверка внутри `transition`.** Если restore point испорчен, `verify_restore_point(active_only=True)` ставит microtask в BLOCKED_PREPARE. Раньше это была слепая запись; теперь CAS с основанием, прочитанным переходом, и никакой более новый статус она не затирает. Блокировка самого manifest (restore point действительно испорчен) не изменилась.
- **Подготовка через state machine.** `ServerStateMachine.prepare_microtask` передаёт в `manifest.prepare_microtask` статус, который сам проверил: старт PREPARING идёт CAS, и опоздавший дубль не откатит уже подготовленную или активированную microtask. Запись ошибки BLOCKED_PREPARE затрагивает только статусы подготовки (PLANNED / PREPARING / BLOCKED_PREPARE). Прямые вызовы `manifest.prepare_microtask` без `expected_status` (фикстуры, CLI WA-1) ведут себя как раньше — см. §8.
- **Сервер.** Endpoint перехода принимает необязательное `expected_status`: устаревшее значение → 409, неверное → 400.

**Все вызывающие `transition()` проверены.**
- В runtime вызов один — серверный endpoint `/microtasks/{id}/transition`. Новый отказ проходит по существующему пути `TransitionRejected` → 409; частичных эффектов нет: CAS — последний шаг до события и checkpoint, указатель активации внутри CAS.
- CLI, remote entry и UI `transition` не вызывают.
- RC-6 пишет статус собственным путём `set_microtask_status_locked` под `mutation_lock` с проверкой в том же участке — по сути это уже CAS.

---

## 4. Отметка этапа перед разрушительным откатом

`RecoveryCoordinator._rollback_stage_preflight` для `APPLY_ROLLBACK` в фазе восстановления (не release-only, не finalize, не под ABORT), под TASK-lock + `mutation_lock`:
1. проверяет этап (R1) — теперь **внутри** блокировок;
2. если статус microtask не из `_TO_RECOVERY_REQUIRED_FROM`, это `RECOVERY_BLOCKED` без записи;
3. переводит microtask в `RECOVERY_REQUIRED` (повтор — без изменений).

После этого RC-4 `apply` берёт TASK-lock и восстанавливает. Между ними state machine ничего не может: выходов из `RECOVERY_REQUIRED` нет, а устаревшее `DONE → VERIFIED` отклоняется по CAS. RETRY re-arm и ADOPT не пройдут, пока сессия открыта (`_no_open_rollback_locked`).

**Изменение поведения.** Microtask попадает в `RECOVERY_REQUIRED` на шаг раньше: перед разрушительным apply, а не после ROLLBACK settlement. Если RC-4 затем откажет (BLOCKED) или сессия завершится без settlement, microtask остаётся на ручной границе `RECOVERY_REQUIRED`, а не DONE/UNKNOWN. Это консервативно: откат уже начат, и вернуть такую microtask к обычной проверке нельзя. Подготовка (`prepare`) не разрушительна и этап не отмечает.

---

## 5. Тесты (`test_web_alarm_state_machine_cas.py`, 12)

| Тест | Что доказывает |
| --- | --- |
| A1 (реальные процессы) | проверка успела раньше → VERIFIED сохраняется, откат RECOVERY_BLOCKED, Workspace не тронут |
| **A2** (реальные процессы, барьеры) | переход state machine прочитал DONE; RC-6 доказал этап и поставил RECOVERY_REQUIRED; устаревшая запись VERIFIED приходит до восстановления → **отклонена**; откат текущего этапа проходит; m1 **никогда не VERIFIED** |
| отметка до восстановления | во время каждой записи RC-4 статус microtask уже RECOVERY_REQUIRED |
| B (реальные процессы) | ABORT settlement → RECOVERY_REQUIRED против устаревшего `DONE → VERIFIED` → не затёрт; следующий `recover` без противоречия |
| C (реальные процессы) | два перехода из одного наблюдённого DONE (VERIFIED и FAILED_VERIFICATION) → применяется ровно один, второй отклонён; одно событие MICROTASK_TRANSITION |
| D1 (реальные процессы) | переход после задержки процесса не переписывает новый статус (UNKNOWN) |
| D2 | повтор со старым наблюдённым статусом (`expected_status`) в свежем процессе → отклонён, запись microtask побайтово не изменилась |
| D3 | сервер: устаревший `expected_status` → 409, неверный → 400, совпадающий → 200 |
| E | активация при другой ACTIVE → отказ целиком, указатель плана не сдвинут |
| F | испорченный snapshot внутри `transition` не затирает параллельный RECOVERY_REQUIRED |
| G ×2 | подготовка через state machine не откатывает ушедшую вперёд microtask; ошибка подготовки не ставит BLOCKED_PREPARE поверх статусов дальше PREPARING |

**Чувствительность** (`sensitivity_pre_2a.txt`): на коде до #2A (Repair #2) падают **11 из 12**. Проходит только A1 — этот порядок защищал уже Repair #2.

## 6. Проверки

| Набор | Результат |
| --- | --- |
| CAS (#2A, новый) | **12/12 OK**; три повтора подряд — OK |
| Фокусные: 19 модулей (CAS, Repair #2, Repair #1, RC-6 ×3, state machine, task store, manifest store, projection ×2, Resolver ×2, RC-3 ×2, RC-4 ×2, server, CLI) | **278/278 OK** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py` (43 модуля) | финальный прогон **475 OK, skip 1** (`full_regression_run3.txt`). Два предыдущих прогона дали по одному **разному** редкому падению — §7 |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK; новые неотслеживаемые файлы — LF, без хвостовых пробелов |
| Исходные probe `TASK_CLAUDE-RC6-VERIFY/probes/` | exit 0 / exit 0, поведение не изменилось |
| Probe повторной проверки (без изменений) | все прежние OK остаются OK. n02 / n02b / n15 — устаревшие точки перехвата / барьер (§7) |
| Adversarial Repair #2 (`repair2_adversarial.py`) | 8/8 OK |
| Adversarial #2A (`probes/repair2a_adversarial.py`) | **5/5 OK**: re-arm RETRY против устаревшего ручного `UNKNOWN → RECOVERY_REQUIRED` (реальные процессы) — отклонён, READY сохранён; ADOPT против того же — DONE не затёрт, повторный `recover` без шагов; отказ RC-4 после отметки — этап на ручной границе, нового восстановления нет, отказанный шаг не повторяется; две параллельные активации — применяется ровно одна; `expected_status` — без записи |
| Живое storage (только чтение) | до и после: 136 / 41, `07298919…5920` / `2269f667…3a61`; read-only `recover` WA-3.6 / 3.7 → `TASK_COMPLETED`, 0 шагов |

---

## 7. Честно о нестабильных и устаревших проверках

- **Редкие падения старых race-тестов на Windows (FINDING, не регрессия #2A).**
  - Прогон 1: `test_rollback_and_normal_owner_never_both_win` (RC-4) — сессия FAILED вместо PRESERVED.
  - Прогон 2: `test_completion_never_admits_new_open_state` (RC-5) — `CloseoutError` вместо REJECTED.
  - Прогон 3 — чистый; отдельные повторы модулей — 4/4 OK; диагностика `rc4_race_diagnostic.py` — 40/40 раундов без FAILED; `closeout_race_diagnostic.py` — 24/24 без `CloseoutError`.
  - Механизм у обоих один: `os.replace` (RC-4 — файл цели, RC-5 — каталог TASK) на Windows отказывает с sharing violation, если параллельный процесс в этот момент держит файл открытым.
  - Код обоих безопасен: RC-4 фиксирует FAILED без повторной записи и держит claims; closeout возвращает TASK в активные (`cannot move task to completed`). Но тесты ждут только два исхода.
  - Пути `complete`, `begin`, `create_microtask` и RC-4 `apply` изменения #2A не затрагивают.
  - **Proposal:** признать в этих двух тестах третий безопасный исход (FAILED без повторной записи / `CloseoutError` «cannot move») либо повторять раунд при sharing violation. Отдельная мелкая задача; тесты принятых этапов без решения не меняю.
- **n02 / n02b** (probe повторной проверки) вешали перехватчик на старую слепую `TaskStore.set_microtask_status`. `transition` её больше не вызывает, поэтому гонка в них не воспроизводится:
  - n02 теперь проверяет обычный порядок «сначала VERIFIED, затем ABORT» (это F-B);
  - n02b завершается без вердикта («child did not reach the barrier»).
  Исторические probe не менялись; гонку закрывают постоянные тесты **B** и **A2** с перехватом на новом CAS-примитиве.
- **n15** — прежний артефакт барьера (Repair #2, §5): его заменил постоянный тест F-D.

---

## 8. Вне scope / остаточное

- **F-B, F-C** не исправлялись (по постановке); анализ и предложения — в `../rc6_repair2_report.md` §7.
- **Legacy CLI WA-1** `snapshot prepare` / `snapshot restore` вызывают `manifest_store` напрямую, мимо state machine. Подготовка без `expected_status` пишет PREPARING по-прежнему вслепую (только запись ошибки теперь не затирает статусы дальше подготовки); `restore_microtask` пишет BACKUP_VERIFIED / RECOVERY_REQUIRED вслепую. Это давно известный хвост **WA4-R** (strict rollout закрывает эти обходы).
- Публичный `TaskStore.set_microtask_status` (слепая запись) остаётся для этих legacy-путей и тестовых фикстур. Новые писатели жизненного цикла обязаны использовать `compare_and_set_microtask_status`.
- **F-F** (`PROJECTION_VERSION`) — без изменений.

---

## 9. Изменённые файлы (#2A поверх Repair #2)

| Файл | Изменение |
| --- | --- |
| `web_alarm/task_store.py` | `MicrotaskStatusConflict`; `compare_and_set_microtask_status` (+ активация в той же блокировке) |
| `web_alarm/state_machine.py` | `transition`: CAS-запись, `expected_status`, активация внутри CAS, устаревший переход → `TransitionRejected`; snapshot-проверка передаёт основание; `prepare_microtask` передаёт проверенный статус |
| `web_alarm/manifest_store.py` | `_best_effort_microtask_status(expected=…)`; `_block_restore_point` / `verify_restore_point(expected_status=…)`; `prepare_microtask(expected_status=…)` (CAS-старт для пути state machine) и запись ошибки только поверх статусов подготовки |
| `web_alarm/recovery_coordinator.py` | `_rollback_stage_preflight`: проверка этапа внутри блокировок + отметка RECOVERY_REQUIRED перед разрушительным apply |
| `web_alarm/server.py` | необязательное `expected_status` в endpoint перехода |
| `test_web_alarm_state_machine_cas.py` | **новый**, 12 тестов |

Граф переходов, набор статусов и модель действий Resolver не менялись. Ожидания существующих тестов не менялись.

---

## 10. Итог

R1 закрыт полностью: устаревший переход state machine больше не может затереть новый статус жизненного цикла, а во время разрушительного отката RC-6 этап не может стать VERIFIED.

**Статус всего Repair #2: RESULT READY / AWAITING INDEPENDENT VERIFICATION.**

**NEXT:** commit / push пользователем → независимая проверка ChatGPT → только после PASS RC-6 = DONE / VERIFIED → NEXT = WA4-E. **WA4-E NOT STARTED.**
