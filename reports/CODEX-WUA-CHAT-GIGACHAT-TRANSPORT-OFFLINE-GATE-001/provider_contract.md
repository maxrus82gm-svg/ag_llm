# H33 provider contract / REAL gates

Evidence is local source and synthetic fixtures only, 2026-11-13. No internet, provider discovery, credentials or OAuth used. Registry identity is verified against code; current provider capabilities, pricing and commercial behavior are **NOT VERIFIED**. No inferred provider limits.

| Registry ID | provider_model_id | Context / output capability | Reasoning / billable semantics | REAL admission |
|---|---|---|---|---|
| gigachat_2 | GigaChat-2 | NOT VERIFIED | NOT VERIFIED | DENY |
| gigachat_2_max | GigaChat-2-Max | NOT VERIFIED | NOT VERIFIED | DENY |
| gigachat_2_pro | GigaChat-2-Pro | NOT VERIFIED | NOT VERIFIED | DENY |
| gigachat_3_lightning | GigaChat-3-Lightning | NOT VERIFIED | NOT VERIFIED | DENY |
| gigachat_3_pro | GigaChat-3-Pro | NOT VERIFIED | NOT VERIFIED | DENY |
| gigachat_ultra | GigaChat-3-Ultra | NOT VERIFIED | NOT VERIFIED | DENY |

All six are enabled, non-local GigaChat identities in the existing Model Registry. Enabled means selectable identity, not permission to send REAL. Unknown/disabled/non-GigaChat identities are rejected by existing preparation. No parallel registry is introduced.

| Field | H33 contract | Before REAL |
|---|---|---|
| Endpoint | Reuses `gigachat_transport.CHAT_URL` = `https://api.giga.chat/v1/chat/completions`; bound into saved Turn admission | Confirm current provider endpoint/TLS and server authorization; no user URL override |
| OAuth | Existing `get_access_token`, OAUTH_URL, cache remain untouched. H33 uses exact fixed synthetic token boundary and constructs only MockTransport | Review existing scope/cache/error sanitization; wire existing OAuth only behind accepted server-only REAL permission. No token refresh retry after SENT/UNKNOWN |
| Wire | Existing PreparedRequest + S2 UTF8 serializer; bytes/hash/model/policy/endpoint bound; HTTP `content=wire`, no `json=`; trusted Bearer/Accept/Content-Type | Independent byte/provenance/secret review; never accept serialized receipt as authority |
| HTTP | One POST, explicit connect/read/write/pool deadline, trust_env=False, redirects=False; bounded decoded response | Independently review network-client factory, TLS/proxy policy and final physical permission check; H33 has no such REAL factory |
| Status | Only HTTP 200 can succeed; non-200 decoded object → safe provider error. Invalid JSON/oversize → parse error; response text from failed status never published | Verify provider schema/status contract, 401/429/5xx policies; no automatic paid retry |
| Usage | Reuses extract_usage/common validator. Only supplied nonnegative integer prompt/completion/total accepted; partial/invalid/missing remain unknown, never invented zero. Reasoning accepted only as valid nested subset ≤ completion, never added to total | Verify provider accounting, rounding, cached/reasoning/tool semantics. Synthetic fixture results do not establish billing behavior |
| Per-chat settings | Existing 250k context / 10k answer defaults and 20k UI choice are user preferences. H33 synthetic transport retains bounded 8192-byte request/response, 128 output-token request, 8-second limit | Resolve preferences against verified per-model context/output caps and calibrated effective policy; do not treat preferences as provider capabilities |
| Budget | Existing H32 ordinary per-attempt scope, HARD_BOUND synthetic policy, reserve/SENT/readback/terminal; missing/old/corrupt marker denied | Real calibration/admission policy, adoption/engine upgrade, append-only ledger growth and RAW retention gates remain OPEN; no Workspace financial budget |
| Recovery | SENT retained on crash/uncertainty; no repeat send on retry/reopen, no automatic release. Terminal must be committed/read back before success | S3c full recovery/rollback/owner fencing, S9 effective policy and S13a independent acceptance |

Minimum REAL checklist: independent H33 acceptance; resolve FOLLOWUP-WUA-H32-REAL-CONTRACT-001; verified per-model caps/calibration; reviewed existing OAuth sanitization; complete applicable S3b/S3c/S9/S13a gates with all reachable physical routes covered; migration/retention decisions; explicit OWNER GO and a separately reviewed server capability. Browser/UI/env/config and H32/H33 synthetic policy cannot grant it. LIVE remains disabled.
