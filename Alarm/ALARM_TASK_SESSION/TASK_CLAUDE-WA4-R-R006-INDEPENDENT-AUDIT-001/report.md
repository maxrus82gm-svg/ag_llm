# CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001 — независимый аудит сдачи Codex R-006 (F1/F2/F3)

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE/VERIFIED: сдача агентом не является independent acceptance.

- Исполнитель: агент 008 (Claude), 2026-10-16, Asia/Yekaterinburg. Verifier — ChatGPT; authority по TASK/STOP — Web Alarm/пользователь.
- ARCH CLASS: Web Alarm Workspace / RT-001 / WA4-R reliability acceptance / R-006. PRIMARY PROFILE 23; TEST PROFILE 36.2.
- Назначение — БЛОК 1 карточки `000_Задачи Claude.md` и стартовое сообщение пользователя. AMENDMENT не было.
- Это verifier-gate. Он **не** разрешает WARN, GATEWAY REQUIRED, STRICT или Final Audit и не означает rollout.

## 1. Итог

| Область | Verdict | Основание (кратко) |
|---|---|---|
| Целостность пакета R-006 | **PASS** | 64/64 файла манифеста и 102/102 исходника совпали побайтно. ZIP CRC/inventory корректны, 45 RAW = оригиналы. Все 6 мутантов — дословно код до исправления. |
| **F1** — closeout vs admission/microtask, foreign identity, нативный отказ до/после move, fresh recovery | **PASS BOUNDED** | Повторено мной: полный прогон и собственные нативные Windows-проверки (WinError 5) со своими оракулами. Исключение — FINDING AUD-05: closeout игнорирует нечитаемую историю у TASK без операций. |
| **F2** — direct close vs MutationExecutor, приёмка, receipt/replay, дубликаты, lock/ownership | **PASS BOUNDED** по race/replay/ownership; часть ремонта R006-F02 (event framing) — **PARTIAL** | Сериализация, отсутствие повторного apply и replay известного receipt воспроизведены независимо, в том числе при реальной гибели процесса после DONE. Ремонт framing неполон: AUD-01 и AUD-02. |
| **F3** — WA-017 crash race, pending metadata, post-move и fresh-process recovery | **PASS BOUNDED** | Независимо: гибель процесса сразу после commit point → MOVED_STATUS_PENDING → поздние writers отклонены → свежий процесс завершает. 32 bounded-раунда. Исторический красный остаётся красным, владелец handle неизвестен. |
| **Общая готовность WA4-R** | **PARTIAL** | Evidence-гейты F1–F3 достаточны для bounded-приёмки на локальном Windows. Для GATEWAY REQUIRED/STRICT недостаточно: открыты 5 FINDING, нет независимого чистого CI. WARN — только по решению пользователя после условий из §9. |

**Ключевое.** Все прогоны и evidence сохранены, собственный статистический результат — §4.

- **Подтверждены заявленные R-006 числа:** 802 выполнено, 801 PASS / 0 FAIL / 0 ERROR / 1 SKIP. Мой независимый полный прогон дал то же множество из 802 test ID с теми же статусами, а не только тот же итог.
- **Найдено 5 воспроизводимых дефектов вне R-006 diff.** Все существуют и на коде до R-006, то есть регрессий R-006 нет. Все fail-closed: ложного physical apply или записи в закрытую TASK я не нашёл. Но два из них дают «вечную» блокировку TASK из обычного HTTP-запроса, один — закрытие TASK с нечитаемой историей.
- **Попутный плюс R-006, не заявленный Codex:** проверки identity закрыли Windows-алиасы TASK ID (`task.` и смена регистра). До R-006 такие запросы записывали события с чужим `task_id` в реальную историю TASK.

## 2. Источник: pinned revision и фактические хеши

- **Supplied baseline Codex:** `main@df3250140c987876771fe2f899f80acaf38fd920` (из `versions.json`). Git-эквивалентность локальной папки и GitHub мной **не проверялась** (DOC-GIT-01): сверка идёт по байтам файлов, а не по commit.
- **Локальная база = pinned R-006:** все **102/102** файла `final_full_source_sha256` совпали побайтно. Расхождений только в EOL нет, отсутствующих файлов нет. Карты в `checks.json` и `versions.json` идентичны. В `web_alarm/*.py` и `test_web_alarm*.py` нет локальных файлов вне pinned-карты, поэтому статус BLOCKED из-за неизвестной версии не применялся. После всех прогонов повторная сверка дала те же 102/102.
- **Изменённые R-006 файлы (локально = pin, все LF):**
  - `web_alarm/task_store.py` — `fe446753140106da5ad424ce412f919676935f884bdafe0f771ac91790ab43ac`;
  - `web_alarm/event_checkpoint_store.py` — `7d094e81b5a40dbced420af9a51c04b6e5b7b4eb4050d96bca0ba01495274aad`;
  - `web_alarm/operation_store.py` — `bb7eaf40dd2280fcd5a38d33fe85d2d97ff19733740719d15fa02cf4e6854360`;
  - `test_web_alarm_wa4r006_local_gate.py` — `cfea279508859b4337e55d3377e7631bfe33b6b1138e1c7c94cd7521382ad8bd`.
- **Diff:** восстановлен мной из байтовых копий `sources/before` → `sources/final` внутри `evidence.zip`. Совпадает с опубликованным `source-changes.diff` (31 добавленная и 6 удалённых строк, тождественны). `sources/final/*` равны локальным файлам, `sources/before/*` — before-pin из `versions.json`.
- **Пакет:**
  - 64/64 файла `manifest.json` совпали побайтно, лишних и отсутствующих нет;
  - все 64 текстовых файла LF, то есть проблемы CRLF→LF для R-006 нет;
  - `manifest.json` = `b14c366452547de2d4a102a5c50b4c7da0ad01dc539e7ded629f1a3fee46f84e` (9 884 B). Внешней печати в карточке Codex нет: это самоописывающий якорь, и его надо сверить с опубликованным в GitHub blob.
- **Параллельная работа во время аудита.** Около 12:14 обе agent-карточки изменились с разницей в секунды — по виду это pull. БЛОК 1 моей карточки после этого перечитан и не изменился. Все мои прогоны начаты позже (с 12:14:54), их source map совпадает с pin.

## 3. Цепочка evidence и RAW (проверено, без повторного исполнения)

Мой собственный аудитор (`tools/pkg_audit.py`, без production-импортов) пересчитал всё заново из байтов.

- **`evidence.zip`** (1 416 419 B, `7d126d5935ce97f47d70e86d274187406148e781121206b7940b1ac1f1fd82e4`) равен pin в `provenance`.
  - `testzip` чист; 53 члена = inventory; расхождений хешей, дубликатов и небезопасных имён нет.
- **8 попыток:** counts пересчитаны из оригинальных `results.json` внутри ZIP и все совпали с `checks.json`.
  - full-release: 802 уникальных ID — 801/0/0/1.
  - Все 103 адресных ID входят в full-release со статусом PASS.
  - Распределение 103 по модулям: mutation_executor 38, wa4r002_diagnostics 18, wa017 13, task_store 11, r006 11, opstore_conc 5, proj_conc 5, claims_conc 2.
- **45 RAW-записей:** байтовый SHA верен, `raw` канонически равен записи по указателю в оригинальном member, selector/status/origin верны. Итого 37 PASS, 7 FAIL, 1 ERROR — исходные красные сохранены.
- **Порядок фаз** (по `started_unix` и source map каждой попытки; source map каждой попытки совпал с `checks`):

  | Время | Попытка | Состояние исходников |
  |---|---|---|
  | 19:44 | baseline-focused | исходный runtime, 101 файл |
  | 19:51 | adversarial-before | исходный runtime + первая версия теста; 6 FAIL + 1 ERROR |
  | 19:55 | adversarial-after | task_store промежуточный `6394c3ba`, event_store final, operation_store ещё исходный |
  | 20:00 | quality, lock-identity-before | то же; 1 FAIL третьего дефекта |
  | 20:05 | quality-final | все файлы final |
  | 20:39–20:52 | full-release | final |
  | 20:54 | bounded | final |

  Незавершённые full-final и focused-final не засчитаны — согласен.
- **Качество quality-контролей.** Все 6 RAM-мутантов из `control-inputs.json` побайтно, по исходнику AST, равны методам **до** исправления из `sources/before`. Ни один не равен final, то есть контроли оживляют реальный старый код, а не подставной.
  - Мой прогон quality: 12/12 outer PASS; каждый требует ровно 1 внутренний FAIL.
  - `verify_package.py --source-check --self-check` Codex тоже PASS. Его self-check тавтологичен (проверяет лишь, что изменённые байты дают другой хеш); моя сверка от него не зависит.
- **Оракулы R-006 не самоподтверждающие.** `raw_state` читает сырые файлы/JSON/hex, директории, точный префикс событий и receipt. Число apply берётся из trace дочерних процессов и сверяется с байтами цели; production projection в роли «ожидаемого» не используется.
  - Слабые места: `apply_count` зависит от патча `_apply`; `raw_state` разбирает события через `str.splitlines()`, то есть с той же ошибкой framing, что и production (см. AUD-01).
- **Исторический F3** (R-005 `E043.jsonl`, 3 022 B, `192b13ce…`; ZIP `020d2770…`): исходный FAIL c0 `FAILED:CloseoutError`, нативный WinError 5 до move, b1/b2 BEGUN. Сохранён как FAIL, не переклассифицирован.

## 4. Что выполнено независимо и что только сверено

Все прогоны — Windows 10 19045, штатный guarded runner `wa4a_acceptance.py`, `.venv` Python 3.12.10 (кроме отмеченного).

- **Изоляция поверх guard runner** (Git, внешние сокеты, не-Python процессы, запись вне TEMP запрещены):
  - `LOCALAPPDATA`/`APPDATA` перенаправлены в disposable TEMP — live storage недостижим;
  - `PYTHONPYCACHEPREFIX` в TEMP — `__pycache__` репозитория не читается; `-B`.
- **Изоляция у Codex:** только `PYTHONUTF8=1`.
- Длительность у меня больше из-за отказа от байткод-кэша; с 791 с Codex её сравнивать нельзя.

| Попытка (моя) | Цели | Выполнено | P / F / E / S | Exit | Изоляция | с | `results.json` SHA-256 |
|---|---|---:|---|---:|---:|---:|---|
| r006mod | `test_web_alarm_wa4r006_local_gate` | 11 | 11/0/0/0 | 0 | 0 | 27.0 | `5ffc1cbaa3be9bbc99903d0dcef5cf92223250e1a000124f88286adddc691e00` |
| r006mod-py313 | то же, Python 3.13.8 | 11 | 11/0/0/0 | 0 | 0 | 24.5 | `398da6ed06d8968e8023cfc3fa21170ffd8434d7748afe0279d9e24762608206` |
| quality | Sensitivity R-006 + R-004 | 12 | 12/0/0/0 | 0 | 0 | 26.3 | `9475703cd2c9c1fc2573d9202823e785053cb8b942f72b4cf12f14b795ccf038` |
| **full** | `all` | **802** | **801/0/0/1** | 0 | 0 | 868.5 | `66604623de351fe4ab3608554053d2c4421466d9a23fd7c32602c1b57a57f01a` |
| bounded1–3 | 2 race-селектора ×3 (по 4 раунда) | 6 | 6/0/0/0 | 0 | 0 | 12.1 / 11.8 / 11.6 | `b0e2d82e…`, `c01cf5b2…`, `3340e37b…` |
| probes (1) | собственные, первая версия | 12 | 7/4/1/0 | 1 | 0 | 27.8 | `00b3f5a9…` |
| probes (2) | + P1c | 13 | 7/6/0/0 | 1 | 0 | 28.6 | `482a861c…` |
| probes (3) | + P6 | 14 | 7/7/0/0 | 1 | 0 | 28.2 | `82bc6f65…` |
| **probes (4, финал)** | + цепочки ошибок в фактах | 14 | **7/7/0/0** | 1 | 0 | 28.1 | `0b00d9d9dd21efaac5899a5da696d45f5b238600c4124f68e659bacc23f1f7a3` |
| probes-before ×2 | те же 14 на runtime **до** R-006 | 14 | 6/8/0/0 | 1 | 0 | 29.9 / 29.5 | `1a41ee1d…`, `a4c9609e89a75dd0297aa9662b3250e24ebe3269e492a089b8379de05cbca9ab` |

- **Полный прогон против R-006.** Тот же набор из 802 ID, ни одного ID с другим статусом. Source map в моём `results.json` совпадает с 102 pin. Все 103 адресных — PASS. SKIP тот же: `test_symlink_target_fails_closed` («symlink creation is not permitted here»).
- **Bounded.** 24 внутренних раунда в повторах плюс 8 в полном прогоне — **32 раунда F2/F3**, все PASS. Исторический CI делал 80 раундов, его ZIP утерян.
- **Probes.** «FAIL» в FindingProbes означает подтверждённый дефект, а не сбой стенда.
  - **ERROR в попытке 1** — дефект моего набора (`ImportError`: класс называется `ManifestSnapshotStore`). Сохранён, исправлен, перепрогнан по TEST-FLAKY-01.
  - Попытки 3 и 4 дали идентичный набор исходов.
  - Проверочный модуль — `probes/test_claude_r006_independent.py` (`97efdaad71d4548a52a89f4f7bcf0f89a3b49ce86c459e51b345b355aa4449e4`), актор — `probes/claude_probe_worker.py` (`f35ce6657cf018e34aa0d9d9a6a89801fae2223e81d7b5f402a2b2836aa8e4d7`).
- **Атрибуция.** `tools/make_before_mirror.py` строит TEMP-зеркало `web_alarm` с тремя модулями из `sources/before` (сверка с before-pin). Source map этого прогона отличается от pin ровно этими тремя модулями (тестовых файлов в зеркале нет намеренно).
- **Только сверено, без исполнения:** исходные красные попытки R-006 (по RAW), запечатанный R-005 (повторно не валидировался), исторический CI.
- Полный прогон на чистой машине или GitHub Actions **НЕ выполнялся**: все мои числа получены на той же физической машине, что и у Codex.

## 5. F1 — RC-5 closeout на Windows

**Evidence R-006.**
- R022–R025 (четыре сценария порядка native/admission) PASS на final pins:
  - нативный отказ до move: `CloseoutError → TaskStoreError → PermissionError(5)`;
  - статус-отказ после move → MOVED_STATUS_PENDING → свежий процесс завершает;
  - completion-first сериализует admission/plan/new mutation;
  - admission-first отклоняет closeout, не трогая evidence.
- R035: повторный нативный отказ в другом процессе, затем успех.
- Identity: исходные красные R004/R005, final R039/R040; мутанты R012/R014.

**Моё независимое воспроизведение** (своя фикстура, свои PRE/POST, свой актор, оракул — сырые байты):
- `test_F1_native_pre_move_handle_from_other_process_refuses_then_fresh_retry` — **PASS**.
  - Handle на `task.md` держит **другой** процесс без FILE_SHARE_DELETE; у Codex handle был в том же процессе.
  - Результат: `CloseoutError → TaskStoreError → PermissionError` **WinError 5**, сырое состояние побайтно прежнее.
  - Свежий процесс → COMPLETED; ровно один `TASK_COMPLETED` добавлен к нетронутому префиксу; replay известного receipt без нового apply (apply = 1).
- `test_F1_native_post_move_status_refusal_then_fresh_recovery` — **PASS**.
  - Handle на `completed/…/task.json` после move даёт WinError 5; состояние MOVED_STATUS_PENDING, файлы и события прежние.
  - Поздняя мутация отклонена (`TASK_NOT_ACTIVE`), replay даёт тот же receipt.
  - Свежий процесс → COMPLETED с `resumed=MOVED_STATUS_PENDING`; повторное закрытие → REJECTED.
- `test_P5_windows_alias_task_ids_are_refused_and_old_loader_was_exposed` — **PASS** на R-006, **FAIL** на коде до R-006.
  - `task_cl.` и `TASK_CL` на Windows резолвятся в каталог реальной TASK. R-006 отказывает в `open_task`, `append_event` и `execute` без изменения байтов.
  - Старый загрузчик принимал алиас и вписывал события с `task_id` = `task_cl.`/`TASK_CL` в реальную историю. После этого `read_events` реальной TASK падает: «event task mismatch».
  - Значит, проверка identity из R006-F01 закрывает и Windows-алиасы — это дополнительный, не заявленный плюс.

**Ограничения F1:**
- Оригинальный исторический F1-артефакт отсутствует.
- WinError 32 не наблюдался; везде было 5.
- Не чистая машина.
- **AUD-05:** closeout не учитывает читаемость истории, если у TASK нет контрактных операций.

**Verdict F1: PASS BOUNDED.**

## 6. F2 — direct close vs MutationExecutor, приёмка, replay, дубликаты, ownership

**Evidence R-006.**
- R026–R030: зонды каталогов во время реального move, нормальное разрешение move между зондами, START/APPLY/DONE не перемешивается с move, отказ preflight-lock, ошибка release-event после DONE → replay без второго apply.
- R033: исключение после durable DONE; R037: процесс убит на STARTED до apply → свежий replay требует reconciliation.
- R041: усечённый JSON операции; R042/R043: оборванный хвост событий.

**Моё независимое воспроизведение:**
- `test_F2_direct_close_cannot_interleave_inflight_apply` — **PASS**.
  - Пока процесс-писатель стоит внутри RC-3 boundary (до физической записи, STARTED уже durable), `TaskStore.complete_task` и `CloseoutService.complete` получают lock timeout на `locks/operations/task_cl.lock`.
  - Цель остаётся PRE. После release — EXECUTED, затем прямое закрытие.
  - Поздняя мутация → REFUSED, replay → REPLAYED, apply = 1.
- `test_F2_direct_close_first_blocks_executor_before_intent_then_refuses` — **PASS**. Пока closer держит оба lock перед move, executor ждёт и не создаёт INTENT. После move — `REFUSED TASK_NOT_ACTIVE`, apply = 0.
- `test_F2_process_death_after_durable_DONE_replays_receipt_without_second_apply` — **PASS**. Процесс убит (`os._exit(79)`) сразу после durable DONE; свежий процесс → REPLAYED с тем же receipt; apply = 1.
- Остаточная read-only гонка cached-path: соответствующие диагностические тесты PASS в моём полном прогоне — `test_F2_cached_snapshot_read_is_refused_without_physical_effect`, `test_F2_projection_cached_snapshot_error_preserves_checkpoint_and_raw_state`, `test_F2_cached_acquire_task_read_reproduces_error_but_preserves_PRE`. Эта гонка остаётся **известным read-only ограничением, а не устранённым дефектом**; см. также O2.

**Ремонт R006-F02 (event framing) — PARTIAL.**
- Склейка записей и чтение недописанного хвоста закрыты корректно: мутанты R009/R010 подтверждены, мои P2/P6 на старом коде показывают склейку.
- Но остались **AUD-01** (асимметрия разделителей между записью и чтением) и **AUD-02** (неатомарная приёмка при нечитаемой истории).

**Verdict F2: PASS BOUNDED** для race/replay/ownership; framing-часть R006-F02 — PARTIAL.

## 7. F3 — WA-017 crash race, pending metadata, recovery

**Evidence R-006.**
- R031: помеченный crash после move, поздние writers отклонены, свежее завершение.
- R032: writer-first не выдаёт себя за фазу crash.
- R021/R045: bounded WA-017.

**Моё независимое воспроизведение:**
- `test_F3_crash_after_commit_point_then_late_writers_and_fresh_recovery` — **PASS**.
  - Процесс закрытия убит (`os._exit(77)`) сразу после `os.replace(active→completed)`.
  - Байты: каталог только в `completed`, статус не COMPLETED, все файлы и цель неизменны; `completion_state = MOVED_STATUS_PENDING`.
  - Поздняя мутация → REFUSED; replay известного receipt → REPLAYED.
  - `create_microtask` и `set_microtask_status` → `TaskStoreError`, байты не изменились.
  - Свежий процесс → COMPLETED с `resumed=MOVED_STATUS_PENDING`, ровно один `TASK_COMPLETED`; повтор → REJECTED; apply = 1.
- Bounded WA-017: 32 раунда PASS (см. §4).

**Историческая причина.**
- Рабочая гипотеза R-003: процесс, читавший TASK до захвата lock, держал handle и блокировал move. Сейчас все чтения при admission находятся под lock. Гипотеза PLAUSIBLE, но не доказана: владелец handle в исходном CI не записан.
- Исторический красный остаётся красным.
- См. O2: lock-free читатели по-прежнему могут вызвать тот же **безопасный** нативный отказ closeout.

**Verdict F3: PASS BOUNDED.**

## 8. Adversarial review: FINDINGS (production не менялся)

Все находки воспроизводятся моими probes и на R-006 (попытки 3 и 4), и на коде до R-006 (зеркало). Ни одна не приводит к ложному physical apply или записи в закрытую TASK: цель неизменна, apply = 0 сверх фикстуры.

### AUD-01 · MEDIUM-HIGH · асимметрия framing событий (U+0085/U+2028/U+2029) — давний дефект

- **Причина.**
  - Writer: `json.dumps(..., ensure_ascii=False) + "\n"` оставляет U+0085, U+2028 и U+2029 «сырыми»; управляющие символы ниже 0x20 он экранирует.
  - Reader: `data.decode().splitlines()` режет строку и по этим символам.
  - В итоге легитимная запись не читается её же reader.
- **P1b:** U+0085, U+2028, U+2029 → «invalid event JSON at line 4»; контроль U+000B → READABLE.
- **P1 через HTTP** (`POST /tasks/{id}/mutations`, target `x\u2028y.bin`):
  - Ответ клиенту: `409 mutation_refused / ADMISSION_UNAVAILABLE`, «nothing was written».
  - Фактически записи INTENT и `OPERATION_INTENT` уже сохранены: begin выполняется до manifest-admission, и это действует для любого target.
  - После этого `read_events` падает, а closeout навсегда блокирован (`PROJECTION_OPERATIONS_UNREADABLE`). Ответ «nothing was written» ложен.
- **P1c через HTTP** (`POST /microtasks/m1/transition` с `verification_evidence`, содержащим U+2029 — свободный текст от агента):
  - История становится нечитаемой.
  - Closeout при этом **eligible** и даёт COMPLETED (`event_recorded=true`): закрытая TASK с нечитаемым audit trail.
- **Исправление (отдельная TASK):**
  - reader разбирает только по `b"\n"` после проверки хвоста, допуская завершающий `\r` у CRLF-записей; либо writer пишет события с `ensure_ascii=True`; лучше и то и другое;
  - regression-тесты P1, P1b, P1c.
- Затронут также `transport_event_store` (тот же `splitlines`), не проверялся.

### AUD-02 · MEDIUM · неатомарная приёмка при нечитаемой или оборванной истории

- **P2.** Хвост событий оборван (форма crash), затем новая мутация.
  - На R-006: `begin` сохраняет payload и `operations/op_new.json` (INTENT), после чего `append_event` отказывает. `EventCheckpointStoreError` выходит из `MutationExecutor.execute`; через HTTP это `409 state_error`.
  - На коде до R-006 запись тоже оставалась, плюс склеенная история и ответ REFUSED «nothing was written».
  - После ручного восстановления разделителя `get(op_new)` → «operation is missing durable intent history», closeout блокирован.
  - Значит, R-006 убрал склейку, но не неатомарность.
- **Исправление:** под теми же lock до любой durable-записи проверять читаемость истории (`read_events` и хвост) и отказывать без записи; плюс механизм из AUD-03.

### AUD-03 · MEDIUM · окно crash между записью INTENT и событием INTENT — тупик восстановления (давний)

- **P3.** Процесс убит (`os._exit(78)`) после `_persist_record(INTENT)` и до `OPERATION_INTENT`.
  - Повтор: `REFUSED REQUEST_REJECTED` с «nothing was recorded or written» — ложь.
  - `OperationStore.get` → «missing durable intent history».
  - Closeout: `PROJECTION_OPERATIONS_UNREADABLE`.
  - Ни один API не может прочитать, урегулировать или отменить операцию; apply = 0.
- **Исправление (нужно решение по lifecycle):**
  - признавать «INTENT rev 1 без события и без последующих событий» незавершённым INTENT;
  - идемпотентно дописывать событие под lock или разрешить явный ABORT;
  - сузить `_validate_history` для этого случая.

### AUD-04 · LOW · lock prepare создаётся до валидации ID (класс R006-F03, вне diff R-006)

- **P4.** В `manifest_store._safe_component` нет отказа для `"."`/`".."`. Поэтому `ManifestSnapshotStore.prepare_microtask("..", m)`, `reconcile_interrupted_preparation("..", m)` и CLI `microtask prepare --task-id ..` создают `locks/<m>.lock` вне `locks/prepare/`, внутри storage root, и только потом падают на валидации TaskStore.
- Серверный маршрут защищён: state machine сначала вызывает `open_microtask`.
- **Исправление:** отвергать `.`/`..` в `manifest_store` и `recovery_report_store` либо валидировать через TaskStore до lock.

### AUD-05 · MEDIUM · closeout завершает TASK с нечитаемой историей, если контрактных операций нет

- **P6.** У TASK без операций хвост событий оборван.
  - На R-006: `CloseoutService.complete` → COMPLETED, `event_recorded=false`, байты событий не изменились.
  - На коде до R-006: COMPLETED плюс склейка.
  - P1c — тот же случай для нечитаемой (U+2029) истории.
- R-006 (сообщение R007) заявляет: «torn history must not become clean completion». Это доказано только при наличии операций: читаемость проверяется лишь через `_validate_history` операций.
- **Исправление:** добавить в gate closeout для ACTIVE-завершения блокер HISTORY_UNREADABLE (читать историю под lock). Путь MOVED_STATUS_PENDING (только статус) не менять.

### Наблюдения без утверждения дефекта

- **O1.** `OperationStore._safe_component` обрезает пробелы, `TaskStore._safe_id` — нет.
  - R-006 перевёл ключ `_serialized` на обрезанный ID: теперь lock-ключи closeout/claims совпадают с begin/executor. Зато `TaskStore.complete_task(" X")` использует `locks/operations/ X.lock`, тогда как OperationStore — `X.lock`.
  - Эксплуатации я не нашёл: identity-проверки и неизвестная TASK отказывают.
  - Предложение: отвергать пробелы по краям, а не обрезать.
- **O2.** Lock-free читатели (`ProjectionService.build`, опрос UI, `inspect`) могут держать handle внутри каталога TASK и так вызвать безопасный нативный отказ closeout WinError 5 (мой F1 pre-move показывает, что хватает любого чужого handle). Это та же форма, что исторический красный F3. Безопасно и повторяемо, но влияет на доступность — мониторить в WARN.
- **O3.** `CloseoutService` дописывает `TASK_COMPLETED` уже после освобождения lock, а `append_event` на Windows не безопасен для нескольких писателей (эмуляция O_APPEND в CRT). Это было и до R-006; проверка хвоста делает порчу fail-closed, но не предотвращает её.
- **O4.** Изоляция запуска у Codex не перенаправляла `LOCALAPPDATA` (запись guard всё равно запрещал). У меня перенаправлено, расхождений в результатах нет.

## 9. Предложение по WARN gate (решает пользователь; WARN сейчас не включается)

WARN по 24/WA-4.7 — **только сообщения** о нарушениях протокола, без блокировок. OBSERVE остаётся bounded. Откат — возврат в OBSERVE. OBSERVE нельзя считать действующим STRICT.

**Минимальные условия входа:**
- **W1.** Независимое чистое исполнение на опубликованных точных pin (GitHub Actions Windows или чистая машина по выбору WEB_08):
  - полный Web Alarm, 11 селекторов R-006, диагностика F1–F3;
  - bounded-гонки с явным бюджетом не меньше 20 раундов каждая;
  - сверка source map со 102 pin.
  - Причина: весь runtime PASS (Codex и мой) получен на одной машине.
- **W2.** Решение по AUD-01…05 — ремонтная TASK или явное принятие риска, отдельно по каждой. Рекомендация:
  - AUD-01, AUD-02, AUD-05 исправить **до WARN**: дёшево, а AUD-01 достижим обычным запросом через gateway;
  - AUD-03 и AUD-04 — до GATEWAY REQUIRED.
- **W3.** Read-only preflight live storage (с разрешения пользователя, без миграции). Найти данные, которые новые fail-closed readers отвергнут:
  - несовпадение identity task/plan/microtask;
  - `events.jsonl` без LF в конце или с U+0085/U+2028/U+2029;
  - INTENT без истории;
  - посторонние lock-файлы.
- **W4.** Acceptance самого WARN: счётчики нативных отказов closeout (WinError 5/32), MOVED_STATUS_PENDING, RECONCILIATION_REQUIRED и блокеров `*_UNREADABLE`. WARN никогда не блокирует и не переписывает данные. Критерий — N операций или дней без необъяснённого класса нарушений; число задаёт пользователь.
- **W5.** Синхронизация документов — только после независимой приёмки (см. §11).
- **Не превращать в PASS:** исходный F1-артефакт и F2-ZIP на 80 раундов — постоянные пробелы evidence; владелец handle в F3 неизвестен.

## 10. Остаточные ограничения

- Та же физическая машина, что у Codex; чистого CI нет.
- Не проверялись: отключение питания, нехватка диска, сторонние writers, антивирус, все коды Windows sharing, symlink (SKIP).
- WinError 32 не воспроизведён.
- 32 bounded-раунда против исторических 80.
- Probes — offline, на disposable-фикстурах. AUD-01 проверен через `WebAlarmApi.dispatch` (тот же in-process HTTP-уровень, что в `wa4a`), без реального сокета.
- `transport_event_store` и другие JSONL-читатели на AUD-01 не проверены.
- Внешней печати манифеста нет.

## 11. DOC IMPACT, полномочия, параллельность, файлы

**DOC IMPACT** (предложения координатору; сам я документы не правил):
- **23** — контракт identity записей (включая Windows-алиасы); framing событий: только LF, правило для U+0085/U+2028/U+2029; читаемость истории в gate closeout.
- **36.2** — 11 селекторов R-006; кандидаты в регрессию из моих probes (P1/P1b/P1c/P2/P3/P4/P6 после ремонта, P5 alias, F1/F2/F3-gate); ограничение symlink.
- **24** — условия входа в WARN (§9).
- **25 / 05 / 06 / 34 / общий 000** — раздельные статусы F1/F2/F3 и AUD-01…05 после verdict.
- **18 / 36 / 36.1** — NO CHANGE.

**Полномочия:**
- Git и GitHub не использовались; `.git` не читался.
- Сети и платных вызовов не было.
- Production, общие тесты, runners, CI и документы не менялись.
- Плагины не ставились. WARN, GATEWAY и STRICT не включались.
- `DOC-CODEX-SELF-PUBLISH-01` на меня не распространяется, публикацию не выполнял.

**Параллельность.**
- Дорожку MCP Codex (`reports/CODEX-WUA-0-*`, карточка Codex, 18/19) я не читал по содержанию и ничего туда не писал: лишь заметил время изменения при проверке, что репозиторий не трогали мои прогоны.
- Pinned-исходники за время аудита не дрейфовали.

**Записано мной** (`Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001/`):
- `report.md` — этот отчёт;
- `evidence.json` — 13 попыток: argv, exit, пересчёт counts, SHA `results.json`, изоляция, различия source map, все не-PASS, полные факты probes;
- `package-audit.json` — мой аудит пакета;
- `probes/` — набор и актор;
- `tools/` — `pkg_audit`, `phase_audit`, `src_diff`, `mutant_origin`, `compare_runs`, `run_gate`, `make_before_mirror`, `collect_evidence`.
- Ротация БЛОКОВ 1–3 в `Документация/000_Задачи Claude.md`.
- Полные сырые выводы остаются в TEMP: `C:\Users\REX\AppData\Local\Temp\claude-wa4r006-*`.

**Как воспроизвести probes:**
- `CLAUDE_EXTRA_PATH=<папка probes> python tools/run_gate.py .venv/Scripts/python.exe <метка> test_claude_r006_independent`;
- для атрибуции — `tools/make_before_mirror.py`, затем `CLAUDE_RUNNER_ROOT=<зеркало>`.

## 12. NEXT

1. ChatGPT независимо проверяет отчёт и evidence; при желании — запуск моих probes.
2. Решения пользователя:
   - ремонтная TASK по AUD-01/02/05 (и AUD-03/04) — Codex или Claude, отдельным БЛОКОМ 1;
   - чистый CI на точных pin (W1);
   - read-only preflight live storage (W3).
3. Решение о WARN — только после этого. Следующие этапы, rollout и правки production мной не запускались.
