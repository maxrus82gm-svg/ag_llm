# TASK WA-3.1 — Canonical Remote entry

STATUS: DONE / VERIFIED

BIG TASK: WA-3 — Remote workflow, recovery and replay protection — IN PROGRESS.

RESULT: `web_alarm/remote_entry.py` plus CLI `webalarm enter [--task-id]` / `webalarm status --active` provide a fail-closed read-only entry. Exactly one active TASK may auto-resolve; zero/multiple require explicit --task-id; completed TASK is rejected; recovery statuses produce RECOVERY_REVIEW_REQUIRED / RECONCILE_BEFORE_MUTATION.

REAL RECOVERY PROOF: a real transport/chat reset occurred after the WA-3.1 restore point but before implementation. Reconciliation proved source/snapshot hashes intact, new implementation files absent, and 000 not yet activated. No blind replay occurred; work resumed from activation.

VERIFICATION: final full WA regression = 82/82 PASS; Remote-entry/CLI/documentation git diff --check PASS.

DOCUMENTATION: 000/01/04/05/06/23/24/25 synchronized.

NEXT: WA-3.2 — Operation ID / replay identity.
