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

## 7. Статус и следующий шаг

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
