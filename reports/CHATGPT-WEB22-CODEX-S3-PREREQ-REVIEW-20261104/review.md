# WEB22 — independent bounded diagnostic review for CODEX-WUA-CHAT-S3-TURN-RECOVERY-001

**Date 2026-11-04. Technical package published main@5088d307defdf3b6b92d4f119c45fc29863a6bb5.**
**Verdict:** PASS / BOUNDED SOURCE + AUTHOR EVIDENCE for two diagnostic prerequisites and correct implementation STOP. **Stage3 product:** PARTIAL / BLOCKED / NOT IMPLEMENTED. Independent real Windows/Node/Python/CI runtime NOT RUN.

## Source and evidence
Codex assigned Stage3 №37; report reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/report.md, manifest.json, test_web_alarm_ultra_chat_turn.py, risk_test_matrix.md and DESIGN ONLY turn_contract.md. GitHub compare of user task base e6715314cc5fc980b0a2b704685c5275f4edf8b5 to technical publication 1dc6e12e08f81d683abfdb8121afce4be40dbcef shows only added negative test and report/evidence for task, no product modules changed (also unrelated user .obsidian changes). Published run_store.py equals its saved before snapshot, as do core/adapter/server/UI and rotation script. The proposed_run_store_NOT_APPLIED.patch is a design proposal not a tested or applied fix.

## Finding A — audit junction
Source run_store.audit_root() constructs .ultra/audit, _atomic_json and create_run_summary use filesystem paths without verified no-follow on audit directory. The existing Workspace index lock does not protect directory containment. Published Windows negative test uses one synthetic Workspace and an owned TEMP outside directory with .ultra/audit junction. evidence/prerequisites_oracles_final/audit_path.json records refused=false, index.json and chat/run summary.json created outside workspace, original marker unchanged. Correct negative oracle fails. Actual source and author evidence support defect; verifier did not reproduce it independently on Windows.

## Finding B — same RUN writer sequences
Source append_run_record() calls _next_sequence then appends stream+index with no single OS writer lock covering this path. Published test orchestrates two real Python processes in same synthetic RUN; raw evidence/prerequisites_oracles_final/same_run_writers.json records two acknowledged sequence=1 and persisted records.idx.jsonl [1,1], two distinct byte offsets. Negative oracle expects unique monotonically increasing sequence or explicit bounded refusal, therefore fails. Prior P9 21 green tests did not cover this edge case.

## Tests / limitations
Author prerequisites 3 tests: normal RUN PASS, both intentional RED FAIL (exit1). Author JS 158 PASS; Python 171 collected =166 PASS+5 SKIP; pytest P9 21 PASS. Older harness errors stored and distinguished; final guard reports 0 provider contacts. 601 history file SHA matches per author-only verification; verifier did not reread physical Windows files. Verifier inspected current source, test, raw JSON and logs but independently executed no new runtime/CI checks. Run Store security beyond those exact source paths, TOCTOU, nested audit paths/handle checks and stream-index crash recovery remain OPEN.

Stage3 durable Turn, idempotency, mock provider, HTTP, cancel/UNKNOWN, UI TEST and restart are **NOT IMPLEMENTED / NOT RUN**. DESIGN ONLY turn_contract.md cannot be treated as implementation. Do not claim Stage3 acceptance, live-ready requests, protection of arbitrary external paths or absence of all data hazards.

## Mechanical slot and next
Initial Codex finish NO ROTATE / NO_TASK_ID exit3 occurred because original assistant TASK used heading '# TASK ID:' rather than strict script declaration. User changed only TASK ID declaration to canonical bold Markdown and used the GUI. Published reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/slot_finish_1793806731834391500.json: check OK, dry-run OK, apply ROTATED, readback OK, exit 0, exact 383-line copy SHA256 d9af4724783c93dc2bb0e028426fa614cd603e9e6f2c2e58296340475d0dad91. Independent GitHub card readback confirms B1 WAITING and B1.1 CODEX-WUA-CHAT-S3-TURN-RECOVERY-001; prior UX handoff snapshot remains at reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/handoff_task.md. No manual coordinator slot edits.

Open: FOLLOWUP-WUA-P9-AUDIT-PATH-001, FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001, FOLLOWUP-WUA-P9-INDEPENDENT-RUNTIME-001 and FOLLOWUP-WUA-S3-TURN-IMPLEMENTATION-001. New USER GO required for Run Store path+writer repair and adversarial Windows/restart/stream-index tests, then independent review, then a new Stage3 task. No Stage4, real Colibri/Ollama/GigaChat, Blueprint execution, paid/live or frozen Desktop MCP allowed. Documentation closeout only in GPT branch until user merges.
