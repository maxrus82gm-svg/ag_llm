# История задач Codex — последние 10 ID

USER GO 04.11.2026. Это короткий индекс, а не место для полных поручений и отчётов. Новый HISTORY ID выдаёт скрипт при сохранении; TASK ID сохраняется. Координатор после независимой проверки обновляет существующую запись и запускает `task_history.py render --apply`.

Полные источники — в `reports/<TASK-ID>/`; адреса и SHA — в `task_record.json`. По умолчанию читать одну запись: `python -B -X utf8 tools/task_history.py read --id H-CODEX-000001`. Список: `python -B -X utf8 tools/task_history.py list --agent codex --last 10`. Команды чтения имеют общий лимит вывода; подробности и порядок веб-планировщика — №18.

<!-- TASK-HISTORY-INDEX:BEGIN -->
| Дата | ID | Задача | Статус / проверка | Адрес подробностей |
| --- | --- | --- | --- | --- |
| 2026-11-26 | `H-CODEX-000046` / `CODEX-WUA-COLIBRI-REAL-CATALOG-001` | READ_ONLY реального каталога локальных LLM | SUBMITTED / AUTHOR OFFLINE PASS / SOURCE REVIEW; independent runtime & real catalogue NOT RUN | `reports/CODEX-WUA-COLIBRI-REAL-CATALOG-001/task_record.json` |
| 2026-11-26 | `H-CODEX-000045` / `CODEX-WUA-EVM-GLOBAL-INDICATORS-001` | EVM — общие пороги, сохранение индикации и восстановление допуска | SUBMITTED / OWNER GUI BOUNDED PASS / SOURCE REVIEW; author OFFLINE 472 PASS, independent CI/REAL/full TEST NOT RUN | `reports/CODEX-WUA-EVM-GLOBAL-INDICATORS-001/task_record.json` |
| 2026-11-25 | `H-CODEX-000044` / `CODEX-WUA-EVM-PERSISTENT-CONNECTION-001` | STANDARD persistent GigaChat permission, EVM, chat input, activity and naming | AUTHOR PARTIAL / OWNER LIVE RESTART BOUNDED PASS 26.11; independent CI and H45 successor owner GUI PASS; independent acceptance OPEN | `reports/CODEX-WUA-EVM-PERSISTENT-CONNECTION-001/task_record.json` |
| 2026-11-17 | `H-CODEX-000043` / `CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001` | STANDARD — завершение, legacy GigaChat session и экземпляры | AUTHOR PARTIAL; successor personal account RECOVERED (owner-authorised, local readback PASS); INDEPENDENT CI, OWNER GUI, REAL PROVIDER NOT RUN | `reports/CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001/task_record.json` |
| 2026-11-17 | `H-CODEX-000042` / `CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001` | EVM — восстановление проверки и инженерные исправления | AUTHOR PARTIAL / SOURCE REVIEW; OFFLINE F02–F05; F01, CI, REAL, UX OPEN | `reports/CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001/task_record.json` |
| 2026-11-17 | `H-CODEX-000041` / `CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001` | EVM — управление моделями, чат и многооконный режим | SUBMITTED / REVIEW PENDING; AUTHOR PARTIAL; S2 72/73 FAIL; GUI/REAL NOT VERIFIED | `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/task_record.json` |
| 2026-11-17 | `H-CODEX-000040` / `CODEX-WUA-EVM-UNIFIED-CONNECTION-001` | EVM ↔ GigaChat — единая сессия, Turn, статусы | SUBMITTED / REVIEW PENDING; AUTHOR OFFLINE PASS; GUI/REAL NOT VERIFIED | `reports/CODEX-WUA-EVM-UNIFIED-CONNECTION-001/task_record.json` |
| 2026-11-17 | `H-CODEX-000039` / `CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001` | GigaChat — первый настоящий ответ одной модели | SUBMITTED / REVIEW PENDING; first REAL GigaChat-2 bounded PASS; 5 models NOT RUN | `reports/CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001/task_record.json` |
| 2026-11-15 | `H-CODEX-000038` / `CODEX-WUA-CHAT-GIGACHAT-REAL-MULTIMODEL-MVP-001` | GigaChat — транспорт и шесть моделей | SUBMITTED / REVIEW PENDING; AUTHOR OFFLINE PASS; H38 REAL NOT RUN | `reports/CODEX-WUA-CHAT-GIGACHAT-REAL-MULTIMODEL-MVP-001/task_record.json` |
| 2026-11-15 | `H-CODEX-000037` / `CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001` | Подготовка GigaChat Ultra к REAL | SUBMITTED / REVIEW PENDING; NOT VERIFIED | `reports/CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001/task_record.json` |
<!-- TASK-HISTORY-INDEX:END -->

Старый полный текст сохранён побайтово: `reports/CODEX-TASK-HISTORY-ID-001/preservation/001_История выполненных задач Codex.md`. Снимок не читать целиком на старте. Старые статусы относятся к своим датам; перенос не является новым PASS. Старше десяти — вне рабочего окна, но не удалено из архива.

[[000_Задачи Codex]]

Прежняя связь: [[001_История выполненных задач Codex]].
