# История задач Codex — последние 10 ID

USER GO 04.11.2026. Это короткий индекс, а не место для полных поручений и отчётов. Новый HISTORY ID выдаёт скрипт при сохранении; TASK ID сохраняется. Координатор после независимой проверки обновляет существующую запись и запускает `task_history.py render --apply`.

Полные источники — в `reports/<TASK-ID>/`; адреса и SHA — в `task_record.json`. По умолчанию читать одну запись: `python -B -X utf8 tools/task_history.py read --id H-CODEX-000001`. Список: `python -B -X utf8 tools/task_history.py list --agent codex --last 10`. Команды чтения имеют общий лимит вывода; подробности и порядок веб-планировщика — №18.

<!-- TASK-HISTORY-INDEX:BEGIN -->
| Дата | ID | Задача | Статус / проверка | Адрес подробностей |
| --- | --- | --- | --- | --- |
| 2026-11-07 | `H-CODEX-000020` / `CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001` | Stage5: полноценный Web/Tk OFFLINE TEST Chat | DOC CLOSED / BOUNDED PASS; 209 Python + 165 JS + 3 reviewer + 10 HTTP PASS independent Windows; final browser GUI and clean Windows portability NOT RUN; Stage6 NEXT | `reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/task_record.json` |
| 2026-11-06 | `H-CODEX-000019` / `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001` | Stage4: исправление внешней отмены после начала запроса | DOC CLOSED / BOUNDED PASS; independent Windows 154 main + 6 reviewer + 60 stress PASS; Stage4 OFFLINE Stage5 READY, full GUI/real NOT RUN | `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/task_record.json` |
| 2026-11-06 | `H-CODEX-000018` / `CODEX-WUA-CHAT-S4-DEADLINE-UNKNOWN-REPAIR-001` | Исправление ложного SUCCESS после дедлайна | DOC CLOSED / DEADLINE BOUNDED PASS: independent 150 + 120 deadline PASS; external Task.cancel suppressed reviewer 1 FAIL x2; Stage4 HOLD | `reports/CODEX-WUA-CHAT-S4-DEADLINE-UNKNOWN-REPAIR-001/task_record.json` |
| 2026-11-06 | `H-CODEX-000017` / `CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001` | Stage4B: S4A↔Turn OFFLINE, устойчивый ответ/восстановление | DOC CLOSED / TECHNICAL PARTIAL; S4B 14+5 independent Windows PASS; S4A deadline 1 FAIL; Stage4 HOLD | `reports/CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001/task_record.json` |
| 2026-11-06 | `H-CODEX-000016` / `CODEX-WUA-CHAT-S4A-COMMON-REQUEST-SERVICE-001` | Единый сервис обычного диалога — Stage4A OFFLINE | DOC CLOSED / S4A BOUNDED PASS; author 116 PASS + compile; new independent runtime NOT RUN; Stage4B/live HOLD | `reports/CODEX-WUA-CHAT-S4A-COMMON-REQUEST-SERVICE-001/task_record.json` |
| 2026-11-05 | `H-CODEX-000015` / `CODEX-WUA-S3-WS-WRITER-BUSY-CI-DIAG-001` | Повторная короткая диагностика блокировки Workspace | DOC CLOSED / DIAGNOSTIC PARTIAL; author 12/12 PASS, 600 RAW; old CI cause UNKNOWN, independent CI NOT RUN | `reports/CODEX-WUA-S3-WS-WRITER-BUSY-CI-DIAG-001/task_record.json` |
| 2026-11-05 | `H-CODEX-000014` / `CODEX-WUA-S3-WS-WRITER-BUSY-REPAIR-001` | Диагностика WorkspaceBusyError и исправление классификации OS ошибок / child stderr | DOC ITERATION CLOSED / TECHNICAL PARTIAL; PARTIAL / SOURCE+AUTHOR EVIDENCE; original CI cause OPEN; independent runtime NOT RUN | `reports/CODEX-WUA-S3-WS-WRITER-BUSY-REPAIR-001/task_record.json` |
| 2026-11-05 | `H-CODEX-000013` / `CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001` | Web Alarm Ultra — Stage 3: первая отправка сообщения, устойчивый Turn и восстановление | DOC ITERATION CLOSED / TECHNICAL PARTIAL; PARTIAL / TEST Windows CI; USER GUI PASS (2 sends/2 TEST replies/F5); writer-lock OPEN; real LLM NOT RUN | `reports/CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001/task_record.json` |
| 2026-11-04 | `H-CODEX-000012` / `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001` | Защита Run Store v2 перед Stage 3 | SUBMITTED / REVIEW PENDING; PASS / INDEPENDENT WINDOWS CI 56/56; full regression NOT RUN | `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/task_record.json` |
| 2026-11-04 | `H-CODEX-000011` / `CODEX-TASK-HISTORY-ID-001` | История по ID, автоматическая нумерация и порядок веб-планировщика | SUBMITTED / REVIEW PENDING; NOT VERIFIED | `reports/CODEX-TASK-HISTORY-ID-001/task_record.json` |
<!-- TASK-HISTORY-INDEX:END -->

Старый полный текст сохранён побайтово: `reports/CODEX-TASK-HISTORY-ID-001/preservation/001_История выполненных задач Codex.md`. Снимок не читать целиком на старте. Старые статусы относятся к своим датам; перенос не является новым PASS. Старше десяти — вне рабочего окна, но не удалено из архива.

[[000_Задачи Codex]]

Прежняя связь: [[001_История выполненных задач Codex]].
