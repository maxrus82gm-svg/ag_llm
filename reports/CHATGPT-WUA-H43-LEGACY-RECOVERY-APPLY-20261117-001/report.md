# H43 — разрешённое восстановление legacy account в STANDARD Personal

**TASK ID:** `CHATGPT-WUA-H43-LEGACY-RECOVERY-APPLY-20261117-001`
**Дата:** 17.11.2026
**Пользовательское разрешение:** «Да, конечно, надо восстанавливать. Всё, окей» в продолжение адресного вопроса о восстановлении `ACTIVE` account в личных чатах STANDARD, без paid GigaChat Turn и без изменения старых grant/ledger.
**Компьютер:** `DESKTOP-SC96D3U`
**Исход:** `RECOVERED_ACCOUNT_ONLY / LOCAL READBACK PASS / REAL GIGACHAT NOT RUN`

## Источники и scope

- Исходный авторский H43: `H-CODEX-000043` / `CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001`, `PARTIAL`. Локальный операторский recovery подготовлен и опубликован отдельно как #645 `ededb63d217e32b7c0b3610db709812b85c8c859` (`tools/legacy_session_recovery.py`).
- Цель — **только одна старая account-запись** хранилища `%LOCALAPPDATA%/WebAlarmWorkspace/personal_chats/.ultra/provider_sessions`. Реальный старый `grant`, другие файлы, RAW, история чатов и весь `BudgetLedger` не изменяются.
- Вне-Git резервная копия `%LOCALAPPDATA%/WebAlarmRecovery/H43_20261117_222742` содержит исходные четыре JSON. Операторский исходный скрипт находится вне репозитория: `%LOCALAPPDATA%/WebAlarmRecovery/H43_operator_recovery_20261117.py`. Он не является обычной точкой запуска продукта.

## Gate перед записью

- Проверено соответствие backup → 4/4 байтовых копий оригиналам; список четырёх JSON файлов совпал. Исходные файлы на момент проверки не менялись.
- Проверен embedded Workspace ID, не путать с ID регистрации Web Alarm. Пройден `BudgetLedger.recover()`: 30 событий, 10 попыток (включая известный `UNKNOWN_TERMINAL`), 3 сохранлённые версии моделей.
- Локальный список владельцев `python.exe/pythonw.exe/py.exe/cmd.exe` по известным launch-маркерам — 0. Нет слушателей на локальных стандартных портах 8765–8768; повторно проверено перед mutation.
- Обнаружено **две** старые записи аккаунта в разных зарегистрированных Workspace: personal ACTIVE и прежний project Workspace ACTIVE (оба без `owner_lock`). Вторая запись не входит в разрешённую область изменения и проверена на неизменность.

## Атомарное действие и факт readback

Вызван `recover_legacy_account(root, embedded_workspace_id, account_id, apply=True, owner_authorized=True, owner_quiescent=...)` через отдельный trusted операторский скрипт. `owner_quiescent` заново проверяет локальные процессы, loopback-порты и неизменность старой сторонней account-записи. Внутренний код использует общий OS-account-lock и Workspace writer-lock; повторно проверяет grant, ledger и исходные bytes.

**Прямой output:** `H43_PRECHECK=PASS` → `H43_APPLY=RECOVERED_ACCOUNT_ONLY`, `H43_EXIT_CODE=0`.

- Только personal account: `ACTIVE` → `CLOSED` с `legacy_recovery=MANUAL_EVIDENCE_V1`.
- В personal `.ultra/provider_sessions` создан новый `legacy_recovery_<old-grant-id>.json` через publish-only, содержащий точный исходный account и контрольную сумму старого grant. Сам старый grant остаётся `ACTIVE` **как историческая запись** и не предоставляет автоматического права на новый Turn.
- Три остальных JSON: 3/3 SHA-256 без изменений. Проверено неизменное состояние BudgetLedger 30/10, подтверждённые pins 3/3, старая account-запись другого Workspace без изменений.
- Отдельный последующий PowerShell readback из нового процесса: `RECHECK=PASS`, исходные account bytes совпадают с `previous_account_raw_utf8` evidence, 3/3 других JSON совпадают с backup, state CLOSED, marker ожидаемый.
- **OAuth/catalog/inference 0/0/0**, retries и платные Turn 0. Запуск STANDARD, EVM, live model connect, UI/F5 и реальная переписка НЕ ПРОВЕРЯЛИСЬ.

## Границы, риски и NEXT

- Нынешняя personal account recovery **DONE (bounded)**. Это не независимая GitHub-hosted CI, не физический GUI PASS и не проверка реального API. Не называть H43 целиком завершённой.
- **OPEN:** историческая вторая `ACTIVE` запись в другом Workspace; никакая миграция или закрытие без нового scope/GO. Сканирование локальных процессов не доказывает отсутствие владельца на другом хосте. Новый старый процесс вне актуального runtime нельзя исключить глобально.
- Для нового STANDARD подключения требуются штатный путь user action, существующие реальные provider limits, защищённый budget/Turn admission; никаких автоматических paid requests. Проверить после пользовательского merge #645 и настоящего запуска в отдельном UI smoke, независимо от данного ремонта.
- Изменение постоянного хранилища аудировано только локально; отчёт не содержит секретов, полного JSON, имени старого grant, ключей и user-private путей.
