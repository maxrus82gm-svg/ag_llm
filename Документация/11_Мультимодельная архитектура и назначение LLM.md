# Мультимодельная архитектура и назначение LLM

## Статус документа

Архитектурное решение / переходный этап разработки.

Этот документ фиксирует переход проекта `ag_llm / GigaChat Ultra Local Agent` от системы, в которой основной исполнитель фактически жёстко связан с одной моделью GigaChat Ultra, к системе, в которой LLM становится выбираемым и назначаемым ресурсом.

На текущем этапе существующий рабочий runtime, инструменты, Workspace, Chat, Project Context, RAW HISTORY, SAFE Mode, Backup, Verification, Trace и другие уже реализованные механизмы сохраняются.

Изменяется не сам принцип работы агента, а способ выбора его «мозга».

---

# 1. Исходное состояние

На текущем этапе основная схема системы выглядит приблизительно так:

    Ultra UI
        ↓
    server.py
        ↓
    GigaChat Ultra API
        ↓
    Agent Runtime / Tools
        ↓
    Workspace

GigaChat Ultra является основной моделью, выполняющей пользовательские задачи.

При этом вокруг модели уже существует значительный независимый runtime:

- Workspace;
- Chat;
- PROJECT CONTEXT;
- RAW HISTORY;
- Active Chat Context;
- file tools;
- READ / WRITE / DELETE scopes;
- SAFE Mode;
- Backup;
- Verification Gate;
- GUARD;
- Trace;
- Server Facts;
- UI;
- persistent storage.

Следовательно, большая часть агентской системы уже не обязана быть логически привязана именно к GigaChat Ultra.

---

# 2. Главный архитектурный переход

LLM должна перестать быть жёстко встроенным центром системы.

Вместо этого модель становится подключаемым вычислительным ресурсом, который можно назначить конкретной роли, операции, Chat или будущему Agent.

Целевая схема:

    ┌───────────────────────────────┐
    │         MODEL REGISTRY        │
    │      Справочник моделей       │
    └───────────────┬───────────────┘
                    │
          ┌─────────┼──────────┐
          │         │          │
          ▼         ▼          ▼
      GigaChat    Ollama     Future Provider
       API        Server      / Runtime
          │         │          │
          └─────────┼──────────┘
                    │
                    ▼
           MODEL ASSIGNMENTS
                    │
       ┌────────────┼────────────┐
       │            │            │
       ▼            ▼            ▼
    MAIN CHAT   COMPRESSION   FUTURE AGENT
      MODEL        MODEL          MODEL

Основной принцип:

    LLM ≠ Agent Runtime

LLM является «мозгом».

Agent Runtime предоставляет:

- контекст;
- инструменты;
- ограничения;
- состояние;
- Workspace;
- Chat;
- безопасность;
- проверку;
- логирование;
- управление жизненным циклом задачи.

---

# 3. MODEL REGISTRY — единый справочник LLM

В системе должен появиться единый справочник доступных моделей.

Предварительное рабочее имя:

    MODEL REGISTRY

или в UI:

    СПРАВОЧНИК LLM

Он является единым источником информации обо всех моделях, которыми умеет пользоваться программа.

Примеры:

    GigaChat Ultra
    GigaChat Pro
    GigaChat Lite
    другие доступные модели GigaChat

    DeepSeek R1 8B Local
    другие локальные модели

В будущем:

    другие облачные API
    другие локальные runtime
    специализированные модели
    собственные модели

MODEL REGISTRY не должен быть привязан к одному поставщику.

---

# 4. PROVIDER и MODEL — разные сущности

Необходимо различать поставщика / runtime и конкретную модель.

Пример:

    PROVIDER:
        GigaChat

    MODEL:
        GigaChat Ultra

или:

    PROVIDER:
        Ollama

    MODEL:
        DeepSeek R1 8B

Это позволит одной интеграции Provider обслуживать сразу несколько моделей.

Например, существующая интеграция GigaChat API должна позволить использовать разные модели GigaChat без создания отдельной реализации API для каждой из них.

Сначала система должна научиться работать по схеме:

    один Provider
    +
    несколько моделей

и только после этого расширяться до:

    несколько Providers
    +
    множество моделей

---

# 5. Первый Provider — GigaChat

Первый этап реализации должен использовать уже работающую интеграцию GigaChat.

Причина:

- API уже подключён;
- credentials уже настроены;
- запросы работают;
- GigaChat Ultra уже выполняет задачи;
- работает tool calling;
- работает обработка контекста;
- работают server-side механизмы.

Поэтому первым экспериментом является не подключение совершенно новой инфраструктуры, а возможность изменить конкретную используемую модель внутри уже существующего GigaChat Provider.

Например:

    MAIN CHAT MODEL:

    GigaChat Ultra
        ↓
    GigaChat Pro

При этом всё остальное должно сохраниться:

    Workspace
    Chat
    Project Context
    история
    tools
    permissions
    backup
    verification
    trace

Меняется только модель, выполняющая следующий RUN.

---

# 6. MODEL ASSIGNMENT — назначение модели

Сам факт наличия модели в MODEL REGISTRY ещё не определяет, где она используется.

Для этого нужен отдельный слой:

    MODEL ASSIGNMENT

MODEL ASSIGNMENT отвечает на вопрос:

    Какую модель использовать для конкретной функции?

На первом этапе нужны минимум два назначения:

    MAIN CHAT MODEL

    COMPRESSION MODEL

Позже могут появиться:

    VERIFICATION MODEL

    FINALIZATION MODEL

    PLANNER MODEL

    CODE AGENT MODEL

    DOCUMENT AGENT MODEL

    SUPERVISOR MODEL

    RESEARCH MODEL

    COORDINATOR MODEL

и другие.

---

# 7. MAIN CHAT MODEL

MAIN CHAT MODEL — модель, являющаяся основным «мозгом» существующего Chat Agent.

На первом этапе выбор может быть глобальным для текущего runtime / интерфейса.

В UI в области текущего Chat должен появиться понятный selector, например:

    Модель чата:
    [ GigaChat Ultra ▼ ]

или эквивалентное управление.

Переключение модели НЕ должно:

- создавать новый Workspace;
- уничтожать Chat;
- уничтожать RAW HISTORY;
- менять Project Context;
- менять tool permissions;
- менять SAFE scopes;
- очищать существующую историю.

Изменяется исполнитель следующего RUN.

---

# 8. Модель по умолчанию и модель конкретного Chat

На первом этапе допустима простая глобальная настройка:

    DEFAULT MAIN CHAT MODEL

Все Chat используют выбранную модель.

Однако архитектура должна сразу допускать следующий этап:

    Workspace default model
            ↓
        Chat override

То есть новый Chat может унаследовать модель по умолчанию, но позже получить собственное назначение.

Пример:

    Chat A
        GigaChat Ultra

    Chat B
        GigaChat Pro

    Chat C
        Local Model

При этом Chat сохраняет свою собственную историю и собственный контекст независимо от используемой модели.

---

# 9. Контекст принадлежит роли, а не модели

Это один из фундаментальных принципов новой архитектуры.

Нельзя считать, что определённая LLM сама по себе является «компрессором», «верификатором» или «главным агентом».

Одна и та же модель может использоваться в нескольких разных ролях.

Например:

    MODEL:
        GigaChat Lite

может одновременно быть назначена:

    COMPRESSION
    VERIFY

Но эти процессы должны иметь разный контекст.

Следовательно:

    MODEL
        ≠
    ROLE CONTEXT

Контекст принадлежит конкретной операции / роли / Agent.

Пример:

    ROLE:
        Context Compressor

    MODEL:
        GigaChat Lite

    ROLE CONTEXT:
        инструкция по сжатию
        правила сохранения фактов
        формат результата

И отдельно:

    ROLE:
        Context Verifier

    MODEL:
        GigaChat Lite

    ROLE CONTEXT:
        инструкция по сравнению RAW и SUMMARY
        правила поиска потерь
        формат замечаний

Физически используется одна модель.

Логически это два разных процесса.

Их контекст не должен смешиваться.

---

# 10. COMPRESSION MODEL

Второе первоначальное назначение:

    COMPRESSION MODEL

Оно используется системой управляемого сжатия контекста.

Пользователь должен иметь возможность выбрать модель, выполняющую сжатие, независимо от MAIN CHAT MODEL.

Например:

    MAIN CHAT MODEL
        GigaChat Ultra

    COMPRESSION MODEL
        GigaChat Lite

или:

    MAIN CHAT MODEL
        GigaChat Ultra

    COMPRESSION MODEL
        DeepSeek R1 8B Local

Система сжатия не должна быть жёстко привязана ни к DeepSeek, ни к Ollama, ни к GigaChat.

Она обращается к выбранному MODEL ASSIGNMENT.

---

# 11. Связь с Compress → Verify → Finalize

Разрабатываемая система управляемого сжатия использует несколько логических этапов:

    COMPRESS
        ↓
    VERIFY
        ↓
    FINALIZE

Это отдельные операции.

В будущем каждая операция потенциально может иметь собственное MODEL ASSIGNMENT.

Например:

    COMPRESS
        GigaChat Lite

    VERIFY
        GigaChat Pro

    FINALIZE
        GigaChat Ultra

или:

    COMPRESS
        Local DeepSeek

    VERIFY
        Local DeepSeek

    FINALIZE
        GigaChat Lite

На первом этапе допустимо использовать одно общее назначение:

    COMPRESSION MODEL

для всех трёх проходов.

Архитектура при этом не должна препятствовать будущему разделению.

---

# 12. Локальные LLM

Следующим Provider после GigaChat планируется поддержка локальных моделей.

Первоначально практическим runtime может быть:

    Ollama Server

Схема:

    ag_llm
        ↓
    Local Provider Adapter
        ↓
    Ollama HTTP Server
        ↓
    Local LLM

Например:

    DeepSeek R1 8B

Однако Ollama не должна становиться обязательной частью архитектуры.

Ollama является только одним из возможных runtime.

В будущем Provider может использовать:

- Ollama;
- llama.cpp;
- vLLM;
- OpenAI-compatible local server;
- собственный inference runtime;
- другой локальный движок.

Следовательно, код верхнего уровня не должен знать, каким именно способом физически запускается локальная модель.

---

# 13. Provider Adapter

Каждый внешний или локальный источник моделей должен подключаться через отдельный Provider Adapter.

Логически:

    Agent Runtime
        ↓
    Model Router
        ↓
    Provider Adapter
        ↓
    конкретный API / runtime

Примеры:

    GigaChatProvider

    OllamaProvider

    FutureProvider

Provider Adapter должен скрывать от остальной системы конкретные особенности API.

Верхний уровень должен по возможности работать с унифицированной моделью вызова.

---

# 14. Предварительная структура записи модели

Точный формат будет определён при реализации.

Но архитектурно MODEL REGISTRY должен иметь возможность хранить минимум:

    internal model ID

    display name

    provider

    provider model identifier

    enabled / disabled

    cloud / local

    endpoint, если требуется

    capabilities

В будущем могут добавляться:

    context window

    tool calling support

    multimodal support

    structured output support

    approximate cost

    latency class

    recommended roles

    custom parameters

Это не означает, что все поля нужно реализовать сразу.

Структура должна лишь позволять расширение без полного переписывания системы.

---

# 15. Credentials и безопасность

Credentials не являются частью переносимой модели проекта.

API keys, authorization data и другие секреты не должны сохраняться в:

    PROJECT CONTEXT

    RAW HISTORY

    Git

    обычной документации

    переносимом Workspace state в открытом виде

MODEL REGISTRY может содержать логическую информацию о Provider, но секреты должны храниться отдельно через существующий или будущий механизм безопасной локальной конфигурации.

---

# 16. MODEL AVAILABILITY

MODEL REGISTRY должен отличать:

    модель зарегистрирована

и:

    модель реально доступна сейчас

Например:

    GigaChat Ultra
        AVAILABLE

    DeepSeek Local
        UNAVAILABLE
        Ollama server not running

Это особенно важно для переносимых Workspace.

Workspace может содержать назначение:

    COMPRESSION MODEL = DeepSeek Local

но на другом компьютере такой модели может не существовать.

Система не должна молча подменять модель другой.

Она должна показать понятное состояние и предложить пользователю выбрать доступную модель.

---

# 17. Capabilities

Не все LLM обладают одинаковыми возможностями.

Поэтому в будущем Model Router должен учитывать capabilities.

Например:

    text
    tools
    structured output
    images
    large context
    local inference

Если роль требует tool calling, а выбранная модель его не поддерживает, система должна уметь обнаружить несовместимость до начала RUN.

На первом этапе можно не строить сложную автоматическую маршрутизацию.

Достаточно заложить соответствующую модель данных.

---

# 18. Агент и модель — разные сущности

Будущая архитектура должна явно различать:

    MODEL

и:

    AGENT

MODEL:

    вычислительная LLM

AGENT:

    роль
    +
    назначенная модель
    +
    собственный контекст
    +
    инструменты
    +
    разрешения
    +
    состояние
    +
    правила выполнения

Пример:

    AGENT:
        Main Workspace Agent

    MODEL:
        GigaChat Ultra

    CONTEXT:
        Project Context
        Chat Working Context

    TOOLS:
        file tools
        verification
        git tools

Другой Agent:

    AGENT:
        Context Compressor

    MODEL:
        GigaChat Lite

    CONTEXT:
        Compression Context

    TOOLS:
        none / restricted

Одна и та же MODEL может одновременно использоваться несколькими Agent.

---

# 19. Подключение моделей к новым Agent

MODEL REGISTRY должен стать общей инфраструктурой для всех будущих Agent.

При создании новой роли не нужно реализовывать новое подключение к API.

Новый Agent должен просто получить:

    role
    model_assignment
    context
    tools
    permissions

Пример:

    AGENT PROFILE

    Name:
        Document Agent

    Model:
        GigaChat Pro

    Context:
        Document Agent Context

    Tools:
        read_file
        write_file

Или:

    Name:
        Local Summarizer

    Model:
        DeepSeek R1 8B

    Context:
        Compression Context

    Tools:
        none

---

# 20. Будущее взаимодействие между Agent

После появления MODEL REGISTRY и MODEL ASSIGNMENTS становится возможен следующий архитектурный этап:

    MULTI-AGENT COORDINATION

Несколько Agent могут выполнять разные части одной задачи.

Предварительно:

    USER TASK
        ↓
    COORDINATOR
        ↓
    AGENT A
        ↓
    RESULT
        ↓
    COORDINATOR
        ↓
    AGENT B
        ↓
    RESULT
        ↓
    VERIFY / FINAL RESULT

При этом модели не должны обязательно напрямую «разговаривать друг с другом» как два открытых Chat.

Более контролируемая схема:

    Agent A
        ↓
    structured result / task state
        ↓
    Coordinator / Server
        ↓
    Agent B

Каждый Agent сохраняет собственный контекст и получает только необходимые данные.

Такой подход позволяет контролировать:

- расход контекста;
- роли;
- права;
- инструменты;
- факты;
- последовательность выполнения;
- логирование;
- безопасность.

Точный протокол общения между Agent является отдельным будущим архитектурным этапом.

---

# 21. Возможный будущий Coordinator

В дальнейшем может появиться специальная сущность:

    COORDINATOR

Coordinator не обязательно является отдельной уникальной LLM.

Это роль Agent Runtime.

Для неё также можно назначить любую подходящую MODEL через MODEL REGISTRY.

Coordinator сможет:

- принять большую задачу;
- определить необходимые роли;
- передать подзадачи другим Agent;
- собрать результаты;
- запросить проверку;
- вернуть итог пользователю.

Таким образом будущая multi-agent система также строится поверх MODEL ASSIGNMENT, а не вокруг жёстко заданных моделей.

---

# 22. UI — первый этап

В существующем UI необходимо предусмотреть как минимум два места выбора модели.

Первое:

    МОДЕЛЬ ЧАТА
    [ GigaChat Ultra ▼ ]

Это MAIN CHAT MODEL.

Второе:

    МОДЕЛЬ СЖАТИЯ
    [ GigaChat Lite ▼ ]

Это COMPRESSION MODEL.

Оба selector должны использовать один MODEL REGISTRY.

Также должна существовать точка входа в управление справочником, например:

    [ Справочник LLM ]

или:

    [ ⚙ Модели ]

Точное расположение и дизайн определяются отдельно.

---

# 23. Не создавать отдельные интеграции для каждой функции

Нельзя делать:

    отдельный GigaChat вызов для Chat
    отдельный GigaChat вызов для Compression
    отдельный DeepSeek код для Compression
    отдельный Ollama код для будущего Agent

Это приведёт к быстрому дублированию архитектуры.

Правильнее:

    MODEL REGISTRY
        ↓
    MODEL ASSIGNMENT
        ↓
    PROVIDER ADAPTER
        ↓
    MODEL

А функции используют единый слой.

---

# 24. Текущий минимальный этап реализации

Первый практический этап должен быть максимально маленьким.

Цель:

    доказать, что существующий Agent Runtime
    способен менять модель без смены всей системы

Минимально необходимо:

1. создать базовый MODEL REGISTRY;

2. создать GigaChat Provider с возможностью выбора конкретной модели;

3. вынести существующий GigaChat Ultra из жёсткой конфигурации в MODEL ASSIGNMENT;

4. добавить:

       MAIN CHAT MODEL

5. проверить переключение нескольких доступных GigaChat моделей;

6. убедиться, что при смене модели сохраняются:

       Chat
       RAW HISTORY
       Project Context
       tools
       permissions
       trace
       verification

7. добавить:

       COMPRESSION MODEL

8. использовать его как источник модели для будущего Context Compressor.

---

# 25. Следующий этап

После проверки GigaChat multi-model:

    MODEL REGISTRY
        ↓
    GigaChat Provider
        ↓
    несколько GigaChat моделей

добавляется второй Provider:

    Ollama / Local Provider

После этого схема становится реальной мультимодельной системой:

    MODEL REGISTRY
        │
        ├── GigaChat Provider
        │       ├── Ultra
        │       ├── Pro
        │       └── другие
        │
        └── Local Provider
                ├── DeepSeek
                └── другие модели

---

# 26. Что не требуется делать сейчас

На текущем этапе НЕ требуется сразу реализовывать:

- полноценный Coordinator;
- автономную команду из множества Agent;
- автоматический выбор лучшей модели;
- сложную оценку стоимости;
- распределённое выполнение;
- прямое общение десятков моделей;
- полный marketplace Provider;
- сложную систему capabilities;
- Web UI для мультимодельности.

Сначала необходимо создать маленькое устойчивое ядро:

    MODEL REGISTRY
    +
    PROVIDER
    +
    MODEL ASSIGNMENT

---

# 27. Связь с существующей системой контекста

Мультимодельная архитектура не заменяет существующую архитектуру контекста.

Сохраняются:

    RAW HISTORY

    WORKING REPRESENTATION

    ACTIVE CONTEXT

    PROJECT CONTEXT

    RUN MICROCONTEXT

Контекст должен собираться системой и передаваться назначенной модели.

Модель не должна становиться единственным владельцем памяти.

Это позволяет сменить:

    GigaChat Ultra
        ↓
    GigaChat Pro

или:

    GigaChat
        ↓
    Local LLM

без потери собственной памяти Agent Runtime.

---

# 28. Главный принцип мультимодельной архитектуры

Не:

    приложение построено вокруг одной LLM

а:

    приложение владеет агентской средой,
    памятью,
    инструментами,
    ограничениями,
    состоянием
    и назначает LLM для конкретной работы.

Кратко:

    МОДЕЛЬ — СМЕННЫЙ МОЗГ.

    КОНТЕКСТ — ПАМЯТЬ РОЛИ / AGENT.

    TOOLS — РУКИ AGENT.

    SERVER FACTS / TRACE — ОБЪЕКТИВНАЯ ИСТОРИЯ ДЕЙСТВИЙ.

    PERMISSIONS / GUARD / VERIFICATION — СИСТЕМА КОНТРОЛЯ.

    MODEL REGISTRY — СПРАВОЧНИК ДОСТУПНЫХ МОЗГОВ.

    MODEL ASSIGNMENT — РЕШЕНИЕ, КАКОЙ МОЗГ ВЫПОЛНЯЕТ КОНКРЕТНУЮ РАБОТУ.

---

# 29. Архитектурное направление проекта

Исторически проект называется:

    GigaChat Ultra Local Agent

На текущем этапе переименование проекта не требуется.

Однако новая архитектура должна перестать зависеть от GigaChat Ultra как от обязательного центрального компонента.

GigaChat Ultra остаётся:

- первой основной моделью;
- проверенным рабочим исполнителем;
- важным Provider;
- одной из доступных моделей.

Но архитектурно система начинает развиваться в сторону:

    Local Agent Runtime
    +
    pluggable LLM
    +
    multiple Agents
    +
    controlled contexts
    +
    future coordination

---

# 30. Ближайшая последовательность развития

Текущий переход рекомендуется выполнять в следующем порядке:

    ЭТАП A
    MODEL REGISTRY

        ↓

    ЭТАП B
    GIGACHAT MULTI-MODEL

        ↓

    ЭТАП C
    MAIN CHAT MODEL ASSIGNMENT

        ↓

    ЭТАП D
    COMPRESSION MODEL ASSIGNMENT

        ↓

    ЭТАП E
    CONTEXT COMPRESSOR
    Compress → Verify → Finalize

        ↓

    ЭТАП F
    LOCAL PROVIDER
    Ollama / другой runtime

        ↓

    ЭТАП G
    PER-CHAT MODEL ASSIGNMENT

        ↓

    ЭТАП H
    AGENT PROFILES

        ↓

    ЭТАП I
    MULTI-AGENT COMMUNICATION / COORDINATOR

Это направление не является обязательством реализовать все этапы сразу.

Каждый слой должен вводиться постепенно и проверяться отдельно.

---

# 31. Необходимая синхронизация документации

После принятия этого архитектурного решения необходимо отдельно синхронизировать существующую документацию проекта.

В частности, новая ветка должна быть отражена там, где фиксируются:

- архитектура проекта;
- текущее состояние;
- Roadmap;
- реестр задач;
- система Chat и Context;
- ближайшие этапы разработки;
- точка входа для нового чата / агента;
- связанные архитектурные решения.

Эта синхронизация является отдельной задачей.

Текущий документ фиксирует само архитектурное решение и является источником для последующего обновления остальных документов.

---

# 32. Главная идея

Проект переходит от схемы:

    ОДНА ПРОГРАММА
        ↓
    ОДНА LLM

к схеме:

    ОДНА АГЕНТСКАЯ СРЕДА
        ↓
    MODEL REGISTRY
        ↓
    МНОЖЕСТВО LLM
        ↓
    НАЗНАЧЕНИЕ МОДЕЛИ КОНКРЕТНОЙ РОЛИ
        ↓
    НЕЗАВИСИМЫЕ КОНТЕКСТЫ
        ↓
    БУДУЩИЕ AGENT
        ↓
    БУДУЩАЯ КООРДИНАЦИЯ

Это является фундаментом для дальнейшего развития `ag_llm` из GigaChat-ориентированного локального агента в универсальную локальную агентскую среду с подключаемыми моделями.