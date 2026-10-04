# Задачи Claude

**Назначение:** отдельный оперативный handoff для задач, которые передаются Claude Desktop / Claude Code в проекте `ag_llm`.

Основной проектный handoff: [[000_Задачи для агента]]
Персональная история выполненных Claude TASK: [[001_История выполненных задач Claude]]

## Правила

- Здесь фиксируются только конкретные задачи, делегированные Claude.
- Этот файл **не заменяет** `000_Задачи для агента.md`, `05_Реестр задач.md`, `06_Журнал выполнения и отчёты.md` и профильные документы проекта.
- Если Claude выполняет значимое изменение проекта, итог после проверки должен быть отражён и в канонической документации проекта по обычным правилам.
- До начала mutation-задачи явно указывать scope, запрещённые действия и критерии проверки.
- Секреты, токены, cookies, Organization ID и платёжные данные сюда не записываются.
- Технические наблюдения по моделям, лимитам и сети вести в `27_Claude.md`.
- БЛОК 1 — пользовательский активный слот. Пользователь переносит сюда следующую утверждённую постановку. Claude обязан перечитать БЛОК 1 перед стартом, но не переписывает и не очищает его без отдельной явной команды.
- После завершения исполнения Claude копирует постановку из БЛОКА 1 в БЛОК 2, сохраняя смысл, scope, запреты и acceptance. БЛОК 2 хранит последнюю выполненную постановку, чтобы она не терялась при следующей замене БЛОКА 1.
- БЛОК 3 — краткий operational closeout Claude: что реально изменено, какие файлы затронуты, какие проверки выполнены, что осталось вне scope, путь к подробному отчёту и статус. До независимой проверки допустим только `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, не `DONE / VERIFIED`.
- До перезаписи БЛОКОВ 2–3 предыдущая независимо подтверждённая TASK должна уже иметь постоянную append-only историю.
- Полная постановка TASK может дополнительно фиксироваться в обычном Chat как человеческий резерв/след обсуждения, но каноническим источником исполнения остаётся актуальный БЛОК 1 персональной карточки.
- Claude сам ведёт только свой оперативный handoff (`БЛОК 2` + `БЛОК 3`) и task-report в `Alarm/ALARM_TASK_SESSION`. Постоянный documentation closeout после независимой проверки выполняет verifier/ChatGPT: `001_История выполненных задач Claude.md`, `06_Журнал выполнения и отчёты.md`, профильный журнал/реестр и другие реально затронутые канонические документы.

---
# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

**Статус:** READY / NOT STARTED.
**TASK:** CLAUDE-WA-004 — RC-2: Persistent Resolver + evidence revision binding.
**Дата постановки:** 2026-10-04.
**Модель:** Claude Opus 5.5.

## 1. Исходная точка

RC-1 / `CLAUDE-WA-003` независимо проверен ChatGPT и закрыт **DONE / VERIFIED**.

Принятый baseline RC-1:
- Operation Contract v2 restart-safe и self-contained;
- contract хранит canonical target identity, server-observed pre-state, expected post-state, durable payload/ref, request fingerprint, provenance, revision и DONE receipt;
- legacy contract v1 читается backward-compatible, но `rearm_contract_sufficient=false`;
- Operation Store/revision имеет минимальную межпроцессную сериализацию;
- authoritative physical mutation executor ещё отсутствует.

Независимая проверка RC-1: full regression **241/241 PASS**, focused RC-1 **44/44 PASS**, multiprocess concurrency повторно PASS, live legacy `WA37-CTRL-001/002` fresh-process readable без изменения storage.

Канонический порядок после RC-1:

`RC-2 → RC-3 → RC-4 → RC-5 → RC-6 → WA4-E → WA4-A → WA4-O → WA4-R`.

## 2. Цель RC-2

Сейчас reconciliation выдаёт детерминированное решение, но оно остаётся advisory и не имеет собственного persistent lifecycle.

Нужно добавить **узкий persistent Resolver layer**, который превращает recovery choice в tracked action:

- `ADOPT`;
- `RETRY`;
- `ROLLBACK`;
- `ABORT`.

Главный инвариант:

> Resolver action действителен только для той конкретной версии evidence и Operation Contract, на которой он был принят. Если target/evidence/operation revision уже изменились, старое решение не применяется: fail-closed → новая reconciliation.

RC-2 должен сделать recovery decision durable/restart-safe, но **не должен выполнять физические project mutations**.

## 3. Важная архитектурная граница

RT-001 пункт V15 **отложил проектирование точной новой microtask/operation state machine**.

Поэтому в RC-2:

- не менять публичный `OperationStatus` и не добавлять в него новые состояния только ради Resolver;
- не перепроектировать lifecycle TASK/microtask;
- не превращать `ADOPT/RETRY/ROLLBACK/ABORT` в скрытую новую глобальную state machine;
- предпочтительно реализовать отдельный узкий `ResolutionRecord / ResolverStore / ResolverService` (названия на инженерное усмотрение), который хранит recovery action и его basis;
- если для корректного выполнения RC-2 реально необходимо изменить публичный operation/microtask lifecycle — **остановиться и оформить DECISION REQUIRED**, а не принимать такое архитектурное решение самостоятельно.

Собственный минимальный внутренний статус Resolution record допустим только как техническая деталь хранения Resolver и не должен становиться новым публичным lifecycle проекта без отдельного решения.

## 4. Что должно быть связано с каждым tracked resolution

Persistent resolution должен однозначно содержать/связывать как минимум:

- `resolution_id`;
- `task_id`;
- `microtask_id`;
- `operation_id`;
- requested action: `ADOPT / RETRY / ROLLBACK / ABORT`;
- исходное deterministic reconciliation decision/reason;
- **evidence_fingerprint**, вычисленный существующим `ReconciliationDecisionEngine`;
- `operation.contract_version`;
- **operation revision** для contract v2;
- request/contract fingerprint или другую устойчивую identity операции;
- timestamp/provenance;
- результат проверки/apply: accepted / stale / rejected + machine-readable reason;
- `NEXT_SAFE_ACTION`.

Не считать одного `evidence_version=1` ревизией фактических evidence: binding должен использовать фактический fingerprint + operation revision.

## 5. Проверка свежести перед принятием action

Перед тем как tracked action считается принятым, Resolver обязан заново получить authoritative state:

1. перечитать OperationRecord;
2. заново собрать reconciliation evidence из текущего Workspace;
3. заново вычислить evidence fingerprint;
4. сверить operation revision / contract identity;
5. убедиться, что новое deterministic decision всё ещё совместимо с запрошенным action.

Если хоть одна binding identity изменилась — action не применяется и не получает статус успешного resolution. Нужна новая reconciliation.

Важно: RC-3 CAS по physical target ещё не существует. Поэтому RC-2 не должен изображать, будто способен навсегда «заблокировать» target после проверки. Persistent resolution остаётся привязанным к своему basis; при последующем использовании/возобновлении его freshness должна быть проверяема, а stale resolution не должен становиться authority.

## 6. Семантика четырёх действий в RC-2

### ADOPT

Разрешён только когда актуальный deterministic decision = `ADOPT_CURRENT_STATE`.

В RC-2 ADOPT:
- фиксирует persistent факт, что существующее Workspace state принято recovery-решением на конкретном evidence basis;
- может отражаться в Resolver events / Recovery Report;
- **не должен молча переводить существующий OperationRecord в новый lifecycle**, если для этого требуется изменение отложенной state machine;
- физический Workspace не меняет.

### RETRY

Разрешён только когда актуальный decision = `RETRY_SAFE`.

Дополнительные условия:
- contract v2;
- `rearm_contract_sufficient=true`;
- durable payload/ref проходит integrity check;
- legacy v1 и incomplete v2 не получают re-arm.

В RC-2 RETRY означает только:
**persistent re-arm / разрешение будущему executor повторно исполнить тот же logical operation с тем же `operation_id`**.

RC-2 **не вызывает write/edit/delete и не выполняет payload**.

### ROLLBACK

Разрешён только когда актуальный decision = `ROLLBACK_CURRENT_MICROTASK`.

В RC-2 ROLLBACK означает только persistent tracked rollback request/resolution.

Запрещено:
- вызывать restore;
- удалять/перезаписывать target;
- менять реальные файлы;
- заявлять, что rollback уже физически выполнен.

Физический safe rollback с сохранением current drift — только RC-4.

### ABORT

ABORT должен стать persistent/idempotent recovery action, означающим: Resolver прекращает дальнейшее recovery-действие по этому resolution и не разрешает RETRY/ADOPT/ROLLBACK на основании него.

ABORT сам не выполняет project mutation и не должен придумывать новый terminal `OperationStatus`. Если корректная семантика ABORT требует изменения глобального operation lifecycle — DECISION REQUIRED.

## 7. Idempotency / replay

Повтор того же logical resolution с тем же:
- `resolution_id` / identity,
- action,
- evidence fingerprint,
- operation revision

должен вернуть известный persistent result без второй записи эффекта/перехода.

Повтор того же identity с другим action или другим basis — conflict/fail-closed.

Concurrent duplicate apply одного resolution из нескольких process не должен создавать несколько успешных resolution/event. Для целостности Resolver store допустима собственная минимальная межпроцессная сериализация. Это **не** RC-3 conflict gate по target.

## 8. Recovery Report: убрать caller authority

После RC-2 Recovery Report должен отражать recovery actions из persistent Resolver state/events, а не доверять словам вызывающего.

Особенно важно:
- `accepted_as_already_done` может появляться только из подтверждённого tracked ADOPT;
- RC-2 RETRY — это re-arm, поэтому **не записывать его как `actually_retried`**, пока физического retry не было;
- RC-2 ROLLBACK — request only, поэтому **не записывать его как `actually_rolled_back`**;
- Report остаётся `authority=evidence_only`, `automatic_mutation_authorized=false`;
- старый API/legacy reports не ломать без необходимости; если сохраняется совместимость, caller-supplied поля не должны иметь права создать ложное authoritative утверждение о выполненном recovery action.

Recovery Report должен быть воспроизводим fresh-process из persisted evidence + Resolver records/events.

## 9. Что НЕ входит в RC-2

Не делать:
- canonical-target conflict admission / ownership reservation — RC-3;
- mutation-boundary CAS — RC-3;
- destructive restore / сохранение drift перед restore — RC-4;
- checkpoint projection rebuild — RC-5;
- project-level resume — RC-6;
- physical write/edit/delete executor — WA4-E;
- UI;
- `.gitattributes`;
- MCP/transport redesign;
- commit / push;
- автоматический старт RC-3.

Не расширять scope только ради «красивой архитектуры».

## 10. Обязательная проверка

Нужны тесты как минимум на следующие свойства:

1. `ADOPT`, `RETRY`, `ROLLBACK`, `ABORT` persistent и переживают fresh process.
2. Action/decision mismatch блокируется:
   - RETRY при ADOPT decision;
   - ADOPT при RETRY_SAFE;
   - и т. п.
3. **Stale target evidence:** reconcile → изменить test target → apply старого resolution → fail-closed.
4. **Stale operation revision:** reconcile → изменить operation revision допустимым переходом → apply старого resolution → fail-closed.
5. Повтор того же resolution = idempotent replay, без duplicate successful event/effect.
6. Тот же resolution identity с другим action/basis = conflict.
7. RETRY на legacy v1 = reject; RETRY на incomplete/corrupt v2 = reject.
8. Payload integrity failure запрещает RETRY re-arm.
9. RETRY/ROLLBACK/ABORT не меняют physical target: byte hash до/после идентичен.
10. ADOPT не создаёт физическую mutation.
11. Recovery Report строит action facts из Resolver persistence:
    - ADOPT может отразиться как accepted;
    - RETRY re-arm не становится `actually_retried`;
    - ROLLBACK request не становится `actually_rolled_back`.
12. Fresh process видит тот же resolution, basis, result и корректный `NEXT_SAFE_ACTION`.
13. Concurrent duplicate resolver apply не создаёт два successful resolution.
14. Полный `python -B -m unittest test_web_alarm_*.py`.
15. `python -B -m compileall -q web_alarm`.
16. `git diff --check`.

Тестовая физическая правка test fixture для stale-evidence сценария допустима только внутри временного test workspace; реальный project workspace задача не мутирует.

## 11. Критерий RC-2 PASS

RC-2 считается готовым к независимой проверке, если одновременно доказано:

- все четыре recovery actions имеют persistent tracked identity;
- action жёстко связан с evidence fingerprint + operation revision/identity;
- stale basis не применяется;
- replay idempotent;
- RETRY = только re-arm;
- ROLLBACK = только tracked request;
- ADOPT/ABORT не требуют скрытого изменения global OperationStatus;
- legacy/incomplete contract не получает unsafe RETRY;
- Recovery Report больше не принимает caller claims за факт выполненного recovery action;
- fresh process восстанавливает то же resolution состояние;
- physical project mutation отсутствует;
- старые тесты не сломаны.

## 12. Порядок работы и closeout

Перед изменениями:
- перечитать реальный current code, не полагаться только на эту постановку;
- проверить drift после RC-1;
- создать рабочую папку `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/` и сохранить нужные safety copies/notes по действующему регламенту;
- если обнаружено противоречие этой TASK утверждённому RT-001 или фактическому RC-1 — остановиться и сообщить, а не молча менять смысл.

После реализации:
- отчёт: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/rc2_report.md`;
- в `000_Задачи Claude.md` скопировать выполненную постановку БЛОКА 1 в БЛОК 2 и заполнить БЛОК 3 кратким фактическим результатом;
- БЛОК 1 не очищать и не заменять: следующую утверждённую TASK туда переносит пользователь;
- `001`, `06`, `25` и другой permanent documentation closeout до независимой проверки не изменять по собственной инициативе — их синхронизирует verifier/ChatGPT после PASS;
- статус до независимой проверки: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**;
- не объявлять DONE самостоятельно;
- не делать commit/push;
- RC-3 не начинать.

**NEXT SAFE ACTION сейчас:** эта постановка только зафиксирована. После явной команды пользователя Claude перечитывает БЛОК 1, выполняет drift check и приступает только к `CLAUDE-WA-004 / RC-2`.
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена Claude 2026-10-04; после независимой проверки (REVIEW FAILED, 2 blocker-а) выполнен Independent Review Repair той же TASK — его постановка дословно ниже исходной. Результат и статус — в БЛОКЕ 3. Исходная постановка из БЛОКА 1 приведена без изменений (опущены только строки статуса слота и его NEXT SAFE ACTION).

**TASK:** CLAUDE-WA-004 — RC-2: Persistent Resolver + evidence revision binding.
**Дата постановки:** 2026-10-04.
**Модель:** Claude Opus 5.5.

## 1. Исходная точка

RC-1 / `CLAUDE-WA-003` независимо проверен ChatGPT и закрыт **DONE / VERIFIED**.

Принятый baseline RC-1:
- Operation Contract v2 restart-safe и self-contained;
- contract хранит canonical target identity, server-observed pre-state, expected post-state, durable payload/ref, request fingerprint, provenance, revision и DONE receipt;
- legacy contract v1 читается backward-compatible, но `rearm_contract_sufficient=false`;
- Operation Store/revision имеет минимальную межпроцессную сериализацию;
- authoritative physical mutation executor ещё отсутствует.

Независимая проверка RC-1: full regression **241/241 PASS**, focused RC-1 **44/44 PASS**, multiprocess concurrency повторно PASS, live legacy `WA37-CTRL-001/002` fresh-process readable без изменения storage.

Канонический порядок после RC-1:

`RC-2 → RC-3 → RC-4 → RC-5 → RC-6 → WA4-E → WA4-A → WA4-O → WA4-R`.

## 2. Цель RC-2

Сейчас reconciliation выдаёт детерминированное решение, но оно остаётся advisory и не имеет собственного persistent lifecycle.

Нужно добавить **узкий persistent Resolver layer**, который превращает recovery choice в tracked action:

- `ADOPT`;
- `RETRY`;
- `ROLLBACK`;
- `ABORT`.

Главный инвариант:

> Resolver action действителен только для той конкретной версии evidence и Operation Contract, на которой он был принят. Если target/evidence/operation revision уже изменились, старое решение не применяется: fail-closed → новая reconciliation.

RC-2 должен сделать recovery decision durable/restart-safe, но **не должен выполнять физические project mutations**.

## 3. Важная архитектурная граница

RT-001 пункт V15 **отложил проектирование точной новой microtask/operation state machine**.

Поэтому в RC-2:

- не менять публичный `OperationStatus` и не добавлять в него новые состояния только ради Resolver;
- не перепроектировать lifecycle TASK/microtask;
- не превращать `ADOPT/RETRY/ROLLBACK/ABORT` в скрытую новую глобальную state machine;
- предпочтительно реализовать отдельный узкий `ResolutionRecord / ResolverStore / ResolverService` (названия на инженерное усмотрение), который хранит recovery action и его basis;
- если для корректного выполнения RC-2 реально необходимо изменить публичный operation/microtask lifecycle — **остановиться и оформить DECISION REQUIRED**, а не принимать такое архитектурное решение самостоятельно.

Собственный минимальный внутренний статус Resolution record допустим только как техническая деталь хранения Resolver и не должен становиться новым публичным lifecycle проекта без отдельного решения.

## 4. Что должно быть связано с каждым tracked resolution

Persistent resolution должен однозначно содержать/связывать как минимум:

- `resolution_id`;
- `task_id`;
- `microtask_id`;
- `operation_id`;
- requested action: `ADOPT / RETRY / ROLLBACK / ABORT`;
- исходное deterministic reconciliation decision/reason;
- **evidence_fingerprint**, вычисленный существующим `ReconciliationDecisionEngine`;
- `operation.contract_version`;
- **operation revision** для contract v2;
- request/contract fingerprint или другую устойчивую identity операции;
- timestamp/provenance;
- результат проверки/apply: accepted / stale / rejected + machine-readable reason;
- `NEXT_SAFE_ACTION`.

Не считать одного `evidence_version=1` ревизией фактических evidence: binding должен использовать фактический fingerprint + operation revision.

## 5. Проверка свежести перед принятием action

Перед тем как tracked action считается принятым, Resolver обязан заново получить authoritative state:

1. перечитать OperationRecord;
2. заново собрать reconciliation evidence из текущего Workspace;
3. заново вычислить evidence fingerprint;
4. сверить operation revision / contract identity;
5. убедиться, что новое deterministic decision всё ещё совместимо с запрошенным action.

Если хоть одна binding identity изменилась — action не применяется и не получает статус успешного resolution. Нужна новая reconciliation.

Важно: RC-3 CAS по physical target ещё не существует. Поэтому RC-2 не должен изображать, будто способен навсегда «заблокировать» target после проверки. Persistent resolution остаётся привязанным к своему basis; при последующем использовании/возобновлении его freshness должна быть проверяема, а stale resolution не должен становиться authority.

## 6. Семантика четырёх действий в RC-2

### ADOPT

Разрешён только когда актуальный deterministic decision = `ADOPT_CURRENT_STATE`.

В RC-2 ADOPT:
- фиксирует persistent факт, что существующее Workspace state принято recovery-решением на конкретном evidence basis;
- может отражаться в Resolver events / Recovery Report;
- **не должен молча переводить существующий OperationRecord в новый lifecycle**, если для этого требуется изменение отложенной state machine;
- физический Workspace не меняет.

### RETRY

Разрешён только когда актуальный decision = `RETRY_SAFE`.

Дополнительные условия:
- contract v2;
- `rearm_contract_sufficient=true`;
- durable payload/ref проходит integrity check;
- legacy v1 и incomplete v2 не получают re-arm.

В RC-2 RETRY означает только:
**persistent re-arm / разрешение будущему executor повторно исполнить тот же logical operation с тем же `operation_id`**.

RC-2 **не вызывает write/edit/delete и не выполняет payload**.

### ROLLBACK

Разрешён только когда актуальный decision = `ROLLBACK_CURRENT_MICROTASK`.

В RC-2 ROLLBACK означает только persistent tracked rollback request/resolution.

Запрещено:
- вызывать restore;
- удалять/перезаписывать target;
- менять реальные файлы;
- заявлять, что rollback уже физически выполнен.

Физический safe rollback с сохранением current drift — только RC-4.

### ABORT

ABORT должен стать persistent/idempotent recovery action, означающим: Resolver прекращает дальнейшее recovery-действие по этому resolution и не разрешает RETRY/ADOPT/ROLLBACK на основании него.

ABORT сам не выполняет project mutation и не должен придумывать новый terminal `OperationStatus`. Если корректная семантика ABORT требует изменения глобального operation lifecycle — DECISION REQUIRED.

## 7. Idempotency / replay

Повтор того же logical resolution с тем же:
- `resolution_id` / identity,
- action,
- evidence fingerprint,
- operation revision

должен вернуть известный persistent result без второй записи эффекта/перехода.

Повтор того же identity с другим action или другим basis — conflict/fail-closed.

Concurrent duplicate apply одного resolution из нескольких process не должен создавать несколько успешных resolution/event. Для целостности Resolver store допустима собственная минимальная межпроцессная сериализация. Это **не** RC-3 conflict gate по target.

## 8. Recovery Report: убрать caller authority

После RC-2 Recovery Report должен отражать recovery actions из persistent Resolver state/events, а не доверять словам вызывающего.

Особенно важно:
- `accepted_as_already_done` может появляться только из подтверждённого tracked ADOPT;
- RC-2 RETRY — это re-arm, поэтому **не записывать его как `actually_retried`**, пока физического retry не было;
- RC-2 ROLLBACK — request only, поэтому **не записывать его как `actually_rolled_back`**;
- Report остаётся `authority=evidence_only`, `automatic_mutation_authorized=false`;
- старый API/legacy reports не ломать без необходимости; если сохраняется совместимость, caller-supplied поля не должны иметь права создать ложное authoritative утверждение о выполненном recovery action.

Recovery Report должен быть воспроизводим fresh-process из persisted evidence + Resolver records/events.

## 9. Что НЕ входит в RC-2

Не делать:
- canonical-target conflict admission / ownership reservation — RC-3;
- mutation-boundary CAS — RC-3;
- destructive restore / сохранение drift перед restore — RC-4;
- checkpoint projection rebuild — RC-5;
- project-level resume — RC-6;
- physical write/edit/delete executor — WA4-E;
- UI;
- `.gitattributes`;
- MCP/transport redesign;
- commit / push;
- автоматический старт RC-3.

Не расширять scope только ради «красивой архитектуры».

## 10. Обязательная проверка

Нужны тесты как минимум на следующие свойства:

1. `ADOPT`, `RETRY`, `ROLLBACK`, `ABORT` persistent и переживают fresh process.
2. Action/decision mismatch блокируется:
   - RETRY при ADOPT decision;
   - ADOPT при RETRY_SAFE;
   - и т. п.
3. **Stale target evidence:** reconcile → изменить test target → apply старого resolution → fail-closed.
4. **Stale operation revision:** reconcile → изменить operation revision допустимым переходом → apply старого resolution → fail-closed.
5. Повтор того же resolution = idempotent replay, без duplicate successful event/effect.
6. Тот же resolution identity с другим action/basis = conflict.
7. RETRY на legacy v1 = reject; RETRY на incomplete/corrupt v2 = reject.
8. Payload integrity failure запрещает RETRY re-arm.
9. RETRY/ROLLBACK/ABORT не меняют physical target: byte hash до/после идентичен.
10. ADOPT не создаёт физическую mutation.
11. Recovery Report строит action facts из Resolver persistence:
    - ADOPT может отразиться как accepted;
    - RETRY re-arm не становится `actually_retried`;
    - ROLLBACK request не становится `actually_rolled_back`.
12. Fresh process видит тот же resolution, basis, result и корректный `NEXT_SAFE_ACTION`.
13. Concurrent duplicate resolver apply не создаёт два successful resolution.
14. Полный `python -B -m unittest test_web_alarm_*.py`.
15. `python -B -m compileall -q web_alarm`.
16. `git diff --check`.

Тестовая физическая правка test fixture для stale-evidence сценария допустима только внутри временного test workspace; реальный project workspace задача не мутирует.

## 11. Критерий RC-2 PASS

RC-2 считается готовым к независимой проверке, если одновременно доказано:

- все четыре recovery actions имеют persistent tracked identity;
- action жёстко связан с evidence fingerprint + operation revision/identity;
- stale basis не применяется;
- replay idempotent;
- RETRY = только re-arm;
- ROLLBACK = только tracked request;
- ADOPT/ABORT не требуют скрытого изменения global OperationStatus;
- legacy/incomplete contract не получает unsafe RETRY;
- Recovery Report больше не принимает caller claims за факт выполненного recovery action;
- fresh process восстанавливает то же resolution состояние;
- physical project mutation отсутствует;
- старые тесты не сломаны.

## 12. Порядок работы и closeout

Перед изменениями:
- перечитать реальный current code, не полагаться только на эту постановку;
- проверить drift после RC-1;
- создать рабочую папку `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/` и сохранить нужные safety copies/notes по действующему регламенту;
- если обнаружено противоречие этой TASK утверждённому RT-001 или фактическому RC-1 — остановиться и сообщить, а не молча менять смысл.

После реализации:
- отчёт: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/rc2_report.md`;
- в `000_Задачи Claude.md` скопировать выполненную постановку БЛОКА 1 в БЛОК 2 и заполнить БЛОК 3 кратким фактическим результатом;
- БЛОК 1 не очищать и не заменять: следующую утверждённую TASK туда переносит пользователь;
- `001`, `06`, `25` и другой permanent documentation closeout до независимой проверки не изменять по собственной инициативе — их синхронизирует verifier/ChatGPT после PASS;
- статус до независимой проверки: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**;
- не объявлять DONE самостоятельно;
- не делать commit/push;
- RC-3 не начинать.

## Дополнение — Independent Review Repair (постановка из Chat, 2026-10-04, дословно)

```text
TASK: CLAUDE-WA-004 / RC-2 — INDEPENDENT REVIEW REPAIR
Статус:
RC-2 = REVIEW FAILED / REPAIR REQUIRED
Не DONE.
RC-3 НЕ начинать.
Независимая проверка выполнена ChatGPT по последнему коммиту репозитория:
Commit 147
fe55c99db2c2493f99db807a95ba6bd8a668b4fe
Основная реализация Resolver подтверждена и НЕ требует переписывания.
Независимо PASS:

* focused Resolver: 19/19;
* full Web Alarm regression: 260/260;
* multiprocess duplicate apply: дополнительно 5/5 PASS;
* compileall PASS;
* git diff --check PASS;
* stale evidence fail-closed работает;
* stale operation revision fail-closed работает;
* RETRY не выполняет physical mutation;
* ROLLBACK остаётся tracked request only;
* ADOPT не меняет OperationStatus;
* legacy RETRY блокируется;
* payload integrity проверяется;
* replay resolution идемпотентен;
* новая глобальная state machine не введена.

Найдены ДВА blocker-а acceptance RC-2.
Независимо воспроизведено:
Исходная reconciliation:
decision = RETRY_SAFE
После accepted ABORT Resolver persistent хранит:
RESOLUTION_NEXT:
Resolver-level recovery of operation op1 is closed;
no further ADOPT/RETRY/ROLLBACK will be accepted for it
Но новый Recovery Report на том же persistent state выдаёт:
REPORT_NEXT:
retry only through the replay-safe execution path using the same operation_id
То есть persistent Resolver говорит ABORT / recovery closed,
а fresh Recovery Report одновременно рекомендует RETRY.
Это нарушает RC-2 requirement:
NEXT SAFE ACTION после resolution/reopen должен выводиться
из persistent authoritative state.
Причина по review:
RecoveryReportBuilder всё ещё получает next_safe_action
из текущего ReconciliationDecision и не учитывает authoritative Resolver outcome.
ТРЕБУЕТСЯ:

1. После persistent Resolver outcome Recovery Report / reopen должен выводить
NEXT SAFE ACTION с учётом Resolver state.
2. Accepted ABORT должен иметь приоритет над advisory reconciliation:
после accepted ABORT Recovery Report не может рекомендовать
ADOPT / RETRY / ROLLBACK по той же операции.
3. Для других accepted resolutions NEXT SAFE ACTION должен отражать
фактическую persistent Resolver semantics:
   * RETRY = re-armed request only, ничего не выполнено;
   * ROLLBACK = tracked rollback request only;
   * ADOPT = accepted existing state;
   * ABORT = recovery closed.
4. Не вводить новую public Operation/Microtask state machine.
Решение должно оставаться внутри узкого Resolver/Recovery Report layer.
5. Если resolution stale, он не должен становиться authority.
В таком случае NEXT SAFE ACTION должен требовать новую reconciliation /
fresh resolution, а не продолжать старое действие.

Независимо воспроизведено:
Persistent Resolver записал:
RESOLUTION_RESULT = STALE
result_code = EVIDENCE_FINGERPRINT_CHANGED
Resolution физически присутствует в Resolver store:
STORE_COUNT = 1
Но fresh Recovery Report выдаёт:
resolver_actions = []
Причина по review:
ResolverService.report_facts() фильтрует records только по:
result == ACCEPTED
В результате persistent STALE / REJECTED resolution/result
не попадают в Recovery Report вообще.
Это нарушает requirement RC-2:
Recovery Report должен строиться/обновляться
из persistent resolver records/events,
а fresh process должен получать тот же resolution/result.
ТРЕБУЕТСЯ:

1. Recovery Report `resolver_actions` должен отражать persistent
Resolver records всех релевантных результатов:
   * ACCEPTED;
   * STALE;
   * REJECTED.
2. При этом authority-effects должны остаться fail-closed:
   * `accepted_as_already_done` только из FRESH + ACCEPTED + ADOPT;
   * RETRY re-arm НЕ становится `actually_retried`;
   * ROLLBACK request НЕ становится `actually_rolled_back`;
   * STALE / REJECTED не дают authority на действие.
3. Для каждого `resolver_actions` желательно сохранить как минимум:
   * resolution_id;
   * action;
   * result;
   * result_code;
   * effect;
   * freshness/freshness_code;
   * evidence_fingerprint;
   * operation_revision;
   * physical_mutation_performed.
4. Fresh process должен видеть тот же persistent outcome,
включая STALE / REJECTED.

Добавить минимум два focused regression test.
TEST A — ABORT authoritative NEXT SAFE ACTION
Сценарий:

* operation имеет RETRY_SAFE;
* создать accepted ABORT;
* создать Recovery Report новым service/process;
* доказать:
   * Resolver ABORT остаётся persistent/fresh;
   * Recovery Report содержит ABORT в resolver_actions;
   * Recovery Report NEXT SAFE ACTION НЕ рекомендует RETRY;
   * NEXT SAFE ACTION соответствует persistent ABORT semantics.

TEST B — STALE outcome survives Recovery Report / fresh process
Сценарий:

* получить reconciliation basis;
* изменить Workspace evidence;
* apply старого resolution → STALE / EVIDENCE_FINGERPRINT_CHANGED;
* создать Recovery Report новым service/process;
* доказать:
   * resolution существует;
   * resolver_actions содержит этот STALE record;
   * result/result_code сохранены;
   * никакой authority-effect не возникает;
   * NEXT SAFE ACTION требует fresh reconciliation/resolution.

Желательно также проверить REJECTED record аналогично,
если это не требует существенного расширения scope.
НЕ делать:

* RC-3 conflict gate;
* ownership reservation;
* mutation-boundary CAS;
* physical rollback;
* authoritative write/edit/delete executor;
* новую глобальную Operation/Microtask state machine;
* UI changes;
* .gitattributes;
* line-ending normalization;
* unrelated refactor;
* commit / push;
* RC-3 после repair.

Не переписывать уже работающий Resolver без необходимости.
Сделать минимальный repair двух обнаруженных acceptance gaps.
После repair обязательно:

1. новые focused tests на оба blocker-а;
2. весь `test_web_alarm_resolver.py`;
3. `test_web_alarm_resolver_concurrency.py`;
4. полный Web Alarm regression;
5. `python -B -m compileall -q web_alarm`;
6. `git diff --check`;
7. подтвердить отсутствие physical Workspace mutation;
8. fresh-process reopen;
9. проверить, что public OperationStatus/models.py не расширены.

После repair статус остаётся только:
RESULT READY / AWAITING INDEPENDENT VERIFICATION
DONE / VERIFIED самостоятельно не объявлять.
БЛОК 1 `000_Задачи Claude.md` НЕ менять и НЕ заменять:
это всё ещё та же CLAUDE-WA-004 / RC-2.
После repair обновить:

* БЛОК 2 — если требуется отразить актуальную постановку той же TASK без потери исходного смысла;
* БЛОК 3 — фактический результат repair и повторных тестов;
* `rc2_report.md` — добавить раздел Independent Review Repair с найденными blocker-ами, исправлением и verification.

`001`, `06`, `25` не обновлять:
их синхронизирует ChatGPT после независимого PASS.
NEXT SAFE ACTION:
исправить только два blocker-а RC-2,
повторить verification,
остановиться и вернуть RESULT READY.
RC-3 НЕ начинать.
```

---
# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ
---

**TASK:** CLAUDE-WA-004 — RC-2: Persistent Resolver + evidence revision binding (+ Independent Review Repair).
**Статус:** DONE / VERIFIED — 2026-10-04. Independent verification PASS на commit 148 `0b7cb7d`; RC-3 не начат.

**Исходный RC-2 (commit 147 `fe55c99`):**
- узкий persistent Resolver (`resolution_store.py`, `resolver_service.py`): ADOPT / RETRY / ROLLBACK / ABORT — write-once tracked records, привязанные к `evidence_fingerprint` и `operation_revision`;
- stale → STALE; несоответствие действия и решения, legacy, неполный контракт, повреждённый payload → REJECTED;
- RETRY — только re-arm, ROLLBACK — только запрос, ADOPT и ABORT не меняют `OperationStatus`;
- Recovery Report не принимает заявки вызывающего без резолюции.

Проверяющий подтвердил основную реализацию (19/19, 260/260, гонка 5/5).

**Repair двух blocker-ов ревью:**
1. **NEXT SAFE ACTION отчёта** теперь выводится из persistent состояния Resolver: `report_facts` → `_authoritative_next_action`. Приоритет:
   - accepted ABORT → «recovery closed»;
   - последняя fresh accepted резолюция → её сохранённая семантика (re-armed / request only / adopted);
   - fresh REJECTED → его совет;
   - любой stale → нужна новая reconciliation;
   - резолюций нет → совет reconciliation.

   Builder ставит этот совет выше advisory-решения; источник пишется в `evidence_identity`.
2. **`resolver_actions`** теперь содержит все persistent-исходы (ACCEPTED / STALE / REJECTED) с полями `result_code`, `authority`, `freshness` и прочими. Authority по-прежнему fail-closed: `accepted_as_already_done` только из FRESH + ACCEPTED + ADOPT, `actually_*` пустые, STALE и REJECTED authority не дают.

**Затронутые файлы repair:** `web_alarm/resolver_service.py`, `web_alarm/recovery_report_builder.py`, `web_alarm/recovery_report_service.py` (+1 строка), `test_web_alarm_resolver.py` (+6 тестов, включая TEST A и TEST B). Итого +211 / −7. `models.py`, `OperationStatus`, `server.py`, `resolution_store.py`, UI, `.gitattributes` не менялись.

**Проверка repair:**
- новые тесты до правки воспроизводили оба дефекта, после — PASS;
- `test_web_alarm_resolver.py` — 24/24; concurrency — 5/5;
- полный Web Alarm — **266/266 OK** (skip 1);
- compileall и `git diff --check` OK;
- хеши проекта не меняются; живое storage не изменилось (136 файлов);
- свежий процесс видит ABORT и STALE в отчёте;
- `OperationStatus` прежний.

**Independent verification ChatGPT:** проверен последний commit 148 `0b7cb7deae8220d1f2e0f432293b0edc784b7b6d`; focused Resolver + concurrency 25/25 PASS; full Web Alarm 266/266 PASS; concurrency дополнительно 5/5 PASS; `compileall` и `git diff --check` PASS. Независимо воспроизведены ABORT → resolver-authoritative NEXT SAFE ACTION, STALE → persistent report без authority и REJECTED/CONTRACT_INSUFFICIENT → manual-review NEXT. Blocker после repair не найден.

**Deferred follow-up:** верхний `Context Pack / Remote entry NEXT_SAFE_ACTION` всё ещё может быть перезаписан advisory reconciliation, хотя `LATEST_RECOVERY_REPORT` уже содержит Resolver-authoritative NEXT. Это признано projection/resume boundary и переносится в RC-5/RC-6; RC-2 не блокирует. Остальное как в исходном RC-2: CAS — RC-3; lifecycle после ADOPT / ABORT — V15; после принятия — перезапуск процессов WEB-02.

**Подробный отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/rc2_report.md`, §9 — Independent Review Repair. Safety copies — `safety_copies/` и `safety_copies/repair/`, хеши — `baseline.md`.

## Правило круговорота

1. Следующую утверждённую TASK в БЛОК 1 переносит пользователь. Claude БЛОК 1 перед стартом перечитывает, но сам его не очищает и не переписывает без отдельной команды.
2. После фактического завершения собственной работы Claude копирует постановку из БЛОКА 1 в БЛОК 2 и заполняет БЛОК 3 кратким factual closeout.
3. До независимой проверки БЛОК 3 получает статус только `RESULT READY / AWAITING INDEPENDENT VERIFICATION`; Claude не объявляет `DONE / VERIFIED`.
4. Независимый verifier/ChatGPT проверяет код, тесты и evidence. После PASS он синхронизирует постоянную историю: `001`, `06`, нужный профильный журнал/реестр и другие реально затронутые канонические документы.
5. Только после такой постоянной фиксации разрешено при следующей завершённой TASK перезаписать БЛОКИ 2–3.
6. Пользователь заменяет БЛОК 1 новой утверждённой TASK; это и есть ручная точка ротации.
7. Долговременные технические наблюдения и метрики по Claude переносить в `27_Claude.md`, когда они действительно относятся к модели/лимитам/сети.
8. БЛОКИ 2–3 — оперативный handoff, а не замена append-only истории и независимой verification authority.
