# TASK WA-1.4 — Manifest and Snapshot

STATUS: DONE / VERIFIED

BIG TASK: WA-1 — Fund state and file core — IN PROGRESS.

RESULT: per-microtask Manifest/Snapshot restore points implemented. Existing files get byte snapshots + size/SHA256/captured_at; new targets use exists_before=false. Snapshot/source reread verification is required before publication. Explicit restore restores existing bytes and removes files absent before the microtask. Corruption/path tampering fails closed; restore validation/mutation failures set RECOVERY_REQUIRED.

VERIFICATION: final 2026-10-02 run = 36/36 PASS; morning post-disconnect recheck = 36/36 PASS; targeted git diff --check PASS.

RECOVERY NOTE: during post-test hardening a missing `_safe_component` caused 6 focused test errors. Verification credit was not granted; disk state was reconciled, the helper repaired, and the full suite rerun green. Overnight disconnect occurred during documentation closeout only. On reconnect, docs 01/04/05/06/23/24/25 were already updated; only 000 Block 2/mini-registry and this context/history were stale and were repaired without blind replay.

DOCUMENTATION: 000/01/04/05/06/23/24/25 synchronized.

NEXT: WA-1.5 — Event Log and Checkpoint.

NEXT SAFE ACTION: start WA-1.5 as a fresh task-session with its own declared scope and verified restore point; do not replay any WA-1.4 mutation intent.
