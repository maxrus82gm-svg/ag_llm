# Следующий gate после AMENDMENT 04

Кандидат WUA 0.2.1 локально готов, Gate A–D PASS. Отчёт:
amendment_04/report.md. DESKTOP E2E NOT VERIFIED.

Следующее необходимое решение — отдельное разрешение пользователя на установку
и активацию кандидата 0.2.1 в действующем Desktop. Сейчас этого разрешения нет;
установленный cache 0.2.0, config.toml, глобальный required и процессы не меняются.

После разрешённой активации нужны настоящие обычные ChatGPT MCP-вызовы ping,
list_capabilities, read_synthetic_context(synthetic_wua_desktop_001) и
read_synthetic_context(other_task). Независимый verifier сверяет receipt,
session_id/nonce/hash/call_id/storage и TASK_ID_DENIED. Local Codex, host RPC и SDK
не заменяют ordinary Chat. Git-публикация остаётся запрещена.
