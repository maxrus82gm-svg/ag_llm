# CODEX-WA4-R-004-F1-CLOSEOUT-GATE

2026-10-14 · Codex 007 · Web Alarm / WA4-R Reliability · verifier WEB_07.

**RESULT READY / AWAITING INDEPENDENT VERIFICATION · LOCAL ONLY / NOT SYNCED.** F1 не объявлен VERIFIED. WARN / GATEWAY REQUIRED / STRICT, rollout и интеграция Ultra не запускались.

## 1. Вывод

В проверенных F1-сценариях текущий production-код сохраняет безопасное состояние и позволяет восстановить прерванное завершение новым процессом. **Новый runtime-дефект не подтверждён; production-код не изменён.** Найден и закрыт пробел тестового доказательства: прежний F1 post-move test использовал TASK без операций/receipt, поэтому не доказывал сохранность непустой истории завершённой физической операции.

Изменён только общий `test_web_alarm_wa4r002_diagnostics.py`: сохранены все 15 прежних selectors, усилен существующий F1, добавлены три сценария. Собственные quality controls/evidence находятся рядом. `closeout.py`, `task_store.py`, `test_web_alarm_reliability_wa017.py`, другие runtime/tests, общий CI и регламенты не исправлялись. Четыре runtime-файла F2/F3 побайтно совпадают с final pins предыдущего repair; прежние F2/F3 test method bodies не изменены (AST comparison).

Это ограниченное инженерное доказательство текущего F1-контракта, а не утверждение, что любой `CloseoutError` безопасен или что выяснен владелец каждого исторического Windows handle.

## 2. Вход, источник и правила

Полный исходный БЛОК 1 прочитан и оставался побайтно неизменным до регламентной ротации. Маршрут 08 → общий/собственный 000 → 34 → 18 → 01 → 23/24/25 → 36/36.1/36.2 выполнен адресно по локальным файлам. Использованы DOC-GIT-01, DOC-PARALLEL-01, DOC-TASK-BLOCK1-01, TEST-ENG/QA/EVID/FLAKY/SCOPE. Версии локальных нормативов и исходников закреплены в `versions.json`; Git/GitHub не читались. GitHub-версия текущего checkout независимо не сверялась.

Windows 10 build 19045, Python 3.12.10, `PYTHONUTF8=1`, `-B -X utf8`; только disposable TEMP fixtures. Runner `wa4a_acceptance.py` и его guard не менялись. Workspace: `M:\GitHub\ag_llm`; attempt root: `C:\Users\REX\AppData\Local\Temp\codex-wa4r004-_fq7_1ip`. Внешние HTTP, LLM, Git и live Workspace не использовались. Параллельный drift карточки Claude сохранён без отката.

Оригинальный пользовательский ZIP `wa4r002-independent-38379575748-1.zip` адресно проверен: run **38379575748**, artifact **11802732223**, SHA-256 **020d2770b48f90e0d24df071b10c2ad5fe5caa2972d8d3070445ac875963e120**, совпадение подтверждено. Внутри 63 tests = 62 PASS / 1 FAIL, isolation пуст. Извлечён только релевантный failing F3 round 0: c0 exit 0 / `FAILED:CloseoutError`, chain `CloseoutError → TaskStoreError → PermissionError`, errno 13 / WinError 5 в directory `os.replace`; terminal active=true, completed=false, PLANNED, op_b1/op_b2, m1/late_m3, семь событий и исходные project bytes. Остальные workers BEGUN/BEGUN/CREATED сохранены в `historical-F3.json` вместе с frames.

Это **pre-move исторический F3**, не доказательство исторического F1 post-move recovery. Исходный FAIL сохраняется; текущие зелёные проверки его не превращают в PASS. Отдельный исходный F1 artifact здесь не получен/не атрибутирован; заключение относится к текущим детерминированным сценариям. Исходный ZIP и минимальная выписка включены в переносимые evidence.

## 3. Качество fixture и независимость oracle

Каждая F1 fixture выполняет **одну настоящую MutationExecutor WRITE**, получает durable DONE receipt, затем законно переводит operation и microtask в VERIFIED и строит checkpoint до quiescent closeout PRE. Никакие receipt не создаются вручную.

Есть два разных PRE: исходный файл `b'PRE\r\n\x00\xff'` сохранён в snapshot; после единственной разрешённой операции actual target равен `b'POST\n\x00\xfe'`. Именно второе состояние является **PRE попытки closeout**. Отказ closeout должен сохранять этот POST и историю операции, а не восстанавливать старый snapshot.

Oracle читает filesystem/JSON напрямую: обе locations, task/plan/microtasks/operations/receipts/events/checkpoint, claims, restore manifests/entries/snapshot metadata, actual snapshot bytes/target bytes и SHA-256 всех файлов TASK. JSON records отвергают duplicate keys. В сравнениях задаются literal bytes/status/identity; `ProjectionService` не формирует expected. Его rebuild используется только для создания действующего checkpoint в fixture; `completion_state` — дополнительная сверка уже независимо наблюдаемой формы.

Сохраняются raw PRE, phase markers, PID/exit/stdout/stderr каждого worker, промежуточные и терминальные records. PID подтверждает отдельные процессы recovery/read/replay. В завершённом состоянии разрешено изменить только task status/update time и добавить один `TASK_COMPLETED`; остальные файлы и receipt должны быть идентичны. Запрещённая поздняя mutation и historical replay не меняют closed history. Счётчик `_apply` остаётся **1**, включая первоначальную fixture operation.

## 4. Детерминированные F1-сценарии

Префикс selectors: `test_web_alarm_wa4r002_diagnostics.RaceEvidenceTests.`

| Selector | Достигнутая фаза и oracle |
|---|---|
| `test_F1_native_pre_move_refusal_preserves_nonempty_evidence_and_fresh_retry` — новый | После свежего gate под locks открыт настоящий Windows RAW handle без delete sharing. Реальный `os.replace` даёт PermissionError/WinError 5 или 32; worker exit 2, marker handle_open есть, directory_moved отсутствует. Active-only, **весь raw state равен closeout PRE**. Новый процесс читает тот же PRE, затем после освобождения handle completes с resumed=null. Receipt/checkpoint/snapshot сохранены, один apply. |
| `test_F1_native_post_move_status_failure_and_fresh_recovery` — усилен | Есть directory_moved и native status-reader marker; настоящий atomic task.json replacement отказывает, exit 2/точная error chain. Completed-only + PLANNED = `MOVED_STATUS_PENDING`, не success. Whole file hashes равны closeout PRE. Новый процесс читает pending; новый mutation ID REFUSED, прежний VERIFIED receipt REPLAYED без записей. Fresh completion resumed=MOVED_STATUS_PENDING, один completion event, raw reopen идентичен; повторный complete REJECTED. |
| `test_F1_completion_first_serializes_RAW_admission_plan_and_new_mutation` — новый | Closer остановлен перед directory move после свежего gate; operations и mutation locks отдельно подтверждены реальными timeout probes **до** запуска contenders. Затем RAW-reader/admission, plan writer и новый executor ждут. После release closeout COMPLETED, begin/plan получают строгий TaskStoreError, executor REFUSED, активный RAW-handle не открылся. Нет поздних operation/plan records или apply; whole non-status history неизменна. |
| `test_F1_admission_first_rejects_closeout_without_touching_existing_evidence` — новый | RAW reader удерживает operations lock до admission. Closer ждёт; после admission fresh gate содержит OPERATION_OPEN. Барьер фиксирует **post-admission PRE**: op_late INTENT без receipt, прежняя VERIFIED operation/receipt неизменна, checkpoint законно указывает op_late/m1. Closer REJECTED без directory move; весь raw state после отказа равен post-admission PRE и повторно читается новым процессом. |

Это фазовые расписания, не вывод о порядке по sleep. Timeout probes проверяют реально удерживаемые locks; они не заменяют terminal/phase oracle. Существующий WA-017 random-start crash race отдельно выполнен со своими строгими REJECTED/EXIT 9 assertions; он не заменяет детерминированные F1 cases.

## 5. Проверки и исходные красные результаты

| Attempt | PASS | FAIL | ERROR | SKIP | Isolation |
|---|---:|---:|---:|---:|---:|
| baseline-F1, исходный существующий selector | 1 | 0 | 0 | 0 | 0 |
| F1-first, первая новая матрица | 3 | 1 | 0 | 0 | 0 |
| F1-corrected | 4 | 0 | 0 | 0 | 0 |
| quality-first | 4 outer | 0 outer | 0 | 0 | 0 |
| focused-F1F2F3 | 92 | 0 | 0 | 0 | 0 |
| bounded-F1-1 | 4 | 0 | 0 | 0 | 0 |
| bounded-F1-2 | 4 | 0 | 0 | 0 | 0 |
| quality-final | 5 outer | 0 outer | 0 | 0 | 0 |
| focused-final, после усиления byte prefix | 92 | 0 | 0 | 0 | 0 |
| bounded-final-1 | 4 | 0 | 0 | 0 | 0 |
| bounded-final-2 | 4 | 0 | 0 | 0 | 0 |
| quality-byte-prefix, окончательная версия | 6 outer | 0 outer | 0 | 0 | 0 |

Каждый final quality outer PASS требует ровно **один inner assertion FAIL**, без inner ERROR/SKIP. Эти intentional red не входят в product PASS. Повторы и focused перекрываются — не суммировать как уникальное покрытие.

**Первый F1-first FAIL — TEST/ORACLE DEFECT.** Новый admission-first тест ошибочно требовал checkpoint, равный состоянию *до* допущенной операции. `OperationStore.begin` законно обновляет derived checkpoint. Вместо ослабления outcome добавлен барьер после свежего gate: checkpoint буквально обязан содержать op_late/m1, legacy operation и остальные данные неизменны; rejected closeout обязан оставить **точно post-admission raw state**, включая checkpoint. Первоначальные source bytes, traceback, results и raw state сохранены отдельно; никакого production repair из-за этой ошибки не делалось.

**Отдельная collection/export setup error:** первая metadata-проба собрала 791 ID, затем ошибочно попыталась экспортировать diff в report из процесса с TEMP-only guard. Guard заблокировал запись; audit содержит одно событие. Это не продуктовый тест и не успешный чистый attempt. Исходные данные сохранены. Исправлено разделением guarded TEMP collection и разрешённой упаковки отчёта в другом процессе. Final collection: **791 уникальный ID = 788 сохранённых + 3 новых**, isolation 0; syntax двух изменённых Python modules PASS.

**Full Web Alarm execution — NOT RUN в этой TASK.** Условие БЛОКА 1 «при изменении runtime» не наступило. Выполнен 92-test focused gate с diagnostics, WA-017, projection concurrency, executor, TaskStore, operation-store concurrency и target-claim concurrency. Сбор 791 ID не выдаётся за выполнение 791 теста; прежний full UX-002 также не выдаётся за новый запуск. Full suite может отдельно выполнить WEB_07 по своей risk assessment.

## 6. Шесть отрицательных контролей

Контроли в `quality_controls.py`, отдельный guarded invocation. Production-файлы не меняются; повреждения только в owned TEMP records или памяти отдельного child.

| Контроль | Намеренное нарушение / доказанный отказ oracle |
|---|---|
| missing native pre trigger | Реальный fault handle убран; closeout завершается. Тест падает на exit 0 вместо ожидаемого 2. |
| counterfeit persisted receipt | После настоящего native post-move failure меняется sha256 в actual stored receipt; raw comparison операций падает. |
| lost checkpoint identity | Меняется actual checkpoint.last_operation_id; независимое сравнение checkpoint падает. |
| missing closeout operations lock | В отдельном child source method удалён только внешний operations lock; probe до contenders обнаруживает свободный lock и падает. |
| false success after native status failure | В child подавлен CloseoutError и возвращён COMPLETED. Зафиксированы moved/status-reader phases, completed + PLANNED и stdout COMPLETED/exit 0. Тест ловит ложный success на ожидаемом error exit. |
| semantically equal rewritten event prefix | После recovery меняются actual bytes прежних log records при сохранении их parsed JSON. Тест падает на несовпадении исторического byte prefix; сравнения одних словарей здесь недостаточно. |

Таким образом, controls проверяют не только появление ошибки Windows, но и сохранность непустых данных, точного event prefix, сериализацию и запрет false success. Последовательно сохранены quality-first (4), quality-final (5) и окончательный quality-byte-prefix (6). Последний и итоговый focused/repeats относятся к одному final source hash; прежние результаты сохраняют свои pins.

## 7. MANUAL ENGINEERING REVIEW

**Просмотрено:** CloseoutService.complete/inspect/verdict; TaskStore.complete_task/complete_task_locked/completion_state, atomic JSON writer, path lookup и mutable checks; interprocess lock; OperationStore begin/transition/RAW-read boundary; MutationExecutor closed replay/physical boundary; projection closeout blockers/checkpoint refresh; event persistence и текущие F1/F2/F3 tests. Анализ выполнен отдельно от подсчёта PASS.

- Порядок **operations TASK lock → TaskStore mutation lock → fresh projection/gate → directory move → status write** сохраняется. Детерминированные оба порядка admission/closeout подтверждены фазами. Плановый writer берёт только mutation lock и после move отказывает; новый executor не получает apply authority.
- Directory move — commit point. Ошибка до него оставляет active data; после него location уже закрывает mutation независимо от PLANNED status. Fresh completion финализирует metadata, а не повторяет physical operation. Legacy closed-status-in-active shape остаётся под свежим gate; её существующие WA-017 tests выполнены.
- `CloseoutError` не превращён в REJECTED или success. Рассмотренный auto-retry WinError не внедрён: он не нужен для доказанного контракта, может скрывать исходный отказ и не устранит внешний reader. Recovery — отдельный явный новый процесс после освобождения handle.
- Whole task tree, claims, event prefix, exact operation/receipt, checkpoint и snapshot сравниваются независимо. Empty-operation shortcut отвергнут; исходная fixture действительно делает один write. Нативный status failure удаляет свой staging tmp в наблюдённых прогонах; это не доказательство всех возможных вторичных cleanup failures.
- Во время отдельного review найден ещё пробел oracle: JSON-equality старых event records не замечает переписывание их байтов. Добавлены raw events_hex/prefix assertion и строгий duplicate-key parser событий; реальный TEMP log с неизменным parsed JSON намеренно переписан в quality control и отвергнут. После этого повторены focused и bounded gates на final source, а не использованы старые PASS.
- Historical replay — сохранённый receipt, не новое подтверждение текущих bytes. В данных scenarios actual target дополнительно проверяется literal bytes/hash; receipt не используется как универсальная current-state authority. Fresh pending/completed reopen и повторный complete не воскрешают active TASK и не создают второй event/apply.
- Ошибка первоначального checkpoint oracle разобрана по исходникам: admission обновляет derived projection *до* closeout, поэтому правильный no-mutation baseline фиксируется после admission. Новый барьер и checks строго различают разрешённые admission effects и запрещённые closeout effects.
- F2/F3 compatibility подтверждена точными четырьмя runtime hashes предыдущего reported repair, неизменностью старых test bodies, их выполнением и lock-removal negative control. Это не самостоятельная независимая приёмка предыдущего repair.

**Остаточные границы:** controlled native handle ≠ установленный исторический handle owner; historical F1 raw отсутствует; внешний writer/антивирус не исключён; crash/power loss/другие файловые системы не сертифицированы этой матрицей. Существующие WA-017 crash tests выполнены, но текущая TASK не повторяет абсолютно все kernel failure modes. Low-level `complete_task_locked` по-прежнему требует locks вызывающего кода; ungated storage primitive не превращён в public closeout gate. Общая STRICT authority/rollout вне scope. Ни `event_recorded=False`, ни повреждённый storage не объявлены автоматически безопасными: новые positive случаи требуют точно сохранённую историю и один completion event.

## 8. Воспроизведение

Из `M:\GitHub\ag_llm`, новый уникальный TEMP parent; runner outputs не должны существовать. Все реальные команды/exit/source hashes также в `checks.json` и raw attempt artifacts.

```powershell
$env:PYTHONUTF8='1'
$qa = Join-Path $env:TEMP ('wa4r004-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $qa | Out-Null
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-R-004-F1-CLOSEOUT-GATE --output "$qa\focused" test_web_alarm_wa4r002_diagnostics test_web_alarm_reliability_wa017 test_web_alarm_projection_concurrency test_web_alarm_mutation_executor test_web_alarm_task_store test_web_alarm_operation_store_concurrency test_web_alarm_target_claims_concurrency
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-R-004-F1-CLOSEOUT-GATE-QUALITY --output "$qa\quality" reports.CODEX-WA4-R-004-F1-CLOSEOUT-GATE.quality_controls.Sensitivity
```

Для двух bounded повторов использовались именно четыре F1 selectors таблицы §4, по отдельной новой output directory; запуск прекращался бы на первом FAIL. Общая база 18 diagnostic methods сохраняет прежние F2/F3 case IDs. Не использовать live storage, не менять общие runners/CI ради воспроизведения.

## 9. Evidence и SHARED DOC DELTA

`checks.json` — точные counters/IDs/exit/isolation/source каждого attempt; `versions.json` — до/после, совместимость, collection и нормативы; `historical-F3.json` — адресная первичная выписка; `source-changes.diff` — локальное сравнение bytes без Git; `evidence.zip` — переносимые original/red/green results, phase/raw records, bounded logs, snapshots источников и historical ZIP. `rotation.json` / `manifest.json` проверяют сохранность карточки и пакета. Исходные TEMP не удаляются автоматически.

Предложение координатору **после независимого verdict**, без самостоятельной правки общих документов:

- 36.2 / WA-I02/I10/I11: четыре F1 сценария, nonempty fixture, post-admission checkpoint baseline, six quality controls и exact event-byte prefix; текущие команды и пределы native evidence.
- 23/24/25: при подтверждении WEB_07 записать bounded F1 closeout evidence/recovery gate; directory commit point/authority не менялись, runtime repair отсутствует. Сохранить исторические FAIL и самостоятельный статус F2/F3 acceptance.
- 000/05/06/34 и при необходимости 01: factual source pins, report link, независимый verdict и открытые rollout gates. Не повышать WA4-R до STRICT VERIFIED по этому результату.

**NEXT:** пользователь публикует локальные материалы своим штатным способом; WEB_07 независимо проверяет исходники, input quality, phase/raw oracles, controls, collection/source match и ограничения. До этого — только RESULT READY. Следующие стадии, commit/push/merge и rollout не запускать.
