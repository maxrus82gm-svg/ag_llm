TASK: CLAUDE-WA-012
RC-6 — REPAIR #4A / PREPARING × ACCEPTED RECOVERY
STATUS: APPROVED FOR EXECUTION — DIRECT CHAT HANDOFF

ARCH CLASS: Web Alarm Workspace / Recovery Correctness
PRIMARY PROFILE: 23_Архитектура Web Alarm Workspace.md
SECONDARY PROFILE: 24_План реализации Web Alarm Workspace.md

BASELINE:
GitHub main, commit 164
47e5344ade57aaabca8ed5f782d5eb94f57ad464

PREVIOUS TASK:
CLAUDE-WA-011 / RC-6 Repair #4

==================================================
0. ВАЖНО: ИСТОЧНИК ЗАДАЧИ И ДОКУМЕНТАЦИЯ
==================================================

ЭТА ЗАДАЧА ПЕРЕДАНА НАПРЯМУЮ В CHAT.

Не ищи её в БЛОКЕ 1 документа
"Документация/000_Задачи Claude.md".

Не требуй переноса в БЛОК 1.
Не записывай её в БЛОК 1.
Не очищай и не используй БЛОК 1 для этой TASK.

Авторитетная постановка — НАСТОЯЩЕЕ CHAT-СООБЩЕНИЕ.

При этом обычные правила проекта СОХРАНЯЮТСЯ:

- прочитать 08_Старт.md;
- прочитать обязательный 18_Регламент сопровождения документации.md;
- сверить общий 000_Задачи для агента.md;
- прочитать нужные части 01, 23 и 24;
- использовать предыдущую задачу и отчёт Repair #4;
- соблюдать инструкции Alarm Task Session;
- делать safety copies перед изменениями;
- проводить adversarial review;
- вести factual report;
- сохранять непрерывность документации.

ИСКЛЮЧЕНИЕ ДЛЯ ЭТОЙ TASK:

В персональном документе "000_Задачи Claude.md"
добавь в БЛОК 2 отдельную последовательную запись:

"CLAUDE-WA-012 — RC-6 Repair #4A — FOLLOW-UP"

Сохрани там полную постановку настоящей задачи.

Важно:
не удалять, не заменять и не терять предыдущую
постановку CLAUDE-WA-011 / Repair #4.

Это продолжение предыдущей работы, а не переписывание её истории.

После выполнения сохрани фактический результат новой задачи
отдельной записью в БЛОКЕ 3, не уничтожая результат Repair #4.

Поскольку это прямой Chat-handoff, обычную ротацию
БЛОК 1 → БЛОК 2 здесь не выполнять.

До независимой проверки статус:
RESULT READY / AWAITING INDEPENDENT VERIFICATION.

==================================================
1. ПРИЧИНА ПОВТОРНОЙ ПРОВЕРКИ
==================================================

После завершения Repair #4 ChatGPT провёл независимый
static/architectural review GitHub commit 164.

Основные исправления Repair #4 признаны корректными
по проверенным путям:

- восстановление W1/W2 из PREPARING;
- settlement-supersession policy;
- защита RC-4 от второго физического rollback.

Однако обнаружен потенциальный сценарий, который не покрывается
имеющимися тестами Repair #4.

Это пока STATIC FINDING / REPRODUCTION REQUIRED,
а не объявленный подтверждённым runtime-дефект.

Нужно независимо проверить достижимость сценария.

==================================================
2. ПОТЕНЦИАЛЬНЫЙ ДЕФЕКТ
==================================================

Речь о пересечении двух механизмов:

A. восстановление прерванной подготовки restore point;

B. уже принятой Resolver recovery authority для операции
   той же microtask.

В коде commit 164:

OperationStore.begin() допускает создание INTENT operation
для существующей microtask без обязательного условия ACTIVE.

ManifestSnapshotStore.prepare_microtask() переводит microtask
в PREPARING до публикации restore point.

Resolver может принимать ABORT по актуальному evidence basis.

RecoveryCoordinator._classify() сначала обрабатывает
некоторые recovery states, включая ABORT_ACCEPTED,
а только позже проверяет состояние PREPARING
и назначает RECONCILE_PREPARATION.

При этом settlement ABORT обычно требует
перевода microtask в RECOVERY_REQUIRED.

Но PREPARING не входит в разрешённые исходные состояния
для такого settlement transition.

ВОЗМОЖНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ:

1. Microtask m1 находится в PLANNED.

2. Создаётся operation op1 / INTENT.

3. Начинается prepare restore point:
   m1 → PREPARING.

4. Процесс падает в W1 или W2.

5. До штатного RECONCILE_PREPARATION
   Resolver принимает ABORT для op1.

6. RC-6 строит Projection и видит
   authoritative ABORT_ACCEPTED.

7. RC-6 выбирает SETTLE_ABORT.

8. Settlement preflight пытается перевести
   PREPARING → RECOVERY_REQUIRED.

9. Переход отказывается, поскольку PREPARING
   не является допустимым исходным состоянием.

10. Вызов recover завершается FAIL_CLOSED.

11. При повторном recover выбирается тот же ABORT_ACCEPTED,
    и система может снова не дойти до
    RECONCILE_PREPARATION.

Результат — возможная постоянная recovery/liveness ловушка.

Физическая mutation при этом не разрешена,
поэтому речь прежде всего о correctness и liveness,
а не о подтверждённой записи без authority.

==================================================
3. ЧТО НУЖНО СДЕЛАТЬ
==================================================

СНАЧАЛА — ПРОВЕРКА.

На baseline 164 в изолированном временном storage:

- воспроизвести создание operation до ACTIVE;
- выполнить crash W1;
- получить accepted ABORT, если Resolver это допускает;
- вызвать recover несколько раз;
- перезапустить процесс и повторить recover;
- зафиксировать Projection, lifecycle, resolution и результат;

Затем аналогично проверить W2.

Также проверить противоположный порядок:

- сначала RECONCILE_PREPARATION;
- потом попытка принятия ABORT.

Если сценарий невозможно реализовать через публичные
серверные API, объясни, какой конкретный runtime-инвариант
это запрещает.

Не нужно искусственно исправлять несуществующий дефект.

Если сценарий подтверждён:

выясни root cause и выбери минимальное архитектурно
корректное исправление.

Не предписываю конкретный способ.

Возможные направления для анализа:

- изменение порядка recovery decisions;
- явная защита Resolver от неисполнимого accepted outcome;
- последовательное завершение PREPARING перед settlement;
- корректное моделирование промежуточного recovery state;
- другой способ, который обеспечивает тот же invariant.

НО:

Простого переставления RECONCILE_PREPARATION выше
SETTLE_ABORT может оказаться недостаточно.

После W1 статус может стать BLOCKED_PREPARE,
после W2 — BACKUP_VERIFIED.

Нужно проверить, способен ли последующий ABORT
корректно завершиться из этих состояний.

Не вводить новые переходы вслепую и не ослаблять
защиту lifecycle ради прохождения тестов.

==================================================
4. ОБЯЗАТЕЛЬНЫЕ ИНВАРИАНТЫ
==================================================

- Accepted recovery authority должна иметь корректный,
  достижимый путь завершения или явно описанный
  безопасный manual boundary.

- PREPARING не может давать normal mutation authority.

- Прерванная подготовка не должна оставаться
  вечной ловушкой восстановления.

- Опубликованный restore point нельзя переснимать
  или перезаписывать незаметно.

- Неопубликованный stage не должен приниматься
  за VERIFIED restore point.

- Accepted ABORT нельзя молча проигнорировать,
  потерять или превратить в normal execution.

- VERIFIED history не сдвигается назад.

- Сохранить Repair #4 settlement policy.

- Не допустить второго физического rollback.

- Repeated recover и fresh-process restart
  должны иметь согласованную семантику.

- Все опасные или неоднозначные состояния
  остаются fail-closed.

==================================================
5. ACCEPTANCE TESTS
==================================================

Минимальный набор:

A1. W1 + accepted ABORT до preparation reconciliation.

A2. W2 + accepted ABORT до preparation reconciliation.

A3. W1/W2 сначала reconciled, потом ABORT.

A4. Повторный recover без постоянного FAIL_CLOSED-loop.

A5. Restart между принятием ABORT и recovery.

A6. Crash во время нового recovery path.

A7. Concurrent prepare / recover / ABORT.

A8. Доказанный запрет mutation authority
    во всех промежуточных состояниях.

A9. Сохранение restore-point integrity и pre-state.

A10. Regression по Repair #4, #3, #2/#2A,
     RC-3, RC-4, Resolver, Projection, RC-6.

Если сценарий окажется невозможным:
вместо фиктивного исправления представить
отрицательные тесты, доказательство invariant
и точный анализ пути через API.

После собственных изменений:

- focused tests;
- полный Web Alarm test suite;
- целевые стресс-повторы гонок;
- собственный adversarial pass;
- compileall;
- git diff --check.

Все испытания только во временном storage.
Live Web Alarm storage не менять.

==================================================
6. ДОПОЛНИТЕЛЬНЫЙ ADVERSARIAL PASS
==================================================

Не ограничивайся приведённой последовательностью.

Проверь, не может ли аналогичная ловушка возникать
при другом сочетании:

- PREPARING + accepted recovery;
- BLOCKED_PREPARE + recovery;
- published snapshot + stale operation resolution;
- interrupted preparation + concurrent recovery;
- старые accepted resolution records после обновления policy.

При обнаружении дефекта внутри этого scope:
воспроизвести, исправить, добавить тест.

За пределы scope не выходить.
Другие findings фиксировать как FINDING / PROPOSAL / BLOCKER.

WA4-E НЕ НАЧИНАТЬ.

==================================================
7. DOCUMENTATION BLOCK — ОБЯЗАТЕЛЬНО
==================================================

Документацию продолжить вести по действующему
старому регламенту проекта.

Работа над RC-6 включала несколько последовательных
Repair-задач, поэтому важно не потерять архитектурную
и историческую связь между ними.

Зафиксируй:

- исходный finding независимого verifier;
- воспроизвёлся ли дефект;
- точную причину;
- выбранное архитектурное решение;
- изменения runtime;
- изменённые тесты;
- результаты проверок;
- residual risks;
- как новая работа связана с Repair #4;
- что теперь требуется для independent PASS RC-6.

Создай отдельный отчёт, например:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-012_RC6_REPAIR4A/
    rc6_repair4a_report.md

Оперативную фиксацию этой TASK выполни в БЛОКАХ 2 и 3,
как описано в разделе 0.

Отдельно выполни DOCUMENTATION IMPACT CHECK
по регламенту 18:

DOC IMPACT
CURRENT STATE IMPACT
ARCHITECTURE IMPACT
CONTEXT LIBRARY IMPACT
REGISTRY / ROUTING IMPACT
NEW DOCUMENT REQUIRED
CANONICAL OWNER
AFFECTED DOCUMENTS
CONTRADICTION CHECK
LOSS CHECK

Проверить документационную непрерывность:

23 — архитектурный владелец Web Alarm Workspace.
24 — план и статус этапов.
25 — профильный журнал Web Alarm Workspace.
05 — общий реестр задач.
06 — общий журнал выполнения.
001 — история выполненных задач Claude.
000 — project-level routing и персональный handoff.

Особое внимание:

Часть канонической документации пока отстаёт
от фактического состояния кода.

Не объявлять RC-6 DONE/VERIFIED только потому,
что исполнительские тесты зелёные.

Подготовить точный documentation delta:
что в каких документах должно измениться после PASS,
какие старые утверждения устарели,
какие статусы подтверждены, а какие ожидают verification.

Оперативные документы, task session и factual report
обновить сейчас в пределах полномочий исполнителя.

Постоянную каноническую историю и финальные статусы
синхронизирует independent verifier/координатор
после подтверждённого PASS, согласно регламенту 18.

Не терять и не переписывать предыдущие записи
Repair #1 / #2 / #2A / #3 / #4.

==================================================
8. ЗАВЕРШЕНИЕ
==================================================

После выполнения:

1. Подтверди, что запись этой Chat-задачи
   сохранена в БЛОКЕ 2 как отдельный FOLLOW-UP.

2. Запиши factual closeout в БЛОК 3
   отдельной записью.

3. Сохрани подробный технический отчёт в
   Alarm Task Session.

4. Сообщи:
   - подтверждён ли finding;
   - что исправлено или почему fix не нужен;
   - какие файлы изменены;
   - какие проверки и результаты;
   - какие документы требуют актуализации;
   - остаются ли блокеры перед WA4-E.

5. Итоговый статус:
   RESULT READY / AWAITING INDEPENDENT VERIFICATION.

Не ставить DONE/VERIFIED самостоятельно.

Commit/push выполняет пользователь,
если не будет отдельного прямого разрешения.

После этого остановиться.

Следующий шаг — независимая проверка ChatGPT
по новому GitHub commit.

WA4-E по-прежнему запрещён до independent PASS RC-6.
