# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# 🟨 CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001

## Независимая техническая идентификация sing-box / V2Ray Core и offline-проверка совместимости со строгим MCP-брокером

Уважаемый агент 007 (Codex)!

Продолжаем практическую разработку защищённого подключения ChatGPT к Web Alarm Ultra.

**Исполнитель:** Codex 007  
**Координатор/verifier:** ChatGPT WEB_11  
**ARCH CLASS:** Web Alarm Ultra / ChatGPT MCP / Proxy Engine Compatibility  
**Координаторский источник:** `main@d121bafb63cf7cbc6f2140a61b8799a5eb4621b1`

Независимое заключение WEB_11 по предыдущей задаче опубликовано отдельно в GPT-коммите `a7c24dd02916895e5166cd0e29dc74f5d454a7a8` (№402). Оно может ещё отсутствовать в локальной main-копии. Сведения для текущей TASK приведены ниже; обращаться к Git/GitHub самостоятельно запрещено.

### 1. Исходное состояние

Выполнены три последовательных этапа:

1. `CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001` — реальный локальный MCP SDK и синтетический WebAlarmApi.
    
2. `CODEX-WUA-0-MCP-NOTCP-NPFS-001` — C# STDIO ↔ Windows Named Pipe ↔ server-owned gateway.
    
3. `CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001` — disabled broker profile, preflight и same-process CONNECT loopback model.
    

По третьей задаче независимая проверка WEB_11: PARTIAL / BOUNDED OFFLINE ACCEPTED, 617/617 manifest paths, 12/12 выбранных SHA-256; сохранённые результаты Codex — broker 33/33, MCP 63/63, security 24/24. Независимый Windows test run не проводился.

**Остаётся важный конфликт:**

В историческом preflight от 17 октября оболочка `v2rayN.exe` запускала `sing-box.exe`. Это не подтверждённый V2Ray Core.

Ни точная установленная версия движка, ни соответствие исходникам, ни совместимость его конфигурации со строгой архитектурой пока не доказаны.

Статусы:

- `ENGINE_VERSION_SOURCE_BLOCKED`
    
- `ENGINE_CONFIG_COMPATIBILITY_BLOCKED`
    
- `B_EGRESS_OWNER_NOT_VERIFIED`
    
- `WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED`
    
- `HOSTED_TUNNEL_ON_HOLD_BY_USER`
    

**Цель нынешней TASK — устранить неопределённость конкретного движка, а не продолжать создавать абстрактные модели сети.**

### 2. Обязательная архитектура

Будущая схема остаётся неизменной:

- `wua-client` (C) — отдельная техническая Windows identity, официальный tunnel-client и C# MCP relay.
    
- `wua-broker` (B) — другая техническая Windows identity, выделенный proxy engine.
    
- B-owned engine принимает HTTP CONNECT на точно разрешённом `127.0.0.1:P`.
    
- Тот же B-owned процесс осуществляет фактический внешний egress к утверждённому `R:Q`.
    
- Отсутствуют DIRECT, неразрешённый proxy fallback, дополнительные сетевые выходы и автоматическое ослабление ограничений.
    
- Локальный MCP-мост использует STDIO и Windows Named Pipe, не создавая нового C-side TCP endpoint.
    
- Реальное применение SID/WFP пока заблокировано.
    

**Нельзя автоматически заменить V2Ray Core на sing-box или наоборот.** Выбор движка остаётся за пользователем после технического сравнения.

### 3. Матрица чтения

|Документ / источник|Что читать|Назначение|
|---|---|---|
|`000_Задачи Codex.md`|Правила, БЛОК 1, относящийся БЛОК 4|Текущая задача, права|
|`08_Старт.md`|Актуальный start и Git/roles|Вход|
|`34_TACTICAL_CONTEXT.md`|CURRENT и MCP security|Актуальные ограничения|
|`01_Архитектура и текущее состояние.md`|Ultra/MCP authority|Границы|
|`19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|§3–5, §7.1–7.4, если уже опубликован и локально доступен|Целевой транспорт|
|`37_Старт перехода - Web Alarm Ultra.md`|§9|Цель ChatGPT ↔ Ultra|
|`36_Единая архитектура тестирования.md`|CURRENT, тестовый цикл|Тестирование|
|`36.1_Обязательный регламент тестирования для LLM.md`|TEST-COLLAB/AREA/ENG/DEV/COV/EXEC/QA/EVID/SCOPE|Проверки и evidence|
|`36.3_Профиль тестирования Ultra.md`|Релевантная изоляция|Границы fixtures|
|`18_Регламент сопровождения документации.md`|DOC-GIT-01, DOC-PARALLEL-01, DOC-LOCAL-REPORT-HANDOFF-01, DOC-TASK-READ-SCOPE-01, DOC-HISTORY-ACCESS-01, DOC-VERIFIER-BLOCK4-01, DOC-TASK-BLOCK1-01|Точные правила и зависимости|
|`reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/`|report, engine_compatibility, topology, next_user_go|Источник блокировки|
|`reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/v2ray_preflight_20261017/`|Только очищенные engine metadata|Историческое наблюдение|
|`integrations/wua_chatgpt_mcp/`|Broker/strict profile, относящиеся исходники|Переиспользование|

Не читать исторические персональные `001` самостоятельно. Не загружать полностью весь общий `000` или регламент `18` без адресной причины.

### 4. Фаза A — идентификация реального engine

Провести **строго ограниченный read-only inventory**.

Порядок:

1. Прочитать ранее сохранённые сведения о v2rayN/sing-box.
    
2. Установить, какие точные пути к engine binary уже известны и допустимы для инспекции.
    
3. При доступности соответствующего файла собрать:
    
    - реальный basename и точный тип executable;
        
    - SHA-256;
        
    - размер;
        
    - PE-архитектуру;
        
    - FileVersion/ProductVersion, если существуют;
        
    - издателя и Authenticode metadata, если доступны без внешних запросов;
        
    - сведения о возможном release/build identifier.
        
4. При наличии разрешённого read-only системного способа установить, какой exact executable сейчас связан с известным v2rayN process, без получения командных строк с потенциальными секретами.
    
5. Сопоставить новое наблюдение с историческими metadata и отдельно указать различия.
    

**Граница:** только конкретно известный executable и необходимые metadata.

Не выполнять сканирование всего диска, каталогов программ, памяти процессов, proxy subscriptions, пользовательских profiles, environment secrets и конфигураций.

Не запускать бинарник даже с `--version`, если для этого потребуется создание нового процесса движка. Статическую версию из PE и подтверждённую документацию считать отдельным видом evidence.

Если путь невозможно точно установить безопасным способом, выдать `ENGINE_BINARY_PATH_REQUIRED` и конкретно указать, что должен сообщить пользователь.

### 5. Фаза B — source и schema compatibility

Для обнаруженного кандидата определить:

1. Движок — действительно sing-box, V2Ray Core или другой.
    
2. Точная версия и подтверждённое происхождение.
    
3. Доступность matching source release и конфигурационной схемы.
    
4. Наличие HTTP proxy inbound с обработкой CONNECT.
    
5. Возможность связать один inbound с единственным разрешённым outbound.
    
6. Возможность задать точный approved upstream `R:Q`.
    
7. Семантика маршрутизации unmatched destinations.
    
8. Отсутствие неявного DIRECT при отказе выбранного outbound.
    
9. Использование DNS, UDP, IPv6, telemetry, health, дополнительных процессов и companions.
    
10. Возможность отдельного config/root и последующего запуска под отдельным непривилегированным Windows SID.
    

Проверять факты **по доступным подтверждённым локальным versioned source/docs/schema**, а не по памяти модели или предположениям.

Если нет доверенного соответствующего source, оставить соответствующие выводы `BLOCKED` и указать, какой конкретный release artifact нужен.

В этой TASK запрещён самостоятельный сетевой поиск/скачивание исполняемых файлов и установка нового движка. Достаточно подготовить адресный запрос недостающих материалов.

### 6. Фаза C — инженерное решение по выбранной архитектуре

Сравнить два направления:

**Вариант A — существующий sing-box.**

Оценить возможность удовлетворить `STRICT_V2RAY_BROKER`, не меняя работающий пользовательский экземпляр.

**Вариант B — выделенный V2Ray Core.**

Оценить, нужен ли он вообще, что именно обеспечивает и какие новые зависимости потребует.

Для каждого указать:

- подтверждённые возможности;
    
- неподтверждённые свойства;
    
- необходимость изменений имеющихся offline-контрактов;
    
- различия native config schema;
    
- процессное владение CONNECT listener и внешним socket;
    
- возможные дополнительные сетевые каналы;
    
- влияние на переносимость;
    
- объём оставшейся работы.
    

Не писать второй независимый broker stack без необходимости.

**Результат:** короткое техническое сравнение и рекомендация с уровнем уверенности. Окончательное переключение на иной движок требует решения пользователя.

### 7. Фаза D — offline-проверки и результат

Подготовить воспроизводимые проверки, которые **не запускают engine**:

- версионная и SHA-256 привязка;
    
- подмена executable/release metadata;
    
- schema mismatch;
    
- неизвестная версия;
    
- неподтверждённые capabilities;
    
- недоверенное доказательство owner SID;
    
- неправильный inbound/outbound;
    
- второй proxy, DIRECT/fallback и default-route;
    
- несовпадение между выбранным engine и старым contract;
    
- false PASS через поддельный JSON с положительными флагами.
    

Использовать существующие strict validators, а не создавать всё заново.

При доступном подлинном versioned schema material проверить структурную корректность минимального **disabled** candidate config.

Не создавать фиктивную «нативную конфигурацию», если реального schema evidence нет.

Все новые тесты должны иметь независимый negative oracle. Запустить пропорциональную регрессию затронутых offline-компонентов, не перезаписывая старые результаты.

Провести самостоятельный `MANUAL ENGINEERING REVIEW`: проверить assumptions, выбранные source, parser/default behavior, TOCTOU между inventory и будущим запуском, доверие к binary hash, возможность скрытых дочерних процессов, конфигурационный fallback и риски переноса на другой ПК.

### 8. Write scope и запреты

**Write scope:**

- Новые строго необходимые исходники, fixtures и tests внутри `integrations/wua_chatgpt_mcp/` — только по предмету engine metadata/compatibility.
    
- `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/` — полный отчёт и evidence.
    
- `Документация/000_Задачи Codex.md` — только штатная ротация БЛОКОВ 1–3.
    
- `Документация/001_История выполненных задач Codex.md` — только append-only своя TASK и точечный readback новой записи.
    

**БЛОК 4 — READ-ONLY.** Общие документы №18/19/34/37, production, NPFS, WFP и отчёты предыдущих TASK не менять.

При обнаружении параллельного writer остановить пересекающуюся запись.

**Не делать:**

- Не запускать, останавливать и перенастраивать действующий V2Ray/sing-box.
    
- Не читать subscriptions, пользовательские прокси-профили, private keys, tokens или password storage.
    
- Не устанавливать и не скачивать движки.
    
- Не изменять Windows identities, WFP, Firewall, BFE, службы, прокси, DNS, VPN, сеть или автозапуск.
    
- Не подключаться к настоящему upstream или OpenAI.
    
- Не запускать tunnel-client/hosted tunnel.
    
- Не проводить новые native network security эксперименты на рабочем компьютере.
    
- Не использовать Git/GitHub даже для чтения.
    
- Не расширять права из-за отсутствия подходящего engine.
    
- Не выдавать синтетический PASS за OS-level security proof.
    

`can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER` обязательны.

### 9. Сдаваемые файлы

В новой папке отчёта:

- `report.md`
    
- `engine_inventory.md`
    
- `source_provenance.md`
    
- `engine_capabilities.md`
    
- `singbox_vs_v2ray.md`
    
- `compatibility_gates.json`
    
- `tests.md`
    
- `manual_engineering_review.md`
    
- `next_user_decision.md`
    
- `manifest.json`
    
- очищенные evidence и исходные ошибки при наличии.
    

Не публиковать секретные пути, пользовательские конфигурации и raw system logs. При необходимости использовать безопасный redacted path label с соответствующим hash/receipt.

### 10. Приёмка и статусы

TASK завершена на уровне offline-исследования, если:

- Есть точная идентификация одного локального engine либо обоснованный адресный blocker.
    
- Нет ложного отождествления v2rayN и его core.
    
- Установлен уровень доверия к version/source/schema.
    
- Дана проверяемая оценка HTTP CONNECT и strict route capabilities.
    
- Обоснован выбор между sing-box и V2Ray Core либо указан единственный следующий недостающий input.
    
- Проверки подтверждают отказ на неподходящих/поддельных метаданных.
    
- Нет ненужного дублирования существующего broker code.
    
- Все реальные network/native/WFP gates сохраняются.
    

Статусы разделить:

`ENGINE_BINARY_IDENTIFIED / BLOCKED`  
`ENGINE_RELEASE_PROVENANCE_VERIFIED / BLOCKED`  
`ENGINE_NATIVE_CONFIG_SCHEMA_VERIFIED / BLOCKED`  
`STRICT_CONNECT_COMPATIBILITY_SUPPORTED / UNVERIFIED / UNSUPPORTED`  
`ENGINE_SELECTION_PENDING_USER`  
`B_IDENTITY_NOT_PROVISIONED`  
`B_EGRESS_OWNER_NOT_VERIFIED`  
`WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED`  
`HOSTED_TUNNEL_ON_HOLD_BY_USER`  
`ORDINARY_CHATGPT_E2E_NOT_VERIFIED`

Не обозначать `PRODUCTION READY`.

### 11. Завершение

Сохранить report, tests, evidence и manifest.

Выполнить действующую ротацию персональной карточки:

1. Добавить полную собственную TASK, AMENDMENT и factual result в собственный исторический 001 без чтения старой истории.
    
2. Проверить только новую запись.
    
3. Поддержать окно пяти последних кратких TASK в БЛОКАХ 2–3.
    
4. БЛОК 4 сохранить побайтно.
    
5. Освободить БЛОК 1 после успешной записи.
    

Git/GitHub не использовать.

**Итог Codex:** один короткий factual result с TASK ID, версиями и hashes (без секретов), найденными возможностями, точными тестовыми результатами, blockers, DOC IMPACT и NEXT USER DECISION.

**Основной ожидаемый результат:** понять, какой конкретный движок мы действительно можем применить в защищённой конструкции двух учётных записей, и что требуется для следующего инженерного этапа — без запуска опасных системных экспериментов.

---

