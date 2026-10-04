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

**Статус:** ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
**TASK:** —

Следующую утверждённую постановку сюда вставляет пользователь/координатор.

---
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена Claude 2026-10-04; результат и статус — в БЛОКЕ 3. Ниже — постановка из БЛОКА 1 дословно (в fenced-блоке, чтобы сохранить разбивку строк; сняты только хвостовые пробелы markdown-переносов).

```text
TASK: CLAUDE-WA-005 — RC-3: Canonical-target conflict gate + mutation-boundary CAS

Статус:
READY / NOT STARTED

Исполнитель:
Claude Opus 5.5

Контекст:
RC-0 = DONE / VERIFIED
RC-1 = DONE / VERIFIED
RC-2 = DONE / VERIFIED

Последний подтверждённый этап:
CLAUDE-WA-004 / RC-2 — Persistent Resolver + evidence revision binding.

RC-2 независимо принят ChatGPT после repair:

- focused Resolver + concurrency: 25/25 PASS;

- full Web Alarm: 266/266 PASS;

- multiprocess race: дополнительно 5/5 PASS;

- compileall PASS;

- git diff --check PASS.


RC-3 — следующий канонический этап маршрута:

RC-3
→ RC-4
→ RC-5
→ RC-6
→ WA4-E
→ WA4-A
→ WA4-O
→ WA4-R

==================================================

1. ЦЕЛЬ RC-3
    ==================================================


Не допустить одновременное конфликтующее исполнение нескольких process / TASK / operations по одному и тому же canonical physical target.

RC-1 уже дал:

- canonical target identity;

- Operation Contract v2;

- operation revision;

- physical pre-state;

- durable payload/ref;

- минимальную межпроцессную сериализацию самого Operation Store.


Но RC-1 serialization защищает целостность Operation Store и НЕ является conflict gate по physical target.

RC-3 должен добавить:

1. persistent canonical-target conflict admission;

2. ownership/reservation boundary для mutation window;

3. mutation-boundary CAS;

4. fail-closed поведение при target drift / operation revision drift;

5. межпроцессную защиту от одновременного получения mutation authority по одной canonical цели.


RC-3 НЕ выполняет саму физическую mutation.

Authoritative write/edit/delete executor появится только в WA4-E.

Для одного canonical physical target в один момент времени не может существовать две независимые активные mutation authorities.

Пример:

TASK A / op_A
и
TASK B / op_B

оба указывают на один canonical physical target.

Оба одновременно пытаются получить право на mutation.

Допустимый результат:

ровно один:
ACQUIRED / AUTHORIZED

второй:
CONFLICT / FAIL-CLOSED

Нельзя:

оба PASS
→ оба считают себя владельцами цели.

При этом разные canonical targets не должны без необходимости блокировать друг друга.

Conflict gate НЕ должен доверять caller-supplied path как identity.

Использовать canonical target identity, уже введённую RC-1.

Нужно убедиться, что:

- эквивалентные представления одной цели сходятся к одной conflict identity;

- raw path / display path не создают отдельную authority;

- target identity берётся из проверенного Operation Contract / server-side canonicalization;

- неизвестный / неоднозначный / unsupported target → fail-closed.


Legacy v1 или incomplete contract не должны молча получать mutation authority, если из них невозможно доказать canonical target + CAS basis.

Нужен минимальный persistent record layer для ownership/reservation.

Предпочтительно отдельный узкий record/store поверх Operation Contract, а НЕ расширение глобальной Operation/Microtask state machine.

Минимальная identity должна позволять доказать:

- task_id;

- microtask_id при необходимости;

- operation_id;

- canonical target identity/key;

- claim/reservation identity;

- operation revision;

- pre-state / CAS basis identity;

- created_at;

- status/result;

- provenance, где требуется.


Точный формат выбирай минимальный и механически проверяемый.

ВАЖНО:
не вводить скрытую lease/heartbeat систему.

RT-001/V17 специально отложил точную lease/heartbeat model.

Поэтому в RC-3:

- никакого TTL ownership;

- никакого «если процесс давно молчит — claim свободен»;

- heartbeat не является authority;

- process death сам по себе НЕ разрешает забрать target;

- потеря Remote/Chat НЕ освобождает ownership автоматически.


Неизвестность после crash/disconnect должна оставаться fail-closed до persistent reconciliation / explicit safe action.

При запросе ownership/reservation сервер обязан атомарно:

1. загрузить current Operation Contract;

2. проверить operation identity;

3. проверить operation revision;

4. получить canonical target identity;

5. проверить достаточность contract/CAS basis;

6. перечитать authoritative persistent claim state;

7. проверить существующий owner той же canonical цели;

8. только после этого создать/вернуть claim.


Семантика:

A. target свободен + basis valid
→ claim создаётся.

B. тот же logical operation повторяет тот же запрос
→ replay-safe;
→ вернуть тот же persistent claim/result;
→ второй claim не создавать.

C. другая operation / TASK уже владеет той же canonical целью
→ CONFLICT;
→ никакой mutation authority.

D. operation revision изменилась
→ STALE / CAS failure;
→ никакой authority.

E. target physical state изменился относительно разрешённого CAS basis
→ STALE / STATE_DRIFT / CAS failure;
→ никакой authority.

F. contract insufficient / legacy unsafe / target identity ambiguous
→ FAIL-CLOSED.

Критически важно:

reservation, созданная раньше, сама по себе НЕ должна навсегда доказывать, что mutation всё ещё безопасна.

Перед выдачей финальной mutation authority будущему executor необходимо повторно проверить CAS basis.

Минимум:

- claim всё ещё принадлежит этой operation;

- canonical target identity тот же;

- operation revision та же;

- physical target state соответствует ожидаемому pre-state / разрешённому current basis;

- нет conflicting owner;

- claim не был безопасно released/cancelled.


Если между acquire и mutation boundary внешний writer изменил target:

ACQUIRE PASS
→ внешний change
→ CAS

результат обязан быть:

CAS FAIL / STATE_DRIFT
→ NO MUTATION AUTHORITY

Никакой автоматической перезаписи внешнего изменения.

RC-3 может создать persistent mutation-ready / authorization result, но НЕ должен выполнять physical write/edit/delete.

Если корректная реализация CAS требует крупного нового public lifecycle/state machine, которой нет в утверждённой архитектуре:

STOP
→ DECISION REQUIRED

и объяснить конкретно, какое архитектурное решение нужно.

Нужна минимальная deterministic семантика освобождения claim, достаточная для RC-3 tests и будущего WA4-E.

Обязательные правила:

- release только для доказанного текущего owner / той же logical operation;

- чужая operation не может освободить claim;

- replay release идемпотентен;

- release не выполняет physical mutation;

- timeout / disconnect / heartbeat НЕ являются implicit release;

- после корректного release другая operation может приобрести target при fresh CAS basis.


Не вводить автоматический lease expiry.

Если безопасный release невозможно определить без отдельного архитектурного решения — STOP / DECISION REQUIRED, а не придумывать скрытую политику.

Conflict gate должен быть реальным межпроцессным, а не только threading lock внутри одного Python process.

Обязательный controlled race:

несколько независимых process
→ разные TASK/operation_id
→ один canonical physical target
→ одновременно пытаются acquire

Ожидается:

ровно один active owner;
остальные deterministic conflict/fail-closed;
persistent store остаётся валиден.

Минимум проверить несколько повторов race.

Также проверить:

разные canonical targets
→ могут независимо получить claims;
→ глобальная ненужная serialization всех targets не должна становиться архитектурным requirement.

Для lock identity не использовать небезопасный raw path как имя lock-файла; использовать безопасную deterministic identity/hash canonical target.

RC-3 должен корректно работать поверх уже принятого Resolver.

Не ломать:

ADOPT
RETRY
ROLLBACK
ABORT
STALE
REJECTED

Особенно:

- stale Resolver resolution не может породить ownership authority;

- ABORTed resolver recovery не должен случайно reacquire target;

- RETRY re-arm сам по себе ещё не является mutation authority;

- ROLLBACK request сам по себе ещё не является physical rollback authority.


Не переписывать RC-2 без необходимости.

Legacy Operation Contract v1 не имеет права получить unsafe target ownership только ради совместимости.

Incomplete v2 также должен fail-closed, если для conflict/CAS authority не хватает:

- canonical target;

- physical pre-state;

- operation revision;

- необходимого mutation/CAS basis.


Read compatibility сохранить.

Unsafe upgrade/rewrite legacy record не выполнять.

Conflict gate должен быть доступен через узкий server-owned interface, совместимый с существующим Operation/Resolver API style.

Минимально должны быть доступны операции уровня:

- acquire / reserve;

- inspect/read current claim;

- CAS / authorize mutation boundary;

- release/cancel.


Точные route/name выбирай по текущей архитектуре проекта.

Все mutating control-plane endpoints должны быть:

- persistent;

- replay-safe;

- fail-closed;

- server-owned.


UI в RC-3 не менять.

Новый process обязан без Chat memory восстановить:

- кто владеет canonical target;

- какая operation является owner;

- на какой operation revision claim создан;

- какой CAS basis был использован;

- был ли claim released;

- можно ли текущей operation пройти mutation-boundary CAS;

- почему конфликтующая operation заблокирована.


Fresh-process result должен совпадать с persistent state.

Process restart не должен сам очищать ownership.

Минимальный acceptance RC-3:

1. Basic acquire:
    свободный canonical target → один persistent owner.

2. Replay:
    тот же operation_id + тот же basis → тот же claim/result;
    duplicate effect отсутствует.

3. Same target conflict:
    другая operation той же TASK → conflict.

4. Cross-TASK conflict:
    другая TASK / operation → тот же canonical physical target → conflict.

5. Different targets:
    независимые цели не конфликтуют.

6. Canonical identity:
    эквивалентное представление одной physical цели не обходит gate.

7. Stale operation revision:
    acquire/CAS basis N
    → operation revision N+1
    → старый claim не получает mutation authority.

8. Physical target drift:
    acquire
    → внешний writer меняет bytes
    → mutation-boundary CAS fail-closed.

9. Wrong owner release:
    чужая operation не может release claim.

10. Release replay:
    release идемпотентен.

11. After safe release:
    другая operation может acquire только после fresh validation/CAS basis.

12. Crash/restart:
    новый process видит тот же active claim;
    ownership не исчезает от process death.

13. Legacy v1:
    unsafe acquire/CAS запрещён.

14. Incomplete v2:
    unsafe authority запрещена.

15. Resolver integration:
    stale/rejected/aborted recovery state не получает ложную mutation authority.

16. Multiprocess race:
    минимум несколько независимых process одновременно на одной цели;
    ровно один owner.

17. Full Web Alarm regression.

18. `python -B -m compileall -q web_alarm`

19. `git diff --check`

20. Проверить, что physical Workspace bytes не изменяются самим RC-3 control-plane.


Не расширять public OperationStatus или Microtask lifecycle без необходимости.

Предпочтение:

Operation Contract

- Resolver

- отдельный минимальный Target Claim / Conflict Gate layer.


Если для корректности требуется:

- новая большая глобальная state machine;

- новый lease/heartbeat protocol;

- автоматическая orphan-owner policy;

- изменение архитектурного authority model;


STOP
→ DECISION REQUIRED

До решения пользователя не продолжать архитектурную импровизацию.

НЕ делать:

- physical write/edit/delete;

- authoritative Mutation Executor — это WA4-E;

- destructive rollback — RC-4;

- rollback receipt/post restore verification — RC-4;

- checkpoint rebuild/projection correctness — RC-5;

- Context Pack Resolver-NEXT repair — RC-5/RC-6;

- project-level resume — RC-6;

- lost-response deterministic acceptance — WA4-A;

- UI changes;

- lease/heartbeat/TTL ownership;

- `.gitattributes`;

- line-ending normalization;

- unrelated refactor;

- commit / push;

- автоматический старт RC-4.


Перед изменениями:

1. перечитать актуальные:

    - `000_Задачи Claude.md`;

    - global `000_Задачи для агента.md`;

    - `23_Архитектура Web Alarm Workspace.md`;

    - `24_План реализации Web Alarm Workspace.md`;

    - RC-2 report/history;

2. сверить текущий HEAD и git status;

3. убедиться, что код соответствует принятому RC-2;

4. создать рабочую папку:
    `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-005_RC3/`

5. сохранить safety copies только реально изменяемых файлов + baseline/hash.


Не откатывать:

- пользовательские изменения;

- изменения ChatGPT;

- Obsidian;

- чужой dirty state.


После выполнения:

Отчёт:
`Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-005_RC3/rc3_report.md`

По новому правилу task routing:

- БЛОК 1 НЕ очищать и НЕ заменять;

- выполненную постановку скопировать в БЛОК 2;

- БЛОК 3 заполнить кратким factual result:

    - что реализовано;

    - какие файлы изменены/добавлены;

    - concurrency/CAS semantics;

    - тесты;

    - известные ограничения;

    - report path;

    - итоговый статус.


До независимой проверки допустимый статус только:

RESULT READY / AWAITING INDEPENDENT VERIFICATION

Claude самостоятельно НЕ пишет:

DONE / VERIFIED

и не закрывает permanent history.

Не обновлять самостоятельно после исполнения:

- `001_История выполненных задач Claude.md`;

- `06_Журнал выполнения и отчёты.md`;

- `25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md`;

- финальный canonical DONE/VERIFIED.


Это после независимой проверки синхронизирует ChatGPT/verifier.

Не делать commit/push.

NEXT SAFE ACTION:
выполнить только CLAUDE-WA-005 / RC-3,
остановиться на RESULT READY,
RC-4 НЕ начинать.
```

---
# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ
---

**TASK:** CLAUDE-WA-005 — RC-3: Canonical-target conflict gate + mutation-boundary CAS.
**Статус:** DONE / VERIFIED — 2026-10-04. Independent verification PASS на commit 149 `163dfba`; RC-4 не начат.

**Что реализовано:**
- узкий слой Target Claim / Conflict Gate поверх контракта v2 и Resolver. Identity цели — физический resolved path (`normcase`) по контракту на стороне сервера; файлы и блокировки называются по `sha256`;
- один атомарный документ на цель (`target_claims/<hash>.json`: `active` + `history`) и своя межпроцессная блокировка на цель; порядок — блокировка TASK → блокировка цели;
- acquire: ACQUIRED / REPLAYED / REBASED / CONFLICT / STALE (ревизия, дрейф байтов) / REJECTED (legacy, неполный контракт, payload, ABORT, нет fresh RETRY для операции не в INTENT);
- CAS — `mutation_boundary` под обеими блокировками: владение, ревизии, контракт, допустимость, байты = `cas_basis`. Authority существует только внутри блока, результат сохраняется как evidence;
- release — только владелец, идемпотентно, без TTL / heartbeat. Для STARTED / UNKNOWN ждёт ADOPT или ABORT от Resolver;
- inspect — владелец, блокирующий владелец, `cas_preview`;
- API: `/tasks/<t>/operations/<op>/claim[/authorize|/release]`.

**Файлы:**
- новые: `web_alarm/target_claim_store.py`, `web_alarm/target_claim_service.py`, `test_web_alarm_target_claims.py` (18), `test_web_alarm_target_claims_concurrency.py` (2);
- изменённые: `web_alarm/server.py` (+60), `web_alarm/__init__.py` (+7);
- `models.py`, `OperationStatus`, `operation_store.py`, Resolver, контракт и UI не менялись.

**Concurrency / CAS:**
- 8 процессов из разных TASK на одну цель — ровно 1 ACQUIRED и 7 CONFLICT, 5/5 прогонов; без блокировки цели 4–5 «владельцев»;
- 8 разных целей — все ACQUIRED;
- внешний дрейф между acquire и CAS → `STATE_DRIFT`, без перезаписи.

**Тесты:**
- полный Web Alarm — **286/286 OK** (skip 1);
- compileall OK;
- `git diff --check` OK для всех изменений RC-3. Срабатывают только хвостовые пробелы в пользовательском тексте БЛОКА 1, его не трогал;
- байты проекта и живое storage не изменились.

**Известные ограничения:**
- внешние писатели между CAS и записью ловятся только receipt из RC-1;
- внутри `mutation_boundary` нельзя вызывать `OperationStore.transition` (та же блокировка TASK) — WA4-E нужен вариант при уже взятой блокировке;
- orphan-owner policy отложена (V17);
- история claims без очистки;
- после принятия — перезапуск процессов WEB-02.

**Independent verification ChatGPT:** проверен последний commit 149 `163dfba219e5b49b822e82070124e23c368cb928`; focused RC-3 20/20 PASS; full Web Alarm 286/286 PASS; concurrency suite дополнительно 5/5 PASS; `compileall` PASS. Независимый review подтвердил one-owner gate, canonical physical identity, persistent crash-safe claims, no TTL/heartbeat, fail-closed CAS при revision/state drift и Resolver integration. Runtime blocker не найден.

**Решения verifier:** physical resolved-path identity принята; release guard для STARTED / UNKNOWN принят как консервативный fail-closed; fresh accepted RETRY для non-INTENT принят как продолжение RC-2. Старый acquire на уже известном stale basis может вернуть `REPLAYED`, но не mutation authority; mutation-boundary CAS на текущей revision остаётся fail-closed.

**WA4-E integration note:** standalone `/authorize` — только evidence; реальная запись допустима только внутри `mutation_boundary`. Нормальный первый executor должен под уже удерживаемой TASK-lock зафиксировать STARTED перед physical write через lock-held/internal transition path, а не вызывать обычный re-entrant `OperationStore.transition()`. Это обязательный future integration item, не blocker RC-3.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-005_RC3/rc3_report.md`; safety copies и `baseline.md` — там же.

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
