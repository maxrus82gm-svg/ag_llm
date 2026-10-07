# Baseline — CLAUDE-WA-009 / RC-6 REPAIR #2

Дата: 2026-10-06. Исполнитель: Claude Opus 5.5.

## Git

- local HEAD: `e551b919628bb0e1232d631f8d2637d9f6fa895c` (commit 161)
- GitHub main: `e551b919628bb0e1232d631f8d2637d9f6fa895c	refs/heads/main`
- runtime baseline: commit 160 `07c4667dd131b34d970e78488a68c2107913de85`;
  `git diff --quiet 07c4667 e551b91 -- web_alarm test_web_alarm_*.py` -> 0 (commit 161 = только документация verifier);
  `git diff --quiet HEAD -- web_alarm test_web_alarm_*.py` -> 0 (дрейфа рабочего дерева нет).
- dirty tree на старте:
```text
M "Документация/000_Задачи Claude.md"
?? "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/000_Задачи Claude.md.before"
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/test_web_alarm_recovery_coordinator.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/test_web_alarm_recovery_coordinator_adversarial.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/test_web_alarm_recovery_coordinator_concurrency.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/test_web_alarm_recovery_coordinator_repair1.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/web_alarm__projection.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/web_alarm__recovery_coordinator.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/web_alarm__rollback_service.py
?? Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-009_RC6_REPAIR2/safety_copies/web_alarm__target_claim_store.py
```
  (только моя карточка: пользователь вписал постановку в БЛОК 1)

## Safety copies (`safety_copies/`)

- `web_alarm/recovery_coordinator.py` — `3f8b7f681b8a3bc940f239208e45068c717d047ee9bea22006aeac83e716b9ca`
- `web_alarm/projection.py` — `3dcde1e13760e16ec0dc9833d9275a0f338af09e97460ea0be2c4dd918540703`
- `web_alarm/rollback_service.py` — `391768949878ddb8cc7a574c78718fc58149661af6613a70970d7dbbfc20da2e`
- `web_alarm/target_claim_store.py` — `d0394a081ddc0314a36e88d2041fea5acfb408bca922a2325359b94c184c4245`
- `test_web_alarm_recovery_coordinator.py` — `c7408223f4ae462600a9c6384b6cc327068b1f8e54e5061b049c9c74770e8d7a`
- `test_web_alarm_recovery_coordinator_adversarial.py` — `0c6ff6cffefbbe4f7e5fe557b3a8f6bf1fd7e9ea47d09632b9aa95e8e55856ba`
- `test_web_alarm_recovery_coordinator_concurrency.py` — `9ed892335426f5813d960d522429a917616e8b1a9591d3d5110e0c2cd180658b`
- `test_web_alarm_recovery_coordinator_repair1.py` — `95bd38dfb44967a5ff4611a4eba02fa76241e93e35eae15fcc3341dc94d8a6b1`
- `Документация/000_Задачи Claude.md` — `56363b0af35a206770cf65b44773d615bcea85c49d31232bbb77091a7ad19dcb`

## SHA-256 всех runtime-модулей `web_alarm/` на старте

| файл | sha256 |
| --- | --- |
| `__init__.py` | `590a09b8f2d521a9755cb96b48e3e8f17fe07d2d5aa09974c4927d92f1c11b60` |
| `__main__.py` | `3d2438ae92f4746e9ffaa1f837b1fe803f6281091d1f31f8c95643716f257d9a` |
| `cli.py` | `bd7301444ccfe34dc3d0db8955759c823d651ea70ed5e16204b8222ced3ffa48` |
| `closeout.py` | `44e712582c28a9348c26dadaa4127b4c66db76a769535039bd0a1345dc08d3b7` |
| `context_pack.py` | `cbc374c8ae64d13a4e47b6ef51c334c69774a5365872bbd0464440fa95000ce2` |
| `event_checkpoint_store.py` | `1d3c9b0eef082c1aebffefd2675c936a068f031e3b7077abbbbe5c2b326ca319` |
| `file_state.py` | `041f188b39b472ef4b9a517df0faea0088b282301a1b734382b33593adb28ea1` |
| `manifest_store.py` | `4df1392caf1a2f6e38a496b88d212a73a888fa31995de1a0eb9e75095652cd67` |
| `models.py` | `bd5313dcb09f4bad27ef6e5f400bb4b717def00d703ce59e0060e44bd47d80cf` |
| `operation_contract.py` | `fc779d6b9aadd8fcd2761adf16aa1f69898f346a6aa10f13d4312499e9f7189d` |
| `operation_store.py` | `9272eb3a1b36d7ad9b24d3a0047d6a3b9ce83ec748e101314258b50999f3b76d` |
| `payload_store.py` | `d3a7f2b2bd4224ba38b82bccaf44ca62f95021dc5bb38a7e818cef85772306f1` |
| `projection.py` | `3dcde1e13760e16ec0dc9833d9275a0f338af09e97460ea0be2c4dd918540703` |
| `reconciliation.py` | `ea038e3dff0f6511a7a4732871d6ce25d229d3fa5af5276812de6ba15f78c407` |
| `reconciliation_decision.py` | `6b1a0cecdd2233c305c02e714c18e35ee8cd03e95b41eea607ab055ac68ea3bb` |
| `reconciliation_service.py` | `7ccf2592f01b66723d9766e9dbac410edace77e19997ec21cd0141ae489222a0` |
| `recovery_coordinator.py` | `3f8b7f681b8a3bc940f239208e45068c717d047ee9bea22006aeac83e716b9ca` |
| `recovery_report_builder.py` | `6612f5eaf5b0df955b6a836750ded80a2deaf44f7757ae255807c635c8f69592` |
| `recovery_report_service.py` | `a151956672a3e2392a8afd6b78f1dc04b9f46966b84cdf9122b9afeef0db0920` |
| `recovery_report_store.py` | `9bd9fd82490bbe3fb48fe4dd529d585059dfb36cf5a80442ca0eb9b2f2681583` |
| `remote_entry.py` | `b3cdb106045098d4e774bef10562d6f348a3990336d028b5ca150026ba4bcae0` |
| `resolution_store.py` | `10cb472db7888ec169eb5165fa53dfb874f5a22446f05c651fd51003c1878641` |
| `resolver_service.py` | `8176d4637468ac32e932dc16550cbd3d55339d770397807e2a6abc636fd45ee0` |
| `rollback_service.py` | `391768949878ddb8cc7a574c78718fc58149661af6613a70970d7dbbfc20da2e` |
| `rollback_store.py` | `103dbbcc01fadf7ecc5975cd450f14e93aa891d37354d6e4e89e8030cddb9a72` |
| `server.py` | `6e4267ed14f83cba2310cc6f118dca01b9d4cb2cf278a3964fa726e7a824f6f4` |
| `state_machine.py` | `3c8190daed3779206b93394f8716bcfaf7fe824749306798f6e71606dbf0b5c5` |
| `storage_policy.py` | `1ffc7d61177ca8a4c62335243b153863fd696d8cf20ca5fe7aa0086a29192c76` |
| `store_lock.py` | `6ae82859cb51f89dfcaa2f09ab560cf816236615ed7ad24c8cb89abde72ba4c7` |
| `target_claim_service.py` | `16a121db43ac92f7e5f6609878674f95dd4d3491c64667435f754c40a01ca0b7` |
| `target_claim_store.py` | `d0394a081ddc0314a36e88d2041fea5acfb408bca922a2325359b94c184c4245` |
| `target_identity.py` | `7aedd43e7595456f6a3b9fbafe6ccd54e6bc8c1ccce027982a95fb980d9b9e71` |
| `task_store.py` | `c17a42d66ec43392c97adfb4aaa15b10fbbaed4c06a48ed13093ee117c62b208` |
| `transport_event_store.py` | `107a8e89cff2ffaae2a6eb899d0028e1c2a46788e12edfc3de5b9448a3b020cf` |
| `ui.py` | `86e4d042651bb4a9a5b02b270e5966ebedcf4f5c8f0fe91137dddc0aadbbdbd5` |
| `workspace_registry.py` | `f9c1eb7aee27f6197e7930863f87da213d2e4658f061dac324e2900e548ec556` |

## Исходные evidence

- независимая повторная проверка: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-REVERIFY/rc6_reverification.md`;
- probe: `TASK_CLAUDE-RC6-REVERIFY/probes/reverify_probes.py` (n01b, n13, n13b, n15, n18, n19), исходные `TASK_CLAUDE-RC6-VERIFY/probes/`.

