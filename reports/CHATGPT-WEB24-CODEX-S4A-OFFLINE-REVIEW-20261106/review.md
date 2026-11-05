# WEB24 — S4A OFFLINE review, H-CODEX-000016

**2026-11-06.** TASK `CODEX-WUA-CHAT-S4A-COMMON-REQUEST-SERVICE-001`; HISTORY `H-CODEX-000016`; published source `main@68530d6820540387746a80bf436d7dad29c9e167` (one author commit).

**VERDICT: PASS / BOUNDED SOURCE + AUTHOR EVIDENCE — S4A OFFLINE only.** Stage 4 as a whole and real provider integration NOT ACCEPTED. Fresh independent Windows/Python/CI tests **NOT RUN**.

## Independent review

- Read current №08/000/34/40/05, short histories and applicable №18/36.3/37, assigned B1. GitHub confirms exact TASK/HISTORY IDs, `task_record.json`, `finish` exit 0 with readback, B1 WAITING and B1.1 H16. No duplicate H-ID.
- Inspected all new `ordinary_chat_service.py` and relevant `test_ordinary_chat_service.py`, `interface.md`, selected evidence and source diff. New code uses existing `get_model_spec`, `extract_usage`, canonical JSON; immutable prepared request, explicit byte limits/model/role validation, single injected async transport, safe response/usage/error parsing, timeout/unknown outcome without automatic retry. No concrete OAuth sender, storage writer, HTTP route or Tk integration.
- SHA-256 independently calculated from GitHub bytes: `ordinary_chat_service.py` = `509d26c16f05f259520733e00bc2675bb91f2c132af784ce7b605e77c78b9a85`; `test_ordinary_chat_service.py` = `a349c6d815fa4a02c7393c0309d3715e1d80cba4c9de91ceea8b83d7dceca866`; `report.md` = `069bb86241ad10cab07acefa153d6c5a30a2a7d58ccd828071c1521ea4922e06`; `handoff_task.md` = `91856904adcfdcdebc0c9f2b093ff9cb39ea0255dc3ffc07ed6763dcdae951db`. All four match author manifest.
- Evidence from Codex: 39 unit + 38 model + 9 accounting + 30 Stage3 = **116 selected author PASS**, compile PASS; initial RED/ERROR retained. These are *author-run*, not independently re-executed. The earlier Stage3 regression evidence records an older S4A source SHA than final unit test; it does not prove an exact final-revision Stage3 run (legacy Stage3 tests do not import new S4A module). No full regression/CI.
- Fake transport and local guard establish bounded offline author-tested behavior; injected arbitrary trusted Python transport is not a production sandbox. Context authorization, durable Turn/RAW/attempt identity, reservation/budget checks and OAuth sender are future integration responsibilities. Missing usage is not zero spend.
- Author receipt reports 595/595 user storage unchanged and launcher STANDARD; these are not independent local-disk audits. Published commit changed `.obsidian/workspace.json` outside TASK write-scope (origin UNKNOWN); verifier did not revert it.

## OPEN / NEXT

Keep `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` OPEN (historical CI cause UNKNOWN). Create `FOLLOWUP-WUA-S4A-INTEGRATION-001` OPEN/UNASSIGNED for Stage4B: one shared sender with explicit Stage3/Run Store/B2 gates, model/context snapshots, usage/accounting, late/UNKNOWN and safe network tests; **separate USER GO before any production integration**. Real GigaChat/OAuth/paid calls, Colibri, MCP, Stage5+, Blueprint execution, STANDARD sending: NO GO. No new TASK allocated.

**DOC ITERATION CLOSED / S4A BOUNDED PASS.** Publication of review to GPT needs user acceptance into main.