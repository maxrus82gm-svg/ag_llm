param([string]$ConfigPath,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'WuaMcp.psm1') -Force -DisableNameChecking
try {
    $out=Assert-WuaLocalPath $OutputDirectory -AllowMissing
    if ([IO.Directory]::Exists($out) -and [IO.Directory]::GetFileSystemEntries($out).Length) {throw 'OUTPUT_NOT_EMPTY'}
    [void][IO.Directory]::CreateDirectory($out)
    $config=if ($ConfigPath) {Read-WuaJson $ConfigPath} else {@{schema_version=1;owner_id=[Guid]::NewGuid().ToString('D');paths=@{}}}
    Assert-WuaConfiguration $config
    . (Join-Path $PSScriptRoot 'Discovery.ps1')
    $collectorFailure=$null
    try {$inventory=Invoke-WuaLocalDiscovery $config}
    catch {
        $code='LOCAL_PROVIDER_OR_IMPLEMENTATION_FAILURE'
        if ($_.Exception.Message -cmatch '^[A-Z][A-Z0-9_]{2,80}$') {$code=$_.Exception.Message}
        $collectorFailure=@{status='BLOCKED';code=$code;error_type=$_.Exception.GetType().Name;line=$_.InvocationInfo.ScriptLineNumber;raw_error_redacted=$true}
        $inventory=New-WuaInventory $config @{} 'local_readonly'
        Write-WuaJson (Join-Path $out 'discovery-failure.json') $collectorFailure
    }
    $coverage=Get-WuaCoverage $inventory
    $plan=New-WuaDeploymentPlan $inventory $config
    Write-WuaJson (Join-Path $out 'inventory.json') $inventory
    Write-WuaJson (Join-Path $out 'coverage.json') $coverage
    Write-WuaJson (Join-Path $out 'install-plan.json') $plan
    Write-WuaJson (Join-Path $out 'verification-static.json') (Test-WuaInstallation $plan $inventory $config)
    # This public starter intentionally contains no private paths/endpoint or credentials.
    Write-WuaJson (Join-Path $out 'operator-input.template.json') @{schema_version=1;owner_id=$config.owner_id;paths=@{}}
    $encoding=New-Object Text.UTF8Encoding $false
    [IO.File]::WriteAllText((Join-Path $out 'install-plan.md'),(Format-WuaPlan $plan),$encoding)
    $text=@('# Host inventory (PUBLIC REDACTED)','','No host/user/SID/address/private-path/credential values are exported.',
        ('Required fields represented: '+$coverage.represented+'/'+$coverage.required),('Metadata VERIFIED: '+$coverage.verified_metadata),
        '100% representation is not security readiness. Apply: BLOCKED.','', '| Field | Status | Detail |','|---|---|---|')
    foreach ($f in $inventory.fields) {$text+=('| '+$f.id+' | '+$f.status+' | '+$f.detail+' |')}
    [IO.File]::WriteAllText((Join-Path $out 'inventory.md'),($text -join [Environment]::NewLine),$encoding)
    Write-Output (ConvertTo-WuaCanonicalJson @{status=$(if ($collectorFailure) {'DISCOVERY_BLOCKED_COMPLETE_COVERAGE'} else {'DISCOVERY_COMPLETE_APPLY_BLOCKED'});represented=$coverage.represented;required=$coverage.required;verified_metadata=$coverage.verified_metadata;blocking=$coverage.blocking_count})
} catch {
    $code='LOCAL_DISCOVERY_INPUT_OR_PROVIDER_FAILURE';if ($_.Exception.Message -cmatch '^[A-Z][A-Z0-9_]{2,80}$') {$code=$_.Exception.Message}
    Write-Output (ConvertTo-WuaCanonicalJson @{status='BLOCKED';reason=$code;error_type=$_.Exception.GetType().Name;line=$_.InvocationInfo.ScriptLineNumber;raw_error_redacted=$true});exit 20
}
