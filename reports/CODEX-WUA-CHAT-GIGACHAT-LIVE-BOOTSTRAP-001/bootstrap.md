# Operator bootstrap — current state: PROBE GO pending

The normal `Start_WebAlarm_Standard.cmd` remains HOLD and `Start_WebAlarm_Test.cmd` remains OFFLINE. No permanent REAL switch exists. The one-shot operator invokes `web_alarm.live_bootstrap.catalog_probe` or, after a *second* GO, `serve_one_inference` in trusted server-side Python. Both take a `LiveApproval` object constructed there; no browser request, JSON payload, command-line flag, or environment flag creates that object. Credentials are read by H38 directly from the existing Windows user environment, inside `ProviderSession`, after approval.

Prepared fresh Workspace (no historical data): `%LOCALAPPDATA%/WebAlarmWorkspace/live_bootstrap/probe_83e64481d2dd49fb8bcabea3a4206707`. Web Alarm registration `ws_49c3d0f2e269471ab181bddf4db3c329`; Ultra identity `ws_e6c65b696ee348ca83eda85e4f9606f6`; empty chat `chat_09c134a891a148ffa44b7963208120fa`. Existing `BudgetLedger.initialize()` enrolled it explicitly; readback had 0 events. Existing workspaces and histories were not migrated or changed.

## Stage A — catalog only, after exact GO

1. Reconfirm the registration, Ultra identity, empty fresh chat and ledger using `_verified_workspace`; stop on mismatch. Ensure no other process is using this GigaChat account for the bounded session.
2. Construct a new server-side `LiveApproval`: unique 16–80 character grant ID; `user_go` and `independent_review` provenance; account label for this Windows user GigaChat account; scope `GIGACHAT_API_PERS`; expiry at most 10 minutes; `contracts=()`; `max_oauth=1`, `max_catalog=1`, `max_inference=0`, `max_liability_tokens=1`. Call `catalog_probe(WebAlarmApi(), wa_workspace_id, approval)` exactly once. It invokes H38 `ProviderSession.discover_models()` and closes the grant in `finally`.
3. Record only response model identifiers, status, call counts and sanitized diagnostics. Never record token, credentials, raw headers or provider body. No retries even if the call fails. An uncertain or failed probe requires a new exact decision, never replaying the same grant.

## Stage B — first reply, separate GO after probe/caps/tariff review

Construct a **new** `LiveApproval` with exactly one verified `ModelContract` for a catalog-confirmed text model and its exact accepted response versions, evidence-backed context/output caps, bounded token liability, `max_answer_tokens<=32`, one OAuth, one catalog and one inference call, and expiry no longer than 15 minutes. `serve_one_inference(WebAlarmApi(), wa_workspace_id, approval)` binds the existing Web Alarm loopback server **before** consuming control calls, performs one explicit catalog lookup and then serves. Open the single prepared chat, select the approved model and send `Ответь одним словом: готово` once. F5/reopen are reads, not resends. The approval's expiry shuts the server down; `finally` closes the session. If an attempt is uncertain or active at shutdown, the durable marker stays fail-closed for review.

Before Stage B, separately establish observed model availability/version, exact model caps, tariff/financial bound, and approval of this physical POST. Do not infer caps or price from a registry record or the probe alone. Current task has **no Stage A or B GO**.
