### WA4-R 2026-10-17 / Claude AUD-01T + AUD-02b published; bounded independent review

**PUBLISHED:** [published commit #354](https://github.com/maxrus82gm-svg/ag_llm/commit/3fd942b783ea36b969f801045c7f3ec550689a44), `CLAUDE-WA4-R-AUD01T02B-REPAIR-001`, `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-AUD01T02B-REPAIR-001/`. Repairs have been implemented: global transport LF/UTF-8/torn-tail and interprocess write integrity; per-TASK microtask transition CAS/event serialization and fail-closed history admission. Six code/test files independently SHA-256+size matched against Gate E; report/evidence and 55 listed publication artefacts inspected for availability. **BOUNDED SOURCE/PUBLICATION-INTEGRITY REVIEW PASS WITH OPEN RISKS; FULL INDEPENDENT ACCEPTANCE PENDING.** Local Claude full 849 = 848 PASS/0 FAIL/0 ERROR/1 SKIP with 27 new tests; independent Windows full run NOT RUN, no exact-source GitHub Actions runs found for #354, W1 NOT RUN, W3 NOT RUN. The per-test raw local `results.json` is not published; the available census and summaries were read.

**NEXT GATES (not automatic assignments):** (1) USER approves durability/reconciliation design for AUD-02b-R + AUD-03; define fail-closed detection after crash. (2) Decide controlled lossless repair/quarantine path for AUD-01T-R and bounded repair for AUD-02c / AUD-04, with independent negative/fresh-process oracles. (3) An engineer in an approved, nonoverlapping scope implements/test/reports; independent source/tests/evidence review. (4) New clean Windows CI W1 on exact accepted source and, separately after USER GO, read-only live-storage preflight W3. (5) Only then assess whether a new explicitly authorized WARN gate is safe. **WA4-R PARTIAL; OBSERVE bounded; GATEWAY REQUIRED / STRICT / Final Audit unauthorized**. No WUA-0 / Ultra Tab / GigaChat MVP implementation GO; MCP is WEB_10's separate scope. Historical 2026-10-16 'next task NOT ASSIGNED' notes below are dated snapshots superseded for the *completed Claude repair*, not authorization of a new TASK.

### WA4-R current stage / 2026-10-16 — bounded repair, rollout withheld

**SOURCE:** [user commit #352](https://github.com/maxrus82gm-svg/ag_llm/commit/7778c9e255ee6982391c58e30c77d89f296cd0e0) / Claude `CLAUDE-WA4-R-AUD010205-REPAIR-001` report + tests + evidence. **INDEPENDENT ChatGPT BOUNDED SOURCE/EVIDENCE ACCEPTED** for AUD-01/02/05, no independent full Windows execution or new clean CI. Claude-reported 822 = 821 PASS / 0 FAIL / 0 ERROR / 1 SKIP; repair 20/20, 4/4 RAM mutants, R-006 11/11, quality 12/12, focused 3×172 and bounded race 5×2 PASS. Existing historical FAIL unchanged. WA4-R **PARTIAL**; only bounded OBSERVE accepted, WARN/GATEWAY REQUIRED/STRICT/Final Audit **NOT AUTHORIZED**.

**Completed engineering in bounded review:** AUD-01, AUD-02 and AUD-05 repairs and 20 regression tests. **Proposed next Claude engineering step, NOT YET ASSIGNED:** investigate and repair AUD-01T transport-event integrity + AUD-02b microtask/event ordering, with autonomous adversarial review, isolated evidence and no MCP write-scope. AUD-03/04 need separate user/scope decision after engineering analysis. Next independent gates include source+tests review, new clean CI exact commit, and separately authorized read-only live-storage preflight. OBSERVE is bounded, not automatic WARN. Codex WUA MCP track is independent; local loader PASS not ordinary ChatGPT Desktop E2E. Future Ultra Tab/Blueprint roadmap doc 37 is not part of WA4-R coding scope.

# План реализации Web Alarm Workspace

### Direction and sequencing / 2026-10-14 — approved priorities, no rescope

Main delivery priority: complete the existing Web Alarm plan, including independently closing UX-002 acceptance and WA4-R reliability/evidence gates before new rollout. OBSERVE is bounded; WARN, GATEWAY REQUIRED, STRICT and Final Audit still require separate decisions. Ultra RT-002 token/context economics may continue in parallel under Ultra ownership as portable server-side services; avoid new Tkinter UI functionality. Post-WA4-R **candidate**, not current TASK: independent integration architecture review for Web Alarm Ultra; then staged adapters, one state authority, compatibility and rollback checks before any runtime cutover. No automatic AI/MCP provider integration has been assigned by this note.

### WA4-R stage update / independent OBSERVE acceptance (2026-10-13)

**CURRENT VERIFIED UPDATE / 2026-10-13 / WEB_07 / CODEX-WA4-R-001:** bounded read-only **OBSERVE ACCEPTED WITH OPEN RISKS** after independent source/HTTP/CLI/test review and GitHub Windows job-log verification. Pinned source `7caee3af61679f963eb90a323e57a1015f9a565e`; Actions [38229502661](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38229502661), rerun job `115156352428`: WA4-A 167/167, WA4-O 29/29, OBSERVE 228/228, closeout diagnostic 20/20 (80 rounds), JS 23/23, full Web Alarm 750/750 PASS (zero FAIL/ERROR/SKIP). Astra [38258103453](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38258103453), job `115156365504`: P1–P3 3/3 and focused 103/103 PASS. Workflow artifacts and job logs confirmed; original artifact ZIP payloads not independently unpacked in this closeout. **Only bounded on-demand observation is accepted**, not filesystem watching, writer attribution, mutation gateway, enforcement, lifecycle transition or global STRICT acceptance. `DONE` receipts are historical evidence only, not proof of current bytes. F1 RC-5 Windows closeout, F2 direct-close vs MutationExecutor, F3 WA-017 crash race remain OPEN; historical CI failures are not erased by green reruns. `CODEX-WA4-R-001-DIAG-01` establishes a controlled native WinError 5 safe pre-move refusal, **not** the root cause or terminal invariants of the original red CI. WA4-R overall **IN PROGRESS / STRICT NOT VERIFIED**. **NEXT SAFE ACTION:** separately authorize F1–F3 deterministic raw-state/fresh-process evidence or next bounded rollout decision; **no automatic WARN / GATEWAY REQUIRED / STRICT / Final Audit**. Prior `NOT STARTED / NOT ASSIGNED` lines below are preserved as historical snapshots and superseded by this current update.

**Plan gate:** OBSERVE accepted with open risks. WARN, GATEWAY REQUIRED, STRICT and Final Audit remain separately gated future stages. F1–F3 evidence/recovery work must not be silently considered complete.


## Статус документа

**IMPLEMENTATION PLAN / ACTIVE — WA-1 + WA-2 + WA-3 DONE / VERIFIED; RT-001 RECOVERY CLOSURE ROUTE APPROVED.**

Этот документ является каноническим планом внедрения Web Alarm Workspace. Архитектурные инварианты и назначение системы принадлежат документу `23_Архитектура Web Alarm Workspace.md`; здесь фиксируются порядок реализации, крупные этапы, критерии приёмки и фактический статус внедрения.

**CURRENT UPDATE 2026-10-11 / WA4-O implementation technical PASS:** WA-1…WA-3, RC-0…RC-6, WA4-E, WA4-A DONE / VERIFIED. CODEX-WA4-O-001 UI code/CI independently PASS through PR №7/№266 `4cf2f53`: Windows Actions [38153364378](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38153364378) 5/5 smoke, 167/167 focused, 29/29 operator+launcher, 23/23 JS, 719/719 full, 0 fail/error/skip/isolations. User opened isolated BAT-launched demo and accepted existing style/interface **for interim progression only**; exhaustive visual scenarios not signed off. Future UX changes A/B/C documented here **not implemented**. **NEXT candidate WA4-R**, drafted OBSERVE preflight CODEX-WA4-R-001 **NOT ASSIGNED / NOT STARTED**. Earlier snapshots below historical; Ultra not affected.

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
RC-6 — Project-level Recovery Closure / bounded resume coordinator
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
| RC-3 | persistent canonical-target claim/conflict gate + mutation-boundary CAS; один active owner на physical target; crash/restart ownership сохраняется; stale revision/state drift fail-closed; race tests PASS; standalone authorization не является переносимой mutation authority |
| RC-4 | tracked rollback persistent; current state сохранён до destructive restore; fresh accepted ROLLBACK + server-derived target set; all-target RC-3 ownership incl. NOOP; per-target CAS/receipts; final full-target byte proof precedes persistent VERIFIED; partial/restart-safe recovery and crash-safe pending claim release |
| RC-5 | checkpoint rebuildable/validated projection; inspect/verify pure; stale projection fail-closed; Resolver-authoritative recovery/NEXT projection не должна перезаписываться advisory reconciliation |
| RC-6 | одна canonical `recover/resume` команда строится поверх RC-5 Projection, возвращает project/stage/blockers/open operations/NEXT и bounded выполняет только уже разрешённые safe recovery/administrative steps до `READY_FOR_EXECUTION`; normal physical mutation остаётся строго WA4-E |
| WA4-E | server-owned snapshot→claim/CAS boundary→lock-held STARTED transition→mutation→post-proof→receipt; STARTED фиксируется под уже удерживаемой TASK-lock до первого write; replay того же contract не создаёт второй side effect |
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

**CURRENT STATUS 2026-10-11: WA4-O implementation delivered and independently AUTOMATED PASS; visual user review = interim UI acceptance, exhaustive human visual gate NOT confirmed.** Earlier BLOCKED/PLANNED requirements were satisfied for starting implementation, not a future blocker. The new UX A/B/C entries below are FUTURE, not part of CODEX-WA4-O-001 acceptance.

После доказанной надёжности recovery и исполнения Web Alarm Workspace обязан перейти к отдельному этапу развития операторского интерфейса. Это не замена уже существующего минимального UI WA-2.3, а следующий полноценный слой наблюдаемости над авторитетным persistent state.

Минимальный обязательный результат этапа:

- текущая TASK показывается как последовательность этапов;
- виден активный этап и текущая операция;
- завершённые этапы различаются как минимум по `SUCCESS / FAILED / RECOVERY / WAITING`;
- видны заблокированные зависимости и оставшиеся этапы;
- отображаются `NEXT SAFE ACTION`, причина ошибки/recovery и доступное evidence без необходимости читать большой raw log;
- UI только отображает authoritative server-owned state и не придумывает собственный статус исполнения.

Этот этап является **обязательным перед переходом к полноценному strict rollout**, но прямо сейчас не активируется.


##### UX-2026-10-11 — пользовательская схема рабочего интерфейса (зафиксированы требования, не реализация)

**Статус:** USER-CONFIRMED UX DIRECTION / REQUIREMENTS CAPTURE, по просмотру запущенного локального demo UI и четырём размеченным пользователем скриншотам 2026-10-11. Это предварительная UX-постановка для будущей отдельной инженерной TASK, а не independent PASS новой компоновки, не разрешение на её реализацию и не отмена WA4-O/WA4-R gates. Различать текущие возможности ядра/API, наблюдаемое поведение demo UI и новые пожелания. Стиль действующей тёмной оболочки пользователю нравится; не заменять визуальную систему без необходимости.

**Главная компоновка: три независимые колонки вместо навигатора, совмещающего проекты и задачи.**
1. **Слева — WORKSPACES**: вертикальный выбираемый список рабочих пространств, самостоятельная прокрутка, выбранный проект хорошо выделен. В заголовке плюс-кнопка для добавления Workspace. Не размещать длинный список TASK внутри левой колонки; не использовать вкладки «чатов».
2. **Справа — TASKS для выбранного Workspace** (пользователь называл область History, но уточнил, что нужны *все относящиеся к проекту задачи*, не только архив): список текущих, незавершённых, отложенных и завершённых задач. Краткое редактируемое человеком название и фактический краткий статус; выбор TASK открывает её в центре. Плюс-кнопка в шапке списка создаёт новую TASK в текущем Workspace. Предусмотреть прокрутку и возможность вновь открыть любую незавершённую/закрытую задачу (доступные действия зависят от серверного состояния). Группировка/фильтры — последующий UX-вопрос, не обязательный новый lifecycle.
3. **В центре — полная карточка выбранной TASK**: доступное для чтения исходное описание/постановка проблемы и цели, текущий этап, все этапы в порядке плана, статусы, текущие операции, recovery/NEXT SAFE ACTION, доказательства и отчёты каждого этапа. Центральная область имеет максимальный приоритет по ширине; собственная прокрутка и желательно регулируемые ширина и раскрытие длинного текста, независимо от боковых колонок. Не сводить весь экран к короткой технической «операторской сводке».

**Точки взаимодействия и ограничения:**
- **Workspace ↔ TASK:** каждая TASK жёстко принадлежит зарегистрированному реальному Workspace; переключение проекта меняет правый список и текущую центральную карточку. Не смешивать задачи разных проектов и не переносить TASK между проектами одним изменением фильтра.
- **Добавление Workspace:** форма с человекочитаемым именем и выбором папки через обычный файловый интерфейс Windows вместо обязательного ручного ввода абсолютного пути (например C:\Projects или M:\GitHub). Конкретный безопасный механизм выбора корня (браузерный UI ↔ локальный сервер/нативный диалог) исследовать отдельно; выбранный путь обязательно проверяет сервер и существующий Workspace Registry. Никаких автоматических разрешений на файловую запись от самого выбора папки.
- **Новая TASK:** плюс-кнопка справа открывает в центре чистую форму новой задачи, без подставленных этапов/статусов предыдущей TASK; до явного подтверждения не создавать фактическую TASK. Описание должно допускать длинную постановку.
- **Название TASK:** пользователь должен иметь возможность менять короткое отображаемое имя. Это **не** разрешает незаметно переписывать неизменяемый raw source, task_id, исходный план, evidence, receipt или историю; требуется исследовать безопасное отдельное поле/метаданные и механизм обновления.
- **Пауза/отложенная TASK:** пользователь хочет видеть остановившуюся или отложенную работу и затем продолжать её. Пока это **запрос на UX и будущую проверку state model**, не утверждение о наличии PAUSED на сервере: не вводить декоративный клиентский статус или кнопку остановки, выдаваемую за действительную серверную паузу. Отображать существующие честные состояния (PLANNED, DONE, VERIFIED, UNKNOWN_AFTER_DISCONNECT, recovery и т. п.); новый lifecycle — только отдельное архитектурное решение.
- **Отчёты:** рядом с этапами и/или при раскрытии этапа показывать короткий человеческий итог: цель, сделанные изменения, результат, проверки, evidence, причины остановки, следующий шаг. Текущий диагностический блок «Текущая операция» (operation_id, action, target, receipt, post-state) сам по себе полноценным отчётом не является. Сначала сверить существующее хранение microtask report / evidence и доступность через API, не выдумывать отчёты из UI.
- **Прозрачность статусов:** сохранённое DONE и подтверждённое VERIFIED различать; UNKNOWN_AFTER_DISCONNECT не отображать как автоматически FAILED, PAUSED или успех. Сервер управляет состоянием/переходами; UI только показывает authoritative факты. Ни нажатие карточки, ни обновление, ни просмотр отчёта не должны запускать mutation, retry или rollback.
- **Контекст для агента:** пользователь отдельно спросил, куда вводить/передавать контекст задачи. Нужно уточнить UX между исходной постановкой TASK, persistent context pack (экспорт/копирование) и будущим агентским entry; не обещать, что существующий demo UI уже предоставляет редактируемый полноценный context editor.
- **Запуск и демонстрация:** пользователь открыл UI из созданного BAT launcher; текущая демонстрация полезна для UX-review, но не означает подтверждённую работу с постоянными рабочими данными. Заглавие «Обновление конфигурации сервиса» — название демонстрационной TASK, а не отдельная системная команда/функция.

**Проверяемые UX-сценарии будущей TASK:** (a) 2+ Workspace с разными наборами TASK не перемешиваются; (b) выбор TASK открывает соответствующие описание/этапы/отчёты; (c) новая TASK начинается с чистой формы и не создаётся до подтверждения; (d) выбор папки проходит серверную валидацию; (e) rename display label не меняет идентичность/immutable evidence; (f) прокрутка и адаптивность колонок корректны; (g) незавершённые и закрытые задачи честно различаются, recovery-ограничения сохраняются. Отдельно проверить, какие сценарии требуют расширения API/state model, до выдачи исполнимой постановки Codex/Claude.

**Документальный маршрут:** UX acceptance/приоритеты живут здесь (№24); архитектурные инварианты и только после утверждения новых механизмов их изменения — в №23; подтверждённые результаты выполненной инженерной TASK — в №25; краткий handoff — в №34. Не переносить эту ветку в документы архитектуры Ultra.

##### UX-2026-10-11-B — упрощение создания TASK, удаление старого навигатора и UI-статусы

**Статус:** USER-CONFIRMED ADDITIONAL UX REQUIREMENTS, review двух новых скриншотов 2026-10-11; **NOT IMPLEMENTED**, не является запуском CODEX TASK, разрешением на изменения state machine или удалением записей. Это уточнение дополняет UX-2026-10-11 выше. **Важное уточнение к первому требованию «Новая TASK» выше:** теперь пользователь предпочитает создание/появление пустой TASK сразу по плюсу, без отдельного шага «Создать TASK». До архитектурного решения фактическая server persistence, пустой draft и способы отмены остаются open design; фраза про отсутствие создания до дополнительного подтверждения — **ранняя UX-гипотеза, superseded данным уточнением**, а не текущий окончательный acceptance.

**Дополненные пожелания (целевая UX):**
1. **Создать TASK через плюс справа:** при выборе workspace пользователь нажимает плюс в колонке TASKS, видит сразу новую пустую TASK/рабочий черновик в центре и может вводить или вставлять исходную постановку одним большим полем. Никакого обязательного второго нажатия «Создать TASK» в отдельной боковой форме. Разработчику выяснить, создаётся ли немедленно durable TASK со статусом PLANNED, отдельный безопасный draft или локальный несохранённый черновик; явно сообщать пользователю, сохранена ли задача, и не создавать скрыто исполнимое задание только кликом по плюсу.
2. **Не заставлять человека декомпозировать постановку:** нынешние три поля «Название», «Цель», «RAW TASK» заменить в пользовательском сценарии одним свободным полем первоначальной постановки. Термин RAW TASK = исходный текст постановки целиком; это не отдельная ручная обязанность. Название, цель, этапы, внутренние ID, план и метаданные должны извлекаться/формироваться автоматизированным планировщиком/агентом в будущем, с проверяемой схемой и одобрением перед разрешённым исполнением; существующее API/хранилище может пока требовать эти поля. UI не должен выдумывать machine IDs/status или считать, что планировщик уже реализован.
3. **Удаление TASK:** пользователь хочет команду с понятной корзиной, но различать пустой черновик и существующую TASK с event log, snapshots, receipts, recovery/evidence или завершённым статусом. Для последних проектировать soft-delete/archive/visibility и отдельную безопасную retention policy, а не безвозвратное стирание доказательств. Никакого автоматического удаления/rollback файлов Workspace при удалении карточки. Новые backend-возможности — отдельное архитектурное согласование.
4. **Левая колонка:** только список Workspaces и плюс добавления проекта; форму «Добавить Workspace» из старого навигатора перенести в вызываемый плюсом ввод с безопасным выбором папки. Список проектов независим от задач; путь показывать по наведению/информационной подсказке или в свойствах, не постоянно под названиями. По возможности отдельная осознанная команда «Открыть папку» через поддерживаемый локальный механизм (обычный веб-сайт не может произвольно открывать Explorer).
5. **Правая колонка:** все TASK текущего Workspace (включая законченные, незавершённые, приостановленные/блокированные если подтверждено сервером) с кратким статусом; отдельный раскрывающийся список «Завершённые TASK» в старой левой панели упразднить после переноса. Названия короткие, доступны безопасному переименованию UI label, не machine identity/evidence.
6. **Русские названия в интерфейсе:** человекочитаемые обозначения вроде «В работе», «Завершена», «Ожидает проверки», «Требует восстановления»; это примеры UI labels, **не** новый state enum, и точный mapping на реально существующие server statuses нужно подтвердить. Технические ID, машинные receipts и значения state не переводить в хранилище.
7. **Верхняя панель:** отдельный реальный индикатор состояния подключения (рядом с «Обновить»), доступная проверка/диагностика при необходимости. Не путать с элементом «Проверка подключения» на demo-скриншоте: там это **имя демонстрационной TASK**, не готовая кнопка проверки соединения. Точно так же «Обновление конфигурации сервиса» — имя другой demo TASK; «Доставка и интеграция» — имя demo Workspace. Эти названия не требуют отдельных системных функций. Для неочевидных элементов предусмотреть знак вопроса/tooltip, где это действительно помогает.
8. **Устаревающая объединённая панель «Рабочие пространства / НАВИГАТОР»:** будущая целевая компоновка заменяет её; в текущем demo сохранять сколько нужно для работы/тестирования, затем убрать только после переноса и проверки каждой функции (добавление Workspace, новая TASK, список TASK, statuses, показ пути). Не удалять вслепую в отдельной косметической правке.
9. **Открытая альтернатива:** вкладки TASK внутри выбранного Workspace вместо правой панели обсуждались, но пользователь решил **пока оставить отдельную правую колонку TASKS**. Не записывать вкладки как утверждённый дизайн.

**Приёмочные UX-кейсы после отдельного USER GO:** плюс TASK → одна пустая область постановки без обязательных Name/Goal/RAW-полей и лишней второй кнопки; понятный статус сохранённости и отсутствие неожиданных исполняемых операций; создание/отмена draft; корректное безопасное удаление только по явному действию; переход между workspace меняет только список его задач; все состояния и завершённые TASK справа; locale UI ru без мутации серверных enum; индикатор связи наверху читает фактический health, не демонстрационную TASK; tooltip пути; после удаления навигатора нет недоступных ранее функций. До инженерной задачи выяснить требуемые изменения API/server и политику retention.

**Document impact:** №24 — владелец UX requirements/acceptance; №34 — краткий handoff; №23 **NO CHANGE** пока новая draft/delete/planner модель не утверждена; №25 **NO CHANGE** поскольку это не фактически выполненная/принятая инженерная TASK; общая Ultra-документация **NO CHANGE**.


##### UX-2026-10-11-C — пустая TASK, черновик и момент сохранения (итоговое уточнение пользователя)

**Статус:** USER-CONFIRMED UX PRINCIPLE / NOT IMPLEMENTED (обсуждение после предыдущих двух UX-review, 2026-10-11). Источник — устное уточнение пользователя и присланный скриншот переписки. **Это более позднее решение уточняет и supersedes предположение в UX-2026-10-11-B о немедленном создании durable TASK по нажатию плюса**; предыдущие записи сохранены как trace принятия решения. Не менять серверную state machine и не считать эту UX-концепцию уже действующим механизмом.

**Целевой сценарий (аналог пустого нового чата):**
1. Пользователь выбирает Workspace и нажимает плюс у списка TASK справа. В центральной области сразу открывается **пустой экран ввода одной свободной исходной постановки**; никаких обязательных отдельных Name/Goal/RAW TASK, machine ID или этапов на этом шаге.
2. **Если человек ничего не ввёл**, пустой экран не становится постоянной TASK в списке и исчезает при уходе/смене Workspace/закрытии. Не требовать на пустом вводе лишнего подтверждения, не показывать назойливое «Вы будете заполнять?»; пользователь рассматривал такое предупреждение, но сравнение с новым пустым чатом привело к предпочтению бесшумного исчезновения пустого экрана.
3. **Если человек начал вводить постановку**, её нужно защищать от случайной потери: предложен сохраняемый/автосохраняемый **черновик**, с явным пользователю признаком «черновик/сохранён/не сохранён» и предупреждением только при реальной угрозе потери несохранённого текста. Где хранить draft (браузер/локальный сервер), как избежать дублирования и когда очищать — отдельное безопасное design decision. Не выдавать эфемерную форму или локальный текст за durable server TASK.
4. После готовности текста человек явно передаёт постановку в будущий planner/механизм создания TASK. Планировщик формирует title, goal, этапы и IDs (с возможностью проверки/утверждения); **само нажатие плюса не запускает планирование, исполнение или файловую mutation**. У текущего backend может пока оставаться другая схема create: адаптация потребует отдельной инженерной TASK.
5. Если пользователь передумал, пустая форма исчезает; при непустом черновике UI сохраняет или предупреждает и предлагает безопасный вариант выхода. Удаление уже созданной/работавшей TASK — **отдельная** функция с retention/evidence-политикой, см. UX-2026-10-11-B; не путать с закрытием пустой формы.

**Почему:** пользователь хочет дать человеку одну точку входа с готовой постановкой, а деление на название, цель, этапы, RAW и ID оставить агенту/планировщику «под капотом». Предпочтение — минимальные ручные действия, как в ChatGPT: пустой новый чат не хранится как история лишь от факта открытия. Исходная raw-постановка при этом должна сохраняться внутри сформированной TASK как неизменный источник для будущего аудита.

**UX acceptance после отдельного USER GO:** плюс + пустой экран → выход без текста не оставляет TASK/операций; плюс + ввод текста → безопасная защита непустого draft, прозрачность факта сохранения, восстановление после предусмотренных сбоев в выбранном контракте; явное действие готовности передаёт исходник planner-у, не исполняет mutations; создание task ID/серверного состояния подтверждается server API; отсутствие навязчивого запроса на пустом экране. Требует адресной проверки реальных API, draft lifecycle, persistence и recovery до кодовой постановки.

**Согласованность записей:** A — трёхколоночная компоновка; B — одно поле, planner, русские статусы, отказ от навигатора, альтернативы; C — **наиболее актуальный выбор поведения пустой/непустой TASK**. A/B не удалять и не выдавать ранний вариант «пустая durable TASK сразу» за последний согласованный принцип. №23/№25/Ultra без изменений до отдельного архитектурного решения и фактической реализации.


#### WA4-R / CODEX-WA4-R-001 — next-candidate handoff (2026-10-11, NOT ASSIGNED)

**Original approved sequence remains:** OBSERVE → WARN → GATEWAY REQUIRED → STRICT → Final Audit. This is the terminal technical phase of the original RT-001 Web Alarm plan; it is **not** the deferred user interface redesign. ChatGPT composed two full copyable blocks in the prior conversation (personal Codex БЛОК 1 text + short chat launch message). **Candidate prepared only: not inserted by ChatGPT into the Codex personal card, no confirmed user assignment, no Codex execution, no rollout state activation.** Re-open personal Codex БЛОК 1 before start; follow DOC-TASK-BLOCK1-01@1 (user inserts and launches).

**Proposed first scoped engineering TASK:** `CODEX-WA4-R-001 — Strict Rollout Preflight / OBSERVE`, primary profile 23, plan 24, factual journal 25. Inventory actual tracked mutation routes (Web Alarm HTTP gateway, CLI and legacy direct restore, Desktop Commander Remote, direct agent file tools, external writers). For each path record owner/capability, observable vs unobservable evidence, migration/bypass risk and enforceability. If technically possible safely implement *only* evidence-only diagnostic OBSERVE with tests; otherwise return clear blockers/design recommendation. It must not create mutation authority, forge evidence, claim omniscient external interception, alter checkpoint or automatic recovery. **WARN / GATEWAY REQUIRED / STRICT forbidden in this first candidate**, as are live production mutation, Ultra changes and local Codex Git/GitHub. Use isolated temp tests (negative gateway/admission, closed TASK, stale CAS, offline, restart where needed), adversarial pass, exact full regression when runtime changed; report Factual Result, evidence, open risks and necessary next gate. Independent verification and separate USER GO before any later rollout mode.

**User scheduling decision:** first complete original technical route WA4-R, then start a separately approved UX implementation task from A/B/C. Current disposable demo is not production; WA4-O technical PASS does not certify all human visual/offline/narrow/recovery scenarios. Preserve known P-2/3/4, R-1…R-4 and non-atomic two-step move/rename, no new real controlled remote-disconnect proof. Existing WA4-O code/CI and UX wishes are not evidence of a strict-enforcement bypass closure.

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
| Recovery Closure RC-0…RC-6 | RC-0…RC-6 DONE / VERIFIED; RC-5 independent PASS 2026-10-09 |
| WA-4 — Strict mutation gateway + hardening | PARTIAL: WA4-E/A verified, WA4-O implementation independently automated PASS / interim UI acceptance (full visual pending); WA4-R OBSERVE preflight candidate / NOT ASSIGNED, future UX A/B/C unimplemented |

**HISTORICAL SNAPSHOT (2026-10-08; superseded by 2026-10-11 below):** WA-1…WA-3, RC-0…RC-4 и RC-6 = DONE / VERIFIED; RC-5 (projection implementation + repair) = RESULT READY, independent review по решению пользователя DEFERRED. RC-6 после серии Repair #1…\#4B и CLAUDE-WA-014: переход READY/FAILED_VERIFICATION→ACTIVE отклоняется при принятом/закреплённом ABORT/ROLLBACK или открытой RC-4 session; проверка и CAS перехода атомарны относительно recovery decisions под TASK-lock; законный ACTIVE до ABORT не блокирует rollback. Отчёт `TASK_CLAUDE-WA-014_RC6_ABORT_BEFORE_ACTIVE/rc6_wa014_report.md`: 580 OK, skip 1 ×2; WA-014 11/11; GitHub-аудит ChatGPT PASS. **NEXT: WA4-E TASK DRAFT / NOT STARTED; согласовать пользователя до передачи агенту**, затем WA4-A, WA4-O, WA4-R. Для WA4-E сохраняется STARTED-before-write под TASK-lock; standalone `/authorize` — только evidence. `.gitattributes` FOLLOW-UP deferred; старый WA-3 combined criterion = SUPERSEDED / DEFERRED, смысл — WA4-A.

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

**CURRENT UPDATE (2026-10-09):** RC-5 / CLAUDE-WA-016 DONE / VERIFIED by independent ChatGPT review at d53ec14 (60/60 targeted; 593 full OK, 1 skip, exit 0). Old CURRENT/DEFERRED snapshots above are historical, not active decisions. Recovery Closure RC-0…RC-6 DONE / VERIFIED. F-5 crash window and F-6 Windows test race OPEN FOLLOW-UPS. WA4-E NOT STARTED; needs separate user approval.

**CURRENT FOLLOW-UP UPDATE (2026-10-09, WA-017):** F-5 and F-6 = DONE / VERIFIED after independent ChatGPT audit and home Desktop runtime: 17 targeted tests OK; 607 full OK, 1 skipped; commit c7681c38. Recovery Closure RC-0...RC-6 remains DONE / VERIFIED. Documented residual follow-ups (legacy closed-TASK claim ownership without mutation authority; Windows sharing retry proposal WA4-R; task listing cosmetics) are not WA-017 blockers. WA4-E still NOT STARTED; its separate task/user approval and STARTED-before-write rule remain mandatory. Earlier F-5/F-6 OPEN entries are historical snapshots.

**CURRENT UPDATE (2026-10-09, CLAUDE-WA-018 / WA4-E):** user-approved WA4-E executed by Claude — authoritative executor/gateway (`web_alarm/mutation_executor.py`, `POST /tasks/{id}/mutations`, CLI `mutate`) for write/edit/create/delete and move/rename as two tracked operations. **RESULT READY / AWAITING INDEPENDENT VERIFICATION — not DONE.** STARTED is persisted under the held TASK lock before the first physical write; exact post-proof = RC-1 DONE receipt; replay of the same contract returns the persisted receipt. WA4-A/WA4-O/WA4-R remain NOT STARTED until WA4-E PASS. Earlier "WA4-E NOT STARTED" lines are historical. Report: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-018_WA4E_EXECUTOR/wa018_report.md`.

**CURRENT UPDATE (2026-10-11, WA4-E independent closeout):** CLAUDE-WA-018 / WA4-E = DONE / VERIFIED on `a142817b33964691584aadbd6ea6464779df1815` (177); independent ChatGPT 36/36 focused and 643 full OK (1 skipped), exit 0 on 2026-10-09; GitHub source/test blob identity reconfirmed 2026-10-11. STARTED-before-first-write is durable under TASK-lock, DONE exact bytes/receipt, repeat delivery produces no second write. Move/rename remain non-atomic two-step PARTIAL-safe. P-2 UNKNOWN/FAILED RETRY remains fail-closed unsupported; P-3/P-4 and R-1–R-4 remain open. WA4-A/O/R NOT STARTED; WA4-A requires separately approved USER TASK. `WA4-E NOT STARTED` in earlier dated sections is historical only.

**CURRENT 2026-10-11 — WA4-A independently accepted:** CODEX-WA4-A-001 (code/evidence №259 `b009f803`) A1–A8 deterministic lost-response acceptance; 46 new tests. [GitHub Windows CI run 38135287346](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38135287346): focused **166/166**, full **689/689**, smoke **5/5** PASS, 0 skips/errors, guarded violations 0. CI expansion №260 and self-recursion repair №261 are infrastructure, not new WA4-E authority. **NEXT WA4-O only on USER GO**; WA4-R NOT STARTED. P/R and non-atomic move constraints persist; no new real Remote disconnect. `DONE` operation receipt ≠ `VERIFIED` operation.

**CURRENT HANDOFF / 2026-10-11:** WA4-O PR №7 merged, technical CI 719/719 PASS; demo examined by user as interim version, full visual signoff pending. UX future A/B/C preserved in WA-4.6. WA4-R candidate `CODEX-WA4-R-001` preflight/OBSERVE prepared in prior chat only, user has not confirmed placement in personal Codex БЛОК 1 or execution; no strict rollout enabled. Next CHAT: 08→000→34→18→01→23/24/25, verify GitHub HEAD/personal Codex card, ask user whether to assign or revise candidate. This statement supersedes historical "WA4-O NEXT" lines above, without rewriting their dated history.
