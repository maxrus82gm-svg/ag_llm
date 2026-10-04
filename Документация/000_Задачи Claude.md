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
- БЛОК 2 — только быстрый указатель на последнюю завершённую Claude TASK, а не единственное хранилище истории.
- До замены содержимого БЛОКА 2 завершённая TASK обязана получить постоянную append-only запись в `06_Журнал выполнения и отчёты.md`, краткую запись в `001_История выполненных задач Claude.md`; для профильной подсистемы дополнительно обновляется её профильный журнал (например, Web Alarm → `25`).
- Полная постановка TASK может дополнительно фиксироваться в обычном Chat как человеческий резерв/след обсуждения, но каноническим источником остаются проектные документы.
- После завершения собственной TASK Claude сам готовит её documentation closeout: обновляет этот `000`, персональную историю `001`, постоянный журнал `06`, затронутые профильные документы и реестры только по фактически подтверждённому результату. До независимой проверки не объявляет неподтверждённое `DONE`.

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
- обновить `000_Задачи Claude.md`, `001`, `06`, `25` только по фактическому результату;
- статус до независимой проверки: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**;
- не объявлять DONE самостоятельно;
- не делать commit/push;
- RC-3 не начинать.

**NEXT SAFE ACTION сейчас:** эта постановка только зафиксирована. После явной команды пользователя Claude перечитывает БЛОК 1, выполняет drift check и приступает только к `CLAUDE-WA-004 / RC-2`.
# БЛОК 2 — ПОСЛЕДНЯЯ ЗАВЕРШЁННАЯ ЗАДАЧА
---

**TASK:** CLAUDE-WA-003 — RC-1: Durable Operation Contract + backward compatibility.
**Статус:** DONE / VERIFIED — 2026-10-04.
**Модель:** Claude Opus 5.5.

**Результат:** Operation Contract v2 принят после независимой проверки. ChatGPT повторил full regression 241/241 PASS, focused RC-1 44/44 PASS, пять последовательных multiprocess concurrency прогонов и fresh-process чтение живых `WA37-CTRL-001/002` без изменения storage tree (136 файлов).

**Принято:** contract v2 restart-safe; legacy v1 читается без rewrite и re-arm; physical byte pre/post + server receipt; durable payload/ref; canonical target; revision; межпроцессная сериализация Operation Store. Conflict gate/CAS остаются RC-3, physical resolver actions — последующим boundary.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-003_RC1/rc1_report.md`. Постоянная история обновлена в `001`, `06`, `25`.

## Правило круговорота

1. Новую активную задачу записывать в БЛОК 1 до исполнения; при необходимости её постановка дополнительно фиксируется в обычном Chat.
2. После фактического завершения Claude готовит closeout, но статус `DONE` считается каноническим только после требуемой независимой проверки.
3. До ротации БЛОКА 2 сохранить постоянную append-only запись TASK в `06_Журнал выполнения и отчёты.md` и нужном профильном журнале/реестре.
4. Только после сохранения permanent history перенести краткий итог последней завершённой TASK в БЛОК 2 и очистить БЛОК 1 под следующую задачу.
5. Долговременные технические наблюдения и метрики переносить в `27_Claude.md`.
6. Значимые изменения самого проекта синхронизировать с канонической проектной документацией строго по фактически подтверждённому результату.
7. БЛОК 2 никогда не используется как единственное доказательство существования или содержания старой TASK.
