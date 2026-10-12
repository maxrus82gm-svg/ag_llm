# ASTRA-WEB02-TEST-ARCH-001 — универсальная тестовая архитектура Web Alarm

STATUS: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**. Architecture/coverage сохранены до реализации pilot; финальный factual closeout — 2026-10-12. GitHub CI и independent acceptance — PENDING.

ARCH CLASS: Web Alarm Workspace / Testing & Quality Assurance. PRIMARY PROFILE: 23; plan/history: 24/25. Исполнение локальное, анализ independent от production oracle, **не blind review**: прежняя диагностика Closeout известна из этого чата. Very High — запрошенный режим; отдельного переключения модели не выполнялось.

## Основание и пределы

Обычный маршрут 08 → общий/персональный 000 → 34 → 18 → 01 → 23/24/25 прочитан адресно. User-approved БЛОК 1 управляет текущим scope. Общий 34 и профильные summary отстают от локального WA4-R: это не причина повторять или принимать старые стадии. Git/GitHub, production, прежние tests/runner, CI workflow и общая документация вне write-scope.

Локальный исходный AST inventory: 55 Python modules, 749 `test_*` methods. Это статический перечень, **не** 749 новых PASS и не гарантия unittest collection. Предыдущая локальная DIAG: full 748 PASS + 1 symlink SKIP; реальный Windows pre-lock reader reproducer доказал лишь одну безопасную возможную ветку. Первоначально findings/revision PR №12 отсутствовали; после локального FULL пользователь передал F1–F3 и source revision. Handoff сохранён дословно в `pr12-handoff.md`, анализ дополнен ниже. Git/GitHub не читались; соответствие локальных байтов указанному commit и закрытие findings — UNVERIFIED.

## COVERAGE MATRIX

Ниже source-level mapping, затем pilot execution evidence. Короткие module names в таблице означают test_web_alarm_<name>.py. `test_...` имена — stable unittest selectors, не номера прошлых PASS. Покрытие не оценивается одним процентом: одна строка содержит invariant, fixture state, interleaving/fault, oracle и оставшиеся границы.

| ID / независимый инвариант | Существующее покрытие (module → test selector) | Реальный предел / пробел | Метод и evidence |
| --- | --- | --- | --- |
| WA-I01 Lifecycle: только разрешённые переходы; предыдущая VERIFIED стадия не повреждается | `state_machine` → `test_valid_lifecycle_requires_verification_evidence`, `test_second_microtask_cannot_prepare_before_previous_verified`; `state_machine_cas` → `test_d1_delayed_transition_never_rewrites_the_newer_status`; recovery repair2/wa014 | Нет компактного declarative transition model с coverage каждого edge/precondition; нельзя считать один happy path полной машиной | FUTURE: явная независимая таблица переходов и negative edges; raw status/plan/history до/после, а не сравнение двух production getters |
| WA-I02 Closeout: directory move commit point; closed формы не принимают новых writers | `reliability_wa017` → `test_death_after_the_move_leaves_a_closed_task_that_a_fresh_process_finishes`, `test_writers_racing_a_dying_completion_never_land_in_the_closed_task`; `projection_concurrency` → `test_completion_never_admits_new_open_state` | PR12 F1/F3: natural post-move/status-pending и первоначальный crash-race error не закрыты. «Любая exception безопасна» недопустимо | HOLD: oracles F1a/F1b/F3 ниже; отдельно safety и recovery. Пилот не чинит и не заменяет PR №12 |
| WA-I03 Locks: взаимное исключение, сохранность revisions/events, OS release после crash | `operation_store_concurrency` → `test_concurrent_independent_writers_lose_no_record_revision_or_event`, `test_lock_of_a_crashed_process_is_released_by_the_os`, `test_lock_timeout_fails_closed_without_writing`; target claims concurrency | Claim-only independent-target race ещё не доказывает отсутствие cross-workspace contract/receipt смешивания при исполнении одного textual operation ID | PILOT P3: два реальных процесса одновременно внутри disjoint mutation boundaries; одинаковые task-local ID, разные workspace/bytes, raw isolation oracle |
| WA-I04 Identity/replay: один effect на durable identity; receipt исторический | `lost_response` → `test_A1_A2_http_lost_delivery_then_new_process_replays_exact_receipt`, `test_A3_four_fresh_clients_deliver_one_contract_concurrently`, `test_A7_durable_receipt_is_historical_and_does_not_overwrite_later_drift` | Nonempty write/create и later external drift покрыты; empty-existing ≠ absent в цепочке tracked CREATE/DELETE + crash/replay не покрыт | PILOT P2: empty CREATE/DONE crash, replay, tracked DELETE, replay старого CREATE без resurrection; exists/size/hash независимы |
| WA-I05 Snapshot/manifest: immutable PRE, scope, integrity до mutation | `manifest_store` → `test_corrupted_snapshot_fails_closed_and_blocks_microtask`, `test_tampered_snapshot_path_is_rejected_before_external_read`, `test_existing_restore_point_is_never_overwritten`; mutation admission | Secret/size/storage-root policy не едина для snapshots; это известный runtime preflight риск, не blanket тестовая гарантия | Existing + FUTURE отдельный admission corpus. Pilot проверяет сохранность snapshot files, но не объявляет policy gap закрытым |
| WA-I06 Checkpoint/projection не authority; повреждённый cache не создаёт permission | `projection` → `test_fabricated_checkpoint_cannot_steer_context`, `test_interrupted_rebuild_between_json_and_md_is_not_valid`; `reliability_wa017` → `test_missing_corrupt_partial_or_tampered_checkpoints_are_never_valid` | Часть сравнения использует тот же ProjectionService/checkpoint_fields: shared implementation bug может пройти обе стороны | FUTURE raw reference oracle + metamorphic cache deletion/rebuild; отдельный model contract. Production projection только observation, не источник expected |
| WA-I07 Reconciliation: disconnect ≠ failure, uncertain fate не replay authority | `reconciliation_decision` → `test_pre_state_that_also_satisfies_post_is_not_retry_safe`, `test_missing_core_evidence_is_manual`; `lost_response` interruption; transport authority | Recovery выбранных crash points сильна; не каждая low-level IO phase испытана | PILOT P1: fault во время target staging fsync, fresh-process refusal без повторной попытки physical apply; не ADOPT/RETRY без Resolver |
| WA-I08 RC-4: preserve current before destructive restore; final exact proof всего набора | `rollback` → `test_preservation_failure_of_one_target_blocks_every_target`, `test_noop_target_drifting_after_its_check_is_not_success`, `test_crash_between_verified_and_release_keeps_ownership_until_replay` | Хорошее targeted покрытие; bounded multi-target schedules и real power-loss отсутствуют | Сохранить накопленные regressions; не клонировать эти assertions ради нового framework. Будущий scenario reducer сохраняет prerequisites/claims |
| WA-I09 RC-6: settlement не подделывает lifecycle и не восстанавливает authority | recovery coordinator repair1…4b/wa014, `state_machine_cas` → `test_b_abort_settlement_is_not_overwritten_by_a_stale_verification` | Много регрессий; общее discovery/coverage metadata отсутствует, длинный suite нельзя заменить новым pilot | Inventory + профили, независимый raw settlement oracle позже; existing exact selectors остаются обязательными |
| WA-I10 Windows IO/crash: ошибка до commit не повреждает PRE; partial commit не SUCCESS | `mutation_executor` → `test_started_not_persisted_writes_nothing`, `test_a_refused_write_is_proved_unchanged_and_a_retry_executes_it`, real Windows sharing test; WA017 move/status failures | Refused-write test подменяет весь `_atomic_write_bytes`, поэтому не выполняет temp write/flush/cleanup при failing fsync | PILOT P1: реальный helper пишет staging bytes, injected ENOSPC на fsync; original target и snapshot unchanged, staging orphan отсутствует, raw STARTED/no receipt |
| WA-I11 Restart: устойчивые facts переоткрываются без process memory | `restart_recovery` → оба new chat/server tests; WA4-A child execution и WA017 crash | Состояния типовые; empty tombstone/historical create interplay отсутствует; process exit ≠ power loss | PILOT P2/P3 fresh workers + raw read oracle; точный exit point, count apply attempts, snapshot hashes, command/seed |
| WA-I12 Isolation: fixtures отделены от пользовательских data; доказательство выполнения runner | unchanged `wa4a_acceptance.GUARD`, TEMP+loopback constraints; workflow guarded focused/full | GUARD допускает весь system TEMP, не только fixture; это trusted-test audit, не sandbox hostile native. Smoke unguarded; current runner не требует nonzero/expected collection, hashes пишет после run | Quality probes в TEMP, acceptance envelope и producer/consumer checks ниже; runner/CI сейчас не менять |
| WA-I13 Input quality / workspace isolation | `payload_store` exact bytes/EOL/BOM/limits, `target_identity` aliases/escape, `workspace_registry` два workspaces, claim-only cross-task tests | Нет end-to-end empty/absence timeline и concurrent execution/replay same textual ID across two workspaces | P2 + P3; P3 fixed seed binary corpus, Unicode/spaces target, exact exists/size/SHA; без нормализации bytes |

### AMENDMENT — PR №12: F1–F3 и независимые oracles

**Происхождение:** пользовательский handoff, repository `maxrus82gm-svg/ag_llm`, main `2d05cc40fe2d9beae16a70458cb29bb03f904f97`, Draft PR №12/GPT `d07e603eeb5a2a831739bd7a168bd158d25e95f5`, №288. Это заявленные source identities; агент их не верифицировал. CI `38234408864` и `38234416619` не запускались/не читались агентом. Пользователь сообщает 749 PASS + 1 FAIL из 750 в последнем PR CI; локальные 752 относятся к другому content manifest, поэтому эти числа не взаимозаменяемы.

**Что изменилось в заключении:** первоначальное «findings недоступны» заменено конкретными F1–F3. Безопасный pre-move отказ больше не рассматривается как объяснение всего CloseoutError класса. Для post-move отказа необходим отдельный recovery proof; для F2 — проверка physical effects и stale paths. P1–P3 сохраняются: они закрывают другие пробелы и не дублируют диагностические cases PR12. Новые PR12 stress/recovery tests в этом пилоте **NOT RUN / DESIGN ONLY**; это адресные требования к независимому продолжению, не дополнительные реализованные тесты.

Локальный `TaskStore.complete_task_locked` (`task_store.py:543`) сначала перемещает каталог и затем пишет статус; промежуточное состояние предусмотрено. `CloseoutService.complete` (`closeout.py:85`) допускает завершение такого состояния, но намерение кода не доказывает успешный recovery конкретного CI TASK. Прямой `TaskStore.complete_task` (`task_store.py:530`) явно является storage primitive без RC-5 gate: его race нельзя оценивать требованием «все microtasks VERIFIED», относящимся к gated workflow.

| Finding / invariant mapping | Ближайший существующий test; что уже есть | Независимый oracle и недостающее доказательство |
| --- | --- | --- |
| **F1a pre-move / WA-I02,I10** | `projection_concurrency.ProjectionRaceTests.test_native_windows_reader_refuses_move_and_preserves_active_task`; `reliability_wa017.CrashSafeCompletionTests.test_a_failed_move_writes_nothing_and_the_task_stays_active` — real handle/injected refusal | После quiescence active=1, completed=0; raw TASK identity/status и immutable files совпадают с PRE; workspace bytes unchanged для no-mutation fixture. Ошибка должна быть именно directory-move PermissionError с сохранённой цепочкой/errno/winerror/phase. При конкурентных writers разрешены только изменения, связанные с зафиксированным admitted action; blanket equality mutable plan/events неверна. Нельзя принимать FileNotFoundError/timeout/status-write failure этим oracle |
| **F1b post-move/status-pending / WA-I02,I10,I11** | `reliability_wa017.CrashSafeCompletionTests.test_a_failed_status_write_after_the_move_is_finished_later`, `test_death_after_the_move_leaves_a_closed_task_that_a_fresh_process_finishes` — injected failure/crash с recovery | В CI38234408864 сообщается completed=1 и raw status PLANNED. Нужно независимо доказать active=0, unique TASK, preserved records/snapshots/target bytes, запрет новых physical writers; это только safety phase. Затем ровно один явный gated recovery в fresh process без fault: completed=1, status COMPLETED, все immutable facts сохранены, нового apply нет. Отдельный повтор completion не создаёт TASK/effects. Без этого recovery=NOT PROVED и finding открыт, даже если форма похожа на MOVED_STATUS_PENDING |
| **F2 direct close vs mutation / WA-I02,I03,I05,I07,I10** | `mutation_executor.RaceTests.test_execution_racing_the_task_closure_never_writes_into_a_closed_task` — execute-first/close-first branches; по handoff CI38234416619 и отдельные 80 rounds FAIL | Нужен semantic schedule и raw ledger «durable STARTED → apply enter/exit → durable DONE / directory move» с отдельными разрешёнными interleavings, а не classification по одному API result. Захватить FileNotFound path/phase, обе directories, task.md, snapshot/manifest, raw operation/receipt/events и workspace bytes **до recovery**. Проверить отсутствие active resurrection, потери immutable files/старого event prefix, повторного apply и ложного EXECUTED/receipt. Отсутствие доказанного незаконного write не равно доказанному fail-closed |
| **F3 crash/restart / WA-I02,I03,I11** | `reliability_wa017.CompletionCrashRaceTests.test_writers_racing_a_dying_completion_never_land_in_the_closed_task` — before/after-move race; диагностические additions №287 по handoff | Обязательны reached-phase marker и заданный crash exit; FAILED:CloseoutError не эквивалентен REJECTED или crash. Если writer первым создал blocker, raw plan/operations доказывают blocker и TASK остаётся active. Если move/crash первым, completed-only, writer effects отсутствуют; fresh gated completion проверяется как F1b. Два последующих 80-round PASS не объясняют прежний FAIL, его evidence сохраняется |

**Общий raw state oracle для F1–F3.** Считывать filesystem только на барьере либо после остановки/ожидания всех собственных workers; observer не вызывает repair/build. Независимо вывести форму из наличия `tasks/active/<id>`, `tasks/completed/<id>` и строгого JSON `task.json`, а не из `completion_state()`/projection. Обе directories одновременно, исчезнувшая TASK, неправильная identity, unreadable/invalid JSON — FAIL либо ERROR невозможности доказательства, никогда «допустимый Windows отказ». Completed directory + PLANNED — классификация `status-pending`, **не PASS**. Сравнивать immutable file hashes и точный исходный event prefix; mutable fields допускаются лишь по отдельной test-model transition с ledger причин. Cache/projection не источник expected.

Для **F2** отдельно фиксировать две контролируемые допустимые последовательности: (1) завершённый write/DONE до move: exact POST и исторический receipt сохраняются, после move только replay без apply; (2) move до mutation admission: exact PRE, нет нового apply/receipt, явный отказ. Если natural schedule пересекает STARTED/apply/move и не укладывается в доказанную последовательность, сохранить uncertain состояние и отдельно проверять отсутствие нового исполнения; не выбирать удобную ветку по конечным bytes. Returned SUCCESS с отсутствующим durable подтверждением либо physical effect после зафиксированного закрытия — нарушение. Сохранённая неопределённая операция с honest refusal может быть безопасной, но не доказывает recovery и не оправдывает необработанный FileNotFoundError. Negative controls будущего oracle: lost snapshot, duplicate TASK, неверный receipt hash, изменение bytes после move должны дать red. Instrumentation обозначается test-only; clocks разных процессов сами по себе не заменяют barriers.

Не клонировать четыре существующих regression под новыми именами. После отдельного разрешения расширить их evidence/raw observer или добавить только отсутствующий deterministic interleaving; оставить прежние assertions и исходные red artifacts. Естественный WinError и injected fault имеют разные labels. Сначала сохранить natural failure; controlled replay проверяет гипотезу, а не автоматически устанавливает первопричину оригинального CI.

## TEST ARCHITECTURE PROPOSAL

Рекомендуется один стандартный `unittest` контур с профилями, без логики для конкретной LLM. Агент выбирает разрешённый profile/selector, запускает ту же команду, читает evidence; право запускать Git/CI и принимать результат остаётся отдельным организационным контрактом.

| Компонент | Contract и независимость | Сейчас / следующий шаг |
| --- | --- | --- |
| A Shared fixtures | Явные workspace/storage roots под новым owned TEMP, task/operation identity, exact bytes и отсутствие файла как разные состояния; fixtures не поднимают live services. Cleanup только own root, workers остановлены до cleanup | Pilot минимальные параметризованные helpers в одном новом test module; существующие fixtures не мигрируются |
| B Scenario runner | Типизированные steps: API action, spawn, phase barrier, crash, reopen, observe, assert. Bounded deadlines, собственные child processes, propagated guard, deterministic phase order; seed воспроизводит данные, **не** OS scheduling | Pilot небольшой process helper/worker; generic DSL, arbitrary shell, retries и scheduling engine НЕ реализуются |
| C Invariant oracle | Expected от explicit test contract/model; фактические bytes, raw JSON identity/revision/receipt, history prefix, directories. Не вычислять expected через production assess/projection/reconciliation. API return — вторичное наблюдение | Pilot raw stdlib oracle без production readers. Сам oracle проверяется negative controls. Disk snapshot делается при quiescence или на declared barrier, не считается атомарным во время arbitrary writes |
| D Fault injection | Именованная fault phase, activate count ≥1, точный exception/exit code, before/after commit. Различать injected IO, controlled real OS refusal и natural reproduction | Pilot fsync ENOSPC / process exit after durable DONE / barrier. Ни production patch, ни fault→blanket PASS |
| E Evidence collector | Versioned manifest: task/scenario/invariant IDs, source hashes до/после, Python/OS, seed+corpus, phase transcript, fault trigger count, expected/observed, error chain, statuses, exact command, raw-artifact hashes. No secrets/raw payload dumps | `self.facts` использует существующий runner JSON; report содержит pre/post source manifest. Proposed common envelope/validator не выдаётся за работающий новый runner |
| F Profiles | SMOKE — bounded invariant samples; FOCUSED — механизм + новая regression; FULL — все накопленные tests без замены старых; STRESS — отдельный USER GO с count/time/seed bounds | Existing workflow сохранить. Pilot standalone module auto-discovered full. Добавление нового CI focused selector — только координатор после review |

### Доказательность статусов

- PASS относится к exact source revision, input corpus, expected collected test IDs и реализованным assertions; не означает independent acceptance, rollout либо отсутствие unknown schedules.
- FAIL — нарушен заявленный invariant при корректных prerequisites. ERROR — harness/runtime execution не дошёл до доказательства (включая неожиданный exception, worker timeout, bad fixture). Оба запрещают acceptance; classifier отдельно указывает production/harness/unknown provenance.
- SKIP — объявленная platform/capability причина; не превращается в PASS. NOT RUN / INCOMPLETE — не был запущен selector, оборван runner или нет полного JSON. XFAIL для known critical races не вводится.
- Consumer требует exit=0, `successful=true`, zero guard violations, ожидаемый nonzero collection, уникальный run ID, согласованные counts и test status entries, необходимые artifact hashes, unchanged source manifest, явные permitted skips. Одного зелёного exit, `successful`, или суммы PASS недостаточно.
- Каждая property имеет отдельный ID. При subtests различать top-level tests, cases и failed assertions; не вычитать количество failing subtests из числа parent tests. Failed evidence сохраняется в `finally`/до assertion; не писать только на happy path.

### Воспроизводимость и накопление

Фиксировать input seed и фактический corpus hash, но concurrency воспроизводить barriers на semantic boundaries. Не применять sleep как доказательство порядка. Crash-point достижение должно подтверждаться marker + заданным exit, иначе ERROR. Сокращать failing trace bounded delta-debugging только в TEMP и при сохранении fixture/preconditions/observed schedule; minimal reproducer не заменяет исходный полный failure evidence. Retry создаёт новый attempt, не переписывает прежний FAIL.

Новые tests регистрируются как `(invariant ID, risk, initial state, action/fault schedule, oracle independence, expected exit/status, platform, bounds, source selectors, related regression IDs)`. Review обязан ответить, чем сценарий отличается от ближайшего существующего test. Fixed historical regressions остаются в FULL; удалять дубликат можно лишь отдельным review с сохранением покрытия. Метаданные следует хранить declaratively рядом с tests и проверять against unittest collection; автоиндекс из AST полезен для навигации, но не доказывает исполнение.

## PILOT DESIGN — зафиксирован до реализации

1. **P1 / WA-I07,I10:** `test_staging_fsync_failure_preserves_prestate_across_restart`. Новизна: реальные staging write/flush/cleanup вместо исключения из целиком заменённого helper. Invariant: PRE exact, STARTED без receipt, snapshot intact, fresh replay не пишет. Fault ENOSPC включается только внутри target apply, не ломает pre-STARTED store persistence.
2. **P2 / WA-I04,I11,I13:** `test_empty_create_crash_delete_and_historical_replay_never_resurrects`. Новизна: existence/zero-size исторические receipts на tracked create/delete timeline. Child dies после durable DONE; старый CREATE replay после DELETE не создаёт файл заново. Expected empty-file hash и absent state заданы вне production.
3. **P3 / WA-I03,I11,I13:** `test_same_operation_id_in_two_workspaces_has_independent_concurrent_effects`. Новизна относительно claim-only tests: concurrent real execution и replay двух workspace contracts с одним textual operation ID. Оба workers остановлены внутри apply после STARTED, затем отпущены; независимые raw records/receipts/bytes/history и apply-attempt counts исключают cross-talk.

Test-only helpers остаются в `test_web_alarm_new_invariants.py`, поэтому существующий source-hash collector включает весь pilot. Никаких новых пакетов. Бюджет: одна smoke разработка, focused по трём scenarios + ближайшим modules; один FULL после стабильного pilot, если доступен. Повторять FULL без новых причин не требуется. STRESS не запускается.

## Качество тестовой системы: сейчас и позже

Сейчас: zero-collection/failed-subtest quality probes в отдельном TEMP runner invocation; raw oracle negative controls; exact collection ID/hash manifest; тест fault trigger; bounded child cleanup; validation preconditions и source freeze. Report хранит намеренные красные quality probes отдельно от product tests.

Позже, отдельным scope: generic evidence schema validator; fixture ownership narrower than whole TEMP; per-test duration/deadline, deterministic schedule catalog; targeted mutation testing на известных security gates в disposable copy; dependency-aware reducer; curated nightly stress Windows + optional Linux. Не запускать массовый mutation testing/перестройку всех tests в этом пилоте.

## Совместимость с существующим CI

Локальный `.github/workflows/web-alarm-tests.yml`: Windows latest, Python 3.12; smoke 5 unittest selectors; PR/manual guarded focused suites + full discovery; upload always, retention 7 days. Новый `test_web_alarm_*.py` соответствует paths filter и full discovery. Существующие focused списки новый module автоматически не подхватят. CI labels «166/719 baseline» исторические, не актуальные счётчики.

Coordinator candidate command (workflow НЕ изменён):

~~~powershell
python -B wa4a_acceptance.py --task ASTRA-WEB02-TEST-ARCH-001 --output "$env:TEMP\astra-test-evidence" test_web_alarm_new_invariants
~~~

В Actions использовать `${{ runner.temp }}/astra-test-evidence`, согласованные TMPDIR/TEMP/TMP, pinned approved sources и artifact upload even on failure. Не переносить локальные абсолютные workspace paths в CI; fixture paths создаются динамически. Missing artifact — INCOMPLETE, даже если существующий upload step лишь warn. Нужен отдельный coordinator gate для полной проверки всех required suites, поскольку ранний failure может пропустить следующие steps. GitHub execution в этой задаче не производится.

## EXTENSION CONTRACT — порядок добавления следующей regression

1. Назначить stable invariant/scenario ID и сослаться на approved behavioral contract. Указать ближайший старый test, новую failure phase/input/interleaving и ожидаемый вклад; простое переименование не принимается.
2. Описать initial facts и prerequisites независимо от production DTO. EMPTY, ABSENT, malformed и unverified — разные классы. Исторический receipt и текущий target проверять раздельно. Сначала исключить ошибку fixture; missing prerequisite — ERROR, не useful PASS.
3. Использовать owned temporary roots и bounded process helper. В production обращаться только actor calls; fault patch действует лишь в test worker и указанной фазе. No live data, shell/Git/network shortcuts. Guard разрешает loopback только там, где тесту нужен настоящий HTTP.
4. Определить oracle, который способен отвергнуть wrong bytes/status/identity. Не импортировать production allowed-transition table для генерации expected, не использовать `ProjectionService.build` одновременно как actual и expected. Проверить минимум один отрицательный пример и факт достижения fault/crash/barrier.
5. Сохранить raw evidence до failing assertion и обеспечить child reap при ERROR. Новая синхронизация должна иметь timeout и phase markers, а не бесконечное ожидание. Timer сообщает ошибку, не выбирает допустимый business outcome. Test harness не должен сам repair состояние до oracle.
6. Добавить `test_web_alarm_<topic>.py` со стандартным unittest. **Не импортировать TestCase-классы напрямую в модуль другого suite:** loader может повторно собрать их. Импортировать module alias/functions либо будущий support module без test methods. Если helpers вынесены за текущую source-hash glob, сначала расширить proposed manifest/validator отдельным согласованным изменением; иначе source provenance неполон.
7. Запустить exact selector, focused и затронутую накопленную regression. FULL остаётся старый suite + новые tests; никакой замены исторического red тестом, принимающим любой exception. Публиковать expected collected IDs, skipped reasons, raw JSON hash и отдельные попытки. STRESS только с budget/seed/count/time и USER GO.
8. Независимый reviewer проверяет novelty, oracle, source revision, результаты и CI portability, после чего координатор добавляет нужный focused selector/workflow artifact. Production repair, PR merge и изменение глобального статуса — отдельные полномочия. Новая regression не означает автоматической приёмки всей подсистемы.

Рекомендуемый consumer envelope (DESIGN ONLY; поверх сохранённого original runner JSON, не замена ему):

~~~json
{
  "schema": "test-evidence/v1",
  "run_id": "unique-attempt",
  "profile": "FOCUSED",
  "scenario_id": "WA-P1",
  "invariants": ["WA-I07", "WA-I10"],
  "source_before_sha256": {},
  "source_after_sha256": {},
  "expected_test_ids": [],
  "collected_test_ids": [],
  "input": {"seed": 742919, "corpus_sha256": "..."},
  "schedule": {"kind": "barrier", "reached_phases": []},
  "fault": {"kind": "injected", "point": "target_staging_fsync", "hits": 1},
  "oracle": {"version": "raw-file-and-record/v1", "negative_controls": "PASS"},
  "counts": {"tests": 1, "cases": 1, "pass": 1, "fail": 0, "error": 0, "skip": 0},
  "execution_complete": true,
  "guard_violations": [],
  "artifacts": [{"path": "results.json", "sha256": "..."}],
  "independent_acceptance": "PENDING"
}
~~~

Пустые expected/collected arrays в примере — schema placeholders, не допустимый PASS. Реальный validator должен требовать непустое точное покрытие, учитывать subtests отдельно, не доверять self-reported oracle verdict без failures/assertions и проверять artifact bytes. Полный source snapshot закрепляет координатор при публикации; SHA без доступных bytes не является archive. CI artifact retention 7 days требует отдельного долговременного compact failure corpus для исторических regressions.

## Переносимость на Ultra

Можно переносить process lifecycle, fixture ownership, bounded scheduler/fault/evidence formats и quality gates. Нельзя переносить Web Alarm статусы, admission, snapshot/claim/rollback semantics или NEXT oracle как правила Ultra. Ultra нужен отдельный invariant profile и mapping к его RUN/Verifier/Run Store/evidence freshness, с собственными required-source manifests и независимым acceptance. Здесь ни Ultra tests, ни runtime не меняются.

## Фактическая реализация и evidence

Реализован один новый `test_web_alarm_new_invariants.py`: 3 TestCase methods + минимальные raw oracle/fixture/child/barrier helpers. Универсальный framework/DSL и новый CI pipeline **не** объявляются реализованными. Пилот соответствует зафиксированным P1–P3; production не менялся.

| Проверка | PASS / FAIL / ERROR / SKIP | Время, s |
| --- | --- | --- |
| pilot-1 | 1 / 0 / 2 / 0 | 3.88 |
| pilot-2 | 3 / 0 / 0 / 0 | 5.867 |
| focused | 103 / 0 / 0 / 0 | 149.532 |
| full | 751 / 0 / 0 / 1 | 660.566 |

Первый pilot run: 1 PASS + 2 ERROR из-за моей ошибки имени receipt field (`post_state_match` вместо фактического `matches_expected_post`). Исправлено только чтение schema в новом test oracle; expected exists/size/hash и требование true match не ослаблены. Прежний red run сохранён отдельно. Итоговые pilot/focused/full используют один source hash нового модуля. Во всех product test runs isolation violations=0. Итоговые процессы pilot/focused/full exit=0 при успешных counts; intentional quality probes ниже учитываются отдельно.

Full non-PASS: `test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed` → SKIP; symlink creation is not permitted here

Фактический FULL collection сверён с исходным AST inventory: **749 старых selectors сохранены + 3 новых = 752**, дубликатов/пропущенных selectors нет. Это supplement накопленной regression, не её замена. Основная матрица содержит 26 адресных test selectors, проверенных механически; AMENDMENT дополняет её PR12 mapping. Oracle expected values не импортируются из production readers: SHA/size/exists вычисляются stdlib по известным fixture bytes и raw files. Возвращённый бизнес-статус дополнительно проверяется, но сам не доказывает safety.

**Граница source evidence при завершении.** FOCUSED и FULL записали одинаковые source manifests; все включённые прежние исходники совпадают с исходной protected manifest, новый pilot имеет SHA-256 `b4c9a86ca340699b12224d30b03f9d1305b53b3d3d04d842188016ecaac1978b`. При итоговой сверке обнаружены внешние изменения `test_web_alarm_projection_concurrency.py`, `test_web_alarm_reliability_wa017.py`, `.github/workflows/web-alarm-tests.yml`. Их mtime — 11:48:43 UTC, после записи FULL results (11:37:38 UTC). Это согласуется с внешней синхронизацией, но автор и Git revision не устанавливались. Файлы не менялись и не откатывались этой задачей. Baseline/tested/current hashes сохранены в `versions.json`. Production, runner, прочие прежние тесты и общие документы на этой сверке неизменны. Зелёный FULL относится к сохранённому tested manifest, **не объявляется FULL verification текущего изменившегося checkout**. Дополнительный полный прогон не запускался; актуальную ветку независимо проверяет координатор. Три новых теста и их production dependencies не изменились.

P1: ровно один ENOSPC fault hit внутри target apply после durable STARTED; существующий target и snapshot hashes сохранены; `.tmp` orphan отсутствует; raw record остаётся STARTED без receipt; fresh-process replay не вызывает apply повторно. P2: child exit=91 достигнут только после DONE, пустой файл реально существует; replay возвращает прежний receipt; новый DELETE удаляет его, последующий старый CREATE replay оставляет отсутствие; всего два apply entry. P3: два процесса одновременно достигли apply barrier с raw STARTED/no receipt и неизменёнными PRE; после release оба own-workspace effects точны, raw task/workspace identity и historical receipts различены; fresh replay не добавляет apply или MUTATION_EXECUTED events. Unicode/spaces filename и seeded binary payload, BOM/CRLF/NUL/0xFF проходят без нормализации. Это core API data-path coverage, не полный HTTP malformed-input corpus.

`apply_enter` — счётчик попыток входа в physical apply, не утверждение, что fsync/rename успешно совершили запись. Отдельные raw byte-state observations доказывают фактический target outcome. Fresh process exit/reopen не доказывает power-loss durability или надёжность реального заполненного диска; ENOSPC injected и помечен.

### Quality counterexamples и чувствительность

| Проверка отдельного TEMP harness | Наблюдение | Архитектурное следствие |
| --- | --- | --- |
| Empty TestCase | 0 tests, successful=true, exit=0 | Обязательны nonzero expected collection и exact selectors; один зелёный exit не доказательство |
| Два failing subtests одного parent | tests_run=1, failures=2, passed=-1, exit=1 | Это defect счётчиков evidence, не production. Нужны отдельные counts tests/cases/failing assertions; отрицательный PASS недопустим |
| Пойманный synthetic guard audit event | 1 PASS, successful=true, isolation violations=1, exit=1 | CLI fail-closed корректен; JSON successful сам по себе недостаточен. Реальная shell-команда не выполнялась: использован только `sys.audit` event |
| Из P1 удалена fault activation | Внутренний test ожидаемо FAIL, внешний sensitivity check PASS | Устранён очевидный always-green сценарий: обычный successful write не принимается за проверенный отказ |
| В P3 подменены left input bytes, reference model сохранена | Внутренний test ожидаемо FAIL, внешний sensitivity check PASS | Raw oracle замечает несоответствие модели реальному эффекту |
| Шесть standalone oracle/parser controls | Неверные exists/size/hash/match flag, duplicate JSON key и NaN отвергнуты: 6/6 | Не proof против всех плохих oracles, но реальная bounded negative validation |

Quality sensitivity suite: 2 PASS, 0 FAIL/ERROR/SKIP. Intentional TwoSubtestFailures red и synthetic guard violation сохранены; их нельзя смешивать с product regression failures/guard violations. Текущий runner/CI **не исправлялись**. Pilot использует штатную unittest классификацию: неожиданный child exit, проверенный assertion, может отражаться как FAIL; более подробная provenance-классификация ERROR/harness/runtime предлагается в consumer envelope, а не объявляется уже внедрённой.

### Команды и evidence locators

Из корня checkout, с новым output directory в system TEMP на каждый attempt:

~~~powershell
# В этой локальной среде используется .\.venv\Scripts\python.exe -B
python -B wa4a_acceptance.py --task ASTRA-WEB02-TEST-ARCH-001 --output "$env:TEMP\astra-pilot" test_web_alarm_new_invariants
python -B wa4a_acceptance.py --task ASTRA-WEB02-TEST-ARCH-001 --output "$env:TEMP\astra-focused" test_web_alarm_new_invariants test_web_alarm_lost_response test_web_alarm_mutation_executor test_web_alarm_payload_store test_web_alarm_target_claims_concurrency test_web_alarm_workspace_registry
python -B wa4a_acceptance.py --task ASTRA-WEB02-TEST-ARCH-001 --output "$env:TEMP\astra-full" all
# Одиночный case: заменить module selector на полный test ID из coverage.json
~~~

Фактические outputs: `C:/Users/REX/AppData/Local/Temp/astra-testarch-r68ccd_4/{pilot-1,pilot-2,focused,full}`. Quality cases выполнялись командой `python -B <TEMP>/quality_cases.py Empty <TEMP>/quality-Empty`, аналогично TwoSubtestFailures, CaughtGuardViolation, Sensitivity. Точный небольшой source сохранён как `reports/ASTRA-WEB02-TEST-ARCH-001/quality_cases.py`, байты и hash совпадают с выполненным TEMP script. Для повторения из корня checkout: `python -B reports/ASTRA-WEB02-TEST-ARCH-001/quality_cases.py Sensitivity <fresh-system-TEMP>/quality-Sensitivity`; заменить selector для остальных probes. Они запускаются отдельно и не входят в product FULL; intentional red/guard evidence не следует выдавать за product failure. Raw logs и массовые fixtures остаются в TEMP и могут быть удалены системой. Запуск synthetic audit probe не выполняет реальную shell-команду.

В report folder сохранены `checks.json` (все attempts, ошибки, skips, команды, runtime, intentional probes), `pilot-evidence.json` (final 3 test facts и sensitivity traces), `coverage.json` (весь actual FULL selector set и mappings), `versions.json` (protected/tested/current hashes, внешние изменения, rotation), `pr12-handoff.md` (дословный AMENDMENT), `quality_cases.py` (воспроизводимые meta probes). Сырые массовые stdout/fixtures не копировались в репозиторий. Расхождения final source bytes с focused/full manifest явно перечислены выше; новые файлы не публиковались через Git. При подготовке evidence исправлена одна SyntaxError в TEMP closeout script; затем его проверка правильно остановилась на source drift. Эти ошибки упаковки не скрыты, не относятся к product suite и не потребовали изменения production/tests/CI.

## RISKS / OPEN QUESTIONS

- F1–F3 и revision PR №12 получены от пользователя и разобраны в AMENDMENT. Remote revision/CI independently UNVERIFIED; F1 post-move recovery, F2 terminal safety/fail-closed и исходная причина F3 остаются открыты. Локальный зелёный concurrency test их не закрывает. Два старых test modules и workflow внешне изменились после сохранённого FULL; перед интеграцией координатор сверяет tree, hashes и selectors. Remote conflict absence и актуальный FULL PASS не заявлены.
- Предложенный common envelope/validator, bounded DSL, mutation-testing campaign, stress scheduler и reducer ещё не реализованы. Пилот — небольшой работающий пример, не замена независимого review.
- Основная локальная платформа Windows/Python 3.12; новые 3 cases не требуют symlink privileges и не имеют платформенных SKIP. GitHub Actions и Linux запуск здесь NOT RUN. Нет новых live disconnect/production mutation/power-loss proofs; изоляция trusted-test audit не равна OS sandbox.
- Current guard разрешает весь system TEMP, current runner не исключает zero collection и не даёт корректных subtest PASS counts. У него after-run source hashes; до/после сравнение в этой задаче выполнено внешним closeout script. Нельзя обобщать такой источник на arbitrary mutable CI checkout без source sealing. Выявленные ограничения требуют отдельного разрешённого инфраструктурного исправления.
- Новый module/core helpers входят в существующий hash glob. Любое дальнейшее вынесение support code, external fixtures или profiles требует явного включения в source manifest и пересмотра expected collection; иначе повторится provenance gap.

## DOC IMPACT / полный handoff

DOC IMPACT: YES (proposal, matrix, pilot evidence и task result); CURRENT STATE IMPACT: YES только для testing capability; PRODUCTION ARCHITECTURE IMPACT: NO; TEST ARCHITECTURE: PROPOSAL + 3-test PILOT; CONTEXT LIBRARY IMPACT: NO; REGISTRY/ROUTING IMPACT: YES через координатора; NEW NORMATIVE DOCUMENT: NO сейчас. Canonical owners: профиль 23, план 24, журнал 25, общие 000/05/06/34 — ChatGPT. Общая карта 01 не требует смены runtime contracts; 08/22 меняются лишь после принятого CI/test workflow change.

SHARED DOC DELTA / DOC CLOSEOUT INCOMPLETE: после независимого review координатор фиксирует testing pilot и его пределы, держит PR №12 findings открытыми до отдельной проверки, решает необходимость test-infrastructure TASK для collection/counts/evidence validator. Не присваивать Web Alarm/WA4-R новый общий DONE/VERIFIED, не включать WARN/GATEWAY REQUIRED/STRICT, не распространять Web Alarm правила на Ultra. Эта задача не изменяла общие документы, старые отчёты, existing tests, runner и workflow; внешние изменения сохранены. Пользовательская постановка и предыдущие персональные блоки сохраняются без потерь при ротации.

**NEXT SAFE ACTION:** независимый аудит ChatGPT архитектуры/novelty/oracles и полного source/evidence, сверка с Draft PR №12, затем запуск этого же module в Windows GitHub Actions уполномоченным координатором. Решение об интеграции и дальнейших стадиях — отдельно. Самостоятельных commit/push/merge, дальнейших задач и стресс-прогонов нет.

