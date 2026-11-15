# H36 — bounded independent OFFLINE acceptance and owner GUI verification

**Date:** 2026-11-15. **Verifier/recorder:** ChatGPT WEB30; independent Windows CI executed by WEB29.  
**TASK ID:** `CODEX-WUA-CHAT-TEST-PER-CHAT-MODEL-PERSIST-001`  
**HISTORY ID:** `H-CODEX-000036`  
**Product source:** `main@9dd93ba09408217781c9b8f423a9cecf5bd264aa` (author publication); original TEST-only fix in `web_alarm/ultra_chat.py`, `web_alarm/ui.py`.  
**Independent CI:** [GitHub Windows run 43635085454](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43635085454), `head_sha=ab05ee811a3cd12a59db054b40872acea6f89519`, conclusion `success`, 2/2 jobs. Prior CI setup failures #609–611 preserved as diagnostics, not product regressions.

## Evidence and conclusion

- Author package: `reports/CODEX-WUA-CHAT-TEST-PER-CHAT-MODEL-PERSIST-001/report.md`, manifest, `task_record.json`; original author checks 271 regression cases + 274 subtests, UI 69, new tests 9 + 8, S1 69, S2 73, quality 52 + 7 (per author).
- Independent Windows CI (WEB29): expected historical RED on uncorrected behavior, GREEN after fix; model HTTP/UI, Python regression, S2 and safety/quality gates completed, with no unexpected guard bypass. **TECHNICAL/CI: PASS, strictly bounded OFFLINE.**
- **OWNER GUI / 2026-11-15, owner-reported, not remotely observed by ChatGPT:** launched штатный `Start_WebAlarm_Test.cmd`, checked two chats using GigaChat Lightning and GigaChat Ultra, switched between them and refreshed with F5. Each chat kept its selected model; chat state/history remained separate; synthetic TEST message sent successfully. Owner explicitly reported everything saved correctly. **REAL APPLICATION (TEST) / USER UX: ACCEPTED in this scenario.**
- This is a follow-up to the 2026-11-14 pre-fix GUI failure. The author `closeout.json` and `report.md` retain original submission-time PENDING and must not be rewritten retroactively; this independent review supersedes their pending status within bounded scope.

## Explicit limits and remaining OPEN

No real GigaChat provider, OAuth, API, paid request, production send, STANDARD model switching, clean Windows deployment, full browser/a11y/viewport matrix, full S3b/S3c/S9/S13a or historical pinned S1 RAW was exercised by this owner test. Existing FOLLOWUP remain OPEN where applicable. Neither owner GUI confirmation nor CI grants REAL authority or release readiness. **REAL/RELEASE: HOLD.** No product source or TEST/STANDARD launcher changed by this documentation closeout.

**Verdict:** `H-CODEX-000036 DOC CLOSED / BOUNDED INDEPENDENT OFFLINE TECHNICAL PASS + OWNER TEST GUI ACCEPTED`. Next: record bounded H35 STANDARD GUI result separately; owner alone may merge `GPT` into `main`; no automatic provider/live task.
