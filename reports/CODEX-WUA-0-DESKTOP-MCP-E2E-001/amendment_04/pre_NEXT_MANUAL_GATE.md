# Следующий gate после AMENDMENT 03 — предложение, не исполнение

DESKTOP E2E NOT VERIFIED. Действует READ-ONLY DIAGNOSTICS.
Прежняя инструкция Restart временно не применяется: пользователь прямо запретил
перезапуск ChatGPT Desktop и существующих MCP-процессов без согласования.

Уже подтверждено: четыре настоящих native MCP-вызова текущего local Codex,
включая TASK_ID_DENIED для other_task. Полный отчёт A–E и evidence —
amendment_03_diagnostics/report.md.

## Минимальная следующая проверка CLI, после отдельного разрешения

Новый независимый CLI-run с единственным временным override
mcp_servers.wua_desktop_readonly.required=true, sandbox read-only и --ephemeral.
Команда приведена в разделе D отчёта. Она здесь не запускалась.
Не меняет постоянный config.toml/регистрацию и не перезапускает существующие
процессы. Цель — проверить старт WUA до построения каталога tools.

Нужны настоящий initialize/tools-list trace, JSON tool-call events и server receipt;
сообщение модели об отсутствии tools само по себе не является raw catalog.
Выдержка для отчёта содержит только WUA и не включает secrets других серверов.

## Ordinary Chat gate

В обычном ChatGPT-чате запросить настоящие MCP-вызовы:

```text
Вызови доступные MCP-инструменты WUA Desktop Read-only: ping, list_capabilities,
read_synthetic_context(fixture_id="synthetic_wua_desktop_001"), затем
read_synthetic_context(fixture_id="other_task"). Используй реальные имена
инструментов, предоставленные этому чату. Покажи session_id, nonce,
context_sha256, proof_path и настоящий код отказа для other_task.
Если tools недоступны, сообщи об этом без SDK, терминала или имитации.
```

Фиксировать фактический режим/время/host, затем независимый verifier сверяет
receipt, call_id/nonce/hash/storage и код TASK_ID_DENIED. Local Codex или SDK
не заменяют ordinary Chat. Никакой перезапуск, установка, изменение permissions
или сети этой инструкцией не разрешаются.
