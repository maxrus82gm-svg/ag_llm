# LIVE evidence — Stage A PROBE PASS / inference NOT RUN

Exact USER GO in chat: `CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001 / STAGE A`, 15.11.2026. One execution of `run_stage_a_once.py`; its exclusive `evidence/stage_a_attempt.json` blocks a second run. Script SHA-256 before execution: `50ddecfe9494e73cdb76ed1b18640a18163f3063be598b078cd6fe3df3e9370e`.

Result: OAuth 200 and catalog 200 are inferred from H38's successful parsed return; grant `Probebc453ad3a14527813141f9ab268844ca` is `CLOSED`. H38 durable committed counters: OAuth **1**, catalog **1**, inference **0**. No retry path was invoked. The catalog returned ten safe IDs, including all six registered text models; exact IDs are in `models.md` and `evidence/stage_a_result.json`. The fresh Workspace ledger still has **0 events** after readback, so no inference reserve/SENT/terminal exists. No token, credential, authorization body or header was saved.

These counters and successful parsed results support one physical OAuth request and one physical catalog request; there was no packet-level capture. TLS verification remained enabled; both HTTPS calls succeeded. This is **PROBE PASS**, not a generated reply. STANDARD and TEST were unchanged.

**Stop point:** Stage A grant cannot be reused. Inference/completions remains **NOT AUTHORIZED / 0 calls**. A distinct GO is required after exact model contract, response-version and financial limits are verified; no new grant or API probe will run automatically.
