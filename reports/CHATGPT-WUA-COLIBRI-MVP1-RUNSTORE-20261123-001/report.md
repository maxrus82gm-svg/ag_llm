# WUA #664 — Interrupted Run Store append and explicit operator preview

**Task:** CHATGPT-WUA-COLIBRI-MVP1-RUNSTORE-20261123-001. **Verdict:** scoped OFFLINE PASS; full Colibri MVP1 PARTIAL, LIVE NOT RUN.
Owner GO 23.11 after accepted #663 (d154a3f84baea281deb30dbcf841ffd7004b2fbb). PLAN_READ 2026-11-23T23:19:58+05:00 SHA256 e2839c2663b9b602fc8435e3109ea6428dc2420aab2c8df0515a8e7038b645f6, archive SHA256 1071b531a3985ecb08d474651f73cedaf5aeb73cec1108b19daf764848fb4102.
Only exact pinned Colibri #107/#108 with fake Manager, disposable HTTP Bridge and Windows child workers.
No real HOME Manager, STANDARD, paid API, or MVP2 touched.

## Implementation

- Run Store recovery now offers a read-only dry_run=True branch using the same append-intent and SHA256 integrity checks. It never clears pending files, rewrites index data, or truncates stream bytes. Existing default recovery behaviour remains unchanged.
- TurnService has an internal-only inspect_orphaned_colibri operator preview. It checks the recorded OS lease, excludes still-running owners, verifies durable journal data, and returns WAIT_ORIGINAL_OWNER, PENDING_APPEND_REVIEW (KEEP_COMMITTED or ROLLBACK_UNINDEXED), RECONCILE_DURABLE_TERMINAL, SEAL_UNKNOWN, MANUAL_HOLD or ALREADY_TERMINAL. No GUI/API route is added. Every preview states that remote stop is unproven.
- Explicit reconcile_orphaned_colibri now refuses a pending append without a second opt-in approve_pending_repair=True. Verified committed entries are preserved; unindexed bytes may be rolled back after explicit approval; malformed append-intent and unexplained stream tails remain unmodified manual HOLD. Nothing reissues an inference, guesses a remote cancellation, or changes RAW without durable proof.

## Actual Windows child-process hard-kill tests

Six new tests PASS. A child exits after writing the terminal record into server.jsonl but before the index: dry-run preview preserves exact file hashes and an explicitly approved recovery rolls back unindexed bytes then seals UNKNOWN without assistant RAW or a second fake Manager call. A child exits after the index is durable but before pending cleanup: explicitly approved recovery retains the proven terminal and commits the original successful assistant RAW once. A partial index prefix is handled as uncommitted data only with approval. Altered append SHA and a missing intent with unexplained tail both return MANUAL_HOLD, preserve all bytes, and refuse repair even if requested. A still-running child is identified as the original owner, not an orphan.

## Regression

- New interrupted-append tests: 6/6 PASS.
- Previous WUA owner crash: 3/3 PASS; Windows ACL preflight: 3/3 PASS.
- Shared Turn: 13/13 PASS; two fake Manager SSE: 4/4 PASS; ordinary HTTP/EVM: 2/2 PASS.
- Legacy Run Store v2 (pytest): 51/51 PASS; TurnService: 19/19 PASS.
- Focused Python: 70/70 PASS; JavaScript UI: 207/207 PASS; real headless Chrome dual Manager/same chat: PASS.

Initial test-harness counter assumption was corrected by separating tests. Run Store tests use pytest: one wrong unittest runner reported zero tests; rerun using pytest returned 51 PASS. All resulting raw logs retained outside Git at WUA-664-gate-evidence-20261123, SHA256 sizes recorded in regression.json. Hosted CI and broad historical S1/S2/D8 gates NOT RUN.

## HOLD / NEXT

A crashed WUA does not prove remote Colibri stopped. No automatic reexecution or implicit corruption deletion, no authenticated operator UI, no production enablement. Actual HOME Windows protected handles/ACL/launch, remote process cancellation/status, complete joint MVP1 M1-00..12, Windows CI, native browser SSE and support for actual system/tool roles remain OPEN. Colibri Ultra 14 owns setup of the real additional Manager independently; no direct WUA interaction performed. MVP2 concurrent real Manager requests remain PLANNED. Next: full joint MVP1 acceptance assessment, further negative security/recovery/long-stream checks and agreement on an explicit authenticated operator approval workflow. Separate OWNER GO before any read-only real HOME preflight; separate later GO for actual inference or paid calls.

PLAN_READ 2026-11-23T23:19:58+05:00 SHA256 e2839c2663b9b602fc8435e3109ea6428dc2420aab2c8df0515a8e7038b645f6. H-CHATGPT-000018, #664 for owner GPT to main merge.
