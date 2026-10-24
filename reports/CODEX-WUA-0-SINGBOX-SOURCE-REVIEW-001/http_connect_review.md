# HTTP inbound / CONNECT — partial source evidence

`protocol/http/inbound.go:60` / `Inbound.NewConnectionEx` registers HTTP, creates TCP listener, constructs `auth.NewAuthenticator(options.Users)`, optional inbound TLS and calls external `http.HandleConnectionEx` with stream and packet callbacks. `common/listener/listener_tcp.go:23` / `Listener.ListenTCP` binds a Go net listener; default address literal127.0.0.1 appears in the helper, but future profile must explicitly pin P/address and prohibit reuse/extra listeners.

Bundled docs `docs/configuration/inbound/http.md` say empty users means no authentication; this is **documentation**, not reviewed external authenticator code. `set_system_proxy` is exposed and `common/listener/listener.go:100` / `Listener.Start` enables it when configured: strict proposal must require false. It was not invoked here.

CONNECT request parsing, acceptance conditions, auth rejection/error response, HTTP header limits/ordinary forwarding/stream packet details belong to **github.com/sagernet/sing/protocol/http**, whose implementation is absent. `HTTP_CONNECT_SOURCE_UNVERIFIED / DEPENDENCY_CLOSURE_REQUIRED`. No claim of exact wire semantics from the HTTP name or docs alone.

UoT is real in-repo dispatch: `common/uot/router.go:29` / `Router.RouteConnectionEx` transforms special destinations into packet routing before ordinary TCP router handling. TCP transport alone is not proof of logical TCP-only access. No synthetic/native HTTP request was sent to an engine.
