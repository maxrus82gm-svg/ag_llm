# RC-6 Repair #1 Report — CHATGPT-WA-008

**Status:** RESULT READY / AWAITING RE-VERIFICATION  
**Executor:** ChatGPT / GPT-5.6 Sol  
**Date:** 2026-10-06  
**Scope:** RC-6 Repair #1 after independent verification failure  
**WA4-E:** NOT STARTED

## 1. Baseline

Repair #1 was first fixed in Chat and only then started through Remote.

Actual start baseline:

- GitHub main: `26111c9e39f8b9de90f1b91b6a75b74bd0412e6d` (commit 159);
- local HEAD: same SHA;
- local worktree: clean at baseline;
- independent verifier evidence already persisted in:
  `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-VERIFY/`.

Baseline full Web Alarm regression:

- **416 tests OK**;
- **1 skip**;
- compileall PASS;
- `git diff --check` PASS.

Repair session:

`Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/`

Safety copies were taken before code/document changes.

## 2. Independent verdict entering repair

Independent verifier verdict:

**VERIFICATION FAILED / REPAIR REQUIRED**

Confirmed blockers:

- B1 — completed ADOPT settlement permanently captured recovery focus;
- B2 — false READY after foreign TASK acquired an affected target after RETRY re-arm;
- B3 — Coordinator substituted TASK-current microtask state for the recovery operation's own microtask, allowing false RETRY READY / half ABORT settlement;
- B4 — Projection treated an in-progress RC-4 rollback as stale after rollback's own effects changed evidence;
- B5 — ACTIVE microtask could return READY with a corrupt/unverified restore point.

Findings carried into the repair:

- F1 — ABORT ends at RECOVERY_REQUIRED and no normal global lifecycle exit currently exists;
- F2 — PARTIAL/FAILED rollback must not be auto-closed/released before explicit disposition.

## 3. B1 — settlement pending vs historical

### Root cause

`ProjectionService._operation_recovery()` surfaced any matching
`recovery_settlement` forever.

Coordinator then interpreted `ADOPT_SETTLED` using
`position.current_status`, which is the TASK's current microtask, not
necessarily the operation's microtask.

After:

m1 ADOPT -> DONE -> VERIFIED -> m2 ACTIVE

the old m1 settlement still captured top-level recovery and attempted to
move VERIFIED m1 back to DONE.

### Repair

Projection now distinguishes settlement that still needs administrative
completion from settlement that is durable history.

For every operation view Projection now exposes the lifecycle status of
that operation's own microtask:

`microtask_status`

A matching settlement is operational only while administrative work is
incomplete.

ADOPT becomes historical when:

- operation microtask is DONE or VERIFIED; and
- its operation-owned RC-3 claim is no longer active.

ABORT / ROLLBACK settlement becomes historical when:

- operation microtask is RECOVERY_REQUIRED; and
- its operation-owned claim is no longer active.

Historical settlement remains persisted in the Operation record/view; it
simply stops capturing top-level NEXT.

### Proven outcomes

- ADOPT m1 VERIFIED + m2 ACTIVE -> READY for m2;
- all microtasks VERIFIED -> TASK_READY_TO_CLOSE;
- settlement evidence remains persistent/history.

## 4. B2 — truthful READY and global foreign ownership

### Root cause

Projection intentionally exposes TASK-local active claims.

RC-6 incorrectly treated absence of a foreign claim in that local view as
proof that affected physical targets were globally unowned.

Therefore after RETRY re-arm another TASK could acquire the same target
and a repeated recover could still return READY.

### Repair

READY_FOR_EXECUTION is no longer returned directly from lifecycle state.

Coordinator now performs a pure final readiness proof.

For RETRY:

- operation TASK lock;
- exact operation/resolution/microtask identity;
- accepted RETRY still authoritative and fresh;
- operation revision basis unchanged;
- operation microtask is ACTIVE and current;
- restore point integrity verified;
- full Resolver affected-target set locked in deterministic physical-key order;
- authoritative global TargetClaimStore inspected under those locks;
- compatible same-operation ownership is allowed;
- foreign ownership on primary or secondary target blocks READY;
- Resolver authority/freshness and restore point are re-proved before locks are released.

For normal ACTIVE readiness:

- exact current microtask is ACTIVE;
- verified restore point is loaded;
- every restore-point target is locked in deterministic physical-key order;
- any active RC-3 owner blocks normal pre-WA4-E READY;
- restore point is re-read under the protected proof.

These locks are ephemeral. RC-6 does not acquire normal execution ownership
and performs no Workspace mutation.

WA4-E must still acquire/recheck authoritative ownership before its first
physical write.

### Multiprocess proof

A real subprocess race pauses Coordinator immediately before its final
RETRY READY proof. A foreign TASK then acquires:

- the primary target; or
- a secondary affected target.

Both cases end in RECOVERY_BLOCKED, never READY.

## 5. B3 — operation microtask authority and settlement preflight

### Root cause

Coordinator classified recovery by `position.current_status`.

That status belongs to the TASK's current microtask and can differ from
`operation.microtask_id`.

In addition, ABORT settlement was persisted before Coordinator discovered
that the operation's microtask could not legally become RECOVERY_REQUIRED.

### Repair

Recovery actions now use the operation view's own `microtask_status`.

RETRY:

- a recovery operation in an already VERIFIED/historical microtask can
  never become READY merely because a later microtask is ACTIVE.

Settlement ordering now includes lifecycle preflight before the first
persistent settlement write:

PRE-PROVE
-> WRITE SETTLEMENT
-> WRITE MICRO LIFECYCLE
-> RELEASE OWN CLAIM
-> REBUILD PROJECTION

ADOPT/ABORT/ROLLBACK settlement preflight proves that the operation's own
microtask can satisfy the required administrative state before settlement
is persisted.

Crash/replay remains supported:

- settlement written before micro update -> fresh process finishes admin work;
- micro update written before claim release -> fresh process performs release-only;
- ADOPT microtask already VERIFIED during a race is accepted as a completed
  administrative state and is never moved backwards.

### Proven outcomes

- old m1 operation + m1 VERIFIED + m2 ACTIVE + RETRY -> never READY;
- same + ABORT -> fail closed before settlement write;
- no persistent half-settlement.

## 6. B4 — Projection aligned with RC-4 restart authority

### Original root cause

RC-4 deliberately stops depending on the literal original Resolver evidence
fingerprint after its own target-level effects/reconciliation state has
started.

Projection nevertheless used generic Resolver freshness first and could
classify a resumable tracked rollback as:

`ROLLBACK_STALE_OPEN`

Coordinator then closed it instead of resuming RC-4.

### Repair architecture

RC-4 now exposes projection-facing phase facts derived from one canonical
implementation:

- `rollback_own_effects_started(session)`;
- `rollback_needs_rc4_finalize(session)`;
- `rollback_resume_via_rc4_required(session)`.

The exact `_session_basis` touched rule reuses
`rollback_own_effects_started()`, avoiding duplicate status lists.

Projection uses these persistent facts to distinguish:

- pre-effect stale/superseded rollback that may be safely closed;
- in-flight target reconciliation;
- own-effect rollback that must stay under RC-4 authority;
- DRIFTED/FAILED persisted before RC-4 finalize;
- VERIFIED with release interrupted;
- PARTIAL/FAILED non-verified final outcome.

### Original verifier crash matrix

All now pass in a fresh process:

1. crash after first RESTORED target;
2. crash with T_APPLYING and write landed;
3. crash with T_APPLYING and write not landed;
4. VERIFIED with claims_released=false.

For 1–3:

- Projection surfaces RC-4 operational state;
- Coordinator calls RC-4 apply/reconcile;
- already proven effects are not repeated;
- remaining safe targets complete once;
- result reaches VERIFIED and release/settlement normally.

For 4:

- only ownership release is completed;
- restore receipt/event count does not increase.

## 7. Additional B4 edge found during executor self-review

After the first full repair pass, executor adversarial review found a second
restart window not present in the independent verifier's original probes:

1. rollback target is T_APPLYING;
2. after restart current bytes match neither preserved nor restore state;
3. RC-4 persists target T_DRIFTED;
4. process crashes before `_finalize()`.

RC-4 itself can safely resume this state and finalize FAILED/PARTIAL, but
Projection initially downgraded it to ROLLBACK_STALE_OPEN.

A new red regression reproduced that defect.

### Repair

`rollback_needs_rc4_finalize()` identifies APPLYING sessions with persisted
DRIFTED/FAILED targets.

Projection routes those sessions through RC-4 apply once to finalize the
already-persisted outcome.

After finalization:

- PARTIAL/FAILED is never downgraded to stale auto-cleanup;
- Coordinator returns RECOVERY_BLOCKED/manual;
- claims remain held until explicit disposition.

### Composite ABORT proof

A second regression adds accepted ABORT after the persisted DRIFTED crash.

Result:

- Projection -> ROLLBACK_ABORTED_NEEDS_FINALIZE;
- Coordinator invokes RC-4 only to finalize the already-persisted outcome;
- no untouched restore target is executed;
- result becomes FAILED/PARTIAL;
- claims remain held;
- ABORT settlement is not written over the unsafe open rollback.

## 8. VERIFIED release-pending composite authority

Another regression covers:

ROLLBACK VERIFIED
-> claim release interrupted
-> later accepted ABORT

Projection returns:

`ROLLBACK_ABORTED_RELEASE_PENDING`

Coordinator performs RC-4 release-only.

Proved:

- no additional restore event;
- claims_released becomes true;
- only then does accepted ABORT become operational and settle normally.

Equivalent projection states are defined for a newer non-ABORT accepted
resolution where legally reachable.

## 9. B5 — restore point is part of READY contract

### Root cause

NORMAL + ACTIVE returned READY without requiring
`projection.restore_point.status == VERIFIED`.

### Repair

Projection now emits a structural blocker:

`RESTORE_POINT_NOT_VERIFIED`

when the current ACTIVE microtask lacks a verified restore point.

Coordinator also independently refuses ACTIVE readiness unless the restore
point is VERIFIED and then re-validates it in the pure READY proof.

A corrupt snapshot under ACTIVE therefore:

- cannot produce READY_FOR_EXECUTION;
- surfaces a precise projection blocker/NEXT;
- performs zero Workspace mutation.

Existing tests that intentionally expected clean ACTIVE READY were updated
to prepare an actual verified restore point first.

## 10. F1 — ABORT / RECOVERY_REQUIRED policy

No global state-machine transition was invented.

After durable ABORT settlement:

- microtask remains RECOVERY_REQUIRED;
- settlement becomes historical after admin cleanup;
- Projection's canonical NEXT explicitly says normal mutation is forbidden;
- an explicit project-level lifecycle/replan decision is required.

The previous wording suggesting an immediately available "new operation"
path was removed.

This repair does not define that future global lifecycle decision.

## 11. F2 — PARTIAL/FAILED rollback policy

Coordinator no longer auto-closes PARTIAL/FAILED rollback.

If RC-4 has a non-verified physical final outcome:

- state remains PARTIAL/FAILED;
- Coordinator returns RECOVERY_BLOCKED/manual;
- ownership is preserved;
- no automatic close/release occurs.

For later accepted ABORT/superseding actions Projection distinguishes:

- pre-effect cleanup -> close may be safe;
- in-flight -> interruption-safe reconciliation rules;
- persisted target requiring RC-4 finalize -> finalize only;
- VERIFIED release pending -> release only;
- PARTIAL/FAILED or own effects without a safe automatic terminal proof ->
  manual/block and preserve ownership.

## 12. Files changed

Runtime:

- `web_alarm/projection.py`
- `web_alarm/recovery_coordinator.py`
- `web_alarm/rollback_service.py`

No new global state-machine status or transition was added.

Existing tests adapted/expanded:

- `test_web_alarm_cli.py`
- `test_web_alarm_recovery_coordinator.py`
- `test_web_alarm_recovery_coordinator_adversarial.py`
- `test_web_alarm_recovery_coordinator_concurrency.py`

New:

- `test_web_alarm_recovery_coordinator_repair1.py`

Operational documentation/evidence:

- `Документация/000_Задачи ChatGPT.md`
- `Документация/000_Задачи для агента.md`
- `Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6_REPAIR1/`

`.obsidian/workspace.json` became dirty externally during the session.
It was not intentionally read/edited/reverted as part of Repair #1 and is
not an RC-6 repair change.

## 13. Verification evidence

### Baseline

- full suite: **416 tests OK**, skip=1;
- compileall PASS;
- diff-check PASS.

### Initial blocker regressions

A new permanent Repair #1 file first reproduced B1/B2/B3/B5:

- **7/7 failed on baseline runtime**, as expected.

After the first repair layer:

- **7/7 PASS**.

### Final Repair #1 focused

`test_web_alarm_recovery_coordinator_repair1.py`:

- **21/21 PASS**.

Includes:

- B1 next-microtask/closeout;
- B2 primary/secondary foreign claims;
- B3 historical operation RETRY/ABORT;
- B4 original interrupted rollback matrix;
- B4 persisted DRIFTED-before-finalize crash;
- B4 persisted DRIFTED + later ABORT;
- VERIFIED release pending + later ABORT;
- F2 PARTIAL ownership preservation;
- settlement crash/replay;
- B5 corrupt restore point;
- normal ACTIVE foreign-owner proof.

### Focused RC-3/4/5/6 + public entry

Final core RC-3/4/5/6 focused run:

- **176/176 PASS**.

Final public-entry focused run (Server/CLI + Coordinator/Repair):

- **55/55 PASS**.

After latest runtime changes:

- compileall PASS;
- diff-check PASS.

### Original independent verifier probes

Final runtime replayed the original Claude probe scripts unchanged:

- `rc6_probes.py`: exit 0;
- `rc6_probe_interrupted.py`: exit 0.

Persisted output:

`claude_probes_replay.txt`

### Final full regression

The latest executor evidence supersedes the earlier 438-test intermediate log.

Final evidence:

`final_verification_v3.md`

- **439 tests OK**;
- **1 skip**;
- zero failures/errors;
- UNIT_EXIT=0;
- compileall PASS;
- `git diff --check` PASS.

Earlier `final_regression_with_live_hash_v2.txt` remains preserved as intermediate history, not the final count.

## 14. Live WEB-02 storage proof

Live root derived from actual code:

`C:\Users\REX\AppData\Local\WebAlarmWorkspace`

Final regression wrapped with deterministic read-only tree hash.

BEFORE:

- files: 136;
- directories: 41;
- SHA-256:
  `a9cf87815774d5abdfb8a433af8aca13002d292a2866aa2b27a8901f24c9bff3`

AFTER:

- files: 136;
- directories: 41;
- SHA-256:
  `a9cf87815774d5abdfb8a433af8aca13002d292a2866aa2b27a8901f24c9bff3`

Therefore final Repair #1 regression made **zero live-storage change**.

The hash differs from an older RC-6 evidence hash recorded earlier in the
day, but the current Repair #1 proof is intentionally before-vs-after around
the same final run; no assumption is made that live storage remained frozen
between separate user sessions.

## 15. Scope / deferred

Not implemented:

- WA4-E physical Executor;
- STARTED-before-write normal execution boundary;
- WA4-A;
- WA4-O UI;
- WA4-R strict rollout;
- Program/Stage scheduler;
- multi-model orchestration;
- lease/heartbeat;
- new global Microtask status/transition.

No fundamental RC-4 destructive lifecycle was replaced. RC-4 apply remains
the sole tracked rollback engine.

## 16. Executor conclusion

Known independent blockers B1–B5 are repaired and covered by permanent
regressions.

F1 is made truthful but deliberately remains a manual future lifecycle/replan
decision.

F2 is changed to fail-safe ownership preservation.

Additional adversarial restart defects found during Repair #1 were repaired
and added to the permanent suite.

Executor status:

**RESULT READY / AWAITING RE-VERIFICATION**

This is NOT:

- RC-6 DONE;
- RC-6 VERIFIED;
- permission to begin WA4-E.

## 17. Re-verification checklist

Independent verifier should:

1. query actual GitHub HEAD after user commit/push;
2. verify local/GitHub SHA and clean intended worktree;
3. inspect diff from commit 159;
4. replay original B1–B5 probes;
5. run `test_web_alarm_recovery_coordinator_repair1.py`;
6. independently attack:
   - completed ADOPT settlement with later microtask;
   - foreign claim after RETRY re-arm;
   - historical-operation RETRY/ABORT;
   - restore-point corruption under ACTIVE;
   - crash after RESTORED;
   - T_APPLYING landed/not-landed;
   - T_DRIFTED persisted then crash before finalize;
   - T_DRIFTED + later ABORT;
   - PARTIAL/FAILED ownership;
   - VERIFIED release pending + newer action;
   - READY proof races on primary/secondary target;
7. run focused RC-3/4/5/6;
8. run full explicit `test_web_alarm_*.py`;
9. run compileall and diff-check;
10. independently prove live storage is read-only.

If any blocker appears:

**VERIFICATION FAILED / REPAIR REQUIRED**

If all pass:

**RC-6 DONE / VERIFIED**

Only after that may the project route to WA4-E.

Do not automatically start WA4-E.

## 18. NEXT SAFE ACTION

User reviews the current worktree, excluding/handling the unrelated
`.obsidian/workspace.json` change as they choose.

User commits/pushes Repair #1.

Then an independent agent/model re-verifies the freshest GitHub commit.

Until independent PASS:

**WA4-E MUST NOT START.**
