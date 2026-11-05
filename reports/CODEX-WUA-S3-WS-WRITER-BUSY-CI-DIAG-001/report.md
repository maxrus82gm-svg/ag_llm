# CODEX-WUA-S3-WS-WRITER-BUSY-CI-DIAG-001

**PARTIAL / NOT REPRODUCED. Точная причина исторического CI FAIL — UNKNOWN.** Исполнитель Codex 007. Локальная адресная диагностика завершена; независимая приёмка не выполнена. `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` остаётся **OPEN**.

Выполнено **12 запусков за 19,281 с**: 6 обычных и 6 с дополнительными короткими повторными захватами lock. Все **12 PASS / 0 FAIL / 0 ERROR / 0 SKIP**. Исходный `WorkspaceBusyError` в этой серии не повторился. Серия остановлена по заранее выбранному объёму, дополнительных повторов нет; лимиты TASK ≤20 запусков / ≤300 с соблюдены.

## Область и исходная база

Назначение подтверждено в БЛОКЕ 1. Адресно прочитаны оригинальный selector/fixture, измеритель и заключение H-CODEX-000014, его CI excerpt/предыдущая timeline, независимый review WEB23 и текущий shared scope №40. Старый review не объявляет CI timeout исправленным; нынешнее прямое назначение разрешает только эту диагностику. Персональные правила и порядок native finish сохраняются.

**Ни production, ни `test_ultra_chat_storage.py` не изменены.** Новые helper/guard/report/evidence находятся только в этом каталоге. Monkeypatches — process-local наблюдатели и диагностические wrappers fixture lifecycle; native lock algorithm, timeout/poll/offset, RAW publication и функциональный workload/oracles исходного теста не менялись. Повторных RAW writes/retries, искусственной задержки fsync, правок workflow или реальных Workspace нет. Git/GitHub не использовались.

Перед работой сохранены 8 исходных `.source.txt` copies и SHA-256: storage/test, Run Store/Turn, launcher/config/finish и карточка. Baseline также содержит hashes/names/sizes 605 защищённых файлов. Текущая локальная версия содержит прежние исправления H-CODEX-000014; историческая версия CI run 42040238153 не извлекалась и не исполнялась через checkout. Публикация/remote SHA самостоятельно не проверялись.

## Минимальная проверка и измерения

`diagnose.py` запускает ровно прежний selector:

`test_ultra_chat_storage.ConcurrencyTests.test_two_processes_write_raw_create_and_rename_without_losing_anything`.

Условия чередовались ordinary/short_reacquire, по шесть независимых TEMP fixtures. В обоих условиях два исходных процесса выполняют по 25 RAW, создают суммарно 10 чатов и переименовывают исходный чат. Во втором условии дополнительный процесс берёт **тот же настоящий OS lock**, держит около 20 мс, освобождает и ждёт 2 мс. У него нет записей RAW. Подтверждено 17–31 реальных дополнительных acquisition на такой запуск (всего 140), все child exit 0.

Observer сохраняет entry/acquisition/body end/error, PID/phase, native errno и fsync durations. `result.json/acquisition_sequence` и `trace/*.live.jsonl` сохраняют последовательность конкурирующих процессов; полные `child_<pid>.stdout.txt/.stderr.txt` и `unittest.txt` сохранены отдельно. Пустой stderr у успешного child — полный пустой stderr, а не усечённый tail. Watchdog ограничивает workload 300 с и завершает только собственные зарегистрированные children при budget expiry; в этой серии он не сработал. Все процессы завершены и reap выполнен, TEMP удалены после снимков.

| Условие | Запуски | Max entry→acquire | Max measured body hold | Max fsync |
| --- | --- | --- | --- | --- |
| Обычные два writer | 6/6 PASS | **0,346821 с** | **0,036864 с** | **0,009156 с** |
| Те же writer + короткие захваты конкурента | 6/6 PASS | **0,473193 с** | **0,048250 с** | **0,006747 с** |

По 486 fsync измерений в каждой группе. Все наблюдавшиеся OS отказы — **errno 13/EACCES**; timeout events нет. Entry→acquire включает небольшие path/handle checks; это не чистое kernel wait. Body intervals не включают весь acquisition/release overhead. Tracing добавляет overhead и влияет на расписание, поэтому это ограниченный наблюдаемый эксперимент, а не benchmark без инструментации.

## Целостность синтетических данных

Прежние assertions теста не ослаблены: 50 RAW с точным набором `p0-0..24`/`p1-0..24`, message ID/filename consistency, 10 уникальных default titles, допустимое конечное переименование, отсутствие staging/tmp.

Дополнительно до удаления каждого TEMP сохранены все synthetic RAW и файловый SHA inventory в `series/<N>/integrity.json`. Независимо проверены Workspace/Chat ownership, уникальность ID, точные payloads, per-writer created_at order, отсутствие повреждённых JSON и временных публикаций. **50/50 на каждом запуске, всего 600/600 RAW в 12 разных TEMP Workspace**, без потерь/дублей/повреждений в выполненной области. `validation_summary.json` также подтверждает, что конкурент действительно работал и все children завершились успешно.

## Доказательства, гипотезы и UNKNOWN

**Доказано здесь:** в текущих обычных и controlled-short-contention условиях target прошёл; значительная часть entry waits была реальной contention (native EACCES), но оставалась далеко от default 10 с. Неподтверждённых timeout/new production defects не найдено. Три observer/helper файла прошли in-memory compile. Guard до imports/в children дал 0 запрещённых попыток; его loopback разрешён для test infrastructure, это не OS firewall. Внешние сети/LLM/MCP не вызывались.

**Исторические доказательства сохранены отдельно:** `historical_ci_excerpt.source.txt` — ранее предоставленный пользователем tail, run 42040238153, тест ~16,75 с, весь набор 285,636 с, `WorkspaceBusyError`; он **не полный traceback**. `previous_timeline.source.json` — измерения H-CODEX-000014 с искусственно замедленным fsync, не нынешняя серия. Ни один из них не заменён нынешним PASS.

**Наиболее правдоподобная гипотеза по совокупности прежних данных:** замедление I/O/планирования и повторные захваты могли исчерпать ограниченный wait budget без единичного длинного holder. Прежний эксперимент показывал такую возможность. **Привязка этой гипотезы к историческому CI не доказана.** В нём неизвестны per-lock errno/holder timings и физическая причина замедления; новая серия этого не восстановила. Поэтому итог **UNKNOWN / NOT REPRODUCED**, не FIXED. Повышать timeout, менять fairness или вводить automatic append retry по этим данным оснований нет.

Текущая задача не повторяет предыдущую большую slow-fsync/regression кампанию. Другие suites, native GUI, Linux/network FS/power loss, реальный CI и исторический runtime SHA — **NOT RUN**. Это не full product/storage PASS.

## Команда, версия и воспроизводимость

Среда: **Windows 10 build 19045, Python 3.12.10 x64**, стандартный unittest. Точная исполненная команда/env/source hashes: `evidence/invocation.json`; исходный исполненный helper сохранён в `evidence/executed_diagnose.source.txt`. После серии добавлен только CLI `--label`, чтобы независимая проверка не перезаписывала старые evidence; parser `--help` и compile проверены, target больше не запускался. Все production/test SHA до/после каждого запуска совпадают.

Для независимого запуска с новым, ещё не существующим label из корня проекта:

```powershell
$diagRoot = Join-Path (Get-Location).Path 'reports/CODEX-WUA-S3-WS-WRITER-BUSY-CI-DIAG-001'
$env:PYTHONPATH = (Join-Path $diagRoot 'guard') + [IO.Path]::PathSeparator + (Get-Location).Path
$env:S3_GUARD_OUTPUT = Join-Path $diagRoot 'evidence/guard_ci001'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -X utf8 reports/CODEX-WUA-S3-WS-WRITER-BUSY-CI-DIAG-001/diagnose.py --label ci001
```

Не запускать поверх прежнего label: helper отказывает до серии, вместо перезаписи. Новый label пишет `evidence/<label>/` и `diagnostic_summary_<label>.json`. Серия по-прежнему заранее ограничена 12 cases/300 с; внутри нет production retries или увеличения timeout.

## Краткий план независимого Windows CI

1. Пользователь публикует **один** полный пакет. Уполномоченный координатор выбирает exact опубликованный commit и Windows/Python 3.12.10. Codex не изменяет workflow и не запускает GitHub операции.
2. Выполнить приведённый helper на pinned source, новый label; сохранить commit/runtime/helper/source hashes и limits. Fresh runner должен иметь текущие project dependencies для исходного storage selector.
3. Сохранить полные stdout/stderr, последовательность PID acquisitions, errno/wait/hold/fsync, integrity snapshots и guard receipts. При timeout/budget-abort отличать неполный прогон от PASS; не продолжать бесконечно. First FAIL оставить неизменным.
4. Сопоставить с историческим tail. Даже новый 12/12 PASS не закрывает исходный FOLLOWUP. Новое изменение production допускается только отдельным поручением при найденной причине.

## MANUAL REVIEW / сохранность / OPEN

Проверены observer paths, полный stderr capture и cleanup: assertion child exit==0 сохраняется; дополнительные integrity oracles не подменяют прежние, controller использует реальный lock, а его эффект проверен по positive acquisition count. Watchdog знает только собственные children; перед штатным recursive TEMP cleanup проверяется resolved parent. Частичные/ошибочные результаты сохранялись бы до удаления TEMP. Новых FAIL в этой серии нет; исторический FAIL не имитировался.

**595/595 пользовательских storage файлов неизменны** (`.ultra` 586, `Чат_pro` 9), по names/sizes/SHA. Все восемь baseline source copies сохранны; production/test/launcher/config/finish sources совпадают. Launcher STANDARD не переключался. В `.obsidian/workspace.json` обнаружена внешняя editor delta: агент файл не писал, источник не атрибутирован, rollback не выполнялся. Её реальные данные **не входят в публикационный allowlist**, как и любые production files. В package есть только hash receipt этой дельты.

**OPEN до сдачи:** original CI cause UNKNOWN; основной FOLLOWUP OPEN; независимый pinned Windows CI NOT RUN. Старые TOCTOU/staging/picker/portability/P9-wide риски не оценивались заново и не закрыты. DOC IMPACT: координатор после публикации сохраняет этот bounded результат/UNKNOWN в существующей записи и FOLLOWUP; общие документы автором не редактировались.

Native `finish --no-chat-amendment --apply --headless` выполняется после полного пакета. Полученные HISTORY ID/readback/protocol — в `evidence/finish.json`, `finish_result.json`, `finish_receipt.md`, `task_record.json`; report после регистрации не меняется, manifest обновляется отдельно. Сдача слота не равна независимому PASS. NEXT — одна публикация пользователем, затем независимая проверка и решение координатора по OPEN.
