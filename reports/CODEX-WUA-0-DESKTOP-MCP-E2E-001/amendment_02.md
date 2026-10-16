# AMENDMENT — прямая пользовательская STDIO-регистрация

Дата: 2026-10-16, Asia/Yekaterinburg. Та же TASK:
CODEX-WUA-0-DESKTOP-MCP-E2E-001.

Прямое указание пользователя разрешает подготовить и при официальной поддержке
зарегистрировать WUA Desktop Read-only в ChatGPT Desktop через CLI или
документированную конфигурацию. Источник значений — plugin/mcp.json.
До изменения сохранить исходную конфигурацию и точный откат. Не менять существующие
MCP-серверы, production, GitHub, VPN/proxy/firewall, системные права. UI-автоматизация,
реестр и недокументированные внутренние файлы запрещены. Это дополнение не расширяет
права Web Alarm и не разрешает новый этап разработки.

Официальная документация подтверждает:

- [Model Context Protocol](https://learn.chatgpt.com/docs/extend/mcp): Desktop, CLI и
  IDE одного Codex host используют общий ~/.codex/config.toml; поддержаны
  [mcp_servers.<server-name>], command, args, cwd и STDIO.
- [Developer commands](https://learn.chatgpt.com/docs/developer-commands):
  codex mcp add/get/list/remove управляют такими записями. Локальный CLI подтверждает
  эти команды. Его add не имеет cwd-флага, поэтому выбран документированный TOML
  с сохранением cwd кандидата.

Действие: добавить единственную секцию mcp_servers.wua_desktop_readonly в
C:/Users/REX/.codex/config.toml. Существующие байты остаются неизменным префиксом;
исходный полный файл хранится вне Git-репозитория в собственной backup-папке
C:/Users/REX/.codex/backups/CODEX-WUA-0-DESKTOP-MCP-E2E-001/. Полная конфигурация
не выводится в отчёт: она может содержать сведения других подключений.
Заменяется только ${PLUGIN_ROOT} на абсолютную папку plugin кандидата.

Регистрация не доказывает ordinary Chat E2E. После неё отдельно проверяются
CLI discovery и протокол/три tools по зарегистрированным значениям. SDK-проверка
помечается отдельно. Desktop UI Restart и настоящий вызов из обычного Chat
выполняет пользователь; никаких скрытых reload или обходов.

Прежние evidence и отчёт сохраняются. Публикация GitHub остаётся ON HOLD.
