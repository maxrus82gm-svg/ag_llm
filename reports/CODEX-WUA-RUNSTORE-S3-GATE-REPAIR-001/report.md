# CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001

Статус: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**. Локальное инженерное исправление prerequisites завершено; независимой приёмки ещё нет. Исполнитель Codex 007, verifier по назначению — **ChatGPT WEB 23**.

Исправлены оба опубликованных отказа общего Run Store: выход записи через `.ultra/audit` junction и одинаковая sequence у двух процессов одного RUN. Stage 3 остаётся **HOLD** до независимой приёмки и отдельного USER GO. Turn/HTTP/provider/TEST UI в этой задаче не реализованы.

## Назначение, shared scope и сохранность исходной базы

Перед изменениями прочитаны действующий БЛОК 1 Codex, адресные правила №08/18, соответствующие разделы №36.1/36.3, Stage 3 №37, №40, прежний S3 prerequisite report и P9-контракты/тесты. №18 от 04.11.2026 с HISTORY ID имеет приоритет над прежними формулировками @1/@2 в карточках и отдельных правилах. Новых AMENDMENT к текущему TASK нет; прежние UX/S3 поручения не являются поправками этого TASK.

Проверка владельцев: №40 содержит прежнее состояние `repair NOT ASSIGNED`; оно предшествует прямому поручению пользователя и действующему назначению в БЛОК 1 Codex. Карточка Claude сохраняет `CLAUDE-WUA-CHAT-RUNSTORE-P9-001` со старым PROPOSED и SLOT HOLD; её БЛОК 4 содержит фактическую сдачу/ограниченную приёмку от 03.11.2026. Нового одновременного назначения на запись этого repair не обнаружено. Прежняя карточка Claude и его результаты не изменялись. Межпроцессные writers в тестах — только собственные синтетические процессы.

Продуктовый write-scope соблюдён:

- `run_store.py` — проверки путей, единая блокировка append, целостность и явное восстановление.
- `test_run_store_v2.py` — сохранены все прежние 21 cases, добавлены 30 адресных cases; всего 51.
- `test_web_alarm_ultra_chat_turn.py` — только allowlist нового адреса evidence. Все три исходных оракула и их утверждения сохранены.
- Все новые инструменты, снимки и результаты — в этом отчётном каталоге.

До правок сохранены побайтовые `.source.txt` копии 12 адресных файлов и SHA-256 исходников/611 защищённых файлов (`evidence/baseline.json`). Это снимок реально существовавшей локальной базы с её прежними изменениями, без reset/checkout/замены чужих правок. Предыдущие UX/S3/P9 отчёты использовались только для чтения; guard скопирован в новый пакет.

## Исходный RED и дополнительные найденные отказы

`evidence/published_red.txt` и `.json`: запуск исходного `test_web_alarm_ultra_chat_turn` до продуктовых изменений, **3 tests = 1 PASS / 2 FAIL / 0 ERROR / 0 SKIP**, exit **1**. Сохранённый baseline `run_store.py` SHA-256 `f63d7d15670a290355fa034d21d9e979d890e11d7bf52b02bbb1598a00cab12e`.

1. Junction `.ultra/audit` создавал внешние синтетические `index.json` и `<chat>/run_s3/summary.json`; ожидался только marker.
2. Два процесса подтвердили записи одного RUN с sequences **[1, 1]** вместо **[1, 2]**.

В ходе реализации также сохранены реальные отрицательные результаты:

- `pending_validation_red.txt/.json`: **1 FAIL**, exit 1 — повреждённый append-intent без SHA разрешал его удаление. Добавлена строгая проверка полей intent до любых исправлений.
- `projected_limit_red.txt/.json`: **2 FAIL**, exit 1 — запись превышала введённый bounded-read лимит, а отказ происходил уже при readback. Добавлена проверка прогнозируемого размера до публикации intent/записи stream/index.

Последующие зелёные результаты не заменяют эти исходные логи.

## Итоговый контракт Run Store

Audit-пути проверяются лексически до следования вложенным сегментам. Используются существующие `context_storage` anchor, directory/reparse проверки, bounded no-follow read и проверка конечного пути открытого дескриптора. Проверяются `.ultra/audit`, вложенные chat/RUN/generation каталоги и необходимые компоненты. Junction/reparse, hardlink, нерегулярный файл и опасный `summary_path` дают явный отказ. Для JSON сохранены прежний формат, fsync, bounded Windows replace retries и P9 generation fallback; добавлены exclusive temporary create и readback.

Весь append одного RUN — выбор sequence, offset, stream write, index write, fsync и readback — выполняется под **существующей Workspace OS writer-lock** из `context_storage`. Это намеренно более широкая сериализация всех RUN одного Workspace: второго lock/storage-механизма нет. Вложенный вход остаётся reentrant; занятый Workspace даёт ограниченный по времени `WorkspaceBusyError`; смерть процесса освобождает OS lock.

Перед append проверяется уже подтверждённая последовательность, уникальность record_id, source/stream, непрерывность offsets, lengths, newline, identity и SHA при наличии. Старые корректные v2 записи без SHA остаются читаемыми; новые записи содержат SHA. RAW payload не преобразуется и не воспроизводится повторно.

Для безопасного восстановления добавлен **`append.pending.json` внутри существующего RUN**, а не отдельное хранилище: schema_version 1, run_id, размер/SHA старого подтверждённого index-prefix и планируемый index receipt. Полный RAW в intent не дублируется. Порядок: intent fsync → stream fsync → index fsync → readback SHA/identity → удаление intent → acknowledgement. Любая ошибка перед ответом видна вызывающему коду; незавершённая операция не выдаётся за успешную. Следующий append при pending/orphan останавливается с `RunStoreRecoveryRequired`, без скрытого retry.

Новый явный API `recover_run_records(root, run_id)` использует тот же lock:

| Состояние | Действие |
| --- | --- |
| Чистый RUN без intent | Только проверка; `committed=False`, ничего не удаляется |
| Валидный intent, запись не начата/есть её частичный хвост | Проверить прежний подтверждённый prefix/streams; удалить только доказанный неподтверждённый хвост; сохранить прежние bytes |
| Полный index receipt и проверенная stream-запись, ответ потерян | Сохранить запись; удалить marker; вернуть `committed=True`; не переигрывать событие |
| Неизвестный orphan без intent, torn index, изменённый prefix, посторонний stream/index tail, неверный hash/intent | Явный отказ до исправлений; данные сохраняются для ручного разбора |

Возврат: `{'removed_bytes': {stream: count}, 'committed': bool}`; `removed_bytes` описывает stream-хвосты, не является полным файловым diff. Повтор recovery чистого RUN безопасен. Вызов из будущего Turn/UI не добавлялся.

Лимит чтения — **64 MiB на компонент и суммарные streams одного RUN**. Append/atomic JSON заранее отказывают, если новая запись нарушит читаемый предел. Уже существующие сверхлимитные/повреждённые данные автоматически не мигрируются и не обрезаются.

## Проверки и реальные результаты

Среда: **Windows 10 build 19045, Python 3.12.10 x64, pytest 9.1.1, Node v22.20.0**. Точные команды, длительности, исходные SHA, exit и raw output — в `evidence/*_final*.json/.txt`, сводка — `evidence/results_summary.json`.

| Прогон | Фактический результат | Exit |
| --- | --- | --- |
| Опубликованные prerequisite RED до исправления | 1 PASS / 2 FAIL | 1 |
| Run Store + audit compatibility, final1 | 55 PASS | 0 |
| Run Store + дополнительные recovery negatives, final2 | 60 PASS | 0 |
| Итоговый Run Store/audit, final3 | **62 PASS / 0 FAIL / 0 ERROR / 0 SKIP** | **0** |
| Те же исходные prerequisite-оракулы, final1 и final3 | **3 PASS** каждый | **0** |
| Python regression, final1 | **165 PASS / 1 ERROR / 5 SKIP**, 171 tests | **1** |
| Python regression, final2 после итоговой продуктовой правки | **166 PASS / 0 FAIL / 0 ERROR / 5 SKIP**, 171 tests | **0** |
| JS regression, final1 | **158 PASS / 0 FAIL / 0 SKIP** | **0** |
| In-memory Python compile изменённых исходников | 3 PASS; pyc не создавались | 0 |

Итоговый набор без суммирования повторов: **394 tests = 389 PASS / 5 SKIP / 0 FAIL / 0 ERROR**. Не все предыдущие прогоны были зелёными: отрицательные и промежуточные результаты сохранены.

Ключевые новые проверки: Windows junction на четырёх уровнях; hardlink index/summary/streams/intent/generation; absolute/relative summary escape; короткая запись stream; отказ перед/посреди index; прекращение процесса после intent/stream/index; сохранение ранее подтверждённых bytes; отказ recovery на неизвестных подменах; lock timeout без audit-write; три процесса × 12 Unicode events разных источников с sequences 1..36, offsets и SHA/readback; повторное открытие/продолжение; projected stream/index bounds. Прежние P9 replace/compaction/reentrant/concurrent index проверки остаются в наборе.

Команды повторения из корня проекта:

```powershell
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/run_checks.py run_store --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/run_checks.py prerequisites --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/run_checks.py python --label review1
.venv\Scripts\python.exe -B -X utf8 reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/run_checks.py js --label review1
```

Использовать новый label, чтобы сохранять прошлые guard receipts. Pytest запускался с отключённым plugin autoload и cacheprovider; без indiscriminate discovery. Python guard устанавливался до импорта runtime, наследовался дочерними Python, запрещал внешние sockets/DNS, Git executable/metadata и другие executables кроме Python/Node. Во всех сохранённых штатно завершённых guard-процессах **0 denials**. `os._exit` намеренно не выполняет atexit receipt; Node-набор — VM/mock-fetch tests, Python guard не является его сетевым firewall. Реальные provider/LLM запросы не запускались. Loopback HTTP fixtures использовали только TEMP.

## Сохранность и ограничения

- **601/601 пользовательских файлов неизменны**: `.ultra` 586, `Чат_pro` 9, `Чат_Pro_01` 6; проверены набор имён, размеры и SHA. Существующие пользовательские данные не открывались для записи/восстановления.
- Среди ещё 10 editor-state файлов обнаружено изменение **`.obsidian/workspace.json`**. Агент туда не писал; процесс-источник не атрибутирован. Изменение не откатывалось. Первоначальный conservation-check честно завершился exit 1; его JSON и результат сохранены. Уточнённая проверка отдельно показывает неизменность user storage и внешнюю editor-state delta: `conservation_before_finish_reviewed.json`. Нельзя заявлять, что все 611 файлов совпадают.
- Все 12 исходных backup-копий совпадают с baseline. Вне scope проверенные `context_storage.py`, `audit_storage.py`, Web UI/server/Ultra Chat, launcher/config и скрипт finish совпадают с baseline. Launcher всё время **STANDARD**, пользовательский процесс не перезапускался.
- Первый Python regression получил **WinError 10053** в `PickerHttpTests.test_wrong_origin_host_token_and_fetch_metadata_never_reach_helper`, duplicate Origin subcase. Полный повтор прошёл. Это не исправление picker и не доказательство исчезновения intermittent риска; прежний `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001` остаётся OPEN. Изменять picker вне scope не потребовалось для Run Store repair.
- 5 Python SKIP — native file/directory symlink creation, права не предоставлены Windows. Реальные junction и hardlink cases выполнены; права ОС не менялись.
- Не заявляется абсолютная защита от same-user TOCTOU между final check и path-based rename/unlink. Открытые дескрипторы проверяются, заранее существующие подмены отвергаются; враждебные одновременные перестановки всей файловой структуры не сертифицированы.
- Проверена смерть процесса/ошибки файловой записи. Аппаратное отключение питания, durability каталога на всех файловых системах/сетевых шарах, clean-Windows portability и огромные production RUN не проверялись. Полный scan на append имеет стоимость от размера существующего RUN; нагрузка ограничена зафиксированными синтетическими кейсами. Не сотрудничающий с shared lock внешний writer не получает гарантии сериализации.
- Lock-free чтение во время незавершённого append может дать явный отказ на partial/orphan; оно не выполняет автоматический repair. `audit_storage.py` и его собственные операции остались read-only в scope этой задачи.
- **NOT RUN:** реальный браузер/Tk/native picker GUI, live/user Workspace write, провайдеры/LLM, Stage3 Turn, весь Ultra discovery/CI и independent runtime. `test_final_audit*` не запускались: отдельные scenarios вызывают реальный Git. Git/GitHub не использовались ни напрямую, ни через тесты.

## DOC IMPACT / SHARED DOC DELTA / NEXT

Локальный пакет документирует новый explicit recovery API, intent v1 и ограничение размера. Общая документация руками не изменялась. После независимой приёмки WEB23 должен адресно обновить №05/37/40 и соответствующую запись истории: оценить `FOLLOWUP-WUA-P9-AUDIT-PATH-001` и `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001` по опубликованному source/evidence, сохранить residual TOCTOU/portability/picker и остальные OPEN. Авторская сдача не закрывает FOLLOWUP автоматически. Техническая необходимость правки вне scope не установлена; расширение не выполнялось.

Штатная сдача слота выполняется после готового пакета неизменённым `tools/task_slot_rotate.py finish --no-chat-amendment --apply --headless`. Фактические exit/status, HISTORY ID и readback находятся в **`evidence/finish.json`**, **`evidence/finish_result.json`**, **`finish_receipt.md`** и созданном скриптом **`task_record.json`**. Manifest после native finish обновляется; этот report остаётся неизменным для сохранения его зарегистрированного SHA.

NEXT: передать локальный пакет пользователю для публикации и независимой проверки **ChatGPT WEB 23**. Сверить manifest/сохранённые RED/фактические Windows результаты, независимо выполнить адресные тесты. Stage 3, providers и UI — HOLD до отдельного решения пользователя.
