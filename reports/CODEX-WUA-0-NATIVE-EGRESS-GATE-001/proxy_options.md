# HTTP/mixed vs CONNECT→SOCKS5 — decision

| Option | Safety/compatibility | Failure/maintenance | Current decision |
| --- | --- | --- | --- |
| Existing attested HTTP/mixed inbound | Fewest moving parts; can support HTTPS CONNECT and HTTP absolute-form if actual config confirms it | Still needs native/child OS boundary and broker remote/DNS/DIRECT proof | Preferred **if** confirmed; current HTTP/mixed **NOT VERIFIED** |
| AM07 CONNECT→SOCKS5 prototype | Fixed loopback upstream, synthetic domain ATYP=3, no local DNS/direct/retry; 36/36 historical reference tests | Extra process/identity/port lease/cleanup; CONNECT-only, not all HTTP paths; no real destinations | Useful reference candidate; **not installable production proxy** |
| Proxy environment/NO_PROXY or direct socks5 URL | Per-client settings are not OS confinement; exact-tag parser only allows explicit http/https according to WEB_10 | Ambient/default/child/custom transport may bypass; no process-wide fail-closed proof | Not a Native Egress Gate |

Independent WEB_10 accepted AM07 only as a bounded reference with open risks;
new TASK does not repeat its 36 cases. A correct adapter cannot prove native
client use of it or sing-box's selected remote outbound. Every path still needs
its own exact edge and scoped child coverage. Real native run is not authorized.

## Current read-only ownership snapshot

`inventory.sanitized.json`: V2RayN PID 18032, sing-box PID **19124**; its listen
ports are **127.0.0.1:10808 and :10813** in this TASK. Requested 10808 is owned
by sing-box; requested 10814 has no listener in the all-listener snapshot.
AM07's 10808/10814 and PID 27008 were historical snapshots; the differences do
not establish who changed/restarted anything. This agent did not do so.

Current executable path/command line unavailable through the permitted CIM read.
Loaded config/cwd, HTTP/mixed protocol, current selector/outbound, DNS and DIRECT
rules are **NOT VERIFIED**. No live socket/greeting/CONNECT/DNS/HTTP probe or
runtime config API query. GUI saved rules are not accepted as loaded state.

Next minimal evidence: owner-supplied sanitized, process-correlated loaded config
and selected runtime policy/route provenance with credentials removed, through an
approved read-only channel. Do not raise permissions or guess a file/port scheme.
Protocol operation and actual remote path require separately authorized gates.

**Final architecture recommendation:** air-gapped Windows VM for the first native
offline gate; separately design process-scoped default-deny with exact broker
edges for any later online chain. Reuse existing HTTP/mixed inbound only after
attestation; otherwise extend/review an adapter only under a new scoped mandate.
Neither route is activated by this report.
