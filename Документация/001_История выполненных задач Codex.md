# История задач Codex — последние 10 ID

USER GO 04.11.2026. Это короткий индекс, а не место для полных поручений и отчётов. Новый HISTORY ID выдаёт скрипт при сохранении; TASK ID сохраняется. Координатор после независимой проверки обновляет существующую запись и запускает `task_history.py render --apply`.

Полные источники — в `reports/<TASK-ID>/`; адреса и SHA — в `task_record.json`. По умолчанию читать одну запись: `python -B -X utf8 tools/task_history.py read --id H-CODEX-000001`. Список: `python -B -X utf8 tools/task_history.py list --agent codex --last 10`. Команды чтения имеют общий лимит вывода; подробности и порядок веб-планировщика — №18.

<!-- TASK-HISTORY-INDEX:BEGIN -->
| Дата | ID | Задача | Статус / проверка | Адрес подробностей |
| --- | --- | --- | --- | --- |
| 2026-11-04 | `H-CODEX-000011` / `CODEX-TASK-HISTORY-ID-001` | История по ID, автоматическая нумерация и порядок веб-планировщика | SUBMITTED / REVIEW PENDING; NOT VERIFIED | `reports/CODEX-TASK-HISTORY-ID-001/task_record.json` |
| 2026-11-04 | `H-CODEX-000010` / `CODEX-WUA-CHAT-S3-TURN-RECOVERY-001` | Проверка условий восстановления Turn и Run Store | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/task_record.json` |
| 2026-11-04 | `H-CODEX-000009` / `CODEX-WUA-CHAT-UX-LIVE-FIX-001` | Исправление создания и переименования чатов | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/task_record.json` |
| 2026-11-04 | `H-CODEX-000008` / `CODEX-WUA-CHAT-UI-INTEGRATION-001` | Подключение регистрации Workspace к Ultra Chat | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CODEX-WUA-CHAT-UI-INTEGRATION-001/task_record.json` |
| 2026-11-02 | `H-CODEX-000007` / `CODEX-WUA-LOCAL-LLM-DISCOVERY-001` | Исследование локальных серверов Ollama и Colibri | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001/task_record.json` |
| 2026-11-01 | `H-CODEX-000006` / `CODEX-WUA-DOC-WEB19-REPAIR-001` | Согласование документации после проверки WEB19 | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CODEX-WUA-DOC-WEB19-REPAIR-001/task_record.json` |
| 2026-11-01 | `H-CODEX-000005` / `ASTRA-DOC-CONTEXT-OPTIMIZATION-001` | Оптимизация контекста документации и закрытие слота | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/task_record.json` |
| 2026-10-26 | `H-CODEX-000004` / `ASTRA-WUA-37-ROADMAP-REVISION-001` | Переработка программы перехода Web Alarm Ultra | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/ASTRA-WUA-37-ROADMAP-REVISION-001/task_record.json` |
| 2026-10-26 | `H-CODEX-000003` / `ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001` | Архитектурная проверка миграции Ultra Chat | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001/task_record.json` |
| 2026-10-25 | `H-CODEX-000002` / `CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001` | Контракт строгого допуска Desktop MCP | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/task_record.json` |
<!-- TASK-HISTORY-INDEX:END -->

Старый полный текст сохранён побайтово: `reports/CODEX-TASK-HISTORY-ID-001/preservation/001_История выполненных задач Codex.md`. Снимок не читать целиком на старте. Старые статусы относятся к своим датам; перенос не является новым PASS. Старше десяти — вне рабочего окна, но не удалено из архива.

[[000_Задачи Codex]]

Прежняя связь: [[001_История выполненных задач Codex]].
