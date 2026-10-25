### WEB_10 / 2026-10-20 — portable MCP discovery/deployment toolkit v0.1.0-offline, independent bounded review

**TASK:** `CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001`; [user-published Codex toolkit / commit #374](https://github.com/maxrus82gm-svg/ag_llm/commit/6b3403f034b56b3dbb89f3ffcb44695f8d194101). **VERDICT:** **OFFLINE TOOLKIT SOURCE / ARTIFACT PUBLICATION BOUNDED REVIEW PASS WITH EXPLICIT OPEN IMPLEMENTATION AND SECURITY GATES**; `RESULT READY` for the **permitted Discovery/Plan/static Verify/rollback planner deliverables**, **not** `SECURE INSTALLER READY` or Windows/V2Ray native security acceptance.

**Publication / independent checks:** all **87/87** manifest-listed file paths independently found in current GitHub directory listings, manifest separately present; SHA-256 + original byte count independently matched **10/10 selected critical report/runtime/toolkit files**, using LF for nine and original CRLF for `toolkit/contracts/requirements_manifest.json`; source hash pins in final published PS7 suite were cross-compared with the verified source bytes. This is not a claim that every one of the 87 file hashes was individually recomputed. Static examination covered `Collect-Host.ps1`, `Discovery.ps1`, `WuaMcp.psm1`, Plan/Verify/Install/Uninstall wrappers, `UnavailableWfpBackend.cs`, policy contract, tests, requirements, README and security limitations; no real Windows modification APIs or provisioning implementation present in Install/Uninstall entrypoints. Published Codex card full SHA-256 `bdb2c19f4638cfb9ef64ce9c53a8685968a782392a960d939df4a733f2513cc9` independently matched rotation receipt; B1 waiting, B2 full assignment, B3 result; prior published B2/B3 history text-exact preserved from `a9615a1...`. One recorded atomic card-write `WinError 5` was recovered after a guarded retry; underlying cause not proved.

**Functionality / honest meaning of coverage:** PowerShell/.NET-only portable toolkit (no additional Python runtime) implements bounded local machine discovery, strict 55-field/A–K contract, redacted/public inventory, 11-action deterministic planning, config/plan digest binding, static policy checks and owner-ledger rollback planning. Codex's actual bounded host observation: **55/55 required fields represented**, **14 local metadata facts verified**, **42 requirements BLOCKING**; these counts do **not** establish 55 confirmed safe facts or all-Windows compatibility. The final reported **PowerShell 7 synthetic suite 62/62 PASS** is backed by a published 62-case result with source pins, but was **not independently re-executed by WEB_10** and **does not prove OS network isolation**. Final PowerShell 5.1 **8/8 syntax parses** with execution policy Restricted; final PS5.1 runtime **NOT RUN**. Early 47-case prototype used process-only `-ExecutionPolicy Bypass`, disclosed and not repeated for final release; no policy-store modification claimed. Portable Windows 11 and other profiles are synthetic only; only one Windows 10 Pro host read-only metadata collection was actually used.

**SAFETY GATE:** `Install-WuaMcp.ps1` and `Uninstall-WuaMcp.ps1` remain **unconditionally BLOCKED** with exit 20; source-only `UnavailableWfpBackend.cs` returns `CanApply=false` and throws on mutators, and there is no executable WFP/security backend, trusted host-bound ledger or permission to change host accounts/firewall. A matching plan digest, operator claims, `-Apply`, or an unverified zero-work ledger cannot enable installation/removal. The current model is **T1 candidate only**, not robust T2/IPC isolation, no checked WFP ALE SID/loopback/receiver ownership, no BFE/boot/established-flow proof, no DNS/delegated-service closure, no authenticated broker remote route, no native client/source binary proof, no live ordinary Chat E2E. `HOSTED_TUNNEL_ON_HOLD_BY_USER` remains binding; no host/production changes or live network operations authorized.

**NEXT / NOT USER GO:** review/select approved offline source/asset transfer, secure script-execution prerequisites (no auto-bypass), separately attested isolated Windows laboratory, then propose **one bounded implementation and proof task** for native user-mode provisioning/readback/security backend, independent negative controls and fail-closed rollback. Only after independent security proof + explicit new USER GO can `Apply` be implemented/enabled; later native client/live V2Ray/hosted/ordinary Chat E2E gates remain separate. User's end goal is **repeatable installation on another PC with auditable discovery/plan/ownership and no imported SIDs/secrets**, not indiscriminate extraction of all host data.

---

### WEB_10 / 2026-10-19 — Independent assessment of CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001

**RESULT: BOUNDED ANALYTICAL / PUBLISHED-ARTIFACT INTEGRITY PASS; OS/NATIVE SECURITY NOT VERIFIED.** [Codex 007 architecture report, user-published #372](https://github.com/maxrus82gm-svg/ag_llm/commit/68ba4fed795077ce594de41166d8cdafa77137b6). `reports/CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001/` contains **12/12** declared artefacts and manifest. WEB_10 independently rehashed exact UTF-8 size+SHA-256 for **9/12 LF** and **3/12 original CRLF** files (published GitHub LF-normalization only; original hashes match upon CRLF reconstruction). Independently matched published Codex card SHA-256 `8f1f0705946099390147802164fc6886db94af90998e1900bfa7707e45dbca2b` to rotation receipt; current B1 `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`; B2 contains the original full assignment; B3 contains factual result; original B2/B3 history preserved exactly compared with `card_before.md`. First `WinError 5` during cross-folder replace is retained in `card_rotation.json`; one guarded retry succeeded; underlying denial cause still unknown.

**Independent technical judgement:** Claude's account-scoped egress proposal is a **valid candidate for T1, not a completed policy**. Codex appropriately rejected P1 and any unsupported P2 guarantee, refined the non-VM candidate to nonadmin `wua-client` SID (C) + independent `wua-broker` SID (B), exact `127.0.0.1:P` broker destination from C, B pinned to approved authenticated remote `R:Q`, separate HTTP CONNECT broker with no DIRECT and user-mode provisioned WFP static nonoverlapping deny predicates. Normal user's ChatGPT Desktop remains outside C/B scope and **is not protected by those rules**. WFP/SID policy semantics, `ALE_USER_ID` matching, priority/arbitration, loopback classification, listener takeover, DNS/COM/BITS/other service-mediated requests, startup/BFE failures, old sockets, remote identity/DNS/bootstrap and rollback are **unverified and critical**; T2 malicious-code policy needs a stronger capability/IPC boundary (AppContainer/LPAC or separately proved guest). The report correctly notes that `127.0.0.1:0` is a request for an ephemeral health listener, not disable. Microsoft reference for firewall explicit Block > conflicting ordinary Allow: https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules ; WFP priority constraints: https://learn.microsoft.com/en-us/windows/win32/fwp/filter-arbitration . Neither documents a tested effective host policy. **Do not implement broad Block ALL plus independent Allow localhost as an assumed exception.**

**Codex recorded**: 9/9 Claude manifest entries locally size/hash matched; nine local Windows SDK/CDXML files read statically; 17 definitions checked (16 unchanged and one rotation wording change); 206/206 non-card baseline paths unchanged **per local Codex census**, not independently rehashed from live Windows. **0 native, system, network or security test executions**, earlier reference suites not rerun, source archive `tunnel-client-runtime-source-v0.0.16.tar.gz` still unavailable locally. **Independent verifier** did only GitHub artifact/code-of-report review and documentary Microsoft cross-check; no Windows execution. The 7 planned stages are **NOT RUN**. `OS-ENFORCED EGRESS ISOLATION NOT VERIFIED`; `NATIVE CLIENT FAIL-CLOSED NOT VERIFIED`; `V2RAY REMOTE ROUTE NOT VERIFIED`; `HOSTED TUNNEL NOT STARTED`; `ORDINARY CHAT E2E NOT VERIFIED`. Continue `HOSTED_TUNNEL_ON_HOLD_BY_USER`.

**NEXT / PROPOSAL, not USER GO:** no additional unfocused theory loop required. Obtain version-pinned official native source archive by explicitly authorized offline transfer and identify an independently contained disposable Windows laboratory. A future *separately authorized* bounded implementation/proof task can cover source check, synthetic predicate tests and lab-only WFP semantics, with hard STOP gates; actual native launch, failure injection, live V2Ray traffic, production/host config and ordinary Chat E2E each require **new explicit approvals**. No main Windows direct egress or untrusted bridge allowed. The local identity scheme limits the MCP client and broker only, not the user-facing ChatGPT Desktop app nor all Windows traffic.

---

### WEB_10 — Claude 008 independent no-VM MCP egress architecture: verified report, security gates OPEN (2026-10-18)

**TASK:** `CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001` / External AI Integrations. [User-published research bundle](https://github.com/maxrus82gm-svg/ag_llm/tree/034e17f1a1aeb6ab8c3214682ee0d350a4c5ff8a/reports/CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001), commit `371` / `034e17f1a1aeb6ab8c3214682ee0d350a4c5ff8a`. **WEB_10 VERDICT: BOUNDED DOCUMENTARY/PUBLICATION INTEGRITY PASS, ARCHITECTURE RESEARCH ACCEPTED WITH CRITICAL OPEN GATES; NO OS SECURITY / NATIVE / V2RAY ACCEPTANCE.** All **9/9** report-manifest files independently matched exact published UTF-8 byte sizes and SHA-256; published Claude card's SHA-256 matches expected post-rotation SHA, B1 waiting and B2/B3 contain task statement/closeout. No host process/firewall/VM/network/native testing by Claude or verifier; no assertion that source/archive/proxy remote path is attested.

**PROPOSAL / NOT APPROVED FOR IMPLEMENTATION:** dedicated nonadmin `wua-client` Windows identity + SID-scoped persistent outbound policy, explicit local HTTP proxy, dedicated sing-box broker with no DIRECT routing; optionally separate `wua-broker` identity and address-scoped outbound enforcement; future WFP pin for one loopback broker port; native fault tests in networking-disabled Windows Sandbox. GitHub Actions limited to auxiliary synthetic Windows semantics tests and does not prove host/remote-route safety. Hyper-V VM is **not inherently necessary for operation**, but neither no-VM architecture nor Sandbox suitability has been proven on the actual host. Claude's P1 explicitly **does not satisfy exclusive-V2Ray fail-closed**: shared loopback endpoints remain accessible before the proposed L2b pin. P2 and its enforcement/proxy ownership/route remain untested.

**INDEPENDENT MICROSOFT-DOC CROSS-CHECK / CRITICAL ENGINEERING GAP:** `New-NetFirewallRule -LocalUser` and WFP `FWPM_CONDITION_ALE_USER_ID` are documented concepts, but that does **not prove** that the specific proposed all-protocol outbound SID deny *excluding* IPv4/IPv6 loopback is expressible/enforced as described on host Windows 10 Pro 19045. Windows Firewall explicit block rules take precedence over overlapping allows; documented `-RemoteAddress` syntax does not show a simple negative/exclusion operator. Thus a broad SID BLOCK plus a separate localhost ALLOW is **not an accepted design** without a verified non-overlapping address policy or correctly arbitrated WFP filters. Also prove the single-port loopback WFP pin (U2), all child/process identities, broker port owner and takeover, DNS/system-service mediated egress, firewall/BFE disable/restart semantics, broker remote DNS/dynamic IP, and exact native client binary provenance before assigning fail-closed status. Microsoft: https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule ; https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules ; https://learn.microsoft.com/en-us/windows/win32/fwp/filter-arbitration ; https://learn.microsoft.com/en-us/windows-hardware/drivers/network/filtering-condition-identifiers ; Windows Sandbox Networking=Disable documented at https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-configure-using-wsb-file . No live system proof conducted.

**OPEN DECISIONS:** threat boundary T1 (accidental client bypass) vs T2 (hostile child), whether ChatGPT Desktop itself must be in the protected contour, permissible separate nonadmin identities and a dedicated sing-box broker, stable upstream/IP and strict no-DIRECT rules, and whether even a local sandbox feature change is acceptable. **NEXT / NO AUTOMATIC USER GO:** first settle policy semantics via documentary/source + isolated synthetic test design and missing exact-source archive; any account/firewall/WFP/network/Sandbox/native creation or execution requires a new express user authorization and independent STOP/rollback gate. All prior status flags unchanged: `OS-ENFORCED EGRESS ISOLATION NOT VERIFIED`, `NATIVE CLIENT FAIL-CLOSED NOT VERIFIED`, `V2RAY REMOTE ROUTE NOT VERIFIED`, `HOSTED TUNNEL NOT STARTED`, `ORDINARY CHAT E2E NOT VERIFIED`.

---

# Архитектура внешних AI-интеграций — Codex CLI и ChatGPT MCP

## Статус документа

**ARCHITECTURAL DIRECTION / FUTURE — NOT IMPLEMENTED.**

Направления ниже архитектурно одобрены, но не являются CURRENT runtime. Документ владеет транспортом и способами подключения внешних AI-систем к Agent Runtime. Роли моделей, Model Assignment, Planner / Executor / Dredd и model/provider isolation принадлежат `11_Мультимодельная архитектура и назначение LLM.md`.

### WEB_10 — CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001 — independently bounded preflight review (2026-10-18)

**BOUNDED DOCUMENTARY/SOURCE INTEGRITY REVIEW: ACCEPT WITH OPEN GATES; TASK PARTIAL / NATIVE & VM EXECUTION BLOCKED.** User-published `reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/` on main (current pre-review publication at `391b3946b5b59150ed3bf83460f7d7a97b1b1ecf`). All **33 manifest-listed evidence files plus manifest** (34 total) found; WEB_10 independently matched UTF-8 size/SHA-256 for **18/18 selected critical artefacts**, including 434 kB `card_before.md`, source/VM/isolation plan and factual report (not an all-33 checksum audit). Published own Codex card actual SHA-256 `6df2f7e5f968840ccc71ee3dddec30bb7c0f031ffc9e7e2e630a627248f5e71f` matches `card_rotation.json`; earlier card backup SHA `fd1668b84b41aaabcc1e790db158b95280d2eec5b444d578ac54ed83af2baf0b` also matches. Independent content comparison confirms B1 = `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`, B2 contains complete original assignment and accepted USER GO amendment, B3 factual result, and prior historical B2/B3 tail is **byte-equivalent on published content**. This is an independently successful **personal-card rotation**, *not* evidence that a VM or client was exercised.

**Agent-reported 25 evidence rows: 14 PASS / 6 BLOCKED / 5 NOT RUN**, counts independently consistent with `checks.json`. This task has **0 new native/security unit-test executions**, all **16 planned native cases NOT RUN**, 0 real client/Cloudflared/VM/network/proxy changes, and 150/150 protected non-card files unchanged per Codex local hash census (not independently rehashed from active Windows). Read-only host snapshot: Windows 10 Pro x64 build 19045, i5-12400F virtualization/SLAT available; no ready VM platform/media discovered in *bounded* inventory. Preferred prospective offline boundary is separately approved dedicated lab Hyper-V Gen2 VM with **zero NIC/device/host relay**, contract I01–I12, independent host/guest egress-attempt monitoring, offline staging, exact owned rollback; backend/machine/image/observer still absent, design **PARTIAL**. Exact official v0.0.16 source tar.gz not found in Codex permitted paths; cached ZIP↔EXE byte identity checked, but source→binary attestation and dependency closure **NOT VERIFIED**. Hosted tunnel remains ON HOLD, V2Ray remote route and ordinary Chat E2E **NOT VERIFIED**.

**NEXT (proposal, no authority):** get exact official source archive with verified 239841-byte/SHA256 via user-approved transfer; identify an already isolated lab host/VM and signed-off guest Windows media; separately approve owned VM provisioning and independent isolation verification **without native execution**, then another separate USER GO for source-pinned native loopback cases. No direct Windows internet tests, live broker probes or modifications to production/V2Ray. Own-card rotation now clarified in normative 18; no agent code or shared Web Alarm/LLM12 rollout edited.

### CODEX-WUA-0-NATIVE-EGRESS-GATE-001 — independently bounded source/evidence review (2026-10-18)

**RESEARCH ACCEPTED WITH OPEN RISKS; TASK PARTIAL; OS/NATIVE GATES BLOCKED.** User-published [commit 368](https://github.com/maxrus82gm-svg/ag_llm/commit/316c1b6c76ce981e493c772d78f35937e8f220da), `reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/`: all **26 manifest paths** plus manifest exist; independent UTF-8 size/SHA-256 matched **13/13** sampled key source/test/results/design files, LF/CRLF-aware (not full 26-file SHA census). Codex's stored **22/22 PASS** is new *Python reference* policy-oracle testing only; source and results reviewed by WEB_10, but no independent Windows rerun. Evidence has **18** owned-loopback socket attempts, **1** intercepted synthetic `Popen`, **2** expected Python guard denials, 0 reported leaked resources; checks matrix **15 PASS / 6 BLOCKED / 6 NOT RUN**. The model makes a useful distinction between no dial, observed attempted-but-guard-denied dial, and a deliberately executed unregistered local-loopback direct quality case. **None establishes OS/WFP enforcement on real EXE/descendants.** No WFP changes, VM creation, native tunnel-client, Cloudflared, hosted tunnel or ordinary Chat E2E. Windows SDK WFP declarations support future design only. First proposed gate: separately authorized disposable **offline Windows VM**, independently attested to have no external/host-relay network route; full native test requires subsequent exact-source + isolation review + separate USER GO. Future operational process-scoped WFP boundary needs unresolved child identity/birth, service/port takeover, controller/BFE failure, established flow revocation, broker V2Ray outbound/DNS/DIRECT attestation and owned rollback. Current sing-box listeners 10808/10813 are not proof of HTTP/mixed protocol or remote V2Ray route; exact official `v0.0.16` source pack remains absent locally and full source→binary proof OPEN. Codex card not rotated by agent because scope only report folder; don't edit cards or LLM12/WA4-R to resolve this task. **Hosted activation remains ON HOLD**; no direct OS networking trial is permitted.

### WUA MCP / Secure Tunnel AMENDMENT 07 — bounded synthetic HTTP CONNECT→SOCKS5 review (2026-10-18)

**REFERENCE-ONLY ACCEPTED / AM07 PARTIAL, NO NATIVE/PRODUCTION GO.** [Codex 007 user-published AM07](https://github.com/maxrus82gm-svg/ag_llm/commit/e6724b15e1191c5f49ad2eb9ca6245208cdda157), `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/http_socks_adapter_20261018/`: 32 manifest-listed files plus manifest exist; WEB_10 independently byte-/SHA-256-checked 13/13 sampled key source, tests and evidence (LF/CRLF aware), reviewed implementation/test oracles and the preserved first red attempt (29 PASS / 2 ERROR) followed by recorded 32/32 and final **36/36 PASS** Windows synthetic reference cases. No independent Windows rerun. Adapter is **CONNECT-only**, one literal loopback SOCKS5 upstream, synthetic `.invalid` destination allowlist and domain ATYP=3 without local DNS. It is not a complete production HTTP proxy, does not support real destinations and was not installed. Recorded 70 loopback socket attempts, zero guard violations/remaining threads, one deliberately direct loopback mutant test which the oracle caught. Native Go `tunnel-client` had **0 network executions**, process-wide/direct-fallback safety and actual V2Ray outbound remain **NOT VERIFIED**. Current read-only listener snapshot shows 10808 and 10814, but HTTP/mixed inbound and loaded routing are not established. Official source archive remains `SOURCE PACK BLOCKED` for Codex, and exact source→EXE attestation remains open. **Parallel-card safety:** Codex reports local `000_Задачи Codex.md` B1 inexplicably changed to Claude repair task; published GitHub Codex B1 is correct. Do not publish/overwrite local card without preserving and reconciling the exact local diff. No permission to change network, V2Ray, firewall, launcher, hosted tunnel, or Claude/LLM12 files. Next candidate: scoped source-only follow-up plus separately proved native isolation/live-protocol gate.

### WEB_10 — official tunnel-client v0.0.16 exact-tag source-only preflight (2026-10-17)

**SOURCE-ONLY PARTIAL / NOT NATIVE VERIFIED / NO ACTIVATION GO.** Coordinator reviewed official annotated `v0.0.16` upstream tag → `5f99daabd4aa4a77049e6d81d54a0d8c18335397` directly through GitHub. Released `tunnel-client-runtime-source-v0.0.16.tar.gz` metadata: 239841 bytes, SHA-256 `88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0`; coordinator has **not** downloaded/verified archive bytes or proved source→installed EXE reproducibility. Exact-tag source `pkg/runtimeconfig/proxy.go` rejects explicit SOCKS URLs (requires HTTP/HTTPS); `pkg/transport/proxy.go` fixes `http.Transport.Proxy` with configured explicit proxy; without explicit config, default/environment routes may be direct. `pkg/runtimeconfig/config.go` layers global and component HTTP proxies. `pkg/controlplane/internal/tunnel_service_client.go` applies proxy to main and secret HTTP transports; `pkg/mcpclient/fxmodule.go` does likewise for HTTP MCP with special Unix-socket handling. **OPTIONAL CHILD RISK:** `pkg/cloudflared/runtime/supervisor.go` can launch independent cloudflared EXE when enabled by token/managed configuration; its external egress does not inherit a Go `http.Transport.Proxy` callback. Any Cloudflared/child usage needs its own fail-closed proof, or must be excluded by an explicitly verified mode/config. These observations do not prove whole-client fail-closed, live V2Ray remote route or compatibility of 10808 with HTTP CONNECT. AM06 native fault checks remain BLOCKED, hosted tunnel held, ordinary Chat 0/4. Next step only via a user-assigned source-only review with verified local archive handoff; no agent Git, no network/OS/V2Ray changes and no native run before enforceable isolation.

### WUA MCP / Secure Tunnel AMENDMENT 06 — bounded source provenance and safety gate, 2026-10-17

**SOURCE:** [user-published Codex AM06 c060fdedeede9aa9535d1ca142db4d88496b1295](https://github.com/maxrus82gm-svg/ag_llm/commit/c060fdedeede9aa9535d1ca142db4d88496b1295), `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/native_client_offline_20261017/`. **AM06 PARTIAL / hosted activation NO GO.** Independent GitHub review: 30 manifest-listed paths plus manifest present, 12/12 selected key file size/SHA-256 matched; code confirms static parser-only 5/5 agent PASS and a stop-only native test gate (18 case contracts BLOCKED, 0 real client process runs). The agent's 70 protected input hashes unchanged claim was not independently repeated on live Windows. The official OpenAI release metadata confirms v0.0.16 runtime-source tar.gz, 239841 bytes, SHA-256 `88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0`; annotated tag resolves to `5f99daabd4aa4a77049e6d81d54a0d8c18335397`, matching the binary's cached CLI commit literal (not build attestation). Independently read tag source `pkg/runtimeconfig/proxy.go` only allows explicit `http`/`https` proxy URL schemes, and `pkg/transport/proxy.go` pins fixed proxy on explicit route; full application/config/fallback behavior and exact source→EXE correspondence still OPEN. The observed 10808 SOCKS5 inbound does not establish HTTP CONNECT support. Real V2Ray outbound, native fail-closed, hosted tunnel and ordinary Chat E2E remain **NOT VERIFIED**; native process containment is missing. NEXT candidate: no-execution exact-source transport audit; native offline test only after separately approved and demonstrated OS/hypervisor isolation. No runtime, network, launcher, LLM12, CI or agent-card changes.

### WUA MCP / Secure Tunnel AMENDMENT 05 — bounded evidence, 2026-10-17

**NOT PRODUCTION / NO HOSTED ACTIVATION GO.** For the dedicated Web Alarm MCP direction owned by WEB_10, Codex 007 published `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/v2ray_preflight_20261017/` at [#360](https://github.com/maxrus82gm-svg/ag_llm/commit/2a263a6a75999228d542ce579048f65bb8058984). GitHub-first independent bounded review: 40/40 manifest paths present, 8/8 sampled key source/evidence UTF-8 byte-size and SHA-256 matches (with original LF/CRLF), isolated **Python reference** 19/19 Codex-reported PASS and internally consistent raw result counts; no independent Windows rerun. SOCKS5 greeting at 127.0.0.1:10808 is established; saved OpenAI PROXY GUI rule is **not** the running outbound. Eight **native Go tunnel-client** fault groups BLOCKED/NOT EXECUTED. `V2RAY REMOTE ROUTE NOT VERIFIED`, `REAL CLIENT FAIL-CLOSED NOT VERIFIED`, hosted tunnel `ON HOLD`, ordinary ChatGPT MCP calls `0/4`. The reference TLS/CONNECT model and its quality controls must never be cited as proof of native-Go or V2Ray route/fail-closed. Next candidate: exact official source and config/transport audit; isolated native offline network-fault testing only with separately proven egress containment and authorized scope. No launcher, network, DNS, firewall, proxy, server runtime, Workspace or Web Alarm shared-contract changes; those remain under their respective owners.

## 1. Два независимых направления

Документ разделяет разные механизмы:

1. локальный Codex CLI как возможный backend внутренней роли Planner;
2. внешний ChatGPT как клиент controlled Ultra tools через plugin/MCP-подобный adapter.

Эти направления имеют разное направление вызова, authority и transport. Их нельзя смешивать в одну integration model.

## 2. LOCAL CODEX CLI AS PLANNER BACKEND

### Цель

Использовать локально установленный и authenticated Codex CLI как один из возможных Planner backends.

```text
USER TASK
↓
ULTRA SERVER
↓
PLANNER ADAPTER
↓
LOCAL CODEX CLI PROCESS
↓
STRUCTURED PLAN
↓
SERVER VALIDATION
↓
TASK LIFECYCLE
↓
EXECUTOR
```

Codex на этом пути является Planner. Он не становится владельцем Agent Runtime, не получает automatic physical authority и не заменяет permissions/scopes, Persistence Contract, Dredd или Final Audit.

Предпочтительный integration mechanism — narrow local process / subprocess adapter. Будущий UI может позволять выбирать:

```text
Planner Backend:
- GigaChat
- Codex
- Off
```

При Codex backend adapter может поддерживать model, reasoning/effort, timeout, executable, config и profile, если эти параметры доступны в установленной версии CLI. Конкретные названия Codex models не фиксируются как вечный API contract: нужен discovery/config layer.

Structured output должен соответствовать существующей Planner schema. Даже при machine-readable output Server повторно применяет те же deterministic validation rules.

### Открытые вопросы

- exact CLI command contract;
- machine-readable structured output mode;
- session lifecycle;
- cancellation и timeout;
- provider usage accounting;
- model discovery;
- authentication detection;
- error mapping;
- Windows subprocess lifecycle.

## 2а. FUTURE — Codex App Server: приоритетный кандидат для агентской интеграции

**ARCHITECTURAL DIRECTION / NOT IMPLEMENTED (2026-10-10).** Встроенное управление Codex из стороннего приложения нельзя проектировать только вокруг `codex mcp-server`. OpenAI в августе 2026 объявила **именно режим Codex-as-MCP-server (`codex mcp-server`) deprecated** с рекомендацией использовать **Codex App Server**. Это НЕ означает устаревания самого MCP-протокола, а также MCP-клиента Codex для подключения инструментов.

### Разделить три маршрута, не подменяя друг другом

| Вариант | Механизм | Целевой сценарий |
| --- | --- | --- |
| **Codex App Server — основной кандидат** | `codex app-server`, двусторонний JSON-RPC (локальный stdio; другие transports только после проверки версии и безопасности), `initialize`, `thread/start`, `turn/start`, события, завершение/прерывание | Встроенный в Ultra управляемый Codex-agent: независимое исследование, план, review, bounded task |
| **Codex CLI exec — упрощённый альтернативный путь** | Отдельный `codex exec` subprocess с машинно-читаемым результатом, если установленная версия и выбранные параметры это гарантируют | Изолированная одноразовая CLI TASK, прототип Planner adapter; ограниченный session control |
| **MCP — подключение инструментов** | Codex выступает MCP client для узких Ultra tools или других разрешённых tool-серверов | Доступ Codex к определённым инструментам, а не полный lifecycle управления Codex через deprecated `codex mcp-server` |

Целевая цепочка App Server:

    Ultra Server / Agent Task Router
      → Codex App Server Adapter (local IPC, JSON-RPC)
      → Codex App Server (managed local process)
      → отдельные thread / turn / notifications / approval events
      → structured agent artifact + provenance
      → Ultra validation / consistency gates
      → пользовательское решение

**App Server — интерфейс взаимодействия с работающим Codex-agent**, а не общий HTTP-сервис в интернете, не MCP tool server, не замена model provider API и не утверждение, что Desktop-приложение автоматически предоставляет публичный inbound endpoint. Предпочитать локальный процесс и минимальный транспорт; поддерживаемые возможности и методы проверяются на установленной версии Codex, а не зашиваются в вечный контракт.

### Контракт полномочий и жизненного цикла

- Ultra может назначить **новую** ограниченную сессию Codex только после отдельного решения пользователя. Уже открытая пользователем самостоятельная локальная Codex-среда/чат не становится объектом удалённого управления по факту установки App Server.
- `thread` / `turn` привязываются к Ultra TASK, source snapshot, назначенной роли и версии артефакта; не путать internal Codex thread ID с Ultra Task/Run ID.
- Каждая сессия получает ограниченный scope, только требуемые файлы/контекст, timeout, cancellation, поток событий и сохранённый итог; отдельные errors, approvals и признаки незавершённой работы нельзя скрывать.
- **Git не требуется для чтения текущего исходника.** По общему решению пользователя самостоятельные локальные агенты Codex/Claude не обращаются к Git/GitHub без специального разрешения; историю конкретных ревизий запрашивают у пользователя/координатора. Adapter не должен неявно обходить это правило через shell/tools. При реализации проверить, можно ли надёжно обеспечить эту границу через поддерживаемые sandbox/approvals; иначе не обещать автоматическую гарантию.
- Нельзя считать встроенную безопасность Codex автоматической заменой server-owned Ultra permissions, evidence, verification, rollback и человеческих approvals. При расхождении слоёв безопасный результат — BLOCKED.
- Режим самостоятельного INDEPENDENT PLAN требует скрывать 33/чужие планы до фиксации SUBMITTED; REVIEW может читать исходный план. Техническое enforcement доступа — отдельная будущая проверка.

### Что необходимо исследовать перед внедрением

1. На актуальной **Windows** установке Codex проверить реальный запуск `codex app-server`, supported transport, JSON-RPC handshake, thread/turn lifecycle, notifications и структурированную выдачу.
2. Исследовать authorization, текущие условия использования, session recovery, cancellation, timeout, rate/usage accounting, app-server upgrades и обработку отказов.
3. Установить, можно ли использовать пользовательскую авторизацию выбранным официально поддерживаемым способом; **не делать вывода, что подписка, UI и API-биллинг полностью взаимозаменяемы**.
4. На mock/offline-first прототипе проверить ограничение инструментов, отмену, approval escalation, отсутствие неразрешённых Git-операций, секретов и side effects.
5. Только после отдельного разрешения провести ограниченный local smoke test, затем решить, нужен ли sidecar, отдельный сервис или достаточно subprocess + stdio.

Документ 11 остаётся владельцем Agent/Model Assignment и будущей координации; текущий раздел 19 — владелец transport/adapter. Реализация не начиналась, никаких существующих task-cards или локальных Codex-сессий этот контракт не меняет.

**Официальные основания для следующей реализации:**

- Codex App Server: https://github.com/openai/codex/tree/main/codex-rs/app-server
- CLI transport / App Server command: https://github.com/openai/codex/blob/main/codex-rs/cli/src/main.rs
- OpenAI notice о deprecated `codex mcp-server`: https://github.com/openai/codex/issues/11927#issuecomment (сверить конкретное сообщение от 2026-08-26; ссылка на issue https://github.com/openai/codex/issues/11927)

**Версионная оговорка:** предупреждения/детали App Server могут меняться; никакой конкретный issue, экспериментальная опция или метод не объявляется здесь обязательной неизменной частью production API.

## 3. CHATGPT ↔ ULTRA VIA PLUGIN / MCP

Это отдельная архитектура, где инициатором interaction является внешний ChatGPT или integration environment.

```text
ChatGPT
↓
Plugin / Connector / MCP-compatible integration
↓
Ultra Integration Adapter
↓
Server-owned commands / tools
↓
Ultra Runtime
```

Эта схема не означает, что Ultra скрыто вызывает web ChatGPT как API. Она не использует browser scraping, Selenium или Chrome DOM automation и не является обходом normal OpenAI API.

Возможные будущие операции:

- получить список Workspace;
- получить summary выбранного RUN;
- получить Audit export;
- прочитать конкретный RUN record;
- запустить TASK;
- получить status TASK/RUN;
- получить bounded diagnostics;
- запросить Planner / Executor / Dredd evidence.

Все write/action tools проходят Ultra server permission и safety lifecycle. Plugin не получает прямой raw filesystem access в обход runtime.

## 4. SECURITY BOUNDARY

External AI не владеет напрямую:

```text
.ultra internal storage
permissions
backup
Run Store
TaskLifecycle
verification state
```

Integration Adapter должен быть narrow, typed и server-owned. До production нужны authentication, authorization, transport security, scope control, rate limits, timeouts, audit, cancellation и explicit dangerous-action policy.

## 5. LOCALHOST / REACHABILITY

Возможность web ChatGPT напрямую обращаться к localhost Ultra не доказана и остаётся **OPEN RESEARCH QUESTION**. Перед реализацией нужно установить:

- какой transport поддерживает выбранный официальный plugin/MCP environment;
- требуется ли remote или relay endpoint;
- как выполняется authentication;
- доступен ли local connector / desktop bridge;
- какие ограничения платформы действуют на момент реализации.

Нельзя заранее утверждать, что API key не нужен: это определяется выбранным официальным integration path.

## 6. DIFFERENCE FROM MODEL ASSIGNMENT

**MODEL ASSIGNMENT:** Runtime выбирает LLM для внутренней роли.

```text
Planner → GigaChat
Planner → Codex CLI
```

**EXTERNAL INTEGRATION:** внешний AI/client вызывает Ultra Runtime.

```text
ChatGPT → Ultra MCP/plugin tools
```

Codex CLI Planner backend относится одновременно к internal role assignment и external-process transport: роль описывает документ `11`, transport — этот документ. ChatGPT plugin/MCP относится к external integration и не является Model Assignment.

## 7. FUTURE — переносимый onboarding и помощник подключений («Проводник», рабочее название)

**Статус: CONCEPT / NOT IMPLEMENTED (2026-10-09).** Не меняет текущую ветку разработки и не предполагает, что поддерживаются все провайдеры. Цель — пользователь может установить/получить приложение на другой компьютер и самостоятельно подключить собственные модели, аккаунты и инструменты; локальная конфигурация одного пользователя не становится обязательной или общей для всех.

- При первом запуске и в настройках отображается каталог поддерживаемых интеграций с фактическим статусом: `не настроено`, `нужна авторизация`, `подключено и проверено`, `недоступно/ошибка`, `не поддерживается`. Рядом показываются обнаруженные модели, роли, возможности, разрешения, доступные режимы и дата последней успешной проверки. Эти признаки нельзя выводить из одного лишь наличия записи в конфиге.
- «Проводник» — интерактивный setup-assistant (имя предварительное). Он объясняет, что нужно для конкретного provider/API, MCP tool-server, локального CLI/runtime либо Remote adapter, обнаруживает установленные компоненты, предлагает поддерживаемые способы подключения, проверяет результат и помогает диагностировать ошибки понятным языком. В качестве помощника можно использовать выбранную пользователем LLM/агента (в том числе Codex), но агент не получает секреты и не может сам себе выдавать полномочия.
- Общая система использует adapter/plugin contract с discovery/capability manifest, versioned конфигурацией без секретов, health check, ограниченными операциями и понятными ошибками. Экземпляры провайдеров, модели, MCP-инструменты и локальные CLI подключаются отдельно: наличие доступа к ChatGPT/Claude в браузере само по себе не доказывает наличие программного API-доступа или возможности автоматических вызовов.
- **Внешняя оснастка вместо списка моделей в коде.** В будущей системе ядро содержит стабильный versioned Adapter/Plugin SDK и менеджер расширений; адаптеры/настройки провайдеров добавляются, включаются, обновляются и отключаются через UI, без правки production-кода. Каждый адаптер объявляет машиночитаемый manifest: тип (LLM provider, agent runtime, MCP tool server, CLI либо Remote transport), версию протокола, способы обнаружения моделей и capabilities, необходимые разрешения, health checks и поддерживаемые операции. MCP tool server не следует автоматически считать источником LLM-моделей.
- **Динамический реестр.** После установки и настройки адаптера, проверки его совместимости, авторизации и discovery подключённые модели/агенты автоматически появляются в Model/Agent Registry с фактическим статусом. Выбор модели для роли и включение в команду конкретной TASK остаются явными отдельными решениями пользователя; новое подключение не запускает работу само. Отключение адаптера не уничтожает evidence и историю ранее завершённых TASK.
- **Доверие к расширениям.** Подключение конфигурации стандартного адаптера предпочтительнее установки исполняемого кода. Сторонние расширения проходят проверку источника/версии, явное согласие пользователя на установку и необходимые права, изоляцию, ограничение scopes/ресурсов и аудит. Установка расширения не предоставляет доступ ко всем секретам или Workspace.
- **Помощь при настройке.** «Проводник» и подключённый по разрешению пользователя локальный агент (например Codex или Claude) могут обнаруживать CLI/API/MCP, предлагать конфигурацию, запускать разрешённую диагностику и помогать устанавливать адаптер. Установка ПО, исполнение команд, сетевые изменения и выдача прав требуют подтверждения. API-ключи и токены не передаются агенту и не попадают в prompt/лог: агент видит только безопасный статус и opaque handle.
- Учётные данные изолированы от LLM: API-ключи/токены/refresh tokens вводятся человеком через защищённый UI либо получаются поддерживаемым OAuth/browser/device авторизационным потоком и сохраняются в платформенном хранилище секретов (например OS Credential Manager/Keychain), а не в проекте, репозитории, TASK, истории чата, prompt, context pack, отчётах или логах. Агенту выдаются только безопасный статус и непрозрачный идентификатор подключения. Нельзя отправлять ключи агенту «для настройки» или выводить их в диагностику; удаление/отзыв доступа — явная операция.
- «Проводник» может *предложить* или, после разрешения пользователя, выполнить безопасные подготовительные действия (например обнаружение/настройку CLI, тест доступности API/MCP); установка ПО, смена сетевых настроек, запись секретов, изменение разрешений и подключение аккаунта требуют отдельного подтверждённого действия в поддерживаемом UI/OS authorization flow. Все проверки и изменения аудируются без утечки чувствительных значений.
- Профиль интеграций — **per-user / per-installation**, с поддержкой нескольких Workspace и task-scoped выбора команды из документа 11. Допустим экспорт/импорт только несекретной конфигурации и списка желаемых провайдеров; после переноса на другой компьютер пользователь повторно авторизует подключения. Пути, имена устройств и установленные приложения не должны быть захардкожены для одного владельца.
- Запуск TASK допускается только с реально доступными участниками и явно согласованными scopes. Статус интеграции и её тестовые результаты не заменяют task-level safety, validation, verification и recovery gates Web Alarm. Для ChatGPT Web / Desktop Commander Remote сохраняется ограничение на начальный ручной импульс, пока нет подтверждённого inbound-механизма.


### 7.1. FUTURE — сетевые режимы ChatGPT MCP и мастер подключения (решение пользователя 2026-10-20)

**Архитектурная цель, НЕ реализована и НЕ разрешает развёртывание.** Web Alarm Ultra — переносимая мультимодельная платформа: разные люди подключают собственные LLM/API, локальные модели, CLI/агентов и MCP-инструменты через поддерживаемые адаптеры. Каталог и «Проводник» из раздела 7 должны разделять (а) выбор и официальную авторизацию внешнего ChatGPT → Ultra MCP/plugin, (б) выбор сетевого маршрута, (в) разрешения на конкретные операции Ultra. Обратное направление Ultra → LLM/OpenAI как model provider — **другая интеграция** (документ 11), а MCP-сервер инструментов сам по себе не является LLM-провайдером.

**Планируемые профили (не список готовых функций):**

| Профиль | Назначение и ограничения |
| --- | --- |
| `DIRECT_ALLOWED` | Прямой сетевой путь только при явном выборе пользователя, если политика организации и официальный transport это допускают. Никогда не аварийный fallback из строгого профиля. |
| `APPROVED_PROXY` | Согласованный корпоративный или иной доверенный прокси; возможности, аутентификация и безопасность отдельно проверяются для конкретной среды. |
| `STRICT_V2RAY_BROKER` | Текущая цель WUA/Codex: две отдельные неадминистративные Windows identity `wua-client` и `wua-broker`, точные SID/WFP-ограничения, выделенный брокер через V2Ray к разрешённому upstream; **никакого DIRECT, обхода через другие прокси или тихого ослабления защиты**. При недоступности брокера/V2Ray/WFP или недоказанной границе — fail-closed / BLOCKED. |

V2Ray нужен **для выбранного текущего строгого профиля**, а не для MCP вообще. Две Windows-учётные записи — пока архитектурный кандидат именно строгого профиля, не обязательная часть остальных режимов и не доказательство безопасности сами по себе. Ограничения технических SID не защищают всю Windows или обычный пользовательский ChatGPT Desktop; безопасность его процессов оценивается отдельно. Для hostile child/T2 может понадобиться более сильная граница. WFP/IPv4/IPv6/DNS/IPC/loopback port ownership/boot failure/действительный egress V2Ray остаются непроверенными, а Install/Uninstall — BLOCKED.

**Целевой UX внутри Ultra:** открыть каталог интеграций → выбрать «ChatGPT: внешнее MCP-подключение» → проверить официально доступный вариант связи/поддерживаемые возможности → выбрать сетевой профиль → увидеть точный план локальной установки, системных/сетевых изменений, разрешений и рисков → отдельно подтвердить административные действия → запустить настройку/проверки → получить подтверждённый статус либо безопасный отказ/откат. Для строгого режима допустима кнопка «Настроить MCP и брокер»; до доказанной изоляции она не должна разрешать реальную установку. Нельзя без отдельного USER GO менять рабочие учётные записи, WFP, firewall, V2Ray, маршруты и службы или нарушать работу существующей Windows.

**Авторизация личного ChatGPT:** Ultra не должна запрашивать обычный пароль от ChatGPT, хранить его в TASK/логах или передавать агенту. Использовать только официальный способ, действительно поддерживаемый конкретным каналом интеграции на момент реализации (OAuth/browser/device flow или иной подтверждённый механизм); секреты — в платформенном хранилище, агент получает только безопасный статус/opaque handle. Подписка и вход в ChatGPT Web/Desktop **не гарантируют** API/MCP-доступ. Прямое Web ChatGPT → localhost, desktop bridge, transport и реальный E2E пока остаются OPEN, `HOSTED_TUNNEL_ON_HOLD_BY_USER` неизменен.

**Инженерная граница:** текущий `CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001` — offline Discovery/Plan/static Verify/rollback planner, не готовый системный установщик. Следующий этап Codex должен отделять transport/профили от проверяемого security backend строгого режима. Реальные Windows-пробы только в отдельно подтверждённой лаборатории и по отдельному разрешению. Это уточнение **не назначает Codex задачу автоматически**.

Состав команды и назначения моделей описывает [[11_Мультимодельная архитектура и назначение LLM]]; Program/Stage, permissions и recovery — `23_Архитектура Web Alarm Workspace.md`. Это ориентир будущего onboarding, а не новый CURRENT stage и не разрешение на немедленную установку/изменение подключений.


### 7.2. FUTURE — независимые границы MCP transport, reachability и egress (архитектурная сверка 2026-10-20)

Нельзя называть одним «MCP-подключением» три технически независимых вопроса:

1. **Канал вызова инструментов:** какой официальный клиент ChatGPT и поддерживаемый им transport реально способен вызвать Ultra MCP tools (например локальный процесс или поддерживаемый удалённый endpoint); отдельно подтвердить способ регистрации, аутентификации, версии протокола и фактические capabilities. Наличие MCP-сервера на ПК ещё **не доказывает**, что конкретный обычный ChatGPT Web/Desktop способен к нему обратиться.
2. **Достижимость endpoint:** локальный `localhost`, удалённый сервер или разрешённый relay требуют разных механизмов. Исходящий V2Ray-брокер **сам по себе не публикует локальный MCP endpoint** и не даёт облачному ChatGPT входящего доступа; нельзя незаметно запускать публичный tunnel, открывать порты либо отключать firewall. `HOSTED_TUNNEL_ON_HOLD_BY_USER` сохраняется. Для любого будущего внешнего endpoint отдельно проектируются TLS, client authentication, ограниченные полномочия, отзыв доступа и защита от повторов.
3. **Политика исходящей сети (egress):** `DIRECT_ALLOWED`, `APPROVED_PROXY` и `STRICT_V2RAY_BROKER` описывают **конкретный контролируемый процесс/сетевой маршрут**, а не способ «подключить ChatGPT» и не сеть облачных процессов ChatGPT. Windows SID/WFP могут ограничивать только охваченные доказанной политикой локальные процессы; это не защита всей ОС, браузера, обычного ChatGPT Desktop или удалённого облака.

Профиль явно привязывается к connection identity, фактическому процессу/операции и выбранному route. Запись конфигурации, успешный `ping` MCP и успешный тест V2Ray — **три разных вида evidence**; ни один по отдельности не доказывает end-to-end безопасность. Для строгого профиля нельзя менять route на DIRECT/другой proxy, отключать защиту, переиспользовать credentials или расширять scopes при сбоях: статус `BLOCKED`, без скрытого fallback. Переключение профиля — новое явное решение пользователя с повторной проверкой границ. Для иных профилей поведение при отказе также определяется явной policy, а не неявным обходом выбранного маршрута.

**Отдельные критерии подтверждения перед реализацией:** (а) read-only `ping` и синтетический `read_context` из действительно выбранного обычного ChatGPT-клиента, включая client identity и audit; (б) независимое доказательство reachability и auth для фактического transport; (в) в изолированной Windows-лаборатории негативные тесты egress для охваченных SID/процессов: IPv4/IPv6, DNS, loopback/IPC, listener ownership, перезапуск, отказ брокера/V2Ray/WFP и отсутствие прямого выхода; (г) только после этих проверок — отдельное решение пользователя об установке или production E2E. Недоказанное остаётся `UNVERIFIED / BLOCKED`, а не «работает».

**Мультимодальные данные:** MCP tool capabilities и модальности LLM — разные признаки. Любая будущая передача изображений, звука или других вложений через интеграцию требует отдельно проверенного transport, typed payload, scope, ограничения размера, provenance и правил приватности; одного `MODEL ASSIGNMENT` недостаточно. Каноническая терминология — документ 11, голосовое ASR — документ 12; возможное отображение этих типов в Blueprint LLM пока только тема будущего согласования.


### 7.3. CURRENT — ограниченная независимая приёмка offline WFP и Windows Lab Gate (2026-10-21)

**Evidence source:** `main@fd908cd0fff0abe5ab91b270f89cd1f5933f4192`, `reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/` и `reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/`. Предыдущий WFP backend принят WEB_11 **только как OFFLINE source/build/test candidate**: native WFP enforcement/Windows isolation/rollback/live MCP остались `NOT VERIFIED / BLOCKED`.

**Windows Lab Gate — WEB_11 INDEPENDENT BOUNDED ACCEPTED (документально-кодовая проверка):** опубликованный пакет — 215 из 215 manifest-путей существуют; независимо пересчитанные SHA-256 **13/13** выборочных ключевых текстовых исходников, тестовых результатов и отчёта совпадают. Сопоставлены тесты, подписанная synthetic-positive фикстура, genuine red 50/51 и итоговый 52/52 PASS **по сохранённым результатам Codex**; mutation controls NIC и synthetic-trust приводят к ожидаемым 2 и 1 FAIL. Независимый повторный Windows-run **NOT RUN** (подключённого lab host нет), поэтому counts не обозначают independently rerun tests.

**Реальное состояние:** `gate_results.json` — **I01–I12: 12/12 BLOCKED**, `LAB_PLATFORM_NOT_PROVISIONED`, `HOST_CONFIG_PROOF_PENDING`, `GUEST_ISOLATION_PROOF_PENDING`, `NATIVE_WFP_EXECUTION_BLOCKED`. Для настоящей машины готовый Hyper-V/lab VM/licensed offline Windows media не подтверждены. `source/lab_gate.py` валидирует подписанное evidence и имеет исключительно data-only план, `native_execution_allowed=false`, `vm_changes_allowed=false`, `can_apply=false`; настоящая изоляция не доказана. Подписи свидетельствуют о происхождении заявленных фактов, **не об истинности host/guest sensors или физическом containment**.

**NEXT / HOLD:** пользователь должен отдельно выбрать уже подготовленный lab host и легитимное offline media; далее нужен индивидуальный USER GO на создание/controlled baseline boot disposable VM после точного host-specific review, а потом отдельный USER GO на native WFP только после I01–I12/negative controls, independent observer и recovery proof. На рабочей Windows ничего не устанавливать, не включать Hyper-V, не менять WFP/V2Ray/firewall/сеть; старые `Install/Uninstall BLOCKED`, `CanApply=false` и `HOSTED_TUNNEL_ON_HOLD_BY_USER` не изменены. ChatGPT Desktop ordinary-chat MCP E2E и route строго через V2Ray по-прежнему `NOT VERIFIED`. Документ фиксирует результат проверки, **не санкционирует новый исполнительный TASK или активацию**.

### 7.4. CURRENT — проверенные offline MCP NPFS и выделенный broker (2026-10-24)

**NPFS:** `CODEX-WUA-0-MCP-NOTCP-NPFS-001`, source `main@1147d283674f60ad94dd0be4b26f49e751523669`: independent WEB_11 GitHub source/evidence read, **1404/1404** published paths, **10/10** selected hashes; Codex stored 24/24 NPFS, 63/63 MCP, 24/24 security, independently rerun Windows NOT RUN. Local path: MCP SDK ↔ STDIO C# relay (no Python asyncio on C) ↔ local authenticated Windows Named Pipe ↔ U server-owned MCP SDK/synthetic WebAlarmApi. Finite observation ≠ permanent OS no-network; cross-SID, WFP, real U authority not demonstrated.

**V2Ray broker offline:** `CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001`, source `main@1324f544c7d3fef6c0a80bf71f7460f372f6950d`: independently confirmed **617/617** manifest paths and **12/12** selected hashes; Codex saved 33/33 broker, 63/63 MCP and 24/24 security results, Windows rerun by verifier NOT RUN. Disabled v1 schema/preflight and single-process Python CONNECT/egress loopback fixture exercise fail-closed DIRECT/owner negative oracles; it is not a native V2Ray executable or real B-owned SID socket. Codex initial failures preserved. `can_apply=false`, `can_start_tunnel=false`.

**F2 and native gates:** historical v2rayN used sing-box.exe, not a confirmed V2Ray Core. `ENGINE_VERSION_SOURCE_BLOCKED`, `ENGINE_CONFIG_COMPATIBILITY_BLOCKED`: exact source/version/config behavior unknown. Real B egress owner, C/B identity, WFP IPv4/IPv6/DNS/IPC, protected credentials, secure MCP tunnel and ordinary-chat tools remain NOT VERIFIED/BLOCKED; `HOSTED_TUNNEL_ON_HOLD_BY_USER`. No B-wrapper → host-user SOCKS equivalence and no DIRECT fallback. Next obtain bounded read-only locally approved exact engine metadata and decide sing-box vs V2Ray with user; host-native tests only after isolation and separate GO. No runtime/Windows changes approved. Permanent verdicts in 06 and Codex B4.


### 7.6. HISTORICAL WEB_11 — sing-box v1.13.4 source-only и непроверенная тогда зависимость (2026-10-24)

Source: `CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/amendment01` on `main@e0c89b3536cb030edc4fa905a8e00f1047788c4c`. WEB_11 independent bounded review: **76/76** manifest-listed paths, **7/7** selected SHA-256, **30/30** (11 new+19 pure regression) from Codex's stored Windows evidence, **independent Windows/Go test NOT RUN**. Codex separately downloaded one official source ZIP, SHA256 `ecf6cbedda4c35073656c902722b74daaf9fb89bb6f52de9ed0bdfd3a7729c1c`, 1013 regular files, outside repo. WEB_11 did **not** access this ZIP; source provenance evidence from Codex is bounded, not a detached signature. WEB_11 independently inspected official upstream GitHub tag/revision `SagerNet/sing-box@d09182614c7778c1e0f51d990635c5d4249c437e` for `go.mod`, `box.go`, outbound manager, HTTP inbound, router, UoT and CLI config loader.

**Security findings:** missing/empty explicit outbound is not strict DENY: a default DIRECT implementation exists; unmatched routes can reach default outbound. TCP HTTP inbound delegates parser/CONNECT/auth to external `github.com/sagernet/sing` and `uot` can redirect logical traffic to packet routing; physical TCP by itself does not prove TCP-only requested operations. Local DNS and further conditional route/health/remote-rule/NTP/ECH/Tor/REALITY paths need exact strict-subset exclusions or separate examination. Optional source paths are **not** proof of active working user config. CLI can load multiple configs, default file, external JSON merge and reload. Source-level error return on one ordinary dial path is not global no-fallback guarantee.

**Historical blocker as of WEB_11:** `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde` from pinned official go.mod; expected go.sum module ZIP checksum `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`. HTTP CONNECT/auth and JSON implementation remain **source-incomplete** until this specific module source is acquired and inspected under a separate USER GO. Choosing sing-box and altering current `engine.family=V2Ray` is a user decision **after** compatibility review; no automatic core switch. Even reviewed source/native schema cannot prove actual B-owned egress, C/B Windows identities, WFP no-DIRECT, privileged isolation or hosted ChatGPT tools. `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`. NEXT: exact versioned source-only module acquisition and scoped negative review, then engine selection and isolated OS/native testing with separate GOs. Full verdict in 06/B4.


### 7.7. WEB_12 / terminal bounded sing module source review (2026-10-25)

**Task** `CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001`, user-approved terminal PARTIAL, `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`. **TERMINAL PARTIAL / INDEPENDENT BOUNDED SOURCE & EVIDENCE ACCEPTED**, not native/software activation permission.

Codex 007: exact source-only `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`; one GET via explicitly approved HTTP CONNECT according to agent audit, 0 redirects/fallback, 322 module files, ZIP raw SHA-256 `dfb3b8c7cbc603602c6cf453161d319209e5610477e1118354dd449bd9409659`, Go module h1 `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`. Baseline 30/30, first RED 49/50 (Windows ZIP name normalization; preserved), intermediate 50/50, final **51/51 PASS** (11 source +19 pure +21 dependency), per Codex logs; not independently rerun on Windows.

WEB_12: `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; **87/87** published manifest paths bytes+SHA independently matched (LF/CRLF-aware); **6/6** independently fetched official `SagerNet/sing@ed51f65fbfde` source files and **33/33** locators match; Go module h1 recomputed from **published SHA values of 322 members**, not independently from original ZIP. Stored FAIL/final result and tests inspected. Physical egress/installed executable/ZIP itself, native Go/Windows/WFP, C/B SIDs/sockets, no-DIRECT proof and ordinary ChatGPT MCP E2E **NOT VERIFIED**.

Source risks: `users=[]` disables proxy authentication; 407/error logs can expose username/password or `Proxy-Authorization`; CONNECT sends `200` before dial/route; HTTP Upgrade/plain alternatives and X-Forwarded-For source override; URL-safe-vs-standard Basic Base64 ambiguity and ignored port-parse error; permissive JSON duplicates/null/case/merge/reload; prior default DIRECT, local DNS/UoT/optional other egress; Go stdlib/x/sys source/native behavior incomplete. No proven native bypass asserted. `engine.family=V2Ray` unchanged, `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`; no install/engine switch/proxy/system activation.

**Required strict-admission follow-up (proposed, not assigned):** verify missing/empty auth is denied, prevent credential disclosure at every error/log boundary, reject HTTP Upgrade/plain if strict CONNECT-only, parse exact authority/port safely, enforce protected single canonical config (reject duplicates, unknown defaults and unauthorized merge/reload), reject DIRECT, host DNS, IPv6/UDP/UoT and all secondary/conditional egress unless explicitly audited. Reuse `integrations/wua_chatgpt_mcp/broker.py` and `security_contract.py` plus existing test suites; no second Go parser. Test/source rules alone never attest physical egress/WFP. Read full report and gap matrix `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/`. Historic §7.6 above remains WEB_11 state, including its then-missing dependency, not a current blocker. Engine decision pending user; held tunnel/disabled application remain.

## 7а. FUTURE — Claude как подключаемая LLM и независимый агент Ultra (2026-10-10)

**Статус: CONCEPT / NOT IMPLEMENTED / NO AUTO-EXECUTION.** Этот раздел сохраняет предложенную пользователем возможность включать Claude как второй независимый «мозг»: для отдельного планирования, архитектурного анализа, code review, поиска альтернатив и последующего сравнения результатов. Сейчас Claude Desktop/Code и Codex используются пользователем в самостоятельных локальных рабочих средах; это не означает наличия у Ultra автоматического канала вызова этих приложений. Текущие GigaChat Model Registry/Assignments остаются единственным подтверждённым provider-контуром.

### 7а.1. Четыре разных технических объекта

| Слой | Назначение | Что НЕ следует предполагать |
| --- | --- | --- |
| **Claude model / Messages API** | Отдельный model provider для конкретной роли внутри Ultra через Anthropic SDK/HTTP | Сам API-вызов не является готовым локальным coding-agent с правами на файлы |
| **Claude Code CLI / Claude Agent SDK** | Отдельный локальный agent runtime со своим agent loop, сессиями и инструментами; узкий управляемый адаптер к Ultra | Авторизация Claude Desktop/веб-подписка автоматически не предоставляет право встроить этот runtime в Ultra |
| **MCP tool server / client** | Типизированный транспорт инструментов между совместимым host/client и сервером инструментов | MCP-сервер не равен LLM-провайдеру и сам по себе не запускает Claude |
| **App / connector host / local sidecar** | Интеграционное приложение или локальный сервис, управляющий процессом, состоянием подключения, запросами и ответами | Наличие desktop-приложения не означает существования публичного inbound API или «app server» для внешнего управления |

Для каждого установленного варианта обязательны capability discovery, версия поддерживаемого контракта, безопасная авторизация, health check и проверенное доказательство реального вызова. Не считать одну запись в настройках подключённым и работающим агентом.

### 7а.2. Направление A — Ultra вызывает Claude как LLM provider

    Ultra Server / Role Assignment
      → Anthropic Provider Adapter
      → официальный Messages API / Anthropic Client SDK
      → структурированный role result
      → Ultra validation, evidence и lifecycle

Это возможный путь для внутреннего Planner, Reviewer, Verifier либо иной явно разрешённой роли; он подчиняется модели назначения из документа 11. Agent Runtime, инструменты, контекст, permissions, verification и переходы остаются у Ultra. Нужно исследовать модельные capabilities, структурированный ответ, tool-use, retry/timeout/cancellation, usage и rate-limit accounting, версионирование, стоимость и необходимость отдельного API-доступа.

**Не смешивать claude.ai / Claude Desktop subscription с Claude API credentials и биллингом.** Путь API требует официально поддерживаемой авторизации и может иметь отдельную тарификацию. Модель и доступные функции определяются discovery, а не заранее зашитым названием модели.

### 7а.3. Направление B — Ultra взаимодействует с локальным Claude-агентом

    Ultra Server / Agent Task Router
      → локальный Agent/Process Adapter
      → Claude Code CLI (headless) ИЛИ Claude Agent SDK
      → отдельная bounded agent session
      → сохранённый вариант, findings, structured result
      → Ultra consistency/permission gates и человеческое решение

Claude Agent SDK и CLI предоставляют собственный agent loop; это **агентский backend**, а не ещё одна запись в списке «модели». Возможный транспорт — ограниченный subprocess со структурированным stdout/streaming на Windows либо отдельный локальный sidecar, если подтверждены его реальная необходимость и безопасный контракт. Конкретный CLI синтаксис, лицензия/условия использования в стороннем приложении, способы авторизации, Windows session/termination, изоляция инструментов и error mapping требуют отдельного feasibility check.

**Самостоятельные локальные Claude и Codex сохраняют своё положение исполнителей пользователя:** их рабочие папки и собственные TASK не превращаются автоматически в общий runtime, а установка или запуск адаптера не создаёт разрешение вмешиваться в их существующие сессии.

### 7а.4. Направление C — Claude использует предоставленные Ultra инструменты через MCP

    Claude Desktop / Claude Code (как MCP host/client, если версия поддерживает)
      → ограниченный Ultra MCP tool server
      → typed server-owned tool/API
      → Ultra permissions / TASK state / audit

Это обратное направление: **Claude обращается к Ultra**, а не Ultra вызывает Claude как модель. MCP server может работать локально через stdio либо по Streamable HTTP с проверенной аутентификацией и сетевыми ограничениями. Если используется HTTP, не открывать опасные локальные endpoints наружу по умолчанию; требуются Origin validation, bind policy и разрешения. Наличие у Claude поддержки подключения MCP-сервера не доказывает возможности самопроизвольно вызывать его через внешний API.

Для Ultra → Claude через MCP необходим реальный отдельно предоставленный **Claude-side tool/agent service**; стандартный MCP tool server сам по себе не предоставляет управление Claude model. Не проектировать «вход в Claude Desktop» на неподтверждённом интерфейсе.

### 7а.5. Контракт совместной работы агентов и Круглого стола

- User назначает участника и роль; подключение в каталоге само по себе **не** запускает агента и не даёт разрешение на TASK.
- Одна задача может иметь исходный план и до двух **необязательных** альтернатив с отдельными авторством, контекстом, revisions, provenance и критериями качества. Постоянные оболочки 33.1/33.2 — предмет документационного согласования Round Table, а не реализованный Ultra feature.
- Для INDEPENDENT PLAN выдать одинаковые утверждённые решения и bounded evidence, **не раскрывая базовый план или чужие варианты до SUBMITTED**; REVIEW вправе видеть исходный план. Сравнение и reconciliation — отдельная контролируемая операция; решения и PLAN APPROVAL принадлежат пользователю.
- Передавать роли только необходимые части контекста, версию источника, значимые поправки/unresolved и ограничения. Полная история другого агента и его hidden reasoning не являются обязательным shared context.
- Результат каждого агента — проверяемый артефакт (TASK graph / mappings / risk / acceptance либо findings) с ограничениями достоверности; голосование моделей не подменяет проверку и решение человека.
- Локальные агенты читают текущие исходники напрямую. Если требуется история Git, они запрашивают конкретный диапазон/файлы у пользователя или координатора ChatGPT через действующий ручной канал; **самостоятельное использование Git не входит в полномочия по умолчанию**. Нормативную сверку этого общего правила с документом 18 провести отдельным документационным проходом; здесь не объявлять старые противоречивые инструкции уже исправленными.

### 7а.6. Сетевая политика, безопасность и переносимость

Для каждого подключения нужны явные per-user/per-installation network policy, transport endpoint, timeouts, cancellation, проверка доступности и **fail-closed** при обязательном маршруте через proxy. Не переносить индивидуальную сетевую конфигурацию или пути одного ПК всем пользователям Ultra. Browser proxy сам по себе не обеспечивает такой же маршрут для CLI/SDK или локального sidecar: проверять реальный исходящий канал отдельно до любого сетевого теста.

Доступы — least privilege: контролируемые scopes, read-only по умолчанию на стадии исследования, consent для write/execute, отдельные permissions и audit. Credentials остаются в защищённом хранилище; в prompt, результатах MCP и общих контекстах — только opaque connection handle. Любой опасный external-tool вызов проходит те же server-owned gates. Никакого автоматического изменения Git, чужих рабочих пространств или сетевых настроек.

### 7а.7. Маршрут исследования и верификации — без запуска сейчас

1. Сначала зафиксировать нужный сценарий: **LLM role**, **локальный agent process** или **внешний MCP client**; не пытаться реализовать все три одновременно.
2. Сверить официальные API/SDK/CLI/MCP contracts, лицензирование интеграции, реальные методы auth, доступные provider capabilities и отдельную стоимость.
3. Составить capability/permissions matrix и тесты: discovery, mock structured plan/review, errors, cancel, secret redaction, network fail-closed, ограничение scope, неизменность пользовательского approval.
4. Затем по отдельному разрешению — минимальный изолированный proof of concept с mock/offline-first и лишь после его принятия ограниченный сетевой smoke test.
5. Только на основании подтверждённых возможностей выбрать production transport, onboarding и UI через существующий «Проводник»; все новые команды и изменения кода — отдельные TASK с независимой приёмкой.

**Официальные ориентиры для следующей feasibility-проверки (источники, не гарантия установленной поддержки):**

- Claude API: https://platform.claude.com/docs/en/api/overview
- Claude Agent SDK: https://code.claude.com/docs/en/agent-sdk/overview
- Claude Code CLI: https://docs.anthropic.com/en/docs/claude-code/cli-usage
- MCP transports: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

**Граница владения:** документ 19 — transport/adapters/onboarding; документ 11 — Model Registry, назначение моделей, агентские роли и возможный Coordinator; документ 13 — фактические stage/verification/permissions; документы 28 и 33 — пока ручной Round Table и правила альтернативных планов. Этот раздел сохраняет концепцию, но не предоставляет агентам новых полномочий и не меняет CURRENT состояние.

## 7б. WEB ALARM ULTRA — ChatGPT single Planner, Codex relay and durable handoff (2026-10-16)

**CURRENT USER OVERRIDE / 2026-10-17 (permissions, not a new implementation):** проектируемый в этом разделе Codex Relay и исторический разовый smoke сообщения в ChatGPT **не дают Codex или Claude постоянно действующего доступа к ChatGPT**, самостоятельного права отправлять сообщения, запускать автоматическую обратную связь или пользоваться GitHub. Основной действующий обмен результатами: локальные отчёты/безопасные evidence в `ag_llm` → обычно пользователь commit/push → ChatGPT проверяет опубликованный GitHub SHA и ведёт общую документацию. Любой агентский Git/push или адресный relay требует отдельного явного разрешения пользователя для TASK/AMENDMENT; правила `DOC-GIT-01@1`, `DOC-LOCAL-REPORT-HANDOFF-01@1` (18). Ни схему FUTURE, ни исторический smoke не считать выданными полномочиями.

**Решение пользователя / архитектурная цель (USER DIRECTION / DESIGN, НЕ IMPLEMENTED):** в будущем контуре **Web Alarm Ultra единственным основным Planner является ChatGPT** в обычном Desktop-чате. Не назначать Codex, Claude или GigaChat взаимозаменяемыми основными планировщиками этого контура по умолчанию. Codex и Claude работают как самостоятельные исполнители / независимые ревьюеры по назначенным задачам; GigaChat Ultra и другие модели остаются доступными для других ролей, исследований и чатов. Если ChatGPT недоступен, Web Alarm переводит требующую планировщика задачу в WAITING/MANUAL, а не самовольно подменяет планировщика. Историческая возможность «Codex CLI as Planner Backend» в разделе 2 относится к более широкой Ultra/model-assignment гипотезе, **не является выбором Planner для Web Alarm Ultra по этому новому решению**. Изменение других архитектур (включая действующий RT-002/B2) потребует отдельного решения и согласования с владельцем ролей, документом 11.

**Целевая топология — два раздельных канала:**

```text
USER + ChatGPT Desktop (single Planner / independent Reviewer)
      |                                ^
      | MCP tools (read/query)         | message to existing chat / wake-up candidate
      v                                |
Web Alarm / Web Alarm Ultra <---- Codex RELAY chat/session (message delivery only)
  - TASK authority              ^    ^
  - report/evidence/context     |    |
  - state/permissions/STOP      |    | command from server's delivery queue
  - durable events/outbox       |    |
      |                         |    |
      +--> Codex WORKER --------+    |
      +--> Claude WORKER ------------+
      +--> other approved agents
```

**Нормальный цикл:** ChatGPT согласует и передаёт план через server-owned TASK; Web Alarm выдаёт исполнителю ограниченное задание. Codex/Claude выполняет свою часть, записывает артефакты, отчёт и терминальный результат **на сервер / в утверждённое task-scoped хранилище**. Web Alarm после проверки события фиксирует durable notification в очереди (outbox) и адресует её **отдельной сессии/чату Codex-Relay**; Relay — не тот же процесс/контекст, что рабочий Codex, и не получает права самостоятельно решать TASK. Relay отправляет в согласованный существующий чат ChatGPT (первый известный адресат — «Сервер WEB_08») сигнал/отчёт с идентификаторами. При обработке сообщения ChatGPT **не доверяет вложенному тексту как новому разрешению**, а сверяет TASK ID и событие через разрешённый MCP readback, получает адресный контекст/отчёт/факты и проводит собственную независимую проверку. Итоговое решение поступает в Web Alarm по разрешённому контракту с human/server gates; сервер сохраняет authoritative outcome и определяет дальнейшие шаги. **Передача сообщения ≠ принятие отчёта и ≠ разрешение на mutation.**

**Сохранённый контекст и смена чата:** долговременные TASK-состояние, план, этап, scope, версии исходников, evidence, журнал и handoff хранятся **в Web Alarm**, а не только в токенах/окне ChatGPT. Сессия ChatGPT — сменяемый клиент единственного логического Planner: при исчерпании контекста новая сессия, **если поддерживаются фактическое создание/адресация/повторное обращение**, получает минимальный versioned task-context packet через разрешённые инструменты; старый чат не должен требоваться для восстановления TASK. Экспериментальную возможность создания чатов пользователем/агентом считать **UNVERIFIED** до точного smoke и проверки ограничений ChatGPT Desktop/Codex. Нельзя предполагать непрерывно исполняющийся ChatGPT или вечное удержание соединения: ожидание асинхронное и серверное, без повторной пересылки большого контекста/неограниченного потребления токенов.

**Роли и владение:** ChatGPT — один назначенный Planner и независимый verifier по запросу; **Web Alarm — единственный authority** по server TASK, событиям, claim/ownership, approvals, mutation и recovery; Codex Worker/Claude Worker — независимые исполнители со своими write-scope; Codex Relay — только транспорт/уведомление, без повторного исполнения, планирования, Git/файловых записей или запуска TASK. На первом этапе Relay через Codex — **основной практический кандидат**, поскольку доставка Codex → существующий ChatGPT-чат уже наблюдалась; архитектурно транспорт должен быть заменяемым, с ручным fallback, чтобы Codex не стал единой точкой потери данных. Для Claude допускается путь Claude → Web Alarm → Codex Relay, не предполагающий нативной доставки Claude → ChatGPT.

**Минимальный проектируемый event envelope (схема-кандидат, NOT FINAL):** `event_id`, `task_id`, `run_id`/iteration, `event_type` (например, `REPORT_READY_FOR_REVIEW`), `source_agent`, `report_ref`, `evidence_ref`, `source_revision`, `task_revision`, `target_planner_session_ref`, `created_at`, `scope_ref`, `delivery_status`, `ack_ref`. Адрес, имя файла для записи, ссылка на GitHub и требуемое действие **проверяются сервером по разрешённым scope/ACL и контексту TASK**, а не принимаются из произвольного сообщения. В чате лучше передавать короткий идентификатор/уведомление плюс читабельное summary; полный отчёт — durable и доступен по ref. По отдельному пользовательскому решению Relay может пересылать полный отчёт для удобства, но с лимитом размера, секретов, повторов и расхода контекста.

**Безопасность и надёжность до автономного цикла:** 
- server-owned durable outbox/inbox, состояния `QUEUED → DELIVERED? → ACKNOWLEDGED → REVIEWED / BLOCKED`; недоставленное сохраняется и может быть вручную обработано; delivery/ack не равны выполнению review;
- строгая корреляция `task_id/event_id/revision`, идемпотентность, дедупликация, bounded retry/backoff, timeout, operator STOP, запрет бесконечных циклов «агент разбудил агента»;
- разделение рабочих сессий и Relay, квоты, разграничение Git/Workspace, логирование исходного transport, проверяемая provenance/авторизация; имя отправителя и текст в чате не гарантируют идентичность;
- если изменился ChatGPT chat/session ID, task revision, отчёт или источник прав, старый сигнал нельзя вслепую исполнять; сервер указывает актуальный locator, а контекст читается заново;
- управление несколькими Codex/Claude TASK через server claim/изоляцию и запрет конфликтующих параллельных write-scope; relay не расширяет исходные права агентов.

**Что уже наблюдалось (BOUNDED SUCCESS):** пользователь инициировал передачу из AG LLM через Codex в **существующий** ChatGPT-чат «Сервер WEB_08»: сообщение получено, ChatGPT ответил; последующее поручение привело к GitHub-документированию результата в 34. Это доказывает коммуникационный smoke на имеющейся конфигурации, **но не подтверждает** точный транспорт/identity, server-triggered outbox, отдельный relay-chat, создание новых чатов, автоматическую доставку после любой TASK, работу во время недоступности Desktop, гарантированное пробуждение idle/закрытого чата, MCP readback или unattended двухсторонний цикл. Текущий документ описывает **будущую интеграцию, не уже действующий механизм**.

**Маршрут исследования после отдельного GO:** (0) проверить поддерживаемость локального ChatGPT Desktop MCP read-only tools и права текущей конфигурации; (1) изолированно проверить Codex Relay как отдельную сессию, адресацию существующего чата и реальный delivery ack; (2) изолированно проверить `event_id/TASK ID → read_report` и handoff context, в том числе закрытие/смену чата; (3) negative tests: недоставка, повтор, неверный адресат, устаревшая revision, фальшивая авторизация, параллельные сдачи, долгий простой; (4) только затем отдельная Task на durable server outbox/controlled review loop. **Никаких изменений production, новой CODEX/CLAUDE TASK, rollout, git-операций локальных агентов или платных API** эта запись не разрешает. Не менять активные WEB_08/WA4-R gates. 

**Согласование владельцев:** данный раздел 19 — владелец integration/transport/relay-contract; документ 11 — role/model assignment (внести в будущем только после отдельного согласования), 23 — Web Alarm TASK authority, 24 — исполнение, 37 — дорожная карта перехода, 34 — текущий тактический status и первый smoke. Параллельные возможности Blueprint LLM — FUTURE, типизированный блок события/релэя можно исследовать позднее без реализации редактора сейчас.

---

## 8. Статус и следующий шаг

```text
CURRENT: NOT IMPLEMENTED
APPROVED ARCHITECTURAL DIRECTION: YES
```

Перед реализацией:

1. завершить текущий documentation/context checkpoint;
2. отдельно исследовать Codex CLI command/schema capabilities;
3. реализовать minimal Planner Adapter prototype;
4. отдельно исследовать официальный ChatGPT plugin/MCP transport;
5. только после этого проектировать production bridge.

## Связанные документы

- `00_Главная - карта проекта.md` — HUB;
- `08_Старт.md` и `18_Регламент сопровождения документации.md` — routing;
- `11_Мультимодельная архитектура и назначение LLM.md` — Model Assignment и role isolation;
- `13_Архитектура оперативной верификации и контроля выполнения задач.md` — Planner / TaskLifecycle / verification authority;
- `03_Чаты, проекты и контекст.md` — Workspace, Task/Run identity и Run Store.
