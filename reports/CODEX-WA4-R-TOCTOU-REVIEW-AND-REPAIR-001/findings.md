# Матрица сценариев

Статус относится к указанному сценарию и границе доказательства. Финальный PASS harness не означает отсутствие известных рисков.

| ID | Сценарий / нарушаемый или сохраняемый инвариант | Статус | Evidence / итог |
|---|---|---|---|
| F01 | Junction меняет родителя после final CAS/identity, до write/create/delete; действие должно адресовать проверенный объект | CONFIRMED | MutationResearch.test_junction_swap_redirects_{write,create,delete}_before_post_proof: альтернативная цель изменена, original цела; POST_PROOF_FAILED, STARTED, receipt=null. Кандидат не исправляет |
| F02a | Внешний writer после CAS существующего WRITE/DELETE | CONFIRMED | test_existing_write_loses_uncooperative_update_after_cas / test_existing_delete_removes_uncooperative_update_after_cas: foreign bytes потеряны, DONE/EXACT_POST_STATE_PROVED |
| F02b | Внешний writer после rollback CAS | CONFIRMED | RollbackResearch.test_uncooperative_write_after_rollback_cas_is_lost: foreign bytes потеряны, VERIFIED/ROLLBACK_SUCCESS; replay writes=0 |
| F03a | Подмена обычного файла после lstat до open не замечена | CONFIRMED | ObservationRepairOracles.test_replacement_between_lstat_and_open_must_be_detected: baseline возвращает replacement digest; candidate отказывает. Самостоятельная атомарность CAS из этого не следует |
| F03b | In-place запись между двумя streaming reads | CONFIRMED | test_in_place_write_during_stream_must_not_return_mixed_digest: baseline mixed digest; candidate FileStateError. Ограниченный fix по видимой metadata |
| F04a | snapshot restore читает повреждённый buffer после verify; одинаковый/другой размер | CONFIRMED | SnapshotRepairOracles.test_consumed_snapshot_{must_be_revalidated_before_restore,size_drift_is_refused_before_restore}: baseline изменяет цель до ошибки; candidate no-write |
| F04b | Повторное low-level восстановление повреждённого снимка | CONFIRMED | test_repeated_corrupt_restore_performs_no_write: RED baseline write_count=1; candidate оба отказа, write_count=0 |
| P01 | Дрейф bytes перед final CAS | PROTECTED | test_drift_before_final_cas_is_refused: PRECONDITION_FAILED, apply=0 |
| P02 | Занятие отсутствующего CREATE-имени после CAS | PROTECTED | test_create_collision_after_cas_never_overwrites: чужие bytes сохранны, WRITE_OUTCOME_UNKNOWN/STARTED, replay FATE_UNKNOWN/apply=0; existing absent-WRITE test также PASS |
| P03 | Дрейф после действия, до receipt observation | PROTECTED | test_post_action_drift_has_no_done_receipt_or_blind_replay: POST_PROOF_FAILED, receipt=null, replay apply=0 |
| P04 | Два кооперативных автора / same operation deliveries | PROTECTED | existing mutation_executor concurrency, target_claims_concurrency, operation_store_concurrency: профиль PASS. Область — один общий storage/lock protocol |
| P05 | Completion/lifecycle гонка с mutation | PROTECTED | existing execution_racing_task_closure и state_machine_cas в core, PASS |
| P06 | Процесс погиб до STARTED / после STARTED / после action / после receipt | PROTECTED | 4 existing executor crash tests, плюс crash_consistency: разрешённый replay/RETRY/ADOPT без blind second apply, PASS |
| P07 | Rollback APPLYING/resume, drift after receipt и NOOP ownership | PROTECTED | existing rollback crash/current proof tests и rollback_concurrency, PASS |
| P08 | Порча snapshot сразу после tracked restore_plan | PROTECTED | test_snapshot_change_after_plan_is_blocked_by_freshness: BLOCKED/STALE_RESOLUTION, write=0; первоначальный ошибочный oracle исправлен |
| P09 | Порча snapshot после последнего tracked session basis | PROTECTED | test_snapshot_change_after_final_basis_uses_retained_verified_bytes: VERIFIED, записан удерживаемый проверенный buffer |
| P10 | Стабильное чтение существующего файла / absent | NOT REPRODUCED | test_stable_observation_and_absence_still_work PASS; existing operation_contract tests проверяют raw bytes/EOL |
| P11 | Статические Windows paths/ADS/device names, parent junction escape | PROTECTED | existing target_identity tests PASS, кроме отдельного leaf symlink SKIP |
| P12 | move/rename interrupted between steps | PROTECTED | existing mutation_executor tests: явный PARTIAL, последующее продолжение/replay отслеживается, две receipt; атомарность пары не обещана |
| S01 | Receipt observation → persistence при внешнем изменении | STATIC RISK | `_done_receipt` предшествует `_persist_record`; историческая receipt не является proof текущего состояния. Dynamic injection в это конкретное окно NOT RUN; не объявляется отдельный подтверждённый bypass |
| S02 | Hard-link alias / замена workspace root / shared storage aliases | STATIC RISK | physical_target_key использует path, inode/root handle в persistent authority нет; динамически NOT RUN, отсутствие inode само по себе не finding |
| S03 | Подмена lock-файла/private storage некооперативным процессом | STATIC RISK | InterProcessLock защищает открытый lock object; private store tampering вне проверенного cooperative протокола, динамически NOT RUN |
| S04 | Metadata rollback/ABA во время observation | STATIC RISK | candidate сравнивает dev/ino/mode/size/mtime/reparse bit; same metadata и следующее после проверки изменение не исключены |
| B01 | Leaf symlink replacement во время open | BLOCKED | Native создание symlink недоступно, existing test SKIP; junction-тесты не подменяют этот результат |
| N01 | Linux/POSIX/NFS/SMB/ReFS/другие версии Python | NOT RUN | Проверено только фактическое Windows окружение из environment.json |
| N02 | Power loss / disk/controller durability / kill OS | NOT RUN | Process death tests не являются power-loss proof |
| N03 | Live Workspace, prod recovery, STRICT, network/MCP/tunnel | NOT RUN | Запрещено scope; действий не было |

Для CONFIRMED подробно описаны CHECK → IDENTITY → LOCK/CLAIM → CAS → ACTION → POST-PROOF → PERSISTENCE → RECOVERY → FINAL STATE в report.md и repair-notes.md. Для baseline/candidate наблюдений см. test-results/*observations.jsonl.
