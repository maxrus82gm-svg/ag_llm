# TASK WA-2.2 — Server-owned state machine

STATUS: DONE / VERIFIED

BIG TASK: WA-2 — Local Web Alarm Server + UI — IN PROGRESS.

RESULT: `web_alarm/state_machine.py` is authoritative for Server-side microtask transitions. Verified-snapshot and prior-microtask gates are enforced; client cannot manufacture PREPARING/BACKUP_VERIFIED; DONE→VERIFIED requires evidence; accepted/rejected transitions update event log/checkpoint and computed NEXT SAFE ACTION.

VERIFICATION: full WA focused regression = 64/64 PASS; state-machine/server/documentation `git diff --check` PASS.

DOCUMENTATION: 000/01/04/05/06/23/24/25 synchronized.

NEXT: WA-2.3 — Minimal UI.

NEXT SAFE ACTION: start WA-2.3 as a fresh task-session with declared UI scope and verified restore point.
