# Baseline — CLAUDE-RC6-REVERIFY

Дата: 2026-10-06. Роль: независимый verifier (REVIEW ONLY).

## Git

- local HEAD: `07c4667dd131b34d970e78488a68c2107913de85`
- GitHub main (ls-remote): `07c4667dd131b34d970e78488a68c2107913de85	refs/heads/main`
- Repair baseline: commit 159 `26111c9e39f8b9de90f1b91b6a75b74bd0412e6d`
- dirty tree на старте:
```text
M "Документация/000_Задачи Claude.md"
?? "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-REVERIFY/safety_copies/000_Задачи Claude.md.before"
```
  (единственное изменение — моя карточка: пользователь вписал постановку в БЛОК 1)
- runtime/tests drift vs HEAD: НЕТ

## SHA-256 runtime (web_alarm/)

| файл | sha256 |
| --- | --- |
| `web_alarm/projection.py` | `3dcde1e13760e16ec0dc9833d9275a0f338af09e97460ea0be2c4dd918540703` |
| `web_alarm/recovery_coordinator.py` | `3f8b7f681b8a3bc940f239208e45068c717d047ee9bea22006aeac83e716b9ca` |
| `web_alarm/rollback_service.py` | `391768949878ddb8cc7a574c78718fc58149661af6613a70970d7dbbfc20da2e` |
| `web_alarm/operation_store.py` | `9272eb3a1b36d7ad9b24d3a0047d6a3b9ce83ec748e101314258b50999f3b76d` |
| `web_alarm/operation_contract.py` | `fc779d6b9aadd8fcd2761adf16aa1f69898f346a6aa10f13d4312499e9f7189d` |
| `web_alarm/models.py` | `bd5313dcb09f4bad27ef6e5f400bb4b717def00d703ce59e0060e44bd47d80cf` |
| `web_alarm/task_store.py` | `c17a42d66ec43392c97adfb4aaa15b10fbbaed4c06a48ed13093ee117c62b208` |
| `web_alarm/state_machine.py` | `3c8190daed3779206b93394f8716bcfaf7fe824749306798f6e71606dbf0b5c5` |
| `web_alarm/resolver_service.py` | `8176d4637468ac32e932dc16550cbd3d55339d770397807e2a6abc636fd45ee0` |
| `web_alarm/reconciliation_service.py` | `7ccf2592f01b66723d9766e9dbac410edace77e19997ec21cd0141ae489222a0` |
| `web_alarm/target_claim_service.py` | `16a121db43ac92f7e5f6609878674f95dd4d3491c64667435f754c40a01ca0b7` |
| `web_alarm/target_claim_store.py` | `d0394a081ddc0314a36e88d2041fea5acfb408bca922a2325359b94c184c4245` |
| `web_alarm/rollback_store.py` | `103dbbcc01fadf7ecc5975cd450f14e93aa891d37354d6e4e89e8030cddb9a72` |
| `web_alarm/manifest_store.py` | `4df1392caf1a2f6e38a496b88d212a73a888fa31995de1a0eb9e75095652cd67` |
| `web_alarm/closeout.py` | `44e712582c28a9348c26dadaa4127b4c66db76a769535039bd0a1345dc08d3b7` |
| `web_alarm/server.py` | `6e4267ed14f83cba2310cc6f118dca01b9d4cb2cf278a3964fa726e7a824f6f4` |
| `web_alarm/cli.py` | `bd7301444ccfe34dc3d0db8955759c823d651ea70ed5e16204b8222ced3ffa48` |

## SHA-256 tests

| файл | sha256 |
| --- | --- |
| `test_web_alarm_cli.py` | `da16d5b886309d369c8607ab85ec7aab2c3a3bcfd89212429a941b431eeeca59` |
| `test_web_alarm_context_pack.py` | `0775e6d15091e42f46b32a1349725fd90041aedb38a46e743199029e45766d52` |
| `test_web_alarm_event_checkpoint_store.py` | `de26ecc5698d8e90d7b7a00cc4675d281df01ce39093d7af9db1910e1675cb1c` |
| `test_web_alarm_manifest_store.py` | `d35fb7538581e681a08022138fcbf3da407d759f5104c935a3a6e89b0c50009b` |
| `test_web_alarm_models.py` | `da0b930d37f8b2fcf39bc89e2458d8eeaede163f154f2906eac27551a3964ac1` |
| `test_web_alarm_operation_contract.py` | `dbf6bbc58a6e0d5cfabcaaedd747fd6b095056ae7f77d4edf6c7f532bd552bbf` |
| `test_web_alarm_operation_store.py` | `ea79a121d3e460679db5d0cc77f9e80564657a37f7370cb728adf16373a405ba` |
| `test_web_alarm_operation_store_concurrency.py` | `bab96f7d52a1f60085936c93c1cba7887a1b20dda05d8e92e6e8ba3e949a303b` |
| `test_web_alarm_payload_store.py` | `9b232329cbe3fdf8b84091780967834537f447bc17c690b15a829a09f0303a0a` |
| `test_web_alarm_projection.py` | `510a9aa9ceb1e4e7c583244be82b28fb97e16b8aa78fba8046c63d958ca134d7` |
| `test_web_alarm_projection_concurrency.py` | `26a81b6bb033f3e106600a09b0ac04ee19c8703550948dc54731a1b5229ffb96` |
| `test_web_alarm_reconciliation.py` | `074b467b1b925aec12e12fe6e14dfa0f1223e48cf7f12675ae67034aa7e96605` |
| `test_web_alarm_reconciliation_decision.py` | `4dd20a9a5bb58586dab2e6b47de09281ae62efdb37e50a5397032d4a89043b91` |
| `test_web_alarm_reconciliation_integration.py` | `ced03d05078b77ebcbbd6f4b526806ee4a8e753bfcd40030df02ff7d6be8d334` |
| `test_web_alarm_recovery_coordinator.py` | `c7408223f4ae462600a9c6384b6cc327068b1f8e54e5061b049c9c74770e8d7a` |
| `test_web_alarm_recovery_coordinator_adversarial.py` | `0c6ff6cffefbbe4f7e5fe557b3a8f6bf1fd7e9ea47d09632b9aa95e8e55856ba` |
| `test_web_alarm_recovery_coordinator_concurrency.py` | `9ed892335426f5813d960d522429a917616e8b1a9591d3d5110e0c2cd180658b` |
| `test_web_alarm_recovery_coordinator_repair1.py` | `95bd38dfb44967a5ff4611a4eba02fa76241e93e35eae15fcc3341dc94d8a6b1` |
| `test_web_alarm_recovery_report_acceptance.py` | `14d562590eb844b4f02d77546dc49cf9a35d9c8c7588061c370d058ae7a54ac5` |
| `test_web_alarm_recovery_report_builder.py` | `35a0b5cc3ddc32f8ac0bc28d42d7ba15d9adb552a1d3b6102b0fd937556de73b` |
| `test_web_alarm_recovery_report_integration.py` | `a1189a9b2a17cffb21cf3dc1bed617851188793277c1939628254218d656e840` |
| `test_web_alarm_recovery_report_store.py` | `9e0ae8ec8b6506df921fbacaac56fe359f7edd8d9bd436aab022d7ba0ec195e4` |
| `test_web_alarm_recovery_scenarios.py` | `f9a6ab823f1bf908a58581f49d73d66a5a8a50d205ebccf8a20fb57ec9bb1093` |
| `test_web_alarm_remote_entry.py` | `e8b956d296588672f9a893aff0e7cb5e9fa0a0ae918d09f52720b8ab430a4be0` |
| `test_web_alarm_resolver.py` | `0b9cd46389b397ff97d2a3d3686d1887baee920459e3d969769ebac6a7b06bbc` |
| `test_web_alarm_resolver_concurrency.py` | `2b51c468df66c0a9441040814c1f59b9e17e3b73f4b3b1a00a13e07e9dac8d96` |
| `test_web_alarm_restart_recovery.py` | `11807f4a50ec11d22f37d68105d73380fc2a2f3151915a6136554056c1ce9a3c` |
| `test_web_alarm_rollback.py` | `23e3c3a7255bce7c528faacde8f696079c39c9d7bb7bff9b699558a066d1dd37` |
| `test_web_alarm_rollback_concurrency.py` | `7e064c9222cfd80138cbe637ceda204714eb8f522e2ecf4658bd43f3641f443b` |
| `test_web_alarm_server.py` | `7aa4fd2a77daacb50e990355d82a1046c338fd3a90df4b179cd26c144d89ea3f` |
| `test_web_alarm_state_machine.py` | `483e913b6e3ae4b8059511987e0cd09f64d4a1e494e2bd939740e900fa592bfb` |
| `test_web_alarm_target_claims.py` | `f4efa7b00c3620d960fe50600f9eb5e08f1e1cd3f8ec6aadd24b0645809cb13f` |
| `test_web_alarm_target_claims_concurrency.py` | `48443dc39e85f27c77d92ce8ff39cbea5f1f62fa1403034cb64da57fb3052484` |
| `test_web_alarm_target_identity.py` | `f7ad1b7977454412ca2f2fed2736bf7d34edfd66161baa88dad992d4c1ab163c` |
| `test_web_alarm_task_store.py` | `df3dd3bfbfa9d97329a8d5b4af915b3a994fde7dd4c8918219f08582098eae3b` |
| `test_web_alarm_transport_authority.py` | `3b5218ee6f623f3b9c889032c38f324d2671f7c0f0fcfc638f2ef9c6abd95c53` |
| `test_web_alarm_transport_event_store.py` | `d6654c2c110a10904e8ed21060ab29c1d65808a7bae7fd4d2d4aa7febbb21849` |
| `test_web_alarm_transport_ingestion.py` | `765fa85afb8846855e3de15bbe1fbd4a1b3d24aec62778ad5f70810635cf07eb` |
| `test_web_alarm_transport_recovery.py` | `de660a794815e9d58b0648ab84ecc4e90e398134d9e83d79a71793be078f20b1` |
| `test_web_alarm_ui.py` | `fcfa67c3e352422a15197423fcae3a4598625b66d6d14b2e4c6af066420cc1b7` |
| `test_web_alarm_workspace_registry.py` | `16ac6c5b053cd8123b26004cda26dd080140d0332acea15ac5ecb760521984ed` |

## Карточка

- `Документация/000_Задачи Claude.md` до правки статуса: `de52555bd640b4ae69118363d99413a77fb28475de9c9724042db2d3fbc042cc` (копия: `safety_copies/000_Задачи Claude.md.before`)


## Живое storage (только чтение) — ДО проверки

Путь из кода: `web_alarm/workspace_registry.py::default_storage_root()` → `%LOCALAPPDATA%\WebAlarmWorkspace`.

- files=136 dirs=41
- только файлы: `0729891947f506b0ab73f2edae027d9b20818c69015baf821617ea77d6c05920`
- с каталогами: `2269f667e9143772bb9172a401fc48ea7dfd9a71047511f7cfbce1b0595f3a61`
- совпадает с концом Web04 (тот же метод: sha256 по «относит. путь + sha256 файла»).
