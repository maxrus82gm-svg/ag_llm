# 🟨 Ultra Chat Stage2: усиление безопасной замены файлов общего хранилища (`CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001`)

**Статус исполнителя: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Проверки на финальных байтах: адресный набор 166 (161 PASS / 5 SKIP); полная регрессия `all` 1078 (1076 PASS / 2 SKIP); мутанты 9/9 KILLED в финальном прогоне (в первом — 8/9, причина в §5.3). Подмена папки **после** последней проверки (после проверки временного файла, до `rename`/`replace`) только обнаруживается — остаётся OPEN (§6). Продуктовый PASS не объявляется.

| Поле | Значение |
|---|---|
| Исполнитель | Claude 008 |
| Координатор и независимый проверяющий | ChatGPT |
| Направление | А — Ultra Chat / Shared Storage |
| Источник | БЛОК 1 карточки Claude (назначение пользователя в чате); `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` из `reports/CHATGPT-WEB18-S2-REPAIR-REVIEW-20261031.md` |
| База | `main@ffeb5d192924172f9ae6558cee961731b49295ce` (№477) по содержимому: инженерные байты №475 (ремонт F-01) и №473 (Stage2) совпали, F-01 на месте. Git не использовался |
| Live / платные API, сеть, реальные Workspace и история | **не использовались**: всё во TEMP на синтетических Workspace |

## 1. Итог

Три операции замены теперь публикуют через тот же проверенный механизм, что и писатели контекста сообщения после ремонта F-01:

- `rename_workspace()` — `workspace.json`;
- `save_project_context()` — `project_context.md` и новая ревизия в `project_context_history`;
- `rename_chat()` — карточка чата.

Что это даёт:

- место временного файла проверяется через его открытый дескриптор **до записи первого байта**;
- после замены байты читаются обратно;
- прежний текст Project Context читается без перехода по ссылкам;
- существующая ревизия истории никогда не перезаписывается.

Блокировка, проверка идентичности Workspace, `expected_title`, форматы, сигнатуры и возвращаемые значения — прежние. Ремонт F-01 (`state.json`, варианты) не тронут, его тесты зелёные.

## 2. Pre-start

- `tools/task_slot_rotate.py check` — OK: БЛОК 1 = эта TASK (168 строк), БЛОК 1.1 = ремонт F-01.
- Исходники совпадают по содержимому с опубликованными пакетами (№475 для `context_storage.py` и `test_ultra_chat_storage.py`, №473 и прежние для остальных). Дрейфа нет.
- Ремонт F-01 на месте: пять его функций и три защищённые обёртки.
- Запускатель **STANDARD**. Активной работы другого исполнителя по этим файлам нет.
- Прочитано адресно:
  - карточка (Рабочий порядок, БЛОК 1);
  - №03 §2, §6–8, §10 (Workspace, Project Context и его история, карточка Chat);
  - №37 §2.4 и Stage2; №36.1/36.3: для Python runtime нужен `python_compile`; `ui_smoke_test` — только для `server.py`/`ultra_ui.py`, они не менялись;
  - FOLLOWUP в №05, review WEB18 ремонта;
  - отчёты №473 и №475; реализации `_replace_verified`, `_publish_new_file`, `_atomic_write_text`, `_atomic_write_json`.
- Evidence: `evidence/prestart.json`.
- Учтено замечание WEB18 к прошлому отчёту: в первом прогоне `all` ремонта было 1075 PASS, а не 1077. Все числа этого отчёта вычислены скриптом из сырых JSON по формуле PASS = run − fail − error − skip.

## 3. Аудит фактических путей (до → после)

| Операция | Чтение | Временный файл | Публикация | Обратное чтение |
|---|---|---|---|---|
| `rename_workspace` | `workspace.json` без перехода по ссылкам (Stage2) | `Path.open` в `.ultra`, **место не проверялось** → `os.open(O_EXCL)`, место проверено через дескриптор | `os.replace` с повтором (без изменений) | **не было** → есть |
| `save_project_context`: прежний текст | `Path.read_text`, **по ссылкам, без предела** → чтение без перехода по ссылкам, ≤ 16 МиБ; жёсткая ссылка, ссылка, папка — отказ | — | — | — |
| `save_project_context`: ревизия | — | **не проверялось** → проверено | `os.replace`: **могла затереть** существующее имя → эксклюзивный `rename` (Windows) / `link` (POSIX); при занятом имени — новое имя, до 5 попыток, затем `revision_exists` | **не было** → есть |
| `save_project_context`: `project_context.md` | — | **не проверялось** → проверено | `os.replace` с повтором | **не было** → есть |
| `rename_chat` | карточка без перехода по ссылкам (Stage2) | **не проверялось** → проверено | `os.replace` с повтором | было, осталось |

Папки, через которые идёт запись, проверялись и раньше, под блокировкой: `.ultra` при чтении идентичности, папка чата в `_require_chat_for_write`, `project_context_history` через `_ensure_write_directory`. Это сохранено.

`state.json` из №475 уже шёл через `_replace_verified`. Функция не изменилась, тесты F-01 проходят.

Единственный оставшийся вызов `_atomic_write_json` — карточка в свежей staging-папке `create_chat`. Он вне этой задачи (§6 п.4).

## 4. Изменения (`context_storage.py` +63/−14; `test_ultra_chat_storage.py` +377/−0)

- `rename_workspace`, `rename_chat` → `_replace_verified(...)` вместо `_atomic_write_json` (+ прежнего отдельного `_verify_published` у `rename_chat`).
- `save_project_context`:
  - прежний текст — новая `_read_project_context_for_write`: ограниченное чтение без перехода по ссылкам (обычный файл, одна жёсткая ссылка, конечный путь под корнем).
    - Текст декодируется `utf-8-sig`, переводы строк `\r\n` и `\r` → `\n` — ровно то, что давал прежний `Path.read_text`. Ошибка декодирования — как прежде.
    - Ссылка или жёсткая ссылка → `unsafe_storage_link`, в историю ничего не копируется и ничего не заменяется.
    - Папка, недоступный файл или файл больше 16 МиБ → `project_context_unreadable`.
  - ревизия — новая `_publish_project_context_revision`: прежний формат имени, эксклюзивная `_publish_new_file`, повтор с новым именем при занятом;
  - сам `project_context.md` → `_replace_verified`.
- Решение: отдельную повторную проверку папок непосредственно перед записью не добавлял. Последней и точной проверкой служит проверка места временного файла через дескриптор: подмена папки после любых предыдущих проверок приводит к отказу до записи байтов.

## 5. Проверки

Все — на финальных байтах, во TEMP, на синтетических Workspace. Python — `.venv` 3.12.10 с `-B`, охраняемый раннер `wa4a_acceptance.py` (`run_gate.py`). Тесты не обращаются к Git, сети, платным API и реальной истории: изоляция TEMP раннера показала 0 нарушений.

### 5.1. Команды и результаты

| Проверка | Команда | Exit | Итог |
|---|---|---|---|
| Compile (в памяти) | `tools/final_state.py` | 0 | 2/2 OK |
| Новые тесты **до** изменения (RED) | `run_gate.py … ReplaceHardeningTests ReplaceConcurrencyTests` на исходном коде | 1 | RED: 17 методов — 9 PASS / 7 FAIL или ERROR / 1 SKIP (записи раннера по подтестам: failures=14, errors=1, skips=1) |
| Адресный набор | `run_gate.py … test_ultra_chat_storage test_message_context test_compressor_runtime test_chat_create_atomicity test_failed_run_terminal_message test_context_registry test_ultra_chat_read test_web_alarm_ultra_chat_storage test_web_alarm_ultra_chat` | 0 | **166 = 161 PASS / 5 SKIP**, 0 FAIL / 0 ERROR, изоляция 0 нарушений |
| Мутанты, первый прогон | `tools/run_mutants.py` | 0 | 8 KILLED / 1 SURVIVED из 9 (выжил H03), контроль PASS (78 тестов), остатков во TEMP: 0 |
| Мутанты, финальный прогон | `tools/run_mutants.py` | 0 | 9 KILLED / 0 SURVIVED из 9, контроль PASS (78 тестов), остатков во TEMP: 0 |
| Полная регрессия `all` | `run_gate.py … all` | 0 | **1078 = 1076 PASS / 2 SKIP**, 0 FAIL / 0 ERROR, изоляция 0 нарушений |

Прогон 1 (`evidence/gate_all_run1.json`): 1078 = 1075 PASS / 0 FAIL / 1 ERROR / 2 SKIP, изоляция 0 нарушений. Непрошедшие: `test_web_alarm_folder_picker.PickerHttpTests.test_body_and_media_type_are_strict` — `ConnectionAbortedError [WinError 10053]` в HTTP-тесте folder picker. Подпись совпадает с известным флейком F-S1 (сервер отвечает 403, не дочитав тело POST); причинность независимо не доказана. Модуль не использует `context_storage`. Повтор модуля `test_web_alarm_folder_picker` трижды: 16/16 PASS, 16/16 PASS, 16/16 PASS. В таблице — прогон 2 на тех же байтах.

**RED до изменения** (`evidence/red_before_change.json`) — что делал старый код:

- опубликовал карточку в подменённую папку чата (байты оказались снаружи; чтение обратно лишь сообщило об ошибке);
- опубликовал ревизию в подменённую папку истории без отказа;
- скопировал текст внешнего файла (жёсткая ссылка) в историю;
- перезаписал существующую ревизию;
- не проверил место временного файла;
- `project_context.md`-папка — `PermissionError` вместо явного кода.

Часть падений подтестов «сбой `os.write`» в RED — следствие того, что старый код писал не через `os.write` (запись проходила). Это не дефект, а различие механизма.

Тесты совместимости, конкурентности и характеристики подмены `.ultra` проходили и на старом коде, как и задумано.

### 5.2. Новые тесты (`test_ultra_chat_storage.py`, 17 методов)

| Требование §6 | Тест |
|---|---|
| 1. Обычные переименования, Project Context, история | `test_ordinary_renames_and_project_context_history_keep_every_byte_and_field`: все поля (включая неизвестные) и формат JSON сохраняются; ревизии — точные байты прежних текстов, старые не меняются; повтор того же текста — без записи; BOM/CRLF/одиночный CR — как прежде |
| 2. Устаревший `expected_title` | `test_a_stale_title_is_refused_without_a_lost_update` (байты и время карточки не меняются) |
| 3. Junction заранее, включая историю | `test_a_junction_at_the_history_folder…`, `…hard_linked_to_an_outside_file…`, `…that_is_a_folder…`; прежние Stage2-тесты junction для `.ultra`, `chats`, папки чата |
| 4. Подмена после первой проверки и до публикации | `test_a_chat_folder_swapped_before_the_temporary_file…`, `test_a_history_folder_swapped_before_the_temporary_file…` (подмена ровно перед открытием временного файла: отказ, внешняя папка без опубликованных байтов); `test_the_ultra_folder_cannot_be_swapped_while_its_lock_is_held_on_windows`; `test_a_swap_after_the_last_check_is_detected_by_the_read_back_not_prevented` (residual, характеристика); `test_a_temporary_file_reported_elsewhere_by_the_os_is_never_published` (негативный оракул самой проверки: ОС «сообщает» чужое место временного файла — для всех трёх операций и для `project_context.md` без ревизии) |
| 5. Внешний каталог неизменен | оракул `tree()`: имена, типы, `lstat`-время, размеры, SHA-256 без кода `context_storage`; при подмене перед временным файлом сравниваются файлы (время папки меняется — см. §6) |
| 6. `fsync`, `rename`, `replace`, блокированный файл, завершение процесса | `test_write_failures_leave_the_old_bytes…` (`fsync`, `os.write`, `os.replace` × 3 операции; `rename` публикации ревизии), `test_a_reader_holding_the_file…`, `test_a_writer_killed_mid_replacement…` (`os._exit` перед заменой, затем «рестарт») |
| 7. Два процесса | `test_two_processes_save_project_context_without_losing_a_revision` (20 сохранений → ровно 20 ревизий, ни один прежний текст не потерян), `test_two_processes_rename_the_workspace_and_keep_its_identity_and_fields` |
| 8. RAW, ID, Context Variant, F-01 | ordinary-тест (RAW, Workspace/Chat ID); все 15 тестов F-01 и 36 прежних Stage2-методов в адресном наборе |
| 9. Symlink | `test_a_project_context_symlink…` — SKIP (нет привилегии); жёсткая ссылка и junction выполнены |
| 10. Compile, negative/integration, мутанты, `all` | §5.1 |
| — Ревизия не перезаписывается | `test_an_existing_revision_name_is_never_overwritten` |

### 5.3. Мутанты

Цели — `test_ultra_chat_storage` и `test_message_context` (78 тестов), зеркало во TEMP. Контроль — PASS.

| Мутант | Финал | Кем убит |
|---|---|---|
| H01 rename_workspace by the old unchecked replace | KILLED | `test_a_temporary_file_reported_elsewhere_by_the_os_is_never_published`, `test_write_failures_leave_the_old_bytes_and_no_temporary_files` |
| H02 rename_chat by the old replace plus read-back | KILLED | `test_a_chat_folder_swapped_before_the_temporary_file_gets_no_published_bytes`, `test_a_temporary_file_reported_elsewhere_by_the_os_is_never_published`, `test_write_failures_leave_the_old_bytes_and_no_temporary_files` |
| H03 project_context.md by the old unchecked replace | KILLED | `test_a_temporary_file_reported_elsewhere_by_the_os_is_never_published` |
| H04 the old text read by following links | KILLED | `test_a_project_context_hard_linked_to_an_outside_file_is_refused`, `test_a_project_context_that_is_a_folder_is_refused_explicitly` |
| H05 a revision written by replace (may overwrite) | KILLED | `test_a_history_folder_swapped_before_the_temporary_file_gets_no_revision`, `test_a_temporary_file_reported_elsewhere_by_the_os_is_never_published`, `test_an_existing_revision_name_is_never_overwritten` … |
| H06 verified replace without the temporary-file location check | KILLED | `test_a_chat_folder_swapped_before_the_temporary_file_gets_no_published_bytes`, `test_a_temporary_file_reported_elsewhere_by_the_os_is_never_published` |
| H07 verified replace without the read-back | KILLED | `test_a_swap_after_the_last_check_is_detected_by_the_read_back_not_prevented` |
| H08 a linked Project Context reported as merely unreadable | KILLED | `test_a_project_context_hard_linked_to_an_outside_file_is_refused` |
| H09 the old text not seen as Path.read_text saw it (newlines) | KILLED | `test_ordinary_renames_and_project_context_history_keep_every_byte_and_field` |

**Первый прогон** (`evidence/mutants_run1.json`): 8 KILLED / 1 SURVIVED из 9 (выжил H03), контроль PASS (78 тестов), остатков во TEMP: 0. Выжил H03 (`project_context.md` через старую непроверенную замену). Причина — слабость моего теста. Подслучай «без ревизии» удалял файл, `ensure_workspace_storage` сначала публиковал шаблон (уже проверенной публикацией) и отказывал там; до замены `project_context.md` дело не доходило. Подслучай исправлен (пустой файл: ревизии нет, `ensure` не вмешивается), финальный прогон — 9/9.

## 6. Точные гарантии и остаточные TOCTOU

**Гарантируется** (под блокировкой Workspace, на Windows NTFS, проверено тестами):

1. Заранее существующие junction, symlink или reparse point на пути записи, а также жёсткая ссылка или ссылка на месте `project_context.md` → отказ `unsafe_storage_link`. Ничего не создаётся и не копируется.
2. Подмена папки в любой момент **до открытия временного файла** → отказ до записи первого байта; опубликованных данных снаружи нет.
3. Существующая ревизия не перезаписывается никогда (эксклюзивная публикация, даже без блокировки).
4. Отказ или сбой (`fsync`, `write`, `replace`, `rename`, занятый файл, смерть процесса) не выдаётся за успех; прежние байты целы, временные файлы удаляются (после смерти процесса остаётся только скрытый `.tmp`).

**Не гарантируется (OPEN):**

1. Подмена папки **после** проверки места временного файла и **до** `rename`/`replace`. Запись ложится снаружи и только **обнаруживается** чтением обратно (`unsafe_storage_link`). Характеризовано тестом `…detected_by_the_read_back_not_prevented`. Полностью закрыть это без открытия файлов относительно дескриптора папки (`openat`/`renameat`) нельзя; в Python на Windows таких вызовов нет.
2. При подмене перед открытием временного файла он на мгновение создаётся во внешней папке и сразу удаляется: меняется время изменения этой папки.
3. Для `.ultra` (а значит, для `workspace.json` и `project_context.md`) подмена на Windows **блокируется самой ОС**: в `.ultra` открыт файл блокировки, папку с открытым файлом переместить нельзя (характеризовано тестом). Это свойство Windows; на POSIX не проверялось.
4. Вне этой задачи: карточка в staging-папке `create_chat` пишется через `_atomic_write_json` (папка свежая, внутри проверенного `chat_staging`). Окно «подмена после проверки» там такое же, как было до этой задачи. Предложение — тем же способом отдельной правкой (§9).
5. Защиту от другой программы того же пользователя контракт Stage0 §9 не обещает. Это усиление, а не абсолютная гарантия.

## 7. MANUAL ENGINEERING REVIEW

Самостоятельный проход по всем изменённым путям записи.

- **`rename_workspace`.** Идентичность и поля читаются под блокировкой без перехода по ссылкам (Stage2); изменяется только `display_name`. Запись — `_replace_verified`. Тип `workspace.json` (обычный файл, одна ссылка) проверен этим чтением.
- **`save_project_context`.**
  - Ввод проверяется до любого создания.
  - Прежний текст — без перехода по ссылкам.
  - Сравнение с новым текстом — как раньше (по декодированному тексту).
  - Порядок: ревизия, затем замена контекста. При отказе публикации ревизии контекст не заменяется. При отказе замены контекста после опубликованной ревизии в истории остаётся лишняя ревизия — история только пополняется (так было и раньше).
  - Возвращаемый словарь и пути — прежние.
- **`rename_chat`.** Проверки владельца, версии, `expected_title`, «повтор — без записи» не тронуты; запись — `_replace_verified`.
- **Изменения поведения (намеренные):**
  - `project_context.md` — ссылка, жёсткая ссылка или папка: раньше ссылка заменялась обычным файлом, а текст внешнего файла копировался в историю; теперь явный отказ;
  - при коллизии имени ревизии — новое имя вместо перезаписи.
- **F-01 и прежние контракты.** `_replace_verified`, `_publish_new_file` и писатели контекста не изменены. Все тесты Stage1/Stage2/F-01 в адресном наборе и в `all` — PASS без правок.

## 8. Совместимость, идентичности, запускатель

- Сигнатуры и возвращаемые значения трёх функций прежние. Байтовый формат: JSON с отступом 2, LF и `\n` в конце; текст контекста и ревизий — UTF-8 как прежде.
- Workspace ID, Chat ID, RAW, Context Variant не меняются (ordinary-тест и тесты F-01).
- Файлы вне scope (`ultra_ui.py`, `web_alarm/server.py`, `web_alarm/ui.py`, `web_alarm/ultra_chat.py`, JS, HTTP-тесты, `test_message_context.py`) байт-в-байт как в опубликованных пакетах (`evidence/change_inventory.json`).
- **Запускатель STANDARD**: active `standard`, `load_launch()` standard, три файла — как в пакете запускателя. TEST-переключений не было.

## 9. DOC IMPACT (общие документы не менялись)

- **№03 §6/§8 (Project Context и его ревизии), §10 (Chat metadata), §2 (Workspace):** правило записи заменяемых файлов (проверка места временного файла через дескриптор, чтение обратно), чтение прежнего текста без ссылок, эксклюзивная публикация ревизии без перезаписи, новые коды `project_context_unreadable`, `revision_exists`.
- **№37 Stage2:** `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` выполнен в границе §6. Подмена после последней проверки остаётся OPEN residual (Stage0 §9).
- **№05:** FOLLOWUP → кандидат на закрытие после независимой проверки. Новый кандидат: тот же перевод для карточки staging в `create_chat` (§6 п.4).
- **№06 / №34 / №40:** записи о сдаче и проверке вносит координатор.

## 10. NOT RUN и SKIP

- SKIP (нет привилегии на symlink): `test_a_project_context_symlink…` (новый) и прежние 3 symlink-теста хранилища; в `all` — прежние 2. Junction и жёсткие ссылки выполнены.
- NOT RUN:
  - POSIX, UNC, `subst`, длинные пути, сетевые папки, другие файловые системы;
  - страницы (JS), `ui_smoke_test`, Tk-контур: `ultra_ui.py`, `server.py`, `ui.py` не менялись;
  - повторные серии на флейки; `test_final_audit` (может вызывать Git); live/paid API.

## 11. Пакет: SOURCE / TEST / EVIDENCE

`reports/CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001/`:

- `report.md`; `manifest.json` (SHA-256 изменённых файлов и заменённого содержимого, неизменность опубликованных файлов, все файлы пакета, результат сканирования); `handoff_task.md` (снимок постановки, пишет скрипт ротации).
- **SOURCE:** `context_storage.py`. **TEST:** `test_ultra_chat_storage.py`.
- **EVIDENCE:**
  - `prestart.json`;
  - `red_before_change.json`;
  - `gate_focused.json`;
  - `gate_all.json` (прогон 2); `gate_all_run1.json` (прогон 1, WinError 10053); `gate_picker_rerun1..3.json`;
  - `mutants_run1.json`, `mutants.json`;
  - `change_inventory.json`;
  - `final_state.json`;
  - `rotation.json`.
- **Инструменты:** `prestart.py`, `record_gate.py`, `run_mutants.py`, `change_inventory.py`, `final_state.py`, `make_manifest.py`.

Публикация — только после `web_alarm.evidence_sanitizer scan` с exit 0. Файлы пакета — LF, без путей.

**Незакоммиченные изменения (коммит делает пользователь):** `context_storage.py`, `test_ultra_chat_storage.py`, папка пакета, карточка после ротации.
