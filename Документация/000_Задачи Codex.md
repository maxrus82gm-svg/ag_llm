# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**Приоритет USER GO 2026-10-24:** в этой персональной карточке БЛОК 1 и БЛОКИ 2–4, а также личный архив `001` обновляет ChatGPT-координатор **только после** пользовательской публикации и верификации/решения terminal BLOCKED. Локальному исполнителю запрещено изменять любые БЛОКИ карточки, `001` или самостоятельно запускать ротацию. Отчёт/manifest/evidence в разрешённой папке сохранять обязательно; до приёмки БЛОК 1 остаётся за текущей TASK. Источник: `DOC-TASK-CLOSEOUT-OWNER-01@1` (18); старые правила самоличной ротации более не действуют.

**USER GO 2026-10-23 (приоритетная адресная политика этой карточки):** [[001_История выполненных задач Codex]] — полный архив; БЛОКИ 2–3 — лишь пять последних кратких задач и итогов, постоянно обновляемых. БЛОК 4 — отдельная независимая проверка. Старые вложенные правила и статусы внутри исторического архива не являются новой инструкцией; архив читать только адресно по TASK ID, никогда автоматически целиком.


- **`DOC-TEST-LIFECYCLE-01@1` (18) — длительные тесты и честная сдача.** Не выдавать копируемый финальный результат или `RESULT READY` до окончания обязательных тестов. Если управление возвращено до их окончания, начинать сообщение с `# 🔴 ТЕСТЫ НЕ ЗАВЕРШЕНЫ — ЗАДАЧА В РАБОТЕ — ОТЧЁТ ПРЕДВАРИТЕЛЬНЫЙ`; сообщить TASK ID, проверенный статус и как возобновить. Черновой `report.md` помечать `DRAFT`, не обещать автоматического пробуждения без доказанного транспорта. Перед технической сдачей проверить exit code, итоговый файл, изоляцию, manifest и evidence; архив/ротацию выполняет только координатор после приёмки; при FAIL/BLOCKED сообщить факты, а не объявлять PASS.
- **`DOC-VERIFIER-BLOCK4-01@1` (18): БЛОК 4 независимого verifier.** БЛОКИ 1–3 прежние; БЛОК 4 — READ-ONLY для исполнителя, его пишет назначенный независимый проверяющий (пока ChatGPT) после фактического review/test. Память — последнее полное заключение + до двух кратких прежних, постоянный архив всех verdict в 06. Новая TASK не обнуляет БЛОК 4. При отсутствии независимого результата — NOT VERIFIED, не PASS.

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- **Перед TASK / `DOC-TASK-READ-SCOPE-01@1`:** собственные Правила, активный БЛОК 1 и относящийся БЛОК 4 (READ-ONLY), затем указанные в TASK актуальные разделы `08_Старт`, `34_TACTICAL_CONTEXT`, `01`/профиль темы, `36/36.1/36.2` (Web Alarm) или `36.3` (Ultra). Координатор даёт матрицу `файл → точный раздел/Rule-ID → зачем → обязательно/условно/полностью`. Весь глобальный `000_Задачи для агента` и весь `18` не читать механически; при пробеле/конфликте прав, security или отчётности требуется конкретное нормативное правило `18` вместе с зависимостями. Обязательные правила остаются в силе, Git-права не появляются. Codex приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Обязательная отчётность внутри проекта (`rule-ref:DOC-LOCAL-REPORT-HANDOFF-01@1`, 18).** По каждой TASK — в том числе PARTIAL, FAIL, BLOCKED и исследовательской — всегда сохранять полный factual `report.md`, manifest и необходимые безопасные evidence по разрешённому относительному пути внутри локального `ag_llm`, обычно `reports/<TASK-ID>/`. Итоговые файлы нельзя оставлять только во внешнем TEMP/кэше или в пути, исключённом `.gitignore`; при исключении сохранить очищенную публикационную копию в допустимой части проекта и отметить недоступный оригинал. Не публиковать секреты и приватные raw-логи. Git-коммиты/публикацию обычно делает пользователь; Codex не использует Git/GitHub и не имеет постоянного права самостоятельно отправлять сообщения в ChatGPT без конкретного USER GO для TASK/AMENDMENT. Допускаются временные изолированные пробы и минимальные технические файлы, но не вместо обязательного итогового отчёта.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- **Ротация и архив (USER GO 2026-10-24):** Codex сохраняет только техническую сдачу (`report.md`, manifest, evidence, точные проверки). Запись в персональный `001`, окно из пяти кратких TASK/итогов в БЛОКАХ 2–3, независимый БЛОК 4 и закрытие БЛОКА 1 выполняет ChatGPT-координатор после независимого review. Старый порядок самостоятельной ротации отменён; при ошибке архивирования — `CARD CLOSEOUT BLOCKED`, без очистки.

---

> **USER FREEZE / 2026-10-25 — PAUSED, NOT CLOSED.** Область ChatGPT Desktop → MCP → Web Alarm Ultra / V2Ray / WFP остановлена пользователем. Подробный неизменяемый архив: `39_Архив ChatGPT Desktop MCP - Web Alarm Ultra - заморозка 2026-10-25`; отдельный архитектурный владелец №19. `CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001` имеет опубликованную авторскую сдачу `RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_12`, **но не independent PASS**. Полный исходный текст БЛОКА 1 ниже сохранён без изменений. Новые MCP TASK, тесты/host изменений не разрешены; БЛОК 1 не очищать/не ротировать до отдельной приёмки или пользовательского terminal closeout. `can_apply=false`, `can_start_tunnel=false`, tunnel HOLD.

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

# ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001

## Дополнительная аналитика Астры — перенос Ultra в Web Alarm Ultra

**Исполнитель:** Astra (аналитическая сессия через Codex)  
**Координатор:** ChatGPT / Сервер WEB 13  
**Тип задачи:** архитектурное исследование и создание документа  
**Режим:** READ-ONLY SOURCE ANALYSIS + ограниченная запись документации  
**Исходная база:** `main@7924d7653e896e3fe110e7d67162730a9b7e857d`, коммит №436. Проверить соответствие локальной копии этой базе доступным разрешённым способом. Самостоятельные Git/GitHub-операции запрещены без отдельного разрешения пользователя.

### 1. Цель

Уважаемая Астра!

Необходимо провести углублённую архитектурную аналитику переноса существующей GigaChat Ultra (Python/Tkinter) в новый интерфейс Web Alarm Ultra.

Задача — **сопоставить утверждённые планы с реально существующим кодом и разработать технически обоснованную, последовательную программу переноса**.

Не нужно создавать второй Ultra Runtime, переписывать существующие механизмы или сразу реализовывать Ultra Chat.

**Утверждённая стратегия пользователя: ОДНО ОБЩЕЕ PYTHON-ЯДРО ULTRA.**

Во время перехода старая Tkinter Ultra продолжает работать. Новый веб-интерфейс постепенно использует её существующие механизмы через переиспользуемые Python-контракты. У одного состояния или операции должен быть один логический владелец.

### 2. Изучить документацию

Сначала адресно прочитать:

- №37 — утверждённый план перехода Web Alarm Ultra и его последние приоритетные решения.
    
- №24 — действующий план реализации Web Alarm Workspace.
    
- №23 — архитектура Web Alarm, Workspace, TASK, permissions и mutation authority.
    
- №03 — чаты, сообщения, RAW History, Working Context, Workspace.
    
- №11 — мультимодельная архитектура и назначения моделей.
    
- №20, особенно §5а, и №21 — RT-002/B2, оптимизация runtime, токенов, контекстов, бюджетов и фактические результаты проверок.
    
- `Blueprint LLM.md` — будущая совместимость с визуальными процессами.
    
- №36.2 и №36.3 — профили тестирования Web Alarm и Ultra.
    
- №18 — адресно правила изменения документации, границы агентов, проверки и отчётности.
    

**Разделять:** утверждённую архитектуру, реализованный код, экспериментальные результаты, частично принятые проверки и будущие предложения.

Не считать всю оптимизацию RT-002 уже внедрённой. В частности, проверить фактические production-подключения модулей budget/accounting, а не только существование исходников и тестов.

### 3. Изучить реальную кодовую базу

**Старая Ultra:**

- `ultra_ui.py`;
    
- корневой `server.py`;
    
- `model_registry.py`;
    
- `gigachat_transport.py`;
    
- `ui_state.py`;
    
- релевантные компоненты Workspace, chat storage, history, context assembly;
    
- роли, Planner, Executor, Dredd/Verifier;
    
- Run Store, audit, бюджет токенов и accounting.
    

**Web Alarm:**

- `web_alarm/server.py`;
    
- `web_alarm/ui.py`;
    
- `web_alarm/ultra_connections.py`;
    
- действующие Workspace/TASK/read-model компоненты;
    
- новые тесты EVM и связанные HTTP/UI-тесты.
    

Найти реальную структуру зависимостей. Не читать весь репозиторий или архивы без необходимости. Для существенных выводов указывать точные файлы, классы, функции и места использования.

**Текущий факт:** Claude реализовал вкладку EVM в коммите №436. Пять файлов исходников и тестов прошли первичный независимый source/publication review; окончательные Windows CI и визуальная приёмка ещё открыты. Настоящие GigaChat API-запросы в новой вкладке пока не выполняются.

### 4. Главные исследовательские вопросы

#### A. Что из старой Ultra переносим?

Составить матрицу возможностей старой Ultra:

- Workspace и управление проектами;
    
- создание, выбор и хранение чатов;
    
- RAW History и активный контекст;
    
- назначение моделей, профили и роли;
    
- обычный чат с GigaChat;
    
- Planner/Executor;
    
- Dredd/Verifier и Final Audit;
    
- server-owned исполнение, инструменты и разрешения;
    
- просмотр событий, состояния и результатов;
    
- контекстная память, сжатие, инспектор;
    
- бюджет, токены, стоимость и метрики;
    
- настройки и сохранение состояния.
    

Для каждой возможности определить:

1. Где она реально реализована.
    
2. Чем управляет Tkinter, а чем Python-ядро.
    
3. Что уже готово к веб-интеграции.
    
4. Что требует выделения общего UI-independent сервиса.
    
5. Что нужно переработать.
    
6. Что пока переносить не стоит.
    
7. Как будет проверяться отсутствие регрессии.
    

Не предлагать копирование функциональности только потому, что её легче повторно написать.

#### B. Как совместить Workspace двух систем?

Проверить отношения между:

- Web Alarm Workspace;
    
- Ultra Workspace;
    
- Chat;
    
- Message/Turn;
    
- TASK;
    
- RUN;
    
- Context;
    
- Model Assignment.
    

Предложить каноническую схему идентификаторов, ссылок и владельцев хранения.

Особое требование: новый Ultra Chat должен работать с Workspace, но не создавать вторую независимую систему управления теми же TASK и файлами.

Если старые модели несовместимы, предложить адаптер и миграцию данных, а не скрытое объединение или перезапись.

#### C. Как организовать общее Python-ядро?

Сопоставить варианты:

**Вариант 1:** общие UI-independent Python-модули и сервисы, используемые Tkinter и веб-слоем.

**Вариант 2:** общий сервис в отдельном процессе/sidecar с чётким API, если независимый процесс действительно необходим.

При необходимости предложить третий вариант.

Сравнить:

- количество новых механизмов;
    
- риск дублирования;
    
- сериализацию состояния;
    
- concurrency и ownership;
    
- обработку ошибок, отмену и восстановление;
    
- безопасность и границы доступа;
    
- тестирование;
    
- обратную совместимость;
    
- сложность сопровождения;
    
- путь постепенного вывода Tkinter.
    

**Нужен выбранный вариант с конкретными аргументами по исходному коду.**

#### D. Каким должен быть Ultra Chat?

Пользователь решил, что **Ultra Chat должен стать главным экраном Web Alarm Ultra и открываться по умолчанию**.

Целевая структура:

- слева — Workspace и история диалогов;
    
- в центре — основная область переписки;
    
- справа — контекстные настройки и инструменты модели/ролей/проверок;
    
- сверху — переходы между **Ultra Chat**, **Операторской панелью** и **EVM / Подключения Ultra**.
    

Это ориентир, а не требование дословно скопировать Tkinter. Астра вправе предложить более качественную организацию интерфейса и обосновать её.

Определить, что реально входит в первый рабочий MVP:

- создание и открытие Workspace/Chat;
    
- сохранение и восстановление переписки;
    
- выбор уже зарегистрированной модели EVM;
    
- ввод сообщения, отправка, ожидание, ошибка, отмена;
    
- реальный ответ через существующий GigaChat transport;
    
- история и метаданные сообщений;
    
- корректное поведение при сетевых отказах.
    

Отдельно разграничить **обычный разговор с LLM** и **управляемую агентскую задачу**. Обычный разговор не должен автоматически запускать всю дорогую цепочку Planner/Executor/Dredd.

#### E. Как сохранить оптимизацию токенов?

Изучить фактический путь формирования prompt в старой Ultra и документы RT-002/B2.

Разделить экономию токенов по режимам:

- обычный Chat;
    
- Planner;
    
- Executor;
    
- Verifier/Dredd;
    
- Final Audit;
    
- контексты, память и история;
    
- инструменты и повторная передача данных.
    

Указать реальные измерения с RUN ID, источником, версией и состоянием внедрения.

В обсуждении пользователя фигурировала оценка около 13 000 токенов после оптимизации. **Не считать её подтверждённым benchmark без найденного evidence.**

Проверить риск возврата старого большого расхода токенов при переходе на веб.

Предложить, какие существующие механизмы reuse обязательны, а какие budget guards ещё нельзя считать production-ready.

#### F. Как организовать проверяющего и агентские режимы?

Исследовать механизмы Dredd/Verifier и их реальные границы.

Определить:

- как веб-интерфейс сможет запускать существующий режим проверки;
    
- как показывать прогресс, этапы, ошибки и результаты;
    
- где хранятся свидетельства проверки;
    
- как исключить обход server-owned прав;
    
- какие функции стоит оставить в «Операторской панели»;
    
- как в будущем подключать внешнего проверяющего.
    

**Не возобновлять замороженный ChatGPT Desktop MCP / Tunnel / V2Ray проект.** Его интеграция не является условием Ultra Chat.

#### G. Какие риски и зависимости мешают переходу?

Проверить:

- блокирующие особенности Tkinter-зависимостей;
    
- скрытое глобальное состояние и singleton-модули;
    
- параллельные обращения к одному состоянию;
    
- конфликт с Web Alarm server-owned mutation authority;
    
- наличие полномочий для реальных API-запросов;
    
- хранение credentials, Host/Origin/CSRF, loopback boundary;
    
- необходимость timeouts, cancellation, лимитов и rate guards;
    
- незакрытые WA4-R и RT-002 gates;
    
- противоречия существующих документов и кода.
    

Для каждого риска — степень, доказательство, минимальный способ устранения, блокирует ли MVP или может быть отложен.

### 5. Требуемая дорожная карта

Выдать конкретную последовательность будущих инженерных TASK, а не одну большую задачу «перенести Ultra».

Для каждого этапа указать:

- цель;
    
- что получит пользователь;
    
- фактическую исходную зависимость;
    
- точные компоненты/файлы предполагаемых изменений;
    
- запреты и границы;
    
- тесты и критерии приёмки;
    
- способ отката;
    
- следующий безопасный шаг.
    

Отдельно предложить **первую небольшую задачу после принятия EVM**, которая приведёт к появлению полезного Ultra Chat, но не потребует одномоментного переноса старой Ultra целиком.

Если выявлены альтернативные маршруты, сравнить их и дать предпочтительный.

### 6. Обязательный документ

Создать:

`Документация/Дополнительная аналитика Астры.md`

Заголовок:

`# Дополнительная аналитика Астры — перенос Ultra в Web Alarm Ultra`

Статус документа:

**ARCHITECTURAL REVIEW / PROPOSAL / AWAITING USER APPROVAL**

Это самостоятельный аналитический документ, который мы будем сохранять и использовать при последующих задачах. Он не заменяет утверждённый план №37 и не утверждает новый порядок исполнения без решения пользователя.

Структура:

1. Краткий вывод.
    
2. Source snapshot и границы исследования.
    
3. AS-IS старая Ultra.
    
4. AS-IS Web Alarm и готовая EVM.
    
5. Матрица переноса возможностей.
    
6. Рекомендуемая архитектура общего ядра.
    
7. Дизайн Ultra Chat и структура Workspace/Chat.
    
8. Перенос ролей, проверок и агентских функций.
    
9. Контексты, оптимизация токенов и бюджеты.
    
10. Риски, блокеры и зависимости.
    
11. Предлагаемые этапы миграции.
    
12. **NEXT TASK** — первая рекомендованная задача для реализации.
    
13. Открытые вопросы и решения, которые должен принять пользователь.
    

Отдельный большой отчёт, дублирующий этот документ, не нужен. Файл и будет основным аналитическим результатом.

### 7. Связь в Obsidian — строго по указанию пользователя

Пользователь указал конкретное место на графе.

Новая заметка должна быть **привязана к документу №24 «План реализации Web Alarm Workspace»**, а не к №37.

Разрешённое исключение для документа №24 — добавить ровно одну Wiki-ссылку:

`[[Дополнительная аналитика Астры]]`

Разместить её в небольшом разделе или строке «Дополнительная аналитика», без изменения нормативного содержания №24.

**Не добавлять Wiki-ссылки на новый документ в №37, №34, №00, №05, №06 или другие заметки.**

В самом новом документе ссылки на документы-источники указывать обычным текстом или кодовыми именами файлов, без новых `[[...]]`.

Перед и после правок проверить количество Wiki-связей №24 и соседних заметок. Ожидаемый эффект — **ровно одно новое ребро графа: 24 ↔ Дополнительная аналитика Астры**.

Если документ №24 имеет локальные несохранённые изменения или уже изменяется другим исполнителем, **не перезаписывать его**: создать только новый аналитический документ и передать координатору готовую однострочную дельту для ссылки.

### 8. Ограничения и параллельные работы

Разрешённая запись:

- `Документация/Дополнительная аналитика Астры.md`;
    
- одна Wiki-ссылка в `Документация/24_План реализации Web Alarm Workspace.md`, только при отсутствии конфликта.
    

Весь production Python/JavaScript, тесты, CI, credential/configuration и другие документы — READ-ONLY.

В LLM 15 параллельно продолжается WA4-R / TOCTOU под управлением Codex. Астра не должна изменять файлы этого направления или согласовывать его как завершённое.

Без отдельного разрешения запрещены:

- выполнение платных GigaChat вызовов;
    
- запуск новых внешних интеграций;
    
- изменение production-кода;
    
- Git/GitHub read/write операции локальным агентом;
    
- отключение защит или тестовых ограничений;
    
- активация замороженного MCP;
    
- удаление Tkinter;
    
- изменение утверждённых RT-002/B2 решений.
    

Это исследование, а не разрешение на implementation или rollout.

### 9. Проверки результата

Перед сдачей Астра самостоятельно проверяет:

- каждое ключевое утверждение опирается на конкретный исходник или документ;
    
- гипотезы явно отделены от доказанных фактов;
    
- не объявлены завершёнными незакрытые RT-002/WA4-R этапы;
    
- исключено дублирование ядра и владельцев состояния;
    
- дорожная карта не содержит скрытых обязательных «переписать всё»;
    
- проектируемый Ultra Chat использует существующие модели EVM;
    
- обычный чат не наследует автоматически весь дорогой agent pipeline;
    
- обратная совместимость Tkinter сохранена;
    
- у каждой будущей задачи указаны проверяемый результат и откат;
    
- появилась только одна разрешённая новая Wiki-связь;
    
- никакой production-код не изменён.
    

### 10. Сдача

Подготовить краткое сообщение координатору:

- `TASK ID`;
    
- статус выполнения;
    
- выбранная архитектура и главные аргументы;
    
- основные находки и риски;
    
- предлагаемый первый implementation-шаг;
    
- точное местоположение аналитического документа;
    
- создана ли Wiki-связь №24;
    
- какие файлы изменены;
    
- что не проверялось;
    
- что требуется решить пользователю.
    

**Итоговый статус:** `RESULT READY / AWAITING INDEPENDENT REVIEW`.

После выполнения пользователь публикует файлы в GitHub. ChatGPT независимо проверяет аналитику, качество дорожной карты, документационную дельту и состояние Obsidian Graph.

**Не объявлять план утверждённым до решения пользователя.**
---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Полный архив — [[001_История выполненных задач Codex]].

- **2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — admission policy inside existing broker/security pipeline; Codex 52/52 offline, 51/51 regression (19 overlap), 7/7 mutants, WEB_12 independent 53/53 manifest; **PASS / BOUNDED OFFLINE ACCEPTED**, native/WFP/Chat NOT VERIFIED.
- **2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — source-only exact sing dependency; Codex 51/51, WEB_12 87/87, six upstream files and 33 locators. **TERMINAL PARTIAL**, native blocked.
- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — source-only sing-box v1.13.4, defaults DIRECT/DNS/UoT; WEB_11 bounded source accepted, native not run.
- **2026-10-24 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — embedded sing-box local snapshot, WEB_11 bounded, installed executable not attested.
- **2026-10-24 / CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — disabled broker preflight, WEB_11 bounded offline, engine/WFP blocked.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — new `strict_preflight`, separated structural vs strict policy statuses; controller-owned canonical/source pins, opaque auth refs, CONNECT-only exact destination and deny DIRECT/fallback/secondary/DNS/UDP/UoT/IPv6/merge/reload. Codex 52/52 offline, 51/51 overlapping compatible tests, 7 mutants caught, preserved RED 19/21, WEB_12 53/53 manifest SHA. **OFFLINE PASS only**, upstream credentials in 407/error logs still SECURITY BLOCKER. Real C/B SID/NPFS, WFP, secret-store and ChatGPT E2E NOT VERIFIED. `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/report.md`.
- **CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — WEB_12 terminal bounded source-only PARTIAL, 87/87 files and 6/6 upstream SHA/33 locators; no native/real egress. `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/report.md`.
- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — WEB_11 bounded 30/30 Codex, sing-box defaults DIRECT/DNS/UoT/other conditional route risks. `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`.
- **CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — WEB_11 bounded snapshot, Codex 44/44, actual engine attestation/native not run. `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/report.md`.
- **CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — WEB_11 bounded 33/33 broker, 63/63 MCP, 24/24 security Codex evidence, no native WFP. `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/report.md`.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Verifier:** WEB_12 / ChatGPT. Codex — READ-ONLY. Исторические вердикты в №06.

## 1. Последний вердикт — WEB_12 / 2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001

**PASS / INDEPENDENT BOUNDED OFFLINE SOURCE & EVIDENCE ACCEPTED**, `main@6456d669a8a804ddd75a0dbca242782c18d914da`.

**Независимый вердикт WEB_12:** **PASS / INDEPENDENT BOUNDED OFFLINE SOURCE & EVIDENCE ACCEPTED** — только `strict admission` Python, source и опубликованная evidence на `main@6456d669a8a804ddd75a0dbca242782c18d914da`; актуальная база при документационном closeout `main@124b43ed47ec5b2b40217324345ddbdd88066a19`. **Не** является native/Windows/WFP, физическим no-DIRECT, credential-safe upstream или ChatGPT MCP E2E pass.

**Проверено самостоятельно WEB_12:** manifest **53/53** опубликованных файлов по размерам и SHA-256 (с учётом CRLF/LF); frozen task B1 совпадает с `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/evidence/task_snapshot.md`, blob `fb13fa784b168c371db87f6f2d750fa0dbc85b13` (manifest SHA256 `9e9c8b73f2496093924e6c50ca0eefea9148002a888c65ae6e2b5865e4ae843a`, 14632 байт), 4/4 исходных файлов `source_before/` по blob SHA совпали с предшествующим изменению HEAD; просмотрены `broker.py`, `security_contract.py`, schema, новая `admission_suite.py` и decision flow, source pin, red/green evidence, mutant outputs. **Codex-run** 52/52 PASS, 51/51 совместимая source/pure regression PASS, **7/7** executed Python mutants caught, initial **19 PASS / 21 FAIL / 0 ERROR** saved. Counts **перекрываются на 19 legacy pure tests**, не складывать их как уникальные. WEB_12 **не запускал** этот suite на независимой Windows или нативном движке; integrity 53/53 не означает native proof.

**Реализовано:** `strict_preflight(raw_bytes, controller_config_pin, controller_source_pin, request_metadata)` повторно использует existing common/parser, schema, `security.validate` и `validate_admission`; structural valid ≠ strict admitted; `strict_policy_status=VALID` может сочетаться с `STRICT_ADMISSION_BLOCKED`. Opaque `wua-secret-ref:` (без чтения credential store), mandatory/nonempty/unique auth declaration, отдельный upstream reference, protected canonical single source, exact controller-owned SHA pin, CONNECT-only request metadata/host/port, deny unknown auth/outbound/DIRECT/fallback/DNS/UDP/UoT/IPv6/secondary/merge/reload/environment override; negative tests/explicit rejection codes. **Не превращать декларативную проверку в утверждение, что реальный native движок/OS соблюдают запрет.**

**Остаточные блокировки:** опасность upstream `sing` при ошибках 407 (credentials/`Proxy-Authorization` in error/log) сохраняется **SECURITY BLOCKER**, не устранена Python offline-контрактом; secret store access control, native listener/auth, exact installed binary/engine compatibility, real Windows identities C/B, SID/NPFS cross-user, WFP IPv4+IPv6/DNS/IPC, B-only egress and fail-closed/physical no DIRECT, native route and ordinary ChatGPT MCP E2E **NOT VERIFIED**. `engine.family=V2Ray` unchanged, `STRICT_ADMISSION_BLOCKED`, `can_apply=false`, `can_start_tunnel=false`, `install_uninstall=BLOCKED`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`. No live tunnel, proxy, Windows, WFP or engine change was authorized. Publication commit also included unrelated user-side `.obsidian/workspace.json` metadata: does not affect source acceptance; keep extraneous files out of future scoped technical publications.

**Terminal disposition authorized by user:** offline TASK accepted/archived, old B1 cleared to WAITING. No automatic engine/native/WFP/network/tunnel GO; next task goes in chat only. Full archives in 001, `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/`, journal №06.

## 2. Последний вердикт — 2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001 / amendment01

**TERMINAL PARTIAL / INDEPENDENT BOUNDED SOURCE & EVIDENCE ACCEPTED**, `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; user explicitly approved terminal PARTIAL closeout, not full security approval.

Codex 007: exact source-only `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`; one GET via explicitly approved HTTP CONNECT according to agent audit, 0 redirects/fallback, 322 module files, ZIP raw SHA-256 `dfb3b8c7cbc603602c6cf453161d319209e5610477e1118354dd449bd9409659`, Go module h1 `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`. Baseline 30/30, first RED 49/50 (Windows ZIP name normalization; preserved), intermediate 50/50, final **51/51 PASS** (11 source +19 pure +21 dependency), per Codex logs; not independently rerun on Windows.

WEB_12: `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; **87/87** published manifest paths bytes+SHA independently matched (LF/CRLF-aware); **6/6** independently fetched official `SagerNet/sing@ed51f65fbfde` source files and **33/33** locators match; Go module h1 recomputed from **published SHA values of 322 members**, not independently from original ZIP. Stored FAIL/final result and tests inspected. Physical egress/installed executable/ZIP itself, native Go/Windows/WFP, C/B SIDs/sockets, no-DIRECT proof and ordinary ChatGPT MCP E2E **NOT VERIFIED**.

Source risks: `users=[]` disables proxy authentication; 407/error logs can expose username/password or `Proxy-Authorization`; CONNECT sends `200` before dial/route; HTTP Upgrade/plain alternatives and X-Forwarded-For source override; URL-safe-vs-standard Basic Base64 ambiguity and ignored port-parse error; permissive JSON duplicates/null/case/merge/reload; prior default DIRECT, local DNS/UoT/optional other egress; Go stdlib/x/sys source/native behavior incomplete. No proven native bypass asserted. `engine.family=V2Ray` unchanged, `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`; no install/engine switch/proxy/system activation.

Full report `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/amendment_01/report.md`, manifest `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/manifest.json`; pinned complete task in personal 001. No permission to enable/alter engine, Windows, proxy, WFP, local identities, hosted tunnel, ordinary ChatGPT connection or network route.

## 3. Предыдущий — WEB_11 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001

**PARTIAL / INDEPENDENT BOUNDED SOURCE REVIEW ACCEPTED**, `main@e0c89b3536cb030edc4fa905a8e00f1047788c4c`, 76/76 paths, 7/7 selected hashes, Codex 30/30 offline, native NOT RUN. Missing sing module source was historical state later narrowed by WEB_12.

## 4. Позапрошлый — WEB_11 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001

**PARTIAL / BOUNDED STATIC-SNAPSHOT ACCEPTED**, `main@bc0a1be97e7a44a0869310e6961e77ff6c841073`, 70/70 paths, 10/10 hashes, Codex 44/44, native NOT RUN.

---

**Status:** source-only partial, not production. Full earlier NPFS/broker independent verdicts remain permanently archived №06; B1 waiting only after user-approved terminal closeout.
