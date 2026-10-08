# Baseline — CLAUDE-WA-011 / RC-6 Repair #4

- HEAD: `ce5e1799ab4a08157c779680711bebaf29d686dd` (commit 163, GitHub main)
- Дата: 2026-10-08
- `git status --short` на старте (чужие изменения, не мои):

```text
 M .obsidian/workspace.json
 M "\320\224\320\276\320\272\321\203\320\274\320\265\320\275\321\202\320\260\321\206\320\270\321\217/000_\320\227\320\260\320\264\320\260\321\207\320\270 Claude.md"
```

Карточка изменена пользователем (постановка Repair #4 в БЛОКЕ 1); `.obsidian/*` — не мой, не трогаю.

| Файл | SHA-256 |
| --- | --- |
| `web_alarm/__init__.py` | `590a09b8f2d521a9755cb96b48e3e8f17fe07d2d5aa09974c4927d92f1c11b60` |
| `web_alarm/__main__.py` | `3d2438ae92f4746e9ffaa1f837b1fe803f6281091d1f31f8c95643716f257d9a` |
| `web_alarm/cli.py` | `bd7301444ccfe34dc3d0db8955759c823d651ea70ed5e16204b8222ced3ffa48` |
| `web_alarm/closeout.py` | `44e712582c28a9348c26dadaa4127b4c66db76a769535039bd0a1345dc08d3b7` |
| `web_alarm/context_pack.py` | `cbc374c8ae64d13a4e47b6ef51c334c69774a5365872bbd0464440fa95000ce2` |
| `web_alarm/event_checkpoint_store.py` | `1d3c9b0eef082c1aebffefd2675c936a068f031e3b7077abbbbe5c2b326ca319` |
| `web_alarm/file_state.py` | `041f188b39b472ef4b9a517df0faea0088b282301a1b734382b33593adb28ea1` |
| `web_alarm/manifest_store.py` | `c182b7d7a08b2162dbc00e0b2e029bd114651e608fabd959642669ce77dd67a3` |
| `web_alarm/microtask_gate.py` | `f5c435ef8d7be3b0ed42b26bdd1f7f517ddea8dd3881f8660d2f1d275732d0cd` |
| `web_alarm/models.py` | `bd5313dcb09f4bad27ef6e5f400bb4b717def00d703ce59e0060e44bd47d80cf` |
| `web_alarm/operation_contract.py` | `fc779d6b9aadd8fcd2761adf16aa1f69898f346a6aa10f13d4312499e9f7189d` |
| `web_alarm/operation_store.py` | `df861bb51c86b012f096fc312f4829fde5e52f06410bc2fefab531b43f5ebef0` |
| `web_alarm/payload_store.py` | `d3a7f2b2bd4224ba38b82bccaf44ca62f95021dc5bb38a7e818cef85772306f1` |
| `web_alarm/projection.py` | `24f8f0c0c03524bd6635ec072460ae165b0cca8d0258c2f48c0d494b1ad83199` |
| `web_alarm/reconciliation.py` | `ea038e3dff0f6511a7a4732871d6ce25d229d3fa5af5276812de6ba15f78c407` |
| `web_alarm/reconciliation_decision.py` | `6b1a0cecdd2233c305c02e714c18e35ee8cd03e95b41eea607ab055ac68ea3bb` |
| `web_alarm/reconciliation_service.py` | `7ccf2592f01b66723d9766e9dbac410edace77e19997ec21cd0141ae489222a0` |
| `web_alarm/recovery_coordinator.py` | `00261414273939f70dadbcdc61f28277ccb7e444e8dd62ce6f8d5ad7afde4145` |
| `web_alarm/recovery_report_builder.py` | `6612f5eaf5b0df955b6a836750ded80a2deaf44f7757ae255807c635c8f69592` |
| `web_alarm/recovery_report_service.py` | `a151956672a3e2392a8afd6b78f1dc04b9f46966b84cdf9122b9afeef0db0920` |
| `web_alarm/recovery_report_store.py` | `9bd9fd82490bbe3fb48fe4dd529d585059dfb36cf5a80442ca0eb9b2f2681583` |
| `web_alarm/remote_entry.py` | `b3cdb106045098d4e774bef10562d6f348a3990336d028b5ca150026ba4bcae0` |
| `web_alarm/resolution_store.py` | `10cb472db7888ec169eb5165fa53dfb874f5a22446f05c651fd51003c1878641` |
| `web_alarm/resolver_service.py` | `8176d4637468ac32e932dc16550cbd3d55339d770397807e2a6abc636fd45ee0` |
| `web_alarm/rollback_service.py` | `c44461effc1e98d6510f2ca3228ed568263ffcf348c564deac711140fbd9a872` |
| `web_alarm/rollback_store.py` | `103dbbcc01fadf7ecc5975cd450f14e93aa891d37354d6e4e89e8030cddb9a72` |
| `web_alarm/server.py` | `983246df33a4caec8d086cf02f3bb4e13155282ba4c1bcab081fb723849fc6ba` |
| `web_alarm/state_machine.py` | `82efa8bb3e9c1d63f69e535700877862dfb19bb827d9000264f4daf6949bf6c3` |
| `web_alarm/storage_policy.py` | `1ffc7d61177ca8a4c62335243b153863fd696d8cf20ca5fe7aa0086a29192c76` |
| `web_alarm/store_lock.py` | `6ae82859cb51f89dfcaa2f09ab560cf816236615ed7ad24c8cb89abde72ba4c7` |
| `web_alarm/target_claim_service.py` | `1d1558305a621247dc25f3390f2097171d261374b67429d519a75e06bc20dfe1` |
| `web_alarm/target_claim_store.py` | `d069fc00ebfa246f18af4afcd9244f935fae281edd73f4f03149d9742d6db185` |
| `web_alarm/target_identity.py` | `7aedd43e7595456f6a3b9fbafe6ccd54e6bc8c1ccce027982a95fb980d9b9e71` |
| `web_alarm/task_store.py` | `3e05c9a6b384ec541c66ab19ee6027c2e2600fb6f50c9811dd31bd742331effb` |
| `web_alarm/transport_event_store.py` | `107a8e89cff2ffaae2a6eb899d0028e1c2a46788e12edfc3de5b9448a3b020cf` |
| `web_alarm/ui.py` | `86e4d042651bb4a9a5b02b270e5966ebedcf4f5c8f0fe91137dddc0aadbbdbd5` |
| `web_alarm/workspace_registry.py` | `f9c1eb7aee27f6197e7930863f87da213d2e4658f061dac324e2900e548ec556` |
| `test_web_alarm_cli.py` | `da16d5b886309d369c8607ab85ec7aab2c3a3bcfd89212429a941b431eeeca59` |
| `test_web_alarm_context_pack.py` | `0775e6d15091e42f46b32a1349725fd90041aedb38a46e743199029e45766d52` |
| `test_web_alarm_event_checkpoint_store.py` | `de26ecc5698d8e90d7b7a00cc4675d281df01ce39093d7af9db1910e1675cb1c` |
| `test_web_alarm_manifest_store.py` | `d35fb7538581e681a08022138fcbf3da407d759f5104c935a3a6e89b0c50009b` |
| `test_web_alarm_models.py` | `da0b930d37f8b2fcf39bc89e2458d8eeaede163f154f2906eac27551a3964ac1` |
| `test_web_alarm_operation_contract.py` | `dbf6bbc58a6e0d5cfabcaaedd747fd6b095056ae7f77d4edf6c7f532bd552bbf` |
| `test_web_alarm_operation_store.py` | `ea79a121d3e460679db5d0cc77f9e80564657a37f7370cb728adf16373a405ba` |
| `test_web_alarm_operation_store_concurrency.py` | `bab96f7d52a1f60085936c93c1cba7887a1b20dda05d8e92e6e8ba3e949a303b` |
| `test_web_alarm_payload_store.py` | `9b232329cbe3fdf8b84091780967834537f447bc17c690b15a829a09f0303a0a` |
| `test_web_alarm_projection.py` | `9b4fb279f5b2a262ddb63d2c65ae719a410a74e51cf102ff5c134143e26b54e7` |
| `test_web_alarm_projection_concurrency.py` | `26a81b6bb033f3e106600a09b0ac04ee19c8703550948dc54731a1b5229ffb96` |
| `test_web_alarm_reconciliation.py` | `074b467b1b925aec12e12fe6e14dfa0f1223e48cf7f12675ae67034aa7e96605` |
| `test_web_alarm_reconciliation_decision.py` | `4dd20a9a5bb58586dab2e6b47de09281ae62efdb37e50a5397032d4a89043b91` |
| `test_web_alarm_reconciliation_integration.py` | `ced03d05078b77ebcbbd6f4b526806ee4a8e753bfcd40030df02ff7d6be8d334` |
| `test_web_alarm_recovery_coordinator.py` | `c7408223f4ae462600a9c6384b6cc327068b1f8e54e5061b049c9c74770e8d7a` |
| `test_web_alarm_recovery_coordinator_adversarial.py` | `0c6ff6cffefbbe4f7e5fe557b3a8f6bf1fd7e9ea47d09632b9aa95e8e55856ba` |
| `test_web_alarm_recovery_coordinator_concurrency.py` | `9ed892335426f5813d960d522429a917616e8b1a9591d3d5110e0c2cd180658b` |
| `test_web_alarm_recovery_coordinator_repair1.py` | `90be1c61284e78f199131d333368a645820cf5f5a392df8a7a49ded7d5057493` |
| `test_web_alarm_recovery_coordinator_repair2.py` | `42be3c91ee5f9af7e97a86bc7653c01f1963390bba78fe7597a5fa7c27c51c66` |
| `test_web_alarm_recovery_coordinator_repair3.py` | `bf316497034a0f28f211ad27e25e079dc2bf3f3dd575a72aeff08c7e2d983811` |
| `test_web_alarm_recovery_report_acceptance.py` | `14d562590eb844b4f02d77546dc49cf9a35d9c8c7588061c370d058ae7a54ac5` |
| `test_web_alarm_recovery_report_builder.py` | `35a0b5cc3ddc32f8ac0bc28d42d7ba15d9adb552a1d3b6102b0fd937556de73b` |
| `test_web_alarm_recovery_report_integration.py` | `a1189a9b2a17cffb21cf3dc1bed617851188793277c1939628254218d656e840` |
| `test_web_alarm_recovery_report_store.py` | `9e0ae8ec8b6506df921fbacaac56fe359f7edd8d9bd436aab022d7ba0ec195e4` |
| `test_web_alarm_recovery_scenarios.py` | `f9a6ab823f1bf908a58581f49d73d66a5a8a50d205ebccf8a20fb57ec9bb1093` |
| `test_web_alarm_remote_entry.py` | `e8b956d296588672f9a893aff0e7cb5e9fa0a0ae918d09f52720b8ab430a4be0` |
| `test_web_alarm_resolver.py` | `0b9cd46389b397ff97d2a3d3686d1887baee920459e3d969769ebac6a7b06bbc` |
| `test_web_alarm_resolver_concurrency.py` | `2b51c468df66c0a9441040814c1f59b9e17e3b73f4b3b1a00a13e07e9dac8d96` |
| `test_web_alarm_restart_recovery.py` | `11807f4a50ec11d22f37d68105d73380fc2a2f3151915a6136554056c1ce9a3c` |
| `test_web_alarm_rollback.py` | `7646162b57ec828151b9e2a04b100ab5560a7d2ec90b8ea13c910f052287b76a` |
| `test_web_alarm_rollback_concurrency.py` | `101aaa45019b3b4111357a4eab24f171ee5e557abb4d8769ed084202ca332a62` |
| `test_web_alarm_server.py` | `7aa4fd2a77daacb50e990355d82a1046c338fd3a90df4b179cd26c144d89ea3f` |
| `test_web_alarm_state_machine.py` | `483e913b6e3ae4b8059511987e0cd09f64d4a1e494e2bd939740e900fa592bfb` |
| `test_web_alarm_state_machine_cas.py` | `7a2ce35e5342667d490c3494666fbec0b43af4d883f815f23a472f6d092e1dff` |
| `test_web_alarm_target_claims.py` | `a6fd3b43880f26a22ee2dbbfb2d076a9e8385c6a8ed006c1d27540537e844616` |
| `test_web_alarm_target_claims_concurrency.py` | `48443dc39e85f27c77d92ce8ff39cbea5f1f62fa1403034cb64da57fb3052484` |
| `test_web_alarm_target_identity.py` | `f7ad1b7977454412ca2f2fed2736bf7d34edfd66161baa88dad992d4c1ab163c` |
| `test_web_alarm_task_store.py` | `df3dd3bfbfa9d97329a8d5b4af915b3a994fde7dd4c8918219f08582098eae3b` |
| `test_web_alarm_transport_authority.py` | `3b5218ee6f623f3b9c889032c38f324d2671f7c0f0fcfc638f2ef9c6abd95c53` |
| `test_web_alarm_transport_event_store.py` | `d6654c2c110a10904e8ed21060ab29c1d65808a7bae7fd4d2d4aa7febbb21849` |
| `test_web_alarm_transport_ingestion.py` | `765fa85afb8846855e3de15bbe1fbd4a1b3d24aec62778ad5f70810635cf07eb` |
| `test_web_alarm_transport_recovery.py` | `de660a794815e9d58b0648ab84ecc4e90e398134d9e83d79a71793be078f20b1` |
| `test_web_alarm_ui.py` | `fcfa67c3e352422a15197423fcae3a4598625b66d6d14b2e4c6af066420cc1b7` |
| `test_web_alarm_workspace_registry.py` | `16ac6c5b053cd8123b26004cda26dd080140d0332acea15ac5ecb760521984ed` |
| `Документация/000_Задачи Claude.md` | `fabbb4d2bc5ab49d9dc5c5c67cfd030a1279e5bc464b03e3a5ddae0dbd8dc9b2` |
