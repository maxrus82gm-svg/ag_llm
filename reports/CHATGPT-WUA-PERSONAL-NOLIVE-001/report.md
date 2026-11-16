# CHATGPT-WUA-PERSONAL-NOLIVE-001 — author implementation (16.11.2026)

**Task ID:** CHATGPT-WUA-PERSONAL-NOLIVE-001

**Owner observation:** STANDARD #627 starts but the personal-chat button is hidden; messages cannot be sent. The two permanent CMD shortcuts must not change.

**Root cause (source):** `web_alarm.ui` hides the button until the personal registry is populated; the only current personal initialization is the operator-only `offer_standard_live`. In the absence of a separately admitted provider session, REAL turns are denied by `ordinary_real_hold`. These are separate concerns.

**Change:** A local, write-token/same-origin guarded `POST /ultra/chat/personal` explicitly initializes the existing shared Ultra identity, audit ledger, and first chat on user click; repeat calls reuse the registration. It does not mint OAuth, LIVE approval, inference or grant. The browser shows the personal section independently from Workspace, preserves the existing chat and model routines, and keeps REAL HOLD unchanged. TEST fixture route unaffected, permanent launchers unchanged.

**Author regression additions:** Python HTTP checks for missing token, forged body, create/idempotency, persisted identity on new server and no real turn. Node DOM checks for first personal-chat flow and Workspace isolation.

**Author tests (isolated Windows scratch, 16.11.2026):** Python narrow personal/live 9/9 OK; Node shipped DOM 76/76 PASS; broader Python application/launcher/admission/stage5 77 tests OK (1 SKIP). The first partial scratch checkout had 6 missing-fixture errors; support files were copied and the same 77-test run completed successfully. Commands: `python -B -m unittest test_web_alarm_ordinary_application test_web_alarm_standard_live test_web_alarm_launcher test_web_alarm_ordinary_admission test_web_alarm_ultra_chat_s5 -q`; `node --test test_web_alarm_ultra_chat_ui.js`. Tests never contacted paid provider or STANDARD storage. **GitHub Windows CI** remains PENDING at authoring, **independent source review PENDING**, **owner physical GUI PENDING**. This is an author implementation, not independently accepted release.

**Open:** ordinary sending via GigaChat remains gated. A separate safe in-app provider setup/START/STOP and provider-specific consent/verification is required for actual messages; do not enable REAL by bypassing approval. Existing Codex LIVE Bootstrap task stays unchanged.

**Files:** `web_alarm/standard_live.py`, `web_alarm/ordinary_provider.py`, `web_alarm/server.py`, `web_alarm/ui.py`, `test_web_alarm_ordinary_application.py`, `test_web_alarm_ultra_chat_ui.js`.
