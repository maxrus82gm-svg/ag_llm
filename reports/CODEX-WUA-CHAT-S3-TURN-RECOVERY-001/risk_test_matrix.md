# Изменение → риск → тест → независимый oracle

Матрица определена до продуктовой реализации. Продуктовые изменения остановлены по TASK §4.4/§6/§9 после подтверждённых out-of-scope дефектов. Проверенные prerequisite tests не заменяют перечисленные NOT RUN Stage3 cases.

| Планируемое изменение / требование TASK §7 | Риск | Тест / oracle | Фактический статус |
| --- | --- | --- | --- |
| Общий RUN writer, P9 audit path | Junction выводит записи за Workspace | `test_audit_junction_must_not_write_outside_workspace`; перечень реальных файлов внешнего синтетического TEMP | RED: summary.json + index.json записаны вне Workspace |
| Единственный RUN writer | Два процесса подтверждают один sequence | `test_same_run_two_processes_have_unique_sequences_or_visible_refusal`; phase marker, raw JSONL, уникальные sequences | RED: [1,1] вместо [1,2], обе записи подтверждены |
| Обычный RUN/общая история | Неверный путь/ownership даже без инъекции | `test_normal_run_roundtrip_uses_existing_store`; receipt SHA + чтение record/summary/Chat | PASS |
| 1–4: Turn accept/idempotency | Дубли, другой текст под тем же ключом, ложное принятие | Два HTTP клиента, независимое чтение Turn+RAW файлов, количество user RAW | NOT RUN: Turn не реализован после blocker |
| 5–7: restart/RAW crash/lost HTTP | RAW потерян/дублирован, повтор скрыто создаёт новый запрос | Отдельные процессы, kill по фазе до/после публикации, same IDs/bytes при restart | NOT RUN: зависимая реализация остановлена |
| 8: cancel/late/duplicate result | Ложный SUCCESS или два assistant RAW | Durable RUN receipt + terminal revision + число assistant message files | NOT RUN: RUN/имитатор не запускаются |
| 9: disk/locks/corruption | Успех без записи, необратимое повреждение | Fault injection и содержимое/хеш файлов; existing core и P9 suites | Existing regressions выполнены; новые Turn fault-cases NOT RUN |
| 10: HTTP/ownership/path | Чужой Turn доступен или может писать | Неверные read/write token, Origin, query, schema, IDs и filesystem links | Existing Ultra Chat HTTP negative suite выполнен; Turn routes отсутствуют, новые NOT RUN |
| 11: model/context references | Старый Turn получает новую модель или неразрешённый контекст | Снимок references в Turn и request hash; смена EVM между accept/replay | DESIGN ONLY, NOT RUN |
| 12: RAW/Tk/web совместимость | Изменены старые сообщения/контексты | Existing storage/read suites и SHA настоящих данных до/после | Регрессия + readback выполнены; новых Turn записей нет |
| 13: внешние вызовы | Реальный provider/OAuth/Git запущен тестом | Audit guard до imports, loopback-only sockets/DNS, executable/Git metadata deny, receipts Python children | Guard receipts; provider connections 0 |
| 14: предыдущий UX | Регрессии дерева/rename/picker/первого Chat | Поставляемый JS + HTTP/storage tests | Existing regressions выполнены |

Прочие OPEN: `FOLLOWUP-WUA-S2-CHAT-STAGING-001` и `FOLLOWUP-WUA-CHAT-UX-CRASH-001` остаются ограничениями существующего bootstrap/Chat staging, не объявлены закрытыми. `FOLLOWUP-WUA-P9-INDEPENDENT-RUNTIME-001` может использовать свежий author-local P9 запуск лишь как новое evidence; независимая приёмка и весь Stage3 этим не заменяются.
