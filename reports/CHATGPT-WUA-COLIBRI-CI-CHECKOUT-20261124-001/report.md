# WUA #667 — Windows Actions checkout long-path remediation

**Status at commit: hosted CI re-run NOT YET VERIFIED; source-only #666 remains OFFLINE PASS.**
Original failed GitHub Actions workflow run 45251979977 for WUA #666 32330655a617bba049ea423759345f68c744012a, job windows-offline 137963742139. The Git checkout failed before installing Python or running any test with exit code 128, Filename too long, at a deeply nested historic mirror under reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001. All subsequent S1/S2/D8/HTTP/JS steps were SKIPPED; no false PASS.

The fix makes git configure core.longpaths=true on Windows before actions/checkout, and uses sparse checkout cone mode to include root source and test files, web_alarm, tools and #666 static S1 helper folder; excludes irrelevant multi-level archived reports/mirrors that cause MAX_PATH errors. No files or history deleted from repository. Windows full private RAW S1 is not hosted; only 16 static cases are scheduled. Existing S2 73, D8, five negative tests and Python/JS regression remain required and fail-closed. The source state before CI was verified locally: full S1 69 PASS, S2 73 PASS, D8 1 PASS, S1 static 16 PASS, safety negatives 5 PASS, Python 88 PASS, JS 207 PASS. First local WinError10053 recorded; full retry passed.

Run result of new commit must be verified through GitHub Actions after push, with each step conclusion checked. If checkout succeeds but a needed test asset was excluded, treat that as a CI failure and fix scope explicitly; do not broaden to nested historic reports blindly. No actual Manager, STD, paid API, or production invocation. Overall MVP1 remains PARTIAL and unaccepted; next is owner GO read-only real health preflight only after separate approval.

PLAN_READ 2026-11-24T00:46:49+05:00 SHA256 0fb824ed823b0ddbeed3192e90712165136f8698efc0822b0fac07d376d788ac, archive SHA256 1071b531a3985ecb08d474651f73cedaf5aeb73cec1108b19daf764848fb4102. New WUA-only task H-CHATGPT-000021.
