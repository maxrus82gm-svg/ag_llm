# Gate A — official runtime source preflight

TASK: `CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001`; Codex 007; 2026-10-18.

**OFFICIAL SOURCE PACK BLOCKED. LOCAL SOURCE AUDIT PARTIAL.**

## Проверено локально

`local_file_inventory.json` сохраняет границы поиска: reports (глубина 12),
Downloads и attachments (5), стандартные каталоги VirtualBox/VMware/Hyper-V
(3–5). Не обходились reparse/offline entries, зависимости и `.git`;
68 вложенных каталогов reports отсечены по глубине. Это ограниченный поиск,
не утверждение об отсутствии архива на всех дисках. В пределах поиска нет
точного source archive; обнаруженный Windows ZIP содержит релизный бинарник,
а не подтверждённый runtime source pack.

Ожидаемый пользовательский пакет:

```text
Repository: openai/tunnel-client
Tag: v0.0.16
Commit (сообщён координатором): 5f99daabd4aa4a77049e6d81d54a0d8c18335397
File: tunnel-client-runtime-source-v0.0.16.tar.gz
Bytes: 239841
SHA-256: 88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0
```

[Официальный locator архива](https://github.com/openai/tunnel-client/releases/download/v0.0.16/tunnel-client-runtime-source-v0.0.16.tar.gz)
приведён только для идентификации. В этой TASK ссылка не открывалась;
скачивание, обращения к GitHub и установка зависимостей не выполнялись.

`provenance.json`: существующий EXE — 22,591,488 B,
SHA-256 `4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571`;
байтово равен единственному EXE того же имени в cached ZIP. ZIP — 28,122,468 B,
SHA-256 `edef7241b0c647fcb30f1a80ff376b6b25c51927960f257a3f01e21b17c2aba6`;
совпадает с cached metadata digest и cached SHA256SUMS. ZIP прочитан без
извлечения файлов. Commit literal находится по offset 11228448; version output
взятый из прошлого этапа явно помечен cached. В текущей TASK даже `--version`
не запускался. Подпись/независимый build attestation/reproducible build не
получены; provenance остаётся частичным. Совпадение этих связанных release
материалов не является несколькими независимыми доказательствами origin.

## Очередь точного source audit после передачи

Ниже имена, не изученные в этой TASK Go-исходники. Основания — binary path hints
из AM06 и source-only findings WEB_10 в документе 19, строки 17–19.
Все 88 выбранных path hints сохранены в `provenance.json`.

| Область | Обязательные файлы / селекторы | Что установить |
|---|---|---|
| Build и режимы | `go.mod`, `go.sum`, entrypoint `cmd/client`, startup wiring, build/release scripts при наличии | Реальная CLI/schema, defaults, conditional components, build inputs; нет auto-download |
| Конфигурация | `pkg/runtimeconfig/{config,profile,file_config,proxy,oauth_origins}.go` | Precedence global/component/env; validation; missing/invalid proxy; сохранение и перечитывание policy |
| Общий HTTP | `pkg/transport/{default,proxy}.go` | Все transports/dialers, explicit proxy vs env, redirects, bypass/fallback, resolver, timeouts |
| Control-plane | `pkg/controlplane/internal/{tunnel_service_client,poller,retry_after,roundtripper,routing,command_parser}.go` | Main/secret clients, retries/redirects, endpoint injection, managed commands, credential-free fake mode |
| MCP | `pkg/mcpclient/{fxmodule,channel_transport_factory,transport_provider,transport_provider_fx,stdio_command,stdio_command_factory}.go`, `internal/roundtripper.go`, forwarding/shared transports | HTTP/Unix/STDIO branches; child environment, spawn, descendants, inherited network behavior |
| OAuth | `pkg/oauth/{module,resource_meta,auth_meta,discovery_origin,discovery,discovery_retry_policy,hostbundle,state}.go` | Discovery origins, token/resource calls, redirects/retries, browser spawning/callbacks, secret redaction |
| Harpoon | `pkg/runtimeharpoon/{fxmodule,shared_wiring,host_registration,registry,server,discovery_budget,health}.go`, `hostbus/hostbus.go`, `internal/hostclassifier/classifier.go`, `pkg/harpoon/{server,fxmodule,registry}.go` | TCP/HTTP/IPC branches, host relay, environment, discovery, hidden transports |
| Proxy-health | `pkg/proxyhealth/{checker,health,metrics}.go` | Probe destinations, failure transitions, independent transports, whether health loss changes route |
| Optional child | `pkg/cloudflared/runtime/supervisor.go` и его callers/config/token resolution | Полное исключение запуска или отдельное включение exact EXE в контракт; Go proxy callback не наследуется дочерним EXE |
| DNS и альтернативы | Поиск по **всему** проверенному source tree: `net.Dial`, `DialContext`, `Resolver`, `Lookup*`, `http.Client`, `Transport`, `ProxyFromEnvironment`, `os/exec`, `StartProcess`, UDP/QUIC/WebSocket, redirects и retry loops | Не ограничиваться списком известных файлов: проследить constructors → callers → lifetime → shutdown, vendored/embedded assets и Go stdlib/dependencies |

Точные filenames entrypoint и дополнительных callers пока нельзя подтвердить
без архива. Go stdlib версии сборки и module dependency source тоже нужны offline;
`go.sum` подтверждает module bytes только при фактической проверке, не доставляет их.
WEB_10 ранее сообщил HTTP/HTTPS-only explicit proxy validation; без полного
аудита нельзя переносить этот вывод на все пути клиента или объявлять SOCKS5
native поддержанным. HTTP CONNECT→SOCKS5 AM07 остаётся reference-кандидатом.

## Минимальная безопасная передача

Пользователь через свой разрешённый канал получает точный архив и кладёт обычный
локальный файл в `reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/source_input/`;
не присылает ключи, токены, профили туннеля или собственные конфиги. Агент затем
сверяет размер и SHA-256 с закреплёнными выше, не запускает код/сборку.
При несовпадении — STOP, исходный файл сохраняется, причина фиксируется.
Перед будущим чтением tar: ограничить compressed/uncompressed bytes, число
entries и размер каждого; отвергнуть absolute/drive/UNC/`..`/duplicate paths,
symlink/hardlink/device/FIFO и опасные Windows names/streams. Читать text members
в памяти либо извлекать только обычные файлы в новую TASK-owned папку после
такой проверки. Не применять безусловный `extractall`.

Отдельно запросить официальное build attestation либо полную offline build chain
и сравнение результата. Если этого нет, источник может быть проверен по hash,
но source→EXE correspondence сохраняет явное ограничение. VM-исследование ниже
продолжено независимо от отсутствующего пакета.
