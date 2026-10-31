# 🟨 Ultra Chat, Stage2 Repair: безопасный путь записи контекста сообщения (`CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001`)

**Статус исполнителя: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** F-01 воспроизведён до правки (9/9 записей приняты через junction, 7/9 записали снаружи) и устранён (9/9 отказ `unsafe_storage_link`, внешний каталог неизменен). Проверки на финальных байтах: адресный набор 149 (145 PASS / 4 SKIP), полная регрессия `all` 1078 (1076 PASS / 2 SKIP; в первом прогоне — 1 известный флейк F-S1), мутанты 8/9 (R01c — заранее разобранный эквивалент). TOCTOU после последней проверки — открытый residual (§7). Продуктовый PASS не объявляется.

| Поле | Значение |
|---|---|
| Исполнитель | Claude 008 |
| Координатор и независимый проверяющий | ChatGPT |
| Направление | А — Ultra Chat / Chat Storage |
| Источник | БЛОК 1 карточки Claude (вставка пользователя со строкой TASK ID); `FOLLOWUP-WUA-S2-CONTEXT-PATH-001`; finding F-01 из `reports/CHATGPT-WEB18-S2-REVIEW-20261031.md` |
| База | `main@254e48166407d3aabf6484c8627da86acf8b05df` (№474) по содержимому; инженерные байты Stage2 (№473) совпали 8/8 с его manifest. Git не использовался |
| Live / платные API, реальные Workspace, история пользователя | **не использовались**; всё во TEMP на синтетических Workspace |

## 1. Итог

Дефект F-01 подтверждён и устранён.

- **До исправления:** все три писателя контекста сообщения (`create_message_context_variant`, `activate_message_context_variant`, `restore_message_raw`) **принимали** заранее подменённую ссылку (junction) на любом уровне `message_context/<message_id>/variants`. В 7 из 9 случаев они **записали файлы во внешний каталог**: новый Context Variant и/или изменённый `state.json`.
- **После исправления:** все 9 случаев — отказ `unsafe_storage_link`; внешний каталог не меняется ни по именам, ни по времени, ни по SHA-256.
- Обычные каталоги, старые RAW, Workspace/Chat/Message ID и существующие Context Variant работают и сохраняются как были.

Я признаю, что это мой пропуск в Stage2: я обернул эти три функции в блокировку и проверку Chat, но не проверил их собственный путь записи ниже папки чата. В отчёте Stage2 (§4.1, §7) утверждалось, что обходных путей записи не осталось, — это было неверно.

## 2. Pre-start

- `tools/task_slot_rotate.py check` — **OK**: в БЛОКЕ 1 эта TASK (165 строк), БЛОК 1.1 — Stage2 (`CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001`).
- Исходники совпадают по содержимому с опубликованным Stage2-пакетом: 8/8 файлов. Остальные опубликованные файлы запускателя, Stage1 и EVM не изменены.
- Запускатель **STANDARD**.
- Параллельной работы по этим файлам нет: направление B без TASK; Stage2 закрыт REVISE.
- Прочитано адресно: карточка (Рабочий порядок, БЛОК 1), №03 §20–24 (MESSAGE CONTEXT), №37 §2.4, №36.3 (требование `python_compile` для изменения Python runtime; `ui_smoke_test` нужен только для `server.py` и `ultra_ui.py`, они не менялись), №08 (вход исполнителя), FOLLOWUP в №05, review WEB18, отчёт и тесты Stage2.
- Evidence: `evidence/prestart.json`.

## 3. Аудит и воспроизведение дефекта

**Аудит пути записи (до правки).**

| Функция | Что пишет | Как | Проверка ниже папки чата |
|---|---|---|---|
| `_activate_message_context_variant` | `message_context/<id>/state.json` | `_atomic_write_json` → `mkdir(parents=True)` + temp + `os.replace` | **нет** |
| `_create_message_context_variant` | `message_context/<id>/variants/<ctxv>.json`, затем activate | то же | **нет** |
| `_restore_message_raw` | `state.json` (без чтения прежнего) | то же | **нет**; к тому же перезаписывал `state.json` более новой версии |

`_chat_writer` проверял только папку чата и её карточку. `mkdir(parents=True)` и открытие временного файла идут по любой ссылке в родительском пути.

Аудит **всех** остальных мест записи `context_storage.py` (`_atomic_write_*`, `_publish_new_file`, `mkdir`, `rename`, `rmtree`, файл блокировки) других непроверенных путей не нашёл. Каждое из них пишет в папку, проверенную под блокировкой.

**Воспроизведение до правки — два независимых способа.**

1. `tools/reproduce_f01.py` на копии исходных байт №474 (без юнит-тестов). Оракул — перечень имён и SHA-256 внешней папки до и после. Итог `evidence/reproduce_before_fix.json`: **9/9 вызовов приняты, 7/9 записали снаружи**.

   | Junction на | create | activate | restore |
   |---|---|---|---|
   | `message_context` | новый вариант + `state.json` снаружи | `state.json` снаружи | `state.json` снаружи |
   | папке сообщения | новый вариант + `state.json` снаружи | `state.json` снаружи | `state.json` снаружи |
   | `variants` | новый вариант снаружи | принят (читает чужой вариант) | принят |

2. Новые тесты на неисправленном коде — `evidence/red_before_fix.json`: 13 запущено, 22 FAIL и 2 ERROR в subTest, 2 SKIP. Все сценарии с junction — «StorageWriteError not raised»; `restore` перезаписал `state.json` более новой версии.

## 4. Исправление (`context_storage.py`)

Использованы существующие проверенные механизмы Stage2. Новой архитектуры безопасности нет.

**Проверка 1 — до любого чтения или записи** (`_refuse_linked_message_context`, вызывается в трёх публичных обёртках сразу после `_chat_writer`, под блокировкой):

- каждый **существующий** уровень `message_context`, `<message_id>`, `variants` должен быть обычной папкой, конечный путь которой лежит под закреплённым корнем (`_verify_write_directory`);
- ссылка, junction или reparse point → `unsafe_storage_link`, ничего не создаётся.

**Проверка 2 — непосредственно перед каждой записью** (`_message_context_folder_for_write`, из внутренних функций):

- требует, чтобы этот поток держал блокировку Workspace (иначе `RuntimeError`);
- ещё раз проверяет `.ultra`, `chats`, `<chat>`;
- создаёт недостающие уровни только внутри уже проверенного родителя и сразу проверяет каждый (`_ensure_write_directory`). Ссылка, появившаяся после проверки 1, отвергается до создания чего-либо.

**Сама запись:**

- Context Variant — новый неизменяемый файл: эксклюзивная публикация `_publish_new_file` (место временного файла проверяется до записи байтов, перезапись невозможна, после записи — чтение обратно);
- `state.json` — новая `_replace_verified`: тот же порядок, но с заменой (`os.replace` с ограниченным повтором) и чтением обратно. Если `state.json` — ссылка, отказ `unsafe_storage_link`; если папка или иной не-файл — `context_state_damaged`.

**Состояние `state.json` — явные правила:**

| Состояние | create / activate | restore |
|---|---|---|
| нет файла | как прежде (RAW по умолчанию) | пишет RAW |
| корректный v1 | как прежде | пишет RAW |
| **более новая версия** (`schema_version` > 1) | отказ (как прежде, `RuntimeError`) | **отказ `unsupported_version`**, файл не меняется (раньше перезаписывался) |
| повреждён (не JSON, массив, чужой `message_id`, неизвестное представление) | отказ (как прежде) | **явный ремонт указателя**: пишет RAW; Context Variant не трогаются (решение исполнителя, §7 п.3) |
| ссылка / папка | отказ | отказ `unsafe_storage_link` / `context_state_damaged` |

Совместимость: подписи и возвращаемые значения трёх функций прежние, включая `"path"` варианта. Байтовый формат файлов прежний (JSON, отступ 2, LF, `\n` в конце). Блокировка Workspace, проверка владельца Chat, вложенный вызов `create → activate` — без изменений.

Изменено: `context_storage.py` +133/−10 строк; `test_ultra_chat_storage.py` +348/−0. Остальные файлы Stage2 (`server.py`, `ui.py`, `ultra_ui.py`, `ultra_chat.py`, тесты) не менялись — `evidence/change_inventory.json`.

## 5. Проверки

Все прогоны — на финальных байтах, во TEMP, на синтетических Workspace, без сети, Git и live API. Python — `.venv` 3.12.10 с `-B`, через охраняемый раннер `wa4a_acceptance.py` (`run_gate.py`, изоляция TEMP).

### 5.1. Команды и результаты

| Проверка | Команда | Exit | Итог |
|---|---|---|---|
| Компиляция (в памяти, без `.pyc`) | `tools/final_state.py` | 0 | 2/2 OK |
| Воспроизведение **до** правки | `tools/reproduce_f01.py` на копии байт №474 | 0 | 9/9 приняты, **7/9 записали снаружи** |
| Новые тесты **до** правки | `run_gate.py … MessageContextPathTests MessageContextLockTests` | 1 | RED: 22 FAIL + 2 ERROR (subTest), 2 SKIP |
| Воспроизведение **после** правки | `tools/reproduce_f01.py` на рабочей копии | 0 | **9/9 отказ `unsafe_storage_link`, 0 записей снаружи** |
| Адресный набор хранения | `run_gate.py … test_ultra_chat_storage test_message_context test_compressor_runtime test_chat_create_atomicity test_failed_run_terminal_message test_context_registry test_ultra_chat_read test_web_alarm_ultra_chat_storage test_web_alarm_ultra_chat` | 0 | **149: 145 PASS / 4 SKIP**, изоляция 0 нарушений |
| Мутанты | `tools/run_mutants.py` (цели `test_ultra_chat_storage`, `test_message_context`) | 0 | **8/9 KILLED**, контроль PASS (61 тест), R01c — ожидаемый эквивалент (§5.3) |
| Полная регрессия `all` | `run_gate.py … all` | 1 / 0 | прогон 1: 1078 = 1077 PASS / **1 ERROR** (флейк F-S1) / 2 SKIP; прогон 2: **1078 = 1076 PASS / 2 SKIP**, 0 FAIL / 0 ERROR |

SKIP — только создание symlink (нет привилегии на этом хосте): 2 новых и 2 прежних. Junction-варианты тех же проверок выполнены.

### 5.2. Новые тесты (`test_ultra_chat_storage.py`, 15 методов)

**`MessageContextPathTests` (12).** Оракул `tree()`: каждое имя внешней папки с типом, временем `lstat` (включая папки, чтобы увидеть даже созданный и удалённый файл), размером и SHA-256. Код `context_storage` в оракуле не используется. Дополнительно — снимок самого Workspace.

| Требование §6 | Тест |
|---|---|
| 1. Junction на `message_context` и отдельно на `variants` | `test_a_junction_at_message_context…`, `…the_message_folder…`, `…variants…` — каждый по 4 вызова: create, create без активации, activate, restore |
| 1. Сообщение без контекста | `test_a_junction_at_message_context_of_a_message_without_context_yet` |
| 2–3. Все три операции; внешний каталог неизменен | все тесты выше: отказ `unsafe_storage_link`, `tree(outside)` и снимок Workspace — до = после |
| 4. Отсутствующий / обычный каталог, повреждённый файл, существующий вариант | `test_ordinary_folders_keep_working…`, `test_damaged_or_newer_state_is_handled_explicitly`, `test_a_state_file_that_is_a_folder…` |
| 5. Старые RAW, Workspace/Chat/Message ID | `test_ordinary_folders_keep_working_and_old_data_stays_byte_identical` (байты RAW, `workspace.json`, карточки чата; все варианты после restore) |
| 7. Symlink, где разрешено; junction отдельно | `test_directory_symlinks…`, `test_a_state_file_symlink…` — SKIP (нет привилегии), junction — выше |
| Ссылка после первой проверки | `test_a_link_made_after_the_first_check…` (папка `message_context`), `test_a_chat_folder_swapped_after_the_first_check…` (вся папка чата; ничего не создаётся внутри) |
| Блокировка у внутренних писателей | `test_an_internal_context_writer_outside_the_workspace_lock_refuses` |

**`MessageContextLockTests` (3) — п.6.**

- Держатель блокировки в другом процессе: все три писателя ждут и отказывают `WorkspaceBusyError`, ничего не меняется. После убийства держателя restore проходит.
- Два процесса создают по 12 вариантов и делают restore: все 24 варианта на месте с правильными текстами, итоговый `state.json` корректен и ссылается на существующий вариант, временных файлов нет.
- Процесс умирает (`os._exit`) перед заменой `state.json` → старое состояние цело, виден только скрытый временный файл. Процесс умирает перед публикацией варианта → видимого варианта нет. После «перезапуска» restore работает.

### 5.3. Мутанты (TEST-QA)

`tools/run_mutants.py`: каждый мутант убирает одну часть защиты в одноразовом зеркале кода во TEMP; цели — `test_ultra_chat_storage` и `test_message_context` (61 тест). Контроль (без мутации) — PASS. Остатков во TEMP нет.

| Мутант | Итог | Кем убит |
|---|---|---|
| R01 нет проверки 1 во всех трёх писателях | KILLED | junction на `variants` |
| R01a нет проверки 1 в activate | KILLED | junction на `variants` |
| R01b нет проверки 1 в restore | KILLED | junction на `variants` |
| R01c нет проверки 1 в create | **SURVIVED** | эквивалент для записи, см. ниже |
| R02 папки создаются простым `mkdir` перед записью | KILLED | ссылка после первой проверки |
| R03 restore перезаписывает более новое состояние | KILLED | повреждённое / новое состояние |
| R04 вид `state.json` не проверяется | KILLED | `state.json` — папка |
| R05 нет проверки блокировки у внутренних писателей | KILLED | внутренний писатель вне блокировки |
| R06 родители `message_context` не перепроверяются | KILLED | подмена папки чата после первой проверки |

**R01c — заранее разобранный эквивалент.** `create` пишет только новый файл варианта и затем `state.json`, оба через проверку 2. Без проверки 1 он лишь читает через ссылку (без записи) и отказывает на проверке 2. Защиту записи у `create` проверяет R02 (убит). Это не пробел в тестах.

### 5.4. Полная регрессия

Прогон 1 (`evidence/gate_all_run1.json`): 1078 тестов, 1077 PASS, **1 ERROR**, 2 SKIP, 0 нарушений изоляции, 22,1 мин. ERROR — `test_web_alarm_folder_picker…test_remote_bind_metadata_is_rejected_even_for_loopback_client`, `ConnectionAbortedError [WinError 10053]`. Это известный флейк F-S1: сервер отвечает 403, не дочитав тело POST. Модуль не импортирует `context_storage`.

- Повтор модуля `test_web_alarm_folder_picker` трижды (`evidence/gate_picker_rerun1..3.json`): 16/16 PASS каждый раз.
- Прогон 2 (`evidence/gate_all.json`): **1078 = 1076 PASS / 2 SKIP**, 0 FAIL / 0 ERROR, 0 нарушений изоляции, 23.2 мин.
- Число тестов `all` не изменилось (1078): новые методы этой задачи — в `test_ultra_chat_storage.py`, он в `all` не входит (маска `test_web_alarm*`) и прогнан по имени в адресном наборе.
- SKIP — прежние два (symlink без привилегии).

## 6. MANUAL ENGINEERING REVIEW

Самостоятельный adversarial-проход по финальному коду: не только новый запрет, но **все** места записи `context_storage.py`.

- **Три затронутые операции.** Других путей записи, кроме `state.json` и `variants/<ctxv>.json`, у них нет. Оба идут через проверку 2 и проверенную публикацию. Чтения перед записью (`get_message_context_state`, `load_context_variant`, `load_raw_message`) выполняются после проверки 1. Если ссылка появилась уже после неё, чтение может пройти по ссылке (только чтение), но запись отвергается проверкой 2.
- **Остальные писатели** (`ensure_workspace_storage`, `rename_workspace`, `save_project_context`, `create_chat_record`, `rename_chat`, `commit_raw_message`, файл блокировки): все пишут в папки, проверенные под блокировкой в Stage2. Новых непроверенных путей нет.
- **Блокировка, владелец Chat, вложенный вызов** — не тронуты; проверка 2 дополнительно требует, чтобы блокировку держал текущий поток.
- **Отказ ничего не меняет:** снимок Workspace и `tree()` внешней папки до и после в каждом негативном тесте.
- **Совместимость:** подписи, возвращаемые словари, байтовый формат, коды прежние; новый код отказа — `context_state_damaged`.

## 7. Остаточные риски и ограничения

1. **TOCTOU после проверки 2 (не устранён).** Если другая программа того же пользователя подменит папку между проверкой 2 и созданием временного файла, временный файл будет создан во внешней папке. Проверка его места сразу отвергнет запись, и файл удалится, но время изменения внешней папки изменится. Если подмена случится после проверки временного файла и до `rename`/`replace`, запись уже ляжет снаружи и будет только **обнаружена** чтением обратно (`unsafe_storage_link`). Контракт Stage0 §9 такую защиту не обещает. Без открытия файлов относительно дескриптора папки (в Python на Windows нет `openat`) полностью это не закрыть.
2. **Те же окна у других заменяемых файлов Stage2** (`workspace.json` в `rename_workspace`, `project_context.md` и его история в `save_project_context`, карточка в `rename_chat`). Они пишут в проверенные папки, но без проверки места временного файла. Чтение обратно есть только у `rename_chat`. Предложение — перевести их на `_replace_verified` отдельной правкой (§9).
3. **Restore ремонтирует повреждённый `state.json`** (не JSON, чужой `message_id`, неизвестное представление): пишет RAW-состояние, варианты сохраняются. Решение исполнителя: restore — единственный способ пользователя Tk вернуть сообщение в RAW, а create и activate на повреждённом состоянии отказывают. Более новую версию restore не трогает. Если координатор предпочтёт отказ и здесь — это одна строка (§9).
4. **Чтения Tk (P1–P6) и Run Store P9** этой задачей не трогались (БЛОК 1, NEXT).
5. **Платформа:** symlink (4 SKIP) — нет привилегии; junction проверены. POSIX, UNC, `subst`, длинные пути не проверялись.

## 8. Сохранность контрактов Stage1/Stage2, запускатель

- Читатели Stage1 и HTTP Stage1: `test_ultra_chat_read`, `test_web_alarm_ultra_chat` — без правок, PASS.
- Stage2: все 36 прежних методов `test_ultra_chat_storage`, `test_web_alarm_ultra_chat_storage` (11) — PASS без правок; `test_message_context` (10) и `test_compressor_runtime` — PASS без правок.
- Файлы Stage2 вне scope (`server.py`, `ui.py`, `ultra_ui.py`, `ultra_chat.py`, JS и HTTP-тесты) байт-в-байт как в пакете Stage2.
- **Запускатель STANDARD:** `launch_config.json` active `standard`, `load_launch()` standard, три файла запускателя — как в пакете запускателя. TEST-переключений не было.

## 9. DOC IMPACT

Общие документы не менялись. Предложения координатору:

- **№03 §20–21 (MESSAGE CONTEXT):** добавить правило записи. `message_context/<message_id>/{state.json, variants/}` пишется только через проверенные папки (проверка 1 до чтения, проверка 2 перед записью). Вариант — эксклюзивная публикация; `state.json` — проверенная замена с чтением обратно. Restore не перезаписывает более новую версию состояния и ремонтирует повреждённый указатель. Новые коды: `unsafe_storage_link` (для контекста сообщения), `context_state_damaged`.
- **№37 Stage2:** F-01 устранён в объёме pre-existing ссылок и ссылок, созданных после первой проверки. TOCTOU после проверки 2 — открытый residual (§7 п.1–2).
- **№05:** `FOLLOWUP-WUA-S2-CONTEXT-PATH-001` → кандидат на закрытие после независимой проверки. Новый кандидат FOLLOWUP: перевод `rename_workspace`, `save_project_context`, `rename_chat` на `_replace_verified` (§7 п.2).
- **№06 / №34 / №40** — записи вносит координатор.

## 10. NOT RUN

- Symlink (2 новых + 2 прежних SKIP) — нет привилегии; junction выполнены.
- POSIX, UNC, `subst`, длинные пути, сетевые папки.
- Страницы (JS), `ui_smoke_test` и Tk-контур не перезапускались: `server.py`, `ui.py`, `ultra_ui.py` не менялись (№36.3 требует `ui_smoke_test` только для них). Их байты подтверждены `change_inventory.json`.
- Повторные серии на флейки; `test_final_audit` (может вызывать Git); live/paid API.

## 11. Пакет и evidence

`reports/CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001/`:

- `report.md`; `manifest.json` (изменённые файлы с прежними хешами, неизменность опубликованных файлов, все файлы пакета, результат сканирования); `handoff_task.md` (снимок постановки, пишет скрипт ротации).
- `evidence/`:
  - `prestart.json` — до правки;
  - `red_before_fix.json` — новые тесты на неисправленном коде;
  - `reproduce_before_fix.json` и `reproduce_after_fix.json` — независимое воспроизведение;
  - `gate_focused.json` — адресный набор;
  - `gate_all.json` — полная регрессия, прогон 2 (зелёный); `gate_all_run1.json` — прогон 1 (флейк F-S1); `gate_picker_rerun1..3.json` — повторы модуля folder picker;
  - `mutants.json`;
  - `change_inventory.json`;
  - `final_state.json`;
  - `rotation.json`.
- `tools/`: `prestart.py`, `reproduce_f01.py`, `record_gate.py`, `run_mutants.py`, `change_inventory.py`, `final_state.py`, `make_manifest.py`.

Публикация — только после `web_alarm.evidence_sanitizer scan` с exit 0. Файлы пакета — LF, без путей.

**Незакоммиченные изменения (коммит делает пользователь):** `context_storage.py`, `test_ultra_chat_storage.py`, папка пакета, карточка после ротации.
