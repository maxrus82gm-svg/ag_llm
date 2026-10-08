# CLAUDE-WA-016 — RC-5 Repair #2 / Closeout consistency — отчёт исполнителя

**Исполнитель:** Claude Opus 5.5, Claude Code (desktop), локально. **Дата:** 2026-10-09.
**Основание:** вердикт `CLAUDE-WA-015` (FAIL / CONFIRMED BLOCKER, отчёт `TASK_CLAUDE-WA-015_RC5_FINAL_VERIFICATION/rc5_verification_report.md`). Решение пользователя — полный ремонт A-I + A-II + B; постановка утверждена в чате.
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE / VERIFIED. Статусы RC-5 / RC-6 в канонических документах не менялись. WA4-E не начат. Commit / push не выполнялись.
**Baseline:** HEAD = `origin/main` = `257d5719d3eba07a784450925fc8909ef2311941` (172). Код и тесты равны HEAD и не менялись с `53ec5c3`. Полный набор на baseline — **580 OK, skip 1**.

## 1. Что исправлено

Изменён один production-файл — `web_alarm/projection.py` (+63 / −7). Схема данных, RC-4, RC-6, state machine и Resolver не менялись.

| Пункт | Было | Стало |
| --- | --- | --- |
| A-I | `closeout_blockers` искал буквально `ROLLBACK_ACCEPTED`. С RC-6 R1 (commit 162) принятый ROLLBACK VERIFIED-этапа проецируется как `ROLLBACK_STAGE_PROTECTED`, поэтому TASK закрывалась в обход `RECOVERY_BLOCKED` RC-6 | `ROLLBACK_PENDING` выдаётся и при `protected_state == ROLLBACK_ACCEPTED` |
| A-II | Принятые ABORT / ADOPT считались закрытыми уже по факту принятия Resolver'ом; settlement RC-6 мог так и не случиться | Новый блокер `RECOVERY_SETTLEMENT_PENDING` для `ABORT_ACCEPTED`, `ADOPT_ACCEPTED`, `ABORT_OVER_SETTLEMENT`, `*_SETTLED` с незавершённой администрацией. Блокер `SETTLEMENT_CONTRADICTION` |
| A-II, fail-closed | Неизвестное или новое recovery-состояние проходило gate молча — тот же класс ошибки, что A-I | `RECOVERY_OPEN` для любого recovery-состояния операции, которое не объяснено более точным блокером. Исключения — только советы: свежий `*_REJECTED` и `RESOLUTION_STALE` (правило RC-5 F4 / WA-015 F-3 без изменений) |
| B | `_decide` ставил recovery-фокус и блокеры выше статуса COMPLETED / ARCHIVED | Закрытая TASK (COMPLETED / ARCHIVED или каталог вне `active/`, тот же предикат, что у closeout и RC-6) проверяется первой: NEXT «TASK is … read-only history», `authority_source = task_status`. Recovery-факты, `recovery.attention`, представления операций и сессии остаются диагностикой; при их наличии NEXT прямо называет их историческим evidence |

**Изменение контракта (решено пользователем):** тест `test_aborted_operation_no_longer_blocks` переименован в `test_aborted_operation_blocks_until_rc6_settles_it`. Теперь он ожидает: ABORT принят → `RECOVERY_SETTLEMENT_PENDING` → `recover` (`SETTLE_ABORT`) → `[]`. Позитивный случай после settlement RC-6 сохранён.

## 2. Тесты

Новый модуль `test_web_alarm_projection_repair2.py` — 13 тестов, сценарии через subTest:

- `ProtectedRollbackTests` (A-I):
  - ROLLBACK VERIFIED-этапа в естественном порядке (A7b) и для операции, начатой после VERIFIED (A7): `ROLLBACK_PENDING`, HTTP 409, RC-6 `RECOVERY_BLOCKED`, TASK активна, байты не изменились;
  - выход через явное решение (ABORT) → `SETTLE_ABORT` → закрытие → read-only история.
- `SettlementPendingTests` (A-II):
  - ABORT для STARTED / UNKNOWN / INTENT / VERIFIED-операции блокирует закрытие до `recover`; settlement несёт `microtask_status=VERIFIED`; затем закрытие разрешено;
  - ADOPT блокирует до `SETTLE_ADOPT` (операция становится VERIFIED с receipt);
  - **прерванный settlement:** release claim падает → `FAIL_CLOSED`; этап проверен; closeout `RECOVERY_SETTLEMENT_PENDING` + `ACTIVE_CLAIM`, HTTP 409; **свежий процесс** видит тот же вердикт и `FINISH_SETTLEMENT` → `[]` → закрытие.
- `CloseoutRuleTests` (чистое правило на синтетических projection):
  - противоречивый и незавершённый settlement блокируют;
  - неизвестное состояние → `RECOVERY_OPEN`;
  - REJECTED / STALE у терминальной операции и отсутствие recovery — закрытие разрешено;
  - открытая сессия RC-4 даёт один блокер.
- `HistoricalTaskTests` (B):
  - legacy-фикстуры B1–B5 и неоформленный ABORT, завершённые старым примитивом `TaskStore.complete_task`: NEXT read-only (GET task / context / ui совпадают), `task_status`, attention сохранён, `recover` → `TASK_COMPLETED` с тем же read-only reason;
  - чистая COMPLETED и ARCHIVED: точный старый текст.
- `CloseoutRaceTests` (реальные процессы, барьер старта, ×4 раунда):
  - закрытие против принятия ABORT Resolver'ом: никогда нет «COMPLETED + принятый ABORT»;
  - закрытие против `SETTLE_ABORT` RC-6: «COMPLETED» всегда означает, что settlement записан до закрытия.

**Чувствительность.** На коде до исправления новый модуль даёт 10 из 13 FAIL (21 падение по subTest). Каждое падение — само проявление дефекта: `[] != ['RECOVERY_SETTLEMENT_PENDING']`, `[] != ['ROLLBACK_PENDING']`, `'rollback' != 'task_status'`, в гонках — «unexpectedly None» и «принятый ABORT внутри COMPLETED». Три теста проходят и до исправления: это контроли совместимости (советы на терминальной операции, одна открытая сессия, чистая / ARCHIVED история).

## 3. Проверки

| Проверка | Результат |
| --- | --- |
| Новый модуль + `test_web_alarm_projection` | 60 / 60 OK |
| Фокусно RC-5 / RC-4 / RC-6 + интеграция (26 модулей) | **388 OK** |
| Полный набор (49 модулей, 593 теста) после исправления | прогоны 2 и 3 — **593 OK, skip 1**; прогон 1 — 592 OK + **1 ERROR** в существующем RC-5 тесте гонки X (§3.1) |
| Стресс гонок (`CloseoutRaceTests` + W / X / rebuilders) | **8 / 8** проходов |
| Пробы WA-015 на исправленном коде | A1 / A1u / A1i / A5 / A6: 409 `RECOVERY_SETTLEMENT_PENDING`; A7 / A7b: 409 `ROLLBACK_PENDING`; контроли A2 / A3 / A4 / A8 — как раньше. B1–B5: NEXT read-only, `task_status`. `sensitivity_by_commit` на HEAD: A1 и A7 → REJECTED |
| Adversarial (`probes/wa016_adversarial.py`) | D1–D3, §4 |
| Живое storage | только чтение: 136 / 41, хеш `5961c00c…7cd2` до и после. WA-3.6 / WA-3.7: NEXT read-only, `task_status`, attention `[]`, checkpoint `LEGACY_UNVALIDATED` — без изменений |
| `compileall`, `git diff --check`, LF | §3.1 |

### 3.1 Итоговые прогоны и разбор единичной ошибки

- Baseline (`257d571`, до правок) — 580 OK, skip 1.
- После исправления:
  - прогон 1 — 593, **1 ERROR**;
  - прогон 2 — **593 OK, skip 1**;
  - прогон 3 — **593 OK, skip 1**.
- `compileall` — OK.
- `git diff --check` — OK (до ротации отмечались только хвостовые пробелы самой постановки в БЛОКЕ 1; при переносе в БЛОК 2 они сняты).
- LF во всех изменённых файлах.

**Ошибка прогона 1.** `test_web_alarm_projection_concurrency.ProjectionRaceTests.test_rebuild_racing_an_authoritative_change_is_never_falsely_valid` (X): `EventCheckpointStoreError: checkpoint is missing` в `read_checkpoint` уже после гонки.

Разбор:
- В X первый checkpoint создаёт **только** rebuild-процесс. `OperationStore._touch_checkpoint` лишь обновляет уже существующий checkpoint (диагностика: `seeded=False` во всех раундах). Значит, сигнатура ошибки означает «rebuild-процесс не записал checkpoint».
- **Модель:** если сборка projection в rebuild-процессе падает (смоделирована ошибка чтения файла TaskStore при параллельной замене), получается `FAILED:ProjectionError`, checkpoint `MISSING`, а тест X падает ровно этой ошибкой. Ложного `VALID` нет: инвариант X не нарушен, тест просто не допускает легитимный fail-closed исход неудачного rebuild.
- По RC-5 (§14 отчёта RC-5) rebuild не сериализован с записями TaskStore. Неудачное чтение на Windows при конкурентной замене файла — тот же класс, что известное наблюдение WA-014 о `os.replace`.
- **Воспроизвести не удалось:** 140 целевых раундов сценария X — 40 на коде до исправления, 40 на исправленном, 60 на исправленном под нагрузкой полного прогона — 0 пропусков; стресс 8 / 8; прогоны 2 и 3 чистые.
- **Связь с правкой не обнаружена.** X строит projection активной TASK с PLANNED-этапами и INTENT / STARTED-операцией: новых веток (закрытая TASK, все этапы VERIFIED, recovery-состояния кроме `RECONCILIATION_REQUIRED`) там нет. Новый код не добавляет исключений: блокеры только добавляются в список.
- Тест X я **не менял** (не правка ради PASS) — см. F-6.

## 4. Adversarial pass

- **Рестарт.** Projection чиста, вердикт строится из persistent-фактов. Свежий процесс после прерванного settlement видит тот же список блокеров и доводит settlement (тест).
- **Гонки.**
  - Закрытие против Resolver ABORT и против RC-6 settlement сериализованы TASK-lock (тесты на реальных процессах).
  - Существующие W / X — без изменений.
  - Стресс — §3.1.
- **Согласованность RC-5 и RC-6.**
  - `TASK_READY_TO_CLOSE` в RC-6 и пустой closeout вычисляются из одной projection.
  - Новые блокеры требуют per-op recovery ≠ None. Значит, у RC-6 в NORMAL они не возникают, тупика «RC-6 молчит, а closeout закрыт» нет.
  - Каждый новый блокер снимается шагом RC-6 (`SETTLE_*` / `FINISH_SETTLEMENT`) или требует решения человека, как и раньше (`RECOVERY_BLOCKED`).
- **Несколько решений сразу (D3).** ABORT op_a + ADOPT op_b → два `RECOVERY_SETTLEMENT_PENDING`, закрытие отклонено. Один `recover`: `SETTLE_ADOPT`, `SETTLE_ABORT` → `[]` → COMPLETED → read-only.
- **Совместимость checkpoint (D1).**
  - Checkpoint, собранный кодом до исправления для затронутой активной TASK, новый код валидирует как `INCONSISTENT` (`projection_fingerprint`), `authoritative=false`; после rebuild — `VALID`.
  - NEXT для активных TASK не меняется, меняется только список closeout, а он входит в projection fingerprint.
  - Live-checkpoint'ы — `LEGACY_UNVALIDATED`, не затронуты.
  - Как и после каждого изменения семантики, процессы WEB-02 нужно перезапустить (RC-5 F3).
- **Окно краша закрытия (D2) — FINDING F-5, вне scope.**
  - `TaskStore.complete_task_locked` пишет статус COMPLETED до `os.replace` каталога. Смерть процесса между ними оставляет TASK в `active/` со статусом COMPLETED.
  - Повторное закрытие → REJECTED (`TASK_NOT_ACTIVE`), `recover` → `TASK_COMPLETED`, но RemoteEntry считает TASK активной, а `OperationStore.begin` **записывает** новую операцию: store-гейты проверяют каталог, а не статус.
  - Новая projection тут консервативна: read-only NEXT по статусу. Изменение `task_store.py` / store-гейтов вне scope.
  - **Proposal:** сначала переносить каталог, потом писать статус (краш оставит TASK в `completed/`, а все writer'ы откажут), либо проверять статус в гейтах `active_only`.

## 5. FINDINGS / PROPOSAL (вне scope, код не менялся)

- **F-1 (RC-4, без изменений по постановке).**
  - `RollbackService.close` / `_complete_release` пишут глобальный claim store раньше записи сессии.
  - На закрытой TASK claims снимаются, а сессия остаётся прежней (повтор пробы WA-015 B5 после ремонта: `close` 404, claims изменились).
  - Projection больше не предлагает этот шаг, но эндпоинт по-прежнему доступен.
  - **Proposal:** RC-4 отказывает на неактивной TASK до любой записи.
- **F-3.** REJECTED / stale-резолюция терминальной операции не блокирует закрытие, а RC-6 на ней останавливается на `MANUAL_DECISION_REQUIRED` (A10 после ремонта: COMPLETED, история read-only). Оставлено по правилу RC-5 F4 / WA-015; при желании — отдельное решение.
- **F-5.** Окно краша `complete_task_locked`, §4.
- **F-6 (тест RC-5 X, Windows).**
  - Тест требует, чтобы rebuild в гонке всегда создавал checkpoint, хотя неудачный rebuild — легитимный fail-closed исход.
  - Одно невоспроизведённое падение за 4 полных прогона этой задачи (§3.1).
  - **Proposal:** тест сохраняет исходы дочерних процессов и при `FAILED` rebuild-процесса допускает `MISSING` (по-прежнему требуя «никогда ложный VALID»), либо `_atomic_write_text` и чтения TaskStore повторяют попытку при Windows sharing violation.
- **Наблюдение.** Для активной TASK с `ABORT_ACCEPTED` верхний NEXT — текст Resolver «recovery … is closed». На `recover` указывает NEXT closeout gate (`run recover: …`), а RC-6 делает шаг сам. Текст Resolver не менял: он вне scope и не небезопасен.

## 6. Documentation impact

- **ARCHITECTURE IMPACT — YES** (после независимой проверки):
  - `23` — инвариант закрытия TASK при совместной семантике RC-5 / RC-6 и правило read-only истории;
  - `24` — статус RC-5 и exit proof;
  - `25` — журнал.
- Канонические документы обновляет verifier после PASS; я их не менял.

## 7. Файлы

- Изменены:
  - `web_alarm/projection.py`;
  - `test_web_alarm_projection.py` (один тест + импорт);
  - `Документация/000_Задачи Claude.md` (ротация БЛОКОВ 1–3).
- Новые:
  - `test_web_alarm_projection_repair2.py`;
  - `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-016_RC5_REPAIR2/rc5_repair2_report.md`;
  - `…/probes/wa016_adversarial.py`.
- Safety-копий и логов в Git нет (регламент `18`): baseline — Git HEAD, сырые выводы — во временной папке вне репозитория.

**NEXT:** push пользователя → независимая GitHub-проверка ChatGPT → при PASS закрытие RC-5 в документации (`23` / `24` / `25`, `001`, `06`) → согласование WA4-E.
