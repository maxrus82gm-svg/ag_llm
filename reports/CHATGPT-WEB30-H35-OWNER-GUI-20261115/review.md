# H35 — owner's physical STANDARD GUI check (bounded)

**Date:** 2026-11-15; user-reported in interactive WEB30 conversation.  
**TASK ID:** `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001`; **HISTORY ID:** `H-CODEX-000035`.  
**Previous independent Windows review:** `reports/CHATGPT-WEB29-H35-REVIEW-20261114/review.md`, [run 43598906253](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598906253) success 3/3 jobs.

## Observed by owner (not independently remote-observed)

- Opened штатный `Start_WebAlarm_Standard.cmd`. Existing chats and their histories remained present.
- Changed a context limit in one chat to 100000, explicitly pressed **Save**, switched between chats, confirmed each chat retained its own settings without modifying the other.
- Reloaded with **F5** after saving: modified chat settings, including the threshold, persisted. User explicitly confirmed second chat remained unaffected.
- STANDARD displayed a single `GigaChat 2 Pro` selection, which matches the intentionally bounded H35 one-model implementation. Different-model switching, GigaChat 3 Pro onboarding and live model identity were **not** tested.
- Owner discussed potential autosave vs explicit Save; **NO UX CHANGE REQUEST** or new task assigned. Present Save behavior remains unchanged.

**USER UX / REAL APPLICATION (STANDARD local UI): BOUNDED ACCEPTED** for chat history, per-chat settings isolation and persisted F5 behavior, via owner testimony. No recorded screenshot/log or independent physical access.

## Not covered

No REAL GigaChat send, OAuth/API/payment/provider contract/usage telemetry, alternative model, all-route S3b/S3c/S9/S13a, historical pinned S1 RAW, broader accessibility/browser matrix, clean deployment or long-path global CI. H35 author's overall PARTIAL/REAL factory BLOCKED remains; release/paid/live still HOLD. See `FOLLOWUP-WUA-H35-OWNER-STANDARD-UX-001` for narrower remaining GUI matrix and `FOLLOWUP-WUA-H35-GLOBAL-CI-CHECKOUT-LONGPATH-001` for independent infrastructure gap. This owner check is not a new technical CI run and not a claim of full H35 readiness.
