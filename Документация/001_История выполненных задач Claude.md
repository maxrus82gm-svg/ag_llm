# История задач Claude — последние 10 ID

USER GO 04.11.2026. Это короткий индекс, а не место для полных поручений и отчётов. Новый HISTORY ID выдаёт скрипт при сохранении; TASK ID сохраняется. Координатор после независимой проверки обновляет существующую запись и запускает `task_history.py render --apply`.

Полные источники — в `reports/<TASK-ID>/`; адреса и SHA — в `task_record.json`. По умолчанию читать одну запись: `python -B -X utf8 tools/task_history.py read --id H-CLAUDE-000001`. Список: `python -B -X utf8 tools/task_history.py list --agent claude --last 10`. Команды чтения имеют общий лимит вывода; подробности и порядок веб-планировщика — №18.

<!-- TASK-HISTORY-INDEX:BEGIN -->
| Дата | ID | Задача | Статус / проверка | Адрес подробностей |
| --- | --- | --- | --- | --- |
| 2026-11-03 | `H-CLAUDE-000010` / `CLAUDE-WUA-CHAT-RUNSTORE-P9-001` | Защита Run Store от конкурентных изменений | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-CHAT-RUNSTORE-P9-001/task_record.json` |
| 2026-11-01 | `H-CLAUDE-000009` / `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001` | Безопасная замена файлов общего хранилища | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001/task_record.json` |
| 2026-10-31 | `H-CLAUDE-000008` / `CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001` | Защита путей контекста от вложенных junction | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001/task_record.json` |
| 2026-10-31 | `H-CLAUDE-000007` / `CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001` | Общее хранилище Workspace и Chat | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001/task_record.json` |
| 2026-10-31 | `H-CLAUDE-000006` / `CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001` | Закреплённые независимые окна карточек моделей | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001/task_record.json` |
| 2026-10-30 | `H-CLAUDE-000005` / `CLAUDE-WUA-EVM-INTERACTION-DND-001` | Раскрытие карточек, предварительный просмотр и перетаскивание | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-EVM-INTERACTION-DND-001/task_record.json` |
| 2026-10-29 | `H-CLAUDE-000004` / `CLAUDE-DOC-TASK-SLOT-ROTATION-001` | Скриптовая сдача и ротация слота задачи | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-DOC-TASK-SLOT-ROTATION-001/task_record.json` |
| 2026-10-29 | `H-CLAUDE-000003` / `CLAUDE-WUA-EVM-COMPACT-LAYOUT-001` | Компактное расположение карточек EVM | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001/task_record.json` |
| 2026-10-28 | `H-CLAUDE-000002` / `CLAUDE-WUA-EVM-MODEL-CARD-UI-001` | Интерфейс карточек моделей EVM | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-EVM-MODEL-CARD-UI-001/task_record.json` |
| 2026-10-28 | `H-CLAUDE-000001` / `CLAUDE-WUA-CHAT-S1-READONLY-UI-001` | Первый экран Ultra Chat и безопасное чтение истории | HISTORICAL — результат в источнике; исторический verdict сохранён; заново не проверен | `reports/CLAUDE-WUA-CHAT-S1-READONLY-UI-001/task_record.json` |
<!-- TASK-HISTORY-INDEX:END -->

Старый полный текст сохранён побайтово: `reports/CODEX-TASK-HISTORY-ID-001/preservation/001_История выполненных задач Claude.md`. Снимок не читать целиком на старте. Старые статусы относятся к своим датам; перенос не является новым PASS. Старше десяти — вне рабочего окна, но не удалено из архива.

[[000_Задачи Claude]]
