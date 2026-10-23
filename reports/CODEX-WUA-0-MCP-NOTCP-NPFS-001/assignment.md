# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# 🟨 CODEX-WUA-0-MCP-NOTCP-NPFS-001

## Разработать локальный MCP-мост STDIO ↔ Windows Named Pipe без дополнительных TCP-соединений

Уважаемый агент 007 (Codex)!

Назначаю новую инженерную задачу по развитию подключения ChatGPT к Web Alarm Ultra.

**Исполнитель:** Codex 007  
**Координатор / независимый verifier:** ChatGPT WEB_11  
**ARCH CLASS:** Web Alarm Ultra / MCP Integration / Windows IPC / Strict V2Ray Security  
**Исходный GitHub reference:** `main@a547092f74d6ee4f2a32982b8c7c067c61e160da`

Этот SHA — ориентир координатора. Самостоятельное использование Git/GitHub не разрешено.

### 1. Цель

Продолжить разработку после `CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001`.

По предыдущему отчёту Codex:

- Реальный локальный MCP SDK-прототип существует.
    
- Сохранены результаты исполнителя: 63/63 MCP checks и 24/24 security tests.
    
- Независимая приёмка этого прототипа пока не завершена.
    
- Обнаружены два существенных архитектурных конфликта F1 и F2.
    

**F1 — основной предмет нынешней TASK.**

При создании Python asyncio event loop на исследованной Windows возникает дополнительное динамическое TCP loopback-соединение. Это противоречит будущей модели, где `wua-client` разрешён только один строго определённый TCP endpoint брокера.

Необходимо устранить зависимость C-owned MCP frontend от такого Python runtime.

**F2 — сохраняемый обязательный security gate.**

Если будущий `wua-broker` передаёт соединение пользовательскому V2Ray/SOCKS, настоящий внешний socket не принадлежит SID брокера. Поэтому выбранная целевая архитектура использует отдельный B-owned V2Ray process, выполняющий HTTP CONNECT и фактический внешний egress.

Этот второй конфликт не пытаться решать параллельной установкой V2Ray. Сохранить его как блокирующее требование для последующего отдельного этапа.

**Практическая цель этой TASK:** получить реальный исполняемый C-side STDIO ↔ Windows Named Pipe relay и отдельный U-side authenticated MCP/API gateway, совместимые с уже разработанным локальным MCP-протоколом.

### 2. Матрица чтения

Читать только необходимые действующие источники. Не загружать автоматически глобальные архивы.

|Источник|Раздел / контракт|Цель|Объём|
|---|---|---|---|
|`Документация/000_Задачи Codex.md`|Правила, БЛОК 1 и относящийся БЛОК 4|Права, статус прошлого review, ротация|Обязательно|
|`Документация/08_Старт.md`|Актуальный стартовый маршрут|Проектный контекст|Адресно|
|`Документация/34_TACTICAL_CONTEXT.md`|CURRENT и MCP/WUA security|Текущие ограничения|Адресно|
|`Документация/01_Архитектура и текущее состояние.md`|Web Alarm / Ultra / MCP|Граница runtime|Адресно|
|`Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|§3–5 и §7.1–7.3, relevant MCP amendments|Transport, reachability, V2Ray и SID|Обязательно|
|`Документация/37_Старт перехода - Web Alarm Ultra.md`|§9|ChatGPT ↔ Ultra, read-only доступ|Обязательно|
|`Документация/36_Единая архитектура тестирования.md`|CURRENT и общий тестовый цикл|Порядок проверок|Адресно|
|`Документация/36.1_Обязательный регламент тестирования для LLM.md`|TEST-COLLAB/AREA/ENG/DEV/COV/EXEC/QA/EVID/SCOPE|Проверка кода и доказательств|Обязательно|
|`Документация/36.2_Профиль тестирования Web Alarm Workspace.md`|Изоляция Web Alarm и её тестов|Не задеть production|Адресно|
|`Документация/36.3_Профиль тестирования Ultra.md`|Применимые integration/runtime gates|Совместимость с Ultra|Адресно|
|`Документация/18_Регламент сопровождения документации.md`|DOC-GIT-01@1, DOC-PARALLEL-01@1, DOC-ENGINEERING-ROLES-01@2, DOC-TASK-BLOCK1-01@1, DOC-TASK-READ-SCOPE-01@1, DOC-HISTORY-ACCESS-01@1, DOC-VERIFIER-BLOCK4-01@2|Scope, Git, handoff, независимый review|Только точные правила и dependencies|
|`reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001/`|report, topology, connection_gates, manual_engineering_review|Исходные F1/F2 и тесты|Обязательно, адресно|
|`integrations/wua_chatgpt_mcp/`|server, api_channel, common, configs, tests|Существующая реализация|Изучить затронутый код|

Если необходимо восстановить историческую постановку, сначала использовать `assignment.md` конкретной TASK или попросить координатора предоставить выдержку.

**Запрещено самостоятельно читать целиком, искать или индексировать** `Документация/001_История выполненных задач Codex.md` и другие персональные исторические архивы.

Разрешена только будущая адресная запись собственной завершённой задачи в свой архив с точечным readback новой записи.

### 3. Целевая топология

Спроектировать и реализовать:

**C — будущая identity** `**wua-client**`**:**

- Официальный `tunnel-client` подключает локальный MCP через STDIO.
    
- В качестве локального MCP subprocess выступает новый лёгкий relay.
    
- Relay не использует Python asyncio, HTTP localhost, внешний TCP или произвольные helper-процессы.
    
- Relay общается с серверной частью исключительно через локальный Windows Named Pipe.
    

**U — существующая server-owned authority Web Alarm Ultra:**

- Принимает ограниченные MCP-запросы через собственный локальный pipe endpoint.
    
- Проверяет identity и разрешение caller.
    
- Передаёт только разрешённые read-only операции существующей логике MCP/WebAlarmApi.
    
- Не предоставляет прямой доступ к Run Store, файловой системе, model API, произвольным TASK или системным операциям.
    

**B — будущая identity** `**wua-broker**`**:**

- В этой TASK код брокера и V2Ray не менять.
    
- Сохранить требование отдельного B-owned процесса, фактически владеющего внешним socket.
    
- Не возвращаться к небезопасной схеме B-wrapper → V2Ray обычного пользователя.
    

В результате MCP frontend не должен требовать нового WFP TCP allowlist.

### 4. C-side no-TCP relay

Реализовать отдельный исполняемый компонент для Windows с использованием уже доступной локальной toolchain.

Предпочтительно использовать системные .NET/C# Windows Named Pipe API либо иной документированный native mechanism, который не создаёт TCP-соединения.

Конкретный язык выбрать самостоятельно после проверки toolchain и исходных зависимостей.

Обязательные свойства:

1. STDIO transport: правильная передача JSON-RPC/MCP сообщений в обе стороны, без подмены MCP-протокола.
    
2. Реальный Windows Named Pipe client к точному локальному endpoint.
    
3. Никаких собственных TCP/UDP/DNS-запросов, HTTP proxy/environment fallback или network auto-discovery.
    
4. Никакого произвольного subprocess execution.
    
5. Жёсткие ограничения на сообщение, очередь, время ожидания, количество запросов и срок жизни.
    
6. Controlled EOF, cancellation, partial frames, broken pipe, timeout, peer exit и restart.
    
7. Защита от silent truncation, duplicate/replay, message mixing, cross-session bleed и неправильного correlation ID.
    
8. Никакого самостоятельного reconnect к неизвестному endpoint.
    
9. Никаких секретов, команд shell или приватного контекста в логах.
    
10. Явная граница между тестовой конфигурацией и будущими реальными credentials/identities.
    

**Важное требование:** два направления потока должны работать без взаимной блокировки. Простая синхронная копия первого потока с ожиданием EOF не подходит, если из-за неё зависает ответное направление.

Не использовать monkeypatch недокументированных Python internals как обход F1.

### 5. U-side pipe gateway

Создать локальный проверяемый gateway-кандидат, который принимает соединение от relay.

Обязательная архитектура:

- Local NPFS endpoint, а не remote SMB/UNC pipe.
    
- Одна строго принадлежащая fixture instance, без wildcard access.
    
- Explicit pipe security descriptor / DACL, наименее необходимые permissions.
    
- Проверка server identity клиентом и client identity сервером по документированным Windows mechanisms.
    
- Windows effective token / SID и доступные peer-process APIs рассмотреть отдельно.
    
- PID, pipe name, synthetic nonce или одноразовый MAC **сами по себе не считаются доказательством подлинности SID**.
    
- Scoped session grant, bounded lifetime, replay protection и точный allowed tool set.
    
- Отказ для неподписанного/чужого запроса без автоматического расширения permissions.
    
- Никакого делегированного доступа к сети, файлам или процессам.
    
- Корректное закрытие собственных handles и processes.
    

Пока настоящие технические учётные записи C/B отсутствуют, разрешён только **доказуемо ограниченный тестовый сценарий под текущим пользователем**.

Не создавать новые Windows accounts. Не заявлять `C/B SID ISOLATION VERIFIED` по двум фиктивным SID.

Если реализация и проверка под разными настоящими security tokens невозможна без отдельного USER GO, эту часть отметить как `CROSS_SID_PROOF_PENDING` и предоставить точные prerequisites.

Внутренний MCP SDK gateway может использовать Python в U-контуре, потому что этот процесс **не относится к будущей C/B WFP-политике**. Но передача от C к U должна оставаться через Named Pipe, без нового C-owned TCP.

### 6. Настоящий сквозной локальный тест

Обязательное практическое испытание:

`MCP SDK Client → STDIO → новый relay → Windows Named Pipe → U-side MCP gateway → synthetic WebAlarmApi`

Не заменять эту цепочку тестовыми функциями, напрямую вызывающими MCP handlers.

Использовать уже реализованные четыре инструмента:

- `ping`;
    
- `list_capabilities`;
    
- `read_synthetic_context`;
    
- `get_status`.
    

Оставить для них прежний read-only scope. Проверить возвращаемые данные по независимому nonce/context hash и server-owned fixture record.

Сравнить результаты с предыдущим MCP SDK fixture baseline. Старые 63/63 и 24/24 — reference evidence Codex, **не автоматически независимый PASS** и не повод игнорировать возможную regression.

Новый комплект должен позволять повторить тесты без настоящего OpenAI tunnel, сети, реальных учёток или production Web Alarm.

### 7. Безопасность и negative testing

Создать адресные проверки:

- MCP initialize / tools/list / tools/call через полный новый transport.
    
- Pipe отсутствует, занят чужим процессом, закрывается посреди ответа или меняет владельца.
    
- Неверный peer SID/token, если проверка реально доступна; иначе отдельный незакрытый lab gate.
    
- Несовпадение имени pipe, owner, session, grant или protocol version.
    
- Чужой TASK ID, неизвестный tool, type mismatch, oversized request/response.
    
- Дублирование ID, replay и смешивание двух сессий.
    
- EOF или crash одной стороны с гарантированным завершением только собственных ресурсов.
    
- Частичные сообщения, медленный peer, unresponsive peer и bounded stop.
    
- Попытка использовать удалённый Named Pipe/SMB.
    
- Лишний socket, дочерний процесс или неожиданное направление связи.
    
- Случайный возврат к Python asyncio в C-owned executable path.
    
- Наличие внешних proxy environment variables у тестового caller.
    

**Отдельный качественный oracle:** тест должен обнаруживать намеренную вставку неразрешённого TCP dial или неправильного pipe peer, а не просто считать отсутствие ошибок успехом.

Не выдавать отсутствие TCP в собственном Python audit log за независимое OS process-wide доказательство. Исследовать доступные непривилегированные Windows observability tools и честно отделить source/static evidence, instrumented process observations и OS-enforced guarantees.

Никакого применения WFP для проверки F1 на рабочем компьютере.

### 8. Предыдущие security gates остаются действующими

Не изменять:

- `STRICT_V2RAY_BROKER`;
    
- две технические identities `wua-client` и `wua-broker`;
    
- `CanApply=false`;
    
- Install/Uninstall BLOCKED;
    
- `HOSTED_TUNNEL_ON_HOLD_BY_USER`.
    

Не считать no-TCP relay доказательством того, что:

- Весь официальный Go tunnel-client не имеет дополнительных сетевых маршрутов.
    
- Внешний V2Ray socket принадлежит B SID.
    
- Windows WFP реально ограничивает процессы.
    
- Remote ChatGPT умеет вызвать эти инструменты в текущем workspace.
    
- Настоящий MCP tunnel подключён.
    

Все эти утверждения требуют самостоятельных будущих проверок.

### 9. Разрешённые файлы и операции

**Write scope:**

1. `integrations/wua_chatgpt_mcp/` — только относящиеся к этой TASK исходники, конфигурационные контракты и тесты. Существующий MCP fixture и его интерфейс сохранить совместимыми.
    
2. `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/` — новый отчёт, evidence, тестовые результаты и manifest.
    
3. `Документация/000_Задачи Codex.md` — только штатная ротация своей TASK в БЛОКАХ 1–3. **БЛОК 4 — READ-ONLY.**
    
4. `Документация/001_История выполненных задач Codex.md` — только append-only добавление своей полной завершённой TASK, её AMENDMENT и factual result, затем readback исключительно добавленной записи. Предыдущую историю не читать и не переписывать.
    

**Read-only:** `web_alarm/`, старый WFP/toolkit, общая документация, исходники Claude, production Web Alarm/Ultra, существующие CI/workflows и чужие TASK.

Если обнаружен параллельный writer или непредусмотренный diff в разрешённом участке — до записи остановить конфликтующую часть.

**Разрешены:** локальная сборка уже доступным toolchain, собственные ограниченные fixture processes, создание временного тестового Windows Named Pipe и offline/local integration tests.

**Запрещены:** Git/GitHub даже для чтения; установка зависимостей; повышение привилегий; изменение рабочих Windows accounts, ACL за пределами собственной временной pipe instance, WFP, Firewall, V2Ray, служб, реестра и сетевых настроек; запуск настоящего tunnel-client; hosted MCP activation; реальные Platform credentials; настоящие OpenAI/V2Ray network requests.

Никаких изменений Execution Policy/Proxy/VPN/Hyper-V или production deployment.

### 10. Обязательная проверка

Провести:

1. Static/syntax/build проверки нового relay и gateway.
    
2. Полный реальный локальный MCP SDK integration test через Named Pipe.
    
3. Targeted security/negative tests.
    
4. Пропорциональную регрессию прежнего пакета; отдельный статус, если она недоступна.
    
5. Mutation/negative controls на TCP обход и неправильный pipe peer.
    
6. Manual engineering / adversarial source review после тестов.
    

Исторические ошибки не стирать. Любой исходный FAIL сохранить вместе с причиной и subsequent result.

Исполнитель обязан самостоятельно рассмотреть adjacent risks: thread deadlock, partial read/write, impersonation, ACL race, startup ordering, peer replacement, reconnect ambiguity, resource leaks, cancel/crash, wrong inherited handles и portability.

Не менять тестовые ожидаемые значения исключительно ради получения PASS.

### 11. Сдаваемые артефакты

Сохранить в `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/`:

- `report.md` — фактический итог;
    
- `README.md` — воспроизводимый локальный запуск;
    
- `topology.md` — точные процессы, identities, STDIO/pipe/socket границы;
    
- `pipe_security.md` — peer/DACL/token модель и открытые ограничения;
    
- `tests.md` — exact selectors, числа, отрицательные контроли;
    
- `evidence/` — source-pinned результаты и исходные FAIL;
    
- `manual_engineering_review.md`;
    
- `next_user_go.md` — будущие только адресные разрешения;
    
- `manifest.json` — path/bytes/SHA-256.
    

Новые исполняемые исходники находятся в `integrations/wua_chatgpt_mcp/`, а не прячутся только в отчёте.

### 12. Критерии приёмки

Предмет TASK можно сдать как `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, если:

- Новый relay действительно обрабатывает MCP traffic, а не только placeholder JSON.
    
- Есть работающий Named Pipe IPC между разными owned test processes.
    
- Реальный MCP SDK client получает четыре разрешённых tools через весь канал.
    
- Relay не зависит от Python asyncio или дополнительных TCP listeners.
    
- Отказ pipe/peer/owner/credential безопасно прекращает именно собственное соединение.
    
- Есть meaningful negative tests и mutation controls.
    
- Старые MCP read-only safety invariants не ослаблены.
    
- WFP/Accounts/V2Ray/Hosted Tunnel/Production по-прежнему заблокированы.
    
- Подготовлены полные report, evidence и manifest.
    

При отсутствии настоящего independent OS network observer **не объявлять доказанным полный запрет любых TCP-вызовов**. Честно указать уровень доказательства.

Нужны раздельные статусы:

`LOCAL_STDIO_NPFS_MCP_TESTED`  
`C_RELAY_NO_TCP_SOURCE_REVIEWED`  
`RUNTIME_NETWORK_OBSERVATION_[VERIFIED/NOT_VERIFIED]`  
`REAL_CROSS_SID_AUTH_PENDING`  
`WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED`  
`B_V2RAY_EGRESS_OWNER_NOT_VERIFIED`  
`HOSTED_TUNNEL_ON_HOLD_BY_USER`  
`ORDINARY_CHATGPT_E2E_NOT_VERIFIED`

**Не объявлять весь MCP production-ready по результатам одного локального теста.**

### 13. Завершение и ротация

После сохранения полного результата:

1. Добавить полную исходную TASK, AMENDMENT, factual result и locator в собственный `001_История выполненных задач Codex.md`.
    
2. Проверить только новую архивную запись.
    
3. Обновить компактные БЛОКИ 2–3 собственными итогами, сохранив окно последних пяти задач.
    
4. Не изменять БЛОК 4 независимой проверки.
    
5. Только затем освободить БЛОК 1 до `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`.
    

Если архив или карточка изменены параллельно — не перезаписывать чужую работу; статус `CARD ROTATION BLOCKED`.

Не выполнять commit/push. Публикацию осуществляет пользователь.

После фактического завершения отправить в чат компактный итог: TASK ID, статус, затронутые файлы, тесты, фактическая транспортная цепочка, подтверждённые и незакрытые риски, DOC IMPACT, NEXT SAFE ACTION.

Независимую приёмку после публикации выполняет WEB_11.

**Главное требование:** получить настоящий безопасный локальный IPC-компонент, который можно будет включить в будущую конструкцию MCP + две Windows identities + V2Ray, а не ещё один отчёт о том, почему это пока невозможно.

---

