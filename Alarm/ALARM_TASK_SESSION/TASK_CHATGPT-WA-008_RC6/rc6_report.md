# RC-6 Report — CHATGPT-WA-008

**Status:** RESULT READY / AWAITING INDEPENDENT VERIFICATION  
**Executor:** ChatGPT / GPT-5.6 Sol  
**Date:** 2026-10-06  
**Stage:** RC-6 — Project-level Recovery Closure / bounded one-command recovery-resume coordinator  
**WA4-E:** NOT STARTED

## 1. Baseline and continuity

RC-6 was approved in Chat before any Remote work.

Initial runtime baseline at RC-6 start:

- commit 156: `897d724b74843740ce2b936fcb6671106bb2dee0`;
- local HEAD == GitHub HEAD;
- baseline full Web Alarm regression: **379/379 PASS**;
- `python -B -m compileall -q web_alarm`: PASS;
- `git diff --check`: PASS.

During the interrupted RC-6 session the user committed/pushed commit 157:

- commit 157: `6042033180e26235234389dcf81e4068cdfd440b`;
- this commit contains the already completed M1 settlement/projection work plus RC-6 activation/safety documentation;
- it also contains user/external Obsidian changes. RC-6 did not intentionally edit or revert those files.

M2/M3 were continued on a clean commit-157 worktree. The final uncommitted RC-6 coordinator/public-entry/test work remains on top of commit 157 for user review/commit.

## 2. Safety / task session

Task session:

`Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/`

Persisted evidence includes:

- `task.md` — approved RC-6 scope;
- `baseline.md`;
- `baseline_regression.txt`;
- `api_contract_inspection.txt`;
- `m2_pre.md`;
- `safety_copies/baseline/`;
- `safety_copies/m2_pre/`;
- `final_regression.txt`;
- `final_regression_v2.txt`;
- this report.

All mutation/concurrency/adversarial tests used isolated temporary storage/workspaces.

The live WEB-02 storage was treated read-only. Final regression recorded:

- before: 136 files / 41 directories;
- file-tree SHA-256: `b22a803d9f9405cc1b8a99f567fb8c26a708f131ff6aa0a8803e48294068aa14`;
- after: same file count, directory count and hash.

Therefore the final regression produced **zero live-storage change**.

## 3. Architecture implemented

RC-6 introduces one canonical project-level orchestration service:

`web_alarm/recovery_coordinator.py`

Public service contract:

`RecoveryCoordinator.recover(task_id, max_recovery_steps=...)`

The coordinator:

1. builds fresh RC-5 Projection;
2. classifies the authoritative recovery state;
3. performs at most one mechanically safe recovery/administrative step;
4. rebuilds fresh Projection;
5. repeats in a bounded loop;
6. stops before any WA4-E normal physical execution boundary.

It does not create a parallel source of truth. Final state/NEXT always comes from the fresh projection after authoritative state mutations.

Returned machine-readable result contains at least:

- state;
- reason;
- requires_human;
- ready_for_execution;
- initial/final projection fingerprints;
- performed_steps;
- blocked_by;
- next_safe_action;
- authority_source;
- task_id;
- recovery_state;
- final projection;
- error when fail-closed.

Bounded step exhaustion returns fail-closed and never loops indefinitely.

## 4. Durable recovery settlement

A recovery settlement field was added to contract-v2 Operation records:

`recovery_settlement = { action, resolution_id, basis_operation_revision, settled_at }`

This is backward compatible:

- legacy records do not gain/migrate the field on read;
- v2 validation checks the field strictly when present;
- normal generic `OperationStore.transition()` rules were not weakened.

Recovery-only settlement is an internal lock-held primitive and is not a general public transition.

### ADOPT

ADOPT means:

- accepted Resolver ADOPT must still be current authority;
- evidence must still be fresh;
- all Resolver-basis physical targets are locked in deterministic physical-key order;
- foreign RC-3 ownership on any affected target blocks settlement;
- authority/freshness is re-proved after target locks are held;
- exact current post-state is server-observed;
- normal receipt is persisted;
- Operation becomes VERIFIED;
- durable recovery settlement = ADOPT;
- Microtask becomes DONE;
- own RC-3 claim is released;
- coordinator stops at READY_FOR_VERIFICATION.

No physical effect is repeated.

### ABORT

ABORT means:

- accepted ABORT must still be the authoritative Resolver action;
- evidence/history is preserved;
- original forensic execution status is not rewritten to fake success/failure;
- durable recovery settlement = ABORT;
- Microtask becomes RECOVERY_REQUIRED;
- own claim is released when safe;
- coordinator stops at MANUAL_DECISION_REQUIRED.

ABORT never marks the microtask VERIFIED.

### ROLLBACK

ROLLBACK reuses RC-4 only:

- no second rollback engine was added;
- fresh accepted ROLLBACK prepares/reuses the tracked RC-4 session;
- RC-4 preservation/claims/CAS/restore/post-proof/release semantics remain authoritative;
- after RC-4 reaches VERIFIED with claims released, RC-6 persists operation recovery settlement = ROLLBACK;
- original forensic execution status remains intact;
- Microtask becomes RECOVERY_REQUIRED;
- the rollback proves the old attempt was undone, not that the normal operation succeeded;
- final state requires a new recovery/execution decision rather than silently executing.

## 5. RETRY boundary with WA4-E

Fresh accepted RETRY is administrative re-arm only.

RC-6:

- re-proves accepted RETRY freshness;
- re-proves that this exact resolution is still the Resolver-authoritative resolution;
- verifies operation revision;
- verifies no tracked rollback remains open;
- locks the full Resolver affected-target set;
- rejects foreign RC-3 ownership on any affected target;
- re-proves Resolver authority/freshness under those locks;
- changes only the Microtask lifecycle to ACTIVE when legal;
- returns READY_FOR_EXECUTION.

RC-6 does **not**:

- acquire new execution ownership for WA4-E;
- write/delete/create a Workspace target;
- execute the RETRY effect;
- perform STARTED-before-write executor integration.

That boundary remains WA4-E.

## 6. Rollback-state matrix

Coordinator behavior for RC-5/RC-4 projected states:

- `ROLLBACK_ACCEPTED` → prepare tracked RC-4 session;
- `ROLLBACK_PREPARED` → finish preservation via RC-4 prepare replay;
- `ROLLBACK_PRESERVED / AUTHORIZED / APPLYING` → RC-4 apply/reconcile;
- `ROLLBACK_VERIFIED + claims_released=false` → RC-4 apply finishes release only;
- `ROLLBACK_VERIFIED + claims_released=true` → durable ROLLBACK settlement;
- `ROLLBACK_ABORTED_OPEN` → close old rollback non-destructively, then ABORT settlement;
- `ROLLBACK_ABORTED_IN_FLIGHT` → RC-4 apply is used only to reconcile the already-interrupted target fate under the accepted ABORT contract, then session closes; no blind continuation;
- `ROLLBACK_SUPERSEDED_BY_RETRY/ADOPT/...` when not in-flight → close old session before following newer Resolver authority;
- `ROLLBACK_STALE_OPEN` → close, never destructive stale apply;
- `ROLLBACK_SUPERSEDED_IN_FLIGHT` → RECOVERY_BLOCKED/manual;
- `ROLLBACK_STALE_IN_FLIGHT` → RECOVERY_BLOCKED/manual;
- `ROLLBACK_MULTIPLE_OPEN` → RECOVERY_BLOCKED/manual, no silent session selection;
- terminal CLOSED/PRESERVATION_FAILED → manual/new reconciliation semantics.

No fundamental RC-4 lifecycle change was required.

## 7. Ownership / claim safety

RC-6 does not create a second ownership system.

For RETRY and ADOPT, the coordinator protects the entire Resolver basis target set with the existing RC-3 target-lock namespace, in deterministic physical-key order.

It rejects a foreign active claim on:

- the operation target;
- any secondary affected target in the same recovery basis.

It never releases another operation's claim.

For already-settled own operations, the existing RC-3 owner-release path is reused.

## 8. Resolver race fix found during adversarial review

A specific race was found while implementing RC-6:

1. Coordinator classifies old accepted RETRY.
2. Before RETRY re-arm, another process accepts ABORT.
3. The old RETRY can still be evidence-fresh because ABORT itself does not change target bytes/revision.

Checking only RETRY freshness was therefore insufficient.

Fix:

- under the operation TASK lock, RC-6 also calls Resolver authoritative-selection facts;
- the exact resolution_id about to execute must still be the current authoritative resolution;
- after full target locking it re-checks authority/freshness again.

Deterministic multiprocess test proves:

- old RETRY is stopped fail-closed;
- Microtask is not re-armed;
- later ABORT remains authority;
- a subsequent recover settles ABORT normally.

## 9. Restart / replay / lost-response safety

Persisted settlement plus RC-4 state are sufficient for a fresh process.

Covered scenarios include:

- repeated recover on clean/RETRY state;
- repeated recover after ADOPT;
- step-budget interruption followed by fresh resume;
- lost response after ADOPT operation settlement but before Microtask/claim cleanup;
- rollback process restart/replay through RC-4;
- two simultaneous recover processes on RETRY;
- two simultaneous recover processes on one ROLLBACK session.

A fresh process finishes the administrative cleanup from durable facts and does not repeat the physical effect.

WA4-A normal-executor lost-response injection remains NOT STARTED.

## 10. Concurrency

Real subprocess tests cover:

### recover vs recover — RETRY

Two processes start together.

Result:

- both converge to READY_FOR_EXECUTION;
- no physical Workspace write;
- one deterministic microtask state;
- old operation remains forensic STARTED.

### recover vs recover — ROLLBACK

Two processes start together.

Result:

- both converge to MANUAL_DECISION_REQUIRED after safe rollback closure;
- exactly one tracked rollback session exists;
- restore is not duplicated;
- rollback settlement is single/durable.

### recover vs new Resolver action

Coordinator pauses after classifying RETRY.
Another process accepts ABORT.
Old RETRY re-arm is refused because it is no longer Resolver-authoritative.

### recover vs new operation

Old recovery operation already owns the target.
A concurrent new operation attempts claim/authorization.

Result:

- recovery remains READY_FOR_EXECUTION;
- new operation claim = CONFLICT;
- new mutation authority = false;
- old owner remains owner;
- Workspace bytes unchanged.

No global server lock was added.

## 11. Public one-command entry

Existing placeholder route was upgraded instead of adding a competing endpoint:

- Server: `POST /tasks/{task_id}/recover`;
- optional JSON `max_recovery_steps`;
- returns RC-6 coordinator result.

CLI:

- `webalarm task recover --task-id ...`;
- optional `--max-recovery-steps`.

The old `advisory_only / WA-3_NOT_IMPLEMENTED` stub is removed.

UI/HTML was not redesigned.

## 12. Checkpoint / report authority

Coordinator reads fresh Projection directly.

Tests prove:

- corrupt checkpoint JSON cannot steer recovery;
- stale Recovery Report cannot override fresh Resolver RETRY;
- checkpoint/report remain derived/history evidence only.

## 13. Closeout / completed TASK

Coordinator does not silently complete a TASK.

Covered:

- completed TASK → TASK_COMPLETED, no mutation;
- all microtasks VERIFIED + clean closeout → TASK_READY_TO_CLOSE;
- TASK remains active/PLANNED until explicit CloseoutService completion.

READY_FOR_EXECUTION is never treated as TASK completion.

## 14. False-READY protection

Coordinator refuses READY on known contradictions including:

- Projection blockers such as multiple ACTIVE/later-stage lifecycle contradiction;
- unresolved reconciliation without accepted action;
- stale accepted resolution;
- foreign target ownership;
- open unsafe rollback;
- superseded/stale in-flight rollback;
- multiple open rollback sessions;
- unhandled recovery states.

Fail-closed is preferred to guessed continuation.

## 15. Files changed by RC-6

### M1 / commit 157

Runtime:

- `web_alarm/models.py`
- `web_alarm/operation_contract.py`
- `web_alarm/operation_store.py`
- `web_alarm/projection.py`
- `web_alarm/task_store.py`

Tests:

- `test_web_alarm_recovery_coordinator.py` initial settlement tests

Operational documentation/task-session material was also added/updated.

### M2/M3 — current uncommitted worktree on top of commit 157

Runtime:

- `web_alarm/recovery_coordinator.py` — new
- `web_alarm/server.py`
- `web_alarm/cli.py`
- `web_alarm/__init__.py`

Tests:

- `test_web_alarm_recovery_coordinator.py`
- `test_web_alarm_recovery_coordinator_concurrency.py` — new
- `test_web_alarm_recovery_coordinator_adversarial.py` — new
- `test_web_alarm_server.py`
- `test_web_alarm_cli.py`

Documentation/task-session closeout:

- `Документация/000_Задачи ChatGPT.md`
- `Документация/000_Задачи для агента.md`
- this RC-6 report and task-session evidence.

Permanent history documents are intentionally not being marked DONE/VERIFIED by the executor.

## 16. Verification

Baseline:

- full Web Alarm: **379/379 PASS**;
- compileall: PASS;
- diff-check: PASS.

Focused intermediate checks:

- settlement primitives + operation contract/store: **35/35 PASS**;
- settlement + Projection integration: **82/82 PASS**;
- coordinator/Resolver/Projection focused after authority fix: **86/86 PASS**;
- Server/CLI/public-entry smoke: **34/34 PASS**;
- multiprocess concurrency: PASS;
- RC-6 integration/concurrency/adversarial-only final check: **35/35 PASS**.

Final full regression, persisted in `final_regression_v2.txt`:

- **Ran 416 tests**
- **OK**
- **skipped=1**
- no failures/errors;
- compileall PASS;
- `git diff --check` PASS;
- live storage hash before == after.

The one skipped test is recorded as a skip by the existing full suite and is not a failure.

## 17. Adversarial coverage

Explicitly exercised:

- crash/lost response after settlement before cleanup;
- rollback interrupted with T_APPLYING;
- ABORT after interrupted rollback;
- newer RETRY/ADOPT after old open rollback;
- stale open rollback;
- superseded in-flight rollback;
- multiple open rollback sessions;
- stale old RETRY vs newer ABORT;
- two recover processes;
- recover vs new operation ownership;
- foreign claim on primary target;
- foreign claim on secondary affected target;
- corrupt checkpoint;
- stale Recovery Report;
- projection lifecycle contradiction;
- completed TASK;
- closeout-eligible TASK;
- bounded-loop exhaustion and later resume.

## 18. Findings / deferred work

No in-scope RC-6 correctness blocker remains known after the adversarial pass and full regression.

Deliberately deferred:

- WA4-E authoritative physical Executor;
- STARTED-inside-held-claim-before-first-write;
- normal physical RETRY effect;
- WA4-A normal executor lost-response fault injection;
- UI/HTML operational control centre;
- Program/Stage scheduler and multi-model orchestration;
- lease/heartbeat;
- strict rollout / WA4-R.

Existing P2 remains relevant for WA4-E/UX: a normal writer may wait/timeout while rollback legitimately holds target locks, including NOOP protection windows. RC-6 does not redefine that policy.

## 19. Acceptance status

Executor conclusion:

**RESULT READY / AWAITING INDEPENDENT VERIFICATION**

Not claimed:

- DONE;
- VERIFIED;
- WA4-E started.

## 20. Independent reviewer checklist

Reviewer should independently:

1. query actual GitHub HEAD after user commit/push;
2. inspect commit 157 plus the later RC-6 commit/worktree delta;
3. read this report and the approved `task.md`;
4. review `recovery_coordinator.py`, settlement storage/validation, Projection settlement precedence, Server/CLI route;
5. specifically attack:
   - stale Resolver authority;
   - ADOPT post-state race;
   - secondary-target foreign claims;
   - ABORT/in-flight rollback;
   - superseded/stale in-flight rollback;
   - multiple-open rollback;
   - recover vs recover;
   - recover vs Resolver;
   - recover vs new operation;
   - false READY;
6. rerun focused RC-6 tests;
7. rerun full `test_web_alarm_*.py` suite explicitly;
8. run compileall and diff-check;
9. independently confirm no live-storage mutation;
10. only after PASS update permanent closeout/history and route to WA4-E.

## 21. NEXT SAFE ACTION

User reviews/commits/pushes the current RC-6 work.

Then a different agent/model performs independent verification of the freshest commit.

Until that PASS:

**WA4-E MUST NOT START.**
