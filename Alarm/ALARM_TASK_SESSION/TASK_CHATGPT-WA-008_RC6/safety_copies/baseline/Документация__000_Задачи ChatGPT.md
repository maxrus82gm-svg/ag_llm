# Задачи ChatGPT

**Назначение:** персональная operational task-card ChatGPT / GPT-5.6 Sol для проекта `ag_llm`. Глобальный router: [[000_Задачи для агента]]. Канонический регламент: [[18_Регламент сопровождения документации]].

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

Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
TASK: —

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
