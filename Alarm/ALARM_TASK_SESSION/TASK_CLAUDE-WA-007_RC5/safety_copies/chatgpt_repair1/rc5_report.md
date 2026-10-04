# CLAUDE-WA-007 — RC-5: Projection correctness + pure inspection + safe TASK closeout

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локальный доступ.
**Дата:** 2026-10-04.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. DONE не объявлен; commit / push не выполнялись. **RC-6 NOT STARTED.**
**ARCH CLASS:** Web Alarm Workspace runtime (WEB-02). **PRIMARY PROFILE:** `23` (инвариант 27, а также 10, 15, 19, 20); план и acceptance — `24`; исполнительный план — `33`.
**База:** HEAD `c46bee7` (commit 154 = принятый RC-4 baseline). Код `web_alarm/` и тесты перед стартом побайтно совпадали с HEAD. Полный Web Alarm на базе — 329/329 OK (skip 1). Dirty tree до старта — только чужие правки документов и `.obsidian/workspace.json` (список — в `baseline.md`).

---

## 1. RESULT

Checkpoint перестал быть самостоятельной истиной:

```text
AUTHORITATIVE PERSISTENT STATE → ProjectionService.build (pure) → Context Pack / Server / CLI / RemoteEntry
                                                          ↘ explicit rebuild → checkpoint.json + checkpoint.md (только projection)
```

Доказано тестами:

- **A.** Checkpoint — rebuildable, validated projection. У него есть механический source basis и fingerprints. Валидация различает `VALID / STALE / INCONSISTENT / LEGACY_UNVALIDATED / MISSING / CORRUPT`.
- **B.** Пути inspect / verify действительно только читают. Digest всего machine-local storage и Workspace до и после каждого пути совпадает, включая `locks/`.
- **C.** Stale, подделанный и legacy checkpoint никогда не становится текущей истиной. CURRENT и NEXT всегда берутся из projection.
- **D.** TASK нельзя завершить при незакрытом authoritative-состоянии: публичное завершение проходит closeout gate под TASK-блокировками. Многопроцессный TOCTOU-тест проходит; без блокировок он ломается, что доказано отдельным probe.

---

## 2. Проблемы baseline (подтверждены кодом)

| № | Наблюдение постановки | Факт на commit 154 |
| --- | --- | --- |
| 4.1 | Checkpoint считается истиной | `EntryContextPackBuilder.build` брал из checkpoint `current_microtask_id`, `last_verified`, `current_status`, `snapshot_status`, `last_operation_id`, `next_safe_action`. `_task_bundle` / `_ui_task_view` / `/recover` — тоже. **Подтверждено.** |
| 4.2 | Нет source basis | `CheckpointRecord` не хранил ни ревизий, ни fingerprint. **Подтверждено.** |
| 4.3 | Ручная запись checkpoint | `cli checkpoint write --next-safe-action ...` писал «истину», `report` её печатал. Тест CLI это закреплял. **Подтверждено.** |
| 4.4 | Snapshot verify не pure | `verify_snapshot` → `_require_verified_snapshot` → `verify_restore_point(active_only=True)`: при ошибке manifest/microtask переходят в `BLOCKED_PREPARE`, затем `_reject` пишет событие и checkpoint. При успехе тоже пишется checkpoint. **Подтверждено.** |
| 4.5 | Advisory reconciliation перезаписывает NEXT | `pack["NEXT_SAFE_ACTION"] = reconciliation[...]` при любой reconciliation, без учёта persistent Resolver. **Подтверждено.** |
| 4.6 | `complete_task` без gate | CLI `task complete` → `TaskStore.complete_task` без проверок. **Подтверждено.** |

Дополнительно найдено:
- `OperationStore._touch_checkpoint` частично переписывал checkpoint (`last_operation_id`). Ошибка этой записи возвращалась вызывающему уже **после** persist операции.
- `TaskStore` не сериализовал записи plan / microtask: на этом был возможен TOCTOU при закрытии задачи.

---

## 3. Source-of-truth matrix

| Источник | Роль | Что из него берёт projection |
| --- | --- | --- |
| TaskStore: `TaskRecord` | **authority** | status, plan_revision, `updated_at`, расположение (active / completed) |
| TaskStore: `TaskPlanRecord` | **authority** (порядок); `current_microtask_id` — только подтверждение | revision, порядок, указатель (диагностика) |
| TaskStore: `MicrotaskRecord` | **authority** | status, sequence, `updated_at`; orphan-записи вне plan |
| Manifest / restore point | **authority** (целостность проверяется чисто) | VERIFIED / NOT_VERIFIED / NOT_PREPARED / NOT_APPLICABLE текущей microtask |
| OperationStore | **authority** | identity, status, revision, contract version, request fingerprint, `updated_at` |
| ResolutionStore + `ResolverService.report_facts` | **authority** (accepted + fresh) | action / result / basis, свежесть на сейчас, авторитетный NEXT |
| RC-3 TargetClaimStore | **authority** | активные claims этой TASK (owner — операция или rollback) |
| RC-4 RollbackStore | **authority** | status, revision, `claims_released`, NEXT, receipts как **исторические** факты |
| `checkpoint.json` / `checkpoint.md` | **derived** | только сравнивается с projection и никогда не читается для её построения |
| Recovery Report | evidence / history | в Context Pack как `LATEST_RECOVERY_REPORT`; NEXT не задаёт |
| Reconciliation calculation | advisory | NEXT только при отсутствии применимой резолюции (правило 4) |
| Event log | history | не читается projection; Context Pack не читает историю |
| UI view / Entry Context Pack | derived | строятся из projection |

---

## 4. Архитектура projection

Новый модуль `web_alarm/projection.py`, класс `ProjectionService`:

- **`build(task_id)` — pure.** Без блокировок и записи; checkpoint и события не читаются. Результат: `task`, `position`, `restore_point`, `operations` (с `resolutions` и `recovery` по каждой), `last_operation_id`, `rollbacks` (факты сессий), `ownership.active_claims`, `blockers`, `diagnostics`, `recovery`, `next_safe_action`, `authority_source`, `closeout`. Метаданные: `source_basis`, `source_fingerprint`, `projection_fingerprint`, `generated_at`, `advisory_reconciliation`.
- **Позиция выводится из жизненного цикла** (§7):
  - порядок задаёт plan;
  - непрерывный префикс VERIFIED даёт `last_verified`;
  - первая не-VERIFIED microtask становится current; если все VERIFIED — последняя.
  - `plan.current_microtask_id` — только подтверждение: `CORROBORATED`, `STALE_BEHIND_LIFECYCLE` или `CONTRADICTS_LIFECYCLE` (диагностика).
  - Невозможные состояния `MULTIPLE_ACTIVE`, `VERIFIED_OUT_OF_ORDER`, `LATER_STAGE_STARTED`, нечитаемые хранилища → projection blocker, NEXT закрыт до ручного разбора.
- **`validate_checkpoint(task_id)` — pure** (§8, §11).
- **`rebuild_checkpoint(task_id)`** — явная запись только `checkpoint.json` и `checkpoint.md` под TASK-блокировкой операций (§9, §22). Есть вариант `rebuild_checkpoint_locked` для вызывающего, который уже держит блокировку. Rebuild разрешён только для active TASK: completed-история не переписывается.
- **`closeout_blockers(projection)`** — чистая консервативная классификация (§19).

`web_alarm/closeout.py`, класс `CloseoutService`:
- `inspect` — pure;
- `complete` — gated (§20, §21).

---

## 5. Fingerprints

- **`source_basis`** — детерминированная выписка authoritative-фактов:
  - task (status, plan_revision, `updated_at`, location);
  - plan (revision, порядок, указатель, `updated_at`);
  - microtasks (id, sequence, status, `updated_at`) и orphans;
  - restore point текущей microtask (статус, `manifest_id`, `updated_at` или причина);
  - operations (id, microtask, status, revision, contract version, request fingerprint, `updated_at`);
  - resolutions (id, action, result, evidence fingerprint, revision, fresh, freshness code — свежесть пересчитывается сейчас и зависит от байтов Workspace);
  - rollbacks (id, операция, резолюция, status, revision, `claims_released`);
  - claims (hash, claim_id, generation, операция, owner);
  - advisory reconciliation (evidence fingerprint, решение, reason code).

  `source_fingerprint` = SHA-256 канонического JSON.
- **`projection_fingerprint`** = SHA-256 семантической части projection (без метаданных и без времени).
- **Одинаковое состояние → одинаковые fingerprints и в свежем процессе.** Проверено тестом B/Z через subprocess и на живом storage (сборка дважды).
- **Изменение authority при неизменном виде** (новая ревизия плана, `updated_at` microtask или операции, свежесть резолюции, ревизия rollback, release claims) всё равно меняет source basis.

---

## 6. Состояния валидации checkpoint

| Статус | Когда |
| --- | --- |
| `VALID` | source fingerprint равен свежему, поля checkpoint равны полям свежей projection, metadata и `projection_fingerprint` совпадают, `checkpoint.md` побайтно равен рендеру JSON |
| `STALE` | source basis изменился после rebuild |
| `INCONSISTENT` | basis тот же, но содержимое не сходится (подмена NEXT / status / current id / fingerprint) или md не соответствует JSON |
| `LEGACY_UNVALIDATED` | нет RC-5 metadata (RC-0…RC-4 файл или ручная запись без basis) |
| `MISSING` / `CORRUPT` | файла нет / не читается |

Ни один статус не делает checkpoint authority (`authoritative: false` всегда). Validation никогда не пишет. Даже скопированная настоящая metadata не спасает подделку — тест H даёт `INCONSISTENT`.

---

## 7. Legacy compatibility

- `CheckpointRecord.projection` — новое необязательное поле. Старые файлы без него читаются и получают `LEGACY_UNVALIDATED`. Чтение их не переписывает: digest до и после равен (тест E). Явный rebuild создаёт современный checkpoint с тем же `checkpoint_id`.
- Рендер `checkpoint.md` без projection побайтно прежний.
- Operation Contract, Resolver, rollback-записи и Recovery Reports не мигрировались. В `rollback_receipts` новых отчётов добавлены поля, старые отчёты валидны.
- Живое storage: обе завершённые задачи (WA-3.6, WA-3.7) → `LEGACY_UNVALIDATED`, NEXT «TASK is COMPLETED; read-only history» (§17).
- **Старый код новый checkpoint не прочтёт** (лишнее поле → fail-closed). **Процессы WEB-02 после принятия нужно перезапустить** (это уже был открытый хвост).

---

## 8. Pure inspection (§24)

Тест Y (`test_every_inspection_path_is_read_only`) трижды прогоняет набор путей чтения. Digest всего storage (включая `locks/`, events, checkpoint, manifest, microtasks, operations, resolutions, claims) и Workspace каждый раз неизменен. Набор путей:
- server: `GET` task, ui, context, projection, checkpoint, closeout, operations (список и запись), resolutions, rollbacks, recovery-reports, claim inspect;
- `POST /reconcile` и `POST snapshot verify`;
- library: build / validate / closeout inspect / RemoteEntry;
- CLI: `status`, `report`, `checkpoint show`, `checkpoint validate`, `task closeout`.

Отдельные тесты A, E, O: чтения не создают checkpoint и не переписывают legacy-файл.

---

## 9. Чистота snapshot verify (§12–13)

- `ServerStateMachine.verify_snapshot` теперь вызывает `verify_restore_point(active_only=False)`, который при ошибке только поднимает исключение. Не пишутся событие, checkpoint и статус manifest / microtask.
- Ответ содержит `workflow_mutation_performed: false`. Ошибка → `409 snapshot_not_verified` с `details.workflow_mutation_performed = false`. Endpoint оставлен POST ради совместимости.
- Тесты F/G покрывают успех, испорченный snapshot, отсутствующий snapshot и сломанный manifest. Digest до и после равен, microtask остаётся `BACKUP_VERIFIED`, manifest — `VERIFIED`.
- Путь **перехода** (`READY`/`ACTIVE` на сломанном restore point) по-прежнему блокирует состояние: это реальный workflow failure, тест state machine не менялся.

---

## 10. Приоритет Resolver / Reconciliation / Rollback (§16)

Одно правило (docstring `projection.py`):

0. Структурный projection blocker → закрытый NEXT, ручной ремонт.
1. Rollback-сессия той резолюции, которую Resolver считает авторитетной для операции → NEXT сессии.
2. Авторитетная резолюция (accepted ABORT; иначе последняя свежая accepted; иначе совет свежего REJECTED) → её persistent NEXT.
3. Accepted, но уже не свежая → не authority: «stale basis, нужна новая reconciliation» (`resolver_stale`).
4. Нет применимой резолюции, а операция в STARTED / UNKNOWN (или microtask в recovery-статусе) → advisory reconciliation.
5. Норма → lifecycle state machine. Когда все microtasks VERIFIED — NEXT от closeout gate: либо «gate чист — gated complete», либо первый блокер.

Recovery Report — только evidence, никогда не перекрывает этот порядок (тест: отчёт старше ADOPT → NEXT от ADOPT). Правила 1–3 повторяют уже принятую логику `ResolverService._authoritative_next_action` и сопоставление rollback-сессий из `RecoveryReportService`; новой семантики нет.

**Решение внутри scope** — порядок между операциями: при нескольких операциях, требующих внимания, первой идёт незавершённая rollback-сессия (ownership удерживается, последовательность не закрыта), затем самая свежая активность, затем `operation_id`. Все операции, требующие внимания, перечислены в `recovery.attention`.

Тесты матрицы §17:
- без резолюции → reconciliation;
- RETRY / ADOPT / ABORT accepted → resolver, raw reconciliation не перезаписывает;
- ROLLBACK: accepted → resolver; PRESERVED → rollback; VERIFIED → rollback (исторические факты);
- stale ADOPT → `resolver_stale`;
- RemoteEntry → `RECOVERY_AUTHORITY_READY` / `PROJECTION_BLOCKED`.

---

## 11. RC-4 P1 — historical / as_of (§18)

Функция `rollback_session_facts` (`rollback_service.py`) — общая для Recovery Report и projection. Списки `restored`, `noop`, `historically_restored` помечены:
- `facts_source: "rollback_receipt"`;
- `facts_as_of` — момент финализации;
- `verified_at` — момент итоговой проверки, если VERIFIED;
- `current_physical_state_asserted: false`.

Схема receipts RC-4 не менялась. Тест N: после VERIFIED rollback легальная RC-3 операция переписывает цель. Projection и новый Recovery Report по-прежнему показывают `restored=[target.txt]` как исторический факт с `as_of` и **не** утверждают текущее состояние; на диске другие байты.

---

## 12. TASK closeout gate (§19–21)

`CloseoutService.inspect` (pure) возвращает:
- `eligible`;
- `blockers` (code, reason, `next`);
- facts;
- NEXT;
- fingerprints;
- `workflow_mutation_performed: false`.

`CloseoutService.complete`:
1. операционный TASK-lock (сериализация с `begin` / `transition`, Resolver, RC-3, RC-4);
2. `TaskStore.mutation_lock` (сериализация с записью microtask / plan);
3. свежая projection и проверка eligibility **под обеими блокировками**;
4. `complete_task_locked`;
5. событие `TASK_COMPLETED` (история; при ошибке записи completion не откатывается, флаг `event_recorded`).

Отказ ничего не пишет (кроме lock-файлов); TASK остаётся active. При ошибке переноса каталога статус восстанавливается: половинчатого завершения нет.

Публичные пути:
- CLI `task complete` → gate: 0 — COMPLETED, 3 — REJECTED с blockers;
- CLI `task closeout` — inspect;
- server `GET /tasks/{id}/closeout`, `POST /tasks/{id}/complete` (409 `closeout_rejected`).

`TaskStore.complete_task` остался низкоуровневым примитивом хранилища (используется тестами) и теперь тоже берёт mutation lock.

---

## 13. Точная классификация open / unresolved

Используются только существующие контракты RC-2 / RC-3 / RC-4, новая семантика не вводится:

| Состояние | Блокер | Как снять |
| --- | --- | --- |
| TASK не active (completed / archived) | `TASK_NOT_ACTIVE` | — |
| Projection blocker (невозможный план, нечитаемое хранилище) | `PROJECTION_*` | ручной разбор |
| Orphan-microtask вне plan, нечитаемые claims | `ORPHAN_MICROTASKS`, `CLAIMS_UNREADABLE` | ручной разбор |
| Пустой plan | `NO_MICROTASKS` | — (консервативно: ничего не проверено) |
| Microtask не VERIFIED | `MICROTASK_NOT_VERIFIED` | lifecycle |
| Операция INTENT | `OPERATION_OPEN` | перевести в FAILED или accepted ABORT |
| Операция STARTED / UNKNOWN без accepted ABORT и без свежего accepted ADOPT | `OPERATION_UNRESOLVED` | правило release RC-3: свежий ADOPT или ABORT |
| Операция DONE | `OPERATION_NOT_VERIFIED` | DONE → VERIFIED («DONE is not VERIFIED») |
| Операция VERIFIED / FAILED | — (terminal; старая stale-резолюция их не открывает) | — |
| Свежий accepted RETRY | `RETRY_PENDING` | — |
| Accepted ROLLBACK без rollback-сессии | `ROLLBACK_PENDING` | RC-4 |
| Rollback-сессия PREPARED / PRESERVED / AUTHORIZED / APPLYING / PARTIAL / FAILED | `ROLLBACK_OPEN` | apply / close |
| Rollback VERIFIED с `claims_released=false` | `ROLLBACK_RELEASE_PENDING` | apply или close доснимают claims |
| Rollback VERIFIED (released), CLOSED, PRESERVATION_FAILED | — (сессия закрыта; операция классифицируется отдельно) | — |
| Активный claim этой TASK | `ACTIVE_CLAIM` | завершить или освободить владельца |

Особый случай: STARTED-операция, чья microtask откатана и проверена (rollback VERIFIED), остаётся `OPERATION_UNRESOLVED`. Совет — закрыть её recovery через accepted ABORT, потому что жизненный цикл операции после отката не определён (FINDING F1).

---

## 14. Сериализация и конкурентность

- **Порядок блокировок** везде один: операционный TASK-lock → `TaskStore.mutation_lock`. Обратного порядка нет: TaskStore не вызывает OperationStore. Глобальной блокировки нет: блокировки на уровне TASK.
- `TaskStore`: записи `create_microtask`, `set_plan`, `set_current_microtask`, `set_microtask_status` и `complete_task` идут под `locks/tasks/<task>.lock`. Блокировка не re-entrant; для держателя есть `*_locked`.
- **Rebuild** идёт под операционным TASK-lock. Поэтому два rebuilder'а не перемешивают JSON и md. Записи TaskStore с rebuild не сериализованы, но любая гонка обнаруживается: валидация всегда пересчитывает свежую projection (тест X).
- **«Сначала состояние, потом projection»** (§25): state machine и `OperationStore` после своей authoritative-записи пересобирают checkpoint. Ошибка projection не отменяет и не роняет мутацию: возвращается `checkpoint_error`, старый checkpoint честно становится STALE (тест adversarial).

---

## 15. Изменённые файлы

Новые:
- `web_alarm/projection.py` (736 строк);
- `web_alarm/closeout.py` (100);
- `test_web_alarm_projection.py` (32 теста);
- `test_web_alarm_projection_concurrency.py` (3 многопроцессных теста).

Изменённые (`git diff --numstat`):

| Файл | + / − | Суть |
| --- | --- | --- |
| `web_alarm/context_pack.py` | +63 / −108 | всё из projection; блок `CHECKPOINT` (статус валидации), `AUTHORITY_SOURCE`, `RECOVERY`, `BLOCKERS`, `PROJECTION`; `RECONCILIATION` — тот же расчёт, что стоит за NEXT |
| `web_alarm/task_store.py` | +127 / −79 | `mutation_lock`, блокировка записей, `complete_task_locked` с восстановлением статуса |
| `web_alarm/server.py` | +89 / −54 | bundle / ui / recover из projection; новые endpoints; `snapshot_not_verified`; capabilities |
| `web_alarm/state_machine.py` | +67 / −76 | checkpoint = rebuild projection; чистый `verify_snapshot` (`SnapshotNotVerified`) |
| `web_alarm/cli.py` | +54 / −28 | gated `task complete`, `task closeout`, `checkpoint rebuild / validate`, `checkpoint write` выведен, `status` / `report` из projection |
| `web_alarm/rollback_service.py` | +48 / −23 | `rollback_session_facts` (as_of) |
| `web_alarm/event_checkpoint_store.py` | +20 / −1 | `checkpoint_markdown`, строки projection в md |
| `web_alarm/remote_entry.py` | +14 / −1 | `RECOVERY_AUTHORITY_READY`, `PROJECTION_BLOCKED` |
| `web_alarm/operation_store.py` | +13 / −11 | `_touch_checkpoint` = rebuild projection, ошибки не роняют операцию |
| `web_alarm/__init__.py` | +7 | экспорт |
| `web_alarm/models.py` | +4 | `CheckpointRecord.projection` |

Не менялись: `manifest_store.py`, RC-2 / RC-3 модули, reconciliation, UI HTML / JS, `.gitattributes`.

**Намеренно изменённые ожидания 5 прежних тестов** (они закрепляли «checkpoint = истина»):
- `test_web_alarm_cli`: `checkpoint write` → exit 2, далее `checkpoint rebuild` → VALID, `report` печатает NEXT из projection; `task complete` пустой задачи → REJECTED (`NO_MICROTASKS`), задача остаётся active;
- `test_web_alarm_context_pack`: `LAST_OPERATION` больше не метка вызова state machine (её нет в OperationStore) → `None`, плюс `AUTHORITY_SOURCE` / `CHECKPOINT`;
- `test_web_alarm_state_machine` (2 места): `checkpoint.last_operation_id` → `None`; метка проверяется в событии.

Прочие поведенческие изменения API:
- `GET /tasks/{id}` при испорченном checkpoint теперь 200 с `checkpoint_validation=CORRUPT`, раньше было 409;
- ошибка snapshot verify — 409 `snapshot_not_verified` без перевода состояния (раньше 409 `transition_rejected` + `BLOCKED_PREPARE`).

LF во всех файлах сохранены (CRLF: 0).

---

## 16. Тесты

| Набор | Результат |
| --- | --- |
| RC-5 focused (`test_web_alarm_projection`) | **32/32 OK** |
| RC-5 multiprocess races | **3/3 OK** |
| event / checkpoint + models | 13/13 |
| Context Pack + Remote entry + restart recovery | 14/14 |
| Server + UI | 16/16 |
| state machine | 6/6 |
| CLI | 6/6 |
| task store | 11/11 |
| Resolver / RC-2 focused (resolver, concurrency, Recovery Report integration / acceptance) | 41/41 |
| RC-4 focused + concurrency | 43/43 |
| RC-3 focused + concurrency | 20/20 |
| **Полный** `python -B -m unittest test_web_alarm_*.py` | **364/364 OK** (skip 1), ≈85 с |
| `python -B -m compileall -q web_alarm` | OK |
| `git diff --check` | OK |

Соответствие минимуму §28:

| Пункт | Тест |
| --- | --- |
| A | `test_missing_checkpoint_projection_is_built_and_reading_creates_nothing` |
| B, Z | `test_valid_modern_checkpoint_is_reproduced_by_a_fresh_process` |
| C | `test_source_change_makes_an_old_checkpoint_stale_and_never_used` (plan, microtask, операция, ревизия операции) |
| D | `test_tampered_checkpoint_is_never_valid` |
| E | `test_legacy_checkpoint_is_read_unvalidated_never_rewritten_then_rebuilt` |
| F, G | `test_snapshot_verify_success_and_failures_write_nothing` |
| H | `test_fabricated_checkpoint_cannot_steer_context` |
| I–K | `test_fresh_accepted_retry_adopt_abort_outrank_reconciliation` |
| L | `test_tracked_rollback_session_outranks_its_request` |
| M | `test_stale_accepted_resolution_is_never_authority` |
| N | `test_rollback_facts_are_historical_after_a_later_legitimate_writer` |
| O | `test_closeout_inspection_is_pure` |
| P, Q | `test_closeout_blocks_unverified_microtask_and_open_operations` |
| R | `test_closeout_blocks_an_active_target_claim` |
| S, T | `test_closeout_blocks_open_rollback_and_pending_release` |
| U | `test_public_completion_cannot_bypass_the_gate` |
| V | `test_clean_task_completes_through_the_gate` |
| W | `test_completion_never_admits_new_open_state` (concurrency) |
| X | `test_rebuild_racing_an_authoritative_change_is_never_falsely_valid` (concurrency) |
| Y | `test_every_inspection_path_is_read_only` |

**Чувствительность.** Мутации в памяти по одной ломают ключевые свойства; каждую ловят свои тесты:
- «checkpoint диктует Context Pack»;
- «валидация игнорирует source basis»;
- «verify_snapshot как до RC-5»;
- «резолюции игнорируются»;
- «gate выключен»;
- «rollback-факты утверждают настоящее».

Многопроцессные тесты проверены отдельным probe (§17).

---

## 17. Многопроцессные результаты

Реальные процессы, барьер старта; окна расширены только в дочерних процессах теста.

- **W** (closeout против `begin` × 2 и `create_microtask`). Probe на 6 раундов: с gate `COMPLETED` 3 / `REJECTED` 3, **нарушений 0**. Тот же сценарий с closeout **без** TASK-блокировок: 2 нарушения из 6 («completed + новое открытое состояние внутри») и одно половинчатое состояние (`FAILED: TaskStoreError`). Блокировки — не формальность.
- **X** (rebuild против `create_microtask` и перехода операции). В probe встречаются оба исхода: `VALID` 4 / `STALE` 2. Тест требует `VALID ⇔ checkpoint == свежая projection` (и source, и поля). Ложного VALID нет.
- **Два и более rebuilder'а:** итог `VALID`, JSON и md всегда от одного rebuild.

---

## 18. Живое storage — только чтение

`%LOCALAPPDATA%\WebAlarmWorkspace`: до и после всех RC-5 прогонов 136 файлов и 41 каталог. Хеш дерева файлов `07298919…5920` совпадает с baseline; полный хеш, включая каталоги, тоже совпал. Rollback-записей и claim-файлов нет.

Projection, validate, closeout inspect и Context Pack на WA-3.6 и WA-3.7:
- location completed, NEXT «TASK is COMPLETED; read-only history» (`task_status`);
- checkpoint `LEGACY_UNVALIDATED`;
- closeout `TASK_NOT_ACTIVE`;
- projection детерминирована, NEXT в pack равен NEXT projection.

Live-тестов с записью не было.

---

## 19. ADVERSARIAL REVIEW / FINDINGS / PROPOSALS

**Проверено сверх минимума (тесты есть):**
- checkpoint показывает m1 current при m1 VERIFIED и m2 не VERIFIED → current m2;
- указатель плана отстаёт → диагностика, не authority;
- несколько ACTIVE / VERIFIED не по порядку / поздняя стадия начата → блокер, закрытый NEXT, `PROJECTION_BLOCKED`, закрытие запрещено;
- ревизия операции меняется без видимой смены статуса → STALE;
- accepted резолюция протухает → `resolver_stale`;
- rollback VERIFIED с незавершённым release → `ROLLBACK_RELEASE_PENDING` + `ACTIVE_CLAIM`;
- rollback CLOSED с частичными receipts: сессия закрыта, операция классифицируется отдельно;
- испорченный md при целом JSON → INCONSISTENT; испорченный JSON → CORRUPT, а Context Pack работает;
- rebuild прерван между JSON и md (`os._exit`) → не VALID, повторный rebuild → VALID;
- конкурентные rebuilder'ы;
- завершение во время rebuild (одна блокировка);
- завершение при незавершённом release;
- задача без операций;
- completed-задача: projection pure, rebuild отказан, NEXT read-only;
- Recovery Report старше / новее Resolver;
- события противоречат записям → projection не меняется;
- receipt RC-4 + последующий легальный writer.

**Найдено и исправлено внутри scope (с регрессией):**
1. Context Pack второй раз вызывал reconciliation, и блок `RECONCILIATION` мог разойтись с NEXT. Теперь используется тот же расчёт (метаданные projection).
2. Порядок фокуса между операциями: незавершённая rollback-сессия могла уступить NEXT более свежей reconciliation другой операции. Теперь она идёт первой (тест).
3. Ошибка построения projection внутри rebuild могла выйти из перехода state machine или из `begin` как произвольное исключение уже **после** записанной мутации. Теперь это всегда `ProjectionError`: мутация остаётся, checkpoint STALE, вызывающий получает `checkpoint_error` (тест).
4. Прежние проблемы baseline: `_touch_checkpoint` и гонка `TaskStore` (см. §2, §14).

**FINDING / PROPOSAL (вне scope, код не менял):**
- **F1 — жизненный цикл после ADOPT / ABORT / отката (V15).** Операция остаётся STARTED / UNKNOWN после VERIFIED rollback или ADOPT; microtask после отката тоже не определена. Closeout сейчас fail-closed и даёт конкретный выход (accepted ABORT). **Proposal:** определить переходы отдельным решением (RC-6 / WA4) — это новая семантика lifecycle, **DECISION REQUIRED**.
- **F2 — `ServerStateMachine.transition` не атомарен** (WA-2.2): проверка, затем несколько отдельных записей TaskStore. Два параллельных перехода одной microtask → «последний пишущий выигрывает», события пишутся оба. Projection ловит невозможные комбинации, но не все гонки. **Proposal:** выполнять переходы под `TaskStore.mutation_lock` (lock-held варианты уже есть для complete).
- **F3 — смешанные версии процессов.** Старый код не читает новый checkpoint (fail-closed). Старые писатели TaskStore не берут новую блокировку, поэтому гарантия TOCTOU закрытия действует, только когда все писатели — код RC-5. **Обязательно перезапустить процессы WEB-02 после принятия.**
- **F4 — консервативные места, требующие подтверждения verifier:**
  - DONE-операция блокирует закрытие (`OPERATION_NOT_VERIFIED`);
  - пустой plan блокирует (`NO_MICROTASKS`);
  - INTENT снимается только переводом в FAILED или ABORT;
  - checkpoint завершённой задачи после gated completion валидируется как STALE: basis сменился (status / location), это история.
- **F5 — размер.** `GET /tasks/{id}` и `/projection` теперь несут projection с advisory evidence. Для RC-6 (одна read-only команда) может понадобиться компактный вид.
- **F6 — документация (для verifier).**
  - `22`: CLI — `checkpoint write` выведен; новые `checkpoint rebuild / validate`, `task closeout`, gated `task complete` с кодом 3;
  - `23`: инвариант 27 реализован; правило приоритета (§10) и классификацию закрытия (§13) стоит закрепить;
  - `24`: статус RC-5.

  Я эти документы не менял.
- Открытые хвосты без изменений: лимит preserved-state 1 МиБ; старый CLI `snapshot restore` → WA4-R.

---

## 20. Closeout

- `rc5_report.md` — этот файл.
- `baseline.md` — HEAD, dirty tree, SHA-256 safety copies.
- `safety_copies/` — копии 22 файлов до правки.

**RC-6 NOT STARTED.**

**NEXT SAFE ACTION:** независимая проверка RC-5 (commit пользователя → ChatGPT). До PASS RC-6 не начинать; после PASS — перезапуск процессов WEB-02 (F3).
