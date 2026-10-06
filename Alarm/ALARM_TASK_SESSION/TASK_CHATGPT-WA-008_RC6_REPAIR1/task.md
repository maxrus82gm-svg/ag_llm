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
