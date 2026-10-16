# Текущий gate: Tunnels и обязательный V2Ray

**HOSTED TUNNEL ON HOLD BY USER. DESKTOP E2E NOT VERIFIED.**
**V2RAY ROUTE NOT VERIFIED / PROXY FAIL-CLOSED NOT VERIFIED.**

Пользователь ещё не проверял OpenAI Platform Tunnels; подтверждённого tunnel_id нет.
Он проверит доступ самостоятельно. После результата следующий этап согласуется
отдельно. API-ключи в чат не передаются.

До согласования действующий туннель не создавать и не запускать. Не менять
config.toml, рабочие MCP-подключения, WUA, сеть, V2Ray, firewall, proxy, DNS или права.
Получение tunnel_id само по себе не снимает это ограничение.

Полный текущий план и пределы доказательств:
`v2ray_proxy_constraints_20261016/report.md`.

В будущем до активации обязательны два отдельных подтверждения:

1. Все внешние соединения tunnel-client явно направлены через существующий
   подтверждённый V2Ray inbound, а V2Ray передаёт OpenAI через нужный proxy outbound.
2. При отказе прокси отсутствуют прямые попытки выхода, DNS/дополнительные transports
   и fallback. Нужна проверка startup, polling, RPC, reconnect и отказа; одного
   listener, внешнего IP или значения HTTPS_PROXY недостаточно.

Проверки пока не выполнялись. Текущая документация содержит предложение штатного
параметра --http-proxy, но конфигурация не применена. Prepared launcher с --start
безусловно отказывает до credentials/Popen. Прежнюю инструкцию запуска не выполнять.

После отдельного согласования и прохождения proxy gates остаётся настоящий ordinary
Chat gate: ping, list_capabilities, read_synthetic_context с
fixture_id="synthetic_wua_desktop_001", затем fixture_id="other_task" с TASK_ID_DENIED.
Независимый verifier должен сверить исходные ответы и серверный receipt. До этого
ordinary Chat — 0 calls, DESKTOP E2E NOT VERIFIED. Старый localhost bridge PASS
сохраняется и не является доказательством V2Ray или ordinary Chat E2E.
