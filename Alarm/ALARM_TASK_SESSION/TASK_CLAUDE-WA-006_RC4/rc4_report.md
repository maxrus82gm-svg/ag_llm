# CLAUDE-WA-006 — RC-4: Tracked safe rollback + preserved current state + persistent receipts

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локальный доступ.
**Дата:** 2026-10-04.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**ARCH CLASS:** Web Alarm Workspace runtime (WEB-02). **PRIMARY PROFILE:** `23` (инвариант 26, а также 25, 29, 31–33); acceptance — `24`.
**База:** HEAD `072fcdc` (commit 151; RC-3 DONE / VERIFIED). Код `web_alarm/` и тесты перед стартом совпадали с HEAD; dirty tree — только `.obsidian/workspace.json` (Obsidian) и БЛОК 1 карточки.

**Не менялись:**
- `models.py` и публичный `OperationStatus`;
- lifecycle операций и microtask;
- `operation_store.py`, `operation_contract.py`, `target_identity.py`;
- Resolver: `resolver_service.py`, `resolution_store.py`;
- `reconciliation*.py`, UI, `.gitattributes`, переводы строк.

Commit / push не выполнялись. **RC-5 NOT STARTED.**

---

## 1. RESULT

ROLLBACK из запроса RC-2 стал отдельной tracked recovery operation. Путь: принятая fresh резолюция ROLLBACK →
1. persistent-сессия rollback;
2. сохранение текущего состояния **всех** целей (байты content-addressed вне репозитория, проверка hash+size);
3. повторная проверка restore point;
4. атомарное владение RC-3 всеми изменяемыми целями;
5. CAS по каждой цели непосредственно перед мутацией;
6. восстановление точных байтов snapshot или удаление созданного файла;
7. post-read;
8. persistent receipt по каждой цели;
9. итог, который строится только из этих receipts.

Сбой в середине разбирается по фактическим байтам, а не повтором вслепую. Recovery Report различает «ROLLBACK запрошен» и «ROLLBACK физически выполнен».

**Регрессия:** 312/312 OK — 286 прежних + 26 новых, 1 skip (привилегия symlink, как раньше).

## 2. ARCHITECTURE

**Новые модули:**

| Модуль | Ответственность |
| --- | --- |
| `web_alarm/rollback_store.py` (299 строк) | `RollbackStore` — запись сессии `<task_dir>/rollbacks/<rollback_id>.json` (атомарно, `revision`, строгая fail-closed валидация, включая receipts). `PreservedStateStore` — сохранённые байты в `<task_dir>/rollback_preserved/<sha256>.bin` (наследник `PayloadStore`: content-addressed, write-once, hash+size при записи и чтении, запрет размещения внутри workspace, лимит размера) |
| `web_alarm/rollback_service.py` (826 строк) | `RollbackService.prepare / apply / close / inspect / report_facts`. Единственные две точки физической мутации — `_write_restored_bytes` (атомарная запись) и `_delete_created` |

**Изменённые модули — минимально и локально:**
- `manifest_store.py` (+68): новый **`restore_plan()`** — проверенный read/plan-примитив без побочных эффектов. Проверяет VERIFIED manifest, связь entry ↔ snapshot, hash+size каждого snapshot и возвращает точные байты и fingerprint restore point. В отличие от `verify_restore_point(active_only=True)` при ошибке **ничего не пишет**: не блокирует manifest и не меняет статус microtask. `restore_microtask()` и CLI не тронуты.
- `target_claim_store.py` / `target_claim_service.py` (+17 / +10): обратно совместимое расширение RC-3, см. §6.
- `recovery_report_store.py` / `recovery_report_builder.py` / `recovery_report_service.py`: поле `rollback_receipts` и факты rollback из persistent receipts, см. §10.
- `server.py` (+51): маршруты `/tasks/<t>/rollbacks`, ошибки, capability `rollbacks`.
- `__init__.py` (+8): экспорт.

**Почему не дублируется старый authority Manifest / Snapshot.** Байты и pre-state берутся только из существующего restore point WA-1 через `restore_plan()`. Второго snapshot-мира нет. Новое хранилище — только сохранённое **текущее** состояние перед rollback; по смыслу это другие данные (то, что rollback собирался уничтожить). Старый прямой `restore_microtask()` как executor не используется. Атомарная запись берётся оттуда же (`_atomic_write_bytes`). Серверный endpoint snapshot по-прежнему verify-only.

## 3. IDENTITY / PERSISTENCE / ROLLBACK ← RESOLUTION

**`rollback_id = "rb_" + sha256([task_id, resolution_id])[:32]`** — одна сессия на одну резолюцию ROLLBACK (логический basis). Повтор `prepare` с той же резолюцией возвращает ту же сессию (`REPLAYED`), второго независимого rollback не возникает.

**Запись сессии:**
- `rollback_id`, `task_id`, `microtask_id`, `operation_id`, `resolution_id`;
- `basis` — `evidence_fingerprint` из резолюции, `operation_revision`, `operation_request_fingerprint`, `manifest_id`, `restore_point_fingerprint`;
- `status`, `revision`, `created_at` / `updated_at`, `provenance`;
- `targets[]` — упорядочены по `target_hash`;
- `last_attempt` — почему заблокировано;
- `result`, `claims_released`, `next_safe_action`.

**Поля цели:**
- `manifest_entry_id`, `snapshot_id`, `source_path`;
- канонические `target` / `target_key` / `target_hash` (физическая identity RC-3);
- `expected_restore` — pre-state snapshot;
- `preserved` — exists / size / sha256, ссылка на blob, `preserved_at`;
- `planned_action` — `WRITE_RESTORE` / `DELETE_CREATED` / `NOOP`;
- `claim_id`, `status`, `receipt`, `failure`.

**Статусы сессии** — деталь хранения Resolver-слоя, **не** новый публичный lifecycle:

`PREPARED → PRESERVED → AUTHORIZED → APPLYING → VERIFIED | PARTIAL | FAILED`

плюс терминальные `PRESERVATION_FAILED` (ничего не мутировано) и `CLOSED` (владение снято после неуспеха). Соответствие смысловым фазам карточки:

| Фаза карточки | Статус |
| --- | --- |
| INTENT | PREPARED |
| CURRENT_STATE_PRESERVED | PRESERVED |
| AUTHORIZED | AUTHORIZED |
| APPLYING | APPLYING |
| APPLIED + VERIFIED | VERIFIED (каждая цель проверена post-read) |
| PARTIAL / FAILED | PARTIAL / FAILED |
| UNKNOWN | APPLYING, найденный процессом под блокировкой TASK |

**Статусы целей:** `PENDING` (не начато) → `PRESERVED` → `APPLYING` (судьба неизвестна, если процесс прервался) → `RESTORED` (post проверен) / `NOOP` (уже в pre-state) / `DRIFTED` / `FAILED`.

**Authority (`_authority`) — отказ без записи и без мутации, если:**
- резолюции нет (`NO_ROLLBACK_RESOLUTION`);
- она не ROLLBACK (`NOT_A_ROLLBACK`);
- она не ACCEPTED (`ROLLBACK_NOT_ACCEPTED`);
- она от другой task / microtask / op (`RESOLUTION_MISMATCH`);
- есть accepted ABORT (`RECOVERY_ABORTED`);
- контракт legacy v1 (`LEGACY_CONTRACT`);
- restore point невалиден (`RESTORE_POINT_INVALID`);
- резолюция не fresh (`STALE_RESOLUTION`).

Набор целей берётся **только** из проверенного manifest. Вызывающий передаёт лишь `resolution_id`.

## 4. CURRENT-STATE PRESERVATION

`prepare` сначала сохраняет PREPARED (intent), затем по каждой цели в порядке `target_hash`:
1. каноническая identity;
2. scope секретов — deny-list RC-0; исключение только для собственной цели операции с записанным в контракте override;
3. `observe_path`;
4. если файл есть — чтение байтов, сверка с наблюдением, `PreservedStateStore.put` (hash+size проверяются на записи), повторное наблюдение — нестабильная цель даёт отказ;
5. если файла нет — persistent `exists=false`, без blob.

Затем выбирается действие: preserved == expected → `NOOP`; expected существует → `WRITE_RESTORE`; иначе `DELETE_CREATED`.

**Любой сбой хотя бы одной цели** — scope, лимит, нестабильность, ошибка чтения или целостности — переводит **всю** сессию в `PRESERVATION_FAILED`, и деструктивная фаза в этой сессии невозможна. Сбой в середине preservation оставляет PREPARED: повтор `prepare` дозавершает сохранение, blob'ы content-addressed. Содержимое в events, отчёты и логи не попадает, только hash / size / exists.

## 5. CONFLICT / CAS MODEL

`apply`, всё под блокировкой TASK и блокировками **всех** изменяемых целей; порядок захвата — TASK → цели по возрастанию `target_hash`, тот же глобальный порядок, что в RC-3:
1. **Прерванные записи:** цель в `APPLYING`, байты равны `expected_restore` → `RESTORED` (receipt с `recovered_after_interruption=true`, **без повторной записи**). Байты равны `preserved` → запись не дошла, цель снова `PRESERVED`. Иначе → `DRIFTED (UNKNOWN_AFTER_INTERRUPTION)`.
2. **Basis сессии:** authority жива (нет ABORT, резолюция ACCEPTED), `operation_revision` и request fingerprint прежние, `restore_point_fingerprint` прежний. **До первой собственной мутации** — дрейф целей относительно preserved (`STATE_DRIFT`) и **полная** проверка свежести Resolver.
3. **Владение — всё или ничего:**
   - каждая изменяемая цель свободна, либо принадлежит этому rollback, либо собственному claim исходной операции (он переходит к rollback, см. §6);
   - конфликт хотя бы на одной цели → `BLOCKED / TARGET_CONFLICT` с `blocking_owners`, **ни одного claim не записано**;
   - перед записью claims ещё раз CAS всех целей.
4. **По каждой цели перед мутацией:**
   - claim ещё принадлежит rollback;
   - каноническая identity прежняя;
   - текущие байты == preserved (CAS);
   - persist `APPLYING`;
   - запись точных байтов snapshot (атомарно) или удаление;
   - post-read;
   - receipt; при совпадении `RESTORED`, иначе `FAILED / POST_VERIFY_MISMATCH`.

   Дрейф → `DRIFTED / STATE_DRIFT`, файл **не перезаписывается**, сессия останавливается.
5. **Итог:** все цели RESTORED / NOOP → `VERIFIED`, владение снимается (`ROLLBACK_VERIFIED`). Иначе `PARTIAL` (часть восстановлена) или `FAILED`; владение удерживается, пока не будет `close`.

## 6. RC-3 INTEGRATION — расширение и versioning

- **Claim получает необязательное поле `owner = {"kind": "ROLLBACK", "rollback_id": …}`.** Отдельного «rollback-lock» нет: тот же документ цели, те же блокировки и `next_generation`, `cas_basis = preserved`.
- В RC-3 `_same_operation` теперь **исключает** claims с `owner`. Для любой операции, включая исходную, rollback-claim — **чужой владелец** (`CONFLICT` / `NOT_OWNER`), его видно в `blocking_owner.owner`. Исходная операция не может авторизоваться через claim своего rollback.
- **Если на цели активен claim самой исходной операции** (executor успел захватить цель, потом сессия потерялась), rollback атомарно переводит его в `SUPERSEDED (SUPERSEDED_BY_ROLLBACK)` и берёт цель без разрыва владения. Обход это или нет — см. §11.2.
- **Versioning:** `CLAIM_STORE_VERSION` остаётся 1. Claim без `owner` сохраняет прежний смысл RC-3. Старый код на claim с `owner` падает fail-closed («unexpected fields»), поэтому после принятия процессы WEB-02 нужно перезапустить. Старые claims и тесты RC-3 не изменились (20/20 PASS).

## 7. MULTI-TARGET

- Владение всеми изменяемыми целями — **атомарно**: все блокировки взяты, конфликты и CAS проверены до первой записи claim. Конфликт или дрейф на одной цели не даёт деструктивной фазы ни для одной.
- `NOOP`-цели не захватываются: rollback их не меняет. Перед финалом они проверяются (дрейф → `DRIFTED`).
- Разные цели не блокируют друг друга (блокировки на цель). Тест: пока rollback держит свои цели, RC-3-операция на постороннем файле получает `ACQUIRED`, а на цели rollback — `CONFLICT (owner ROLLBACK)`.

## 8. FAILURE / CRASH SEMANTICS

| Ситуация | Поведение |
| --- | --- |
| Сбой во время preservation | Сессия в PREPARED, проект не тронут, повтор `prepare` дозавершает |
| Сбой после preservation, до мутации | PRESERVED, проект не тронут, свежий процесс видит то же и может применить |
| Сбой после записи цели, до receipt | APPLYING. Свежий `apply` доказывает байты: цель → RESTORED (recovered), без повторной записи |
| Сбой до того, как запись дошла | APPLYING, байты == preserved → безопасно применяется один раз под CAS |
| Внешний дрейф | Нет перезаписи. До мутаций — `BLOCKED / STATE_DRIFT`; в середине — `PARTIAL / FAILED` |
| PARTIAL / FAILED | Для `apply` состояние финальное: повтор возвращает известный результат. Продолжение — `close` (снять владение) и новая reconciliation; резолюция к этому моменту уже устарела из-за собственных восстановлений |
| Повтор VERIFIED | `REPLAYED`, ноль записей, mtime не меняется |

## 9. RECEIPTS

**Receipt цели** (`targets[].receipt`):
- `rollback_id`, `target`, `target_key`, `target_hash`;
- `action` (WRITE_RESTORE / DELETE_CREATED / NOOP);
- `preserved` (exists / size / sha256 до rollback), `expected_restore`, `observed_post`;
- `matches_expected_restore`, `recovered_after_interruption`;
- `operation_revision`, `evidence_fingerprint`, `restore_point_fingerprint`, `at`.

Валидация fail-closed: RESTORED и NOOP **обязаны** иметь receipt с совпадением. Подменённый receipt даёт `RollbackError` при чтении (тест).

**Итог** (`result`): `overall` (SUCCESS / PARTIAL / FAILED / NOT_STARTED), `restored`, `noop`, `unresolved`. Строится только из persistent-фактов по целям. `SUCCESS` — только если доказан весь набор целей.

## 10. RECOVERY REPORT INTEGRATION

- **`actually_rolled_back`** берётся **только** из целей сессий со статусом `RESTORED` и `matches_expected_restore=true`. Принятая резолюция ROLLBACK сама по себе — по-прежнему `ROLLBACK_REQUESTED` в `resolver_actions` и даёт `actually_rolled_back=[]`.
- **Новое поле `rollback_receipts`** (по умолчанию `[]`; старые отчёты, включая живой `report_wa37_ctrl002`, читаются): `rollback_id`, `resolution_id`, `status`, `overall`, `restored`, `noop`, `unresolved`, `claims_released`, `physical_mutation_performed`. Частичный rollback виден как `PARTIAL` с `unresolved` и никогда не выдаётся за полный.
- **NEXT SAFE ACTION:** если authoritative-совет Resolver относится к ROLLBACK-резолюции, у которой есть сессия, используется совет сессии; `evidence_identity.next_safe_action_source = "rollback"`. ABORT по-прежнему старше.
- **Заявка вызывающего** `actually_rolled_back` без подтверждающего receipt → `RecoveryReportClaimError`. NOOP-цель — тоже не rollback (тест).

## 11. РЕШЕНИЯ ВНУТРИ SCOPE — на внимание проверяющему

1. **Свежесть «с поправкой на собственные изменения».** Карточка (§7) требует проверять свежесть резолюции ROLLBACK перед *каждой* мутацией. Буквально это невыполнимо для нескольких целей: восстановив первую цель, rollback сам меняет evidence, и fingerprint перестаёт совпадать. Реализовано так:
   - **полная** проверка fingerprint Resolver — до первой мутации;
   - после неё basis доказывается без поправки на свои изменения: ревизия и identity операции, restore point, нет ABORT, восстановленные цели == restore state, остальные == preserved, плюс CAS каждой цели.

   Это не слабее исходного требования: всё, что могло бы изменить решение reconciliation, кроме собственных receipts, проверено.
2. **Переход claim исходной операции к rollback** (SUPERSEDED_BY_ROLLBACK) вместо конфликта. Без него rollback операции, чей executor успел захватить цель, был бы невозможен: release для STARTED закрыт guard'ом RC-3. Переход атомарный, разрыва владения нет.
3. **PARTIAL / FAILED финальны для `apply`**; продолжение — `close` и новая reconciliation (fail-closed).
4. **Лимит preservation** = лимит payload RC-0 (1 МиБ, настраивается в конструкторе). Цель больше лимита → `PRESERVATION_FAILED`, rollback такой микрозадачи невозможен (у snapshot WA-1 лимита нет). **Может понадобиться решение** о большем лимите для preservation.
5. **Цель с секретным именем** сохраняется только если это собственная цель операции с записанным override; иначе `PRESERVATION_FAILED`.
6. **Legacy v1 как источник** → `LEGACY_CONTRACT`: RC-3 не даёт legacy-операциям владение целями.
7. **Lifecycle не меняется:** после VERIFIED rollback операция остаётся STARTED, статус microtask не меняется. Проекция — RC-5.

## 12. ИЗМЕНЁННЫЕ ФАЙЛЫ

| Файл | Изменение |
| --- | --- |
| `web_alarm/rollback_store.py` | **новый** |
| `web_alarm/rollback_service.py` | **новый** |
| `web_alarm/manifest_store.py` | +68 — `restore_plan()` |
| `web_alarm/target_claim_store.py` | +17 / −1 — `owner`, `ROLLBACK_OWNER` |
| `web_alarm/target_claim_service.py` | +10 / −2 — `_same_operation` исключает claims с `owner`; `owner` в сводке владельца |
| `web_alarm/recovery_report_store.py` | +7 — `rollback_receipts` |
| `web_alarm/recovery_report_builder.py` | +6 / −1 — передача поля, источник совета |
| `web_alarm/recovery_report_service.py` | +18 — факты rollback, совет, проверка заявок |
| `web_alarm/server.py` | +51 — маршруты, ошибки, capability |
| `web_alarm/__init__.py` | +8 — экспорт |
| `test_web_alarm_rollback.py` | **новый**, 25 тестов |
| `test_web_alarm_rollback_concurrency.py` | **новый**, 1 межпроцессный тест (4 раунда) |

Safety copies 8 изменённых файлов + `baseline.md` (SHA-256, HEAD) — в `safety_copies/`.

**API:**
- `POST /tasks/<t>/rollbacks {microtask_id, operation_id, resolution_id}` — prepare: 201 PRESERVED / 200 REPLAYED / 409;
- `POST …/rollbacks/<id>/apply` — 200 VERIFIED / REPLAYED, 409 BLOCKED / PARTIAL / FAILED / REJECTED;
- `POST …/rollbacks/<id>/close`;
- `GET …/rollbacks[?operation_id]`, `GET …/rollbacks/<id>`.

Неизвестный суффикс → 404. Произвольного restore нет.

## 13. TESTS (§15 карточки)

| № | Тест | Результат |
| --- | --- | --- |
| 1 | `test_accepted_fresh_rollback_creates_persistent_preserved_session` | PASS |
| 2, 3, 4 | `test_missing_wrong_stale_rejected_or_aborted_resolution_never_restores` (нет резолюции, REJECTED, STALE, ABORT), `test_abort_after_prepare_blocks_destructive_phase` | PASS |
| 5 | `test_restore_point_integrity_failure_never_restores_and_is_side_effect_free` — битый snapshot до prepare → `RESTORE_POINT_INVALID`; после prepare → `BLOCKED`; manifest JSON побайтно цел | PASS |
| 6, 7 | `test_existing_bytes_and_absence_are_preserved_and_verified_before_restore` — blob == текущие байты, absence persistent, в events нет содержимого | PASS |
| 8 | `test_preservation_failure_of_one_target_blocks_every_target` (+ `test_crash_during_preservation_resumes_without_any_mutation`) | PASS |
| 9, 11 | `test_existing_target_restored_exactly_and_pre_state_target_is_noop` — точные байты, post-hash и size; NOOP без записи (spy на запись) | PASS |
| 10 | `test_created_file_is_deleted_and_absence_verified` | PASS |
| — | `test_two_targets_restored_including_recreated_file` | PASS |
| 12 | `test_drift_after_preservation_is_never_overwritten` (до мутаций), `test_drift_at_the_destructive_boundary_stops_as_partial` (дрейф второй цели после записи первой) | PASS |
| 13 | `test_same_target_normal_owner_blocks_rollback` | PASS |
| 14 | `test_conflict_on_one_target_blocks_the_whole_destructive_phase` — на свободной цели не остаётся частичной reservation | PASS |
| 15 | `test_rollback_ownership_is_per_target_and_visible_to_rc3` | PASS |
| 16 | `test_replay_of_completed_rollback_has_no_second_side_effect` — 0 записей, mtime прежний | PASS |
| 17 | `test_crash_after_preservation_before_mutation_leaves_project_unchanged` (свежий процесс) | PASS |
| 18 | `test_crash_after_one_restore_is_proven_not_repeated` (`os._exit` после первой записи; свежий процесс не пишет её повторно), `test_crash_before_the_write_landed_is_safely_applied_once` | PASS |
| 19 | `test_tampered_receipt_fails_closed` + проверки полей receipt в 9 / 10 / 18 | PASS |
| 20 | PARTIAL ≠ VERIFIED (тест 12b), SUCCESS только при полном наборе | PASS |
| 21 | `test_request_only_rollback_is_not_actually_rolled_back`, `test_verified_rollback_populates_actual_facts_and_rejects_unbacked_claims`, PARTIAL-отчёт в 12b | PASS |
| 22 | `test_fresh_process_sees_same_status_receipts_and_next_action` | PASS |
| — | `test_source_operation_claim_is_taken_over_not_bypassed`, `test_server_rollback_endpoints` | PASS |
| 23 | Живое storage WEB-02 (read-only, свежий процесс): `report_wa37_ctrl002` читается (`rollback_receipts=[]`), rollback'ов нет, legacy claim → `DENIED / LEGACY_CONTRACT`, старый manifest WA-3.7 читается (VERIFIED); дерево `88fc4f99…4149`, 136 файлов до и после | PASS |
| 24 | RC-1 / 2 / 3 focused + manifest + Recovery Report (11 модулей) | **115/115 OK** (skip 1) |
| 25 | `test_rollback_and_normal_owner_never_both_win` — 4 процесса `apply` + 4 процесса RC-3 из чужих TASK на одну цель, 4 раунда (2 без задержки, 2 с jitter): либо rollback (1 восстановление, 0 чужих владельцев), либо одна операция (0 восстановлений), никогда оба; восстановление никогда не дважды. **5/5 прогонов.** **Чувствительность** (scratchpad, 6 раундов на режим): без задержки с блокировками — один победитель каждый раз; **без блокировок — 3 раунда «два владельца» + 3 падения процессов**. С jitter реально выигрывает и rollback | PASS |
| 26 | Полный `test_web_alarm_*.py` | **312/312 OK** (skip 1), 46 с |
| 27 | `python -B -m compileall -q web_alarm` | OK |
| 28 | `git diff --check` (всё дерево) | OK |

## 14. COMPATIBILITY

- **Manifest / snapshots WA-1:** формат не менялся; `restore_microtask` и CLI не тронуты; `restore_plan` только читает.
- **Legacy WA-3.7, контракт v2, записи Resolver RC-2, claims RC-3, старые Recovery Reports:** формат не менялся, всё читается (тесты + живое storage).
- **Новые форматы:** `rollback_version=1`, claim с `owner`, поле отчёта `rollback_receipts`. Старый код на них падает fail-closed → **после принятия процессы WEB-02 перезапустить** (сейчас не запущены).

## 15. UNRESOLVED / PROPOSALS

1. **Лимит preservation** для файлов больше 1 МиБ (§11.4) — нужно решение.
2. **Старый CLI `snapshot restore`** (`restore_microtask`, WA-1) остаётся прямым нетрекаемым деструктивным путём. Не менял; предлагаю закрыть или пропустить через RC-4 на strict rollout (WA4-R).
3. **Проекция результата rollback** в checkpoint / Context Pack и статус microtask — RC-5.
4. **Продолжение PARTIAL** только через `close` и новую reconciliation. Если нужен «resume после устранения дрейфа» в той же сессии — отдельное решение.

## 16. CLOSEOUT

- `000_Задачи Claude.md`: по новому правилу ротации полная постановка из БЛОКА 1 скопирована в БЛОК 2, итог записан в БЛОК 3. Только после проверки, что БЛОКИ 2–3 сохранены на диске, БЛОК 1 очищен до `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ / TASK: —`.
- `001`, `06`, `25`, глобальный `000_Задачи для агента` и canonical DONE / VERIFIED не менялись: это делает проверяющий.

**RC-5 NOT STARTED.**

## 17. NEXT SAFE ACTION

Независимая проверка RC-4 (ChatGPT / пользователь). RC-5 не начинать.
