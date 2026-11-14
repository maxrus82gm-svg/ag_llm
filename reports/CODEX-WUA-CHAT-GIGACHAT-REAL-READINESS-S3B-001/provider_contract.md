# H34 provider contract: verified code / unverified service

2026-11-14. No web, API discovery, credentials, OAuth or paid call used. Sources are local Model Registry, S2/S3a, existing GigaChat module and accepted H32/H33 reports. Assigned source revision is a coordinator claim; eight H33 source hashes match locally, Git/HEAD not inspected.

| Registry ID | Provider model ID | Current service context / output caps | Reasoning / cache / billing | REAL |
|---|---|---|---|---|
| gigachat_2 | GigaChat-2 | UNVERIFIED | UNVERIFIED | DENY |
| gigachat_2_max | GigaChat-2-Max | UNVERIFIED | UNVERIFIED | DENY |
| gigachat_2_pro | GigaChat-2-Pro | UNVERIFIED | UNVERIFIED | DENY |
| gigachat_3_lightning | GigaChat-3-Lightning | UNVERIFIED | UNVERIFIED | DENY |
| gigachat_3_pro | GigaChat-3-Pro | UNVERIFIED | UNVERIFIED | DENY |
| gigachat_ultra | GigaChat-3-Ultra | UNVERIFIED | UNVERIFIED | DENY |

Registry identities are enabled/non-local GigaChat entries in code, not declarations of currently available commercial models. ProviderProfile is an immutable capability/evidence overlay cross-checked against that same registry, not a second model registry. H34 accepts only SYNTHETIC fixture profiles; an object labeled VERIFIED_REAL is explicitly rejected. UI 250000/10000/20000 preferences never become provider caps.

| Property | Verified local contract | Evidence still required before REAL |
|---|---|---|
| Endpoint | Existing CHAT_URL; trusted server profile and actual httpx URL must match. No body/config URL override | Current endpoint/version, account/model availability, TLS certificate chain and explicit approved proxy behavior |
| OAuth | Single existing get_access_token/cache remain. New unconditional server authority gate precedes cached token, env and HTTP. H34 cannot call OAuth even with a cached token or owner fixture. Legacy fake placeholder does not read/cache credentials; actual fixture token is obtained by H33 after SENT | Account/scope, expiry/refresh behavior, sanitization and token storage review. Any future real factory must reuse existing function and accepted server authority; no refresh/retry after SENT/UNKNOWN |
| Bytes | One S2 final serializer before admission. Metadata canonical snapshot/model/role verified before reserve; body/hash/profile/endpoint/policy/owner bound to existing ledger. H33 sends content=wire | Independently verify all producer/consumer call paths and source SHA; no arbitrary client/checker authority |
| Context/output | H34 synthetic fixtures use explicit bounded profiles and S2 HARD_BOUND. These are test data, never provider facts | Verified context window, output cap, reasoning reserve semantics, input estimator/calibration and maximum liability for chosen first model |
| Usage | Existing Ordinary validator, extract_usage and S2 validate_usage reused. Supplied prompt/completion/total validated; partial/missing/invalid stay UNKNOWN. Valid reported precached count preserved in S3a; absent cached count stays unknown and conservative input liability remains | Provider definitions of prompt vs cached/processed tokens, total vs billable counts, reasoning inclusion/subset, rounding/pricing and usage on errors |
| HTTP | H33 exact MockTransport only, no redirects/env proxy; bounded response and explicit timeouts; legacy parsers/error classes retained | Real response schema/statuses, HTTP error/rate limit contract, socket/client factory and TLS/proxy acceptance. No automatic retries |
| Recovery | Exact reserve/SENT/terminal readback, durable Run owner nonce, one in-flight attempt, cancellation/deadline checks, fresh-process refusal on unresolved owner/SENT | Independent S3c restart/rollback/fault/fencing acceptance; no UNKNOWN→zero or automatic resend |
| Policy | Frozen server-owned policy/profile hashes and Final Audit context; existing ledger enrollment and engine fingerprint. No automatic initialize/adoption/migration | S9 effective policy approval/revisions, production ledger enrollment/adoption preserving history, capacity and RAW retention/privacy |

Coordinator must provide dated primary evidence for the first chosen model: endpoint/account/scope; exact context/output limits; reasoning/cache/usage definitions; max attempt liability policy and estimator; permitted response statuses; retry/stop limits; independent acceptance of all applicable gates. No external lookup is delegated to the implementation agent during STRICT OFFLINE.

Recommended bounded next preparation: choose one existing registry model, verify its contract, approve one short Ordinary Chat request with explicit input/output/attempt/timeout/stop limits. Reuse H32/H33 Turn authority and the H34 physical guard; a legacy Run capability must never fabricate a Turn. More models, compression/memory expansion and financial Workspace aggregation are separate priorities after the first approved safe dialogue.
