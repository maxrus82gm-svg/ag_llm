# S2 isolation: classification, import closure, and proof boundary

TASK `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001`, STRICT OFFLINE.

## Source scope and roots

The initial local crosscheck matched all 203 baseline source/CMD hashes from
H24, with S1 pinned to WEB25's published/independently executed SHA
35426388b49eb4a8154f5dfe8717ff4f3796b315ce3b391a71db6834e4a09696.
The assigned base is main@0ee846a1159c690d2bc29eab46fca807e4027541; no Git
metadata or GitHub was accessed to verify the checkout identity itself.

Actual entrypoints reviewed:

| Source | Runtime origin |
| --- | --- |
| server | Root MCP server entrypoint and existing physical LLM/OAuth routes |
| ultra_ui | Start_Ultra.cmd → ultra_ui.py, existing Tk runtime |
| web_alarm.launcher | Both permanent STANDARD/TEST CMD → -m web_alarm.launcher |
| web_alarm.server | Web Alarm HTTP application/API implementation |
| web_alarm.__main__ → web_alarm.cli | Existing python -m web_alarm CLI path |

The oracle requires all six module identities. It does **not** limit checking
to currently reachable entrypoints: every local source except the policy
library and the exact reviewed OFFLINE capsule is a conservative production
candidate. New, unused, maintenance and future consumers therefore do not gain
an implicit exemption. The 82-node local graph has 80 such roots. Package/file
identities use full relative names, distinguishing server from web_alarm.server.

Discovery starts with the unchanged S1 census and follows explicitly named
local dependencies and package initializers. It does not recursively read
archives or reports. Synthetic file-based checks separately prove that builtin
__import__(..., fromlist=['child']) discovers a child absent from that initial
census, then distinguishes its safe imports from a path to policy.

## One bounded OFFLINE capsule, never a filename-only exemption

The only approved capsule identity is ultra_budget_ledger, with a fixed
Python3.12 AST SHA-256:
4ec4bc2a511477366ee9e71a7aae7dbf79e259f34f1e0dd018147c2faabfc1fb.
The full AST includes its docstrings and implementation; whitespace/EOL alone
do not alter the pin. This constant is not refreshed from current source at
test time. Altered code fails OFFLINE_CAPSULE_CHANGED. An identical copy under
another identity is an ordinary candidate and fails for its policy dependency.

Current local outgoing edges: context_storage, run_store, ultra_budget_policy.
All three remain independently inspected graph nodes, not transitive safe
exceptions. There are **zero incoming edges to ledger** and no path from any of
the 80 candidate roots to policy. Importing ledger from server, from a newly
introduced bridge, or through from/alias bindings makes policy reachable and
fails. Its shared dependencies cannot start importing policy unnoticed either.

The library policy's existing purity test remains intact. New capsule code,
library upgrades, a new production consumer or production enforcement require
their own review/authority; changing a filename cannot confer permission.

## Import forms and failure rules

The AST graph records imports inside functions and inactive branches too.
It handles import/from aliases, qualified package identities, relative from
imports, package initializer side effects, re-exported loader aliases and
assignment alias chains. Union-based binding analysis never hides an earlier
possible loader through a later rebind; cycles/depth exhaustion fail closed.

Literal __import__/importlib.import_module, aliases/getattr, module dictionaries,
literal exec/compile strings and relative import_module package arguments are
parsed without executing them. Builtin literal fromlists expand child-module
discovery; unknown/star fromlists and nonzero/unknown builtin relative levels
require review. Static star imports also require review (none in the current
production census). Unknown dynamic names/packages, loader escapes, opaque
exec and unsupported file/runpy import loaders give an issue, never safe PASS.

The receiver-independent protected-name/path net also rejects unexplained policy
or ledger literals/concatenations, including dotted submodules and .py paths.
Exact reviewed ledger metadata may name its policy engine file; this is bound
to the capsule AST, not a general URL/name allowlist.

Local modules shadowing stdlib/external names take priority in the graph and
are scanned. New unresolved roots fail UNKNOWN_IMPORT_ROOT. Current external
dependency roots are httpx and mcp; stdlib names come from project Python.
This recognizes existing dependency boundaries, not an exemption for local
files named httpx/mcp. Third-party internals are not recursively executed or
audited by this task.

## Addressed existing metadata query

Current web_alarm.model_cards._adapter_state uses find_spec(provider.adapter).
find_spec may import parents of a dotted name, so arbitrary unknown spec queries
are not ignored. This one call is tied to H24's reviewed S1 metadata pins and
reference census: frozen Provider, builtin adapter gigachat_transport, custom
provider adapter None, the factory statements, and _adapter_state's annotated
function body. Domain-changing source edits make the S1 reconciliation fail,
and then the unknown query is denied here.

New outside references/imports to Provider, BUILTIN_PROVIDERS or _adapter_state
are rejected as PINNED_SPEC_INPUT_DOMAIN_ESCAPE; dynamic lookup of those module
internals also requires review. This keeps the narrowly reviewed input domain
from becoming an implicit general-purpose import helper. The current graph's
one observation explicitly records this proof. All other unknown spec queries
fail; literal spec queries are conservatively included as import targets.

## Negative evidence and limits

isolation_checks.py invokes the **actual existing S2 isolation test method**
against synthetic in-memory source maps or discovered TEMP files. Each inner
run must execute one method with no ERROR/SKIP. The 47 checks comprise 43
expected inner RED and four safe PASS; source maps must remain unchanged.
Resolved-import cases additionally require an actual policy path, rather than
passing solely because a protected string was observed. Raw assertion traces,
issues and paths are retained in quality.result.json; negative_matrix.json is
the compact independent readback.

Three deliberate oracle weakenings are detected: suppress issues (43 outer
FAIL), omit a transitive ledger edge (1 FAIL), and accept capsule code by name
without validating its hash (1 FAIL). Each process returns expected exit1,
zero ERROR/SKIP and zero unexpected guard violations.

This is conservative static isolation testing on a fixed local source snapshot,
not a complete Python interpreter, a runtime capability boundary or a pre-HTTP
budget guard. Arbitrary obfuscation, runtime monkeypatching, native/external
code internals, OS subprocess dispatch, hostile concurrent source replacement
and unseen plugin/config entrypoints are not fully proved by it. Unsupported
recognized import constructs fail closed; future mechanisms require review.
S3b must enforce the physical send boundary independently. No inspected source,
exec string or import target was executed to construct this graph.
