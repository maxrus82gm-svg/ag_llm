# AM07 reference adapter — дизайн и граница

```text
synthetic client
  → 127.0.0.1:<owned CONNECT port>
  → adapter: exact *.invalid:port allowlist
  → ONLY 127.0.0.1:<one owned SOCKS5 fixture port>
  → SOCKS5 ATYP=3 domain; fixture maps synthetic name in memory
  → 127.0.0.1:<owned echo origin>
```

Все три сервиса в одном отдельном Python test process. Рабочий V2Ray не участвует.
`adapter.py` не имеет standalone/live entry point: запуск файла отказывается
устанавливать listener. Код импортируется только в контролируемый стенд.

## Инварианты прототипа

- `Config` frozen; upstream host **строго literal 127.0.0.1**, один порт. Никаких
  дополнительных endpoints, proxy discovery, environment lookup или defaults.
- Разрешены 1–16 точных authorities с ASCII LDH domain, суффиксом `.invalid`,
  явно заданным портом. Запрещены IP literals, real domains, userinfo/URLs,
  wildcard rules, trailing dots и неоднозначный authority syntax. Невалидная
  конфигурация отвергается до bind/connect. Listener bind только 127.0.0.1.
- Единственная outbound connect строка — `_socks()`: AF_INET/TCP socket на
  configured upstream. После любого error нет повторного connect, retry/direct
  fallback/альтернативного route. Закрываются обе стороны, upstream socket
  снимается с учёта даже при ошибке handshake.
- SOCKS5: NO AUTH method only; ver/method/reply RSV/REP/ATYP/length проверяются,
  short replies отвергаются. Destination всегда ATYP=3 с domain bytes; adapter
  не вызывает resolver. BND_ADDR в ответе IPv4/domain/IPv6 только считывается,
  никогда не используется как новая dial target.
- HTTP/1.1 CONNECT only. Метод/authority, ASCII/header syntax, duplicate headers,
  Host mismatch, body framing и уже считанный early tunnel data проверяются.
  Unknown destination →403, malformed →400, non-CONNECT →405, limit →431,
  header deadline →408; SOCKS refusal/protocol →502, timeout →504, capacity →503.
- Proxy-Authorization/Authorization не пересылаются в SOCKS и не логируются.
  После CONNECT stream opaque: TLS/token handling остаются клиенту. Никаких
  headers/body/error-message dumps; events только фиксированные коды/числа.

## Ресурсы и lifetime

Defaults: максимум 2 активных handlers (config max 8), headers 4096 bytes/24
fields (hard configurable caps 8192/64), request line 1024; handshake timeout
0.7s, relay idle 0.7s, max active duration 3s, combined tunnel byte budget 65536.
Тесты также используют меньшие bounded values. Backlog ограничен; при capacity
превышении новый worker не создаётся. Events capped 128. Каждый relay chunk ≤4096.

Отказ отправляется с write shutdown и drain ≤8192 bytes/30ms: это исправляет
обнаруженный Windows RST до чтения ответа 431/503. Drain не пересылается/не
логируется и не продлевается бесконечно. Это не общая HTTP proxy implementation.
EOF закрывает обе стороны; полноценный TCP half-close и production backpressure/
load/SLA не проверены. Все собственные threads недемонические, joined; `stop`
закрывает tracked sockets. Повторное использование stopped instance запрещено.

## Доказательство в стенде и его пределы

`test_adapter.py` включает до первого fixture socket Python audit hook. Bind —
только literal127/port0; socket type — IPv4 TCP; connect — только к сейчас
зарегистрированным owned ports и по ролям driver→adapter, adapter→SOCKS,
SOCKS→origin. DNS, UDP, subprocess, ctypes запрещены. Ports удаляются после
закрытия fixtures/reap. Это контроль **данного Python исходника**, не WFP, packet
capture, произвольного native кода или всех фоновых процессов Windows.

Socket audit фиксирует connect attempts, role/port/case. Успех подтверждается
реальным echo и совпадением physical peer port origin с outbound local port
SOCKS fixture. Ошибка без fault marker не становится PASS. Неожиданные fixture/
adapter errors, isolation violations и оставшиеся workers делают suite FAIL.

Отдельный negative quality control намеренно проходит local SOCKS fault →
**direct к собственному loopback origin**. Только роль mutant получает это
разрешение; oracle обязан обнаружить обход. В финальном trace один такой
intentional direct dial. В реальном adapter role direct dials **0**. Это не
реальный внешний bypass и не проверка proxy policy native Go клиента.

Становиться рабочим адаптером кандидат пока не может: надо определить применимые
native HTTP(S) paths, получить matching sources и разрешённую native isolation,
подтвердить live SOCKS/HTTP inbound/outbound/DNS, отдельно разрешить installation.
Текущий синтетический allowlist специально не допускает OpenAI/real destinations.
