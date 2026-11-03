# 🟨 Run Store v2: конкурентные писатели индекса без потерь (P9) — `CLAUDE-WUA-CHAT-RUNSTORE-P9-001`

**Статус исполнителя: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** P9 воспроизведён на исходных байтах (5/5 сценариев с дефектом) и устранён (0/5 — потерь, повторных номеров и дублей ревизий нет). Финальные проверки: `test_run_store_v2.py` 21 = 21 PASS / 0 FAIL / 0 ERROR / 0 SKIP; регрессия Audit/Run pytest 20/20, unittest 50 PASS / 2 SKIP, самоизолирующиеся 25/25 и 73/73; полный `all` 1078 = 1076 PASS / 0 FAIL / 0 ERROR / 2 SKIP; мутанты 6 KILLED / 1 SURVIVED (M05 — заранее разобранный эквивалент). Это снимает только препятствие P9, не Stage3. Независимая приёмка — WEB20.

| Поле | Значение |
|---|---|
| Исполнитель | Claude 008 |
| Координатор / независимый verifier | ChatGPT WEB20 |
| Направление | А — Ultra Chat, общее Python-ядро; работа LLM15/Codex (Ollama/Colibri) не затрагивалась |
| Источник | БЛОК 1 карточки Claude (полный текст WEB20; после случайного удаления восстановлен пользователем); назначение пользователя в чате |
| База | `main@2494f9fb13e13a6146ed514b385154a12b3efbe1` по постановке. Git не использовался: локальные файлы сверены по содержимому с опубликованными пакетами (`evidence/change_inventory.json`) |
| Live / платные API, сеть, реальные Workspace | **не использовались**: синтетические Workspace во TEMP |

## DONE

- **P9 воспроизведён до правки** — отдельный многопроцессный скрипт со стартовым барьером; оракул читает файлы индекса обычным `json`, без кода `run_store`. Подробности в §VERIFICATION.
- **Исправление (`run_store.py`).** Каждая мутация индекса выполняет чтение → изменение → публикацию под **существующей блокировкой Workspace из `context_storage.py`** — тот же OS-файл `.ultra/locks/writer.lock`, что и у всех писателей Ultra. Второго механизма блокировки и отдельного реестра нет. Под блокировкой работают `ensure_task_index_entry`, `ensure_run_index_entry`, `update_run_summary_index` и `create_run_summary`.
- **Защита публикации.** `_save_index` отказывает, если текущий поток не держит эту блокировку.
- **Читатель без блокировки** (Tk, веб) больше не падает, если писатель сжал generation-файл, пока читатель его читал: такой файл пропускается, читатель получает более старый, но целый индекс.
- **Тесты.** В `test_run_store_v2.py` добавлены 12 тестов P9; новый тестовый файл не понадобился. RED на исходном `run_store.py`, GREEN на исправленном.

## CHANGED

| Файл | Что | Строк +/− |
|---|---|---|
| `run_store.py` | `_index_lock()` и `_require_index_lock()`; четыре мутатора под блокировкой; защита в `_save_index`; пропуск исчезнувшего generation у читателя | +98 / −58 |
| `test_run_store_v2.py` | 12 тестов P9 (pytest-стиль, как файл) | +313 / −0 |
| `reports/CLAUDE-WUA-CHAT-RUNSTORE-P9-001/` | отчёт, manifest, evidence, инструменты | новые |

**Только для чтения, не изменены** (`evidence/change_inventory.json`):

- совпадают с опубликованными пакетами: `context_storage.py`, `web_alarm/server.py`, `web_alarm/ui.py`, `ultra_ui.py`, `web_alarm/model_cards.py`, `web_alarm/ultra_chat.py`, запускатель (3 файла);
- совпадают с копией или хешем до правки: `web_alarm/store_lock.py`, `audit_storage.py`;
- `server.py` и `model_registry.py` не закреплены ни одним пакетом, и их хеш до правки не записан; их время изменения раньше начала задачи;
- файлы Ollama/Colibri и общая документация не открывались для записи.

## DIFF — инженерное обоснование

**Почему блокировка ядра, а не `_existing_workspace_writer`.**

- `_existing_workspace_writer` требует `.ultra/workspace.json` с действительной идентичностью. Его не имеют фикстуры Run Store (голый `tmp_path`) и любые Workspace без истории Ultra — как и предупреждала постановка.
- Использован примитив `_workspace_writer_lock`: ему нужен только существующий корень с обычной папкой `.ultra`. `_index_lock` создаёт `.ultra`, если её нет, как Run Store всегда делал. Корень не создаёт.
- Свойства примитива, проверенные в Stage2: реентерабелен в своём потоке (вложенный `ensure_run → ensure_task` и вызов из-под блокировки ядра не ждут); освобождается ОС при смерти процесса; при занятости — `WorkspaceBusyError` после таймаута ядра (10 с); `.ultra`-ссылку сам отвергает.
- Импортированы приватные имена `context_storage` (`_workspace_writer_lock`, `_write_anchor`, `_held_writer_locks` и константы пути). Публичный псевдоним потребовал бы правки `context_storage.py` (READ-ONLY) — предложение в §QUESTIONS.

**Почему это закрывает P9.**

- Индекс читается и номер `T-xxx`/`R-xxx` выбирается внутри той же блокировки, в которой публикуется. Ревизия считается от действительно последнего индекса.
- Два писателя больше не могут прочитать одно состояние: это и было причиной потерь, повторного использования номеров и одинаковых ревизий в generation fallback.
- Формат индекса, `run_id`, `task_block_id`, `chat_id`, `display_id`, `summary_path`, retry замены и fallback через `index_generations` не изменены.

**Изменения поведения (намеренные):**

- отсутствующий корень Workspace теперь видимая ошибка (раньше `mkdir(parents=True)` молча создавал корень и `.ultra`);
- `.ultra`-junction — отказ `unsafe_storage_link`;
- `.ultra/locks` как файл — отказ.

**Не изменено:** `append_run_record` (поток записей одного RUN) — не общий индекс; контракт «один писатель на RUN» прежний (см. §PROBLEMS п.3).

## VERIFICATION

Все прогоны — во TEMP на синтетических Workspace, без сети, Git и API; Python `.venv` 3.12.10, `-B`.

`test_run_store_v2.py` написан в стиле pytest, а охраняемый раннер `wa4a_acceptance.py` собирает только unittest. Поэтому pytest-файлы идут через `tools/run_pytest.py`:

- `--basetemp`, LOCALAPPDATA/APPDATA/USERPROFILE и `PYTHONPYCACHEPREFIX` — во TEMP;
- `-B` и `PYTHONDONTWRITEBYTECODE`; `-p no:cacheprovider` (существующий `.pytest_cache` не трогается);
- до и после прогона сверяются записи корня репозитория.

Unittest-модули идут через охраняемый раннер (блокирует сокеты и не-Python процессы).

### Воспроизведение P9 (`tools/reproduce_p9.py`, оракул — файлы индекса без кода `run_store`)

| Сценарий | До исправления | После |
|---|---|---|
| S1 — 2 процесса × 40: новая задача + новый RUN | потеряно 80; номер выдан двум записям 63×; выданных номеров нет в индексе: 78; ошибки: KeyError×2 | дефектов нет |
| S2 — 4 процесса × 20: то же | потеряно 122; номер выдан двум записям 40×; выданных номеров нет в индексе: 114; ошибки: KeyError×5, PermissionError×3 | дефектов нет |
| S3 — 2 × 20, `index.json` удерживается читателем (generation fallback) | потеряно 37; номер выдан двум записям 19×; выданных номеров нет в индексе: 31; дублей ревизий generations: 39; ошибки: KeyError×11 | дефектов нет |
| S4 — 2 × 20: обновления статуса RUN | потеряно 21 | дефектов нет |
| S5 — 2 × 20: одни и те же ID задач | потеряно 0; номер выдан двум записям 11×; выданных номеров нет в индексе: 12 | дефектов нет |

### Команды и результаты

| Проверка | Команда | Exit | Итог |
|---|---|---|---|
| Существующие тесты, исходные байты | `tools/run_pytest.py … test_run_store_v2.py` | 0 | 9 = 9 PASS / 0 FAIL / 0 ERROR / 0 SKIP |
| **RED**: итоговый `test_run_store_v2.py` на исходном `run_store.py` (зеркало) | `tools/red_on_base.py` | 1 | 21 = 13 PASS / 8 FAIL / 0 ERROR / 0 SKIP |
| **Итог**: `test_run_store_v2.py` | `tools/run_pytest.py … test_run_store_v2.py` | 0 | **21 = 21 PASS / 0 FAIL / 0 ERROR / 0 SKIP** |
| pytest-регрессия Audit/Run, до / после | `tools/run_pytest.py … test_audit_v2_compatibility.py test_usage_accounting.py test_executor_context_delta.py test_audit_lazy_ui.py` | 0 / 0 | 20 = 20 PASS / 0 FAIL / 0 ERROR / 0 SKIP / **20 = 20 PASS / 0 FAIL / 0 ERROR / 0 SKIP** |
| unittest-регрессия Audit/Run (охраняемый раннер), до / после | `run_gate.py … test_audit_observability test_provider_attempt_integration test_planner_diagnostics test_run_auth_failure test_rt002_final_audit_m1 test_rt002_s2_budget_policy` | 0 / 0 | 52 = 50 PASS / 0 FAIL / 0 ERROR / 2 SKIP / **52 = 50 PASS / 0 FAIL / 0 ERROR / 2 SKIP**; 2 SKIP — модули, запускаемые только своим `main()` |
| Самоизолирующиеся runner'ы, до / после | `python -B test_rt002_final_audit_m1.py`, `python -B test_rt002_s2_budget_policy.py` | 0 / 0 | m1: 25 = 25 PASS (PASS) / **25 = 25 PASS (PASS)**; s2: 73 = 73 PASS (PASS) / **73 = 73 PASS (PASS)** |
| Мутанты | `tools/run_mutants.py` | 0 | 6 KILLED / 1 SURVIVED из 7; контроль PASS (21 тестов); остатков во TEMP: 0 |
| Полная регрессия `all` | `run_gate.py … all` | 0 | **1078 = 1076 PASS / 0 FAIL / 0 ERROR / 2 SKIP**, изоляция 0 нарушений |



**Preflight регрессии.**

- Исключены: `test_final_audit.py` (Git по постановке), `test_final_audit_recovery.py` (реальные `git init` / `git add`), `test_rt002_s1_routes.py` (тяжёлые маршрутные тесты процессов вне индекса).
- `test_rt002_final_audit_m1` и `test_rt002_s2_budget_policy` в общем раннере пропускаются целыми модулями: так задумано, они запускаются только своим `main()` с собственной песочницей и защитами. Поэтому выполнены отдельно (`evidence/standalone_runners.json`), до и после правки.

### Новые тесты P9 (12) и требования §6

| Требование | Тест |
|---|---|
| Два и более процесса — разные TASK/RUN без lost updates; монотонность без пропусков | `test_p9_concurrent_processes_create_tasks_and_runs_without_lost_updates` (2×25 и 4×8; номера `1..N` подряд; каждый выданный номер = сохранённый; одна ревизия на подтверждённую запись) |
| Повторная регистрация того же ID — без дубля | `test_p9_repeat_registration_from_two_processes_creates_one_entry` (обоим процессам один номер) |
| Конфликт принадлежности — отказ | `test_p9_identity_conflicts_are_refused_without_any_write` |
| Вложенный вход без deadlock | `test_p9_nested_calls_reenter_and_another_thread_waits`; пробник A6 (Run Store под блокировкой ядра в том же потоке) |
| Таймаут — ограниченный и объяснимый отказ | `test_p9_a_held_workspace_lock_is_a_bounded_visible_refusal` (`WorkspaceBusyError`, индекс не меняется; после смерти держателя работа продолжается) |
| Сбой процесса в контрольной точке | `test_p9_a_process_dying_at_publication_leaves_no_unconfirmed_success` (до и после публикации; повтор после «рестарта» идемпотентен) |
| Временная и постоянная блокировка `index.json` → generation fallback; восстановление canonical | `test_p9_writers_with_a_held_index_use_generations_then_recover_the_canonical_index` (2 процесса; 32 generation-файла, у каждого своя ревизия; после освобождения — canonical и сжатие); прежние 4 теста fallback/retry |
| Конкурентные обновления статуса | `test_p9_status_updates_from_two_processes_are_all_kept` |
| Публикация только под блокировкой | `test_p9_the_index_is_never_published_outside_the_lock` |
| Junction | `test_p9_a_junction_at_ultra_is_refused_and_the_target_untouched` |
| Повреждённый индекс | `test_p9_a_damaged_index_is_a_visible_error_and_is_not_overwritten` |
| Читатель во время сжатия generations | `test_p9_a_reader_tolerates_a_generation_compacted_while_it_reads` |

### Мутанты (`tools/run_mutants.py`, зеркало во TEMP, цель — `test_run_store_v2.py`)

| Мутант | Итог | Кем убит |
|---|---|---|
| M01 ensure_task_index_entry without the lock | KILLED | `test_p9_a_held_workspace_lock_is_a_bounded_visible_refusal`, `test_p9_a_junction_at_ultra_is_refused_and_the_target_untouched` … |
| M02 ensure_run_index_entry without its own lock | KILLED | `test_p9_concurrent_processes_create_tasks_and_runs_without_lost_updates`, `test_p9_writers_with_a_held_index_use_generations_then_recover_the_canonical_index` |
| M03 update_run_summary_index without the lock | KILLED | `test_p9_status_updates_from_two_processes_are_all_kept` |
| M04 the publication guard removed | KILLED | `test_p9_the_index_is_never_published_outside_the_lock` |
| M05 create_run_summary without its own lock (expected equivalent) | SURVIVED | — |
| M06 a lock that does not exclude other processes | KILLED | `test_p9_a_held_workspace_lock_is_a_bounded_visible_refusal`, `test_p9_a_junction_at_ultra_is_refused_and_the_target_untouched` … |
| M07 a reader crashes on a compacted generation | KILLED | `test_p9_a_reader_tolerates_a_generation_compacted_while_it_reads` |

M05 (`create_run_summary` без собственной блокировки) выжил, как разобрано заранее: обе внутренние операции блокируются сами. Любое чередование, которое предотвращает внешняя блокировка, даёт тот же результат, что и допустимый последовательный порядок «обновление, затем создание». Для индекса это эквивалент; внешняя блокировка оставлена для атомарности составной операции.

### Adversarial review (`tools/adversarial_p9.py`)

- **A1 junction at .ultra** — PROTECTED (`refused unsafe_storage_link`)
- **A2 junction at .ultra/audit** — OPEN (pre-existing: Run Store does not verify .ultra/audit; not changed by P9) (`accepted`)
- **A3 damaged index** — PROTECTED (visible error, nothing overwritten)
- **A4 legacy duplicate generations** — CHARACTERISED: two generations of one revision (possible only from writers before P9) resolve deterministically to one; the other's entries are not merged back (pre-existing loss stays lost)
- **A5 .ultra/locks is a file** — PROTECTED (visible refusal, no write) (`refused storage_unavailable`)
- **A6 Run Store under the core lock in the same thread** — NO DEADLOCK (same lock, reentrant in its thread)
- **A7 missing Workspace root** — visible refusal, nothing created (before P9: the root and .ultra were created silently) (`refused FileNotFoundError`)

## PROBLEMS

1. **OPEN, вне P9: `.ultra/audit` как junction.** Run Store не проверяет свою папку `audit` и пишет через ссылку наружу (пробник A2). Так было и до задачи. Исправление требует проверки путей во всех записях Run Store (`summary.json`, потоки, индекс) — это отдельная задача. Предложен FOLLOWUP.
2. **Исторические дубли generations** (только от писателей до P9) разрешаются детерминированно в одну. Записи проигравшей стороны не сливаются обратно: прежняя потеря остаётся потерей (A4).
3. **`append_run_record`** (поток записей одного RUN) не под блокировкой. Контракт прежний: один писатель на RUN (запись ведёт рекордер Tk своего RUN). Номер записи берётся чтением последней строки. Два писателя одного RUN могли бы получить одинаковый номер — сценарий не проверялся, в текущем коде он не возникает. Это не P9.
4. **Читатели без блокировки** видят индекс атомарно (замена файла целиком). При сжатии generations они могут получить более старый индекс, но не смесь и не сбой.
5. **Ожидание блокировки** — до 10 с (таймаут ядра) в потоке, который пишет индекс. Сетевые и пользовательские ожидания под блокировкой не выполняются.
6. **Платформа:** проверено на Windows NTFS. POSIX (`flock`), UNC, `subst`, сетевые папки — NOT RUN.
7. **Не закрыто этой задачей:** `FOLLOWUP-WUA-S2-CHAT-STAGING-001`, читатели Tk P1–P6, гейты Stage3.

## QUESTIONS

1. **Дефект вставки в БЛОК 1:** в нём нет строки `**TASK ID:** \`CLAUDE-WUA-CHAT-RUNSTORE-P9-001\``; есть только заголовок `# TASK: …`. `task_slot_rotate.py check` даёт `INVALID / NO_TASK_ID`, а ротация БЛОК 1 → 1.1 без этой строки невозможна. БЛОК 1 исполнитель не правит. На момент сдачи строка не добавлена: ротация не выполнена (NO ROTATE); пакет полный, ротацию выполню после исправления.
2. **Публичный псевдоним блокировки в `context_storage.py`** (например, `workspace_writer_lock(root)`), чтобы Run Store не импортировал приватные имена. Требует отдельного разрешения: `context_storage.py` был READ-ONLY.
3. **FOLLOWUP для `.ultra/audit`** (PROBLEMS п.1) — назначать ли.

## DOC IMPACT (общие документы не менялись)

- **№03 / Run Store (аудит RUN):** мутации индекса RUN v2 выполняются под блокировкой Workspace ядра (`.ultra/locks/writer.lock`), публикация без неё запрещена. Читатели без блокировки получают целый, возможно более старый индекс. Отсутствующий корень, `.ultra`-ссылка, `.ultra/locks`-файл — видимые отказы.
- **№37 этап 3 (prerequisites):** P9 устранён в границах проверенного контракта. Остаются `.ultra/audit`-ссылка (новый FOLLOWUP), staging, читатели Tk P1–P6, гейты Stage3.
- **№05:** P9 → кандидат на закрытие после независимой проверки WEB20. Новый кандидат FOLLOWUP: проверка путей записи Run Store (`.ultra/audit`).
- **№06 / №34 / №40** — координатор.

## NEXT

- Пользователь: добавить строку TASK ID в БЛОК 1 (QUESTIONS п.1), затем опубликовать.
- WEB20: независимая проверка исходников и evidence.
- Stage3 не начинать. Перед ним — FOLLOWUP `.ultra/audit`, staging, Tk P1–P6 и гейты Stage3.

## Пакет

`reports/CLAUDE-WUA-CHAT-RUNSTORE-P9-001/`:

- `report.md`, `manifest.json` (размеры и SHA-256, неизменность опубликованных файлов, результат сканирования), `handoff_task.md` (снимок постановки; пишет скрипт ротации).
- `evidence/`:
  - `reproduce_before_fix.json`, `reproduce_after_fix.json`;
  - `pytest_baseline.json`, `red_on_base.json`, `pytest_focused.json`;
  - `pytest_regression_base.json`, `pytest_regression.json`;
  - `gate_regression_unittest_base.json`, `gate_regression_unittest.json`, `standalone_runners.json`;
  - `gate_all.json`;
  - `mutants.json`, `adversarial.json`, `change_inventory.json`;
  - `rotation.json` (после ротации).
- `tools/`: `reproduce_p9.py`, `run_pytest.py`, `red_on_base.py`, `run_mutants.py`, `adversarial_p9.py`, `record_gate.py`, `record_standalone.py`, `change_inventory.py`, `make_manifest.py`.

Публикация — только после `web_alarm.evidence_sanitizer scan` с exit 0. Файлы пакета — LF, без путей.

**Незакоммиченные изменения (коммит делает пользователь):** `run_store.py`, `test_run_store_v2.py`, папка пакета.
