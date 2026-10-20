# Planning only. No stop/delete/filter/account/file mutation implementation is present.
param([Parameter(Mandatory=$true)][string]$LedgerPath,[switch]$Apply,[switch]$DryRun)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'WuaMcp.psm1') -Force -DisableNameChecking
try {Write-Output (ConvertTo-WuaCanonicalJson (New-WuaRollbackPlan (Read-WuaJson $LedgerPath)));exit 20}
catch {Write-Output '{"status":"ROLLBACK BLOCKED","reason":"FOREIGN_OR_INVALID_LEDGER","keep_deny":true,"mutations":0}';exit 20}
