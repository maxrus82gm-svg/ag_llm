# Connection gates / actual health meaning

No gate below is an approval to change the host. Current global state: **HOSTED_TUNNEL_ON_HOLD_BY_USER**.

| Gate | Required evidence / current result | Failure behavior |
|---|---|---|
| L1 local MCP | Real official SDK initialize/list/call; four exact tools, nonce/hash/storage/read scope; two process lifetimes | Implemented and tested only on synthetic API fixture. Invalid request → bounded generic error, no arbitrary dispatch |
| L2 fixture route | Own CONNECT→SOCKS→fake control receiver, independent correlation/attempt observer and faults | Synthetic tests only; no direct/secondary route in this code; observer negative control must detect unexpected connect |
| R0 runtime compatibility | All C-owned runtime sockets/IPC, not just MCP logical transport | **BLOCKED:** current Python asyncio creates dynamic TCP; no-TCP C relay/compatible runtime not implemented/proven |
| I0 server authority IPC | Exact local pipe, existing server authority identity, DACL, exclusive creation, client/server process/token validation, task grant, replay/size/deadline bounds, no network delegation | **BLOCKED:** current JSONL fixture HMAC is not Windows pipe/token proof |
| S0 two identities | Two new local unprivileged SIDs, separate from UI, origin/owner/token/children/startup/credential ACL proof on target PC | **NOT PROVISIONED by this TASK**; no account enumeration/creation. SID strings or all-true proof JSON do not qualify |
| W0 OS egress | Reviewed lab-proven effective WFP policy: C only P, B only R:Q; IPv6/nonTCP/DNS/delegation/child/bind/boot/concurrency failures tested | **NOT VERIFIED**; previous CanApply=false/Install-Uninstall BLOCKED remain; no automatic extra TCP exception |
| B0 V2Ray ownership | Separate dedicated V2Ray HTTP CONNECT instance under effective B SID; signed binary/config/upstream pin; no DIRECT/resolver/fallback; control-subject fault receipts | **NOT VERIFIED**; existing V2Ray untouched. Host-user SOCKS delegation cannot qualify |
| G0 official client | Exact approved source archive/build attestation and version; complete control-plane/MCP/OAuth/Harpoon/proxy-health/retry/redirect/env/child/DNS audit | Cached v0.0.16 help/sample confirms limited syntax; **native graph/fail-closed/source↔binary BLOCKED** |
| P0 Platform/workspace | User confirms Secure MCP Tunnel entitlement/permissions in correct Platform and ChatGPT workspace, authorized tunnel resource and runtime auth delivery | **NOT CHECKED**; no resource/key/API access created, no password requested |
| A0 hosted activation | R0/I0/S0/W0/B0/G0/P0 accepted independently, exact executable/config/identity/endpoint/time budget, explicit new USER GO | **NOT ACTIVATED**; current kit has no apply/start path and ignores fake approvals |
| E0 ordinary Chat | Four actual calls from ordinary ChatGPT: ping, capabilities, allowed synthetic context and forbidden other_task; independent API/relay/server receipt comparison | **NOT VERIFIED**; SDK success is not ChatGPT E2E |

G0 official prerequisites and P0 access are distinct from model assignment: the tunnel's control-plane API key authenticates runtime tunnel traffic; it is not a call to a model completion API. This kit makes no model API request and uses no paid model service. Availability, organization/workspace roles and billing terms were not queried; do not infer them from a ChatGPT subscription or the cached sample. API keys/passwords must not be sent in chat.

## Versioned client contracts

`integrations/wua_chatgpt_mcp/configs/tunnel-client.v0.0.16.disabled.yaml` follows the cached official STDIO sample. `tunnel.launch.contract.json` lists only six names confirmed in saved `run_help.txt`: config, global/control-plane/MCP/Harpoon HTTP proxy and health listener. Placeholder argv is data, not executable. Explicit proxies are HTTP URLs; a SOCKS URL is not inserted. No guessed disable flags, no fake tunnel ID. Upstream documentation links in `source_evidence.json` are references from the TASK; no network/Git fetch was performed. Full precedence and ignore-NO_PROXY semantics are not elevated from cached documentation into runtime proof.

Future launcher must clear ambient environment/profile overrides, prevent unsigned config substitution and secret inheritance into tools, pin executable/config/child closure and use an independently verified supervisor. Current data lists relevant denied keys but cannot prove every native override or transport is covered. Optional Cloudflared/managed tokens, extra Harpoon transports, browser auto-start and unsafe raw logging stay absent; unknown startup path STOP.

## Preflight versus health

`diagnostics.py` structurally validates a pinned own JSON. A valid synthetic example still returns exit20 and can_apply/can_start_tunnel=false. Fake evidence is ignored, not converted to authority. It performs no network/user/ACL/WFP discovery. `diagnostic_cli.json` records the real CLI result and mandatory unverified states. The earlier `diagnostic_preflight.json` is a pre-runtime-review structural snapshot; it also never permits activation.

MCP `get_status` means only: its scoped synthetic server-owned API responded. `ping`/capabilities do not imply proxy, identity, WFP, cloud or ordinary Chat health. A future supervisor must distinguish those components, detect config/owner/heartbeat/loss drift and stop only its owned chain under explicit authority. No auto-resume, DIRECT or another proxy; no replacement credential scope, host reset or extra port on failure. Such native supervision is not implemented here.
