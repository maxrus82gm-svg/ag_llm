# CLAUDE-WA-018 — WA4-E / Authoritative Mutation Executor & Gateway — отчёт исполнителя

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локально. **Дата:** 2026-10-09.
**Постановка:** БЛОК 1 карточки Claude («USER APPROVED FOR EXECUTION»; запуск подтверждён пользователем в чате).
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE / VERIFIED. WA4-A / WA4-O / WA4-R не начаты. Commit / push не выполнялись.

## 1. Preflight

- **Git:** `main`, HEAD = `origin/main` = `3b5ab323446c16cacadf9ce2c796af8b8d75c85a` (176); код и тесты = принятый `c7681c3` (174). Baseline — 607 OK, skip 1.
- **Грязное дерево до старта — не мои изменения:**
  - БЛОК 1 карточки Claude (постановка);
  - параллельная документационная работа Codex `CODEX-DOC-034-GRAPH-001` — `000_Задачи Codex.md`, `00`, `08`, `34`;
  - `.obsidian/*`.

  Эти файлы не трогались, кроме минимальной дельты в `34` на строках, которые Codex не менял (§7).
- **Маршрут:** `08` → глобальный `000` → `34` → `18` → `01`; `23`, `24`, `33` (RT-001), `25` — по WA4-E.
- **Глобальный `000`, БЛОК 1:** отражены активная TASK, исполнитель и маршрут к карточке Claude (+3 / −2); подтверждённая история и отложенный БЛОК 3 (151C) не тронуты.
- **Наблюдения:**
  - в постоянной истории `001` нет записей WA-015…017 (синхронизирует verifier после PASS);
  - устаревшие CURRENT-статусы: `24`, шапка — «RC-5 … independent review DEFERRED»; `04`, строка 69 — «RC-5 … DEFERRED; WA4-E NOT STARTED». На деле RC-5 DONE / VERIFIED. Не исправлялись — это синхронизация verifier.

**Карта точек интеграции (существующий canonical API, новых слоёв нет):**

| Звено цепочки | Компонент |
| --- | --- |
| durable contract, `operation_id`, fingerprint, revision, payload | RC-1 `OperationStore.begin`, `operation_contract`, `PayloadStore` |
| canonical target (`..`, symlink / junction, регистр Windows, ADS, устройства) | RC-1 `target_identity.canonical_target`, RC-3 `physical_target_key` |
| restore point / manifest | `ManifestSnapshotStore.restore_plan` (чистая проверка целостности) |
| ownership | RC-3 `TargetClaimService.acquire` |
| authority + CAS | RC-3 `mutation_boundary` (TASK lock → mutation lock → target lock; `_cas`; `microtask_gate.execution_refusal`, включая TASK_CLOSED из WA-017) |
| STARTED / DONE + receipt | RC-1 transition (+ новый lock-held путь `_transition_locked`) |
| неизвестный исход | RC-2 reconciliation + Resolver (ADOPT / RETRY / ROLLBACK / ABORT), RC-6 `recover`, RC-4 rollback |
| projection / closeout | RC-5 (без изменений) |

## 2. Что реализовано

**`web_alarm/mutation_executor.py`** (новый), класс `MutationExecutor.execute(task, microtask, operation_id, action, target, …)`.

1. **INTENT.**
   - `operation_id` обязателен: это ключ идемпотентности, без него повтор был бы новой операцией.
   - RC-1 `begin`: новый durable contract или тот же при повторе; изменённый запрос → `OPERATION_ID_CONFLICT`.
   - DELETE без объявленного состояния получает явное post-state «отсутствует», иначе RC-1 считает контракт неполным.
2. **Admission до границы.**
   - Тип операции известен; контракт полный.
   - Payload прочитан с проверкой hash + size — **до STARTED**.
   - Цель входит в VERIFIED restore point своей микрозадачи (`TARGET_NOT_IN_MANIFEST` / `RESTORE_POINT_NOT_VERIFIED`): исполняется только то, что RC-4 умеет откатить.
3. **Ownership.**
   - RC-3 claim: CONFLICT → `TARGET_OWNED`; дрейф pre-state → `PRECONDITION_FAILED`.
   - Повторный захват уже освобождённого basis → `CLAIM_ALREADY_RELEASED`.
4. **Граница RC-3 `mutation_boundary`** — authority только внутри неё:
   - заново доказываются claim / revision / контракт / байты pre-state;
   - F-C gate: TASK не закрыта, этап ACTIVE и lifecycle-current, нет ABORT / ROLLBACK.

   Внутри:
   - повторная проверка manifest;
   - **STARTED через `OperationStore._transition_locked` под уже удерживаемым TASK-lock** (публичный `transition` ждал бы тот же нереентерабельный lock); если STARTED не записан — `STARTED_NOT_PERSISTED`, **ничего не пишется**;
   - физическая запись:
     - WRITE / edit — temp + fsync + `os.replace`;
     - CREATE и WRITE отсутствующего файла — temp + `os.link` (на Windows без жёстких ссылок — `os.rename`, который не заменяет существующий файл): **никогда не перезаписывает** появившийся файл;
     - DELETE — unlink;
   - **RC-1 DONE под теми же locks = exact post-proof и persisted receipt:** сервер перечитывает байты и сравнивает их с контрактным post-state; несовпадение → операция остаётся STARTED.
5. **После границы:** release claim. Отказ границы до STARTED оставляет claim за операцией (модель RC-3: владение принадлежит логической операции до её завершения), и повтор продолжается.
6. **Replay и неизвестный исход:**
   - DONE / VERIFIED → тот же receipt (`REPLAYED`), в том числе для закрытой TASK (`_closed_replay`: только чтение и проверка fingerprint) и для одновременной двойной доставки;
   - STARTED / UNKNOWN → `RECONCILIATION_REQUIRED` + решение reconciliation (чистое) и NEXT через RC-2 / RC-6; **вслепую не повторяется**;
   - авторитетный свежий RETRY операции в STARTED исполняется заново через ту же границу и CAS;
   - RETRY операции UNKNOWN → `RETRY_LIFECYCLE_UNSUPPORTED` (§6).
7. **move / rename** (`24`, WA-4.2 — без новой схемы):
   - две операции `<id>.delete-source` (объявляется первой и фиксирует байты источника) и `<id>.create-destination` (CREATE с ровно этими байтами);
   - обе цели под claims **до первой записи**; затем шаг 1, затем шаг 2;
   - rename не меняет каталог;
   - один физический файл (в том числе смена только регистра на Windows) → `SAME_PHYSICAL_TARGET`;
   - пара не атомарна: прерывание или чужое изменение источника между шагами → честный `PARTIAL` с NEXT (повтор продолжает с шага 2 или откат через RC-2 / RC-4);
   - повтор после завершения → `REPLAYED`.

**Изменения существующих модулей:**
- `operation_store.py`: `transition` = обёртка над новым `_transition_locked`; тело не изменилось, только сдвинуто на уровень (+96 / −80 по diff);
- `server.py`: `POST /tasks/{id}/mutations` (200 EXECUTED / REPLAYED, 409 с полными деталями) и capability `mutations`;
- `cli.py`: команда `mutate` (выход 0 / 3 / 2);
- `__init__.py`: экспорт.

RC-2 / RC-3 / RC-4 / RC-5 / RC-6 не менялись.

## 3. Доказательства безопасности

| Гарантия | Доказательство |
| --- | --- |
| STARTED до первой записи | в момент вызова записи другой экземпляр OperationStore читает с диска `STARTED`, а цель ещё в pre-state (`test_started_is_persisted_before_the_first_physical_write`); реальная смерть процесса до STARTED → INTENT, байты не тронуты, повтор исполняет один раз; отказ записи STARTED → ничего не записано |
| snapshot / manifest / CAS | цель вне manifest; испорченный snapshot; дрейф pre-state; путь вне корня — везде REFUSED, байты не изменены; разные написания одного пути → одна физическая цель (`TARGET_OWNED`) |
| replay без второго эффекта | повтор в процессе и в свежем процессе, двойная одновременная доставка (реальные процессы ×4), повтор после закрытия TASK — тот же receipt, счётчик записей 0, событие `MUTATION_EXECUTED` ровно одно |
| exact post-proof | подменённые байты → `POST_PROOF_FAILED`, receipt нет, STARTED; без проверки post-proof соответствующий тест падает (§4) |
| 4 окна краша (реальный `os._exit`) | до STARTED → исполняется при повторе; после STARTED, до записи → `RECONCILIATION_REQUIRED` (RETRY_SAFE) → RETRY → исполнено; после записи, до receipt → reconciliation `ADOPT_CURRENT_STATE` → ADOPT + `recover` → VERIFIED, второй записи нет; после receipt (ответ потерян) → `REPLAYED` с тем же receipt, ownership освобождается при повторе |
| гонки | два executor на одну физическую цель (разное написание) — ровно один EXECUTED, итоговые байты победителя (×4); исполнение против закрытия TASK — запись в закрытую TASK невозможна (×4) |
| Windows | реальное нарушение совместного доступа (чужой открытый handle) → `WRITE_REFUSED_TARGET_UNCHANGED`, байты целы, receipt нет — фиктивного SUCCESS нет |
| совместимость | RC-4 откатывает исполненную запись (ROLLBACK → VERIFIED, байты = snapshot); RC-6 после исполнения снова `READY_FOR_EXECUTION` (лишнего владения нет); многоцелевая микрозадача восстанавливает прерванную запись через ROLLBACK; HTTP и CLI |

## 4. Тесты

- **Новый `test_web_alarm_mutation_executor.py`** — 36 тестов:
  - `PositiveTests` 5;
  - `AdmissionTests` 10;
  - `FailureTests` 5;
  - `SingleTargetRecoveryTests` 3;
  - `CrashWindowTests` 4;
  - `RaceTests` 3 (реальные процессы);
  - `CompatibilityTests` 6.
- **Чувствительность:** по одной в памяти отключались защиты — STARTED-before-write, гейт manifest, CAS pre-state, create-if-absent, exact post-proof. Каждое отключение ловится: 2 / 2, 1 / 1, 1 / 1, 2 / 2, 1 / 1 FAIL.
- **Прогоны** — §4.1.

### 4.1 Итоговые прогоны

| Проверка | Результат |
| --- | --- |
| Baseline (`3b5ab32`, до правок) | 607 OK, skip 1, exit 0 |
| Новый модуль | **36 / 36 OK** (до и после перевода файла в LF) |
| Фокусно 32 модуля: executor, operation_store ×2, operation_contract, target_claims ×2, rollback ×2, projection ×3, WA-017, resolver ×2, reconciliation integration, server, cli, state_machine ×2, task_store, manifest, payload, recovery_coordinator ×10 | **492 OK**, exit 0 |
| Полный набор (51 модуль), прогон 1 | **643 OK, skip 1**, exit 0 |
| Полный набор, прогон 2 | **643 OK, skip 1**, exit 0 |
| Стресс: executor `RaceTests` + `CrashWindowTests` + RC-5 W/X + WA-017 crash race + RC-3 concurrency, 6 проходов | **6 / 6 OK** |
| Чувствительность (5 отключённых защит) | все пойманы |
| `compileall`, `git diff --check` (код и тесты), LF | OK |
| Живое storage | только чтение: 136 / 41, хеш до = после (`5961c00c…7cd2`) |

## 5. Adversarial pass — найдено и исправлено внутри scope

1. Отказ внутри границы до STARTED не освобождал claim. При первоначальном «исправлении» (release при отказе) операция становилась неисполнимой: RC-3 никогда не отдаёт освобождённый basis повторно. Итоговое решение по модели RC-3: claim остаётся за операцией, повтор продолжается; явный отказ `CLAIM_ALREADY_RELEASED` (тест).
2. Двойная одновременная доставка одного контракта давала второй стороне REFUSED. Теперь при любом отказе по claim или границе операция перечитывается; если она DONE, возвращается тот же receipt (тест на реальных процессах ×4).
3. WRITE отсутствующего файла через `os.replace` мог заменить файл, появившийся в окне. Теперь используется семантика create-if-absent (тест).
4. CREATE внутри окна (внешний писатель после CAS): не перезаписывается, `WRITE_OUTCOME_UNKNOWN` (тест).

## 6. Открытые риски и PROPOSAL (вне scope; код не менялся)

- **P-1 move / rename не атомарны.** Это пара операций; прерывание = PARTIAL. Нативная атомарная move требует двухцелевой схемы Operation Contract (v3) и двухцелевого RC-4 — нужно архитектурное решение.
- **P-2 RETRY после UNKNOWN_AFTER_DISCONNECT / FAILED.** В lifecycle RC-1 из этих статусов нет перехода, исход повтора нельзя записать. Сейчас fail-closed `RETRY_LIFECYCLE_UNSUPPORTED` (NEXT: ABORT + новая операция). PROPOSAL: re-arm переход → STARTED по принятому RETRY — это решение по lifecycle.
- **P-3 RC-2 оценивает RETRY / ADOPT по всему restore point микрозадачи.** В многоцелевой микрозадаче прерванная одиночная запись получает ROLLBACK (весь этап) или MANUAL, а не RETRY / ADOPT. Поведение безопасное, но грубое. PROPOSAL: область evidence на уровне операции (RC-2).
- **P-4 исполненный RETRY остаётся устаревшей «советной» резолюцией.** RC-6 видит у DONE-операции `RESOLUTION_STALE` → MANUAL (класс F-3). Безопасно, но шумно.
- **R-1 окно между CAS и записью.** Защищает от совместимых писателей (target lock + claim), но не от несовместимого внешнего процесса в микросекундном окне: WRITE через атомарную замену может заменить чужую запись, сделанную ровно в этом окне. Post-proof подтверждает только наши байты. CREATE / WRITE отсутствующего файла защищены (без замены). Полное закрытие — WA4-R (strict).
- **R-2 Windows: отказ ОС не повторяется автоматически** (sharing violation → честный отказ, затем RETRY). Повтор с ограничением — PROPOSAL для WA4-R.
- **R-3 CREATE не создаёт каталоги.** Родитель должен существовать (manifest и так этого требует).
- **R-4 размер move ограничен лимитом payload** (`MAX_PAYLOAD_BYTES`).
- **R-5 DONE ≠ VERIFIED:** executor заканчивает на DONE + receipt; переход операции в VERIFIED — отдельный шаг (правило «DONE is not VERIFIED»).
- F-1 / F-3 не трогались.

## 7. Documentation impact

- `23`:
  - статус WA4-E → «RESULT READY / AWAITING INDEPENDENT VERIFICATION»;
  - раздел «WA4-E — authoritative mutation executor (… AWAITING INDEPENDENT VERIFICATION)»: цепочка, replay, ownership, move / rename, PROPOSAL.
- `24`: строка CURRENT UPDATE о WA4-E (не DONE).
- Глобальный `000`, БЛОК 1: активная TASK и маршрут.
- `34`: дельта на строках «Следующий кандидат» и NEXT, которых Codex не касался.
- `001` / `05` / `06` / `25` и итоговый DONE / VERIFIED — verifier после PASS.

## 8. Файлы

- Новые:
  - `web_alarm/mutation_executor.py`;
  - `test_web_alarm_mutation_executor.py`;
  - этот отчёт.
- Изменены:
  - `web_alarm/operation_store.py`, `web_alarm/server.py`, `web_alarm/cli.py`, `web_alarm/__init__.py`;
  - документы `23`, `24`, глобальный `000`, `34`, `000_Задачи Claude.md` (ротация).
- Живое storage только читалось.

**NEXT:** commit / push пользователем → независимый review WA4-E (ChatGPT) → только после PASS отдельная WA4-A.
