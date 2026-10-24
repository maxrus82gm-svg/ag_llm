# Source call graph — граница известного и отсутствующего

**BLOCKED / DOWNLOAD_GO_REQUIRED.** Это карта делегирования в сохранённом sing-box, не реализация sing и не доказательство runtime.

## Точные локальные locators

| Файл | Функция | Строка | Наблюдаемый вызов |
| --- | --- | --- | --- |
| `go.mod` | `require` | 36 | `github.com/sagernet/sing v0.8.3-0.20260315153529-ed51f65fbfde` |
| `go.sum` | `checksum` | 239 | `github.com/sagernet/sing v0.8.3-0.20260315153529-ed51f65fbfde h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=` |
| `protocol/http/inbound.go` | `NewInbound` | 43 | `authenticator: auth.NewAuthenticator(options.Users),` |
| `protocol/http/inbound.go` | `NewInbound` | 41 | `router:        uot.NewRouter(router, logger),` |
| `protocol/http/inbound.go` | `Inbound.NewConnectionEx` | 99 | `err := http.HandleConnectionEx(ctx, conn, std_bufio.NewReader(conn), h.authenticator, adapter.NewUpstreamHandlerEx(metadata, h.newUserConnection, h.streamUserPacketConnection), metadata.Source, onClose)` |
| `protocol/http/inbound.go` | `Inbound.newUserConnection` | 106 | `func (h *Inbound) newUserConnection(ctx context.Context, conn net.Conn, metadata adapter.InboundContext, onClose N.CloseHandlerFunc) {` |
| `protocol/http/inbound.go` | `Inbound.streamUserPacketConnection` | 120 | `func (h *Inbound) streamUserPacketConnection(ctx context.Context, conn N.PacketConn, metadata adapter.InboundContext, onClose N.CloseHandlerFunc) {` |
| `option/options.go` | `Options.UnmarshalJSONContext` | 30 | `decoder := json.NewDecoderContext(ctx, bytes.NewReader(content))` |
| `option/options.go` | `Options.UnmarshalJSONContext` | 31 | `decoder.DisallowUnknownFields()` |
| `cmd/sing-box/cmd_run.go` | `readConfigAndMerge` | 112 | `mergedMessage, err = badjson.MergeJSON(globalCtx, options.options.RawMessage, mergedMessage, false)` |

SHA файлов и exact source root — `evidence/source_boundary.json`. Все шесть соответствуют прежнему tree manifest; это не новый приёмочный verdict.

## Не замкнутые ветви

HTTP TCP/TLS inbound → внешний sing `http.HandleConnectionEx` (CONNECT parsing/auth UNKNOWN) → `adapter.NewUpstreamHandlerEx` callbacks → newUserConnection → uot router → sing-box route. Packet callback существует отдельно. Auth factory передаётся handler; enforcement до dial пока не установлен.

JSON: sing-box `Options.UnmarshalJSONContext` → внешний sing JSON decoder (unknown/null/types/duplicate keys semantics UNKNOWN) → `checkOptions`. CLI `readConfigAndMerge` → внешний `badjson.MergeJSON` → options. Внутренние тела sing отсутствуют в разрешённом материале.

После exact module archive/h1 нужно раскрыть методы, authority/port/IPv4/IPv6, early EOF, malformed input, auth reject-before-dial, alternative handlers, nested JSON/defaults/merge/reload и transitives. Go стандартная библиотека и прочие dependencies не считаются автоматически закрытыми.
