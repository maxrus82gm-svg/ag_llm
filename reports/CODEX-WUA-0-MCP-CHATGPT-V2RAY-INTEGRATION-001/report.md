# CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001 — итоговый отчёт

Codex 007, 2026-10-21, Asia/Yekaterinburg. **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.** Это сдача разрешённого локального integration package, не разрешение на production и не независимая приёмка. Координаторский source reference `main@f9c18194f4e2b6ec9f17033a1d0afc34768c6dd5` не проверялся через Git/GitHub; локальные байты привязаны hashes/manifest.

**Практический результат:** реализован настоящий MCP stdio server на существующем SDK2, который реально обращается к отдельному процессу с `WebAlarmApi` на новом синтетическом хранилище. Реализованы четыре read-only tools, bounded authenticated API channel, strict profile/preflight, versioned disabled templates и исполняемые synthetic route/security tests. Найдены **два blocking conflicts** будущего Windows-маршрута: скрытый TCP у Python asyncio и настоящий SID владельца V2Ray egress. Они не замаскированы зелёными тестами.

## Обязательные раздельные статусы

```text
LOCAL_MCP_INTEGRATION_VERIFIED — SDK/local synthetic fixture only
STRICT_ROUTE_SYNTHETIC_TESTED — owned CONNECT→SOCKS→control-plane simulation only
TWO_WINDOWS_IDENTITIES_NOT_PROVISIONED
OS_WFP_EGRESS_NOT_VERIFIED
V2RAY_LIVE_ROUTE_NOT_VERIFIED
SECURE_TUNNEL_NOT_ACTIVATED
ORDINARY_CHATGPT_E2E_NOT_VERIFIED
HOSTED_TUNNEL_ON_HOLD_BY_USER
PRODUCTION / REAL STARTUP: BLOCKED
```

Windows account inventory здесь не проводилась: технические identities не созданы этой TASK и не предоставлены как проверенные prerequisites. Наличие fictional SID в тестах не означает существование аккаунта. Рабочий V2Ray и его ownership/profile не исследовались и не менялись.

## 1. Реализованный код и настоящий API

Standalone source: `integrations/wua_chatgpt_mcp/`. Изначально каталога не было; чужая работа не перезаписывалась. Использованы существующие `.venv` Python3.12.10/MCP2.2.0/httpx0.28.1/pydantic2.13.5; зависимостей не устанавливали. Старый WUA-0 PoC использован как source reference, его исторические 34 PASS не выдаются за новый запуск.

`server.py` использует официальный SDK `mcp.server.lowlevel.Server`, `stdio_server`, typed Tool/CallToolResult и настоящий initialize/list/call lifecycle. Независимый client в `tests/mcp_smoke.py` использует официальный `ClientSession`, а не прямой вызов handler. Bounded input wrapper не заменяет MCP-протокол и передаёт frames SDK.

`ApiChannel` запускает только фиксированный свой `api_fixture.py` на том же существующем interpreter с изолированными argv/environment. Worker отдельно владеет свежим fixture root, создаёт через API один synthetic workspace/TASK и после baseline разрешает только `/status` и `/tasks/synthetic_wua_integration_001/context`. Контекст получается настоящим `WebAlarmApi.dispatch`, не зашитым ответом. Разрешены только synthetic scope и root внутри новой TASK/runs; ни Run Store, ни private Ultra files, ни произвольные TASK/method/path/tool/model/Git не открываются.

Инструменты:

| Tool | Реальный источник / ограничение |
|---|---|
| ping | Ограниченные поля server-owned `/status` + session/nonce/read receipt |
| list_capabilities | Точный allowlist/version0.1.0/read-only scope, подтверждённый отдельным API status-read |
| read_synthetic_context | Единственный разрешённый TASK; server-owned projection, nonce и independently проверяемый context SHA256 |
| get_status | `/status` только своего тестового API; storage_root и private config не возвращаются |

Authorization: trusted fixture bootstrap/session grant, HMAC API-request binding, отдельная API проверка scope/operation/replay/quota; в tool arguments нет реальных tokens. Strict schemas/UUID/type/unknown-field checks, bounded generic errors, redacted request UUID/tool/result audit. Request frame8192, depth12/items64, API response32768, tool payload16384; API wait2s, bounded shutdown и owned process cleanup. Тестовый MAC key не экспортируется в public evidence: ephemeral bootstrap удаляется в finally. В evidence доступны только synthetic contexts/nonces/IDs/receipts. Подменённые nonce/session/content/storage hashes приводят к закрытию канала и завершению own worker.

SDK test повторяет чтение после остановки/нового запуска: новая session/nonce/context; само чтение не меняет fixture storage. PID собственного MCP процесса получен через его receipt и наблюдался read-only `OpenProcess(SYNCHRONIZE)`/`WaitForSingleObject`; API exit/reader-stop receipt проверен отдельно. Это факт lifecycle, не SID/token proof. API child завершает stdin/EOF, затем при необходимости только свой процесс terminate/kill; чужие процессы не затрагиваются.

## 2. Топология: что совместимо, что BLOCKED

Полная таблица process/channel/authority/failure — `topology.md`.

**F1, реально установленный runtime conflict.** У данного Python3.12 Windows `ProactorEventLoop` вызывает `_fallback_socketpair`: AF_INET TCP bind127:0/connect к динамическому loopback-порту. `AF_UNIX` отсутствует; Trio не установлен и не устанавливался. `runtime_compatibility.json` содержит actual owned-loopback probe, порт отдельно удерживаемого фиктивного P, наблюдённый другой порт и stdlib source SHA. Прежний C-only-P predicate intent с этим расходится. Это сравнение с намерением WFP, не реальный запуск filters. Audit guard нашего fixture начинает работать после event-loop construction, поэтому **не доказывает** отсутствие startup-сокета. Не добавляли новый порт/range и не обходили WFP.

Выбранный future target: C official Go → STDIO → **C-owned synchronous no-TCP pipe relay** → local authenticated NPFS → U server-owned MCP SDK/API. Current Python SDK fixture не является этим C relay. Relay и production pipe/DACL/peer-token connector **не реализованы**, а не «готовы к запуску». MCP/API protocol и tool validation реализованы и пригодны для такого connector без переписывания всего SDK/tool слоя. Production TASK grants/real context authority ещё требуют нового review.

**F2, ownership/topology conflict.** CONNECT broker под B, отправляющий в SOCKS обычного пользователя, не защищает внешний V2Ray socket правилами B. Если V2Ray тоже под B, появляется дополнительный B→localS, которого нет в прежнем B-only-R:Q. Выбран future dedicated V2Ray native HTTP CONNECT inbound P **под actual B SID**, затем только literal approved R:Q. Это новая отдельная instance, текущий V2Ray не трогается. Поддержка точной версии/формата/outbound/owner не доказана. SOCKS10808 не объявлен CONNECT или доказательством маршрута.

Current synthetic tests используют reference CONNECT→SOCKS→owned control receiver; reference byte-exact перенесён в новый package с source/hash provenance (`reused_sources.json`). Это рабочий **reference fixture**, не выбранный production layout. Все `.invalid` имена передаются в SOCKS как данные и отображаются фиктивным сервером на собственный loopback receiver; DNS/public destinations не используются.

U/UI/обычный ChatGPT не покрыты WFP двух SID. WFP connect policy не закрывает автоматически named pipes, BITS/COM/system DNS и service mediation. Необходимы отдельные IPC authority/ACL/delegation tests и при необходимости более сильная T2 boundary. Старый WFP selected edge остаётся unmatched, а не overriding allow; native block/allow arbitration, accepted health flows H, bind/port ownership, descendants/token changes, IPv6/DNS/BFE/boot остаются NOT VERIFIED.

## 3. Tunnel/configuration/preflight

Созданы семь versioned portable JSON/YAML contracts/templates в package/configs: strict empty template, fictional example, disabled v0.0.16 client YAML, data-only launch argv, dedicated B broker, gateway IPC и health contracts. Нет настоящих SID/password/key/tunnel_id/profile/remote proxy secrets. Ports/paths/SIDs должны быть discovered/bound на целевом ПК, а не перенесены из примера.

Шесть CLI names и STDIO YAML structure сверены **по сохранённым локально** official v0.0.16 help/sample; `source_evidence.json` содержит hashes и ограничения. Explicit HTTP proxies для global/control-plane/MCP/Harpoon заданы как argv data, неизвестные YAML proxy keys/CLI flags не придуманы; SOCKS URL не подставляется в HTTP proxy. Health loopback H отдельно отражён как bind/inbound gate. Cloudflared/Harpoon optional paths/secret env inheritance и весь Go proxy/fallback graph не считаются закрытыми одной настройкой.

Никакого upstream/Git/OpenAI запроса, настоящего Go help/run или повторного поиска/запуска бинарника не выполнялось. Matching source↔binary/native all-paths proof остаётся BLOCKED по прежним материалам. Навык OpenAI Docs использован с приоритетом TASK-ограничений на сеть: current upstream/entitlement не запрашивались; ссылки TASK — ориентиры, не свежая проверка.

`diagnostics.py` реально выполнен: корректный pinned synthetic profile даёт структурный VALID, **exit20, can_apply=false/can_start_tunnel=false** и все real states unverified. Fake proof/all-true approval не дают полномочий. Это offline structural CLI без account/port/network discovery. `get_status` означает только API health, не WFP/V2Ray/cloud health. Tunnel runtime API auth и model API/Model Assignment — разные направления; никаких model API вызовов/платных запросов нет. Доступ Platform/ChatGPT workspace и billing не проверялись; пароль ChatGPT не нужен и не запрашивался.

## 4. Фактические тесты / evidence / ошибки

| Gate | Финальный результат |
|---|---|
| Real MCP SDK integration | **63/63 named checks PASS**, 2 свежие sessions, initialize/list/four calls, foreign task/type/unknown denial, hash/nonce/storage/restart/own process stop; `runs/mcp06/` |
| Integration/security suite | **24/24 unittest methods PASS, 0 FAIL/ERROR**; `runs/security03/` |
| Route mutation | Один targeted positive-route control: inner exit1, **1 expected FAIL, 0 ERROR**, detected; `runs/mutant_route02/` |
| Owner mutation | Один targeted V2Ray-owner control: inner exit1, **1 expected FAIL, 0 ERROR**, detected; `runs/mutant_owner02/` |
| Runtime compatibility probe | Actual owned Python self-connect≠P; **BLOCKED conflict found**, не WFP acceptance |
| Offline diagnostic CLI | exit20, structurally VALID example, **real activation BLOCKED** |
| Syntax/source pins | Python AST, before/after source hashes во всех final runs; файлы package неизменны между final tests и handoff |

24 methods включают реальные loopback CONNECT/SOCKS/control correlation; refused/closed listener/timeout/abrupt/malformed upstream; redirect/body-size denial; all proxy/NO_PROXY overrides before dial; method/endpoint substitution; takeover nonce; intentional unexpected connect detection; bounded broker config; wrong SID/owner/child/startup pin; all-true fake proofs; strict parser/path; direct API valid-MAC wrong scope/write/replay, bad MAC, killed child, nonce/session/content/storage tamper и oversized **real MCP frame** с reaped API child.

63 SDK checks, 24 test methods и два targeted mutants — разные виды evidence, они не сложены в «89 независимых native tests». Simulation poll/result/secret/health/MCP/OAuth/Harpoon phases не являются запуском этих Go branches. Ошибки upstream не создают неожиданных recorded edges; intentional observer negative test PASS означает, что ровно ожидаемая собственная loopback попытка была обнаружена/отказана до соединения. Native/whole-host observer coverage не заявлена.

**Первоначальные отказы сохранены:** mcp01/mcp02 — connection closed до initialize, уточнённый safe stderr установил Denied:FIXTURE_WRITE_DENIED для штатного NUL stderr sink. Адресно разрешён только os.devnull; guard остальных writes не снимался. Последующие mcp03=59/59, mcp04/mcp05=61/61; mcp06=63/63 после добавления независимой process-stop проверки. security01=21/21, security02=23/23, security03=24/24 после новых coverage controls. Старые results не переписаны зелёными; редактированы только private traceback path prefixes до publication-safe aliases. Первые два запуска были до появления source-pin runner; их исходные полные source snapshots не заявляются. Отдельный source review исправил finally cleanup при channel-startup error; подробности `manual_engineering_review.md`.

## 5. Scope / ограничения / DOC IMPACT

Записи: только новый integration package, собственная TASK с owned fixture files и затем разрешённая card rotation. Старые PoC/reports/toolkit/WFP source и web_alarm runtime read-only. Защищённый bounded набор файлов зафиксирован до работы; итоговая сверка/число — `integrity.json`. Старые BackendImplemented=false и CanApply=false подтверждаются адресным source read и неизменными hashes, а не запуском installer. Install/Uninstall остаются BLOCKED.

**Реальные account/WFP/Firewall/BFE/service/ACL/network/V2Ray/VM/Hyper-V/ExecutionPolicy изменения=0; native Go/Cloudflared/hosted/API-key/model API/Git/GitHub calls=0.** Были разрешённые собственные процессы, STDIO, loopback fixtures, file writes в новых TASK roots и read-only own-process/volume metadata. Это не «ноль Windows API/сетевых соединений вообще» и не whole-host traffic attestation. Существующие пользовательские процессы/env/profiles не менялись, production/Claude/LLM12/CI не редактировались.

Независимые Windows SID/WFP/IPC/bind/DNS/children tests, native tunnel-client/fail-closed, V2Ray live route, Platform access, hosted activation и ordinary Chat — **NOT RUN / BLOCKED** с адресными gates в `connection_gates.md`/`next_user_go.md`. Ранее принятый lab kit не даёт готовую VM; I01–I12 real lab остаются pending. Нельзя запускать эксперимент на рабочем host ради снятия BLOCKED.

DOC IMPACT: новая реализация/fixtures/contracts/reports + штатная собственная карточка. Общие19/34/37 не менялись. SHARED DOC DELTA для WEB_11 после независимого review: 19§7.3 и37§9 — local real SDK integration verified only synthetic; отметить hidden asyncio TCP и actual V2Ray egress-owner conflicts; STDIO/pipe vs network policy; no production/native/tunnel/E2E acceptance. Это предложение, не общая документационная запись Codex.

## 6. Следующее действие и публикация

Пакет готов для WEB_11: source/tests, versioned disabled templates, source/reuse provenance, SDK structured receipts, synthetic API bytes, route observations, original failures, actual runtime conflict, diagnostic/health/connection/deployment/manual review и manifest size/SHA. `.gitignore` читается как обычный файл; новые scope не попадают под показанные root exclusions. Git/global-excludes/index не проверялись. Пользователь публикует/передаёт; Codex не отправлял отчёт в чужой чат и не объявляет independent PASS.

**NEXT SAFE ACTION:** независимый review WEB_11 и отдельная source/own-IPC-fixture TASK на no-TCP C relay + server-owned SDK gateway. Затем выбор dedicated B V2Ray implementation/source/config и отдельные lab native gates. Настройка/активация Windows/V2Ray/tunnel — только новые конкретные USER GO. Список прав и prerequisites без абстрактного «разрешить всё» — `next_user_go.md`.

Полная исходная постановка заморожена в `assignment.md`. После сохранения этого отчёта и pre-rotation manifest выполняется двухэтапная own-card rotation: full assignment в B2, factual result B3, readback, затем B1 WAITING. Прежние rules/history byte-exact; receipt содержит exact guarded reconstruction rollback. Фактический результат ротации и финальной сверки добавляется ниже; при чужой правке только rotation BLOCKED без перезаписи.


## 7. Фактическая ротация и финальная целостность

Полная постановка B2 и factual result B3 записаны и прочитаны до очистки B1; теперь B1=`ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Сохранены byte-exact 549445 байт старой истории и 6852 байт правил/prefix. Два in-memory negative controls отклоняют чужую правку карточки и подмену постановки. Conditional exact rollback проверен реконструкцией before SHA из prefix+assignment+history suffix. Сырая старая карточка в публикационную папку не копировалась; pending отсутствует.

После ротации 667/667 protected non-card files неизменны; вне новых package/report scope изменена только разрешённая собственная карточка. `card_rotation.json`/`integrity.json` содержат hashes/readback/guards; финальный manifest включает оба новых каталога и все evidence кроме собственного self-hash. Независимая приёмка WEB_11 и публикация остаются pending.
