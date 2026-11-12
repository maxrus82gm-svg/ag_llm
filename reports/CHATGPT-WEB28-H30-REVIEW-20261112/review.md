# WEB28 — H30 independent read-only pre-send preflight review

**2026-11-12** · TASK `CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001` · HISTORY `H-CODEX-000030`.
**Source:** GitHub main №574 `d26c4ad9380b2bb1a0ccd1dd88bdf2facd3c954c`; Codex H30 original source base №571 `3acd5b240ea856496bcb446fdfecaa165de0c172`.
**Verdict:** **PASS / BOUNDED INDEPENDENT WINDOWS OFFLINE — H30 READ-ONLY P0/P1 PREFLIGHT only**. Historical author report PARTIAL retained, full S3b still OPEN.

## Evidence
- A separate, read-only GitHub clone checked out exact main №574 on authorized Windows, Python 3.12.10 and isolated test venv; no changes to any product source, real Workspace, STANDARD, Tkinter, credentials or LIVE.
- Seven `wa4a_acceptance.py` selected tests: four existing H30 tests (forbidden real transport; invalid IDs/model/REAL config; pre-send REJECTED means FAILED/0 usage attempts; UNKNOWN retry not sent twice) plus three adjacent independent checks (invalid response cannot replay; late cancel records known usage but never success; READY replay uses frozen context). **7 PASS/0 FAIL/0 ERROR/0 SKIP, exit 0, 2.984 s; zero network/DNS/secret/OS isolation violations.** Source hashes and per-test records in `reports/CHATGPT-WEB28-H30-REVIEW-20261112/independent_runs.json`.
- Initial three local attempts were NOT PASS: 1/7 (6 errors), 2/7 (5 errors), 2/7 (5 errors). Diagnostic stack traced to `run_store._atomic_json` `FileNotFoundError` from Windows MAX_PATH in synthetic TEMP filename; a shorter throwaway TEMP produced clean 7/7. No source changes, no weakening of guard. These earlier outcomes are not product regression evidence.
- Independently verified SHA-256 pins at H30 original base №571 for `ordinary_chat_service.py`, `web_alarm/ordinary_chat_bridge.py`, `web_alarm/turn_service.py`, `ultra_budget_policy.py`, `ultra_budget_ledger.py`, plus H30 report SHA `4c671ac5a4055e40947432b741cdf1dc3216c44d3e2ce49ac6551324a115b02b`.
- F-01 source finding from H30 already fixed separately by H31: GitHub independent Windows [run 43264689001](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43264689001) 21/21 PASS, guard0. This is neither H30 code change nor H30 test replacement.

## Technical map and residual
`OrdinaryCoreAdapter.execute` exact fixture admission, shared `ordinary_chat_service.execute_request` injected transport, durable `TurnService` idempotency/UNKNOWN, pure S2 `serialize_request_body` and S3a `BudgetLedger.reserve/mark_sent/recover` are reusable. **Missing:** Ordinary final HTTP wire-bytes binding, policy route/per-attempt defaults and historical ledger adoption, atomic S2/S3a admission physically adjacent to one send; no new core/transport/ledger allowed.

**NOT RUN:** actual physical HTTP send paths, broad S3b/retry/cancel/crash race, full regression, H31 physical Windows CMD/browser/F5 and Stage5 rollback, REAL GigaChat/OAuth/paid, H30/H31 backup integrity and safe cleanup on originating PC. Those remain OPEN/HOLD; user live GO required. The Windows CI H30 workflow `.github/workflows/gpt-web28-h30-independent.yml` is included in the same atomic documentation commit; **its GitHub Actions run was NOT RUN at report creation**. [Workflow](https://github.com/maxrus82gm-svg/ag_llm/actions/workflows/gpt-web28-h30-independent.yml) will run automatically on `GPT` push. Results must be verified separately before user merge; no invented run ID.

**Closeout:** full consistent task_record/№001/05 (FOLLOWUP)/06/34/40/B4/review/evidence and workflow in one numbered GPT commit №575. B1/1.1, author report, production and tests untouched. Only user merges to main.
