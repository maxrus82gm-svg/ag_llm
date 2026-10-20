# 🟨 Безопасное ручное восстановление повреждённого транспортного журнала после аварии (`CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001`)

**Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Не DONE/VERIFIED. LOCAL ONLY — публикует пользователь (GitHub Desktop).

- **Finding:** `AUD-01T-R` — Audit 01, Transport events, Residual recovery gap: остаточная проблема восстановления общего транспортного журнала.
- **Проект:** Web Alarm Workspace / RT-001 / WA4-R (надёжность хранения и восстановления).
- **Исполнитель:** агент 008 (Claude), 2026-10-20. **Координатор/verifier:** ChatGPT, LLM12.
- **Ориентир:** `main@8ab1c7d6c03c829ed6bd82290a700c0048fd24ab` — сообщение координатора; Git не использовался (DOC-GIT-01).
- **Не затрагивалось:** живое хранилище, сеть, server/API, runner/CI, общая документация, MCP/WUA. WA4-R остаётся PARTIAL; WARN/GATEWAY/STRICT/Final Audit не включались.

## 1. Итог

| | |
|---|---|
| Причина | `TransportEventStore` пишет запись одним `write` + `fsync`. Гибель процесса внутри записи оставляет последний JSONL-фрагмент без LF. Дальше `read_events()` и `append()` намеренно отказывают (fail-closed), а штатной безопасной процедуры вернуть журнал в работу нет |
| Что сделано | Отдельный **offline-инструмент оператора** `web_alarm/transport_event_recovery.py`: `inspect` (dry-run, ни одной записи) → `apply` с fingerprint плана и причиной. Сначала полный побайтный архив оригинала и хвоста с проверкой чтением, затем атомарная замена на точный валидный префикс под lock транспортного writer. Квитанция пишется рядом с архивом, не в журнал |
| Чего нет | Автоматического/фонового «исправления», live API, `--force`, изменений `transport_event_store.py`/`store_lock.py`/server; дописывания или восстановления оборванного события |
| Изменения в репозитории | **2 новых файла** (модуль 546 строк, тесты 866 строк). Изменённых — **0**: итоговая карта 105 + 2, drift 0 |
| Тесты | Новый модуль — 35 методов: 34 PASS / 1 SKIP (symlink: нет привилегии). Мутанты 8/8 убиты. Focused ×3: 119 тестов — r1/r2 чисто, r3 — 1 FAIL **в существующем тесте** из-за ложного срабатывания guard runner (F-T1, воспроизведено и на исходном коде 2/10). **Полный набор: 909 = 907 PASS / 0 FAIL / 0 ERROR / 2 SKIP, isolation 0**; против прежних 874 удалено 0, смен статуса 0 |

Здоровый журнал ведёт себя побайтно как раньше: store и lock не изменены (drift 0). Инструмент вызывается только явно.

## 2. Диагноз

- [ЛОК] `web_alarm/transport_event_store.py`:
  - writer: под `InterProcessLock` (`locks/transport/transport_events.lock`) проверяет конец файла на `\n`, дописывает одну запись, делает `fsync`; при ошибке write/fsync откатывает (`truncate`) до прежнего размера;
  - reader `read_events()` — без lock: файл без завершающего `\n` → `unterminated transport event log`; повреждённая строка → отказ.
- Откат при ошибке работает, **гибель процесса — нет**: отката не происходит, хвост остаётся. Это `AUD-01T-R` из отчёта `TASK_CLAUDE-WA4-R-AUD01T02B-REPAIR-001` (п. 284, 295).
- **Gate A подтверждает на исходных байтах** (зеркало без нового модуля):
  - control-тесты — store отказывает в чтении и записи, байты не меняются, публичных методов ремонта нет (`append`, `list_events`, `read_events`) — PASS;
  - trigger «операция восстановления существует» — FAIL;
  - новый тестовый модуль — ImportError.

## 3. Выбранный контракт восстановления

### 3.1 `inspect` — диагностика без мутации

Без записи, без lock, без создания каталогов. Корень хранилища — только явный, абсолютный и канонический (без `.`/`..`, junction, symlink, alias в пути).

| Вердикт | Когда | Действие |
|---|---|---|
| `NO_LOG` / `HEALTHY` (в т. ч. пустой, или идентичные дубли строк) | нет файла / всё валидно | NOOP |
| `TORN_TAIL` | все полные строки валидны **тем же правилом, что `read_events()`**; после последнего LF есть непустой хвост, начинающийся с `{`, без NUL. Подтипы: `TRUNCATED_JSON`, `COMPLETE_JSON_WITHOUT_LF` (включая `…}\r` в CRLF-журнале), `TRUNCATED_UTF8` (обрыв посреди символа), `INVALID_UTF8` | план + `plan_fingerprint` |
| `CORRUPT_MIDDLE` | любая полная строка невалидна (`INVALID_JSON`, `UNKNOWN_SCHEMA`, `UNKNOWN_EVENT_TYPE`, `INVALID_RECORD`, `INVALID_UTF8`, `BLANK_LINE`) — даже если хвост тоже оборван | REFUSE, tail-salvage запрещён |
| `AMBIGUOUS` | конфликт `event_id` (один id — разные записи); NUL в хвосте (признак power loss/сбоя носителя, PWR-01); хвост не начинает JSON-объект; у файла больше одной жёсткой ссылки | REFUSE, forensic-разбор |
| `BAD_TARGET` | нет каталога `transport/` (это не корень хранилища); reparse-точки; не канонический путь; не обычный файл | REFUSE |

**Содержимое плана:**
- канонический root и относительный путь;
- источник: размер и SHA-256;
- префикс: offset, строки, SHA-256, SHA-256 упорядоченного списка `event_id`;
- хвост: размер, SHA-256, offset, подтип;
- риск и `plan_fingerprint` (SHA-256 канонического плана, **привязан к root**).

Содержимого событий и payload в выдаче нет (проверено тестами по маркеру payload).

### 3.2 `apply` — явное подтверждение оператором

1. Аргументы: `--plan-fingerprint` (ровно 64 строчных hex, иначе отказ — значение участвует в пути архива) и `--reason` (1–500 символов, валидный Unicode). `--force` нет.
2. **Предпроверка без lock:** все отказы (нет лога, здоров, middle, ambiguous, mismatch, плохая цель) — **до создания lock-файла или чего-либо ещё**.
3. `InterProcessLock` транспортного writer, тот же путь. Timeout → `LOCK_TIMEOUT`.
4. Под lock — свежий inspect и сверка fingerprint (`PLAN_MISMATCH` для stale/foreign).
5. **Архив** в новом каталоге попытки `transport_recovery/<fp16>/<UTC-uuid>/`:
   - `original.bin` (весь исходный файл), `tail.bin` (точный хвост), `plan.json` (план + причина);
   - эксклюзивное создание (`O_EXCL`), fsync, чтение и сверка SHA, атрибут read-only.
   Ни один файл архива не правится и не перезаписывается. Сбой → `ARCHIVE_FAILED`, журнал не тронут.
6. Временный файл префикса `transport/.transport_events.jsonl.recovery-<attempt>.tmp` (`O_EXCL`, fsync, сверка) проверяется **настоящим `TransportEventStore.read_events()`**.
7. Повторная проверка идентичности (st_ino/st_dev), байтов и отсутствия reparse непосредственно перед заменой → `SOURCE_CHANGED`.
8. `os.replace` (атомарно для читателей).
9. Пост-проверка: байты = префикс, `read_events()` = те же `event_id` по порядку. Если нет — исходные байты (те же, что в архиве) возвращаются через новый temp + `os.replace`, итог `FAILED/POST_CHECK_FAILED`.
10. `receipt.json` в каталоге попытки. Если не записан — это явно сообщается (`receipt_recorded: false`), а не скрывается.

**Повтор.** Если журнал уже равен префиксу плана, а в архиве есть проверяемое доказательство (plan.json c тем же fingerprint, `original.bin` с SHA источника, префикс оригинала = текущие байты) — `ALREADY_APPLIED` без единой записи. Повреждённый или поддельный `plan.json` доказательством не считается.

### 3.3 Инструкция оператора

```text
0. Остановить Web Alarm (процедура offline; lock делает её безопасной и без этого, но живой читатель
   может кратко получить fail-closed "cannot read" или помешать замене — тогда просто повторить apply).
1. python -m web_alarm.transport_event_recovery inspect --storage-root <абсолютный канонический путь>
   exit 0  = NO_LOG/HEALTHY — делать нечего
   exit 10 = TORN_TAIL — план напечатан (размеры, SHA, offset, plan_fingerprint), содержимого событий нет
   exit 20 = REFUSE (CORRUPT_MIDDLE / AMBIGUOUS / BAD_TARGET) — НЕ ремонтировать, forensic-разбор
2. Сверить план (сколько строк остаётся, сколько байт уходит в архив).
3. python -m web_alarm.transport_event_recovery apply --storage-root <тот же путь>
        --plan-fingerprint <64 hex из шага 1> --reason "<кто и почему>"
   exit 0  = APPLIED (или ALREADY_APPLIED при повторе) — квитанция напечатана
   exit 20 = REFUSED до изменения журнала (stale/foreign plan, lock timeout, сбой архива, ...)
   exit 30 = FAILED после архива — поле state точно описывает оставшееся состояние
4. Оборванное событие НЕ восстановлено: была ли его доставка — неизвестно. Повторная отправка — решение
   владельца источника события, не инструмента. Точные байты: transport_recovery/<fp16>/<attempt>/tail.bin.
```

## 4. Модель угроз, lock order, точки сбоя

- **Защищает от:**
  - ошибки оператора: не тот корень, устаревший или чужой план, повтор;
  - конкурентных writers и читателей;
  - гибели процесса на любом шаге;
  - сбоев I/O;
  - подмены путей через junction и hard link.
- **Не защищает от:**
  - злонамеренного локального администратора;
  - потери питания (PWR-01 — fsync каталога в Windows недоступен, заявлений о power-loss durability нет);
  - TOCTOU-окна между последней проверкой и `os.replace` при **намеренной** подмене пути (остаток, требует прав записи в хранилище).
- **Lock order:** только транспортный lock (лист). Другие lock не берутся, deadlock с иерархией operations/mutation/events невозможен.
- **Платформенные факты** [ЛОК, `probes/probe_windows_primitives.py`]:
  - `os.replace` при открытом читателе → WinError 5, оригинал цел;
  - read-only цель → отказ;
  - `O_EXCL`; junction без прав администратора и с reparse-атрибутом;
  - `Path.resolve()` идёт сквозь junction;
  - symlink требует привилегию (WinError 1314);
  - fsync каталога недоступен.

| Гибель процесса (реальный `os._exit`, оценка свежим процессом) | Журнал | Повтор `apply` |
|---|---|---|
| `locked`, `archive_original_written`, `archive_written`, `archive_verified` | исходный, fail-closed | APPLIED в новой попытке; частичный архив сохранён как есть |
| `temp_written`, `before_replace` | исходный, fail-closed; `inspect` сообщает 1 оставшийся temp | APPLIED |
| `after_replace` (квитанции нет), `receipt_written` | точный префикс | ALREADY_APPLIED, без записей |

## 5. Совместимость и откат

- Формат `TransportEventRecord`, runtime API, store, lock, server — без изменений. Новые артефакты лежат только в отдельном `transport_recovery/` и не читаются ни одним существующим кодом.
- **Откат:** удалить два новых файла. Данные мигрировать не нужно: восстановленный журнал — обычный валидный журнал прежнего формата.

## 6. Тесты

Все прогоны — guarded runner `wa4a_acceptance.py` через `tools/run_gate_batch.py` → `tools/run_gate.py`:
- `.venv` Python 3.12.10, Windows 10.0.19045;
- `-X utf8 -B`, LOCALAPPDATA/APPDATA и pycache — в одноразовом TEMP;
- цели — `tools/spec-*.json`;
- сырые per-test `results.json` (пути заменены на `<TEMP>/<REPO>/<USER>`) — `runs/<label>/`;
- census и SHA оригиналов — `evidence.json`.

### Gate A — RED / baseline (зеркало исходного кода: модуль удалён, store/lock/тесты = `baseline/`)

| Прогон | Итог | Смысл |
|---|---|---|
| `gatea-baseline` | 13 = 12 PASS / 1 FAIL | control: store отказывает в чтении/записи на оборванном хвосте, байты не меняются, публичных методов ремонта нет; 10 тестов store PASS; **trigger FAIL** — операции восстановления нет |
| `red-module-baseline` | 1 ERROR | новый модуль тестов не импортируется: `web_alarm.transport_event_recovery` отсутствует |
| `red-final-baseline` (финальные тесты) | 14 = 12 PASS / 1 FAIL / 1 ERROR | то же на финальных байтах тестов; source map = исходной, расхождений 0 |

### Gate B — `test_web_alarm_transport_event_recovery.py` (35 методов, реальные `unittest`)

| Направление постановки | Тесты |
|---|---|
| 1 healthy/empty/missing — NOOP/REFUSE без мутации | `test_missing_log_and_missing_root_parts_are_never_created` (каталоги и lock не создаются), `test_empty_and_healthy_logs_are_noop_and_apply_changes_nothing` |
| 2 обрезанный JSON, полный JSON без LF, CRLF/Unicode, невалидный UTF-8; точный архив/префикс/offset | `test_truncated_record_plan_is_byte_exact_and_shows_no_content`, `test_every_tail_kind_is_classified_and_recovered_byte_exactly` (5 подтипов), `test_crlf_framed_history_keeps_its_exact_prefix`, `test_torn_first_record_leaves_an_empty_log`, `test_apply_archives_original_and_tail_before_keeping_the_exact_prefix` |
| 3 corrupt middle / неизвестная схема / невалидный id / неоднозначный хвост → REFUSE | `test_corrupt_middle_is_refused_even_with_a_torn_tail` (6 видов), `test_event_id_conflict_is_ambiguous_but_an_identical_duplicate_is_tolerated`, `test_tails_not_left_by_one_interrupted_write_are_ambiguous` (NUL, только NUL, не начало записи, одиночный CR) |
| 4 stale SHA/size, чужой/искажённый план, новые события → отказ, оригинал цел | `test_stale_foreign_and_malformed_plans_are_refused_without_any_write` (в т. ч. тот же байтовый журнал в другом root, 64 символа с `..\`, верхний регистр), `test_repeat_is_already_applied_and_after_new_appends_is_stale`, `test_damaged_or_forged_archive_is_never_taken_as_proof` |
| 5 межпроцессная гонка append, lock timeout, двойное подтверждение | `test_writer_waits_for_the_repair_and_then_appends_after_the_prefix` (writer заблокирован и ни разу не увидел оборванный журнал, `errors == 0`), `test_lock_held_by_another_process_times_out_without_any_change`, `test_two_concurrent_confirmations_apply_exactly_once` |
| 6 внедрённые ошибки и **реальная гибель потомка** + свежий процесс | Fault: архив (`ARCHIVE_FAILED`), fsync, replace (`REPLACE_FAILED` + повтор), квитанция (`receipt_recorded: false`), неверные байты после replace (возврат оригинала), молча испорченная запись архива (ловит read-back), чужая запись без lock (`SOURCE_CHANGED`), настоящий read-only файл. Crash: `os._exit` на 8 фазах (таблица §4) |
| 7 плохой root, symlink/junction/path-swap, права | `test_bad_roots_are_refused` (относительный, несуществующий, файл, `..`), `test_junctions_anywhere_in_the_tree_are_refused_before_any_write` (root-alias, архив, locks), `test_path_swap_to_an_identical_copy_after_inspect_is_refused`, `test_hard_linked_log_is_ambiguous`; `test_symlinked_log_is_refused` — **SKIP** (WinError 1314, NOT RUN) |
| 8 регрессия writers/readers, никаких ложных TASK/operation | `test_new_appends_work_and_the_lost_event_is_not_resumed` (replay той же identity → существующая запись, другая identity → conflict), проверка «в storage только transport/locks/transport_recovery»; полный набор |

**Оракулы.** Сырые байты и SHA журнала, архива, хвоста; полная перепись дерева storage до/после для всех отказов; идентичности `event_id`; маркеры фаз дочернего процесса. Только код возврата не проверяет ни один тест.

### Gate C — adversarial и качество тестов

Дополнительные режимы отказа:
1. Читатель без lock во время 20 циклов tear/repair: читатель реально видел оборванный журнал (6063 наблюдения) и точный префикс (552); 5 раз — fail-closed «cannot read» во время замены; ни одного иного состояния. 7 реальных отказов `os.replace` (WinError 5) — повтор безопасен.
2. Подмена каталога `transport` на junction к **идентичной** копии после inspect.
3. Hard link журнала.
4. Чужой план для побайтно идентичного журнала в другом root.
5. Повреждённый или поддельный `plan.json` в архиве.
6. Запись, теряющая байт и сообщающая успех.
7. Запись в журнал процессом, игнорирующим lock, между проверкой и заменой.
8. Дифференциальный fuzz (seed 20261020, 400 случаев): вердикт классификатора совпадает с `read_events()` во всех случаях; план TORN_TAIL всегда даёт префикс, читаемый store. Распределение: TORN_TAIL 149, CORRUPT_MIDDLE 166, AMBIGUOUS 71, HEALTHY 14.

**Мутанты** (`tools/build_mirror.py`, одна точная замена в зеркале TEMP):

| Мутант | Раунд 1 | Финал (`mut2-*`, финальные тесты) | Убивающие тесты |
|---|---|---|---|
| M1 повреждённая середина как хвост | убит | убит | corrupt-middle (варианты), дифференциальный fuzz |
| M2 без проверки архива чтением | **выжил** (проверка дублирована) | убит после переопределения «убрать обе проверки» | silently-corrupted archive write |
| M3 без transport lock | убит (2) | убит (3) | lock timeout, двойное подтверждение, writer `errors == 0` (добавлено после раунда 1) |
| M4 без сверки fingerprint под lock | убит | убит | stale/foreign plans, CLI |
| M5 NUL-хвост принимается | убит | убит | ambiguous tails |
| M6 junction не распознаются | убит | убит | junction, path-swap |
| M7 без сверки источника перед заменой | убит | убит | foreign write without lock |
| M8 truncate на месте вместо temp + replace | убит | убит **только тестами, патчащими seam `_replace`** — честно: семантически почти эквивалентен (truncate атомарен к гибели процесса, читатель тоже не видит полусостояния). Выбор temp + replace — по контракту постановки и ради проверки результата настоящим reader до подмены | |

### Gate D — регрессия

| Прогон | Итог |
|---|---|
| focused-r1/r2/r3: новый модуль + Gate A + transport_event_store, transport_recovery, transport_ingestion, transport_authority, aud01t02b_repair, crash_consistency | r1 119 = 118 PASS / 1 SKIP; r2 то же; **r3 = 117 PASS / 1 FAIL / 1 SKIP, isolation 1** — `test_web_alarm_aud01t02b_repair…test_concurrent_processes_lose_no_transport_event`, F-T1 |
| **full (`all`)** | **909 = 907 PASS / 0 FAIL / 0 ERROR / 2 SKIP, isolation 0**; `runs/full-vs-previous.json` против прежнего полного 874: удалено 0, смен статуса 0, добавлено 35 (34 PASS + 1 SKIP); 2 SKIP — давний `test_symlink_target_fails_closed` и новый symlink. Source map прогона = `source-final.json` |
| flake ×10 на исходном и ×10 на текущем коде | исходный: **2/10** с той же ошибкой guard (`\\?\…\locks\transport` и `\\?\…\tasks\active`); текущий: 0/10 |

Сравнение с независимым W1 (874/OK) — по моему полному прогону того же набора 874 до TASK (ID совпадают); собственного CI не запускал.

### Gate E

- `source-gate.json` (PASS, 105/105) → `source-final.json`: drift 0, missing 0, новые ровно 2.
- `diff/`: unified diff новых файлов + `diff-summary.json` (SHA до/после, EOL — LF).
- `gate-e.json`, `manifest.json` (собираются с проверкой scope утверждениями).
- `runs/byte-scan.json`: без CR, BOM, U+0085/2028/2029; `compile()` OK.
- EOL-событие карточки — §8.
- `forensic_sample/`: синтетика через настоящий CLI. `verification.json`:
  - inspect exit 10, apply exit 0, повтор ALREADY_APPLIED;
  - архив = оригинал (1068 B), хвост = потерянные байты (138 B), журнал = префикс (930 B, 3 события);
  - файлы архива read-only.

  Копии `archive_plan.json`/`archive_receipt.json` с путём, заменённым на `<TEMP>`, поэтому их SHA отличается от записанного в квитанции; бинарные файлы точные.

## 7. Ход работы — честно, включая красные попытки

1. **`green1`: 37 = 31 PASS / 1 FAIL / 4 ERROR (по методам) / 1 SKIP.**
   - Две ошибки обвязки тестов:
     - `addCleanup` читал `self.base` в момент очистки, и subTest-циклы удаляли не тот каталог;
     - перепись дерева читала lock-файл под чужой байтовой блокировкой.
   - **Одна настоящая находка, пойманная тестом:** `apply` на отсутствующем журнале отказывал, но **сначала создавал lock-файл** — мутация при отказе. Исправлено: вся проверка решения выполняется до lock (`_decide`), повторно — под lock.
2. **Факты `green2` показали два слабых теста** — они проходили, не проверяя заявленное:
   - тест читателя стартовал после ремонта и ни разу не видел оборванный журнал → переписан: ждёт первого наблюдения и делает 20 циклов;
   - факты фаз гибели перезаписывались в каждом subTest → накапливаются.
3. **Мутанты раунда 1:**
   - M2 выжил — проверки дублированы; мутант переопределён честно;
   - M3 показал, что «writer заблокирован» был бы истинным и без lock → добавлен решающий оракул `errors == 0`;
   - два мутанта не имели убивающего теста (M7, M2) → добавлены тесты чужой записи без lock и тихо испорченной записи архива.
4. **Самопроверка кода перед финалом:**
   - отпечаток плана теперь строго 64 строчных hex — он участвует в пути архива, иначе 64 символа с `..\` позволяли бы читать вне архива;
   - повреждённый `plan.json` больше не роняет инструмент `KeyError`.

   Тесты добавлены.
5. Тестовый источник получил 2 сырых U+2028 из `"a\u2028b"` (известная особенность инструмента записи) → заменены на `chr(0x2028)`; повторный скан чистый.
6. В обвязке: две ошибки экранирования путей при записи спецификаций через shell — исправлено записью файлов напрямую, на результаты не влияло.

Все красные попытки сохранены: `runs/green1/`, `runs/mut-*` (раунд 1), `runs/focused-r3/`, `runs/flake-*`.

## 8. Findings, ограничения, NOT RUN

- **F-T1 (вне scope, runner — FINDING/PROPOSAL):** guard `wa4a_acceptance.py:264-268` проверяет `Path(value).resolve().is_relative_to(TEMP)`. При одновременном создании каталогов несколькими процессами `resolve()` в Windows иногда возвращает `\\?\C:\…\Temp\…`, и запись внутри TEMP ложно считается «outside disposable temp».
  - Существующий тест `test_web_alarm_aud01t02b_repair…test_concurrent_processes_lose_no_transport_event` падает с isolation violation: исходный код 2/10, текущий 0/10 + 1/3 focused.
  - Код TASK не участвует.
  - Предложение: нормализовать путь в guard (снимать префикс `\\?\` перед сравнением или сравнивать `os.path.normcase` абсолютных путей). Runner не менял (запрещено). Может влиять и на независимый CI.
- **F-T2:** во время `os.replace` читатель без lock может кратко получить fail-closed «cannot read transport events» (наблюдалось 5 раз из 6620), и `os.replace` при открытом читателе отказывает (WinError 5 → `FAILED/REPLACE_FAILED`, журнал не тронут, повтор безопасен). Поэтому инструкция: выполнять при остановленном Web Alarm.
- **F-T3:** инструмент читает журнал целиком в память (как и `read_events()`); на очень больших журналах — память O(n). Бенчмарка нет.
- **Остаточные риски:**
  - PWR-01 — fsync каталога в Windows невозможен, заявлений о power-loss durability нет;
  - TOCTOU между последней проверкой и `os.replace` при **намеренной** подмене пути (нужны права записи в хранилище);
  - инструмент не определяет, был ли доставлен оборванный event — это сознательно оставлено человеку.
- **EOL-событие (Gate E):** персональная карточка в рабочей копии целиком стала CRLF до старта TASK (вероятно, autocrlf при Fetch/Pull). Нормализованное содержимое с подставленным слотом ожидания совпало с итогом прошлой ротации (`card_precheck.json`: MATCH). Ротация сохранила CRLF. Остальные 105 исходников — без изменений EOL; 8 тестовых файлов были CRLF и раньше.
- **NOT RUN:**
  - symlink-тест (нет привилегии);
  - живое хранилище и W3;
  - потеря питания;
  - CI/GitHub (организует ChatGPT);
  - Linux/macOS (POSIX-ветки `os.replace`/fsync не исполнялись);
  - большие журналы.

## 9. DOC IMPACT / SHARED DOC DELTA (координатору; общие документы не правились)

- **23 (Global transport evidence):** «AUD-01T-R OPEN» → offline-процедура оператора `python -m web_alarm.transport_event_recovery` (inspect → apply с fingerprint).
  - Архив оригинала и хвоста до изменения, атомарная замена на валидный префикс под transport lock, квитанция вне журнала.
  - Middle/ambiguous/NUL-хвост — отказ. Оборванное событие не восстанавливается.
  - Без power-loss гарантий (PWR-01). Не вызывается server/store.
- **24:** AUD-01T-R — реализовано, ожидает независимой проверки. Следующее — независимый review + W1-повтор; активация инструмента на реальных данных — отдельное решение пользователя (W3/операционный регламент).
- **25:** результат TASK (RESULT READY), счётчики §6.
- **36.2:** новый модуль `test_web_alarm_transport_event_recovery.py`: реальная гибель потомка на 8 фазах, межпроцессные гонки, читатель без lock, дифференциальный fuzz против `read_events()`, 8 мутантов.
- **05/06/34:** статус AUD-01T-R «реализовано, на проверке»; находки F-T1…F-T3 (§8).
- 18/36/36.1: NO CHANGE.

## 10. Комплект для публикации (GitHub Desktop)

- **Репозиторий:** `web_alarm/transport_event_recovery.py` (новый), `test_web_alarm_transport_event_recovery.py` (новый).
- **Папка** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001/` целиком:
  - `report.md`, `scope.md`, `manifest.json`, `evidence.json`, `gate-e.json`;
  - `source-gate.json`, `source-final.json`, `card_precheck.json`, `card-rotation.json`, `block3-closeout.md`;
  - `diff/`, `baseline/`, `probes/`, `forensic_sample/`;
  - `runs/` (очищенные сырые `results.json`), `tools/`.
- **Плюс** `Документация/000_Задачи Claude.md` (ротация БЛОКОВ 1–3, CRLF сохранён).
- **Не публикуется:** исходные TEMP-каталоги прогонов (их SHA — в `evidence.json`).
