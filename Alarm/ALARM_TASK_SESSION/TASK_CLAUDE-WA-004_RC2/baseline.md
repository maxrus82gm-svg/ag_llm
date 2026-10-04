# CLAUDE-WA-004 / RC-2 — baseline safety copies

HEAD: `9596187451fbe6fff3b2494c79613bea18ea434d`; рабочее дерево `web_alarm/` и `test_web_alarm_*.py` перед началом чистое (0 изменений).

Копии побайтно идентичны оригиналам; authority = SHA-256 по физическим байтам + размер. Удалить после независимой проверки RC-2.

| Файл | Копия | Размер | SHA-256 |
| --- | --- | --- | --- |
| `web_alarm/recovery_report_service.py` | `safety_copies/web_alarm_recovery_report_service.py` | 3992 | `fa9187768be2e7df2bd861049e31ca60b5b66dceacb51919baf5086b6eb14af2` |
| `web_alarm/recovery_report_store.py` | `safety_copies/web_alarm_recovery_report_store.py` | 14066 | `2a4414283b6b3b12452b6a9dd5695b93b0b9605932d6190c4547b4b1173645f8` |
| `web_alarm/server.py` | `safety_copies/web_alarm_server.py` | 38406 | `66b033e044e2be1b16465ff606db18a4b33ddd3140e7bb36e45d8e0542e53607` |
| `web_alarm/__init__.py` | `safety_copies/web_alarm___init__.py` | 3138 | `1479233a57d442868c5fdf504939ba47168f9ae77ddc0b8829891dbc9e130661` |
| `test_web_alarm_recovery_report_acceptance.py` | `safety_copies/test_web_alarm_recovery_report_acceptance.py` | 16298 | `72d5109aed2300086019a0611810d864e7d70bebbd747589b703dde977cac5b9` |
| `test_web_alarm_recovery_report_integration.py` | `safety_copies/test_web_alarm_recovery_report_integration.py` | 7887 | `1932f963c121d0797c752652efde17cdc47097b7a6e92f62bf0158b28658bc48` |

**Дополнено после начала правки:** копии двух файлов ниже взяты из `HEAD` (`git cat-file`), а не с диска. Перед правкой рабочее дерево было чистым, а оба файла в рабочем дереве — LF (`i/lf w/lf`), поэтому байты HEAD совпадают с исходными байтами на диске.

| Файл | Копия | Размер | SHA-256 |
| --- | --- | --- | --- |
| `web_alarm/recovery_report_builder.py` | `safety_copies/web_alarm_recovery_report_builder.py` | 9273 | `e429d0e0b5d82f68e8232db3a8edc6e281354ee71232437c1bce500f7ffb8eef` |
| `web_alarm/operation_store.py` | `safety_copies/web_alarm_operation_store.py` | 26475 | `81b2287e90a21866bf1212590adb6fcbe8f6d95c2f4b8181e523ad05f3e5a3ce` |

## Independent Review Repair — baseline

HEAD: `fe55c99db2c2493f99db807a95ba6bd8a668b4fe` (commit 147). Копии сняты с диска перед repair-правкой; побайтно совпадают с HEAD.

| Файл | Копия | Размер | SHA-256 |
| --- | --- | --- | --- |
| `web_alarm/resolver_service.py` | `safety_copies/repair/web_alarm_resolver_service.py` | 17829 | `b4f1a966f27b849e975d2b3e4586d09881f61685d6eab5be062617c7ffd369d8` |
| `web_alarm/recovery_report_builder.py` | `safety_copies/repair/web_alarm_recovery_report_builder.py` | 9471 | `f8b2d66ca92af20393cede94b6c04e8d504d2788074a2ae08ed3a9c08c07394c` |
| `web_alarm/recovery_report_service.py` | `safety_copies/repair/web_alarm_recovery_report_service.py` | 5318 | `2ab93002421f8781e3cba287def03203c55092d8e52fa04047e1c0cef1eddb2f` |
| `test_web_alarm_resolver.py` | `safety_copies/repair/test_web_alarm_resolver.py` | 21517 | `7d5b4dd70721ee6efa0d82ecb882e8690d6d830010ca525a4b1245af70c33f61` |
