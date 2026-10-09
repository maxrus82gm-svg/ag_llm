# Архитектура Web Alarm Workspace

## Статус документа

**ARCHITECTURAL SOURCE / PARTIAL IMPLEMENTATION — WA-1…WA-3 и RC-0…RC-4 DONE / VERIFIED; RC-5 DONE / VERIFIED (WA-016 independent PASS 2026-10-09); RC-6 DONE / VERIFIED (GitHub review 2026-10-08); WA4-E NEXT / NOT STARTED.**

WA-1 и WA-2 реализованы и проверены полностью. WA-3.1–WA-3.7 также DONE / VERIFIED с fresh-process recovery evidence. Старый literal combined post-change disconnect criterion **не получил PASS задним числом**: по утверждённому RT-001 он закрыт как `SUPERSEDED / DEFERRED`, а его смысл перенесён в будущий deterministic lost-response acceptance после authoritative mutation executor. Канонический маршрут: `RC-0 → RC-1 → RC-2 → RC-3 → RC-4 → RC-5 → RC-6 → WA4-E → WA4-A → WA4-O → WA4-R`. RC-0…RC-4 завершены и независимо проверены. RC-5 после WA-016 независимо принят 2026-10-09: closeout согласован с RC-6 settlement; закрытая TASK показывает read-only NEXT. RC-6 завершён после цепочки независимых проверок и Repair #1…\#4B/WA-014; его итог проверен ChatGPT по GitHub, без собственного запуска тестов. Следующий этап — WA4-E, пока не утверждён к исполнению. RC-1 добавил durable Operation Contract v2; RC-2 — persistent Resolver; RC-3 — persistent canonical-target claims, interprocess conflict gate и mutation-boundary CAS; RC-4 — tracked safe rollback; RC-5 — projection/inspection; RC-6 — bounded project recovery/resume. Authoritative physical mutation executor всё ещё не реализован.

Этот документ является каноническим владельцем архитектуры Web Alarm Workspace. Его нужно проверять и обновлять при любом подтверждённом изменении протокола, state machine, структуры TASK/микрозадач, snapshot/recovery-механики, правил replay protection, хранения или роли Web Alarm Server.

Порядок реализации, крупные этапы, критерии приёмки и их статус принадлежат отдельному документу `24_План реализации Web Alarm Workspace`. Связка документов намеренная: `23` отвечает на вопрос **«что строим и какие правила обязаны сохраняться»**, а `24` — **«в каком порядке и как именно это реализуем»**.

### Обсуждение архитектурных вопросов

WEB-02 остаётся самостоятельной переносимой подсистемой внутри `ag_llm`, но отдельного аналитического контура у неё больше нет. Сложные и спорные архитектурные вопросы WEB-02 разбираются в общем Круглом столе проекта (`28_Круглый стол - протокол и текущий вопрос.md`) наравне с вопросами любой другой подсистемы; WEB-02 не владеет этим контуром.

Пока по вопросу нет утверждённого пользователем вердикта и отдельной исполнительной TASK, выводы Круглого стола не изменяют каноническую архитектуру WEB-02, план реализации или подтверждённую историю.

### CURRENT-инварианты Recovery Closure (RC-5 / RC-6), подтверждение 2026-10-08

- RC-5 реализует rebuild/validation Projection и чистые inspect/verify без изменения physical Workspace; самостоятельный RC-5 PASS подтверждён 2026-10-09 по WA-016, не задним числом.
- RC-6 `recover/resume` работает поверх persisted authority, ограничивает административное recovery и допускает tracked RC-4 restore **только** для текущего этапа с доказанной историей законной активации. Факт recovery-решения не выдаёт обычному исполнителю право физической записи; это будущий WA4-E.
- `ACTIVE` разрешается только при отсутствии у операций микрозадачи принятого/закреплённого ABORT или ROLLBACK и открытой RC-4 session. Проверка `activation_refusal` и CAS активации сериализованы одной TASK-lock-секцией; нечитаемые факты отказывают fail-closed. `READY → ACTIVE` и `FAILED_VERIFICATION → ACTIVE` защищены; ADOPT/RETRY не считаются запретными destructive dispositions.
- Если ABORT/ROLLBACK был принят **до** ACTIVE, активация запрещена и restore исходной точки не может перезаписать внешние изменения. Если ACTIVE легитимно предшествовал recovery-решению, санкционированный rollback по RC-4 остаётся разрешённым. Для pre-execution ROLLBACK путь «сначала активируй» больше не действует: manual review + ABORT / replan.
- Оставшиеся observations не переписывают этот contract: при конкурентном Windows `os.replace` наблюдалась единичная ошибка сохранения rollback record без доказанного нарушения safety; статичный `next_safe_action` при отклонённой активации может быть неточен. Это находки для будущей приоритизации, не автоматически утверждённый Repair.

Код и независимый GitHub-review: `CLAUDE-WA-014`, commit `2c10478291b932ff0c77ef130438adc7470fcd65`, отчёт `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-014_RC6_ABORT_BEFORE_ACTIVE/rc6_wa014_report.md`; после него удалены только восстановимые Python safety copies (cleanup Codex). Повторный runtime-прогон самим verifier не выполнялся.

## 1. Зачем это нужно

`Web Alarm Workspace` — отдельная рабочая оболочка для безопасной работы Web ChatGPT с локальным проектом через Desktop Commander Remote или другой совместимый удалённый канал.

Её задача проста: если Remote оборвался, Chat потерял контекст или ответ на команду не дошёл обратно, работа не должна превращаться в угадывание — что уже сделано, что не сделано и можно ли повторять последнюю операцию.

Web Alarm Workspace должен хранить состояние TASK вне текущего Chat: план, текущий этап, исходные копии файлов, журнал операций, подтверждённый прогресс и точку безопасного продолжения.

Главная идея:

```text
обрыв связи
не равен
потере всей TASK
```

Проблема должна оставаться локальной для текущей микрозадачи. Уже подтверждённые этапы не должны теряться.

---
## 2. Базовая схема

```text
Web ChatGPT
    ↓
Desktop Commander Remote
    ↓
Web Alarm Workspace
    ↓
локальный проект / файлы / Git / команды
```

Desktop Commander остаётся транспортом и даёт удалённый доступ к компьютеру.

### 2.1. Обязательный адаптер ChatGPT Web / Desktop Commander Remote

Для участника **ChatGPT Web**, работающего в текущем пользовательском чате, Desktop Commander Remote является штатным транспортом связи с Web Alarm Workspace.

Текущий поддерживаемый режим специально разделяет **активацию** и **обмен данными**:

```text
пользователь в ChatGPT → короткий ручной стартовый импульс
ChatGPT → Desktop Commander Remote → Web Alarm Workspace
Web Alarm Workspace → persistent context/task package
ChatGPT → Desktop Commander Remote → persistent result/contribution
```

До появления отдельного поддерживаемого inbound-механизма Web Alarm **не обязан и не должен считаться способным самостоятельно «разбудить» конкретный открытый ChatGPT-чат**. Ручным может оставаться только стартовый импульс пользователя в чате: например, команда начать Круглый стол или забрать активный пакет.

После этого пользователь **не должен вручную копировать TASK, контекст, стадии Круглого стола или результат между Web Alarm и ChatGPT**. Web Alarm должен уметь подготовить persistent входной пакет для ChatGPT, а ChatGPT через Desktop Commander Remote — прочитать его и записать persistent выходной пакет/результат обратно. Конкретный формат может быть file bridge или Server/API contract; он должен быть устойчивым, машинно читаемым и независимым от истории текущего Chat.

Это правило относится именно к адаптеру **ChatGPT Web / Desktop Commander Remote**. Другие исполнители Ultra/Claude/локальные модели могут использовать API, MCP, CLI или собственные адаптеры, но для ядра Web Alarm все они должны сводиться к одной логической модели: получить входной пакет → вернуть результат с provenance/status.

Web Alarm Workspace отвечает не за транспорт, а за организацию работы:
- TASK и её контекст;
- разбиение на микрозадачи;
- snapshots перед изменениями;
- checkpoints;
- журнал действий;
- статусы этапов;
- восстановление после обрыва;
- сведения о затронутых файлах;
- подтверждённый прогресс.

В будущем внутри оболочки может появиться отдельный локальный `Web Alarm Server`, который будет автоматически поддерживать эти правила.

---
## 3. Правило входа

Фраза пользователя:

> **Работаем через Web Alarm Workspace**

означает переход в специальный режим удалённой работы.

Перед первой значимой мутацией ChatGPT должен:

1. зафиксировать полную постановку TASK в обычном Chat;
2. открыть или создать TASK в Web Alarm Workspace;
3. записать цель, ограничения и критерии завершения;
4. разбить TASK на последовательные микрозадачи;
5. определить scope каждой микрозадачи;
6. только после подготовки restore point начинать изменяющие операции.

Web Alarm Workspace становится внешней точкой восстановления Remote-сессии.

## 4. TASK и микрозадачи

Большая TASK заранее делится на небольшие этапы:

```text
TASK_152
├── M001
├── M002
├── M003
├── M004
└── ...
```

Количество этапов не фиксировано. Главное — каждый этап должен быть достаточно ограниченным, чтобы его можно было восстановить отдельно.
Пример состояния:

```text
M001 VERIFIED
M002 VERIFIED
M003 VERIFIED
M004 VERIFIED
M005 ACTIVE
M006 PLANNED
```

Если обрыв произошёл на `M005`, завершённые `M001–M004` не откатываются.

## 5. Содержимое микрозадачи

Каждая микрозадача должна иметь собственное рабочее хранилище:

```text
M005/
├── plan
├── manifest
├── snapshot/
├── session log
├── checkpoint
└── verification
```

**Plan** — что должен сделать этап.

**Manifest** — какие файлы или объекты этап имеет право менять.

**Snapshot** — состояние затрагиваемых файлов непосредственно перед началом этапа.

**Session log** — фактические события выполнения.

**Checkpoint** — краткое текущее состояние и следующий безопасный шаг.

**Verification** — доказательства того, что этап действительно завершён корректно.
## 6. Главное правило безопасности

**Нет подтверждённого restore point — нет начала изменяющей операции.**

Перед первой мутацией:

```text
PLANNED
↓
PREPARING
↓
BACKUP_DONE
↓
BACKUP_VERIFIED
↓
READY
↓
ACTIVE
```

Если обязательный файл не удалось скопировать или snapshot невозможно проверить, этап получает:

```text
BLOCKED_PREPARE
```

и изменяющая работа не начинается.

Если во время этапа внезапно требуется изменить дополнительный файл, сначала расширяется manifest и создаётся snapshot этого файла. Только после этого разрешается его менять.

## 7. Что хранить в manifest

Для каждого затрагиваемого объекта желательно фиксировать:
- исходный путь;
- существовал ли он до начала этапа;
- размер;
- hash;
- путь к snapshot;
- ожидаемый тип изменения.
Это позволяет однозначно определить rollback:

```text
existing file → восстановить snapshot
new file      → удалить
deleted file  → вернуть snapshot
```

Snapshot конкретной микрозадачи должен отражать состояние проекта **после всех предыдущих VERIFIED-этапов и до первой мутации текущего этапа**.

## 8. Жизненный цикл микрозадачи

Основные состояния:

```text
PLANNED
PREPARING
BACKUP_VERIFIED
READY
ACTIVE
DONE
VERIFIED
```

Аварийные и промежуточные состояния:

```text
BLOCKED_PREPARE
UNKNOWN_AFTER_DISCONNECT
RECOVERY_REQUIRED
FAILED_VERIFICATION
```

`DONE` и `VERIFIED` — не одно и то же.

`DONE` означает, что действие было выполнено.

`VERIFIED` означает, что результат независимо проверен и этап можно считать закрытым.

По умолчанию следующий этап не начинается, пока текущий не получил `VERIFIED`.
## 9. Поведение после обрыва

Disconnect не означает автоматически, что последняя операция провалилась.

После reconnect выполняется:

```text
RECOVER
↓
READ TASK STATE
↓
READ CURRENT MICROTASK
↓
RECONCILE DISK STATE
```

Далее возможны три случая.

### Операция реально выполнена
Фактическое состояние соответствует ожидаемому. Результат принимается, проверяется и работа продолжается.

### Операция выполнена частично или состояние неоднозначно
Этап получает `RECOVERY_REQUIRED`. После сверки можно либо принять фактическое состояние, либо восстановить snapshot текущей микрозадачи.

### Операция не начиналась
Если состояние файлов совпадает с исходным checkpoint, этап запускается снова.

## 10. Запрет слепого rollback

Нельзя автоматически откатывать проект после любого disconnect.

Команда могла успешно выполниться локально, а Remote мог потерять соединение уже после её выполнения. Поэтому сначала всегда выполняется reconciliation и только потом принимается решение:

```text
ADOPT
или
ROLLBACK CURRENT MICROTASK
```
## 11. Завершённые этапы не откатываются

Если состояние TASK выглядит так:

```text
M001 VERIFIED
M002 VERIFIED
M003 VERIFIED
M004 VERIFIED
M005 INTERRUPTED
```

стандартная максимальная точка отката — начало `M005`.

`M001–M004` уже являются подтверждённым состоянием проекта и не должны отменяться из-за проблемы текущего этапа.

## 12. Operation ID и защита от повторов

Каждая изменяющая операция должна иметь устойчивый `operation_id`.

Одна операция проходит состояния:

```text
INTENT
DONE
VERIFIED
```

Все записи относятся к одному `operation_id`.
Если после reconnect приходит повтор уже известного `operation_id`, система не должна выполнять мутацию повторно вслепую. Сначала возвращается или проверяется сохранённое состояние этой операции.

## 13. Event log и Current Checkpoint

Нужны два уровня состояния.

**Event log** — полная хронология действий и переходов.

**Current checkpoint** — компактное актуальное состояние TASK, которое новый Chat может прочитать за один вход.

Пример:

```text
TASK: TASK_152
WORKSPACE: M:\GitHub\ag_llm
LAST VERIFIED: M004
CURRENT: M005
STATUS: UNKNOWN_AFTER_DISCONNECT
SNAPSHOT: VERIFIED
LAST OPERATION: op_018
NEXT SAFE ACTION: reconcile server.py
```

Checkpoint обновляется после VERIFIED, RECOVERY, смены активной микрозадачи, изменения scope и появления blocker.

Новый Chat не должен восстанавливать рабочее состояние из сотен старых сообщений, если актуальный checkpoint уже существует.
## 14. NEXT SAFE ACTION и протокол входа

`NEXT SAFE ACTION` — центральное поле Web Alarm Workspace.

Система должна всегда подсказывать, что разрешено и необходимо делать сейчас.

Пример:

```text
CURRENT: M005 PREPARING
SNAPSHOT: NOT VERIFIED
MUTATION: NOT ALLOWED
NEXT SAFE ACTION: declare files and create snapshot
```

После подготовки:

```text
CURRENT: M005 READY
SNAPSHOT: VERIFIED
MUTATION: ALLOWED
NEXT SAFE ACTION: begin implementation
```

После обрыва:

```text
CURRENT: M005 UNKNOWN_AFTER_DISCONNECT
MUTATION: NOT ALLOWED
NEXT SAFE ACTION: reconcile disk state
DO NOT: repeat last operation
```
## 15. Работа идёт в реальном Workspace

Web Alarm Workspace не является отдельной копией проекта и не должен заставлять работать в изолированной песочнице.

Каждая TASK явно хранит:

```text
WORKSPACE_NAME: ag_llm
WORKSPACE_ROOT: M:\GitHub\ag_llm
```

ChatGPT анализирует и изменяет реальные файлы в указанном Workspace.

Web Alarm Workspace хранит только рабочее состояние TASK и restore points нужных файлов.

Например, если этап будет менять:

```text
server.py
ultra_ui.py
08_Старт.md
```

их исходные версии сохраняются до первой мутации, а затем работа продолжается непосредственно в `M:\GitHub\ag_llm`.

При необходимости ChatGPT может выходить из оболочки для чтения, поиска, анализа или тестирования проекта. Это не завершает TASK и не отменяет протокол Web Alarm Workspace.

Возврат к изменяющей работе снова проходит через текущее состояние TASK и `NEXT SAFE ACTION`.
## 16. Web Alarm Server

Внутри оболочки должен появиться локальный `Web Alarm Server`.

Он не заменяет LLM и не принимает творческие решения вместо ChatGPT. Его роль — диспетчер протокола и state machine.

Сервер должен уметь:

- создавать TASK и микрозадачи;
- хранить Workspace root;
- хранить manifest и snapshots;
- проверять наличие restore point;
- вести event log;
- собирать Current checkpoint;
- хранить `operation_id`;
- обнаруживать replay;
- хранить короткие отчёты и verification;
- выдавать `NEXT SAFE ACTION`;
- контролировать допустимые переходы состояний.

На первой версии сервер может прежде всего направлять работу и предупреждать о нарушении протокола.

В более строгой версии изменяющая операция может технически блокироваться, пока текущая микрозадача не получила `READY`.
## 17. Короткий обязательный свод правил

При входе в Web Alarm Workspace Chat должен получать краткий протокол:

```text
1. Не менять проект без READY.
2. Не начинать этап без snapshot.
3. Не менять файл вне manifest.
4. Новый файл в scope → сначала snapshot/manifest.
5. Незакрытую операцию после disconnect не повторять вслепую.
6. Disconnect не равен failure.
7. После disconnect сначала reconciliation.
8. VERIFIED-этапы не откатывать из-за текущего сбоя.
9. Следовать NEXT SAFE ACTION.
10. DONE не равно VERIFIED.
```

Эти правила должны быть короткими и машинно читаемыми, чтобы новый Chat мог быстро восстановить дисциплину работы без чтения всей архитектурной документации.

## 18. Отчёты по микрозадачам

После завершения каждого этапа сохраняется короткий отчёт:

```text
M004 REPORT
Goal: ...
Files: ...
Result: ...
Verification: ...
Status: VERIFIED
```
Отчёт нужен не вместо event log, а как быстрый человеческий handoff для пользователя и следующего Chat.

## 19. Завершённые TASK сохраняются

Завершённые задачи не удаляются.

Рекомендуемая структура:

```text
tasks/
├── active/
└── completed/
```

После финального VERIFIED TASK переносится в completed.

Сохраняются:

- исходная постановка;
- план;
- микрозадачи;
- manifests;
- snapshots;
- checkpoints;
- отчёты;
- verification;
- финальный результат.

Это позволяет позже открыть любую завершённую TASK и быстро понять, что было сделано, почему, какими файлами и с каким результатом.
## 20. Несколько реальных Workspace

Web Alarm Workspace должен быть отдельным слоем и не привязываться навсегда только к `ag_llm`.

Одна TASK всегда связана с конкретным реальным Workspace, например:

```text
M:\GitHub\ag_llm
M:\GitHub\another_project
D:\Projects\project_x
```

Сам проект остаётся снаружи оболочки. Web Alarm Workspace хранит состояние работы над ним.

## 21. Связь с Watchdog

Watchdog и Web Alarm Workspace решают разные задачи:

```text
Watchdog
→ состояние Remote-транспорта

Web Alarm Workspace
→ состояние TASK и восстановление работы
```

Watchdog может обнаружить OFFLINE, но не должен сам решать, какие файлы откатывать. После восстановления канала решение принимается через reconciliation текущей микрозадачи.

### 21.1 Recovery Report

После reconciliation Web Alarm может сохранить короткий machine-usable `RecoveryReportRecord`. Он строится из persistent reconciliation evidence + уже принятого deterministic decision, transport/process evidence и checkpoint identity. Report отдельно фиксирует `side_effect_scope = none / partial / full / ambiguous`, что принято как already done, что реально retried/rolled back, unresolved facts и `NEXT SAFE ACTION`.

Recovery Report хранится restart-safe в machine-local Web Alarm storage (`recovery_reports/<task_id>/<report_id>.json`), доступен новому Server process, через Server `recovery-reports` API и как latest report в Entry Context Pack. Он всегда `authority=evidence_only`, `automatic_mutation_authorized=false`: Report не выполняет retry/rollback/adopt, не меняет lifecycle/checkpoint/Workspace и не может из transport signal самостоятельно вывести fate операции. Недостаточные или несвязанные evidence остаются fail-closed/ambiguous.

## 22. Главные инварианты

1. Новая значимая Remote TASK сначала фиксируется в обычном Chat.
2. Большая TASK заранее разбивается на микрозадачи.
3. Каждая микрозадача имеет собственный restore point.
4. Нет подтверждённого snapshot — нет мутации.
5. Предыдущие VERIFIED-этапы не откатываются из-за ошибки текущего этапа.
6. Disconnect не равен failure.
7. После disconnect сначала reconciliation, потом решение.
8. Незакрытая операция не повторяется вслепую.
9. Каждая мутация имеет устойчивый `operation_id`.
10. Event log хранит историю, checkpoint хранит текущее состояние.
11. Новый Chat должен продолжать TASK без восстановления всей переписки.
12. Реальный проект находится вне Web Alarm Workspace.
13. Web Alarm Workspace не должен зависеть от скрытого состояния конкретной LLM.
14. Scope-extension snapshot обязан быть immutable/versioned: повторное добавление одного source path не может перезаписать более ранний captured revision.
15. Автоматический переход к следующей микрозадаче допускается только после persistent closeout gate предыдущей: `DONE_VERIFIED` + согласованный checkpoint/документация + отдельная recorded activation новой микрозадачи. Последнее видимое сообщение Chat не является authoritative state.
16. Caller-facing error, result-storage failure или UI message-delivery timeout не доказывают, что mutation не выполнялась. Fate операции определяется только по persistent operation state + reconciliation фактического Workspace.
17. Composite orchestration не считается atomic transaction: каждый mutating step должен иметь собственный operation receipt/post-state proof, пока нижний слой не предоставляет настоящую транзакцию.
18. Execution acknowledgement, persistent receipt acknowledgement и user-message delivery acknowledgement — разные состояния и не должны автоматически подменять друг друга.
19. Bootstrap новой TASK и closeout текущей TASK являются отдельными state machines с persistent receipts; после failure продолжение разрешено только с первого отсутствующего receipt.
20. Recovery acceptance включает fresh-process reopen: после независимой verification новый process обязан восстановить тот же checkpoint/decision/NEXT SAFE ACTION без hidden state старого Chat/Server.
21. Transport/Watchdog evidence является только сигналом. Watchdog не имеет authority выполнять retry/rollback/adopt, менять VERIFIED-state или активировать следующую TASK.
22. Production Web Alarm state/snapshots предпочтительно хранить физически вне Obsidian vault; если fallback находится внутри vault, runtime directories должны быть исключены из индексации и Graph View.
23. Durable operation contract обязан переживать новый process/Chat и включать canonical target identity, pre/post-state, durable payload или immutable payload reference, request fingerprint, provenance/agent identity, schema/version и persistent receipt; legacy records читаются backward-compatible без обязательной немедленной перезаписи.
24. `RETRY` в resolver не является физическим повтором mutation: до authoritative executor это только tracked persistent re-arm, привязанный к текущей evidence revision.
25. Integrity записи Operation Store/revision должна иметь минимальную межпроцессную сериализацию до появления conflict gate; полноценный canonical-target conflict admission и mutation-boundary CAS являются отдельным следующим boundary.
26. Rollback является tracked recovery operation; перед destructive restore текущее неизвестное состояние сохраняется как recoverable evidence.
27. Checkpoint — projection, а не самостоятельный authority: он должен быть rebuildable/validated из authoritative persistent state и fail-closed при stale revision.
28. WEB-02 владеет workflow state и significant tracked mutations зарегистрированного workflow. Desktop Commander остаётся транспортом и инструментом для чтения, shell/GUI и действий вне tracked workflow; tracked mutation не обходят control plane после strict rollout.
29. Canonical Windows target identity, line endings, multi-file/non-file mutations, snapshot secrets/scope/retention и Obsidian как внешний писатель являются обязательными cross-cutting constraints до strict rollout.
30. Точная новая state machine, storage backend, lease/heartbeat model и MCP topology не фиксируются этим решением и остаются отдельными deferred design questions.
31. Для файлового состояния authority — физические байты на диске: SHA-256 по точным bytes + размер. Git blob/index, `core.autocrlf`, `.gitattributes` и иная line-ending normalization не являются proof состояния target; Git-операция, переписавшая bytes, считается внешним писателем и требует обычной reconciliation.
32. Сравнение после нормализации CRLF/LF или BOM допускается только как диагностика (`EOL_ONLY_DRIFT` или эквивалент): оно не разрешает автоматический ADOPT/RETRY и при byte mismatch ведёт к fail-closed / manual review.
33. Snapshot и будущий durable payload для tracked mutation хранятся в machine-local storage вне репозитория/vault, проверяются hash+size, имеют явный scope/secret/size/retention policy; содержимое snapshot/payload не должно попадать в обычные events/reports/logs. Legacy `Alarm/` не является production snapshot storage.
34. Target claim RC-3 является persistent ownership/conflict fact, но не переносимой mutation authority. Физическая mutation разрешима только внутри server-owned `mutation_boundary`, пока одновременно удерживаются TASK-lock и canonical-target lock и повторно доказаны owner/revision/contract/physical-byte CAS facts. Standalone `/authorize` — только evidence. Для будущего WA4-E нормальная первая попытка должна фиксировать STARTED под уже удерживаемой TASK-lock **до physical write** через lock-held/internal transition path; обычный re-entrant `OperationStore.transition()` внутри boundary запрещён. Timeout/process death/Chat loss сами по себе claim не освобождают.
35. Tracked rollback RC-4 является отдельной persistent recovery operation. До первого destructive restore current bytes/absence каждого target сохраняются как recoverable evidence. Для rollback-success ownership/target-lock распространяется на **весь restore target set, включая NOOP**, потому что каждый target участвует в финальном proof. Persistent `VERIFIED / SUCCESS` допускается только после exact final byte-state proof всего target set под удерживаемыми target-lock/claims; claims снимаются после persistence VERIFIED. Receipt фиксирует исторический факт действия, но не заменяет proof текущего состояния; partial/interrupted rollback остаётся restart-safe и не повторяет неизвестный effect вслепую.

### RC-6 — подтверждённый lifecycle gate (WA-014, 2026-10-08)

Для transition `READY`/`FAILED_VERIFICATION` → `ACTIVE` Server проверяет recovery dispositions операций той же microtask: принятый либо settled `ABORT`/`ROLLBACK`, а также незавершённая RC-4 rollback session запрещают активацию. Нечитаемые authority facts блокируют её fail-closed. Решение и публичная CAS-запись `ACTIVE` выполняются внутри per-TASK operation lock, с mutation lock в согласованном порядке; принятый до активации ABORT/ROLLBACK не может создать фиктивную историю исполнения. Обратный порядок — сначала законная ACTIVE, затем ABORT/ROLLBACK — сохраняет право на восстановление через RC-4/RC-6. Если ROLLBACK принят до ACTIVE, выход «сначала активировать» запрещён, требуется ручной разбор/ABORT/replan. Эта гарантия RC-6 не является реализацией будущего physical executor WA4-E.

Independent GitHub review WA-014 2026-10-08: PASS по коду и сохранённым тестовым артефактам (580 OK, 1 skip, два прогона; 11 новых тестов). Тесты независимо не запускались; существующие findings Windows `os.replace` и устаревший текст NEXT остаются отдельными наблюдениями, не автоматически утверждёнными repair-задачами.

## 23. Точка развития

Этот документ описывает архитектуру и правила системы, а не конкретный порядок её реализации.

Программа внедрения уже вынесена в [[24_План реализации Web Alarm Workspace]]. В начале `24` хранится короткая карта крупных этапов, а ниже — подробная реализация каждого этапа, критерии приёмки и контрольные точки.

Фактическая история выполненных больших задач и микрозадач этой ветки ведётся отдельно в [[25_Журнал Web Alarm Workspace - выполненные задачи и аудит]]. В `25` попадает только подтверждённый результат выполнения и проверки, а не будущий план.

До начала реализации этот документ остаётся архитектурным источником идеи, а не утверждением о работающей функции.

### FUTURE — масштабируемая многоэтапная программа TASK

Web Alarm должен сохранять возможность масштабирования от короткой TASK на несколько микрозадач до длительной управляемой программы на десятки этапов без превращения всей работы в один гигантский prompt или hidden state конкретной LLM.

Целевая future-capability:

- родительская TASK/Program может заранее задавать **лимит/бюджет этапов** (`max_stages` / stage budget как концепт), например 10 или 20; число не должно быть глобально захардкожено;
- Planner обязан либо построить понятный план в заданном бюджете, либо явно предложить разбиение на несколько родительских TASK/Program; молча превышать установленный пользователем лимит нельзя;
- полный план этапов сохраняется persistent на диске до/по мере исполнения: stable stage id, порядок/зависимости, статус, acceptance, входные/выходные evidence refs, assigned role/agent/model, receipts и authoritative NEXT;
- каждый этап проходит обычный closeout/verification gate; автоматический переход дальше разрешён только из persistent доказанного состояния, а не из последнего сообщения модели;
- выполнение может иметь policy уровня программы: ручное подтверждение каждого этапа, автоматическое прохождение безопасных этапов или остановка только на human/decision gate;
- stage-scoped context остаётся bounded: наличие программы на 20 этапов не означает передачу всей истории всех 20 этапов каждой LLM; следующий исполнитель получает только необходимое persistent state/evidence;
- этапы одной программы могут назначаться разным агентам/моделям (например ChatGPT, Claude/Opus, Codex или другой backend), но выбор исполнителя не переносит ему Server authority, ownership, permissions или право обходить verification;
- в будущей orchestration-модели независимые этапы могут выполняться **параллельно** разными агентами, если доказаны отсутствие конфликтующих mutation scopes/claims, корректные зависимости и безопасные verification/merge gates; текущая последовательная state machine не объявляется параллельным scheduler;
- концепция выбора пользователем команды LLM, мощного Planner, назначения исполнителей, ChatGPT в режимах analysis/controlled execution, тестирования новых моделей и будущего соединения с Ultra описана в [[11_Мультимодельная архитектура и назначение LLM]] (раздел «FUTURE — команда моделей, интеллектуальная маршрутизация и профили способностей»);
- будущая подключаемая оснастка для добавления моделей без правки ядра, динамический Model/Agent Registry, API/MCP/CLI/Remote адаптеры, «Проводник» настройки подключений и изоляция секретов описаны в [[19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP]] (раздел «FUTURE — переносимый onboarding»); это не заменяет Web Alarm mutation/recovery authority;
- UI должен уметь показывать масштаб программы как иерархию/ленту/сетку: например `7 / 20 VERIFIED`, текущий этап, queued/blocked/failed stages, human gates, предложения агента и раскрываемые детали каждого этапа;
- программа должна поддерживать безопасную паузу, resume после нового process/Chat и replan оставшихся этапов без переписывания уже VERIFIED history;
- найденные агентами предложения могут добавляться как proposal/replan candidates, но не становятся автоматически новым планом без принятого orchestration decision.

Это **обязательное направление масштабируемости архитектуры**, но не новый CURRENT-этап и не вставка в текущую последовательность `24`. Ближайшие RC/WA4 stages должны лишь не закрывать этот путь. Конкретная state machine Program/Stage, scheduler policy, UI-компоненты и Coordinator implementation будут отдельным будущим design/implementation решением после стабилизации текущего recovery/executor фундамента.

## 24. Связь в Obsidian

В графе Obsidian для этой ветки достаточно минимальной цепочки:

```text
00_Главная - карта проекта
        ↓
23_Архитектура Web Alarm Workspace
        ├──→ 24_План реализации Web Alarm Workspace
        ├──→ 25_Журнал Web Alarm Workspace - выполненные задачи и аудит
        └──→ [[26_Журнал наблюдений Remote - обрывы, transport и recovery evidence]]
```

Документ `26` — технический evidence-журнал реальных Remote-обрывов и recovery-наблюдений; он специально подключён к графу только здесь, как дочерний источник фактов для Web Alarm architecture.

Дополнительные Wiki Links из `23`, `24`, `25` и `26` на остальные архитектурные документы не создавать, чтобы не превращать граф проекта в плотную сетку. Связанные темы при необходимости упоминаются обычным текстом.

## Итог

Web Alarm Workspace — это внешняя рабочая память, протокол, журнал, restore points и диспетчер состояния TASK для длительной работы Web ChatGPT с реальными локальными проектами.

Главный инвариант:

**нет подтверждённого snapshot — микрозадача не считается начавшейся.**

Главная цель:

**сделать потерю Chat или Remote локальной проблемой текущего этапа, а не потерей всей TASK.**


## 23. Controlled real Remote disconnect acceptance evidence

WA-3.7 provides the live controlled acceptance proof for the Remote recovery architecture. The authoritative passing incident is `WA37-CTRL-002` / `INC-WA37-CTRL-002`.

Before transport loss, the controlled microtask had a VERIFIED restore point and OperationStore record persisted as `STARTED`. The user intentionally stopped Desktop Commander Remote and later restored it. Recovery never interpreted transport loss as mutation failure and did not replay the mutation. Persistent evidence plus current Workspace proved the isolated target still exactly matched PRE_STATE and the exact expected post-state had not been reached.

The deterministic reconciliation result was `RETRY_SAFE / PRE_STATE_AND_POST_NOT_REACHED`; this is a decision, not automatic execution authority. Recovery Report `report_wa37_ctrl002` persisted `side_effect_scope=none`, bound `REMOTE_OFFLINE → REMOTE_RECOVERED`, and `actually_retried=[]`. A fresh process independently recovered the same result and report.

The earlier `WA37-CTRL-001` attempt is intentionally retained as non-acceptance evidence because the mutation reached FULL expected post-state without the required controlled transport break. Historical failed/non-acceptance attempts are never rewritten into PASS results.

Architectural consequence: a real Remote disconnect is recoverable from persistent operation identity + verified snapshot + current Workspace + evidence-only transport signals. The last visible Chat/UI response remains non-authoritative. Any retry remains a later explicit action even when reconciliation returns `RETRY_SAFE`.

**WA-3 parent acceptance caveat:** WA-3.7 полностью доказала restart-safe recovery после real controlled Remote loss, но final parent criterion требует ещё более строгую temporal composition в одном incident: target уже перешёл в local post-state, а transport разрывается до того, как Chat получает authoritative result. FULL/no-disconnect и NONE/real-disconnect из разных incidents не считаются эквивалентом этого combined proof.

### RC-5 — независимая приёмка WA-016 (2026-10-09)

ROLLBACK_STAGE_PROTECTED with protected_state=ROLLBACK_ACCEPTED blocks closeout as ROLLBACK_PENDING. Accepted ABORT/ADOPT block TASK completion until RC-6 durable settlement and administrative lifecycle/ownership release; SETTLEMENT_CONTRADICTION and other non-advisory recovery states fail closed. Terminal REJECTED/STALE remain advisory (F-3 unchanged). COMPLETED/ARCHIVED or outside active/ gives read-only NEXT, authority_source=task_status; recovery facts remain history. ChatGPT independently reviewed commit d53ec140a41ea879e6ea14610fd53a2c8da71554 and ran targeted 60/60 PASS, full 593 OK, 1 skipped, exit 0. F-5/F-6 OPEN follow-ups. WA4-E NOT STARTED.

### WA-017 — завершение TASK и отказоустойчивый checkpoint (independent PASS, 2026-10-09). Completion commit point = atomic directory move active/ to completed/; status COMPLETED is written after move. Interrupted completion is classified by completion_state and resumed by gated task complete. TASK outside active/ or with COMPLETED/ARCHIVED status is read-only: operation writers and RC-3 mutation_boundary refuse TASK_CLOSED regardless of ACTIVE microtask/claims. Pre-WA-017 STATUS_WRITTEN_NOT_MOVED may be moved only after fresh closeout proof. A failed checkpoint rebuild is fail-closed: MISSING/STALE/INCONSISTENT, never a fabricated VALID. SHA c7681c3841676438d1246ec3de5ac7049c52a4f9. Independent verifier ran targeted 17/17 and full 607 OK (1 skipped), exit 0. Remaining non-blocking items: claim acquire may grant ownership but not mutation authority for legacy closed TASK; occasional Windows open-handle move/rebuild refusal; old task listing cosmetics. F-1/F-3 unchanged. WA4-E NOT STARTED.
