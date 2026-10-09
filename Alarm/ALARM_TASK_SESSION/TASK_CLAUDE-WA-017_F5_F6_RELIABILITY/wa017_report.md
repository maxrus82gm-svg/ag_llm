# CLAUDE-WA-017 — F-5 / F-6 Reliability Repair — отчёт исполнителя

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локально. **Дата:** 2026-10-09.
**Постановка:** БЛОК 1 карточки; запуск подтверждён пользователем («сразу можешь приступать»).
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. F-5 / F-6 не отмечены DONE / VERIFIED. Статусы RC-0…RC-6 не менялись. WA4-E не начат. Commit / push не выполнялись.
**Baseline:** HEAD = `origin/main` = `d53ec140a41ea879e6ea14610fd53a2c8da71554` (173, WA-016 принят); код и тесты равны HEAD. Полный набор — **593 OK, skip 1**.

## 1. F-5 — crash-safe завершение TASK

### 1.1 Воспроизведение до исправления

Проба `probes/f5_completion_crash.py`, временное storage. Дочерний процесс закрывает чистую TASK через gate (`CloseoutService.complete`) и убивается `os._exit(9)` внутри `TaskStore.complete_task_locked`.

| Точка смерти | Результат (код `d53ec14`) |
| --- | --- |
| после записи статуса COMPLETED, до переноса | TASK в `active/` со статусом COMPLETED; RemoteEntry считает её активной; **`OperationStore.begin` принят** (`op_late` записана в закрытую TASK); **rebuild checkpoint принят**; повторный публичный `complete` → REJECTED (`TASK_NOT_ACTIVE`), состояние не сходится никогда |
| до переноса | то же (в старом порядке статус уже записан) |

Тот же «застрявший» вид давал и путь без смерти процесса: перенос падает (на Windows — из-за открытого файла в каталоге), а откат статуса тоже не удаётся записать.

**Инвариант «закрытая TASK не получает mutation authority» был нарушен.** Отдельная проба во временном storage, закреплено тестом `ClosedTaskAuthorityTests`, который на коде до исправления даёт 3 из 3 FAIL:
- RC-3 `mutation_boundary` / `authorize` не проверяли, закрыта ли TASK;
- операция закрытой TASK с ACTIVE-этапом и удерживаемым claim получала `AUTHORIZED / CAS_BASIS_HOLDS, mutation_authority=True`;
- это так и после закрытия публичным ungated-примитивом `TaskStore.complete_task`, и в форме краша «статус записан, каталог не перенесён».

Gated closeout сам по себе такую TASK не закрывает (все этапы VERIFIED, нет claims), но гарантия не может зависеть от того, каким путём TASK закрыли.

### 1.2 Исправление

1. **`task_store.py`:**
   - **Коммит-точка закрытия — атомарный перенос каталога** `active/` → `completed/`; статус COMPLETED пишется после неё. Неудачный перенос не меняет ничего (отката статуса больше нет).
   - `completion_state` (чистая функция): `ACTIVE`, `COMPLETED`, `MOVED_STATUS_PENDING` (перенос был, статус не записан), `STATUS_WRITTEN_NOT_MOVED` (форма краша кода до WA-017).
   - `complete_task_locked` идемпотентно доводит незавершённое закрытие.
   - **Центральный гейт писателей:** `task_directory(active_only=True)` и `microtask_directory(active_only=True)` отказывают и TASK с закрытым статусом в `active/`. Через эти точки идут все store: операции, Resolver, RC-4, манифест / restore point, reconciliation, rebuild checkpoint. Лишнего чтения нет: `task.json` и так читался.
2. **`closeout.py`:** `complete` доводит незавершённое закрытие.
   - После переноса (`MOVED_STATUS_PENDING`) остаётся только записать статус: коммит-точка пройдена, доказывать нечего.
   - Форма кода до WA-017 переносится только после **повторного доказательства gate**, без учёта самого закрытого статуса. Ответ получает `resumed`, событие `TASK_COMPLETED` — `resumed`.
3. **`microtask_gate.execution_refusal`** (общий гейт RC-3 `mutation_boundary` и READY RC-6): закрытая TASK → `TASK_CLOSED` в любой форме. Изменение RC-6-модуля обосновано доказанным нарушением обязательного инварианта (§1.1); семантика для активных TASK не меняется.
4. **`projection.py`:** диагностика `INTERRUPTED_COMPLETION` и NEXT «…the TASK is closed and read-only history: finish its completion record with the gated `task complete`».
5. **`remote_entry.py`:** TASK с закрытым статусом не кандидат на вход и не ломает выбор единственной активной TASK.

Схема хранения не менялась: те же файлы и поля, другой порядок записи.

### 1.3 Доказательства после исправления

| Сценарий | Результат |
| --- | --- |
| Смерть после переноса (реальный `os._exit`) | `completed/`, статус PLANNED → TASK закрыта; все писатели отказывают; RemoteEntry её не видит; RC-6 → `TASK_COMPLETED`; закрытие **свежим процессом** → `COMPLETED, resumed=MOVED_STATUS_PENDING`; повтор → REJECTED |
| Смерть до переноса | ни один байт `task.json` не изменился, TASK активна, закрытие свежим процессом → COMPLETED |
| Смерть после записи статуса | закрытие уже завершено, повтор → REJECTED |
| Перенос отклонён ОС (PermissionError) | `CloseoutError`, ничего не записано, TASK активна; повтор → COMPLETED |
| Запись статуса после переноса упала | TASK закрыта для писателей; следующий `complete` → `resumed=MOVED_STATUS_PENDING` |
| Форма до WA-017 (статус в `active/`) | все писатели отказывают; RemoteEntry выбирает другую активную TASK; `complete` повторно доказывает gate и переносит. Если старые писатели успели добавить открытую операцию → REJECTED (`OPERATION_OPEN`), TASK не переносится и остаётся закрытой для писателей |
| Mutation authority у закрытой TASK (ungated-примитив / статус ожидается / статус в `active/`, этап ACTIVE + claim) | `DENIED / TASK_CLOSED`, `mutation_authority=False` во всех трёх формах |
| Гонка в реальных процессах: закрытие умирает сразу после коммит-точки, параллельно 2× `begin` + `create_microtask` (×4 раунда) | если закрытие успело — в закрытую TASK не попало ничего, все писатели FAILED, повторный `complete` доводит; если первым был писатель — gate отклонил, TASK активна |
| Повторный closeout | REJECTED (`TASK_NOT_ACTIVE`), без записи |

## 2. F-6 — гонка rebuild checkpoint на Windows

### 2.1 Диагностика

- **Сигнатура WA-016.** `read_checkpoint` после гонки X: «checkpoint is missing».
  - В X первый checkpoint создаёт **только** rebuild-процесс: `_touch_checkpoint` лишь обновляет существующий.
  - Значит, сигнатура = «rebuild-процесс упал».
- **Целевые повторы.** 340 раундов сценария X (WA-016 — 140, WA-017 — 200 в 4 параллельных потока на замороженном коде HEAD) с полной трассировкой дочерних процессов — **0 сбоев**. Случай редкий, зависит от среды.
- **Механизм доказан на этой машине (Windows) детерминированно:**
  - пока другой процесс держит `checkpoint.json` открытым (так делают антивирус и индексатор), `os.replace` → `PermissionError [WinError 5]` → `EventCheckpointStoreError` → `ProjectionError`;
  - старые байты целы, временный файл удалён, валидация STALE, после освобождения файла rebuild → VALID.
- **Воспроизведение сигнатуры.** Принудительный отказ replace у rebuild-процесса в гонке X → `FAILED:ProjectionError`, checkpoint `MISSING`. **Старый контракт теста X падает ровно с `EventCheckpointStoreError: checkpoint is missing`**.
- **Вывод.** Реализация уже была fail-closed: ни потери данных, ни ложного VALID. Дефект — в контракте теста: он требовал, чтобы rebuild в гонке всегда удавался.

### 2.2 Исправление (контракт теста; реализация не менялась)

`test_web_alarm_projection_concurrency.py`, тест X:
- фиксирует исход каждого дочернего процесса;
- единственный допустимый отказ rebuild — `FAILED:ProjectionError`;
- `REBUILT` без checkpoint = потеря данных → FAIL;
- отсутствие checkpoint допустимо только при проваленном rebuild и с валидацией `MISSING`;
- при наличии checkpoint `VALID ⇔` (тот же source basis, те же поля **и** согласованный `checkpoint.md`), то есть «никогда ложный VALID» вместе с Markdown;
- допустимые статусы — VALID / STALE / INCONSISTENT; финальный rebuild → VALID.

Новый детерминированный тест `test_a_failed_rebuild_in_the_race_fails_closed_and_loses_nothing` прогоняет ту же гонку с принудительным отказом.

### 2.3 Доказательства инварианта «никогда VALID»

`CheckpointRebuildFailureTests`:
- проваленный первый rebuild → нет файла, нет `.tmp`, `MISSING`, затем VALID;
- проваленный rebuild поверх прежнего checkpoint:
  - отказ JSON → оба файла побайтно прежние, STALE;
  - отказ Markdown → INCONSISTENT;
- матрица повреждений, `authoritative=false` везде, NEXT подделкой не управляется:
  - JSON удалён → MISSING;
  - пустой, обрезанный, не объект, неизвестная схема → CORRUPT;
  - подменён NEXT, удалён или подменён `.md` → INCONSISTENT;
  - снята база → LEGACY_UNVALIDATED;
- **реальная Windows sharing violation** (второй процесс держит файл) → `ProjectionError` с `PermissionError` в цепочке, байты целы, STALE, затем VALID.

## 3. Тесты и проверки

- **Новый модуль `test_web_alarm_reliability_wa017.py`** — 13 тестов: крэш / рестарт / повторный closeout / гонка F-5, полномочия, форма до WA-017, F-6.
- **Изменён `test_web_alarm_projection_concurrency.py`:** контракт X и новый тест отказа rebuild.
- **Чувствительность на коде до исправления** (новый модуль с заглушками имён):
  - **F-5:** все тесты падают — `AUTHORIZED` вместо `DENIED/TASK_CLOSED` (×3), старый порядок оставляет COMPLETED до переноса, нет `completion_state`, нет `resumed`. Проходит только тест отказа переноса без краша: этот путь старый код откатывал.
  - **F-6:** 4 теста проходят и до исправления — подтверждение, что реализация уже была fail-closed.
- **Итоги прогонов:** см. §3.1.

### 3.1 Итоговые прогоны

| Проверка | Результат |
| --- | --- |
| Baseline (`d53ec14`, до правок) | 593 OK, skip 1 |
| Новый модуль WA-017 | 13 / 13 |
| `test_web_alarm_projection_concurrency` (W, X, rebuilders, новый X-fail) | 4 / 4 |
| Фокусно 31 модуль: WA-017, task_store, projection ×3, remote_entry, target_claims ×2, cli, server, state_machine ×2, context_pack, restart, rollback ×2, operation_store ×2, resolver, manifest, event_checkpoint, recovery_coordinator ×10 | **442 OK** |
| Полный набор (50 модулей), прогон 1 | **607 OK, skip 1** |
| Полный набор, прогон 2 | **607 OK, skip 1** |
| Стресс: `CompletionCrashRaceTests` + W / X / X-fail / rebuilders + гонки closeout WA-016, 8 проходов | **8 / 8** |
| Пробы F-5 после исправления | все окна смерти сходятся (§1.3) |
| `compileall`, `git diff --check`, LF / хвостовые пробелы | OK |
| Живое storage | только чтение: 136 / 41, хеш до = после (`5961c00c…7cd2`); WA-3.6 / WA-3.7: `completion_state=COMPLETED`, NEXT read-only, диагностик нет; RemoteEntry `[]` |

## 4. Оставшиеся ограничения

- **Legacy-форма с данными старых писателей.** Если до обновления процессы старого кода успели записать открытую операцию в «закрытую по статусу» TASK, `complete` её не переносит (REJECTED). Нужен ручной разбор; писатели при этом заблокированы.
- **`TargetClaimService.acquire`** (RC-3) для операции уже закрытой TASK не проверяет её закрытость. Это владение, а не полномочие: authorize даёт `TASK_CLOSED`. Через gated closeout такая операция в закрытой TASK невозможна (`OPERATION_OPEN` / `ACTIVE_CLAIM`). Не исправлялось: RC-3 вне scope без доказанной необходимости.
- **Перенос каталога на Windows** отклоняется, если файл внутри TASK открыт другим процессом (например, lock-free читателем projection). Теперь это чистый отказ без записи, повтор закрытия проходит. Раньше это вело к записи и откату статуса.
- **Событие `TASK_COMPLETED`** — история. Если процесс умер после записи статуса, но до события, события нет: так было и раньше, флаг `event_recorded`.
- **Источник реального сбоя WA-016** (чей именно handle) не пойман: 340 раундов без повтора. Доказан класс механизма; реализация fail-closed.
- **`server._list_tasks`** перечисляет форму до WA-017 в `active` со статусом COMPLETED. Косметика, не исправлялась.
- **F-1 / F-3** не трогались.

## 5. Влияние на WA4-E

- Executor WA4-E обязан получать полномочие только внутри RC-3 `mutation_boundary`; теперь гейт там же отказывает закрытой TASK (`TASK_CLOSED`) независимо от этапов и claims.
- STARTED-before-write (`OperationStore.transition`) и все записи WA4-E идут через `active_only`-гейт — закрытая по каталогу или по статусу TASK их отвергает.
- Коммит-точка закрытия — перенос каталога. WA4-E не должен держать открытыми файлы внутри каталога TASK в момент закрытия (на Windows это вызовет чистый отказ закрытия). Закрытие и запись WA4-E сериализованы TASK-lock.
- Сбой rebuild checkpoint для WA4-E не фатален (`_touch_checkpoint` уже проглатывает). Checkpoint никогда не authority.
- **PROPOSAL (WA4-R / hardening):** ограниченный повтор атомарной записи при Windows sharing violation во всех store — снизит транзиентные отказы. Безопасность от этого не зависит.

## 6. Documentation impact

- **ARCHITECTURE IMPACT — YES** после независимой проверки:
  - `23` — коммит-точка закрытия TASK = перенос каталога; закрытая TASK (каталог или статус) не принимает писателей и не даёт mutation authority; контракт checkpoint при неудачном rebuild;
  - `24` / `25` — статус F-5 / F-6.
- Канонические документы обновляет verifier.

## 7. Файлы

- Изменены:
  - `web_alarm/task_store.py` (+64 / −20);
  - `web_alarm/closeout.py` (+24 / −3);
  - `web_alarm/microtask_gate.py` (+11 / −1);
  - `web_alarm/projection.py` (+16);
  - `web_alarm/remote_entry.py` (+3 / −1);
  - `test_web_alarm_projection_concurrency.py` (+51 / −23);
  - `Документация/000_Задачи Claude.md` (ротация).
- Новые:
  - `test_web_alarm_reliability_wa017.py`;
  - `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-017_F5_F6_RELIABILITY/wa017_report.md`;
  - `…/probes/f5_completion_crash.py`.
- Safety-копий и логов в Git нет: baseline — Git HEAD, сырые выводы — во временной папке.

**NEXT:** commit / push пользователем → независимый GitHub-аудит ChatGPT → только затем F-5 / F-6 DONE / VERIFIED и обновление `23` / `24` / `25`.
