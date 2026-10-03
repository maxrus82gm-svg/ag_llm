# DOC-WA-REMOTE-OBS-001 — Remote transport/recovery evidence journal

STATUS: DONE / VERIFIED

RESULT: created `Документация/26_Журнал наблюдений Remote - обрывы, transport и recovery evidence.md` and linked it in Obsidian only from document 23.

EVIDENCE CAPTURED: real project incidents, Desktop Commander 0.2.52 process/runtime snapshot, local remote-channel transport source analysis, incident packet and proposed compact telemetry fields.

KEY TECHNICAL FACT: current Remote process chain stayed alive across the observed window; installed transport uses durable `mcp_remote_calls` plus Realtime doorbell, conditional pending→executing claim, reconnect pending recovery, half-open WebSocket self-heal and a separate terminal result write. Therefore a lost caller response cannot prove that a side effect did not occur.

VERIFICATION: document 26 read from disk; exact Wiki Link search found one match only in document 23; documentation `git diff --check` PASS. No Web Alarm runtime code changed.

NEXT: WA-3.3.1 — Reconciliation Evidence / read-only inspector.
