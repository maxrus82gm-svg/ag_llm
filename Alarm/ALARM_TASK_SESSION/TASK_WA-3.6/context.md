# TASK WA-3.6 — Short machine-usable Recovery Report

STATUS: DONE / VERIFIED / FRESH REOPEN PASS

BIG TASK: WA-3 — Remote workflow, recovery and replay protection — IN PROGRESS.

START GATE: WA-3.5 = DONE / VERIFIED; fresh reopen WA-3.5 = PASS.

RESULT: persistent machine-usable Recovery Report implemented and verified. M001 schema/store 9/9 PASS; M002 deterministic builder 8/8 PASS; M003 service + Server/Context integration 6/6 PASS; M004 adversarial acceptance 10/10 PASS. Combined 33/33 PASS; full Web Alarm 197/197 PASS; py_compile + diff-check PASS.

AUTHORITY INVARIANT: Recovery Report remains evidence-only and never makes retry/rollback/adopt/workflow decisions itself. Side-effect classification = none / partial / full / ambiguous; insufficient evidence remains fail-closed.

LIVE RECOVERY DURING CLOSEOUT: MESSAGE_DELIVERY_TIMEOUT -> REMOTE_OFFLINE -> REMOTE_RECOVERED. Snapshot reconciliation proved partial docs execution: 000 already done, eight docs pre-state; 000 was not replayed. Transport evidence persisted with fixed IDs.

WEB ALARM STATE: TASK WA-3.6 = COMPLETED; WA36-M001..M004 = VERIFIED; checkpoint current/last_verified = WA36-M004 / VERIFIED. Fresh independent Python process reopened the same state: PASS.

WA-3 OVERALL: still IN PROGRESS. Required intentionally controlled real Remote transport-disconnect acceptance gate is not yet closed; the live unplanned incident does not replace it.

NEXT SAFE ACTION: formulate the controlled WA-3 disconnect acceptance task in ordinary Chat before any new Remote activation. Do not start WA-4 automatically.
