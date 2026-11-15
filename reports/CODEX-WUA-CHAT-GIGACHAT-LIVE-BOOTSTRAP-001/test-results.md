# Addressed OFFLINE checks

Stage A LIVE control probe is recorded separately in `live-evidence.md`: 1 OAuth + 1 catalog + 0 inference, grant CLOSED. No OFFLINE suite was rerun after the successful external probe because source code was unchanged.

Stage B preflight was read-only/local; `evidence/stage_b_preflight.json` records identity, ledger, process/port and TLS checks. Mandatory provider output cap and exact Lite response-version ID were unconfirmed, so no Stage B grant, OAuth, catalog or inference was executed. No new source change required a test rerun.

The later user amendment authorized a narrow H38 contract change and OFFLINE checks only. After that change, `evidence/amendment_offline_sealed.txt` records **37/37 PASS** (MockTransport and loopback HTTP), no failure/error/skip. `evidence/amendment_s1.txt` records guarded S1 **69/69 PASS** with no isolation violation. `evidence/amendment_s2_final.txt` records guarded S2 **73/73 PASS** with no isolation violation. The early amendment runs exposed test fixture accounting and AST reconciliation mismatches; those were corrected before the final passing runs. No account API call was made during the amendment. Prepared Workspace ledger readback after testing remained **0 events**.

Environment: Windows, project `.venv` Python, real credential/scope removed from each test process, `PYTHONDONTWRITEBYTECODE=1`. No account API request was made during OFFLINE tests.

| Check | Result |
|---|---|
| Final combined run, `evidence/combined_offline.txt` | 31 PASS, 0 FAIL/ERROR/SKIP, exit 0 (52.758 s). Includes 5 new bootstrap cases and 26 H38 Ordinary/multimodel cases. |
| Final narrow bootstrap rerun after grant-bound tightening, `evidence/bootstrap_final.txt` | 6 PASS, 0 FAIL/ERROR/SKIP, exit 0 (1.063 s). Includes broad-grant rejection. |
| New bootstrap cases | Existing ledger required and preserved; probe rejects inference grant; session closes; failed catalog keeps server unserved and closes it. |
| Reused H38 cases | OAuth/catalog/one physical POST/reopen/RAW/usage/hold cases remain green through MockTransport only. |
| Initial combined run | 29 PASS, 1 ERROR, exit 1: new test oracle used nonexistent `Recovered.events`; corrected to `event_count`, then 5/5 new tests PASS. No product defect observed. |
| Registry introspection before Stage A | 6/6 registered and enabled; account availability was then unverified. Stage A subsequently returned all six IDs. |
| Windows user environment + system TLS shape | Credentials present and inherited value equal; scope `GIGACHAT_API_PERS`; 99 CAs and hostname/TLS verification enabled. No provider handshake. |
| Fresh Workspace/ledger readback | New Workspace, new empty chat, ledger 0 events, registry/identity/ledger match. |

**NOT RUN in the amendment:** real OAuth/catalog/inference, physical Chromium owner UX, first real response/F5, full B2 regression/Windows CI. Stage A OAuth/catalog were already completed under their separate GO and were not repeated. H38's previously accepted broad OFFLINE evidence is reused; addressed H38/S1/S2 suites above were run after the change. STANDARD/TEST launchers remain unaltered.
