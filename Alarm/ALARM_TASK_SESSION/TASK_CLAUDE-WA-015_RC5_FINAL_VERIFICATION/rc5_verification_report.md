# CLAUDE-WA-015 — RC-5 Independent Final Verification — verifier report

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локально. **Дата:** 2026-10-08.
**Роль:** независимая проверка RC-5 (`CLAUDE-WA-007` + Repair №1 ChatGPT + интеграция RC-6). REVIEW ONLY: production-код не менялся.
**Baseline:** локальный HEAD = `origin/main` = `53ec5c3d83ab8cdca76da62037885e5672f0b015` (commit 171). Код `web_alarm/` и `test_web_alarm_*.py` побайтно равны HEAD. Грязное дерево до старта — только БЛОК 1 карточки (постановка, не закоммичена) и `.obsidian/workspace.json`.

## 1. Вердикт

**FAIL / CONFIRMED BLOCKER** — в closeout gate RC-5 при совместной семантике RC-5/RC-6. Физической угрозы Workspace нет. Блокер узкий; минимальный ремонт затрагивает только `web_alarm/projection.py` (§7).

| Пункт | Итог |
| --- | --- |
| A-I. Принятый ROLLBACK VERIFIED-этапа больше не блокирует закрытие | **CONFIRMED, регрессия с commit 162** — BLOCKER |
| A-II. Принятые ABORT / ADOPT, ещё не оформленные RC-6 (settlement), не блокируют закрытие | **CONFIRMED** (так задумано в RC-5, но противоречит RC-6) — входит в тот же ремонт, нужно DECISION |
| B. Историческая TASK получает recovery-NEXT вместо read-only | **CONFIRMED**; действия по такому NEXT отклоняются — кроме частичного эффекта RC-4 `close` на legacy-данных (FINDING вне scope) |
| Остальная приёмка RC-5 и Repair №1 (§5) | **подтверждена**, расхождений нет |

## 2. Метод

- Всё разрушительное — только во временном storage. Живое storage `%LOCALAPPDATA%\WebAlarmWorkspace` только читалось: 136 файлов / 41 каталог, хеш `5961c00c…7cd2` до и после.
- Воспроизведения идут через HTTP control plane (`WebAlarmApi.dispatch`). Через публичные сервисы делаются только регистрация Workspace / TASK и legacy-завершение для B. Изменения файлов «вне сервера» в пробах — это эффект операции или внешний писатель (executor WA4-E ещё нет).
- Пробы: `probes/hyp_a_premature_closeout.py`, `probes/hyp_b_historical_next.py`, `probes/sensitivity_by_commit.py`, `probes/purity_and_authority_sweep.py`. Запуск из корня репозитория: `python -B <probe>`. Сырые выводы в Git не добавлены (регламент `18`), ключевые строки приведены ниже.

## 3. Гипотеза A — преждевременный closeout

### A-I — регрессия: принятый ROLLBACK VERIFIED-этапа (BLOCKER)

**Воспроизведение A7b, естественный порядок, HTTP:**
1. m1 VERIFIED.
2. m2 подготовлен, переведён в ACTIVE.
3. `op_1` (`write two.txt`) начата на ACTIVE m2 и переведена в FAILED, но её запись успела лечь.
4. m2 → DONE → VERIFIED (200: FAILED не держит verification gate).
5. reconcile даёт `ROLLBACK_CURRENT_MICROTASK`; ROLLBACK принят (201).

Результат:

```text
closeout after ROLLBACK accepted: [true, []]
RC-6 recover would (on a copy): "RECOVERY_BLOCKED steps=[] workspace_changed=False"
POST complete: [200, "COMPLETED"]
```

Вариант A7 (операция начата после VERIFIED) даёт то же. Projection показывает операцию как `ROLLBACK_STAGE_PROTECTED`. После закрытия projection истории показывает `RESOLUTION_STALE` и NEXT «run a new reconciliation», но reconcile на завершённой TASK отвечает 409.

**Когда появилось** (`sensitivity_by_commit.py`, одинаковый сценарий):

| Код | A7: блокеры closeout → complete |
| --- | --- |
| 156 `897d724` (RC-5 + Repair №1) | `['ROLLBACK_PENDING']` → REJECTED |
| 161 `e551b91` | `['ROLLBACK_PENDING']` → REJECTED |
| 162 `2f1f878` (CLAUDE-WA-009, RC-6 Repair #2, R1) | `[]` → **COMPLETED** |
| HEAD `53ec5c3` | `[]` → **COMPLETED** |

**Root cause:**
- `closeout_blockers` ищет буквальное состояние `recovery["state"] == "ROLLBACK_ACCEPTED"`.
- RC-6 R1 (`ProjectionService._protect_stage`, моя прошлая работа WA-009) переименовывает его для VERIFIED / не текущего этапа в `ROLLBACK_STAGE_PROTECTED`; исходное значение остаётся в поле `protected_state`.
- Closeout не был обновлён. Для STARTED / UNKNOWN / DONE операций это маскируют блокеры `OPERATION_*`; для FAILED (терминальной) операции не маскирует ничего.

**Нарушенный инвариант** — собственный контракт RC-5:
- docstring `closeout_blockers`: «an authoritative ROLLBACK without a VERIFIED rollback whose ownership is released has no terminal safe outcome»;
- `rc5_report.md` §13: «Accepted ROLLBACK без rollback-сессии → `ROLLBACK_PENDING`»;
- `33` RC-5: «closeout gate не завершает TASK при open/unresolved operations».

**Impact:**
- TASK необратимо закрывается в обход границы RC-6, где нужно решение человека (`RECOVERY_BLOCKED`, «explicit project-level decision is required»).
- Принятое recovery-решение остаётся в истории навсегда неисполненным.
- Байты Workspace и claims не меняются.

**Severity:** MEDIUM.

### A-II — ABORT / ADOPT, принятые, но не оформленные RC-6

**A1 (HTTP).** m1 и m2 VERIFIED; `op_1` на m2 → STARTED. Варианты: A1u — UNKNOWN_AFTER_DISCONNECT, A1i — INTENT.

```text
closeout before ABORT: [false, ["OPERATION_UNRESOLVED"]]      (A1i: ["OPERATION_OPEN"])
resolution: "ABORT:201/ACCEPTED"
closeout after ABORT (not settled): [true, []]
RC-6 recover would (on a copy): "TASK_READY_TO_CLOSE steps=['SETTLE_ABORT'] workspace_changed=False"
POST complete: [200, "COMPLETED"]
persisted after completion: op.status STARTED, op.recovery_settlement null, claims_active 0, workspace_changed false
projection (completed): recovery.state ABORT_ACCEPTED, authority_source resolver (context / ui — то же)
POST recover (completed): TASK_COMPLETED, reason = Resolver ABORT text; settlement after recover: null
POST reconcile on completed: 409 reconciliation_evidence_error
```

**A5, ADOPT:** свежий принятый ADOPT, не оформленный.
- closeout `[true, []]`; RC-6 сначала выполнил бы `SETTLE_ADOPT` (операция → VERIFIED с receipt).
- После закрытия операция навсегда остаётся STARTED без receipt. Projection истории сразу показывает `RESOLUTION_STALE` (BASIS_UNAVAILABLE) с неисполнимым «run a new reconciliation».

**Естественный вход в A1i.** Closeout сам советует для INTENT: «transition to FAILED or record an accepted ABORT». Если пойти по ветке ABORT, TASK закрывается без settlement.

**Root cause.**
- RC-5 закрывает операцию по факту принятия в Resolver (правило release RC-3: accepted ABORT или свежий ADOPT).
- RC-6 позже придал ADOPT / ABORT «durable lifecycle semantics» через settlement (`33`, RC-6). Microtask gate Repair #3 (`verification_refusal`) уже требует settlement для того же факта: «reconcile it and settle its recovery before the microtask is verified».
- TASK-gate остался слабее microtask-gate. Действующий тест `test_aborted_operation_no_longer_blocks` закрепляет поведение RC-5: он сам строит этот сценарий и ждёт `[]`.

**Impact:**
- Необратимо незавершённая recovery-администрация: settlement после закрытия записать нельзя, все store пишут только в active.
- RC-5 и RC-6 расходятся в ответе на вопрос «готова ли TASK к закрытию».
- История TASK показывает живое recovery-состояние (см. B).
- Физического эффекта и утечки владения нет.

**Severity:** LOW.

### Контроли (все ожидаемые)

- **A2** — ABORT оформлен через `recover` (`SETTLE_ABORT`, settlement с `microtask_status: VERIFIED`) → closeout чист → COMPLETED → NEXT «TASK is COMPLETED; its state is read-only history» (`task_status`).
- **A3** — STARTED без резолюции → `OPERATION_UNRESOLVED`, complete 409.
- **A4** — без операций → `TASK_READY_TO_CLOSE` → COMPLETED, read-only.
- **A6** — у операции claim → `ACTIVE_CLAIM`, complete 409. После публичного release (разрешён после ABORT) closeout чист, settlement по-прежнему null — тот же класс, что A-II.
- **A8** — RETRY терминальной операции → `RETRY_PENDING`, 409.
- **A10, наблюдение:** свежий REJECTED ADOPT у FAILED-операции → closeout чист, а RC-6 возвращает `MANUAL_DECISION_REQUIRED`. Это сознательное правило RC-5 F4: rejected / stale резолюция — лишь совет и терминальную операцию не открывает. Блокером не считаю; см. F-3.

## 4. Гипотеза B — NEXT исторической TASK

**Фикстура.** Recovery-факты создаются через HTTP на активной TASK. Затем TASK переносится в `completed/` старым неограниченным примитивом `TaskStore.complete_task` — это путь до RC-5, и он по-прежнему публичный метод библиотеки. Через HTTP он не выставлен.

| Фикстура | `recovery.state` / `authority_source` | NEXT (GET task = projection = context = ui) | Исполнимость (bytes) |
| --- | --- | --- | --- |
| B1: STARTED, без резолюции | RECONCILIATION_REQUIRED / reconciliation | «reconciliation evidence … unavailable …; manual review is required before any mutation» | reconcile 409, resolutions 409, transitions 404, rebuild 409; ничего не изменилось |
| B2: + принятый ROLLBACK | RESOLUTION_STALE / resolver_stale | «… run a new reconciliation and resolve …» | reconcile 409, prepare 404; ничего не изменилось |
| B3: + сессия PRESERVED | ROLLBACK_STALE_OPEN / rollback | «Close the tracked rollback session, then run a new reconciliation» | apply 404, close 404; ничего не изменилось |
| B4: + apply прерван после записи (APPLYING, in flight, 2 claims) | ROLLBACK_APPLYING / rollback | «rollback was interrupted during a restore; apply again …» | apply 404, close 409 (`TARGET_FATE_UNKNOWN`); ничего не изменилось |
| B5: + apply завершился PARTIAL (2 claims) | ROLLBACK_PARTIAL / rollback | «… then close this rollback to release its ownership» | apply 200 REPLAYED; **close 404, но claim store изменился**: обе claims сняты, запись сессии осталась PARTIAL, `claims_released=false` |

**Общие наблюдения по всем фикстурам:**
- `POST recover` → `TASK_COMPLETED` (RC-6 правильно ставит статус TASK первым), но в `reason` повторяет recovery-NEXT.
- `RemoteEntry.enter` отказывает: «unknown active task_id».
- В UI нет кнопок recovery-действий. Он показывает NEXT и chip `recovery_state` рядом с COMPLETED.
- Через gated-путь (A1 / A5 / A7 / A10) завершённая TASK тоже получает recovery-NEXT (`ABORT_ACCEPTED` / `RESOLUTION_STALE`). Значит, B достижима и без legacy-примитива.

**Root cause.** `ProjectionService._decide`: фокусная операция с recovery-вниманием (и структурные блокеры) проверяются раньше ветки `task.status in (COMPLETED, ARCHIVED)`. Read-only NEXT получает только история без recovery-фактов.

**Impact:**
- Вводящий в заблуждение NEXT и источник authority для истории; явной read-only / manual границы нет.
- Исполнимого физического действия нет: все записи Resolver / RC-4 / state machine / operations упираются в `active_only` store-гейты.
- Исключение B5 — RC-4 `close` (так же `_complete_release`) сначала пишет глобальный claim store и только потом падает на записи сессии (`active_only`). Это частичный эффект на исторической TASK; пока он возможен только на legacy-данных: gated closeout не пропускает открытые rollback и claims. Код RC-4 — вне scope (F-1).

**Severity:** LOW–MEDIUM.

## 5. Приёмка RC-5 и Repair №1 (§5 постановки)

| Контракт | Evidence | Итог |
| --- | --- | --- |
| Checkpoint не authority: stale / tampered / legacy не управляют NEXT | `CheckpointProjectionTests`; sweep P1 (tampered → INCONSISTENT), P2/P4 (legacy → LEGACY_UNVALIDATED): подделанный NEXT не попал ни в context, ни в ui, ни в RemoteEntry, ни в projection | OK |
| Projection строится из authoritative stores; inspect не пишет | `PurityTests` (Y); sweep на 4 состояниях вне фикстур Y: ABORT без settlement + tampered checkpoint; RC-4 APPLYING in flight + claims + legacy checkpoint; завершённая TASK с открытой сессией; ABORT settled + испорченный restore point. 3 прохода всех GET / POST reconcile / POST snapshot verify / library / CLI: хеш storage (включая `locks/`) и Workspace неизменен, **4/4** | OK |
| Snapshot verify чист и при успехе, и при отказе | тесты F/G; sweep P3: verify 409, ни байта | OK |
| Свежая authority Resolver выше advisory reconciliation | `PrecedenceTests` (I–K, M) | OK |
| Незавершённая RC-4 сессия не исчезает при позднем ABORT / RETRY / ADOPT (Repair №1) | `AdversarialRepairTests` 17/17; B3/B4/B5 — сессия видна и в истории | OK |
| `T_APPLYING`, restart, supersession, неполный release — fail-closed | `AdversarialRepairTests`, RC-6 repair-наборы; B4: in-flight → «apply again» (RC-4 сначала доказывает байты) | OK |
| `complete` против «новой незакрытой операции» | W (`test_completion_never_admits_new_open_state`), стресс 10/10 | OK |
| Гонка rebuild не даёт ложный VALID | X, стресс 10/10 | OK |
| Исторические receipts не выдаются за текущее состояние | N (`facts_source=rollback_receipt`, `current_physical_state_asserted=false`) | OK |

## 6. Проверки

- **Полный набор** (`python -B -m unittest` по 48 модулям `test_web_alarm_*`) на baseline `53ec5c3`, дважды:
  - прогон 1 — **580 OK, skip 1** (≈259 с);
  - прогон 2 (после всех проб) — **580 OK, skip 1** (≈236 с).

  Историческая точка сравнения: 379 после Repair №1, 580 после WA-014; рост — тесты RC-6.
- **RC-5:**
  - `test_web_alarm_projection` — 47 тестов, из них `AdversarialRepairTests` 17 и `CloseoutTests` 8;
  - `test_web_alarm_projection_concurrency` — 3 теста, стресс **10/10** (30 прогонов W/X/rebuilders).
- **RC-4 / RC-6 и интеграция** (rollback ×2, recovery_coordinator ×10, context / server / cli / task_store / state_machine ×2 / remote_entry / ui / restart) входят в оба полных прогона; падений нет.
- **Пробы:**
  - A — 8 сценариев + 4 дополнительных;
  - B — 5 фикстур;
  - чувствительность по коммитам — 4 кодовые базы;
  - purity sweep — 4/4.
- `python -B -m compileall -q web_alarm` — OK.
- `git diff --check`: до ротации отмечал только хвостовые пробелы в самой вставленной постановке БЛОКА 1; при переносе в БЛОК 2 они сняты, после ротации — OK. LF во всех новых файлах.

## 7. Минимальный repair plan (RC-5 Repair #2) — предложение, не выполнено

Scope: `web_alarm/projection.py` + тесты. Ни нового графа, ни схемы, ни RC-4 / RC-6.

1. **A-I.** В `closeout_blockers` выдавать `ROLLBACK_PENDING` также при `recovery.get("protected_state") == "ROLLBACK_ACCEPTED"`.
2. **A-II (DECISION REQUIRED).**
   - Новый блокер `RECOVERY_SETTLEMENT_PENDING` для состояний, которые RC-6 ещё оформляет: `ABORT_ACCEPTED`, `ADOPT_ACCEPTED`, `ABORT_OVER_SETTLEMENT`, `ADOPT_SETTLED` / `ABORT_SETTLED` / `ROLLBACK_SETTLED` с незавершённой администрацией. Плюс блокер `SETTLEMENT_CONTRADICTION`.
   - Меняет принятый контракт RC-5 (`test_aborted_operation_no_longer_blocks`): было «ABORT accepted → eligible», станет «ABORT accepted → recover → eligible».
   - Альтернатива: принять A-II как административный остаток и оставить только пункты 1 и 3.
3. **B.** В `_decide` проверять COMPLETED / ARCHIVED первым. NEXT = «TASK is … read-only history» плюс пометка, что оставшиеся recovery-факты — только историческое evidence. `authority_source = task_status`; диагностика операций и `recovery.attention` сохраняются.
4. **Тесты:** 4 регрессии (прототип ниже) и обновлённый тест A-II.

**Изолированный прототип** (копия кода и тестов HEAD в scratchpad; рабочее дерево не тронуто). Diff `projection.py` — +25 / −2 строки (сокращённо):

```diff
+_SETTLEMENT_PENDING = {
+    "ABORT_ACCEPTED", "ADOPT_ACCEPTED", "ABORT_OVER_SETTLEMENT", "ADOPT_SETTLED", "ABORT_SETTLED", "ROLLBACK_SETTLED",
+}
 ...
-        if projection["blockers"]:
+        if task.status in (TaskStatus.COMPLETED, TaskStatus.ARCHIVED):
+            next_action = f"TASK is {task.status.value}; its state is read-only history"
+            if attention or projection["blockers"]:
+                next_action += "; the recovery facts it still carries (...) are historical evidence only: ..."
+            source = "task_status"
+        elif projection["blockers"]:
 ...
-        if recovery is not None and recovery["state"] == "ROLLBACK_ACCEPTED":
+        if recovery is not None and "ROLLBACK_ACCEPTED" in (recovery["state"], recovery.get("protected_state")):
             add("ROLLBACK_PENDING", ...)
+        if recovery is not None and recovery["state"] in _SETTLEMENT_PENDING:
+            add("RECOVERY_SETTLEMENT_PENDING", ..., "run recover: it settles the accepted recovery decision ...")
+        if recovery is not None and recovery["state"] == "SETTLEMENT_CONTRADICTION":
+            add("SETTLEMENT_CONTRADICTION", ...)
```

Результаты прототипа:

- Полный набор прототипа: 580 существующих + 4 новых теста = **584**, **1 FAIL, skip 1**. Падает только `test_web_alarm_projection.CloseoutTests.test_aborted_operation_no_longer_blocks` (`['RECOVERY_SETTLEMENT_PENDING'] != []`) — это сам контракт A-II, который требует решения.
- Все тесты RC-6 (10 модулей recovery_coordinator), RC-4, Context Pack и Server проходят без изменений.
- Пункты 1 и 3 сами по себе не ломают ни одного существующего теста.
- 4 новые регрессии на прототипе проходят:
  - `test_unsettled_abort_blocks_until_rc6_settles_it`;
  - `test_unsettled_adopt_blocks`;
  - `test_protected_rollback_of_a_verified_stage_keeps_blocking`;
  - `test_completed_task_with_open_recovery_is_read_only_history`.
- Те же 4 теста на коде HEAD падают **4/4** — чувствительность подтверждена.
- Прототип — evidence для постановки ремонта, а не поставка: в рабочее дерево не переносился.

## 8. FINDINGS вне scope (код не менялся)

- **F-1 (RC-4).**
  - `RollbackService.close` и `_complete_release` пишут глобальный claim store до записи сессии.
  - На завершённой TASK запись сессии отклоняется (`active_only`), claims при этом уже сняты (B5): сессия PARTIAL с `claims_released=false` и снятыми claims, повтор `close` не сходится.
  - Physical write нет; пока только legacy-данные.
  - **Proposal:** отказ RC-4 на неактивной TASK до любой записи.
- **F-2 (RC-1 / WA4-E).**
  - `OperationStore.begin/transition` допускают операции (и STARTED / UNKNOWN) на VERIFIED-этапе.
  - Mutation authority защищает F-C gate, но это вход в A-II.
  - **Proposal:** gating lifecycle операций по этапу — в scope WA4-E.
- **F-3 (RC-5 / RC-6), DECISION.** Для свежих REJECTED / stale резолюций терминальных операций RC-6 останавливается на `MANUAL_DECISION_REQUIRED`, а closeout разрешает закрытие (A10). Нужно согласовать одно правило; рекомендую оставить их advisory и не держать RC-6.
- **F-4.** Ответ `recover` на завершённой TASK повторяет recovery-NEXT в `reason`. Закрывается пунктом 3 §7.

## 9. Documentation impact

После ремонта и PASS:
- `23` — инвариант закрытия TASK при совместной семантике RC-5/RC-6 и read-only история;
- `24` — статус RC-5;
- `25` — журнал;
- `001` / `06` — по регламенту.

Сейчас ARCHITECTURE IMPACT — только findings. Статусы RC-5 / RC-6 я не менял. Канонические документы обновляет verifier.

## 10. Файлы

- Новые:
  - этот отчёт;
  - `probes/hyp_a_premature_closeout.py`, `probes/hyp_b_historical_next.py`, `probes/sensitivity_by_commit.py`, `probes/purity_and_authority_sweep.py`.
- Изменён `Документация/000_Задачи Claude.md`: ротация БЛОКОВ 1–3.
- Production-код и тесты не менялись. Commit / push не выполнялись. WA4-E не начат.

**NEXT:**
1. Пользователь — commit / push.
2. ChatGPT — GitHub-проверка вердикта.
3. Решение по §7 (A-II — DECISION) → отдельная TASK RC-5 Repair #2.
4. Повторная независимая приёмка RC-5.
5. После PASS — documentation closeout RC-5 и согласование WA4-E.
