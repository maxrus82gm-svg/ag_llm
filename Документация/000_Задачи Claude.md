# Задачи Claude

**Назначение:** отдельный оперативный handoff для задач, которые передаются Claude Desktop / Claude Code в проекте `ag_llm`.

Основной проектный handoff: [[000_Задачи для агента]]
Персональная история выполненных Claude TASK: [[001_История выполненных задач Claude]]

## Правила

- Здесь фиксируются только конкретные задачи, делегированные Claude.
- Этот файл **не заменяет** `000_Задачи для агента.md`, `05_Реестр задач.md`, `06_Журнал выполнения и отчёты.md` и профильные документы проекта.
- Если Claude выполняет значимое изменение проекта, итог после проверки должен быть отражён и в канонической документации проекта по обычным правилам.
- До начала mutation-задачи явно указывать scope, запрещённые действия и критерии проверки. Эти границы ограничивают **самовольные изменения**, но не глубину инженерного анализа.
- Claude работает как самостоятельный основной инженерный агент, а не только как исполнитель перечисленного чек-листа. Перечисленные tests/acceptance cases — обязательный минимум, не потолок. Перед `RESULT READY` Claude обязан сделать собственный adversarial pass и попытаться опровергнуть решение релевантными race/restart/replay/persistence/ownership/finalization/compatibility сценариями.
- Если неперечисленная проблема найдена внутри текущего scope — Claude сам её проверяет, исправляет и добавляет regression test. Если исправление выходит за scope/этап или требует архитектурного решения — код за рамками не менять; reproduction/evidence/root cause/impact и предложение обязательно вынести в task-report и БЛОК 3 как `FINDING / PROPOSAL / BLOCKER` для решения verifier/пользователя.
- Claude имеет право читать соседний релевантный код и делать безопасные isolated probes/tests ради проверки гипотез. Это не даёт права самовольно запускать следующий этап, менять утверждённый план или расширять production mutation-scope.
- Секреты, токены, cookies, Organization ID и платёжные данные сюда не записываются.
- Технические наблюдения по моделям, лимитам и сети вести в `27_Claude.md`.
- БЛОК 1 — входной активный слот. Пользователь/координатор переносит сюда следующую утверждённую постановку. Claude обязан перечитать БЛОК 1 перед стартом.
- После фактического завершения исполнения Claude **сам** выполняет безопасную ротацию без отдельной команды: (1) копирует полную постановку из БЛОКА 1 в БЛОК 2, сохраняя scope, запреты и acceptance; (2) записывает БЛОК 3 — factual closeout: что реально изменено, файлы, проверки, что осталось вне scope, report path и статус `RESULT READY / AWAITING INDEPENDENT VERIFICATION`; (3) только после успешной записи БЛОКОВ 2–3 очищает БЛОК 1 до короткого `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`.
- Если запись/сессия оборвалась во время ротации, БЛОК 1 нельзя очищать или повторно переносить вслепую: сначала перечитать фактический файл и доказать сохранность БЛОКОВ 2–3. Незавершённая/PAUSED TASK по этому правилу не очищается.
- БЛОК 2 хранит полную последнюю выполненную постановку; БЛОК 3 — её operational result. До независимой проверки Claude не пишет `DONE / VERIFIED`.
- До перезаписи БЛОКОВ 2–3 предыдущая независимо подтверждённая TASK должна уже иметь постоянную append-only историю.
- Полная постановка TASK может дополнительно фиксироваться в обычном Chat как человеческий резерв/след обсуждения, но каноническим источником исполнения остаётся актуальный БЛОК 1 персональной карточки.
- Claude сам ведёт оперативную ротацию своей персональной карточки (`БЛОК 1` + `БЛОК 2` + `БЛОК 3`) по правилам выше и task-report в `Alarm/ALARM_TASK_SESSION`. Постоянный documentation closeout после независимой проверки выполняет verifier/ChatGPT: `001_История выполненных задач Claude.md`, `06_Журнал выполнения и отчёты.md`, профильный журнал/реестр и другие реально затронутые канонические документы.

---
# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
TASK: —

---
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена Claude 2026-10-04. Результат и статус — в БЛОКЕ 3. Ниже — полная постановка из БЛОКА 1 дословно (fenced-блок сохраняет разбивку строк; хвостовые пробелы сняты).

```text
TASK: CLAUDE-WA-007 — RC-5:
Projection correctness + pure inspection + safe TASK closeout

Статус:
READY / NOT STARTED

Исполнитель:
Claude Opus 5.5

==================================================
0. КОНТЕКСТ И BASELINE
==================================================

Канонический маршрут:

RC-0 = DONE / VERIFIED
RC-1 = DONE / VERIFIED
RC-2 = DONE / VERIFIED
RC-3 = DONE / VERIFIED
RC-4 = DONE / VERIFIED

Текущий этап:
RC-5 — Projection correctness + pure inspection

Следом, но НЕ в этой TASK:

RC-6
→ WA4-E
→ WA4-A
→ WA4-O
→ WA4-R

Принятый RC-4 code baseline:

commit 154
c46bee7f60ff8354be956881d30de916d5264891

Independent verification RC-4:

- RC-4 focused: 43/43 PASS;
- RC-2/RC-3/RC-4 combined focused: 88/88 PASS;
- full Web Alarm: 329/329 PASS;
- compileall PASS;
- git diff --check PASS;
- independent NOOP race probe PASS.

ВАЖНО ПО GIT:

После commit 154 ChatGPT/verifier локально сделал documentation closeout RC-4
и подготовил project-level NEXT = RC-5.

Поэтому при старте TASK:

1. сначала определить фактический HEAD;
2. если HEAD новее 154 только из-за verifier documentation/task-card commits — это нормально;
3. runtime-код Web Alarm должен соответствовать принятому RC-4 baseline, если пользователь явно не сообщил об ином;
4. любые неожиданные runtime/code changes после 154:
   STOP → reconciliation before editing;
5. существующие documentation changes и `.obsidian/workspace.json` не откатывать.

==================================================
1. РЕЖИМ РАБОТЫ АГЕНТА
==================================================

Ты работаешь как самостоятельный основной инженерный агент.

Scope ограничивает САМОСТОЯТЕЛЬНЫЕ ИЗМЕНЕНИЯ,
но не глубину анализа.

Перечисленные ниже tests / scenarios —
ОБЯЗАТЕЛЬНЫЙ МИНИМУМ, а не потолок.

До RESULT READY обязательно выполнить собственный adversarial pass:

- попытаться опровергнуть projection model;
- искать stale-state races;
- process restart/reopen;
- concurrent state changes;
- resolver/reconciliation precedence bugs;
- hidden writes в read-only путях;
- closeout TOCTOU;
- legacy persistence problems;
- взаимодействие RC-2 / RC-3 / RC-4.

Если обнаружен неперечисленный дефект ВНУТРИ RC-5 scope:
→ reproduce;
→ fix;
→ regression test.

Если реальная проблема требует RC-6 / WA4-E / новой глобальной state machine:
→ НЕ расширять scope;
→ сохранить evidence;
→ FINDING / PROPOSAL / BLOCKER;
→ recommended next action.

Принцип:

ШИРОКАЯ СВОБОДА АНАЛИЗА.
ОГРАНИЧЕННАЯ СВОБОДА ИЗМЕНЕНИЙ.

==================================================
2. ЦЕЛЬ RC-5
==================================================

Checkpoint и все пользовательские представления состояния должны перестать быть самостоятельной истиной.

Целевая модель:

AUTHORITATIVE PERSISTENT STATE
→ PURE PROJECTION
→ Context Pack / API / future UI

а НЕ:

old checkpoint
→ считается истиной
→ диктует NEXT SAFE ACTION.

RC-5 должен доказать четыре вещи:

A. checkpoint является rebuildable / validated projection;

B. inspect / verify действительно read-only и не имеют скрытых mutations;

C. stale projection никогда не выдаётся как authoritative current state;

D. TASK нельзя закрыть, пока существует unresolved/open authoritative state.

==================================================
3. SOURCE OF TRUTH MATRIX
==================================================

Перед реализацией явно зафиксировать в report,
какие источники являются authority.

Минимум рассмотреть:

AUTHORITATIVE:

- TaskStore:
  - TaskRecord;
  - TaskPlanRecord;
  - MicrotaskRecord;

- Manifest / verified restore-point integrity;

- OperationStore:
  - operation identity;
  - status;
  - revision;
  - contract;

- ResolutionStore + ResolverService:
  - accepted action;
  - basis;
  - freshness;

- RC-3 TargetClaimStore:
  - active physical-target ownership;

- RC-4 RollbackStore:
  - rollback status;
  - revision;
  - target receipts;
  - claims_released;
  - next_safe_action.

DERIVED / EVIDENCE / HISTORY:

- checkpoint.json / checkpoint.md;
- Recovery Report;
- Reconciliation calculation;
- event log;
- Entry Context Pack;
- UI task view.

Checkpoint НЕ может быть источником фактов,
из которых затем «доказываются» сами authoritative stores.

Event history также не должен становиться заменой current authoritative records.

==================================================
4. ИЗВЕСТНЫЕ ПРОБЛЕМЫ ТЕКУЩЕГО КОДА
==================================================

Перед изменениями подтвердить или опровергнуть кодом/tests следующие наблюдения.

--------------------------------
4.1 CHECKPOINT CURRENTLY TRUSTED
--------------------------------

Сейчас EntryContextPackBuilder при наличии checkpoint предпочитает:

- checkpoint.current_microtask_id;
- checkpoint.last_verified_microtask_id;
- checkpoint.current_status;
- checkpoint.snapshot_status;
- checkpoint.last_operation_id;
- checkpoint.next_safe_action.

То есть stale checkpoint способен переопределить фактический TaskStore / Operation / Resolver state.

Server `_task_bundle()` и `_ui_task_view()` также читают persisted checkpoint.

Это противоречит:

checkpoint = projection, not authority.

--------------------------------
4.2 CHECKPOINT НЕ ИМЕЕТ SOURCE BASIS
--------------------------------

CheckpointRecord сейчас не содержит достаточной механической связи с состоянием, из которого он был построен.

Нет достаточного доказательства:

- plan revision;
- authoritative operation revision;
- Resolver basis/freshness;
- rollback revision/status;
- projection/source fingerprint.

Поэтому файл невозможно механически отличить:

VALID
от
STALE BUT PLAUSIBLE.

--------------------------------
4.3 MANUAL CHECKPOINT WRITE
--------------------------------

CLI сейчас позволяет caller написать:

checkpoint write
--current-status
--snapshot-status
--last-operation-id
--next-safe-action

То есть caller фактически может вручную создать «истину».

После RC-5 normal/public workflow не должен позволять caller-supplied checkpoint управлять authoritative NEXT.

Выбери минимальную backward-compatible policy:

предпочтительно:
- explicit `checkpoint rebuild` из authoritative state;
- manual arbitrary write deprecated/rejected;

ИЛИ иной вариант, при котором legacy checkpoint может существовать,
но всегда является UNVALIDATED / NON-AUTHORITATIVE.

Не ломать старые файлы только ради чистоты схемы.

--------------------------------
4.4 SNAPSHOT VERIFY НЕ PURE
--------------------------------

ServerStateMachine.verify_snapshot():

- вызывает `_require_verified_snapshot`;
- тот вызывает `verify_restore_point(active_only=True)`;
- при ошибке этот путь способен менять manifest/microtask status;
- при успехе verify_snapshot вызывает `_write_checkpoint()`.

Следовательно «verify» имеет скрытые persistent writes.

RC-5 требует:

VERIFY / INSPECT
→ ZERO WORKFLOW MUTATION.

Нужен pure restore-point integrity primitive.

Не использовать destructive restore.

--------------------------------
4.5 ADVISORY RECONCILIATION МОЖЕТ ПЕРЕПИСАТЬ NEXT
--------------------------------

EntryContextPackBuilder сейчас:

если reconciliation != None:
→ заменяет NEXT_SAFE_ACTION
  на reconciliation["NEXT_SAFE_ACTION"].

После RC-2 это недостаточно.

Persistent fresh accepted Resolver resolution
является более сильным recovery fact,
чем новый advisory calculation.

Пример:

accepted RETRY / ADOPT / ABORT / ROLLBACK
уже persistent

→ raw reconciliation не имеет права молча вернуть UI/Context
к старому advisory NEXT.

--------------------------------
4.6 TASK COMPLETE ОБХОДИТ CLOSEOUT GATE
--------------------------------

TaskStore.complete_task()
сейчас может физически переместить TASK в completed
без проверки:

- все ли microtasks VERIFIED;
- есть ли open operations;
- есть ли unresolved recovery;
- есть ли active RC-3 claims;
- есть ли незакрытый RC-4 rollback;
- завершён ли pending rollback claim release.

CLI `task complete`
использует этот low-level path напрямую.

RC-5 должен добавить настоящий closeout gate.

==================================================
5. CANONICAL PROJECTION SERVICE
==================================================

Нужен один server-owned / library-owned способ построить CURRENT projection.

Предпочтительно отдельный минимальный service/layer,
например:

ProjectionService
или эквивалент.

Название не является contract.

Главное:

build(task_id)
→ PURE
→ authoritative stores
→ deterministic semantic projection.

Projection не должна зависеть от persisted checkpoint.

Persisted checkpoint можно сравнить с projection,
но нельзя использовать его для построения projection.

==================================================
6. MINIMUM PROJECTION CONTENT
==================================================

Projection минимум должна механически выводить:

TASK:
- task_id;
- workspace_id;
- task status;
- plan revision.

PLAN POSITION:
- ordered microtasks;
- contiguous last VERIFIED;
- actual current microtask;
- current microtask status.

RESTORE POINT:
- pure snapshot/restore-point integrity status.

OPERATIONS:
- relevant/open operations;
- operation status/revision;
- unresolved operation facts.

RESOLUTION:
- latest relevant accepted resolution;
- action/result;
- whether it is CURRENTLY FRESH;
- basis identity.

ROLLBACK:
- associated rollback session, if any;
- status/revision;
- overall result;
- claims_released;
- next_safe_action;
- historical receipts/facts.

OWNERSHIP:
- active relevant claims / blockers where needed for safety projection.

RECOVERY:
- authoritative recovery state;
- authoritative NEXT SAFE ACTION;
- source/reason for that NEXT.

PROJECTION METADATA:
- projection semantic version;
- source/basis identity;
- deterministic source fingerprint;
- projection fingerprint;
- as_of / generated_at;
- whether persisted checkpoint is VALID / STALE / MISSING / LEGACY_UNVALIDATED / CORRUPT.

Точные field names можно выбрать самостоятельно,
но semantics должны быть явными и тестируемыми.

==================================================
7. CURRENT MICROTASK ДОЛЖЕН ВЫВОДИТЬСЯ, А НЕ ВЕРИТЬ POINTER
==================================================

Отдельно проверить current microtask selection.

Текущий код может предпочесть plan.current_microtask_id
или checkpoint.current_microtask_id.

Projection должна доказать позицию по ordered lifecycle.

Минимальный принцип:

- порядок из plan;
- contiguous VERIFIED prefix;
- первый не-VERIFIED stage = основной current candidate;
- ACTIVE pointer может corroborate состояние, но не должен молча противоречить lifecycle;
- multiple ACTIVE / impossible ordering
  → fail-closed projection blocker;
- pointer на VERIFIED stage при существующем более позднем non-VERIFIED
  → pointer stale, не authority.

Не менять общую Microtask state machine без необходимости.

==================================================
8. CHECKPOINT VALIDATION
==================================================

Persisted checkpoint должен иметь достаточно metadata,
чтобы можно было доказать:

VALID
или
STALE.

Нельзя проверять checkpoint только сравнением timestamp.

Нужна semantic basis/fingerprint.

Минимальные свойства:

same authoritative source state
→ same semantic source/projection fingerprint
даже после fresh process.

изменился relevant authoritative fact
→ old checkpoint validation != VALID.

Примеры relevant changes:

- plan revision;
- microtask status;
- operation revision/status;
- fresh/stale Resolver resolution;
- rollback revision/status;
- claims release state.

Если visible projection случайно выглядит одинаково,
но underlying authority revision изменилась,
source basis всё равно должен отразить изменение.

==================================================
9. CHECKPOINT REBUILD
==================================================

Checkpoint должен быть rebuildable из projection.

Нужны два разных действия:

INSPECT / VALIDATE:
→ PURE
→ никаких writes.

REBUILD:
→ explicit mutation только projection files;
→ checkpoint.json / checkpoint.md;
→ не меняет Task/Microtask/Operation/Resolver/Rollback/Workspace.

Нельзя автоматически чинить stale checkpoint во время обычного GET / context / inspect.

Read path должен показать:

checkpoint_status = STALE

и текущую derived projection,
а не незаметно переписать файл.

==================================================
10. LEGACY CHECKPOINTS
==================================================

Старые checkpoint files RC-0…RC-4 должны читаться backward-compatible.

Они могут не иметь новой source basis.

Такие записи:

НЕ переписывать автоматически при read.

Они должны классифицироваться примерно как:

LEGACY_UNVALIDATED
или эквивалент.

Normal projection consumers НЕ должны доверять legacy next_safe_action.

Explicit rebuild может создать современную projection.

==================================================
11. TAMPER / STALE DETECTION
==================================================

Обязательно проверить минимум два вида stale:

A. Source stale:

checkpoint построен правильно,
после чего operation revision / microtask / resolver / rollback state изменились.

→ validation = STALE.

B. Projection tamper:

source basis оставили прежним,
но вручную изменили, например:

next_safe_action
current_status
current_microtask_id.

→ validation НЕ должна вернуть VALID.

То есть source fingerprint недостаточен сам по себе,
если content checkpoint не проверяется против freshly derived projection.

==================================================
12. PURE RESTORE-POINT VERIFY
==================================================

Сделать side-effect-free integrity verification restore point.

Требования:

- success → no writes;
- corrupt snapshot → no writes;
- missing snapshot → no writes;
- invalid manifest → no writes.

Особенно:

pure verify НЕ должен:

- ставить BLOCKED_PREPARE;
- менять Microtask status;
- менять Manifest status;
- писать checkpoint;
- append event;
- менять Workspace.

Существующий mutating preparation/transition path
может отдельно переводить state при фактическом workflow failure.

Не смешивать:

inspection
и
workflow transition.

==================================================
13. SERVER SNAPSHOT VERIFY
==================================================

Existing Server snapshot verification path
должен стать реально read-only.

Если endpoint остаётся POST ради backward API compatibility — допустимо.

Но response обязан явно показывать:

workflow_mutation_performed = false
или эквивалент.

Проверить storage digest before/after.

==================================================
14. CONTEXT PACK ДОЛЖЕН ИСПОЛЬЗОВАТЬ PROJECTION
==================================================

EntryContextPackBuilder после RC-5:

НЕ берёт current truth из checkpoint.

Он получает canonical projection.

Checkpoint information может отображаться как:

- persisted projection;
- validation status;
- stale/missing diagnostic.

Но CURRENT_STATUS / CURRENT_MICROTASK / NEXT_SAFE_ACTION
должны происходить из authoritative projection.

Context Pack по-прежнему:

- bounded;
- read-only;
- restart-safe;
- не читает весь event history.

==================================================
15. SERVER TASK / UI VIEW
==================================================

`_task_bundle()` / `_ui_task_view()` также не должны использовать stale checkpoint как authority.

UI HTML/JS в RC-5 НЕ переделывать.

Можно изменить/дополнить server-side data model,
которую будущий UI будет использовать.

Если API compatibility позволяет —
сохранить старые fields и добавить:

projection
checkpoint_validation
authority_source

или эквивалент.

Не выдавать stale checkpoint NEXT как current next.

==================================================
16. RECOVERY AUTHORITY PRECEDENCE
==================================================

Зафиксировать один deterministic precedence rule.

Минимальный смысл:

1. Если существует активная tracked RC-4 rollback session
   по current fresh ROLLBACK resolution,
   её persistent state / NEXT имеет приоритет
   над исходным Resolver request.

2. Иначе fresh accepted persistent Resolver resolution
   имеет приоритет над raw advisory reconciliation.

3. Если accepted resolution больше НЕ fresh:
   её next нельзя показывать как authoritative current next;
   projection должна показать stale basis /
   необходимость новой reconciliation.

4. Если нет applicable fresh Resolver action:
   reconciliation может дать advisory recovery decision.

5. В normal state без recovery:
   NEXT выводится из canonical microtask/state-machine facts.

Recovery Report:
→ evidence/history only;
→ не получает власть поверх fresher Resolver/Rollback state.

==================================================
17. RESOLVER TEST MATRIX
==================================================

Минимум проверить projection после fresh accepted:

- RETRY;
- ADOPT;
- ABORT;
- ROLLBACK request.

Raw reconciliation НЕ должна перезаписать их NEXT.

Для ROLLBACK дополнительно:

accepted ROLLBACK
→ RC-4 session PREPARED/PRESERVED/APPLYING/etc.
→ projection NEXT следует текущей rollback session.

После VERIFIED rollback:
→ projection отражает verified historical result,
  но не утверждает вечную current physical truth после release.

==================================================
18. RC-4 P1 — HISTORICAL / AS_OF SEMANTICS
==================================================

Это обязательный design input RC-5.

RC-4 report:

`restored`
`noop`

фиксируют состояние НА МОМЕНТ final verification.

После:

VERIFIED
→ claims release
→ новая легальная operation

файл может измениться.

Поэтому projection/report/UI-facing facts должны явно различать:

HISTORICAL FACT:
"target was restored/noop at rollback verification time"

и

CURRENT PHYSICAL STATE:
"что лежит на диске сейчас".

Не называть historical rollback receipt
вечным current-state proof.

Минимум добавить явный:

as_of
historical
verified_at
source = rollback_receipt

или эквивалентную semantics.

Не обязательно менять RC-4 receipt schema,
если projection может выразить это корректно без migration.

==================================================
19. CLOSEOUT INSPECTION
==================================================

Нужен PURE closeout inspector:

inspect_task_closeout(task_id)
или эквивалент.

Он возвращает:

eligible = true/false
blockers = [...]
authoritative facts
NEXT SAFE ACTION.

Сам inspect:

ZERO MUTATION.

Минимум проверять:

- все plan microtasks VERIFIED;
- нет impossible/stale plan state;
- нет unresolved/open operations;
- нет active RC-3 claims;
- нет rollback session, которая требует продолжения/reconciliation/close;
- VERIFIED rollback с pending claim release не считается полностью clean;
- accepted RETRY означает pending future execution и блокирует closeout;
- accepted ROLLBACK без terminal safe RC-4 outcome блокирует closeout.

Для ADOPT / ABORT / CLOSED/PRESERVATION_FAILED и других terminal recovery facts:

не придумывать новую semantics на глаз.

Проанализировать существующие RC-2/RC-4 contracts
и выбрать conservative rule.

Если existing contracts не позволяют однозначно классифицировать конкретный state:
fail-closed + FINDING,
а не автоматически разрешать completion.

==================================================
20. AUTHORITATIVE TASK COMPLETE
==================================================

Public task completion больше не должен обходить gate.

Как минимум:

CLI `task complete`
→ closeout gate
→ complete only if eligible.

Low-level TaskStore.complete_task()
может остаться storage primitive,
но normal public workflow не должен вызывать его без gate.

Если добавление Server complete endpoint естественно и минимально —
допустимо.

Не добавлять UI.

При reject:

- TASK остаётся active;
- никаких частичных moves;
- return blockers/NEXT.

При accept:

- eligibility повторно доказана;
- TASK complete выполняется под подходящей task-level serialization.

==================================================
21. CLOSEOUT CONCURRENCY / TOCTOU
==================================================

Обязательна настоящая multiprocess проверка.

Сценарий:

Process A:
→ closeout inspection / complete.

Process B:
→ создаёт/открывает operation для той же TASK.

Нельзя получить:

TASK moved to COMPLETED
+
new unresolved operation admitted inside it.

Допустимые результаты:

A wins:
→ TASK completes;
→ B fails because TASK no longer mutable/active.

ИЛИ:

B wins:
→ operation persists;
→ closeout sees blocker and refuses.

Не должно быть TOCTOU:

check clean
→ foreign operation appears
→ complete anyway.

Использовать существующую task-lock infrastructure,
если она подходит.

Не создавать глобальный lock.

==================================================
22. PROJECTION REBUILD CONCURRENCY
==================================================

Также проверить race:

Process A:
→ rebuild checkpoint.

Process B:
→ меняет authoritative revision/state.

Допустимо, что persisted projection мгновенно становится stale.

Недопустимо:
→ read/validate после race молча объявляет её VALID.

Предпочтительно rebuild выполняется под existing task-level serialization
или делает final basis recheck.

Какой вариант лучше — реши после анализа кода.

==================================================
23. PUBLIC MANUAL CHECKPOINT AUTHORITY
==================================================

После RC-5 caller не должен иметь возможность сказать:

NEXT_SAFE_ACTION = "do dangerous thing"

и затем заставить Context Pack/UI считать это authority
через `checkpoint write`.

Возможные решения:

A. убрать/deprecate arbitrary public checkpoint write
и заменить `checkpoint rebuild`;

B. сохранить legacy write только как явно NON-AUTHORITATIVE data,
которое validation никогда не принимает без current basis.

Выбери минимальный backward-compatible вариант.

Обязательно test:

manual fabricated checkpoint
→ Context Pack current NEXT остаётся server-derived.

==================================================
24. PURE INSPECTION CONTRACT
==================================================

После RC-5 следующие operations должны быть доказанно read-only,
если их задача только inspect/verify:

- projection build;
- checkpoint validation;
- checkpoint show/inspect;
- Entry Context Pack build;
- Server task GET;
- Server UI-data GET;
- operation GET/list;
- resolution GET/list/freshness;
- rollback GET/list;
- pure snapshot verify;
- closeout inspect;
- reconciliation calculation.

Не обязательно объединять их в один API.

Но tests должны сравнивать machine-local storage + Workspace
before/after и ловить скрытые writes:

- checkpoint;
- event log;
- manifest;
- microtask;
- operation;
- resolution;
- rollback;
- claims;
- Workspace files.

==================================================
25. CHECKPOINT REBUILD — EXPLICIT WRITE ONLY
==================================================

Единственный нормальный write projection:

explicit rebuild
или workflow mutation,
которая после authoritative state change обновляет projection.

При workflow mutation:

state first
→ projection second.

Projection write failure
НЕ должна отменять факт уже произошедшей authoritative mutation
и НЕ должна превращать stale checkpoint в authority.

Нужна понятная failure semantics.

Не строить сложную distributed transaction.

==================================================
26. BACKWARD COMPATIBILITY
==================================================

Обязательно сохранить:

- RC-0…RC-4 persistent data;
- legacy CheckpointRecord;
- existing tasks without new projection metadata;
- existing Operation Contract;
- Resolver records;
- rollback records;
- Recovery Reports.

Read legacy:
→ no automatic migration write.

Explicit rebuild:
→ может создать современный projection.

Не изменять production storage при обычном inspection.

==================================================
27. ЧТО RC-5 НЕ ДЕЛАЕТ
==================================================

НЕ делать:

- RC-6 project-level one-command resume;
- WA4-E authoritative physical mutation executor;
- STARTED-before-write executor integration;
- WA4-A lost-response injection;
- UI/HTML redesign;
- persistent jobs;
- scheduler;
- multi-stage 10/20-step Program implementation;
- model/agent coordinator;
- lease/heartbeat;
- OS filesystem locks;
- strict rollout;
- закрытие legacy snapshot restore bypass;
- `.gitattributes`;
- unrelated Agent Runtime changes.

Будущая Program/TASK scalability из документа 23:
учитывать архитектурно,
но НЕ реализовывать сейчас.

==================================================
28. ОБЯЗАТЕЛЬНЫЕ TESTS — МИНИМУМ
==================================================

A. Missing checkpoint:
authoritative projection строится правильно;
read не создаёт checkpoint.

B. Valid modern checkpoint:
validate = VALID;
fresh process даёт тот же semantic projection fingerprint.

C. Stale source:
после plan/microtask/operation revision change
old checkpoint = STALE;
Context/UI не используют его NEXT.

D. Tampered checkpoint:
next/status/current id изменены вручную;
validation != VALID.

E. Legacy checkpoint:
старый record читается;
LEGACY_UNVALIDATED / equivalent;
read не переписывает его;
explicit rebuild создаёт valid modern projection.

F. Pure snapshot verify SUCCESS:
0 persistent writes.

G. Pure snapshot verify FAILURE:
corrupt snapshot;
0 persistent writes;
microtask/manifest НЕ переходят в BLOCKED_PREPARE.

H. Context Pack:
stale/fabricated checkpoint не может подменить
CURRENT_STATUS / CURRENT_MICROTASK / NEXT_SAFE_ACTION.

I. Resolver RETRY precedence:
fresh accepted RETRY
не перезаписывается advisory reconciliation.

J. ADOPT precedence.

K. ABORT precedence.

L. ROLLBACK precedence:
tracked rollback session NEXT сильнее старого request/advisory reconciliation.

M. Stale accepted resolution:
не используется как authoritative next;
projection fail-closed.

N. RC-4 historical semantics:
restored/noop facts имеют явный as_of/history meaning;
последующая легальная mutation не превращает старый receipt
в current physical proof.

O. Pure closeout inspect:
zero writes.

P. closeout blocks non-VERIFIED microtask.

Q. closeout blocks unresolved/open operation.

R. closeout blocks active target claim.

S. closeout blocks pending/nonterminal rollback.

T. closeout blocks VERIFIED rollback with claims_released=false.

U. public task complete cannot bypass gate.

V. clean task closeout succeeds.

W. multiprocess closeout vs operation begin:
никакого completed + new-open-operation race.

X. projection rebuild vs source revision race:
последующий validation никогда не даёт false VALID.

Y. repeated inspect/context/ui:
storage digest unchanged.

Z. fresh process:
same authoritative projection/NEXT from same persisted source state.

Эти tests — минимум, а не потолок.

==================================================
29. ADVERSARIAL PASS
==================================================

После A–Z самостоятельно проверить дополнительные сценарии.

Особенно подумать о:

- checkpoint says m1 current, но m1 VERIFIED и m2 non-VERIFIED;
- plan.current points backward;
- multiple ACTIVE microtasks in tampered persistence;
- operation revision changes без visible status change;
- accepted resolution becomes stale;
- rollback VERIFIED but claim release incomplete;
- rollback CLOSED with historical partial receipts;
- corrupted checkpoint.md при valid checkpoint.json;
- corrupted checkpoint.json при intact authoritative stores;
- explicit rebuild interrupted between JSON and MD;
- two concurrent rebuilders;
- completion during rebuild;
- completion while active claim release is in progress;
- legacy tasks with no OperationStore records;
- completed/archive task inspection;
- Recovery Report older/newer than Resolver;
- event history contradicts current authoritative record;
- current projection after RC-4 historical receipt + later legitimate writer.

Если находишь bug внутри RC-5:
fix + regression.

Если вне:
FINDING / PROPOSAL.

==================================================
30. ACCEPTANCE RC-5
==================================================

RC-5 можно отдавать на independent verification только если доказано:

- checkpoint = projection, not authority;
- projection можно построить без checkpoint;
- projection содержит deterministic source/basis identity;
- stale/tampered/legacy checkpoint не используется как current truth;
- explicit validation механически отличает VALID от STALE;
- inspect/read не выполняют hidden writes;
- snapshot verification действительно pure;
- Context Pack и Server views строятся из authoritative projection;
- fresh accepted Resolver/RC-4 state имеет deterministic precedence над advisory reconciliation;
- RC-4 rollback facts явно исторические/as_of, если ownership уже released;
- closeout inspect pure;
- public task completion проходит closeout gate;
- open/unresolved state блокирует completion;
- closeout TOCTOU race закрыт;
- multiprocess projection race не создаёт false VALID;
- legacy state backward-compatible;
- full Web Alarm regression PASS;
- RC-6 NOT STARTED.

==================================================
31. WORKFLOW / SAFETY
==================================================

Перед кодом:

1. перечитать:
   - Документация/000_Задачи Claude.md;
   - Документация/000_Задачи для агента.md;
   - Документация/18_Регламент сопровождения документации.md;
   - Документация/23_Архитектура Web Alarm Workspace.md;
   - Документация/24_План реализации Web Alarm Workspace.md;
   - Документация/33_Круглый стол - план исполнения.md;
   - RC-4 report §18–§19;

2. определить фактический Git HEAD;

3. определить pre-existing dirty tree;

4. не трогать чужой `.obsidian/workspace.json`;

5. создать:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-007_RC5/

6. safety copies всех существующих файлов,
которые будешь менять;

7. сохранить baseline hashes/status;

8. подтвердить baseline full Web Alarm regression
(принятый RC-4 baseline = 329/329 PASS);

9. live WEB-02 storage:
только read-only inspection;
никаких destructive/migration tests на живом storage.

Все mutation/concurrency tests:
isolated temporary storage/workspace.

==================================================
32. ВОЗМОЖНЫЕ ФАЙЛЫ
==================================================

Ожидаемые области анализа:

- web_alarm/event_checkpoint_store.py
- web_alarm/models.py
- web_alarm/context_pack.py
- web_alarm/state_machine.py
- web_alarm/server.py
- web_alarm/cli.py
- web_alarm/task_store.py
- web_alarm/operation_store.py
- web_alarm/reconciliation_service.py
- web_alarm/resolver_service.py
- web_alarm/recovery_report_service.py
- web_alarm/rollback_store.py
- web_alarm/rollback_service.py
- web_alarm/target_claim_store.py / service.py

Возможен новый узкий projection/closeout module.

Не надо менять все перечисленные файлы просто потому,
что они перечислены.

Минимизировать diff.

==================================================
33. VERIFICATION
==================================================

После реализации минимум:

- новые RC-5 focused tests;
- event/checkpoint tests;
- Context Pack tests;
- Server tests;
- state-machine tests;
- CLI tests;
- Resolver tests;
- Recovery Report integration;
- RC-4 focused + concurrency;
- RC-3 focused + concurrency;
- RC-2 focused;
- реальные multiprocess RC-5 race tests;
- full:
  python -B -m unittest <all test_web_alarm modules>
- python -B -m compileall -q web_alarm
- git diff --check

Плюс собственные adversarial tests.

==================================================
34. REPORT
==================================================

Создать:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-007_RC5/rc5_report.md

Обязательно описать:

- фактические stale-authority проблемы baseline;
- source-of-truth matrix;
- projection architecture;
- projection/source fingerprints;
- checkpoint validation states;
- legacy compatibility;
- pure inspection proof;
- snapshot verify purity;
- Resolver/Reconciliation/Rollback precedence;
- RC-4 historical/as_of representation;
- TASK closeout gate;
- exact unresolved/open classification;
- task-level serialization / concurrency;
- changed files;
- focused/full tests;
- multiprocess results;
- live storage read-only evidence;
- ADVERSARIAL REVIEW / FINDINGS / PROPOSALS;
- RC-6 NOT STARTED.

==================================================
35. STOP / DECISION REQUIRED
==================================================

Остановиться и вынести решение, если для correctness требуется:

- новая глобальная Operation/Microtask state machine;
- изменение semantics RC-2 Resolver actions;
- изменение RC-4 rollback lifecycle;
- lease/heartbeat;
- WA4-E physical executor;
- OS-level filesystem transaction;
- архитектурный scheduler;
- Program/Stage orchestration.

Не обходить проблему локальным костылём.

==================================================
36. CARD ROTATION
==================================================

После фактического завершения:

1. полную эту постановку →
   БЛОК 2 персональной карточки Claude;

2. БЛОК 3 →
   factual result +
   tests +
   adversarial findings/proposals;

3. статус:
   RESULT READY / AWAITING INDEPENDENT VERIFICATION;

4. только после подтверждения сохранности БЛОКОВ 2–3:

БЛОК 1 →

Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
TASK: —

5. НЕ писать DONE / VERIFIED;

6. НЕ обновлять самостоятельно:
   - 001;
   - 05;
   - 06;
   - 24;
   - 25;
   - глобальный 000;

это делает ChatGPT/verifier после independent PASS;

7. не commit / push;

8. RC-6 НЕ начинать.

NEXT SAFE ACTION:

выполнить только CLAUDE-WA-007 / RC-5,
провести обязательный самостоятельный adversarial pass,
остановиться на
RESULT READY / AWAITING INDEPENDENT VERIFICATION.

RC-6 НЕ НАЧИНАТЬ.
```

---
# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ
---

**TASK:** CLAUDE-WA-007 — RC-5: Projection correctness + pure inspection + safe TASK closeout.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION — 2026-10-04. DONE не объявлен; commit / push не выполнялись; **RC-6 NOT STARTED**.

**База:** HEAD `c46bee7` (commit 154 = принятый RC-4); код перед стартом совпадал с HEAD, полный Web Alarm 329/329.

**Что сделано:**
- **Projection.** Новый `web_alarm/projection.py` (`ProjectionService`):
  - `build` — чистая (без блокировок и записи) projection из authoritative stores: TaskStore, restore point, OperationStore, Resolver, RC-3 claims, RC-4 rollback. Checkpoint и события не читаются.
  - Позиция выводится из жизненного цикла, а не из указателей. Невозможные состояния → fail-closed blocker.
  - Детерминированные `source_fingerprint` и `projection_fingerprint`.
- **Валидация и rebuild checkpoint.**
  - `validate_checkpoint` различает `VALID / STALE / INCONSISTENT / LEGACY_UNVALIDATED / MISSING / CORRUPT`; подмена и md тоже проверяются, checkpoint никогда не authority.
  - Явный `rebuild_checkpoint` — единственный писатель projection, под TASK-lock.
  - State machine и OperationStore пересобирают checkpoint после своей записи; ошибка projection мутацию не отменяет.
- **Потребители.** Context Pack, `/tasks/{id}`, `/ui`, `/recover`, CLI `status` / `report` и RemoteEntry берут CURRENT и NEXT только из projection. Приоритет: rollback-сессия > авторитетная резолюция > stale-резолюция (нужна новая reconciliation) > advisory reconciliation > lifecycle / closeout gate.
- **Snapshot verify** стал чистым: без событий, checkpoint и `BLOCKED_PREPARE`, ошибка → 409 `snapshot_not_verified`.
- **CLI `checkpoint write`** выведен (exit 2). Вместо него — `checkpoint rebuild / validate`.
- **RC-4 факты помечены как исторические:** `facts_source=rollback_receipt`, `facts_as_of`, `verified_at`, `current_physical_state_asserted=false`.
- **Closeout gate.** Новый `web_alarm/closeout.py`:
  - чистый `inspect` (eligible, blockers, NEXT);
  - `complete` под операционным TASK-lock + новым `TaskStore.mutation_lock`, eligibility повторно доказывается под блокировками;
  - CLI `task complete` идёт через gate (код 3 при отказе), добавлен `task closeout`; server `GET /closeout`, `POST /complete`;
  - классификация консервативная, по контрактам RC-2/3/4.
- **Adversarial pass, исправлено внутри scope:**
  - Context Pack больше не делает второй расходящийся расчёт reconciliation;
  - незавершённый rollback стоит выше более свежей reconciliation другой операции;
  - ошибка projection не уходит из мутации как произвольное исключение;
  - `_touch_checkpoint` и записи TaskStore сериализованы.

**Файлы:**
- новые: `web_alarm/projection.py`, `web_alarm/closeout.py`, `test_web_alarm_projection.py` (32), `test_web_alarm_projection_concurrency.py` (3);
- изменённые: `context_pack.py`, `task_store.py`, `server.py`, `state_machine.py`, `cli.py`, `rollback_service.py`, `event_checkpoint_store.py`, `remote_entry.py`, `operation_store.py`, `models.py`, `__init__.py`;
- ожидания 5 прежних тестов (`cli`, `context_pack`, `state_machine`) изменены намеренно: они закрепляли «checkpoint = истина».

**Тесты:**
- RC-5 — 32/32, multiprocess — 3/3;
- RC-4 — 43/43, RC-3 — 20/20, RC-2 — 41/41;
- полный Web Alarm — **364/364 OK** (skip 1);
- compileall и `git diff --check` OK;
- мутационные probe: каждое сломанное свойство ловится;
- W без блокировок ломается (2 нарушения из 6), с gate — 0 нарушений.

**Живое storage (только чтение):** 136 файлов, хеш до и после совпал; WA-3.6 / WA-3.7 → `LEGACY_UNVALIDATED`, NEXT «TASK is COMPLETED».

**FINDING / PROPOSAL (вне scope, код не менял):**
- F1 — жизненный цикл операции и microtask после ADOPT / ABORT / отката не определён (V15). Closeout fail-closed с выходом через ABORT, нужно **DECISION**.
- F2 — переходы state machine не атомарны. Proposal: выполнять их под `TaskStore.mutation_lock`.
- F3 — **после принятия обязательно перезапустить процессы WEB-02** (старый код не читает новый checkpoint и не берёт новую блокировку).
- F4 — консервативные правила подтвердить: DONE блокирует, пустой plan блокирует.
- F5 — объём ответа `/tasks/{id}`.
- F6 — документация `22` / `23` / `24` — для verifier.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-007_RC5/rc5_report.md`; baseline и хеши — `baseline.md`, копии — `safety_copies/`.

## Правило круговорота

1. Следующую утверждённую TASK в БЛОК 1 переносит пользователь/координатор. До старта Claude перечитывает её полностью.
2. После фактического завершения Claude **сначала** копирует полную постановку в БЛОК 2, **затем** записывает factual closeout в БЛОК 3 со статусом только `RESULT READY / AWAITING INDEPENDENT VERIFICATION`.
3. Только если БЛОКИ 2–3 успешно сохранены, Claude сам очищает БЛОК 1 и оставляет короткий маркер `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Отдельное разрешение пользователя на эту очистку не требуется.
4. Если ротация прервалась, сначала reconciliation фактического файла; нельзя вслепую очищать БЛОК 1 или повторно переписывать БЛОКИ 2–3.
5. Незавершённая/PAUSED TASK не проходит completed-ротацию: её состояние сохраняется явно и не маскируется под результат.
6. Независимый verifier/ChatGPT проверяет код, тесты и evidence. После PASS он синхронизирует постоянную историю: `001`, `06`, нужный профильный журнал/реестр и другие реально затронутые канонические документы и фиксирует `DONE / VERIFIED`.
7. Новую TASK вставляют в пустой БЛОК 1 после требуемого verifier-closeout предыдущей; БЛОКИ 2–3 предыдущей TASK можно перезаписать следующей завершённой TASK только когда предыдущий подтверждённый результат уже закреплён в permanent history.
8. Долговременные технические наблюдения и метрики по Claude переносить в `27_Claude.md`, когда они действительно относятся к модели/лимитам/сети.
9. БЛОКИ 2–3 — оперативный handoff, а не замена append-only истории и независимой verification authority. Глобальный `000_Задачи для агента.md` имеет другую роль project-level router и Claude его автоматически не очищает.
