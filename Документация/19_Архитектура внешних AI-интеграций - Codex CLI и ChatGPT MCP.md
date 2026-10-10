# Архитектура внешних AI-интеграций — Codex CLI и ChatGPT MCP

## Статус документа

**ARCHITECTURAL DIRECTION / FUTURE — NOT IMPLEMENTED.**

Направления ниже архитектурно одобрены, но не являются CURRENT runtime. Документ владеет транспортом и способами подключения внешних AI-систем к Agent Runtime. Роли моделей, Model Assignment, Planner / Executor / Dredd и model/provider isolation принадлежат `11_Мультимодельная архитектура и назначение LLM.md`.

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

Состав команды и назначения моделей описывает [[11_Мультимодельная архитектура и назначение LLM]]; Program/Stage, permissions и recovery — `23_Архитектура Web Alarm Workspace.md`. Это ориентир будущего onboarding, а не новый CURRENT stage и не разрешение на немедленную установку/изменение подключений.


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
