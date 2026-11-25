# WORKSPACE-ISOLATION-01 — WUA local relocation and policy

**Date:** 24.11.2026 (HOME +05:00). **TASK:** CHATGPT-WUA-WORKSPACE-ISOLATION-20261124-001. **Execution outcome:** LOCAL MIGRATION PASS (bounded author verification); DOCUMENTED / independent review NOT RUN. **Git:** local main b31a4a036e808d99b3d75c69b57ea115107dfe79 unchanged; GitHub GPT base #672 d8c789a1332e7d46f44e049b762600be3dec8699. Main has owner-side merge and unrelated AI_Info.pur / support document changes; those files are outside this task. **LOCAL-PLAN-01:** helper read before task and again before mutation; latter SHA256 e104b9d12d5775374e556d38ad9addb8335ab080b92660a60cde83b206a6f30f at 23:52 +05:00; no effect on WUA-COLIBRI-BRIDGE-001 stages; no edit to #34.1 or #34.1.1.

## Local placement and historical evidence resolver

All listed former direct children of M:\GitHub were relocated to the existing WUA project; no unrelated project touched. Resolve old historical WUA gate vault names by their **unchanged basename** under M:\GitHub\ag_llm\reports\_local\; resolve old backup/card names under M:\GitHub\ag_llm\Backups\. This mapping applies to earlier report paths; do not rewrite historical reports or hashes.

| Former direct child of M:\GitHub | New project-relative address | Files with SHA256/size verified |
| --- | --- | ---: |
| WUA-659-gate-evidence-20261122 | reports/_local/WUA-659-gate-evidence-20261122 | 4 |
| WUA-662-gate-evidence-20261123 | reports/_local/WUA-662-gate-evidence-20261123 | 10 |
| WUA-663-gate-evidence-20261123 | reports/_local/WUA-663-gate-evidence-20261123 | 11 |
| WUA-664-gate-evidence-20261123 | reports/_local/WUA-664-gate-evidence-20261123 | 12 |
| WUA-665-gate-evidence-20261123 | reports/_local/WUA-665-gate-evidence-20261123 | 3 |
| WUA-666-gate-evidence-20261123 | reports/_local/WUA-666-gate-evidence-20261123 | 25 |
| WUA-local-only-migration-20261122-171607 | Backups/WUA-local-only-migration-20261122-171607 | 30 |
| WUA-premerge-backup-20261122-171234 | Backups/WUA-premerge-backup-20261122-171234 | 1 |
| WUA-premerge-backup-20261122-171257-verified | Backups/WUA-premerge-backup-20261122-171257-verified | 28 |
| ag_llm_local_backup_20261122_170216 | Backups/ag_llm_local_backup_20261122_170216 | 3 |
| _ag_llm_claude_card_before_PR35_20261029_225056.md | Backups/_ag_llm_claude_card_before_PR35_20261029_225056.md | 1 |
| _ag_llm_claude_card_PR35_main_before_B1_restore_20261029.md | Backups/_ag_llm_claude_card_PR35_main_before_B1_restore_20261029.md | 1 |

**129 files, 12,914,753 bytes**: exact before/after manifests of SHA256, sizes, relative names and directories matched, same-volume rename, no files deleted. Raw per-file local evidence: Backups/WORKSPACE-ISOLATION-01-20261124/migration-manifest.json, SHA256 760bfd90f24fda28778a3521ffb6a5e522974599ac8c238087db59fae1a5884b. Local original .git/info/exclude bytes retained in that backup directory.

## Linked worktree and launcher

ag_llm_UI_TEST_651 was a registered detached Git worktree, not a standalone repository. Actual HEAD #670 88728ed3d1a249351626c13c8f4627d791fc1698; no tracked/untracked non-ignored status changes; .venv is a junction to main project .venv, common Git directory ag_llm/.git. No matching active process command lines or desktop/Start menu/taskbar shortcut references found in bounded inspection; not a claim about every external caller.

Used git worktree move (rc=0), **not** copy/delete. New paths:
- _ultra_agent_test/ag_llm_UI_TEST_651
- _ultra_agent_test/Start_WebAlarm_UI_TEST_651.cmd

Before and after relocation: actual shared Python interpreter loaded launch_test_config.json; offline admission ordinary-core-offline accepted; guarded isolated fixture with --no-browser, ephemeral localhost HTTP GET / returned 200; real_available=false; child stopped normally and its temporary storage removed. Git worktree registration, detached HEAD, clean Git status and .venv junction verified again. New launcher uses relative paths from %~dp0 to the same test worktree and main .venv, retains --require-test; original launcher bytes preserved at Backups/WORKSPACE-ISOLATION-01-20261124/Start_WebAlarm_UI_TEST_651.cmd.original (SHA256 4b25a5c99a66817dc7a59cd9a041b4dc3f85c1f549ecb236bade99c9352070c8). New launcher SHA256 c87b66a8e5795a4b75a4946137a9844f3cc39d9b09039a24b16e07e10d6b462f. Old absolute launcher path no longer exists; use the relocated path. The actual interactive CMD/Chrome launch was NOT RUN; scoped functional fixture/admission only, not byte-by-byte worktree SHA256 inventory.

## Protection / scope / outcome

Local .git/info/exclude protection installed before moving: /Backups/ and /reports/_local/; existing _ultra_agent_test/ ignore reused. git ls-files confirmed no tracked items in these three destinations; git check-ignore passed. The tracked .gitignore and mandatory documents #08/#000/#18 are to carry the permanent rule. Raw manifest, worktree, secrets, backups, local #34.1 and archive are not published. No force-add, reset, clean, unrelated worktree deletion, model/API calls or STANDARD/Manager restarts. Local main HEAD and full normal porcelain status identical before/after (clean). All 14 named root objects absent at completion; no claim that other users' unrelated directories were removed. Existing external Codex and system-TEMP worktrees are outside this authorised migration and must not be moved/deleted without owner review. No new GitHub CI; independent verification and interactive GUI NOT RUN. The M1-10 LIVE gate, Colibri coordination and other open product gates are unchanged.

**NEXT:** owner accepts GPT -> main; use new local launcher path; all future local agent scratch/results follow WORKSPACE-ISOLATION-01. Historical reports remain immutable. 
