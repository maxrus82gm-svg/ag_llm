# Постановка — CLAUDE-WA-013 / RC-6 Repair #4B (прямой Chat-handoff)

Получена в чате «Сервер Web06» 2026-10-08, подтверждена пользователем его словами («вот тебе еще одна задача»). БЛОК 1 карточки по постановке не используется. Текст дословно, хвостовые пробелы сняты:

```text
TASK: CLAUDE-WA-013
RC-6 REPAIR #4B — PRE-EXECUTION ABORT × SIBLING ROLLBACK
STATUS: APPROVED FOR EXECUTION — DIRECT CHAT HANDOFF
ARCH CLASS: Web Alarm Workspace / Recovery Safety
PRIMARY PROFILE: `23_Архитектура Web Alarm Workspace.md`
SECONDARY PROFILE: `24_План реализации Web Alarm Workspace.md`
Baseline: GitHub `main`, commit 165
`32bdf9635afcf81a9e6f1090a3bcba54b907c126`
Previous TASK: `CLAUDE-WA-012 / RC-6 Repair #4A`
0. ВАЖНО — ЗАДАЧА ПЕРЕДАНА В CHAT
Это прямое задание от пользователя через ChatGPT.
Не искать постановку в БЛОКЕ 1 документа `000_Задачи Claude.md`. Не записывать её туда, не очищать БЛОК 1 и не требовать предварительного переноса.
Авторитетный источник этой TASK — настоящее сообщение в чате.
Обычный проектный протокол сохраняется:

* `08_Старт.md` → `18_Регламент сопровождения документации.md` → глобальный `000_Задачи для агента.md` → `01` → профиль `23/24`.
* Использовать предыдущие отчёты Repair #3, #4 и #4A.
* Следовать инструкциям `Alarm/ALARM_TASK_SESSION/00_INSTRUCTION.md`.
* Перед изменением существующих файлов создавать safety copies.
* Все испытания выполнять исключительно в изолированном временном storage.
* Выполнить собственный adversarial pass.

Фиксация в персональной карточке:
В БЛОК 2 добавить отдельную последовательную FOLLOW-UP запись `CLAUDE-WA-013 / Repair #4B` с полной постановкой из чата. Сохранить все предыдущие записи Repair #4 и #4A без потерь.
После фактического выполнения добавить самостоятельный factual result в БЛОК 3, сохранив старые результаты.
Обычная ротация через БЛОК 1 для этой TASK не применяется.
1. Основание независимой проверки
ChatGPT выполнил независимый GitHub-only review коммита 165.
Основные исправления Repair #4A прошли статическую проверку по заявленным сценариям:

* W1/W2 + accepted ABORT;
* восстановление PREPARING перед settlement;
* устранение постоянного FAIL_CLOSED в проверенных pre-execution состояниях;
* ручная граница для ADOPT/ROLLBACK/RETRY.

Однако обнаружен дополнительный потенциальный safety-блокер, связанный с несколькими операциями одной microtask.
Статус находки: STATIC FINDING / RUNTIME REPRODUCTION REQUIRED.
Реальное нарушение ещё не подтверждено экспериментом. Твоя первая задача — попытаться воспроизвести его либо доказать невозможность.
2. Подозреваемый дефект
Repair #4A разрешил settlement ABORT для microtask, которая никогда не была ACTIVE.
При этом RC-6 переводит её:
`PLANNED / BACKUP_VERIFIED / READY / BLOCKED_PREPARE → RECOVERY_REQUIRED`
Это защищённая ручная граница.
Но старый механизм RC-4 рассматривает `RECOVERY_REQUIRED` как статус, из которого разрешена подготовка к физическому rollback.
Возникает вопрос: не позволяет ли новая семантика ABORT ошибочно считать никогда не исполнявшуюся microtask пригодной для физического отката?
Проверяемая последовательность

1. Создать microtask `m1`, которая ещё никогда не переходила в `ACTIVE`.
2. Подготовить её restore point штатным способом.
3. Создать две операции одной microtask:
   * `op1`;
   * `op2`.
4. Принять `ABORT` для `op1`.
5. Через `RecoveryCoordinator.recover()` завершить его settlement.
6. Подтвердить, что `m1` стала `RECOVERY_REQUIRED`, хотя ни разу не была `ACTIVE`.
7. Для `op2` создать достижимое reconciliation evidence, позволяющее Resolver принять `ROLLBACK`. Для этого проверить реальный partial-known-state сценарий с несколькими targets.
8. Попытаться выполнить ROLLBACK по `op2`.
9. Проверить, не проходят ли RC-6 preflight, RC-4 prepare/apply и физическое восстановление файлов без доказательства предыдущей активации microtask.

Почему возникло подозрение
В commit 165:

* `RecoveryCoordinator._settlement_rule()` разрешает pre-execution ABORT → RECOVERY_REQUIRED.
* `_rollback_stage_preflight()` считает RECOVERY_REQUIRED допустимым исходным статусом для rollback apply.
* `Projection.rollback_stage_protected()` защищает VERIFIED и не-текущие microtasks, но не проверяет факт предыдущего ACTIVE.
* `RollbackService` располагает механизмом физического restore по VERIFIED restore point.

Следовательно, возможна потеря различия между:
A. Microtask действительно исполнялась, затем потребовала recovery.
B. Microtask никогда не исполнялась, но получила RECOVERY_REQUIRED из-за pre-execution ABORT.
Нужно проверить, достаточно ли других инвариантов, чтобы эту ситуацию безопасно исключить.
3. Исследование ДО изменения кода
На неизменённом baseline 165:

1. Построить воспроизведение с двумя операциями одной microtask.
2. Проверить достижимость accepted ROLLBACK после settlement ABORT другой операции.
3. Проверить обычный путь `RecoveryCoordinator.recover()`.
4. Отдельно проверить прямой публичный вход RC-4 `prepare/apply`, не обходя необходимые штатные проверки.
5. Зафиксировать состояние физических файлов до и после.
6. Проверить изменения target claims, rollback sessions, Resolver authority и recovery settlement.
7. Повторить после restart в свежем процессе.

Обязательно различать:

* изменения, произведённые авторизованным исполнителем;
* внешние изменения файла;
* изменение операции только в persisted lifecycle без реального авторизованного physical effect.

Если сценарий невозможен — доказать, какой конкретный механизм его предотвращает. Представить отрицательный тест, а не искусственно внедрять исправление.
Если сценарий подтверждён — записать baseline reproduction и root cause, затем приступать к минимальному исправлению.
4. Требования к исправлению
При подтверждении дефекта исправить возможность ошибочного rollback для microtask без доказанного права на предыдущую физическую mutation.
Не считать один лишь статус RECOVERY_REQUIRED доказательством предыдущего ACTIVE.
Особенно важно:
Нельзя просто добавить или убрать разрешённые статусы, сломав настоящий recovery для ранее исполнявшихся microtasks.
Исследовать, можно ли использовать уже существующее достоверное persisted evidence об истории активации и операции. Если его недостаточно — сформулировать минимальный вариант решения, сохраняющий crash/restart correctness.
Любой новый механизм должен быть устойчив к:

* рестарту процесса;
* гонкам;
* повторному recover;
* устаревшему Resolver basis;
* историческим операциям;
* старым restore points;
* прямому вызову RC-4.

Не ослаблять проверку snapshot integrity, CAS, ownership, target locks, operation revision или replay protection.
Никакого автоматического восстановительного действия при недостатке доказательств.
Если для полноценного исправления требуется новая модель persistent authority или изменение утверждённой архитектуры за пределами scope, зафиксировать `BLOCKER / PROPOSAL` и остановиться, не выполняя архитектурную миграцию самостоятельно.
5. Обязательные инварианты

1. Никогда не исполнявшаяся microtask не должна получить право на destructive rollback только благодаря pre-execution ABORT.
2. Нормальная mutation authority существует только для соответствующей ACTIVE microtask в текущем этапе.
3. Корректный RC-4 rollback для действительно исполнявшейся microtask должен продолжить работать.
4. VERIFIED microtask не откатывается.
5. Pre-execution ABORT остаётся безопасным, достижимым и не возвращает прежний вечный FAIL_CLOSED.
6. Repair #4 W1/W2 сохраняет восстановимость подготовки.
7. Settlement policy Repair #4 сохраняется: второй rollback по той же settled operation запрещён.
8. Late ABORT, RETRY, ADOPT, rollback finalize и claims release не деградируют.
9. Persisted rollback receipts не заменяют проверку действительного текущего состояния файлов.
10. Любое сомнение в полномочиях или сохранности pre-state приводит к безопасному отказу, а не к destructive mutation.

6. Минимальные проверки
Создать regression tests на:

* B1: Pre-execution ABORT (`op1`) → accepted ROLLBACK (`op2`) одной microtask.
* B2: Тот же сценарий с прямым входом RC-4.
* B3: Корректный rollback после настоящего ACTIVE → UNKNOWN/RECOVERY_REQUIRED.
* B4: Повторный recover и fresh-process restart.
* B5: W1/W2 + ABORT + последующий sibling ROLLBACK.
* B6: Stale resolution, повторный rollback, settlement supersession.
* B7: Конкурентный ABORT/ROLLBACK/recover.
* B8: Проверка фактических байтов до и после; отсутствие неразрешённой физической мутации.
* B9: Сохранение всех ранее исправленных сценариев Repair #2/#2A/#3/#4/#4A.

Проверить разные targets: WRITE/RESTORE, DELETE и NOOP там, где это имеет значение.
Затем выполнить:

* новые тесты;
* sensitivity against baseline 165;
* focused regression;
* полный Web Alarm test suite ×2;
* adversarial pass;
* стресс-повторы гонок;
* compileall;
* git diff --check.

Все изменения и тестовые аварии — только в изолированном storage. Живые пользовательские данные не менять.
7. Documentation и continuity
Создать сессию:
`Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-013_RC6_REPAIR4B/`
Основной отчёт:
`rc6_repair4b_report.md`
В отчёте указать:

* baseline и commit SHA;
* исходный finding независимого verifier;
* reproduction / negative proof;
* root cause;
* выбранное исправление или доказательство его ненужности;
* все изменённые файлы;
* тесты и точные результаты;
* собственный adversarial review;
* residual risks;
* влияние на прежние RC-6 Repairs;
* ограничения и блокеры перед WA4-E.

Оформить Documentation Impact Check по документу `18`.
Сверить затрагиваемые документы `23`, `24`, `25`, `05`, `06`, `001`, глобальный `000` и START `08`, но не выполнять преждевременный permanent closeout.
Важное решение пользователя: после независимого PASS RC-6 ChatGPT лично займётся полной синхронизацией постоянной документации, включая историю WEB_03, изменения RC-5/RC-6 и новый протокол GitHub-first / Desktop-for-actions.
Поэтому сейчас:

* веди оперативные записи TASK;
* сохрани evidence и отчёт;
* подготовь точный documentation delta;
* постоянные статусы `DONE / VERIFIED` не устанавливай;
* канонические исторические документы самостоятельно не переписывай.

8. Границы и завершение
Это целевая работа Repair #4B, а не новая реализация RC-6 или WA4-E.
Не менять соседние подсистемы без подтверждённой необходимости.
Не начинать WA4-E, WA4-A, WA4-O или WA4-R.
Не делать commit/push — это выполняет пользователь, если не дано отдельного прямого разрешения.
После завершения:

1. Сохранить полный factual report.
2. Заполнить БЛОК 2 и БЛОК 3 как отдельный FOLLOW-UP, не трогая БЛОК 1 и прежние результаты.
3. Сообщить, подтвердился ли дефект.
4. Указать, происходил ли реально destructive rollback.
5. Сообщить результаты новых, регрессионных и adversarial тестов.
6. Перечислить изменённые файлы.
7. Указать, остались ли блокеры RC-6.

Финальный статус:
`RESULT READY / AWAITING INDEPENDENT VERIFICATION`
Не ставить `DONE / VERIFIED` самостоятельно.
NEXT: пользователь commit/push → независимая GitHub-only проверка ChatGPT → только после PASS синхронизация постоянной документации и решение о WA4-E.
```
