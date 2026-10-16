# Original attempt 01 — retained

`smoke_attempt_01.json`: exit 1, zero completed assertions, MCP connection closed.
Direct isolated diagnosis reproduced `PermissionError: only_own_fixture_loopback_allowed`
from Python 3.12 Windows `asyncio` -> `socket.socketpair()` during event-loop creation.
The research guard mistakenly blocked Windows' internal event-loop wakeup socket.
This was a PoC isolation/harness defect, not a Web Alarm runtime defect.

Repair: construct the asyncio Runner/event loop before installing the connection
guard, then run the SDK's `run_stdio_async()` on that loop. All subsequent socket
connections remain restricted to the fixture's exact loopback address/port.
Improve the verifier to retain child stderr even if initialization fails.
Original failed-attempt evidence is not overwritten or counted as a PASS.

`smoke_attempt_02.json`: MCP initialization succeeded, but the verifier used
v1 camelCase Python attributes (`serverInfo`) against installed mcp 2.2.0,
which exposes snake_case (`server_info`, `structured_content`, `is_error`,
and annotation fields). Corrected the verifier's API usage, without changing
Web Alarm or relaxing assertions. This is a second harness defect, not a
Web Alarm failure. Original attempt 02 is retained separately.

`smoke_attempt_03.json`: 5 PASS, 1 FAIL. The verifier incorrectly expected
AUTHORITY_SOURCE=`projection`; the actual server-owned authority for a fresh
PLANNED task without microtasks is `lifecycle` (also specified by the existing
`test_web_alarm_context_pack.py:119`). Correct the oracle to the exact lifecycle,
PLANNED, NO_MICROTASK, MISSING and non-authoritative checkpoint contract.
No production change, skip, broad accepted-value set, or assertion removal.

`smoke_attempt_04.json`: 8 PASS, 1 FAIL. The foreign TASK was correctly refused,
but mcp 2.2.0 masks unexpected ValueError details, so the intended stable error
code was absent. Use the SDK's deliberate ToolError for an allowlist denial.
Keep the strict error-code assertion. No sensitive exception disclosure is enabled.
