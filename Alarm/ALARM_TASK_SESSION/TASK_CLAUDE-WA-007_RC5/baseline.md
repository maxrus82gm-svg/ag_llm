# CLAUDE-WA-007 / RC-5 — baseline

HEAD: `c46bee7f60ff8354be956881d30de916d5264891` (commit 154 = принятый RC-4 baseline; HEAD новее 154 нет).
Runtime-код `web_alarm/` и `test_web_alarm_*.py` побайтно совпадают с HEAD (`git diff --quiet HEAD -- web_alarm test_web_alarm_*.py`).

Dirty tree до старта (чужие правки, не откатываются):

```text
M .obsidian/workspace.json
 M "Документация/000_Задачи Claude.md"
 M "Документация/000_Задачи для агента.md"
 M "Документация/001_История выполненных задач Claude.md"
 M "Документация/05_Реестр задач.md"
 M "Документация/06_Журнал выполнения и отчёты.md"
 M "Документация/23_Архитектура Web Alarm Workspace.md"
 M "Документация/24_План реализации Web Alarm Workspace.md"
 M "Документация/25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md"
```

Safety copies сняты до любой правки; побайтно равны оригиналам и HEAD (кроме карточки, которая отличается от HEAD правками пользователя/ChatGPT).

| Файл | Копия | Размер | SHA-256 |
| --- | --- | --- | --- |
| `web_alarm/__init__.py` | `safety_copies/web_alarm___init__.py` | 4225 | `330b365cefaa06803f80526592d3245da6a156c85f6cd5982807114166ad3be3` |
| `web_alarm/models.py` | `safety_copies/web_alarm_models.py` | 11427 | `65803e7de0b6a07b1edc7240c3dcd46f30fc522cc5a18925353310a0aebcc927` |
| `web_alarm/event_checkpoint_store.py` | `safety_copies/web_alarm_event_checkpoint_store.py` | 7395 | `1279a1ec0524846e7fc675fb36c67ac6b43b5968bdd187240f1d5d13506609da` |
| `web_alarm/context_pack.py` | `safety_copies/web_alarm_context_pack.py` | 8377 | `42b066d4883884274d19c584ece3c42b50619158c6c988ae5101af7174f32c93` |
| `web_alarm/state_machine.py` | `safety_copies/web_alarm_state_machine.py` | 16856 | `65e432b7b7423a79bfb0a58d512885de8d7aa6f4c20faf865d2ec0f6eb5cfa51` |
| `web_alarm/operation_store.py` | `safety_copies/web_alarm_operation_store.py` | 26761 | `57dbbfad1967095c1db1e7e2f298abc88ea1181928c4e9fb62737136ac962f11` |
| `web_alarm/server.py` | `safety_copies/web_alarm_server.py` | 47130 | `c2ba3d3c203bf40041fa97f3b66e2c9b607dbb66878fbd0aef84565b54e13484` |
| `web_alarm/cli.py` | `safety_copies/web_alarm_cli.py` | 9048 | `1af9eae4e7ae67adcfd7bbfd7fff90f53e879b847823af26610baca989f2e8be` |
| `web_alarm/remote_entry.py` | `safety_copies/web_alarm_remote_entry.py` | 3517 | `3b21c90dca39f71256019863ca95bed8531d7e68004fafb60a1eccd5b8f85c96` |
| `web_alarm/task_store.py` | `safety_copies/web_alarm_task_store.py` | 15062 | `49fa43ced6bbde44317f62fda224d1f628d10ff0746df81c3b551fa5efef4839` |
| `web_alarm/manifest_store.py` | `safety_copies/web_alarm_manifest_store.py` | 26229 | `4df1392caf1a2f6e38a496b88d212a73a888fa31995de1a0eb9e75095652cd67` |
| `web_alarm/rollback_service.py` | `safety_copies/web_alarm_rollback_service.py` | 50291 | `3df292b4e19258ff41f5038d9f8dc259e07e5152c6ced45bc0694f271fc2b622` |
| `test_web_alarm_context_pack.py` | `safety_copies/test_web_alarm_context_pack.py` | 6399 | `1d6168c96460c2c67de074f8911f87c7eeb7090c40f42a76be7c37933b4a98ff` |
| `test_web_alarm_state_machine.py` | `safety_copies/test_web_alarm_state_machine.py` | 7830 | `700af2f4e30d6e2f877b9b0e4849059797ef40c81a4c78cfde0fc58bda45dce2` |
| `test_web_alarm_cli.py` | `safety_copies/test_web_alarm_cli.py` | 6886 | `7c6c7a36283bd92af71dba8c1081de873e9b895383459587e3718d0579826993` |
| `test_web_alarm_server.py` | `safety_copies/test_web_alarm_server.py` | 12200 | `b1f3b5d77db6fb96bffe30fc87e09c06f80daf0a91bbfc9e5ab21564b621f2ce` |
| `test_web_alarm_ui.py` | `safety_copies/test_web_alarm_ui.py` | 5858 | `fcfa67c3e352422a15197423fcae3a4598625b66d6d14b2e4c6af066420cc1b7` |
| `test_web_alarm_remote_entry.py` | `safety_copies/test_web_alarm_remote_entry.py` | 4549 | `e8b956d296588672f9a893aff0e7cb5e9fa0a0ae918d09f52720b8ab430a4be0` |
| `test_web_alarm_reconciliation_integration.py` | `safety_copies/test_web_alarm_reconciliation_integration.py` | 8623 | `ced03d05078b77ebcbbd6f4b526806ee4a8e753bfcd40030df02ff7d6be8d334` |
| `test_web_alarm_event_checkpoint_store.py` | `safety_copies/test_web_alarm_event_checkpoint_store.py` | 5298 | `de26ecc5698d8e90d7b7a00cc4675d281df01ce39093d7af9db1910e1675cb1c` |
| `test_web_alarm_task_store.py` | `safety_copies/test_web_alarm_task_store.py` | 7200 | `df3dd3bfbfa9d97329a8d5b4af915b3a994fde7dd4c8918219f08582098eae3b` |
| `Документация/000_Задачи Claude.md` | `safety_copies/Документация_000_Задачи Claude.md` | 108603 | `3444631b39623e7d9a11053809ce522c3fcf6be623c9a73e9acca177c3d014b7` |
