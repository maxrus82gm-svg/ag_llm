# Compatibility decision

|Invariant|Evidence level|Status|
|---|---|---|
|Official v1.13.4 source revision|HTTPS exact archive + ZIP comment d09182614c7778c1e0f51d990635c5d4249c437e, package hash|BOUNDED VERIFIED; detached signature/binary correspondence unverified|
|HTTP CONNECT parsing/auth|HTTP integration present; actual parser external missing|UNVERIFIED / dependency source required|
|Single inbound / routing / reject primitives|In-repo factories and route code reviewed|SUPPORTED AS PRIMITIVES; full strict profile unverified|
|Default no DIRECT|Empty/default engine can create DIRECT|UNSUPPORTED AS DEFAULT; explicit reviewed policy required|
|One B-owned actual socket to literal R:Q|Ordinary in-process path visible; no selected protocol/config or OS token proof|UNVERIFIED|
|No DNS/UDP/IPv6/health/helpers|Several concrete conditional paths found|BLOCKED until strict subset/dependency/OS proof|
|Config/root isolation|CLI explicit path possible, defaults/merge/reload exist|CONDITIONAL; protected launcher/config policy not implemented|
|Existing family=V2Ray|Still rejects sing-box|USER DECISION REQUIRED; unchanged|
|MCP/NPFS independence|Existing code unchanged, pure gates regress|Preserved; no new native/SDK test|

Minimal future migration proposal: only after missing sing dependency review and explicit user engine selection, add a separately reviewed family/native schema mapping to existing broker module. Keep C/B/U and NPFS roles, same B listener+remote-owner requirement and all no-DIRECT/WFP gates. Do not relabel current V2Ray contract as accepted sing-box config; no second broker stack is justified.
