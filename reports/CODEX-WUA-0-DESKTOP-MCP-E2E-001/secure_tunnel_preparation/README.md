# WUA Secure MCP Tunnel — активация отложена пользователем

**DESKTOP E2E NOT VERIFIED. V2RAY ROUTE NOT VERIFIED. PROXY FAIL-CLOSED NOT VERIFIED.**

Действующий туннель пока не создавать и не запускать. Пользователь ещё не проверял
Platform Tunnels и не имеет подтверждённого tunnel_id. После проверки следующий
этап согласуется отдельно. API-ключи в чат не передаются.

Обязательное условие: все внешние соединения tunnel-client только через V2Ray;
при отказе прокси — отсутствие прямого выхода. Поддержка proxy flags найдена,
но фактический маршрут и fail-closed не доказаны. Прежний launcher не закреплял
прокси явно; в текущем процессе переменные HTTP(S)_PROXY отсутствуют. Работающий
V2RayN и loopback-порты сами по себе маршрут не подтверждают.

`Start-WUA-Tunnel.cmd` сейчас ведёт к безусловному отказу
`HOSTED_TUNNEL_ON_HOLD_BY_USER` до чтения секретов и создания процесса. Обходного
флага нет. До отдельно согласованного этапа запуск не выполнять.

Полный план proxy gates: `../v2ray_proxy_constraints_20261016/report.md`.
Текущий gate: `../NEXT_MANUAL_GATE.md`.

Сохранены официальный tunnel-client v0.0.16 и его проверенные hashes, WUA 0.2.1,
неизменённый YAML-шаблон и предыдущие evidence. Шаблон пока не утверждён для
V2Ray-only запуска. Его параметры не изменялись этим этапом. Не регистрировались
новые ChatGPT-подключения и облачные ресурсы; глобальные настройки не менялись.

Сохранённый `local_bridge_test/` подтверждает четыре RPC через официальный
localhost dev proxy: три OK и TASK_ID_DENIED, один receipt, неизменность данных
и ноль guard violations. Стенд остановлен. Этот PASS не проверял V2Ray, hosted
control plane или обычный ChatGPT. Будущая hosted evidence-папка остаётся пустой.

[OpenAI: Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
Предыдущая инструкция и launcher сохранены как исторические артефакты в
`../v2ray_proxy_constraints_20261016/before/`; они не являются разрешением запуска.
