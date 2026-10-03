# WA-2.1 history

- WA-1 confirmed DONE / VERIFIED before WA-2 start.
- WA-2.1 scope published in ordinary Chat and activated after a verified restore point.
- Added `web_alarm/server.py` and focused `test_web_alarm_server.py`.
- Initial full regression: 56/57 PASS, 1 FAIL because TASK creation did not verify registered Workspace identity. Failure recorded; no verification credit.
- Added registered-Workspace gate; final full regression passed 57/57; loopback HTTP smoke and diff-check passed.
- Documentation scope snapshotted and SHA256-verified before closeout.
- A composite Remote closeout call returned transport failure after partial execution. Disk was reread before continuing; already-applied edits were not replayed.
- 000/01/04/05/06/23/24/25 synchronized.
- WA-2.1 closed DONE / VERIFIED. Next: WA-2.2 Server-owned state machine.
