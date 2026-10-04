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

**Статус постановки:** выполнена Claude 2026-10-04; после независимых проверок (REPAIR REQUIRED) выполнены Independent Review Repair #1 и #2 той же TASK — их постановки дословно ниже исходной, по порядку. Результат и статус — в БЛОКЕ 3. Ниже — полная постановка из БЛОКА 1 дословно (fenced-блок сохраняет разбивку строк).

```text
TASK: CLAUDE-WA-006 — RC-4: Tracked safe rollback + preserved current state + persistent receipts

Статус:
READY / NOT STARTED

Исполнитель:
Claude Opus 5.5

Контекст:
RC-0 = DONE / VERIFIED
RC-1 = DONE / VERIFIED
RC-2 = DONE / VERIFIED
RC-3 = DONE / VERIFIED

Последний подтверждённый этап:
CLAUDE-WA-005 / RC-3 — Canonical-target conflict gate + mutation-boundary CAS.

Последний подтверждённый Git baseline перед документационным обновлением:
commit 150
0f9e93aac968dd1397e94c6300e828a3acc9c187

RC-3 независимо принят ChatGPT:

- focused RC-3: 20/20 PASS;
- full Web Alarm: 286/286 PASS;
- concurrency suite: дополнительно 5/5 PASS;
- compileall PASS;
- один persistent owner на canonical physical target;
- crash/restart claim сохраняется;
- stale operation revision / physical state drift fail-closed;
- Resolver state не обходит conflict gate.

Принятые решения RC-3:

- conflict identity = server-resolved canonical physical target;
- STARTED / UNKNOWN claim не освобождается до безопасного recovery outcome;
- non-INTENT operation получает новую authority только через fresh accepted RETRY;
- standalone /authorize является evidence only;
- mutation authority существует только внутри mutation_boundary.

ВАЖНО ДЛЯ БУДУЩЕГО WA4-E:
обычный executor должен фиксировать STARTED под уже удерживаемой TASK-lock ДО physical write через lock-held/internal transition path.
Это не нужно реализовывать как общий normal-mutation executor в RC-4.

Канонический маршрут:

RC-4
→ RC-5
→ RC-6
→ WA4-E
→ WA4-A
→ WA4-O
→ WA4-R

==================================================
1. ЦЕЛЬ RC-4
==================================================

Превратить ROLLBACK из persistent request, который появился в RC-2, в отдельную tracked safe recovery operation.

Сейчас:

Resolver:
ROLLBACK
→ только persistent request
→ physical restore НЕ выполняется.

ManifestSnapshotStore:
restore_microtask()
→ уже умеет физически восстанавливать snapshot
→ но это старый прямой destructive restore;
→ он не является достаточным tracked recovery lifecycle RC-4.

RC-4 должен дать безопасный путь:

accepted fresh ROLLBACK resolution
→ persistent rollback intent
→ сохранить current state ДО destructive restore
→ доказать restore point
→ получить conflict/CAS authority на все изменяемые physical targets
→ physical restore
→ exact post-restore verification
→ persistent per-target / overall receipt
→ replay/fresh-process recovery без слепой повторной destructive mutation.

Главный инвариант:

НЕИЗВЕСТНОЕ CURRENT STATE НЕЛЬЗЯ УНИЧТОЖИТЬ ROLLBACK-ОМ.

До первого destructive restore фактическое current состояние всех затрагиваемых целей должно быть сохранено как recoverable evidence.

==================================================
2. СУЩЕСТВУЮЩИЙ КОД, КОТОРЫЙ НУЖНО ИСПОЛЬЗОВАТЬ
==================================================

Перед проектированием перечитать минимум:

- web_alarm/manifest_store.py
- web_alarm/reconciliation.py
- web_alarm/reconciliation_decision.py
- web_alarm/resolver_service.py
- web_alarm/resolution_store.py
- web_alarm/target_claim_store.py
- web_alarm/target_claim_service.py
- web_alarm/operation_contract.py
- web_alarm/operation_store.py
- web_alarm/recovery_report_service.py
- web_alarm/recovery_report_builder.py
- web_alarm/server.py
- соответствующие tests RC-1 / RC-2 / RC-3.

Особенно учесть:

ManifestSnapshotStore.restore_microtask()
уже существует и физически меняет Workspace.

НЕ создавать второй независимый snapshot/restore мир без необходимости.

Но НЕ использовать старый restore_microtask() как готовый authoritative RC-4 executor, если он уничтожает current state без нового tracked lifecycle.

Допустимо рефакторить существующий restore слой на:
- read/plan primitives;
- verified snapshot access;
- безопасные atomic file primitives;

если это позволяет RC-4 использовать существующие snapshot bytes без дублирования authority.

Server сейчас специально НЕ экспонирует destructive restore:
snapshot endpoint допускает verify only.

Не превращать старый endpoint в unrestricted restore.

==================================================
3. AUTHORITY ДЛЯ ROLLBACK
==================================================

Физический rollback допускается только если существует:

1. persistent ResolutionAction.ROLLBACK;
2. result = ACCEPTED;
3. resolution всё ещё fresh;
4. resolution относится к тому же task_id / microtask_id / operation_id;
5. current evidence / operation revision не изменились относительно basis;
6. restore point существует и проходит integrity verification;
7. все targets rollback определены сервером из persisted manifest/snapshot, а не caller input.

STALE / REJECTED / ABORT / отсутствующая resolution:
→ NO RESTORE.

Caller не может сам передать список файлов, которые надо восстановить, как authority.

Target set должен происходить из verified manifest текущей microtask.

==================================================
4. PERSISTENT ROLLBACK IDENTITY
==================================================

Нужен отдельный минимальный persistent rollback layer.

Не превращать это молча в новую глобальную Operation/Microtask state machine.

Минимальная rollback identity должна позволять доказать:

- rollback_id;
- task_id;
- microtask_id;
- source operation_id;
- source resolution_id;
- evidence fingerprint;
- source operation revision;
- restore-point / manifest identity;
- точный target set;
- created_at / updated_at;
- provenance;
- current-state preservation state;
- execution status;
- per-target result;
- overall result;
- receipts / verification;
- next safe action.

Точные internal statuses выбери минимальными и механически проверяемыми.

Обязательные смысловые фазы:

INTENT / PREPARED
→ CURRENT_STATE_PRESERVED
→ AUTHORIZED
→ APPLYING
→ APPLIED / PARTIAL / FAILED / UNKNOWN
→ VERIFIED

Названия можно выбрать другие, если смысл сохраняется.

Replay одного rollback_id / того же logical basis:
→ не создаёт второй независимый rollback.

==================================================
5. PRESERVE CURRENT STATE BEFORE RESTORE
==================================================

До ПЕРВОЙ destructive mutation:

для КАЖДОГО target rollback нужно server-side получить current physical state:

- exists;
- exact size;
- SHA-256 exact bytes;
- canonical physical identity.

Если файл существует:
его current bytes должны быть сохранены в machine-local recovery storage ВНЕ repo / Obsidian vault.

Если target отсутствует:
persistent evidence должно явно фиксировать absence.

Сохранённые current bytes:
- immutable/content-addressed или эквивалентно устойчивые;
- hash + size проверяются после записи;
- не попадают содержимым в event/report/log;
- obey существующие secret/scope/size constraints;
- позволяют при необходимости исследовать/восстановить состояние, которое rollback собирался уничтожить.

Если current-state preservation хотя бы одного target не удалось доказать:
→ NO destructive restore по всей rollback session.

Не начинать частичную физическую фазу до успешного preservation ВСЕГО target set.

==================================================
6. CONFLICT GATE / RC-3 INTEGRATION
==================================================

Rollback НЕ имеет права обходить RC-3 только потому, что это recovery.

Перед первым physical change rollback должен получить exclusive mutation ownership для ВСЕХ canonical physical targets, которые он собирается менять.

Требование:

- target set канонизируется server-side;
- deterministic ordering target ownership / locks;
- конфликт хотя бы на одном target
  → no physical mutation по rollback session;
- уже полученные reservations безопасно освобождаются/фиксируются;
- разные независимые targets не должны глобально блокировать друг друга.

Нельзя создавать параллельный «особый rollback lock», который не конфликтует с обычными RC-3 claims.

Если текущий RC-3 claim contract технически не может безопасно представить multi-target rollback ownership:

STOP → DECISION REQUIRED.

В этом случае:
- ничего destructive не выполнять;
- описать точный architectural gap;
- показать минимальные безопасные варианты интеграции;
- не обходить RC-3 временной лазейкой.

Допускается минимальное backward-compatible расширение RC-3 ownership layer, если оно очевидно локально, не создаёт новую глобальную state machine и хорошо покрывается тестами.

==================================================
7. PRE-MUTATION CAS
==================================================

После preservation и ownership acquisition, непосредственно перед каждой физической mutation:

- перечитать authoritative rollback record;
- проверить source ROLLBACK resolution freshness;
- проверить operation revision;
- проверить ownership;
- проверить canonical target;
- сравнить current physical bytes с сохранённым rollback CAS basis.

Если bytes изменились после preservation:
→ STATE_DRIFT / STALE;
→ этот target не перезаписывать;
→ rollback session не продолжать как будто всё нормально;
→ persistent state должен позволять fresh-process reconciliation.

Нельзя использовать сохранённый час назад hash как безусловное разрешение на restore.

==================================================
8. RESTORE SEMANTICS
==================================================

Для каждого manifest entry:

A. target существовал до microtask:
→ восстановить EXACT snapshot bytes;
→ atomic write;
→ post-read;
→ exact size/hash должны совпасть с original snapshot.

B. target не существовал до microtask:
→ rollback означает удалить созданный файл;
→ delete допускается только после current-state CAS;
→ после действия target обязан быть absent.

C. target уже находится ровно в pre-state:
→ physical mutation не требуется;
→ записать persistent NOOP / ALREADY_RESTORED факт;
→ не переписывать файл бессмысленно.

D. snapshot corrupt / missing / identity mismatch:
→ fail-closed;
→ no destructive restore.

==================================================
9. PARTIAL FAILURE
==================================================

Файловая система не является общей атомарной транзакцией на несколько targets.

Поэтому RC-4 обязан корректно переживать:

target A restored
→ crash / error
→ target B ещё не restored.

Нельзя скрывать это как общий SUCCESS.

Persistent rollback state должен содержать per-target receipts/status.

После fresh process система должна различать минимум:

- not started;
- current-state preserved;
- restored + post verified;
- already pre-state;
- pending;
- failed / drifted;
- unknown after interruption.

Повтор после partial/unknown:
→ сначала inspect/reconcile;
→ уже доказанно restored target не мутировать второй раз;
→ target с неизвестным fate не повторять вслепую.

==================================================
10. PERSISTENT RECEIPT
==================================================

Для реально restored target receipt минимум содержит:

- rollback_id;
- target identity;
- action performed (WRITE_RESTORE / DELETE_CREATED / NOOP);
- pre-rollback preserved state hash/size/exists;
- expected restore state;
- observed post state;
- matches_expected_restore;
- timestamp;
- relevant revision / basis identity.

Overall rollback receipt/result:
- строится из per-target persistent facts;
- не из caller memory;
- одинаков после fresh process reopen.

SUCCESS допускается только если весь target set доказан как restored/pre-state.

==================================================
11. RECOVERY REPORT INTEGRATION
==================================================

RC-2 оставил:

actually_rolled_back = []

потому что тогда ROLLBACK был только request.

После RC-4 это должно измениться.

Recovery Report:
- ROLLBACK_REQUESTED всё ещё не означает physical rollback;
- `actually_rolled_back` появляется ТОЛЬКО из persistent verified RC-4 receipts;
- partial rollback отражается как partial/unresolved, а не как full rollback;
- fresh process строит тот же report из persistence;
- caller claim без backing receipt отклоняется.

Resolver action и physical rollback receipt должны оставаться разными фактами:

ROLLBACK accepted
≠
ROLLBACK physically completed.

==================================================
12. IDEMPOTENCY / RESTART SAFETY
==================================================

Обязательные свойства:

- same rollback_id + same basis → known persistent result;
- same completed rollback replay → NO second physical side effect;
- fresh process видит тот же rollback session;
- fresh process видит per-target receipts;
- crash после preservation, но до restore → project unchanged;
- crash после physical target restore → fresh process сначала доказывает фактический target state и не делает blind second restore;
- stale source resolution → no continuation;
- changed target → fail-closed / new reconciliation.

==================================================
13. LEGACY / BACKWARD COMPATIBILITY
==================================================

Нельзя ломать существующие:

- WA-1 manifests/snapshots;
- legacy WA-3.7 operations;
- Operation Contract v2;
- Resolver records RC-2;
- Target Claim records RC-3;
- старые Recovery Reports.

Read-only открытие старого machine-local storage:
→ не должно его переписывать.

Если вводится новая версия rollback/claim record:
→ явная versioning/backward-compatibility policy.

==================================================
14. ЧТО RC-4 НЕ ДЕЛАЕТ
==================================================

НЕ делать:

- general normal write/edit/delete executor — это WA4-E;
- общий новый Operation/Microtask lifecycle без отдельного решения;
- RC-5 checkpoint/projection redesign;
- RC-6 project-level resume;
- Context Pack projection repair, кроме минимального поля, без которого RC-4 невозможно корректно отразить;
- UI;
- strict rollout;
- lease/heartbeat;
- `.gitattributes`;
- line-ending normalization;
- unrelated refactor;
- commit / push;
- автоматический старт RC-5.

Если корректная реализация требует изменения deferred global state machine / lease model / фундаментальной RC-3 ownership model:

STOP → DECISION REQUIRED.

==================================================
15. ОБЯЗАТЕЛЬНЫЕ TESTS
==================================================

Минимум:

1. Accepted fresh ROLLBACK:
   → persistent rollback intent создаётся.

2. No accepted ROLLBACK:
   → no mutation.

3. STALE ROLLBACK resolution:
   → no mutation.

4. REJECTED / ABORT:
   → no mutation.

5. Restore-point integrity failure:
   → no mutation.

6. Preserve current existing file:
   → exact current bytes сохранены и verified до restore.

7. Preserve current absence:
   → absence persistent.

8. Preservation failure одного target:
   → zero physical rollback по всем targets.

9. Existing-before target:
   → exact snapshot bytes restored + post hash/size verified.

10. New-file target:
    → safely deleted + absence verified.

11. Already-pre-state target:
    → NOOP, без physical rewrite.

12. Target drift after preservation:
    → CAS fail / no overwrite.

13. Same-target conflict with normal RC-3 owner:
    → rollback blocked; no mutation.

14. Multi-target acquisition:
    → конфликт на одном target не допускает начало destructive phase.

15. Different independent targets:
    → ownership не создаёт ненужный global lock.

16. Replay completed rollback:
    → same receipt / zero second mutation.

17. Crash/restart after preservation before mutation:
    → fresh process resumes/inspects safely; bytes unchanged.

18. Crash/restart / lost response after one target restore:
    → restored target не мутируется повторно вслепую;
    → partial state persistent.

19. Per-target receipt integrity.

20. Overall SUCCESS только при verified full target set.

21. Recovery Report:
    - request-only ROLLBACK != actually_rolled_back;
    - completed verified rollback populates actual facts from persistence;
    - partial rollback не выдаётся за full;
    - caller unsupported claim rejected.

22. Fresh-process reopen:
    → same rollback status / receipts / NEXT SAFE ACTION.

23. Legacy live storage read-only compatibility.

24. RC-1 / RC-2 / RC-3 focused regressions.

25. Real multiprocess conflict/race test.

26. Full Web Alarm regression.

27.
python -B -m compileall -q web_alarm

28.
git diff --check

==================================================
16. ACCEPTANCE RC-4
==================================================

RC-4 можно отдать на independent verification только если доказано:

- rollback имеет persistent identity;
- только fresh accepted ROLLBACK resolution может открыть execution path;
- current state ВСЕХ targets сохранён до destructive phase;
- preservation проверен hash+size;
- restore point повторно verified;
- rollback не обходит RC-3 conflict gate;
- target set не caller-authoritative;
- CAS стоит непосредственно на destructive boundary;
- unknown external drift не перезаписывается;
- exact original snapshots восстанавливаются корректно;
- created-by-microtask files удаляются корректно;
- no-op pre-state не мутируется;
- partial failure persistent и restart-safe;
- replay не создаёт second side effect;
- persistent receipts доказывают фактический rollback;
- Recovery Report отличает requested rollback от actually completed rollback;
- fresh process восстанавливает тот же authoritative rollback state;
- backward compatibility сохранена;
- full regression PASS;
- RC-5 не начат.

==================================================
17. SAFETY / WORKFLOW
==================================================

Перед изменениями:

1. перечитать:
   - Документация/000_Задачи Claude.md;
   - Документация/000_Задачи для агента.md;
   - Документация/18_Регламент сопровождения документации.md;
   - Документация/23_Архитектура Web Alarm Workspace.md;
   - Документация/24_План реализации Web Alarm Workspace.md;
   - последние RC-2 / RC-3 reports;

2. сверить фактический Git HEAD и dirty tree;

3. НЕ считать `.obsidian` своими изменениями;

4. создать:
   Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-006_RC4/

5. сохранить safety copies всех существующих файлов, которые собираешься менять;

6. зафиксировать baseline и исходные hashes;

7. не делать destructive test на реальном project data:
   destructive rollback tests только в isolated temporary Workspace;
   live storage проверять read-only, если явно не требуется иное.

==================================================
18. ОТЧЁТ
==================================================

Создать:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-006_RC4/rc4_report.md

В отчёте обязательно:

- architecture выбранного rollback layer;
- почему не дублируется старый Manifest/Snapshot authority;
- identity / persistence;
- linkage Resolution → Rollback;
- current-state preservation;
- conflict/CAS model;
- multi-target behavior;
- failure/crash semantics;
- per-target / overall receipts;
- Recovery Report integration;
- changed files;
- tests;
- regression;
- compatibility;
- unresolved decisions;
- explicit confirmation:
  RC-5 NOT STARTED.

==================================================
19. НОВОЕ ПРАВИЛО РОТАЦИИ ПЕРСОНАЛЬНОЙ КАРТОЧКИ
==================================================

После фактического завершения RC-4 Claude сам, без отдельной команды пользователя:

1. СНАЧАЛА копирует ЭТУ ПОЛНУЮ постановку из БЛОКА 1 в БЛОК 2.

2. ЗАТЕМ заполняет БЛОК 3 factual closeout:
   - TASK;
   - что сделано;
   - файлы;
   - tests/results;
   - ограничения;
   - report path;
   - статус:
     RESULT READY / AWAITING INDEPENDENT VERIFICATION.

3. ТОЛЬКО ПОСЛЕ успешного сохранения БЛОКОВ 2–3 очищает БЛОК 1 и оставляет:

   Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
   TASK: —

Если запись оборвалась во время ротации:
→ не повторять вслепую;
→ перечитать фактический документ;
→ доказать, что БЛОКИ 2–3 сохранены;
→ только затем решать, очищать ли БЛОК 1.

Claude НЕ обновляет самостоятельно после исполнения:
- 001_История выполненных задач Claude.md;
- 06_Журнал выполнения и отчёты.md;
- 25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md;
- canonical DONE / VERIFIED.

Это после independent verification делает ChatGPT/verifier.

Не делать commit/push.

NEXT SAFE ACTION:
выполнить только CLAUDE-WA-006 / RC-4,
остановиться на RESULT READY / AWAITING INDEPENDENT VERIFICATION,
очистить персональный БЛОК 1 по новому регламенту,
RC-5 НЕ начинать.
```

## Дополнение — Independent Review Repair (постановка из БЛОКА 1, 2026-10-04, дословно)

```text
TASK: CLAUDE-WA-006 — RC-4 INDEPENDENT REVIEW REPAIR:
Final full-target verification before VERIFIED/SUCCESS

Статус:
REPAIR REQUIRED / RC-4 NOT VERIFIED

Исполнитель:
Claude Opus 5.5

Контекст:
CLAUDE-WA-006 / RC-4 реализован на commit 152:

42ce55083d0dcf0eb700c6eec0fa2ce463a3e6cd

Independent review ChatGPT подтвердил:

- штатные focused RC-4 tests: 26/26 PASS;
- compileall PASS;
- git diff --check PASS;

НО обнаружен acceptance blocker, которого нет в текущей test matrix.

RC-4 НЕ является DONE / VERIFIED.
RC-5 НЕ начинать.

==================================================
1. BLOCKER
==================================================

В multi-target rollback возможен сценарий:

target A
→ restored
→ immediate post-read PASS
→ persistent receipt записан

затем до завершения всей rollback-session внешний writer меняет A

затем:

target B
→ restored
→ immediate post-read PASS

Текущий код может после этого объявить:

rollback.status = VERIFIED
result.overall = SUCCESS

несмотря на то, что фактический current state target A уже НЕ соответствует expected restore state.

Independent probe ChatGPT воспроизвёл это на commit 152:

RESULT VERIFIED
STATUS VERIFIED
FIRST_RECORDED_STATUS RESTORED
FIRST_RECEIPT_MATCH True

при этом фактические bytes первого target:

external-after-first-receipt

OVERALL:
SUCCESS

Это acceptance blocker.

==================================================
2. ПРИЧИНА
==================================================

Проверить в первую очередь:

web_alarm/rollback_service.py

Текущая логика имеет три связанных свойства:

1. `_session_basis()`:

после появления собственного effect (`RESTORED / APPLYING / FAILED`)
больше не проверяет полный Resolver evidence fingerprint.

Само по себе это допустимо, потому что rollback изменяет evidence своими действиями.

НО вместо полного fingerprint требуется доказать current state каждого target относительно tracked rollback facts.

2. `_apply_locked()`:

targets со status:

RESTORED
NOOP

в основном per-target цикле пропускаются.

Их фактические bytes перед финальным SUCCESS повторно не доказываются.

3. `_finalize()`:

определяет SUCCESS по persistent target statuses / receipts:

RESTORED
NOOP

но не выполняет final physical verification всего target set.

Таким образом старый receipt фактически превращается в доказательство текущего состояния, хотя он доказывает только состояние В МОМЕНТ своей записи.

==================================================
3. ОБЯЗАТЕЛЬНЫЙ ИНВАРИАНТ REPAIR
==================================================

Перед переходом rollback session в:

VERIFIED
/
SUCCESS

система ОБЯЗАНА под текущими rollback locks повторно доказать весь target set по физическому Workspace.

Для КАЖДОГО target:

current physical state
==
expected_restore

по exact authority:

exists
size
SHA-256 exact bytes.

Нельзя считать старый receipt proof текущего состояния.

Receipt = историческое доказательство выполненного действия.

Final verification = доказательство текущего состояния всего rollback target set.

Это разные факты.

==================================================
4. FINAL FULL-TARGET VERIFICATION
==================================================

Добавить отдельный явный final verification boundary.

Он должен выполняться:

- после всех per-target restore/no-op действий;
- ДО:
  - `record["status"] = VERIFIED`;
  - overall SUCCESS;
  - release rollback claims;
  - возврата VERIFIED вызывающему.

Пока target locks ещё удерживаются.

Для каждого target:

A. expected_restore.exists = true

→ target обязан существовать как file;
→ exact size совпадает;
→ exact SHA-256 совпадает.

B. expected_restore.exists = false

→ target обязан отсутствовать.

Если хотя бы один target больше не совпадает:

→ НЕЛЬЗЯ ставить VERIFIED/SUCCESS;
→ НЕЛЬЗЯ выдавать full rollback;
→ persistent session должна показать drift/unresolved/partial-or-failed state;
→ внешний current state НЕ перезаписывать автоматически.

Особенно:

ранее RESTORED target
→ external drift
→ не делать второй restore только потому, что receipt когда-то был PASS.

Нужна новая reconciliation/recovery decision.

==================================================
5. RECEIPT SEMANTICS
==================================================

Не уничтожать исторический факт:

target действительно мог быть физически restored ранее.

Поэтому различить:

1. historical action receipt:
   rollback реально восстановил target и immediate post-check был PASS;

2. current/final verification:
   target всё ещё находится в restore state на момент overall completion.

Если target после valid restore receipt позже drifted:

- historical receipt сохраняется;
- overall rollback НЕ SUCCESS;
- target считается unresolved/currently drifted;
- Recovery Report не должен ложно говорить, что весь rollback успешно завершён.

Выбери минимальное schema-compatible решение.

Допустимый вариант:

- target переводится в FAILED/DRIFTED current status;
- historical receipt сохраняется;
- failure содержит код вроде:
  POST_RECEIPT_DRIFT
  /
  FINAL_VERIFICATION_DRIFT;
- report logic отдельно различает:
  historical physical rollback
  и
  current verified completion.

Если для этого нужно минимально расширить target status / receipt schema — допустимо.

НЕ вводить новую глобальную Operation/Microtask state machine.

==================================================
6. NOOP TARGETS
==================================================

Final full-target proof обязателен также для NOOP targets.

NOOP означает:

в момент проверки physical mutation не требовалась.

Он НЕ означает:

этот target можно больше не проверять.

Сценарий:

NOOP target PASS
→ другой target восстанавливается
→ внешний writer меняет NOOP target
→ overall SUCCESS

тоже должен fail-closed.

Добавить отдельный regression test.

==================================================
7. RESUME / INTERRUPTION
==================================================

После interrupted rollback:

RESTORED target с receipt
не должен автоматически считаться current-good только потому, что receipt существует.

При resume:

- APPLYING target по-прежнему reconcile по current bytes;
- ранее RESTORED/NOOP target тоже должен быть проверен относительно expected_restore перед eventual VERIFIED;
- drift → no blind rewrite.

То есть собственные прошлые effects разрешают не использовать старый full evidence fingerprint буквально,
НО заменой должна быть target-by-target current proof,
а не доверие status enum.

==================================================
8. RECOVERY REPORT
==================================================

Проверить semantics после repair.

Требование:

ROLLBACK_REQUESTED
≠
historically restored target
≠
fully VERIFIED rollback.

Если target был restored, получил receipt, а затем drifted:

Recovery Report может сохранять доказанный исторический факт physical rollback,
НО:

- overall rollback_receipt не SUCCESS;
- target должен быть виден как unresolved/drifted;
- NEXT SAFE ACTION требует reconciliation/manual recovery;
- report не должен утверждать full successful rollback.

Caller claims без backing persistent evidence по-прежнему reject.

==================================================
9. ОБЯЗАТЕЛЬНЫЕ НОВЫЕ TESTS
==================================================

TEST A — главный blocker reproduction:

multi-target rollback:

A restored
→ receipt persisted

перед restore B:
external writer меняет A

B restored successfully

Ожидание:

- overall != SUCCESS;
- status != VERIFIED;
- A current bytes остаются external bytes;
- A НЕ переписывается второй раз;
- persistent state показывает A drift/unresolved;
- historical receipt A не теряется;
- NEXT SAFE ACTION требует reconciliation;
- claims не освобождаются как successful verified rollback.

Этот тест ДО repair обязан падать на commit 152.

TEST B — NOOP final drift:

A = NOOP / pre-state
→ NOOP receipt/status сформирован

пока выполняется другой target:
external writer меняет A

Ожидание:

- no VERIFIED/SUCCESS;
- внешний drift не перезаписывается;
- A unresolved/drifted.

TEST C — clean multi-target success:

без внешнего drift:

- final full-target verification PASS;
- VERIFIED;
- SUCCESS;
- claims released.

TEST D — resume:

один target уже имеет RESTORED receipt,
process/retry/resume происходит,
target после receipt изменён внешним writer.

Ожидание:

- no blind second restore;
- no SUCCESS;
- drift persistent.

TEST E — Recovery Report:

receipt existed historically,
но final drift произошёл.

Ожидание:

- report не выдаёт rollback session за SUCCESS;
- unresolved/drift виден;
- authoritative NEXT требует reconciliation.

==================================================
10. НЕ РАСШИРЯТЬ SCOPE
==================================================

В рамках repair НЕ делать:

- RC-5;
- projection redesign;
- RC-6;
- WA4-E;
- normal mutation executor;
- UI;
- strict rollout;
- lease/heartbeat;
- `.gitattributes`;
- line-ending normalization;
- unrelated refactor.

Лимит preserved-state 1 MiB:

НЕ blocker этого repair.

Пока оставить как conservative fail-closed policy:

если current bytes нельзя сохранить из-за лимита
→ PRESERVATION_FAILED
→ zero destructive mutation.

Зафиксировать как known limitation / future policy decision.

Legacy direct CLI `snapshot restore`:

НЕ blocker этого repair.

Не менять сейчас.
Оставить follow-up для strict rollout / WA4-R, где legacy bypass должен быть закрыт принятой политикой.

==================================================
11. VERIFICATION ПОСЛЕ REPAIR
==================================================

Обязательно:

1. новые blocker tests A–E;

2. весь:
   test_web_alarm_rollback.py

3.:
   test_web_alarm_rollback_concurrency.py

4. RC-3 focused regressions;

5. RC-2 focused regressions;

6. full Web Alarm regression;

7.
python -B -m compileall -q web_alarm

8.
git diff --check

9. fresh-process reopen repaired scenarios;

10. live storage read-only compatibility;
    никаких изменений live storage.

==================================================
12. REPORT
==================================================

Дополнить существующий:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-006_RC4/rc4_report.md

новым разделом:

INDEPENDENT REVIEW REPAIR

В нём указать:

- blocker;
- root cause;
- exact repair;
- final full-target verification model;
- historical receipt vs current verification semantics;
- новые tests;
- результаты regressions;
- known limitation 1 MiB;
- legacy direct restore deferred to WA4-R;
- RC-5 NOT STARTED.

==================================================
13. ПЕРСОНАЛЬНАЯ КАРТОЧКА
==================================================

Это repair той же:

CLAUDE-WA-006 / RC-4

а НЕ новая RC-5 TASK.

После repair:

1. БЛОК 2 должен сохранить исходную полную CLAUDE-WA-006 постановку
   и добавить/сохранить эту repair-постановку как продолжение той же TASK.
   Не потерять исходный RC-4 assignment.

2. БЛОК 3 обновить фактическим результатом repair.

3. Статус:
   RESULT READY / AWAITING INDEPENDENT VERIFICATION

4. После подтверждения БЛОКОВ 2–3:
   БЛОК 1 снова очистить до:

   Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
   TASK: —

5. Не писать DONE / VERIFIED.

6. Не менять:
   - 001;
   - 06;
   - 25;
   - глобальный 000.

Их синхронизирует ChatGPT только после independent PASS.

Не commit / push.

NEXT SAFE ACTION:
закрыть только этот RC-4 blocker,
остановиться на RESULT READY / AWAITING INDEPENDENT VERIFICATION,
RC-5 НЕ начинать.
```

## Дополнение — Independent Review Repair #2 (постановка из БЛОКА 1, 2026-10-04, дословно)

```text
TASK: CLAUDE-WA-006 — RC-4 INDEPENDENT REVIEW REPAIR #2:
Protect the full verification target set from concurrent RC-3 owners

Статус:
REPAIR REQUIRED / RC-4 NOT VERIFIED

Исполнитель:
Claude Opus 5.5

Контекст:
Это продолжение той же CLAUDE-WA-006 / RC-4.
Это НЕ RC-5.

Проверяемый commit:
153
626716436044e649fc7a311400ca42dbfeb2a98a

Первый independent-review blocker
(receipt history != current final state)
закрыт правильно.

Independent verification ChatGPT подтвердила:

- новые repair tests A–E проходят;
- focused RC-4 + concurrency: 31/31 PASS;
- compileall PASS.

НО найден второй concurrency blocker.

RC-4 пока НЕ DONE / VERIFIED.
RC-5 НЕ начинать.

==================================================
1. BLOCKER
==================================================

Финальная full-target verification RC-4 проверяет также NOOP targets.

Но текущий rollback ownership / target lock acquisition выполняется только для:

mutating = targets where planned_action != NOOP

То есть NOOP target:

- входит в rollback target set;
- входит в final full-target proof;
- влияет на VERIFIED / SUCCESS;
- НО rollback не держит на нём RC-3 ownership;
- rollback не держит его target-lock в течение final verification → SUCCESS boundary.

Из-за этого другая normal RC-3 operation может легально получить mutation authority на NOOP target во время rollback.

==================================================
2. INDEPENDENT REPRODUCTION
==================================================

ChatGPT воспроизвёл следующий сценарий на commit 153:

1. RC-4 rollback имеет:
   - один mutating target;
   - один NOOP target.

2. RC-4 выполняет final full-target proof.

3. До окончательного persistence/return VERIFIED,
   другая TASK создаёт normal Operation Contract v2 на NOOP target.

4. Через обычный RC-3:

   acquire
   → ACQUIRED

   mutation_boundary
   → AUTHORIZED
   → mutation_authority = True

5. Другая operation меняет NOOP target.

6. RC-4 продолжает финализацию.

Фактический результат:

FOREIGN_ACQUIRE ACQUIRED
FOREIGN_AUTH AUTHORIZED True

RESULT VERIFIED
STATUS VERIFIED
OVERALL SUCCESS
FINAL_VERIFIED True

при этом:

KEEP_CURRENT != KEEP_EXPECTED

То есть RC-4 объявил VERIFIED/SUCCESS,
хотя один target полного restore set уже изменён другой авторизованной operation.

Это acceptance blocker.

==================================================
3. ROOT CAUSE
==================================================

Проверить:

web_alarm/rollback_service.py

В apply():

mutating = [
    target
    for target in record["targets"]
    if target["planned_action"] != NOOP
]

Target locks берутся только по `mutating`.

`_acquire_all(...)` также получает только `mutating`.

Поэтому NOOP target:

- не получает rollback-owned RC-3 claim;
- не защищён от другой RC-3 operation;
- но `_prove_current()` использует его как часть final all-target proof.

Комментарий:

“final full-target verification under the still-held locks”

фактически неверен для NOOP targets:
их lock не удерживается.

==================================================
4. REQUIRED INVARIANT
==================================================

Если target входит в набор, от которого зависит:

rollback.status = VERIFIED
result.overall = SUCCESS

то его состояние должно быть защищено от конкурентной RC-3 mutation
на всём final verification → VERIFIED persistence boundary.

Нельзя:

verify target
→ отпустить/не иметь ownership
→ другой authorized writer меняет target
→ записать SUCCESS.

Для cooperative Web Alarm writers финальная proof-boundary должна быть механически защищена RC-3 ownership.

==================================================
5. EXPECTED DESIGN
==================================================

Предпочтительный минимальный вариант:

rollback должен получить temporary rollback ownership также для NOOP targets,
если они участвуют в full-target verification.

То есть разделить:

PHYSICAL ACTION:
- WRITE_RESTORE
- DELETE_CREATED
- NOOP

от:

ROLLBACK VERIFICATION OWNERSHIP:
- все targets, входящие в restore-point / final success proof.

Rollback не обязан физически писать NOOP target.

Но до final VERIFIED он обязан исключить concurrent RC-3 mutation этого target.

Возможная схема:

all_targets
→ acquire rollback RC-3 ownership in deterministic target-hash order

mutating_targets
→ perform physical restore/delete

noop_targets
→ no physical mutation

all_targets
→ final exact physical proof

VERIFIED persistence / receipts

all_targets claims
→ release

Главное:
не создавать отдельный bypass-lock для NOOP.

Использовать тот же RC-3 canonical physical-target conflict layer.

==================================================
6. SOURCE OPERATION CLAIM EDGE CASE
==================================================

Существующая логика takeover source operation claim должна сохраниться.

Если source operation уже владеет target:
→ rollback может корректно supersede/take over,
как реализовано RC-4.

Это должно одинаково работать и для target, который в rollback оказался NOOP.

Не создавать два active owners.

==================================================
7. NO PHYSICAL MUTATION FOR NOOP
==================================================

Важно:

получение rollback ownership на NOOP target
НЕ означает, что его надо переписывать.

NOOP остаётся:

- exact current state == expected restore;
- physical write/delete отсутствует;
- receipt action = NOOP.

Ownership нужен только как concurrency barrier
на время tracked rollback verification.

==================================================
8. FULL FINALIZATION BOUNDARY
==================================================

Перед VERIFIED:

rollback должен всё ещё удерживать ownership/target-lock для ВСЕХ targets,
участвующих в success proof.

Порядок:

1. ownership all targets proved;
2. per-target restore/no-op;
3. final `_prove_current()` all targets;
4. persist:
   VERIFIED / SUCCESS / final_verification=true;
5. только после этого release all rollback claims;
6. return VERIFIED.

Не должно существовать окна:

final proof
→ target becomes writable by another RC-3 owner
→ SUCCESS persistence.

Если текущий persistence/release ordering технически требует другого порядка,
решение должно всё равно сохранять этот инвариант.

==================================================
9. RAW EXTERNAL WRITERS
==================================================

RC-3 locks не могут остановить произвольный editor / Git / внешний процесс,
который игнорирует Web Alarm.

RC-4 не обязан обеспечивать filesystem transaction против любого внешнего OS writer.

Но:

- final physical proof обязателен;
- cooperative Web Alarm / RC-3 writer НЕ должен иметь authority внутри protected finalization window.

Этот repair именно про RC-3-authorized concurrent writer.

Не пытаться строить OS filesystem locking / leases вне текущей архитектуры.

==================================================
10. REQUIRED TESTS
==================================================

TEST F — exact blocker reproduction:

Rollback target set:
- A = mutating target;
- B = NOOP target.

До/во время finalization другая TASK пытается:

RC-3 acquire B
→ mutation_boundary
→ write B.

Нужно доказать:

пока rollback владеет verification window:

foreign acquire/authority НЕ может одновременно победить.

Допустимый deterministic результат:

rollback wins:
- foreign operation gets CONFLICT/DENIED until rollback completes;
- final SUCCESS valid;

ИЛИ foreign owner wins BEFORE rollback obtains all-target ownership:
- rollback blocked before destructive phase;
- no false SUCCESS.

НЕЛЬЗЯ:

foreign AUTHORIZED
+
rollback VERIFIED
на одном temporal window.

TEST G — NOOP target receives rollback claim:

после acquire-all:
- NOOP target active claim owner.kind = ROLLBACK;
- rollback_id matches;
- no physical mutation performed.

TEST H — NOOP source-operation claim takeover:

source op already holds claim on NOOP target;
rollback safely supersedes/takes it over;
no duplicate owner.

TEST I — clean rollback:

all-target ownership
→ final verification PASS
→ VERIFIED/SUCCESS
→ all rollback claims released.

TEST J — conflict on NOOP target before destructive phase:

foreign owner already owns NOOP target.

Expected:
- rollback blocked;
- zero destructive writes on all other targets;
- no partial rollback ownership left.

TEST K — multiprocess:

rollback vs normal RC-3 operation competing specifically for a NOOP target.

Invariant:
never both obtain mutation authority.

==================================================
11. REGRESSION REQUIREMENTS
==================================================

After repair run:

- all FinalVerificationRepairTests;
- all RC-4 tests;
- RC-4 concurrency;
- RC-3 focused + concurrency;
- RC-2 focused;
- full Web Alarm regression;
- compileall;
- git diff --check;
- fresh-process reopen;
- live storage read-only compatibility.

==================================================
12. SCOPE
==================================================

Do NOT expand into:

- RC-5;
- RC-6;
- WA4-E;
- UI;
- normal mutation executor;
- lease/heartbeat;
- OS-level file locking;
- `.gitattributes`;
- line-ending normalization;
- unrelated refactor.

1 MiB preservation limit:
still known fail-closed limitation, not blocker here.

Legacy direct snapshot restore:
still deferred to WA4-R / strict rollout.

==================================================
13. REPORT
==================================================

Дополнить тот же:

Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-006_RC4/rc4_report.md

разделом:

INDEPENDENT REVIEW REPAIR #2

Зафиксировать:

- reproduction;
- root cause: NOOP target outside RC-3 ownership set;
- exact ownership model after repair;
- lock/claim ordering;
- new tests F–K;
- regressions;
- RC-5 NOT STARTED.

==================================================
14. CARD ROTATION
==================================================

Это всё ещё CLAUDE-WA-006 / RC-4.

После repair:

1. БЛОК 2 сохраняет:
   - исходную RC-4 постановку;
   - repair #1;
   - эту repair #2.

2. БЛОК 3 обновляется новым factual result.

3. Статус:
   RESULT READY / AWAITING INDEPENDENT VERIFICATION

4. Только после подтверждения сохранности БЛОКОВ 2–3:
   очистить БЛОК 1:

   Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
   TASK: —

5. Не писать DONE / VERIFIED.

6. Не менять:
   - 001;
   - 06;
   - 25;
   - глобальный 000.

7. Не commit / push.

NEXT SAFE ACTION:
закрыть только RC-4 repair #2,
остановиться на RESULT READY / AWAITING INDEPENDENT VERIFICATION,
RC-5 НЕ начинать.
```

---
# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ
---

**TASK:** CLAUDE-WA-006 — RC-4: Tracked safe rollback (+ repair #1: final full-target verification; + repair #2: full verification target set under RC-3 ownership).
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION — 2026-10-04, повторно после repair #2. DONE не объявлен; commit / push не выполнялись; **RC-5 NOT STARTED**.

**Предыдущие этапы:** исходный RC-4 — commit 152 `42ce550`; repair #1 (receipt ≠ доказательство текущего состояния) — commit 153 `6267164`.

**Blocker repair #2:** NOOP-цель входила в финальное доказательство, но rollback не держал на ней ни target lock, ни RC-3 claim. Чужая RC-3 операция могла получить AUTHORIZED и записать эту цель между финальной проверкой и VERIFIED. Воспроизведено: на commit 153 тест F даёт `ACQUIRED, AUTHORIZED` + `VERIFIED`.

**Что сделано (`web_alarm/rollback_service.py`):**
- Физическое действие отделено от владения ради проверки. Lock'и всех целей берутся по `target_hash`, RC-3 claims — all-or-nothing на все цели, включая NOOP (NOOP по-прежнему не пишется). Используется тот же слой RC-3, без отдельного bypass-lock.
- Claim исходной операции на NOOP-цели перехватывается (`SUPERSEDED_BY_ROLLBACK`); второго владельца нет.
- `_prove_current` доказывает и байты, и владение. `_finalize` сначала записывает VERIFIED и только потом снимает claims (всё под lock'ами всех целей). Прерванное снятие идемпотентно доделывают `apply` / `close`.
- Adversarial pass, исправлено внутри scope:
  - сессию, заблокированную после собственных восстановлений, теперь можно закрыть (раньше её claims оставались навсегда);
  - цель в полёте доказывается по байтам до того, как требуется restore point;
  - совет NEXT SAFE ACTION для такой сессии.

**Файлы:**
- `web_alarm/rollback_service.py` (+103 / −48);
- `test_web_alarm_rollback.py` (+267 / −1: класс `FullTargetOwnershipRepairTests`, 11 тестов);
- `test_web_alarm_rollback_concurrency.py` (+86 / −8: тест K в реальных процессах).

Формат записей, `rollback_store.py`, RC-3, Resolver, server и report не менялись.

**Тесты:**
- F–K и дополнительные — все падали на commit 153, теперь OK;
- `test_web_alarm_rollback.py` — 41/41; concurrency — 2/2; RC-3 focused — 20/20; RC-2 focused — 41/41;
- полный Web Alarm — **329/329 OK** (skip 1);
- compileall и `git diff --check` OK;
- живое storage (read-only) не изменилось: 136 файлов, rollback-сессий и claim-файлов нет.

**FINDING / PROPOSAL (вне scope, код не менял):**
- P1: в Recovery Report поля `restored` / `noop` сессии исторические (на момент финализации) — предложено маркировать их `as_of` в проекции RC-5.
- P2: NOOP-цели теперь заблокированы на всё время `apply`; RC-3 writer ждёт до `lock_timeout` — учесть в WA4-E.

**Совместимость:** сессии 152/153, прерванные посреди `apply`, вслепую не продолжаются (`CLAIM_LOST` или `PARTIAL`, 0 записей, `close` работает). В живом storage таких сессий нет.

**Ограничения (не blocker):** preserved-state 1 МиБ — fail-closed политика; старый CLI `snapshot restore` — follow-up WA4-R.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-006_RC4/rc4_report.md` (§19 — repair #2, §18 — repair #1); safety copies — `safety_copies/repair2/`, хеши — `baseline.md`.

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
