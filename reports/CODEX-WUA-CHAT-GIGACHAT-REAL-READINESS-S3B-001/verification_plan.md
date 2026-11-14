# H34 verification plan / before implementation

ARCH CLASS: Web Alarm Ultra / GigaChat / S3b transport+admission. Apply TEST-ENG-01, 36.1/36.3; affected UL-I01/03/04/06/07/10/11. One existing core/storage/policy/ledger/HTTP boundary. STRICT OFFLINE; inherited H27 guard before runtime imports. Fixtures and output under explicit synthetic TEMP; no Git, external network, credentials or production writes.

| Change | Risk | Existing selector | Gap / required check |
|---|---|---|---|
| Seven send sites | Ungated physical post, auth before budget, injected client | S1 RouteTransportTests/static census; planner/verifier/compressor tests | Per-site no-authority → zero token/HTTP; exact admitted positive fake request with SENT readback |
| Server attempt authority | Forgery, replay, wrong owner/root/route/model/policy | H33 authority/byte tests; S3a ledger tests | Explicit synthetic server profiles/owners, fresh/repeated attempt and restart, one shared ledger |
| Physical H33 extension | Byte/header/URL change after admission, hidden retry | test_web_alarm_gigachat_transport.py | New authority at actual httpx request, exact immutable content, two meaningful expected RED controls |
| OAuth guard | Credential read/leak, cached-token bypass | S1 OAuth traffic probe; extract_usage tests | Unowned OAuth denied before cache/env; raw auth body never in errors; existing OAuth stays single owner |
| Terminal/recovery | Success before durable terminal, unknown becomes zero | H32/H33, S3a, Turn/Run Store | Crash/SENT/reopen, cancel, late reply, lost terminal ACK and bad usage on generic legacy path |
| Compatibility/isolation | Parser changes, unreviewed imports, launcher regression | H29/H31/H32/H33, S1/S2 dedicated, H25/H33 quality, Node | Guarded broad regression, compile/UI-smoke for server, source review, protected hashes |

Evidence must retain initial failures and separate positive PASS / expected RED / unexpected FAIL / NOT RUN. Local author checks are not independent Windows acceptance. Dedicated S1/S2 runners remain mandatory; missing historical RAW → NOT RUN, never synthetic replacement. Record legitimate test-contract adaptations for the new safety behavior rather than silently relaxing assertions.
