# История задач Codex — последние 10 ID

USER GO 04.11.2026. Это короткий индекс, а не место для полных поручений и отчётов. Новый HISTORY ID выдаёт скрипт при сохранении; TASK ID сохраняется. Координатор после независимой проверки обновляет существующую запись и запускает `task_history.py render --apply`.

Полные источники — в `reports/<TASK-ID>/`; адреса и SHA — в `task_record.json`. По умолчанию читать одну запись: `python -B -X utf8 tools/task_history.py read --id H-CODEX-000001`. Список: `python -B -X utf8 tools/task_history.py list --agent codex --last 10`. Команды чтения имеют общий лимит вывода; подробности и порядок веб-планировщика — №18.

<!-- TASK-HISTORY-INDEX:BEGIN -->
| Дата | ID | Задача | Статус / проверка | Адрес подробностей |
| --- | --- | --- | --- | --- |
| 2026-11-09 | `H-CODEX-000027` / `CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001` | CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001 | DOC CLOSED / ORDINARY CORE BRIDGE BOUNDED INDEPENDENT OFFLINE PASS; STAGE6/LIVE HOLD; PASS / INDEPENDENT WINDOWS GUARDED Python 109/109 + Node 52/52 + guards 6/6; 5 SHA matched; GUI/CI/live NOT RUN | `reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/task_record.json` |
| 2026-11-08 | `H-CODEX-000026` / `CODEX-RT002-B2-ORDINARY-CHAT-POLICY-DECISION-001` | Ordinary Chat — подготовка бюджетных решений U1–U6 | DOC CLOSED / BOUNDED INDEPENDENT DOCUMENT PASS; CHAT-A01 design constraint captured; A/B/C UNCALIBRATED NOT ACTIVE; U1–U6 USER PENDING; S3b/Stage6 HOLD | `reports/CODEX-RT002-B2-ORDINARY-CHAT-POLICY-DECISION-001/task_record.json` |
| 2026-11-08 | `H-CODEX-000025` / `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001` | Исправление S2 isolation oracle для OFFLINE ledger | DOC CLOSED / S2 ORACLE BOUNDED INDEPENDENT PASS; Stage6 HOLD; Windows S2 73/73 + quality 47/47 + three weakening RED; S1 69/69; S3a independent NOT RUN | `reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/task_record.json` |
| 2026-11-08 | `H-CODEX-000024` / `CODEX-RT002-B2-S1-INVENTORY-RECON-001` | Web Alarm Ultra — исправление инвентаризации сетевых маршрутов S1 | DOC CLOSED / S1 OFFLINE BOUNDED INDEPENDENT PASS; S2 one FAIL OPEN; Stage6 HOLD; PASS / TARGETED INDEPENDENT WINDOWS S1 69/69 + extra 23/23; S2 INDEPENDENT 72/73 FAIL; overall PARTIAL | `reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/task_record.json` |
| 2026-11-08 | `H-CODEX-000023` / `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001` | Web Alarm Ultra — Stage6A RT-002 S3a OFFLINE ledger | DOC CLOSED / S3a INDEPENDENT OFFLINE BOUNDED PASS; GitHub CI 35 S3a + 51 Run Store + 3 expected RED + guard6; WEB25 source PARTIAL preserved; S1/S2 successors fixed; S3b/Stage6/live HOLD | `reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/task_record.json` |
| 2026-11-07 | `H-CODEX-000022` / `CODEX-WUA-S5-TURN-UX-RECOVERY-001` | Web Alarm Ultra — Stage 5 OFFLINE: исправление отображения Turn, проверки состояния и восстановления после отмены | DOC CLOSED / STAGE5 OFFLINE BOUNDED USER SMOKE; Stage6 next separate TASK; PARTIAL / BOUNDED SOURCE+AUTHOR EVIDENCE WEB25; USER WINDOWS STAGE5 SMOKE PASS; RAW/480px/Tcl OPEN | `reports/CODEX-WUA-S5-TURN-UX-RECOVERY-001/task_record.json` |
| 2026-11-07 | `H-CODEX-000021` / `CODEX-WUA-S5-TURN-CHECK-DIAG-001` | CHAT-ONLY AMENDMENT 1 — SHA-256 `bb0bcb656d6d8144dbc49b65262fe0e160926799b9c2efde66e78d37a9852479` | DOC CLOSED / DIAGNOSTIC PARTIAL; H22 successor accepted bounded; PARTIAL / BOUNDED DIAGNOSTIC SOURCE REVIEW WEB25; author tests only; historical RAW loss OPEN | `reports/CODEX-WUA-S5-TURN-CHECK-DIAG-001/task_record.json` |
| 2026-11-07 | `H-CODEX-000020` / `CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001` | Stage5: полноценный Web/Tk OFFLINE TEST Chat | DOC CLOSED / BOUNDED PASS; 209 Python + 165 JS + 3 reviewer + 10 HTTP PASS independent Windows; final browser GUI and clean Windows portability NOT RUN; Stage6 NEXT | `reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/task_record.json` |
| 2026-11-06 | `H-CODEX-000019` / `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001` | Stage4: исправление внешней отмены после начала запроса | DOC CLOSED / BOUNDED PASS; independent Windows 154 main + 6 reviewer + 60 stress PASS; Stage4 OFFLINE Stage5 READY, full GUI/real NOT RUN | `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/task_record.json` |
| 2026-11-06 | `H-CODEX-000018` / `CODEX-WUA-CHAT-S4-DEADLINE-UNKNOWN-REPAIR-001` | Исправление ложного SUCCESS после дедлайна | DOC CLOSED / DEADLINE BOUNDED PASS: independent 150 + 120 deadline PASS; external Task.cancel suppressed reviewer 1 FAIL x2; Stage4 HOLD | `reports/CODEX-WUA-CHAT-S4-DEADLINE-UNKNOWN-REPAIR-001/task_record.json` |
<!-- TASK-HISTORY-INDEX:END -->

Старый полный текст сохранён побайтово: `reports/CODEX-TASK-HISTORY-ID-001/preservation/001_История выполненных задач Codex.md`. Снимок не читать целиком на старте. Старые статусы относятся к своим датам; перенос не является новым PASS. Старше десяти — вне рабочего окна, но не удалено из архива.

[[000_Задачи Codex]]

Прежняя связь: [[001_История выполненных задач Codex]].
