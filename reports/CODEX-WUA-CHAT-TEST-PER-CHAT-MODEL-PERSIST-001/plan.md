# TEST per-chat model persistence — REUSE CHECK / 2026-11-15

Scope: the accepted permanent TEST Ordinary Core profile, existing metadata writer and shipped UI. No STANDARD implementation, provider transport, REAL admission, launcher/profile or production storage changes. Legacy Stage5 rollback keeps its existing capability contract. Existing TEST data receives a model field only upon explicit model selection; reads do not migrate or rewrite records.

Base: 16/16 H35 source fingerprints match the local accepted package, including LF/CRLF variants. B1 names published main@cd0e4d943bb8d341baf07eef2a1d5c2a1619035a. No Git/HEAD read was performed; source-content comparison is the available local base check. Active B1 exactly matches this task. Backup with SHA-256 precedes all edits and remains outside the project until independent acceptance.

RED first: run the shipped browser code against a persistent synthetic model-store oracle; choose Lightning in A and Ultra in B, switch A/B and recreate the page (F5). Run the actual TEST HTTP /model request before adding its route. Preserve commands/logs/counts and original failures.

Fix: reuse the existing Chat metadata.json and identity/writer/_replace_verified contract. Store a separate TEST-only model field; validate against the same enabled remote GigaChat registry selection as TEST capability. Expose capability-gated GET/POST /model only on exact OrdinaryCoreChatService. STANDARD already owns its independent route/method/metadata and must behave identically.

UI: new TEST capability activates per-chat read/write. Keep selected model unavailable while loading or saving; failed/unknown reads show an explicit warning and never silently pick another model. A missing field permits the initial default. Epoch/revision checks discard late responses. A pending Turn retains original model/text/key even if the next-message preference changes.

Validation: focused RED→GREEN, durable HTTP metadata reopen, two chats/two workspaces/new disposable base, unknown/corrupt model repair, storage/token/scope failures, concurrent/late browser responses, send/replay and RAW/usage preservation. Run existing shipped UI, relevant TEST/Core/Turn/RAW/usage/launcher/STD HOLD regression and S2 exact gate pin reconciliation if its reviewed module changes. No external network, OAuth or credential reads. Actual owner GUI/F5 and independent Windows CI remain pending.

FOLLOWUP (not implemented): ordinary chat opening without requiring Workspace. Finish only after final report/evidence/manifest; history ID assigned by official script.
