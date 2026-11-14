# H34 physical inventory / before and after

2026-11-14, local sources. Assigned main@f50d5432228fdfc5ad67999f7620b9fb64bf1a49 is a coordinator claim; no Git operations. All eight H33 manifest source fingerprints match exactly. No other project or live storage inspected/changed.

| Entry / callers | Before H34 physical boundary | Auth / timeout / repetition | Required change |
|---|---|---|---|
| server.ask_gigachat / MCP | AsyncClient.post(CHAT_URL,json=body) | common get_access_token, 180s, status/JSON parser, no accounting | Guard before auth, bind MCP scope, reuse shared byte transport and ledger |
| server._run_agent_task_impl / executor loop | shared AsyncClient.post(json=body) | common token, 180s, provider events, multiple legitimate tool-loop attempts | Bind authoritative Workspace/Chat/Run, one fresh durable attempt per call, no unknown retry |
| server._request_audit_diagnostic / executor diagnostic | injected client's post(json=body) under wait_for | caller headers/client, audit deadline, events | Reject arbitrary client; fixed audit route and owner, no injected bypass |
| planner_runtime.PlannerSession.call / active task planner | AsyncClient.post(json=body) | token, 90s, session/repair retries and events | Fixed planner_session route, actual final body and existing attempt ID |
| planner_runtime.run_planner / legacy direct | AsyncClient.post(json=body) | token, 90s, events; direct declared UNREACHABLE_PROVEN by S1 | Still guard direct invocation; no implicit authority from reachability label |
| verifier_runtime._request_gigachat / final, permission, planner review | AsyncClient.post(json=body) | token, 60s, typed verifier errors | Route chosen by trusted caller purpose, not provider body; preserve error parser |
| compressor_runtime._request_gigachat / compressor | AsyncClient.post(json=body) | token, 180s, compressor event/callback loop | Fixed independent compressor scope, common ledger and exact bytes |
| gigachat_transport.get_access_token / old seven | OAuth AsyncClient.post(form data) | env Basic credentials, RqUID, 30s, cache; missing-token error embeds raw body | Separate non-LLM gate before cache/env/network; sanitize errors; no OAuth invocation authorized |
| H33 Ordinary byte path | GigaChatTransport.send_bytes → exact MockTransport client.stream(content=wire) | exact TurnAdmission, fixed synthetic token, 8s, no retry | Reuse HTTP boundary, preserve H32/H33 contract; minimally add exact server-owned OFFLINE attempt type |
| OrdinaryCoreAdapter → _FixtureTransport.send_bytes → send | in-memory only | exact type + TurnAdmission, S2/S3a | Preserve unchanged |
| ModelCards checker, launcher urllib, manual probe | dynamic checker / local probe / non-production models GET | S1 separately classifies; no production import from probes | Recheck dynamic/static coverage; do not infer REAL authority from callback or URL |

REUSE CHECK: existing policy already declares all routes and scopes; ledger already stores exact UTF8 wire, policy/context/binding, reserve/SENT/terminal/readback and fails closed on corrupt/old enrollment. H33 owns the HTTP byte boundary; the missing piece is a common server-owned adapter binding legacy calls to that boundary and existing ledger. No second core, ledger, registry, OAuth cache or history store is needed.

Implemented: exact server-only synthetic owner/attempt capability; seven call-site factory/token substitutions and trusted route selection; common guarded client serializes the final body BEFORE admission and delegates immutable bytes to H33. Default unowned calls fail closed. REAL creation remains unconditionally unavailable. Provider caps remain UNVERIFIED until coordinator-supplied evidence; synthetic profiles must be explicitly labeled and can never admit network.

Risks to verify: wrong/injected client; endpoint/body/model/policy substitution; lost reserve/SENT/terminal ACK; repeated attempt/logical call; cancel/deadline before/after SENT; concurrent owner; stale session; marker/engine/capacity; legacy parser and provider-event compatibility. STANDARD/Tk/launchers are protected; only seven call sites receive safety edits. If owner provisioning cannot be proved for a legacy entry, default stays closed and that integration gap must remain OPEN.

## Final census / evidence

All seven listed source sites now enter `gigachat_admission._GuardedClient.post`, then the same H33 `GigaChatTransport.send_bytes` physical HTTP boundary. S1 retains their seven source-boundary entries and separately inventories the shared stream; it does not pretend there are seven independent network clients left. OAuth POST is syntactically inventoried separately, but `require_real_authority` makes it unreachable under H34.

`evidence/post_s1.physical_trace.json`: 20 synthetic HTTP attempts with SENT readback, covering mcp_chat, executor, audit_diagnostic, planner_session, planner_direct, verifier_final, verifier_permission, planner_review and compressor. Source tests require a guarded factory and no direct OAuth in every listed function. `oracle_final` additionally checks that each of seven denied entry calls fails specifically through server/OAuth admission, not an unrelated exception: 1 PASS +7 subtests, zero client construction.

Dynamic Ordinary in-memory/HTTP paths remain exact-type gated. Raw/injected audit clients are denied. ModelCards ships LiveCheckNotAuthorized; a custom checker is a privileged server extension, not a browser/config-selected H34 authority. It remains an explicit full-program static/dynamic coverage gate. Manual models probe/other network tools were never run and are not production imports. Launcher urllib probes are local service checks; profiles and physical CMD are unchanged/NOT RUN.

H34 covers the listed seven and accepted Ordinary chain in bounded OFFLINE form. It does not independently accept all possible future extensions, REAL sockets, full S3b/S3c/S9/S13a, historical adoption, hardware durability/fencing, ledger compaction or RAW privacy.
