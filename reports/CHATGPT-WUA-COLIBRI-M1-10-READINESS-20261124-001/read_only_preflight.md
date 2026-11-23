# M1-10 — bounded HOME read-only preflight (NOT AUTHORISED / NOT RUN)

## Before any real operation
- Obtain a **new explicit OWNER GO** naming HOME machine, already-running Client/Bridge, permitted specific GET endpoints, installed build/identity, time window and owner-authorised target. This document is NOT that GO. No new listener or Bridge activation.
- Colibri Ultra 14 confirms actual installed Client Bridge source SHA / protocol, current Manager/slot instance, a **read-only proof of no active or queued work**, and which read-only status path is safe. Source #115 is not installed evidence. Unknown -> STOP.
- Inspect under separately approved scope the protected descriptor/credential ACL and Windows owner SID, launch identity, immutable expected bridge_id, loopback-only origin, authentic principal and exact target/instance. Do NOT print token, IP, credential URL, private path, or full principal to chat/log/GitHub. Reject broad groups, symlinks/reparse, stale descriptor, wrong port or origin, race/owner ambiguity.

## Only if separately allowed
- Authenticated GET `/bridge/v1/health` with **read** permission; verify bridge_id, protocol_version=1.0.0, permissions, status, catalogue revision, schema and absence of redirects/fallback.
- Authenticated GET `/bridge/v1/models` with **read** permission; verify chosen manager_id/slot_id/model_key, deterministic target_id, instance_id, allowed_operations, READY/streaming and stable identity. READY does **not** mean idle.
- **Critical contract gap:** canonical Bridge v1 Health/Target schemas do **not** report active_request_count or queued_request_count. Neither GET proves the slot is free. Require Colibri 14 separate safe read-only evidence and owner attestation, otherwise M1-10 holds (not PASS).
- GET `/bridge/v1/requests/{request_id}` needs **chat** permission and a *known own* request ID, so it is **excluded** from initial read-only. Forbid `POST /chat/stream`, `POST /chat/cancel`, `/v1/control`, restart, health probes to arbitrary LAN, probing busy slots, and paid APIs.
- Compare real installed build/contract/protocol against #107/#108 WUA pins. Any drift -> STOP. After bounded read-only, check no changes in other PIDs, slots, ports, history, settings, request counts; unable to prove => UNKNOWN/HOLD.

## Decision
- Wrong identity/ACL, active or queued request, unknown principal, missing permission, deployment mismatch, stale instance, nonempty unsupported system/tool instructions, unproven unchanged state -> STOP without retries.
- Even read-only PASS does not permit one token of generation or cancellation; those require separate OWNER GO. No MVP2, no automatic retry on UNKNOWN.
- Current: M1-10 NOT RUN, actual HOME HTTP calls=0, model starts/restarts=0, paid calls=0, secret reads=0. Prior #665 matrix remains 8 scoped PASS, 3 PARTIAL, 2 NOT_RUN.
