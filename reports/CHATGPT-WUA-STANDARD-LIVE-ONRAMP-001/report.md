# CHATGPT-WUA-STANDARD-LIVE-ONRAMP-001 — bounded STANDARD operator onramp

**Status: IMPLEMENTATION CANDIDATE / INDEPENDENT WINDOWS CI PENDING / PHYSICAL GUI NOT RUN.** This is a distinct implementation slice after first GigaChat-2 LIVE PASS in `CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001`. It does not finish or rotate Codex's active БЛОК 1.

**USER GO:** 15.11.2026, continue integration using GitHub, without Desktop Commander, preserve STANDARD/TEST/Tkinter and user history. This slice adds **a reviewed-version GigaChat-2 path only**; the full six-model physical activation remains FOLLOWUP `FOLLOWUP-WUA-GIGACHAT-PERMANENT-LIVE-001`.

**REUSE CHECK:** Retains `Start_WebAlarm_Standard.cmd` → `web_alarm.launcher --standard`, one `WebAlarmApi` and `create_server`, H38 `ProviderSession`/`LiveApproval`/`ModelContract`, `OrdinaryProviderFactory.for_session`, `RealGigaChatTransport`, S2/S3a BudgetLedger, existing Turn/RAW/history. No second engine, OAuth client, API endpoint, credential store, history migration or third CMD.

**Changes prepared:**
- `web_alarm/standard_live.py` lists only registered and already-audited Workspace roots, asks for exact owner console confirmation, creates a 30-minute grant restricted to 12 messages to exact observed GigaChat-2 version.
- `web_alarm/launcher.py` composes the preapproved server-side session only for an interactive STANDARD startup; it binds loopback before OAuth/catalog and closes the grant on shutdown/error. Non-interactive/TEST/self-test stays without real authority.
- `web_alarm/ordinary_provider.py` identifies catalog-present but unapproved model choices as `NOT_APPROVED`; existing synthetic default remains unchanged.
- `web_alarm/ui.py` disables send for non-approved LIVE choices instead of pretending all six generated successfully.
- `test_web_alarm_standard_live.py` tests no-enrollment/no credentials/decline/exact grant and model hold; existing offline regression suites will also run.
- `.github/workflows/wua-standard-live-offline.yml` uses Windows 3.12 sparse checkout and isolated no-credential tests.

**Exact operator limits:** 12 physical inference attempts maximum, 1 OAuth, 1 catalog, input wire max 8192 bytes and max output 128 tokens each; conservative maximum liability `12*(8192+128)=99840` tokens, expiry 1800 seconds. Public tariff, account balance and exact provider output cap remain UNKNOWN; the 128-token figure is an operator ceiling. No network is called by the console selection alone. No automatic retry/fallback after uncertain inference.

**Not claimed:** general six-model inference, automatic migration/enrollment for existing Workspace ledgers, Chromium/F5 user UX, verified account pricing/quota, expanded S3b/S3c/S9/S13a, release/production readiness. These are OPEN; no fresh paid/live calls authorised by this code review. User approval at runtime remains separate.

**TEST / ACCEPTANCE:** No Windows CI run ID yet. This report must be updated with actual source SHA, run IDs, logs, negative tests and outcome before a DOC CLOSED verdict. Candidate is validated on a review branch before the same atomic commit may be fast-forwarded into GPT. No merge to main, no physical paid calls; CI verdict and source SHA to be read back from GitHub Actions.
