# Stage B replacement — first real inference SUCCESS (15.11.2026)

**Independent operator:** ChatGPT via Desktop Commander Remote on `DESKTOP-SC96D3U`, under the user's explicit one-attempt approval. No Codex work was used for this replacement attempt.

- Prepared isolated Workspace and chat from `bootstrap.md`, only `gigachat_2` (`GigaChat-2`), prompt `Ответь одним словом: готово`.
- Checked corrected readiness path `turn_test.real_available` and model availability against source. Offline `test_web_alarm_live_bootstrap`: **6/6 PASS**. Fresh retry marker did not exist; previous Stage B grant was `CLOSED`.
- First operator invocation stopped at `DENIED_ENV_NOT_READY` **before marker/grant/network**: Desktop Commander subprocess did not inherit the existing Windows User environment. Confirmed only presence of credentials and `GIGACHAT_API_PERS` scope, then passed these to the child Python process without printing or copying their values.
- Dedicated copy `run_stage_b_user_retry_once.py` used unique `evidence/stage_b_user_retry_attempt.json` and `evidence/stage_b_user_retry_result.json`; the original `run_stage_b_once.py` and its attempt evidence were not modified or replayed.
- Physical provider calls committed: **1 OAuth POST, 1 GET /v1/models, 1 inference POST**; 0 retries; token liability **783**, within the approved 1056. Approved `max_tokens=32`, max wire 1024 bytes, grant expiry 180 seconds.
- Provider model version **`GigaChat-2:2.0.30.01`**, observed answer **`Готово`**; Turn **`SUCCEEDED`**, usage prompt **100**, completion **4**, total **104**; reasoning unavailable.
- The loopback response's latest Turn matched the submitted Turn; history contains user+assistant, and both RAW messages verified. New separate Python process re-opened stored chat, obtained both messages and checked assistant text `Готово`.
- Budget ledger: **3 events**, **1 attempt**, terminal **`KNOWN_TERMINAL`**. After the three-minute grant, durable grant readback confirmed **`CLOSED`**, server process exited, port 8765 not listening. The final result JSON also records `SUCCESS`, `grant_state=CLOSED`, and `error_code=null`.
- Prior Tkinter, STANDARD, TEST, and historical workspaces were not changed. No real provider calls were made beyond this single approved envelope. No credential, OAuth token, header, or authorization response was saved in evidence.

**Scope:** First real generation through the existing Web Alarm Ultra HTTP/core/RAW/ledger path is confirmed. A permanent user-controlled LIVE launcher, physical Chromium/F5 owner UX, and independently accepted full six-model generation remain **NOT DONE**. Keep task slot and general release HOLD open for separate review; do not claim production readiness from this single successful attempt.
