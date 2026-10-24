# Route/default/failure findings

`route/route.go:103` / `Router.routeConnection`: route action selects `action.Outbound`, missing tag/network incompatibility returns error; reject action returns rejection. First terminal matched route/reject/hijack is selected in `Router.matchRule` (route/route.go). If no selected rule, it uses default outbound.

`adapter/outbound/manager.go:69` / `Manager.Start/Create`: explicit final must exist; absent explicit final, first created outbound becomes default. If no default is configured, `box.go:319` / `New default fallback factories` installs **DIRECT**. Bundled route docs corroborate first-outbound behavior. Therefore default DENY is **not native engine default**.

`route/conn.go:102` / `ConnectionManager.NewConnection`: ordinary `ConnectionManager.NewConnection` closes on dial error. In the inspected Trojan illustration `protocol/trojan/outbound.go:50` / `trojanDialer.DialContext (illustration, not selected protocol)`, no transport/mux path dials configured `serverAddr` then serializes logical destination; errors return without selecting DIRECT here. This bounded observation does not cover every transport, selector, retry, helper or external dependency.

Selector can load cached selection/change target; URLTest selects by health and probes. Exclude groups, secondary/detour/proxy chains and dynamic API mutation from any future strict mapping. Lower dialer interface/address fallback is a separate mechanism from proxy DIRECT fallback and needs its own restrictions/OS proof.

Future proposal, **not generated config**: one explicit pinned outbound R:Q; explicit TCP admission for one inbound; terminal catch-all reject; no bypass/resolve/sniff/direct extra branch, endpoints or groups. No protocol chosen and no family change performed. Source check of known branches and mutation rejection is not native fail-closed verification.
