# Proxy implementation audit — PARTIAL

Основания: байты EXE с фиксированным SHA-256; Go build info, pcHeader/funcnametab/
filetab, встроенный текст документации и error literal; прежние локальные CLI helps.
Метаданные извлечены `static_audit.py` без исполнения EXE. Имена функций не являются
телами функций, call graph или доказательством runtime-порядка. Ниже **не source
review завершённого transport-кода**: исходников этого build в доступном pack нет.

| Путь | Найдено в самом установленном бинарнике | Что ещё необходимо проверить |
| --- | --- | --- |
| Общий transport | `pkg/transport.ApplyProxy`, `CloneDefault`; paths `transport/default.go`, `transport/proxy.go` | Фактическое присваивание Transport.Proxy/DialContext, nil/default/Unix branches, наследование настроек |
| Выбор маршрута | `pkg/proxy.ResolveRoute`, `NormalizeProxyURL`, `envProxyForURL`, `proxyBypassHost`, `hostPortMatch` | Explicit/ambient precedence, bypass для loopback/hostname/IP, ошибки parse и пустые значения |
| Config/environment | `runtimeconfig.resolveProxyFlag`, `resolveProxyWithFallback`, `parseProxyReference`, `parseHTTPProxyURL`, `lookupEnvWithFileValues` | Полные flags/env/YAML/per-binding правила; `env:`/file resolution; означает ли отсутствие значения default route |
| Control-plane | `buildControlPlaneHTTPTransport`, `buildSecretControlPlaneHTTPTransport`, `controlPlaneUsesProxy`; poller, retry_after, roundtripper и routing source paths | Poll/metadata/response/admin clients, secret-specific transports, redirects, reconnect, bounded retry и любой alternate endpoint |
| MCP HTTP | `ChannelTransportFactory.HTTPClientForBinding`, `runtimeHTTPClientForBinding`, `httpClientForKey`, `withRuntimeMCPRedirectPolicy`, `runStartupProbeWithRetry` | Различия startup/runtime/SDK clients, per-channel proxy, redirect/auth headers, SSE/Streamable reconnect |
| MCP STDIO | `stdio_command.go`, `stdio_command_factory.go`, serialized/shared forwarding transports | Сам transport не HTTP; child process может иметь собственную сеть — его тоже должна охватывать изоляция |
| Harpoon | `runtimeharpoon.Server.redirectPolicy`, `normalizeRedirects`, `WithHTTPTransport`, `RegisterAdditionalTransport`, discovery/host registration paths | Target-specific HTTP clients, callout/discovery, additional/Unix transports, inherited proxy и новые redirect hosts |
| OAuth | `withSameOriginRedirects`, `discoveryOriginTransport.RoundTrip`, `doWithRetryForTimeout`, `startOAuthDiscoveryWithRetryPolicy` | Какой HTTP client используется для resource/auth metadata, trusted origins, discovery/retry и любых token/JWKS путей; наличие dependency не доказывает их активацию |
| DNS | Go `net.(*Resolver).dial`, `lookupIPAddr`, `lookupIP`; HTTP `socksDialer` и `Transport.dialConn` | Где разрешаются target/proxy hosts, IPv4/IPv6/Windows resolver, direct UDP/TCP DNS, background/child resolution |
| Proxy health | `proxyhealth.Checker.checkProxyRoute`, `connectThroughProxyWithTLSConfig`, `dialTCP`, `recordDirect`, `buildRoutes` | Отличить bookkeeping от dial; установить destinations/interval/TLS и сеть health checker вне основных HTTP клиентов |
| Retries/redirects/fallback | Собственные retry/redirect functions в control-plane/MCP/OAuth/Harpoon и стандартный net/http | Нужны тела всех ветвей и contained runtime faults; одно имя с fallback/direct не доказывает сетевой bypass |
| Optional companion | `cloudflared/runtime/supervisor.go`, runtime adapter и manifest; отдельный cloudflared.exe в ZIP | Даже доказательство proxy policy главного Go EXE не переносится на companion. Companion здесь не запускался |

## Explicit proxy и NO_PROXY: новый факт, ограниченный уровень доказательства

Встроенный раздел `## Outbound proxy environments` извлечён прямо из EXE, offset
10349107 (точное значение хранится в `binary_excerpts.json`). Он заявляет:
явные proxy flags переопределяют environment и игнорируют NO_PROXY для затронутых
targets; при отсутствии explicit proxy действуют HTTP_PROXY/HTTPS_PROXY/NO_PROXY.
Перечислены global, control-plane, MCP/per-channel и Harpoon flags.

Это официальный **встроенный контракт данного поставленного артефакта**, а не
доказанный вызов ApplyProxy и не native fault result. AM05 не мог установить эту
семантику из одних CLI flags; AM06 нашёл её в сохранённых байтах. Проверить реальное
соблюдение ещё предстоит. Семантика ALL_PROXY здесь не заявлена и не угадана.

## SOCKS5 против HTTP CONNECT

Найдены `runtimeconfig.parseHTTPProxyURL`, `proxy.parseProxyURL` и error literal:
`proxy URL scheme must be http or https, got %q` (offset 10154413). Поэтому
обоснованный поддерживаемый контракт кандидата — **HTTP(S) proxy**, для HTTPS
target с CONNECT. Прямой `socks5://`/`socks5h://` не считать поддержанным решением
без соответствующей проверки валидатора. В EXE одновременно есть стандартный
`net/http.(*socksDialer)`; это не отменяет ограничений конфигурации приложения.
Саму ветвь отказа SOCKS URL в этом этапе не исполняли.

Если live inbound V2Ray предоставляет только SOCKS5, потребуется уже разрешённый
HTTP CONNECT inbound либо отдельный локальный адаптер HTTP CONNECT → SOCKS5.
Если существующий порт mixed и принимает CONNECT, адаптер может не потребоваться.
AM05 доказал только SOCKS greeting на 10808; здесь live listener не трогали.
Нельзя произвольно заменить схему этого адреса на http://. Адаптер не создан;
его собственные DNS/retries/fallback и дочерние пути тоже потребуют проверки.

## Ошибки интерпретации, которые исключены review

- `resolveProxyWithFallback` может означать наследование config. Тело отсутствует;
  это **не доказательство** «после сетевого отказа клиент идёт direct».
- `recordDirect` в proxyhealth может описывать классификацию маршрута. Это
  **не доказательство** попытки прямого подключения при сбое proxy.
- Наличие `ProxyFromEnvironment`, SOCKS и DNS symbols не доказывает, какой client
  вызывает их при explicit proxy и какой branch исполняется после отказа.
- Documented ignore-NO_PROXY не гарантирует покрытие всех будущих targets,
  дополнительных transports или стороннего companion.

Итог: **SOURCE AUDIT PARTIAL**. Идентичность и адресная карта binary paths
установлены; тела transport-кода, соответствие source↔binary и native fallback
semantics — **BLOCKED / NOT PROVEN**, без утверждения о дефекте самого клиента.
