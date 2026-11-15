# CHATGPT-WUA-STANDARD-LIVE-CI-REPAIR-001 — missing pinned S1 reconciliation fixture in Windows sparse checkout

**Scope:** CI infrastructure correction ONLY. No runtime source, model permissions, tests, history or provider contracts changed. Separate from implementation candidate `CHATGPT-WUA-STANDARD-LIVE-ONRAMP-001` (commit №623, SHA `24aa1e2de31001961e01bad93673d5dc957b8d06`).

**Observed first run:** GitHub-hosted Windows Actions [run 43745198104](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43745198104) on the exact №623 commit failed with **34 PASS / 1 ERROR** (35 tests). All 7 new STANDARD onramp tests PASS; H38 bootstrap passed; the remaining GigaChat multimodel tests passed except one import-time `FileNotFoundError` for root `rt002_multimodel_reconciliation.json` in `test_rt002_s1_routes.py`. `actions/checkout` intentionally used sparse patterns `/*.py` and `/web_alarm/`, which omitted the tracked JSON. No provider credentials, OAuth, catalog or inference used.

**Repair:** include only `/rt002_multimodel_reconciliation.json` in the existing sparse-checkout file allowlist and assert it exists at test entry. Do not copy the fixture from historical reports, change pinned source, weaken S1 or disable the failing test. No broader full repository checkout (legacy Windows MAX_PATH blocker).

**Acceptance:** fresh GitHub-hosted Windows run on the new commit must execute all 35 tests; check exact SHA, exit code, full job logs and uploaded artifact; all PASS with zero FAIL/ERROR. Until then verdict **PENDING / CI NOT RUN FOR REPAIR**; unrelated physical Chromium, account balance and five additional real model inferences NOT RUN. This is infrastructure-only and does not make STANDARD LIVE production-ready.
