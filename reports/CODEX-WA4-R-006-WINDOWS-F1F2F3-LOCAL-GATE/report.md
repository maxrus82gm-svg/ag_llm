# CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE

**RESULT READY / AWAITING INDEPENDENT VERIFICATION. LOCAL ONLY / NOT SYNCED.**

Codex 007 → ChatGPT / WEB_08. Дата: 2026-10-15, Asia/Yekaterinburg. ARCH CLASS: Web Alarm Workspace / WA4-R Reliability / Windows Local Gate. PRIMARY PROFILE: 23; TEST PROFILE: 36.2.

## 1. Итог

Финальный локальный Windows gate: **802 выполненных теста — 801 PASS / 0 FAIL / 0 ERROR / 1 SKIP**, isolation 0. Все **103 адресных теста внутри полного набора — PASS**, включая 11 новых; это subset одного full-release, а не отдельный завершённый focused run. Дополнительно **12 outer PASS** quality controls с 12 intentional inner FAIL и **2 bounded PASS / 8 внутренних раундов** F2/F3. Ни DONE/VERIFIED, ни общая STRICT acceptance не присвоены.

Обнаружены и исправлены **три связанные причины**, которые прежние focused проверки не выявляли: несвязанная record identity; неполный delimiter событий; создание lock path до валидации TASK ID. Первоначальные шесть FAIL, один ERROR нового test helper и отдельный invalid-lock FAIL сохранены. Это новые локальные результаты R-006, не перенос старых PASS.

## 2. Источник, маршрут и среда

Supplied baseline координатора: `main@df3250140c987876771fe2f899f80acaf38fd920`. Git/GitHub не использовались; совпадение local folder с GitHub HEAD не утверждается. До работы семь final R-004 file-byte pins совпали с локальными файлами. После ремонта изменились три runtime-модуля и добавлен один общий test module. Полный source map финального запуска содержит **102 файла** и сверяется с текущими bytes через `verify_package.py --source-check`.

Маршрут `08 → 000 → 34 → 18 → 01 → 23/24/25 → 36/36.1/36.2` проверен адресно. Неизменные нормативы/профили сверены по SHA с уже прочитанными R-005 источниками; актуальные изменения 08/34 о будущей Web Alarm Ultra прочитаны как planning, не implementation GO. Применены DOC-GIT/PARALLEL/TASK-BLOCK1/ENGINEERING-ROLES и TEST-COLLAB/ENG/AREA/EVID/SCOPE; общий контур read-only.

Среда: **Windows-10-10.0.19045-SP0**, существующая `.venv`, **Python 3.12.10**, `PYTHONUTF8=1`, `-X utf8 -B`. Обработка артефактов также использовала Python 3.13.8; она не выдаётся за runtime execution. Fixture/output — отдельные disposable TEMP, guard существующего `wa4a_acceptance.py`: запрет Git metadata, внешних сокетов, native/shell execution и записи вне TEMP; controlled Python children и loopback test HTTP разрешены. Никакого live storage.

| Изменённый/новый общий файл | Final file-byte SHA-256 |
|---|---|
| `web_alarm/task_store.py` | `fe446753140106da5ad424ce412f919676935f884bdafe0f771ac91790ab43ac` |
| `web_alarm/event_checkpoint_store.py` | `7d094e81b5a40dbced420af9a51c04b6e5b7b4eb4050d96bca0ba01495274aad` |
| `web_alarm/operation_store.py` | `bb7eaf40dd2280fcd5a38d33fe85d2d97ff19733740719d15fa02cf4e6854360` |
| `test_web_alarm_wa4r006_local_gate.py` | `cfea279508859b4337e55d3377e7631bfe33b6b1138e1c7c94cd7521382ad8bd` |

Полные before/after raw и LF-normalized pins — [versions.json](versions.json), компактный нормализованный diff — [source-changes.diff](source-changes.diff). Старый diagnostic module, MutationExecutor, CloseoutService и общий runner не редактировались.

## 3. Подтверждённые findings и причины

### R006-F01 — foreign identity принимается за принадлежащую TASK/стадии

TaskStore конструировал TaskRecord/TaskPlanRecord/MicrotaskRecord из валидного JSON, но не сравнивал их identity с directory/request. RAW TASK equality проверяет текст, а не принадлежность metadata. До исправления зафиксированы: gated COMPLETED с foreign TASK ID; COMPLETED с foreign plan parent; **реальный EXECUTED/POST** при чужом parent TASK в microtask; с чужим microtask ID — REFUSED позже boundary, но уже после сохранения INTENT. Root-cause confidence **HIGH**: контролируемые RED и восстановление старых loaders в RAM воспроизводят нарушения.

Исправление: проверка task_id в TASK/plan readers и task_id + microtask_id в stage reader **до возврата record**, следовательно до использования metadata для admission/closeout. Ошибка typed TaskStoreError; новых authority/lifecycle правил нет. Прямой completion защищён от чужого TASK ID; он остаётся **ungated storage primitive**, не заменяет публичный CloseoutService и не обязан выполнять его plan/operation eligibility.

### R006-F02 — complete JSON без newline склеивается со следующим event

`read_events().splitlines()` принимал последний JSON object без delimiter. Старый append сразу дописывал следующий JSON, создавая физически невалидную JSONL строку. При verified operation gated closeout возвращал COMPLETED и `event_recorded=true`, хотя его append повреждал history. Сохранены original/fault/post hex. Confidence **HIGH**: оба read/append controls возвращают исходный RED независимо.

Исправление: nonempty event history должна заканчиваться LF. Reader отказывает при отсутствии delimiter и оборачивает invalid UTF-8 в доменную ошибку; appender проверяет последний byte через binary `a+b` и **не пишет** при незавершённой строке. Полный LF event остаётся прежнего формата. Никаких автоматических newline repair, усечения истории или повторных mutation. Empty log и CRLF-terminated records остаются допустимы. В ACTIVE state нечитаемая operation history блокирует closeout/replay.

### R006-F03 — TASK ID валидируется после создания lock-файла

`OperationStore._serialized` строил lock path до первой record-level проверки. `CloseoutService.complete("../outside")` в isolated TEMP создал `locks/outside.lock`, затем отказал на внутренней валидации. Это доказанная path-boundary ошибка, не реальная запись в чужой проект. Confidence **HIGH**: отдельный initial FAIL и RAM mutant старого lock method.

Исправление: `_safe_component` вызывается до создания lock; `.`/`..` также отвергаются в component validators OperationStore/TaskStore. Никакой новой блокировки или смены порядка locks; корректные ID проходят прежний путь.

## 4. F1/F2/F3 и дополнительные доказательства

| Область | Доказанный локальный scope |
|---|---|
| F1 | Все четыре native/admission-order сценария R-004 выполнены на новых runtime pins. PRE/intermediate/terminal, operation/receipt/checkpoint/snapshot/claims, точный events prefix, fresh readers и single fixture apply сохранены. Native WinError **5** наблюдён; 32 отдельно не воспроизводился. |
| F2 | Lookup phantom duplicate/genuine duplicate и bounded recheck, direct-close serialization, STARTED/APPLY/DONE, stale CAS/canonical ownership, preflight refusal, known receipt replay и no-second-effect проходят full gate. Дополнительный bounded direct-close race: четыре раунда. |
| F3 | WA-017 crash race + marked post-move crash/fresh recovery + writer-first rejection выполнены. Bounded WA-017: ещё четыре раунда. Исторический handle owner по-прежнему неизвестен. |

Дополнительные ключевые RAW:

- Повторный реальный status-write refusal в **другом recovery worker**, затем successful fresh completion: [R035](records/R035.json). Обе ошибки имеют native marker, PID/exit 2, WinError 5; обе pending state побайтно/структурно одинаковы. Receipt/checkpoint/snapshot/claims неизменны, prefix сохранён, один completion event.
- Принудительно убитый worker на **durable STARTED / before_apply**: [R037](records/R037.json). Сохранены PID, ненулевой exit, пустой stdout, точная trace; PRE target и STARTED без receipt. Fresh lock probes проходят, fresh replay требует reconciliation, late mutation REFUSED. `apply_enter` здесь **не означает effect**: apply_exit/DONE отсутствуют, физические bytes остались PRE.
- Исключение после durable DONE до ответа: [R033](records/R033.json). Actual parent apply=1, raw DONE/receipt/POST; fresh child возвращает тот же receipt REPLAYED без нового apply. Parent PID в source не записан: **NOT PRESENT IN SOURCE**; child PID записан.
- Truncated operation JSON: [R041](records/R041.json). Closeout/replay отказывают, target/history bytes не меняются; ручной ремонт storage не имитируется автоматическим retry.
- Неверные TASK/plan/stage identities и invalid lock IDs — новые individual records в индексе ниже, с initial RED и final PASS.

При corruption injection некоторые cleanup callbacks восстанавливают **только synthetic faulty record** для штатного чтения/удаления fixture. Поэтому первичный oracle — именованные `*_fault_*`, `*_PRE`, `*_terminal` **до cleanup**, с оригинальными hex и byte hashes; финальный helper `terminal` после cleanup не подменяет фактическое повреждённое состояние. В частности initial foreign TASK case сохранил фактический completed/foreign record до восстановления исходного metadata.

Исторический original F3 остаётся сохранённым FAIL: [R-005 E043](../CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE/records/historical-red/E043.jsonl), source archive SHA `020d2770b48f90e0d24df071b10c2ad5fe5caa2972d8d3070445ac875963e120`, coordinator-supplied CI SHA `37123b176097c15c8d21e0040bdf7d7f3e8072a3`. Pre-move WinError 5 / active PLANNED не превращён в post-move/crash или historical VERIFIED. Original F1 artifact и F2 80-round ZIP отсутствуют в предоставленных источниках.

## 5. Прогоны, collection и quality

Exact argv/environment/output — [commands.json](commands.json); по каждому run сохранены original results, source map, stdout/stderr и isolation. Counts ниже — **PASS / FAIL / ERROR / SKIP**, без сложения повторов в число уникальных тестов.

| Attempt | Выполнено | P / F / E / S | Exit | Isolation | Секунды |
|---|---:|---|---:|---:|---:|
| `baseline-focused` | 92 | 92 / 0 / 0 / 0 | 0 | 0 | 149.824 |
| `adversarial-before` | 10 | 3 / 6 / 1 / 0 | 1 | 0 | 16.545 |
| `adversarial-after` | 10 | 10 / 0 / 0 / 0 | 0 | 0 | 17.413 |
| `lock-identity-before` | 1 | 0 / 1 / 0 / 0 | 1 | 0 | 0.046 |
| `quality` | 11 | 11 / 0 / 0 / 0 | 0 | 0 | 19.275 |
| `quality-final` | 12 | 12 / 0 / 0 / 0 | 0 | 0 | 20.497 |
| `full-release` | 802 | 801 / 0 / 0 / 1 | 0 | 0 | 791.165 |
| `bounded-release` | 2 | 2 / 0 / 0 / 0 | 0 | 0 | 10.046 |

`adversarial-before` ERROR — дефект нового helper: внешний kill законно оставляет пустой stdout, который общий `finish()` пытался разобрать как JSON. Исправлен только новый тест: killed worker reap + raw stdout/stderr/exit/trace без выдуманного ответа. Исходный ERROR и первая test version сохранены.

`quality-final`: шесть новых + шесть существующих R-004 controls; каждый outer PASS требует **1 inner test / 1 FAIL / 0 ERROR / 0 SKIP** с actual traceback/raw facts. Mutants меняют только RAM процесса/дочернего controlled helper, не production files. Для foreign-micro loader control тот же production API исполняется в parent, чтобы унаследовать RAM mutant; это явно записано в facts. Intentional inner RED не считается product FAIL.

**Незавершённые попытки не засчитаны:** `full-final` контролируемо остановлен после доказательства третьего дефекта, до окончательного gate; `focused-final` не имеет results/exit marker, процесс и session отсутствовали, attribution UNKNOWN. Partial logs сохранены. Final 103 PASS — именно subset завершённого full-release. Collection **802 unique IDs** адресно сравнена со всеми 802 фактически выполненными IDs, source maps совпали.

Единственный SKIP: `test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed` — `symlink creation is not permitted here`. Новые 11 методов и native F1 tests не пропущены.

## 6. R-005 transport / newline проверка

Оригинальный sealed validator `--sources --self-check` прошёл без изменения старого пакета. Подтверждены ровно семь CRLF metadata/report файлов из 56 manifest-listed files. В LF simulation исходный strict validator **правильно отказал** (`Package file mismatch: checks.json`); [validate_r005_transport.py](validate_r005_transport.py) восстановил оригинальные bytes в TEMP только по **trusted SHA-256 + original size**, затем прежний validator подтвердил 43 RAW records/ZIP origins и manifest.

Trusted R-005 seal: `f594e6c315b638fcb61ce35f683cc07c3a8f04316be196a1d86821aabf0b6e64`. Содержательная byte mutation и попытка normalize binary отвергнуты; исходники/ZIP/pins не переписаны. [transport-check.json](transport-check.json) разделяет actual local bytes и simulated LF, R-005 export controls и два transport controls. Это переносимое адресное решение, **не universal normalization или новая общая CI-система**; доверенный manifest anchor verifier обязан получить независимо.

## 7. MANUAL ENGINEERING REVIEW

1. Перечитаны TaskStore loaders/completion/_task_path, OperationStore `_serialized/begin/_load_path/_validate_history/_transition_locked`, CloseoutService complete, executor preflight/drive/boundary/release, EventCheckpointStore read/append, claims CAS/mutation_boundary, связанные state-machine/manifest/resolver/rollback lock callers. Порядок **operations → TASK mutation → canonical target** сохранён; новые identity checks не захватывают lock. EventStore не добавляет operations lock и не создаёт non-reentrant inversion.
2. Разобраны оба порядка admission/closeout, genuine move gap, kill после STARTED до apply, ошибка после DONE до event/reply, повторный status recovery отказ, known receipt delivery. Read-before-lock RAW mechanism остаётся закрыт existing R-003 boundaries; никто не выполняет blind apply после unknown fate.
3. Directory move остаётся commit point. `MOVED_STATUS_PENDING` закрывает mutation по location; fresh completion завершает metadata. Оно не даёт новой physical authority. Исторически допустимый `event_recorded=false` после уже committed completion не переименован в гарантированно полную history. Новая torn-history проверка блокирует active closeout, а не меняет статус-only recovery contract.
4. Independent oracle использует actual bytes/hex, identity/directory/request, receipt/hash, exact event prefix и reached trace, а не тот же production projection как expected. [raw-review.json](raw-review.json) дополнительно проверяет сохранённые native phases/WinError/PID, killed-worker effects, post-DONE replay и quality accounting: **10 PASS проверок данных**, без повторного runtime execution.
5. Новые readers намеренно отказывают на старых foreign/mismatched records; автоматическая миграция/rename/rebinding не выполнена. Append не чинит torn history; последующий explicit recovery/data repair требует отдельного решения. Valid records/empty log/нормальные append и весь existing regression сохранены.
6. Considered risks: corrupt JSON/UTF-8/history, stale CAS и Workspace binding, lost reply, claim ownership после OS process death, handle release, genuinely missing receipt, cleanup после kill. Нормальные workers reaped в fixture; forced child kill сопровождается fresh OS-lock proof. Первые прерванные родительские прогоны могут оставить свои synthetic TEMP directories; чужие/старые TEMP не чистились, полная глобальная cleanup не заявляется.

## 8. Остаточные границы

Это **bounded local Windows evidence**, не формальная linearizability proof и не independent ChatGPT acceptance. Не сертифицированы power loss/reboot/real disk exhaustion, внешние не соблюдающие advisory locks writers/антивирус, все Windows sharing codes/файловые системы и symlink case с недоступной привилегией. Event tail check не превращает публичный appender в транзакционный multiwriter journal; существующая serialization контрактных writers сохраняется. Payload/receipt не доказывает текущие bytes вне измеренного snapshot.

Historical handle owner и исходные missing archives не восстановлены поздним PASS. Независимый CI на новой опубликованной runtime revision **NOT RUN**. Рекомендован clean Windows run на exact новых pins/commit либо другой независимый execution, выбранный WEB_08; это отдельное решение, не новый rollout GO. WARN/GATEWAY REQUIRED/STRICT, UI, Ultra/Voice, shared runner/CI и live Workspace не менялись.

Read-only `ProjectionService.build` по-прежнему не берёт TASK locks и может получить cached-path/snapshot I/O error во время move. Existing diagnostic выполнялся и проверяет сохранность raw data/checkpoint и свежий повторный view; ожидаемый read-only error не выдан за устранённый дефект. Этот gate защищает рассмотренные admission/mutation/recovery boundaries, а не гарантирует отсутствие всех read races или всех способов внешней подмены storage.

## 9. Пакет, сохранность и SHARED DOC DELTA

[raw-index.jsonl](raw-index.jsonl) → **45 прямых текстовых RAW records**. [provenance.json](provenance.json) содержит original ZIP/member sizes/SHA, JSON pointer/selector и historical locator. Новый `evidence.zip` содержит только результаты/логи/источники **R-006**, без копирования старых ZIP; digest каждого member закреплён. [verify_package.py](verify_package.py) проверяет RAW ↔ original ZIP equality, counters/CRC, source pins и manifest, плюс TEMP corruption control.

[scope-check.json](scope-check.json) и [rotation.json](rotation.json) фиксируют итоговую неизменность старых evidence/документов и lossless safe rotation. [manifest.json](manifest.json) перечисляет **все файлы публикации**, source bytes/hashes; сам manifest исключён из собственного hash. Publication до подтверждения пользователя — LOCAL ONLY. Полный TEMP output сохраняется: `C:\Users\REX\AppData\Local\Temp\codex-wa4r006-lwgw7sov`.

**SHARED DOC DELTA для WEB_08:** `23` — record identity и fail-closed event framing после independent PASS; `36.2` — 11 новых regression selectors, шесть новых negative controls, symlink limitation и Windows evidence; `25/05/06/34/общий 000` — factual R-006/раздельные решения F1/F2/F3 и NEXT только по независимому verdict. `24/01` — статус/краткое mechanism impact при необходимости; `18/36/36.1` — NO CHANGE contract, предложен адресный transport adapter, а не новая общая норма. Shared документы агентом не редактировались.

NEXT: пользователь публикует manifest-listed пакет и scoped code/tests; WEB_08 независимо сверяет source/RAW/quality/риски и принимает решения. Полная постановка сохранена в БЛОКЕ 2, factual result — в БЛОКЕ 3; прежняя история byte-exact сохранена, БЛОК 1 переведён в ожидание. Следующие TASK/rollout не запускать.

## 10. Адресный RAW индекс

В каждой записи `raw` — неизменённый parsed original test record; `origin` связывает exact attempt/member/pointer/selector/canonical hash. Byte SHA/size текста — в индексе/manifest, отдельно от original member bytes.

| RAW | Attempt | Original outcome | Selector suffix |
|---|---|---|---|
| [R001](records/R001.json) | `adversarial-before` | FAIL | `test_foreign_microtask_parent_refuses_before_intent_and_apply` |
| [R002](records/R002.json) | `adversarial-before` | ERROR | `test_killed_started_worker_releases_locks_without_blind_repeat` |
| [R003](records/R003.json) | `adversarial-before` | FAIL | `test_microtask_record_id_mismatch_refuses_before_intent_and_apply` |
| [R004](records/R004.json) | `adversarial-before` | FAIL | `test_plan_identity_mismatch_blocks_gated_completion` |
| [R005](records/R005.json) | `adversarial-before` | FAIL | `test_task_identity_mismatch_blocks_gated_and_direct_completion` |
| [R006](records/R006.json) | `adversarial-before` | FAIL | `test_unterminated_event_read_and_append_fail_without_modifying_prefix` |
| [R007](records/R007.json) | `adversarial-before` | FAIL | `test_unterminated_events_block_closeout_and_known_receipt_replay` |
| [R008](records/R008.json) | `lock-identity-before` | FAIL | `test_invalid_identity_does_not_create_outside_operations_lock` |
| [R009](records/R009.json) | `quality-final` | PASS | `test_old_event_appender_splices_json_records` |
| [R010](records/R010.json) | `quality-final` | PASS | `test_old_event_reader_accepts_missing_delimiter` |
| [R011](records/R011.json) | `quality-final` | PASS | `test_old_microtask_loader_exposes_foreign_parent_apply` |
| [R012](records/R012.json) | `quality-final` | PASS | `test_old_plan_loader_exposes_foreign_plan_completion` |
| [R013](records/R013.json) | `quality-final` | PASS | `test_old_public_lock_creates_before_validating_identity` |
| [R014](records/R014.json) | `quality-final` | PASS | `test_old_task_loader_exposes_false_completed` |
| [R015](records/R015.json) | `quality-final` | PASS | `test_counterfeit_persisted_receipt_is_detected` |
| [R016](records/R016.json) | `quality-final` | PASS | `test_false_success_after_native_status_failure_is_detected` |
| [R017](records/R017.json) | `quality-final` | PASS | `test_lost_checkpoint_identity_is_detected` |
| [R018](records/R018.json) | `quality-final` | PASS | `test_missing_closeout_operations_lock_is_detected` |
| [R019](records/R019.json) | `quality-final` | PASS | `test_missing_native_pre_move_trigger_is_detected` |
| [R020](records/R020.json) | `quality-final` | PASS | `test_semantically_equal_rewritten_event_prefix_is_detected` |
| [R021](records/R021.json) | `full-release` | PASS | `test_writers_racing_a_dying_completion_never_land_in_the_closed_task` |
| [R022](records/R022.json) | `full-release` | PASS | `test_F1_admission_first_rejects_closeout_without_touching_existing_evidence` |
| [R023](records/R023.json) | `full-release` | PASS | `test_F1_completion_first_serializes_RAW_admission_plan_and_new_mutation` |
| [R024](records/R024.json) | `full-release` | PASS | `test_F1_native_post_move_status_failure_and_fresh_recovery` |
| [R025](records/R025.json) | `full-release` | PASS | `test_F1_native_pre_move_refusal_preserves_nonempty_evidence_and_fresh_retry` |
| [R026](records/R026.json) | `full-release` | PASS | `test_F2_directory_probes_do_not_invent_duplicate_during_real_move` |
| [R027](records/R027.json) | `full-release` | PASS | `test_F2_move_between_destination_and_source_probe_is_resolved` |
| [R028](records/R028.json) | `full-release` | PASS | `test_F2_move_cannot_interleave_START_APPLY_DONE_boundary` |
| [R029](records/R029.json) | `full-release` | PASS | `test_F2_preflight_lock_failure_refuses_without_apply_and_replay_is_safe` |
| [R030](records/R030.json) | `full-release` | PASS | `test_F2_release_event_error_after_DONE_is_replayed_without_second_apply` |
| [R031](records/R031.json) | `full-release` | PASS | `test_F3_marked_post_move_crash_late_writers_and_fresh_completion` |
| [R032](records/R032.json) | `full-release` | PASS | `test_F3_writer_first_refusal_does_not_claim_crash_phase` |
| [R033](records/R033.json) | `full-release` | PASS | `test_exception_after_durable_done_replays_without_second_apply` |
| [R034](records/R034.json) | `full-release` | PASS | `test_foreign_microtask_parent_refuses_before_intent_and_apply` |
| [R035](records/R035.json) | `full-release` | PASS | `test_fresh_recovery_can_fail_again_without_success_or_second_apply` |
| [R036](records/R036.json) | `full-release` | PASS | `test_invalid_closeout_and_public_lock_identity_create_no_lock_files` |
| [R037](records/R037.json) | `full-release` | PASS | `test_killed_started_worker_releases_locks_without_blind_repeat` |
| [R038](records/R038.json) | `full-release` | PASS | `test_microtask_record_id_mismatch_refuses_before_intent_and_apply` |
| [R039](records/R039.json) | `full-release` | PASS | `test_plan_identity_mismatch_blocks_gated_completion` |
| [R040](records/R040.json) | `full-release` | PASS | `test_task_identity_mismatch_blocks_gated_and_direct_completion` |
| [R041](records/R041.json) | `full-release` | PASS | `test_truncated_operation_json_refuses_closeout_and_replay_without_writes` |
| [R042](records/R042.json) | `full-release` | PASS | `test_unterminated_event_read_and_append_fail_without_modifying_prefix` |
| [R043](records/R043.json) | `full-release` | PASS | `test_unterminated_events_block_closeout_and_known_receipt_replay` |
| [R044](records/R044.json) | `bounded-release` | PASS | `test_execution_racing_the_task_closure_never_writes_into_a_closed_task` |
| [R045](records/R045.json) | `bounded-release` | PASS | `test_writers_racing_a_dying_completion_never_land_in_the_closed_task` |
