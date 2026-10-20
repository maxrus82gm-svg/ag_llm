# Diagnostic CI only — AUD-01T-R transport tail recovery

🟨 Независимая проверка восстановления повреждённого транспортного журнала на Windows.

- **DO NOT MERGE** this PR or diagnostic Markdown marker.
- Base/source revision pinned: `main@9fc0d2fca4b9982d1086b50bba8e3f8ecdc4e698`.
- Published Claude package `CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001` already present at that source revision.
- This branch contains one marker file change solely to trigger existing `web-alarm-tests.yml` on `pull_request`.
- Code, tests, workflows, live storage and `main` are unchanged in the diagnostic branch.
- Check 909 method census (including expected skips), focused and full failure/ERROR counts, isolation guard F-T1, source SHA, old reds, negative controls, archive proof.
- Green CI does not authorize production recovery or rollout.
