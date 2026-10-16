# WUA Desktop Read-only — прямая STDIO-регистрация

2026-10-16, Asia/Yekaterinburg. TASK CODEX-WUA-0-DESKTOP-MCP-E2E-001,
AMENDMENT 02. **Регистрация выполнена. Desktop E2E ещё NOT VERIFIED.**

## Поддерживаемый механизм и выполненное действие

[Официальная документация MCP](https://learn.chatgpt.com/docs/extend/mcp)
описывает общий пользовательский ~/.codex/config.toml для ChatGPT Desktop, CLI
и IDE на одном Codex host. Поддержаны STDIO и таблицы mcp_servers с command,
args и cwd. [CLI](https://learn.chatgpt.com/docs/developer-commands) поддерживает
add/get/list/remove; текущий codex mcp add не предлагает cwd, поэтому использована
документированная конфигурация, чтобы сохранить точное рабочее окружение кандидата.

Добавлена единственная таблица в C:/Users/REX/.codex/config.toml:

```toml
[mcp_servers.wua_desktop_readonly]
command = "M:/GitHub/ag_llm/.venv/Scripts/python.exe"
args = ["-I", "-X", "utf8", "-B", "M:/GitHub/ag_llm/reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/plugin/server.py"]
cwd = "M:/GitHub/ag_llm/reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/plugin"
```

Все значения взяты из plugin/mcp.json; ${PLUGIN_ROOT} раскрыт в абсолютную папку
кандидата. Секретов и дополнительных разрешений в новой записи нет.
Техническое имя подключения — wua_desktop_readonly, MCP server name —
WUA Desktop Read-only v0.2.0. Это отдельная прямая регистрация: добавление
marketplace для неё не требуется и не выполнялось.

codex mcp get wua_desktop_readonly --json подтвердил enabled=true, stdio,
точные command/args/cwd. Регистрация не требует изменения существующего
плагина, vendor или production Web Alarm.

## Сохранность и откат

Прежние байты файла полностью сохранены как префикс новой конфигурации.
После удаления добавленной WUA-таблицы разобранные настройки полностью совпадают
с исходными, включая astro_modeler, gigachat_ultra и node_repl.
Базой была свежая конфигурация непосредственно перед записью, а не старый снимок
первой диагностики. Её SHA-256:

- before: b1f68a1c96da9f6329c5a5f9156b81255b2b695e4a1c8d9b7787d50dd7ce5ecc
- after: 514639478eb7678592b6330c7e6ad54113a5199e1c8fd78c24d0c499b14bd6db

Полная исходная конфигурация сохранена **вне репозитория**, чтобы не распространять
данные других подключений:

`C:/Users/REX/.codex/backups/CODEX-WUA-0-DESKTOP-MCP-E2E-001/20261016T093101Z-01d1331b/config.before.toml`

Рядом state.json и точные добавленные байты wua.appended.bin. В отчёте нет полного
содержимого пользовательской конфигурации.

rollback_stdio.py без параметров подтвердил готовность точного отката и ничего
не изменил. Если откат будет запрошен, агент может выполнить:

```powershell
& "M:/GitHub/ag_llm/.venv/Scripts/python.exe" -X utf8 -B "M:/GitHub/ag_llm/reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/rollback_stdio.py" --apply
```

Скрипт восстанавливает точные before-байты только если текущий файл совпадает с
сохранённым after. При последующих изменениях он откажется от записи, чтобы
сохранить чужие настройки. Реальный откат не выполнялся.

## Проверка трёх инструментов

registered_stdio_check_01.json: **PASS**, SDK запущен по зарегистрированным
command/args/cwd, протокол 2025-11-25. Выполнены настоящие вызовы ping,
list_capabilities и read_synthetic_context для synthetic_wua_desktop_001.
Все вернули успех; session_id и nonce согласованы, canonical context_sha256
совпал с ожидаемым серверным hash. Fixture storage не изменён, guard_denials=0.

SDK session: 328a038a85944102b345d25cddbfc102. Receipt:
evidence/328a038a85944102b345d25cddbfc102/session.json.
Имя клиента явно содержит WUA Local SDK Regression - Registered STDIO Diagnostic.
**Эти 3 вызова — SDK, не обычный ChatGPT Chat и не Desktop E2E.**

В текущем уже открытом агентском сеансе WUA-инструменты ещё не предоставлены.
После регистрации обычный Chat ещё не проверялся; прежний отрицательный gate
сохранён, настоящих вызовов из ordinary Chat по-прежнему 0.

## Что осталось пользователю

Пути и аргументы вводить не требуется. Следующее ручное действие:
в Settings → MCP servers нажать **Restart**, когда перезапуск безопасен для
текущей работы. Это шаг активации, прямо описанный в официальной MCP-документации.
Агент не перезапускал приложение/серверы и не автоматизировал UI.

Затем проверить настоящие вызовы из обычного Chat, используя запрос из
NEXT_MANUAL_GATE.md. Положительный результат только при реальных tools и
сверяемом server receipt. Если обычный Chat не видит tools, зафиксировать отсутствие;
не заменять результат успешным SDK или Work/Codex-сеансом.

Production, GitHub, сеть, VPN/proxy/firewall и системные права не менялись.
Публикация ON HOLD. Полная TASK ожидает Desktop gate; независимая приёмка
не объявляется. Старые отчёт/status/manifest сохранены в
checkpoints/pre_stdio_registration/.
