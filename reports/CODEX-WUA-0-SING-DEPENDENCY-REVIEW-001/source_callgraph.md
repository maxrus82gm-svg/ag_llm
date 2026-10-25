# Source call graph — bounded dependency review

Exact source roots/hashes: amendment_01/evidence/source_locators.json. Module ZIP h1 is verified; native execution is NOT RUN.

HTTP: sing-box Inbound.NewConnectionEx → sing ReadRequest (linkname Go net/http.readRequest; stdlib gap) → enabled auth Verify/407 → SourceAddress → CONNECT/Upgrade/plain HTTP → upstream callback → parent newUserConnection → UoT router → sing-box route/dial. CONNECT 200 precedes callback; nil authenticator skips verification. Plain HTTP uses injected pipe/callback, not the separate http.Client nil-dialer default.

JSON: CLI readConfigAt → UnmarshalExtendedContext(CommentFilter) → context Decoder.Decode → parent Options.UnmarshalJSONContext → DisallowUnknownFields/decode/checkOptions. Nested inbound registry → badjson.UnmarshallExcludedContext → context unknown-field decoder. Multi-file path sort → MergeJSON → recursive object/append merge → Options decode. Reload can recreate service; protected admission is not implemented by these source calls.

| Snapshot / file | Function | Line | ID / anchor |
| --- | --- | --- | --- |
| sing/protocol/http/handshake.go | HandleConnectionEx | 33 | http_read: `request, err := ReadRequest(reader)` |
| sing/common/auth/auth.go | NewAuthenticator | 15 | auth_factory: `if len(users) == 0 {` |
| sing/common/auth/auth.go | NewAuthenticator | 16 | auth_factory: `return nil` |
| sing/common/auth/auth.go | NewAuthenticator | 29 | auth_factory: `return ok && common.Contains(passwordList, password)` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 37 | auth_guard: `if authenticator != nil {` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 50 | auth_guard: `authOk = authenticator.Verify(username, password)` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 56 | auth_guard: `if !authOk {` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 59 | auth_guard: `request, http.StatusProxyAuthRequired,` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 44 | auth_codec: `strings.HasPrefix(authorization, "Basic ")` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 45 | auth_codec: `base64.URLEncoding.DecodeString(authorization[6:])` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 66 | auth_error_disclosure: `", password=", password` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 68 | auth_error_disclosure: `Proxy-Authorization=", authorization` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 79 | connect_target: `if request.Method == "CONNECT" {` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 80 | connect_target: `M.ParseSocksaddrHostPortStr(request.URL.Hostname(), request.URL.Port()).Unwrap()` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 81 | connect_target: `if destination.Port == 0 {` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 89 | connect_dispatch: `200 Connection established` |
| sing/protocol/http/handshake.go | HandleConnectionEx | 104 | connect_dispatch: `handler.NewConnectionEx(ctx, requestConn, source, destination, onClose)` |
| sing/protocol/http/handshake.go | HandleConnectionEx/handleHTTPConnection | 106 | http_alternates: `strings.ToLower(request.Header.Get("Connection")) == "upgrade"` |
| sing/protocol/http/handshake.go | HandleConnectionEx/handleHTTPConnection | 136 | http_alternates: `err = handleHTTPConnection(ctx, handler, conn, request, source)` |
| sing/protocol/http/handshake.go | HandleConnectionEx/handleHTTPConnection | 180 | http_alternates: `return http.ErrUseLastResponse` |
| sing/protocol/http/handshake.go | HandleConnectionEx/handleHTTPConnection | 172 | http_alternates: `go handler.NewConnectionEx(ctx, output, source, M.ParseSocksaddr(address).Unwrap()` |
| sing/protocol/http/addr.go | SourceAddress | 12 | source_override: `request.Header.Get("X-Forwarded-For")` |
| sing/protocol/http/addr.go | SourceAddress | 17 | source_override: `address.Addr = originAddr` |
| sing/common/metadata/addr.go | ParseSocksaddrHostPortStr | 227 | port_cast: `port, _ := strconv.Atoi(portStr)` |
| sing/common/metadata/addr.go | ParseSocksaddrHostPortStr | 232 | port_cast: `Port: uint16(port)` |
| sing/protocol/http/link.go | ReadRequest | 10 | stdlib_link: `//go:linkname ReadRequest net/http.readRequest` |
| sing/protocol/http/client.go | NewClient/DialContext | 49 | client_system_default: `if options.Dialer == nil {` |
| sing/protocol/http/client.go | NewClient/DialContext | 50 | client_system_default: `client.dialer = N.SystemDialer` |
| sing/protocol/http/client.go | NewClient/DialContext | 106 | client_system_default: `base64.StdEncoding.EncodeToString([]byte(auth))` |
| sing/common/json/context.go | build-selected aliases | 1 | json_build: `//go:build go1.20 && !without_contextjson` |
| sing/common/json/context.go | build-selected aliases | 6 | json_build: `github.com/sagernet/sing/common/json/internal/contextjson` |
| sing/common/json/std.go | alternative aliases | 1 | json_std_build: `//go:build !go1.20 &#124;&#124; without_contextjson` |
| sing/common/json/std.go | alternative aliases | 5 | json_std_build: `import "encoding/json"` |
| sing/common/json/unmarshal.go | UnmarshalExtendedContext | 18 | json_extended: `NewCommentFilter(bytes.NewReader(content))` |
| sing/common/json/unmarshal.go | UnmarshalExtendedContext | 20 | json_extended: `err := decoder.Decode(&value)` |
| sing/common/json/internal/contextjson/decode.go | decodeState.object | 744 | json_unknown: `f = fields.byFoldedName[string(foldName(key))]` |
| sing/common/json/internal/contextjson/decode.go | decodeState.object | 776 | json_unknown: `} else if d.disallowUnknownFields {` |
| sing/common/json/internal/contextjson/decode.go | decodeState.object | 777 | json_unknown: `json: unknown field %q` |
| sing/common/json/internal/contextjson/decode.go | decodeState.literalStore | 953 | json_null: `case reflect.Interface, reflect.Pointer, reflect.Map, reflect.Slice:` |
| sing/common/json/internal/contextjson/decode.go | decodeState.literalStore | 955 | json_null: `// otherwise, ignore null for primitives/string` |
| sing/common/json/internal/contextjson/stream.go | Decoder.Decode | 47 | json_single_decode: `func (dec *Decoder) DisallowUnknownFields()` |
| sing/common/json/internal/contextjson/stream.go | Decoder.Decode | 78 | json_single_decode: `err = dec.d.unmarshal(v)` |
| sing/common/json/internal/contextjson/stream.go | Decoder.Decode | 81 | json_single_decode: `dec.tokenValueEnd()` |
| sing/common/json/badjson/merge_objects.go | UnmarshallExcludedContext | 42 | json_nested: `content.Remove(key)` |
| sing/common/json/badjson/merge_objects.go | UnmarshallExcludedContext | 54 | json_nested: `return json.UnmarshalContextDisallowUnknownFields(ctx, inputContent, object)` |
| sing/common/json/badjson/object.go | JSONObject.decodeJSON | 104 | json_duplicates: `m.Put(entryKey, entryValue)` |
| sing/common/x/linkedhashmap/map.go | Map.Put | 46 | json_overwrite: `func (m *Map[K, V]) Put(key K, value V) V {` |
| sing/common/x/linkedhashmap/map.go | Map.Put | 51 | json_overwrite: `entry.Value.Value = value` |
| sing/common/json/badjson/merge.go | MergeJSON/mergeJSON | 82 | json_merge: `if rawSource == nil && rawDestination == nil {` |
| sing/common/json/badjson/merge.go | MergeJSON/mergeJSON | 115 | json_merge: `destination = append(destination, source...)` |
| sing/common/json/badjson/merge.go | MergeJSON/mergeJSON | 128 | json_merge: `entry.Value, err = mergeJSON(entry.Value, oldValue, disableAppend)` |
| sing/common/json/badjson/merge.go | MergeJSON/mergeJSON | 48 | json_merge: `return destination, nil` |
| sing-box/protocol/http/inbound.go | Inbound.NewConnectionEx | 60 | http_dispatch: `Network:           []string{N.NetworkTCP}` |
| sing-box/protocol/http/inbound.go | Inbound.NewConnectionEx | 43 | http_dispatch: `auth.NewAuthenticator(options.Users)` |
| sing-box/protocol/http/inbound.go | Inbound.NewConnectionEx | 99 | http_dispatch: `http.HandleConnectionEx(` |
| sing-box/protocol/http/inbound.go | Inbound.NewConnectionEx | 41 | http_dispatch: `uot.NewRouter(router, logger)` |
| sing-box/common/listener/listener_tcp.go | Listener.ListenTCP | 23 | listener: `func (l *Listener) ListenTCP()` |
| sing-box/common/listener/listener_tcp.go | Listener.ListenTCP | 71 | listener: `return listenConfig.Listen(l.ctx,` |
| sing-box/common/listener/listener.go | Listener.Start | 100 | system_proxy: `if l.setSystemProxy {` |
| sing-box/common/listener/listener.go | Listener.Start | 113 | system_proxy: `err = systemProxy.Enable()` |
| sing-box/route/route.go | Router.routeConnection | 103 | selected_outbound: `selectedOutbound, loaded = r.outbound.Outbound(action.Outbound)` |
| sing-box/route/route.go | Router.routeConnection | 140 | selected_outbound: `if selectedRule == nil {` |
| sing-box/route/route.go | Router.routeConnection | 141 | selected_outbound: `defaultOutbound := r.outbound.Default()` |
| sing-box/route/route.go | Router.routeConnection | 131 | selected_outbound: `return action.Error(ctx)` |
| sing-box/box.go | New default fallback factories | 319 | direct_default: `outboundManager.Initialize(func()` |
| sing-box/box.go | New default fallback factories | 320 | direct_default: `return direct.NewOutbound(` |
| sing-box/box.go | New default fallback factories | 325 | direct_default: `option.DirectOutboundOptions{}` |
| sing-box/box.go | New default fallback factories | 328 | direct_default: `dnsTransportManager.Initialize(func()` |
| sing-box/box.go | New default fallback factories | 333 | direct_default: `option.LocalDNSServerOptions{}` |
| sing-box/adapter/outbound/manager.go | Manager.Start/Create | 69 | manager_default: `if m.defaultOutbound == nil {` |
| sing-box/adapter/outbound/manager.go | Manager.Start/Create | 70 | manager_default: `m.defaultOutboundFallback()` |
| sing-box/adapter/outbound/manager.go | Manager.Start/Create | 310 | manager_default: `m.defaultTag == "" && m.defaultOutbound == nil` |
| sing-box/route/conn.go | ConnectionManager.NewConnection | 102 | connection_failure: `remoteConn, err = this.DialContext(ctx, N.NetworkTCP, metadata.Destination)` |
| sing-box/route/conn.go | ConnectionManager.NewConnection | 116 | connection_failure: `N.CloseOnHandshakeFailure(conn, onClose, err)` |
| sing-box/protocol/trojan/outbound.go | trojanDialer.DialContext (illustration, not selected protocol) | 50 | one_server_example: `serverAddr: options.ServerOptions.Build()` |
| sing-box/protocol/trojan/outbound.go | trojanDialer.DialContext (illustration, not selected protocol) | 134 | one_server_example: `h.tlsDialer.DialTLSContext(ctx, h.serverAddr)` |
| sing-box/protocol/trojan/outbound.go | trojanDialer.DialContext (illustration, not selected protocol) | 136 | one_server_example: `h.dialer.DialContext(ctx, N.NetworkTCP, h.serverAddr)` |
| sing-box/protocol/trojan/outbound.go | trojanDialer.DialContext (illustration, not selected protocol) | 144 | one_server_example: `return trojan.NewClientConn(conn, h.key, destination)` |
| sing-box/common/dialer/dialer.go | NewWithOptions | 45 | resolve: `if dialOptions.Detour != "" {` |
| sing-box/common/dialer/dialer.go | NewWithOptions | 57 | resolve: `if options.RemoteIsDomain &&` |
| sing-box/common/dialer/dialer.go | NewWithOptions | 126 | resolve: `NewResolveDialer(` |
| sing-box/dns/transport/local/resolv_windows.go | dnsReadConfig/adapterAddresses | 99 | local_dns: `windows.GetAdaptersAddresses(` |
| sing-box/dns/transport/local/resolv_windows.go | dnsReadConfig/adapterAddresses | 27 | local_dns: `conf.servers = defaultNS` |
| sing-box/common/uot/router.go | Router.RouteConnectionEx | 29 | uot: `case uot.MagicAddress:` |
| sing-box/common/uot/router.go | Router.RouteConnectionEx | 72 | uot: `r.router.RoutePacketConnectionEx(` |
| sing-box/protocol/group/urltest.go | URLTestGroup.PostStart | 270 | health: `g.ticker = time.NewTicker(g.interval)` |
| sing-box/route/rule/rule_set_remote.go | RemoteRuleSet.StartContext/PostStart | 108 | remote_rules: `s.fetch(ctx, startContext)` |
| sing-box/route/rule/rule_set_remote.go | RemoteRuleSet.StartContext/PostStart | 113 | remote_rules: `s.updateTicker = time.NewTicker(s.updateInterval)` |
| sing-box/route/rule/rule_set_remote.go | RemoteRuleSet.StartContext/PostStart | 118 | remote_rules: `go s.loopUpdate()` |
| sing-box/box.go | New conditional services | 204 | ntp: `if ntpOptions.Enabled {` |
| sing-box/box.go | New conditional services | 374 | ntp: `ntp.NewService(ntp.Options{` |
| sing-box/protocol/tor/outbound.go | Outbound.start | 109 | tor_helper: `tor.Start(t.ctx, t.startConf)` |
| sing-box/protocol/tor/outbound.go | Outbound.start | 166 | tor_helper: `socks.NewClient(N.SystemDialer,` |
| sing-box/common/tls/ech.go | ECHClientConfig.fetchAndHandshake | 150 | ech_dns: `s.dnsRouter.Exchange(ctx, message, adapter.DNSQueryOptions{})` |
| sing-box/common/tls/reality_client.go | realityClientFallback | 222 | reality_cover: `go realityClientFallback(` |
| sing-box/common/tls/reality_client.go | realityClientFallback | 234 | reality_cover: `return uConn, nil` |
| sing-box/common/tls/reality_client.go | realityClientFallback | 245 | reality_cover: `client.Do(request)` |
| sing-box/cmd/sing-box/cmd.go | preRun | 67 | config_default: `if len(configPaths) == 0 && len(configDirectories) == 0 {` |
| sing-box/cmd/sing-box/cmd.go | preRun | 68 | config_default: `configPaths = append(configPaths, "config.json")` |
| sing-box/cmd/sing-box/cmd.go | preRun | 62 | config_default: `os.Chdir(workingDir)` |
| sing-box/cmd/sing-box/cmd_run.go | readConfig/readConfigAndMerge | 52 | config_merge: `if path == "stdin" {` |
| sing-box/cmd/sing-box/cmd_run.go | readConfig/readConfigAndMerge | 80 | config_merge: `for _, directory := range configDirectories {` |
| sing-box/cmd/sing-box/cmd_run.go | readConfig/readConfigAndMerge | 96 | config_merge: `sort.Slice(optionsList,` |
| sing-box/cmd/sing-box/cmd_run.go | readConfig/readConfigAndMerge | 112 | config_merge: `badjson.MergeJSON(` |
| sing-box/option/options.go | Options.UnmarshalJSONContext | 31 | schema: `decoder.DisallowUnknownFields()` |
| sing-box/option/options.go | Options.UnmarshalJSONContext | 37 | schema: `return checkOptions(o)` |
| sing/common/exceptions/error.go | New | 26 | error_new: `return errors.New(F.ToString(message...))` |
| sing/common/json/internal/contextjson/decode.go | decodeState.literalStore | 970 | json_type_error: `d.saveError(&UnmarshalTypeError{Value: "bool"` |
| sing/common/json/comment.go | NewCommentFilter | 32 | comment_filter: `func NewCommentFilter(reader io.Reader) io.Reader {` |
| sing/common/buf/buffer_windows.go | Buffer.Iovec | 3 | platform_dependency: `import "golang.org/x/sys/windows"` |
| sing-box/protocol/http/inbound.go | Inbound.NewConnectionEx | 102 | parent_error_log: `h.logger.ErrorContext(ctx, E.Cause(err, "process connection from ", metadata.Source))` |
| sing-box/option/inbound.go | Inbound.UnmarshalJSONContext | 43 | parent_nested: `err = badjson.UnmarshallExcludedContext(ctx, content, (*_Inbound)(h), options)` |
| sing-box/cmd/sing-box/cmd_run.go | readConfigAndMerge | 112 | parent_merge: `mergedMessage, err = badjson.MergeJSON(` |
| sing-box/cmd/sing-box/cmd_run.go | run | 181 | parent_reload: `if osSignal == syscall.SIGHUP {` |
| sing-box/adapter/upstream.go | myUpstreamHandlerWrapperEx.NewConnectionEx | 44 | parent_callback: `w.connectionHandler(ctx, conn, myMetadata, onClose)` |

BLOCKED: exact Go stdlib parser/URL/TLS/net and runtime/platform x/sys closure. No source→binary, SID/WFP, owner/traffic or ordinary Chat proof. No automatic additional downloads.
