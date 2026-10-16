# Подготовленный путь WUA → обычный ChatGPT через Secure MCP Tunnel

**Подготовлено локально. Hosted-туннель ещё не запускался. DESKTOP E2E NOT VERIFIED.**

Официальный tunnel-client v0.0.16 находится в `tools/`; ZIP и опубликованные SHA-256
сверены. Профиль `wua-stdio.template.yaml` принят штатной offline-командой. Он запускает
запечатанный WUA 0.2.1 с private Python, без изменений адаптера, config.toml и marketplace.
Пустой tunnel_id в шаблоне намеренный: его реальное значение передаётся при запуске.

Нужен существующий tunnel_id из [Platform Tunnels](https://platform.openai.com/settings/organization/tunnels),
связанный с целевым ChatGPT workspace, и restricted runtime API key с Tunnels Read + Use.
Доступность раздела и права ещё не проверены. Новые ключи и роли агент не создавал.
Секретный ключ не отправлять в чат и не включать в скриншоты.

Когда доступ будет подтверждён, открыть `Start-WUA-Tunnel.cmd`. Все длинные пути уже
заданы. В окне ввести tunnel_id и скрытым вводом ключ; держать окно открытым на время
проверки. Это явный запуск нового исходящего соединения к OpenAI, ещё не выполненный
агентом. Не требуется менять VPN, proxy, DNS или firewall. Клиент использует прежний
синтетический сервер и новый TASK-scoped cwd. Будущие receipts будут в
`secure_tunnel_preparation/CODEX-WUA-0-DESKTOP-MCP-E2E-001/evidence/`.

Ручной шаг в ChatGPT после готовности туннеля: **Plugins → Add custom MCP server →
Connection: Tunnel → выбрать тот же tunnel_id → Create as a plugin**, с предусмотренным
интерфейсом подтверждением. Действующий marketplace WUA не удалять и не переустанавливать.
Выбрать новое Tunnel-подключение в обычном Chat, выполнить четыре вызова из
`../NEXT_MANUAL_GATE.md`. Три инструмента в списке сами по себе не являются E2E.

Ключ не сохраняется launcher-ом в файл или аргументы: он передаётся окружением только
нового процесса. Профиль ссылается на `env:WUA_TUNNEL_RUNTIME_KEY`. Raw HTTP logging,
автоматическое открытие браузера и Cloudflare companion не включены. Локальный health
интерфейс при будущем запуске привязан к `127.0.0.1` со свободным портом; его адрес
появится в `runtime-health.url`. Ctrl+C останавливает только новый foreground runtime.

Откат данной подготовки не требуется: она не активировала ни одного подключения.
Если туннель будет запущен, сначала остановить его Ctrl+C; удаление облачного ресурса
или нового ChatGPT-подключения является отдельным действием пользователя. Исходные
WUA plugin/direct записи и прежние evidence сохраняются.

[OpenAI: Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels),
[OpenAI: подключение MCP в ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt).

Локальная проверка bridge выполнена отдельно через штатный bounded `dev proxy`:
четыре настоящих RPC-вызова, три OK и TASK_ID_DENIED, единые session/nonce/hash,
storage unchanged и ноль guard violations. Receipt и сырые RPC — `local_bridge_test/`.
Стенд автоматически остановился через 45 секунд; облачный доступ не проверялся.
Его localhost URL и тестовый tunnel_id не использовать в ChatGPT. Обычный Chat: 0 calls.
