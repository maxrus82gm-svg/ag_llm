---
graph_cluster: round-table
---

# Круглый стол — независимый анализ GPT

**Назначение:** независимый анализ участника B по текущему вопросу Круглого стола (раунд 1). Протокол, карточка вопроса и source snapshot — [[28_Круглый стол - протокол и текущий вопрос]].

Документ **не является источником архитектурной истины** и сам по себе ничего не разрешает менять.

## Постоянная инструкция

**Участник:** B — GPT. Режим и способ подключения указываются в карточке вопроса в `28` и в начале оперативной части.

**Входы:**
- карточка вопроса в `28`: вопрос, scope, source snapshot, текст постановки, исходные материалы;
- проект в состоянии snapshot;
- фактическое подтверждённое состояние проекта — `01` и профильные документы; при расхождении с кодом источником факта является код.

**Выход:** независимый анализ `RT-xxx` в оперативной части этого документа.

**Разрешено:**
- изучать исходные материалы, код, тесты и runtime-состояние проекта;
- самостоятельно исследовать проект сверх исходного набора — с обязательной фиксацией дополнительно изученного;
- запускать проверки, не изменяющие проект.

**Запрещено:**
- до печати раунда 1 читать `29_Круглый стол - независимый анализ Claude` и другие вклады текущего вопроса (`29.1`, `30.1`, `31`, `32`);
- менять канонические документы, код или чужие документы контура;
- подстраивать выводы под другую сторону или под заранее ожидаемое решение.

**Правила независимости и evidence:** разделы 4–6 протокола `28`. Вклад явно отделяет факты (с evidence), гипотезы и рекомендации и содержит аттестацию независимости.

**Следующий этап:** после печати раунда 1 — [[30.1_Круглый стол - перекрёстная оценка GPT]].

**Шаблон записи:**

```text
### RT-xxx — <название>
Участник / модель / режим / подключение / provenance:
Snapshot (commit, dirty state):
Аттестация независимости: что читал / чего не читал
Краткий итог (не больше страницы)
Изученные материалы (+ дополнительно изученное)
Факты (с evidence)
Гипотезы
Собственные выводы и рекомендации
Найденные риски и противоречия
Альтернативы
Рекомендуемое направление
Что осталось проверить / уровень уверенности
```

**Правила очистки:** после закрытия вопроса (Decision Record в `32`) очищается только область между `RT:BEGIN` и `RT:END`; постоянная инструкция не меняется.

---

## Оперативная часть — текущий вопрос

<!-- RT:BEGIN -->

> **Перенос (2026-10-03):** запись перенесена без изменений из бывшего `35_Независимая аналитика GPT WEB-02.md`; изменён только ID в заголовке: `WEBQ-001` → `RT-001` (legacy_alias: `WEBQ-001`). Номера документов, упомянутые в тексте, относятся к прежнему контуру: `33` → `28`, `34` → `29`, `35` → `30`, `36` → `31`, `37` → `32`.
>
> **Участник B:** GPT — ChatGPT; модель и режим во вкладе не указаны (см. карточку вопроса в `28`).

# RT-001 — Независимый аудит текущей архитектуры WEB-02 и следующего этапа

## 0. Статус и границы этого анализа

На момент анализа в `33_Вопросы и проблемы WEB-02, требующие решения.md` формальная карточка активного вопроса ещё не заполнена. Поэтому здесь фиксируется самостоятельный ответ на фактически поставленный пользователем вопрос:

> Куда реально пришёл WEB-02, какие архитектурные проблемы в нём остаются, что из текущего плана действительно нужно делать дальше и каким должен стать рабочий WEB-02, чтобы новый Chat/агент мог безопасно продолжить работу после разрыва связи или потери контекста.

Для независимости **`34_Независимая аналитика Claude WEB-02.md` не читался и не использовался**.

Изучены:
- `23_Архитектура Web Alarm Workspace.md`;
- `24_План реализации Web Alarm Workspace.md`;
- `25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md`;
- `26_Журнал наблюдений Remote - обрывы, transport и recovery evidence.md`;
- текущий код `web_alarm/`, в том числе operation store, state machine, manifest/snapshot, reconciliation, context pack, remote entry, transport events, recovery reports, HTTP server и UI;
- текущий regression suite WEB-02.

Независимая проверка regression:

```text
python -B -m unittest discover -s . -p "test_web_alarm_*.py"

Ran 197 tests in 20.310s
OK
```

Файлы runtime и каноническая документация в ходе анализа не менялись. Этот документ сам по себе не является разрешением на изменение `23–26` или кода.

---

## 1. Краткий итог

WEB-02 уже не является просто идеей или набором backup-скриптов.

В нём реально построены четыре сильных слоя:

1. persistent TASK/microtask state;
2. restore-point / snapshot слой;
3. operation identity + read-only reconciliation;
4. restart-safe recovery evidence/reporting.

Это уже хороший **local control plane + recovery journal**.

Но система пока не замыкает полный цикл:

```text
INTENT
→ безопасно исполнить mutation
→ сохранить exact expected/result receipt
→ потерять ответ
→ новый агент сам восстановит факт
→ применит recovery decision
→ продолжит ту же operation
```

Сейчас WEB-02 особенно силён в ответе на вопрос:

> «Что, вероятнее всего, произошло и что безопасно делать дальше?»

Но значительно слабее в вопросе:

> «Как именно выполнить или завершить это действие так, чтобы повтор был технически безвредным и не зависел от памяти Chat?»

Главный разрыв находится **между journal/reconciliation и execution**.

---

## 2. Какую роль WEB-02 уже фактически выполняет

По текущему коду WEB-02 состоит из нескольких независимых authority-слоёв.

### 2.1 Persistent task state

Хранятся:
- Workspace registration;
- TASK;
- plan;
- microtasks;
- statuses;
- event log;
- checkpoint;
- reports.

Это переживает новый Python process / Server process.

### 2.2 Restore-point layer

Для microtask есть:
- manifest;
- `exists_before`;
- size/hash;
- immutable snapshot bytes;
- verified restore point.

Это правильная основа rollback/reconciliation.

### 2.3 Operation identity

`OperationStore` хранит:
- `operation_id`;
- task/microtask;
- action;
- target;
- request fingerprint;
- expected precondition hash;
- lifecycle status.

Повтор одного и того же `operation_id` не создаёт новый operation record.

### 2.4 Reconciliation

Collector сравнивает:
- snapshot/pre-state;
- current Workspace;
- operation lifecycle;
- optional exact expected post-state.

Decision engine возвращает ограниченный набор решений:
- `ADOPT_CURRENT_STATE`;
- `RETRY_SAFE`;
- `ROLLBACK_CURRENT_MICROTASK`;
- `MANUAL_REVIEW_REQUIRED`.

Критически важно: decision остаётся read-only и не выдаёт себе mutation authority.

### 2.5 Transport evidence

Отдельно хранятся:
- REMOTE_ONLINE/OFFLINE/RECOVERED;
- delivery failures;
- process restart evidence.

Это хороший принцип: transport не определяет fate операции.

### 2.6 Recovery Report

Есть persistent machine-readable отчёт:
- side-effect scope;
- evidence identity;
- decision;
- что принято already done;
- что retried/rolled back;
- next safe action.

Именно этот слой уже делает recovery объяснимым, а не «магическим».

---

## 3. Что в архитектуре сделано особенно правильно

### 3.1 Disk state важнее последнего сообщения Chat

Это фундаментально правильное решение.

Живые инциденты уже доказали:
- ошибка caller может соответствовать 0 mutations;
- может соответствовать partial execution;
- может соответствовать full execution;
- UI timeout вообще не доказывает остановку workflow.

Поэтому текущий принцип:

```text
Chat/UI result != authoritative operation state
```

нужно сохранять во всех следующих версиях.

### 3.2 Restore point создаётся до mutation

Это правильная граница безопасности.

Система не должна сначала менять файл, а потом пытаться придумать, как его восстановить.

### 3.3 Reconciliation отделён от исполнения

Это тоже верно.

В текущем состоянии лучше получить `MANUAL_REVIEW_REQUIRED`, чем автоматически повторить или откатить неизвестную mutation.

### 3.4 Evidence и decision связаны fingerprint

Decision нельзя безопасно переносить на другое фактическое состояние.

Это хороший фундамент для будущего Resolver.

### 3.5 Transport evidence не имеет authority

Watchdog/Remote status должен быть датчиком, а не управляющим органом.

Это особенно важно потому, что:
- transport может умереть после успешной mutation;
- executor process может остаться жив;
- UI может потерять ответ отдельно от execution.

### 3.6 Production state вынесен из управляемого Workspace

Физическое разделение runtime state и проекта — правильное направление.

Недавняя проблема с Obsidian дополнительно показывает, почему snapshots и runtime artifacts не должны засорять пользовательский vault.

---

## 4. Главные архитектурные разрывы

Ниже проблемы перечислены не по «красоте кода», а по тому, насколько они мешают исходной цели WEB-02.

### 4.1 Operation не хранит полный контракт результата

Это самый важный разрыв.

Текущий `OperationRecord` хранит:

```text
operation_id
task_id
microtask_id
action
target
status
request_fingerprint
expected_precondition_sha256
result_summary
```

Но в нём нет:
- exact expected post-state;
- expected post hash;
- expected existence state;
- самого нормализованного mutation payload;
- persistent receipt фактически применённого результата.

При этом reconciliation получает `expected_post_state` **от вызывающей стороны**.

Следствие:

новый Chat может знать `operation_id`, но не обязан знать, каким должен был стать файл.

Это противоречит главной цели WEB-02: потеря контекста Chat не должна уничтожать способность восстановить operation.

### 4.2 Request fingerprint есть, а сам request не является durable operation contract

Fingerprint защищает от подмены запроса при повторе того же ID.

Но fingerprint нельзя исполнить.

Если Chat потерял контекст, по одному SHA256 нельзя восстановить:
- что именно записывать;
- какой patch применять;
- каким должен быть post-state.

То есть operation identity сейчас хорошо отвечает:

> «Это тот же запрос или другой?»

но плохо отвечает:

> «Что именно этот запрос обязан был сделать?»

Для настоящего persistent executor нужно хранить либо:
- нормализованный mutation command;
- либо content-addressed payload;
- либо ссылку на immutable operation payload.

---

## 5. Recovery decision пока нельзя штатно применить

Сейчас pipeline фактически такой:

```text
persistent evidence
→ reconciliation
→ decision
→ NEXT SAFE ACTION
→ человек/Chat выполняет действие снаружи
```

Нет отдельного authoritative Resolver, который умеет:

```text
ADOPT_CURRENT_STATE
→ закрыть ту же operation на основании fingerprint evidence

RETRY_SAFE
→ безопасно продолжить ту же operation_id

ROLLBACK
→ провести rollback как tracked recovery operation
```

Из-за этого Recovery Report описывает решение, но само решение не становится частью operation lifecycle.

Это делает WEB-02 хорошим диагностом, но ещё не полноценным recovery coordinator.

---

## 6. Recovery-статусы имеют тупиковые ветки

В microtask state machine:

```text
UNKNOWN_AFTER_DISCONNECT
→ RECOVERY_REQUIRED
```

но из `RECOVERY_REQUIRED` нормального recovery transition дальше нет.

В OperationStore:

```text
UNKNOWN_AFTER_DISCONNECT
```

terminal.

Это безопасно как временный fail-closed дизайн, но в production recovery это тупик.

Система должна уметь не только сказать:

> «Нужно reconciliation»

но и после доказанного reconciliation завершить recovery без создания параллельной неучтённой операции.

---

## 7. Operation admission пока не связан жёстко с microtask gate

`OperationStore.begin()` проверяет:
- TASK существует и active;
- microtask существует;
- operation_id/fingerprint.

Но сам begin не требует:
- microtask = READY/ACTIVE;
- verified restore point;
- target входит в manifest;
- target не имеет другой открытой operation.

То есть operation journal можно открыть в состоянии, где mutation по архитектурным правилам ещё не разрешена.

Пока mutation выполняется снаружи это выглядит терпимо, но при появлении gateway это станет опасной двусмысленностью.

Правильный будущий инвариант:

```text
NO VALID GATE
→ NO EXECUTABLE OPERATION
```

---

## 8. Нет защиты от двух разных operation_id на один и тот же target

Replay protection сейчас ориентирован на identity конкретного `operation_id`.

Но новый Chat может создать новый `operation_id` с тем же:
- target;
- action;
- request fingerprint.

Система не запрещает одновременно иметь две незакрытые операции на один target.

Для recovery это опаснее обычного replay:
- старый executor может ещё доехать;
- новый Chat создаёт новый operation_id;
- обе операции выглядят формально независимыми.

Нужен target-level conflict policy.

Минимум:

```text
one open mutating operation per target per TASK
```

или более строгий lease на microtask mutation session.

---

## 9. RETRY_SAFE пока является логическим выводом, а не технической гарантией exactly-once

`RETRY_SAFE` сейчас означает:

> по текущему снимку Workspace pre-state сохранился и expected post-state не достигнут.

Но между reconciliation и реальным повтором может измениться мир:
- старый Remote-call продолжит выполнение;
- другой процесс изменит файл;
- пользователь отредактирует target;
- второй агент начнёт свою mutation.

Следовательно решение должно быть связано с **CAS/precondition непосредственно в момент write**.

Иначе существует окно:

```text
reconcile PRE_STATE
→ decision RETRY_SAFE
→ внешний actor меняет target
→ retry всё равно пишет
```

Будущий executor обязан перечитать precondition непосредственно перед atomic mutation.

---

## 10. Persistent stores атомарны по отдельному файлу, но не транзакционны как workflow

В нескольких местах один логический transition состоит из последовательности:

```text
изменить status record
→ append event
→ переписать checkpoint
```

Каждый отдельный JSON пишется аккуратно через temp + replace, но вся тройка не является одной транзакцией.

Возможен crash между шагами:

```text
microtask status уже ACTIVE
event ещё не записан
checkpoint ещё старый
```

или:

```text
operation DONE
event append failed
checkpoint показывает STARTED
```

Сейчас recovery часто может разобраться по фактическим файлам, но чем больше WEB-02 становится authority, тем опаснее такие расхождения.

Нужно выбрать один источник истины:
- transactional SQLite/WAL;
- либо append-only authoritative event log + projections;
- либо явный transaction journal/commit marker.

Три равноправных mutable представления состояния увеличивают риск drift.

---

## 11. Межпроцессной блокировки нет

В `OperationStore` есть `threading.RLock`.

Он защищает только один Python object внутри одного process.

Но WEB-02 уже используется через:
- ThreadingHTTPServer;
- CLI;
- отдельные Python subprocess;
- Desktop Commander;
- fresh-process recovery tests.

Файлового lock/lease между процессами нет.

Следовательно два процесса могут одновременно:
- открыть operation;
- писать event log;
- менять checkpoint;
- менять microtask state.

Это уже не будущая теоретическая проблема: сама архитектура специально рассчитана на новый Chat/new process.

Значит межпроцессная serialization нужна **до** превращения Web Alarm в основной mutation gateway.

## 12. Restore path обходит основную server state machine

`ManifestSnapshotStore.restore_microtask()` после восстановления напрямую делает:

```text
set_microtask_status(..., BACKUP_VERIFIED)
```

То есть rollback:
- не проходит через `ServerStateMachine.transition()`;
- не получает обычный transition policy;
- не обязан записать тот же event/checkpoint lifecycle;
- может переводить microtask назад в состояние, которое обычная state machine публично не разрешает.

Это архитектурный разрыв: самый опасный recovery-action проходит по отдельной дороге.

Rollback должен стать first-class operation.

Например:

```text
RECOVERY_REQUIRED
→ ROLLBACK_INTENT
→ ROLLBACK_STARTED
→ ROLLBACK_APPLIED
→ RESTORE_VERIFIED
→ ACTIVE | READY | FAILED
```

С persistent receipt и evidence.

---

## 13. Restore может уничтожить полезный drift

Текущий restore:
- перезаписывает existing target snapshot bytes;
- удаляет target, если `exists_before=false`.

Но перед этим не создаётся обязательный snapshot **текущего** состояния.

Если после исходного snapshot:
- пользователь внёс полезную ручную правку;
- другой процесс что-то изменил;
- partial mutation создала важные данные,

rollback может их уничтожить.

Для production recovery нужен принцип:

```text
rollback never destroys the current state without preserving it
```

То есть перед destructive rollback:
- capture current recovery snapshot;
- привязать его к recovery operation;
- только затем восстанавливать original pre-state.

---

## 14. Verification function местами имеет побочный эффект

`verify_restore_point(active_only=True)` при проблеме пытается перевести restore point/microtask в blocked state.

То есть операция с названием "verify" не всегда read-only.

Это затрудняет reasoning:
- caller думает, что только проверяет;
- фактически state может измениться.

Нужен строгий контракт:

```text
inspect/verify = pure read
mark_blocked = explicit command
```

Особенно важно для нового агента, который должен безопасно собирать evidence после reconnect.

---

## 15. TASK можно завершить без server-level closeout gate

`TaskStore.complete_task()`:
- меняет TASK на COMPLETED;
- переносит directory в completed.

Но сам метод не проверяет:
- все ли microtasks VERIFIED;
- есть ли open operations;
- закончено ли recovery;
- synced ли checkpoint;
- нет ли unresolved transport/reconciliation incident.

То есть низкоуровневый storage API может закрыть TASK раньше архитектурного closeout.

Нужен единый `complete_task` gate уровня Web Alarm core, который сначала механически доказывает завершённость.

---

## 16. Checkpoint сейчас фактически является mutable projection, но используется почти как source of truth

Context Pack предпочитает checkpoint:
- current microtask;
- status;
- snapshot status;
- last operation;
- NEXT SAFE ACTION.

При этом реальный status отдельно лежит в microtask record, operation отдельно, manifest отдельно.

Если crash произошёл после изменения одного store и до checkpoint update, новый Chat может получить stale projection.

Нужно формально определить:

```text
checkpoint = cache/projection
```

и уметь:
- пересобирать его из authoritative records;
- проверять revision/fingerprint;
- автоматически помечать stale.

Или наоборот — сделать transactional state store, где checkpoint является частью одной commit.

---

## 17. Event log пока не является полноценным write-ahead log

`events.jsonl` полезен как история, но transition сначала может изменить основной record, а затем append event.

Значит event log не гарантирует:
- что каждый committed state change имеет event;
- что event является причиной state change;
- что state можно восстановить replay событий.

Если журнал должен стать настоящим recovery foundation, порядок должен быть определён явно.

Варианты:

### Вариант A — SQLite transaction

Все authoritative records обновляются одной транзакцией.

### Вариант B — WAL/event sourcing

```text
append intent/event
fsync
→ apply projection
→ commit marker/receipt
```

Сейчас система находится между этими моделями.

---

## 18. Transport Store хороший по authority, но не является реальным sensor pipeline

Server умеет принимать:

```text
POST /transport/events
```

Но сам по себе не наблюдает Desktop Commander.

То есть событие появляется только если кто-то его записал.

Это нормально для WA-3.5 как data model, но не для окончательной эксплуатации.

Нужно различать:

```text
TransportEventStore = evidence storage
Sensor/Watchdog adapter = producer evidence
```

Producer должен автоматически:
- видеть online/offline/recovered;
- иметь стабильную process identity;
- писать timestamps;
- где возможно связывать event с operation.

При этом authority у него всё равно не появляется.

---

## 19. Canonical Remote Entry пока TASK-level, но проекту нужен project-level Resume

`RemoteEntry` хорошо работает, когда есть ровно одна active TASK.

Но если:
- active TASK нет;
- последняя TASK уже completed;
- проект ждёт постановки следующего этапа;
- WA-3 закрыта, но WA-4 ещё не активирована,

`webalarm enter` не знает «где находится проект» в широком смысле.

Он отвечает только состоянием active TASK.

Для исходной цели «новый Chat быстро продолжает работу» нужен верхний уровень:

```text
PROJECT
BRANCH
CURRENT PROGRAM STAGE
LAST VERIFIED RESULT
ACTIVE TASK (optional)
OPEN OPERATIONS
BLOCKERS
NEXT SAFE ACTION
```

То есть `resume` должен существовать даже при `ACTIVE TASK = none`.

---

## 20. Реальная Remote-работа пока проходит мимо WEB-02

Это главный эксплуатационный разрыв.

Система умеет:
- хранить operations;
- reconcile;
- строить recovery report.

Но значительная часть реальных действий всё ещё выполняется прямыми Desktop Commander calls и фиксируется отдельным ручным session log.

Следствие:
- Web Alarm знает не обо всех mutations;
- report иногда невозможно построить честно;
- операция может иметь receipt только в ручном журнале, но не в OperationStore.

Пока это так, WEB-02 остаётся параллельным контролем, а не primary control plane.

Именно WA-4 должен устранить этот разрыв.

---

## 21. UI пока показывает storage, а не рабочую ситуацию

Текущий UI полезен для inspection:
- TASK list;
- RAW TASK;
- plan;
- checkpoint;
- manifest;
- reports;
- recovery state.

Но оператору после reconnect нужен ответ не «покажи мне JSON», а:

```text
Где мы?
Что точно уже сделано?
Есть ли незакрытая operation?
Что требует reconciliation?
Можно ли сейчас мутировать Workspace?
Какой один следующий безопасный шаг?
```

То есть основной экран должен быть **Situation / Resume**, а сырой JSON — secondary details.

Минимальная верхняя панель:

```text
PROJECT: ag_llm
STAGE: WEB-02 / WA-x
TASK: ...
MICROTASK: ...
OPERATION: ...
REMOTE: ...
RECOVERY: ...
MUTATION: ALLOWED/BLOCKED
NEXT SAFE ACTION: ...
```

---

## 22. Документация уже показывает стоимость ручной синхронизации

В `24` сверху всё ещё есть старый статус:

```text
IMPLEMENTATION PLAN / ACTIVE — WA-1 IN PROGRESS
```

и позже старый заголовок:

```text
WA-3 ... WA-3.5 PREPARED / CODE NOT STARTED
```

при том, что в конце того же документа уже записано:
- WA-1 DONE;
- WA-2 DONE;
- WA-3.1–3.7 DONE;
- full 197/197 PASS.

Это не проблема «невнимательной документации» конкретного человека.

Это архитектурный сигнал:

> current status размножен по слишком большому числу мест.

Чем больше WEB-02 растёт, тем меньше статус должен редактироваться вручную.

Рекомендация:
- machine state → один generated/current STATUS;
- architecture docs → invariants;
- plan → future criteria;
- history → append-only evidence.

---

## 23. Нужно ли сейчас делать ещё один live controlled disconnect

Текущий план оставляет WA-3 открытой из-за строгого критерия:

```text
local post-state достигнут
→ Remote disconnect
→ Chat ещё не получил authoritative result
```

Сам по себе такой тест полезен как демонстрация.

Но **как следующий инженерный шаг** я бы его не ставил первым.

Причина:

даже если этот live test PASS, он не исправляет:
- отсутствие expected post-state внутри OperationRecord;
- отсутствие durable mutation payload;
- отсутствие Resolver;
- отсутствие CAS в execution;
- отсутствие cross-process lock;
- возможность нового operation_id на тот же target.

То есть мы можем идеально доказать ещё один timing incident, но production recovery всё равно останется зависимым от внешнего исполнителя.

### Моя рекомендация

Не считать этот тест бесполезным.

Но перенести его роль:

```text
из «последнего доказательства старой read-only recovery архитектуры»
в
«fault-injection acceptance нового persistent executor/resolver»
```

Тогда тест проверит действительно сильное свойство:

1. operation contract уже durable;
2. mutation выполнена сервером;
3. receipt/post-state сохранён;
4. ответ намеренно теряется;
5. новый process вызывает resume;
6. operation определяется как уже APPLIED;
7. повтор того же operation_id возвращает тот же receipt;
8. mutation физически выполнялась ровно один раз.

Такой тест гораздо ценнее.

---

## 24. Что делать до WA-4

Между текущим WA-3 и строгим mutation gateway нужен небольшой **Recovery Closure**.

Название не принципиально. Это может быть:
- WA-3.8;
- WA-3R;
- WA-4.0.

Смысл важнее номера.

### Recovery Closure должен сделать пять вещей

#### RC-1 — Durable Operation Contract

Operation хранит:
- expected pre-state;
- expected post-state;
- normalized mutation request/payload identity;
- target identity;
- idempotency identity.

Chat после restart ничего не должен «вспоминать» для reconciliation.

#### RC-2 — Resolver

Добавить explicit actions:
- ADOPT;
- RETRY;
- ROLLBACK;
- ABORT/MANUAL.

Каждый action меняет operation/microtask state только через core state machine.

#### RC-3 — Open-operation conflict gate

Перед новым begin:
- проверить открытые операции того же target;
- не позволить новому Chat обойти старый uncertain operation новым ID.

#### RC-4 — Cross-process serialization

Минимум:
- global/task lock;
- transaction revision;
- owner/lease там, где идёт mutation.

#### RC-5 — Rebuildable checkpoint

Checkpoint либо транзакционен, либо явно считается projection и восстанавливается из authoritative state.

---

## 25. Каким должен быть mutation gateway

Будущий gateway не должен быть просто HTTP-обёрткой над `write_file`.

Его контракт должен быть примерно таким:

```text
apply(
    operation_id,
    task_id,
    microtask_id,
    target,
    expected_pre_sha256,
    expected_post_sha256,
    mutation_payload
)
```

Сервер внутри одного контролируемого lifecycle делает:

```text
1. validate TASK/microtask/ownership
2. validate manifest + restore point
3. reject competing open operation
4. read actual pre-state
5. CAS actual == expected pre
6. persist INTENT + immutable payload contract
7. mark STARTED
8. apply atomic file mutation
9. reread target
10. verify exact expected post-state
11. persist APPLIED receipt
12. append event / update projection transactionally
13. return receipt
```

Если ответ потерян:

```text
same operation_id
→ return same receipt
```

а не новая mutation.

Это и есть настоящая replay safety.

---

## 26. Idempotency должна быть свойством executor, а не дисциплиной Chat

Сейчас правило звучит примерно так:

> «Не повторяй mutation вслепую».

Это хорошее правило для текущего этапа.

Но production цель должна быть сильнее:

> «Даже если caller повторил тот же operation request после потери ответа, executor технически не выполнит side effect второй раз».

То есть безопасность должна переехать:
- из prompt/protocol;
- в server-owned idempotency.

Тогда новый Chat может быть менее идеальным, а система останется безопасной.

---

## 27. Lease нужен не только TASK, но и mutation authority

В WA-4 запланирован ownership.

Я бы разделил:

### Read lease не нужен

Несколько клиентов могут читать state.

### Mutation lease нужен

Одновременно mutation authority имеет один owner/session.

Lease содержит:
- owner id;
- task id;
- acquired_at;
- heartbeat;
- expiry;
- recovery transfer reason.

Но lease сам по себе не заменяет CAS.

Даже владелец lease обязан проверять actual pre-state перед write.

---

## 28. Storage: JSON можно оставить, но только при явной transaction model

Текущие JSON-файлы удобны:
- легко инспектировать через Remote;
- легко восстанавливать вручную;
- нет внешних dependencies.

Но рост числа coordinated records делает SQLite всё более привлекательным.

### SQLite даст

- transaction boundaries;
- WAL;
- cross-process locking;
- unique constraints;
- querying open operations;
- revision consistency.

Snapshots всё равно можно оставить файлами.

Практичная схема:

```text
SQLite
  TASK / microtask / operation / event / checkpoint projection / lease

Filesystem
  immutable snapshot bytes
  large operation payloads if needed
  job logs
```

Но переход на SQLite не является обязательным прямо сейчас.

Если остаётся JSON:
- нужен global file lock;
- event/transaction commit marker;
- revision;
- recovery from partial persistence.

---

## 29. Long-running commands должны быть persistent jobs

Тесты, compile, git diff и другие долгие действия часто переживают Chat timeout.

Сейчас это выглядит как исключение/инцидент.

Лучше сделать first-class Job:

```text
job_id
operation/task binding
command identity
pid/process identity
started_at
status
stdout/stderr file
exit_code
result fingerprint
```

Тогда Chat после reconnect спрашивает:

```text
job status <id>
```

а не угадывает, завершился ли subprocess.

---

## 30. Resume Pack должен быть маленьким

Главная практическая метрика WEB-02:

> сколько действий и сколько текста нужно новому агенту до первого безопасного шага.

Цель:

```text
webalarm resume
```

Ответ примерно:

```text
PROJECT        ag_llm
BRANCH         WEB-02
PROGRAM STAGE  Recovery Closure / WA-4
TASK           WA-...
MICROTASK      M00x ACTIVE
OPEN OP        op_x STARTED
TARGET         ...
EXPECTED POST  sha...
REMOTE         ONLINE/OFFLINE/UNKNOWN
NEEDS ACTION   reconcile op_x
MUTATION       BLOCKED
LAST VERIFIED  ...
NEXT SAFE ACTION ...
```

Плюс:
- 5–10 protocol rules;
- ссылки только на документы текущего профиля.

Не нужно заставлять новый Chat читать всю историю проекта.

---

## 31. Предлагаемая конечная архитектура

```text
ChatGPT Web / Local Agent
          │
          │ resume / apply / job / reconcile / resolve
          ▼
┌──────────────────────────────────────────────┐
│              WEB-02 CONTROL PLANE            │
│                                              │
│  Project Resume / Situation                  │
│  Task + Microtask State Machine              │
│  Operation Contract + Idempotency            │
│  Resolver                                    │
│  Lease / Cross-process Lock                  │
│  Reconciliation                              │
│  Job Manager                                 │
│  Transport Sensor Evidence                   │
│  Recovery Reports                            │
└──────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────┐
│          TRANSACTIONAL EXECUTION CORE         │
│                                              │
│  snapshot-on-first-touch                     │
│  CAS / precondition                          │
│  atomic write                                │
│  exact post verification                     │
│  persistent receipt                          │
└──────────────────────────────────────────────┘
          │
          ▼
      REAL WORKSPACE

Desktop Commander:
- bootstrap;
- arbitrary shell;
- GUI;
- установка ПО;
- действия вне registered workflow.

Но значимые tracked mutations внутри workflow идут через WEB-02.
```

---

## 32. Что я бы упростил

### 32.1 Microtask lifecycle

Текущая цепочка:

```text
PLANNED
PREPARING
BACKUP_VERIFIED
READY
ACTIVE
DONE
VERIFIED
```

частично отражает внутренние implementation steps.

Для оператора важнее:

```text
PLANNED
READY
ACTIVE
VERIFIED
BLOCKED
NEEDS_RECOVERY
```

`PREPARING` и `DONE` могут остаться internal receipts, если действительно нужны.

Чем меньше states, которые агент должен вручную переключать, тем ниже риск bookkeeping failure.

### 32.2 Recovery Report

Report полезен для history и handoff.

Но текущий state не должен зависеть от того, что человек вручную заполнил:
- accepted_as_already_done;
- actually_retried;
- actually_rolled_back.

Эти поля в будущем лучше генерировать из resolver operation events.

### 32.3 Документационный closeout

Один verified state change не должен требовать ручной правки множества документов.

Нужен generated STATUS/current projection.

---

## 33. Порядок следующих работ

### Этап 1 — Decision / cleanup, без новой live mutation

Зафиксировать архитектурное решение:
- WA-3 read-only recovery признана достаточно доказанной;
- strict combined disconnect переносится в acceptance нового executor;
- Recovery Closure вставляется перед full WA-4.

Одновременно убрать противоречащие current status формулировки в `24` после отдельного утверждённого решения.

### Этап 2 — Durable Operation Contract

Добавить:
- expected post;
- durable request/payload identity;
- one-open-op-per-target;
- tests нового Chat без внешней памяти expected post.

### Этап 3 — Resolver

ADOPT/RETRY/ROLLBACK должны стать tracked state transitions.

### Этап 4 — Transaction/locking

Cross-process lock/revision и coherent commit state.

### Этап 5 — Mutation Executor

CAS + atomic write + exact post verification + persistent receipt.

### Этап 6 — Fault-injection disconnect acceptance

Именно здесь провести сценарий:

```text
mutation applied
receipt persisted
response intentionally lost
new Chat/process
resume
same operation_id
no second side effect
```

### Этап 7 — Project-level Resume + Situation UI

Один вход до безопасного next step.

### Этап 8 — Jobs / sensor / generated status

Убрать ручное восстановление long-running commands и status bookkeeping.

### Этап 9 — Rollout

```text
OBSERVE
→ WARN
→ GATEWAY REQUIRED
→ STRICT
```

---

## 34. Критерии настоящей готовности WEB-02

Я бы считал WEB-02 готовым к регулярной работе, когда доказаны не только сценарии disconnect, а следующие свойства:

1. Новый Chat не передаёт expected post-state из памяти.
2. Один и тот же request нельзя случайно превратить в две mutations.
3. Повтор того же operation_id после потерянного ответа безвреден.
4. Два process не могут одновременно мутировать одну TASK/target.
5. Любая significant mutation имеет persistent operation receipt.
6. Reconciliation decision можно штатно применить.
7. Rollback сам является tracked operation и не уничтожает текущий drift без backup.
8. Checkpoint восстанавливается из authoritative state.
9. Active TASK может отсутствовать, но project resume всё равно знает текущий stage/NEXT.
10. Новый агент получает безопасный next step одной командой.
11. Transport evidence собирается автоматически, но не получает authority.
12. Документационный CURRENT status не синхронизируется вручную в множестве файлов.
13. Controlled lost-response fault injection доказывает exactly-once side effect для gateway mutation.

---

## 35. Метрики, которыми стоит мерить прогресс

Количество тестов важно, но само по себе не показывает практическую зрелость.

Я бы добавил четыре метрики.

### A. Remote calls per logical mutation

Сколько Remote interactions нужно для одного безопасного изменения.

Цель — снижать.

### B. Actions to safe resume

Сколько действий делает новый Chat от входа до понимания `NEXT SAFE ACTION`.

Цель — 1–2.

### C. Untracked mutation ratio

Какая доля significant mutations прошла мимо OperationStore/gateway.

Production цель — 0.

### D. Manual status sync count

Сколько документов приходится вручную менять после закрытия одного этапа.

Production цель — 0–1 generated projection + append-only history.

---

## 36. Риски, которые я не считаю сейчас главными

### Security внешнего API

До публикации наружу обязательны:
- authentication;
- Host/origin policy;
- path hardening;
- explicit remote exposure.

Но пока Server loopback-only, это не главный blocker recovery architecture.

### Красота UI

UI можно улучшать позже.

Сначала authoritative executor/resolver, потом визуальная полировка.

### MCP adapter

MCP полезен как transport/adapter.

Но если Core не идемпотентен и не умеет resolve operation, MCP не решит проблему.

Сначала Core.

---

## 37. Независимый итоговый вывод GPT

### Куда пришёл WEB-02

Система уже имеет сильный persistent recovery foundation:
- storage;
- restore points;
- operation identity;
- deterministic reconciliation;
- restart-safe reports;
- transport evidence;
- доказанные disconnect/restart сценарии.

Это реальный результат.

### Главная проблема

WEB-02 всё ещё находится **рядом с execution**, а не владеет execution.

Именно поэтому:
- expected result частично живёт вне operation;
- retry остаётся рекомендацией;
- recovery decision не закрывает lifecycle;
- реальные mutations могут обходить journal;
- exactly-once пока зависит от дисциплины агента.

### Главный следующий шаг

Не ещё один ручной disconnect ради самого disconnect.

Главный следующий шаг — **замкнуть operation contract + resolver + CAS/idempotent executor**.

После этого strict lost-response test действительно докажет ключевое production свойство.

### Что я предлагаю изменить в текущем плане

Не отменять WA-4.

Но перед ней явно выделить Recovery Closure:
- durable expected post;
- durable request payload/identity;
- resolvable recovery states;
- one open operation per target;
- cross-process serialization;
- coherent checkpoint.

Затем WA-4 становится не просто «запретителем неправильных writes», а основным безопасным интерфейсом mutations.

### Окончательная формула

Цель WEB-02 должна звучать не:

> «после разрыва Chat знает, что нельзя повторять вслепую».

А:

> **«после разрыва новый агент одной командой получает authoritative state, а повтор того же operation request технически не может создать второй side effect».**

Именно это превращает WEB-02 из хорошего recovery-журнала в настоящий persistent execution coordinator.

---

## Статус этой записи

**INDEPENDENT ANALYSIS COMPLETE.**

Эта запись не является финальным архитектурным вердиктом и не разрешает менять `23/24/25/26` или runtime.

Следующий этап аналитического контура: независимый материал из `34` и этот материал из `35` сопоставляются в `36_Общая идея и согласованное решение WEB-02.md`.

<!-- RT:END -->
