param([Parameter(Mandatory=$true)][string]$InventoryPath,[Parameter(Mandatory=$true)][string]$ConfigPath,[Parameter(Mandatory=$true)][string]$OutputDirectory,[switch]$LocalPreview)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'WuaMcp.psm1') -Force -DisableNameChecking
try {
    $inventory=Read-WuaJson $InventoryPath;$config=Read-WuaJson $ConfigPath
    $plan=New-WuaDeploymentPlan $inventory $config
    $out=Assert-WuaLocalPath $OutputDirectory -AllowMissing
    if ([IO.Directory]::Exists($out) -and [IO.Directory]::GetFileSystemEntries($out).Length) {throw 'OUTPUT_NOT_EMPTY'}
    [void][IO.Directory]::CreateDirectory($out)
    Write-WuaJson (Join-Path $out 'install-plan.json') $plan
    $encoding=New-Object Text.UTF8Encoding $false
    [IO.File]::WriteAllText((Join-Path $out 'install-plan.md'),(Format-WuaPlan $plan),$encoding)
    if ($LocalPreview) {
        Write-Output 'PRIVATE LOCAL PREVIEW: do not publish this console output. No secrets are accepted by configuration schema.'
        Write-Output (ConvertTo-WuaCanonicalJson @{operator_input=$config;new_technical_names=(Get-WuaCandidateNames $config);approval_sha256=$plan.approval_sha256})
    }
    Write-Output (ConvertTo-WuaCanonicalJson @{status='PLAN_READY_APPLY_BLOCKED';approval_sha256=$plan.approval_sha256;actions=$plan.payload.actions.Count})
} catch {Write-Output '{"status":"BLOCKED","reason":"INVALID_OR_MISMATCHED_PLAN_INPUT","raw_error_redacted":true}';exit 20}
