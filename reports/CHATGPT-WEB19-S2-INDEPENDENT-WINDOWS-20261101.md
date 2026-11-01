# WEB19 — independently executed Windows tests for Stage2 replace hardening №479

**Review:** 2026-11-01, ChatGPT / WEB19. **TASK:** `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001`. **Pinned source:** `main@508cba49c8f21b0e8a9c451b84f1c0f1a8fb6a19`; main/GPT HEAD №480 `e288fe308d87a5a30ddaa2b19acdf3b49ee54ed2` at test-start. **Outcome:** **INDEPENDENT FOCUSED WINDOWS PASS**, not full regression, CI, Stage3 or product verification.

## Source and setup

GitHub files `context_storage.py` and `test_ultra_chat_storage.py` were independently fetched from №479 into isolated `%TEMP%\WEB19_S2_REVIEW_e288fe3` on an authorized Windows computer, **not** into the live project. Raw local SHA-256 checked against Claude's manifest:
- `context_storage.py`: **97846 bytes**, `7e3881647d63f8119424bb67081c9b163194fdf9a395a63d7499c44104de1280`
- `test_ultra_chat_storage.py`: **96913 bytes**, `d1b8733f00f8d33cd36552b1ee16aaf3aeb879b971c22559fe94c66b5c780cc2`

Both matched exactly. Python 3.13.8 AST parse succeeded (`AST_COMPILE_OK`). No source tracked files changed, Git commands, paid/live APIs, real Workspace, launcher switch or external network in these tests; test fixtures used disposable TEMP directories.

## New independent execution

| Selector in isolated scratch directory | Python | Raw outcome |
| --- | --- | --- |
| `python -B -m unittest -q test_ultra_chat_storage` | 3.13.8 / Windows | **68 run, 64 PASS, 4 SKIP, 0 FAIL/ERROR**, exit 0, 12.915 s |
| `python -B -m unittest -v test_ultra_chat_storage.ReplaceHardeningTests test_ultra_chat_storage.ReplaceConcurrencyTests` | 3.13.8 / Windows | **17 run, 16 PASS, 1 SKIP**, exit 0, 2.086 s |
| `py -3.12 -B -m unittest -q test_ultra_chat_storage` | 3.12.10 / Windows | **68 run, 64 PASS, 4 SKIP**, exit 0, 15.176 s |
| Reviewer-authored `py -3.12 -B web19_independent_probe.py` | 3.12.10 / Windows | **4/4 original assertions PASS**, exit 0 |

Reviewer independently authored a scratch-only probe (not copied from Claude test code) checking: (1) stale Chat `expected_title` cannot overwrite bytes; Workspace/Chat IDs preserved; (2) original Project Context history revision bytes unchanged after subsequent saves; (3) synthetic external file hardlinked to Project Context refuses with `unsafe_storage_link` and outside SHA-256 unchanged; (4) pre-existing Windows junction targeting synthetic outside history refuses with `unsafe_storage_link` and outside file list/bytes unchanged. Probe raw result: `{"status":"PASS","checks":["ids_and_stale_title_no_lost_update","exclusive_history_revision_unchanged","hardlink_outside_unchanged","history_junction_outside_unchanged"],"count":4}`, exit 0.

Focused suite symlink-creation case SKIP due to insufficient privilege. Three other module-level SKIPs were not exhaustively investigated; they must not be counted as PASS.

## Source review and limits

`rename_workspace` and `rename_chat` call `_replace_verified`; `save_project_context` uses `_read_project_context_for_write`, exclusive `_publish_project_context_revision`, and `_replace_verified`. Tests confirm selected path/atomicity/identity expectations on Windows. After-final-check same-user directory swap remains a TOCTOU risk; read-back detection is not prevention. `create_chat` staging metadata card remains on earlier `_atomic_write_json` path — `FOLLOWUP-WUA-S2-CHAT-STAGING-001` **OPEN/UNASSIGNED**.

**NOT RUN:** independently executed 1078-suite `all`, author 166-case multi-module focused gate, 9 mutation tests, GitHub Actions/CI, Tk readers P1–P6, clean-machine portability, Windows GUI, real Workspace, paid/live, post-final-check exploit races. Historical author first-run ERROR remains recorded in WEB18.

**Verdict:** Additional **INDEPENDENT FOCUSED WINDOWS PASS** on pinned №479 bytes. Original WEB18 bounded source+author-evidence PASS and DOC ITERATION CLOSED preserved, not retroactively changed to FULL PASS. Stage3 **HOLD**; Run Store P9 next priority; no new Claude TASK. Source: `reports/CHATGPT-WEB18-S2-HARDEN-REVIEW-20261101.md`.
