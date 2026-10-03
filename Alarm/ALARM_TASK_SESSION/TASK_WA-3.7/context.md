# TASK WA-3.7 — Controlled real Remote transport-disconnect acceptance gate

STATUS: DONE / VERIFIED / FRESH REOPEN PASS. WA-3 overall remains IN PROGRESS due to one final combined post-change controlled-disconnect acceptance gap.

BIG TASK: WA-3 — Remote workflow, recovery and replay protection — IN PROGRESS.

START GATE: WA-3.1–WA-3.6 implementation DONE / VERIFIED; WA-3.6 fresh-process reopen PASS. WA-3 overall remains IN PROGRESS only because the intentionally controlled real Remote transport-disconnect acceptance gate is still open.

GOAL: intentionally break the real Chat ↔ Desktop Commander Remote transport during a safe isolated mutation with persistent operation identity, then prove recovery from disk without blind replay.

CORE INVARIANT: disconnect/timeout is transport evidence only. It never proves mutation failure and never gets retry/rollback/adopt/workflow authority.

PLANNED SPLIT:
- WA37-M001 — freeze/verify controlled-test contract only: fixed safe target, absent pre-state, exact expected-post bytes/hash, fixed future operation_id. M001 does NOT create the controlled target or OperationStore record.
- WA37-M002 — prepare verified restore point for the actual controlled target, create the fixed OperationStore INTENT, transition it to STARTED immediately before the mutation window, then execute intentional real Remote disconnect/reconnect/reconciliation/Recovery Report/fresh-process proof.
- WA37-M003 — full regression, documentation closeout, WA-3 overall acceptance reconciliation and final WA-3 fresh reopen gate.

WEB ALARM STATE: TASK WA-3.7 = COMPLETED; WA37-M001–M003 = VERIFIED; checkpoint = WA37-M003 / VERIFIED. `report_wa37_ctrl002` persists `side_effect_scope=none`, `RETRY_SAFE`, `actually_retried=[]`; transport = REMOTE_OFFLINE -> REMOTE_RECOVERED. Fresh-process reopen WA-3.7 PASS.

CURRENT SAFE STATE: WA-3.7 is closed and restart-safe. `WA37-CTRL-001` proves FULL mutation without disconnect; `WA37-CTRL-002` proves real disconnect with NONE side effect and no blind replay. Final WA-3 reconciliation found these do not yet satisfy the stricter single-incident criterion 'Workspace changed locally, then Remote disconnects before Chat receives result'.

NEXT SAFE ACTION: formulate the final post-change controlled-disconnect follow-up TASK in ordinary Chat first. Do not create/activate it through Remote until the user approves the Chat formulation. WA-3 remains IN PROGRESS; WA-4 must not start automatically.
