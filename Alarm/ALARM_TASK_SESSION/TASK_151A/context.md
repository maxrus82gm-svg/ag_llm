# TASK 151A — remote context

STATUS: DONE.
CONTROL POINT: KT-1 ACCOUNTING = DONE.

Confirmed:
- provider/context/usage accounting implemented for Planner, Executor, Dredd/Planner Review, AUDIT_DIAGNOSTIC and Compressor;
- UNKNOWN provider usage remains UNKNOWN, never coerced to zero;
- B1-clean: 5/5 positive, median 36,060 tokens, range 31,229–36,875;
- B1-dirty: 5/5 positive, median 30,647, range 25,158–41,175;
- B2-bounded: 5/5 positive, median 46,284, range 43,694–60,044;
- B3 exact analytical: 5/5 positive, median 33,019, range 31,596–38,668;
- offline inventory: 24 isolated RUN, provider started/terminal identity and context accounting valid;
- retained negatives/outliers include B1 HTTP 429 with UNKNOWN usage, B2 blocked pilot, R-027 1,736,351-token stress baseline and T-030 false-PASS + repair.

Physical paths:
- B1 clean/dirty: write_file -> read_file -> verify_file_content;
- B2 bounded: find_text -> replace_text -> python_compile -> verify_file_content -> ui_smoke_test;
- B3 exact: read_file -> read_file only, no user-file mutation.

Validation baseline for 151A repair remains full unittest 314/314 PASS, UltraApp construction smoke PASS and git diff --check PASS.
Statistical repeat phase changed no runtime semantics.

NEXT:
TASK 151B — Evidence Freshness / plan-state revision binding / KT-2.
Do not start it from this file alone: first route through 08 -> 000 -> 18 -> 01 -> 20/21, define fresh scope/profile and fill 000 block 1.

Post-close cleanup:
- ordinary TASK151A root safety/rollback `.bak` files were removed after independent closure verification;
- retained intentionally: `TASK151A__R030_false_pass_artifact.md.bak`, `TASK151A__R026_before_recovery/`, `TASK151A_BENCH/` and permanent `ALARM_TASK_SESSION/` continuity;
- no Git commit/push/pull/reset/clean/checkout/switch/config without explicit user instruction.
