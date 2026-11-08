# WEB25 — H-CODEX-000024 / RT-002 B2 S1 inventory reconciliation — independent review 08.11.2026

**Task:** `CODEX-RT002-B2-S1-INVENTORY-RECON-001`.  
**Publication:** `main@a455d97f5379b56933fb08655c8542617afbf9d3` (#542), parent user #541, source `test_rt002_s1_routes.py` SHA-256 `35426388b49eb4a8154f5dfe8717ff4f3796b315ce3b391a71db6834e4a09696`.  
**Verdict:** **PASS / TARGETED INDEPENDENT WINDOWS OFFLINE S1** for 69-method exact guarded selector and 23 extra reconciliation/fake/mutation tests. **Overall H24 product PARTIAL** because guarded S2 is still 72 PASS / **1 FAIL**. Not full B2/Stage6 PASS, not S3b predecessor clearance.

## Source/package independent readback

GitHub #542 published one changed engineering source `test_rt002_s1_routes.py`, own task artifacts, history sequence and Codex mechanical slot; `.obsidian/workspace.json` incidental user UI state not attributable to Codex, unchanged by verifier. `H-CODEX-000024` record found; author `finish ROTATED / exit0`, БЛОК 1 WAITING, БЛОК 1.1 H24; own B2–B4 remained previously untouched. Read author `report.md`, `manifest.json` (148 entries), route reconciliation and S2 amendment; independently checked source SHA using Windows `Get-FileHash`. **Not** claiming all 148 manifest hashes independently audited. Author reports 202 existing source/CMD byte-identical; reviewer confirms changed-source scope in GitHub commit, not independent before/after 202-byte audit.

## Actual independent executable proof (Windows device)

Using the authorized Desktop Commander Windows host, pinned local S1 SHA matched published GitHub #542:

- Exact `run_guarded.py s1`: 69/69 PASS, no fail/error/skip, gate PASS, exit 0; isolation violations/evidence problems 0, Python 3.12.10. Independent 42.608s; temp log SHA-256 `2e7dc4b18b5a2a3b1d666133db7a4372622a65484dd192cde8b92bf139200c3a`.
- Exact `run_guarded.py checks`: **23/23 PASS**, exit0, zero skips/isolation problems. Includes **18 in-memory source mutation cases** and fake checks; reviewer observed 10.229s. Three separate author oracle-weakening runs were **NOT independently repeated**; author evidence retains expected RED x3.
- Exact standalone S2 core `test_rt002_s2_budget_policy.py`: **72 PASS / 1 FAIL**, gate FAIL exit1, isolation violations 0. Failure exactly `IsolationTests.test_no_production_module_imports_the_policy_yet`: source scan sees `ultra_budget_ledger.py` import `ultra_budget_policy`. Independent 1.511s, temp log SHA-256 `68a02fd45238230d4247699413830eccbc8c40b3f50d287f4d1d40e443c42f17`.

Structured run record: `reports/CHATGPT-WEB25-CODEX-RT002-S1-REVIEW-20261108/independent_runs.json`. These are independent terminal outputs at verified source SHA, not author PASS copied. Guard installs test/fake transport; HTTPX logs naming external host reflect **mock transport**, not actual paid network calls. No production config, real Workspace or live model was intentionally invoked. Independent console outputs observed in tool transcript; full temporary raw logs are **not** advertised as published report artifacts.

## S1 semantic findings and limits

S1 preserves `EXPECTED_SEND_SITES` 7 physical LLM POST + 1 OAuth POST unchanged for S2 consumer and now compares full `EXPECTED_PRODUCTION_SITES` including 4 additional reviewed constructions: `web_alarm/launcher.py` import/urlopen (`LOCAL_HTTP_ORIGIN`, initial localhost GET), `ordinary_chat_service.py` `getattr.send` (`CAPABILITY_CHECK`) and `dynamic.send` (`POTENTIAL_LLM`). The latter remains a **potential physical send** for future S3b, not safe. `web_alarm/model_cards.py` exact two metadata endpoint literals are classified through pinned AST node+reference census, not whole-module exclusion. New send/alias/getattr, extra callers, host changes and metadata-to-send mutations trigger fail-closed S1 tests. These are static AST/source-snapshot oracles, not comprehensive dynamic Python network control.

**OPEN:** launcher local-origin does not prove redirects/proxies ultimately remain loopback; model_cards injected authorized checker can be future external send boundary; future adapter/plugin/config destinations need independent S3b inventory. No S1 green certificate for all future physical routes or S3b.

## S2 confirmed failure and disposition

S2 `IsolationTests.test_no_production_module_imports_the_policy_yet` iterates S1 `_production_modules()` including newly added standalone OFFLINE `ultra_budget_ledger.py`, and asserts no such module imports policy. H23 OFFLINE S3a necessarily imports S2 policy. The S2 oracle is older than that module: **a contract-classification mismatch**, not evidence of production dispatch. H24 changed only S1 test, S2 and ledger are unchanged; no separate pre-H24 S2 executable baseline exists, so don't misstate one. New `S2-OFFLINE-LEDGER-ISOLATION-ORACLE` requires a **separate scoped user-authorized test-oracle repair** preserving production no-early-enforcement rule and negative oracles; no blanket allowlist for arbitrary policy imports. Current S2 gate FAIL remains an actual blocking result for full B2 successor approval.

**Stage6 state:** S3a author 35 PASS remains **NOT independently executed/accepted** here. S3b physical HTTP budget guard and S9 reconciliation NOT implemented, Ordinary Chat route/policy numeric defaults not approved, historical ledger migration and RAW wire retention/fencing OPEN. No real GigaChat/OAuth/paid, no UI / whole repo Windows CI; those were NOT RUN.

## Decision / NEXT

**DOC ITERATION H24:** S1 scoped inventory repair **INDEPENDENT BOUNDED PASS** with exact source and non-regressed mutation sensitivity. Overall task **PARTIAL** due S2 gate FAIL. Do not reopen S1 change just to hide S2 failure. Safe next candidate — only after USER GO — narrow `test_rt002_s2_budget_policy.py` oracle reconciliation for OFFLINE S3a classification, plus independent S3a runtime and USER Ordinary Chat policy decisions before authorizing S3b. All approved RT-002/B2 §5а predecessor rules and Stage7 HOLD remain.

Sources: `reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/{task_record.json,report.md,manifest.json,route_reconciliation.md,amendment_request_s2.md,followups.json,evidence/}`; №20 §5а, №21, №37.
