# Reproduce H33 on isolated Windows

Author used local Windows, Python 3.12.10 in `.venv`, existing dependencies. Independent GitHub-hosted Windows run is NOT RUN by the author: no Git/GitHub authority. Coordinator should follow №22 GitHub Actions Windows and preserve exact published source SHA/run ID/logs/artifact. Do not call Desktop Commander for reproducible offline tests.

Use short checkout and TEMP paths (for example `D:\w` and `D:\t`) to avoid Windows MAX_PATH. Set TEMP and TMP in that CI process before Python starts; never change the host globally. Install the repository's declared dependencies in Python 3.12 plus the existing test dependencies (`pytest==9.1.1`, `httpx==0.28.1`; pytest provides subtests here); Node is required for UI tests. See `evidence/environment.json` for exact author versions. Do not access real secrets; remove GIGACHAT_* variables. No provider/network access is needed for any test. Loopback is permitted only for synthetic Web API tests and asyncio self-pipe.

From the checkout root, use unique stage names (existing evidence is never overwritten):

```powershell
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001\run_checks.py independent_h33 test_web_alarm_gigachat_transport.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001\run_standalone.py independent_s1 test_rt002_s1_routes.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001\run_standalone.py independent_s2 test_rt002_s2_budget_policy.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001\mutation_checks.py independent_mutations
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001\run_checks.py independent_quality --import-mode=importlib reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/isolation_checks.py reports/CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001/isolation_checks.py
node --test test_web_alarm_ultra_chat_ui.js
```

Regression selection/actual command is recorded verbatim in `evidence/regression.result.json`; rerun the same selected node IDs through run_checks.py with a new stage. The child installs the pinned H27 process guard before runtime imports and inherits it via PYTHONPATH; arbitrary plugins are disabled. Only three exact historical guard-control node IDs can produce the expected nine denials. Unexpected denial counts must be zero. Full case lists distinguish base tests from subtests; do not sum overlapping suite totals.

S1 and S2 require their dedicated runners. Plain pytest/unittest discovery is not their acceptance command. S1 needs exact historical R031/R026 RAW pins; if unavailable in CI, record that gate NOT RUN with missing pins, keep failure logs and never manufacture replacement RAW. Local author S1 had the pinned evidence and passed. S2 core uses the pinned derived dataset; provenance mode is separate and was NOT RUN.

Mutations run two real negative tests with in-memory modifications, require RED without errors, and verify disk source hashes unchanged. Their failure logs are expected evidence, not regression failures. The first baseline run `initial` has a corrected test-expectation failure; preserve it. Do not rerun the physical TEST CMD/browser/manual GUI smoke as part of ordinary CI; H31 physical device gate remains separately tracked. Do not rotate a verifier's task slot or run finish when reproducing tests.
