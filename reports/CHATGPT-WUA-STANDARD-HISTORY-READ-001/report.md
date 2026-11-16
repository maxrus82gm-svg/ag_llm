# CHATGPT-WUA-STANDARD-HISTORY-READ-001 — STANDARD legacy history HTTP 503

**TASK ID:** CHATGPT-WUA-STANDARD-HISTORY-READ-001  
**Date:** 2026-11-16  
**Status at authoring:** AUTHOR FIX PREPARED; GitHub Windows independent CI PENDING; owner physical GUI/F5 NOT RUN. Not a release acceptance.

## Owner symptom and read-only reproduction

After #628 personal chats can be created without Workspace/LIVE and survive F5. Previously working legacy Workspace chats show "Загружаем историю…" followed by a generic Ultra Chat fetch error. STANDARD still answers GET / with HTTP 200; its read capability and workspace/chat lists work. Bounded read-only requests for messages returned HTTP 503 error code `offline_history_invalid` for all 11 observed `ag_llm` chats and one of three observed `1234` chats; other tested Workspace histories returned 200. This is a server refusal, not evidence of lost RAW and not a validated integrity sweep.

## REUSE CHECK / root cause

`OrdinaryApplicationChatService` inherits from `OrdinaryCoreChatService` → `OfflineUltraChatService`. Its `messages()` invokes `super().messages()`; Stage5 then asserts an exact synthetic `TEST_OFFLINE` Turn for assistant RAW. Historical Tk/Ultra messages do not carry that provenance. This maps to HTTP 503 `offline_history_invalid`.

Production STANDARD should use `UltraChatService.messages()`: the existing bounded Ultra Core reader validates workspace registration/identity, ownership, file sizes, damaged records, pagination, run outcomes and no-follow rules. No new storage format, copied history or migration.

## Scope of patch

- With no synthetic fixture: call `UltraChatService.messages(self, ...)`, then project usage through existing `chat_usage`. If old usage/Turn indexes are missing or unreadable, report usage unavailable, **not** whole history unavailable.
- With synthetic fixture: preserve inherited strict Stage5 TEST provenance checks and existing synthetic accounting.
- Preserve `ordinary_real_hold`, provider admission, model selection, read/write tokens and existing TEST flow. Do not change GigaChat credentials or call provider.
- No changes to `Start_WebAlarm_Standard.cmd`, `Start_WebAlarm_Test.cmd`, Tk, Workspace registrations, existing RAW, or permanent local storage.

## Regression and acceptance

New `test_web_alarm_ordinary_application.py` integration tests using disposable TEMP: normal STANDARD GET of untagged legacy user/assistant/failure messages returns 200 with correct outcomes and unchanged RAW; reopened HTTP server returns identical history; STANDARD send remains 403 HOLD; strict Stage5 TEST service still refuses the same unverified data; damaged legacy record is reported as partial rather than wiping readable history.

GitHub workflow `.github/workflows/wua-standard-live-offline.yml` runs automatically on GPT `web_alarm/**` changes: Windows Python 3.12 `test_web_alarm_standard_live`, `test_web_alarm_live_bootstrap`, `test_web_alarm_gigachat_multimodel`, `test_web_alarm_ordinary_application` and Node UI tests, isolated checkout and no real credentials, with log artifact. **Results must be read back from the exact run before PASS is claimed.** Broad legacy Tk physical data cannot be uploaded to GitHub; full old-history acceptance is owner Chromium smoke after merge, not simulated RAW proof.

**Follow-up:** `FOLLOWUP-WUA-STANDARD-LEGACY-HISTORY-001` OPEN until CI and owner physical confirmation. GigaChat REAL remains separate HOLD.
