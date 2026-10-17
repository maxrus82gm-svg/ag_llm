# MANUAL ENGINEERING REVIEW — AMENDMENT 05

Codex 007; отдельный source/adversarial review сверх автоматического результата.
Итог: **reference stand пригоден как изолированный доказательный инструмент;
нативный tunnel-client и live remote route НЕ VERIFIED**.

## Проверенные ветви и границы

- `preflight.py`: process/PID/listener correlation, поиск process -c argument,
  различение абсолютного и относительного пути, отказ выдавать неподтверждённую
  копию config за active. Config содержимое не попало в raw output. Старый helper
  SyntaxError зафиксирован, устранён в собственном scope.
- `gui_policy.py`: выбор только разрешённых GUI/DB полей; DB ro+immutable,
  query_only, hashes до/после. IndexId используется только локально для SELECT
  двух numeric type columns; пароль/username/subscription/remote Address не SELECT.
  IsActive относится к сохранённому GUI snapshot. Нет аттестации loaded runtime.
- `isolated_proxy_suite.py::audit`: все connect/bind/getaddrinfo идут через
  Python socket в этом исходнике. Literal 127.0.0.1 и текущие собственные порты;
  hostname resolution и subprocess запрещены. Это не WFP/packet capture и не
  policy для arbitrary native/C/Go code.
- TLS fixture: private key только TEMP, собственное доверие только в client
  SSLContext; системные CA не меняются. Accept handshake и handler I/O ограничены
  timeout. Threads недемонические и join на server_close; serving thread также join.
- `ReferenceProxyOnlyClient`: require explicit owned proxy, reject conflicting
  component override/extra transport; destination проверяется до DNS/connect.
  Новый HTTPSConnection на тот же proxy для каждого retry/redirect; direct fallback
  отсутствует по source. Это проект модели, не reverse-engineered Go implementation.

## Реальные failure paths эталонной модели

1. **Не слушающий порт:** порт сохраняется bound собственным socket, но listen
   отсутствует; исключено случайное использование чужого сервера. На этой Windows
   наблюдался TimeoutError, а не обязательный ECONNREFUSED. Проверяется отсутствие
   origin request/direct attempt, не конкретный угаданный WinError.
2. **503 и accept/close:** fault markers фиксируют достижение proxy handler;
   CONNECT failure/RemoteDisconnected не приводят к origin. Ошибка не подменяется
   успешным пустым ответом.
3. **Timeout:** proxy действительно принял CONNECT и удерживал ответ до собственного
   release/ограниченного ожидания. Клиент получил timeout; отсутствие успеха само
   по себе недостаточно — дополнительно проверяются connect trace и origin.
4. **Успех→disconnect→retry:** первый TLS request достигает origin. Второй и retry
   достигают двух специально закрытых CONNECT, новых origin requests нет. Raw
   markers отделяют достигнутую fault phase от wall-clock предположения.
5. **Redirect:** origin redirect на второй собственный origin снова требует pinned
   proxy. CONNECT 302 не рассматривается как разрешение изменить transport. Эта
   проверка не охватывает Go redirect/auth header policy и произвольные HTTPS domains.
6. **TLS refusal:** client context без trust anchors отвергает self-signed fixture
   после CONNECT. Один ConnectionResetError fixture proxy при peer rejection
   разрешён именно в S15; иные fixture errors делают тест красным. Не используется
   blanket «любой exception допустим».
7. **Configuration guard:** для отсутствующего proxy, конфликтующего component
   override, hostname и extra transport проверяется точный PolicyError code до
   socket activity. Isolation errors нельзя засчитать как ожидаемый policy PASS.

## Quality controls и найденные пробелы harness

- Начальная Q01 проверяла прямой обход без предварительного отказа. Review усилил
  её до real proxy accept/close → catch → intentional direct origin; oracle обязан
  отвергнуть путь. Первоначальные 18/18 сохранены как более узкая ревизия.
- Q02 проверяет стандартный Python proxy_bypass_environment с NO_PROXY=* и затем
  намеренный direct путь. Это положительный контроль способности oracle обнаружить
  bypass, а не доказательство поведения Go/Windows environment.
- Review нашёл растущий allowlist закрытых портов. Финал удаляет proxy/reservation/
  origin ports после закрытия; итоговый OWN_PORTS пуст. Это устраняет возможность
  позднего обращения к уже переиспользованному чужому порту.
- Daemon handler threads заменены на bounded joined handlers. TLS accept получил
  собственный timeout. После final cleanup нет оставшихся serving/handler threads,
  TEMP удалён. При boundary attempt тест останавливается с безопасным checkpoint.
- Origin oracle сопоставляет physical peer port с proxy forward socket, поэтому
  подставленный заголовок не может сам по себе доказать proxy path.
- Неожиданные fixture exceptions учитываются отдельно; финал имеет 1 ожидаемый
  TLS reset и 0 неожиданных. Первичные snapshots/stdout/stderr не удалены.

## Что этими тестами НЕ доказано

- NO_PROXY cases reference client передают словарь политике, которая по контракту
  использует explicit proxy. Они не меняют системное окружение и не исполняют
  native Go resolution/precedence. DNS case отвергает hostname до resolver, поэтому
  **нет доказательства** разрешения api.openai.com через V2Ray или remote DNS.
- Extra transport case проверяет reject в reference constructor; QUIC, SOCKS UDP,
  Cloudflared, Harpoon/OAuth не выполнялись. Это не тест их native кода.
- Совпадение целевых адресов с 127.0.0.1, audit events и source review достаточны
  для этого ограниченного Python стенда. Нет непрерывного OS packet capture,
  native-process egress deny или доказательства всего фонового трафика компьютера.
- GUI policy может отличаться от загруженного core. Внешний IP, SOCKS greeting,
  CONNECT или активный процесс не доказывают выбранный remote proxy outbound.
- Проверенный localhost MCP bridge прошлого этапа использовал тот же официальный
  бинарник, но не fault injection прокси. Его 4 MCP calls нельзя засчитать здесь.

## Решение по настоящему клиенту и альтернативы

Справка native dev proxy доступна; запуска real transport в этом этапе не было.
Возможные alternative paths рассмотрены:

1. Только loopback CLI flags + краткий TCP snapshot — недостаточно для гарантии
   отсутствия native background/default/redirect paths и коротких UDP/DNS попыток.
2. Python audit в родительском wrapper — не наследуется Go process и не решает задачу.
3. Изменение рабочего V2Ray/firewall/TUN/permissions — запрещено AMENDMENT и не сделано.
4. Выдать reference simulator за tunnel-client — недопустимо; статусы раздельны.
5. Exact official transport source pack + отдельная проверка действительно contained
   offline режима — предпочтительный следующий безопасный исследовательский шаг.
   Если этого недостаточно, process/container isolation требует отдельного согласования.

Не установлена невозможность безопасного native offline теста вообще. Установлен
конкретный текущий evidence gap, из-за которого его запуск не был обоснован.
Восемь native fault groups BLOCKED. Общий результат AM05 — PARTIAL, без снятия hold,
без hosted key/tunnel, без повышения ordinary Chat E2E и без независимой self-acceptance.
