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
