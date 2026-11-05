# CODEX-WUA-S3-WS-WRITER-BUSY-REPAIR-001

**BLOCKED по точной причине исходного CI FAIL / PARTIAL диагностики и ремонта.** Исполнитель Codex 007. Итоговый локальный пакет готов к независимой проверке; независимый PASS не заявляется. `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` остаётся **OPEN**.

Локальный `WorkspaceBusyError` воспроизведён и объяснён как **ограниченный отказ при реальной конкуренции за lock**. Подтверждены и исправлены три отдельные проблемы диагностики: неверная классификация неожиданных OS-ошибок как busy, отсутствие принудительного UTF-8 у тестового child и усечение его stderr. Это **не доказательство исправления конкретного CI timeout**: источник замедления и per-lock errno/timing исходного CI неизвестны. По критериям TASK зависимая попытка «исправить исходный CI» остановлена, без увеличения timeout или ослабления lock.

## Назначение / источники / scope

Подтверждён точный TASK ID в БЛОКЕ 1; прочитаны действующие правила карточки/№08/18, применимые тестовые контракты №36/36.1/36.2 и shared scope №40. Проверены `_workspace_writer_lock`, `_try_lock_byte`, reentrant state, `_existing_workspace_writer`, release paths, create/rename/RAW callers и соответствующие тесты. Текущий P9 Claude SLOT HOLD не даёт ему нового пересекающегося назначения; Run Store/API/UI этой задачей не менялись.

Исходный опубликованный отказ первоначально доступен из локального review `CHATGPT-WEB23-CODEX-S3-TURN-REVIEW-20261105/review.md`. Его копия сохранена в `evidence/published_review.source.txt`; факт FAIL и ограничения — `published_first_fail.json`. Затем пользователь прислал оригинальный **excerpt**, сохранённый как `ci_original_user_excerpt.txt` и полный текст CHAT-ONLY AMENDMENT 01. Это не полный child traceback. Git/GitHub не использовались; Actions URL не открывались. Разрешённые официальные Python/Microsoft справочные страницы читались отдельно от GitHub.

До правок сохранены 12 `.source.txt` копий исходной локальной базы и sizes/SHA-256 для них и 605 защищённых файлов. Прежние незакоммиченные изменения не сбрасывались. Write-scope: **только `context_storage.py`, `test_ultra_chat_storage.py` и этот отчётный каталог**. Общие документы и чужие отчёты не редактировались; собственная карточка сдаётся только native finish.

## Исходный CI FAIL — что известно

- Run **42040238153**, Job **127288825334**, Windows/Python 3.12.10.
- Selector: `test_ultra_chat_storage.ConcurrencyTests.test_two_processes_write_raw_create_and_rename_without_losing_anything`.
- Начало 14:02:56.580 UTC; FAIL 14:03:13.332 UTC, около **16,75 с**. Набор: **171 tests за 285,636 с, failures=1, exit 1**.
- Child вернул exit 1; tail указывает `_existing_workspace_writer` → `_workspace_writer_lock` → `WorkspaceBusyError`. Старый helper сохранял только `err[-800:]`; исходная операция и полные сведения о держателе/errno отсутствуют.
- Прежние CI isolated replay 5/5 PASS не отменяют этот FAIL. Они сохранены как отдельный результат из review.

CI elapsed 16,75 с совместим с 10-секундным ожиданием после части работы/старта процессов. Полный CI набор существенно медленнее текущего локального (~68 с), но **это не доказывает**, что CI имел ту же задержку fsync, те же 20 критических секций или только EACCES. Источник CI slowdown (диск, scheduler, внешнее сканирование и т. п.) остаётся **UNKNOWN**, а не установленной причиной.

## Диагностика до ремонта

`run_diagnostics.py` запускает неизменённую функциональную часть исходного selector на disposable TEMP. Опциональные process-local wrappers из `guard/writer_trace.py` измеряют ожидание/удержание/OS errno/fsync, не меняя production source. Задержка fsync явно инъецируется в процесс теста, реальный `os.fsync` всё равно вызывается. Native locking/release и timeout 10 с сохраняются.

| Серия | Прогоны и фактические исходы | Измерения |
| --- | --- | --- |
| `baseline` | 5 PASS, exit 0 каждый | max wait **0,295 с**, max hold **0,055 с**, 80 outer lock operations на прогон |
| `slow350` (fsync +350 мс) | 2 PASS | max wait **9,030 с**, max hold **0,714 с**, ~29,6 с/прогон |
| `slow500` (fsync +500 мс) | 1 PASS / **1 ERROR**, exit 1 сохранён | trace: `WorkspaceBusyError` ~10 с; stderr decoding затем замаскировал отказ |
| `slow500live` | 1 PASS / **1 ERROR**, exit 1 сохранён | фазовая trace локализовала отказ в `append_raw_message:p1-8` |
| `slow500utf8` (исправлен только test helper) | **1 FAIL / 1 PASS** | полный новый child stderr сохранён; `WorkspaceBusyError` в `append_raw_message:p1-16`, ожидание **10,000 с** |

Сводка всех серий — `evidence/diagnostics_summary.json`. Каждый round имеет собственный output/result/trace; первый отказ не перезаписан последующим PASS. В первых двух отрицательных pressure-прогонах реальный итог unittest — **ERROR**, не FAIL: reader thread получил `UnicodeDecodeError`, а `finish` затем `TypeError` на отсутствующем stderr. Telemetry отдельно подтверждает исходный `WorkspaceBusyError`. В UTF-8 серии отказ уже виден непосредственно как **FAIL** исходного selector с полным traceback.

### Разбор временной шкалы

`evidence/timeline_analysis.json` восстановлен из live JSONL, сохранявшейся внутри критических секций до возможного kill peer при cleanup теста:

- ожидающий PID не приобрёл lock за **10,003524 с**;
- **904** native отказа, все с `errno=13 / EACCES`;
- в этом окне другой процесс завершил **20** критических секций;
- сумма измеренных body intervals внутри ожидания **9,966146 с**;
- максимальная отдельная body section **0,533128 с**;
- наибольший наблюдаемый body-gap **0,003912 с**, polling — **0,010 с**.

Наблюдалось вытеснение ожидающего writer серией коротких повторных захватов. Для достижения общего deadline не нужен единичный держатель на 10 с или утечка lock. Текущий poll/reacquire алгоритм не содержит FIFO очереди. Body intervals измерены после acquisition и до фактического unlock, поэтому **недооценивают** OS ownership; body-gap является верхней оценкой реального свободного окна. Дополнительный tracing I/O имеет overhead; это controlled reproduction, не замер исходного CI. Незавершённых live JSONL строк не обнаружено.

Отдельный `controlled_wait.py` удержал настоящий shared lock до истечения default deadline другого writer. Получен `workspace_busy` через ~10 с, byte-level snapshot Workspace до/после отказа совпал. После явного release один явный idempotent commit создал RAW, повтор того же ID вернул created=false. Автоматического повтора неидемпотентного append нет.

### Что доказано / что нет

1. **Допустимый bounded refusal** воспроизведён как при единственном длительном владельце, так и при повторных коротких захватах в slow-I/O workload. Отказ не означает потерю уже подтверждённого RAW.
2. В успешной нагрузке не обнаружены два одновременных писателя, потери/дубли/неправильный порядок/утечка lock. Это bounded evidence, не глобальное доказательство отсутствия всех sync bugs.
3. **Test/harness defects** UTF-8 и stderr truncation подтверждены RED и исправлены.
4. **Неверная классификация OS error** подтверждена отдельным fault RED и исправлена. Нет доказательства, что именно она вызвала исторический CI FAIL.
5. Точный original-CI trigger остаётся недоказанным. Данных недостаточно для безопасной смены fairness/timeout policy или объявления исходного FOLLOWUP закрытым.

## Минимальное исправление

### `context_storage.py`

Раньше `_try_lock_byte` превращал **любой** `OSError` в «занято», вплоть до `EBADF`/ошибки аргумента/файловой системы. RED `error_classification_red.txt` инъецирует EBADF и получает ложный `WorkspaceBusyError`. Теперь retryable только **EACCES/EAGAIN**; прочие OS-ошибки немедленно сохраняют исходный тип/errno и проходят существующий cleanup. Новый test проверяет отсутствие публикации, пустое reentrant-состояние и возможность следующего корректного commit.

Такое разделение соответствует документированному locking conflict EACCES у Windows CRT; Python POSIX nonblocking lock также требует учитывать EACCES/EAGAIN. См. [Microsoft `_locking`](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170), [Python `fcntl`](https://docs.python.org/3.12/library/fcntl.html), [Python `msvcrt`](https://docs.python.org/3.12/library/msvcrt.html). POSIX-ветвь source-reviewed, **не исполнялась на этом Windows-хосте**.

**Не изменены** timeout=10, poll=0,01, byte offset, OS locking mode, lock-file format, reentrancy, Workspace ID recheck, no-follow/junction проверки и публикация RAW. Не добавлены второй writer, очередь, скрытый retry или подавление исключения. API-различие намеренное: неожиданный lock I/O failure теперь OSError с первопричиной вместо ложного busy; valid contention по-прежнему WorkspaceBusyError.

### `test_ultra_chat_storage.py`

- Child явно получает `-X utf8`, согласованный с UTF-8 pipes; flag родителя не наследуется как argument дочернего процесса. `utf8_diagnostic_red.txt`: UTF-8 mode 0 вместо 1 при legacy environment; после ремонта русский `WorkspaceBusyError` читается целиком.
- `Base.finish` больше не обрезает stderr до 800 символов. `stderr_truncation_red.txt`: начальный marker длинного stderr терялся. После ремонта сохраняются marker и конец traceback; child exit 1 всё так же проваливает assertion.
- Добавлены **3** независимых regression cases. Функциональный workload и все oracles исходного concurrency test не ослаблены и не заменены retries.

Все три исходных негативных результата сохранены: 2 FAIL + 1 ERROR. Они отдельны от intentional slow-I/O pressure failures и исторического CI excerpt.

## Финальная регрессия / Windows

Среда: Windows 10 build 19045, Python **3.12.10 x64**, pytest **9.1.1**. Exact commands/source digests/exit/counts/stdout/stderr — в соответствующих JSON/TXT. Финальные runners фиксируют SHA до и после; source_unchanged=true.

| Проверка после исправлений | Итог | Exit |
| --- | --- | --- |
| Исходный selector, `afterrepair` | **5/5 PASS**; max wait 0,398 с, max hold 0,055 с | 0 каждый |
| Lock/Concurrency/ProcessDiagnostic tests | **14 PASS / 1 SKIP**, 15 cases | 0 |
| Python regression | **169 PASS / 5 SKIP**, 174 cases | 0 |
| Run Store/audit + Stage3 Turn/HTTP + original prerequisites | **92 PASS**, дополнительно **26 subtests PASS** | 0 |
| Post-repair four-process stress | **PASS**, 160 новых + 1 прежний RAW, 16 новых чатов | 0 |
| Post-repair genuine held-lock timeout | **PASS**, ожидаемый busy через **10,005 с**, snapshot unchanged, явное продолжение создаёт ровно 1 RAW | 0 |
| In-memory Python compile | 2 PASS, без pyc | 0 |

Без сложения overlapping/repeated tests: **266 cases = 261 PASS / 5 SKIP**. 26 pytest subtests, repeats и probes приведены отдельно. **Это не удаляет предыдущие FAIL/ERROR и не является full FIXED исходного CI.**

Stress использует отдельный O_EXCL marker внутри реальной critical section для выявления одновременных владельцев; 4 процесса × 40 stable-ID Unicode RAW, конкурентные create/rename, независимая проверка всех IDs/точного текста/Workspace-Chat ownership/per-writer created_at order, уникальных default titles и финального title. Старый RAW SHA неизменен; staging/tmp/exclusion marker после завершения отсутствуют. На fault cases возможна остановка peer в cleanup исходного теста; там не заявляется завершение всего workload или сохранение неисполненных намерений.

Full storage regression включает nested reentry, exception/termination release, корректный timeout, identity conflict и unsafe path/junction/hardlink отказы. Node/UI/browser не запускались: их source не менялся; соответствующие Python HTTP/Turn consumers проверены. Реальные LLM/Colibri/OAuth/paid/MCP, live Workspace write, Git-dependent discovery/`test_final_audit*` и independent CI — NOT RUN.

Guard поставлен до runtime imports, наследуется Python children; внешние sockets/DNS/Git metadata/executables запрещены. Loopback fixtures разрешены. Все сохранённые guard receipts имеют 0 denials; killed peer не обязан выполнить atexit. Это не OS-wide firewall. Диагностические wrappers существуют только в report harness и не включаются в production.

## MANUAL ENGINEERING REVIEW

- Пройдены acquire/refusal/reentrant/unlock/exception/kill paths. Ошибка до acquisition закрывает handle, не входит в writer body и не оставляет held-key; успешный владелец снимает свой byte-lock и закрывает handle в finally. Только повторный вход того же thread использует счётчик. Эти ветви не переписывались.
- Проверена гипотеза «единичный >10с holder / leaked lock» против trace: локальный timeout получен без неё, через 20 коротких sections. Из этого не следует, что утечка невозможна во всех средах.
- Проверена гипотеза «любой Busy означает реальную contention»: опровергнута EBADF fault RED. Ремонт ограничен классификацией errno и cleanup oracle, без модификации безопасности/ID.
- Проверены тестовые negative controls UTF-8/truncation; full stderr остаётся причиной FAIL, а не заменяется успехом. Исторический CI tail не дополнялся вымышленными frames.
- Отвергнуты увеличение timeout, removal lock, искусственная пауза после unlock и автоматический retry `append_raw_message` с новым UUID: они не устанавливают причину CI и/или меняют safety/liveness policy без доказательства.
- Проверены diff и source-scope: один короткий runtime branch + тестовая диагностика; Run Store/Turn/API/UI/launcher и существующие отчёты не редактировались. Для historical diagnostic series SHA первоначально снимался в конце серии; это не pin каждой импортированной версии при добавлении unrelated test cases. Ограничение записано отдельно. Final `afterrepair`/regression/probe receipts имеют before/after pin и source snapshots; functional legacy selector и его oracles сохранены.

## Сохранность / OPEN до сдачи

- **595/595** файлов текущего пользовательского storage неизменны: `.ultra` 586, `Чат_pro` 9, по набору/размеру/SHA. Тесты использовали только disposable TEMP.
- Из 10 editor-state файлов изменился `.obsidian/workspace.json`; агент туда не писал, процесс-источник не установлен, изменение сохранено и не откатывалось. Всего 605 защищённых baseline files; не заявляется их полное совпадение.
- 12 before-copies сохранны. Read-only Run Store/audit/Stage3/API/UI/launcher/finish sources совпадают; launcher всё время STANDARD, пользовательские процессы не перезапускались.
- **OPEN 1 / основной gate:** точный CI slowdown/errno/владелец и время его удержания неизвестны. Для основной причины статус **BLOCKED**, для локальной диагностики/подтверждённых ремонтов **PARTIAL**. `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` не закрывать одним новым зелёным CI или пятью isolated PASS.
- **OPEN 2:** не-FIFO polling допускает bounded timeout при slow-I/O chains. Если требуется гарантированный прогресс при таких нагрузках, нужен отдельный утверждённый контракт fairness/очереди/операционного бюджета. Корректный Busy не является успешным commit.
- **Предложенная адресная мера:** сохранить полные новые stderr + wait/hold/errno/fsync timings в следующем independent CI. При необходимости отдельно адаптировать caller/workload к явному bounded отказу с постоянными IDs и проверкой durable outcome; **не** добавить общий автоматический retry неидемпотентного append и **не** просто увеличить timeout.
- **OPEN 3:** новые OS errors сохраняют причину; потребители должны различать unexpected I/O failure и contention. HTTP/Turn regression прошла, native Tk GUI/error UX и Linux/сетевые FS/clean-machine/power-loss NOT RUN.
- 5 native symlink SKIP — отсутствующее Windows privilege, без смены прав. Junction/hardlink negatives исполнялись. Прежние TOCTOU/staging/picker/portability/P9-wide риски не объявлены закрытыми.

## DOC IMPACT / передача / одна публикация

Scope/общая документация не расширялись. После пользовательской **одной** публикации полного пакета координатор независимо проверяет результат, обновляет существующую запись/№05/06/34/40 и сохраняет исходный FOLLOWUP OPEN до достаточного evidence. Справочные ссылки не заменяют результаты исполнения.

Применённое чат-уточнение CI сохранено в `chat_amendment_01.md` и передаётся штатному `finish --chat-amendment ... --apply --headless`. Native HISTORY ID/readback и точный протокол — `evidence/finish.json`, `finish_result.json`, `finish_receipt.md`, `task_record.json`. После регистрации этот report не редактируется, manifest обновляется отдельно. Ручных переносов слота нет; finish не означает независимую приёмку или снятие OPEN.

NEXT: независимый verifier оценивает bounded findings/ремонт и назначает адресное продолжение CI диагностики при необходимости. Не включать Stage4/real sending/Colibri/paid/MCP по результатам этой задачи.
