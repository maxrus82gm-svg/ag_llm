# Проверки и точная collection

Финальный Windows-run: `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/runs/attempt-20261024-013425-5ffffe57`. **24 collected / 24 PASS / 0 FAIL / 0 ERROR / 0 SKIP**. Сборки Relay/Gateway: exit0, warnings-as-errors. Финальные исходники и бинарники скопированы в source_snapshot и сверены SHA-256; compiler argv — build.json. SDK2 установленный, тесты не вызывают handlers напрямую.

Команды: см. README.md. Baseline regression: `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/runs/regression-20261024-012158-837df4bd/results.json` — **63/63 MCP checks; 24/24 security methods**, без переписывания старого отчёта. Common fixture path guard расширен ровно на текущую TASK/runs; прежние default/interface сохранены.

## Exact selectors

- `NpfsTests.test_01_official_sdk_four_tools_and_readonly` — PASS
- `NpfsTests.test_02_restart_and_proxy_environment` — PASS
- `NpfsTests.test_03_pipe_missing` — PASS
- `NpfsTests.test_04_remote_smb_and_bad_name` — PASS
- `NpfsTests.test_05_wrong_server_pid_sid_image` — PASS
- `NpfsTests.test_06_gateway_rejects_wrong_client_image` — PASS
- `NpfsTests.test_07_wrong_grant` — PASS
- `NpfsTests.test_08_session_mixing` — PASS
- `NpfsTests.test_09_oversize_partial_duplicate_and_bad_type` — PASS
- `NpfsTests.test_10_owner_crash_and_unresponsive_stdin` — PASS
- `NpfsTests.test_11_exclusive_instance` — PASS
- `NpfsTests.test_12_wrong_peer_oracle_and_mutant` — PASS
- `NpfsTests.test_13_pipe_response_bounds_correlation_replay_and_close` — PASS
- `NpfsTests.test_14_os_tables_and_tcp_mutation` — PASS
- `NpfsTests.test_15_sdk_child_job_cleanup_after_gateway_crash` — PASS
- `NpfsTests.test_16_scoped_gateway_raw_wire_replay` — PASS
- `NpfsTests.test_17_full_duplex_concurrent_requests` — PASS
- `NpfsTests.test_18_slow_partial_stdio_is_bounded` — PASS
- `NpfsTests.test_19_source_no_network_or_child_and_python_syntax` — PASS
- `NpfsTests.test_20_gateway_protocol_and_config_pins` — PASS
- `NpfsTests.test_21_authority_session_binding` — PASS
- `NpfsTests.test_22_hard_lifetime_kills_only_owned_relay` — PASS
- `NpfsTests.test_23_unicode_relay_image_path` — PASS
- `NpfsTests.test_24_official_sdk_cancellation_crosses_relay` — PASS

## Oracle / риск / предел

| Проверки | Риск и независимое следствие |
|---|---|
| 01–02 | Official SDK initialize/list/four tools; ошибки foreign TASK/unknown tool/types/extra/replay; canonical response hashes, nonce, actual seed JSON и receipt; restart и ambient proxy environment |
| 03–08, 11–12, 20–21 | Missing/remote/wrong name; peer PID/SID/image; DACL exclusive instance; bad key/session/protocol/source pin; authority-session binding; before-auth state absent |
| 09, 13, 16, 18 | JSON duplicates/types/size, partial input/output, response bounds/correlation, wire replay, unresponsive/slow peer; bounded stop |
| 10, 15, 22 | Gateway crash, own worker OS wait/job descendant cleanup, idle/EOF; shortened hard deadline control |
| 14 | OS TCP/UDP v4/v6 PID sampling + Toolhelp C children; normal 51 samples / zero endpoint rows, mutant 51 samples / 49 observed rows; independent owned loopback accept. Finite sampling only |
| 17, 23–24 | Twelve concurrent SDK requests retain correlation; real SDK ping through Unicode image path; SDK cancellation reaches an intentionally stalled independent pipe peer with the matching requestId |
| 19 | Source/syntax gate; C path excludes Python/network/child launch, fresh fixture scope remains strict |

Security controls: TCP dial mutant and wrong-peer mutant are deliberately unsafe copied sources under this attempt only. Normal policy oracle PASS; mutated policy oracle **FAIL** is the required detection result. They are not production flags. A shortened-watchdog executable checks a lifecycle branch. Nested negative fault cases are assertions inside methods, not extra inflated test counts.

Unknown cross-SID/Windows WFP/Go/V2Ray/ordinary Chat: NOT RUN / NOT VERIFIED. Remote-name rejection occurs before connect; no real SMB request. Cancellation test is a transport fault probe against a scoped owned fake peer, not WebAlarmApi/Chat E2E. The four successful tools use the complete real SDK/API chain in 01/02.

Initial failures and all later runs: evidence/attempt_catalog.json and original result files. Early aliases, WinError87 and bad launcher image pins are classified; they were not hidden by final PASS. Early full intermediate source snapshots are missing; final source/binary snapshot and initial hash diagnostics retained. No CI or independent verifier execution claimed.
