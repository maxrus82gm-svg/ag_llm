# Задачи ChatGPT

**Назначение:** персональная operational task-card ChatGPT / GPT-5.6 Sol для проекта `ag_llm`. Глобальный router: [[000_Задачи для агента]]. Канонический регламент: 18_Регламент сопровождения документации.

## Правила

- БЛОК 1 — только текущая утверждённая TASK ChatGPT.
- После фактического завершения: полная постановка → БЛОК 2; factual result → БЛОК 3; затем БЛОК 1 очищается.
- До независимой проверки не писать `DONE / VERIFIED`.
- Scope ограничивает изменения, но не глубину анализа; перед RESULT READY обязателен adversarial pass.
- Permanent history (`05/06/25` и другие канонические closeout-документы) обновляет verifier после PASS.
- Не commit / push без явной команды пользователя.

---
# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

Статус: ACTIVE / IN PROGRESS
TASK: CHATGPT-WA-008 / RC-6

TASK: CHATGPT-WA-008 — RC-6
Project-level Recovery Closure: bounded one-command recovery / resume orchestration

Статус: ACTIVE / IN PROGRESS
Исполнитель: ChatGPT / GPT-5.6 Sol

Baseline: фактический HEAD проверяется перед работой. На старте RC-6 локальный/GitHub HEAD = commit 156 `897d724b74843740ce2b936fcb6671106bb2dee0`.

0. Место в маршруте
RC-0→RC-1→RC-2→RC-3→RC-4→RC-5→RC-6→WA4-E→WA4-A→WA4-O→WA4-R.
RC-6 — последний Recovery Closure перед authoritative Executor.

1. Решение о scope
Старый план описывал RC-6 как minimal read-only project-level resume. Утверждённая в Chat TASK расширяет этот scope до bounded Recovery Coordinator, сохраняя исходную one-command resume цель как обязательное подмножество.
RC-6 может выполнять только уже разрешённые административные/recovery действия и доводить TASK до READY_FOR_EXECUTION. Он не выполняет normal Workspace mutation следующей operation — это WA4-E.

2. Главная цель
Один canonical entry `recover(task_id)` / `resume(task_id)` должен:
- прочитать authoritative state через RC-5 Projection;
- классифицировать recovery;
- выполнить максимум один механически безопасный recovery-step за итерацию;
- reread fresh Projection;
- повторять bounded loop;
- остановиться на READY_FOR_EXECUTION / MANUAL_DECISION_REQUIRED / BLOCKED / COMPLETED / FAIL_CLOSED;
- вернуть один authoritative NEXT SAFE ACTION и bounded trace.

3. Authority
Coordinator не создаёт новую competing truth. После каждого mutation fresh Projection заново определяет final state/NEXT. Checkpoint и Recovery Report — только derived/history.

4. Граница RC-6 / WA4-E
RC-6 разрешено: inspect/reconcile; применять уже accepted Resolver recovery lifecycle; использовать RC-4 rollback; безопасно закрывать recovery sessions; rebuild derived projection/checkpoint; administrative transitions, необходимые для durable ADOPT/ABORT semantics.
RC-6 запрещено: выполнять physical normal RETRY/next operation, normal target write Executor'ом, STARTED-before-write WA4-E transaction, lost normal-executor response injection.

5. Result classes
Минимум различать: READY_FOR_EXECUTION, MANUAL_DECISION_REQUIRED, RECOVERY_IN_PROGRESS, RECOVERY_BLOCKED, TASK_COMPLETED, NO_ACTION_REQUIRED, FAIL_CLOSED. Точные names допустимо уточнить, semantics должны быть тестируемыми.

6. Bounded loop / replay
Нужен max_recovery_steps. Exhaustion → fail-closed. Повтор recover после process restart, lost response или repeated button press не создаёт duplicate effect/session/release и не перескакивает execution boundary.

7. Clean task
Clean non-recovery task → READY_FOR_EXECUTION/NO_ACTION_REQUIRED, zero Workspace writes.

8. Unresolved operation
STARTED/UNKNOWN_AFTER_DISCONNECT без accepted resolution → pure reconciliation + MANUAL_DECISION_REQUIRED. Server сам не выбирает RETRY/ADOPT/ABORT/ROLLBACK.

9. RETRY
Fresh accepted RETRY → validate freshness/claims/open rollback cleanup → READY_FOR_EXECUTION. Никакого physical retry в RC-6.

10. ADOPT
Определить durable lifecycle: physical post-state уже существует; effect не повторяется; Operation/Microtask/verification/projection/claims/closeout получают однозначную semantics. ADOPT не может быть просто снятием warning.

11. ABORT
Определить durable safe closure без стирания evidence. Учесть open/in-flight rollback и unknown physical fate. Не переводить microtask в VERIFIED искусственно.

12. ROLLBACK
Fresh accepted ROLLBACK → reuse existing RC-4 prepare/apply/close lifecycle, no second rollback engine. После verified rollback pre-state восстановлен, но normal operation ещё не выполнена; NEXT обычно ведёт к WA4-E retry/другому решению.

13. RC-5 Repair #1 states
Обработать ROLLBACK_ABORTED_OPEN, ROLLBACK_ABORTED_IN_FLIGHT, ROLLBACK_SUPERSEDED_BY_*, ROLLBACK_SUPERSEDED_IN_FLIGHT, ROLLBACK_STALE_OPEN, ROLLBACK_STALE_IN_FLIGHT, ROLLBACK_MULTIPLE_OPEN.
Safe automatic close только когда physical fate доказан. Superseded/stale + in-flight и multiple-open fail-closed/manual, если механически безопасный порядок не доказан.

14. Interrupted target fate proposal
Исследовать narrow RC-4 inspect-only reconcile primitive для T_APPLYING без destructive continuation. Допустим только если это узкий pure/fail-closed helper. Если требуется фундаментально менять RC-4 lifecycle → STOP / DECISION REQUIRED.

15. Ownership / serialization
Использовать RC-3 claims и existing task-level serialization. Не удалять claim по возрасту. Перед READY_FOR_EXECUTION не должно оставаться неожиданного recovery ownership.
Два concurrent recover(task) не могут расходиться по branch или делать double effect.

16. Races
Обязательны multiprocess: recover vs recover; recover vs Resolver new action; recover vs new operation. Revision/freshness recheck под serialization. No global server lock.

17. Restart / lost coordinator response
После meaningful phase fresh process должен продолжать из persistent facts. Lost response самого recover call → повтор safe. Lost response normal Executor mutation остаётся WA4-A.

18. Public entry
Минимум service `recover(task_id)`. Желательно CLI `task recover` и server `POST /tasks/{id}/recover`. Пользователь не оркестрирует RC-слои вручную.

19. Trace
Result включает initial/final projection fingerprint, performed/replayed/no-op steps, authority facts, stop reason, final state/NEXT. Bounded summary, не полный event dump.

20. False READY forbidden
Нельзя READY при projection contradiction, unresolved operation/ownership, stale accepted action, unsafe/open rollback, unknown interrupted fate, multiple open rollback sessions, task lifecycle contradiction.

21. Closeout
READY_FOR_EXECUTION != TASK COMPLETED. Coordinator не auto-complete TASK. CloseoutService остаётся отдельным explicit gate.

22. Projection/checkpoint/report
После authoritative recovery mutation → fresh Projection. Checkpoint optional derived write; его failure не отменяет recovery fact. Recovery Report не диктует current NEXT.

23. Future UI contract
Возвращать machine-readable state/reason/performed_steps/blocked_by/requires_human/allowed_actions/next_safe_action/ready_for_execution/projection_fingerprint. UI сейчас не делать.

24. Tests A–Z — минимум
A clean task; B unresolved/no auto-choice; C accepted RETRY no physical write; D durable ADOPT; E durable ABORT; F accepted ROLLBACK via RC-4; G open rollback+ABORT; H open rollback+RETRY; I open rollback+ADOPT; J stale open rollback; K in-flight+ABORT; L superseded/stale+in-flight fail-closed unless narrow helper proven; M multiple open rollback no silent selection; N repeated recover idempotent; O restart after each step; P lost recover response replay; Q concurrent recover; R recover vs new Resolver action; S recover vs new operation; T corrupt/stale checkpoint irrelevant; U stale Recovery Report irrelevant; V claim conflict blocked; W projection contradiction fail-closed; X completed task no mutation; Y closeout-eligible not silently completed; Z bounded-loop exhaustion no infinite loop.

25. Adversarial pass
Обязательно самостоятельно ломать: crash boundaries, rollback VERIFIED→claim release, Resolver revision mid-loop, stale RETRY, multiple ops/sessions, ADOPT drift, ABORT partial rollback, false READY, corrupted store, legacy live storage, loop off-by-one, replay after response loss. В-scope fix+regression; WA4-E/WA4-A findings не реализовывать.

26. Не делать
Не реализовывать normal authoritative Executor physical mutation, WA4-E STARTED-before-write, automatic physical RETRY, WA4-A fault injection, UI/HTML, multi-model orchestration, 10/20-stage scheduler, lease/heartbeat, OS transaction, strict rollout.

27. Acceptance
Один canonical recover entry; fresh Projection authority; deterministic clean READY; unresolved→human; RETRY prepared not executed; durable ADOPT/ABORT; ROLLBACK uses RC-4; open/stale rollback not lost; idempotent/restart/concurrency safe; Resolver race safe; claim safe; false READY impossible; full Web Alarm regression PASS; WA4-E NOT STARTED.

28. Workflow
Создать `Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/`, safety copies, baseline hashes/status/regression; live storage read-only; mutation/race tests only isolated temp storage; minimal diff; no commit/push.

29. Report
`Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/rc6_report.md`: baseline, state matrix, coordinator architecture, ADOPT/ABORT/ROLLBACK/RETRY semantics, concurrency/restart/replay/bounded loop, changed files, tests, live storage read-only evidence, adversarial findings, explicit WA4-E NOT STARTED.

30. Card rotation
После выполнения: полная постановка→БЛОК 2 `000_Задачи ChatGPT.md`; factual result→БЛОК 3; затем БЛОК 1 ожидание. Global 000 только router/status. Не уничтожать deferred 151C. RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не писать DONE/VERIFIED, не commit/push, WA4-E не начинать.

---
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена ChatGPT 2026-10-04. Результат — в БЛОКЕ 3.
**Связь:** это Repair #1 той же `CLAUDE-WA-007 / RC-5`; исходная полная RC-5 постановка хранится в `000_Задачи Claude.md`.

```text
TASK: CLAUDE-WA-007 — RC-5 INDEPENDENT REVIEW REPAIR #1:
An open tracked rollback must not disappear behind a later Resolver action

Статус:
REPAIR REQUIRED / RC-5 NOT VERIFIED

Исполнитель:
ChatGPT / GPT-5.6 Sol (Remote Desktop Commander)

Это продолжение той же CLAUDE-WA-007 / RC-5.
Это НЕ RC-6.

Baseline:
commit 155
1efc6793404e219cb97cbc665c12ecb8fde05b0d

Independent verification ChatGPT:

- RC-5/related focused regression: 158/158 PASS;
- full Web Alarm: 364/364 PASS;
- compileall PASS;
- git diff --check PASS;
- несмотря на зелёную регрессию, отдельный semantic probe нашёл blocker.

==================================================
1. BLOCKER
==================================================

Точный reproduction:

1. Operation находится в recovery state.
2. Resolver принимает fresh ROLLBACK.
3. RC-4 создаёт rollback session:
   status = PRESERVED.
4. После этого Resolver принимает ABORT для той же operation.
5. ProjectionService.build() возвращает:

authority_source = resolver
recovery.state = ABORT_ACCEPTED
rollback_id = None

NEXT SAFE ACTION:

"Resolver-level recovery of operation op_1 is closed;
no further ADOPT/RETRY/ROLLBACK will be accepted for it"

НО одновременно authoritative RollbackStore содержит:

rollback status = PRESERVED
claims_released = false
session ещё не CLOSED.

И closeout того же projection правильно содержит:

ROLLBACK_OPEN

Получается внутреннее противоречие:

top-level NEXT:
"recovery closed"

vs

authoritative RC-4 lifecycle:
"tracked rollback session still open".

RC-5 не может быть VERIFIED при таком расхождении.

==================================================
2. ROOT CAUSE
==================================================

Проверить:

web_alarm/projection.py

`_operation_recovery()` сейчас связывает rollback authority только с:

current authoritative Resolver resolution_id
→ rollback session с тем же resolution_id.

После принятия ABORT:

Resolver authoritative resolution = ABORT resolution

а существующая rollback session принадлежит более ранней
ROLLBACK resolution.

Поэтому session исчезает из operation-level recovery selection,
хотя сама persistent RC-4 session остаётся незавершённой.

`closeout_blockers()` затем отдельно замечает её как ROLLBACK_OPEN,
поэтому один projection выдаёт два разных operational conclusions.

==================================================
3. REQUIRED INVARIANT
==================================================

Незавершённая tracked RC-4 rollback session является authoritative
operational state сама по себе.

Она не должна исчезать из top-level recovery/NEXT только потому,
что позже появилась другая Resolver resolution.

Пока rollback session не достигла safe terminal state:

- CLOSED;
- PRESERVATION_FAILED;
- либо VERIFIED + claims_released=true;

projection обязана учитывать её как незавершённую recovery work.

При этом более поздний Resolver action МОЖЕТ менять,
ЧТО именно теперь разрешено делать с session.

Особенно:

accepted ABORT
НЕ означает:

"rollback session больше не существует".

Он означает:

"destructive rollback больше нельзя продолжать;
существующую tracked session надо привести к safe terminal state".

==================================================
4. НЕ ДЕЛАТЬ ПРОСТО "ROLLBACK ALWAYS WINS"
==================================================

Нельзя просто всегда показывать сохранённый:

session.next_safe_action

поверх Resolver.

Почему:

для PRESERVED session до ABORT он может говорить:

"apply the rollback"

но после accepted ABORT RC-4 правильно запрещает destructive apply.

Independent probe подтвердил:

apply after ABORT
→ BLOCKED
→ RECOVERY_ABORTED
→ zero destructive effect.

После этого RC-4 session можно безопасно close.

Поэтому нужен composite projection semantics:

ROLLBACK SESSION STATE
+
CURRENT RESOLVER AUTHORITY
→ CURRENT SAFE NEXT.

==================================================
5. EXPECTED SEMANTICS
==================================================

Минимальный смысл:

A. Nonterminal rollback + no later action that revokes it:
→ существующая RC-5 semantics остаётся;
→ rollback session ведёт NEXT.

B. Nonterminal rollback + accepted ABORT:
→ top-level recovery всё ещё обязана указывать rollback_id/session;
→ authority/NEXT не должны утверждать "всё закрыто";
→ destructive rollback continuation не рекомендуется;
→ NEXT должен вести к безопасному завершению tracked session.

Например по смыслу:

"Resolver recovery is ABORTED, but rollback <id> is still open;
do not continue destructive restore.
Close the tracked rollback session.
If an in-flight target has unknown fate, first reconcile that target
through the RC-4 interruption-safe path, then close the session."

Точная формулировка/field names — на усмотрение реализации.

C. После session CLOSED:
→ она больше не является open recovery authority;
→ accepted ABORT может нормально стать top-level Resolver state.

D. VERIFIED + claims_released=true:
→ settled historical rollback не должен вечным образом перехватывать
будущую recovery authority.

==================================================
6. IN-FLIGHT EDGE CASE
==================================================

Отдельно проверить session в APPLYING с target.status = APPLYING.

RC-4 close() в таком состоянии может вернуть TARGET_FATE_UNKNOWN.

RC-4 apply() сначала доказывает реальные bytes interrupted target,
и только затем проверяет session basis / ABORT.

Поэтому после ABORT projection должна давать безопасный NEXT:

- не "продолжай rollback";
- не "recovery закрыта";
- а "reconcile interrupted target fate through RC-4 safe apply path,
  then close the aborted rollback".

Не менять RC-4 ordering без необходимости.

==================================================
7. REQUIRED TESTS
==================================================

TEST AA — exact blocker:

ROLLBACK accepted
→ session PRESERVED
→ ABORT accepted
→ projection.

Должно быть НЕВОЗМОЖНО получить одновременно:

top-level "recovery closed"
+
ROLLBACK_OPEN.

Projection должна surface rollback_id/open-session cleanup.

TEST AB — Context Pack:

тот же scenario.

NEXT_SAFE_ACTION Context Pack
не говорит просто "recovery closed";
он совпадает с canonical projection cleanup NEXT.

TEST AC — RemoteEntry / Server projection:

тот же authoritative NEXT.

TEST AD — closeout consistency:

если closeout содержит ROLLBACK_OPEN,
top-level NEXT не может утверждать,
что recovery fully closed.

TEST AE — safe cleanup:

PRESERVED session + ABORT
→ projection рекомендует safe close;
→ RollbackService.close()
→ CLOSED;
→ rebuilt projection больше не считает session open.

TEST AF — apply-after-ABORT safety:

PRESERVED + ABORT
→ RollbackService.apply()
= BLOCKED / RECOVERY_ABORTED;
→ zero Workspace mutation;
→ projection после этого всё равно ведёт к safe session closure.

TEST AG — interrupted/in-flight rollback + ABORT:

session APPLYING / target APPLYING
→ projection явно требует interruption reconciliation before close;
→ не рекомендует новый destructive continuation;
→ после safe reconciliation + close session становится terminal.

TEST AH — settled rollback:

VERIFIED + claims_released=true
→ более поздний legitimate Resolver state не должен быть скрыт
исторической rollback session.

TEST AI — existing test remains:

unfinished rollback на op_1
по-прежнему outranks newer advisory reconciliation другой operation,
если это recovery, требующая внимания.

==================================================
8. ADVERSARIAL PASS
==================================================

AA–AI — только минимум.

Отдельно самостоятельно проверить:

- ABORT before rollback prepare;
- ABORT after PRESERVED;
- ABORT after AUTHORIZED;
- ABORT after interrupted APPLYING;
- ABORT after PARTIAL/FAILED;
- ABORT after VERIFIED but before claim release;
- ABORT after VERIFIED + released;
- multiple historical rollback sessions for one operation;
- stale ROLLBACK resolution + still-open session;
- open session + newer RETRY/ADOPT if such state can be created legally;
- Context Pack / Server / RemoteEntry / closeout all agree on ONE NEXT.

Если legal state cannot be created through public contracts:
зафиксировать это тестом/analysis, не invent semantics.

==================================================
9. SCOPE
==================================================

Это RC-5 projection repair.

Предпочтительно исправить:

web_alarm/projection.py
и RC-5 tests.

Допустимы минимальные изменения projection-facing helpers,
если нужны для точного описания session state.

НЕ менять без необходимости:

- RC-2 Resolver semantics;
- RC-4 rollback lifecycle;
- Operation state machine;
- RC-6;
- WA4-E;
- UI;
- lease/heartbeat;
- scheduler.

Если выяснится, что корректный answer требует изменения RC-4 lifecycle:
STOP → FINDING / DECISION REQUIRED.

==================================================
10. REGRESSION
==================================================

После repair:

- новые AA–AI;
- весь test_web_alarm_projection.py;
- projection concurrency;
- Context Pack;
- RemoteEntry;
- Server;
- Resolver;
- RC-4 + concurrency;
- RC-3 + concurrency;
- full Web Alarm regression;
- compileall;
- git diff --check;
- fresh-process projection reopen.

==================================================
11. REPORT
==================================================

Дополнить:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-007_RC5/rc5_report.md

разделом:

INDEPENDENT REVIEW REPAIR #1

Зафиксировать:

- exact reproduction;
- root cause;
- final precedence model;
- semantics open rollback + later ABORT;
- in-flight case;
- tests AA–AI;
- adversarial findings;
- full regression;
- RC-6 NOT STARTED.

==================================================
12. CARD ROTATION
==================================================

Это всё ещё CLAUDE-WA-007 / RC-5.

После фактического завершения:

1. БЛОК 2 сохраняет:
   - исходную RC-5 постановку;
   - repair #1.

2. БЛОК 3:
   factual result +
   tests +
   adversarial findings/proposals.

3. Статус:
RESULT READY / AWAITING INDEPENDENT VERIFICATION

4. После подтверждения сохранности БЛОКОВ 2–3:
БЛОК 1 →

Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
TASK: —

5. Не писать DONE / VERIFIED.

6. Не обновлять permanent history / global 000.

7. Не commit / push.

8. RC-6 НЕ начинать.

NEXT SAFE ACTION:

закрыть RC-5 Independent Review Repair #1,
сделать собственный adversarial pass,
остановиться на
RESULT READY / AWAITING INDEPENDENT VERIFICATION.

RC-6 НЕ НАЧИНАТЬ.
```

---
# БЛОК 3 — ОПЕРАЦИОННЫЙ РЕЗУЛЬТАТ
---

**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**Дата:** 2026-10-04.
**Baseline:** commit 155 `1efc6793404e219cb97cbc665c12ecb8fde05b0d`.
**RC-6:** NOT STARTED.

### Что изменено

- `web_alarm/projection.py`: open RC-4 session больше не исчезает за более поздней Resolver action; добавлена composite precedence для ABORT, superseding RETRY/ADOPT/ROLLBACK, stale basis, multiple open sessions и in-flight fail-closed.
- `test_web_alarm_projection.py`: добавлены regression/adversarial tests AA–AI и дополнительные legal-state scenarios.
- RC-2 Resolver и RC-4 rollback lifecycle не изменялись.

### Доказанный результат

- exact blocker `PRESERVED rollback + later ABORT` закрыт;
- Context Pack / Server / RemoteEntry / closeout согласованы по одному canonical NEXT;
- later accepted RETRY и ADOPT при open rollback не позволяют старому rollback получить destructive NEXT;
- stale open rollback требует cleanup/reconciliation, а не destructive apply;
- superseded/stale + in-flight без ABORT fail-closed на manual review;
- две легально достижимые open rollback-session одной operation surface как `ROLLBACK_MULTIPLE_OPEN`, ни одна не скрывается;
- settled rollback сохраняет historical outcome своей resolution, но не перехватывает более новую accepted action.

### Проверки

- `AdversarialRepairTests`: 17/17 PASS;
- `test_web_alarm_projection.py`: 47/47 PASS;
- related focused: 173/173 PASS;
- full Web Alarm: 379/379 PASS;
- `compileall`: PASS;
- `git diff --check`: PASS;
- live storage read-only: 136 files / 41 dirs; before == after; WA-3.6/WA-3.7 legacy-compatible.

### Findings / proposals

- Легально достижимы later accepted RETRY/ADOPT после `PRESERVED` rollback и несколько open rollback-session одной operation.
- Для полностью автоматического cleanup `superseded/stale + T_APPLYING` нужен отдельный RC-4 inspect/reconcile-only primitive или lifecycle decision. Сейчас projection безопасно требует manual review; это не блокирует RC-5 correctness.
- После принятия RC-5 всё ещё требуется перезапуск WEB-02 процессов из исходного F3, чтобы старые процессы не работали со старой projection/checkpoint semantics.

### Evidence

- Report: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-007_RC5/rc5_report.md`, §21.
- Safety copies: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-007_RC5/safety_copies/chatgpt_repair1/`.
- Baseline/result hashes: `chatgpt_repair1_baseline.txt`, `chatgpt_repair1_result.txt`.

**NEXT SAFE ACTION:** пользователь commit/push → независимый verifier проверяет самый свежий commit. До PASS RC-6 не начинать.
