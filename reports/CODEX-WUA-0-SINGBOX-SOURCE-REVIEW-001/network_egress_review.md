# DNS/UDP/IPv6/hidden egress/ownership

|Source locator|Observed path|Future strict condition / limitation|
|---|---|---|
|`common/dialer/dialer.go:45` / `NewWithOptions`|Detour or default dialer; domain upstream wraps resolver|LiteralIPv4 R avoids this domain path; prohibit detour/resolve actions, verify TLS still authenticates chosen server|
|`dns/transport/local/resolv_windows.go:99` / `dnsReadConfig/adapterAddresses` and box default factory|Windows adapter DNS enumeration/default NS and local DNS transport|Empty DNS config does not remove resolver capability; no-DNS must be proven, not inferred|
|`common/uot/router.go:29` / `Router.RouteConnectionEx`|TCP stream can become logical packet flow|Reject packet/UoT routes, not merely OS UDP sockets|
|`protocol/group/urltest.go:270` / `URLTestGroup.PostStart`|URLTest ticker/probes and changing selection|No URLTest/group/network strategy fallback in proposed strict subset|
|`route/rule/rule_set_remote.go:108` / `RemoteRuleSet.StartContext/PostStart`|Initial fetch + periodic remote rule-set update|No remote rules/resources; cached dynamic source also needs exclusion|
|`box.go:204` / `New conditional services`|Conditional NTP service/dialer|NTP disabled; no helper/system time write|
|`common/tls/ech.go:150` / `ECHClientConfig.fetchAndHandshake`|ECH config DNS HTTPS record lookup|No automatic ECH acquisition; ordinary TLS path only if later approved|
|`common/tls/reality_client.go:222` / `realityClientFallback`|Verification failure triggers cover HTTP via existing conn|Not a newly direct socket in this function; still unauthorized cover traffic unless excluded|
|`protocol/tor/outbound.go:109` / `Outbound.start`|Tor startup and local SOCKS client in Tor-specific path|No Tor/companions; dependencies not closed|

Box may create Clash/V2Ray APIs, services, endpoints and other conditional features. Build/update tools are separate entrypoints; a text hit in cmd/internal is not evidence of automatic runtime update. No global absence of telemetry/update/companion paths is proven: review is bounded and external module closure incomplete.

Ownership path illustration: HTTP listener uses `net.ListenConfig`, ordinary protocol dial uses in-process default dialer and literal upstream. `common/dialer/default.go:239` rejects unresolved domain and chooses IPv4/IPv6 dials by address; both UDP and TCP APIs exist. Goroutines are not separate Windows identities, but real socket owner depends on launch token/thread impersonation/handles/runtime/OS. No SID was created/read as proof. F2 remains **B_EGRESS_OWNER_NOT_VERIFIED**.

Potential one B process is plausible in the narrow chosen subset, not established for arbitrary installed build/config. Existing WFP/source-only candidate cannot enforce it until independent lab tests. No native network test executed.
