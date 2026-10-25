> Полная копия amendment_01/report.md. Относительные пути в тексте относятся к amendment_01; source_callgraph.md и strict_route_gap_matrix.md находятся в корне TASK.

# CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001 — USER GO amendment 01

**Codex 007 / 2026-10-25 — PARTIAL / BOUNDED DEPENDENCY SOURCE REVIEW. AWAITING INDEPENDENT VERIFICATION WEB_12. LOCAL ONLY / NOT SYNCED.**

Получен ровно один разрешённый ZIP sing; Go module h1 совпал. Реальная реализация HTTP/auth/JSON изучена в пределах полученного дерева и сохранённого sing-box. **51/51 offline checks PASS**: 21 новый archive/source control и прежние 30 проверок. Это не запуск Go/движка и не подтверждение native strict security или ChatGPT E2E.

Исходный BLOCKED-пакет сохранён в `../initial_blocked/`: 15 файлов, включая прежний manifest. Его DOWNLOAD_GO_REQUIRED — предыдущий статус. Новое прямое разрешение пользователя сохранено в `USER_GO.md`; одно получение теперь израсходовано. БЛОК 1/архивы не редактировались. Прежняя независимая приёмка WEB_11 sing-box сохранена в своём ограниченном объёме. Новая независимая приёмка WEB_12 ещё не проведена.

## A. Получение и целостность

| Поле | Фактическое значение |
| --- | --- |
| Module | `github.com/sagernet/sing` |
| Version | `v0.8.3-0.20260315153529-ed51f65fbfde` |
| Единственный URL | `https://proxy.golang.org/github.com/sagernet/sing/@v/v0.8.3-0.20260315153529-ed51f65fbfde.zip` |
| Получен UTC | `2026-10-24T20:33:00.125100+00:00` (2026-10-25 01:33:00 +05) |
| HTTP / redirects / attempts | `200 / 0 / 1` |
| ZIP bytes | `310819` |
| Raw ZIP SHA-256 | `dfb3b8c7cbc603602c6cf453161d319209e5610477e1118354dd449bd9409659` |
| Expected = computed module ZIP h1 | `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=` |
| ZIP | `M:/WUA_SOURCE_REVIEW/sing/v0.8.3-0.20260315153529-ed51f65fbfde/sing-module-source.zip` |
| Source | `M:/WUA_SOURCE_REVIEW/sing/v0.8.3-0.20260315153529-ed51f65fbfde/source` |
| Tree | `322` файла, `756376` uncompressed bytes |

До получения read-only проверены актуальные proxy metadata и loopback listener: `http://127.0.0.1:10808`, процесс sing-box, PID 38964 на момент preflight. Путь к EXE через Process.Path недоступен, права не расширялись. Пробный CONNECT не отправлялся. Единственный разрешённый GET выполнен через explicit HTTPS CONNECT к этому literal адресу с TLS hostname verification для proxy.golang.org. Audit hook зафиксировал одно socket.connect к loopback и запрещал иные адреса, внешнее локальное DNS-разрешение и child processes. Downloader не следует redirects, не делает retries/DIRECT; NO_PROXY не выбирает иной transport. Это ограничение данного процесса, **не OS containment, actual remote V2Ray или B-owned socket proof**. Существующий proxy config не читался/не менялся.

До распаковки проверены module/version prefix, go.mod declaration, размеры/count/expansion, пути/CRC, duplicate/case/file-directory collisions, Windows aliases, symlink/reparse и executable members. Принимается консервативное ASCII source-подмножество, не все формально допустимые Go ZIP. ZipInfo-normalized/NUL-truncated имена запрещены. Destination был новым; parent reparse checks, запись xb и scope/readback проверены. Системная защита от hostile concurrent path replacement не доказана. Ничто из ZIP не исполнялось.

**h1 отличается от raw SHA:** SHA-256 каждого uncompressed body; сортировка полных module-prefixed имён; строки `<hex>  <name>\n`; SHA-256 их UTF-8 concatenation; Base64 и `h1:`. Результат совпал с заранее заданным pin из принятого sing-box go.sum. Есть фиксированный двухфайловый vector и проверка независимости от ZIP order/compression. Go tooling не запускался; local dirhash source в двух стандартных путях не найден и не скачивался. Это content binding по доверенному expected checksum; detached signature, новый sumdb lookup, full upstream commit SHA зависимости и source→installed EXE соответствие не подтверждены. Pseudo-version suffix не объявляется full revision proof.

Receipt: `evidence/download_receipt.json`; preflight: `proxy_preflight.json`; полный member manifest/распаковка: `module_integrity.json`; финальная сверка: `final_integrity.json`. ZIP и source tree вне repo. Две ошибки локальной подготовки preflight (null Process.Path и отсутствовавшая evidence directory) исправлены до download; указаны в preflight, не скрыты.

## B. HTTP CONNECT/auth — source findings

Точные файл/функция/строка/anchor/SHA для IDs ниже — `evidence/source_locators.json` и корневой `source_callgraph.md`.

| Finding для будущего strict profile | Установлено / ограничение | Locators |
| --- | --- | --- |
| **HIGH: empty users отключает auth** | NewAuthenticator возвращает nil при len=0; handler проверяет auth только при non-nil. Strict config обязан требовать непустые защищённые credentials | auth_factory, auth_guard |
| **HIGH: credentials в error** | После 407 error может содержать введённые username/password либо исходный Proxy-Authorization; parent inbound передаёт error в logger. Реальные credentials не читались; утечка работающей установки не утверждается | auth_error_disclosure, error_new, parent_error_log |
| Auth-before-dispatch при включённом auth | Verify/отказ до CONNECT, Upgrade и plain HTTP. На ошибке возврат до handler; authOk заново инициализируется на каждый request, успешный user идёт в context | auth_guard, connect_dispatch |
| Basic codec mismatch | Server URL-safe Base64 с игнорированием decode error, библиотечный client StdEncoding. Алфавиты +/slash и malformed/partial decode требуют совместимости. **Доказанный auth bypass не заявлен** | auth_codec, client_system_default |
| CONNECT 200 раньше dial | 200 записывается до handler.NewConnectionEx. Это не свидетельство успешного upstream, strict route или реального owner | connect_dispatch |
| Authority/port/IPv4/IPv6 | URL.Hostname/Port → helper: Atoi error игнорируется, uint16 cast, zero→80/443 default. netip разбирает IP, mapped IPv4 Unwrap, иначе Fqdn. Что допускает HTTP parser, зависит от Go stdlib; malformed/overflow последствия условны | connect_target, port_cast, stdlib_link |
| Не только CONNECT | Есть Upgrade и обычный HTTP после общей auth. HTTP transport передаёт dial через callback/in-memory pipe, redirects не следует (ErrUseLastResponse). CONNECT-only restriction отсутствует | http_alternates |
| Недоверенный source override | X-Forwarded-For может заменить source.Addr; не использовать его как identity/SID authority | source_override |
| Потенциальный client direct | Отдельный NewClient при nil Dialer выбирает SystemDialer. Это свойство соответствующего caller, не доказанный bypass server injected handler | client_system_default |
| Parsing/EOF | ReadRequest связан go:linkname с private net/http.readRequest. Parser error возвращается; buffered bytes передаются callback. Полная grammar/malformed/early-EOF и linkname compatibility без точной stdlib остаются gap | http_read, stdlib_link |

Server callback → adapter.NewUpstreamHandlerEx → parent newUserConnection → UoT router → sing-box route. HTTP/Upgrade проходят общий auth guard, но это не global absence-of-bypass для всех других inbounds/plugins. CONNECT к UoT magic destination может перейти в packet routing. Parsing/auth сами по себе не обеспечивают строгую B-политику.

## C. JSON/config — source findings

| Область | Установлено / ограничение | Locators |
| --- | --- | --- |
| Build aliases | Go>=1.20 без without_contextjson использует bundled contextjson; alternative aliases encoding/json существуют, context extensions импортируют bundled decoder. Реальные build tags EXE в этой TASK не устанавливались | json_build, json_std_build |
| Unknown fields | Parent Options задаёт DisallowUnknownFields; core struct decoder сохраняет unknown error. Nested custom decoders — отдельная граница; inbound registry и badjson excluded-fields вызывают context disallow-unknown | json_unknown, json_nested, parent_nested |
| Duplicate keys | Generic loop не имеет seen-key reject; assignment повторяется. badjson object вызывает Map.Put, обновляющий существующую entry. Native decode не является duplicate-free policy; custom поля могут merge/overwrite по типу | json_duplicates, json_overwrite, json_unknown |
| Type/case/null | Core struct decoder имеет folded-name fallback; type errors сохраняются. Null обнуляет pointer/map/slice/interface, primitive null игнорируется; custom UnmarshalJSON(Context) имеет отдельную обработку | json_unknown, json_null, json_type_error |
| Empty/default | Empty users→no auth, нулевой Options не проверяет strict intent; прежние DIRECT/local DNS defaults сохранены. Decode success не означает strict validity | auth_factory, parent direct_default |
| Extended/single value | Loader использует CommentFilter и один Decode; wrapper не делает EOF-check вторым Decode. Canonical single-document acceptance/rejection trailing values без отдельного oracle не заявляется | json_extended, json_single_decode, comment_filter |
| Merge | Nil raw inputs обрабатываются отдельно; objects рекурсивно merge; destination scalar сохраняется; arrays append destination+source при disableAppend=false. CLI сортирует paths, merges новый source в старый destination и заново декодирует Options | json_merge, parent_merge |
| Reload | CLI содержит SIGHUP check→close/recreate. Это source capability; не доказательство signal compatibility Windows EXE или защиты config files | parent_reload |

Будущему strict профилю нужен один защищённый canonical config с reject duplicates/unknown defaults/ambiguous or trailing data до engine, explicit deny и запретом неутверждённых merge/reload inputs. **Ничего из этого не применяется; второй JSON parser не создавался.**

## D. Route и оставшиеся dependencies

Корневой `strict_route_gap_matrix.md` разделяет SOURCE CONFIRMED / CONDITIONAL / UNVERIFIED / BLOCKED. Прежние default DIRECT/local DNS/UoT/optional health/rulesets/NTP и другие conditional egress сохранены; их наличие в рабочем profile не утверждается. Ошибка normal dial на одном path не доказывает no-fallback всех protocols/groups/resolvers.

sing go.mod: Go1.20; runtime dependency golang.org/x/sys v0.21.0, в том числе Windows buf/bufio imports. Testify/indirect test dependencies не устанавливались. Точная Go stdlib HTTP/URL/net/TLS/Base64/platform syscall source не предоставлена. Дополнительных downloads после sing ZIP **0**. Нехватка этих материалов — адресный blocker для полного closure, не разрешение auto-fetch.

Source review не доказывает SID/WFP/actual socket owner, защиту всей Windows, native schema compatibility или remote route. Обычный ChatGPT и hosted tunnel не задействованы; engine не выбирается исполнителем.

## E. Реализация и проверки

Изменены два существующих файла: `integrations/wua_chatgpt_mcp/singbox_source_review.py` (module Hash1/admission и bounded sing loci/order tripwires) и существующий `integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py` (21 новый control, reuse 11 source+19 pure). Сокращённое tests/... в постановке отнесено к этому фактическому suite; нового корневого файла нет. Прежний sing-box inspect сохранён; can_apply/can_start_tunnel false. Нет второго broker, Go parser или config framework.

Команда: `.\.venv\Scripts\python.exe -B integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py --dependency`. Существующая Windows/Python venv, без installs. Audit hook запрещает socket/subprocess events offline suite. Синтетические ZIP создаются внутри run и адресно очищаются; original archives/trees не меняются. Counts — test methods, subtest failure details сохранены.

| Attempt в runs/ | Collection / PASS / FAIL / ERROR / SKIP | Exit |
| --- | --- | --- |
| source-20261025-013427-60d77978, baseline before edits | 30 /30/0/0/0 | 0 |
| source-20261025-013946-682a46e7, first dependency | 50 /49/1/0/0 | 1 |
| source-20261025-014025-e29db5fb, fixture/name guard correction | 50 /50/0/0/0 | 0 |
| **source-20261025-014112-a2f64d92, capped snapshot hardening** | **51 /51/0/0/0** | **0** |

Первый FAIL сохранён без изменения: Windows ZipInfo нормализовал backslash при создании fixture; ожидаемый PATH reject не достигался, но h1 всё равно отвергал изменённый ZIP. Oracle не ослаблялся до «любого исключения»: исправленная fixture меняет raw local+central names и проверяет orig_filename trigger. Валидатор теперь отвергает нормализацию/NUL. Это fixture/representation gap, не наблюдавшийся native bypass. Manual review дополнительно связал hash/ZIP чтение с одним capped byte snapshot (32MiB+1), устранив второе чтение изменяемого пути; финальный 51-run выполнен после этой новой правки.

Controls: module h1/content/order/compression, CRC, traversal/aliases/case/link/binary/file-directory/size, source pin drift, omission/relocation auth guard, parser/port/JSON merge drift, DIRECT/unknown default. **Go mutations — копии текста, Go не исполняется.** Strict-intent отказ — oracle существующего broker validator, не native route proof. Runtime JSON duplicate/null/auth/malformed HTTP outcomes — **NOT RUN / TEST GAP**, не PASS.

## MANUAL ENGINEERING REVIEW

1. Проверены authority → current metadata → exclusive one-attempt reservation → TLS/GET → hash → extraction → review/tests. Ни предыдущий GO, ни receipt/51 PASS не дают право на следующий fetch/native/activation. PID snapshot и audit hook не выданы за WFP proof.
2. Перечитаны integrity/name/resource checks и source tree readback. h1 и raw SHA разделены; оба вычисляются по bounded ZIP snapshot. Reparse checks не названы hostile OS-level TOCTOU containment.
3. Пройден порядок ReadRequest→auth→source override→CONNECT/Upgrade/HTTP→callbacks. В просмотренной enabled-auth ветке Verify предшествует handler, а nil auth сознательно выключает проверку. 200-before-dial и альтернативные methods учтены.
4. Изучены Verify/Contains, codec variants, E.New и parent ErrorContext. Credentials-in-error подтверждены без настоящих секретов. Гипотеза о доказанном malformed-header auth bypass не принята без полного parser/runtime oracle.
5. Прочитаны JSON aliases, core unknown/type/null/object branches, badjson Map.Put/merge, nested excluded-fields registry и parent reload. DisallowUnknownFields не признан защитой от duplicates/default/fallback. Python-имитация Go semantics не писалась.
6. Проверены первый RED trigger, узкий expected code, cleanup, source pins, сохранение прежних test IDs и конечная collection. Lexical checks защищают известный snapshot, не все будущие ветви. Это author review, не независимая приёмка.
7. Открыты credential logging remediation, strict CONNECT/config admission, DNS/UoT/background egress, exact stdlib/x/sys, actual SID/owner/WFP и real failure behavior. Зелёные pure tests не снимают gates.

## Статусы / NEXT

```text
SOURCE AUDIT: PARTIAL / BOUNDED DEPENDENCY SOURCE REVIEW
EXACT MODULE ZIP H1: VERIFIED AGAINST PROVIDED PIN
HTTP/AUTH/JSON MODULE IMPLEMENTATION: SOURCE REVIEWED WITH FINDINGS
COMPLETE STDLIB/PLATFORM/TRANSITIVE CLOSURE: BLOCKED
OFFLINE SOURCE/CONTRACT CHECKS: 51/51 PASS (not native semantics)
NATIVE GO / NATIVE NETWORK TESTS: NOT RUN / FORBIDDEN
REAL CLIENT FAIL-CLOSED / B-OWNED EGRESS / WFP: NOT VERIFIED
V2RAY REMOTE ROUTE: NOT VERIFIED
HOSTED TUNNEL: ON HOLD BY USER / NOT STARTED
ORDINARY CHAT E2E: NOT VERIFIED
engine.family=V2Ray; can_apply=false; can_start_tunnel=false
CARD / BLOCK 4 / 001 / SHARED DOCS: NOT MODIFIED
GIT / GITHUB: NOT USED; PUBLICATION NOT VERIFIED
INDEPENDENT REVIEW WEB_12: PENDING
```

NEXT: передать factual пакет WEB_12. Не повторять download: GO израсходован. Для полного parser/platform closure нужны адресно разрешённые exact Go stdlib/build и x/sys source, без auto-download; native требует отдельной доказанной изоляции и GO. Перед выбором движка решить credential disclosure и строгий admission. **Активация этого snapshot как доказанно строгого broker не рекомендуется.** Это не выбор движка и не разрешение patch/deployment.

DOC IMPACT для координатора: №19/34/06 отразить новый bounded review, receipt/h1/findings, RED и final51 раздельно, WEB_12 pending и оставшиеся blockers; общие документы не изменены. Карточка/001 не ротируются исполнителем. Полные ZIP/third-party source вне repo не попадут в публикацию автоматически; manifest включает отчёты, sanitized evidence и два разрешённых изменённых source/test. Старые initial/prepare_handoff материалы — историческая BLOCKED-фаза, не команда новой загрузки.
