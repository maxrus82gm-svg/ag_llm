# Журнал Web Alarm Workspace — выполненные задачи и аудит

**Назначение:** профильный журнал архитектурной ветки Web Alarm Workspace.

Этот документ хранит подробную историю фактически выполненной работы по Web Alarm Workspace и не заменяет общие проектные документы.

Роли документов разделены так:

- `23_Архитектура Web Alarm Workspace.md` — что представляет собой система и какие инварианты обязаны сохраняться;
- `24_План реализации Web Alarm Workspace.md` — в каком порядке реализуются крупные этапы и какие у них критерии приёмки;
- этот `25` — что реально было выполнено, какими микрозадачами, что проверено и чем закончился каждый этап;
- `000_Задачи для агента.md` — только текущая оперативная точка, отложенная задача и handoff;
- `06_Журнал выполнения и отчёты.md` — общая история всего проекта `ag_llm`.

---

## 1. Правило ведения журнала

Запись добавляется после фактического выполнения и проверки отдельной микрозадачи или крупного этапа Web Alarm Workspace.

Рабочий цикл:

```text
TASK в обычном Chat
↓
БЛОК 1 в 000
↓
одна небольшая Remote-микрозадача
↓
verification
↓
короткий отчёт в Chat
↓
запись результата в этот журнал
↓
следующая микрозадача
```
## 2. Формат записи

Каждая большая задача `WA-*` получает собственный раздел. Внутри неё микрозадачи фиксируются последовательно.

Минимальная запись микрозадачи должна содержать:

- идентификатор и краткую цель;
- статус;
- какие файлы или компоненты затронуты;
- что реально сделано;
- чем результат проверен;
- проблемы, recovery или rollback, если они были;
- итог;
- следующий безопасный шаг.

Пример структуры:

```text
WA-1 — Фундамент состояния и файловое ядро

WA-1.1 — DONE
Goal:
Files:
Result:
Verification:
Problems / Recovery:
Next:

WA-1.2 — ...
```

Запись не создаётся заранее как будто работа уже выполнена. План принадлежит `24`; этот журнал отражает только факты выполнения.

---

## 3. Текущее состояние ветки

**Статус:** WA-1 + WA-2 DONE / VERIFIED; WA-3 IN PROGRESS — WA-3.1–WA-3.7 DONE / VERIFIED; WA-3.7 fresh reopen PASS; один combined post-change controlled-disconnect acceptance gate остаётся открыт.

Архитектура зафиксирована в `23`, план реализации — в `24`.

WA-3.5 завершена целиком; fresh-process reopen PASS. WA-3.6 DONE / VERIFIED / FRESH REOPEN PASS. WA-3.7 DONE / VERIFIED / FRESH REOPEN PASS: M001–M003 VERIFIED; focused 95/95, full WA 197/197, compileall/diff-check PASS. Final WA-3 reconciliation не закрыла parent gate: `CTRL-001` = FULL local change без disconnect, `CTRL-002` = real disconnect/recovery с NONE side effect. Требуется один combined incident: local change уже произошло, затем Remote disconnect до Chat-result.

---

## 4. WA-1 — Фундамент состояния и файловое ядро

### WA-1.1 — Зафиксировать схемы данных

**Статус:** DONE / VERIFIED — 2026-10-01.

**Goal:** определить минимальные машинные схемы для Workspace registration, TASK, microtask, manifest, snapshot record, operation record, verification record, checkpoint и event log.

**Files:**
- `web_alarm/__init__.py` — новый файл;
- `web_alarm/models.py` — новый файл;
- `test_web_alarm_models.py` — новый focused regression;
- `24_План реализации Web Alarm Workspace.md` — обновлён фактический статус этапа;
- этот журнал — добавлена подтверждённая история выполнения.

**Result:**
- создан отдельный пакет `web_alarm`, не связанный с production runtime Ultra;
- введён `SCHEMA_VERSION = 1`;
- определены versioned records для Workspace, TASK, microtask, manifest entry, snapshot, operation, verification, checkpoint и event;
- для сущностей заданы устойчивые ID, timestamps и schema version;
- зафиксированы recovery-состояния микрозадачи, включая `UNKNOWN_AFTER_DISCONNECT` и `RECOVERY_REQUIRED`;
- operation schema содержит `operation_id`, replay fingerprint и precondition hash;
- manifest/snapshot различают существующий и новый файл;
- checkpoint содержит `NEXT SAFE ACTION`;
- добавлен `record_to_dict()` для JSON-friendly primitives.

**Verification:**
- `python -B -m unittest -v test_web_alarm_models.py` → **7/7 PASS**;
- `git diff --check -- web_alarm/__init__.py web_alarm/models.py test_web_alarm_models.py` → **PASS**;
- тестовый запуск выполнялся с `-B`, чтобы не создавать bytecode-файлы в ходе verification.

**Problems / Recovery:**
- при составном обновлении документа `24` ответ Remote был заблокирован после частичного исполнения;
- вместо слепого повтора выполнен reread фактического состояния;
- подтверждено, какие части уже применились, после чего внесены только отсутствующие изменения;
- дублирования мутаций не произошло.

**Restore point:** до первой кодовой мутации создан и проверен manifest в `Alarm/ALARM_TASK_SESSION/TASK_WA-1.1/`; три новых code-файла были явно зафиксированы как отсутствовавшие до этапа, существующие документы сохранены с SHA256.

**Next:** WA-1.2 — Workspace Registry. Этап **не активирован** и не должен начинаться автоматически.

---

### WA-1.2 — Реализовать Workspace Registry

**Статус:** DONE / VERIFIED — 2026-10-01.

**Goal:** регистрировать реальные внешние Workspace через устойчивые `workspace_id`, `display_name`, `workspace_root`, сохранять их на диск и повторно открывать после перезапуска процесса.

**Files:**
- `web_alarm/workspace_registry.py` — новый disk-backed Registry;
- `test_web_alarm_workspace_registry.py` — новый focused regression;
- `web_alarm/__init__.py` — экспорт Registry;
- `01/05/06/23/24/25` — синхронизация подтверждённого статуса ветки.

**Result:**
- Registry хранит каждый Workspace отдельным JSON record;
- исходный проект остаётся снаружи Web Alarm state и не копируется;
- повторная регистрация того же root возвращает прежнюю identity;
- две разные project roots получают разные устойчивые ID;
- новая инстанция Registry перечитывает сохранённую регистрацию;
- storage root по умолчанию — machine-local Web Alarm root; в tests он явно изолируется;
- missing root, file вместо directory, unsafe explicit ID и unknown schema version блокируются fail-closed;
- запись публикуется через temporary file + `os.replace`.

**Verification:**
- `python -B -m unittest -v test_web_alarm_workspace_registry.py test_web_alarm_models.py` → **15/15 PASS**;
- `git diff --check` по WA-1.2 code/test scope → **PASS**.

**Problems / Recovery:** disconnect/replay recovery не потребовался; Remote-команды этой микрозадачи подтвердились однозначно.

**Restore point:** до code mutation создан и SHA256-проверен `Alarm/ALARM_TASK_SESSION/TASK_WA-1.2/manifest.json`; `workspace_registry.py` и его test были записаны как отсутствовавшие до этапа, `__init__.py` и документация имеют проверенные snapshots.

**Next:** WA-1.3 — TASK и план микрозадач. Запускается отдельной микрозадачей с новым restore point.

---

### WA-1.3 — TASK и план микрозадач

**Статус:** DONE / VERIFIED — 2026-10-01.

**Goal:** реализовать persistent lifecycle TASK и ordered microtask plan, сохранив RAW TASK отдельно от подготовленного плана.

**Files:**
- `web_alarm/task_store.py` — новый TASK/microtask storage;
- `web_alarm/models.py` — добавлен `TaskPlanRecord`;
- `test_web_alarm_task_store.py` — новый focused regression;
- `test_web_alarm_models.py` — schema regression расширен;
- `web_alarm/__init__.py` — экспорт TaskStore;
- `01/05/06/23/24/25` — синхронизация подтверждённого статуса ветки.

**Result:**
- TASK публикуется в `tasks/active/<task_id>/` с `task.json`, immutable `task.md`, `plan.json` и `microtasks/*.json`;
- RAW TASK и metadata проверяются на drift при каждом open;
- ordered plan и current microtask сохраняются и восстанавливаются после новой инстанции TaskStore;
- `set_plan` валидирует exact set микрозадач, запрещает duplicates/unknown IDs и обновляет sequence;
- `complete_task` переносит всю директорию из `active` в `completed` без потери source/plan/microtasks;
- `archive_task` оставляет completed TASK читаемой со статусом ARCHIVED;
- unsafe task IDs и unknown schema version блокируются fail-closed.

**Verification:**
- `python -B -m unittest -v test_web_alarm_task_store.py test_web_alarm_workspace_registry.py test_web_alarm_models.py` → **25/25 PASS**;
- `git diff --check` по WA-1.3 code/test scope → **PASS**.

**Problems / Recovery:** disconnect/replay recovery не потребовался; все изменяющие Remote-шаги были подтверждены.

**Restore point:** до code mutation создан и SHA256-проверен `Alarm/ALARM_TASK_SESSION/TASK_WA-1.3/manifest.json`; новый TaskStore/test записаны как отсутствовавшие до этапа, существующие model/init/tests/docs имеют snapshots.

**Next:** WA-1.4 — Manifest и Snapshot. Запускается новой микрозадачей с отдельным restore point.

---

### WA-1.4 — Manifest и Snapshot

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** перед изменениями микрозадачи создавать полный manifest ожидаемых targets и подтверждённый restore point, позволяющий однозначно вернуться к исходному состоянию текущего этапа.

**Files:**
- `web_alarm/manifest_store.py` — новый Manifest/Snapshot storage и explicit restore;
- `web_alarm/models.py` — добавлены `ManifestStatus` и `ManifestRecord`;
- `web_alarm/task_store.py` — per-microtask work directory и persistent status helpers;
- `test_web_alarm_manifest_store.py` — новый focused regression;
- `test_web_alarm_task_store.py` / `test_web_alarm_models.py` — расширены regressions;
- `web_alarm/__init__.py` — экспорт ManifestSnapshotStore;
- `01/04/05/06/23/24/25` — синхронизация подтверждённого статуса.

**Result:**
- restore point хранится отдельно внутри work directory микрозадачи;
- existing file получает byte snapshot, size, SHA256, captured_at и snapshot path;
- новый target фиксируется через `exists_before=false` без fake snapshot;
- source перечитывается после capture, а snapshot перечитывается и hash-проверяется до публикации restore point;
- повторный prepare не перезаписывает исходный restore point;
- target outside registered Workspace, directory/symlink ambiguity, duplicate target, corrupted/missing snapshot и tampered internal snapshot path блокируются fail-closed;
- successful prepare переводит microtask только в `BACKUP_VERIFIED`, не в полноценный READY;
- explicit restore побайтно возвращает existing file и удаляет file, которого до этапа не существовало;
- restore validation/mutation failure переводит microtask в `RECOVERY_REQUIRED`.

**Verification:**
- initial focused regression → **34/34 PASS**;
- после дополнительного hardening повторная проверка корректно выявила missing `_safe_component`: **6 tests ERROR**, verification не засчитана;
- выполнен disk reconciliation/repair, затем финальный focused regression → **36/36 PASS**;
- `git diff --check` → **PASS**.

**Problems / Recovery:** реальный post-test defect не был скрыт: failed verification записана как FAILED, исправление выполнялось отдельным repair-step, после чего весь набор проверок был повторён.

**Restore point:** до первой WA-1.4 mutation и перед documentation closeout созданы и SHA256-проверены snapshots в `Alarm/ALARM_TASK_SESSION/TASK_WA-1.4/`.

**Next:** WA-1.5 — Event Log и Checkpoint. Запускается новой микрозадачей с отдельным restore point.

---

### WA-1.5 — Event Log и Checkpoint

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** разделить append-only хронологию фактов и компактное текущее состояние TASK.

**Files:**
- `web_alarm/event_checkpoint_store.py` — новый storage;
- `test_web_alarm_event_checkpoint_store.py` — focused regression;
- `web_alarm/__init__.py` — package export;
- `01/04/05/06/23/24/25` — синхронизация статуса.

**Result:**
- `events.jsonl` дописывается append-only и переживает новую инстанцию storage;
- `checkpoint.json` публикуется atomic replace;
- `checkpoint.md` генерируется из JSON и содержит `NEXT SAFE ACTION`;
- checkpoint связывается с TASK/workspace и текущей/последней verified microtask;
- обновление checkpoint не меняет event history;
- corrupted/unknown-schema checkpoint и invalid event line блокируются fail-closed.

**Verification:** полный WA focused regression → **42/42 PASS**; `git diff --check` → **PASS**.

**Restore point:** до code mutation и documentation closeout созданы и SHA256-проверены snapshots в `Alarm/ALARM_TASK_SESSION/TASK_WA-1.5/`.

**Next:** WA-1.6 — Базовый CLI.

---

### WA-1.6 — Базовый CLI

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** дать WA-1 командную точку входа для Desktop Commander и локального тестирования без UI/Server.

**Files:**
- `web_alarm/cli.py` — новый argparse CLI;
- `web_alarm/__main__.py` — entrypoint `python -m web_alarm`;
- `test_web_alarm_cli.py` — focused CLI regression.

**Result:**
- task create/open/complete;
- microtask create/prepare;
- snapshot verify/restore;
- checkpoint write/show;
- status и report;
- явный `--storage-root`;
- JSON output для machine-readable операций;
- ошибки возвращают exit code 2 и понятный `ERROR:` в stderr.

**Verification:** CLI + полный WA regression → **47/47 PASS**; `python -B -m web_alarm --help` smoke PASS; `git diff --check` → **PASS**.

**Result WA-1:** большая задача WA-1 полностью **DONE / VERIFIED**. Следующий большой этап — WA-2 Local Web Alarm Server + UI.

---

## 5. WA-2 — Local Web Alarm Server + UI

### WA-2.1 — Server API

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** поднять узкий localhost-first HTTP API поверх WA-1 core storage без скрытых real-project mutations.

**Files:**
- `web_alarm/server.py` — новый stdlib HTTP server/API facade;
- `test_web_alarm_server.py` — focused Server API regression;
- `01/04/05/06/23/24/25` — синхронизация статуса ветки.

**Result:**
- `GET /status`;
- `GET/POST /workspaces`;
- `GET/POST /tasks`, `GET /tasks/{id}`;
- `POST /tasks/{id}/plan` и `/microtasks`;
- `POST /microtasks/{id}/prepare`;
- `POST /microtasks/{id}/snapshot` только для verify;
- `POST /microtasks/{id}/report`;
- `POST /tasks/{id}/recover` как read-only/advisory recovery entry;
- loopback bind по умолчанию, non-loopback требует явного override;
- TASK нельзя создать для незарегистрированного Workspace;
- server-side restore реального Workspace намеренно не экспонирован на WA-2.1;
- invalid JSON/typed body возвращают явные 4xx JSON errors.

**Verification:** первый прогон → 56/57 PASS, 1 FAIL из-за отсутствующего workspace-binding check; defect исправлен без false PASS. Финальный полный WA regression → **57/57 PASS**; реальный loopback HTTP smoke PASS; `git diff --check` → **PASS**.

**Problems / Recovery:** во время documentation closeout один составной Remote-вызов вернулся с transport failure после частичного исполнения. Выполнен disk reconciliation: уже применённые изменения не повторялись, дописан только отсутствующий CURRENT-status в `24`.

**Restore point:** до code mutation и documentation closeout созданы и SHA256-проверены snapshots в `Alarm/ALARM_TASK_SESSION/TASK_WA-2.1/`.

**Next:** WA-2.2 — Server-owned state machine.

---

### WA-2.2 — Server-owned state machine

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** сделать Server авторитетным владельцем microtask transition и `NEXT SAFE ACTION`, не доверяя клиенту произвольные статусы.

**Files:**
- `web_alarm/state_machine.py` — новый authoritative policy layer;
- `web_alarm/server.py` — prepare/snapshot/transition интеграция;
- `test_web_alarm_state_machine.py` — focused regression;
- `test_web_alarm_server.py` — transition API regression;
- `01/04/05/06/23/24/25` — синхронизация статуса.

**Result:**
- `PLANNED → ACTIVE` без restore point физически отклоняется;
- `PREPARING/BACKUP_VERIFIED` не могут быть назначены клиентом — их создаёт prepare flow;
- `BACKUP_VERIFIED → READY → ACTIVE` требует verified restore point;
- предыдущая microtask должна быть VERIFIED до подготовки следующей;
- одновременно не допускается второй ACTIVE microtask;
- `DONE → VERIFIED` требует непустой verification evidence;
- accepted/rejected transitions пишутся в event log;
- checkpoint обновляется из фактического состояния и хранит computed `NEXT SAFE ACTION`;
- invalid transition возвращает HTTP 409 с current/requested status, reason и `NEXT SAFE ACTION`;
- recovery statuses распознаются, но reconciliation остаётся WA-3.

**Verification:** focused state-machine + полный WA regression → **64/64 PASS**; `git diff --check` → **PASS**.

**Restore point:** до code mutation и documentation closeout созданы и SHA256-проверены snapshots в `Alarm/ALARM_TASK_SESSION/TASK_WA-2.2/`.

**Next:** WA-2.3 — Минимальный UI.

---

### WA-2.3 — Минимальный UI

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** дать локальную рабочую оболочку для человека поверх Server API без UI-фреймворка и без скрытых project mutations.

**Files:**
- `web_alarm/ui.py` — статический local HTML/JS dashboard;
- `web_alarm/server.py` — HTML serving + read-only `GET /tasks/{id}/ui` aggregate;
- `test_web_alarm_ui.py` — focused UI regression.

**Result:**
- `/` и `/ui` отдают local dashboard без CDN;
- отображаются Workspace и active/completed TASK;
- TASK создаётся из RAW text с выбором registered Workspace;
- detail view показывает RAW TASK, plan/microtasks, checkpoint, manifest/snapshot, reports, recovery state и крупный `NEXT SAFE ACTION`;
- пользовательский контент выводится через `textContent`, не через `innerHTML`;
- read-only UI aggregate не изменяет real Workspace;
- реальные HTTP smoke tests проверяют HTML root и JSON UI aggregate.

**Verification:** UI + полный WA regression → **69/69 PASS**; `git diff --check` → **PASS**.

**Restore point:** до code mutation и documentation closeout созданы и SHA256-проверены snapshots в `Alarm/ALARM_TASK_SESSION/TASK_WA-2.3/`.

**Next:** WA-2.4 — Entry Context Pack.

---

### WA-2.4 — Entry Context Pack

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** одной read-only операцией дать новому Chat компактную, restart-safe рабочую точку без чтения полной истории TASK.

**Files:**
- `web_alarm/context_pack.py` — новый builder;
- `web_alarm/server.py` — read-only `GET /tasks/{id}/context`;
- `test_web_alarm_context_pack.py` — focused regression.

**Result:**
- pack содержит TASK, WORKSPACE, GOAL, PLAN SUMMARY, LAST VERIFIED, CURRENT MICROTASK, CURRENT STATUS, SNAPSHOT STATUS, LAST OPERATION, NEXT SAFE ACTION, PROTOCOL RULES;
- дополнительно формируется компактный `CONTEXT_TEXT` для нового Chat;
- pack строится из persistent state/checkpoint/state-machine fallback и переживает новую инстанцию builder/server;
- полная event history не читается и event noise не увеличивает context pack;
- операция read-only и не мутирует real Workspace.

**Verification:** Entry Context Pack + полный WA regression → **75/75 PASS**; compactness/restart/read-only tests PASS; `git diff --check` → **PASS**.

**Result WA-2:** большая задача WA-2 полностью **DONE / VERIFIED**.

**Next:** WA-3.1 — Канонический Remote entry.

---

## 6. WA-3 — Remote workflow, recovery и replay protection

### WA-3.1 — Канонический Remote entry

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** дать новому Chat/после reconnect один fail-closed read-only вход, который сначала восстанавливает рабочий контекст и только затем позволяет следовать `NEXT SAFE ACTION`.

**Files:**
- `web_alarm/remote_entry.py` — active TASK resolver + canonical entry result;
- `web_alarm/cli.py` — `enter [--task-id]` и `status --active`;
- `test_web_alarm_remote_entry.py` — focused regression;
- `test_web_alarm_cli.py` — CLI integration regression.

**Result:**
- без explicit id canonical entry принимает только ровно одну active TASK;
- 0 active TASK и несколько active TASK fail-closed;
- completed TASK не принимается как active;
- explicit `--task-id` позволяет безопасно выбрать одну из нескольких active TASK;
- result read-only и содержит Entry Context Pack;
- recovery statuses маркируются `RECOVERY_REVIEW_REQUIRED` и `RECONCILE_BEFORE_MUTATION`;
- normal state маркируется `CONTEXT_READY` и направляет к `NEXT SAFE ACTION`;
- новая CLI/process instance получает тот же persistent context.

**Real recovery event:** во время подготовки WA-3.1 оборвалась связь. После reconnect сначала выполнен reconciliation: source/snapshot hashes совпали с manifest, новые файлы `remote_entry.py`/test ещё отсутствовали, `000` оставался неактивированным. Следовательно, implementation не начинался; blind replay не выполнялся, работа продолжилась с activation step.

**Verification:** focused Remote-entry + полный WA regression → **82/82 PASS**; `git diff --check` → **PASS**.

**Restore point:** initial scope и documentation closeout snapshot-нуты и SHA256-проверены в `Alarm/ALARM_TASK_SESSION/TASK_WA-3.1/`.

**Next:** WA-3.2 — Operation ID / replay identity.

---

### WA-3.2 — Operation ID / replay identity

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** закрепить persistent identity для потенциально изменяющих операций и отличать повтор доставки от новой операции.

**Files:** `web_alarm/operation_store.py`, `web_alarm/server.py`, `web_alarm/__init__.py`, `test_web_alarm_operation_store.py`.

**Result:** новый operation создаётся в `INTENT` со stable `operation_id` и canonical request fingerprint. Повтор того же ID с тем же request возвращает существующую запись; другой request под тем же ID блокируется. Lifecycle ограничен переходами `INTENT → STARTED → DONE → VERIFIED / FAILED / UNKNOWN_AFTER_DISCONNECT`; повтор текущего состояния идемпотентен. Для `STARTED` и `UNKNOWN_AFTER_DISCONNECT` replay decision = `RECONCILE_REQUIRED`. Store переживает restart и не выполняет real-project mutation.

Во время интеграции один composite Remote call оборвался частично: `__init__.py` уже был обновлён, `server.py` — нет. После disk reconciliation повторно менялся только `server.py`.

**Verification:** полный WA regression → **90/90 PASS**; `git diff --check` → **PASS**.

**Restore point:** `Alarm/ALARM_TASK_SESSION/TASK_WA-3.2/`.

**Next:** WA-3.3 — Reconciliation.

---

### DOC-WA-REMOTE-OBS-001 — Remote transport / recovery evidence journal

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** вынести реальные Remote disconnect/partial-execution наблюдения в отдельный технический журнал Web Alarm и использовать их как evidence для WA-3.3, не размазывая Wiki Links по документации.

**Result:** создан `26_Журнал наблюдений Remote - обрывы, transport и recovery evidence.md`. В документ занесены подтверждённые incident cases, текущая process/runtime диагностика Desktop Commander 0.2.52, анализ установленного `remote-channel.js`, failure-mode границы, incident packet и поля будущей telemetry.

**Technical findings:** Remote process chain оставался жив в наблюдаемом окне; Windows crash evidence не найдено; transport использует durable `mcp_remote_calls` + Realtime doorbell, conditional `pending → executing` claim, pending recovery after reconnect, half-open WebSocket self-heal и отдельную terminal result write. Это подтверждает, что transport failure/потерянный reply нельзя трактовать как отсутствие mutation.

**Obsidian:** один Wiki Link на документ 26 добавлен только в `23_Архитектура Web Alarm Workspace.md`.

**Code runtime:** не изменялся.

**Next:** активировать WA-3.3.1 — Reconciliation Evidence / read-only inspector.

---

### WA-3.3.1 — Reconciliation Evidence / read-only inspector

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** собрать доказуемый read-only evidence по одной active operation/microtask без retry/rollback и без изменения Workspace/persistent recovery state.

**Files:** `web_alarm/reconciliation.py`, `test_web_alarm_reconciliation.py`, package export в `web_alarm/__init__.py`.

**Result:** collector связывает TASK/Workspace, operation, manifest entries и snapshots; чисто читает snapshot bytes и current files; возвращает per-target pre/current/optional exact expected-post evidence, operation precondition binding, verification evidence и классификации `PRE_STATE`, `EXPECTED_POST_STATE`, `DRIFT`, `CHANGED_UNCLASSIFIED`, `MISSING_EVIDENCE`. Corrupted snapshot не вызывает mutating `verify_restore_point` и не меняет manifest/microtask status.

**Verification:** первый focused run 9/10 PASS из-за неверного test expectation для доказанного PRE_STATE; test исправлен без изменения корректной runtime logic. Повтор focused → 10/10 PASS. Финальный полный WA regression → **100/100 PASS**; py_compile PASS; `git diff --check` PASS.

**Live transport evidence:** во время read-only inspection зафиксирован `INC-REMOTE-005`: `Result could not be stored (TypeError: fetch failed)` при живом Desktop Commander process. Incident добавлен в документ 26; mutation отсутствовала, поэтому read-only calls повторены безопасно по одному.

**Next:** WA-3.3.2 — Deterministic Decision Engine.

---

### WA-3.3.2 — Deterministic Decision Engine

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** преобразовывать immutable evidence WA-3.3.1 в одно детерминированное fail-closed recovery decision без исполнения mutation.

**Files:** `web_alarm/reconciliation_decision.py`, `test_web_alarm_reconciliation_decision.py`, package export в `web_alarm/__init__.py`.

**Result:** engine выдаёт только `ADOPT_CURRENT_STATE`, `RETRY_SAFE`, `ROLLBACK_CURRENT_MICROTASK` или `MANUAL_REVIEW_REQUIRED`; решение содержит reason, evidence fingerprint/summary и `NEXT SAFE ACTION`. `DRIFT`, `MISSING_EVIDENCE`, `CHANGED_UNCLASSIFIED`, lifecycle/evidence conflict и неполный exact post-state fail-closed. `automatic_mutation_authorized=false` для любого решения.

**Verification:** первый focused run 15/16 PASS выявил policy defect: exact post-state при lifecycle `INTENT` ошибочно принимался как ADOPT. После repair focused → **16/16 PASS**. Независимый reconciliation после Remote-разрыва повторно подтвердил full WA regression → **116/116 PASS**, py_compile PASS, `git diff --check` PASS.

**Recovery / transport:** `INC-REMOTE-008` показал, что automatic continuation ушёл дальше видимой Chat-точки: WA-3.3.2 code/session реально завершились, тогда как часть документации оставалась на более ранней стадии. Рабочий код не откатывался; disk state independently verified, затем документация reconciled. `INC-REMOTE-007` отдельно показал, что manual scope-extension snapshot должен быть immutable/versioned.

**Next:** WA-3.3.3 — Server / Remote integration.

---

### WA-3.3.3 — Server / Remote reconciliation integration

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** сделать WA-3.3.1 Evidence Collector + WA-3.3.2 Decision Engine доступными новому Chat через read-only Server / Context / Remote path без исполнения recovery mutation.

**Files:** `web_alarm/reconciliation_service.py`, `web_alarm/server.py`, `web_alarm/context_pack.py`, `web_alarm/remote_entry.py`, `web_alarm/__init__.py`, `test_web_alarm_reconciliation_integration.py`.

**Result:**
- создан `ReconciliationService`, объединяющий evidence + decision;
- Server отдаёт read-only reconciliation result с evidence, decision и authoritative `NEXT_SAFE_ACTION`;
- Entry Context Pack автоматически прикладывает reconciliation bundle, когда recovery действительно нужен;
- Canonical Remote Entry поднимает reconciliation decision новому Chat и остаётся `READ_ONLY=true`;
- никакие retry/rollback/adopt действия автоматически не исполняются;
- результат переживает новый Server/Python process.

**Verification:** independent recovery Session A: focused integration **7/7 PASS**, full WA **123/123 PASS**, py_compile + diff-check PASS. Fresh Session B: restart-specific new Server/Remote/HTTP checks **3/3 PASS**.

**Recovery / transport:** реализация снова ушла дальше видимой Chat-точки после обрывов. Session.jsonl показал уже выполненные integration edits и focused verification. Старый финальный Python process к моменту reconciliation уже отсутствовал, поэтому код проверен независимым новым process вместо слепого повторения старого tool call. Несколько result-storage failures после частичных edits обработаны через disk reread и apply-only-missing.

**Next:** WA-3.3.4 — recovery scenarios / final verification.

---

### WA-3.3.4 — Recovery scenarios / final verification

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** доказать end-to-end recovery matrix перед закрытием WA-3.3 без автоматического исполнения recovery mutations.

**Session A:** core four-way matrix → `RETRY_SAFE`, `ADOPT_CURRENT_STATE`, `ROLLBACK_CURRENT_MICROTASK`, `MANUAL_REVIEW_REQUIRED`; **4/4 PASS**.

**Session B:** `UNKNOWN_AFTER_DISCONNECT`, duplicate same-operation delivery, fresh service instances, new-file exact post, deleted-file expected absence, corrupted snapshot fail-closed; весь focused file → **10/10 PASS**.

**Session C:** новый process, py_compile PASS, полный WA regression → **133/133 PASS**, `git diff --check` PASS. Runtime repair не понадобился.

**Safety:** reconciliation remained read-only; expected decisions did not execute retry/rollback/adopt. Session boundaries used separate persistent close/reopen points and versioned snapshots (`initial_v1`, `session_b_v1`, `closeout_v1`).

**Result:** WA-3.3 Reconciliation полностью **DONE / VERIFIED**.

**Next:** WA-3.4 — Recovery после restart Chat/Server.

---

### WA-3.4 — Recovery after restart Chat / Server

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** доказать, что persistent recovery одинаково восстанавливается после нового Chat при живом Server и после полного restart Chat+Server.

**Case A:** родительский HTTP Server остаётся жив; новый Python subprocess как новый Chat читает `/tasks/{id}/context`. Persistent checkpoint, reconciliation decision/fingerprint и `NEXT SAFE ACTION` совпадают с baseline; Workspace не меняется → **1/1 PASS**.

**Case B:** новый Python subprocess сам поднимает новый Web Alarm Server из того же storage, читает context по HTTP и создаёт новый `RemoteEntry`. Два последовательных process-level restart дают идентичный recovery state → focused suite **2/2 PASS**.

**Final verification:** full WA regression **135/135 PASS**, py_compile + diff-check PASS. Runtime repair не понадобился.

**Recovery during transition:** `INC-REMOTE-012` — transition call потерял внешний result после того, как WA-3.4 directory + `manifest_initial_v1` уже сохранились, но до context/session. Manifest reread + SHA256 reverify PASS; snapshot generation не replay-илась, созданы только отсутствующие session files.

**Next:** WA-3.5 — Watchdog signal, not authority.

---

### DOC-WA-REMOTE-CONCLUSIONS-001 — Consolidated Remote failure conclusions

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** превратить реальные INC-REMOTE-001…013 и связанные recovery observations в устойчивые инженерные правила для WA-3.5+, WA-3.6 и WA-4.

**Result:**
- в документе 26 добавлена consolidated baseline-модель failure handling;
- подтверждено, что caller/UI error может соответствовать 0, partial или full execution;
- composite orchestration признана неатомарной без per-step receipts/post-state proof;
- visible Chat отделён от authoritative persistent workflow state;
- execution receipt, persistence receipt и UI delivery признаны разными acknowledgement layers;
- bootstrap/closeout закреплены как отдельные state machines с persistent receipts/gates;
- fresh-process reopen закреплён как обязательная часть recovery acceptance;
- Watchdog/transport telemetry закреплены как evidence-only, без recovery authority;
- immutable/versioned snapshots и physical storage вне Obsidian vault подняты в архитектурные/rollout требования.

**Propagation:** architectural invariants → `23`; implementation requirements for WA-3.5/3.6/WA-4 → `24`; factual status/history → `05/06/25/000`.

**Runtime:** не изменялся.

**Next:** WA-3.5 — Watchdog signal, not authority.

---

### WA-3.5.A — Transport Event Model / persistent append-only Store

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** создать restart-safe append-only storage transport evidence без Server ingestion и без recovery/workflow authority.

**Files:** `web_alarm/transport_event_store.py`, `test_web_alarm_transport_event_store.py`, package export в `web_alarm/__init__.py`.

**Result:** шесть event types (`REMOTE_ONLINE`, `REMOTE_OFFLINE`, `REMOTE_RECOVERED`, `RESULT_DELIVERY_FAILED`, `MESSAGE_DELIVERY_TIMEOUT`, `PROCESS_RESTARTED`); nullable `task_id/microtask_id/operation_id`; `remote_call_kind`, `error_class`, process metadata, payload и timestamp; global `transport/transport_events.jsonl`; fail-closed read при corrupted JSON/schema/type/metadata. Store не создаёт TASK/checkpoint state и не имеет recovery authority.

**Verification:** focused **10/10 PASS**; full Web Alarm **145/145 PASS**; py_compile + `git diff --check` PASS.

**Restore points:** `code_a_v1` + `closeout_a_docs_v1` VERIFIED.

**Next:** fresh-process reopen A; затем WA-3.5.B Watchdog / Server ingestion.

---

### WA-3.5.B — Watchdog / Server transport evidence ingestion

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** подключить transport evidence к существующему Web Alarm Server без передачи Watchdog какой-либо workflow/recovery authority.

**Files:** `web_alarm/server.py`, `test_web_alarm_transport_ingestion.py`.

**Result:** GET/POST `/transport/events`, capability `transport_evidence`, filters по task/microtask/operation/event_type, real HTTP ingestion/read, явные `authority=evidence_only` и `workflow_mutation_performed=false`.

**Safety proof:** ingestion byte-for-byte не меняет TASK directory и Workspace; checkpoint record до/после идентичен. Transport route не вызывает state machine.

**Verification:** focused **7/7 PASS**; full Web Alarm **152/152 PASS**; pycompile + `git diff --check` PASS.

**Restore points:** `code_b_v1` + `closeout_b_docs_v1` VERIFIED.

**Next:** fresh-process reopen B; затем WA-3.5.C recovery/restart persistence tests.

---

### WA-3.5.C — Recovery/Restart transport persistence tests

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** доказать restart-safe transport evidence и replay identity при `UNKNOWN_AFTER_DISCONNECT`, process restart и duplicate event delivery.

**Test-first:** initial focused run **3/5 PASS**; два failure доказали, что same `event_id` повторно append-ился и conflicting reuse не блокировался.

**Repair:** отдельный `repair_c_store_v1` snapshot; Store теперь возвращает existing record при same-ID/same-evidence replay и fail-closed конфликт при same-ID/different-evidence.

**Scenarios:** OFFLINE→RECOVERED order, RESULT_DELIVERY_FAILED, PROCESS_RESTARTED, fresh Python process persistence, UNKNOWN operation + bound evidence reopen — PASS.

**Verification:** C + A/B transport suites **22/22 PASS**; full Web Alarm **157/157 PASS**; pycompile + diff-check PASS.

**Fresh reopen:** PASS — новый process независимо восстановил A+B+C как DONE / VERIFIED и D как NOT ACTIVATED.

**Next:** WA-3.5.D authority-negative tests, но D пока не активирована.

---

### WA-3.5.D — Authority-negative tests + final Watchdog verification

**Статус:** DONE / VERIFIED — 2026-10-02.

**Goal:** механически доказать, что Watchdog/transport evidence не имеет recovery/workflow authority.

**Files:** `test_web_alarm_transport_authority.py`; runtime-файлы WA-3.5 не потребовали repair.

**Result:** focused authority-negative matrix **7/7 PASS**. Все шесть transport event types не меняют TASK/microtask/operation/checkpoint/Workspace и не переписывают reconciliation decision. `REMOTE_RECOVERED` не разрешает unknown operation; message/result delivery failures не выполняют auto-adopt/rollback; process restart не завершает operation и не продвигает microtask; duplicate/out-of-order/unbound events остаются evidence-only.

**Verification:** transport A+B+C+D **29/29 PASS**; full Web Alarm **164/164 PASS**; pycompile + diff-check PASS.

**Recovery note:** при записи test-файла composite tool-call был заблокирован после частичного append. Disk reread подтвердил уже применённые чанки, после чего добавлены только отсутствующие части.

**Restore points:** `code_d_v1`, `activate_d_docs_v1`, `closeout_d_docs_v1` VERIFIED.

**Next:** финальный fresh-process reopen WA-3.5; затем WA-3.6.

---

### WA-3.5 — Final fresh-process reopen

**Статус:** PASS — 2026-10-02.

Новый process независимо перечитал persistent session/context/000/05/24 и восстановил одну authoritative точку: **WA-3.5 = DONE / VERIFIED**, **WA-3.6 = NOT ACTIVATED**. WA-3.6 можно только подготовить новой постановкой в обычном Chat и отдельным versioned TASK-session.

---

### WA-3.6 — TASK population / review gate

**Статус:** POPULATED / USER REVIEW REQUIRED — 2026-10-02. Implementation NOT STARTED.

Создан machine-local workspace `ws_ag_llm` для `M:\\GitHub\\ag_llm` и Web Alarm TASK `WA-3.6` из канонического RAW TASK. План: `WA36-M001`…`WA36-M004`, все `PLANNED`; current = `WA36-M001` только для review. Checkpoint: `PLANNED`, `snapshot_status=NOT_PREPARED`, `next_safe_action=USER_REVIEW_REQUIRED`, last operation отсутствует.

Во время первого create-task вызова консоль получила UnicodeEncodeError уже после записи TASK. Disk reconciliation подтвердил полное создание `task.json` / `task.md` / `plan.json`; create не повторялся. Это заполнение TASK, а не начало implementation.

---

### WA-3.6 — Short machine-usable Recovery Report

**Статус:** DONE / VERIFIED — 2026-10-02. Fresh reopen PASS.

**M001:** `recovery_report_store.py` + focused store contract; persistent/conflict-safe/restart-safe Report, side-effect enum `none / partial / full / ambiguous` — **9/9 PASS**.

**M002:** pure `RecoveryReportBuilder`; authoritative evidence/decision binding, deterministic side-effect classification, отдельные already-done / retried / rolled-back facts, no authority inference — **8/8 PASS**.

**M003:** `RecoveryReportService`, Server `recovery-reports` read/create path, capability + latest report в Context Pack, package export; fresh Python process/new API instance persistence — **6/6 PASS**.

**M004:** adversarial acceptance matrix — **10/10 PASS**. Combined Recovery Report suites **33/33 PASS**; full Web Alarm **197/197 PASS**; `py_compile` + task-scoped `git diff --check` PASS. Runtime repair не потребовался.

**Live recovery during closeout:** после `WA36-M004-DOCS-001` произошли `MESSAGE_DELIVERY_TIMEOUT → REMOTE_OFFLINE → REMOTE_RECOVERED`. Verified restore point показал partial docs side effect: только `000` уже содержал корректный closeout, остальные 8 документов оставались exact pre-state. `000` не replayed; продолжены только отсутствующие документы. Transport events записаны evidence-only с fixed event_id. Incident не засчитывается вместо требуемого intentionally controlled disconnect test.

**Acceptance:** WA-3.6 implementation может закрыться. WA-3 overall остаётся IN PROGRESS до отдельного controlled real Remote transport-disconnect gate и последующего final reopen/closeout.

---

### WA-3.7 — TASK population / controlled-disconnect review gate

**Статус:** PLANNED / POPULATED / USER REVIEW REQUIRED — 2026-10-02. Controlled test NOT STARTED.

После WA-3.6 DONE / VERIFIED / FRESH REOPEN PASS создана отдельная Web Alarm TASK `WA-3.7 — Controlled real Remote transport-disconnect acceptance gate`. Каноническая постановка сначала была зафиксирована в обычном Chat, затем перенесена в persistent TASK/session.

Plan: `WA37-M001` — safe fixture + pre/post contract + verified restore point + persistent operation identity; `WA37-M002` — intentional real Remote disconnect + reconnect без replay + reconciliation + transport evidence + Recovery Report + fresh-process proof; `WA37-M003` — regressions/docs + WA-3 final acceptance/reopen. Все microtask = `PLANNED`; current = M001; checkpoint = `PLANNED / NOT_PREPARED / USER_REVIEW_REQUIRED`; last_operation_id = null.

На population-этапе не создавался test target, не готовился snapshot, не переводился operation в STARTED, не запускался intentional disconnect и не менялся runtime. Следующий шаг — пользовательский review заполненной TASK. WA-4 автоматически не активируется.

---

### WA-3.7 — Controlled real Remote transport-disconnect acceptance

**Статус:** M001 VERIFIED; M002 VERIFIED / CONTROLLED PASS; M003 ACTIVE / CLOSEOUT — 2026-10-03.

**M001:** зафиксирован test contract: isolated target, absent pre-state, exact expected-post hash, safety/disconnect window. До controlled execution был найден и исправлен sequencing scope: M001 не владеет mutation lifecycle; фактический snapshot + OperationStore принадлежат M002.

**Attempt 1 — `WA37-CTRL-001`:** target достиг exact expected post-state, но real Remote disconnect не произошёл. Попытка сохранена как non-acceptance evidence; PASS не присваивался. Target восстановлен через VERIFIED M002 restore point в absent pre-state.

**Attempt 2 — `WA37-CTRL-002`:** persistent OperationStore status = STARTED до intentional остановки Desktop Commander Remote. После восстановления канала сначала выполнен persistent/disk reconciliation, без replay. Transport Store: `REMOTE_OFFLINE → REMOTE_RECOVERED`. Target = exact PRE_STATE; expected post not reached; deterministic decision = `RETRY_SAFE / PRE_STATE_AND_POST_NOT_REACHED`; Report `report_wa37_ctrl002` = `side_effect_scope=none`, `actually_retried=[]`. Fresh-process reconciliation + persisted Report reopen PASS.

После доказанного NONE side effect операция закрыта `FAILED` с явным result summary; retry сознательно не выполнялся. M002 = VERIFIED.

**M003 regression:** focused recovery/reconciliation/transport 95/95 PASS; full Web Alarm 197/197 PASS; compileall PASS. Финальный docs/diff-check/fresh reopen ещё выполняются.

**Final WA-3 acceptance reconciliation:** WA-3.7 fresh-process reopen PASS, но WA-3 overall остаётся IN PROGRESS. Причина — один недоказанный combined criterion: в одном controlled incident должно быть доказано `local mutation reached post-state -> Remote transport lost -> Chat result unavailable -> reconnect/reconciliation without replay`. Следующий follow-up этап не активируется через Remote до отдельной постановки в обычном Chat.

---

### CLAUDE-WA-001 — Independent preflight RT-001 / EP-RT001-001

**Статус:** DONE / VERIFIED — 2026-10-04. Independent preflight подтверждён ChatGPT; read-only, runtime не изменён.

**Сделано:** вердикт `32` и план `33` сверены с кодом `web_alarm/` (HEAD `dc246b9`), тестами (197/197 OK) и persistent storage (2 legacy-операции WA-3.7, обе терминальные и однофайловые). Отчёт: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-001/preflight_report.md`.

**Выводы для ветки:**
- **Совместимость при расширении контракта.** Глобальная `SCHEMA_VERSION = 1` строго проверяется в 8 хранилищах, поэтому RC-1 нужна отдельная версия контракта операции.
- **Каноническая идентичность target.** Target операции не канонизирован и расходится с манифестом.
- **Дрейф `24`.** После вердикта добавлен WA-4.6 Task Progress UI; WA-4.3 lease противоречит V17. Сопоставление нужно выполнить в P00.

**Verification 2026-10-04:** фактические замечания preflight подтверждены. D1–D3 приняты как planning corrections и отражены в `33`/`24`; PLAN APPROVAL отдельно ещё не объявлен.

**Next:** USER PLAN REVIEW / PLAN APPROVAL EP-RT001-001.

---

### P00 — Canonical Plan Handoff RT-001 / EP-RT001-001

**Статус:** DONE / VERIFIED — 2026-10-04. Documentation-only; runtime/code не изменялись.

**Result:** после USER PLAN APPROVAL и independent verification CLAUDE-WA-001 утверждённый RT-001 перенесён в канонические документы WEB-02. `23` содержит новые authority/recovery invariants; `24` содержит канонический маршрут `RC-0 → RC-1 → RC-2 → RC-3 → RC-4 → RC-5 → RC-6 → WA4-E → WA4-A → WA4-O → WA4-R` с exit proofs. Старый strict combined WA-3 criterion = `SUPERSEDED / DEFERRED`, не PASS; его смысл перенесён в WA4-A. Старые WA-4.1–WA-4.7 сопоставлены без потери retention/security; exact lease/heartbeat model остаётся deferred по V17.

**Next:** RC-0 — baseline и normalization policy. RC-1 не начинать до RC-0 PASS.

---

### CLAUDE-WA-002 — RC-0: Baseline и normalization policy

**Статус:** DONE / VERIFIED — 2026-10-04. Runtime, `.gitattributes` и переводы строк в рамках RC-0 не менялись.

**Baseline:** HEAD `dc246b9`; `python -B -m unittest test_web_alarm_*.py` — 197/197 OK (25 модулей, два прогона); storage WEB-02: 1,5 МБ, 136 файлов, 29 снимков, 2 терминальные операции.

**Выводы для ветки:**
- **Policy:** authority — SHA-256 по физическим байтам + размер; git и нормализация переводов строк — внешний писатель, не доказательство; `EOL_ONLY_DRIFT` — только диагностика.
- **Риск при `autocrlf=true` без `.gitattributes`:** из 121 хеша ручных manifest `Alarm/` после свежего checkout сойдётся 1. Предложен FOLLOW-UP `.gitattributes`.
- **Метрики:** Remote-вызовов на мутацию — 11,7 / 7,0; мутаций мимо OperationStore — 100% / 89%; ручная синхронизация — 9 документов; число действий до безопасного продолжения — NOT MEASURED.
- **Ограничения для снимков:** deny-list секретов, хранение только вне репозитория, лимит размера, retention без автоудаления.

Отчёт: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-002_RC0/rc0_report.md`.

**Independent verification:** на HEAD `8029a69` повторно 197/197 PASS; manifest-аудит подтверждён 121 total / 115 match / 6 missing / 1 simulated fresh-checkout match; Remote-call metrics подтверждены 375/32 = 11,7 и 126/18 = 7,0. Byte/hash policy принята и перенесена в `23/24`.

**Decision:** `.gitattributes` FOLLOW-UP отложен как отдельная maintenance-задача; он не блокирует RC-1.

**Next:** RC-1 — Durable Operation Contract + backward compatibility (`CLAUDE-WA-003`).

---

### CLAUDE-WA-003 — RC-1: Durable Operation Contract + backward compatibility

**Статус:** DONE / VERIFIED — 2026-10-04. `.gitattributes`, UI и переводы строк в рамках RC-1 не менялись; физических мутаций проекта нет.

**Результат:**
- Новые операции сохраняются как Operation Contract v2:
  - `workspace_id`, `target_key`, `mutation_kind`;
  - `pre_state`, который сервер читает при INTENT;
  - `expected_post_state` — из payload или объявленный (pre-commitment);
  - `payload_ref` — content-addressed blob в каталоге TASK machine-local storage;
  - claimed `provenance`, `policy`, fingerprint v2;
  - `revision`;
  - `receipt` при DONE, который сервер читает сам; при противоречии DONE отклоняется, признак `EOL_ONLY_DRIFT` — диагностика.
- Legacy v1 (`WA37-CTRL-001/002`) читаются без перезаписи, `rearm_contract_sufficient=false`.
- Запросы в старом стиле создают v2 с `complete=false`.

**Verification (исполнитель):**
- полный WA regression 241/241 OK (197 прежних + 44 новых, 1 skip — привилегия symlink);
- multiprocess-тесты целостности: 8 процессов, 10/10 стабильно; без блокировки падают 5/5;
- fresh-process reopen и reconcile без входных данных от вызывающего: `RETRY_SAFE` → `ADOPT_CURRENT_STATE`;
- compileall и `git diff --check` OK;
- живое storage WEB-02 до и после чтения совпадает: 136 файлов.

**Границы:** Resolver и re-arm — RC-2; conflict gate и CAS по target — RC-3; executor — WA4-E. Нефайловые и многофайловые операции контрактом v2 не представляются.

**Independent verification:** ChatGPT повторно подтвердил full regression 241/241, focused 44/44, 5 последовательных multiprocess concurrency PASS и read-only fresh-process legacy reopen с неизменным storage tree. Blocker не найден; RC-1 принят.

**Next:** RC-2 — Tracked Resolver / evidence revision (`CLAUDE-WA-004`). При запуске WEB-02 использовать новый процесс с принятым RC-1 кодом.

---

### CLAUDE-WA-004 — RC-2: Persistent Resolver + evidence revision binding

**Статус:** DONE / VERIFIED — 2026-10-04. Финальная независимая проверка выполнена по последнему commit 148 `0b7cb7deae8220d1f2e0f432293b0edc784b7b6d`.

**Результат:**
- введён отдельный persistent Resolver layer без новой public Operation/Microtask state machine;
- ADOPT / RETRY / ROLLBACK / ABORT имеют persistent identity и binding к evidence fingerprint + operation revision;
- stale basis и stale revision fail-closed; STALE / REJECTED сохраняются как tracked outcomes;
- RETRY только re-arm того же `operation_id`; physical mutation не выполняется;
- ROLLBACK только tracked recovery request; physical restore остаётся RC-4;
- ADOPT фиксирует уже достигнутый post-state без project mutation; ABORT persistent/replay-safe;
- duplicate/replay одного logical resolution идемпотентен; конфликт identity/action/basis отклоняется;
- Recovery Report выводит resolver outcomes, authority и NEXT SAFE ACTION из persisted Resolver state; caller claims не имеют самостоятельной authority;
- legacy v1/incomplete/corrupt contracts не получают unsafe RETRY re-arm.

**Independent review + repair:** первая проверка commit 147 `fe55c99` нашла два blocker-а: accepted ABORT не подавлял advisory RETRY в Recovery Report, а persistent STALE/REJECTED records не попадали в `resolver_actions`. Repair в commit 148 исправил оба дефекта и добавил regression tests.

**Independent verification:** focused Resolver + concurrency 25/25 PASS; full Web Alarm 266/266 PASS; multiprocess race дополнительно 5/5 PASS; compileall и `git diff --check` PASS. Независимые ручные сценарии подтвердили:
- accepted ABORT → report NEXT = recovery closed, source = Resolver;
- STALE / `EVIDENCE_FINGERPRINT_CHANGED` остаётся persistent и видимым без authority, NEXT требует fresh reconciliation;
- REJECTED / `CONTRACT_INSUFFICIENT` не рекомендует RETRY и переводит в manual review.

**Deferred projection follow-up:** `context_pack.py` всё ещё может перезаписать верхний `NEXT_SAFE_ACTION` advisory reconciliation, хотя `LATEST_RECOVERY_REPORT` уже содержит Resolver-authoritative NEXT. Это не blocker RC-2: интеграция закреплена как обязательный exit item RC-5/RC-6 (projection correctness / minimal resume).

**Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/rc2_report.md`.

**Next:** RC-3 — Canonical-target conflict gate + mutation-boundary CAS. Не запускать автоматически; сначала сформировать и утвердить персональную task-card исполнителя.
