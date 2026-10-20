# Guarded scaffold. This version contains no executable provisioning backend.
param([Parameter(Mandatory=$true)][string]$PlanPath,[Parameter(Mandatory=$true)][string]$InventoryPath,[Parameter(Mandatory=$true)][string]$ConfigPath,[string]$ApprovedHash,[string]$LedgerPath,[switch]$Apply,[switch]$DryRun)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'WuaMcp.psm1') -Force -DisableNameChecking
try {
    $plan=Read-WuaJson $PlanPath;$inventory=Read-WuaJson $InventoryPath;$config=Read-WuaJson $ConfigPath
    if ($LedgerPath) {Write-Output (ConvertTo-WuaCanonicalJson (Get-WuaResumeDecision $plan (Read-WuaJson $LedgerPath)))}
    $decision=Get-WuaApplyDecision $plan $inventory $config $ApprovedHash
    Write-Output (ConvertTo-WuaCanonicalJson $decision)
    exit 20
} catch {Write-Output '{"status":"BLOCKED","reason":"INSTALL_INPUT_REJECTED","mutations":0}';exit 20}
