# OFFLINE checks — 17.11.2026

Credentials were removed from test processes. No OAuth, catalog or inference request was made. No Git/GitHub operation was used.

| Check | Result |
|---|---|
| `python -B -m unittest -q test_web_alarm_model_cards test_web_alarm_ordinary_application test_web_alarm_gigachat_multimodel test_web_alarm_evm_unified` | **64/64 PASS**, `evidence/python_final_full.txt`; includes one Turn handoff, synthetic/foreign denial, full diagnostic reply preservation |
| `node --test test_web_alarm_evm_ui.js test_web_alarm_ultra_chat_ui.js` | **120/120 PASS**, `evidence/ui_final.tap`; includes pinned windows and F5-style UI flows |
| `python -B -m unittest -q test_web_alarm_standard_live` | **13/13 PASS**, `evidence/standard_live.txt`; existing bounded GigaChat onramp preserved |
| S1 guarded inventory | **69/69 PASS**, 0 isolation violations, `evidence/s1_final.txt`; exact reviewed AST pins reconcile the current launcher, EVM metadata and Ordinary bridge. No new physical provider send path. |
| S2 guarded isolation | **73/73 PASS**, 0 isolation violations, `evidence/s2_final.txt`; exact reviewed policy gates cover the changed Ordinary modules and current GigaChat/standard live owners. |

## Operational-grant amendment, 17.11.2026

The first system-Python attempt could not import `httpx`; the project `.venv` was used. Before updating the old oracles and AST pins, the targeted run correctly failed on obsolete `MAX_SENDS`/12/128 expectations and changed reviewed AST. The new runtime and guard paths were inspected, then the pins were updated and the following checks passed without provider network access:

| Check | Result |
|---|---|
| `.venv\\Scripts\\python.exe -B -m unittest -q test_web_alarm_gigachat_live_control test_web_alarm_standard_live test_web_alarm_gigachat_multimodel test_web_alarm_evm_unified test_web_alarm_model_cards test_web_alarm_ordinary_application` | **85/85 PASS**, `evidence/python_operational.txt`. Includes full 27 KB answer, 13th send, idempotency, response guard, approval envelope and EVM regressions. |
| Two added exact-pin and invalid-grant negative tests | **2/2 PASS**, same evidence file. |
| `node --test test_web_alarm_evm_ui.js test_web_alarm_ultra_chat_ui.js` | **120/120 PASS**, `evidence/ui_operational.tap`. |
| `.venv\\Scripts\\python.exe -B test_rt002_s1_routes.py` | **69/69 PASS**, 0 isolation violations, `evidence/s1_operational.txt`. |
| `.venv\\Scripts\\python.exe -B test_rt002_s2_budget_policy.py` | **73/73 PASS**, 0 isolation violations, `evidence/s2_operational.txt`. |

No real OAuth, catalog or inference call was made. Physical browser and paid API checks were not run.

An initial Python run had an obsolete EVM timeout oracle and a stale source-text check for credential ownership; both test expectations were updated to the existing runtime owner/new timeout contract. An initial JS run expected a check POST without a write token; the fixture now supplies the required capability. Early S1/S2 runs exposed stale exact AST pins from current source and the new EVM/Turn changes; pins were reviewed and reconciled before final green runs. Full Windows CI and physical browser/live provider checks were not run. Real model caps, entitlement, tariff and additional six-model inference remain unknown.
