# LIVE evidence — Stage A PROBE PASS / inference NOT RUN

Exact USER GO in chat: `CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001 / STAGE A`, 15.11.2026. One execution of `run_stage_a_once.py`; its exclusive `evidence/stage_a_attempt.json` blocks a second run. Script SHA-256 before execution: `50ddecfe9494e73cdb76ed1b18640a18163f3063be598b078cd6fe3df3e9370e`.

Result: OAuth 200 and catalog 200 are inferred from H38's successful parsed return; grant `Probebc453ad3a14527813141f9ab268844ca` is `CLOSED`. H38 durable committed counters: OAuth **1**, catalog **1**, inference **0**. No retry path was invoked. The catalog returned ten safe IDs, including all six registered text models; exact IDs are in `models.md` and `evidence/stage_a_result.json`. The fresh Workspace ledger still has **0 events** after readback, so no inference reserve/SENT/terminal exists. No token, credential, authorization body or header was saved.

These counters and successful parsed results support one physical OAuth request and one physical catalog request; there was no packet-level capture. TLS verification remained enabled; both HTTPS calls succeeded. This is **PROBE PASS**, not a generated reply. STANDARD and TEST were unchanged.

**Stage A stop point:** its grant cannot be reused and it authorized no inference. The later Stage B conditional GO is assessed below; no new grant or API probe ran automatically.

## Stage B USER GO — preflight stopped before network

The user granted a bounded first response, conditional on confirmed model caps and exact response-version IDs. `stage-b-blocker.md` documents why the mandatory H38 `ModelContract` could not be justified. Stage B grant created: **no**. Stage B OAuth: **0**; catalog: **0**; inference: **0**. No new RAW, Turn or ledger event. The prepared Workspace remains intact and the prior Stage A grant remains CLOSED. The Stage B GO was **not exercised**; this is not LIVE PASS.

## Contract amendment — OFFLINE only

The user later approved a narrow first-version contract amendment with an explicit ban on new provider calls pending a fresh GO. The change and 37/37 + S1 69/69 + S2 73/73 OFFLINE results are in `contract-amendment.md`. Real OAuth/catalog/inference calls during the amendment: **0/0/0**. The prepared Workspace ledger readback remains **0 events**. No real response, RAW, Turn or usage has been created. The revised first-attempt envelope awaits a new explicit approval in `go-stage-b-updated.md`.

## Revised Stage B USER GO — stopped locally after control calls

The user gave a fresh GO for one inference on 15.11.2026. A new grant `Firstb8c4483a73cae4bfee1ed06bfa3593f0` was created. H38 durable counters after closure: OAuth **1**, catalog **1**, inference **0**, liability **0**. Both successful parsed control calls used verified TLS with no automatic retry. The catalog confirmed `GigaChat-2` AVAILABLE. The operator's local readiness parser looked at the wrong level of the capability response and stopped before POST `/turns`; read-only diagnosis confirmed the nested `turn_test.real_available=true`. The exclusive attempt marker remains spent. No response version, generated text, RAW, Turn or usage was produced. Workspace ledger after closure: **0 events, 0 attempts**. Port 8765 is no longer listening. See `stage-b-live-stop.md` and `evidence/stage_b_result.json`. The first inference still requires a new explicit GO.
