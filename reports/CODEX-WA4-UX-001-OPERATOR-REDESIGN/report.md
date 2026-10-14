# CODEX-WA4-UX-001-OPERATOR-REDESIGN

STATUS: IN PROGRESS / LOCAL ONLY. ARCH CLASS: Web Alarm Workspace / Operator UI / UX; PRIMARY 23; TEST 36.2. БЛОК 1 frozen. AMENDMENT: пользователь явно разрешил адресное изменение test_web_alarm_operator_ui.js. Backend/shared docs/Ultra/CI read-only.

TEMP: C:/Users/REX/AppData/Local/Temp/codex-wa4ux001-md3m9ccc. Baseline 34 HTTP/Python PASS, 23 JS PASS. Разрешённый simple_local helper недоступен (account/model unsupported); работа ведётся основным агентом.

Реализация: отдельные Workspace/main/TASK columns; source и human REPORT events по этапам; RU labels с исходными enum в tooltip; настоящий GET /status signal и aging; локальный draft по origin+workspace_id+root, Web Locks exclusive, storage failure + beforeunload, пустая форма ephemeral. Existing POST /tasks — только явная регистрация, server IDs, без planner/исполнения; title первая строка, goal/raw normalized source. Pending before POST сохранён; любой неопределённый outcome блокирует повтор и удаление draft, сохраняя текст. Idempotent create backend отсутствует — отдельное предложение, не fake recovery. Folder picker/rename/pause/task deletion — PROPOSAL only.

Первый legacy JS после замены layout: 17 PASS/6 FAIL, ожидаемые устаревшие UI assertions; обновлены после разрешения. Новые draft tests: 43 PASS/1 FAIL — выявлен read-before-lock gap; повторное чтение under-lock исправило, 44 PASS. Native browser IAB: recovery UI и реальный autosave/reload уже проверены на guarded disposable demo-2 http://127.0.0.1:51134; live data не используются. Первый demo bootstrap получил AttributeError (неверный helper method), исправлен на существующий API, новый fixture root; исходный startup failure сохраняется.

PENDING: final JS/HTTP/static, negative controls, final browser desktop/narrow + readonly hashes + registration, regression, manual engineering review, source/evidence/rotation.
