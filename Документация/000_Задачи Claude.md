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

**Статус постановки:** выполнена Claude 2026-10-08 (RC-6 Repair #3; результат — в БЛОКЕ 3). Ниже — полная постановка из БЛОКА 1 дословно (хвостовые пробелы сняты), вместе с вводными словами координатора. Предыдущие постановки — RC-6 Repair #2 (+ #2A), повторная проверка RC-6, первая проверка RC-6 и CLAUDE-WA-007 / RC-5 — сохранены следом без изменений: ни одна из них не закреплена в `001`.

```text
Да, именно так и делаем: **задачу сначала фиксируем здесь в чате**, потом уже отдаём Claude. И я бы сейчас не дробил её на микрокоманды: даём ему найденные нами проблемы, обязательные инварианты и критерии приёмки, а **архитектурный способ исправления оставляем ему**. Это как раз наш нормальный сценарий.

Я бы зафиксировал следующую задачу так:

> **TASK: CLAUDE-WA-010 / RC-6 — REPAIR #3 / FINAL SAFETY CLOSURE**
>
> **Контекст**
>
> Продолжаем RC-6 после Repair #2 / #2A, baseline — GitHub `main`, commit `162` (`2f1f8780367fd5a2a2c44d10182002197f64e9bb`).
>
> Independent verification ChatGPT после commit 162 завершилась **FAIL**: основные исправления Repair #2/#2A действительно присутствуют и большая их часть выглядит корректно, но обнаружены оставшиеся safety / liveness / crash-consistency gaps.
>
> **WA4-E пока НЕ начинать.** Цель этой задачи — довести RC-6 до состояния, которое можно снова отдавать на независимую verification перед разрешением WA4-E. Это соответствует принятому протоколу проекта.
>
> ---
>
> **Главная цель**
>
> Закрыть оставшиеся подтверждённые проблемы RC-6 так, чтобы:
>
> - серверный mutation authority никогда не разрешал физическую mutation, когда lifecycle/recovery состояние microtask её запрещает;
> - recovery не мог необратимо застрять из-за гонки между `VERIFIED` и поздним recovery settlement;
> - `READY_FOR_EXECUTION` был привязан именно к полностью доказанному protected basis;
> - crash/IO interruption между связанными persistent writes не оставлял систему в состоянии, которое невозможно автоматически распознать и безопасно восстановить;
> - все изменения оставались fail-closed и не ослабляли уже работающие R1/R2/F-A/F-D/F-E.
>
> ---
>
> **Finding 1 — F-C / CRITICAL: mutation authority after ABORT**
>
> Подтверждён authority gap.
>
> После accepted `ABORT` / aggregate recovery disposition microtask может находиться в `RECOVERY_REQUIRED`, и Projection/NEXT запрещают normal mutation.
>
> Однако новая operation той же microtask потенциально может пройти цепочку:
>
> `OperationStore.begin()`
> → `TargetClaimService.acquire()`
> → `mutation_boundary()`
> → получить `AUTHORIZED`
>
> потому что mutation-authority path в основном проверяет состояние самой operation/claim/contract, но не обеспечивает эквивалентный **microtask-level lifecycle/recovery gate**.
>
> Это особенно критично перед WA4-E, поскольку будущий executor должен доверять именно `mutation_boundary`.
>
> **Обязательный инвариант:** если microtask находится в состоянии/disposition, где normal physical mutation запрещена, ни новая, ни старая operation не должна получить mutation authority до явного допустимого lifecycle/recovery решения.
>
> Не привязываемся к конкретной реализации gate — выбери архитектурно правильное место и способ, желательно с одним authoritative правилом, а не с несколькими расходящимися проверками.
>
> F-C изначально был известен как открытый gap: после ABORT NEXT запрещает mutation, но server authority всё ещё мог выдать claim новой operation.
>
> ---
>
> **Finding 2 — F-B / late ABORT vs VERIFIED**
>
> Repair #2A закрыл stale transition, когда recovery успевает первой.
>
> Но остаётся обратный порядок:
>
> 1. operation имеет accepted ABORT;
> 2. microtask ещё находится в статусе, из которого возможен `VERIFIED`;
> 3. `VERIFIED` успевает зафиксироваться раньше settlement lifecycle update;
> 4. ABORT settlement затем требует `RECOVERY_REQUIRED`;
> 5. система обнаруживает contradiction и fail-closes, но автоматического пути к согласованному состоянию нет.
>
> Уже существующий `SETTLEMENT_CONTRADICTION` полезен как safety barrier, но сам по себе не является recovery mechanism.
>
> **Цель:** определить и реализовать корректную семантику этой гонки. Нельзя откатывать VERIFIED stage физически или молча разрушать verification. Но система не должна попадать в бесконечно неразрешимое состояние только из-за порядка двух допустимых событий.
>
> Здесь особенно важен архитектурный анализ: возможно, правильное решение находится раньше — на момент допуска `VERIFIED`, на момент принятия settlement либо через дополнительный CAS/authority condition.
>
> ---
>
> **Finding 3 — R3 / READY proof basis incomplete**
>
> `RecoveryCoordinator._proof()` сохраняет в том числе:
>
> - `microtask_updated_at`;
> - `manifest_id`;
> - `restore_point_fingerprint`;
> - `target_set_fingerprint`;
> - operation/revision/resolution identity.
>
> Но independent review показал, что `_proof_matches()` напрямую не сравнивает весь сохранённый proof basis, в частности `restore_point_fingerprint` и `target_set_fingerprint`.
>
> Дополнительная проверка `source_fingerprint` существует, однако нужно доказать, что она действительно включает **весь смысловой basis**, который protected proof зафиксировал, а не только видимые идентификаторы вроде `manifest_id`.
>
> **Обязательный инвариант:** `READY_FOR_EXECUTION` должен возвращаться только для точно того restore point + affected target set + lifecycle/operation/resolution basis, которые были защищены target locks во время proof.
>
> Проверить также ABA-сценарий: состояние изменилось между proof и final classification, а затем вернулось к тем же поверхностным значениям.
>
> Этот вопрос специально оставался в independent checklist: соответствуют ли fingerprints реально locked target set и участвуют ли они в freshness.
>
> ---
>
> **Finding 4 — crash consistency A / activation**
>
> В `compare_and_set_microtask_status(..., activate=True)` связанное изменение persistent state выполняется несколькими записями:
>
> сначала `plan.current_microtask_id`,
> затем status microtask.
>
> При process/IO crash между этими writes возможно состояние:
>
> `plan.current_microtask_id = m2`,
> но `m2 != ACTIVE`.
>
> Projection сейчас рассматривает lifecycle как более authoritative, чем plan pointer, поэтому это не обязательно immediate corruption, но атомарность операции фактически не гарантирована.
>
> **Нужно решить:** является ли такое состояние допустимой crash state с детерминированным restart recovery либо activation должна иметь более сильную transactional/recoverable семантику.
>
> Не ограничиваем решение требованием «сделать обе записи одной атомарной операцией» — важен конечный invariant после crash/restart.
>
> Этот crash-window был отдельно обнаружен в independent review.
>
> ---
>
> **Finding 5 — crash/race consistency B / restore-point blocking**
>
> `_block_restore_point()` сначала может записать:
>
> `manifest.status = BLOCKED_PREPARE`
>
> а затем только попытаться conditional CAS microtask status.
>
> Если CAS отказывается из-за concurrent transition, manifest уже изменён.
>
> Возможен persistent mismatch вроде:
>
> `microtask = VERIFIED`
> `manifest = BLOCKED_PREPARE`.
>
> Repair #2A tests подтверждают, что stale transition не должен переписать новый microtask status, но этого недостаточно: нужно проверить и парную консистентность manifest/lifecycle state.
>
> **Цель:** stale/failing snapshot verification не должна портить restore point уже продвинувшейся/accepted microtask. При crash или race система либо сохраняет старый authoritative restore point, либо получает явно recoverable persistent state.
>
> Этот кандидат также был отдельно отмечен independent verification.
>
> ---
>
> **Что уже считается рабочим и не должно быть сломано**
>
> Repair #2/#2A уже дал существенные исправления:
>
> - historical/VERIFIED rollback protection;
> - single aggregated settlement disposition;
> - state-machine CAS против stale transition;
> - `RECOVERY_REQUIRED` перед destructive rollback APPLY;
> - общий multi-target lock ordering;
> - прекращение повторения одного `BLOCKED/REJECTED` RC-4 step в одном `recover()`.
>
> Сохрани эти свойства и добавь regression coverage на них.
>
> ---
>
> **Ожидаемая работа**
>
> Сначала самостоятельно перепроверь каждый finding на актуальном baseline и зафиксируй reproduction/root cause. Если какой-либо finding после более глубокого анализа окажется неверным — не исправляй его искусственно; объясни, какой существующий invariant уже его закрывает, и докажи это тестом/кодом.
>
> Затем спроектируй минимально достаточный Repair #3. Не нужно механически выполнять предложенные выше способы — важнее цель и единая архитектурная семантика.
>
> Добавь targeted regressions для каждого подтверждённого finding, включая adversarial/concurrency/crash-boundary cases там, где это практично.
>
> После repair:
>
> - focused tests;
> - все новые Repair #3 tests;
> - предыдущие Repair #2/#2A adversarial tests;
> - полный test suite;
> - разумные stress/repeat прогоны для race-тестов;
> - подтвердить, что live storage / реальные project files не были затронуты.
>
> Если найдёшь дополнительный blocker во время работы — не маскируй его ради зелёного suite; зафиксируй и либо включи в repair, если это небольшой связанный дефект, либо вынеси отдельным finding.
>
> ---
>
> **Артефакты / отчёт**
>
> Подготовить обычный AGENT REPORT с:
>
> - baseline commit;
> - reproduction каждого finding;
> - root cause;
> - выбранная архитектурная семантика;
> - changed files;
> - новые tests;
> - результаты focused/full/adversarial/stress прогонов;
> - safety/live-storage statement;
> - какие finding закрыты;
> - известные остаточные риски;
> - final recommendation: готов ли RC-6 снова к independent verification.
>
> Закоммитить изменения в GitHub обычным проектным способом.
>
> **Не объявлять RC-6 VERIFIED самостоятельно.**
>
> После твоего repair independent verification снова выполнит ChatGPT по GitHub. Только после independent PASS будет разрешён переход к WA4-E.
```

### Предыдущая постановка — CLAUDE-WA-009 / RC-6 Repair #2 (+ #2A) (сохранена)

**Статус постановки:** выполнена Claude 2026-10-06 (RC-6 Repair #2; результат — в БЛОКЕ 3). Ниже — полная постановка из БЛОКА 1 дословно (хвостовые пробелы сняты). Предыдущие постановки — повторная проверка RC-6, первая проверка RC-6 и CLAUDE-WA-007 / RC-5 — сохранены следом без изменений: ни одна из них не закреплена в `001`.

```text
TASK: CLAUDE-WA-009 / RC-6 — REPAIR #2

Название:
Verified-stage protection + single recovery owner +
READY proof binding + lock-order convergence

Статус:
READY / NOT STARTED

Исполнитель:
Claude

Независимый verifier после user commit/push:
ChatGPT / GPT-5.6 Sol

==================================================
0. МЕСТО TASK
==================================================

Это НЕ новый major stage.

Это Repair #2 внутри RC-6 после второй независимой
проверки commit 160.

RC-6:

VERIFICATION FAILED / REPAIR REQUIRED

WA4-E:

NOT STARTED / ЗАПРЕЩЁН ДО НОВОГО INDEPENDENT PASS

==================================================
1. BASELINE
==================================================

Перед фактическим стартом ОБЯЗАТЕЛЬНО:

1. определить настоящий GitHub main HEAD;
2. сверить local HEAD;
3. проверить dirty tree;
4. не доверять SHA из этой TASK без проверки;
5. не трогать .obsidian/*.

Ожидаемый runtime baseline:

commit 160
07c4667dd131b34d970e78488a68c2107913de85

Но использовать только фактически подтверждённый HEAD.

==================================================
2. ОБЯЗАТЕЛЬНО ПРОЧИТАТЬ
==================================================

Project docs:

- 08_Старт.md
- 000_Задачи для агента.md
- 000_Задачи Claude.md
- 000_Задачи ChatGPT.md
- 18_Регламент сопровождения документации.md
- 23_Архитектура Web Alarm Workspace.md
- 24_План реализации Web Alarm Workspace.md
- 33_Круглый стол - план исполнения.md

RC-6 executor:

- TASK_CHATGPT-WA-008_RC6/task.md
- rc6_report.md

Repair #1:

- TASK_CHATGPT-WA-008_RC6_REPAIR1/task.md
- rc6_repair1_report.md
- final_verification_v3.md

Independent re-verification:

- TASK_CLAUDE-RC6-REVERIFY/rc6_reverification.md
- все новые verifier probes и outputs.

==================================================
3. ГЛАВНАЯ ЦЕЛЬ
==================================================

Устранить:

R1
R2
R3

и в том же Repair закрыть дешёвые технические defects:

F-D
F-E

При этом НЕ менять самостоятельно global lifecycle policy
по F-A/F-B/F-C.

Для F-A/F-B/F-C:

только анализ + evidence + proposal.

Если correctness R1–R3 невозможно обеспечить
без изменения global lifecycle semantics:

STOP / DECISION REQUIRED.

==================================================
4. R1 — VERIFIED STAGE НЕЛЬЗЯ ФИЗИЧЕСКИ ОТКАТЫВАТЬ
==================================================

Подтверждённый сценарий:

m1 VERIFIED;
старая operation op1/m1 остаётся unresolved;
m2 ACTIVE;
Resolver принимает ROLLBACK(op1).

Текущий defect:

recover()
→ RC-4 успевает физически restore m1;
→ только ПОСЛЕ physical effect Coordinator замечает,
  что operation принадлежит VERIFIED historical microtask;
→ FAIL_CLOSED.

Это недопустимо.

Инвариант:

VERIFIED stage является protected historical boundary.

Recovery Coordinator не имеет права запускать
destructive recovery action для operation,
если operation.microtask_id уже VERIFIED,
если только отдельная архитектурная процедура
explicitly не разрешила rollback принятого stage.

Такой процедуры сейчас нет.

REPAIR REQUIREMENT:

До:

PREPARE_ROLLBACK
и тем более до APPLY_ROLLBACK

обязательно preflight:

- exact operation;
- operation.microtask_id;
- current authoritative microtask status;
- accepted resolution;
- operation revision;
- stage relationship.

Если operation microtask = VERIFIED:

ROLLBACK не выполняется.

Результат:

RECOVERY_BLOCKED / MANUAL_DECISION_REQUIRED

и:

- zero Workspace mutation;
- zero rollback session destructive progress;
- no claim acquisition for restore;
- no settlement write.

Важно:

этот preflight должен быть ДО первого RC-4 physical step,
а не после.

==================================================
5. R1 REGRESSIONS
==================================================

Обязательно:

R1-A:
m1 VERIFIED
+ unresolved op1/m1
+ m2 ACTIVE
+ accepted ROLLBACK(op1)

recover:

- files m1 unchanged;
- no restore receipt;
- no destructive RC-4 target transition;
- not READY;
- blocked/manual.

R1-B:
тот же сценарий после process restart.

R1-C:
m1 DONE but not VERIFIED.

Проверить отдельно:
можно ли recovery продолжать по существующей semantics
или требуется verification boundary.

Не расширять запрет VERIFIED механически на DONE,
если это ломает legit recovery.

R1-D:
historical VERIFIED m1 + later m2/m3
не должны менять результат.

==================================================
6. R2 — ОДНА MICROTASK НЕ МОЖЕТ ИМЕТЬ
ДВА КОНФЛИКТУЮЩИХ SETTLEMENT-OWNER
==================================================

Подтверждённый сценарий:

одна microtask;
две operations;
у одной ADOPT settlement;
у другой ABORT settlement.

Coordinator:

ADOPT требует DONE,
ABORT требует RECOVERY_REQUIRED.

Каждый recover:

DONE → RECOVERY_REQUIRED → DONE → ...
до step budget.

Следующий recover повторяет то же.

Это архитектурный конфликт:
два historical operation settlements одновременно
пытаются управлять одним lifecycle state.

REPAIR REQUIREMENT:

Top-level recovery должен агрегировать
recovery facts НА УРОВНЕ MICROTASK,
а не независимо исполнять settlement каждого op.

Для одной microtask определить canonical recovery disposition.

Минимальный принцип:

- completed/historical settlement не должен повторно
  управлять lifecycle;
- settlement, который уже выполнил свою administrative
  lifecycle часть, становится history;
- одновременно pending conflicting settlements
  должны fail closed как contradiction,
  а не переключать lifecycle.

Нельзя исправлять это простым:
"последний operation побеждает"
без доказанной authority semantics.

==================================================
7. R2 — SETTLEMENT ADMIN COMPLETION
==================================================

Нужен устойчивый критерий:

settlement pending administrative work

vs

settlement historical/completed.

Критерий не должен зависеть только от того,
совпадает ли текущий microtask status
с желаемым status конкретного settlement.

Иначе два settlements снова будут спорить.

Можно:

- вывести microtask-level recovery aggregate;
- добавить derived settlement administrative state;
- использовать существующие persistent facts.

Но НЕ вводить новую competing source of truth
без необходимости.

Если требуется новая persistent field/version:

обосновать и покрыть migration/backward compatibility.

==================================================
8. R2 REGRESSIONS
==================================================

Минимум:

R2-A:
same microtask:
op1 ADOPT settled/completed,
op2 ABORT pending.

Coordinator должен стабильно прийти
к одному terminal/manual state.

Повтор recover:

idempotent.

R2-B:
ABORT first, ADOPT historical.

R2-C:
две ADOPT settlements.

R2-D:
две ABORT settlements.

R2-E:
ADOPT + ROLLBACK settlement.

R2-F:
settlement already administratively complete
+ later operation settlement.

Никакого:

DONE ↔ RECOVERY_REQUIRED ping-pong.

Никакого:

step budget exhaustion только из-за
conflicting historical settlements.

==================================================
9. R3 — READY PROOF ДОЛЖЕН БЫТЬ ПРИВЯЗАН
К ТОЙ ЖЕ EXECUTION BASIS, КОТОРУЮ ВОЗВРАЩАЕТ READY
==================================================

Подтверждённая гонка:

Coordinator начинает READY proof для m1;
во время proof project position меняется;
m2 становится current;
цель m2 принадлежит foreign TASK.

После proof Coordinator rebuild projection,
видит m2 ACTIVE
и возвращает READY_FOR_EXECUTION,
хотя защищённый proof был выполнен для m1.

Это false READY.

REPAIR REQUIREMENT:

READY proof должен вернуть immutable proof identity:

минимум:

- task_id;
- microtask_id;
- projection/source fingerprint или equivalent basis;
- restore point identity;
- affected target set identity;
- resolution/operation identity, если recovery READY;
- lifecycle revision/updated_at или equivalent.

После proof и fresh Projection:

READY разрешён ТОЛЬКО если fresh execution basis
точно совпадает с proved basis.

Если current microtask changed:

НЕ READY.

Нужно заново классифицировать
и выполнить новый proof для новой microtask.

==================================================
10. R3 REGRESSIONS
==================================================

Обязательно real multiprocess/barrier:

R3-A:
proof m1;
concurrent lifecycle changes current -> m2;
m2 foreign-owned.

Never READY.

R3-B:
proof m1;
current changes -> m2;
m2 clean.

Первый proof НЕ может автоматически авторизовать m2.

Coordinator обязан:
reclassify -> new proof m2 -> только потом READY.

R3-C:
restore point changes между proof и return.

R3-D:
resolution identity changes.

R3-E:
operation revision changes.

R3-F:
same microtask,
но affected target basis changes.

==================================================
11. F-D — LOCK ORDER
==================================================

Independent verifier воспроизвёл:

RC-6 и RC-4 берут target locks
в различном порядке.

Две TASK с общими targets:
→ взаимное ожидание
→ Coordinator выходит только по timeout.

Не unsafe physical corruption,
но это реальный concurrency defect.

Repair #2 должен устранить расхождение,
ЕСЛИ это можно сделать локально и без смены
fundamental RC-4 semantics.

REQUIREMENT:

единый deterministic target lock ordering
для:

- RC-3;
- RC-4;
- RC-6 READY proofs;
- Resolver target proof paths.

Предпочтительно:

единый shared helper / key definition.

Не иметь:

одна подсистема sort by physical path,
другая sort by hash.

==================================================
12. F-D REGRESSION
==================================================

Real multiprocess test:

две operations / TASK;
два overlapping targets;
порядок перечисления противоположный.

Барьер после first target lock.

Ожидается:

- no deadlock cycle;
- один ожидает / получает conflict / продолжает безопасно;
- timeout не является normal resolution;
- no physical corruption.

==================================================
13. F-E — BLOCKED STEP НЕ ДОЛЖЕН ПОВТОРЯТЬСЯ
ДО STEP BUDGET
==================================================

Подтверждено:

RC-4 apply возвращает BLOCKED.

Coordinator игнорирует semantic result,
rebuilds same Projection
и повторяет APPLY до max_recovery_steps.

Получаются повторяющиеся ROLLBACK_BLOCKED events.

REPAIR REQUIREMENT:

mechanically terminal-for-now outcome шага:

BLOCKED
MANUAL_REQUIRED
или equivalent

должен остановить текущий recover invocation.

Не повторять тот же deterministic blocked step
без state change.

==================================================
14. F-E REGRESSION
==================================================

RC-4 apply -> BLOCKED.

Ожидается:

- ровно одна попытка за recover invocation;
- state = RECOVERY_BLOCKED / MANUAL;
- performed_steps отражает один blocked step;
- event count не растёт × step budget.

Repeated external recover может попробовать снова,
только если это соответствует contract,
но один invocation не spin'ит.

==================================================
15. F-A — STATE MACHINE CAS
==================================================

Finding:

ServerStateMachine.transition читает status
вне mutation lock,
затем пишет новый status внутри lock
без current-value CAS/recheck.

Реальный эффект:
concurrent verification может затереть
RECOVERY_REQUIRED от ABORT.

Repair #2:

НЕ МЕНЯТЬ это автоматически,
если исправление требует изменения
global lifecycle primitive.

Нужно:

- точный анализ;
- minimal proposed CAS semantics;
- affected callers;
- regression design;
- классификация:
  IN-SCOPE SAFE FIX
  или
  DECISION REQUIRED.

Если можно безопасно добавить recheck/CAS
без изменения transition graph и без ломки callers,
можно предложить пользователю,
но до explicit approval не менять.

==================================================
16. F-B — LATE ABORT / TASK STUCK
==================================================

Finding:

ABORT по already-closed/historical operation
может оставить TASK в permanent RECOVERY_REQUIRED.

Это безопасный fail-closed,
но operational exit отсутствует.

Repair #2:

не придумывать exit transition.

Нужно:

- доказать reachable scenarios;
- определить, должен ли Resolver вообще принимать
  такой late ABORT;
- предложить минимальные архитектурные варианты.

Статус:
DECISION REQUIRED,
если нужен новый lifecycle/replan mechanism.

==================================================
17. F-C — NEXT ЗАПРЕЩАЕТ МУТАЦИЮ,
НО SERVER AUTHORITY ЕЁ ЕЩЁ ДОПУСКАЕТ
==================================================

После ABORT:

Projection/NEXT говорит:
normal mutation forbidden.

Но verifier показал:

новая operation
в той же RECOVERY_REQUIRED microtask
может получить RC-3 claim
и mutation_authority=True.

Это особенно важно перед WA4-E.

Repair #2:

НЕ строить WA4-E.

Нужно:

- доказать authority gap;
- найти правильный слой enforcement:
  OperationStore?
  TargetClaimService?
  будущий WA4-E?
  lifecycle guard?
- дать recommendation.

Если safe локальный guard очевиден
и не меняет global lifecycle semantics:
описать как optional repair.

Без решения пользователя:
не расширять scope автоматически.

==================================================
18. VERIFIED STAGE INVARIANT
==================================================

Ввести явный regression-invariant:

microtask VERIFIED
=> RC-6 не выполняет destructive recovery
этой microtask.

Любая future exception
должна требовать отдельной explicit authority.

Это должно проверяться:

до RC-4 prepare/apply,
до target claims,
до physical write/delete.

==================================================
19. SINGLE MICROTASK RECOVERY DISPOSITION
==================================================

Coordinator не должен независимо
"исполнять все settlements" operations.

Для каждой microtask должен быть один
derived recovery disposition.

Если operation facts конфликтуют:

- deterministic safe aggregation;
или
- contradiction -> FAIL_CLOSED/MANUAL.

Не lifecycle ping-pong.

==================================================
20. READY PROOF TOKEN / BASIS
==================================================

Рекомендуемая форма
(название необязательно):

ReadyProof / proof_basis:

- task_id
- microtask_id
- lifecycle identity/revision
- manifest_id
- restore_point_fingerprint
- target-set fingerprint
- operation_id
- operation_revision
- resolution_id
- projection/source fingerprint

Для normal READY operation fields могут быть None.

Главное:

после proof return
нельзя использовать его для другой basis.

==================================================
21. НЕ ЛОМАТЬ REPAIR #1
==================================================

Обязательно сохранить:

B1:
historical settlement focus fix.

B2:
global foreign claim proof.

B3:
operation.microtask_id semantics
для RETRY/ABORT/ADOPT.

B4:
RC-4 restart semantics.

B5:
restore-point VERIFIED gate.

F1:
truthful RECOVERY_REQUIRED message.

F2:
PARTIAL/FAILED ownership preservation.

Additional Repair #1 edge:
persisted DRIFTED before finalize.

==================================================
22. TEST MATRIX
==================================================

Добавить постоянные tests минимум:

- R1 verified-stage rollback no mutation;
- R1 fresh-process;
- R2 mixed settlements idempotent;
- R2 repeated recover no ping-pong;
- R3 multiprocess basis-change race;
- R3 clean m2 requires a second proof;
- F-D lock-order multiprocess;
- F-E blocked step only once.

И сохранить все Repair #1 regressions.

==================================================
23. ADVERSARIAL PASS
==================================================

После обязательных tests самостоятельно атаковать:

- 3 operations same microtask;
- mixed ADOPT/ABORT/ROLLBACK facts;
- new Resolver action while old settlement cleanup pending;
- current microtask changes twice during READY proof;
- closeout after mixed history;
- crash between ROLLBACK preflight and RC-4 prepare;
- multiple rollback sessions;
- lock timeout/retry;
- lost response after blocked step;
- historical VERIFIED operation with newer recovery action.

Scope ограничивает изменения,
не анализ.

==================================================
24. FULL VERIFICATION
==================================================

Минимум:

- new Repair #2 tests;
- Repair #1;
- RC-6 focused;
- RC-6 adversarial;
- RC-6 concurrency;
- Projection + concurrency;
- Resolver + concurrency;
- RC-3 + concurrency;
- RC-4 + concurrency;
- StateMachine;
- Server;
- CLI.

После этого:

полный explicit test_web_alarm_*.py

python -B -m compileall -q web_alarm

git diff --check

==================================================
25. ORIGINAL VERIFIER PROBES
==================================================

Повторить:

- original RC-6 verifier probes;
- RC-6 re-verification probes,
  включая новые R1/R2/R3/F-D/F-E.

Не изменять старые probe
для получения PASS.

Если нужен новый ожидаемый result:
создать новый regression test,
а historical probe оставить evidence.

==================================================
26. LIVE STORAGE
==================================================

READ-ONLY ONLY.

Actual path определить из runtime.

До/после:

- file count;
- directory count;
- deterministic hash.

Mutation/crash/concurrency:
только temp storage.

==================================================
27. CODE SCOPE
==================================================

Ожидаемые области:

- recovery_coordinator.py
- projection.py
- rollback_service.py / shared lock helper
- возможно target_claim / target identity helper
- tests.

State machine / lifecycle authority:

не менять без отдельного решения,
кроме совершенно механического bug fix,
который НЕ меняет transition semantics.

==================================================
28. STOP / DECISION REQUIRED
==================================================

STOP, если R1–R3 требуют:

- нового global Microtask status;
- изменения Resolver action model;
- rollback of VERIFIED stage как новой feature;
- WA4-E implementation;
- scheduler;
- lease;
- global job system.

Не обходить hack'ом.

==================================================
29. TASK SESSION
==================================================

Создать:

Alarm/ALARM_TASK_SESSION/
TASK_CLAUDE-WA-009_RC6_REPAIR2/

Сначала:

- baseline;
- safety copies;
- original report/probe references.

Report:

rc6_repair2_report.md

==================================================
30. CARD PROTOCOL
==================================================

Сначала TASK зафиксирована в Chat.

После команды пользователя:

000_Задачи Claude.md
БЛОК 1
-> ACTIVE / IN PROGRESS.

После factual completion:

БЛОК 2
-> полная Repair #2 постановка.

БЛОК 3
-> factual Repair #2 result.

БЛОК 1
-> ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.

Старые RC-6 / Repair #1 /
re-verification records не стирать.

==================================================
31. STATUS AFTER IMPLEMENTATION
==================================================

Даже если всё зелёное:

только

RESULT READY / AWAITING INDEPENDENT VERIFICATION

Не:

DONE / VERIFIED.

Не commit / push.

==================================================
32. NEXT AFTER CLAUDE
==================================================

Пользователь commit/push Repair #2.

Затем:

ChatGPT / GPT-5.6 Sol
делает независимую verification
freshest GitHub commit.

ChatGPT НЕ участвует
в Repair #2 implementation.

Только после моего independent PASS:

RC-6 может стать DONE / VERIFIED.

И только затем:

NEXT = WA4-E.

==================================================
33. CURRENT NEXT SAFE ACTION
==================================================

СЕЙЧАС:

TASK зафиксирована только в Chat.

Никаких изменений кода/документов
до команды пользователя на запуск Claude.

После команды:

-> actual HEAD;
-> Claude БЛОК 1;
-> task-session;
-> baseline;
-> implementation Repair #2.
```

#### Дополнение к постановке — REPAIR #2A (2026-10-07)

Выполнено Claude 2026-10-07 как продолжение той же TASK; результат — дополнением в БЛОКЕ 3. Постановка из БЛОКА 1 дословно (хвостовые пробелы сняты):

```text
TASK: CLAUDE-WA-009 / RC-6 — REPAIR #2A
F-A CAS / lifecycle race closure

Статус:
READY / NOT STARTED

Это продолжение Repair #2.
Не новая major TASK.
WA4-E не начинать.

Цель:
закрыть остаточное окно R1, которое сам исполнитель
зафиксировал после Repair #2.

Проблема:

ServerStateMachine.transition читает текущий status,
затем позже под mutation_lock пишет новый status,
не перепроверяя, что status не изменился между чтением и записью.

Из-за этого возможна гонка:

RC-6 проверил:
operation.microtask_id всё ещё допустима для rollback;

параллельно state machine:
microtask -> VERIFIED;

RC-6 начинает RC-4 rollback уже VERIFIED stage.

Это оставляет R1 неполностью закрытым.

Требование:

не менять transition graph;
не добавлять новый lifecycle status;
не менять semantics допустимых переходов.

Добавить механический stale-write guard / CAS:

1. transition получает observed current status;
2. под существующим mutation_lock
   перечитывает authoritative current status;
3. если он уже отличается от observed basis:
   не перезаписывать его;
   fail closed / stale transition;
4. только если basis всё ещё совпадает —
   применять существующий разрешённый transition.

Обязательно проверить всех callers transition(),
чтобы новый stale failure обрабатывался корректно
и не создавал partial side effect.

Ключевой invariant:

ни один stale transition не может затереть
более новый RECOVERY_REQUIRED / VERIFIED /
другой authoritative lifecycle state.

Regression минимум:

A.
RC-6 rollback preflight vs concurrent
microtask -> VERIFIED.

Ожидается:
- VERIFIED сохраняется;
- destructive rollback не начинается;
- zero Workspace mutation.

B.
ABORT settlement -> RECOVERY_REQUIRED
vs concurrent stale verification transition.

Ожидается:
- RECOVERY_REQUIRED не затирается.

C.
два concurrent normal transitions
с одним observed source status.

Допустим только один,
второй получает stale/conflict.

D.
restart/replay:
stale transition после process delay
не переписывает новый persistent status.

E.
все существующие state-machine tests
и RC-6/RC-4 concurrency tests остаются зелёными.

После fix:

- Repair #2 tests;
- state machine;
- RC-6;
- concurrency;
- RC-4;
- full test_web_alarm_*.py;
- compileall;
- git diff --check;
- adversarial race;
- live storage read-only hash before/after.

F-B и F-C:
НЕ исправлять в этой подзадаче.
Оставить findings/proposals отдельно.

После успешного F-A closure:

статус всего Repair #2:
RESULT READY / AWAITING INDEPENDENT VERIFICATION.

Не commit / push.

Только после этого пользователь commit/push,
а ChatGPT выполняет независимую verification.
```

### Предыдущая постановка — CLAUDE-RC6-REVERIFY (сохранена)

**Статус постановки:** выполнена Claude 2026-10-06 (повторная независимая проверка RC-6 после Repair #1; результат — в БЛОКЕ 3). Ниже — полная постановка из БЛОКА 1 дословно (хвостовые пробелы сняты). Предыдущие постановки — первая проверка RC-6 и CLAUDE-WA-007 / RC-5 — сохранены следом без изменений: ни одна из них не закреплена в `001`.

```text
TASK: CLAUDE-RC6-REVERIFY
RC-6 — INDEPENDENT RE-VERIFICATION AFTER REPAIR #1

Статус:
READY / NOT STARTED

Роль:
независимый verifier / adversarial reviewer.

Это повторная независимая проверка RC-6
после CHATGPT-WA-008 / RC-6 — REPAIR #1.

НЕ продолжать WA4-E.
НЕ считать Repair report доказательством сам по себе.
Сначала REVIEW ONLY.
Не исправлять runtime-код молча.

==================================================
0. ПРИЧИНА RE-VERIFICATION
==================================================

Предыдущая independent verification RC-6:

VERIFICATION FAILED / REPAIR REQUIRED

Verifier:
Claude Opus 5.5

Были подтверждены блокеры:

B1 — completed ADOPT settlement навсегда захватывал recovery focus;

B2 — повторный recover мог давать false READY,
если после RETRY re-arm foreign TASK получал affected target;

B3 — Coordinator использовал TASK-current microtask
вместо microtask самой recovery-operation,
что давало false RETRY READY и half ABORT settlement;

B4 — Projection ошибочно считала начатый RC-4 rollback stale
после собственных rollback effects;

B5 — ACTIVE microtask могла получить READY
с повреждённым / NOT_VERIFIED restore point.

Также были findings:

F1 — ABORT -> RECOVERY_REQUIRED,
при этом normal lifecycle выхода из него сейчас нет;

F2 — PARTIAL/FAILED rollback нельзя безопасно
auto-close/release без explicit disposition.

После этого выполнен:

CHATGPT-WA-008 / RC-6 — REPAIR #1

==================================================
1. ACTUAL BASELINE — ОБЯЗАТЕЛЬНО СНАЧАЛА
==================================================

Не доверять SHA из этой TASK без проверки.

Сначала определить реальный latest GitHub main.

Ожидаемый commit после user push:

commit 160

SHA:
07c4667dd131b34d970e78488a68c2107913de85

Но verifier обязан самостоятельно:

1. определить настоящий GitHub HEAD;
2. сверить local HEAD с GitHub;
3. проверить dirty tree;
4. зафиксировать фактический baseline;
5. не начинать проверку старого commit,
   если main уже ушёл вперёд.

Commit 160 содержит Repair #1.

Baseline Repair #1:
commit 159
26111c9e39f8b9de90f1b91b6a75b74bd0412e6d

Проверять diff:
159 -> freshest Repair commit.

.obsidian/*:
не считать RC-6 runtime change;
не редактировать / не откатывать пользовательские изменения.

==================================================
2. ПРОЧИТАТЬ
==================================================

Обязательные project docs:

- Документация/08_Старт.md
- Документация/000_Задачи для агента.md
- Документация/000_Задачи ChatGPT.md
- Документация/000_Задачи Claude.md
- Документация/18_Регламент сопровождения документации.md
- Документация/23_Архитектура Web Alarm Workspace.md
- Документация/24_План реализации Web Alarm Workspace.md
- Документация/33_Круглый стол - план исполнения.md

Original RC-6:

- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/task.md
- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/rc6_report.md

Previous independent verification:

- Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-VERIFY/
  rc6_independent_verification.md

- probes/rc6_probes.py
- probes/rc6_probe_interrupted.py
- probe outputs
- full_regression.txt

Repair #1:

- Alarm/ALARM_TASK_SESSION/
  TASK_CHATGPT-WA-008_RC6_REPAIR1/task.md

- rc6_repair1_report.md

- final_verification_v3.md

- claude_probes_replay.txt

Repair report использовать только как карту изменений,
не как подтверждение correctness.

==================================================
3. ОСНОВНЫЕ RUNTIME-ФАЙЛЫ REPAIR
==================================================

Проверить минимум:

- web_alarm/projection.py
- web_alarm/recovery_coordinator.py
- web_alarm/rollback_service.py

Также читать связанные authority/lifecycle layers:

- web_alarm/operation_store.py
- web_alarm/operation_contract.py
- web_alarm/models.py
- web_alarm/task_store.py
- web_alarm/state_machine.py
- web_alarm/resolver_service.py
- web_alarm/reconciliation_service.py
- web_alarm/target_claim_service.py
- web_alarm/target_claim_store.py
- web_alarm/rollback_store.py
- web_alarm/manifest_store.py
- web_alarm/closeout.py

Public entry:

- web_alarm/server.py
- web_alarm/cli.py

==================================================
4. ОСНОВНАЯ ЦЕЛЬ RE-VERIFICATION
==================================================

Независимо доказать или опровергнуть:

Repair #1 реально устранил B1–B5,
не ослабив ранее принятые RC-2 / RC-3 / RC-4 / RC-5 invariants
и не создав новые false READY / unsafe cleanup / replay defects.

RC-6 после Repair должен:

- оставаться bounded Recovery Coordinator;
- использовать fresh Projection как canonical read model;
- не выполнять normal physical execution;
- не пересекать WA4-E boundary;
- быть restart/replay safe;
- быть claim-safe;
- быть Resolver-authority safe;
- не повторять physical effects;
- fail closed при неизвестной судьбе;
- давать truthful machine-readable READY.

==================================================
5. B1 — ОБЯЗАТЕЛЬНО ПОВТОРИТЬ
==================================================

Проверить:

ADOPT m1
-> settlement
-> m1 DONE
-> m1 VERIFIED
-> m2 ACTIVE

Ожидается:

old settlement остаётся history,
но НЕ захватывает top-level recovery.

recover(task):
-> работает с m2;
-> не пытается VERIFIED m1 вернуть в DONE.

Если m2 ACTIVE и все READY invariants доказаны:
-> READY_FOR_EXECUTION.

Также:

все microtasks VERIFIED
-> TASK_READY_TO_CLOSE.

Не:
FINISH_SETTLEMENT старой operation.

Дополнительно самостоятельно атаковать:

- settlement есть, claim release ещё не завершён;
- m1 VERIFIED раньше claim release;
- новая Resolver action появилась после historical settlement;
- несколько historical settlements разных operations.

==================================================
6. B2 — ОБЯЗАТЕЛЬНО ПОВТОРИТЬ
==================================================

Сценарий:

accepted RETRY
-> recover
-> microtask ACTIVE
-> READY

после этого foreign TASK acquire
на тот же affected target.

Повторный recover:

если foreign owner уже существует
во время final readiness proof:

НЕ READY.

Проверить:

- primary target;
- secondary affected target;
- alias / canonical physical target identity;
- foreign rollback owner;
- same operation compatible owner,
  если такая semantics допустима кодом.

READY proof должен читать
authoritative global RC-3 ownership,
а не только TASK-local Projection claims.

ВАЖНО:

RC-6 READY proof остаётся read-only.
Он не должен сам захватывать normal execution claim.

WA4-E позже всё равно обязан
повторно acquire/recheck authority.

==================================================
7. B3 — OPERATION MICROTASK AUTHORITY
==================================================

Повторить original defect:

m1 VERIFIED;
old op_1 относится к m1;
m2 ACTIVE;
accepted RETRY(old op_1).

Ожидается:

never READY old op_1.

Recovery action может управлять lifecycle
только operation.microtask_id.

TASK current microtask используется
для project position,
но не как replacement operation microtask status.

ABORT case:

m1 VERIFIED;
accepted ABORT old op.

Ожидается:

- fail closed / blocked до persistent settlement;
- recovery_settlement остаётся None;
- m1 остаётся VERIFIED;
- никакого half-settlement.

Атаковать crash windows:

- после settlement, до micro update;
- после micro update, до claim release;
- after claim release;
- concurrent verification между этими фазами.

==================================================
8. B4 — RC-4 RESTART SEMANTICS
==================================================

Это самая важная часть re-verification.

Projection не должна заменять RC-4
более слабым generic freshness rule.

Обязательно повторить ORIGINAL verifier probes:

A.
crash после первого RESTORED target,
до начала следующего.

Fresh process:
-> Projection = rollback operational state;
-> RC-4 resume;
-> no duplicate effect;
-> remaining targets restore once;
-> VERIFIED.

B.
T_APPLYING,
write landed,
process crash.

Fresh process:
-> current-byte reconcile;
-> no double write;
-> continue safely.

C.
T_APPLYING,
write NOT landed.

Fresh process:
-> reconcile;
-> exactly one restore;
-> continue safely.

D.
VERIFIED,
claims_released=false.

Fresh process:
-> release only;
-> no extra restore receipt/event.

==================================================
9. НОВЫЙ B4 EDGE ИЗ REPAIR SELF-REVIEW
==================================================

Executor после первоначального Repair нашёл
дополнительный restart defect.

Сценарий:

1. rollback target = T_APPLYING;
2. after restart bytes match neither preserved nor restore;
3. RC-4 persists T_DRIFTED;
4. process crashes BEFORE _finalize().

До дополнительного fix Projection могла
объявить эту session stale и close её.

Теперь verifier должен независимо доказать:

Fresh process:

-> Projection НЕ ROLLBACK_STALE_OPEN;
-> RC-4 получает session;
-> RC-4 выполняет current-byte proof;
-> finalize persisted DRIFTED outcome;
-> result PARTIAL или FAILED;
-> claims НЕ release;
-> Coordinator -> RECOVERY_BLOCKED/manual.

Отдельно:

тот же persisted DRIFTED crash
-> затем accepted ABORT.

Ожидается:

-> ROLLBACK_ABORTED_NEEDS_FINALIZE;
-> RC-4 только финализирует
   уже persisted target outcome;
-> untouched restore targets
   НЕ продолжаются;
-> PARTIAL/FAILED;
-> claims остаются;
-> ABORT не затирает unsafe rollback fact.

==================================================
10. VERIFIED RELEASE-PENDING + NEW AUTHORITY
==================================================

Проверить:

rollback VERIFIED
claims_released=false
-> later accepted ABORT

Ожидается:

RC-4 release only.

Не:
повтор restore.

После release:
accepted ABORT может стать operational
и settlement выполняется отдельно.

Попробовать также другие реально достижимые
new Resolver actions после VERIFIED rollback.

Не придумывать невозможные public Resolver transitions:
сначала доказать reachability через public API.

==================================================
11. F2 — PARTIAL / FAILED
==================================================

Проверить:

rollback = PARTIAL или FAILED.

Coordinator не должен:

- auto-close;
- auto-release ownership;
- скрывать физический partial outcome;
- автоматически выполнять newer RETRY/ADOPT/ABORT
  поверх unsafe open physical state.

Ожидается:

RECOVERY_BLOCKED
или MANUAL_DECISION_REQUIRED

и claims сохраняются
до explicit project-level disposition.

Проверить PARTIAL/FAILED:

- без новой Resolver action;
- с later ABORT;
- с возможной later superseding action,
  только если она реально достижима через public Resolver.

==================================================
12. F1 — ABORT / RECOVERY_REQUIRED
==================================================

Repair не вводит новый global lifecycle transition.

После ABORT:

microtask = RECOVERY_REQUIRED.

NEXT должен честно говорить:

- normal mutation запрещена;
- требуется explicit project-level
  replan/lifecycle decision.

Не должно быть обещания:

"просто создать новую operation"

если механического lifecycle пути для этого нет.

Verifier должен решить:

текущая формулировка truthful?

Если нет:
BLOCKER/FINDING.

Не добавлять новый transition самостоятельно.

==================================================
13. B5 — RESTORE POINT
==================================================

ACTIVE microtask + corrupt snapshot / manifest.

Никогда:

READY_FOR_EXECUTION.

Проверить:

- corrupted snapshot bytes;
- missing snapshot;
- corrupt manifest;
- invalid restore-point fingerprint;
- restore point changes between initial Projection and final READY proof.

Ожидается:

RECOVERY_BLOCKED / FAIL_CLOSED /
PROJECTION_BLOCKED

с zero Workspace mutation.

==================================================
14. TRUTHFUL READY CONTRACT
==================================================

Перед READY_FOR_EXECUTION механически доказать:

- TASK active;
- no projection blocker;
- exact execution microtask identified;
- exact lifecycle status executable;
- restore point valid;
- accepted recovery resolution current/fresh,
  если READY связан с recovery;
- operation belongs to same microtask;
- no unsafe/open rollback;
- no incompatible foreign ownership;
- no unresolved settlement admin work.

Verifier должен специально искать
любой path, который возвращает READY
без одного из этих доказательств.

==================================================
15. CONCURRENCY — ОБЯЗАТЕЛЬНО REAL MULTIPROCESS
==================================================

Повторить / расширить:

A.
recover vs recover — RETRY.

B.
recover vs recover — ROLLBACK.

C.
recover old RETRY
vs newer ABORT.

D.
recover READY proof
vs foreign primary target acquire.

E.
recover READY proof
vs foreign secondary target acquire.

F.
recover vs new operation.

G.
если возможно:
recover settlement completion
vs normal microtask verification.

Допустим race:

Coordinator доказал READY,
locks отпущены,
после этого появился foreign owner.

Это более поздняя race,
которую обязан ещё раз ловить WA4-E.

Недопустимо:

foreign owner уже существует
во время final protected READY proof
-> READY.

==================================================
16. REPLAY / LOST RESPONSE
==================================================

Проверить fresh-process replay:

- after ADOPT settlement;
- after micro update;
- before claim release;
- after claim release;
- rollback mid-restore;
- rollback after restore before event/receipt,
  если architecture позволяет такую точку;
- VERIFIED before release;
- DRIFTED before finalize;
- bounded coordinator step exhaustion.

Повтор recover не должен:

- повторить physical effect;
- создать второй rollback session;
- снять чужой claim;
- перескочить WA4-E boundary.

==================================================
17. PROJECTION HISTORY VS OPERATIONAL ATTENTION
==================================================

Проверить, что persisted history
не исчезает из operation data,
но не захватывает top-level NEXT.

Особенно:

- historical ADOPT settlement;
- historical ROLLBACK settlement;
- historical ABORT settlement;
- later accepted resolution;
- next microtask;
- all-verified closeout.

Никакой hidden second authority
в Coordinator.

==================================================
18. RESTORE / CLAIM LOCK ORDER
==================================================

Проверить deterministic target ordering
и отсутствие нового deadlock pattern:

- Resolver target set;
- manifest restore target set;
- RC-3 target locks;
- task lock / mutation lock order.

Особенно сравнить
RecoveryCoordinator READY proof
с existing Resolver/RC-3/RC-4 lock order.

Если найден потенциальный lock inversion:
BLOCKER или FINDING с reproduction/proof.

==================================================
19. ORIGINAL VERIFIER PROBES
==================================================

Обязательно запустить НЕИЗМЕНЁННЫМИ:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-VERIFY/probes/rc6_probes.py

и:

rc6_probe_interrupted.py

Не использовать сохранённый executor output
как замену собственного запуска.

==================================================
20. REPAIR-SPECIFIC TESTS
==================================================

Запустить:

test_web_alarm_recovery_coordinator_repair1.py

Но не считать его достаточным доказательством.

Verifier обязан придумать минимум
несколько собственных adversarial probes,
которых нет в Repair suite.

==================================================
21. ОБЯЗАТЕЛЬНЫЕ REGRESSION SUITES
==================================================

Минимум:

- RC-6 Coordinator;
- RC-6 adversarial;
- RC-6 concurrency;
- Repair #1;
- Projection;
- Projection concurrency;
- Resolver;
- Resolver concurrency;
- RC-3 claims;
- RC-3 concurrency;
- RC-4 rollback;
- RC-4 concurrency;
- State machine;
- Server;
- CLI.

Затем:

полный явный набор
test_web_alarm_*.py.

Также:

python -B -m compileall -q web_alarm

git diff --check

==================================================
22. LIVE STORAGE
==================================================

Live Web Alarm storage:

READ-ONLY ONLY.

Определить actual path из runtime code,
не доверять старой записи.

До / после verifier regression:

- file count;
- directory count;
- deterministic tree/file hash.

Никаких mutation/crash/concurrency probes
на live storage.

Все такие tests:
isolated temporary storage/workspace.

==================================================
23. ПРОВЕРИТЬ ACTUAL DIFF REPAIR
==================================================

Verifier обязан самостоятельно посмотреть
diff baseline Repair:

commit 159
26111c9e...

-> freshest Repair commit
(ожидается commit 160 / 07c4667d...)

Особенно runtime:

- web_alarm/projection.py
- web_alarm/recovery_coordinator.py
- web_alarm/rollback_service.py

Проверить, что Repair не:

- ослабил accepted Resolver freshness;
- создал shortcut вокруг RC-3 claims;
- создал новый rollback engine;
- изменил global lifecycle молча;
- позволил normal physical mutation;
- auto-close unsafe session;
- превратил Projection в write-path;
- ввёл глобальный server lock.

==================================================
24. НЕ ДЕЛАТЬ
==================================================

Не реализовывать:

- WA4-E;
- WA4-A;
- WA4-O;
- WA4-R;
- normal physical Executor;
- STARTED-before-write;
- automatic physical RETRY;
- Program/Stage scheduler;
- multi-model orchestration;
- lease/heartbeat;
- OS filesystem transaction;
- новый global Microtask transition.

==================================================
25. ЕСЛИ НАЙДЕН BLOCKER
==================================================

Сначала:

точный reproduction.

Затем:

- affected invariant;
- exact root cause;
- minimal repair scope;
- почему существующие tests не поймали;
- persistent state после failure;
- влияет ли это на старые RC-4/RC-5 invariants.

Статус:

VERIFICATION FAILED / REPAIR REQUIRED.

Не чинить runtime молча.

Если нужен простой test-only probe —
можно создать verifier evidence.

WA4-E не начинать.

==================================================
26. ЕСЛИ BLOCKER НЕ НАЙДЕН
==================================================

Только после independent PASS:

RC-6 = DONE / VERIFIED.

Verifier тогда может обновить
предусмотренные регламентом permanent closeout/history docs:

- global router;
- профильную историю Web Alarm;
- permanent status/route docs.

Но:

WA4-E самостоятельно НЕ начинать.

NEXT только:

WA4-E READY / NOT STARTED

или эквивалентный канонический route.

==================================================
27. REPORT
==================================================

Создать отдельную verifier session:

Alarm/ALARM_TASK_SESSION/
TASK_CLAUDE-RC6-REVERIFY/

Отчёт:

rc6_reverification.md

Обязательно включить:

- actual GitHub/local HEAD;
- diff reviewed;
- independent architecture findings;
- B1–B5 result matrix;
- F1/F2 judgement;
- original probe results;
- новые verifier probes;
- concurrency results;
- crash/restart results;
- focused test counts;
- full test count;
- compileall;
- diff-check;
- live storage before/after proof;
- PASS или FAIL;
- почему conclusion независим
  от ChatGPT Repair report.

==================================================
28. CARD PROTOCOL
==================================================

Эта TASK сначала зафиксирована в Chat.

Только после отдельной команды пользователя
она переносится в:

Документация/000_Задачи Claude.md
БЛОК 1.

На старте verification:

БЛОК 1:
CLAUDE-RC6-REVERIFY / ACTIVE.

После factual завершения:

БЛОК 2:
полная постановка re-verification.

БЛОК 3:
factual verifier result.

БЛОК 1:
очищается.

Не стирать исторические RC-5 / RC-6 records;
сохранить их ниже / в предусмотренной истории.

==================================================
29. ACCEPTANCE
==================================================

PASS только если verifier независимо доказал:

- B1 fixed;
- B2 fixed;
- B3 fixed;
- B4 fixed;
- B5 fixed;
- F1 truthful;
- F2 safe;
- no new false READY;
- no duplicate effect;
- no unsafe rollback close;
- no foreign claim release;
- no stale action execution;
- crash/restart safe;
- multiprocess convergence safe;
- RC-4 semantics preserved;
- full regression PASS;
- live storage unchanged;
- WA4-E not started.

==================================================
30. CURRENT NEXT SAFE ACTION
==================================================

СЕЙЧАС:

TASK только зафиксирована в Chat.

Никаких изменений документов,
никакого Remote,
никакого verifier execution
до команды пользователя.

После команды:

-> проверить actual HEAD;
-> перенести TASK в Claude БЛОК 1;
-> создать verifier task-session;
-> начать independent re-verification.
```

### Предыдущая постановка — RC-6 INDEPENDENT VERIFICATION (сохранена)

**Статус постановки:** выполнена Claude 2026-10-06 (независимая проверка RC-6; результат — в БЛОКЕ 3). Ниже — полная постановка из БЛОКА 1 дословно (хвостовые пробелы сняты). Постановка CLAUDE-WA-007 / RC-5 сохранена следом без изменений: RC-5 ещё не прошёл независимую приёмку и не имеет записи в `001`, поэтому по правилу карточки не перезаписывается.

```text
TASK: RC-6 INDEPENDENT VERIFICATION
CHATGPT-WA-008 — Project-level Recovery Closure

Статус:
READY / NOT STARTED

Роль:
независимый verifier / adversarial reviewer.
Не продолжать WA4-E.
Не доверять отчёту исполнителя без собственной проверки.

==================================================
1. СНАЧАЛА ФАКТИЧЕСКИЙ BASELINE
==================================================

2. Определить настоящий latest GitHub HEAD.
3. Сверить local HEAD с GitHub.
4. Проверить dirty tree.
5. Не доверять SHA из task/report без проверки.
6. Не трогать пользовательские .obsidian/*.

Проверять только самый свежий commit пользователя,
содержащий RC-6.

==================================================
2. ПРОЧИТАТЬ
==================================================

Обязательно:

- Документация/08_Старт.md
- Документация/000_Задачи для агента.md
- Документация/000_Задачи ChatGPT.md
- Документация/18_Регламент сопровождения документации.md
- Документация/23_Архитектура Web Alarm Workspace.md
- Документация/24_План реализации Web Alarm Workspace.md
- Документация/33_Круглый стол - план исполнения.md

RC-6:

- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/task.md
- Alarm/ALARM_TASK_SESSION/TASK_CHATGPT-WA-008_RC6/rc6_report.md
- final_regression_v2.txt

Не считать report доказательством сам по себе.

==================================================
3. КРИТИЧЕСКИЕ ФАЙЛЫ
==================================================

Проверить минимум:

- web_alarm/recovery_coordinator.py
- web_alarm/models.py
- web_alarm/operation_contract.py
- web_alarm/operation_store.py
- web_alarm/projection.py
- web_alarm/task_store.py
- web_alarm/target_claim_service.py
- web_alarm/rollback_service.py
- web_alarm/resolver_service.py
- web_alarm/server.py
- web_alarm/cli.py

Tests:

- test_web_alarm_recovery_coordinator.py
- test_web_alarm_recovery_coordinator_concurrency.py
- test_web_alarm_recovery_coordinator_adversarial.py
- test_web_alarm_projection.py
- test_web_alarm_resolver.py
- test_web_alarm_rollback.py
- test_web_alarm_rollback_concurrency.py
- test_web_alarm_server.py
- test_web_alarm_cli.py

==================================================
4. ГЛАВНЫЙ ВОПРОС
==================================================

Доказать или опровергнуть:

один RecoveryCoordinator может безопасно
довести persistent recovery одной TASK
до правильной границы:

READY_FOR_EXECUTION /
READY_FOR_VERIFICATION /
MANUAL_DECISION_REQUIRED /
RECOVERY_BLOCKED /
FAIL_CLOSED /
TASK_READY_TO_CLOSE /
TASK_COMPLETED,

не выполняя normal physical mutation,
которая принадлежит будущему WA4-E.

==================================================
5. ОСОБО АТАКОВАТЬ
==================================================

Не ограничиваться существующими тестами.

Попытаться сломать:

1. stale Resolver authority;
2. old RETRY → newer ABORT;
3. ADOPT между proof и settlement;
4. foreign claim на primary target;
5. foreign claim на secondary affected target;
6. recover vs recover;
7. recover vs new Resolver action;
8. recover vs new operation;
9. open rollback + ABORT;
10. open rollback + RETRY;
11. open rollback + ADOPT;
12. stale open rollback;
13. ABORT + T_APPLYING;
14. superseded/stale + T_APPLYING;
15. multiple open rollback sessions;
16. rollback VERIFIED but claims release interrupted;
17. crash/lost response after settlement before cleanup;
18. corrupt/stale checkpoint;
19. stale Recovery Report;
20. projection contradiction / false READY;
21. completed TASK;
22. closeout-eligible TASK;
23. bounded-loop exhaustion/replay;
24. process restart between meaningful phases.

Проверить, что:
- no duplicate physical effect;
- no unauthorized claim release;
- no silent rollback selection;
- no stale action execution;
- no false READY.

==================================================
6. ВАЖНЫЕ SEMANTICS
==================================================

RETRY:
- только administrative re-arm;
- zero normal Workspace mutation;
- actual effect остаётся WA4-E.

ADOPT:
- exact post-state proof;
- full affected-target protection;
- durable settlement;
- Operation VERIFIED + receipt;
- Microtask DONE;
- no repeated effect.

ABORT:
- durable settlement;
- forensic operation status не стирается;
- Microtask не становится VERIFIED.

ROLLBACK:
- только существующий RC-4;
- никакого второго restore engine;
- verified rollback ≠ normal operation success.

==================================================
7. ПРОВЕРКИ
==================================================

Обязательно независимо запустить:

- RC-6 focused integration;
- RC-6 adversarial;
- RC-6 concurrency;
- Resolver focused;
- RC-3/RC-4 relevant regression;
- Server/CLI;
- полный явный набор test_web_alarm_*.py;
- python -B -m compileall -q web_alarm;
- git diff --check.

Mutation/race tests:
только isolated temp storage.

Live WEB-02:
read-only.

==================================================
8. РЕЖИМ НЕЗАВИСИМОЙ ПРОВЕРКИ
==================================================

Сначала REVIEW ONLY.

Не исправлять код молча.

Если найден blocker:
- зафиксировать точный reproduction;
- объяснить root cause;
- указать минимальный repair scope;
- статус: VERIFICATION FAILED / REPAIR REQUIRED;
- WA4-E не начинать.

Если blocker не найден:
- статус: RC-6 DONE / VERIFIED;
- обновить предусмотренные verifier'ом
  permanent closeout/history документы;
- глобальный router перевести на следующий stage;
- NEXT = WA4-E, но сам WA4-E не запускать.

==================================================
9. ОТЧЁТ
==================================================

Нужен независимый отчёт:

- actual HEAD;
- inspected architecture;
- собственные findings;
- новые adversarial probes;
- focused/full test counts;
- live-storage read-only evidence;
- PASS или FAIL;
- почему вывод независим от executor report.

Не commit / push.

Не начинать WA4-E.
```

### Предыдущая постановка — CLAUDE-WA-007 / RC-5 (сохранена)

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

**TASK:** CLAUDE-WA-010 / RC-6 — REPAIR #3 / FINAL SAFETY CLOSURE (исполнитель Claude; независимый verifier — ChatGPT по GitHub).

- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE, не VERIFIED. **WA4-E NOT STARTED.**
- **Commit / push не выполнялись.** В постановке сказано «закоммитить обычным проектным способом»; по регламенту commit и push делает пользователь.
- **Baseline:** GitHub `main`, commit 162 = `2f1f8780367fd5a2a2c44d10182002197f64e9bb`; полный набор на baseline — 475 OK, skip 1.
- **Воспроизведение на 162:**
  - F1a–d — authority у новой, старой и соседней операции при RECOVERY_REQUIRED / отложенном ABORT / VERIFIED;
  - F2a/b — вечный FAIL_CLOSED в обоих порядках;
  - F3 — READY с proof `7abac391…` при фактическом `9e91d6ef…`;
  - F5 — microtask VERIFIED + manifest BLOCKED_PREPARE;
  - F4 — окно есть, но состояние уже восстановимо.
- **Семантика (граф переходов, статусы, модель Resolver и схемы записей не менялись):**
  - **F-C — один gate.** Новый `web_alarm/microtask_gate.execution_refusal`: мутация только для ACTIVE microtask, которая является текущим этапом и не несёт disposition ABORT/ROLLBACK (settled, принятого или открытой сессии RC-4). Gate общий для RC-3 `mutation_boundary` и READY / re-arm RC-6. Boundary держит TASK-lock → `mutation_lock` → target-lock, так что пока authority выдана, жизненный цикл заморожен.
  - **F-B.** VERIFIED допускается только без открытого recovery операций microtask: projection строится под TASK-lock + `mutation_lock`, CAS — в той же секции. Так приём ABORT и VERIFIED сериализованы. Решение после VERIFIED:
    - ADOPT/ABORT — административный settlement, этап остаётся VERIFIED;
    - ROLLBACK/RETRY — явная ручная граница, её закрывает явный ABORT.
  - **R3.** `_confirm_ready` под теми же блокировками заново выводит весь proof (fingerprint содержимого restore point, защищённое множество целей, microtask, ревизия, resolution) и строит финальную projection. READY только при полном совпадении, иначе новый проход классификации.
  - **F4.** Порядок «указатель, затем статус» — допустимое восстановимое состояние после краша (указатель не authority, повторная активация завершает). Плюс перепроверка «все предыдущие VERIFIED» под блокировкой.
  - **F5.** Блокировка restore point — проверка и запись под `mutation_lock`; устаревшая проверка его не трогает; краш между записями восстановим.
- **Найдено и закрыто попутно:**
  - **C1** — ABORT по FAILED/VERIFIED-операции давал вечный FAIL_CLOSED;
  - **n03** — поздний ABORT поверх существующего settlement давал вечный FAIL_CLOSED, теперь он завершается через `ABORT_OVER_SETTLEMENT` → RECOVERY_REQUIRED.
- **Файлы:**
  - новый `web_alarm/microtask_gate.py`;
  - изменены `target_claim_service.py`, `state_machine.py`, `recovery_coordinator.py`, `projection.py`, `task_store.py`, `manifest_store.py`, `operation_store.py`;
  - новый `test_web_alarm_recovery_coordinator_repair3.py` (34 теста).
- **Изменения существующих тестов:**
  - фикстуры authority теперь с ACTIVE microtask (RC-3, RC-4 ×2, projection) — ожидания те же;
  - фикстура «легаси-VERIFIED» для R1/B3;
  - ожидания изменены сознательно (новая семантика F-B) в трёх тестах: repair1 B3-ABORT, repair2 R2-противоречие для ABORT, CAS A1/A2. Подробно — §6.2 отчёта.
- **Проверки:**
  - Repair #3 — 34/34; на 162 падают 28 из 34;
  - фокусно 21 модуль — 322/322;
  - полный набор (44 модуля) — **511 OK, skip 1**, дважды;
  - стресс-повторы гоночных модулей — 21/21;
  - adversarial Repair #3 — 4/4 (в том числе 24 раунда «VERIFIED ↔ ABORT» на реальных процессах, оба порядка);
  - adversarial #2A — 5/5;
  - Repair #2 — 7 OK + a10 на легаси-форме 4/4;
  - исходные пробы RC-6 — exit 0 / 0;
  - compileall и `git diff --check` — OK.
- **Безопасность:** всё во временном storage; живое storage только на чтение — 136 / 41, хеш до = после (`5961c00c…7cd2`).
- **Дополнительно / остаточное:**
  - **FINDING (не исправлен, DECISION REQUIRED):** краш при подготовке restore point оставляет microtask PREPARING без выхода в workflow. Это безопасно (мутации нет), но выход только ручной. Proposal — путь «возобновить подготовку»;
  - поздний ADOPT/ROLLBACK поверх существующего settlement (одно поле settlement) — дизайн WA4-E;
  - целостности restore point в gate RC-3 нет (её доказывает READY RC-6; proposal для WA4-E);
  - legacy CLI WA-1 — WA4-R;
  - исторические пробы n02 / n03 / n19 / a10 падают на своей фикстуре, которую теперь отклоняет state machine; инварианты соблюдены.
- **Рекомендация:** RC-6 готов снова к независимой проверке. NEXT — commit / push пользователем → проверка ChatGPT → только после PASS RC-6 = DONE / VERIFIED → WA4-E.
- **Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-010_RC6_REPAIR3/rc6_repair3_report.md`.

---

### Предыдущий результат — CLAUDE-WA-009 / RC-6 Repair #2 (+ #2A) (сохранён: независимая проверка ChatGPT после commit 162 завершилась FAIL, в `001` не переносился)

**TASK:** CLAUDE-WA-009 / RC-6 — REPAIR #2 (исполнитель Claude; независимый verifier — ChatGPT).
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION (2026-10-06). Не DONE / VERIFIED. **WA4-E NOT STARTED.** Commit / push не выполнялись.

**Baseline:** GitHub `main` = локальный HEAD = commit 161 `e551b91`; runtime = commit 160 (161 — только документация verifier).

**Исправлено:**
- **R1** — RC-6 больше не откатывает VERIFIED-этап (и вообще не текущий). Шаги, ведущие к разрушительному откату, в projection получают состояние `ROLLBACK_STAGE_PROTECTED`, а координатор перед RC-4 `prepare` / `apply` повторно проверяет это под блокировками → `RECOVERY_BLOCKED` без записи, без сессии и без claims. Откат текущего DONE-этапа работает как прежде.
- **R2** — settlement всех операций microtask сводятся в одно решение: есть ABORT / ROLLBACK → `RECOVERY_REQUIRED`, только ADOPT → `DONE`. Учитываются только текущие settlement. Пинг-понга нет, повторный `recover` ничего не пишет. RETRY поверх ABORT соседа не поднимает microtask в ACTIVE. VERIFIED-microtask с ABORT → `SETTLEMENT_CONTRADICTION` без записи.
- **R3** — READY выдаётся только при неизменной `source_fingerprint` и совпадающей идентичности proof. Иначе новый proof для нового базиса. В результате появилось поле `ready_proof`.
- **F-D** — общий порядок блокировок целей по `target_hash` (хелпер в `target_claim_store`) для RC-6 и RC-4.
- **F-E** — шаг, отклонённый RC-4 (BLOCKED / REJECTED), не повторяется в том же вызове → `RECOVERY_BLOCKED` / `RECOVERY_STEP_REFUSED`.

**Файлы:**
- `recovery_coordinator.py`, `projection.py`, `target_claim_store.py`, `rollback_service.py` (только `_lock_targets` через хелпер);
- новый `test_web_alarm_recovery_coordinator_repair2.py` (24 теста). Ожидания существующих тестов не менялись.

**Проверки:**
- Repair #2 — 24/24; на исходном runtime 20 из 24 падают (чувствительность);
- фокусно — 245/245; полный набор — **463 OK** (skip 1); compileall и `git diff --check` OK;
- исходные probe — exit 0 / exit 0;
- probe повторной проверки: R1–R3, F-E — OK. Остались n02 / n02b (F-A, вне scope) и n15 (артефакт барьера, заменён постоянным тестом F-D);
- adversarial — 8/8 OK;
- живое storage только на чтение, хеш до и после одинаковый.

**F-A / F-B / F-C — только анализ, код не менялся:**
- F-A — CAS в state machine: безопасная правка, но нужно одобрение пользователя; закроет и остаточное окно R1;
- F-B — Resolver принимает действия по операциям с settlement / VERIFIED-этапа → **DECISION**;
- F-C — проверка жизненного цикла нужна в `mutation_boundary` (RC-3) и в WA4-E → **DECISION**.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/rc6_repair2_report.md`. Baseline — `baseline.md`, копии — `safety_copies/`, probe — `probes/`.

**NEXT:** commit / push пользователем → независимая проверка ChatGPT → только после PASS RC-6 = DONE / VERIFIED и NEXT = WA4-E.

**Дополнение — REPAIR #2A (2026-10-07), F-A CAS / закрытие окна R1:**
- **Статус всего Repair #2 (с #2A):** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE. **WA4-E NOT STARTED.** Commit / push не выполнялись; Repair #2 тоже ещё не закоммичен (HEAD = 161).
- **Почему одного CAS мало.** Гонка «RC-6 проверил этап → state machine перевёл его в VERIFIED → RC-4 откатил» — не устаревшая запись: статус DONE не менялся, и CAS бы её пропустил. Поэтому закрытие из двух частей, без новых статусов и переходов:
  1. все переходы state machine стали compare-and-set: новый `TaskStore.compare_and_set_microtask_status` под `mutation_lock`; устаревший переход → обычный `TransitionRejected` / 409, ничего не пишется; добавлен необязательный `expected_status` (библиотека и сервер); активация переносит указатель текущей microtask в той же блокировке; BLOCKED_PREPARE при испорченном snapshot и подготовка через state machine тоже идут через CAS;
  2. перед разрушительным apply координатор в том же защищённом участке, где доказывает этап, переводит microtask в RECOVERY_REQUIRED (её статус после ROLLBACK settlement). Выходов из него у state machine нет, а устаревший `DONE → VERIFIED` отклоняется — во время отката этап не может стать VERIFIED.
- **Файлы:** `task_store.py`, `state_machine.py`, `manifest_store.py`, `recovery_coordinator.py`, `server.py`; новый `test_web_alarm_state_machine_cas.py` (12 тестов). Граф переходов и ожидания существующих тестов не менялись.
- **Проверки:**
  - CAS — 12/12 (на коде до #2A 11 из 12 падают); фокусно — 278/278; финальный полный набор — **475 OK** (skip 1); compileall и `git diff --check` OK;
  - adversarial #2A — 5/5; adversarial Repair #2 — 8/8; исходные probe — exit 0 / 0;
  - живое storage только на чтение, хеш не изменился.
- **Честно:**
  - два предыдущих полных прогона дали по одному разному редкому падению старых race-тестов (RC-4 FAILED, RC-5 `CloseoutError`). Это sharing violation при `os.replace` на Windows — безопасный третий исход, который тесты не учитывают; диагностика 40 + 24 раунда чистая, пути не затронуты #2A → FINDING / proposal;
  - probe n02 / n02b перехватывают старую слепую запись и гонку больше не воспроизводят — её покрывают постоянные тесты A2 и B.
- **Вне scope:** F-B, F-C (не менялись); legacy CLI `snapshot prepare` / `restore` — WA4-R.
- **Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/repair2a/rc6_repair2a_report.md`.

---

### Предыдущий результат — CLAUDE-RC6-REVERIFY (сохранён: проверка завершилась FAIL, в `001` не переносилась)

**TASK:** CLAUDE-RC6-REVERIFY — повторная независимая проверка RC-6 после Repair #1 (CHATGPT-WA-008). Роль Claude — независимый verifier.
**Статус:** RESULT READY — вердикт **VERIFICATION FAILED / REPAIR REQUIRED** (2026-10-06). **WA4-E NOT STARTED.** Commit / push не выполнялись; permanent history и глобальный router не менялись (по постановке — только при PASS).

**Baseline:** GitHub `main` = локальный HEAD = commit 160 `07c4667`; runtime-код совпадает с HEAD; diff 159 → 160 прочитан полностью.

**Независимые проверки:**
- Repair #1 — 21/21; фокусно (RC-6, projection, Resolver, RC-3, RC-4, state machine, server, CLI) — 221/221;
- полный набор — **439 OK** (skip 1);
- compileall и `git diff --check` OK;
- исходные probe без изменений — exit 0 / exit 0;
- 23 новых probe, часть — на реальных процессах и с `os._exit`;
- живое storage только на чтение: 136 / 41, хеш до и после одинаковый; `recover` на WA-3.6 / 3.7 → `TASK_COMPLETED` без шагов.

**B1–B5:**
- B1, B2, B4, B5 в исходных сценариях устранены;
- B3 исправлен для RETRY / ABORT / ADOPT, но не для ROLLBACK (см. R1);
- F1 — формулировка правдива, но механически не обеспечена; F2 — безопасно.

**Новые блокеры:**
- **R1** — `recover` физически откатывает уже VERIFIED-этап. Accepted ROLLBACK для старой операции m1 при ACTIVE m2 → RC-4 восстанавливает файлы m1; settlement отказывает только после этого. Нарушен инвариант 5. Причина: для ROLLBACK нет проверки статуса microtask до PREPARE / APPLY.
- **R2** — две операции одной microtask с settlement ADOPT и ABORT: `recover` бесконечно переключает её DONE ↔ RECOVERY_REQUIRED (до 8 записей за вызов), итог FAIL_CLOSED по бюджету; ABORT-microtask может остаться DONE.
- **R3** — READY возвращается для microtask, по которой защищённая проверка не выполнялась (узкая гонка, воспроизведена двумя процессами).

**FINDINGS (не блокеры):**
- F-A — переход state machine без CAS затирает RECOVERY_REQUIRED после ABORT (давний F2 из RC-5);
- F-B — поздний ABORT по уже закрытой операции навсегда заклинивает TASK (fail-closed) → **DECISION**;
- F-C — запрет мутации после ABORT не обеспечен: новая операция получает claim и `mutation_authority` → вход для WA4-E / **DECISION**;
- F-D — разный порядок блокировок целей в RC-6 и RC-4 → взаимная блокировка двух TASK до таймаута (самокоррекция прошлого отчёта);
- F-E — BLOCKED от RC-4 не останавливает цикл: 8 повторов за вызов;
- F-F — `PROJECTION_VERSION` не поднят; F-G — 409 и перезапуск WEB-02 (перенесено).

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-REVERIFY/rc6_reverification.md`. Probe и выводы — `probes/`, регрессия — `full_regression.txt` и `focused_regression.txt`, baseline — `baseline.md`.

**NEXT:** RC-6 Repair #2 (R1–R3, плюс F-D / F-E) исполнителем RC-6 → повторная независимая проверка; решения по F-A, F-B, F-C.

---

### Предыдущий результат — RC-6 INDEPENDENT VERIFICATION (сохранён: проверка завершилась FAIL, в `001` не переносилась)

**TASK:** RC-6 INDEPENDENT VERIFICATION — CHATGPT-WA-008 (Project-level Recovery Closure). Роль Claude — независимый verifier.
**Статус:** RESULT READY — вердикт **VERIFICATION FAILED / REPAIR REQUIRED** (2026-10-06). **WA4-E NOT STARTED.** Commit / push не выполнялись; permanent history и глобальный router не менялись (по постановке они обновляются только при PASS).

**Baseline:** GitHub `main` = локальный HEAD = commit 158 `5d40e49`; runtime-код совпадает с HEAD.

**Независимые проверки:**
- RC-6 focused + adversarial + concurrency — 35/35;
- Resolver — 25/25;
- RC-3/RC-4 — 63/63;
- Server/CLI — 19/19;
- Projection — 50/50;
- **полный набор — 416/416 OK** (skip 1);
- compileall и `git diff --check` OK;
- живое storage только на чтение: `recover` на WA-3.6/3.7 → `TASK_COMPLETED` без шагов, хеш дерева до и после одинаковый.

**Блокеры** — собственные probe на временном storage, в тестах исполнителя не покрыты:
- **B1** — settled-операция навсегда остаётся фокусом. После штатного ADOPT → verify m1 → m2 ACTIVE `recover` всегда FAIL_CLOSED (пытается вернуть VERIFIED m1 в DONE), NEXT застревает, `TASK_READY_TO_CLOSE` недостижим.
- **B2** — ложный READY при повторе: чужая TASK взяла claim на основную цель после re-arm, а `recover` всё равно даёт `READY_FOR_EXECUTION`.
- **B3** — решения по microtask принимаются по lifecycle-current, а не по microtask операции:
  - ложный READY для RETRY операции уже VERIFIED microtask;
  - ABORT такой операции сначала записывает settlement, потом падает → вечный FAIL_CLOSED.
- **B4** — прерванный собственный RC-4 rollback считается «stale»:
  - без цели в полёте координатор закрывает откат на полпути (одна цель не восстановлена);
  - с целью в полёте — `RECOVERY_BLOCKED`;
  - штатный resume RC-4 недостижим.
- **B5** — ложный READY при испорченном restore point под ACTIVE microtask (нарушен инвариант 4).

**FINDINGS (не блокеры):**
- F1 — ABORT ведёт в тупик: у RECOVERY_REQUIRED нет выходов → **DECISION REQUIRED**.
- F2 — авто-close PARTIAL/stale-сессий снимает claims до решения человека → нужна policy.
- F3 — часть исключений выходит из `recover` как есть; неизвестная TASK → 409.
- F4 — самоотчёт: в RC-5 lifecycle NEXT не учитывает испорченный restore point (та же дыра, что B5).

**Подтверждено без замечаний:** RETRY без физической записи; гонка «старый RETRY → новый ABORT»; чужой claim при первом re-arm / ADOPT; multiple-open / superseded in-flight → блок; прерванный release после VERIFIED; идемпотентность settlement; бюджет шагов; corrupt checkpoint и stale Recovery Report.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-VERIFY/rc6_independent_verification.md`. Воспроизведения — `probes/` (скрипты и выводы), полная регрессия — `full_regression.txt`.

**NEXT:** repair RC-6 (B1–B5 с regression-тестами) исполнителем RC-6 → повторная независимая проверка; решения по F1/F2.

---

### Предыдущий результат — CLAUDE-WA-007 / RC-5 (сохранён: независимая приёмка RC-5 отложена пользователем, записи в `001` нет)

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
