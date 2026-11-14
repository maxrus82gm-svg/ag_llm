# H34 — GigaChat REAL readiness / S3b

Статус: **AUTHOR RESULT READY / BOUNDED OFFLINE PASS / AWAITING INDEPENDENT VERIFICATION**.
TASK ID: `CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001`.
Дата: 2026-11-14. Исполнитель: Codex 007. Workspace: `M:\GitHub\ag_llm`.
HISTORY ID выдаёт только штатный finish: [task_record.json](task_record.json), [closeout.json](closeout.json), [handoff_task.md](handoff_task.md). После регистрации SHA этого report не меняется.

Семь legacy LLM-send подключены к единому защищённому OFFLINE-адаптеру: final bytes → S2/S3a reserve/SENT/readback → H33 HTTP MockTransport → terminal/readback → существующий parser и provider events. Подготовлены серверные owner/attempt/profile-контракты; REAL и настоящий OAuth остаются закрыты. Это авторская ограниченная OFFLINE-сдача, не независимое принятие полного S3b/S3c/S9/S13a и не разрешение LIVE.

## Основание и REUSE CHECK

Назначение из БЛОКА 1; №08/18, актуальные №34/40, №37 §2.1–2.2/§3а, №20 §5а, открытые FOLLOWUP №05, №22 Windows CI, №36.1/36.3 и TEST-ENG-01. Принятые H32/H33 и локальный review WEB29 изучены. Независимый H33 run 43478748679 — факт из переданного review; автор H34 не обращался к GitHub.

Заявленная база `main@f50d5432228fdfc5ad67999f7620b9fb64bf1a49` / №594 — ориентир координатора. Git/HEAD/branch/status не проверялись: полномочий нет. Восемь H33 исходных fingerprints совпали точно: [base_fingerprints.json](evidence/base_fingerprints.json). Чужие версии не перезаписывались.

Переиспользованы: единственный Model Registry, provider_accounting snapshot/attempt IDs, Ordinary validators/extract_usage, S2 serializer/policy, S3a BudgetLedger, shared writer, Run Store, H33 HTTP transport и H32/H33 Turn/RAW/usage/settings. Policy/ledger/Run Store/context/Registry не изменены, второго OAuth/cache/core/history/budget нет.

Новым нужен только `gigachat_admission.py`: старые семь функций создавали HTTP-клиенты и повторно кодировали dict, а H33 authority привязана к text-only Turn. Agent/tool/compressor payload и существующая Run identity не являются Ordinary PreparedRequest. Минимальный адаптер связывает их с тем же ledger и тем же H33 byte boundary; собственных парсеров модели, storage engine или финансового кошелька он не создаёт. ProviderProfile — immutable evidence/caps overlay, сверяемый с исходным Registry, не новый каталог моделей.

## Изменения и маршруты

До инженерных правок создана [инвентаризация](route_inventory.md). После интеграции семь исходных `.post`-точек являются входами guarded client; фактическая HTTP-граница общая — H33 `client.stream(content=wire)` с точным MockTransport. Наличие `json=body` на входе legacy client означает сериализацию **до** admission; после admission передаются только готовые bytes.

| Физическая исходная точка | Фиксированный маршрут / scope | Результат H34 |
|---|---|---|
| server.ask_gigachat | mcp_chat / MCP | Общие admission/ledger/HTTP, default без owner запрещён |
| server._run_agent_task_impl | executor / RUN | Привязка к настоящему существующему Run после Audit recorder; policy/Final Audit context и текущий provider_attempt_id |
| server._request_audit_diagnostic | audit_diagnostic / RUN | Произвольный injected client отвергается; только точный guarded parent того же owner. Отказ клиента попадает в terminal-событие |
| planner_runtime.PlannerSession.call | planner_session / RUN | Сохранены session transcript/repair и parser; fresh admission на каждую попытку |
| planner_runtime.run_planner | planner_direct / RUN | Даже legacy direct/unreachable label не обходит gate |
| verifier_runtime._request_gigachat | verifier_final / verifier_permission / planner_review / RUN | Purpose задаёт доверенный caller, ограниченный набор маршрутов; parser/errors прежние |
| compressor_runtime._request_gigachat | compressor / отдельный scope | Общий ledger и byte transport, существующие compressor events/usage |

OAuth POST остаётся отдельной не-LLM точкой в существующем gigachat_transport. Guard `require_real_authority()` безусловно отказывает **до cached token, env и HTTP**. Отрицательные проверки вызывают сам getter и получают отказ; реальных OAuth HTTP-вызовов нет. Raw auth data убраны из missing-token error. Legacy placeholder — фиксированный synthetic string, не второй OAuth/cache; фактическая fixture token boundary H33 вызывается только после SENT.

Изменены 7 существующих production-файлов: четыре legacy runtime, gigachat_transport, ordinary_gigachat_transport и только repr-поле ProviderResponse в ordinary_chat_service. Добавлен один admission adapter. В H33 изменён только список точных допустимых authority types. В legacy ошибках убраны raw response/непроверенный finish_reason, классы ошибок и успешные payload/parser-сценарии сохранены. ProviderResponse repr скрывает data, чтобы asyncio debug не печатал неизвестные поля ответа.

Тесты S1/S2 согласованы адресно: известный guarded factory, точные AST/reference pins нового gateway и H33 adapter, один новый pinned OFFLINE ingress. Весь production import graph по-прежнему сканируется. Новая source-проверка отдельно запрещает возвращение raw AsyncClient/OAuth во все семь функций. Unknown consumer/gate/endpoint mutations остаются RED.

## Авторитет, byte boundary и recovery

1. Допустим только exact synthetic fixture и explicit TEMP root с уже enrolled S3a ledger. Send/owner entry не вызывают initialize/adoption/reset. Неизвестный/старый/corrupt/capacity-limited ledger отказывает.
2. Server owner проверяет Workspace/Run/Chat через существующий Run Store, сохраняет nonce/state/policy/profile/Final Audit binding под shared writer. Повторный/параллельный owner и неоднозначная история не переоформляются молча. CLOSED metadata проверяется по версии, полному набору полей, identity и отсутствию inflight.
3. На каждый вызов проверяется существующий provider snapshot: Registry/model, роль, canonical snapshot hash/length. Выбранная модель или body после учётного snapshot не подменяются незаметно. У MCP/direct без metadata identity детерминирована внутри серверного owner; replay старой попытки запрещён.
4. Final wire связан с endpoint/profile/policy/Run/Chat/attempt. Reserve и fresh SENT проверяются exact receipt + durable readback. Поддельный/replayed ACK не является authority. Только одна inflight попытка на Run owner; несколько независимых Run не превращаются в глобальную квоту Workspace.
5. H33 передаёт `content=wire`, доверенные headers/endpoint, trust_env=False/redirects=False. У фактического MockTransport ещё раз проверяются request method/URL/content, owner/ledger/SENT, профиль, deadline и отмена. Config/URL/UI/env/Boolean и произвольный transport не создают REAL client.
6. Transport выполняется отдельной async task: callback может uncancel себя, но не erase cancellation родительского caller. Late/cancelled answer не публикуется; supplied validated usage сохраняется для учёта. Нет refresh/retry после SENT/UNKNOWN.
7. Terminal outcome/usage коммитятся и перечитываются до возврата response старому parser. Lost/fake terminal ACK, другой owner и crash не превращаются в SUCCESS. RESERVED/SENT/UNKNOWN не становятся нулём, liability не освобождается автоматически.
8. Clean reopen может читать завершённые факты, но не повторить старый attempt. Fresh Python process при unresolved durable owner/SENT получает отказ. Настоящая hardware power-loss/OS durability и operator reconciliation остаются самостоятельными gates.

H29 per-chat настройки и usage не менялись. Missing/partial/invalid usage остаётся UNKNOWN. Использованы общий Ordinary validator и S2 validate_usage; корректный supplied precached count сохраняется, отсутствие cached не подменяется нулём. Реальные cached/reasoning/billing semantics UNVERIFIED, поэтому реальные профили не принимаются. Старый provider-event observer может потерять свою summary при ошибке; независимый S3a ledger всё равно сохраняет допущенную попытку/usage. Этот reporting gap отмечен, а не выдан за полный учёт всех agent routes.

## MANUAL ENGINEERING REVIEW

Перечитаны семь producer функций, общий gateway, H33 transport, OAuth/cache gate, S2 scopes/usage/terminal, S3a reserve/replay/readback и Run Store owner updates. Прослежены нормальный путь и сбои до reserve, после reserve, после SENT, в token await, у HTTP, между terminal ACK/readback и при повторном owner.

Отвергнуты варианты: новый OAuth/ledger/chat core; injection произвольного HTTP client; доверие JSON receipt/Boolean; legacy allow shim ради старых тестов; автоматический reset/migration; принятие H29 preferences за caps. Вместо них — один exact-type server adapter и существующий физический H33 boundary.

Review выявил и исправил два подтверждённых дефекта первоначальной H34 ветви: body/model могли смениться после provider snapshot, callback мог подавить cancellation в том же task. Новые реальные negative tests сначала дали **2 FAIL** (`review_red`), затем **2 PASS** (`review_green`). Добавлены snapshot/model/role validation и separate transport task/parent cancellation count. Исходные RED сохранены.

Дополнительно закрыты: terminal event при отказе audit client; timeout, подавленный поздним callback; правильное сохранение HTTPX legacy 2xx semantics; raw provider fields в ошибках/repr; strict version/identity check CLOSED owner. Проверены replay, fake reserve/SENT/terminal, wrong wire/URL/owner, cancel в трёх фазах, два owner и свежий процесс, malformed/corrupt/old ledger, capacity и неизвестный usage. Тесты утверждают actual bytes/ledger state/liability/readback, не только возвращённый enum.

Динамические paths: Ordinary exact in-memory и HTTP authorities сохранены; injected diagnostic client закрыт. ModelCards по умолчанию LiveCheckNotAuthorized, supplied checker является отдельным privileged server extension и не получает H34 capability от своего authorized Boolean. Наличие custom Python checker не означает общую S3b-защиту любого кода процесса. S1 source census, lookup aliases и quality negative controls остаются включены; arbitrary privileged Python/все расширения не объявляются sandboxed.

Открыто: реальная сеть/TLS/OAuth semantics; проверенные caps/calibration; full-program S3b и дополнительные dynamic extensions; полный S3c/S9/S13a; old audit adoption, RAW privacy/retention, capacity strategy, hardware fencing; legacy observer reporting и физический CMD/F5. Все перечислены в [real_readiness.md](real_readiness.md), не замаскированы локальными PASS.

## Проверки и evidence

Точные команды/версии, collection, stdout/stderr, guard events, SHA и expected RED transcripts сохранены в evidence и manifest. [Windows reproduction](windows_reproduce.md). Guard установлен до runtime imports, Python children наследуют его; plugins отключены, credentials не передаются. Только synthetic TEMP/loopback; реальных внешних/OAuth/платных HTTP — 0.

| Набор | Результат | Evidence |
|---|---|---|
| Полная legacy/admission/parser/agent regression | 244 PASS +110 subtests, exit0, guard0 | clean_legacy.result.json/cases/stdout/stderr |
| H29/H31/H32/H33/common core/S3a/Turn/Run Store | 254 PASS +256 subtests, exit0; 1 Tk cleanup warning | final_h33.result.json/cases/stdout |
| После последней strict CLOSED-owner правки: H34+H33 | 49 PASS +85 subtests, exit0, guard0 | post_review.result.json |
| Финальный oracle семи отказов: проверка именно admission cause | 1 PASS +7 subtests, exit0, guard0 | oracle_final.result.json |
| S1 dedicated acceptance | 69/69 PASS, exit0; matching historical RAW pins | post_s1.result.json/unittest.txt |
| S2 dedicated core | 73/73 PASS, exit0, isolation0 | post_s2.result.json/unittest.txt |
| Existing H25 + H34 gate quality | 52 PASS +6 subtests, exit0, guard0 | post_quality.result.json |
| Node UI | 57/57 PASS, exit0 | node.stdout.txt/result.json |
| Existing python_compile + ui_smoke_test | 8 changed production files compile PASS; real UltraApp constructor in TEMP PASS, guard0 | sealed_server_gates.result.json |
| Три weakening controls | 3 expected RED, 0 errors; outer exit0, sources unchanged | sealed_mutations.result.json, failure transcripts |

Наборы пересекаются и не суммируются. Общая H33 regression выполнена повторно после repr/ошибок; единственная последующая production-правка — более строгий readback CLOSED legacy owner — отдельно покрыта всем H34/H33 набором, S1/S2/quality и последним широким прогоном.

После широкого прогона усилен только test oracle семи отказов: теперь он дополнительно проверяет admission-код в cause chain, исключая ложный PASS из-за постороннего preflight error. Адресный повтор 1+7 PASS; production-код после успешных финальных проверок не менялся.

В S1 [physical trace](evidence/post_s1.physical_trace.json) — **20 Mock POST**, все девять logical routes семи source sites, перед каждым readback SENT. В H34 trace — девять synthetic route attempts с bytes/hash/model/endpoint/policy/terminal. Trace не содержит Authorization/токенов/RAW. URL в httpx Request не является сетевым соединением.

Слабые варианты budget DENY, actual HTTP wire check и terminal readback дают реальные assertion failures: соответственно 1/1/2, без ошибок. Это expected RED, не regression FAIL. Диск production исходников не менялся при мутациях.

История FAIL/ограничений сохранена:

- initial: 15 base PASS +24 subtests, 1 failed subtest и 1 failed base test — нормализация invalid policy error и слишком короткий тестовый deadline до SENT; исправлены без ослабления gate.
- s1_initial: 69 выполнены, 5 errors — старые fixture roots были sibling от нового strict TEMP, исправлен только fixture path. s1_second и последующие 69 PASS.
- contracts1: 83 PASS +61 subtests, 2 FAIL — два parser-only audit tests передавали raw FakeClient, теперь явно mock trusted seam; отдельно реальный injected client проверяется отрицательно.
- compatibility2: timeout240, INCOMPLETE; унаследованный runner не сохранил partial output. Дефект runner исправлен: progress/current node, сохранение timeout output и exit124, bounded600. Counts этого незавершённого запуска неизвестны и не включены в PASS.
- legacy_final: 240 assertions PASS, но 10 неожиданных блокировок non-Python process у пяти старых Git-fallback tests; outer runner exit1. final_legacy: 243 assertions PASS, ещё 4 таких отказа у двух самостоятельных fixtures; тоже outer exit1. Ни один Git process не стартовал. Все пять сценариев теперь явно подменяют unavailable Git; адресный repair 2 PASS/guard0. Это не expected guard controls и исходные failures не удалены.
- server_gates1: до child запуска guard запретил копирование credential env старым helper; значения не возвращены, compile/UI тогда NOT RUN. Runner удаляет GIGACHAT_* ключи по имени до guard/import, не извлекая values. sealed_server_gates PASS/guard0. Из-за -E/PYTHONPATH suppression исходного helper guard явно установлен в child bootstrap; сам app/helper не подменён.
- Tk __del__ `main thread is not in main loop`: 1 warning в H33 broad suite, assertions PASS. Tk source неизменен; предупреждение сохраняется как ограничение старого combined test, не исправлено вне scope.

Последний clean_legacy завершён: 244 PASS +110 subtests, effective exit0, неожиданных guard denials 0. В итоговых валидных наборах неожиданные guard denials равны 0. В H33 broad suite ровно 9 ожидаемых отрицательных probes у трёх прежних exact node IDs. Старый JSON exit_code в pre-fix legacy artifacts — код pytest; outer runner exit1 определяется unexpected denials. Новые runner поля различают pytest и effective runner exit; manifest не считает такие этапы PASS.

## Сохранность и ограничения

Перед правками сохранена SHA-256-копия в `C:\Users\REX\AppData\Local\Temp\codex-h34-backup-w31lp2xr`. Первоначально 20 файлов, до отдельного repr edit добавлен неизменённый original ordinary_chat_service: **21 backup**, SHA readback. Копию сохранять до независимой приёмки; H30/H31/H32/H33 TEMP backups не читались/не удалялись/не заменялись.

**162 protected файла** сверены неизменными: нормативные документы, STANDARD/TEST configs и CMD, Tk, существующие web Turn/RAW/usage, policy/ledger/Run Store/context/Registry и CI. STANDARD active=standard; TEST ordinary-core-offline плюс stage5-offline rollback. Launcher/ярлыки/рабочий сервер не переключались, production Workspace не записывались. S1 исторические RAW читались по его разрешённому pinned contract без изменений.

Фактический код меняет поведение unowned legacy send: он теперь отказывает до OAuth/HTTP, включая внутренние MCP/Tk вызовы без server authority. UI/архитектура STANDARD/Tk не редактировались. Разрешённые synthetic сценарии сохраняют body/parser/event contracts. Непроверенный REAL не оставлен как compatibility bypass.

NOT RUN: реальные OAuth/API/внешняя сеть/расходы; Git/GitHub status/read/commit/push; независимый H34 Windows CI; физический CMD/Chrome/F5 и чистая Windows; S2 provenance; production adoption/migration/compaction; реальная durability/power loss/TLS/rate-limit/account checks; полное независимое S3b/S3c/S9/S13a. Синтетические caps — не real model facts. Общего бюджета Workspace не добавлено.

## DOC IMPACT и NEXT

Координатору после независимой приёмки: factual bounded 7-site OFFLINE результат в №001/05/34/40 и БЛОК 4; не объявлять FULL S3b/Stage6/Stage7/LIVE. Сопоставить S3B-S3C-S9, STATIC-DYNAMIC-COVERAGE, S2-STATIC-IMPORT-COVERAGE, S3A-ADOPTION-UPGRADE/CAPACITY/DURABILITY-FENCING/RAW-WIRE-RETENTION и FOLLOWUP-WUA-H32-S1-RAW-CI-001/H32-REAL-CONTRACT-001/H33-SERVER-REAL-AUTHORITY-001/H31-PHYSICAL-SMOKE-001. Эти OPEN автор не закрывал. Дополнительно отметить legacy observer reporting и Tk combined-test cleanup warning.

NEXT: пользователь публикует единый комплект; независимый verifier запускает точные Windows OFFLINE-наборы с source SHA/run ID/artifact, проверяет source/diff/pins/expected RED и replay. Затем подтвердить контракт одной выбранной модели и согласовать отдельный server REAL factory/authority шаг с применимыми predecessor gates. Первый реальный запрос — только после их принятия и отдельного OWNER GO с endpoint/model/attempt/output/timeout/stop limits. Backup пока хранить. Автор не выполняет публикацию и не назначает successor автоматически.
