# H34 independent Windows reproduction

Author checks are local, Windows/Python 3.12.10, pytest 9.1.1, HTTPX 0.28.1, Node 22.20.0. Exact versions: evidence/environment.json. Independent GitHub run is NOT RUN by author; no Git/GitHub authority. Coordinator follows №22 with published exact source SHA, windows-latest, run ID, raw logs and artifact. No Desktop Commander needed for these automated tests.

Use short checkout/TEMP paths, e.g. D:\w and D:\t. Set TEMP/TMP in the CI process before Python, not system-wide. Install repository dependencies plus pytest 9.1.1; subtests are provided by this pytest version. Do not supply real GIGACHAT_* variables or secrets. The runner omits credential variable names before retrieving values. H27 guard is installed before runtime imports, inherited by Python children, plugins disabled; only synthetic TEMP storage and explicit loopback are allowed.

Run from project root with **new stage names**, because existing evidence must not be overwritten:

```powershell
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\run_checks.py independent_legacy test_gigachat_admission.py test_planner_session.py test_planner_diagnostics.py test_provider_attempt_integration.py test_verifier_runtime.py test_final_audit.py test_task_planner.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\run_checks.py independent_h33 test_web_alarm_gigachat_transport.py test_web_alarm_ordinary_admission.py test_web_alarm_ordinary_core_bridge.py test_web_alarm_perchat_usage_settings.py test_rt002_s3a_ledger.py test_ordinary_chat_service.py test_web_alarm_ultra_chat_turn.py test_web_alarm_ultra_chat_turn_service.py test_web_alarm_ultra_chat_turn_s4b.py test_web_alarm_ultra_chat_turn_http.py test_web_alarm_ultra_chat_s5.py test_run_store_v2.py test_web_alarm_launcher.py::StableEntryTests test_web_alarm_ordinary_test_activation.py::ActivationTests::test_active_profile_uses_bridge_and_old_stage5_is_available test_web_alarm_ordinary_test_activation.py::ActivationTests::test_missing_test_config_cannot_fall_back_to_standard
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\run_standalone.py independent_s1 test_rt002_s1_routes.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\run_standalone.py independent_s2 test_rt002_s2_budget_policy.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\run_checks.py independent_quality --import-mode=importlib reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/isolation_checks.py reports/CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001/isolation_checks.py
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\server_gates.py independent_server_gates
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001\mutation_checks.py independent_mutations
node --test test_web_alarm_ultra_chat_ui.js
```

Do not run reconcile_pins.py during verification: it is an explicit author maintenance record, not an acceptance step. Verify published pins and failure sensitivity as shipped. The entire production import graph remains scanned.

S1/S2 require dedicated runners, not pytest discovery. S1 needs exact historical pinned R031/R026 RAW: absent in CI → gate NOT RUN with evidence, never manufacture replacement RAW. Local author had matching pins. S2 core uses the unchanged pinned derived dataset; provenance mode was NOT RUN. Raw unittest transcripts are saved as .unittest.txt because *.log is ignored.

Broad legacy suite may take ~8 minutes on author Windows; runner budget is 600 seconds and writes .cases.current.json progress. Timeout is exit124 / INCOMPLETE and preserves partial output; never count it as PASS. Underlying pytest exit0 is insufficient if unexpected guard denials are nonzero: effective runner exit is 1. Historical pre-fix artifacts retain their original JSON fields; report explains outer exit and denied boundaries.

The existing compile/UI helpers use -E/remove PYTHONPATH. server_gates.py explicitly prepends the unchanged guard to the child -c code, then invokes the real helpers. Compile output is TEMP, UI source is byte-identical in TEMP cwd, LOCALAPPDATA is empty TEMP. The normal UltraApp constructor is withdrawn/destroyed. No app source or guard is patched to gain permission. This is synthetic constructor smoke, not user CMD/Chrome/F5 acceptance.

Three in-memory mutations must produce expected RED against real tests: budget DENY disabled, actual HTTP wire check removed, terminal verification disabled. Failure transcripts must contain assertions, not errors; disk source hashes remain unchanged. Earlier unexpected failures and blocked Git attempts remain preserved; corrected fixtures explicitly simulate unavailable Git, no Git executable is run. Do not classify those historical incidents as expected guard controls.

Upload report/manifest, all result/cases/progress JSON, guard events, stdout/stderr, source fingerprints, physical traces and expected RED transcripts. Do not upload synthetic RAW stores, auth headers, credentials or host environment. Do not run task_slot_rotate.py finish when merely reproducing this task's tests.
