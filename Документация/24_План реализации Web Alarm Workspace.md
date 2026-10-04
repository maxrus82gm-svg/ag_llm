# План реализации Web Alarm Workspace

## Статус документа

**IMPLEMENTATION PLAN / ACTIVE — WA-1 + WA-2 + WA-3 DONE / VERIFIED; RT-001 RECOVERY CLOSURE ROUTE APPROVED.**

Этот документ является каноническим планом внедрения Web Alarm Workspace. Архитектурные инварианты и назначение системы принадлежат документу `23_Архитектура Web Alarm Workspace.md`; здесь фиксируются порядок реализации, крупные этапы, критерии приёмки и фактический статус внедрения.

WA-1, WA-2 и WA-3 закрыты как DONE / VERIFIED. RT-001 утвердил correctness-first маршрут перед strict rollout. **RC-0, RC-1 и RC-2 = DONE / VERIFIED — 2026-10-04; RC-3 = следующий разрешённый этап, ещё не запущен.** Статус меняется только после предусмотренной проверки конкретной TASK; незапущенные этапы остаются `PLANNED`.

## Краткая карта реализации

Сначала — только крупные этапы, чтобы план можно было быстро прочитать целиком:

```text
WA-1 — Фундамент состояния и файловое ядро
WA-2 — Локальный Web Alarm Server и простой UI
WA-3 — Remote recovery и replay protection
WA-4 — Строгий mutation gateway и hardening
```

### Канонический маршрут после RT-001 / PLAN APPROVAL `EP-RT001-001`

```text
RC-0 — Baseline + normalization policy
↓
RC-1 — Durable Operation Contract + backward compatibility
↓
RC-2 — Tracked Resolver / evidence revision
↓
RC-3 — Canonical-target conflict gate + CAS
↓
RC-4 — Tracked safe rollback
↓
RC-5 — Projection correctness + pure inspection
↓
RC-6 — Minimal project-level resume
↓
WA4-E — Authoritative Mutation Executor / Gateway
↓
WA4-A — Deterministic lost-response acceptance
↓
WA4-O — UX / operational layer
↓
WA4-R — Strict rollout + final audit
```

Этот маршрут является каноническим порядком исполнения. Подробная planning-история и rationale остаются в `33`; здесь хранятся только порядок, границы и acceptance. Старые WA-4.1–WA-4.7 ниже сохраняются как требования: WA-4.1/4.2 → `WA4-E`; WA-4.3 → RC-1/RC-3 с точной lease/heartbeat моделью deferred по V17; WA-4.4/4.5 — cross-cutting retention/security constraints; WA-4.6 → `WA4-O`; WA-4.7 → `WA4-R`.

| Boundary | Канонический результат / exit proof |
| --- | --- |
| RC-0 | regression/bytes/hash baseline зафиксирован отдельно от вспомогательных метрик; line-ending policy однозначна |
| RC-1 | durable operation contract restart-safe; legacy records читаются совместимо; запись Operation Store/revision межпроцессно защищена |
| RC-2 | ADOPT/RETRY/ROLLBACK/ABORT — persistent tracked resolutions, bound to evidence fingerprint + operation revision; `RETRY` только re-arm; stale/rejected fail-closed; Recovery Report/NEXT reproducible from persisted Resolver state; без physical mutation до `WA4-E` |
| RC-3 | canonical-target conflict gate + mutation-boundary CAS; конфликтующие process не проходят параллельно; race tests PASS |
| RC-4 | rollback tracked; current drift сохранён до destructive restore; intent/receipt/post verification persistent |
| RC-5 | checkpoint rebuildable/validated projection; inspect/verify pure; stale projection fail-closed; Resolver-authoritative recovery/NEXT projection не должна перезаписываться advisory reconciliation |
| RC-6 | одна read-only resume-команда возвращает project/stage, blockers, open operations и один authoritative `NEXT SAFE ACTION`, включая persistent Resolver/Recovery Report state |
| WA4-E | server-owned snapshot→CAS→mutation→post-proof→receipt; replay того же contract не создаёт второй side effect |
| WA4-A | deterministic lost-response fault injection + fresh process возвращает тот же receipt без второй mutation |
| WA4-O | authoritative progress/situation UI без собственного выдуманного execution status |
| WA4-R | OBSERVE→WARN→GATEWAY REQUIRED→STRICT только после полного regression/final audit |

Коротко по смыслу:

- **WA-1** — научить систему хранить TASK, микрозадачи, manifest, snapshots, checkpoints и отчёты на диске.
- **WA-2** — поднять локальный сервер и понятную оболочку, через которую ChatGPT и пользователь видят текущее состояние TASK.
- **WA-3** — доказать восстановление после обрыва Remote/Chat и защититься от повторного выполнения неизвестной операции.
- **WA-4** — сделать Web Alarm Workspace настоящим контролируемым mutation gateway и подготовить его к регулярной работе.

Далее каждый этап расписан подробно: подзадачи, ожидаемое поведение, критерии приёмки и контрольные точки.

## 1. Цель программы

Нужно превратить существующую ручную схему Remote-continuity в отдельную локальную систему, которая переживает обрыв Desktop Commander, смену Chat и перезапуск собственного процесса без потери состояния TASK.

Итоговый пользовательский сценарий должен быть простым:

```text
пользователь создаёт / вставляет TASK
↓
ChatGPT входит в Web Alarm Workspace
↓
TASK разбивается на микрозадачи
↓
перед изменением файлов создаётся и проверяется snapshot
↓
работа идёт в реальном Workspace
↓
состояние и отчёты сохраняются независимо от Chat
↓
после обрыва новый Chat продолжает с последней доказанной точки
```
## 2. Принципы реализации

1. **Не ломать текущий рабочий процесс сразу.** Существующие `Alarm/ALARM_TASK_SESSION` и ручные safety-backup остаются fallback, пока новая система не пройдёт проверку.
2. **Сначала наблюдаемость и хранение состояния, потом жёсткий gate.** Первая версия должна помогать и дисциплинировать, а не становиться единственной точкой отказа.
3. **Реальный проект остаётся снаружи.** Web Alarm Workspace не копирует весь проект и не превращает его в sandbox.
4. **Runtime-state Web Alarm желательно хранить вне управляемого Workspace.** Это позволяет одной системе обслуживать несколько проектов и не загрязнять их рабочие директории.
5. **Машинное состояние и человеческое представление разделяются.** JSON/JSONL — источник состояния; Markdown — читаемый handoff и отчёт.
6. **Все переходы state machine валидирует сервер.** ChatGPT предлагает действие, сервер отвечает, допустимо ли оно сейчас.
7. **Recovery проектируется с первой версии.** Его нельзя откладывать «на потом», потому что именно ради него создаётся система.
8. **Никакого автоматического rollback только по факту disconnect.**
9. **Никакого слепого replay изменяющей операции.**
10. **Каждая большая задача внедрения закрывается отдельной проверкой до перехода к следующей.**

## 3. Предлагаемое физическое разделение

Код первой реализации можно разрабатывать внутри `ag_llm` как отдельный модуль, не смешивая его с текущим Agent Runtime.

Рабочее состояние Web Alarm рекомендуется хранить отдельно от обслуживаемых проектов, например:

```text
%LOCALAPPDATA%\WebAlarmWorkspace\
```
Предлагаемая runtime-структура:

```text
WebAlarmWorkspace/
├── config.json
├── workspaces/
│   └── <workspace_id>.json
├── tasks/
│   ├── active/
│   │   └── <task_id>/
│   └── completed/
│       └── <task_id>/
└── logs/
```

Внутри TASK:

```text
<task_id>/
├── task.json
├── task.md
├── plan.json
├── checkpoint.json
├── checkpoint.md
├── events.jsonl
└── microtasks/
    ├── M001/
    ├── M002/
    └── ...
```

Конкретный путь и формат окончательно фиксируются в первой большой задаче после проверки удобства на Windows.
## 4. Большие задачи реализации

### WA-1 — Фундамент состояния и файловое ядро

**Статус: IN PROGRESS — WA-1.1 DONE / VERIFIED**

Цель WA-1 — сделать систему, которая уже умеет надёжно хранить TASK и состояние микрозадач без UI и без строгого server-side запрета на запись.

#### WA-1.1 — Зафиксировать схемы данных

**Статус: DONE / VERIFIED — 2026-10-01.**

Реализован отдельный schema layer `web_alarm/models.py` и focused regression `test_web_alarm_models.py`: зафиксированы versioned records, устойчивые ID, timestamps, статусы recovery/replay и JSON-friendly представление. Focused verification: **7/7 PASS**, `git diff --check` PASS.

Определить машинные схемы для:

- Workspace registration;
- TASK;
- microtask;
- manifest;
- snapshot record;
- operation record;
- verification record;
- checkpoint;
- event log.

Все сущности должны иметь устойчивые ID, timestamps и version/schema revision.

#### WA-1.2 — Реализовать Workspace Registry

**Статус: DONE / VERIFIED — 2026-10-01.**

Реализован `web_alarm/workspace_registry.py`: локальный disk-backed Registry хранит внешние Workspace как отдельные JSON records, сохраняет устойчивый `workspace_id`, не копирует исходный проект, переоткрывается новой инстанцией и fail-closed обрабатывает несуществующий root, file вместо directory, небезопасный ID и неизвестную schema version. Focused verification вместе с WA-1.1 regression: **15/15 PASS**, `git diff --check` PASS.

Система должна уметь зарегистрировать реальный проект:

```text
workspace_id
display_name
workspace_root
```

Workspace root не копируется внутрь Web Alarm Workspace и остаётся исходным местом работы.
#### WA-1.3 — TASK и план микрозадач

**Статус: DONE / VERIFIED — 2026-10-01.**

Реализован `web_alarm/task_store.py` и schema `TaskPlanRecord`: TASK хранится в `tasks/active/<task_id>/` через `task.json`, immutable `task.md`, `plan.json` и отдельные JSON микрозадач; ordered plan/current microtask переживают новую инстанцию storage. `complete_task` переносит директорию в `tasks/completed/`, `archive_task` сохраняет её читаемой со статусом ARCHIVED. Focused WA regression: **25/25 PASS**, `git diff --check` PASS.

Нужны операции:

```text
create_task
open_task
save_raw_task
set_plan
create_microtask
set_current_microtask
complete_task
archive_task
```

Исходная постановка пользователя хранится отдельно от подготовленного плана и не переписывается задним числом.

#### WA-1.4 — Manifest и Snapshot

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/manifest_store.py`: каждая микрозадача получает отдельный `restore_point` с manifest, per-target entry/snapshot records и byte snapshots существующих файлов. Existing target фиксирует `size/sha256/captured_at`; новый target — явный `exists_before=false`. Restore point публикуется только после snapshot reread/hash verification, переживает restart, не перезаписывается повторной подготовкой и поддерживает explicit restore existing/new targets. Corruption, path escape/tampering и invalid restore state блокируются fail-closed; restore validation/mutation failure переводит микрозадачу в `RECOVERY_REQUIRED`. Focused WA regression: **36/36 PASS**, `git diff --check` PASS.

Перед `READY` микрозадача должна иметь manifest всех ожидаемых изменяемых объектов.

Для существующих файлов snapshot сохраняет байтовую копию и минимум:

```text
source_path
exists_before
size
sha256
snapshot_path
captured_at
```

Для отсутствующего до этапа файла фиксируется `exists_before=false`.

Snapshot должен перечитываться после создания, а hash копии должен совпасть с зафиксированным исходным hash.
#### WA-1.5 — Event Log и Checkpoint

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/event_checkpoint_store.py`: append-only `events.jsonl` хранит хронологию фактов, `checkpoint.json` атомарно хранит только актуальное состояние TASK, а `checkpoint.md` генерируется из JSON и содержит `NEXT SAFE ACTION`. Event history переживает restart и не меняется при обновлении checkpoint; corrupted/unknown-schema checkpoint и invalid event line блокируются fail-closed. Focused WA regression: **42/42 PASS**, `git diff --check` PASS.

`events.jsonl` хранит append-only историю переходов и операций.

`checkpoint.json` хранит только актуальное состояние:

```text
task_id
workspace_id
last_verified_microtask
current_microtask
current_status
snapshot_status
last_operation_id
next_safe_action
updated_at
```

`checkpoint.md` может генерироваться из JSON как удобное представление для человека и ChatGPT.

#### WA-1.6 — Базовый CLI

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализованы `web_alarm/cli.py` и `web_alarm/__main__.py`: доступна точка входа `python -m web_alarm` с командами task create/open/complete, microtask create/prepare, snapshot verify/restore, checkpoint write/show, status и report. CLI работает с явным `--storage-root`, использует существующие WA-1.1–WA-1.5 storage layers без обхода их проверок, ошибки возвращают ненулевой exit code и `ERROR:` в stderr. Focused CLI + полный WA regression: **47/47 PASS**, module-entrypoint smoke PASS, `git diff --check` PASS.

До появления UI нужен минимальный локальный CLI:

```text
webalarm task create
webalarm task open
webalarm status
webalarm microtask prepare
webalarm snapshot create
webalarm checkpoint
webalarm report
webalarm task complete
```

CLI нужен прежде всего для тестирования ядра и работы через Desktop Commander.
#### WA-1 — Критерии приёмки

WA-1 считается завершённой, если:

- можно зарегистрировать минимум два разных Workspace;
- можно создать TASK и разбить её на микрозадачи;
- после перезапуска процесса состояние TASK восстанавливается с диска;
- микрозадача не получает `READY`, пока manifest/snapshot неполны;
- существующий файл восстанавливается из snapshot побайтно;
- новый файл корректно обозначается как `exists_before=false`;
- event log не теряет историю при обновлении checkpoint;
- completed TASK переносится в архив без потери отчётов и snapshots;
- повторное открытие TASK показывает точный `NEXT SAFE ACTION`.

**Результат WA-1:** работающая файловая основа Web Alarm Workspace без зависимости от конкретного Chat.

---

### WA-2 — Локальный Web Alarm Server и простой интерфейс

**Статус: IN PROGRESS — WA-2.1 DONE / VERIFIED**

Цель WA-2 — вынести правила state machine в постоянно работающий локальный сервер и сделать удобную точку входа для человека и ChatGPT.

Сервер должен слушать только локальный интерфейс по умолчанию и не требовать публикации наружу.
#### WA-2.1 — Server API

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/server.py`: stdlib `ThreadingHTTPServer` по умолчанию слушает только loopback, API остаётся advisory и использует WA-1 stores без обхода их проверок. Реализованы status/workspaces/tasks/plan/microtasks/prepare/snapshot-verify/report/recovery-entry endpoints; server-side restore намеренно не экспонирован, чтобы WA-2.1 не делал скрытых мутаций реального Workspace. TASK creation требует существующий registered Workspace. Реальный loopback HTTP smoke и полный WA regression: **57/57 PASS**, `git diff --check` PASS.

Нужны узкие операции уровня протокола, например:

```text
GET  /status
POST /workspaces
POST /tasks
GET  /tasks/{id}
POST /tasks/{id}/plan
POST /tasks/{id}/microtasks
POST /microtasks/{id}/prepare
POST /microtasks/{id}/snapshot
POST /microtasks/{id}/transition
POST /microtasks/{id}/report
POST /tasks/{id}/recover
```

Имена endpoint могут измениться, но смысл должен остаться узким и typed.

#### WA-2.2 — Server-owned state machine

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/state_machine.py` и интеграция в `web_alarm/server.py`: Server теперь авторитетно разрешает/запрещает переходы microtask, не позволяет клиенту сфабриковать `PREPARING/BACKUP_VERIFIED`, проверяет verified restore point перед `READY/ACTIVE`, требует verification evidence для `DONE → VERIFIED`, не позволяет следующей микрозадаче стартовать до VERIFIED предыдущей, ведёт event log/checkpoint и вычисляет `NEXT SAFE ACTION` из фактического статуса. Rejected transition возвращает 409 с current/requested status, причиной и `NEXT SAFE ACTION`. Focused + полный WA regression: **64/64 PASS**, `git diff --check` PASS.

Переходы между состояниями проверяет сервер.

Пример недопустимого перехода:

```text
PLANNED → ACTIVE
```

если нет `BACKUP_VERIFIED / READY`.

Сервер обязан вернуть понятную причину отказа и актуальный `NEXT SAFE ACTION`.
#### WA-2.3 — Минимальный UI

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/ui.py` и read-only aggregate `GET /tasks/{id}/ui`: Server отдаёт локальный HTML/JS dashboard по `/`/`/ui` без внешних CDN/frameworks. UI показывает Workspace, active/completed TASK, создаёт TASK из RAW text с выбранным Workspace, отображает RAW TASK, plan/microtasks, checkpoint, manifest/snapshot, reports, recovery state и крупный `NEXT SAFE ACTION`. Пользовательские данные рендерятся через `textContent`, passive detail view не мутирует реальный Workspace. Реальный HTTP UI smoke и полный WA regression: **69/69 PASS**, `git diff --check` PASS.

Первая оболочка не должна быть сложной. Достаточно экранов:

- список Workspace;
- active/completed TASK;
- исходная TASK;
- план микрозадач;
- текущий checkpoint;
- manifest текущего этапа;
- snapshot status;
- короткие отчёты;
- recovery state;
- `NEXT SAFE ACTION`.

Пользователь должен иметь возможность вставить новую TASK обычным текстом и выбрать Workspace, с которым она связана.

#### WA-2.4 — Entry Context Pack

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/context_pack.py` и read-only `GET /tasks/{id}/context`: одним запросом Server формирует restart-safe Entry Context Pack из persistent TASK/Workspace/plan/checkpoint/state-machine без чтения полной event history. Pack содержит все обязательные поля, отдельный компактный `CONTEXT_TEXT`, не зависит от накопленного event noise, не мутирует Workspace и после новой инстанции builder возвращает ту же авторитетную рабочую точку. Полный WA regression: **75/75 PASS**, `git diff --check` PASS.

Сервер должен уметь выдавать один компактный пакет для нового Chat:

```text
TASK
WORKSPACE
GOAL
PLAN SUMMARY
LAST VERIFIED
CURRENT MICROTASK
CURRENT STATUS
SNAPSHOT STATUS
LAST OPERATION
NEXT SAFE ACTION
PROTOCOL RULES
```

Этот пакет должен быть достаточно мал, чтобы новый Chat мог начать работу без чтения всей истории TASK.
#### WA-2 — Критерии приёмки

WA-2 считается завершённой, если:

- сервер поднимается локально и восстанавливает state после restart;
- UI показывает active/completed TASK и все микрозадачи;
- пользователь может создать TASK из текста и связать её с Workspace;
- invalid state transition физически отклоняется сервером;
- `NEXT SAFE ACTION` вычисляется из текущего состояния, а не хранится как произвольный текст Chat;
- Entry Context Pack выдаётся одной операцией;
- никакой endpoint не делает скрытую мутацию реального проекта без отдельного шага подготовки;
- текущие Alarm-файлы остаются рабочим fallback.

**Результат WA-2:** отдельная локальная оболочка уже может использоваться как диспетчер TASK, даже если фактические file mutations пока выполняются обычными инструментами Remote.

---

### WA-3 — Remote workflow, recovery и replay protection

**Статус: IN PROGRESS — WA-3.1 + WA-3.2 + WA-3.3 + WA-3.4 DONE / VERIFIED; WA-3.5 PREPARED / CODE NOT STARTED.**

Цель WA-3 — сделать Web Alarm Workspace устойчивым именно к тому классу сбоев, из-за которого система создаётся: потеря ответа, reconnect, смена Chat и повторная доставка действия.

#### WA-3.1 — Канонический Remote entry

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/remote_entry.py` и CLI-входы `webalarm enter [--task-id]` / `webalarm status --active`. Canonical entry fail-closed определяет ровно одну active TASK; при 0 или нескольких active TASK требует явный `--task-id`, completed TASK не принимает как active. Результат read-only включает Entry Context Pack и `ENTRY_STATE`: abnormal recovery-status переводит вход в `RECOVERY_REVIEW_REQUIRED` с `RECONCILE_BEFORE_MUTATION`. После реального сброса связи перед продолжением WA-3.1 выполнен disk reconciliation: restore point и pre-state подтвердились, blind replay не выполнялся. Полный WA regression: **82/82 PASS**, `git diff --check` PASS.

Для ChatGPT нужен один стандартный вход, например:

```text
webalarm enter
webalarm status --active
```

В ответ Chat получает Entry Context Pack и не начинает мутацию до проверки текущего состояния.
#### WA-3.2 — Operation ID

**Статус: DONE / VERIFIED — 2026-10-02.**

Реализован `web_alarm/operation_store.py` и typed Server endpoints для persistent operation identity. Новый `operation_id` публикует `INTENT` с canonical request fingerprint; повтор того же ID с тем же request возвращает существующую запись, а конфликтующий request fail-closed получает 409. Lifecycle `INTENT → STARTED → DONE → VERIFIED / FAILED / UNKNOWN_AFTER_DISCONNECT` допускает только разрешённые переходы; повтор текущего/terminal состояния идемпотентен. Replay в `STARTED` или `UNKNOWN_AFTER_DISCONNECT` возвращает `RECONCILE_REQUIRED`, а не повтор mutation. Состояние переживает новую Store/Server instance и само не выполняет real-project mutation. Полный WA regression: **90/90 PASS**, `git diff --check` PASS.

Перед изменяющей операцией Web Alarm Server создаёт или принимает устойчивый `operation_id`.

Минимальные состояния:

```text
INTENT
STARTED
DONE
VERIFIED
FAILED
UNKNOWN_AFTER_DISCONNECT
```

Один и тот же `operation_id` не должен создавать вторую независимую мутацию.

Повторный запрос обязан вернуть уже известное состояние операции или перевести её в recovery, если результат нельзя доказать.

#### WA-3.3 — Reconciliation

**Статус: DONE / VERIFIED — WA-3.3.1–WA-3.3.4 complete.**

**Execution split:**
- WA-3.3.1 — Reconciliation Evidence / read-only inspector — **DONE / VERIFIED**;
- WA-3.3.2 — deterministic Decision Engine — **DONE / VERIFIED**;
- WA-3.3.3 — Server / Remote integration — **DONE / VERIFIED**;
- WA-3.3.4 — recovery scenarios / final verification — **DONE / VERIFIED**.

WA-3.3.1 реализован в `web_alarm/reconciliation.py`. Collector read-only собирает operation binding, manifest/snapshot pre-state, current exists/size/SHA256, optional exact expected post-state, verification evidence и per-target признаки `MATCHES_PRE_STATE`, `MATCHES_EXPECTED_POST_STATE`, `DRIFT_DETECTED` / `MISSING_EVIDENCE`. Snapshot integrity проверяется без вызова mutating `verify_restore_point`, поэтому даже corrupted snapshot не меняет manifest/microtask status. Focused regression 10/10 PASS; полный WA regression **100/100 PASS**.

WA-3.3.2 реализован в `web_alarm/reconciliation_decision.py`. Pure engine детерминированно выдаёт только `ADOPT_CURRENT_STATE`, `RETRY_SAFE`, `ROLLBACK_CURRENT_MICROTASK` или `MANUAL_REVIEW_REQUIRED`, привязывая результат к SHA256 fingerprint всего evidence. `DRIFT`/`MISSING_EVIDENCE`/`CHANGED_UNCLASSIFIED`, conflicting lifecycle/evidence и неполный exact post-state fail-closed уходят в manual review. Любой результат содержит `automatic_mutation_authorized=false`: engine ничего не исполняет. Первый focused run выявил один policy defect — exact post-state при lifecycle `INTENT` ошибочно принимался как ADOPT; правило исправлено на `LIFECYCLE_CONTRADICTS_POST_STATE`. После repair focused **16/16 PASS**, полный WA regression **116/116 PASS**, py_compile и `git diff --check` PASS.

WA-3.3.3 реализован через `web_alarm/reconciliation_service.py` и интеграцию в Server, Entry Context Pack и Canonical Remote Entry. Server получил read-only reconcile endpoint; Context Pack подмешивает reconciliation bundle и authoritative `NEXT SAFE ACTION`; Remote Entry отдаёт reconciliation decision без исполнения recovery mutation. Focused integration **7/7 PASS**, независимый full WA regression **123/123 PASS**, restart-specific fresh-process checks **3/3 PASS**, py_compile и diff-check PASS. На этапе recovery дополнительно доказано, что результат и decision переживают новый Server/Python process.

WA-3.3.4 закрывает recovery-matrix без runtime-правок. Session A доказала четыре базовых исхода (`RETRY_SAFE`, `ADOPT_CURRENT_STATE`, `ROLLBACK_CURRENT_MICROTASK`, `MANUAL_REVIEW_REQUIRED`) → **4/4 PASS**. Session B добавила `UNKNOWN_AFTER_DISCONNECT`, duplicate delivery, fresh service instance, new-file, delete-file и corrupted snapshot → **10/10 PASS**. Session C: полный WA regression **133/133 PASS**, py_compile и diff-check PASS. Значит read-only reconciliation stack прошёл финальную проверку сценариев и WA-3.3 считается DONE / VERIFIED.

После reconnect система должна уметь сравнить:

- snapshot текущей микрозадачи;
- manifest;
- текущие hashes/наличие файлов;
- последнюю известную операцию;
- ожидаемый post-state, если он был зафиксирован;
- verification evidence.

Результат reconciliation должен быть одним из ограниченного набора:

```text
ADOPT_CURRENT_STATE
RETRY_SAFE
ROLLBACK_CURRENT_MICROTASK
MANUAL_REVIEW_REQUIRED
```
#### WA-3.4 — Recovery после перезапуска Chat и сервера

**Статус: DONE / VERIFIED — 2026-10-02.**

Проверка выполнена process-level без runtime-правок. Case A: новый Chat/Python process читает тот же живой HTTP Server и получает идентичный persistent checkpoint/reconciliation fingerprint/NEXT SAFE ACTION → **1/1 PASS**. Case B: новый Python process поднимает новый Web Alarm Server, читает тот же disk state по HTTP и создаёт новый `RemoteEntry`; два последовательных restart дали идентичный результат → общий focused suite **2/2 PASS**. Финальный полный WA regression → **135/135 PASS**, py_compile и diff-check PASS.

Нужно отдельно проверить два независимых случая:

1. Chat потерян, Web Alarm Server продолжал работать.
2. Одновременно потерян Chat и перезапущен Web Alarm Server.

В обоих случаях новый Chat должен получить одинаково корректный checkpoint с диска.

#### WA-3.5 — Watchdog как signal, но не authority

**Статус: DONE / VERIFIED — 2026-10-02.**

**Цель:** подключить persistent transport/Watchdog evidence к Web Alarm так, чтобы система знала о состоянии Remote-канала, result delivery и process lifetime, но Watchdog никогда сам не принимал recovery-решения.

**Baseline по INC-REMOTE-001…013:** caller/UI failure уже наблюдался при 0, partial и full execution. Поэтому transport evidence и workflow authority физически разделяются; fate операции определяется только persistent state machine + reconciliation.

Минимальные transport events:

```text
REMOTE_ONLINE
REMOTE_OFFLINE
REMOTE_RECOVERED
RESULT_DELIVERY_FAILED
MESSAGE_DELIVERY_TIMEOUT
PROCESS_RESTARTED
```

Каждое событие должно хранить compact evidence: timestamp; `task_id` / `microtask_id` / `operation_id`, если известны; тип Remote-call; error class; process id/start time, если доступны; компактный payload.

**Watchdog не имеет authority:** не выполняет retry/rollback; не принимает `ADOPT_CURRENT_STATE`; не ставит TASK/microtask в VERIFIED/DONE; не меняет `NEXT SAFE ACTION` только по transport signal; не активирует следующую TASK; не считает message-delivery timeout доказательством failure операции.

**Execution split:**
- **WA-3.5.A — Transport Event Model / persistent append-only Store — DONE / VERIFIED.** Реализованы шесть transport event types, nullable workflow binding, process/error/call metadata, global append-only JSONL store и fail-closed parser; focused 10/10, full WA 145/145 PASS; без Server ingestion и без workflow authority.
- **WA-3.5.B — Watchdog / Server ingestion — DONE / VERIFIED.** `WebAlarmApi` получил GET/POST `/transport/events`, filters по TASK/microtask/operation/type, capability `transport_evidence`, `authority=evidence_only`, `workflow_mutation_performed=false`; focused 7/7, full WA 152/152 PASS; TASK directory, checkpoint и Workspace доказанно не меняются.
- **WA-3.5.C — Recovery/Restart tests — DONE / VERIFIED.** OFFLINE→RECOVERED, result-delivery failure, `PROCESS_RESTARTED`, fresh Python process и `UNKNOWN_AFTER_DISCONNECT` persistence PASS; test-first run 3/5 выявил duplicate-ID defect, после `repair_c_store_v1` same-ID replay идемпотентен, conflicting reuse fail-closed; transport focused 22/22, full WA 157/157 PASS.
- **WA-3.5.D — Authority-negative tests + full regression — DONE / VERIFIED.** Focused 7/7 PASS; transport A+B+C+D 29/29 PASS; full Web Alarm 164/164 PASS; runtime repair не понадобился.
- **Fresh reopen gate.** Новый process заново читает persistent state и подтверждает `WA-3.5 = DONE / VERIFIED` до старта WA-3.6.

**Критерий завершения WA-3.5:** transport evidence restart-safe, доступно новому Chat/Server и связано с TASK/operation где возможно; Watchdog не мутирует Workspace и recovery/workflow state; authority-negative tests механически подтверждают это; final full regression + fresh reopen PASS.

**WA-3.5.D:** DONE / VERIFIED — authority-negative 7/7 PASS; transport A+B+C+D 29/29 PASS; full WA 164/164 PASS.

**Fresh reopen WA-3.5:** PASS. **WA-3.6:** DONE / VERIFIED; fresh reopen WA-3.6 PASS. M001 9/9, M002 8/8, M003 6/6, M004 10/10; combined 33/33, full Web Alarm 197/197 PASS.

#### WA-3.6 — Короткий recovery report

**Статус: DONE / VERIFIED; FRESH REOPEN PASS.**

Execution split закрыт: M001 — persistent schema/store; M002 — pure deterministic builder; M003 — RecoveryReportService + Server/Context integration; M004 — adversarial acceptance + final regression/docs closeout. Report restart-safe, evidence-only и fail-closed; Server/API и новый process читают тот же persistent report.

Во время M004 docs closeout live transport incident дал `MESSAGE_DELIVERY_TIMEOUT → REMOTE_OFFLINE → REMOTE_RECOVERED`. Restore-point reconciliation доказал partial execution и позволил продолжить только с отсутствующих документов без replay уже изменённого `000`. Этот incident не заменяет требуемый intentionally controlled disconnect acceptance test для WA-3 overall.

После каждого recovery сохраняется короткий machine-usable отчёт. Минимальные поля:

- `incident_id`;
- `task_id` / `microtask_id` / последний `operation_id`;
- caller/UI error class (`result storage`, `message delivery timeout`, transport offline и т.д.);
- transport/process evidence и был ли process restart;
- last persistent operation state;
- affected targets + pre/current/expected-post summary;
- доказанный масштаб side effect: `none / partial / full / ambiguous`;
- reconciliation decision;
- что было принято как уже выполненное;
- что реально повторялось/отменялось;
- `NEXT SAFE ACTION`;
- fresh-process reopen result.

Recovery report не должен считать последнюю видимую реплику Chat authoritative. Он строится из persistent state и evidence после reconciliation.

#### WA-3.7 — Controlled real Remote transport-disconnect acceptance gate

**Статус: DONE / VERIFIED; FRESH REOPEN PASS. Parent WA-3 закрыт решением RT-001: stricter combined post-change disconnect criterion = SUPERSEDED / DEFERRED, не PASS; его смысл перенесён в `WA4-A`.**

WA-3.7 закрывает последний отдельный acceptance gate WA-3. Тест обязан использовать реальный намеренный разрыв Chat ↔ Desktop Commander Remote во время безопасной изолированной mutation с заранее persistent `operation_id`, verified restore point и известными pre/expected-post состояниями. Timeout/offline сам по себе не считается failure и не получает recovery authority.

**Execution split:** `WA37-M001` = VERIFIED; `WA37-M002` = VERIFIED; `WA37-M003` = VERIFIED. TASK WA-3.7 = COMPLETED; fresh-process reopen PASS.

**Final WA-3 reconciliation:** WA-3.7 закрыта и restart-safe: `CTRL-001` доказал FULL local mutation без required disconnect; `CTRL-002` доказал real `REMOTE_OFFLINE → REMOTE_RECOVERED`, exact PRE_STATE, RETRY_SAFE, side_effect none, no replay, persistent Recovery Report/fresh-process PASS. Focused 95/95, full WA 197/197, compileall + scoped diff-check PASS. Более строгая temporal composition `post-state reached → transport lost → Chat result unavailable` не была доказана в одном incident и **не получает PASS задним числом**. RT-001 закрыл literal criterion как `SUPERSEDED / DEFERRED` и перенёс его смысл в deterministic lost-response acceptance `WA4-A` после authoritative executor.

#### WA-3 — Критерии приёмки

WA-3 считается завершённой, если доказаны сценарии:

- disconnect до начала мутации;
- disconnect во время мутации;
- мутация завершилась, но ответ потерян;
- повторно доставлен тот же `operation_id`;
- Chat сменился после M003, а TASK продолжилась с M004/M005 без потери VERIFIED-этапов;
- сервер перезапущен между INTENT и VERIFIED;
- rollback затрагивает только текущую микрозадачу;
- recovery не выполняет автоматический blind rollback;
- recovery не повторяет уже доказанную мутацию;
- result-storage/UI message timeout не трактуется как доказательство отсутствия выполнения;
- partial и full execution composite-call различаются через per-step receipts/post-state reconciliation;
- bootstrap/closeout после сбоя продолжаются с первого отсутствующего persistent receipt;
- после recovery новый process получает тот же checkpoint/decision/NEXT SAFE ACTION;
- Watchdog/transport telemetry не имеет права принимать recovery decision;
- после recovery формируется понятный machine-usable отчёт и новый `NEXT SAFE ACTION`.

Обязателен отдельный controlled test, где Remote-связь намеренно разрывается после локального изменения, но до получения ответа Chat.

**Результат WA-3:** потеря транспорта или Chat становится штатным восстанавливаемым событием.

---

### WA-4 — Строгий mutation gateway, hardening и ввод в рабочий режим

**Статус: PLANNED**

**Корректировка по итогам independent preflight `CLAUDE-WA-001` (2026-10-04):** текущие подпункты WA-4 сохранены как смысловые требования, но их исполнение сопоставляется с новым маршрутом RT-001: WA-4.1/4.2 → будущий authoritative `WA4-E` после RC-0…RC-6; WA-4.3 → базовая serialization/CAS через RC-1/RC-3, а точная lease/heartbeat model **DEFERRED по V17**; WA-4.4 retention и WA-4.5 security остаются cross-cutting constraints; WA-4.6 → `WA4-O`; WA-4.7 → `WA4-R`. Эта корректировка не означает PLAN APPROVAL и не запускает runtime-исполнение.

WA-4 выполняется только после того, как WA-1–WA-3 доказали корректность хранения и recovery и закрыт предшествующий Recovery Closure route RT-001.

Цель — превратить рекомендательный протокол в настоящее узкое горло для изменяющих операций, не запрещая обычное чтение, анализ и тестирование проекта.
#### WA-4.1 — Mutation Gateway

Web Alarm Server получает узкие операции:

```text
write
edit
create
delete
move
rename
```

Перед исполнением сервер механически проверяет:

- TASK active;
- microtask current;
- status = READY/ACTIVE;
- target входит в manifest;
- snapshot подтверждён;
- precondition hash соответствует ожидаемому состоянию;
- `operation_id` новый либо является безопасным recovery существующей операции.

#### WA-4.2 — Atomicity и precondition checks

Для записи существующего файла предпочтительно использовать temporary file + atomic replace там, где это возможно.

Live incidents показали, что внешний composite tool-call сам по себе не является транзакцией. Поэтому mutation gateway должен считать атомарной единицей именно одну operation/receipt, а многошаговую orchestration — последовательностью таких операций. Каждый mutating step получает отдельный `operation_id` или дочерний receipt и собственный post-state proof.

Если файл изменился внешне после подготовки snapshot или предыдущей проверки, mutation gateway не должен молча перезаписывать новое состояние.

Вместо этого:

```text
STATE_DRIFT
↓
RECOVERY_REQUIRED
```

Это защищает и от параллельного ручного редактирования, и от второго Chat, и от повторной доставки уже частично выполненной composite sequence.
#### WA-4.3 — Conflict serialization и ownership boundary

Требование этого этапа — не допустить одновременное конфликтующее исполнение по одному canonical physical target. Минимальная межпроцессная сериализация persistent Operation Store/revision вводится раньше, в RC-1; полноценный conflict gate, canonical-target admission и mutation-boundary CAS — в RC-3.

Точная lease/heartbeat модель **не фиксируется сейчас**: по V17 она отложена до доказанной базовой serialization + revision/CAS. До отдельного решения система не должна вводить скрытый lease protocol или считать heartbeat источником authority.

После RC-3 ownership reservation может использоваться только как явно определённый механизм защиты конфликтующих mutation scopes; recovery ownership должен оставаться fail-closed и проверяемым.

#### WA-4.4 — Retention, physical storage и очистка

Completed TASK сохраняются, но snapshots могут занимать значительный объём. Live Obsidian case дополнительно показал, что runtime snapshots внутри пользовательского vault загрязняют Graph/поиск даже при правильной логике recovery.

Production state/snapshot root поэтому должен по возможности находиться вне пользовательского Obsidian vault и вне навигационных директорий проекта; fallback внутри project root допускается только с явными ignore/filter rules.

Нужно определить policy:

- сколько completed TASK хранить полностью;
- когда разрешено архивировать старые snapshots;
- что никогда не удалять без явного правила;
- как показывать общий размер хранилища;
- как экспортировать TASK перед очисткой.

На первом этапе автоматическое удаление snapshots лучше не включать.

#### WA-4.5 — Security boundary

Web Alarm Server по умолчанию работает локально и не публикует API наружу.

Workspace root должен быть явно зарегистрирован, а path validation не должен позволять выход за разрешённые roots через `..`, symlink/junction или некорректную нормализацию пути.
#### WA-4.6 — Расширенный Task Progress UI / UX-Ops

**Статус: BLOCKED / PLANNED. Не начинать до закрытия correctness/recovery-контура RT-001: Recovery Closure, authoritative Mutation Executor / Gateway и lost-response acceptance должны быть DONE / VERIFIED.**

После доказанной надёжности recovery и исполнения Web Alarm Workspace обязан перейти к отдельному этапу развития операторского интерфейса. Это не замена уже существующего минимального UI WA-2.3, а следующий полноценный слой наблюдаемости над авторитетным persistent state.

Минимальный обязательный результат этапа:

- текущая TASK показывается как последовательность этапов;
- виден активный этап и текущая операция;
- завершённые этапы различаются как минимум по `SUCCESS / FAILED / RECOVERY / WAITING`;
- видны заблокированные зависимости и оставшиеся этапы;
- отображаются `NEXT SAFE ACTION`, причина ошибки/recovery и доступное evidence без необходимости читать большой raw log;
- UI только отображает authoritative server-owned state и не придумывает собственный статус исполнения.

Этот этап является **обязательным перед переходом к полноценному strict rollout**, но прямо сейчас не активируется.

#### WA-4.7 — Rollout

Переход на строгий режим выполняется ступенчато:

```text
OBSERVE
↓
WARN
↓
REQUIRE READY FOR GATEWAY MUTATIONS
↓
STRICT REMOTE WORKFLOW
```

Сначала Web Alarm Server только сообщает о нарушении протокола.

После доказанной стабильности рабочее правило для Web ChatGPT меняется: значимые mutation через Remote выполняются через Web Alarm Workspace / gateway, а прямые изменяющие вызовы считаются выходом из защищённого режима.

Чтение файлов, поиск, запуск безопасных проверок и просмотр проекта не обязаны проходить через mutation gateway, если они не изменяют состояние.

#### WA-4 — Критерии приёмки

WA-4 считается завершённой, если:

- gateway отклоняет mutation без READY;
- target вне manifest отклоняется;
- отсутствующий snapshot блокирует mutation;
- stale precondition/hash переводит этап в recovery, а не перезаписывает файл;
- повтор `operation_id` идемпотентен;
- две конфликтующие mutation session не могут одновременно пройти admission для одного canonical physical target;
- restart сервера не теряет persistent serialization/recovery semantics; точная lease/heartbeat модель остаётся отдельным deferred design decision;
- completed TASK можно открыть и прочитать спустя перезапуск;
- multi-workspace сценарий работает минимум с двумя реальными проектами;
- rollback текущей микрозадачи доказан на create/edit/delete;
- расширенный Task Progress UI показывает authoritative состояние TASK, текущий/завершённые/ожидающие этапы, recovery/error и `NEXT SAFE ACTION` без ручного дублирования статуса;
- документация синхронизирована с реально работающим поведением.
---

## 5. Контрольные точки программы

| Контрольная точка | Что должно быть доказано |
| --- | --- |
| WA-KT0 | Схемы состояния и storage contract зафиксированы, тестовые TASK создаются без UI |
| WA-KT1 | Файловое ядро, manifest, snapshot, checkpoint и archive переживают restart |
| WA-KT2 | Локальный Server + UI управляют state machine и выдают Entry Context Pack |
| WA-KT3 | Disconnect/reconnect и replay проходят controlled recovery без дублей |
| WA-KT4 | Mutation gateway физически соблюдает READY/manifest/snapshot/precondition |
| WA-KTF | Multi-workspace regression, recovery matrix и документация закрыты |

Переход к следующей контрольной точке выполняется только после доказательства предыдущей.

## 6. Что сознательно не делать в первой версии

Чтобы не превратить Web Alarm Workspace сразу в новый большой Agent Runtime, первая реализация не должна пытаться:

- заменить Desktop Commander Remote;
- заменить Git;
- копировать весь рабочий проект;
- хранить полный RAW transcript ChatGPT;
- самостоятельно решать архитектурные задачи вместо ChatGPT;
- автоматически откатывать проект при любом сетевом событии;
- публиковать локальный Web Alarm Server в интернет;
- интегрироваться одновременно со всеми будущими MCP/plugin-сценариями;
- переносить внутрь себя Planner/Executor/Dredd Ultra.

Эти вещи рассматриваются только при отдельной необходимости.
## 7. Первый end-to-end proof

До широкого использования нужен небольшой тестовый Workspace и одна TASK примерно из трёх микрозадач.

Контрольный сценарий:

```text
создать TASK
↓
разбить на M001–M003
↓
подготовить snapshot M001
↓
изменить существующий файл
↓
VERIFY M001
↓
M002 создать новый файл
↓
на M003 намеренно оборвать Remote после mutation
↓
переподключиться новым Chat
↓
получить Entry Context Pack
↓
reconcile
↓
не повторить уже выполненную mutation
↓
завершить M003
↓
архивировать TASK
```

Только после такого proof можно считать базовую идею доказанной в реальной Remote-работе.

## 8. Документационное сопровождение

При реализации ветки документы имеют разные роли:

- `23_Архитектура Web Alarm Workspace.md` — что система собой представляет и какие инварианты обязаны сохраняться;
- этот `24` — что реализуем следующим, что уже завершено и какие критерии приёмки действуют;
- `25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md` — append-only профильная история фактически выполненных больших задач и микрозадач, verification и recovery;
- `01_Архитектура и текущее состояние.md` — только краткий CURRENT/FUTURE status;
- `04_Дорожная карта разработки.md` — только наличие и крупный статус ветки;
- `05_Реестр задач.md` и `06_Журнал выполнения и отчёты.md` — реальные TASK и история после фактического начала реализации.

Нельзя переводить этап в DONE только потому, что код написан. Статус меняется после предусмотренной проверки.
## 9. Текущий статус программы

| Большая задача | Статус |
| --- | --- |
| WA-1 — Фундамент состояния и файловое ядро | DONE / VERIFIED — WA-1.1–WA-1.6 complete |
| WA-2 — Local Web Alarm Server + UI | DONE / VERIFIED — WA-2.1–WA-2.4 complete |
| WA-3 — Remote recovery + replay protection | DONE / VERIFIED — WA-3.1–WA-3.7 complete; old stricter combined criterion SUPERSEDED / DEFERRED by RT-001, not PASS |
| Recovery Closure RC-0…RC-6 | IN PROGRESS — RC-0, RC-1, RC-2 DONE / VERIFIED; RC-3 next / not started |
| WA-4 — Strict mutation gateway + hardening | PLANNED AFTER RC-0…RC-6 |

**CURRENT:** WA-1, WA-2 и WA-3 = DONE / VERIFIED. RT-001 / `EP-RT001-001` получил PLAN APPROVAL 2026-10-04; **RC-0, RC-1 и RC-2 = DONE / VERIFIED**. RC-1 ввёл durable Operation Contract v2; RC-2 добавил persistent Resolver с evidence/revision binding, fail-closed stale/rejected outcomes и Resolver-derived Recovery Report/NEXT SAFE ACTION. Канонический следующий этап — RC-3, затем RC-4…RC-6, `WA4-E`, `WA4-A`, `WA4-O`, `WA4-R`. Обнаруженный при RC-2 review разрыв верхнего `Context Pack NEXT_SAFE_ACTION` не является blocker RC-2 и закреплён как обязательный projection/resume follow-up для RC-5/RC-6. `.gitattributes` FOLLOW-UP остаётся отложенным. Старый stricter combined criterion WA-3 не объявлен пройденным: он `SUPERSEDED / DEFERRED`, а его смысл перенесён в `WA4-A`.

Текущий production runtime Ultra не переключён на strict Web Alarm mutation control: persistent recovery одинаково восстанавливается при новом Chat и новом Server process; resolver retry/rollback/adopt execution пока не выполняется автоматически, authoritative executor ещё не реализован.

## Итоговый маршрут

```text
WA-1
Файловое ядро и восстанавливаемое состояние
        ↓
WA-2
Локальный Server и понятный интерфейс
        ↓
WA-3
Реальный Remote recovery и replay protection — DONE / VERIFIED
        ↓
RC-0 → RC-1 → RC-2 → RC-3 → RC-4 → RC-5 → RC-6
Recovery Closure
        ↓
WA4-E → WA4-A → WA4-O → WA4-R
Executor → lost-response acceptance → UX/Ops → strict rollout
        ↓
WEB ALARM WORKSPACE READY FOR REGULAR USE
```

Система считается готовой не тогда, когда появился UI, а тогда, когда реальный disconnect перестал приводить к потере точки продолжения, повтору неизвестной mutation или откату уже VERIFIED-работы.