# CODEX-WA4-R-002 — Historical Race Evidence & Recovery Proof

STATUS: **READY FOR INDEPENDENT REVIEW**. Исполнитель: Codex, 2026-10-13. ARCH CLASS: Web Alarm Workspace; PRIMARY PROFILE: 23, test profile: 36.2. Независимая приёмка — WEB_07. WA4-R overall не закрывается.

## Scope и исходные сведения

Разрешены только диагностика F1–F3, необходимые diagnostic tests и disposable fixtures. Production/Ultra/rollout/CI/Git не изменяются. БЛОК 1 заморожен; его исходные байты сохранены в TEMP. Контрольная точка №302 `11f0a0a47518619119a5d60685abe852da915f10` получена из задания, локальная Git-эквивалентность не установлена; evidence привязывается к content hashes.

Маршрут 08 → 000 → 34 → 18 → 01 → 23/24/25 → 36/36.1/36.2 прочитан адресно. Bounded OBSERVE принят с открытыми F1–F3; новый rollout не назначен. Прежние выводы Astra известны, слепая независимость не заявляется. Вспомогательный simple_local оказался недоступен; анализ продолжен основным агентом.

## AMENDMENT / EVIDENCE HANDOFF от пользователя через WEB_07

БЛОК 1 не изменяется. Выписка координатора — адресный источник, GitHub агентом не читался; оригинальные ZIP/raw bytes локально пока недоступны.

- F1: Actions `38234408864`, job `114761827459`, FAIL, `test_web_alarm_projection_concurrency.ProjectionRaceTests.test_completion_never_admits_new_open_state`; 20 запусков, один FAIL; строка 349 `self.assertTrue(active_dir.is_dir())` → `AssertionError: False is not true`. Artifact `wa4r-diag-independent-38234408864-1`, `results.json`, `isolation.jsonl`. Ранее handoff сообщает completed/PLANNED после отказа записи task.json; это не воспроизведённый здесь исторический raw state.
- F2: Actions `38234416619`, jobs `114761856006` и `114761856074`, FAIL, `test_web_alarm_mutation_executor.RaceTests.test_execution_racing_the_task_closure_never_writes_into_a_closed_task`. Цепочки: `event_checkpoint_store.py:85` → FileNotFoundError active/task_e/events.jsonl → EventCheckpointStoreError при release claim; `task_store.py:186` → FileNotFoundError active/task_e/task.md → TaskStoreError при acquire claim. Ранний FAIL: run `38220560220`, job `114715508896`, FileNotFoundError active/task_e/microtasks/m1/restore_point/snapshots/*.bin.
- F3: отдельные WA-017 jobs `114761827262` / `114761855777` в runs выше дали 20/20 PASS каждый. Первый красный F3 run/traceback НЕ идентифицированы; эти PASS его не закрывают.
- Пути D:/a/_temp относятся к runner, не локальному ПК. ZIP может предоставить пользователь/координатор. Продолжать без production repair; raw terminal safety и fresh-process recovery доказывать отдельно. Исторические FAIL не повышать до VERIFIED повторным PASS.

## Аудит актуальности тестов — ДО новых тестовых изменений

Контракт: directory move — commit point; вне active TASK нет новой physical mutation. COMPLETED directory + PLANNED — допускаемая прерванная запись статуса, требующая отдельного recovery proof, а не normal completion PASS. Прямой TaskStore.complete_task — storage primitive, не RC-5 gate; обязательность VERIFIED всех microtasks к нему не применяется. Raw observer не получает expected из ProjectionService/completion_state.

| Инвариант → production-контракт | Существующий selector (module/class) | Oracle | Актуальность / действие |
| --- | --- | --- | --- |
| F1 move не произошёл → PRE сохранён | projection_concurrency.ProjectionRaceTests.test_native_windows_reader_refuses_move_and_preserves_active_task | Real Windows handle, error chain, terminal snapshot/fresh read | CURRENT; повторить без изменения |
| F1 перемещение/статус/новые writers | projection_concurrency.ProjectionRaceTests.test_completion_never_admits_new_open_state | START barrier+jitter, raw snapshot, safe pre-move refusal, producer outcomes | INSUFFICIENT для post-move failure/recovery; strict asserts не ослаблять |
| F1 status persistence interrupted | reliability_wa017.CrashSafeCompletionTests.test_a_failed_status_write_after_the_move_is_finished_later | Injected whole _write_task failure, production getters, recovery в том же процессе | INSUFFICIENT для native Windows replace failure и fresh-process raw oracle; дополнить новым diagnostic case |
| F1 pre-move injected refusal | reliability_wa017.CrashSafeCompletionTests.test_a_failed_move_writes_nothing_and_the_task_stays_active | task.json bytes + location + repeat complete | CURRENT; сохранить |
| F2 close-first/execute-first | mutation_executor.RaceTests.test_execution_racing_the_task_closure_never_writes_into_a_closed_task | sleep-based race, PRE/POST, DONE, результат; child stderr на FAIL | INSUFFICIENT: нет exact snapshot/acquire/release schedules и raw restart ledger; assertions соответствуют желаемому контракту, падение не делает их OBSOLETE |
| F3 after-move crash | reliability_wa017.CrashSafeCompletionTests.test_death_after_the_move_leaves_a_closed_task_that_a_fresh_process_finishes | exit9, completed/PLANNED, writers refused, fresh complete | CURRENT; добавить raw independent concurrent phase proof, не заменить |
| F3 before-move / after-status crash | reliability_wa017.CrashSafeCompletionTests.test_death_before_the_move_changes_nothing / test_death_after_the_status_write_is_a_finished_completion | controlled exit, state/recovery | CURRENT; включить focused |
| F3 competing writers | reliability_wa017.CompletionCrashRaceTests.test_writers_racing_a_dying_completion_never_land_in_the_closed_task | start barrier, staggered sleep, terminal before assertion, strict REJECTED/exit9 | INSUFFICIENT для детерминированного interleaving; сохранить первый FAIL и исходные ожидания |

Итог аудита: оснований OBSOLETE нет, утверждённого изменения production-контракта нет; старые ожидания не подгоняются под наблюдённые исключения. Новый диагностический module дополнит накопительную regression, не объявит известный API error исправленным. Предварительный бюджет: один небольшой pilot, один адресный focused набор, без 80-round stress и без whole-project FULL при отсутствии production изменений. При harness ошибке — отдельный сохранённый attempt, затем только оправданный адресный повтор.

## Итог F1–F3

**Подтверждены два дефекта доставки результата F2 и отдельный raw read error при конкурентной projection. В исследованных schedules незаконная physical mutation не обнаружена.** Native post-move status failure оставляет recoverable closed TASK; fresh-process gated recovery действительно выполнен. Эти выводы ограничены зафиксированными состояниями и не отменяют исторические FAIL.

| Finding | Доказано локально / root cause | После fresh process | Severity и оставшаяся неопределённость |
| --- | --- | --- | --- |
| F1 pre-move | Штатный прежний native Windows handle test прошёл; известный открытый handle не позволяет переместить каталог, active TASK/data сохраняются. Это контролируемый native sharing отказ, не injected exception | Прежний test выполняет fresh-process capture terminal; current focused PASS. Прежний DIAG отдельно доказывал REJECTED после создания blocker | Исторический F1 OPEN. Не каждый CloseoutError относится к pre-move |
| F1 post-move/status-pending | Новый worker реально выполняет directory move; перед штатной записью статуса удерживает обычный read handle на completed/task.json. Windows выдаёт PermissionError/WinError 5 через TaskStoreError/CloseoutError. Raw completed-only/PLANNED; task record равен PRE, restore point/RAW не потеряны, staging orphan нет | Новый mutation request REFUSED без apply; свежий CloseoutService.complete → COMPLETED/resumed=MOVED_STATUS_PENDING; повтор → REJECTED, TASK_COMPLETED event ровно один | HIGH evidence target исторического F1; повреждение данных в контролируемой ветке не доказано. Причина **этого** отказа доказана; первоначальный CI terminal snapshot/error chain отсутствует локально. Его assertion active=False совместим с этой веткой, но не устанавливает её самостоятельно |
| F2 cached acquire/task.md | Worker удерживает operations lock, но acquire читает TASK без mutation lock; pause после выбора active path до read_text. Прямой TaskStore.complete_task берёт только mutation lock и перемещает каталог. Продолжение читает старый путь → FileNotFoundError → TaskStoreError, не перехваченный acquire handler MutationExecutor | Raw completed/COMPLETED, op INTENT, receipt=None, target PRE, 0 apply. Новый процесс replay → REFUSED, operation record не изменён | **MEDIUM confirmed reliability defect**, safety class high-risk. Error chain/path совпадают с выпиской WEB_07; точный исторический schedule/полное множество outcomes не восстановлены |
| F2 cached release/events.jsonl | DONE и exact receipt уже сохранены под boundary locks. Release выполняется позже без mutation lock: claim file durably RELEASED, затем events path вычислен как active. Move происходит до path.open; append → FileNotFoundError → EventCheckpointStoreError. `_release` не ловит этот тип | Raw target POST, DONE/receipt сохранены, active claim отсутствует; событие TARGET_CLAIM_RELEASED отсутствует, прежняя история сохранена. Свежий replay возвращает тот же receipt, apply count остаётся 1 | **MEDIUM confirmed reliability/audit gap**, не доказанная незаконная запись. Caller получает exception после фактического исполнения; автоматический физический retry недопустим. Совпадает с исторической цепочкой, но оригинальный raw terminal CI не доступен |
| F2 snapshot / checkpoint | Ранний restore_plan после cached snapshot path и move даёт контролируемый REFUSED/RESTORE_POINT_NOT_VERIFIED, PRE сохранён. Отдельный прямой ProjectionService.build с тем же окном в verify_restore_point выдаёт raw FileNotFoundError; старые checkpoint.json/md побайтово сохранены | Свежая projection строится; checkpoint классифицируется STALE, authoritative=false. Target PRE, 0 apply, manifest/snapshots сохранены | **MEDIUM raw-reader reliability defect**. Это доказанная конкретная reader ветка. Первоначальный snapshot FAIL внутри MutationExecutor не атрибутирован до полного исходного traceback: нельзя объявить прямой build точной исторической call chain |
| F2 STARTED/apply/move/DONE | Реальный mutation boundary удерживает mutation lock. После durable STARTED writer остановлен до apply; close пытается взять тот же lock, независимый bounded lock probe получает TaskStoreError. Move между STARTED и DONE в этом compliant path невозможен. После release: apply → durable DONE → выход boundary → direct move | POST/DONE, один apply, fresh replay REPLAYED | Гарантия этого production пути сохранена. Требование «STARTED → apply → move → DONE» проверено как **запрещённое interleaving**, а не искусственно создано отключением lock. Ранние read и поздний release находятся вне этой гарантии |
| F3 marked crash/restart | Gated completion реально переместил TASK; marker записан после move и до process exit91, пока оба TASK locks удерживаются. Два late writers стартуют; microtask writer доказанно ожидает mutation lock. После crash оба отказывают, late operation/microtask не появились | Raw completed-only/PLANNED → fresh gated COMPLETED; повтор REJECTED, один TASK_COMPLETED, 0 apply, PRE/immutable files сохранены. Отдельный writer-first control даёт REJECTED и **не** достигает crash marker | **INCONCLUSIVE для первоначального исторического F3**: red run не найден. Новые сценарии доказаны, root cause первого FAILED:CloseoutError не установлен. Два исторических 80-round PASS и текущий PASS это не меняют |

### Почему locks и error handling дают именно эти исходы

`task_store.py::complete_task` удерживает только mutation lock; gated `closeout.py::complete` берёт operations → mutation. `target_claim_service.py::acquire/release` берут operations → target, поэтому direct storage completion может переместить TASK во время их read/event work. Авторизованная physical mutation, напротив, выполняется в `mutation_boundary` под operations → mutation → target; STARTED и DONE записываются внутри неё.

`task_store.py::_load_task_from` читает task.json и task.md по переданному каталогу: путь не обновляется после move. `event_checkpoint_store.py::append_event` получает Path до открытия, а запись release-claim уже произошла в отдельном claim store. `MutationExecutor._execute` ловит TargetClaimError на acquire, `_release` — TargetClaimError/OperationStoreError/TaskStoreError, но не EventCheckpointStoreError. Это доказывает механизмы unhandled errors, не расширяет контракт на произвольные внешние writers.

`manifest_store.py::restore_plan` оборачивает snapshot read OSError в ManifestStoreError, который executor превращает в REFUSED. `verify_restore_point` читает snapshot после is_file без такого OSError wrapper; direct projection build распространяет FileNotFoundError. `ProjectionService.rebuild_checkpoint_locked` дополнительно оборачивает build error в ProjectionError; этот **другой** entrypoint не следует считать эквивалентом direct build. Новые tests различают эти пути.

## Новые тесты, актуальность и пределы oracle

Добавлен один auto-discovered module `test_web_alarm_wa4r002_diagnostics.py`, **8** методов. Существующие tests/production/runner/CI не изменены. Первый pilot имел 7 methods; после него усилены raw PRE/plan/microtask/receipt checks, доказан lock-wait late writer и добавлена отдельная projection/snapshot/checkpoint regression. Это новая test revision; финальные counts относятся к ней.

Audit delta после pilot: `CheckpointRebuildFailureTests.test_a_failed_rebuild_keeps_the_previous_checkpoint_byte_identical`, `test_missing_corrupt_partial_or_tampered_checkpoints_are_never_valid` и `test_a_real_windows_sharing_violation_is_a_failed_rebuild_not_lost_data` — **CURRENT**, входят в focused. Они проверяют rebuild/cache integrity, но не cached snapshot path при direct read; новый case дополняет, не заменяет их. F2 replay tests и `test_closed_task_replay_returns_the_persisted_receipt` — **CURRENT**, также выполнены.

Для F1 concurrency test нужна последующая адресная корректировка **diagnostic outcome classification**: ветка «не COMPLETED значит active» не представляет допустимый interrupted status-pending shape. Это **NEEDS UPDATE для этой ветки oracle**, а не основание принимать любой failed closeout. Прежде чем менять её, WEB_07 должен проверить native error phase, completed-only/raw invariants и fresh recovery; обычный completion PASS и recoverable interruption должны остаться разными verdicts. В этой задаче старая строгая проверка сохранена и выполнена. F2/F3 strict assertions также не ослаблялись: unhandled exception не становится допустимым бизнес-результатом от того, что raw safety проверена отдельно.

Raw oracle: stdlib JSON с duplicate-key rejection, literal PRE/POST bytes, hashlib SHA-256, raw TASK/plan/microtask/operation/receipt/events и hashes всех fixture files. Expected values не берутся из production state getters/projection. Чтения делаются на обозначенных паузах или после worker reap. Fixture targets и RAW/restore point сохранены; event prefix проверяется отдельно от законных новых events. Fresh checkpoint validation — **вторичное** production observation, дополненное независимым сохранением checkpoint bytes и known source transition active→completed.

Negative controls: удаление native handle вызывает ожидаемый внутренний FAIL; подмена raw receipt SHA вызывает ожидаемый внутренний FAIL. Внешний quality suite принимает только ровно 1 failure/0 errors/0 skips на испорченный case. Это проверка чувствительности конкретных assertions, а не доказательство качества всех oracles. Barrier reach, native error chain, exit91 и отсутствие crash marker в writer-first control проверяются явно. Seed не нужен: payload фиксирован, порядок задаётся semantic barriers; clocks/sleeps не служат доказательством порядка. Polling имеет deadline 25 s, worker completion 30 s, cleanup kill/reap — только собственные процессы.

## Выполненные проверки и команды

| Attempt | PASS | FAIL | ERROR | SKIP | Seconds | Exit / guard violations |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| pilot-1, предыдущая revision, 7 new cases | 7 | 0 | 0 | 0 | 10.756 | 0 / 0 |
| focused, финальные 8 new + 55 прежних | 63 | 0 | 0 | 0 | 97.003 | 0 / 0 |
| negative controls, отдельный harness | 2 | 0 | 0 | 0 | 2.303 | 0 / 0 |

**PASS здесь означает выполнение заявленного diagnostic oracle; для cases, ожидающих конкретный API exception, он одновременно подтверждает существующий defect, а не его исправление.** В JSON сохранены фактические child exit2/error chains и terminal facts; их нельзя скрыть за общей зелёной строкой.

Из корня checkout, Python 3.12.10 / Windows, `.venv`:

~~~powershell
python -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-R-002 --output "$env:TEMP\codex-wa4r002-76z9y0j6\pilot-1" test_web_alarm_wa4r002_diagnostics
python -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-R-002 --output "$env:TEMP\codex-wa4r002-76z9y0j6\focused" test_web_alarm_wa4r002_diagnostics test_web_alarm_reliability_wa017 test_web_alarm_projection_concurrency test_web_alarm_mutation_executor
python -B -X utf8 reports/CODEX-WA4-R-002/quality_controls.py "$env:TEMP\codex-wa4r002-76z9y0j6\quality"
~~~

Повторитель использует **свежие** output directories. Первый pilot выполнен до добавления восьмого case и относится к своему hash; initial source bytes отдельно не sealed, поэтому reproducible canonical source — финальный module и focused manifest. Остальные attempts не перезаписывались. Полный Web Alarm suite и 80-round stress **NOT RUN**: задача bounded diagnostic, production не менялся, адресный набор включает все три затронутых прежних modules. Новые 8 методов входят в существующий full discovery pattern; static inventory 753 прежних + 8 = 761, это **не** runtime 761 PASS. Focused collection сверена по exact IDs: 63 уникальных, без потерь/дубликатов.

Изоляция: только owned `TemporaryDirectory` fixtures и system TEMP outputs, controlled Python subprocesses, унаследованный штатный audit guard, external sockets/DNS/Git metadata/native shell запрещены. Loopback разрешён guard для существующей инфраструктуры, новые scenarios сеть не используют. Никаких real TASK/storage, реальных ключей или paid API. Guard — trusted-test audit, не hostile OS sandbox. Натуральный Windows механизм вызывается только на одноразовых fixture files; это controlled-native reproduction, не случайный повтор первоначального CI и не proof power-loss durability.

## Evidence и source provenance

- `checks.json`: counts, unique selectors, exact raw paths/hashes, runtime/elapsed, scopes выполненного/NOT RUN.
- `evidence.json`: 24 дедуплицированных raw states и ссылки на них из test facts, reached phases, worker results/error chains и negative controls. SHA state-ref вычислен по canonical JSON со sorted keys; raw records и file hashes сохранены. Повторные identical states не размножаются.
- `versions.json`: before/final content manifests, baseline №302 как supplied identity, границы Git equivalence, preservation/rotation hashes. Все 158 preexisting контрольных файлов неизменны до ротации. Production hashes также совпадают с прежним локальным DIAG manifest; это не доказательство совпадения с конкретным remote CI commit.
- `quality_controls.py`: воспроизводимые negative controls, вне product discovery. Product test source находится в корне checkout и включён в штатный hash collector.
- Raw runner files и logs: `C:/Users/REX/AppData/Local/Temp/codex-wa4r002-76z9y0j6/{pilot-1,focused,quality}` и соответствующие `.log`; компактные факты сохранены в report folder, TEMP может быть очищен системой. Source bytes и evidence при публикации закрепляет пользователь/координатор; хеш сам по себе не immutable archive.

Исторические источники сохранены без правок: [WA4-R report](../CODEX-WA4-R-001/report.md), [DIAG-01](../CODEX-WA4-R-001-DIAG-01/report.md), [Astra analysis](../ASTRA-WEB02-TEST-ARCH-001/report.md), [PR12 handoff](../ASTRA-WEB02-TEST-ARCH-001/pr12-handoff.md). Первичные remote locators из нового AMENDMENT: [F1 run](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38234408864), [F2 run](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38234416619), [ранний snapshot FAIL](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38220560220). Эти страницы агент не открывал; facts о jobs/FAIL выше предоставлены WEB_07. Первоначальный F3 locator остаётся неизвестным. Original ZIP payloads не скачивались/не распаковывались, terminal state исходных красных CI здесь не восстановлен.

## Минимальный repair proposal — ТОЛЬКО для отдельной согласованной задачи

1. **F2 acquire / typed refusal:** перед physical boundary преобразовать конкретный TaskStore read failure в корректный typed refusal либо обеспечить согласованное relocation-safe чтение. Не выдавать недоказанное admission и не перезаписывать source state. Нужны regression assertions PRE/INTENT/no receipt/no apply, включая current cached-task reproducer.
2. **F2 release / audit:** гарантировать согласованность получения directory path и append с direct completion либо явно сохранить известный durable outcome и отдельный pending audit/release result при EventCheckpointStoreError. Нельзя молча терять chronology или повторять physical write из-за отсутствующего ответа. Если добавляется mutation lock, соблюдать общий порядок operations → mutation → target; брать mutation lock уже под target lock нельзя. Требуются DONE/exact receipt/history/claim/replay checks и отсутствие deadlock.
3. **Snapshot readers:** исправлять только доказанный path: consistent read boundary/relocation handling и typed ManifestStoreError вместо raw OSError в verify_restore_point, сохраняя fail-closed и integrity checks. Отдельно проверить direct build, guarded checkpoint rebuild и executor restore_plan: они сейчас обрабатывают отказ по-разному. Без исходного полного CI stack не объявлять это ремонтом именно исторического snapshot FAIL.
4. **F1:** в контролируемой native ветке production recovery работает; обязательного production repair из safety proof не следует. Нужны outcome-specific diagnostics/ответ для interruption, addressable original artifact и адресный test-classification review; arbitrary CloseoutError принимать нельзя.
5. **F3:** production repair не обоснован по нынешним evidence. Найти исходный red run/traceback; сохранить strict assertions, markers и текущие deterministic positive/negative controls. Не чинить неизвестную первопричину по двум зелёным stress runs.

Это proposal для WEB_07, не запрос разрешить repair в текущем запуске. Все части, требующие production изменений, остановлены на evidence/предложении; запрещённые правки не выполнялись.

## DOC IMPACT / NEXT SAFE ACTION

DOC IMPACT: YES — diagnostic results/test coverage; RUNTIME CONTRACT CHANGE: NO; ULTRA/UI/ROLLOUT CHANGE: NO; SHARED DOC DELTA / DOC CLOSEOUT INCOMPLETE. Координатор после независимого review обновляет 23/24/25, общий 000/05/06/34 и 36.2 адресно: отдельные native recovery proofs, подтверждённые F2 delivery errors, сохранённые исторические OPEN и следующий repair scope. Общие документы в этой задаче не редактируются.

**NEXT / получатель WEB_07:** независимо проверить новый source/evidence и source revision, при необходимости получить original F1/F2 artifacts и missing F3 red run, решить точный repair scope. До соответствующего USER GO нет production repair, commit, merge, WARN/GATEWAY REQUIRED/STRICT или следующей задачи. Персональная safe rotation сохраняет постановку и AMENDMENT отдельно, прежние БЛОКИ 2–3 побайтово; БЛОК 1 освобождается только после сохранения результата. Статус остаётся READY FOR INDEPENDENT REVIEW, не VERIFIED.

**Контроль сдачи:** 157 preexisting контрольных файлов неизменны; разрешённая персональная ротация — единственная дельта среди 158. Обе фазы проверены; полная постановка и 267738 bytes прежней истории сохранены побайтово. БЛОК 1 — ожидание. Полные hashes ротации и artifacts — в versions.json.
