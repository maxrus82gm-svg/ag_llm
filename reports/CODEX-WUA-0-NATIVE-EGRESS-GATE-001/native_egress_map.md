# Native MCP egress map — PARTIAL

Classification: **SOURCE VERIFIED** = exact local source/declaration, or explicitly
marked coordinator exact-tag source statement; **STATIC HYPOTHESIS** = architecture
candidate; **NOT VERIFIED** = runtime/identity coverage not established;
**BLOCKED** = needed exact source or execution authority absent.

Official tag v0.0.16 → `5f99daabd4aa4a77049e6d81d54a0d8c18335397` is a WEB_10
statement in canonical 19/34, not a new agent Git query. `SOURCE PACK BLOCKED`:
official runtime tar.gz expected SHA-256
`88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0` absent in
bounded local search. EXE SHA-256
`4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571` is a local
byte identity, not reproducible build attestation. No Go bodies reconstructed
from names; no local full native call graph or runtime network execution.

| Initiator → destination | Transport | Proxy policy source | Possible bypass / unresolved edge | Required future prohibition | Evidence / status |
| --- | --- | --- | --- | --- | --- |
| tunnel-client control-plane → configured base/path, polling/metadata/responses | HTTP(S) | global/component config; main transport | empty override, redirect/retry/new client, DNS; exact paths open | allow only pinned loopback proxy edge, all other native flows denied | Fixed Proxy/main transport **SOURCE VERIFIED by WEB_10 tag review**; full graph **BLOCKED** |
| secret control-plane transport → configured endpoint | HTTP(S), secret/header handling | separate transport plus component config | separate client/settings; stale secret reference must not select direct | same scope/edge policy; no credential-dependent default route | **SOURCE VERIFIED by WEB_10** applies proxy; complete behavior **NOT VERIFIED** |
| MCP HTTP startup/runtime/channel → configured MCP server | Streamable HTTP/HTTP(S) | global/MCP/binding plus SDK factories | startup vs runtime factories, reconnect/SSE, binding overrides | every socket under scope, exact intended proxy edge | HTTP proxy/Unix special case **SOURCE VERIFIED by WEB_10**; SDK/binding completeness **BLOCKED** |
| MCP STDIO → private Python/read-only server | pipes; child may open sockets | child environment/config independent | child process, other binary, resolver/API requests | default-deny descendants at birth; only approved local API edge | Architecture known; exact launch/env/network graph **NOT VERIFIED** |
| OAuth → resource/auth metadata, possible token/JWKS origins | HTTP(S), redirects | discovery/client-specific, trusted origins | new issuer origin, token client, retry, different resolver/transport | same deny boundary for all allowed origins; no unsupervised child/service | Source paths alone not proof; bodies **BLOCKED** |
| Harpoon → target/discovery/additional transport | HTTP(S), optional extra/Unix transport | global/Harpoon/target config | target-specific client, redirect/new scheme/additional transport | unknown transports denied, minimal first mode excludes them | Embedded config hints only; complete implementation **BLOCKED** |
| proxy-health → proxy/target probe destinations | independent dial/CONNECT/TLS | configured route health | DNS/dial outside primary HTTP client; bookkeeping mistaken for network fallback | health sockets covered by same scope, no special broad permit | AM06 symbol map only; bodies/actual destinations **BLOCKED** |
| resolver inside any member → OS DNS/DoH/DoT or proxy name | UDP/TCP/HTTPS/IPv6 possible | app/Windows/resolver-specific | direct DNS, proxy-host lookup, v6/alternate NIC, DoH via 443 | deny every non-edge flow, all families/protocols; literal proxy endpoint | full native resolver behavior **NOT VERIFIED**; no DNS probe performed |
| optional cloudflared → external companion service | separate native transport/process | own config/token/managed supervisor | does not inherit parent Go HTTP Proxy callback | exclude by verified mode AND enforce descendant default-deny; otherwise independent proof | supervisor child risk **SOURCE VERIFIED by WEB_10**; installed source/egress **NOT VERIFIED** |
| any member → newly spawned helper / existing IPC broker | process/IPC then network | separate process authority | child of another EXE, PID reuse, shared Python path, existing external broker | authenticated scope identity and birth-time confinement; audit IPC escape channels | **STATIC HYPOTHESIS** risk; containment **NOT VERIFIED** |
| CONNECT adapter → SOCKS5 broker | literal loopback TCP, domain ATYP=3 | AM07 frozen explicit upstream | bypass adapter entirely; endpoint port takeover; helper/child leaks | adapter only exact SOCKS edge; prove receiver/broker identity | AM07 local code **SOURCE VERIFIED** for reference only, 36/36 historical; no native inference |
| SOCKS/HTTP broker sing-box → approved remote upstream | runtime-dependent TCP/UDP/DNS | loaded core, selectors/rules/detours | DIRECT, selected fallback, local DNS, another remote route | independently attest loaded policy/outbound; future exact broker remote policy | ownership snapshot only; **NOT VERIFIED** |
| WUA child → Web Alarm local fixture/API | loopback HTTP or STDIO adapter | read-only application allowlist | arbitrary host port/gateway or other storage/process | exact local API endpoint, authentication/identity where required, no public destinations | original read-only design, current real chain **NOT VERIFIED** |
| ChatGPT Desktop frontend → cloud/plugin association | platform/host network stack | host application policy, not tunnel-client proxy flags | frontend route may sit outside runtime scope | if included in protected chain, needs its own explicit scope/route proof; existing app policy untouched | ordinary Chat E2E **NOT VERIFIED**; no authority to alter current frontend |

The approved remote broker is a **trust boundary**, not evidence of a secure route.
Allowing loopback to it does not prove what it does remotely. Client restrictions
cannot prove broker DIRECT/DNS policy; permitting every external broker flow would
evade the user's requirement. First offline VM has **no live broker bridge**.

## Missing source pack: precise request

Need verified official `tunnel-client-runtime-source-v0.0.16.tar.gz` via separately
authorized transfer; size 239841, expected digest above. Inspect actual contents,
module locks and build provenance before treating it as corresponding to EXE.
Required families: `pkg/{transport,proxy,runtimeconfig,controlplane,mcpclient,oauth,
runtimeharpoon,proxyhealth,cloudflared,process,app,runtimecli,localproxy}`,
`cmd/client/{root_command,run_command,dev_command,stdio_preflight}.go`, `go.mod`,
`go.sum`, generated/build inputs; relevant Go stdlib/net/http/net/resolver and
exact SDK/dependency bodies. Full path list already in AM06 `binary_symbols.json`;
it is a locator list, not the files themselves. Source availability and EXE
identity must remain separate questions.
