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

Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ
TASK: —

---
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА
---

**Статус постановки:** выполнена Claude 2026-10-04; результат и статус — в БЛОКЕ 3. Ниже — полная постановка из БЛОКА 1 дословно (fenced-блок сохраняет разбивку строк).

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

---
# БЛОК 3 — РЕЗУЛЬТАТ ПОСЛЕДНЕЙ ВЫПОЛНЕННОЙ ЗАДАЧИ
---

**TASK:** CLAUDE-WA-006 — RC-4: Tracked safe rollback + preserved current state + persistent receipts.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION — 2026-10-04. DONE не объявлен; commit / push не выполнялись; **RC-5 NOT STARTED**.

**Что сделано:**
- ROLLBACK из запроса RC-2 стал отдельной tracked recovery operation: принятая fresh резолюция ROLLBACK → persistent-сессия (`rollback_id` выводится из резолюции; повтор возвращает ту же сессию);
- текущее состояние **всех** целей сохраняется до деструктивной фазы (байты content-addressed вне репозитория, проверка hash+size; absence фиксируется явно); сбой хотя бы одной цели → `PRESERVATION_FAILED`, без мутаций;
- проверенный side-effect-free `restore_plan()` из существующего restore point WA-1 (без второго snapshot-мира);
- атомарное владение RC-3 всеми изменяемыми целями: конфликт на одной цели блокирует всю фазу;
- CAS по каждой цели перед мутацией: точные байты snapshot либо удаление созданного файла, post-read, persistent receipt по цели;
- итог строится из receipts; VERIFIED только при доказанном полном наборе;
- сбой в середине разбирается по байтам (восстановленное не перезаписывается); повтор VERIFIED не даёт побочных эффектов;
- Recovery Report: `actually_rolled_back` — только из проверенных receipts; новое поле `rollback_receipts` (PARTIAL виден явно); заявки вызывающего без receipt отклоняются.

**Файлы:**
- новые: `web_alarm/rollback_store.py`, `web_alarm/rollback_service.py`, `test_web_alarm_rollback.py` (25), `test_web_alarm_rollback_concurrency.py` (1 тест, 4 раунда);
- изменённые: `manifest_store.py` (+68, `restore_plan`), `target_claim_store.py` / `target_claim_service.py` (claim `owner` = ROLLBACK; RC-3 видит его как чужого владельца), `recovery_report_store.py` / `_builder.py` / `_service.py`, `server.py` (+51, `/tasks/<t>/rollbacks[/<id>/apply|close]`), `__init__.py`;
- `models.py`, `OperationStatus`, `operation_store`, контракт, Resolver, reconciliation и UI не менялись.

**Тесты:**
- полный Web Alarm — **312/312 OK** (skip 1); RC-1/2/3 focused — 115/115;
- гонка rollback против RC-3 — 5/5 прогонов; без блокировок — «два владельца»;
- compileall и `git diff --check` OK;
- живое storage (read-only) не изменилось (136 файлов).

**Ограничения и решения на проверку:**
- свежесть резолюции проверяется полностью до первой мутации, дальше — «с поправкой на свои изменения»;
- claim исходной операции переходит к rollback (`SUPERSEDED_BY_ROLLBACK`);
- PARTIAL / FAILED финальны (`close` + новая reconciliation);
- лимит preservation 1 МиБ — нужно решение для больших файлов;
- старый CLI `snapshot restore` остаётся прямым деструктивным путём (предложение на WA4-R);
- lifecycle и проекция — RC-5;
- после принятия — перезапуск процессов WEB-02.

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-006_RC4/rc4_report.md`; safety copies и `baseline.md` — там же.

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
