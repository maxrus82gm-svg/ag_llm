# AGENT REPORT — CLAUDE-WA-014 / RC-6 Focused Safety Gate: accepted ABORT before ACTIVE

- **Исполнитель:** Claude (Opus 5.5). Независимый verifier — ChatGPT по GitHub.
- **Дата:** 2026-10-08.
- **Источник:** БЛОК 1 карточки `000_Задачи Claude.md`; пользователь передал её в чате как утверждённую. Строка статуса в БЛОКЕ 1 при этом была «DRAFT / READY FOR USER HANDOFF — НЕ ЗАПУЩЕНА» — handoff дал пользователь. Полная постановка — `task_statement.md`.
- **PRIMARY:** `23_Архитектура Web Alarm Workspace.md`; порядок — `24`.
- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.** Commit / push не выполнялись.
- **Baseline:** HEAD 167 `fb5e6e38c9ff13d43655ea51445fb7fef422cd38`. `web_alarm/` и `test_web_alarm_*.py` идентичны commit 166 `19ca5626a28559cfe506ff6c993eb25a1c0a6e3f` (проверено `git diff`; 167 менял только документы, карточку и `.obsidian`). Полный набор на baseline — 569 OK, skip 1. Safety copies 85 файлов — `baseline.md`, `safety_copies/`.
- **Маршрут:**
  - `08` → `18` → глобальный `000` → `01` → `23` / `24` (прочитаны в WA-013 этого же чата, перечитаны нужные места);
  - `00_INSTRUCTION.md` (ведутся `session.jsonl`, `context.md`, `history.md`);
  - отчёты #4A / #4B.

---

## 1. Итог

**Gate A — CONFIRMED.** Гипотеза verifier воспроизведена через поддерживаемые API (HTTP control plane, без прямой записи в storage). Шаги:
1. `op1` получает ABORT ACCEPTED при READY (settlement ещё не закреплён).
2. Штатный переход READY → ACTIVE проходит (HTTP 200), хотя гейт исполнения F-C уже отказывает microtask в праве на запись (`MICROTASK_RECOVERY_REQUIRED`).
3. Затем и RC-6 `recover`, и прямой RC-4 (`/rollbacks` + `/apply`) физически восстанавливают файлы: существующий, удалённый и созданный.

Тот же класс без ABORT: ROLLBACK, принятый до ACTIVE, + активация (выход «активируй, потом recover» из Repair #4A) → откат изменений, сделанных вне сервера.

**Gate B — выполнен, минимально.** Переход в ACTIVE отклоняется, если у операций microtask уже есть ABORT/ROLLBACK disposition: принятый, закреплённый или открытая сессия RC-4. Это то же правило, что у гейта исполнения F-C.
- Решение и CAS — в одной секции под TASK-lock. Под тем же TASK-lock пишут disposition все: Resolver, RC-4, RC-6.
- Значит, ACTIVE снова означает «у этапа было окно, в котором запись могла быть разрешена». На этом и держится правило отката Repair #4B.
- Законный порядок (ACTIVE до ABORT) по-прежнему откатывается.

---

## 2. Gate A — воспроизведение на baseline (код 166)

`probes/gate_a_abort_before_active.py`. Временное storage; шаги lifecycle — через `WebAlarmApi.dispatch`: reconcile, resolutions, `/microtasks/m1/transition`, переход операции, `/recover`, `/rollbacks`. Файлы меняет сама проба «извне», RC-3 `mutation_boundary` не вызывался. Колонка «гейт» — вердикт `execution_refusal`, то есть правила F-C, которое применяет `mutation_boundary` перед любой нормальной записью. Вывод: `probes/gate_a_baseline_166.txt`.

| Сценарий | Гейт при READY | ACTIVE | Гейт при ACTIVE | Итог |
| --- | --- | --- | --- | --- |
| A1 RC-6 `recover`, ABORT `op1` → ACTIVE → ROLLBACK `op2` (write / delete / create) | MICROTASK_NOT_ACTIVE | **200** | **MICROTASK_RECOVERY_REQUIRED** | **DESTRUCTIVE** ×3: шаги PREPARE_ROLLBACK, APPLY_ROLLBACK, SETTLE_ROLLBACK, SETTLE_ABORT; свежий процесс — MANUAL без повторного действия |
| A2 прямой RC-4 через HTTP (write / delete / create) | MICROTASK_NOT_ACTIVE | **200** | **MICROTASK_RECOVERY_REQUIRED** | **DESTRUCTIVE** ×3: prepare 201 PRESERVED, apply 200 VERIFIED |
| A3 порядок ABORT → попытка ACTIVE | — | **200** | — | активация проходит |
| A4 обратный порядок: ACTIVE легитимно, потом ABORT `op1`, ROLLBACK `op2` (write / create) | — | 200 | окно было (запись разрешима) | восстановлено — **законно, должно остаться** |
| A5 ROLLBACK `op2` до ACTIVE (без ABORT) → ACTIVE → RC-6 / прямой RC-4 | MICROTASK_NOT_ACTIVE | **200** | **MICROTASK_RECOVERY_REQUIRED** | **DESTRUCTIVE** ×2 |

**Подтверждённая причинность.** В A1 / A2 / A5 microtask стала ACTIVE, когда гейт исполнения уже отказывал её операциям в праве на запись. Окна полномочий не было ни разу, но ACTIVE прошёл как доказательство исполнения:
- для правила отката Repair #4B (`rollback_refusal`: ACTIVE → «исполнялась»);
- для RC-6 (`_classify` / preflight).

Settlement ABORT при этом записывался уже из ACTIVE или RR (факт `microtask_status` = RECOVERY_REQUIRED), так что метка #4B «закреплено до исполнения» не появлялась.

## 3. Root cause

Переход READY → ACTIVE (и FAILED_VERIFICATION → ACTIVE) в state machine проверял restore point, предыдущие этапы и единственность ACTIVE, но **не recovery disposition**. Поэтому ACTIVE мог появиться у microtask, которой F-C уже навсегда отказал в праве на запись. Repair #4A ещё и рекомендовал этот путь как выход для принятого ROLLBACK до исполнения.

## 4. Gate B — решение и почему

1. **`microtask_gate.activation_refusal`** — то же определение, что у `execution_refusal` (`disposition_actions`): есть ABORT/ROLLBACK (закреплённый, принятый authority или открытая сессия RC-4) → `MICROTASK_RECOVERY_REQUIRED`; нечитаемые факты → `LIFECYCLE_STATE_UNAVAILABLE` (fail-closed). ADOPT и RETRY не мешают: выходы Repair #4A «активируй» для них сохранены.
2. **`ServerStateMachine._admit_active`** (вызывается для любого перехода в ACTIVE):
   - решение под TASK-lock, а в той же секции — публичный CAS с `activate=True` (mutation lock; повторная проверка предыдущих VERIFIED и единственного ACTIVE, F4);
   - порядок блокировок TASK → mutation, как везде;
   - ABORT, принятый до активации, отклоняет её; принятый после — находит этап, у которого окно было;
   - отказ — `TransitionRejected` / HTTP 409 `transition_rejected` с причиной, событие MICROTASK_TRANSITION_REJECTED, ничего не записано.
3. **Ручная граница #4A для ROLLBACK** (`pre_execution_next_action`): больше не советует активацию. Принятый ROLLBACK её теперь и не допускает; выход — ручной разбор и ABORT или replan.

**Почему здесь.** Это авторитетная граница жизненного цикла: ровно в ней ACTIVE и становится «доказательством».
- Нет новой persisted схемы, миграции и изменения графа: добавлено предусловие, как F-B для VERIFIED в Repair #3. WA4-E не нужен.
- RC-6 и прямой RC-4 закрываются автоматически: правило отката #4B видит microtask, не бывшую ACTIVE, и отказывает (`MICROTASK_NEVER_EXECUTED`).

**Отклонено:**
- Отличать «ACTIVE до / после ABORT» по времени (события, `created_at`) — история, а не authority, и часы.
- Отказывать в откате любой ACTIVE microtask с принятым ABORT — ломает законный A4: порядок post hoc не восстановить.
- Persisted факт выдачи authority (RC-3 / WA4-E) — новая модель.

## 5. Изменения

| Файл | Изменение |
| --- | --- |
| `web_alarm/microtask_gate.py` | `activation_refusal`; `pre_execution_next_action` — для ROLLBACK без выхода «активируй» (docstring) |
| `web_alarm/state_machine.py` | `_admit_active` (TASK-lock, решение + публичный CAS в одной секции); переход в ACTIVE идёт только через него |
| `test_web_alarm_recovery_coordinator_wa014.py` | **новый**, 11 тестов |
| `test_web_alarm_recovery_coordinator_repair4b.py` | тест B4 из #4B (ещё не принят): активация в окне краша теперь отклоняется — ожидание обновлено (+ импорт) |

Не менялись: RC-6 `recovery_coordinator.py`, RC-4, Resolver, Projection, OperationStore / контракт, RC-3, TaskStore, server. Тест Repair #3 F4 (`test_f4_activation_rechecks_earlier_microtasks_under_the_lock`) **не менялся**: публичный CAS сохраняет его шов.

## 6. Тесты WA-014 (11)

- **Эксплойт × 3 вида целей:** ABORT принят → активация отклонена (state machine + HTTP 409); гейт исполнения MICROTASK_NOT_ACTIVE; ROLLBACK `op2` → `recover` без APPLY, MANUAL; прямой RC-4 REJECTED; байты, сессии, claims, settlement `op2` — без изменений.
- **ROLLBACK до ACTIVE:** активация отклонена; причина #4A без «активируй»; прямой RC-4 REJECTED; ABORT закрывает в RR; байты целы.
- **Открытая сессия RC-4** (старой сборки) при устаревшем ROLLBACK → активация отклонена.
- **Повтор (replay):** 3 отказа подряд — запись microtask не изменилась, 3 события отказа; свежий процесс — SETTLE_ABORT, RR с фактом READY; из RR в ACTIVE переход невозможен; повторный `recover` пуст.
- **FAILED_VERIFICATION → ACTIVE** под ABORT — отклонено.
- **Нечитаемые факты** → LIFECYCLE_STATE_UNAVAILABLE, после восстановления чтения активация проходит.
- **Правило считает только разрушающие disposition:** RETRY — нет отказа, ABORT — отказ.
- **Позитивный контроль × 3 вида + прямой RC-4:** ACTIVE до ABORT → откат восстанавливает точные байты.
- **Сериализация на реальных процессах, оба порядка:**
  - ABORT не может вклиниться между решением активации и записью ACTIVE (ждёт TASK-lock, затем ACCEPTED; ACTIVE — законный порядок);
  - активация ждёт записи ABORT и затем отклоняется.

**Чувствительность** (`probes/sensitivity_pre_wa014.py`): на runtime 166 падают **9 из 11**; проходят только 2 позитивных контроля.

## 7. Проверки

| Набор | Результат |
| --- | --- |
| Baseline (код 166), полный набор | 569 OK, skip 1 (`baseline_full_regression.txt`) |
| Gate A (`probes/gate_a_baseline_166.txt`) | **CONFIRMED**: A1 ×3, A2 ×3, A5 ×2 — DESTRUCTIVE; A3 — ACTIVE 200 после ABORT; A4 — законный откат |
| Gate A после исправления (`probes/gate_a_after_fix.txt`) | A1 / A2 / A3 / A5 — активация **409 transition_rejected**, **ни один байт не изменился**; A4 ×2 — по-прежнему восстанавливает |
| WA-014, новый модуль | **11/11 OK**; в стресс-повторах ещё 5 раз подряд OK |
| Чувствительность на 166 | **9 из 11** падают (`probes/sensitivity_pre_wa014.txt`); проходят 2 позитивных контроля |
| Фокусно, 28 модулей (WA-014, #4B, #4A, #4, #3, CAS, #2, #1, RC-6 ×3, RC-4 ×2, RC-5 ×2, Resolver ×2, RC-3 ×2, контракт, operation store ×2, state machine, task store, manifest store, report acceptance, server, CLI) | **425 тестов, 28/28 модулей exit 0** (`focused_regression.txt`) |
| Полный явный `test_web_alarm_*.py`, 48 модулей | прогон 1 — **580 OK, skip 1**; прогон 2 — **580 OK, skip 1** (`full_regression_run1.txt`, `full_regression_run2.txt`) |
| Стресс-повторы | **29/29 OK** (`stress_repeats.txt`): WA-014 ×5, #4B ×2, RC-4 concurrency ×3, #4A ×3, #4 ×3, #3 ×2, #2 ×2, RC-6 concurrency ×3, CAS ×2, RC-3 concurrency ×2, projection concurrency ×2 |
| Adversarial WA-014 (`probes/wa014_adversarial.py`) | 24 + 30 = **54 раунда, нарушений I1 / I2 — 0**; 1 известная ошибка Windows `os.replace` в законном порядке (§10) |
| Прежние пробы (исходные RC-6 ×2, повторная проверка, #2, #3 ×2, #4 ×2, #4A ×2, #4B: repro / R1 / adversarial) | все exit 0; вердикты **совпадают с состоянием после #4B**. #4B Z1: 0 разрушительных из 12 (до WA-014 было 10 из 24 — та самая активация после ABORT) |
| Проба #2A | b01–b03, b05 — OK. Исходная b04 несовместима со стендом: её барьер стоит внутри секции под TASK-lock, второй процесс ждёт блокировку до таймаута — взаимная блокировка в самом стенде, в рабочем коде такой нет. Та же проверка с барьером на новой границе решения (`probes/repair2a_b04_after_wa014.py`) — **6/6 OK**: проходит ровно одна активация |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK; новые и изменённые `.py` / `.md` — LF, без хвостовых пробелов |

## 8. Безопасность / живое storage

Все испытания — только во временном storage; живое `%LOCALAPPDATA%\WebAlarmWorkspace` только читалось (read-only выборка: 0 файлов resolution — данных «ACTIVE после ABORT» от старых сборок нет).

| Живое storage | Файлов | Каталогов | SHA-256 (путь + содержимое) |
| --- | --- | --- | --- |
| до работы | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |
| после всех проверок | 136 | 41 | `5961c00c8c466c6bdd476f85abea52e10ea11db470f5b40c0f76bf0a5ea37cd2` |

Живое storage **не изменилось**.

## 9. Собственный adversarial review

| Атака / вопрос | Результат |
| --- | --- |
| Гонка ABORT ↔ активация ↔ ROLLBACK + прямой RC-4 ↔ recover, реальные процессы, случайные задержки (`probes/wa014_adversarial.py`); решение активации инструментировано **внутри** заблокированной секции | 24 + 30 = **54 раунда**, нарушений I1 / I2 — **0**. ACTIVE выдан только при нуле принятых ABORT/ROLLBACK; восстановление только после успешной активации. Исходы: 35 — активация отклонена гейтом; 14 — активация первой, законный откат; 5 — ABORT уже закреплён, RR → ACTIVE запрещён графом |
| Другие пути в ACTIVE | RC-6 REARM_RETRY уже требует отсутствия ABORT/ROLLBACK (то же правило); CLI переходов microtask нет (`status --active` — чтение); legacy `restore_microtask` → BACKUP_VERIFIED, дальше штатный гейт |
| Порядок блокировок / взаимная блокировка | везде TASK → mutation; внутри `activation_refusal` новых захватов нет; тесты порядка блокировок Repair #2 проходят |
| Рестарт | правило без состояния; свежий процесс даёт тот же ответ (тест повтора) |
| Устаревший basis | открытая сессия RC-4 при устаревшем ROLLBACK всё равно блокирует (тест) |
| Совместимость | новых persisted полей нет; downgrade не затронут |
| Прежние пробы | см. §7 |

Найдено в ходе работы и учтено: первая версия `_admit_active` делала CAS через `_locked`-вариант и обходила шов теста Repair #3 F4. Переделано: решение под TASK-lock + публичный CAS внутри. Тест F4 проходит без изменений, защита F4 сохранена.

## 10. Остаточные риски / findings

1. **Данные старых сборок (≤ 166):** microtask, активированная после принятого ABORT до этого исправления, неотличима от законного порядка; откат её этапа по-прежнему разрешён. В живом storage resolution нет (0) — затронутых данных нет.
2. **`TransitionRejected.next_safe_action`** при отказе активации — статичный текст state machine для READY («transition … to ACTIVE»). Причина отказа точная; так же устроен отказ VERIFIED с Repair #3. При желании — отдельная мелкая правка NEXT.
3. **Известное FINDING Windows:** в 1 из 54 раундов прямой RC-4 получил «cannot persist rollback record» (`os.replace` при конкурентном читателе, sharing violation; как раньше в гонках RC-4 / RC-5). Порядок там был законный, итог согласованный (MANUAL), разрушения нет.
4. **Активация теперь ждёт TASK-lock.** Если TASK-lock держит долгий шаг — apply RC-4, READY-proof RC-6 — переход в ACTIVE ждёт его. По таймауту блокировки — ошибка хранилища, ничего не записано, можно повторить. Так же с Repair #3 устроен VERIFIED. Стенды, которые паркуют процесс внутри CAS активации (проба #2A b04), теперь сами себя блокируют — см. §7.
5. **Изменение семантики #4A:** выход «активируй, потом recover» больше не действует для ROLLBACK (только ABORT / replan); для ADOPT и RETRY сохранён. Это сознательное следствие закрытия A5 — оценить при проверке.

## 11. Связь с прежними Repair и документация

- **#4B:** правило отката не менялось, теперь его посылка «ACTIVE = было окно полномочий» верна и для нового порядка событий. Тест B4 обновлён (активация в окне краша отклоняется).
- **#4A:** ABORT до исполнения достижим и закрепляется (инвариант сохранён); ручная граница ROLLBACK — без «активируй».
- **#4 / #3 / #2 / #2A:** без изменений; F4 и F-B (VERIFIED) — та же схема «решение под блокировками».

```text
DOC IMPACT: YES (после independent PASS)
CURRENT STATE IMPACT: YES — после PASS
ARCHITECTURE IMPACT: YES — предусловие перехода в ACTIVE (lifecycle), владелец 23
CONTEXT LIBRARY IMPACT: NO
REGISTRY / ROUTING IMPACT: NO
NEW DOCUMENT REQUIRED: NO
CANONICAL OWNER: 23 (архитектура); 24 (exit-proof RC-6); 25 (история)
AFFECTED DOCUMENTS: 23, 24, 25, 05, 06, 001, 01, 000 (глобальный); 000_Задачи Claude (ротация сделана)
CONTRADICTION CHECK: REQUIRED — см. delta
LOSS CHECK: NOT APPLICABLE (только добавления)
```

**Documentation delta (verifier / ChatGPT после PASS; сверх delta #4A §9 и #4B §11):**
- `23` §8 / §22 (жизненный цикл и инварианты): «переход в ACTIVE не выполняется, пока у операций microtask есть ABORT/ROLLBACK disposition (принятый, закреплённый, открытая сессия RC-4) — то же правило, что у гейта исполнения F-C; решение и запись ACTIVE — в одной секции под TASK-lock». Добавить, что ACTIVE в правиле отката #4B означает «было окно, в котором запись могла быть разрешена».
- `23` (recovery до исполнения): ручная граница ROLLBACK — без выхода через активацию.
- `24` — exit-proof RC-6 дополнить тем же; RC-6 = DONE / VERIFIED только после PASS.
- `25` / `05` / `06` / `001` — запись CLAUDE-WA-014 в цепочке RC-6 (append-only), с итогом Gate A (CONFIRMED) и Gate B.

**Сделано сейчас в пределах полномочий исполнителя:** ротация карточки (БЛОК 1 → БЛОК 2, результат в БЛОК 3, БЛОК 1 очищен до «ОЖИДАНИЕ НОВОЙ ЗАДАЧИ»; записи WA-013 и ранее сохранены), task session, этот отчёт.

## 12. Блокеры и рекомендация

**Блокеры RC-6 внутри scope:** исполнитель не видит. Исходный эксплойт закрыт в RC-6 и прямом RC-4, законный откат сохранён, гонки и рестарт покрыты.

**NEXT:** commit / push пользователем → независимая GitHub-only проверка ChatGPT → только после PASS: синхронизация постоянной документации и решение о следующем этапе. **WA4-E NOT STARTED.**
