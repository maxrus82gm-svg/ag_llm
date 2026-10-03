# TASK WA-3.6 — Short machine-usable Recovery Report

## Goal
Create a short persistent machine-usable Recovery Report that lets a new Chat, Server process or Remote session recover the proven result of reconciliation without trusting the last visible Chat message.

Authoritative derivation:
persistent state
+ reconciliation evidence
+ deterministic reconciliation decision
→ Recovery Report.

## Authority invariant
Recovery Report is evidence/output only. It must not itself:
- RETRY;
- ROLLBACK;
- ADOPT_CURRENT_STATE;
- resolve UNKNOWN_AFTER_DISCONNECT;
- mutate Workspace/checkpoint;
- change TASK/microtask/operation lifecycle;
- set DONE/VERIFIED;
- activate a next TASK;
- infer mutation fate only from transport signals.

Authority stays with persistent state machine + reconciliation evidence + deterministic decision engine.

## Required machine-usable fields
- report_id, incident_id, created_at;
- task_id, microtask_id, operation_id;
- caller/UI error class;
- transport/process evidence and process-restart flag;
- last persistent operation state and checkpoint/state identity;
- affected targets with pre/current/expected-post summary;
- relevant receipt/evidence identity;
- side_effect_scope = none | partial | full | ambiguous;
- authoritative reconciliation decision and evidence summary;
- accepted_as_already_done;
- actually_retried;
- actually_rolled_back;
- untouched/unresolved facts;
- next_safe_action;
- fresh-process reopen result.

## Critical distinction
What physically happened must be separate from what recovery later did.
A mutation may have side_effect_scope=full while retried=false because reconciliation proved it had already completed.

## Fail-closed rules
If evidence cannot prove none/partial/full, classification is ambiguous.
If authoritative reconciliation has not produced a decision, the report must not invent one.
Transport/watchdog evidence remains evidence-only.

## Required scenarios
1. disconnect before mutation → none;
2. partial execution → partial with exact completed/missing targets;
3. full mutation + lost result → full, no replay;
4. UNKNOWN_AFTER_DISCONNECT;
5. MESSAGE_DELIVERY_TIMEOUT;
6. RESULT_DELIVERY_FAILED;
7. REMOTE_OFFLINE → REMOTE_RECOVERED;
8. PROCESS_RESTARTED;
9. duplicate/replayed operation_id;
10. insufficient evidence → ambiguous/fail-closed;
11. already-adopted current state;
12. fresh-process reread returns the same report/decision/NEXT SAFE ACTION.
## Planned execution split
M001 — define report contract/schema and restart-safe persistent store, test-first.
M002 — deterministic report builder from authoritative reconciliation inputs; prove no recovery authority and fail-closed behavior.
M003 — machine-usable read/exposure path and restart/fresh-process persistence without Chat dependence.
M004 — adversarial acceptance matrix, reconciliation/transport/full regression, py_compile, git diff --check, documentation closeout, fresh reopen.

## Defect rule
If a test discovers a defect:
STOP → record defect → separate scope-extension → immutable/versioned restore point → small repair → independent verification.

## Completion gate
WA-3.6 is DONE / VERIFIED only when:
- report is derived from authoritative persistent/reconciliation evidence;
- none/partial/full/ambiguous are mechanically distinguished;
- already-completed work is not represented as replayed work;
- retry/rollback/adopt facts are recorded separately;
- NEXT SAFE ACTION is persistent;
- a fresh process reads the same report after restart;
- old Chat context is unnecessary;
- full Web Alarm regression remains green.

## Current stage boundary
This task is being populated only.
Do not prepare snapshots, set microtasks READY/ACTIVE, modify runtime code, or start tests before explicit user review/approval.
After WA-3.6 completion, perform a separate fresh-process reopen and WA-3 acceptance gate. Do not start WA-4 automatically.
