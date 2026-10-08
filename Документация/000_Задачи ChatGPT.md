# Задачи ChatGPT

**Назначение:** персональная operational task-card ChatGPT / GPT-5.6 Sol для проекта `ag_llm`. Глобальный router: [[000_Задачи для агента]]. Канонический регламент: 18_Регламент сопровождения документации.

## Правила

- БЛОК 1 — только текущая утверждённая TASK ChatGPT.
- После фактического завершения: полная постановка → БЛОК 2; factual result → БЛОК 3; затем БЛОК 1 очищается.
- До независимой проверки не писать `DONE / VERIFIED`.
- Scope ограничивает изменения, но не глубину анализа; перед RESULT READY обязателен adversarial pass.
- Permanent history (`05/06/25` и другие канонические closeout-документы) обновляет verifier после PASS.
- Не commit / push без явной команды пользователя.


### Порядок ChatGPT: GitHub-first review и Remote Alarm

**Только для ChatGPT.** Когда пользователь сообщает, что Codex или Claude завершил TASK, запушил изменения и передал отчёт, первым делом проводить независимую **read-only проверку на GitHub**: найти фактический commit, сопоставить diff с TASK/отчётом, проверить затронутые файлы, тестовые доказательства, инварианты, риски и возможные расхождения. Не начинать такую приёмку с Desktop Commander. Не утверждать, что runtime-тесты были запущены, если они не запускались.

По результатам GitHub-review определить и обсудить с пользователем дальнейшее действие: PASS/closeout, доработка самим ChatGPT либо возврат задачи Codex/Claude. Исполнитель исправления назначается **после анализа**, а не заранее. Если по GitHub не хватает доказательств, допустима адресная read-only проверка через Remote после первичного GitHub-review.

**Перед первым локальным изменением ChatGPT через Desktop Commander** включить предусмотренный `Alarm/ALARM_TASK_SESSION/00_INSTRUCTION.md` task-session protocol: зафиксировать исходное состояние, план и `INTENT`; во время работы сохранять `DONE`, результаты проверок и краткий recovery handoff. При обрыве сначала сверить фактические данные, не повторять mutation вслепую. Для чистого GitHub-review без локальных изменений Alarm-сессию создавать не нужно.

Этот порядок **не является задачей или обязательным протоколом для локальных Codex/Claude**: они используют собственные правила и не обязаны вести ChatGPT Remote Alarm. Commit/push от ChatGPT — только по явной команде пользователя.

---
# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

**Статус:** ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.
**TASK:** —

RC-6 Repair #1 фактически выполнен исполнителем и перенесён в БЛОКИ 2–3.

Текущий статус RC-6:
**RESULT READY / AWAITING RE-VERIFICATION**.

До независимого PASS:
- не считать RC-6 DONE / VERIFIED;
- WA4-E не начинать.

---
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена ChatGPT 2026-10-06; ожидает независимой re-verification.
**TASK:** CHATGPT-WA-008 / RC-6 — REPAIR #1.
**Baseline:** commit 159 / 26111c9e39f8b9de90f1b91b6a75b74bd0412e6d.
**Report:** Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/rc6_repair1_report.md.

# CHATGPT-WA-008 / RC-6 — REPAIR #1

**Status:** RESULT READY / AWAITING RE-VERIFICATION
**Executor:** ChatGPT / GPT-5.6 Sol
**Baseline at start:** commit 159 `26111c9e39f8b9de90f1b91b6a75b74bd0412e6d` (GitHub == local, clean tree).
**Independent verifier:** Claude Opus 5.5.
**Verdict entering repair:** VERIFICATION FAILED / REPAIR REQUIRED.
**WA4-E:** NOT STARTED / forbidden until fresh independent PASS.

## Scope

Repair only RC-6 defects B1–B5 found by the independent verifier, plus make F1/F2 semantics truthful without inventing a new global state machine or changing accepted RC-4 destructive semantics.

### B1 — settlement steals recovery focus forever
- Settlement must distinguish pending administrative work from historical completed fact.
- After ADOPT settlement is administratively complete and its microtask advances to VERIFIED, it remains history but must not capture top-level NEXT.
- ADOPT m1 VERIFIED + m2 ACTIVE => recover must target m2 and return truthful READY if all READY invariants hold.
- All microtasks VERIFIED => TASK_READY_TO_CLOSE, not FINISH_SETTLEMENT on historical m1.

### B2 — false READY after foreign claim appears
- READY proof for resolution-driven execution must inspect authoritative global RC-3 claim state for the resolution affected-target set, not task-local projection ownership only.
- Foreign owner present during final readiness proof => RECOVERY_BLOCKED.
- Same for primary and secondary affected targets.
- RC-6 remains read-only for readiness claim proof; WA4-E must later acquire/recheck authority before physical mutation.

### B3 — operation microtask != project current microtask
- Recovery decisions operate on the lifecycle state of `operation.microtask_id`, never substitute `position.current_status` from another microtask.
- Before any persistent settlement write, preflight that the operation microtask transition/interpretation is legal.
- No half-settlement: if lifecycle action is illegal, fail closed before mutation.
- Historical operation in an already VERIFIED microtask must not become executable because a later microtask is ACTIVE.

### B4 — own RC-4 effects incorrectly become stale
- Projection must align with `RollbackService._session_basis()` semantics.
- Before any own rollback effect, stale Resolver evidence may classify rollback as stale.
- After persistent own effects/touched target state (RC-4 statuses treated as touched, including RESTORED/APPLYING/FAILED), raw Resolver freshness alone must not classify the tracked session stale.
- Surface current persistent rollback state and let RC-4 `apply()` reconcile/resume from receipts/current bytes.
- Do not auto-close an interrupted rollback merely because its original evidence fingerprint changed due to its own effects.

### B5 — false READY with invalid restore point
- READY_FOR_EXECUTION requires a verified restore point for the actual execution microtask when it may mutate Workspace.
- `restore_point.status = NOT_VERIFIED` => never READY.
- If NOT_APPLICABLE is ever allowed, it must be mechanically limited to a genuinely non-mutating stage; do not assume it here.

## F1 policy — ABORT / RECOVERY_REQUIRED
- Do not invent a new global lifecycle transition in this repair.
- After ABORT, RECOVERY_REQUIRED is a truthful MANUAL PROJECT DECISION boundary.
- NEXT must not claim a mechanically unsupported 'new operation' path.
- If correctness requires a new global status/transition: STOP / DECISION REQUIRED.

## F2 policy — partial/failed rollback close
- If rollback has physical own effects and safe terminal correctness is not proved, do not auto-close/release claims.
- Return MANUAL_DECISION_REQUIRED or RECOVERY_BLOCKED and preserve ownership.
- Automatic close is allowed only for pre-effect stale/superseded/aborted cleanup with no in-flight fate and no destructive rollback effect begun.
- ABORT + in-flight may use RC-4 apply only to reconcile the already-started target effect; must not blindly continue untouched destructive targets after authority revocation.

## Truthful READY contract
Before any READY_FOR_EXECUTION prove at least:
- active TASK;
- no projection blocker;
- exact execution microtask;
- executable lifecycle status for that microtask;
- valid restore point for that microtask;
- recovery resolution (if any) remains current/fresh;
- operation belongs to that microtask;
- no unsafe/open rollback;
- no incompatible foreign ownership across affected targets;
- no pending settlement administrative work.

## Settlement ordering
PRE-PROVE -> WRITE SETTLEMENT -> WRITE MICRO LIFECYCLE -> RELEASE OWN CLAIM -> REBUILD PROJECTION.
Crash points must be replay-safe:
- before settlement: nothing written;
- after settlement before micro update: fresh process finishes once;
- after micro update before claim release: release-only;
- after release: settlement historical, not operational focus.

## Mandatory regression matrix
- B1-A ADOPT -> DONE -> VERIFIED -> next ACTIVE -> READY next micro.
- B1-B ADOPT -> all VERIFIED -> TASK_READY_TO_CLOSE.
- B2 primary foreign claim after RETRY re-arm -> second recover != READY.
- B2 secondary foreign claim same.
- B3-A old operation belongs VERIFIED m1 + m2 ACTIVE + RETRY -> never READY old op.
- B3-B same + ABORT -> no half-settlement write.
- B4 crash after first RESTORED before next target -> fresh recover resumes RC-4.
- B4 T_APPLYING write landed -> reconcile/no double write/continue.
- B4 T_APPLYING write not landed -> reconcile/single restore/continue.
- B4 VERIFIED + claims_released=false -> finish release only.
- B5 ACTIVE + corrupt restore point -> never READY.
- ADOPT crash after settlement before micro update -> fresh process finishes once.
- ABORT crash after settlement before RECOVERY_REQUIRED -> fresh process completes administrative closure, remains manual.
- settled + own claim active -> release-only.
- multiprocess RETRY readiness vs foreign acquire on primary and secondary target.

## Verification
Run at minimum:
- Repair #1 focused tests;
- existing RC-6 focused/concurrency/adversarial;
- Projection + concurrency;
- Resolver + concurrency;
- RC-3;
- RC-4 + concurrency;
- Server/CLI;
- full explicit `test_web_alarm_*.py`;
- `python -B -m compileall -q web_alarm`;
- `git diff --check`;
- independent adversarial pass.

All mutation/crash/concurrency tests use isolated temp storage. Live WEB-02 is read-only only, with before/after deterministic tree evidence.

## Out of scope / STOP
Do not implement WA4-E, WA4-A, WA4-O, WA4-R, Program scheduler, lease/heartbeat, OS transaction, or a new global microtask state machine.
If correctness requires a new global status/transition, fundamental RC-4 destructive lifecycle change, or Resolver ABORT semantic change: STOP / DECISION REQUIRED.

## Report / rotation
Create `rc6_repair1_report.md` in this task session.
After factual completion: Repair #1 task -> ChatGPT Block 2; factual result -> Block 3; Block 1 waiting; status only `RESULT READY / AWAITING RE-VERIFICATION`.
Do not write DONE/VERIFIED. Do not commit/push. WA4-E not started.

---
### СОХРАНЁННЫЙ ПРЕДЫДУЩИЙ RC-6 RECORD
Ниже сохранён предыдущий executor record до Repair #1. Он исторический и не подменяет текущий Repair result.

## PRIOR RC-6 EXECUTOR RECORD — PRE-REPAIR BLOCK 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена ChatGPT 2026-10-06; ожидает независимой проверки.
**Связь:** полный factual result — БЛОК 3; детальный report — `Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/rc6_report.md`.

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

---
# БЛОК 3 — ОПЕРАЦИОННЫЙ РЕЗУЛЬТАТ
---

**Статус:** RESULT READY / AWAITING RE-VERIFICATION.
**Дата:** 2026-10-06.
**TASK:** CHATGPT-WA-008 / RC-6 — REPAIR #1.
**Baseline:** commit 159 / 26111c9e39f8b9de90f1b91b6a75b74bd0412e6d.
**WA4-E:** NOT STARTED.

### Исправлено

- B1: completed settlement больше не захватывает top-level recovery focus; ADOPT history не мешает следующей microtask/closeout.
- B2: final READY proof читает authoritative global RC-3 ownership по affected target set; foreign primary/secondary owner блокирует READY.
- B3: recovery управляет lifecycle только operation.microtask_id; settlement preflight выполняется до persistent settlement write; half-settlement устранён.
- B4: Projection выровнена с RC-4 restart semantics; own effects / in-flight / persisted DRIFTED-before-finalize / release-pending идут через RC-4, а не stale cleanup.
- B5: ACTIVE без VERIFIED restore point никогда не READY.
- F1: ABORT остаётся truthful MANUAL boundary в RECOVERY_REQUIRED; новый global transition не изобретён.
- F2: PARTIAL/FAILED rollback не auto-close и не release; ownership сохраняется до explicit disposition.

### Дополнительный adversarial finding исполнителя

Найден и исправлен соседний crash window:
T_APPLYING -> T_DRIFTED persisted -> crash before RC-4 finalize.

Он теперь:
- не превращается в ROLLBACK_STALE_OPEN;
- дозавершается через RC-4;
- при later ABORT финализирует только already-persisted outcome;
- не продолжает untouched restore;
- после FAILED/PARTIAL сохраняет claims и возвращает RECOVERY_BLOCKED.

### Проверки

- Repair #1 permanent regressions: **21/21 PASS**.
- Core RC-3/4/5/6 focused: **176/176 PASS**.
- Public Server/CLI + Coordinator/Repair: **55/55 PASS**.
- Original Claude verifier probes без изменения скриптов: **exit 0 / exit 0**.
- Full explicit test_web_alarm_*.py: **439 tests OK, skipped=1**.
- compileall: PASS.
- git diff --check: PASS.
- Live storage before/after: **136 files / 41 dirs / SHA-256 a9cf87815774d5abdfb8a433af8aca13002d292a2866aa2b27a8901f24c9bff3 unchanged**.

### Evidence

- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/rc6_repair1_report.md
- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/final_verification_v3.md
- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/claude_probes_replay.txt
- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/safety_copies/

### Scope

Не реализованы и не начаты:
- WA4-E;
- WA4-A;
- WA4-O;
- WA4-R;
- Program/Stage scheduler;
- новый global Microtask lifecycle.

Known in-scope correctness blocker после executor adversarial pass: **none**.

**NEXT SAFE ACTION:** пользователь commit/push текущего Repair #1 worktree, затем независимый verifier повторно проверяет freshest GitHub commit. До PASS — RC-6 не DONE/VERIFIED и WA4-E не запускать.

---
### СОХРАНЁННЫЙ ПРЕДЫДУЩИЙ RC-6 RECORD
Ниже сохранён предыдущий executor result до Repair #1. Независимая проверка обнаружила в нём B1–B5; текущий Repair result выше является актуальным executor result.

## PRIOR RC-6 EXECUTOR RECORD — PRE-REPAIR BLOCK 3 — ОПЕРАЦИОННЫЙ РЕЗУЛЬТАТ
---

**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**Дата:** 2026-10-06.
**TASK:** CHATGPT-WA-008 / RC-6 — Project-level Recovery Closure.
**Стартовый baseline:** commit 156 `897d724b74843740ce2b936fcb6671106bb2dee0`.
**Промежуточный user commit:** commit 157 `6042033180e26235234389dcf81e4068cdfd440b` — M1 settlement/projection + activation docs.
**Текущий M2/M3:** незакоммиченный worktree поверх commit 157; commit/push делает пользователь.

### Фактический результат

- добавлен bounded `RecoveryCoordinator.recover(task_id)`;
- один coordinator использует fresh RC-5 Projection как canonical read model и не создаёт competing truth;
- normal physical execution не выполняется: `RETRY` только re-arm → `READY_FOR_EXECUTION`; WA4-E не начат;
- ADOPT получил durable settlement: full affected-target locking, fresh-authority recheck, exact server-observed post-state receipt, Operation VERIFIED, Microtask DONE, own claim cleanup, затем `READY_FOR_VERIFICATION`;
- ABORT получил durable settlement без стирания forensic execution status; Microtask → RECOVERY_REQUIRED;
- ROLLBACK использует существующий RC-4 prepare/apply/reconcile/release и затем durable ROLLBACK settlement;
- open/stale/superseded rollback cleanup не скрывается; superseded/stale in-flight и multiple-open fail-closed/manual;
- RETRY/ADOPT блокируются чужим RC-3 claim на любом target из Resolver basis, включая secondary target;
- найден и закрыт race `old RETRY -> newer ABORT`: перед действием и под target locks exact resolution_id повторно доказывается как текущая Resolver authority;
- Server `POST /tasks/{id}/recover` переведён с advisory stub на RC-6 coordinator;
- CLI: `task recover`;
- TASK completion остаётся отдельным Closeout gate.

### Concurrency / restart

Доказано отдельными процессами:

- recover vs recover (RETRY) → единый READY, без physical write;
- recover vs recover (ROLLBACK) → одна tracked rollback session, no duplicate restore;
- recover vs newer Resolver ABORT → старый RETRY fail-closed;
- recover vs new operation → новый claim CONFLICT / authority=false, старый owner не потерян;
- fresh process после ADOPT settlement до Microtask/claim cleanup дозавершает administrative closure без повторного effect;
- bounded step interruption → последующий recover безопасно продолжает persistent lifecycle.

### Adversarial

Проверены:

- ABORT/open rollback;
- RETRY/ADOPT superseding open rollback;
- stale open rollback;
- ABORT + T_APPLYING;
- superseded in-flight rollback;
- multiple open rollback sessions;
- corrupt checkpoint;
- stale Recovery Report;
- foreign primary/secondary target claims;
- projection contradiction;
- completed TASK;
- closeout-eligible TASK;
- false READY;
- step-budget exhaustion/replay.

### Проверки

- baseline full Web Alarm: **379/379 PASS**;
- RC-6 integration/concurrency/adversarial final focused: **35/35 PASS**;
- финальный full Web Alarm: **416 tests, OK, skipped=1, 0 failures/errors**;
- `python -B -m compileall -q web_alarm`: PASS;
- `git diff --check`: PASS;
- live WEB-02 storage before/after: **136 files / 41 dirs, SHA-256 `b22a803d9f9405cc1b8a99f567fb8c26a708f131ff6aa0a8803e48294068aa14` unchanged**.

### Evidence

- Report: `Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/rc6_report.md`
- Task: `Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/task.md`
- Full final regression: `final_regression_v2.txt`
- Safety: `safety_copies/baseline/`, `safety_copies/m2_pre/`, `safety_copies/pre_closeout/`

### Findings / deferred

Known in-scope RC-6 correctness blocker after adversarial/full regression: **none**.

Deferred exactly by scope:
- WA4-E authoritative physical Executor;
- STARTED-before-write integration;
- WA4-A normal-executor lost-response injection;
- UI/HTML WA4-O;
- scheduler/multi-model Program;
- strict rollout WA4-R.

Existing P2 remains future WA4-E/UX input: legitimate rollback target locks can make a normal writer wait/timeout.

**WA4-E:** NOT STARTED.

**NEXT SAFE ACTION:** пользователь commit/push текущего RC-6 worktree → другой agent/model независимо проверяет freshest commit. До independent PASS не писать DONE/VERIFIED и не начинать WA4-E.
