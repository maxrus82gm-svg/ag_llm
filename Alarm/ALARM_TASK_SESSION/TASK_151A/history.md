# TASK 151A — remote history

## 2026-09-30 / 2026-10-01 — provider/context/usage accounting implementation
TASK151A accounting was implemented for Planner, Executor, Dredd, AUDIT_DIAGNOSTIC and current Compressor, with Run Store aggregation and UNKNOWN usage preserved as unknown.

Initial local validation:
- targeted accounting/integration 13/13 PASS;
- accounting + Compressor 26/26 PASS;
- broad relevant regression 112 PASS + 20 subtests;
- full unittest 305/305 PASS;
- UltraApp UI smoke PASS;
- git diff --check PASS.

## Live B1 T-023/R-023
Failed before any provider request because the Ultra process did not see GIGACHAT_CREDENTIALS. This exposed missing terminalization around get_access_token. Fixed with canonical run_failed reason=provider_auth_error and regression coverage. Historical R-023 raw stream is not rewritten silently.

## Live B1 T-024/R-024
Accounting recorded 3 Planner attempts + 1 Dredd Planner Review, total provider tokens 18201, complete=true. RUN blocked before Executor because git_diff arguments were {}, while validator requires paths. Planner protocol now declares exact evidence-tool argument contracts and validation errors name the failing tool.

## Live B1 T-025/R-025
Started with stale UI setting write_scope=Документация. Scope enforcement correctly blocked mutation of ultra_ui.py. This was configuration, not a runtime defect.

## Live B1 T-026/R-026
Started with write_scope='.'. Planner produced a VALID plan on the first attempt, proving the paths fix. Executor reached physical write, but Windows rejected atomic os.replace(temp, ultra_ui.py) with WinError 5. The target file was writable and not ReadOnly; the specific conflict was rename/delete semantics while ultra_ui.py was the running pythonw entry script.

Repair:
- normal atomic temp + os.replace remains primary;
- only on Windows, only for an existing current entry script, and only after PermissionError from replace, runtime falls back to in-place binary rewrite with truncate + flush + fsync;
- non-entry PermissionError remains fail-closed;
- UTF-16 .jsonl semantics are preserved;
- temp file cleanup is verified.

R-026 ended as FAILED / NOT_RUN with run_failed reason=external_interruption_recovery; it did not remain RUNNING.

Post-repair validation:
- targeted file editing: 21 passed + 20 subtests;
- expanded regression: 121 passed + 31 subtests;
- full unittest: 311/311 PASS;
- UltraApp UI smoke PASS;
- git diff --check PASS.

NEXT: restart Ultra on repaired code and repeat identical B1 with write_scope='.'.

## 2026-10-01 — R-027 reclassification, canonical B1 and Remote diagnosis

R-027/T-027 was reclassified against doc20 as B2, not B1, because it changed existing code and required compile/smoke. It ended BLOCKED/readiness_no_progress after 20 API requests and 17 tool calls. New TASK151A accounting made the cost explainable: 25 provider attempts, 1,736,351 known tokens, Executor context growth from ~24.8k to ~924.5k chars due to full file tool results accumulating in the transcript. This is retained as a baseline for future 151G Stage Context Compiler.

The R-027 benchmark marker was removed from ultra_ui.py. A cleanup newline mistake was caught immediately by py_compile and repaired; current py_compile, UI smoke and git diff --check pass.

A true isolated B1-clean was then run headless in Alarm/TASK151A_BENCH/B1_clean: run 20261001_004029_1585f3, SUCCESS/PASS, exactly three tools, 8 provider calls, 33,142 tokens, accounting complete. First B1-dirty attempt reached Final Audit but GigaChat returned HTTP 429; its Dredd usage is explicitly UNKNOWN and the run is not used for clean-vs-dirty comparison.

Desktop Commander Remote 0.2.52 was inspected. The two Node processes are expected remote-parent + local MCP child. Built-in remote health checks do not support the idea that a short normal idle intentionally disconnects the device. The more credible failure is a hung-but-alive local child: MCP request timeout is 60s, while callClientTool catches/rethrows failures without invalidating isReady or discarding the child. Public upstream issue #633 describes the same false-online failure class. A concise version-specific note was added to 22_Техническая информация.md. No live Remote package patch was applied while the user is away.
