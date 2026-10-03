# План реализации Web Alarm Workspace

## Статус документа

**IMPLEMENTATION PLAN / ACTIVE — WA-1 IN PROGRESS.**

Этот документ является каноническим планом внедрения Web Alarm Workspace. Архитектурные инварианты и назначение системы принадлежат документу `23_Архитектура Web Alarm Workspace.md`; здесь фиксируются порядок реализации, крупные этапы, критерии приёмки и фактический статус внедрения.

Реализация начата с WA-1. Статус меняется только после предусмотренной проверки конкретной микрозадачи; незапущенные этапы остаются `PLANNED`.

## Краткая карта реализации

Сначала — только крупные этапы, чтобы план можно было быстро прочитать целиком:

```text
WA-1 — Фундамент состояния и файловое ядро
WA-2 — Локальный Web Alarm Server и простой UI
WA-3 — Remote recovery и replay protection
WA-4 — Строгий mutation gateway и hardening
```

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

**Статус: IN PROGRESS — WA-3.1 + WA-3.2 + WA-3.3.1 + WA-3.3.2 DONE / VERIFIED**

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

**Статус: IN PROGRESS — WA-3.3.1 + WA-3.3.2 DONE / VERIFIED.**

**Execution split:**
- WA-3.3.1 — Reconciliation Evidence / read-only inspector — **DONE / VERIFIED**;
- WA-3.3.2 — deterministic Decision Engine — **DONE / VERIFIED**;
- WA-3.3.3 — Server / Remote integration — PLANNED;
- WA-3.3.4 — recovery scenarios / final verification — PLANNED.

WA-3.3.1 реализован в `web_alarm/reconciliation.py`. Collector read-only собирает operation binding, manifest/snapshot pre-state, current exists/size/SHA256, optional exact expected post-state, verification evidence и per-target признаки `MATCHES_PRE_STATE`, `MATCHES_EXPECTED_POST_STATE`, `DRIFT_DETECTED` / `MISSING_EVIDENCE`. Snapshot integrity проверяется без вызова mutating `verify_restore_point`, поэтому даже corrupted snapshot не меняет manifest/microtask status. Focused regression 10/10 PASS; полный WA regression **100/100 PASS**.

WA-3.3.2 реализован в `web_alarm/reconciliation_decision.py`. Pure engine детерминированно выдаёт только `ADOPT_CURRENT_STATE`, `RETRY_SAFE`, `ROLLBACK_CURRENT_MICROTASK` или `MANUAL_REVIEW_REQUIRED`, привязывая результат к SHA256 fingerprint всего evidence. `DRIFT`/`MISSING_EVIDENCE`/`CHANGED_UNCLASSIFIED`, conflicting lifecycle/evidence и неполный exact post-state fail-closed уходят в manual review. Любой результат содержит `automatic_mutation_authorized=false`: engine ничего не исполняет. Первый focused run выявил один policy defect — exact post-state при lifecycle `INTENT` ошибочно принимался как ADOPT; правило исправлено на `LIFECYCLE_CONTRADICTS_POST_STATE`. После repair focused **16/16 PASS**, полный WA regression **116/116 PASS**, py_compile и `git diff --check` PASS.

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

Нужно отдельно проверить два независимых случая:

1. Chat потерян, Web Alarm Server продолжал работать.
2. Одновременно потерян Chat и перезапущен Web Alarm Server.

В обоих случаях новый Chat должен получить одинаково корректный checkpoint с диска.

#### WA-3.5 — Watchdog как сигнал, но не authority

Существующий DesktopCommander Watchdog может в будущем сообщать Web Alarm Server о смене состояния транспорта:

```text
REMOTE_ONLINE
REMOTE_OFFLINE
REMOTE_RECOVERED
```

Но Watchdog не принимает решение о rollback и не меняет TASK самостоятельно.

Он только добавляет transport evidence в event log.

#### WA-3.6 — Короткий recovery report

После каждого recovery сохраняется короткий отчёт:

- где произошёл обрыв;
- какой `operation_id` был последним;
- что реально найдено на диске;
- что было принято как выполненное;
- что было повторено или отменено;
- с какой точки продолжилась работа.
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
- после recovery формируется понятный отчёт и новый `NEXT SAFE ACTION`.

Обязателен отдельный controlled test, где Remote-связь намеренно разрывается после локального изменения, но до получения ответа Chat.

**Результат WA-3:** потеря транспорта или Chat становится штатным восстанавливаемым событием.

---

### WA-4 — Строгий mutation gateway, hardening и ввод в рабочий режим

**Статус: PLANNED**

WA-4 выполняется только после того, как WA-1–WA-3 доказали корректность хранения и recovery.

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

Если файл изменился внешне после подготовки snapshot или предыдущей проверки, mutation gateway не должен молча перезаписывать новое состояние.

Вместо этого:

```text
STATE_DRIFT
↓
RECOVERY_REQUIRED
```

Это защищает и от параллельного ручного редактирования, и от второго Chat.
#### WA-4.3 — Task ownership и защита от двух исполнителей

Для active TASK нужен простой lease/lock.

Система должна различать:

- кто открыл TASK;
- существует ли уже активная mutation session;
- когда был последний heartbeat;
- можно ли безопасно передать ownership новому Chat после timeout/recovery.

Lock не должен навечно блокировать TASK после падения процесса. Нужен контролируемый recovery ownership.

#### WA-4.4 — Retention и очистка

Completed TASK сохраняются, но snapshots могут занимать значительный объём.

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
#### WA-4.6 — Rollout

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
- две mutation session не могут одновременно владеть одной TASK;
- restart сервера не теряет lock/recovery semantics;
- completed TASK можно открыть и прочитать спустя перезапуск;
- multi-workspace сценарий работает минимум с двумя реальными проектами;
- rollback текущей микрозадачи доказан на create/edit/delete;
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
| WA-3 — Remote recovery + replay protection | IN PROGRESS — WA-3.1 + WA-3.2 + WA-3.3.1 + WA-3.3.2 DONE / VERIFIED |
| WA-4 — Strict mutation gateway + hardening | PLANNED |

**CURRENT:** WA-1 и WA-2 = DONE / VERIFIED. WA-3 продолжается: WA-3.1 Canonical Remote entry, WA-3.2 Operation ID / replay identity, WA-3.3.1 Reconciliation Evidence и WA-3.3.2 Deterministic Decision Engine = DONE / VERIFIED; следующий этап — WA-3.3.3 Server / Remote integration.

Текущий production runtime Ultra не переключён на Web Alarm Workspace: WA-1/WA-2 + WA-3.1/3.2/3.3.1/3.3.2 остаются отдельной рабочей оболочкой; reconciliation и decision engine пока read-only/pure и не исполняют retry/rollback/adopt mutation.

## Итоговый маршрут

```text
WA-1
Файловое ядро и восстанавливаемое состояние
        ↓
WA-2
Локальный Server и понятный интерфейс
        ↓
WA-3
Реальный Remote recovery и replay protection
        ↓
WA-4
Строгий mutation gateway и hardening
        ↓
WEB ALARM WORKSPACE READY FOR REGULAR USE
```

Система считается готовой не тогда, когда появился UI, а тогда, когда реальный disconnect перестал приводить к потере точки продолжения, повтору неизвестной mutation или откату уже VERIFIED-работы.