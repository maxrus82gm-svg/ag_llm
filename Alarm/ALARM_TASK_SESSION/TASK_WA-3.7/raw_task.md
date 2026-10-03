# TASK WA-3.7 — Controlled real Remote transport-disconnect acceptance gate

## Current stage
CHAT formulation is complete. This Remote stage is TASK/documentation population only.

Do not:
- prepare a snapshot;
- set any microtask READY/ACTIVE;
- create the controlled mutation fixture;
- start a persistent mutation operation;
- intentionally break Remote transport;
- modify runtime code.

Implementation starts only after explicit user review of the populated TASK.

## Starting point
WA-3.1 through WA-3.6 implementation = DONE / VERIFIED.
WA-3.6 fresh-process reopen = PASS.

WA-3.6 proof:
- M001 9/9 PASS;
- M002 8/8 PASS;
- M003 6/6 PASS;
- M004 10/10 PASS;
- combined Recovery Report 33/33 PASS;
- full Web Alarm 197/197 PASS;
- py_compile + scoped diff-check PASS.

A real unplanned MESSAGE_DELIVERY_TIMEOUT -> REMOTE_OFFLINE -> REMOTE_RECOVERED incident already proved partial docs reconciliation without replay, but it does NOT replace the intentionally controlled acceptance test.

WA-3 overall therefore remains IN PROGRESS.

## Goal
Perform a deliberately controlled real Chat <-> Desktop Commander Remote transport disconnect during a safe isolated mutation and mechanically prove the complete WA-3 recovery contract.

The test must use real transport loss, not only a simulated process restart or synthetic evidence event.

## Core rule
Disconnect is not failure.

After reconnect:
persistent state
+ operation lifecycle
+ transport evidence
+ manifest/snapshot
+ actual Workspace state
-> deterministic reconciliation
-> Recovery Report
-> NEXT SAFE ACTION.

No mutation may be blindly replayed because the caller/UI lost the response.

## Controlled test safety
Use a dedicated isolated test target inside the registered workspace.

The target must:
- not affect Ultra runtime;
- not affect Web Alarm runtime;
- not be a primary project/documentation file;
- have deterministic pre-state;
- have deterministic expected post-state;
- be safe to restore/remove;
- exist only to prove operation/reconciliation semantics.

Do not use server.py, state_machine.py, Recovery Report runtime, production configuration, or user working assets as the controlled mutation target.

## Required operation contract
Before intentional transport loss there must be:
- task_id;
- microtask_id;
- stable operation_id;
- action;
- exact target;
- canonical request fingerprint;
- expected precondition;
- verified restore point;
- persistent INTENT;
- persistent STARTED before the actual mutation window.

The controlled disconnect point must occur after the operation is persistently STARTED but before Chat can safely know the final mutation result.

The caller must face real uncertainty: mutation could be none, partial, full, or ambiguous.

## Forbidden behavior
During the test:
- do not press Retry as a blind mutation replay;
- do not treat timeout/offline as proof that mutation did not execute;
- do not change lifecycle from transport signal alone;
- do not auto-rollback;
- do not auto-adopt current state;
- do not mark DONE/VERIFIED from REMOTE_RECOVERED;
- do not use the last visible Chat message as authoritative state;
- do not skip reconciliation.

## Transport evidence
Persist real evidence when observed:
- REMOTE_OFFLINE;
- REMOTE_RECOVERED;
- MESSAGE_DELIVERY_TIMEOUT if it actually occurs;
- RESULT_DELIVERY_FAILED if it actually occurs.

Where possible every event must bind to task_id, microtask_id and operation_id.

Transport evidence remains evidence_only and has no workflow authority.

## Reconciliation after reconnect
Read, in order:
1. persistent TASK;
2. microtask state;
3. checkpoint;
4. persistent operation record/lifecycle;
5. transport events;
6. manifest;
7. verified snapshots;
8. current target state.

Compare target against:
- pre-state;
- current-state;
- expected-post-state.

Classify side effect:
- none;
- partial;
- full;
- ambiguous.

No guessing is allowed.

The deterministic decision engine, not transport telemetry, decides the authoritative recovery result.

## Recovery Report
After reconciliation persist a machine-usable Recovery Report containing at least:
- incident_id;
- task_id;
- microtask_id;
- operation_id;
- caller/UI error class;
- transport evidence;
- persistent operation state;
- affected target pre/current/expected-post;
- side_effect_scope;
- reconciliation decision;
- accepted_as_already_done;
- actually_retried;
- actually_rolled_back;
- untouched/unresolved facts;
- NEXT SAFE ACTION;
- fresh-process reopen result.

If mutation already executed fully:
side_effect_scope = full
and actually_retried must remain empty.

If evidence proves no mutation:
side_effect_scope = none.
A later retry is a separate authoritative action, never an automatic interpretation of transport failure.

## Planned execution split
WA37-M001 — controlled test contract/preparation:
- isolate safe target;
- define expected pre/post state;
- create immutable/versioned restore point;
- create persistent operation identity;
- prove operation is bound to TaskStore/OperationStore;
- stop before deliberate disconnect until the exact test moment is ready.

WA37-M002 — controlled disconnect/recovery:
- drive operation to persistent STARTED;
- enter the safe mutation window;
- intentionally break real Remote transport;
- restore connection;
- do not replay;
- reconcile persistent state and actual Workspace;
- persist transport evidence;
- persist Recovery Report;
- prove fresh-process recovery.

WA37-M003 — closeout:
- focused acceptance verification;
- recovery/transport/full Web Alarm regressions;
- py_compile and task-scoped diff-check;
- documentation closeout;
- reconcile all WA-3 acceptance criteria;
- WA-3.7 DONE / VERIFIED;
- fresh-process reopen WA-3.7;
- if and only if every WA-3 gate is satisfied, close WA-3 and perform final WA-3 fresh reopen.

## Defect rule
If the controlled test discovers a defect:
STOP.
Record the failed incident without rewriting history.
Then:
defect record
-> separate scope-extension
-> immutable/versioned restore point
-> minimal repair
-> independent verification
-> a new controlled incident/operation identity for retest.

Do not silently repair runtime inside the same acceptance mutation.

## WA-3.7 PASS criteria
PASS requires proof that:
1. operation identity existed before disconnect;
2. verified restore point existed before mutation;
3. a real intentionally controlled Remote transport disconnect occurred;
4. reconnect caused no blind replay;
5. reconciliation determined mutation fate from persistent evidence + Workspace;
6. transport evidence did not gain workflow authority;
7. Recovery Report is persistent and correct;
8. accepted-as-already-done is distinct from actually-retried;
9. a fresh process sees the same recovery result;
10. full Web Alarm regression remains green.

## After PASS
- documentation closeout WA-3.7;
- WA-3.7 = DONE / VERIFIED;
- separate fresh-process reopen WA-3.7;
- reconcile the complete WA-3 acceptance matrix.

Only if all WA-3 acceptance is proven:
WA-3 = DONE / VERIFIED
-> final WA-3 fresh reopen
-> record new NEXT SAFE ACTION.

WA-4 must NOT start automatically.

## First step of future implementation stage
Before any mutation:
- reread TASK_WA-3.6 session/context;
- reread TASK_WA-3.7 session/context;
- reread 000;
- confirm WA-3.6 DONE/VERIFIED/fresh reopen PASS;
- confirm WA-3.7 exists and is still only PLANNED/USER_REVIEW_REQUIRED;
- reconcile if any unexpected WA-3.7 implementation artifact already exists.

Only after explicit user approval:
prepare WA37-M001.

## Current boundary
This population stage ends with:
- TASK_WA-3.7 created;
- Web Alarm task + planned microtasks created;
- checkpoint = PLANNED / NOT_PREPARED / USER_REVIEW_REQUIRED;
- documentation synchronized.

It must end BEFORE any controlled-disconnect implementation begins.

## Authoritative sequencing correction before controlled execution

The original Chat formulation placed the controlled target snapshot and persistent operation identity inside M001. Runtime state-machine audit proved that would make the operation lifecycle semantically cross microtask boundaries: M001 would have to be VERIFIED before M002 can become active, while the actual mutation/reconciliation belongs to M002.

Therefore the authoritative execution split is refined without changing the acceptance goal:
- M001 freezes and verifies only the test contract: future target path, absent pre-state, exact expected-post bytes/hash, fixed operation_id, safety and disconnect window. It must leave the future target absent and the operation_id unused.
- M002 owns the actual controlled target restore point and the complete OperationStore lifecycle. It prepares/ verifies the target snapshot, creates the fixed INTENT, persists STARTED immediately before the mutation window, then performs the real disconnect/recovery/reconciliation.
- M003 remains final regression/documentation/WA-3 acceptance closeout.

This correction preserves the requirement that snapshot, operation identity, mutation and reconciliation are bound to the same microtask and prevents a false VERIFIED state before the mutation actually occurs.

## Controlled execution result

The first execution identity `WA37-CTRL-001` did not satisfy the controlled-disconnect acceptance criterion: the target reached exact expected post-state, but Remote transport was not intentionally disconnected in the required window. The attempt is retained as historical non-acceptance evidence and was not relabeled as a PASS.

After restore to the verified absent pre-state, the retest used `WA37-CTRL-002` with the same canonical request fingerprint. The operation was persisted as STARTED before the user intentionally stopped Desktop Commander Remote. After the user restored the Remote process, reconciliation was performed before any retry. Persistent evidence showed the target still exactly matched PRE_STATE and did not match the exact expected post-state. Deterministic decision: `RETRY_SAFE / PRE_STATE_AND_POST_NOT_REACHED`; Recovery Report side effect: `none`; `actually_retried=[]`.

Bound transport evidence for the acceptance incident is `REMOTE_OFFLINE -> REMOTE_RECOVERED`. Recovery Report `report_wa37_ctrl002` (`INC-WA37-CTRL-002`) is persistent and evidence-only. A fresh Python process independently reopened the same reconciliation result and the persisted report. No blind replay, automatic rollback, automatic adopt, or transport-authority mutation occurred.

M002 therefore satisfies the controlled real Remote transport-disconnect recovery criterion with a proven NONE side effect. The authoritative decision allowed a replay-safe retry, but the acceptance proof intentionally did not execute that retry; the operation was closed FAILED only after the no-side-effect result was persistently proven. M003 is responsible for regression/documentation/final WA-3 acceptance closeout.
