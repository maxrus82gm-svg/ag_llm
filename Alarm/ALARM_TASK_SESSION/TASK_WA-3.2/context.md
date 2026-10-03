# TASK WA-3.2 — Operation ID / replay identity

STATUS: DONE / VERIFIED

BIG TASK: WA-3 — Remote workflow, recovery and replay protection — IN PROGRESS.

RESULT: `web_alarm/operation_store.py` provides persistent operation_id identity, canonical request fingerprint, conflict gate and replay-safe lifecycle. Same ID/same request returns known state; same ID/different request fails closed; STARTED/UNKNOWN replay => RECONCILE_REQUIRED. Server exposes typed operation create/list/get/transition endpoints. Operation Store itself performs no real-project mutation.

RECOVERY NOTE: one composite Remote integration call failed after partial execution. Reconciliation proved __init__.py edits already applied and server.py untouched; only missing Server integration was continued.

VERIFICATION: final full WA regression = 90/90 PASS; Operation/Server/documentation git diff --check PASS.

DOCUMENTATION: 000/01/04/05/06/23/24/25 synchronized.

NEXT: WA-3.3 — Reconciliation.
