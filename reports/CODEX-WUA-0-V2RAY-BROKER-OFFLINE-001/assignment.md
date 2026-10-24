# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# 🟨 CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001

## Разработать выделенный V2Ray-брокер со строгой сетевой политикой для подключения ChatGPT MCP

Уважаемый агент 007 (Codex)!

Назначаю следующую практическую инженерную задачу по развитию Web Alarm Ultra и внешнего MCP-подключения ChatGPT.

**Исполнитель:** Codex 007  
**Координатор и независимый verifier:** ChatGPT WEB_11  
**ARCH CLASS:** Web Alarm Ultra / ChatGPT MCP / V2Ray Egress / Windows Identity Isolation  
**Исходный reference:** `ag_llm/main@1147d283674f60ad94dd0be4b26f49e751523669`

Reference указан координатором; он не предоставляет локальному Codex разрешение использовать Git/GitHub.

### 1. Основание и цель

Предыдущая задача `CODEX-WUA-0-MCP-NOTCP-NPFS-001` подготовила локальный исполняемый MCP-мост:

`MCP SDK → STDIO → C# relay → Windows Named Pipe → U gateway → synthetic WebAlarmApi`.

Результаты исполнителя: 24/24 NPFS tests, 63/63 MCP regression checks, 24/24 security tests. Независимая документально-кодовая проверка WEB_11 подтвердила существование 1404 manifest-listed paths и 10/10 выборочных SHA-256. Это **ограниченная приёмка source/evidence**, не независимый прогон Windows и не production approval.

Решение первого конфликта F1 существенно продвинуто: C-side relay больше не требует Python asyncio и его динамического TCP loopback-соединения.

**Сейчас необходимо практически проработать второй конфликт F2: кто действительно владеет внешним V2Ray-соединением.**

Недопустима схема, в которой `wua-broker` лишь передаёт данные обычному пользовательскому V2Ray. При такой конструкции настоящий внешний сокет принадлежит пользовательскому процессу, а WFP-правила для `wua-broker` не ограничивают его.

**Цель TASK:** подготовить переиспользуемый, проверяемый offline-комплект для будущего выделенного V2Ray engine, работающего под собственной непривилегированной Windows identity `wua-broker` и поддерживающего обязательный профиль `STRICT_V2RAY_BROKER`.

Нужны код, versioned contracts, конфигурация кандидата, validators, настоящие изолированные тесты и доказательные negative controls. Не ограничиваться архитектурным текстом.

### 2. Матрица чтения

Использовать актуальные локальные документы адресно.

|Источник|Точный раздел / смысл|Режим|
|---|---|---|
|`Документация/000_Задачи Codex.md`|Правила, активный БЛОК 1, последний БЛОК 4|Обязательно|
|`Документация/08_Старт.md`|Текущий стартовый маршрут|Адресно|
|`Документация/34_TACTICAL_CONTEXT.md`|CURRENT / MCP / identity / network gates|Адресно|
|`Документация/01_Архитектура и текущее состояние.md`|Соответствующая Web Alarm/Ultra authority|Адресно|
|`Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|§3–5, §7.1–7.3 и конкретные Secure Tunnel amendments|Обязательно|
|`Документация/37_Старт перехода - Web Alarm Ultra.md`|§9, ChatGPT ↔ Ultra|Обязательно|
|`Документация/36_Единая архитектура тестирования.md`|Общий цикл и различение тестовых сред|Адресно|
|`Документация/36.1_Обязательный регламент тестирования для LLM.md`|TEST-COLLAB, AREA, ENG, DEV, COV, EXEC, QA, EVID, SCOPE|Обязательно|
|`Документация/36.3_Профиль тестирования Ultra.md` и применимые положения 36.2|Integration/runtime isolation|Адресно|
|`Документация/18_Регламент сопровождения документации.md`|DOC-GIT-01@1, DOC-PARALLEL-01@1, DOC-LOCAL-REPORT-HANDOFF-01@1, DOC-TASK-READ-SCOPE-01@1, DOC-HISTORY-ACCESS-01@1, DOC-VERIFIER-BLOCK4-01@2, DOC-TASK-BLOCK1-01@1|Только точные определения и необходимые зависимости|
|`reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001/`|`topology.md`, `connection_gates.md`, `manual_engineering_review.md`|Обязательно, адресно|
|`reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/`|`report.md`, `topology.md`, `pipe_security.md`, `next_user_go.md`|Обязательно, адресно|
|`integrations/wua_chatgpt_mcp/`|Текущие route contracts, тесты, diagnostic и NPFS-компоненты|Затронутые файлы|

Не читать весь глобальный регламент либо `000_Задачи для агента.md` механически.

Исторические `001_История выполненных задач Codex.md` и архивы других агентов **не читать, не искать и не индексировать**. Исключение — собственная ограниченная append-only запись по завершении TASK.

### 3. Неизменная целевая конструкция

В будущей установленной системе:

**C —** `**wua-client**`**:**

- Официальный OpenAI tunnel-client.
    
- Исходящее сетевое соединение только к точно разрешённому `127.0.0.1:P`.
    
- Локальный MCP через уже подготовленный STDIO/NPFS relay.
    
- Никаких DIRECT, альтернативных proxy routes и широкого TCP allowlist.
    

**B —** `**wua-broker**`**:**

- Отдельный непривилегированный Windows SID.
    
- Отдельный проверенный V2Ray engine process.
    
- Этот же B-owned процесс принимает HTTP CONNECT на выделенном loopback endpoint `P`.
    
- Этот же процесс осуществляет внешний TCP egress к единственному разрешённому upstream `R:Q`.
    
- Никакого внешнего socket под SID основного пользователя или стороннего помощника.
    

**U — Web Alarm Ultra:**

- Владеет серверными задачами, разрешениями и read-only MCP authority.
    
- Не передаёт C/B системные привилегии или произвольные команды.
    

`P`, `R`, `Q`, SID и идентификаторы экземпляров — параметры будущего target-host discovery. Не переносить их слепо с рабочего компьютера.

Оставить отдельными три независимых подтверждения: функционирование локального MCP, реальный маршрут V2Ray и фактическое WFP enforcement.

### 4. Проверить возможность выбранного V2Ray engine

Перед реализацией конфигурации определить, какой **конкретный движок и версия** могут поддержать целевую схему.

Использовать только уже доступные разрешённые локальные source/docs/binary metadata, прежде всего существующие материалы проекта. Допускается bounded read-only обследование точных заранее известных путей к установленному engine, но не чтение рабочих конфигураций, подписок, секретов или профилей V2Ray.

Не скачивать и не устанавливать новый engine.

Установить по проверяемому материалу:

1. Поддерживается ли нативный HTTP proxy inbound с CONNECT.
    
2. Как задаётся единственный удалённый outbound и фактический next hop `R:Q`.
    
3. Как исключаются DIRECT, `freedom`, альтернативный outbound, proxy chain, load balancer и fallback.
    
4. Возможны ли скрытые DNS, UDP, IPv6, routing resolution, health, telemetry и companion connections.
    
5. Как устроены routing precedence и поведение при отсутствии правила.
    
6. Можно ли использовать отдельный локальный config/root без обращения к пользовательскому профилю.
    
7. Как будут подтверждаться executable version/hash, loaded config и effective Windows token.
    

**При отсутствии подходящего проверенного engine/source не выдумывать конфигурационный синтаксис.**

В таком случае сдать versioned candidate contract и validators, а соответствие настоящему движку отметить `ENGINE_CONFIG_COMPATIBILITY_BLOCKED`.

Нельзя автоматически заменять V2Ray на другой network engine или proxy stack: это отдельное архитектурное решение пользователя.

### 5. Реализовать минимальный отдельный broker package

В существующем `integrations/wua_chatgpt_mcp/` создать компактный самостоятельный модуль будущего B-owned broker profile.

Требуются:

- Versioned schema целевой топологии.
    
- Strict configuration validator.
    
- Disabled template для выделенного engine.
    
- Offline preflight с проверяемым отказом.
    
- Read-only health/status contract.
    
- Source/config hash binding.
    
- Контроль владельца процесса и expected SID на уровне требований/структурированных аттестаций.
    
- Контроль допустимых inbound/outbound endpoints.
    
- Отсутствие автоматической смены proxy, IP, порта, учётных данных или policy.
    
- Понятные причины блокировки.
    

Использовать готовые `security_contract.py`, `diagnostics.py`, route tests и общие strict-функции там, где это оправданно.

**Архитектурная экономия — обязательный критерий.** Не плодить второй независимый валидатор тех же параметров, не копировать существующий CONNECT→SOCKS adapter в production engine и не создавать большой слой абстракций для одной функции.

Если новый модуль заметно усложняет существующий код, объяснить, почему существующие механизмы нельзя переиспользовать.

### 6. Разделить конфигурацию и доказанное поведение ОС

Данные будущего профиля должны описывать:

- Expected B SID, owner и process/image pin.
    
- Точный локальный HTTP CONNECT endpoint `127.0.0.1:P`.
    
- Единственный upstream destination `R:Q`.
    
- Тип и защищённую идентичность remote upstream.
    
- Строго запрещённые направления и fallback.
    
- Условия старта и остановки.
    
- Зависимости от будущей WFP-policy.
    
- Source, binary, config generation и ревизии.
    

Но **валидный JSON/config не подтверждает реальный token, route или WFP**.

Нужны различимые состояния:

- `BROKER_PROFILE_STRUCTURALLY_VALID`
    
- `ENGINE_VERSION_SOURCE_VERIFIED` либо `BLOCKED`
    
- `ENGINE_CONFIG_COMPATIBILITY_VERIFIED` либо `BLOCKED`
    
- `B_IDENTITY_NOT_PROVISIONED`
    
- `B_EGRESS_OWNER_NOT_VERIFIED`
    
- `V2RAY_LIVE_ROUTE_NOT_VERIFIED`
    
- `WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED`
    
- `HOSTED_TUNNEL_ON_HOLD_BY_USER`
    

Даже все положительные offline-результаты не должны снимать `can_apply=false` и `can_start_tunnel=false`.

### 7. Исполняемая offline test suite

Тесты проводить только в новом принадлежащем TASK fixture-root с собственными контролируемыми loopback endpoints.

Никаких внешних соединений, публичных IP, реального upstream или рабочего V2Ray.

Подготовить synthetic model выбранного B-owned маршрута и независимые fault oracles:

**Положительные случаи:**

- Единственный CONNECT inbound.
    
- Единственный разрешённый outbound к собственному test receiver.
    
- Проверяемая принадлежность соединения заявленной synthetic role.
    
- Передача запроса и получение независимого receiver receipt.
    
- Правильное закрытие потока и освобождение ресурсов.
    

**Отрицательные случаи:**

- Отказ upstream, listener и peer.
    
- Неожиданный DIRECT или второй proxy.
    
- Подмена source/destination, IP, port или протокола.
    
- Неверный owner/SID в конфигурационном контракте.
    
- Переход к существующему пользовательскому SOCKS.
    
- DNS lookup или hostname вместо разрешённого literal endpoint.
    
- Неожиданный UDP/IPv6 route.
    
- Port takeover, configuration drift, replay и stale attestation.
    
- Extra child/companion engine.
    
- Отказ во время handoff, partial CONNECT, timeout и restart.
    
- Попытка активировать профиль через fake signed-looking JSON или `all_approved=true`.
    

**Обязательные mutations:** намеренно внести в синтетический код/конфигурацию как минимум обход через DIRECT и передачу egress другому owner. Тестовый oracle должен действительно обнаружить оба нарушения.

Не выдавать synthetic owner label за Windows access token proof. Проверка реального B-owned socket требует отдельной лаборатории и разрешения.

Если найденные угрозы требуют новых native-тестов, сохранить их точные selectors и prerequisites, но не запускать их на рабочей Windows.

### 8. Безопасность и разрешённые операции

**Write scope:**

- `integrations/wua_chatgpt_mcp/` — только новые или адресно необходимые файлы модуля брокера, конфигураций и тестов.
    
- `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/` — отчёт и evidence.
    
- `Документация/000_Задачи Codex.md` — только собственная регламентная ротация БЛОКОВ 1–3, БЛОК 4 READ-ONLY.
    
- `Документация/001_История выполненных задач Codex.md` — только append-only новая запись собственной TASK и точечный readback добавленных байтов.
    

**Read-only:** существующий NPFS, прежние WFP/toolkit/lab packages, Web Alarm production, общая документация, CI, чужие задачи и материалы Claude.

Если потребуется изменить уже реализованный NPFS, исходники Web Alarm или общую production security policy, сначала зафиксировать необходимость и запросить отдельный scope.

**Категорически запрещено без нового USER GO:**

- Создавать настоящие учётные записи `wua-client`, `wua-broker`.
    
- Менять SID/ACL, Windows Firewall/WFP/BFE или системные маршруты.
    
- Читать или менять рабочие V2Ray profiles, subscriptions, tokens.
    
- Запускать существующий V2Ray или новый настоящий engine с реальными сетевыми возможностями.
    
- Создавать системные службы, автозапуск, listener вне собственного локального fixture.
    
- Открывать туннель или обращаться к OpenAI Platform.
    
- Изменять системный proxy, DNS, VPN, Execution Policy.
    
- Устанавливать ПО, скачивать binaries, делать Git/GitHub operations.
    
- Запускать host-wide scans и тесты с настоящим внешним сетевым трафиком.
    
- Использовать пользовательские пароли/ключи в отчёте или репозитории.
    

Разрешены собственные временные процессы и loopback fixtures для тестирования реализованного offline-кода. Действующую сетевую конфигурацию Windows не изменять.

Не пытаться запускать настоящий engine только ради зелёного результата. Точная реальная совместимость может остаться `BLOCKED`.

### 9. Регрессия и самостоятельный review

Провести:

1. Проверку schemas, static/syntax и version compatibility.
    
2. Новые broker tests с положительными и отрицательными сценариями.
    
3. Targeted mutation controls.
    
4. Адресную регрессию существующего strict profile и MCP components, без перезаписи старых evidence.
    
5. Проверку, что NPFS, toolkit и WFP activation gates остались заблокированными.
    
6. Полный manual engineering/adversarial review изменённых исходников.
    

Самостоятельно исследовать routing precedence, fallback, DNS delegation, source ownership, startup/restart, process inheritance, config substitution, partial connect, pre-existing flows, loss of observers и race между проверкой конфигурации и запуском.

Если дефект обнаружен внутри разрешённого scope — исправить и добавить regression. Вне scope — зафиксировать FINDING/PROPOSAL без самовольных изменений.

Сохранить реальные initial FAIL и разграничить исправленный test defect, code defect и блокер отсутствующей среды.

### 10. Обязательные результаты

В `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/` сохранить:

- `report.md` — полный фактический итог.
    
- `README.md` — воспроизводимый запуск offline-тестов.
    
- `engine_compatibility.md` — версия/источники и уровень достоверности.
    
- `strict_broker_topology.md` — процессы, SID, локальные и внешние соединения.
    
- `security_boundary.md` — что доказано кодом, а что требует WFP.
    
- `broker_test_results.json` — точные тесты, counts, initial FAIL.
    
- `manual_engineering_review.md` — самостоятельная проверка.
    
- `next_user_go.md` — конкретные будущие prerequisites и разрешения.
    
- `manifest.json` — path, bytes, SHA-256.
    
- Необходимые source/config templates и evidence в соответствующих подпапках.
    

Исходники рабочего offline-комплекта — в `integrations/wua_chatgpt_mcp/`, а не исключительно в отчёте.

### 11. Критерии сдачи

Статус `RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11` допустим, когда:

- Есть исполняемый offline-комплект strict broker configuration/preflight.
    
- Реализована проверка одного inbound и одного допустимого upstream route.
    
- Принцип настоящего B-owned external socket закреплён в исполняемых контрактах.
    
- Неподходящая схема B-wrapper → пользовательский SOCKS отвергается.
    
- Отсутствуют неразрешённые DIRECT/fallback в тестовом кандидате.
    
- Негативные тесты действительно выявляют запрещённый выход/owner mismatch.
    
- Использованы существующие компоненты без неоправданного дублирования.
    
- Предоставлены источники совместимости конкретного engine либо явный `BLOCKED`, если их нет.
    
- Реальные Windows accounts, WFP, V2Ray, OpenAI и hosted tunnel не запускались и не менялись.
    
- Есть полный report, evidence, manifest.
    

Не объявлять `B_EGRESS_OWNER_VERIFIED`, `V2RAY_ROUTE_VERIFIED`, `HOSTED_TUNNEL_READY` или `PRODUCTION READY` по синтетическим тестам.

### 12. Ротация, история и handoff

После окончания:

1. Сохранить полный factual report и manifest.
    
2. Append-only добавить исходную TASK, AMENDMENT, результат и locator в собственный `001_История выполненных задач Codex.md`.
    
3. Проверить только добавленную новую запись.
    
4. Сохранить максимум пять последних кратких TASK/результатов в БЛОКАХ 2–3.
    
5. БЛОК 4 независимого verifier сохранить побайтно.
    
6. Освободить БЛОК 1 только после успешной проверки.
    

Не делать Git/GitHub commit/push. Публикация — пользователь, независимый review — WEB_11.

**Итог в чат:** один компактный блок: TASK ID, результат, что реально реализовано, тесты и mutations, compatibility status, обнаруженные риски, DOC IMPACT, NEXT SAFE ACTION.

**Приоритет:** получить инженерно полезный, компактный и проверяемый V2Ray-брокерный комплект, который позже можно будет безопасно подключить к уже готовому MCP/NPFS контуру без пересмотра всей конструкции.

---

