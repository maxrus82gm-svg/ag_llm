# Следующий gate: реальный MCP в обычном ChatGPT

**Текущий статус: DESKTOP E2E NOT VERIFIED.** После полного перезапуска пользователь
подтвердил отрицательный результат: local marketplace WUA 0.2.1 распознаётся через @,
но инструменты не передаются модели; настоящих вызовов 0 из 4.
Повторять установку, перезапуск Desktop и @-упоминание прежнего подключения не нужно.

Причина и evidence: `post_restart_diagnostics_20261016/report.md`.
Официальный альтернативный путь подготовлен: `secure_tunnel_preparation/README.md`.

## Ближайший шаг

Проверить доступ к https://platform.openai.com/settings/organization/tunnels и наличие
настоящего tunnel_id, связанного с целевым ChatGPT workspace. Ключ не присылать в чат.
Без такого ресурса и restricted runtime key живое подключение не запускается.
Доступность этих функций для текущей учётной записи ещё не подтверждена.

Все пути и STDIO-аргументы уже заполнены в подготовке. После реквизитов: запуск нового
TASK-only foreground runtime, проверка health/ready и discovery; затем ручное добавление
пользовательского MCP-сервера в ChatGPT с Connection: Tunnel и тем же tunnel_id.
Это новый ChatGPT binding, не переустановка marketplace WUA. GUI агентом не автоматизируется.

## Четыре вызова в новом обычном ChatGPT Desktop Chat

Выбрать новое Tunnel-подключение и отправить:

> Выполни настоящие MCP-вызовы WUA: (1) ping; (2) list_capabilities;
> (3) read_synthetic_context с fixture_id="synthetic_wua_desktop_001";
> (4) read_synthetic_context с fixture_id="other_task". Последний должен быть отвергнут.
> Не имитируй ответы. Если инструментов нет, остановись и сообщи 0 calls.
> Покажи реальные task_id, session_id, nonce, context_sha256, proof_path,
> а также код отказа последнего запроса. Подтверди, что это обычный Desktop Chat.

## Независимая сверка

Verifier получает сырой результат обычного Chat и оригинальный receipt из
`secure_tunnel_preparation/CODEX-WUA-0-DESKTOP-MCP-E2E-001/evidence/<session_id>/session.json`.
Проверяет одинаковые session_id/nonce/context hash, три OK и один TASK_ID_DENIED,
call_id, только GET, storage unchanged, ноль guard violations/production/model calls.
Имя клиента не является доверенным подтверждением режима. Нужны отдельная аттестация
пользователя и результаты обычного Chat. При разных MCP-сессиях receipts вручную
не объединять; gate остаётся неуспешным до выяснения session affinity.

SDK, host-loader, Work/Codex, успешный daemon startup и список tools не заменяют этот gate.
Независимая приёмка не объявляется Codex самостоятельно. GitHub-публикация не выполнялась.
