# TASK 151B — remote context

STATUS: DONE.
CONTROL POINT: KT-2 FRESHNESS = DONE.

Implemented:
- evidence applicability binds task_block_id, run_id, plan_version, stage_id, evidence_generation, requirement identity, tool, arguments fingerprint, dependency targets + observed state fingerprint, execution sequence, executed/result and source record identity;
- REPLAN does not inherit stale non-persistence PASS from an older plan version;
- execution repair increments the affected stage evidence generation;
- target/dependency drift invalidates old satisfied evidence and reopens the stage;
- missing/unknown source/dependency identity is fail-closed;
- Final Audit PASS binds a concrete evidence snapshot and the Server rechecks that snapshot after verifier response and before terminal SUCCESS.

Validation:
- focused freshness/planner tests: 74 OK;
- expanded verification regression: 95 OK;
- focused identity/freshness/storage tests: 46 OK;
- full unittest: 320 OK;
- explicit KT-2 regression matrix (stage evidence + task planner + final audit): 150 OK;
- py_compile PASS; UltraApp construction smoke PASS; git diff --check PASS.

Live proof:
- B1 20261001_154859_053216 — SUCCESS/PASS, 42,528 tokens, write_file -> read_file -> verify_file_content;
- B2 20261001_154927_e54fa7 — SUCCESS/PASS, 61,092 tokens, find_text -> replace_text -> python_compile -> verify_file_content -> ui_smoke_test;
- B3 20261001_155015_f999db — SUCCESS/PASS, 37,485 tokens, read_file -> read_file only;
- all three emitted final_audit_evidence_snapshot_bound.

Negative matrix:
old plan version, repair generation, target/dependency drift, state change during Final Audit, missing source record, wrong exact evidence, unresolved requirements, external stage-start drift, permissions/scope and truncated/incomplete evidence are fail-closed in regression. No known false PASS in the checked KT-2 matrix.

NEXT:
TASK 151C — Compact Final Audit Packet + Task-scoped Git Evidence / KT-3.
Do not start from this file alone: route 08 -> 000 -> 18 -> 01 -> 20/21 and define a fresh TASK151C scope/documentation block.

Post-close cleanup:
- ordinary TASK151B rollback/safety `.bak` files were removed after independent closure verification;
- temporary `TASK151B_BENCH/run_live_matrix.py` was removed;
- retained intentionally: `TASK151B_BENCH/` live evidence and permanent `ALARM_TASK_SESSION/TASK_151B/` continuity;
- no Git commit/push/pull/reset/clean/checkout/switch/config without explicit user instruction.
