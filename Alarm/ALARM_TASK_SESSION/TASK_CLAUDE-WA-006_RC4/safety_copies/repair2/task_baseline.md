# CLAUDE-WA-006 / RC-4 — baseline safety copies

HEAD: `072fcdc5837d0de90a9bcebad50b9dea59cc7bbd` (commit 151; RC-3 DONE / VERIFIED на 149, docs closeout 150–151). Код `web_alarm/` и тесты перед стартом совпадают с HEAD; dirty tree — только `.obsidian/workspace.json` (Obsidian) и `000_Задачи Claude.md` (БЛОК 1 RC-4).

Копии побайтно идентичны оригиналам и HEAD; authority = SHA-256 по физическим байтам + размер. Удалить после независимой проверки RC-4.

| Файл | Копия | Размер | SHA-256 |
| --- | --- | --- | --- |
| `web_alarm/manifest_store.py` | `safety_copies/web_alarm_manifest_store.py` | 22975 | `e1632012e86aac8bee51fcb97939cde4a72efa16dc2516dc408288df58c95dc0` |
| `web_alarm/target_claim_store.py` | `safety_copies/web_alarm_target_claim_store.py` | 9870 | `7e5aaba8829f2c69a5e1e6d788726712196f1b8b5996b97b30f96e1793157edd` |
| `web_alarm/target_claim_service.py` | `safety_copies/web_alarm_target_claim_service.py` | 27686 | `797251f014f0760e85f8084fcd82b36db2422b463c4e0f91a3d797a2bd8ad0e0` |
| `web_alarm/recovery_report_store.py` | `safety_copies/web_alarm_recovery_report_store.py` | 14430 | `e8d940f0e8001746b8ec8d52cc1fdbd3ec0ed0bba5bcb81e2a64819f98bfdbf4` |
| `web_alarm/recovery_report_builder.py` | `safety_copies/web_alarm_recovery_report_builder.py` | 10224 | `5009ba11af05890fda3b6b6be9ea00d73f5150ecfb465a8bc6558c6e3b18665c` |
| `web_alarm/recovery_report_service.py` | `safety_copies/web_alarm_recovery_report_service.py` | 5383 | `7c109e55cf799f2bdc4aa2f89e5c6d6f5dad8d41938244bdfe8230c6f6027385` |
| `web_alarm/server.py` | `safety_copies/web_alarm_server.py` | 44370 | `cffa02f7194daa46e8448a5235afcc351cda64e69181b66c9242bd66bf06f6bc` |
| `web_alarm/__init__.py` | `safety_copies/web_alarm___init__.py` | 3917 | `2985536589e899ca5855a5c9d442e35bd3dcba65dc4126273a69ec45c056e0f3` |

## Independent Review Repair — baseline

HEAD: `42ce55083d0dcf0eb700c6eec0fa2ce463a3e6cd` (commit 152). Копии сняты перед repair; побайтно совпадают с HEAD.

| Файл | Копия | Размер | SHA-256 |
| --- | --- | --- | --- |
| `web_alarm/rollback_service.py` | `safety_copies/repair/web_alarm_rollback_service.py` | 42758 | `1e9db0055d5c5f689b924a1b4f935720732560da443dad9b8e2f531d8e173e04` |
| `web_alarm/rollback_store.py` | `safety_copies/repair/web_alarm_rollback_store.py` | 13760 | `c82dd31978ae5952ee65ccaa5a789da5da55d60e67ceeef84fc8ab6403506c6c` |
| `test_web_alarm_rollback.py` | `safety_copies/repair/test_web_alarm_rollback.py` | 29252 | `87433f08a7fd52b50aa03f3bf11f33bec6ce52f67259b17225c2d76d1e77d0b2` |
