# WUA ChatGPT MCP integration kit 0.1.0

Working **synthetic-only** integration: official MCP SDK client → official MCP stdio server → separate server-owned JSONL API worker → real `web_alarm.server.WebAlarmApi.dispatch` on new disposable storage. Four read tools: `ping`, `list_capabilities`, `read_synthetic_context`, `get_status`. No call returns a context without reading the actual fixture API. This is external tool access, not Ultra Model Assignment or a paid model API client.

**Production is BLOCKED.** Accounts/WFP/V2Ray/tunnel are not activated; current fixture bootstrap cannot select a production root or grant native authority. A valid structural profile, all-true approval or fake evidence cannot turn `can_apply`/`can_start_tunnel` on. No installer or tunnel launcher is provided. The tunnel argv/YAML files are disabled **data templates**, not commands to run.

## Existing prerequisites / no installs

Tested locally with existing repository `.venv/Scripts/python.exe`: Python3.12.10, MCP2.2.0, httpx0.28.1, pydantic2.13.5. Uses SDK2 `mcp.server.lowlevel.Server` callbacks, official `stdio_server` and independent `ClientSession`. No hand-written fake MCP transport. Other SDK API versions are not promised; absent dependencies → BLOCKED, no automatic pip/download. The API fixture imports the existing project's WebAlarmApi read-only source, never production storage; no production dependency files are changed.

From the repository root, choose fresh two-digit labels:

```powershell
& '.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/run_suite.py mcp10
& '.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/run_suite.py security10
& '.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/run_suite.py mutant_route10
& '.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/run_suite.py mutant_owner10
```

Those example labels were not used in the submitted package. Outputs: `reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001/runs/<label>/`. Existing directories are refused. The runner sets own TEMP/TMP and a minimal child environment, parses Python source, pins source hashes and records SDK versions. Normal runner exit0=checks passed; mutant runner exit0=exact expected **one** failing control detected (inner test exit1, not an ordinary success). Any extra error or different failure list is rejected. Published final results and original failures are in report/evidence. New verifier runs add files; preserve the submitted manifest before generating a distinct verification manifest.

Do not run `server.py` against real storage. Its only bootstrap mode is `synthetic_fixture_only`, staged under this TASK's `runs/`, exact fixed synthetic TASK ID, fresh owned API root. Fixture bootstrap contains a session-specific ephemeral MAC key, written only in the owned temporary stage and removed by test finally; no actual credentials are read. Server/API processes are trusted test code, not a sandbox against malicious Python extensions/admins.

## Protocol / authorization

MCP initialize/tools-list/tools-call use the real SDK. Each tool has a strict additionalProperties=false schema and typed UUID `request_id`; context additionally requires exact `task_id=synthetic_wua_integration_001`. Request IDs are replay-limited. Unknown tools/fields/types/TASKs are denied with bounded generic errors. Read-only annotations are hints; actual allowlist and gateway authorization enforce the fixture scope.

`ApiChannel` is the replaceable read interface. Current worker is independent STDIO process; it alone owns newly created WebAlarmApi storage. API `POST` is used only to seed one synthetic workspace/TASK. Runtime requests can select only the two fixed GET routes `/status` or `/tasks/<fixture>/context`; there is no arbitrary method/path/file/model/Git API. API worker independently checks HMAC, session, request replay/quota and TASK/operation. Adapter verifies response UUID/session/nonce, canonical content SHA and unchanged storage digest; mismatch closes the channel and reaps its owned child. API stderr is a reviewed NUL sink, not persisted private output.

Bounds: 8192-byte input frame; JSON depth12/items64; API response32768; tool result16384 before SDK wrapping; API response timeout2s; approved loopback route deadline1.5s; bounded broker connections/time/bytes. Secrets/context/args are not written in audit; redacted audit carries UUID/tool/result only. Public evidence contains only synthetic context/nonce/IDs and no channel key. Canonical SHA256/HMAC input: ASCII JSON, sorted keys, separators `(',',':')`. It is different from a raw file digest.

On EOF/error the API child is closed, waited, then only that owned process terminated/killed if required, reader joined; `owned-api-stop.json` records completion. Startup failure also closes the asyncio runner. No existing user's processes or services are stopped. There is no native supervisor or real tunnel stop authority here.

## Important topology finding: STDIO does not remove runtime TCP

The installed Windows Python3.12 `ProactorEventLoop` uses `_fallback_socketpair`: a real dynamic IPv4 loopback TCP connection during event-loop creation. `runtime_compatibility.json` records an actual **owned loopback** probe and stdlib source hash. AF_UNIX is unavailable in this interpreter. This conflicts with the previous intended C-SID rule allowing only `127.0.0.1:P`. The fixture's Python audit deny is installed **after** loop initialization and is not evidence that SID/WFP would permit startup. No WFP rule was applied or weakened.

Selected future target: C-owned official Go → STDIO → a **reviewed synchronous no-TCP C relay** → authenticated local pipe → server-owned MCP SDK/API authority U. B is a separate dedicated V2Ray HTTP CONNECT broker under the actual B token, with only approved literal upstream `R:Q`. Current Python SDK fixture is not that C relay and must not be launched under the single-port policy as if compatible. Relay/pipe peer-token/DACL production implementation remains BLOCKED; the SDK tool/gateway protocol and tests are reusable without pretending the missing deployment connector exists.

`reference_connect.py` is a byte-exact reused synthetic AM07 CONNECT→SOCKS5 prototype. Its live use would require an extra B→localS edge and proven V2Ray egress ownership; it is **not** the chosen production layout. No actual port10808/profile/process was inspected or changed. Port numbers and SID strings in `strict.synthetic.example.json` are test values, not discovered/provisioned host facts. Render real bindings only after a separate authorized discovery/review; never import the example SIDs to another PC.

## Route / diagnostic scope

Synthetic route tests use only literal127.0.0.1 listeners created by the test. `.invalid` authorities are sent in SOCKS bytes and mapped by the fake upstream to an owned local receiver; no DNS/public request occurs. Independent Python audit observer checks roles C→P, reference broker→S, fakeSOCKS→owned receiver and flags any other attempted edge. It does not constrain native Go, OS services, children outside this process or the actual user's V2Ray.

`diagnostics.py --profile <staged JSON> --pin <canonical SHA256> --output <new TASK JSON>` is structural/offline only, expected exit20 even for a valid synthetic profile. It neither enumerates accounts nor probes live listeners. Status and config contracts are in `configs/`; profile/template placeholders stay DISABLED. Template CLI names are taken from cached official v0.0.16 help/sample, not newly downloaded/current upstream. Full native proxy/env/redirect/DNS/child graph and source↔binary identity remain unverified.

Read `reports/.../report.md`, `topology.md`, `connection_gates.md`, `deployment_plan.md`, `manual_engineering_review.md` and `next_user_go.md` before proposing a real connection. Ordinary ChatGPT E2E, native fail-closed and OS containment are separate gates. Working SDK tests do not prove any of them.


## Local NPFS candidate (2026-10-24)

`npfs/Relay.cs` and `Shared.cs` compile to the C-side no-TCP executable; `npfs/Gateway.cs` owns one explicit-DACL local pipe and a suspended/job-contained fixed U SDK child. `npfs/gateway_worker.py` reuses the four existing tools with real WebAlarmApi on a new TASK fixture. The legacy STDIO fixture remains available. Run `tests/run_npfs.py` with the existing project Python for the Windows integration/fault suite; `tests/npfs_regression.py` reruns the previous 63-check SDK and 24-test security selectors into the new TASK only. See `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/README.md`. This is current-user synthetic evidence, not a production connector, cross-SID/WFP proof, tunnel activation or ordinary Chat E2E. Dedicated B-owned V2Ray egress remains an independent blocker.
