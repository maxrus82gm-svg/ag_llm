# Process / IPC / socket topology and compatibility

TASK `CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001`. Profile **STRICT_V2RAY_BROKER**. C/B below are role labels and future fresh local Windows SID bindings, not existing accounts. U is the existing server-owned authority, excluded from the two technical SID rules. No assertion that those rules protect all of U, ordinary ChatGPT Desktop or the whole Windows host.

## Actually exercised local integration

`Independent official MCP SDK client --STDIO--> SDK MCP adapter --authenticated bounded JSONL STDIO--> separate synthetic API worker --in-process dispatch--> WebAlarmApi(new owned storage)`.

All these test processes run under the current test user; real C/B accounts are absent as proven prerequisites. API worker creates only its new fixture root under TASK/runs/, seeds a synthetic workspace/TASK, then exposes only scoped GET reads. `get_status` filters `/status`: no storage_root is returned. The remote cloud/ChatGPT/Go/V2Ray are not in this test.

**Hidden runtime edge:** the installed Python3.12 Windows ProactorEventLoop creates an IPv4 TCP socketpair on a new dynamic loopback port. Actual own-loopback observation and stdlib source digest: `runtime_compatibility.json`. A broker port was held reserved by an owned test socket while probing, proving the observed self-connect used a different port. The prior WFP candidate's C→127.0.0.1:P predicate intent would reject it. **No real WFP classification was run.** The fixture audit deny begins after loop initialization, so it cannot establish zero startup TCP. The independent SDK test parent also uses this runtime, but only the future C-owned child conflicts with C's policy; the parent/UI is outside C/B.

Therefore **do not deploy this Python asyncio child under C's single-port policy** or add a dynamic range exception. Current MCP code is a working integration fixture, not a compatible native C deployment.

## One selected future target, with missing components explicit

```text
ordinary ChatGPT/cloud
  ↕ OpenAI Secure MCP Tunnel control plane (not activated)
C: official Go tunnel-client ──TCP 127.0.0.1:P──> B: dedicated V2Ray HTTP CONNECT broker
  ↕ inherited STDIO                                 └─TCP literal R:Q─> approved remote proxy upstream
C: reviewed synchronous no-TCP stdio/pipe relay [NOT IMPLEMENTED]
  ↕ authenticated local NPFS pipe [NOT IMPLEMENTED / ACL-TOKEN PROOF PENDING]
U: server-owned MCP SDK gateway + restricted WebAlarmApi read authority
```

U may internally use Python's self-socket outside C/B; this is **not** a claim that U is OS-contained by C/B. U must accept only restricted read RPCs and must not provide network/process/file delegation to C. Other Windows IPC/services usable by C remain a mandatory native threat-model gate. The existing `processes.mcp=C` contract role is the **C-owned stdio frontend/relay**, not an instruction to run current Python server under C. `processes.gateway=SERVER_OWNED_AUTHORITY` is the SDK/API side. No such production connector or pipe is implemented or activated now. Current `ApiChannel`/bounded request/response/tool interface provides the reusable boundary; production authorization/task-grants need a reviewed new connector, not arbitrary storage access or a fake mode switch.

| Channel | Caller → peer / authority | Transport / endpoint / permission | Failure / actual status |
|---|---|---|---|
| Cloud request/control | OpenAI service ↔ official client C | Authenticated HTTPS control-plane, cached candidate base `https://api.openai.com`; runtime tunnel auth private | Real resources/entitlement/source/native paths pending; hosted ON HOLD |
| C outbound proxy | Official C client → dedicated B V2Ray listener | Explicit HTTP proxy at literal127.0.0.1:P, CONNECT for HTTPS. Only approved owned P, peer token/bind/source proof required | No HTTP(S) proxy → SOCKS URL substitution; broker failure STOP; Go runtime/fallback NOT VERIFIED |
| B external egress | Dedicated V2Ray process with actual **B token** → approved remote proxy R:Q | Literal upstream IPv4/TCP R:Q, no host DNS, DIRECT, alternative proxy or implicit fallback | B owns actual egress, not just wrapper; exact engine/config/outbound proof pending |
| Go→local MCP | C client → C no-TCP relay | Inherited STDIO handles, exact signed child/hash/argv/environment | Relay absent; Python runtime conflicts; BLOCKED |
| Relay→authority | C relay → U server-owned SDK/API | Local NPFS pipe only, reject remote SMB, exclusive instance, constrained DACL, mutually verified process/token identity and session grant | No TCP API exception. Pipe/ACL/impersonation implementation and negative tests pending |
| SDK→API | U SDK → U server-owned read interface | In-process call or trusted bounded local interface to existing authority; never expose Run Store directly to C | Actual fixture tests use separate JSONL worker on fresh disposable state; not a production root opener |
| Health/admin H | Official C client binds own loopback ephemeral H | Cached health setting127.0.0.1:0; external UI disabled; no automatically permitted C outbound H | Bind ownership, inbound attack surface, accepted-flow/WFP behavior pending; no invented disable flag |
| Optional branches | OAuth/Harpoon/proxy health/companions | STDIO avoids intended HTTP MCP OAuth discovery; no configured Harpoon target/Cloudflared; explicit proxy candidates still specified | Full native graph/env/child/source audit pending; unknown path BLOCKED, not presumed absent |

The selected B layout uses V2Ray's **verified native HTTP CONNECT inbound** in a separately staged B-owned process; exact implementation/version/schema still must be chosen. It does not imply that any current SOCKS port supports CONNECT. The existing user's V2Ray listener/profile/ownership was neither inspected nor changed.

## Why reference CONNECT→SOCKS is not the live target

The exercised reference layout is test client→owned CONNECT P→owned SOCKS S→owned fake control receiver T. It has three explicit socket edges and an independent role observer. If used live, B would need a local S edge as well as remote egress or would delegate egress to another process. If that V2Ray has U's SID, the two technical SID policy does **not** constrain its external socket. Even if V2Ray also has B's SID, the previous B-only-R:Q policy conflicts with B→local S. No exception is auto-added. Hence the chosen target removes S by using the dedicated B V2Ray process itself as the CONNECT broker.

## WFP and IPC limitations

The previous backend expresses BLOCK predicates; the selected C:P / B:R:Q edge is **unmatched**, not an explicit global allow. Native Windows Firewall arbitration, IPv4/IPv6/protocol/SID semantics, inherited/impersonated/changed tokens, existing flows, BFE boot/restart and bind ownership are not proven. Exact port does not authenticate the listening process; synthetic nonce takeover detection is only a fixture authority oracle. WFP connect predicates do not generally restrict local named pipes, BITS/COM/system DNS or delegated service egress. Local pipe authentication is necessary and does not by itself close all other IPC channels. T2 or delegated-service containment may require a stronger approved boundary. All unknowns block activation; application no-fallback is not OS-enforced child confinement.
