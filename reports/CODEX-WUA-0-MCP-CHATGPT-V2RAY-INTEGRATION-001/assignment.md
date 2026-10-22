# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# 🟨 CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001

## Реализация локального MCP-интеграционного контура ChatGPT ↔ Web Alarm Ultra с двумя техническими Windows identities и обязательным V2Ray

Уважаемый агент 007 (Codex)!

Поручаю продолжить практическую разработку интеграции ChatGPT с Web Alarm Ultra.

**Исполнитель:** Codex 007  
**Координатор и независимый verifier:** ChatGPT WEB_11  
**ARCH CLASS:** Web Alarm Ultra / External AI Integration / Secure MCP Tunnel / Strict Network Isolation  
**SOURCE REFERENCE:** `ag_llm/main@f9c18194f4e2b6ec9f17033a1d0afc34768c6dd5`

Это координаторский GitHub reference, а не разрешение использовать Git/GitHub.

### 1. Главная цель

Создать **практический, воспроизводимый локальный MCP-интеграционный комплект**, который впоследствии позволит обычному ChatGPT обращаться к разрешённым инструментам Web Alarm Ultra через OpenAI Secure MCP Tunnel.

Для текущего пользователя обязателен строгий профиль:

`STRICT_V2RAY_BROKER`

Два разных непривилегированных Windows identities:

- `wua-client` — для официального `tunnel-client` и точно утверждённых дочерних процессов;
    
- `wua-broker` — для выделенного сетевого брокера и контролируемого маршрута через V2Ray.
    

**Главный инвариант:** никаких несанкционированных прямых сетевых выходов, скрытого переключения на DIRECT, других прокси или автоматического ослабления защиты при отказе компонентов.

Это требование должно присутствовать в архитектуре, конфигурационных контрактах, тестах и будущей модели установки.

**Критически важно:** эти две технические учётные записи и их настоящие WFP-ограничения пока не созданы и не активированы. Их наличие в документах не доказывает работающую защиту.

В этой TASK необходимо получить работающую локальную реализацию MCP, а не ещё один большой исследовательский отчёт. Проверять её можно на контролируемых синтетических fixtures без открытия внешней сети и без изменения Windows.

### 2. Обязательная исходная база

Прочитать актуальные локальные нормативные документы в установленном маршруте:

`08 → 000 → 34 → 18 → 01 → 19 → 36 → 36.1 → применимый 36.2/36.3`.

Дополнительно:

- `Документация/37_Старт перехода - Web Alarm Ultra.md`, раздел 9;
    
- `Документация/11_Мультимодельная архитектура и назначение LLM.md` — граница model assignment, не путать с MCP;
    
- `Документация/000_Задачи Codex.md`, БЛОК 1.
    

Использовать ранее опубликованные разработки:

1. `reports/CODEX-WUA-0-MCP-FEASIBILITY-001/` — уже работающий локальный MCP SDK → stdio adapter → синтетический WebAlarmApi, ранее 34 PASS.
    
2. `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/` — подготовка Secure MCP Tunnel, расследование V2Ray и ограниченный CONNECT→SOCKS5 reference adapter.
    
3. `reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/` — переносимый Discovery/Plan/Verify toolkit.
    
4. `reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/` — источник будущих WFP-ограничений.
    
5. `reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/` — offline gate I01–I12, принятый только в ограниченном объёме.
    
6. Существующие `web_alarm/server.py` и серверные контракты получения status/context.
    

Официальные технические ориентиры:

- [https://developers.openai.com/api/docs/guides/secure-mcp-tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
    
- [https://github.com/openai/tunnel-client/blob/master/docs/configuration.md](https://github.com/openai/tunnel-client/blob/master/docs/configuration.md)
    

Не повторять завершённые исследования без конкретной технической причины. Версионно-зависимые CLI-флаги и настройки проверять по доступным проверенным источникам; если их нельзя подтвердить без запрещённого доступа в сеть, явно фиксировать BLOCKED.

### 3. Первая инженерная задача — проверить целостность всей сетевой топологии

До написания основного кода разобрать **все локальные и внешние соединения**, необходимые будущему рабочему процессу.

Особенно важно устранить потенциальное противоречие:

Предыдущая WFP-модель разрешала `wua-client` обращаться только к одному локальному `127.0.0.1:P`, который предполагался брокером. Но tunnel-client должен также взаимодействовать с MCP-сервером, а MCP-адаптер — с Ultra.

Нужно определить, какие соединения используют:

- STDIO;
    
- локальный TCP;
    
- именованный канал Windows IPC;
    
- исходящий HTTPS;
    
- SOCKS5 / HTTP CONNECT.
    

**Нельзя считать, что уже существующий единственный разрешённый TCP-порт подходит для всей схемы.**

Предпочтительно исследовать применение `stdio` между tunnel-client и MCP tool-server, если официальный клиент это поддерживает и такой маршрут позволяет избежать дополнительного небезопасного TCP-порта.

Затем отдельно решить, как MCP tool-server безопасно получает данные от Ultra: server-owned API, доверенный локальный IPC или иной минимальный механизм. Не добавлять новое WFP-исключение автоматически.

Также проверить модель брокера и V2Ray:

- Если брокер подключается к локальному SOCKS5 V2Ray, определить, какой процесс действительно осуществляет внешний egress.
    
- Если V2Ray работает от обычного пользователя, не объявлять его защищённым WFP-политикой двух технических SID.
    
- Не считать SOCKS5 на `127.0.0.1:10808` доказательством HTTP CONNECT или доказательством фактического выхода через V2Ray.
    
- Не менять существующие V2Ray profiles, listeners или process ownership.
    
- Если строгая двухидентификационная модель не покрывает выбранный вариант V2Ray, выдать точный blocking finding и безопасную альтернативу для будущей реализации.
    

**Результат этой части:** одна согласованная топология с явными process identities, каждым IPC/socket/port, trust boundary, разрешениями и blocking gates. Не подменять её красивой схемой без фактической совместимости.

### 4. Реальный локальный MCP Integration Adapter

Использовать уже существующий MCP PoC, где это технически целесообразно, и создать переиспользуемый standalone integration package.

Минимальные инструменты:

- `ping` — проверяемый ответ локального сервера;
    
- `list_capabilities` — точный allowlist и версия интерфейса;
    
- `read_synthetic_context` — чтение разрешённого синтетического TASK context;
    
- `get_status` — ограниченное чтение состояния через server-owned интерфейс, только в явно разрешённом тестовом scope.
    

Реализация должна использовать настоящий MCP transport/protocol, а не имитацию MCP в Python.

Не давать прямой доступ к файлам Ultra, Run Store, Git, системным настройкам, произвольным TASK ID или model credentials.

Обязательны:

- корректная инициализация MCP;
    
- `tools/list` и `tools/call`;
    
- версия и capability manifest;
    
- проверяемая авторизация и scope на стороне интеграции;
    
- fail-closed при неизвестной операции;
    
- строгая типизация входа;
    
- ограничение времени, размера ответов и запросов;
    
- отказ от redirects и непредусмотренных сетевых адресов;
    
- redacted audit с correlation/request ID;
    
- ограниченные ошибки без утечки private context;
    
- безопасный stop/restart с отсутствием зависших собственных процессов.
    

**Практический критерий:** независимый локальный MCP SDK client должен реально обращаться к adapter, а adapter — к собственному изолированному WebAlarmApi fixture, возвращающему проверяемый context.

Просто возвращать заранее зашитый JSON без обращения к server-owned API недопустимо.

### 5. Secure MCP Tunnel integration

Подготовить корректные versioned-конфигурации для официального `tunnel-client`.

Разделить:

1. Local MCP transport (stdio/HTTP).
    
2. OpenAI tunnel control-plane connection.
    
3. Local HTTP CONNECT broker.
    
4. V2Ray outbound.
    
5. Host OS egress enforcement.
    

Для каждого канала определить endpoint, process identity, authority, auth, порт/pipe, допустимый профиль и реакцию на failure.

Текущая официальная конфигурация `tunnel-client` поддерживает явные HTTP/HTTPS proxy settings; нельзя напрямую подставить SOCKS URL в параметр, рассчитанный на HTTP proxy.

Предыдущий CONNECT→SOCKS5 adapter — **reference-only**. Если он используется, проверить совместимость всех необходимых control-plane paths, а не только одного успешного CONNECT.

Не использовать неизвестные CLI-флаги или фиктивные признаки поддержки.

Подготовить:

- шаблон профиля `STRICT_V2RAY_BROKER`;
    
- контракт запуска без секретов;
    
- точный список необходимых официальных OpenAI prerequisites;
    
- условия, при которых tunnel должен оставаться остановленным;
    
- отдельный диагностический preflight и health/status contract.
    

Не создавать tunnel_id, API key или реальную Platform-конфигурацию. Не запрашивать ChatGPT-пароль.

Отдельно документировать, что runtime API key для туннеля и использование платного model API — разные вопросы, но фактическая доступность туннеля зависит от прав Platform/ChatGPT workspace.

### 6. Две технические Windows identities и строгая защита

Создать конфигурационные контракты для:

`wua-client` и `wua-broker`.

Требования:

- разные SID, локальные непривилегированные identities;
    
- исключить основной Windows account и обычный ChatGPT Desktop из scope технических SID;
    
- не импортировать чужие SID с другого компьютера;
    
- отдельные process ownership, credentials, startup rights и ACL;
    
- точный allowlist контролируемых локальных каналов;
    
- явная идентификация V2Ray process boundary;
    
- без DIRECT/fallback;
    
- любые unknown/mismatch/unverified — BLOCKED.
    

Использовать выводы предыдущего WFP-кандидата, **не активируя его**.

Показать, какие свойства обеспечивает обычная конфигурация приложений, а какие требуют обязательной OS-enforced WFP-изоляции. Application-level запрет прямого dial не считать гарантией против произвольного дочернего процесса.

Все source/config templates должны быть переносимыми, без настоящих паролей, токенов, секретных прокси URL и частных host identifiers.

### 7. Тесты

Разработать воспроизводимую offline/integration suite, использующую только собственные временные директории, синтетический WebAlarmApi и явно принадлежащие тесту loopback endpoints.

Обязательные группы:

**MCP:** настоящий SDK initialize, tools/list, tools/call, разрешённое чтение, отказ чужому TASK, перепроверка context hash/nonce, restart и повторное чтение.

**Network route:** HTTP CONNECT→SOCKS5 reference, отдельный control-plane simulation, отказ SOCKS upstream, closed listener, timeout, abrupt close, malformed response, secondary proxy и environment overrides.

**Strict profile:** при потере обязательного брокера/V2Ray отсутствуют попытки DIRECT; при появлении непредусмотренного соединения тестовый observer обязан выдавать FAIL. Вызывать настоящие внешние endpoints запрещено.

**Process/permissions:** разные технические identities на уровне контрактов, неправильный SID/owner, непредусмотренный child, port takeover, подмена endpoint и недоверенный startup configuration.

**Security regression:** WFP toolkit и Install/Uninstall остаются BLOCKED; никаких разрешений через config flag, fake proof или synthetic PASS. Отдельные проверки отсутствия записи в production.

**Quality:** bounded timeouts/resources, отдельные negative/mutant controls и самостоятельный manual engineering/adversarial source review.

Не требовать искусственного количества тестов. Предпочтительны небольшие, но действительно чувствительные к нарушениям независимые oracles.

Тесты могут делать сетевые соединения **только в собственном локальном fixture**, без внешней сети, реального V2Ray или настоящего tunnel-client.

Если отдельный тест требует настоящего исполнения Go tunnel-client, SID/WFP или hosted tunnel — `NOT RUN / BLOCKED`, с конкретным gate, а не фальшивый PASS.

### 8. Permissions и границы работы

**Write scope:**

- Новая самостоятельная директория `integrations/wua_chatgpt_mcp/` — исходники, конфигурационные шаблоны и тесты. Если локально директория уже существует и содержит чужую работу, остановить конфликтующие записи.
    
- `reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001/` — отчёты, evidence и manifest.
    
- `Документация/000_Задачи Codex.md` — только штатная ротация собственной карточки после завершения.
    

Остальные документы, старые отчёты, `web_alarm/`, Ultra production/runtime, тесты Claude и CI — read-only.

**Запрещено без нового USER GO:**

- создавать реальные Windows-учётные записи;
    
- изменять WFP, Firewall, BFE, сервисы, системные ACL, сетевые маршруты или V2Ray;
    
- запускать настоящий tunnel-client, Cloudflared, hosted tunnel;
    
- создавать внешний MCP endpoint, listener на внешнем интерфейсе либо tunnel resource;
    
- менять proxy/environment настоящих пользовательских процессов;
    
- включать Hyper-V, запускать экспериментальные VM/native-WFP тесты;
    
- выполнять Git/GitHub-операции локальным Codex;
    
- обращаться к реальным OpenAI endpoints, создавать или использовать API keys;
    
- выполнять платные API-запросы;
    
- устанавливать новые зависимости без разрешения;
    
- обходить Execution Policy/локальные ограничения.
    

`HOSTED_TUNNEL_ON_HOLD_BY_USER` остаётся.

**Важно:** задача не должна останавливаться полностью только потому, что настоящий tunnel/WFP заблокирован. Разрешённую локальную MCP-интеграцию и synthetic route tests Codex должен довести до практически работающего результата.

### 9. Что должно быть сдано

Подготовить:

1. Исходный код standalone MCP integration package.
    
2. Воспроизводимый local MCP ↔ WebAlarmApi integration test.
    
3. Строгую process/socket/IPC topology с указанием обеих identities и V2Ray boundary.
    
4. Версионированные шаблоны tunnel-client, broker и strict network profile.
    
5. Offline tests, negative controls и evidence.
    
6. Документ `connection_gates.md` с фактическими условиями каждого будущего подключения.
    
7. `deployment_plan.md` — точный порядок будущей установки и проверки на другом ПК, без применения изменений.
    
8. `manual_engineering_review.md`.
    
9. `report.md` и `manifest.json` со всеми файлами, размерами и SHA-256.
    
10. Короткий `NEXT USER GO`, перечисляющий **необходимые конкретные разрешения**, а не абстрактную просьбу разрешить всё.
    

Результат должен быть пригоден для следующего практического этапа без переписывания всей MCP-интеграции заново.

### 10. Критерии приёмки

TASK может получить `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, когда:

- Есть настоящий локальный MCP server/adapter и проверенный MCP SDK client.
    
- Подтверждена фактическая связь с синтетическим server-owned WebAlarmApi.
    
- Есть точная совместимая целевая топология или адресно обозначенные blocking conflicts.
    
- Две технические identities встроены в конструкцию и deployment contracts, а не просто упомянуты.
    
- Все сетевые профили имеют явную fail-closed политику.
    
- Ни один синтетический тест не разблокировал реальное применение WFP/туннеля.
    
- Проведены тесты и самостоятельный инженерный review.
    
- Сохранены полный report/evidence/manifest и прежние ошибки.
    
- Основная Windows, V2Ray и production Web Alarm остались неизменными.
    

**Статусы разделять обязательно:**

- `LOCAL_MCP_INTEGRATION_VERIFIED` — только при фактически выполненном тесте.
    
- `STRICT_ROUTE_SYNTHETIC_TESTED` — только при фактически выполненном тесте.
    
- `TWO_WINDOWS_IDENTITIES_NOT_PROVISIONED`.
    
- `OS_WFP_EGRESS_NOT_VERIFIED`.
    
- `V2RAY_LIVE_ROUTE_NOT_VERIFIED`.
    
- `SECURE_TUNNEL_NOT_ACTIVATED`.
    
- `ORDINARY_CHATGPT_E2E_NOT_VERIFIED`.
    

Ни один статус offline-тестов не превращать в `PRODUCTION READY`.

После окончания: сохранить все материалы, выполнить штатную безопасную ротацию БЛОКОВ 1–3 собственной карточки, прежнюю историю оставить побайтно. Git/GitHub не использовать. Пользователь публикует результат, WEB_11 проводит независимый review.

**Ключевое ожидание:** нам нужен не очередной анализ возможностей MCP, а технически работающий локальный интеграционный комплект, который сохраняет возможность будущего строгого подключения через две Windows identities и V2Ray.

---

