# Фактически проверенная цепочка и границы

Все реальные fixture processes этой TASK работают под текущим пользователем. C/U ниже — роли будущей конструкции, не созданные разные Windows identities.

```text
официальный Python MCP ClientSession (test/UI, вне C)
    ↕ inherited STDIO, настоящий JSON-RPC MCP
C-role: WuaRelay.exe (Shared.cs + Relay.cs; без Python/helper/network API)
    ↕ один точный local NPFS handle; WNP1/session/direction/sequence/HMAC framing
U-role: WuaGateway.exe (server-owned fixture; explicit DACL + token checks)
    ↕ только три явно унаследованных STDIO handles
U-role: фиксированный .venv Python launcher → MCP SDK worker
    ↕ существующий server.make_server / четыре read-only tools
U-role: WebAlarmApi.dispatch, in-process, новое synthetic хранилище TASK/runs
```

Новый transport не подменяет MCP handlers. SDK client действительно выполняет initialize, tools/list и tools/call через все executable/pipe/SDK слои. В бинарном NPFS envelope лежат исходные UTF8 JSON-RPC сообщения; newline framing остаётся на STDIO. Служебные `hello/ready/close` — внутренний authenticated transport lifecycle, не ответ MCP.

Relay открывает только `\\.\pipe\WUA-NPFS-<32 hex>`. Нет параметра remote machine, UNC, TCP endpoint, DNS, proxy или reconnect. Full-duplex обеспечивают два ограниченных потока; обработка ответа не ждёт EOF клиентского ввода. RPC correlation ведётся отдельно для обоих направлений, pending ≤16, ID history ≤96. Разрешены операции узкого MCP read server; нет sampling/model/file/process delegation.

Gateway сначала проверяет свою fixture/config/session/source binding, затем создаёт единственную pipe instance. До проверки client primary token, эффективного Identification token, image pin и MAC grant SDK child не запускается. Child создаётся suspended; три handle переданы через STARTUPINFOEX handle list; kill-on-close Job Object назначен до ResumeThread. Venv redirector и его потомки попадают в job до первого исполнения. При смерти gateway Windows закрывает job handle и завершает его descendants. Это проверено OS wait для реального SDK PID.

Python asyncio остаётся **только на стороне U и у test client**. Их внутренние loopback sockets не относятся к заявлению о C relay и не считаются отсутствующими. U не ограничен будущей C/B WFP policy. Дополнительного C TCP allowlist или исключения для Python selfpipe не добавлено.

Будущие, НЕ запущенные части:

```text
ordinary ChatGPT/cloud ↔ hosted Secure MCP Tunnel [HOLD]
C: official Go tunnel-client → TCP literal127:P → B: dedicated V2Ray HTTP CONNECT
                         ↕ STDIO                         → literal approved R:Q
                       новый C relay
                         ↕ NPFS → U authority
```

B должен быть настоящим владельцем внешнего V2Ray socket. B-wrapper → пользовательский SOCKS/V2Ray не удовлетворяет gate. Код B/V2Ray этой TASK не менялся. `CanApply=false`, Install/Uninstall BLOCKED. Полный Go runtime graph, реальные C/B identities, WFP, другой Windows IPC/delegated egress, boot/restart, Platform entitlement и ordinary Chat E2E остаются отдельными непроверенными условиями.
