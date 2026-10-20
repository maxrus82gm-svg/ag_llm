param([Parameter(Mandatory=$true)][string]$PlanPath,[Parameter(Mandatory=$true)][string]$InventoryPath,[Parameter(Mandatory=$true)][string]$ConfigPath,[string]$FreshInventoryPath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'WuaMcp.psm1') -Force -DisableNameChecking
try {
    $fresh=$null;if ($FreshInventoryPath) {$fresh=Read-WuaJson $FreshInventoryPath}
    $result=Test-WuaInstallation (Read-WuaJson $PlanPath) (Read-WuaJson $InventoryPath) (Read-WuaJson $ConfigPath) $fresh
    Write-WuaJson $OutputPath $result
    Write-Output (ConvertTo-WuaCanonicalJson @{static_plan_binding=$result.static_plan_binding;security_verdict=$result.security_verdict})
} catch {Write-Output '{"status":"BLOCKED","reason":"VERIFICATION_INPUT_REJECTED"}';exit 20}
