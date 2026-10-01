# TASK 151A — remote context

STATUS: IMPLEMENTATION + LOCAL REGRESSION PASS; LIVE ACCOUNTING EVIDENCE PARTIAL.
CONTROL POINT: KT-1 NOT YET CLOSED.

Implemented accounting:
- provider/context/usage accounting schema in provider_accounting.py;
- Planner Session + direct Planner provider attempts;
- Executor provider attempts;
- Dredd Final Audit + Planner Review provider attempts;
- AUDIT_DIAGNOSTIC physical Executor-model call accounting;
- Run Store aggregation for planner/executor/dredd with UNKNOWN usage preserved as unknown, not zero;
- current Compressor emits provider_attempt_started/terminal into existing compressor_logs JSONL.

Local validation after latest runtime repair:
- targeted physical-write: 21 passed + 20 subtests;
- expanded accounting/planner/file-editing: 121 passed + 31 subtests;
- full unittest: 311/311 PASS;
- UltraApp UI smoke PASS;
- git diff --check PASS.

Live history:
- T-023/R-023: auth env missing before any model call; historical run remains old-format RUNNING. Runtime now terminalizes provider_auth_error.
- T-024/R-024: Planner accounting worked; blocked because git_diff arguments were invalid. Planner exact evidence-tool contracts repaired.
- T-025/R-025: write_scope=Документация correctly blocked ultra_ui.py; configuration issue.
- T-026/R-026: write_scope='.'; Windows os.replace on running ultra_ui.py hit WinError 5. Runtime now has restricted current-entry-script in-place fallback. R-026 recovered to FAILED/NOT_RUN with interrupted usage UNKNOWN.
- T-027/R-027: this was actually B2, not B1. It terminalized BLOCKED/readiness_no_progress after 20 API requests / 17 physical tool calls. Provider accounting: 25 started=25 terminal, total known tokens=1,736,351. Planner 5 calls max context 20,491 chars; Executor 20 calls, context grew about 24.8k -> 306k -> 615k -> 924.5k chars because full file tool results accumulated in Executor transcript. This is baseline evidence for future TASK151G Stage Context Compiler, not something to optimize inside 151A.
- R-027 benchmark marker was removed from ultra_ui.py. Cleanup briefly joined two imports; compile caught it immediately; boundary repaired. Current marker count=0; py_compile ultra_ui.py/server.py PASS; UltraApp smoke PASS; git diff --check PASS.
- Canonical isolated B1-clean headless run: workspace Alarm/TASK151A_BENCH/B1_clean, run_id 20261001_004029_1585f3. SUCCESS / Final Audit PASS, exactly 3 physical tools, runtime about 33s. Provider calls=8: Planner2 / Executor5 / Dredd1. Tokens: Planner 7242 / Executor 21798 / Dredd 4102 / total 33142. Accounting complete=true. Contexts stayed bounded around 12.6k-23.7k chars.
- First isolated B1-dirty attempt: Alarm/TASK151A_BENCH/B1_dirty. It reached Final Audit after exactly 3 physical tools, then provider returned HTTP 429. Run FAILED / Audit ERROR; Planner2=4624 tokens, Executor6=26139 tokens, Dredd usage UNKNOWN; total UNKNOWN. Do not use this run for clean-vs-dirty comparison. Retry only after provider cooldown, in a fresh sibling workspace with the exact same task text/models/permissions.
- B3 live profile still pending.

Benchmark definitions from canonical doc20:
- B1 = small file: WRITE -> exact READ -> exact EQUALS -> Final Audit.
- B2 = existing-code change + compile/test/smoke.
- B3 = semantic/analytical task where Executor is genuinely needed.
- B1 clean/dirty comparison uses identical models, permissions, task content and corresponding controlled initial workspace state. Do not use Git reset/clean/worktree; Git remains user-controlled.

Desktop Commander Remote investigation:
- installed package 0.2.52;
- parent remote node and local MCP child are expected two-process architecture, not duplicate Remote sessions;
- normal remote health-check every 10s, joining wedge 30s, heartbeat-stale 75s; capable last_seen cadence 5 min vs server 15 min threshold, so ordinary short idle should not intentionally disconnect;
- QuickEdit=0 and remote code does not read stdin; random Enter is not a valid keep-alive;
- MCP SDK default local request timeout=60s;
- current callClientTool catches/rethrows transport/request errors but does not discard/restart a hung-but-alive child. PID can remain alive and isReady can remain true while execution plane is unusable;
- public upstream issue #633 describes the same false-online/control-plane-vs-data-plane failure class;
- do not patch the live Remote package while unattended. A short technical note was added to Документация/22_Техническая информация.md after hash-matched Alarm backup.

Safety / backups:
- pre-151A and repair backups remain in Alarm until TASK151A final close.
- Alarm/TASK151A__ultra_ui_before_R027_probe_cleanup.bak remains until final close.
- Alarm/TASK151A__22_before_remote_note.bak remains until final close.
- no Git commit/push/pull/reset/clean/checkout/switch/config.

NEXT SAFE STEPS:
1. After provider cooldown, run B1-dirty retry in a fresh isolated sibling workspace with exact B1-clean task text/models/permissions and one unrelated pre-existing file.
2. Run one small isolated B3 semantic benchmark after cooldown.
3. Verify every live provider attempt has started+terminal identity, context accounting and known/explicit-UNKNOWN usage.
4. Decide whether KT-1 needs additional repeated samples now or whether the documented minimum-5 benchmark series belongs to later statistical comparison; do not burn tokens blindly.
5. Reconcile 05/06/21 only after live evidence set is sufficient.
