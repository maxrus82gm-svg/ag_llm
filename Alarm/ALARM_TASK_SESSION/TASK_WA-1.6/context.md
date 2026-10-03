# TASK WA-1.6 — Basic CLI

STATUS: DONE / VERIFIED

BIG TASK: WA-1 — Fund state and file core — DONE / VERIFIED.

RESULT: `web_alarm/cli.py` and `web_alarm/__main__.py` provide `python -m web_alarm` with task create/open/complete, microtask create/prepare, snapshot verify/restore, checkpoint write/show, status and report.

VERIFICATION: full WA focused regression = 47/47 PASS; module entrypoint help smoke PASS; CLI diff-check PASS.

DOCUMENTATION: 000/01/04/05/06/23/24/25 synchronized. WA-1 status moved to DONE / VERIFIED.

NEXT BIG TASK: WA-2 — Local Web Alarm Server + UI.

NEXT SAFE ACTION: start WA-2.1 Server API as a fresh task-session with its own declared scope and verified restore point.
