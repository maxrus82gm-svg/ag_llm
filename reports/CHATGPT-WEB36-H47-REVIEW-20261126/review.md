# WEB36 / H-CODEX-000047 — независимая приёмка OFFLINE

26.11.2026 (+05:00), TASK CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001. Source #683 `47191f3c26b64a66f8f0749abea6a0db9f9ccefd`; tested merge `0e7adfb692c65a6d329e1d8e17fb65b05f6b4f16` (main=GPT при проверке). Other #683 `ae64a307ac564f39bfe19b19e1dc2a05c252f43e` — IDE docs; оба сохранены без renumber/rewrite.

**H47 PASS / BOUNDED INDEPENDENT WINDOWS OFFLINE; DOC CLOSED только для исправлений CI.** H46 scoped CI PASS / PARTIAL, H27 integrated CI observed PASS / собственная независимая приёмка NOT VERIFIED. M1-10/M1-11 HOLD/NOT RUN; M1-09 packaging PARTIAL, M1-12 joint OPEN. Не release/REAL acceptance.

## Целостность пакета

Все шесть файлов авторского манифеста проверены на точном SHA. handoff_task.md, report.md, task_record.json до review и tests.md побайтово совпадают. evidence.json и finish.json: разница 398 и 137 байт из-за CRLF→LF в Git; обратная нормализация дала точные исходные размеры и SHA-256. [Integrity](integrity.json). Исходный манифест и доказательства не перезаписываются. H47 finish ROTATED / H-CODEX-000047, БЛОК 1 WAITING; 1.1 сохранён. Прежний record сохранён в previous и immutable Git. Авторские S1 FULL 69 и оба isolated CMD — только авторские свидетельства.

## Независимые доказательства

- [Windows run 45804549718](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/45804549718), attempt 1, job 139856212527: COMPLETED SUCCESS, все steps SUCCESS. Logs: S1 STATIC16 OK, violations 0; S2 FULL73, failures/errors/skips/isolation violations 0; D8 1 OK, negative controls 5 OK, HTTP/ordinary 36 OK, Bridge/binding/launcher 39 OK (17.844 s), JS 211 PASS / 0 fail/cancel/skip, MCP_SERVER_IMPORT_PASS.
- test_windows_fixture_owner_and_protected_dacl_match_process_user ... ok; test_windows_foreign_owner_is_refused_with_an_otherwise_private_dacl ... ok; test_l2_missing_file_is_standard_and_every_shipped_profile_is_valid_and_non_standard ... ok.
- Prior 45702959182 attempt 2 job 139714802863 #681: 28 PASS, 4 FAIL, 5 ERROR (unsafe_discovery/related assertions and missing demo script), JS NOT RUN. New 39/39 + JS211. Original runner owner SID not directly observed.
- [Smoke 45804549500](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/45804549500) same SHA: WA-017 139856212883, WA4-E 139856213286, WA4-R DIAG 139856213410, WA4-A direct-close 139856213610 success. WA4-A focused+full 139856215688 skipped = NOT RUN. Earlier STANDARD bounded OFFLINE 45702959210 PASS only #681.
- NOT RUN independently: FULL S1 pinned private RAW 69 on new SHA, physical CMD/GUI, clean installation/package, actual Client/Manager/model, LIVE/paid/OAuth. No runtime tests added in docs-only commit.

## Инженерный review

H47 source diff — fixture and workflow only; no production transport/binding/launcher/CMD/fingerprint changes. TokenUser explicitly owner and private DACL grantee; OWNER_SECURITY_INFORMATION and PROTECTED_DACL_SECURITY_INFORMATION; protect parent before creating token. Everyone negative retained; foreign-owner oracle substitutes only owner in native descriptor with real DACL (author account could not assign actual foreign owner). Sparse checkout includes exact directory reports/CLAUDE-WUA-CHAT-S1-READONLY-UI-001/tools with demo_ultra_chat.py. No weakened production checks. READ_ONLY only GET health/models, identity/loopback, no redirect/proxy; clears allowed_operations and enabled_local_targets empty. Name-based TOCTOU residual remains for real-profile preflight. No new local Turn enabled in real STANDARD; OFFLINE transport TEMP-only, never reuse to bypass.

## NEXT / coordination

LOCAL-PLAN-01 fresh locked read HOME 26.11.2026 WEB36 SHA256 b215ef9882542d5e38590965b8635b8c8039320eaf87f7626f9c7137c97831ee; WUA MVP1 IN_PROGRESS, Colibri SUBMITTED, M1-10 HOLD. Owner reports parallel Client/Manager sync, work-PC tunnel/background setup; installed build/ACL/identity/idle evidence pending. Start with one stable HOME target; whole approved Client catalogue scope. [Scenario](live_preflight.md), [settings audit](settings_audit.md), [human instruction](../../WEB_ALARM_START.md). M1-10 requires new scoped OWNER GO; M1-11 separate engineering and GO. No new task/HISTORY ID or automatic assignment. Native task_history.py review/render/validate NOT RUN in GitHub-only operation; targeted record/index updates, previous history retained. No real calls, process/model changes or paid calls. No shared stage change.
