# CLAUDE-WA-004 — RC-2: Persistent Resolver + evidence revision binding

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локальный доступ.
**Дата:** 2026-10-04.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION (повторно, после Independent Review Repair — см. §9).
**ARCH CLASS:** Web Alarm Workspace runtime (WEB-02). **PRIMARY PROFILE:** `23`; acceptance — `24`.
**База:** HEAD `9596187` (RC-1 закоммичен; дрейфа кода после RC-1 нет: рабочее дерево `web_alarm/` и тестов перед стартом чистое, размеры модулей RC-1 совпадают с коммитом).
**Не менялись:** публичный `OperationStatus` и `models.py`, lifecycle TASK/microtask, `reconciliation.py`, decision engine, `operation_contract.py`, UI, `.gitattributes`, переводы строк. Commit / push не выполнялись. Физических мутаций проекта Resolver не выполняет.

---

## 1. RESULT

Добавлен узкий persistent Resolver. Четыре recovery-действия — ADOPT, RETRY, ROLLBACK, ABORT — стали tracked records. Каждая запись жёстко привязана к `evidence_fingerprint` (из существующего `ReconciliationDecisionEngine`) и к `revision` операции.

Перед записью результата Resolver под блокировкой TASK делает следующее:
1. перечитывает `OperationRecord`;
2. заново собирает evidence из текущего Workspace — только persistent: post-state из контракта v2 или manifest, без post-state от вызывающего;
3. пересчитывает fingerprint и решение;
4. сверяет basis, который прислал вызывающий.

Если basis устарел, запрос получает STALE и не применяется. Recovery Report теперь берёт факты о действиях только из записей Resolver.

**Регрессия:** 260/260 OK — 241 прежний тест + 19 новых, 1 skip (привилегия symlink, как в RC-1).

## 2. ЧТО СДЕЛАНО

**Новые модули:**

| Модуль | Ответственность |
| --- | --- |
| `web_alarm/resolution_store.py` | `ResolutionRecord` (write-once, строгая валидация), перечисления `ResolutionAction` / `ResolutionResult`, логическая identity и производный `resolution_id`, `ResolutionStore` в `<task_dir>/resolutions/` |
| `web_alarm/resolver_service.py` | `ResolverService.apply` / `freshness` / `report_facts`: свежий basis, проверка «действие ↔ решение», допустимость re-arm, события |

**Изменённые модули — минимально:**
- `operation_store.py` (+6): публичный `task_lock(task_id)` поверх существующей блокировки RC-1. Resolver проверяет и пишет атомарно относительно переходов операции.
- `recovery_report_store.py` (+7): поле `resolver_actions` (по умолчанию `[]`; старые отчёты читаются).
- `recovery_report_builder.py` (+5): передаёт `resolver_actions` дальше.
- `recovery_report_service.py`: факты о действиях берутся из Resolver, заявки вызывающего проверяются.
- `server.py` (+55):
  - `POST` / `GET /tasks/<id>/resolutions`, `GET /tasks/<id>/resolutions/<rid>` с freshness;
  - capability `resolutions`;
  - ошибки: 400 `invalid_resolution`, 409 `resolution_conflict` / `resolution_not_accepted` / `resolver_error`.
- `__init__.py` — экспорт.

**ResolutionRecord:**
- `resolution_id`, `task_id`, `microtask_id`, `operation_id`, `action`;
- `requested_basis` — что прислал вызывающий: `evidence_fingerprint`, `operation_revision`;
- `basis` — что Resolver вычислил сам:
  - `evidence_version`, `evidence_fingerprint`;
  - `decision_version`, `decision`, `reason_code`;
  - `operation_status`, `operation_contract_version`, `operation_revision`, `operation_request_fingerprint`;
  - `affected_targets`;
- `result` (`ACCEPTED` / `STALE` / `REJECTED`), `result_code`, `result_reason`;
- `effect` — только при ACCEPTED;
- `next_safe_action`, `payload_verified`;
- `physical_mutation_performed=false` — инвариант, другое значение не валидируется;
- `provenance` (claimed), `created_at`.

`result` — внутренняя деталь хранения Resolver, а не новый публичный lifecycle (V15 остаётся отложенным).

**Порядок оценки (всё под `task_lock`):**
1. Если операция уже закрыта принятым ABORT → `REJECTED`, `RECOVERY_ABORTED` (для повторного ABORT — `RECOVERY_ALREADY_ABORTED`).
2. Изменилась `revision` → `STALE`, `OPERATION_REVISION_CHANGED`.
3. Изменился `fingerprint` → `STALE`, `EVIDENCE_FINGERPRINT_CHANGED`.
4. Действие не соответствует решению → `REJECTED`, `ACTION_DECISION_MISMATCH`:
   - ADOPT требует `ADOPT_CURRENT_STATE`;
   - RETRY требует `RETRY_SAFE`;
   - ROLLBACK требует `ROLLBACK_CURRENT_MICROTASK`;
   - ABORT допустим при любом решении.
5. Только для RETRY:
   - legacy v1 → `LEGACY_CONTRACT`;
   - payload не проходит проверку целостности → `PAYLOAD_INTEGRITY_FAILURE`;
   - `rearm_contract_sufficient=false` → `CONTRACT_INSUFFICIENT`.
6. Иначе → `ACCEPTED`.

Все исходы (ACCEPTED / STALE / REJECTED) записываются вместе с событием `RESOLUTION_<RESULT>` в `events.jsonl` (только метаданные).

Если authoritative state прочитать нельзя — операция повреждена или неизвестна, TASK не активна, нет evidence, — это `ResolverError`, и запись **не** создаётся.

**Семантика действий:**

| Действие | `effect` | Что значит в RC-2 |
| --- | --- | --- |
| ADOPT | `WORKSPACE_STATE_ADOPTED` | Текущее состояние Workspace принято как recovery-факт на этом basis. `OperationStatus` не меняется, Workspace не меняется. |
| RETRY | `REARMED_FOR_FUTURE_EXECUTOR` | Только re-arm того же `operation_id` для будущего WA4-E. Ничего не пишется и не исполняется. Executor обязан перепроверить basis. |
| ROLLBACK | `ROLLBACK_REQUESTED` | Только tracked-запрос. Restore не вызывается, файлы, manifest и статус microtask не меняются. Физический rollback — RC-4. |
| ABORT | `RECOVERY_ABORTED` | Recovery операции на уровне Resolver закрыт: дальнейшие ADOPT / RETRY / ROLLBACK по ней отклоняются. Нового terminal `OperationStatus` нет. |

**Idempotency.**
- `resolution_id` либо передаёт вызывающий, либо он выводится детерминированно из логической identity: `task`, `micro`, `op`, `action`, `requested_basis`.
- Повтор с тем же id и той же identity возвращает известный результат: новой записи и события нет.
- Тот же id с другим действием или basis — `ResolutionConflictError`.
- Та же логическая identity под другим id — тоже конфликт: два «успешных» resolution для одного логического действия невозможны.

**Freshness.** `freshness(record)` в любой момент пересчитывает basis. Это нужно потому, что CAS RC-3 ещё нет и цель после проверки не блокируется. Устаревшая резолюция не считается authority.

**Recovery Report (§8):**
- `accepted_as_already_done` берётся только из **fresh accepted ADOPT**: `basis.affected_targets`;
- `actually_retried` и `actually_rolled_back` в RC-2 всегда `[]`;
- re-arm, запрос rollback, ABORT и ADOPT видны в новом поле `resolver_actions` вместе со свежестью basis;
- поля от вызывающего API сохранены ради совместимости, но могут лишь **повторять** факты Resolver. Любая неподтверждённая заявка → `RecoveryReportClaimError`, 409;
- `authority=evidence_only` и `automatic_mutation_authorized=false` не менялись;
- `REPORT_VERSION` остался 1: поле добавлено с default, старые отчёты (включая живой `report_wa37_ctrl002`) читаются.

## 3. РЕШЕНИЯ ВНУТРИ SCOPE — на внимание проверяющему

1. **Resolver не принимает post-state от вызывающего.** Evidence собирается только из persistent state. Следствие: ADOPT и RETRY возможны только для операций, где post-state известен без вызывающего — контракт v2 с payload или declared post, либо manifest `delete`. Для старых и legacy-операций без такого post решение будет `MANUAL_REVIEW_REQUIRED`, и Resolver допускает только ABORT. Это прямое продолжение RC-1 («убрать caller authority»). Для новых операций GPT стоит передавать полный контракт с payload.
2. **Изменены 4 старых теста** в `test_web_alarm_recovery_report_acceptance.py` (2) и `test_web_alarm_recovery_report_integration.py` (2). Они проверяли именно ту caller authority, которую RC-2 обязан убрать: `accepted_as_already_done` от вызывающего без tracked ADOPT. На новом коде они падали ровно с `RecoveryReportClaimError` — это проверено до правки. Минимальная правка:
   - операция получает `payload` (контракт v2 с post-state);
   - перед отчётом записывается tracked ADOPT.

   Проверки (`accepted_as_already_done == ["file.txt"]` и прочие) **не менялись**. Diff: +43 / −3. Исходники сохранены в `safety_copies/`.
3. **Общая блокировка TASK с Operation Store** (а не отдельная блокировка Resolver). Проверка basis и запись резолюции атомарны относительно переходов операции, а события Resolver и Operation Store не перемешиваются в `events.jsonl`. Это целостность хранилища, а не conflict gate RC-3.
4. **STALE и REJECTED тоже сохраняются** (§4: «accepted / stale / rejected»). Повтор того же запроса возвращает тот же результат. Новая попытка требует нового basis.
5. **ABORT окончателен для операции на уровне Resolver.** «Отменить ABORT» нельзя; продолжение — ручной review или новая операция.

## 4. ПРОВЕРКА

| № п. 10 карточки | Проверка | Результат |
| --- | --- | --- |
| 1, 12 | 4 действия persistent; свежий процесс видит ту же запись, basis, результат, freshness и `next_safe_action`; отчёт, собранный в свежем процессе, воспроизводит те же факты | PASS |
| 2 | ADOPT при `RETRY_SAFE`, ROLLBACK при `RETRY_SAFE`, RETRY при `ADOPT_CURRENT_STATE` → `REJECTED / ACTION_DECISION_MISMATCH` | PASS |
| 3 | reconcile → изменение target → apply по старому basis → `STALE / EVIDENCE_FINGERPRINT_CHANGED` | PASS |
| 4 | reconcile (INTENT, rev 1) → переход STARTED (rev 2) → apply по старому basis → `STALE / OPERATION_REVISION_CHANGED` | PASS |
| 5, 6 | Повтор — replay без второй записи и второго события `RESOLUTION_ACCEPTED`; тот же id с другим действием или basis и та же identity под другим id → conflict | PASS |
| 7 | RETRY на legacy v1 → `LEGACY_CONTRACT`, legacy JSON побайтно не изменён; на неполном v2 → `CONTRACT_INSUFFICIENT`; на повреждённом v2 → `ResolverError` без записи | PASS |
| 8 | Повреждённый payload → `PAYLOAD_INTEGRITY_FAILURE`, `payload_verified=false` | PASS |
| 9, 10 | Для каждого действия хеши всех файлов проекта и `OperationRecord` до и после apply идентичны; для ROLLBACK также не меняются microtask и manifest | PASS |
| 11 | Отчёт: только fresh ADOPT → accepted; RETRY / ROLLBACK не попадают в `actually_*`; устаревший ADOPT не является authority; заявки вызывающего без резолюции → `RecoveryReportClaimError` | PASS |
| 13 | 8 реальных процессов одновременно применяют одну резолюцию: ровно 1 `created`, один id, 1 файл, 1 событие `RESOLUTION_ACCEPTED`; 5/5 прогонов. **Чувствительность:** с отключённой `task_lock` (скрипт в scratchpad) тест падает 5/5 | PASS |
| 14 | `python -B -m unittest test_web_alarm_*.py` | **260/260 OK** (skip 1), 28,8 с |
| 15 | `python -B -m compileall -q web_alarm` | OK |
| 16 | `git diff --check` | OK; новые файлы — LF, без хвостовых пробелов; изменённые остаются `i/lf w/lf` |
| — | Живое storage WEB-02 (read-only, свежий процесс): `report_wa37_ctrl002` читается (`resolver_actions=[]`), `WA37-CTRL-001/002` — v1, резолюций нет | дерево `88fc4f99…4149`, 136 файлов до и после — без изменений |
| — | Границы | `models.py`, `ui.py`, `state_machine.py`, `manifest_store.py`, `reconciliation*.py`, `operation_contract.py` не тронуты; `.gitattributes` отсутствует |

Новые тесты: `test_web_alarm_resolver.py` (18), `test_web_alarm_resolver_concurrency.py` (1).

**Инцидент при работе.** Одна правка `server.py` упала с `EPERM` при атомарном rename: файл держал внешний писатель. До повтора проверено: файл парсится, хвост цел, временных файлов нет, не применилась ровно одна правка (`self.resolver = …`). Повторена только она.

## 5. ГРАНИЦЫ И ОТКРЫТЫЕ ВОПРОСЫ (не входят в RC-2)

- **CAS по target (RC-3)** отсутствует. Accepted RETRY не блокирует цель: будущий executor обязан вызвать `freshness` и сверить basis непосредственно перед записью.
- **ADOPT не меняет `OperationStatus`.** Операция с принятым ADOPT остаётся, например, STARTED. Как это отразить в lifecycle или projection — вопрос V15 / RC-5, не RC-2. Не блокирует.
- Checkpoint, Context Pack и Remote entry резолюции пока не показывают. Это projection и resume — RC-5 / RC-6.
- Как и в RC-1, под блокировкой нет записей events и checkpoint из state machine и manifest, а также чтений.
- **Rollout.** Старый код WEB-02 не прочитает новые отчёты (поле `resolver_actions`) и резолюции. После принятия RC-2 процессы WEB-02 нужно перезапустить; сейчас ни один не запущен.

## 6. PROPOSALS (вне scope)

1. **RC-5:** показывать в checkpoint и Context Pack последнюю актуальную резолюцию и её свежесть; `NEXT_SAFE_ACTION` строить с её учётом.
2. **WA4-E:** executor принимает только fresh accepted RETRY без последующего ABORT и обязан записать собственный receipt (контракт RC-1 это уже поддерживает).
3. **V15 (отдельное решение):** нужен ли operation lifecycle-переход после ADOPT / ABORT или достаточно projection.

## 7. CLOSEOUT

- `000_Задачи Claude.md`: постановка из БЛОКА 1 скопирована в БЛОК 2, краткий итог записан в БЛОК 3 со статусом `RESULT READY / AWAITING INDEPENDENT VERIFICATION`. БЛОК 1 не тронут.
- `001`, `06`, `25` и другие канонические документы **не менялись**: их после PASS синхронизирует проверяющий (новое правило карточки).
- Safety copies: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-004_RC2/safety_copies/` + `baseline.md` (SHA-256). Удалить после независимой проверки.

## 8. NEXT SAFE ACTION

Независимая проверка RC-2 (ChatGPT / пользователь):
- перепрогнать 260 тестов;
- проверить чувствительность теста гонки;
- прочитать дифф 2 новых и 6 изменённых модулей и 4 изменённых старых тестов (§3.2);
- принять или оспорить решения §3.1 и §3.5.

RC-3 до этого не начинать.

---

## 9. INDEPENDENT REVIEW REPAIR (2026-10-04)

**Вход.** Независимая проверка ChatGPT по commit 147 `fe55c99`: RC-2 = REVIEW FAILED / REPAIR REQUIRED. Основная реализация Resolver подтверждена: 19/19, 260/260, гонка 5/5, все свойства stale / replay / no-mutation и др. Найдены **два blocker-а acceptance**. Repair минимальный, только в слое Resolver / Recovery Report. Дрейф перед repair: код в рабочем дереве совпадает с commit 147. Safety copies — `safety_copies/repair/`, хеши — `baseline.md`.

### Blocker 1 — NEXT SAFE ACTION отчёта игнорировал persistent Resolver

- **Воспроизведено** до правки тестом (TEST A). После accepted ABORT на `RETRY_SAFE` отчёт выдавал `retry only through the replay-safe execution path…`, хотя резолюция говорит «recovery closed».
- **Причина.** `RecoveryReportBuilder` брал `next_safe_action` только из advisory `ReconciliationDecision`.
- **Исправление.** `ResolverService.report_facts()` теперь возвращает authoritative `next_safe_action` из persistent-резолюций, а builder ставит его выше решения reconciliation. Приоритет:
  1. **accepted ABORT** — всегда, даже при постаревшем basis, потому что ABORT окончателен. NEXT SAFE ACTION = сохранённый текст ABORT («recovery … is closed»);
  2. **последняя fresh accepted** резолюция — её сохранённая семантика:
     - RETRY: re-armed, nothing was executed;
     - ROLLBACK: request only, nothing was restored;
     - ADOPT: existing state accepted;
  3. иначе **последний исход**:
     - fresh REJECTED — его сохранённый совет. При несоответствии действия и решения это совет того же решения; при legacy, неполном контракте или повреждённом payload — manual review, а не RETRY;
     - любой stale (STALE-результат или постаревший basis) — «resolution … is not authority: its basis is stale (…); run a new reconciliation and resolve on its fresh evidence_fingerprint and operation_revision»;
  4. **резолюций нет** — прежнее поведение, совет reconciliation.
- **Аудит источника.** В `evidence_identity` отчёта добавляются `next_safe_action_source="resolver"` и `next_safe_action_resolution_id` — только когда совет пришёл от Resolver. Отчёты без резолюций не меняются.

### Blocker 2 — STALE / REJECTED исходы не попадали в отчёт

- **Воспроизведено** до правки тестом (TEST B). В хранилище 1 STALE-резолюция, а `resolver_actions = []`.
- **Причина.** `report_facts()` фильтровал записи по `result == ACCEPTED`.
- **Исправление.** `resolver_actions` содержит **все** persistent-исходы операции (ACCEPTED / STALE / REJECTED) в порядке создания. Поля:
  - `resolution_id`, `action`, `result`, `result_code`, `effect`;
  - `authority`, `fresh`, `freshness_code`;
  - `evidence_fingerprint`, `operation_revision`, `created_at`;
  - `physical_mutation_performed=false`.
- **Authority по-прежнему fail-closed:**
  - `authority = ACCEPTED and (fresh or ABORT)`;
  - `accepted_as_already_done` берётся только из FRESH + ACCEPTED + ADOPT;
  - `actually_retried` и `actually_rolled_back` всегда `[]`;
  - STALE и REJECTED authority не дают.

### Изменения repair

- `web_alarm/resolver_service.py`: `report_facts` и новый `_authoritative_next_action`;
- `web_alarm/recovery_report_builder.py`: параметр `resolver_next_safe_action`; ключи источника в `evidence_identity`;
- `web_alarm/recovery_report_service.py`: +1 строка;
- `test_web_alarm_resolver.py`: 6 новых тестов, NEXT SAFE ACTION в выводе свежего процесса, 2 дополнительные проверки в существующих тестах отчёта.

Итого +211 / −7 строк. **Не менялись:** `models.py` и `OperationStatus` (`INTENT, STARTED, DONE, VERIFIED, FAILED, UNKNOWN_AFTER_DISCONNECT` — как до RC-2), `resolution_store.py`, `server.py`, `REPORT_VERSION`, lifecycle, UI, `.gitattributes`.

### Новые тесты

| Тест | Что доказывает |
| --- | --- |
| `test_accepted_abort_drives_report_next_safe_action` (**TEST A**) | `RETRY_SAFE` → accepted ABORT → отчёт **в свежем процессе**: ABORT persistent и fresh, в `resolver_actions` с `authority=true`, NEXT SAFE ACTION равен сохранённому тексту ABORT и не равен совету RETRY, источник `resolver`, хеши проекта не изменились |
| `test_stale_outcome_survives_report_and_fresh_process` (**TEST B**) | basis → изменение Workspace → STALE / `EVIDENCE_FINGERPRINT_CHANGED` → отчёт в свежем процессе: запись есть, `result` / `result_code` сохранены, `authority=false`, `effect=null`, все `actually_*` пустые, NEXT SAFE ACTION требует новой reconciliation |
| `test_rejected_outcomes_are_reported_without_authority` | REJECTED / `ACTION_DECISION_MISMATCH` в отчёте без authority; совет остаётся детерминированным |
| `test_rejected_rearm_is_not_recommended_as_retry` | RETRY отклонён (`CONTRACT_INSUFFICIENT`) → отчёт не советует RETRY |
| `test_report_next_action_follows_fresh_accepted_semantics` | RETRY → совет «re-armed, nothing was executed»; затем ADOPT → совет ADOPT; устаревший RETRY без authority |
| `test_report_without_resolutions_keeps_decision_next_action` | без резолюций поведение прежнее, источник не добавляется |

### Verification repair

| № | Проверка | Результат |
| --- | --- | --- |
| 1 | Новые тесты на оба blocker-а: до правки воспроизводили дефект (4 FAIL + 3 ERROR), после — PASS | PASS |
| 2 | Весь `test_web_alarm_resolver.py` | 24/24 OK |
| 3 | `test_web_alarm_resolver_concurrency.py` | 5/5 прогонов OK |
| 4 | Полный `python -B -m unittest test_web_alarm_*.py` | **266/266 OK** (skip 1), 29,8 с |
| 5 | `python -B -m compileall -q web_alarm` | OK |
| 6 | `git diff --check` | OK; изменённые файлы `i/lf w/lf` |
| 7 | Нет физической мутации Workspace | хеши проекта до и после apply / отчёта совпадают (TEST A и тесты действий); живое storage WEB-02 (read-only, свежий процесс): дерево `88fc4f99…4149`, 136 файлов — без изменений |
| 8 | Fresh-process reopen | TEST A / TEST B создают отчёт и читают резолюции в отдельном процессе |
| 9 | `OperationStatus` / `models.py` не расширены | `git diff` пуст и относительно HEAD, и относительно `9596187` (до RC-2) |

### Оставшийся разрыв вне repair-scope (PROPOSAL, на решение)

Context Pack / Remote entry при нужной reconciliation по-прежнему берут `NEXT_SAFE_ACTION` из advisory-решения (`context_pack.py:166`). Блок `LATEST_RECOVERY_REPORT` уже несёт совет Resolver, но верхнее поле — нет. Это projection / resume (RC-5 / RC-6), а repair-задача ограничила работу слоем Resolver / Recovery Report, поэтому не трогал. Исправление готово к переиспользованию: `ResolverService.report_facts(...)["next_safe_action"]` можно наложить в Context Pack так же, как в отчёте (~5 строк). Нужно решение: сделать сейчас в RC-2 или в RC-5.

**NEXT SAFE ACTION:** повторная независимая проверка RC-2. RC-3 не начинать.

---

## 10. INDEPENDENT VERIFICATION — PASS

**Verifier:** ChatGPT, 2026-10-04.
**Проверенный head:** commit 148 `0b7cb7deae8220d1f2e0f432293b0edc784b7b6d` — на момент финального review оставался последним commit репозитория.

Независимо подтверждено:
- `test_web_alarm_resolver.py` + concurrency: **25/25 PASS**;
- full `test_web_alarm_*.py`: **266/266 PASS**;
- multiprocess Resolver race: дополнительно **5/5 PASS**;
- `python -B -m compileall -q web_alarm`: PASS;
- `git diff --check`: PASS;
- ручной ABORT scenario: advisory `RETRY_SAFE` больше не переопределяет persistent ABORT; report NEXT = recovery closed;
- ручной STALE scenario: persistent STALE остаётся в `resolver_actions` без authority, NEXT требует fresh reconciliation;
- ручной REJECTED/`CONTRACT_INSUFFICIENT` scenario: report не рекомендует retry, NEXT = manual review;
- новая public Operation/Microtask state machine не введена; RC-3/RC-4/WA4-E scope не захвачен.

**Verdict:** `CLAUDE-WA-004 / RC-2 = DONE / VERIFIED`.

**Decision по Context Pack:** верхний `Context Pack / Remote entry NEXT_SAFE_ACTION` относится к projection/resume boundary. Его расхождение с Resolver-aware `LATEST_RECOVERY_REPORT` не блокирует RC-2 и переносится как обязательный follow-up в RC-5/RC-6. До их закрытия этот верхний projection не должен считаться stronger authority, чем persistent Resolver/Recovery Report state.

**NEXT:** RC-3 — Canonical-target conflict gate + mutation-boundary CAS. Не начинать автоматически; сначала отдельная утверждённая task-card.
