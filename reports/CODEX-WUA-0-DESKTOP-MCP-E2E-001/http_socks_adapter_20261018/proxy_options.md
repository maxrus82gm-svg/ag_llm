# HTTP inbound или HTTP CONNECT → SOCKS5

| Вариант | Совместимость и стоимость | Что подтверждено | Решение AM07 |
| --- | --- | --- | --- |
| Уже существующий HTTP/mixed inbound sing-box | Наименьшее число компонентов; HTTP proxy должен обслуживать CONNECT для HTTPS и, если требуется, absolute-form HTTP | Текущие listen sockets принадлежат sing-box, но протокол и loaded config не установлены | Предпочтительный будущий вариант **после** read-only подтверждения; использовать сейчас нельзя |
| Отдельный HTTP CONNECT → SOCKS5 adapter | Добавляет процесс, ресурсы, lifecycle; может принудительно закрепить ровно один upstream | Синтетический Python reference: 36/36 PASS, strict synthetic allowlist, domain ATYP=3, без DNS/direct/retry/fallback | **Выбранный проверяемый кандидат AM07**, только в собственном стенде; не развёрнут |
| Включить новый mixed inbound в V2Ray | Потребует изменения работающей конфигурации/возможного restart | Не разрешено | NOT RUN; не предлагается как текущая операция |
| Подать socks5:// напрямую tunnel-client | Официальный tag parser по независимому WEB_10 source review требует http/https | Поддержка SOCKS в стандартном Go transport не отменяет application parser | Не выбран; локальная native ветвь отказа не исполнялась |
| Запустить native клиент с proxy environment и надеяться на V2Ray | Не закрывает defaults/NO_PROXY/дочерние/native transports | Нет process-wide egress proof | Не выбран, native gate BLOCKED |

## Gate A — что известно о рабочем V2Ray

Сохранённый AM05: 10808 и 10813, SOCKS5 method greeting на 10808 → 05 00;
GUI inbound SOCKS, proxy domain rules, configured DNS. Эти данные исторические и
не являются доказательством загруженной конфигурации или выбранного outbound.

Текущий AM07 snapshot: V2RayN PID 18032 → sing-box PID 27008; listen sockets
**127.0.0.1:10808 и 127.0.0.1:10814**. 10813 в этом snapshot не обнаружен.
ExecutablePath/CommandLine текущих процессов через разрешённый read-only CIM
недоступны (null). Причина недоступности не установлена; права не повышались.
Поэтому фактический `-c`/cwd/loaded config не прочитан. `config_candidates=[]`
не означает, что у процесса нет config. Статус HTTP/mixed inbound **NOT VERIFIED**.

Remote outbound selection, DIRECT rules в действующем runtime, proxy-side DNS,
Windows/native DNS и failure policy **NOT VERIFIED**. Ни одного CONNECT/greeting/
DNS/HTTP запроса через live V2Ray в AM07 нет; никакого fault injection на нём.

## Ограничения выбранного кандидата

Прототип поддерживает **только HTTP/1.1 CONNECT** и только синтетические
`.invalid` authorities. Обычный HTTP proxy absolute-form GET/POST возвращает 405.
Следовательно, он пока **не drop-in HTTP proxy для всех control-plane/MCP/OAuth/
Harpoon/proxy-health путей**. Нужно сначала установить точный набор транспорта
native клиента. Он также не поддерживает SOCKS auth, TLS до proxy, production
auth/observability/deployment, real destinations и полноценные TCP half-close.
EOF закрывает обе стороны, а tunnel lifetime/bytes намеренно ограничены.

HTTP CONNECT adapter сам по себе не ограничивает сеть tunnel-client. Даже идеально
закреплённый upstream адаптера не запрещает native клиенту обойти адаптер. Нужны
отдельные proof каждого applicable transport и enforceable native egress boundary.
Неизвестный live SOCKS/mixed upstream тоже может выбирать DIRECT; reference PASS
не проверяет его remote policy.
