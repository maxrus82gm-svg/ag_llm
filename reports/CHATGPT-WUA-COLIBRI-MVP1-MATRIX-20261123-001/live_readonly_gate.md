# Proposed M1-10 real read-only preflight, NOT AUTHORISED and NOT RUN

WUA #665 is a source-only independent evidence review. This document is a
**permission checklist** for a later owner-approved bounded REAL read-only
preflight. It is not a script and no calls have been made.

## Before any real query

- Confirm explicit owner approval for the specific HOME computer and running
  Colibri Client Bridge, chosen source/version, and the exact allowed read-only
  status/health/identity checks. Discovery alone is NOT permission.
- Confirm Colibri Ultra 14 has finished its separate Manager setup; actual
  Client/Manager identities and deployed SHA/contract must be established
  without copying credentials or profiles into WUA documentation.
- Verify Client opt-in Bridge is already up if and only if authorised. Do not
  start a second Client, enable a disabled Bridge, restart STANDARD, or
  bind/scan ports under this preflight.
- Check protected descriptor and token file ACLs/ownership on the
  authorised profile, expected bridge_id, protocol_version, launch identity,
  loopback-only port, authenticated health/principal, and READY status.
  No secrets, raw tokens or credential URLs in any report.
- Check selected Manager/slot instance_id, active and queued request counts,
  exact selected target_id, expected capability, and absence of existing
  user work in the chosen target. Unknown state means stop.
- Check that current WUA source matches pinned v1 contract and real
  installation is compatible; drift means stop before any inference.

## Non-negotiable stop and separation

Wrong principal/bridge identity, unsafe ACL or path, unexpected port,
unverified instance, active/queued owner, unknown cancellation status,
stale descriptor, simultaneous unrelated work, mismatched contract,
absence of explicit owner scope or uncertain process identities: **STOP**.
Do not modify Manager, storage, running LLM, server configuration or
Workspace; do not infer availability from a static screenshot.
M1-10 read-only assessment requires its own explicit OWNER GO.
A later actual minimal local text generation, streaming/usage and optional
cancel requires **another** OWNER GO after read-only PASS.
Paid/cloud external inference (M1-11) needs separate provider/cost GO.
No automatic retry on UNKNOWN and no multi-Manager LIVE concurrency (MVP2).
Postcheck must demonstrate unchanged unrelated PIDs/slots, ports and history.

Status as of 23.11.2026: M1-10 NOT RUN, M1-11 NOT RUN.
