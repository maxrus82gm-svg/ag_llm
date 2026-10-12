# CODEX-WA4-R-001-DIAG-01 — диагностика Closeout Race

STATUS: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**  
Классификация исторического CI-отказа: **INCONCLUSIVE / NOT REPRODUCED; BLOCKED FOR ACCEPTANCE**.  
Исполнитель: локальный Codex, 2026-10-12, Windows 10 / Python 3.12.10 AMD64. Production-код не изменён. Решение о приёмке OBSERVE и PR №11 остаётся за ChatGPT; следующие стадии не запускались.

## Вывод и граница доказательства

Воспроизведён реальный Windows отказ того же класса: открытый Python read handle на `task.md` в **pre-lock** чтении `OperationStore.begin` мешает `os.replace(active/task_r, completed/task_r)`. Получена цепочка `CloseoutError → TaskStoreError → PermissionError(errno=13, winerror=5)`, сообщение Closeout — `cannot move task to completed: task_r`. В этом контролируемом сценарии TASK осталась active/PLANNED, полностью сохранила исходные данные и после fresh-process reopen имела ту же проекцию. После освобождения read handle worker законно создал INTENT в **незакрытой** TASK, а повторный closeout вернул REJECTED/OPERATION_OPEN. Это безопасный fail-closed исход, который исходный тест не умеет отличать от нарушения инварианта.

**Это не установленная причина конкретного первого GitHub CI.** Исходный CI сохранил только `FAILED:CloseoutError`, без сообщения/cause/состояния. Естественные локальные повторения не дали такого отказа. Другие причины с тем же внешним типом — timeout, ошибка чтения либо записи статуса после move — реально различаются конечным состоянием. Поэтому нельзя объявлять исторический сбой FIXED, автоматически приписывать его Windows sharing либо принимать OBSERVE по зелёному повтору. Подтверждена причина контролируемой ветки; причина исторического события и его terminal invariants — **UNVERIFIED**.

## Исходные факты, полномочия и изменения

Координатор сообщил: baseline №280 `c7de06a60e2bd75d5f266ccf931a5ebb4da625f3`, PR №11, Actions run `38206439998`; первая попытка focused 228 PASS / full 748 PASS + 1 FAIL из 749 / JS PASS; вторая full 749 PASS. Это входные сведения, а не локальная проверка Git. Исторический FAIL и rerun сохраняются как разные события.

Проверены маршрут 08 → общий 000 → персональный 000 → 34 → 18 → 01 → профиль 23/24/25, применимые DOC-GIT/READ/VERSION/CHANGE/TASK-BLOCK1 contracts и прежний отчёт WA4-R. Общие документы продолжают описывать WA4-R как candidate/not assigned; актуальное полномочие на эту диагностику — прямой USER GO и персональный БЛОК 1. Общие документы и старый WA4-R report/evidence не переписывались. Источники фиксируются content SHA-256; соответствие локальных bytes указанному коммиту не проверялось.

Целевая правка: **только `test_web_alarm_projection_concurrency.py`**. Сохранились ROUNDS=4, start barrier, исходный random jitter и widened 0.3 s window, строгий `assertEqual(..., "REJECTED")` и все 19 прежних assertion calls. AST-сопоставление: 31 assertion call после правки, ни один исходный не удалён/изменён. Добавлены:

- bounded worker phase/lock trace с monotonic timestamps; тип, сообщение, errno/winerror, cause/context chain и traceback исключения; результат closeout;
- снимок terminal state **до** строгого result assertion, поэтому будущий FAIL сохранит evidence в штатном runner `test.facts`;
- проверка единственности active/completed, сохранности plan prefix, прежних microtask records, history prefix и immutable TASK files;
- сравнение результата с read-only fresh-process reopen; соответствие новых operation/plan IDs фактически успешным workers; ожидание остановки убитых собственных workers.

Дополнительные контролируемые fixtures и scripts оставлены только в system TEMP. Новый tracked диагностический test module не потребовался. Новые артефакты — этот report, четыре компактных JSON evidence и регламентная ротация персональной карточки. Production `web_alarm/*.py`, runner, UI/launcher, Ultra и прочие тесты не менялись; SHA-проверка до/после приложена.

## D1 — фактические пути и исключения

| Источник / selector | Что установлено |
| --- | --- |
| `web_alarm/closeout.py:87–114`, `CloseoutService.complete` | operations TASK lock → TaskStore mutation lock → completion_state → fresh build → verdict → complete_task_locked. Нечистый gate даёт REJECTED; TaskStoreError/OperationStoreError превращаются в CloseoutError с `raise ... from exc`. История TASK_COMPLETED добавляется после отпускания locks; EventCheckpointStoreError даёт event_recorded=false после уже состоявшегося completion. |
| `web_alarm/operation_store.py:157–175, 384–430`, `_serialized`, `begin` | Writer сериализуется operations lock, но `open_microtask` и active TASK read выполняются **до** него. Под lock `_path(...active_only=True)` снова запрещает запись в закрытую TASK; pre-lock чтение не является admission. |
| `web_alarm/task_store.py:149–175, 177–198, 309–312` | mutation lock; проверка двух местоположений; JSON/RAW/plan read. Ошибка чтения оборачивается TaskStoreError. Read APIs не берут mutation lock и могут держать Windows handle одновременно с completion. |
| `web_alarm/task_store.py:443–486` | create_microtask берёт mutation lock и заново проверяет active/mutable. Record/workdir → plan → task metadata — отдельные записи; существующий orphan blocker в projection важен при прерывании writer, но в проверенных гонках orphan/потери не появились. |
| `web_alarm/task_store.py:535–572` | directory move — commit point. Ошибка move: TaskStoreError и неизменённая active TASK. Ошибка после move: closed directory с pending status, который можно закончить gated completion; это предусмотренная interrupted completion, не новая write authority. |
| `web_alarm/store_lock.py:39–81` | acquire использует nonblocking OS lock и конечный deadline. StoreLockTimeout оборачивается store-specific error. `_try_lock` поглощает native OSError: исходный errno при timeout сам runtime не сохраняет. Ошибки mkdir/open/release могут выйти сырым OSError и не обязаны стать CloseoutError; тест не должен сводить все исключения к одному происхождению. |
| `web_alarm/projection.py:791–858, 1060–1092, 1215–1256` | build read-only, без собственного lock. Первые task/plan read failures выходят наружу; operations read failure становится blocker, а gate — REJECTED. Closed или moved/pending TASK получает history-only NEXT; checkpoint advisory, не authority. Rebuild берёт operations lock, write error оборачивается ProjectionError. |
| `web_alarm/event_checkpoint_store.py:64–105, 136–174` | append/read имеют отдельное error wrapping; checkpoint JSON/MD проверяется относительно свежей проекции. Closeout не восстанавливает checkpoint и не обязан сделать его VALID после move. |

`CloseoutError` сам по себе не доказывает ни разрешённый writer, ни незаконный completion. Чистый gate также не гарантирует, что файловая система разрешит commit. Диагностическое чтение не делает recovery/rebuild и не чинит наблюдаемое состояние.

## D2–D3 — временной порядок и воспроизведение

Обычный тест запускает четыре настоящих Python процесса: complete, два begin, create_microtask. Completion держит оба locks во время build и дополнительного 0.3 s окна; writers имеют прежний jitter 0…0.6 s в чётко заданных раундах. Diagnostic trace показывает wait/acquire/release каждого lock и границы build/completion; первые примеры COMPLETED и REJECTED сохранены в `repetitions.json`. Тimestamps задают наблюдаемый порядок, а не доказывают причинность по времени самостоятельно.

Контролируемая Windows последовательность:

1. Disposable verified TASK, microtasks m1/m2; reader worker начинает настоящий `OperationStore.begin`.
2. Test-only wrapper `Path.open` останавливает этот worker после открытия `task.md`, до чтения/operations lock. Handle реальный; `os.replace` не подменён.
3. Parent Closeout получает оба штатных locks, читает чистый gate и вызывает directory move. Windows возвращает **WinError 5**; исходная TaskStore и Closeout exception chain сохранена с source frames.
4. При всё ещё открытом reader handle проверены active-only location, PLANNED, отсутствие новых ops, unchanged TASK tree/history/plan и fresh-process равенство.
5. Reader отпускается, дочитывает файл, получает operations lock и сохраняет `op_reader`/INTENT. TASK по-прежнему active. Повторное completion — REJECTED, NEXT указывает OPERATION_OPEN. Ни одного SUCCESS completion здесь нет.

Это **controlled scheduling**, а не естественное повторение исторического CI; native sharing error не был искусственно создан через `raise PermissionError`. Остальные IO failures ниже — явно labelled fault injection. Lock timeout вызван реальным отдельным процессом, удерживающим соответствующий lock, и тестовым timeout=0.05 s.

| Прогон | Test attempts / реальные W rounds | COMPLETED / REJECTED / CloseoutError | Результат |
| --- | --- | --- | --- |
| Исходный неизменённый baseline | 1 / 4 | не записывались / не записывались / 0 | 1 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| Instrumented smoke (intermediate) | 1 / 4 | 2 / 2 / 0 | 1 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| 20 повторений (intermediate revision) | 20 / 80 | 48 / 32 / 0 | 20 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| Первый controlled run + 4 импортированных теста | 12 / 4 | 3 / 1 / 0 | 12 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| Controlled, intermediate TEMP harness | 8 / 0 | 0 / 0 / 0 | 8 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| Controlled, final TEMP harness | 8 / 0 | 0 / 0 / 0 | 8 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| Final focused: 20 повторений + 75 module tests | 95 / 84 | 46 / 38 / 0 | 95 PASS, 0 FAIL, 0 ERROR, 0 SKIP |
| Final full Web Alarm | 749 / 4 | 2 / 2 / 0 | 748 PASS, 0 FAIL, 0 ERROR, 1 SKIP |

Final focused отдельно: первые 20 тестов = 80 rounds; дополнительный module W = ещё 4. Full добавляет 4. Across recorded instrumented natural schedules: 176 rounds = 101 COMPLETED + 75 REJECTED, 0 CloseoutError. Вместе с исходным baseline выполнено 180 W rounds; это разные revisions, не один финальный прогон.

Неограниченных retries нет: обычный тест имеет 4 rounds, 20 повторений заданы конечным списком; barriers/communicate имеют deadlines, собственные workers останавливаются и reap. Instrumentation добавляет накладные расходы и способна изменить schedule, поэтому отрицательное воспроизведение не является доказательством отсутствия редкого отказа.

## D4 — конечные состояния и безопасность

| Ветка (итоговый controlled harness: 8 PASS) | Terminal state / доказательство |
| --- | --- |
| operations lock timeout | `CloseoutError → OperationStoreError → StoreLockTimeout`; active/PLANNED, seeded op_seed/INTENT и прежняя history сохранены, TASK tree unchanged; reopened equal. |
| mutation lock timeout | `CloseoutError → TaskStoreError → StoreLockTimeout`; active/PLANNED, unchanged/reopened equal. Operations lock освобождён. |
| настоящий pre-lock Windows reader | Move refused с WinError 5; unchanged active state до release. Затем ровно op_reader admitted в active TASK; повторный gate отказал. |
| injected task.json read refusal | До commit: CloseoutError с original PermissionError; active state unchanged после снятия test fault, reopen equal. |
| injected directory rename refusal | До commit: active state unchanged, reopen equal; нет незаконного partial closure. |
| injected status write refusal после move | Completed directory + PLANNED record; INTERRUPTED_COMPLETION и history-only NEXT; begin и create_microtask отказаны без изменения TASK bytes. Явный gated resume дал COMPLETED / resumed=MOVED_STATUS_PENDING, затем reopen equal. |
| injected TASK_COMPLETED history append refusal | COMPLETED / event_recorded=false; closed writes отказаны, существующая history сохранена. Нет ложного утверждения о добавленном event. |
| injected operations read refusal | REJECTED / PROJECTION_OPERATIONS_UNREADABLE; под fault проекция выдаёт blocked NEXT. После fault storage unchanged, reopen equal. |

| Инвариант | Локальный результат / предел |
| --- | --- |
| I1. COMPLETED не получает новую operation/microtask | PASS в фактически наблюдённых completed races и closed/pending controlled checks: ops/plan IDs совпадают с успешными workers, closed writes отказаны. Не является proof против произвольного внешнего writer. |
| I2. Отказ не создаёт незаконное partial closure | PASS для pre-commit failures. Post-move pending status — штатный закрытый resumable state; его read-only и explicit resume проверены отдельно. Отказ нельзя трактовать как «move точно не произошёл». |
| I3. Нет противоречивых active/completed копий | PASS: ровно одна directory во всех зафиксированных terminal snapshots. Pending record явно диагностирован, не скрыт как нормальный COMPLETED. |
| I4. Plan/records/history не теряются | PASS: plan prefix, неизменённые m1/m2, immutable file hashes и history prefix; отдельный timeout с существующим op_seed проверяет сохранность operation/history. |
| I5. Lock/storage failure не даёт write permission | PASS: никакого COMPLETED return при pre-commit error; операция после reader release допустима лишь потому, что TASK осталась active. Moved/pending и completed запрещают новые writes. |
| I6. Нет ложного безопасного NEXT | PASS для проверенных stable states: blocked IO даёт blocker; closed/pending — history-only и gated resume; checkpoints после move честно STALE. Clean active NEXT предлагает gated attempt, не обход lock/permission и не обещание IO success. |
| I7. Restart/reopen | PASS: одинаковые authoritative records, fingerprints, checkpoint status и TASK file hashes в свежем Python процессе. Это process reopen, не power-loss durability/OS reboot proof. |
| I8. Нет скрытой successful mutation после closure | PASS для собственных полностью завершённых race workers и closed probes: operation/plan IDs сверены с worker outcomes; активная копия не пересоздана. Не заявлен контроль чужих writers. |
| Исторический failed CI: I1–I8 | **UNVERIFIED**: terminal evidence отсутствует. Локальные сценарии не заменяют отсутствующие данные этого incident. |

## D5 — классификация и минимальное предложение

**Единственная итоговая классификация исторического события: INCONCLUSIVE / NOT REPRODUCED. Acceptance остаётся blocked до независимого решения.** Для контролируемого pre-lock reader путь и безопасный fail-closed state установлены; локально выявлено, почему общее ожидание «всё, кроме COMPLETED, обязано быть REJECTED» слишком узкое для documented storage failures. Но blanket допуск FAILED:CloseoutError был бы опасен: такой же внешний тип возникает после move, при pending status, и при других непроверенных причинах.

Подтверждённого нарушения terminal safety production-кода не найдено, production repair не выполнен и не требуется на основании одних этих данных. Минимальный следующий диагностический шаг: ChatGPT/координатор запускает **неослабленный instrumented тест** на исходном Windows CI runner, сохраняет runner `results.json` с `facts` при FAIL и проверяет exception chain, phase и terminal snapshot. Для потерянного первого incident, если подробностей нигде не осталось, точная причина может остаться невосстановимой.

Если независимая проверка принимает именно установленный safe-storage-refusal contract, отдельный USER GO может разрешить **test-only repair proposal**: в `test_web_alarm_projection_concurrency.py` явно различать clean COMPLETED, gate REJECTED и узко известный pre-commit storage refusal **только после** доказательства cause и I1–I8; добавить постоянный deterministic Windows reader case. Unknown exception, lost record, contradictory directories или hidden write должны оставаться FAIL. Runtime retry/увеличение timeout/ослабление gate не предлагаются как способ сделать тест зелёным. При выявлении runtime нарушения нужен отдельный repair scope для фактически виновного store/closeout path.

## D6 — проверки и версии

| Итоговая проверка | PASS / FAIL / ERROR / SKIP | Время (runner JSON) |
| --- | --- | --- |
| focused-final | 95 / 0 / 0 / 0 | 265.975 s |
| controlled-v3-final | 8 / 0 / 0 / 0 | 12.743 s |
| full-final | 748 / 0 / 0 / 1 | 670.282 s |

Единственный SKIP: `test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed` — `symlink creation is not permitted here`. Это ограничение Windows symlink permission, не PASS этого сценария. Все три итоговых процесса exit 0; isolation violations 0. Final production/test bytes совпадают между focused и full; исходный baseline и промежуточные revisions явно сохранены в SHA evidence.

Команды выполнялись из `M:\GitHub\ag_llm`; `$dgTemp = "$env:TEMP\wa4rdiag-06exabdv"`:

~~~powershell
# Unchanged baseline, до диагностической правки
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --task CODEX-WA4-R-001-DIAG-01 --output "$dgTemp\baseline" test_web_alarm_projection_concurrency.ProjectionRaceTests.test_completion_never_admits_new_open_state
# Final revision: 20 repetitions + adjacent RC-5 modules
$dgTargets = @(1..20 | ForEach-Object { 'test_web_alarm_projection_concurrency.ProjectionRaceTests.test_completion_never_admits_new_open_state' }) + @('test_web_alarm_projection_concurrency','test_web_alarm_projection','test_web_alarm_projection_repair2','test_web_alarm_task_store')
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --task CODEX-WA4-R-001-DIAG-01 --output "$dgTemp\focused-final" @dgTargets
# TEMP-only deterministic diagnostics, exact SHA in versions.json
.\.venv\Scripts\python.exe -B "$dgTemp\diag_cases.py" "$dgTemp\controlled-v3-final"
# Full regression
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --task CODEX-WA4-R-001-DIAG-01 --output "$dgTemp\full-final" all
~~~

Для portable минимального подтверждения именно native sharing refusal независимый verifier может запустить в guarded disposable fixture следующее; оно не устанавливает причину исторического CI и не заменяет исходный строгий test:

~~~python
from pathlib import Path
import tempfile
from test_web_alarm_projection_concurrency import ProjectionRaceTests, terminal_snapshot
from web_alarm.closeout import CloseoutService, CloseoutError
with tempfile.TemporaryDirectory() as tmp:
    storage = ProjectionRaceTests().setup_task(Path(tmp), verified=True)
    before = terminal_snapshot(storage)
    with (storage / "tasks/active/task_r/task.md").open("r", encoding="utf-8"):
        try:
            CloseoutService(storage).complete("task_r")
        except CloseoutError as exc:
            assert exc.__cause__.__cause__.winerror in (5, 32)
            assert "cannot move task" in str(exc)
        else:
            raise AssertionError("expected Windows rename refusal with held handle")
        assert terminal_snapshot(storage) == before
~~~

Isolation runner `wa4a_acceptance.py` не менялся: writes только TEMP, запрет Git metadata / внешних sockets/DNS / shell/native subprocess, controlled Python children наследуют guard; loopback разрешён для regression HTTP. Isolation violations — 0. Это trusted-test audit guard, не доказательство OS sandbox против злонамеренного native кода. Git/GitHub не вызывались; live storage и пользовательские TASK/проектные файлы не использовались. Node/UI suite отдельно не запускалась: UI не менялся; исторический JS PASS не выдан за текущую проверку.

Исходные/final hashes всех `web_alarm/*.py`, тестов и runner — `versions.json`; все full source hashes сверены с final bytes. Сырые runner results/logs и scripts остаются TEMP, а компактные counts, nonpassing IDs, raw-result hashes, representative traces и контрольные states — здесь. TEMP harness не является постоянным CI test и может быть удалён системой; portable минимальный native case приведён выше. Первый TEMP harness launch упал **до unittest** из-за sys.path; исправлен только TEMP script. Промежуточные успешные прогоны не скрыты, отдельно помечены в `checks.json`; их цифры не подменяют итоговые.

## DOC IMPACT / handoff

DOC IMPACT: YES; CURRENT STATE IMPACT: YES (diagnostic status/evidence only); ARCHITECTURE IMPACT: NO; CONTEXT LIBRARY IMPACT: NO; REGISTRY / ROUTING IMPACT: YES (coordinator handoff); NEW NORMATIVE DOCUMENT: NO. Канонический владелец RC-5 — №23; rollout/status/history — №24/25, общие документы ведёт ChatGPT.

**SHARED DOC DELTA / DOC CLOSEOUT INCOMPLETE:** координатору обновить общий 000/05/06/34 и при необходимости 01/23/24/25: диагностика RESULT READY, исторический CI failure root cause unestablished, controlled native Windows refusal безопасен, production unchanged; OBSERVE не объявлять DONE/VERIFIED автоматически. Сохранить раздельно исходный FAIL, успешный rerun и локальное evidence. Не открывать WARN/GATEWAY REQUIRED/STRICT/Final Audit и не смешивать это с отложенным UX redesign. Нормативные полномочия/Rule-ID не менялись; новые wiki-ссылки и цифровые phantom Graph nodes не добавлены.

Полная неизменённая постановка сохранена в персональном БЛОКЕ 2, factual result в БЛОКЕ 3; прежние блоки сохранены дословно в архиве. БЛОК 1 освобождается только после проверки этих записей. Подтверждение lossless rotation и hashes — в `versions.json`.

**NEXT SAFE ACTION: Independent ChatGPT verification.** Нужна причинная проверка instrumented failure/controlled case и решение координатора о достаточности evidence для OBSERVE acceptance. PR №11 не объединялся; дальнейшая работа остановлена до отдельного назначения.
