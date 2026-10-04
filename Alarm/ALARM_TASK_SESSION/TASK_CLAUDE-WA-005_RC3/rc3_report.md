# CLAUDE-WA-005 — RC-3: Canonical-target conflict gate + mutation-boundary CAS

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локальный доступ.
**Дата:** 2026-10-04.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**ARCH CLASS:** Web Alarm Workspace runtime (WEB-02). **PRIMARY PROFILE:** `23` (инварианты 25, 29, 30); acceptance — `24`.
**База:** HEAD `75ccbff` (commit 148, RC-2 DONE / VERIFIED). Код `web_alarm/` и тесты перед стартом совпадали с HEAD; изменения после RC-2 были только в документах.

**Не менялись:**
- `models.py` и публичный `OperationStatus`: `INTENT, STARTED, DONE, VERIFIED, FAILED, UNKNOWN_AFTER_DISCONNECT`;
- lifecycle microtask;
- `operation_store.py`, `operation_contract.py`, `target_identity.py`;
- Resolver: `resolver_service.py`, `resolution_store.py`;
- UI, `.gitattributes`, переводы строк.

Commit / push не выполнялись. **Сам control-plane RC-3 не меняет ни одного байта Workspace.**

---

## 1. RESULT

Добавлен узкий слой **Target Claim / Conflict Gate** поверх Operation Contract v2 и Resolver.

- **Один владелец на цель.** Для одной физической цели в любой момент существует не больше одного ACTIVE claim. Конкурирующие операции из той же или чужой TASK получают `CONFLICT` с указанием владельца.
- **CAS на границе мутации.** Mutation authority выдаётся только внутри `mutation_boundary`. Там под блокировками TASK и цели заново доказываются:
  - владение claim;
  - ревизия операции;
  - соответствие контракту;
  - допустимость по Resolver;
  - физические байты цели против CAS basis.
- **Освобождение.** Claim освобождается только явным действием владельца. Lease, TTL и heartbeat нет.

**Регрессия:** 286/286 OK — 266 прежних + 20 новых, 1 skip (привилегия symlink, как раньше).

## 2. УСТРОЙСТВО

**Identity конфликта — физическая цель:**
- `physical_key` — это `normcase(resolved canonical path)` с разделителями `/`. Путь берётся из канонизации RC-1 на стороне сервера по проверенному контракту (`workspace_id` + `target`, сверка с `contract.target_key`); путю от вызывающего не доверяем.
- Регистр, слэши, `./`, абсолютный путь, junction-алиас и **вложенный второй workspace**, где у той же цели другой относительный ключ, сходятся к одной identity.
- Имена файла claims и lock-файла — `sha256(physical_key)`; сырой путь в имена не попадает.

**Хранение** (`web_alarm/target_claim_store.py`):
- один документ на цель — `<storage>/target_claims/<hash>.json`: `active` (не больше одного claim), `history` (завершённые claims), `next_generation`;
- атомарный `os.replace`, поэтому состояние владения всегда целостное;
- строгая fail-closed валидация на чтение и запись.

**Поля claim:**
- `claim_id` (детерминирован от hash цели, generation, task, op и revision), `generation`;
- `task_id`, `microtask_id`, `operation_id`, `workspace_id`;
- `target`, `target_key`;
- `operation_revision`, `operation_request_fingerprint`, `contract_version=2`;
- `cas_basis` — authority pre-state из контракта;
- `status`, `created_at`, `provenance` (claimed);
- `ended_at`, `end_reason`, `ended_by`, `superseded_by`;
- `authorizations` — дедуплицированные результаты CAS.

Статусы claim — `ACTIVE` / `RELEASED` / `SUPERSEDED`. Это внутренняя деталь хранилища, а не новый публичный lifecycle.

**Блокировки** (`web_alarm/target_claim_service.py`):
- на каждую цель своя межпроцессная блокировка — `<storage>/locks/targets/<hash>.lock` на `InterProcessLock` из RC-1; разные цели друг друга не сериализуют;
- порядок всегда **блокировка TASK** (`OperationStore.task_lock`) → **блокировка цели**. Ни один путь не ждёт блокировку TASK, держа блокировку цели, поэтому deadlock между TASK исключён;
- блокировка TASK делает проверку ревизии операции и запись claim атомарными относительно её переходов.

**Acquire** (`POST /tasks/<t>/operations/<op>/claim`, тело `{operation_revision}`). Под обеими блокировками, по порядку:

| Шаг / случай | Результат |
| --- | --- |
| Legacy v1 | `REJECTED / LEGACY_CONTRACT` |
| Тот же op и та же ревизия, claim активен | `REPLAYED / SAME_BASIS` — тот же claim, без записи и события |
| Тот же op и та же ревизия, claim уже освобождён | `REPLAYED / SAME_BASIS_ALREADY_RELEASED` — запоздавший дубль не захватывает цель повторно |
| Запрошенная ревизия ≠ текущей | `STALE / OPERATION_REVISION_CHANGED` |
| Цель активна у другого op | `CONFLICT / TARGET_OWNED`, указан `blocking_owner` |
| Недопустим (см. ниже) | `REJECTED / <код>` |
| Байты цели ≠ pre-state контракта | `STALE / STATE_DRIFT` (+ `eol_only_drift`) |
| Свой claim на старой ревизии, текущая ревизия допустима | `REBASED`: старый claim → `SUPERSEDED`, новое поколение; цель не освобождается ни на миг |
| Цель свободна, basis валиден | `ACQUIRED` |

Acquire **никогда** сам не даёт mutation authority.

**Допустимость (`_eligibility`), общая для acquire и CAS:**
- legacy v1 → `LEGACY_CONTRACT`;
- DONE / VERIFIED → `OPERATION_ALREADY_COMPLETED`;
- payload не проходит проверку → `PAYLOAD_INTEGRITY_FAILURE`;
- неполный контракт → `CONTRACT_INSUFFICIENT`;
- accepted ABORT в Resolver → `RECOVERY_ABORTED`;
- INTENT → допустим;
- STARTED / UNKNOWN_AFTER_DISCONNECT / FAILED → только если **последняя fresh accepted** резолюция — RETRY (re-arm), иначе `RECOVERY_RESOLUTION_REQUIRED`. Stale RETRY, REJECTED, ADOPT и ROLLBACK authority не дают.

**CAS на границе мутации** (`mutation_boundary` — context manager; `POST …/claim/authorize` — его вызов с пустым телом). Проверки по порядку:
1. Активный claim принадлежит этому op. Иначе `NOT_OWNER` / `NO_ACTIVE_CLAIM` / `CLAIM_RELEASED`.
2. `claim_id` совпадает, если передан.
3. Запрошенная ревизия равна текущей.
4. Ревизия claim равна текущей (иначе `CLAIM_BASIS_STALE`).
5. `target_key` и `cas_basis` совпадают с контрактом.
6. Повторная проверка допустимости.
7. Наблюдаемые байты цели равны `cas_basis` (иначе `STATE_DRIFT`; внешнее изменение не перезаписывается).

Результат AUTHORIZED / DENIED сохраняется в `claim.authorizations`. Это audit-evidence: id дедуплицирован, повтор ничего не дублирует.

**Mutation authority существует только внутри блока `with`**, пока держатся обе блокировки. `authorize()` возвращает `mutation_authority=false`, `authorized=true|false`: это факт проверки, а не разрешение на будущее. Ранее созданный claim или прошлая авторизация не доказывают безопасность мутации.

**Release** (`POST …/claim/release`):
- освободить может только владеющий op; чужой получает `REJECTED / NOT_OWNER`, а без claim — `NO_CLAIM`;
- повтор после освобождения → `REPLAYED / ALREADY_RELEASED`;
- файлы не трогаются; timeout, disconnect и смерть процесса claim не освобождают;
- **страховка:** если операция в STARTED / UNKNOWN_AFTER_DISCONNECT (судьба мутации открыта), release отклоняется (`RELEASE_REQUIRES_RECOVERY_OUTCOME`), пока Resolver не закроет окно fresh accepted ADOPT или accepted ABORT. INTENT, DONE, VERIFIED и FAILED освобождаются свободно.

**Inspect** (`GET …/claim`, без записи). Показывает:
- цель, `target_hash`, `physical_key`;
- `active_claim`, все claims этой операции;
- `owned_by_operation`, `blocking_owner` — почему конфликтующий op заблокирован;
- `cas_preview` — прошёл бы сейчас CAS.

Для legacy возвращается `DENIED / LEGACY_CONTRACT`.

**HTTP:**
- acquire: 201 ACQUIRED / REBASED, 200 REPLAYED;
- authorize: 200 AUTHORIZED;
- release: 200 RELEASED / REPLAYED;
- остальное — 409 `claim_<result>`, полный outcome в `details`;
- 400 `invalid_claim_request`, 409 / 404 `target_claim_error`;
- capability `target_claims`.

## 3. ИЗМЕНЁННЫЕ ФАЙЛЫ

| Файл | Изменение |
| --- | --- |
| `web_alarm/target_claim_store.py` | **новый**, 265 строк — модель, валидация, атомарное хранилище, `physical_target_key`, `target_hash` |
| `web_alarm/target_claim_service.py` | **новый**, 601 строка — acquire / `mutation_boundary` / authorize / release / inspect, допустимость, блокировки, события |
| `web_alarm/server.py` | +60 — маршруты `…/operations/<op>/claim[/authorize|/release]`, маппинг ошибок, capability |
| `web_alarm/__init__.py` | +7 — экспорт |
| `test_web_alarm_target_claims.py` | **новый**, 18 тестов |
| `test_web_alarm_target_claims_concurrency.py` | **новый**, 2 межпроцессных теста |

Safety copies `server.py` и `__init__.py` + `baseline.md` (SHA-256, HEAD) — в `safety_copies/`.

## 4. VERIFICATION (acceptance §«Минимальный acceptance RC-3»)

| № | Критерий | Тест / проверка | Результат |
| --- | --- | --- | --- |
| 1 | Basic acquire | `test_basic_acquire_creates_one_persistent_owner` — ровно один persistent owner, файл по hash, байты проекта без изменений | PASS |
| 2 | Replay | `test_replay_returns_same_claim_without_duplicate_effect` — тот же claim, `next_generation=2`, история пустая, одно событие | PASS |
| 3, 4 | Конфликт в той же TASK и между TASK | `test_same_task_and_cross_task_operations_conflict` — CONFLICT с владельцем; inspect у заблокированного показывает `blocking_owner`, `cas_preview=NOT_OWNER` | PASS |
| 5 | Разные цели | `test_different_targets_do_not_conflict` + гонка 8 процессов на 8 целей: все ACQUIRED | PASS |
| 6 | Canonical identity | `test_equivalent_spellings_share_one_conflict_identity` — `./`, `\`, абсолютный путь, другой регистр, junction-алиас, **вложенный workspace** (`nested.txt` vs `sub/nested.txt`) → CONFLICT, один файл claims | PASS |
| 7 | Устаревшая ревизия | `test_stale_operation_revision_gets_no_authority` — авторизация на старой ревизии → `OPERATION_REVISION_CHANGED`; на новой при claim со старого basis → `CLAIM_BASIS_STALE` | PASS |
| 8 | Физический дрейф | `test_physical_drift_after_acquire_fails_closed_without_overwrite` — acquire → внешняя запись → CAS `STATE_DRIFT`, внешние байты сохранены; дрейф до acquire → `STALE` | PASS |
| 9, 10 | Release чужим и повторный release | `test_wrong_owner_cannot_release_and_release_replay_is_idempotent` | PASS |
| 11 | После release | `test_after_release_other_operation_acquires_only_on_fresh_basis` — другой op берёт цель (generation 2); после дрейфа новый op получает `STATE_DRIFT`; запоздавший дубль бывшего владельца цель не захватывает | PASS |
| 12 | Падение и рестарт | `test_claim_survives_process_death_and_restart` — процесс захватывает цель и делает `os._exit` без release; свежий процесс видит тот же claim, владельца, ревизию, `cas_preview` и `blocking_owner` у конкурента | PASS |
| 13 | Legacy v1 | `test_legacy_contract_cannot_acquire_or_authorize` — отклонено, файла claims нет, legacy JSON побайтно цел | PASS |
| 14 | Неполный v2 | `test_incomplete_or_corrupt_payload_contract_cannot_acquire` — `CONTRACT_INSUFFICIENT`, `PAYLOAD_INTEGRITY_FAILURE` | PASS |
| 15 | Интеграция с Resolver | `test_resolver_state_never_grants_false_authority`: без резолюции и с REJECTED → отказ; fresh RETRY → claim → AUTHORIZED, но re-arm без claim → `NO_ACTIVE_CLAIM`; RETRY устарел → CAS отказывает, release заблокирован; ABORT → CAS `RECOVERY_ABORTED`, release разрешён, повторный захват не даёт нового claim. `test_aborted_operation_cannot_take_a_free_target`, `test_rollback_request_is_not_mutation_authority` | PASS |
| 16 | Межпроцессная гонка | `test_cross_task_race_on_one_target_has_exactly_one_owner` — 8 процессов из разных TASK на одну цель: ровно 1 ACQUIRED, 7 CONFLICT, все указывают на победителя, хранилище валидно. **5/5 прогонов.** **Чувствительность** (scratchpad): по 5 раундов с блокировкой и без — с ней 1 / 7 каждый раз, без неё 4–5 процессов одновременно считают себя владельцами (остальные падают на конкурентном `os.replace`) | PASS |
| 17 | Полная регрессия | `python -B -m unittest test_web_alarm_*.py` | **286/286 OK** (skip 1), 33,5 с |
| 18 | `python -B -m compileall -q web_alarm` | | OK |
| 19 | `git diff --check` | По всем изменениям, кроме `000_Задачи Claude.md`, — OK. В `000_Задачи Claude.md` срабатывают только **хвостовые пробелы в тексте БЛОКА 1 от пользователя** (markdown hard-break, `Статус:␠␠` и т. п.). Чужой текст не трогал, мои блоки чисты | OK для работы RC-3 |
| 20 | Нет физической мутации | Хеши всех файлов проекта до и после acquire / authorize / release совпадают (тесты 1, 2, CAS, server); живое storage WEB-02 (read-only inspect legacy `WA37-CTRL-002`): дерево `88fc4f99…4149`, 136 файлов — без изменений | PASS |
| — | RC-2 не сломан | `test_web_alarm_resolver*`, `test_web_alarm_operation_store_concurrency` | OK |

Дополнительно: `test_executor_flow_boundary_then_lifecycle_then_release` моделирует порядок WA4-E. Запись внутри boundary делает сам тест, а не RC-3. Release отклоняется, пока операция в STARTED, и проходит после DONE. `test_server_claim_endpoints` — все HTTP-коды и маршруты.

## 5. РЕШЕНИЯ ВНУТРИ SCOPE — на внимание проверяющему

1. **Физическая identity** (абсолютный resolved path), а не `target_key` RC-1. Иначе вложенные workspace обходили бы gate.
2. **Допустимость операции не в INTENT** требует свежий accepted RETRY. Карточка требует, чтобы stale / rejected / aborted не давали authority, а re-arm сам не был authority. Это минимальное правило, которое выполняет оба требования.
3. **Страховка release для STARTED / UNKNOWN.** Карточка разрешает release владельцем без условий, но требует, чтобы неизвестность после crash оставалась fail-closed до reconciliation или явного безопасного действия. Поэтому release в таких статусах ждёт ADOPT или ABORT от Resolver. Правило детерминировано и не вводит lease. **Если проверяющий сочтёт его лишней политикой**, оно снимается удалением одной проверки `_release_refusal`.
4. **Повтор того же basis после release** не захватывает цель снова. Операции нужна новая ревизия, через RETRY re-arm и `REBASED`; иначе — новая операция.
5. **Rebase владельцем.** Свой claim на старой ревизии переносится на новую атомарно, через `SUPERSEDED`. Без этого сценарий RETRY после обрыва упирался бы в запрет release для STARTED.
6. **Authorization сохраняется как evidence,** а authority существует только внутри `mutation_boundary`.

## 6. ГРАНИЦЫ И ЗАМЕТКИ ДЛЯ WA4-E (не входят в RC-3)

- **Внешние писатели** (Obsidian, редакторы, git) gate не проходят. CAS ловит их изменения **до** записи, но не может запретить запись ОС между CAS и записью executor. Это ловит receipt при DONE из RC-1.
- **`mutation_boundary` держит блокировку TASK.** `OperationStore.transition` берёт ту же блокировку новым handle, поэтому **внутри boundary его вызывать нельзя**: это self-deadlock до таймаута. WA4-E понадобится вариант перехода «блокировка уже взята» или порядок «CAS+write → выход → переход». Тест executor-flow фиксирует текущий порядок.
- **Orphan-owner policy не вводилась** (V17). Брошенная операция в STARTED блокирует цель, пока Resolver не закроет её через ADOPT или ABORT; в INTENT владелец освобождает цель сам. Это намеренно fail-closed.
- **Нужна ли проверка claims в `OperationStore.transition`** (например, STARTED только после AUTHORIZED) — вопрос строгого gateway (WA4-E / WA4-R), не RC-3.
- История claims на цель растёт без очистки — retention RC-фазы. Каталог `locks/targets/` пополняется маленькими lock-файлами.
- **Rollout:** старый код не знает маршрутов `/claim`; после принятия перезапустить процессы WEB-02 (сейчас не запущены).

## 7. CLOSEOUT

- `000_Задачи Claude.md`: постановка из БЛОКА 1 скопирована в БЛОК 2 — в fenced-блок, чтобы сохранить разбивку строк без хвостовых пробелов, — итог записан в БЛОК 3. **БЛОК 1 не изменён** (сверено побайтно).
- `001`, `06`, `25` и прочие канонические документы не менялись: их после PASS синхронизирует проверяющий.

## 8. NEXT SAFE ACTION

Независимая проверка RC-3 (ChatGPT / пользователь). RC-4 не начинать.
