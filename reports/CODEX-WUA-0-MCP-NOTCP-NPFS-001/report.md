# CODEX-WUA-0-MCP-NOTCP-NPFS-001 — реальный локальный MCP через Named Pipe

Codex 007, 2026-10-24. **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.** Координаторский reference `main@a547092f74d6ee4f2a32982b8c7c067c61e160da` не проверялся через Git. Фактическая версия — local source/binary hashes и manifest.

Реализованы и реально испытаны Windows C# STDIO↔NPFS relay и отдельный U-side server-owned read-only SDK/API gateway. Официальный SDK client через оба executable и настоящий Named Pipe вызывает четыре прежних инструмента; данные происходят из настоящего WebAlarmApi на новом synthetic хранилище. C relay не использует Python asyncio и не требует добавления TCP endpoint. Это закрывает зависимость нового C frontend от найденного Python selfpipe; полная C/Go/WFP egress-гарантия ещё не доказана.

## Раздельные обязательные статусы

```text
LOCAL_STDIO_NPFS_MCP_TESTED
C_RELAY_NO_TCP_SOURCE_REVIEWED
RUNTIME_NETWORK_OBSERVATION_NOT_VERIFIED
REAL_CROSS_SID_AUTH_PENDING
WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED
B_V2RAY_EGRESS_OWNER_NOT_VERIFIED
HOSTED_TUNNEL_ON_HOLD_BY_USER
ORDINARY_CHATGPT_E2E_NOT_VERIFIED
```

`RUNTIME_NETWORK_OBSERVATION_NOT_VERIFIED` означает отсутствие полного continuous process-wide доказательства: реальный независимый от relay PID sampler Windows TCP/UDP IPv4/IPv6 и Toolhelp дал 51 нормальных samples без endpoints/children и заметил intentional native TCP mutation (49 rows). Выборка может пропустить startup/transient/failed dial; ETW/WFP enforcement не запускались. Нельзя читать source review или Python audit как абсолютный запрет любой сети.

## Реализация и scope

Новая цепочка: `official MCP ClientSession → STDIO → WuaRelay.exe → authenticated local NPFS → WuaGateway.exe → U SDK worker → server.make_server → synthetic WebAlarmApi.dispatch`.

Новые исходники: `npfs/Shared.cs`, `Relay.cs`, `Gateway.cs`, `gateway_worker.py`; тесты `tests/run_npfs.py`, `tests/npfs_regression.py`; config `configs/npfs.fixture.contract.json`. Три адресных совместимых изменения: common.py разрешает fixtures текущей TASK/runs, README и gateway.ipc.contract описывают новый bounded candidate. Существующие четыре tool schemas/handlers не переписаны; baseline STDIO API worker сохранён.

Local NPFS endpoint создаётся сервером: exact name, first/one instance, reject remote clients, protected narrow DACL с фактическим readback. Клиент проверяет server PID/primary SID/image; сервер отдельно проверяет client process primary SID и эффективный Identification token через RunAsClient, image и fresh grant. Session/direction/sequence/length/payload защищены HMAC; RPC duplicate/correlation/limits проверены с обеих сторон. MAC/PID/nonce не названы заменой Windows SID.

Current-user-only fixture намеренно не выдаётся за разные C/B/U tokens. Gateway запускает только фиксированный U SDK child: suspended, explicit three-handle list, job assignment до ResumeThread; crash gateway завершает его реальные descendants. C relay не запускает helpers. Frame deadline2.5s, bridge30s, hard process watchdog40s, 8192/32768 bytes, bounded IDs/queues. Python self-sockets у U/test client не объявлены исчезнувшими.

Подробности процессов: topology.md; auth/ACL/TCB: pipe_security.md; воспроизведение: README.md.

## Настоящие проверки и исправления

Финальный run `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/runs/attempt-20261024-013425-5ffffe57`: **24/24 PASS, 0 FAIL/ERROR/SKIP**, две C# сборки exit0, Python syntax PASS. Source/binary pins и immutable final snapshot сохранены. Четыре tools: ping, list_capabilities, read_synthetic_context, get_status. Независимые fixture nonce/canonical content hash, server receipt и actual JSON seed/tree hash сверены; read не меняет storage. Дополнительно двенадцать concurrent запросов, Unicode executable path и real SDK cancellation fault probe.

Регрессия `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/runs/regression-20261024-012158-837df4bd/results.json`: **63/63 MCP checks и 24/24 security methods**, новые outputs только в этой TASK. Это новые прогоны исполнителя, не independent PASS и не Desktop E2E.

Отрицательные проверки охватывают missing/remote/occupied/wrong peer/name/owner/session/MAC/protocol, foreign TASK, unknown tool/type/extra, oversize/partial/slow/unresponsive, replay/duplicate/correlation, EOF/crash и owned cleanup. TCP mutant замечен OS sampler и owned accept; wrong-peer mutant действительно передал запрос постороннему controlled endpoint, что дало ожидаемый inner policy FAIL. Exact selectors и пределы — tests.md.

Сохранены первоначальные FAIL: неверные SDK snake_case aliases в harness; неподдерживаемый CreateNamedPipe dwOpenMode (WinError87) в новом коде; ошибочный pin Python venv launcher вместо реального peer image в fault harness. Guard при последнем правильно отказал и не ослаблялся. Source review также исправил startup job race, выбор первого terminal event, привязку authority session и Unicode image lookup. Все старые результаты остаются в evidence/attempt_catalog.json. Ранние полные intermediate source snapshots отсутствуют; их hashes/diagnostics есть, полный финальный snapshot есть.

## MANUAL ENGINEERING REVIEW и ограничения

Отдельный разбор — manual_engineering_review.md: duplex/deadlock/partial IO, identification impersonation/revert, ACL startup race, peer replacement/no reconnect, environment/secret inheritance, job-before-run, EOF/crash/watchdog, correlation/grant replay и portability. Финальный review прочитал actual final Relay/Native peer и сохранил конкретные открытые границы.

Не доказаны hostile same-user isolation, signing/loaded dependency closure, реальные cross-SID права, полный native Go graph и постоянный OS no-network observer. Pipe не закрывает все прочие IPC/BITS/COM/DNS delegation. Current-user config/grant delivery не является production credential boundary. У gateway фиксирован fixture layout, короткая bounded session и x64 Windows prerequisites; это не системный installer.

**F2 остаётся отдельным обязательным gate:** выделенный B-owned V2Ray HTTP CONNECT process должен владеть настоящим внешним socket → только approved literal R:Q, без DIRECT/fallback. Пользовательский V2Ray/SOCKS за B-wrapper не подходит. Код брокера/V2Ray, accounts, WFP/firewall, tunnel, системная сеть, production/Claude/LLM12 и старые отчёты не изменялись. 0 Go-client runs, 0 WFP calls, 0 real V2Ray/OpenAI requests, 0 ordinary ChatGPT calls. CanApply=false, Install/Uninstall BLOCKED, hosted HOLD.

## Provenance, документация и ротация

Windows10 build19045 x64, Python3.12.10/MCP2.2.0, existing Framework64 C#5. Начальная bounded inventory: 68 files; 65 unchanged, ровно три предусмотренных package edits. Секреты grant не записывались; named-field scan outputs выполнен. Никаких установок, повышения прав, network settings, Git/GitHub или внешних запросов.

Чтение адресное: правила собственной карточки/B1/B4; 08 актуальный маршрут; 34 current/MCP security; 01 runtime boundary; 19 §3–5/7.1–7.3 и профильные MCP findings; 37§9; 36/36.1 обязательные TEST-*; 36.2/36.3 изоляция/runtime gates; точные DOC-* в18 и зависимости; предыдущий MCP report/topology/gates/manual-review и затронутый код. Личные исторические архивы не читались и не индексировались. Source reference координатора не считается checked commit.

Ротация выполняется после сохранения report/checks/manifest отдельным single-use rotate_card.py: exclusive append к своему001, bounded readback только добавленного диапазона, exclusive card lock/readback/rollback, окно пяти TASK и byte-exact БЛОК4. Фактический статус, offset/length/new-entry digest и B4 before/after — evidence/card_rotation.json; manifest обновляется после ротации. Старые байты архива не читаются и не перезаписываются. При drift ротация блокируется, БЛОК1 не очищается.

**Фактическая ротация:** CARD ROTATION VERIFIED; 27527 новых байт, archive_old_bytes_read=0; БЛОК4 byte-exact сохранён.


**DOC IMPACT / SHARED DOC DELTA: DOC CLOSEOUT INCOMPLETE (общий контур координатора).** Общие документы не изменены. WEB_11 после независимой проверки предлагается обновить19/34 о bounded NPFS candidate, 36.1/профильный каталог о selectors; сохранить F2 и все live gates. Общий18 ещё описывает старый full B2/B3, собственная карточка имеет приоритетный USER GO2026-10-23 на001+пять summary rows; требуется координируемое уточнение18 и устаревших ссылок@1 на verifier@2. Самостоятельно общий регламент не правил. Полный DOC CLOSEOUT остаётся за координатором.

**NEXT SAFE ACTION:** пользователь передаёт/публикует комплект WEB_11 для независимого source/evidence review. Дальнейшие lab/cross-SID/WFP/B-egress/hosted/ordinary Chat этапы — отдельные адресные USER GO, см. next_user_go.md. Автоматической независимой приёмки или прямой доставки в другой чат не заявлено.
