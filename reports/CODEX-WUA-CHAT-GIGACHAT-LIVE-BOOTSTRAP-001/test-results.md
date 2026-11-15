# Addressed OFFLINE checks

Environment: Windows, project `.venv` Python, real credential/scope removed from each test process, `PYTHONDONTWRITEBYTECODE=1`. No account API request was made.

| Check | Result |
|---|---|
| Final combined run, `evidence/combined_offline.txt` | 31 PASS, 0 FAIL/ERROR/SKIP, exit 0 (52.758 s). Includes 5 new bootstrap cases and 26 H38 Ordinary/multimodel cases. |
| Final narrow bootstrap rerun after grant-bound tightening, `evidence/bootstrap_final.txt` | 6 PASS, 0 FAIL/ERROR/SKIP, exit 0 (1.063 s). Includes broad-grant rejection. |
| New bootstrap cases | Existing ledger required and preserved; probe rejects inference grant; session closes; failed catalog keeps server unserved and closes it. |
| Reused H38 cases | OAuth/catalog/one physical POST/reopen/RAW/usage/hold cases remain green through MockTransport only. |
| Initial combined run | 29 PASS, 1 ERROR, exit 1: new test oracle used nonexistent `Recovered.events`; corrected to `event_count`, then 5/5 new tests PASS. No product defect observed. |
| Registry introspection | 6/6 registered and enabled, actual account availability unverified. |
| Windows user environment + system TLS shape | Credentials present and inherited value equal; scope `GIGACHAT_API_PERS`; 99 CAs and hostname/TLS verification enabled. No provider handshake. |
| Fresh Workspace/ledger readback | New Workspace, new empty chat, ledger 0 events, registry/identity/ledger match. |

**NOT RUN:** actual OAuth/catalog/inference; provider TLS handshake; physical Chromium owner UX; independent review of this new composition; full B2 regression/Windows CI. H38's previously accepted broad OFFLINE evidence is reused, not re-executed here. STANDARD/TEST launchers were inspected and not altered. Existing H38 browser/F5 tests passed in the addressed suite; physical F5 remains NOT RUN.
