# Pure prior-module gates only: no collector, Install or Uninstall entrypoint invocation.
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$repoRoot=Split-Path -Parent (Split-Path -Parent $taskRoot)
$prior=Join-Path $repoRoot 'reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001'
$out=[IO.Path]::GetFullPath($OutputPath)
if (-not $out.StartsWith(($taskRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase) -or [IO.File]::Exists($out)) {throw 'OUTPUT_SCOPE'}
Import-Module (Join-Path $prior 'toolkit/WuaMcp.psm1') -Force -DisableNameChecking
$plan=Read-WuaJson (Join-Path $prior 'host_discovery_release/install-plan.json')
$inventory=Read-WuaJson (Join-Path $prior 'host_discovery_release/inventory.json')
$config=Read-WuaJson (Join-Path $prior 'host_discovery_release/operator-input.template.json')
$decision=Get-WuaApplyDecision $plan $inventory $config $plan.approval_sha256
if ($decision.status -cne 'BLOCKED' -or $decision.mutations -ne 0) {throw 'PRIOR_APPLY_NOT_BLOCKED'}
$bad=Get-WuaApplyDecision $plan $inventory $config ('0'*64)
if ($bad.status -cne 'FAIL' -or $bad.mutations -ne 0) {throw 'PRIOR_APPROVAL_GATE'}
$rollback=New-WuaRollbackPlan @{schema_version=1;owner_id='11111111-1111-4111-8111-111111111111';plan_sha256=('a'*64);resources=@();process_state='reported_zero';flow_state='reported_zero'}
if ($rollback.keep_deny -ne $true -or $rollback.status -cne 'ROLLBACK BLOCKED') {throw 'PRIOR_ROLLBACK_GATE'}
$text=ConvertTo-WuaCanonicalJson @{checks=3;passed=3;failed=0;apply=$decision.status;wrong_hash=$bad.status;rollback=$rollback.status;windows_mutations=0;installer_invocations=0;uninstaller_invocations=0;collector_invocations=0;execution_policy_override=$false;runtime=$PSVersionTable.PSVersion.ToString()}
$stream=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$bytes=[Text.Encoding]::UTF8.GetBytes($text);$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
Write-Output 'PRIOR TOOLKIT PURE GATES 3/3; APPLY AND ROLLBACK BLOCKED'
