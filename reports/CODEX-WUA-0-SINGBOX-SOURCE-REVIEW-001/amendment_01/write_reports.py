"""Factual source-review assembly from the pinned one-time local ZIP."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
A=Path(__file__).resolve().parent;OUT=A.parent;REPO=OUT.parents[1];PKG=REPO/'integrations/wua_chatgpt_mcp';sys.path.insert(0,str(PKG))
import singbox_source_review as review
ROOT=Path('M:/WUA_SOURCE_REVIEW/sing-box/v1.13.4/source/sing-box-1.13.4')
FINAL='runs/source-20261024-213332-1493e644'
def load(p):return json.loads(p.read_bytes())
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def doc(name,text):(OUT/name).write_text(text.strip()+'\n',encoding='utf-8')
extra=[]
def ref(path,needle):
    raw=(ROOT/path).read_bytes();text=raw.decode();line=text[:text.index(needle)].count('\n')+1
    extra.append({'path':path,'line':line,'locator':needle,'file_sha256':hashlib.sha256(raw).hexdigest()})
    return '`'+path+':'+str(line)+'`'
def locus(key):
    p,f,anchors=review.LOCI[key];return ref(p,anchors[0])+' / `'+f+'`'
def main():
    download=load(A/'evidence/download_receipt.json');run=load(A/FINAL/'result.json');assert run['collected']==run['passed']==30 and run['failed']==run['errors']==0
    assert download['sha256']==review.ZIP_SHA
    loc={k:locus(k) for k in review.LOCI}
    facts={'task':OUT.name,'status':'PARTIAL / RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11','amendment':1,'final_run':'amendment_01/'+FINAL,'source_tests':11,'existing_pure_regression':19,'final_result':run,'one_source_archive_downloaded':True,'source_archive_path':download['archive_path'],'source_archive_sha256':review.ZIP_SHA,'source_revision':review.REVISION,'source_file_function_locators':'amendment_01/evidence/source_locations.json','source_excerpts':'amendment_01/evidence/source_excerpts.json','initial_blocked_report_preserved':'amendment_01/blocked_report_before_amendment.md','initial_unexpected_test_failures':0,'OFFICIAL_SOURCE_REVISION':'VERIFIED / BOUNDED HTTPS ZIP ORIGIN + ZIP COMMIT COMMENT; NOT CRYPTOGRAPHIC ARCHIVE SIGNATURE','HTTP_CONNECT_SOURCE':'UNVERIFIED / DELEGATED PARSER DEPENDENCY NOT SUPPLIED','STRICT_ROUTE_SOURCE':'CONDITIONAL PRIMITIVES REVIEWED / FULL STRICT CONFIG UNVERIFIED','HIDDEN_EGRESS_PATHS':'BOUNDED REVIEW / GLOBAL ABSENCE AND DEPENDENCIES BLOCKED','ENGINE_SELECTION':'PENDING_USER','B_EGRESS_OWNER':'NOT_VERIFIED','WFP_NATIVE_ENFORCEMENT':'NOT_VERIFIED','HOSTED_TUNNEL':'ON_HOLD_BY_USER','ORDINARY_CHATGPT_E2E':'NOT_VERIFIED','engine_runs':0,'Go_or_dependency_builds':0,'dependency_downloads':0,'network_tests':0,'Git_commands':0,'other_GitHub_operations':0,'can_apply':False,'can_start_tunnel':False,'native_config':None}
    put(OUT/'test_results.json',facts)
    doc('report.md',f'''
# CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001 — USER GO amendment 01

**2026-10-24 / Codex007 — PARTIAL / BOUNDED SOURCE REVIEW; RESULT READY / AWAITING WEB_11.**

Предыдущий SOURCE_BUNDLE_REQUIRED снят дополнительным разрешением пользователя на один официальный source ZIP. Initial BLOCKED report/manifest и checks сохранены в `amendment_01/`; прежняя архивная запись не переписана. B1 уже был освобождён; продолжение санкционировано прямым USER GO, сохранённым в `amendment_01/USER_GO.md`.

## Полученный материал

С [официального релиза v1.13.4](https://github.com/SagerNet/sing-box/releases/tag/v1.13.4) получен один source ZIP по GitHub archive URL с единственным redirect на codeload. Файл: `{download['archive_path']}`. Получен `{download['received_at']}`, **{download['bytes']:,} bytes**, SHA256 **`{review.ZIP_SHA}`**. ZIP comment **`{review.REVISION}`** совпал с заданной полной revision. Распаковано **1013 файлов / 3,870,530 bytes** вне репозитория; CRC, archive paths, duplicate/case collisions, symlinks/reparse destination и запрещённые executable members проверены до записи. Исполняемые файлы отдельно не скачивались, зависимости не устанавливались.

Это bounded chain of custody: официальный HTTPS endpoint, TLS verification, requested exact version, archive revision comment, CRC и фактический package hash. **Tag mapping не единственное основание**, но ZIP comment тоже не цифровая подпись. Detached signature архива, независимый официальный package digest и source→установленный EXE reproducibility не проверены. Go minimum в go.mod —1.24.7; ранее embedded build toolchain1.25.8 не противоречит minimum, но не доказывает воспроизводимость.

Downloader использовал только существующий literal127.0.0.1 HTTP CONNECT proxy10808, с явным HTTPS tunnel и без NO_PROXY/DIRECT fallback. Это не доказательство actual remote V2Ray route или B-owned egress. Ни proxy settings, ни рабочий sing-box не менялись. Receipt/время/URL/redirect/hash — `amendment_01/evidence/download_receipt.json`.

## Основные source findings

1. **Пустой outbound не fail-closed:** default factory создаёт DIRECT ({loc['direct_default']}); при отсутствии explicit final выбирается первый outbound ({loc['manager_default']}). Unmatched connection использует default ({loc['selected_outbound']}). Нельзя принимать empty/minimal config за strict profile.
2. **Есть явные route/reject primitives** и возврат ошибки при missing selected outbound. В просмотренном обычном connection path ошибка dial закрывает соединение ({loc['connection_failure']}); это не глобальная гарантия отсутствия fallback у всех protocol/group/transport/dependencies.
3. **HTTP inbound — TCP listener с delegated handler:** {loc['http_dispatch']}. Реальный HTTP parsing/CONNECT/auth расположен во внешнем `github.com/sagernet/sing`, отсутствующем в единственном разрешённом архиве. Полный HTTP_CONNECT_SOURCE_SUPPORTED **не объявляется**.
4. **TCP listener не исключает logical UDP:** HTTP использует `uot.NewRouter`, а UoT callback переводит поток в packet routing ({loc['uot']}). Для strict intent нужен TCP-only route admission плюс reject остатка, не только запрет UDP socket в Windows.
5. **Есть дополнительные сетевые пути:** local DNS default, resolver selection, health/urltest, remote ruleset fetch/update, NTP, ECH DNS, Tor helper и REALITY cover HTTP на существующем conn. Это conditional features, а не утверждение, что они включены в рабочем config. Подробности — `network_egress_review.md`.
6. **Config loader умеет больше одного файла:** default config.json, stdin, -c array, -C directory, sort/merge и SIGHUP reload. Параметры и protected config roots нужно закрепить отдельно; source/config hash не проверяется движком как наша installation authority.

Принцип «один B-owned process принимает CONNECT и делает actual socket к R:Q» не опровергнут просмотренным обычным in-process path. Пример Trojan outbound отделяет proxy server address от logical destination, но protocol **не выбран**, TLS опционален, dependencies не замкнуты. Same PID/token/OS security по source не доказываются. Текущий `engine.family=V2Ray` **не менялся**.

## Реализация и проверки

Добавлены только `integrations/wua_chatgpt_mcp/singbox_source_review.py` и `tests/singbox_source_review_suite.py`: release-pinned source tripwires и negative controls с reuse common/broker. Это не Go parser/interpreter, не второй broker и не native schema validator.

**30/30 PASS: 11 новых source checks +19 прежних pure broker regression; FAIL/ERROR/SKIP0.** Final run `{FINAL}` внутри amendment01. Проверяются revision/archive/hash/source-file drift, missing required files, critical go.mod/go.sum version/checksum, top-level option field addition, config-default/merge drift, hidden-path anchors, family/secondary proxy refusal и сохранение blocked gates.

Два адресных mutation controls: (a) explicit selected outbound заменён на literal unapproved в **копии Go source** — lexical source-contract отказ; (b) default DENY→DIRECT в **существующем synthetic broker intent** — старый validator отвергает. В нативном Go empty default **уже DIRECT**; эти tests не выдают его за безопасный и Go не исполняют. Source hashes плюс review защищают known snapshot, а lexical anchors сами по себе не универсальный анализ semantics/веток.

Initial source runs оба30/30 PASS сохранены; второй после удаления unused imports, без ослабления oracle. Ошибки навигации к несуществующим именам файлов перечислены в `review_navigation_errors.json` и исправлены адресным rg. Никакого initial red test не скрыто. Старый blocked-phase19/19 не суммируется с финальным30.

## Статусы и NEXT

`OFFICIAL_SOURCE_REVISION_VERIFIED` — bounded GitHub ZIP origin/comment/hash, не detached signature. `HTTP_CONNECT_SOURCE_UNVERIFIED`; strict route primitives условно подтверждены, **STRICT_ROUTE_SOURCE_UNVERIFIED для полного профиля**. `HIDDEN_EGRESS_PATHS` bounded-reviewed, dependency/global absence BLOCKED. Engine selection PENDING_USER; B owner/WFP/ordinary Chat NOT VERIFIED; hosted tunnel HOLD; **can_apply=false; can_start_tunnel=false; native_config=null**.

Нужный следующий материал — source-only dependency bundle **github.com/sagernet/sing@{review.SING_VERSION}** (HTTP/auth/JSON/control helpers). Скачивание dependencies **не входит** в одноразовое разрешение и не выполнялось. Затем возможен bounded review строгого native mapping proposal, без немедленного engine switch. Windows/WFP/native/hosted — отдельный будущий USER GO.

DOC IMPACT: общие18/19/34/37 не изменялись; предложить WEB_11 добавить факты о default DIRECT/DNS, UoT и dependency gap, сохранив gates. Все107 ранее защищённых файлов сверяются в final integrity; original source tree сверяется по1013 hashes. Полный ZIP/source остаётся вне repo, **не входит в пользовательский commit автоматически**; в проекте есть receipt, tree hashes, 54 locators и bounded excerpts. Независимый verifier должен получить этот exact ZIP либо отдельно разрешённый source channel.

Повторный append-only amendment handoff/ротация сохраняет B4 byte-identical, не читает старые001 bytes и не дублирует TASK в compact five. Receipt — `amendment_01/evidence/card_rotation.json`. Независимую приёмку и отправку WEB_11 исполнитель не объявляет; пользователь публикует/передаёт комплект.
''')
    doc('source_bundle_provenance.md',f'''
# Source provenance — actual bundle

Archive: `{download['archive_path']}`; source root: `{ROOT}`.
Source URL: `{download['requested_url']}` → `{download['final_url']}`.
Received: `{download['received_at']}`. SHA256: `{review.ZIP_SHA}`.
ZIP comment revision: `{review.REVISION}`; official v1.13.4 mapping previously supplied by WEB_11 and release page shows d091826. Page reports verified commit signature; **local GPG verification not performed**, and that UI label is not an archive/EXE signature.

One approved archive, 1,438,060 bytes;1013 regular source files, 3,870,530 bytes. Extraction rejected traversal, absolute/colon/backslash names, collisions, links, encrypted entries and executable suffixes; CRC and bounds checked. Full source-tree hash ledger is `amendment_01/evidence/source_tree_manifest.json`. No source file executed, no build/dependency install.

Origin confidence: GitHub TLS + exact requested tag + commit comment + package hash custody. Limit: SHA is locally measured, not independently signed upstream package hash; compromised origin/same-user replacement not cryptographically ruled out. ZIP remains external, only evidence/excerpts copied into project. Full source→binary correspondence remains NOT VERIFIED.

Critical dependency: go.mod/go.sum pin **github.com/sagernet/sing {review.SING_VERSION}**, ZIP sum `{review.SING_SUM}`. Matching dependency bytes are **not vendored in this archive**. A checksum entry does not supply or verify downloaded module content because none was downloaded. HTTP parser/auth and enhanced JSON closure remain BLOCKED; more downloads require another explicit USER GO.
''')
    doc('http_connect_review.md',f'''
# HTTP inbound / CONNECT — partial source evidence

{loc['http_dispatch']} registers HTTP, creates TCP listener, constructs `auth.NewAuthenticator(options.Users)`, optional inbound TLS and calls external `http.HandleConnectionEx` with stream and packet callbacks. {loc['listener']} binds a Go net listener; default address literal127.0.0.1 appears in the helper, but future profile must explicitly pin P/address and prohibit reuse/extra listeners.

Bundled docs `docs/configuration/inbound/http.md` say empty users means no authentication; this is **documentation**, not reviewed external authenticator code. `set_system_proxy` is exposed and {loc['system_proxy']} enables it when configured: strict proposal must require false. It was not invoked here.

CONNECT request parsing, acceptance conditions, auth rejection/error response, HTTP header limits/ordinary forwarding/stream packet details belong to **github.com/sagernet/sing/protocol/http**, whose implementation is absent. `HTTP_CONNECT_SOURCE_UNVERIFIED / DEPENDENCY_CLOSURE_REQUIRED`. No claim of exact wire semantics from the HTTP name or docs alone.

UoT is real in-repo dispatch: {loc['uot']} transforms special destinations into packet routing before ordinary TCP router handling. TCP transport alone is not proof of logical TCP-only access. No synthetic/native HTTP request was sent to an engine.
''')
    doc('route_and_fallback_review.md',f'''
# Route/default/failure findings

{loc['selected_outbound']}: route action selects `action.Outbound`, missing tag/network incompatibility returns error; reject action returns rejection. First terminal matched route/reject/hijack is selected in `Router.matchRule` (route/route.go). If no selected rule, it uses default outbound.

{loc['manager_default']}: explicit final must exist; absent explicit final, first created outbound becomes default. If no default is configured, {loc['direct_default']} installs **DIRECT**. Bundled route docs corroborate first-outbound behavior. Therefore default DENY is **not native engine default**.

{loc['connection_failure']}: ordinary `ConnectionManager.NewConnection` closes on dial error. In the inspected Trojan illustration {loc['one_server_example']}, no transport/mux path dials configured `serverAddr` then serializes logical destination; errors return without selecting DIRECT here. This bounded observation does not cover every transport, selector, retry, helper or external dependency.

Selector can load cached selection/change target; URLTest selects by health and probes. Exclude groups, secondary/detour/proxy chains and dynamic API mutation from any future strict mapping. Lower dialer interface/address fallback is a separate mechanism from proxy DIRECT fallback and needs its own restrictions/OS proof.

Future proposal, **not generated config**: one explicit pinned outbound R:Q; explicit TCP admission for one inbound; terminal catch-all reject; no bypass/resolve/sniff/direct extra branch, endpoints or groups. No protocol chosen and no family change performed. Source check of known branches and mutation rejection is not native fail-closed verification.
''')
    doc('network_egress_review.md',f'''
# DNS/UDP/IPv6/hidden egress/ownership

|Source locator|Observed path|Future strict condition / limitation|
|---|---|---|
|{loc['resolve']}|Detour or default dialer; domain upstream wraps resolver|LiteralIPv4 R avoids this domain path; prohibit detour/resolve actions, verify TLS still authenticates chosen server|
|{loc['local_dns']} and box default factory|Windows adapter DNS enumeration/default NS and local DNS transport|Empty DNS config does not remove resolver capability; no-DNS must be proven, not inferred|
|{loc['uot']}|TCP stream can become logical packet flow|Reject packet/UoT routes, not merely OS UDP sockets|
|{loc['health']}|URLTest ticker/probes and changing selection|No URLTest/group/network strategy fallback in proposed strict subset|
|{loc['remote_rules']}|Initial fetch + periodic remote rule-set update|No remote rules/resources; cached dynamic source also needs exclusion|
|{loc['ntp']}|Conditional NTP service/dialer|NTP disabled; no helper/system time write|
|{loc['ech_dns']}|ECH config DNS HTTPS record lookup|No automatic ECH acquisition; ordinary TLS path only if later approved|
|{loc['reality_cover']}|Verification failure triggers cover HTTP via existing conn|Not a newly direct socket in this function; still unauthorized cover traffic unless excluded|
|{loc['tor_helper']}|Tor startup and local SOCKS client in Tor-specific path|No Tor/companions; dependencies not closed|

Box may create Clash/V2Ray APIs, services, endpoints and other conditional features. Build/update tools are separate entrypoints; a text hit in cmd/internal is not evidence of automatic runtime update. No global absence of telemetry/update/companion paths is proven: review is bounded and external module closure incomplete.

Ownership path illustration: HTTP listener uses `net.ListenConfig`, ordinary protocol dial uses in-process default dialer and literal upstream. {ref('common/dialer/default.go','func (d *DefaultDialer) DialContext')} rejects unresolved domain and chooses IPv4/IPv6 dials by address; both UDP and TCP APIs exist. Goroutines are not separate Windows identities, but real socket owner depends on launch token/thread impersonation/handles/runtime/OS. No SID was created/read as proof. F2 remains **B_EGRESS_OWNER_NOT_VERIFIED**.

Potential one B process is plausible in the narrow chosen subset, not established for arbitrary installed build/config. Existing WFP/source-only candidate cannot enforce it until independent lab tests. No native network test executed.
''')
    doc('config_loader_review.md',f'''
# Configuration loader / ownership of inputs

{loc['config_default']}: CLI -c is an array, -C adds directories, -D changes cwd (and can create it), absent -c/-C uses `config.json`. `preRun` reads SUDO_USER/UID/GID for file manager context; not proof of a safe Windows process token. A future exact invocation must specify one protected absolute config, no config-directory/stdin/default search, pinned cwd and reviewed environment. This TASK does not create such launcher or alter environment.

{loc['config_merge']}: `readConfigAt` reads stdin or file, `readConfig` reads .json directory members and sorts, `readConfigAndMerge` uses external badjson.MergeJSON; run loop handles SIGHUP with check/recreate. Multiple-file merge/parser edge cases belong partly to missing sing module. Atomic immutable config binding, safe roots/ACLs and TOCTOU remain external requirements, not supplied by a hash in our report.

{loc['schema']}: top-level typed options calls DisallowUnknownFields and checkOptions duplicate tags. Nested option registry/UnmarshallExcludedContext uses dependency code: no blanket unknown-field guarantee claimed. Source tests guard current top-level field set against inserted Sneaky field. Native schema was not invented and native config parsing was NOT RUN.

Existing broker family=V2Ray remains immutable. A future user-approved sing-box mapping would require exact registry/option schema review, lossless field policy, dependencies, disabled-only output and negative source/config controls. It is not an automatic translation or permission to load user profiles.
''')
    doc('compatibility_matrix.md',f'''
# Compatibility decision

|Invariant|Evidence level|Status|
|---|---|---|
|Official v1.13.4 source revision|HTTPS exact archive + ZIP comment {review.REVISION}, package hash|BOUNDED VERIFIED; detached signature/binary correspondence unverified|
|HTTP CONNECT parsing/auth|HTTP integration present; actual parser external missing|UNVERIFIED / dependency source required|
|Single inbound / routing / reject primitives|In-repo factories and route code reviewed|SUPPORTED AS PRIMITIVES; full strict profile unverified|
|Default no DIRECT|Empty/default engine can create DIRECT|UNSUPPORTED AS DEFAULT; explicit reviewed policy required|
|One B-owned actual socket to literal R:Q|Ordinary in-process path visible; no selected protocol/config or OS token proof|UNVERIFIED|
|No DNS/UDP/IPv6/health/helpers|Several concrete conditional paths found|BLOCKED until strict subset/dependency/OS proof|
|Config/root isolation|CLI explicit path possible, defaults/merge/reload exist|CONDITIONAL; protected launcher/config policy not implemented|
|Existing family=V2Ray|Still rejects sing-box|USER DECISION REQUIRED; unchanged|
|MCP/NPFS independence|Existing code unchanged, pure gates regress|Preserved; no new native/SDK test|

Minimal future migration proposal: only after missing sing dependency review and explicit user engine selection, add a separately reviewed family/native schema mapping to existing broker module. Keep C/B/U and NPFS roles, same B listener+remote-owner requirement and all no-DIRECT/WFP gates. Do not relabel current V2Ray contract as accepted sing-box config; no second broker stack is justified.
''')
    doc('manual_engineering_review.md',f'''
# Manual engineering/adversarial review — amendment01

Codex007 /2026-10-24, separate source reasoning, not independent WEB_11 acceptance. Reviewed actual pinned archive code and relevant docs; 54 line/function/file-hash locators plus selected additional loci in evidence. No core or Go build/test executed.

- Download: explicit existing loopback HTTP CONNECT, validated TLS GitHub→codeload, no retry/DIRECT/credential export; only one archive. This does not prove proxy remote route or OS containment. ZIP comment matches revision, but comment/tag/hash alone is not cryptographic archive/EXE authenticity.
- Source safety: bounded CRC/paths/collisions/links/member checks before extraction, no archive execution. Full1013 file pins retained. Source bytes unchanged; mutations are memory/copies under report, not changes to upstream tree.
- Corrected assumptions: empty config is **not deny** (DIRECT+localDNS defaults); TCP listener is **not logical UDP exclusion** (UoT); direct factory must not be confused with a reviewed outbound's error return. Interface fallback is not automatically DIRECT proxy fallback.
- HTTP/auth/JSON code closure: external sing dependency missing. No substitute pseudocode or package-name inference. Tag and module checksum strings do not supply dependency bytes. More dependency fetches are outside USER GO.
- Hidden paths traced: health groups, remote rules, NTP, Tor, ECH and REALITY cover. REALITY function reuses existing connection, so do not incorrectly claim a new direct dial there. Optional build tools are not automatically run-service telemetry.
- Config: exact c/cwd possible, but directories/stdin/merge/default/reload and external parser exist. A pointer/line checker is not a full Go static analyzer, native schema validator or protected install boundary.
- Source test quality: positive actual source + distinct bad pins/files/revision/checksum/field/branch mutations; other-outbound mutant is unexecuted Go lexical change, DIRECT mutant is existing strict review intent because original Go default is already DIRECT. No native effect is claimed. Both source attempts30/30, navigation misses retained, no unexpected red tests.
- Ownership: ordinary listener/dial path is in process; no claim of effective B token, no implicit privilege/SID transition, no proof against inherited handles or dependency/native companions. Full OS WFP/no-direct/boot/observerloss/preexisting-flow guarantees remain BLOCKED.

Conclusion: bounded useful source evidence obtained; original no-bundle blocker resolved, **dependency closure and strict config/native acceptance remain partial**. Recommend next source-only dependency input before engine decision or implementation.
''')
    doc('next_user_decision.md',f'''
# NEXT USER DECISION — no additional download performed

One-time source ZIP permission is consumed. Main archive received and reviewed; do not repeat the old archive request. The next missing source input is **github.com/sagernet/sing@{review.SING_VERSION}**, in particular protocol/http, common/auth, common/json and network/control helpers. Pinned go.sum ZIP checksum: `{review.SING_SUM}`; go.mod checksum: `h1:ARkL0gM13/Iv5VCZmci/NuoOlePoIsW0m7BWfln/Hak=`.

Provide an already available matching local source-only dependency bundle with origin/hash, or separately authorize a bounded dependency-source acquisition. **No dependency installation/build is needed or permitted by the existing one-archive GO.** Do not supply working configs/subscriptions/passwords. This is the minimum next source closure for full CONNECT/auth/JSON review; it is not an ask to download every compiled optional feature.

After that review: user decides whether sing-box is the engine candidate, then separately scopes exact disabled native config mapping. Preserve current V2Ray family until that decision. Upstream encrypted/authenticated protocol and endpoint/credential delivery must be explicitly selected, not inferred from a user profile.

Native execution, provisioning C/B identities, WFP, routes, services or hosted tunnel each remain separate USER GO after independently proven lab isolation. Actual same-B PID listener+remote socket, no resolver/UDP/IPv6/helper/fallback, stop on drift/observer loss and existing flow teardown are not proved by source tests. can_apply=false, can_start_tunnel=false, HOSTED_TUNNEL_ON_HOLD_BY_USER, ordinary Chat E2E NOT VERIFIED.
''')
    put(A/'evidence/additional_reviewed_loci.json',extra)
    print(json.dumps({'reports_written':10,'tests':run['collected'],'archive_sha256':review.ZIP_SHA,'partial_dependency_gap':True}))
if __name__=='__main__':main()
