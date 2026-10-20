# WUA MCP Portable Deployment Kit 0.1.0-offline

Copy this **toolkit/** directory to another local Windows machine. No Python,
Pester, NuGet or third-party runtime is needed for Discovery/Plan/static Verify/
rollback planning: PowerShell 5.1-compatible source and built-in .NET suffice.
PowerShell execution policy/signing requirements remain in force. Do not bypass
policy, auto-unblock downloads, elevate, or install anything to run this kit.
Runtime validation on another host is separate from syntax compatibility.
Collector requires a 64-bit PowerShell process; x86/ARM64 deployment profiles
are not certified. A 32-bit collector returns BLOCKED rather than misreporting
the process architecture as the actual OS architecture under WOW64.

**This release cannot install, activate or uninstall a live system.** Install
and Uninstall are guarded engineering scaffolds. They always return BLOCKED,
including `-Apply`, matching approval hashes, synthetic proof claims and valid
ledgers. Exit 20 means BLOCKED. No bypass flag exists; no mutating Windows API
or command is called by these scripts. The source-only C# backend contract
throws NotSupportedException for every mutating operation and is never loaded.

## Read-only discovery

From a terminal allowed by your local execution policy:

```powershell
.\Collect-Host.ps1 -OutputDirectory <new-local-output-directory>
```

The output directory is the only created filesystem state. Use a new empty
local directory, not a network/mapped-network/cloud/reparse path. This is
read-only **system** inventory, not a promise that no report files are written.
No network probe, DNS, package download, policy refresh, privilege escalation,
subject execution, Task Scheduler creation or firewall change occurs.

Discovery reads local CIM properties only: OS version/build/SKU; BFE/MpsSvc/
Schedule state; firewall profile aggregates; policy-key presence; security-product
count; current token admin-membership boolean; effective script execution policy;
technical-name collisions; TCP/UDP port metadata; adapter/address-family/route
counts. It checks local DLL presence, not operational WFP semantics.

For client/broker executables it checks at most 256 **local validated PATH
directories** plus executable paths of known matching local processes. It never
reads command lines, recursively scans disks, executes `--version`, or follows
unsafe PATH entries. Ambiguous candidates are CONFLICT, not first-match wins.
Renamed/unreachable files, missing versions and optional inputs require operator
selection. FileVersionInfo is metadata, not authoritative native version/build proof.

Optional `-ConfigPath` accepts a local **nonsecret** JSON operator input. Start
from `contracts/operator-input.example.json`. Allowed keys:

- `schema_version: 1`, a nonempty UUID `owner_id` generated for this deployment;
- `paths`: explicit local `client_exe`, `broker_exe`, `stdio_exe`, `stdio_script`,
  `source_archive`, `resources_root`, `working_directory`, `deployment_root`;
- optional `local_port` (integer 1024..65535), otherwise a deterministic free
  snapshot candidate is selected from 49152..65535 without opening a socket;
- `remote_endpoint`: literal IPv4 `address`, integer `port` 1..65535,
  `transport: "tcp"`; domains, IPv6 and UDP are not silently enabled;
- `startup_mode`: `task_batch` or future `service_wrapper`;
- optional technical `account_prefix`, `broker_schema_ref`, `remote_identity_ref`.

**Never put passwords, tokens, proxy credentials, cookies or secret config files
in this input.** Unknown keys, imported SID, privilege/force flags, malformed
types and duplicate JSON property names are rejected. Real remote addresses and
paths stay in the operator's local input and in memory, not public outputs.
The kit does not read Credential Manager, browser profiles or secret environment
values. Proxy context therefore remains REQUIRES_USER_INPUT; no value is guessed.

Output: `inventory.json`, redacted `inventory.md`, `coverage.json`,
`install-plan.json`, `install-plan.md`, `verification-static.json`, and a public
`operator-input.template.json`. The template intentionally omits private values.
If an explicit private configuration was used, the public template is **not** a
replacement with the same digest: retain your original nonsecret private input.
Nothing is sent to a server. Deployment UUID is newly generated, not a host ID.

## Coverage and planning

The v1 manifest has **55 required fields in 11 categories**. Coverage means each
is present with a typed value or explicit status. 55/55 represented is **not**
55 verified facts, native compatibility, T2 isolation, or Apply readiness.
DETECTED is weaker than VERIFIED metadata; proof/future fields remain
UNSUPPORTED/REQUIRES_USER_INPUT. Metadata VERIFIED means type/value acquisition,
not security enforcement. A known false fact can be collected correctly while
the requirement remains unmet. All missing/unknown requirements block mutations.

```powershell
.\New-DeploymentPlan.ps1 -InventoryPath <inventory.json> `
  -ConfigPath <original-operator-input.json> -OutputDirectory <new-plan-directory>
```

Default is DryRun. Every action has WHAT/WHY/TARGET/BEFORE/AFTER/PRIVILEGES/
VERIFICATION/ROLLBACK. Public targets use role/path references. Add `-LocalPreview`
only in a **private local terminal** to see exact nonsecret paths, remote endpoint
and proposed technical names. Do not publish that console output. Future Apply
would require reviewing both the public actions and these exact local parameters.

New technical account names derive from owner UUID/prefix; no fixed usernames,
SID, host names or drive letters are assumed. Only **new local accounts** may
provide future SID bindings. No foreign account adoption or SID copying occurs.
Current user ChatGPT Desktop is outside these future C/B policies.

Approval SHA-256 binds canonical payload, inventory, configuration and contract.
It is neither a signature nor user authorization nor device identity. Public
inventory has no trusted host binding: this is a mandatory unresolved proof.
Repeated pure planning with identical inputs is deterministic. A matching ledger
does not justify duplicate creation or trusting its owner claims; resume remains
BLOCKED pending independent actual-object readback.

## Verify and rollback

```powershell
.\Test-WuaMcpInstallation.ps1 -PlanPath <install-plan.json> `
  -InventoryPath <inventory.json> -ConfigPath <operator-input.json> `
  -OutputPath <new-verification.json>
```

This release verifies content binding and can compare a `-FreshInventoryPath`.
Comparison reports field/status differences without transferring private values.
It explicitly leaves SID creation, effective WFP, listener guard, DNS/delegation,
children, failures, V2Ray route and ordinary Chat E2E NOT RUN/NOT VERIFIED.

`Install-WuaMcp.ps1` accepts `-PlanPath`, `-InventoryPath`, `-ConfigPath`, optional
`-ApprovedHash`, `-LedgerPath`, `-DryRun`/`-Apply`. It cannot mutate anything.
`Uninstall-WuaMcp.ps1 -LedgerPath <ledger.json>` returns a guarded rollback plan,
not resource deletion. Do not invoke those wrappers as a live deployment test.

Ledger example is empty and synthetic. Resource IDs must be unique UUIDs,
owner/plan matching, newly created by kit, symbolic allowed target kinds;
foreign/preexisting objects and arbitrary paths/commands are rejected. Even
`reported_zero` processes/flows is not authority to remove deny. Rollback order:
freeze admissions → disable own startup/identities → quiesce and independently
verify all owned/delegated work absent → remove exact owned tasks/identities →
remove owned deny **last** → remove exact checked owned files. Unknown state keeps
deny and returns ROLLBACK BLOCKED. No global reset, recursive wildcard cleanup,
service killing or takeover of another installation exists.

## Security backend and next stage

`policy/backend-contract.json` and `backends/UnavailableWfpBackend.cs` specify the
missing boundary. Real implementation needs reviewed local SID/logon/ACL APIs,
user-mode Fwpm transaction/readback/ownership management, private ledger storage,
noninteractive startup and independent observer. No DLL is compiled or loaded
automatically. The C# stub is source-only, not a completed WFP implementation.
Changing a JSON field cannot enable Apply. A future executable backend is a code
change requiring independent review, proven Windows semantics and new USER GO.

The current predicate model does not prove Windows Block/Allow arbitration,
loopback filtering/bind ownership, BFE/boot/old-flow behavior, DNS/system broker
closure or authenticated V2Ray route. Ordinary `Block ALL + Allow localhost` is
not used. No DIRECT or broad loopback fallback is generated.

Windows 10 Pro/Windows 11 fixtures cover metadata profiles, not real multi-host
certification. Unknown editions/builds/architecture are UNSUPPORTED. No account,
rights, ACL, filter, service, scheduler entry, working V2Ray or MCP launcher is
changed by this release. HOSTED_TUNNEL_ON_HOLD_BY_USER remains in force.

## Synthetic tests

```powershell
.\tests\Test-Toolkit.ps1 -OutputDirectory <new-empty-local-test-directory>
```

No Pester/network/Windows policy/Install/Uninstall invocation occurs. Test results
record source hashes and distinguish logical model points from native security
proof. Use a permitted PowerShell environment; do not override execution policy.
Publish only the redacted report files; never publish raw terminal transcripts
or the explicit private `-LocalPreview` output.
