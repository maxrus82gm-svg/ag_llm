# Source map и точные исходные SHA-256

Все номера ниже — baseline, проверенный против текущих байтов. SHA относятся к физическим bytes, без EOL-нормализации. Полный список 110 хешируемых файлов — source-snapshot.json; хеширование не означает полный ручной review каждого из 110 файлов.

| Source | Bytes | SHA-256 |
|---|---:|---|
| web_alarm/mutation_executor.py | 39988 | 7e34e77e5339f10cdfc48a2439d589ac4c652907613184f1b70cfc460bbcd854 |
| web_alarm/target_identity.py | 4834 | 7aedd43e7595456f6a3b9fbafe6ccd54e6bc8c1ccce027982a95fb980d9b9e71 |
| web_alarm/file_state.py | 5943 | 041f188b39b472ef4b9a517df0faea0088b282301a1b734382b33593adb28ea1 |
| web_alarm/target_claim_service.py | 30670 | 7649ff15ff8ca02c1872234c0bbfad758b8bf7dfe7be91bde5b46933b2c444ce |
| web_alarm/target_claim_store.py | 11265 | d069fc00ebfa246f18af4afcd9244f935fae281edd73f4f03149d9742d6db185 |
| web_alarm/operation_store.py | 44850 | a36468717b8def5ca024cdaff751168fc86adbb6aad58f9679dbde2f4a626d48 |
| web_alarm/rollback_service.py | 54374 | fc3da9b476ab17bad80eec257215061a8c9d3dfdb236bc6945dffea60f5cff69 |
| web_alarm/manifest_store.py | 36996 | 7e5a3b470e612b4a2be99a10ef2bd04fbec02177aac4b27450f085454db2fff3 |
| web_alarm/store_lock.py | 2537 | 6ae82859cb51f89dfcaa2f09ab560cf816236615ed7ad24c8cb89abde72ba4c7 |

## Адресные точки цепочки

- web_alarm/mutation_executor.py: execute@189–243, _execute@394–479, _mutate_locked@481–533, _apply@536–545, _execute_composite@569–653.
- web_alarm/target_identity.py: target_key@41–48, canonical_target@71–119.
- web_alarm/file_state.py: is_link_or_reparse_point@115–123, observe_path@126–149, same_authority@161–167.
- web_alarm/target_claim_service.py: _target@168–178, acquire@252–386, _cas@390–437, mutation_boundary@440–504.
- web_alarm/target_claim_store.py: physical_target_key@89–94, lock_path@264–265, write@278–295.
- web_alarm/operation_store.py: begin@527–723, _done_receipt@725–742, _transition_locked@755–866, read_payload@989–1000.
- web_alarm/rollback_service.py: _preserve@527–565, _session_basis@569–594, _acquire_all@629–679, apply@728–748, _apply_locked@760–864, _prove_current@866–915, _finalize@917–965.
- web_alarm/manifest_store.py: _atomic_write_bytes@80–94, _resolve_target@133–153, _prepare_locked@358–513, verify_restore_point@622–681, restore_plan@683–749, restore_microtask@751–831.
- web_alarm/store_lock.py: acquire@52–63, release@65–76.

## Связь с инвариантами и тестами

| Инвариант | Source anchors | Проверка |
|---|---|---|
| Path identity/Windows aliases | target_identity canonical_target; target_claim_store physical_target_key | existing target_identity, F01 junction schedules |
| Ownership/lifecycle/final CAS | target_claim_service acquire/_cas/mutation_boundary | existing claims/concurrency/state_machine_cas; P01 |
| STARTED-before-action / exact DONE / replay | mutation_executor _mutate_locked/_apply; operation_store _done_receipt/_transition_locked | existing mutation/crash_consistency; P02/P03/P06; F02 |
| Observation consistency | file_state observe_path | ObservationRepairOracles, F03 |
| Retained verified snapshot buffer | manifest_store restore_plan vs restore_microtask | RollbackResearch P08/P09; SnapshotRepairOracles F04 |
| Rollback claims/CAS/APPLYING/current proof | rollback_service _apply_locked/_prove_current/_finalize | existing rollback + rollback_concurrency; F02b |
| Lock scope / release on process death | store_lock InterProcessLock | existing multiprocess and crash suites; S03 remains static |

Дополнительные source references: cli.py snapshot restore dispatch (строка 211); operation_contract.py raw byte-state/fingerprint validation; rollback_store.py durable session/preserved storage; recovery_coordinator.py как вызываемый существующими crash/compatibility тестами recovery path. Связанные модули не объявляются прошедшими полный независимый аудит.

Candidate exact bytes/SHA — test-results/candidate-files.json; неприменённый diff — proposed-fix.patch. Доказательства совпадения навигации Claude — test-results/claude-validation.json.
