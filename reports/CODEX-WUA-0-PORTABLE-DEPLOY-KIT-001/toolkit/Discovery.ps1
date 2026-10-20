# Dot-sourced only by Collect-Host.ps1. Each query is local, property-limited and read-only.
function Get-WuaFileMetadata {
    param([string]$Path,[string]$Kind)
    if (-not $Path) { return $null }
    $local=Assert-WuaLocalPath $Path
    $before=Get-Item -LiteralPath $local -Force -ErrorAction Stop
    if ($before.PSIsContainer -or $before.Length -gt 536870912) { throw 'FILE_TYPE_OR_SIZE_BLOCKED' }
    $share=[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete
    $sha=[Security.Cryptography.SHA256]::Create();$stream=[IO.File]::Open($local,[IO.FileMode]::Open,[IO.FileAccess]::Read,$share)
    try { $hash=([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() } finally {$stream.Dispose();$sha.Dispose()}
    $after=Get-Item -LiteralPath $local -Force
    if ($before.Length -ne $after.Length -or $before.LastWriteTimeUtc -ne $after.LastWriteTimeUtc) { throw 'FILE_CHANGED_DURING_HASH' }
    $version='unavailable';$format=$Kind
    if ($Kind -eq 'PE') {
        $format='PE_OTHER';$s=[IO.File]::Open($local,[IO.FileMode]::Open,[IO.FileAccess]::Read,$share)
        try {
            $reader=New-Object IO.BinaryReader $s
            if ($s.Length -ge 64 -and $reader.ReadUInt16() -eq 0x5a4d) {
                $s.Position=60;$offset=$reader.ReadInt32()
                if ($offset -ge 64 -and $offset -lt 1048576 -and $offset+6 -le $s.Length) {
                    $s.Position=$offset
                    if ($reader.ReadUInt32() -eq 0x4550 -and $reader.ReadUInt16() -eq 0x8664) { $format='PE_AMD64' }
                }
            }
        } finally {$s.Dispose()}
        $raw=[Diagnostics.FileVersionInfo]::GetVersionInfo($local).FileVersion
        if ($raw -cmatch '^\d{1,5}(\.\d{1,6}){1,3}$') { $version=$raw }
    }
    $final=Get-Item -LiteralPath $local -Force
    if ($before.Length -ne $final.Length -or $before.LastWriteTimeUtc -ne $final.LastWriteTimeUtc) { throw 'FILE_CHANGED_DURING_METADATA' }
    return @{sha256=$hash;bytes=[long]$before.Length;format=$format;version_metadata=$version}
}

function Invoke-WuaLocalDiscovery {
    param($Config)
    Assert-WuaConfiguration $Config
    if (-not [Environment]::Is64BitProcess) {throw 'COLLECTOR_REQUIRES_64BIT_POWERSHELL'}
    # Validate all operator paths before even the first provider query. Never touch UNC/cloud paths.
    foreach ($key in $Config.paths.Keys) { [void](Assert-WuaLocalPath $Config.paths[$key] -AllowMissing) }
    $system=[Environment]::SystemDirectory
    $cimModule=[IO.Path]::Combine($PSHOME,'Modules','CimCmdlets','CimCmdlets.psd1')
    if (-not [IO.File]::Exists($cimModule)) { $cimModule=[IO.Path]::Combine($system,'WindowsPowerShell','v1.0','Modules','CimCmdlets','CimCmdlets.psd1') }
    [void](Assert-WuaLocalPath $cimModule)
    Import-Module -Name $cimModule -ErrorAction Stop
    $facts=@{}
    function Put([string]$Id,[string]$Status,$Value,[string]$Detail='LOCAL_METADATA') { $facts[$Id]=New-WuaField $Id $Status $Value $Detail }
    function Query([string]$Class,[string]$Namespace,[string]$Filter,[string[]]$Properties) {
        $argsLocal=@{ClassName=$Class;Namespace=$Namespace;Property=$Properties;OperationTimeoutSec=5;ErrorAction='Stop'}
        if ($Filter) { $argsLocal.Filter=$Filter }
        # No ComputerName, CimSession, remote provider or dynamic input command.
        return ,@(CimCmdlets\Get-CimInstance @argsLocal)
    }
    function Find-BinaryCandidates([string]$Role) {
        $namesLocal=if ($Role -eq 'client') {@('tunnel-client.exe')} else {@('sing-box.exe','v2ray.exe')}
        $set=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
        $entries=@(([Environment]::GetEnvironmentVariable('PATH')) -split ';' | Select-Object -First 256)
        foreach ($entry in $entries) {
            if (-not $entry) {continue}
            try {
                $directory=Assert-WuaLocalPath ($entry.Trim('"'))
                if (-not [IO.Directory]::Exists($directory)) {continue}
                foreach ($nameLocal in $namesLocal) {
                    $candidate=[IO.Path]::Combine($directory,$nameLocal)
                    [void](Assert-WuaLocalPath $candidate -AllowMissing)
                    if ([IO.File]::Exists($candidate)) {[void]$set.Add($candidate)}
                }
            } catch { } # Unsafe/unavailable PATH entries are skipped, never followed.
        }
        foreach ($nameLocal in $namesLocal) {
            try {
                $processRows=Query 'Win32_Process' 'root/cimv2' ("Name='"+$nameLocal+"'") @('ExecutablePath')
                foreach ($processRow in $processRows) {
                    if (-not $processRow.ExecutablePath) {continue}
                    try { $candidate=Assert-WuaLocalPath ([string]$processRow.ExecutablePath);[void]$set.Add($candidate) } catch { }
                }
            } catch { }
        }
        return ,@($set | ForEach-Object {$_})
    }
    try {
        $rows=Query 'Win32_OperatingSystem' 'root/cimv2' '' @('Version','BuildNumber','OperatingSystemSKU')
        if ($rows.Count -ne 1) { throw 'OS_COUNT' }
        Put 'os.version' 'VERIFIED' ([string]$rows[0].Version)
        Put 'os.build' 'VERIFIED' ([int]$rows[0].BuildNumber)
        Put 'os.edition' 'VERIFIED' ([int]$rows[0].OperatingSystemSKU)
    } catch { foreach ($id in @('os.version','os.build','os.edition')) { Put $id 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' } }
    $arch=$env:PROCESSOR_ARCHITECTURE
    Put 'os.architecture' 'VERIFIED' $arch
    Put 'powershell.version' 'VERIFIED' $PSVersionTable.PSVersion.ToString()
    Put 'api.wfp_file' 'VERIFIED' ([IO.File]::Exists([IO.Path]::Combine($system,'fwpuclnt.dll')))
    try {
        $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
        try { $principal=New-Object Security.Principal.WindowsPrincipal $identity;Put 'security.admin_token' 'VERIFIED' ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'TOKEN_MEMBERSHIP_BOOL_ONLY' } finally {$identity.Dispose()}
    } catch { Put 'security.admin_token' 'MISSING' $null 'TOKEN_MEMBERSHIP_UNAVAILABLE' }
    try { Put 'startup.execution_policy' 'DETECTED' ([string](Microsoft.PowerShell.Security\Get-ExecutionPolicy)) 'READ_ONLY_NEVER_AUTO_BYPASS' }
    catch { Put 'startup.execution_policy' 'MISSING' $null 'EXECUTION_POLICY_UNAVAILABLE' }
    foreach ($pair in @(@('BFE','bfe.state'),@('MpsSvc','firewall.state'),@('Schedule','startup.scheduler'))) {
        try { $rows=Query 'Win32_Service' 'root/cimv2' ("Name='"+$pair[0]+"'") @('Name','State');if ($rows.Count -ne 1) {throw 'SERVICE_COUNT'};Put $pair[1] 'VERIFIED' ([string]$rows[0].State) }
        catch { Put $pair[1] 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' }
    }
    try {
        $rows=Query 'MSFT_NetFirewallProfile' 'root/standardcimv2' '' @('Enabled','DefaultOutboundAction')
        if (-not $rows.Count) { throw 'NO_PROFILE_DATA' }
        $enabled=@($rows | Where-Object {$_.Enabled -eq 1}).Count
        Put 'firewall.profiles' 'DETECTED' @{profile_count=$rows.Count;enabled_count=$enabled;default_outbound_codes=@($rows | ForEach-Object {[int]$_.DefaultOutboundAction})} 'SNAPSHOT_NOT_EFFECTIVE_WFP_PROOF'
    } catch { Put 'firewall.profiles' 'MISSING' $null 'REQUIRES_ELEVATION_OR_PROVIDER_UNAVAILABLE' }
    try {
        $gpo=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\Policies\Microsoft\WindowsFirewall',$false)
        $mdm=[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\Microsoft\PolicyManager\current\device\Firewall',$false)
        $value=@{gpo_present=($null -ne $gpo);mdm_present=($null -ne $mdm)}
        if ($gpo) {$gpo.Dispose()};if ($mdm) {$mdm.Dispose()}
        Put 'policy.management' 'DETECTED' $value 'PRESENCE_ONLY_NOT_POLICY_AUTHORITY'
    } catch { Put 'policy.management' 'MISSING' $null 'REQUIRES_ELEVATION_OR_PROVIDER_UNAVAILABLE' }
    try {
        $rows=Query 'AntiVirusProduct' 'root/SecurityCenter2' '' @('productState')
        Put 'security.products' 'DETECTED' @{count=$rows.Count;third_party_unresolved=$true} 'COUNT_NOT_EFFECTIVE_FILTER_PROOF'
    } catch { Put 'security.products' 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' }
    $names=Get-WuaCandidateNames $Config
    try {
        $count=0
        foreach ($role in @('client','broker')) {
            $rows=Query 'Win32_UserAccount' 'root/cimv2' ("LocalAccount=TRUE AND Name='"+$names[$role]+"'") @('Name')
            $count+=$rows.Count
        }
        if ($count) { Put 'accounts.collision_free' 'CONFLICT' $false 'TECHNICAL_NAME_ALREADY_EXISTS' } else { Put 'accounts.collision_free' 'VERIFIED' $true }
    } catch { Put 'accounts.collision_free' 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' }
    Put 'accounts.new_sid_binding' 'UNSUPPORTED' $null 'NEW_SIDS_RESOLVED_ONLY_DURING_FUTURE_APPLY'
    $used=@();$portSnapshotKnown=$false
    try {
        $tcp=Query 'MSFT_NetTCPConnection' 'root/standardcimv2' 'State=2' @('LocalPort')
        $udp=Query 'MSFT_NetUDPEndpoint' 'root/standardcimv2' '' @('LocalPort')
        $used=@($tcp | ForEach-Object {[int]$_.LocalPort})+@($udp | ForEach-Object {[int]$_.LocalPort});$portSnapshotKnown=$true
    } catch { Put 'endpoint.snapshot_free' 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' }
    if ($portSnapshotKnown) {
        $port=0;$selection='operator'
        if ($Config.Contains('local_port')) { $port=[int]$Config.local_port } else {
            $selection='snapshot_candidate';$seed=[Convert]::ToUInt32((Get-WuaHash @{owner=$Config.owner_id}).Substring(0,8),16)
            for ($i=0;$i -lt 16384;$i++) { $candidate=49152+[int](($seed+$i)%16384);if ($candidate -notin $used) {$port=$candidate;break} }
        }
        if (-not $port) { Put 'endpoint.local' 'CONFLICT' $null 'NO_UNUSED_CANDIDATE' }
        else {
            Put 'endpoint.local' 'VERIFIED' @{address='127.0.0.1';port=$port;selection=$selection} 'SNAPSHOT_CANDIDATE_NOT_PORT_RESERVATION'
            if ($port -in $used) { Put 'endpoint.snapshot_free' 'CONFLICT' $false 'PORT_ALREADY_IN_USE' } else { Put 'endpoint.snapshot_free' 'VERIFIED' $true 'SNAPSHOT_ONLY_NO_OWNER_GUARD' }
        }
    }
    foreach ($pair in @(@('MSFT_NetIPAddress','network.families'),@('MSFT_NetRoute','network.routes'))) {
        try {
            $rows=Query $pair[0] 'root/standardcimv2' '' @('AddressFamily')
            Put $pair[1] 'DETECTED' @{v4_count=@($rows | Where-Object {$_.AddressFamily -eq 2}).Count;v6_count=@($rows | Where-Object {$_.AddressFamily -eq 23}).Count} 'COUNTS_ONLY_NO_ADDRESSES'
        } catch { Put $pair[1] 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' }
    }
    try {
        $adapters=Query 'MSFT_NetAdapter' 'root/standardcimv2' '' @('InterfaceOperationalStatus')
        Put 'network.interfaces' 'DETECTED' @{count=$adapters.Count;connected_count=@($adapters | Where-Object {$_.InterfaceOperationalStatus -eq 1}).Count} 'COUNTS_ONLY_NO_NAMES_OR_IDENTIFIERS'
    } catch { Put 'network.interfaces' 'MISSING' $null 'LOCAL_QUERY_UNAVAILABLE' }
    Put 'network.proxy_context' 'REQUIRES_USER_INPUT' $null 'NO_ENV_OR_PROXY_SECRET_VALUES_READ'
    $files=@(@('broker_exe','broker.binary','PE'),@('client_exe','mcp.binary','PE'),@('source_archive','mcp.source_archive','ARCHIVE'),@('stdio_exe','mcp.stdio_exe','PE'),@('stdio_script','mcp.stdio_script','TEXT'))
    foreach ($item in $files) {
        $selectedPath=$null
        if ($Config.paths.Contains($item[0])) {$selectedPath=$Config.paths[$item[0]]}
        elseif ($item[0] -in @('broker_exe','client_exe')) {
            $roleLocal=if ($item[0] -eq 'client_exe') {'client'} else {'broker'}
            $candidates=Find-BinaryCandidates $roleLocal
            if ($candidates.Count -gt 1) {Put $item[1] 'CONFLICT' $null 'MULTIPLE_CANDIDATES_REQUIRE_LOCAL_SELECTION';continue}
            if ($candidates.Count -eq 1) {$selectedPath=$candidates[0]}
        }
        if (-not $selectedPath) { Put $item[1] 'REQUIRES_USER_INPUT' $null 'SAFE_LOCAL_PATH_NOT_FOUND_OR_SUPPLIED';continue }
        try {
            $meta=Get-WuaFileMetadata $selectedPath $item[2];$status='VERIFIED';$detail='STATIC_HASH_ONLY'
            if ($item[2] -eq 'PE' -and $meta.format -ne 'PE_AMD64') { $status='UNSUPPORTED';$detail='PE_AMD64_REQUIRED' }
            if ($item[0] -eq 'source_archive' -and ($meta.bytes -ne 239841 -or $meta.sha256 -cne '88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0')) { $status='CONFLICT';$detail='EXACT_SOURCE_ARCHIVE_MISMATCH' }
            Put $item[1] $status $meta $detail
            if ($item[0] -in @('broker_exe','client_exe')) {
                $versionId=if ($item[0] -eq 'broker_exe') {'broker.version'} else {'mcp.version'}
                if ($meta.version_metadata -eq 'unavailable') { Put $versionId 'REQUIRES_USER_INPUT' $null 'NO_TRUSTED_VERSION_METADATA' }
                else { Put $versionId 'DETECTED' $meta.version_metadata 'FILE_METADATA_NOT_NATIVE_VERSION_PROOF' }
            }
        } catch { Put $item[1] 'MISSING' $null 'LOCAL_FILE_UNAVAILABLE_OR_UNSAFE' }
    }
    foreach ($pair in @(@('resources_root','mcp.resources'),@('working_directory','mcp.working_directory'),@('deployment_root','files.deployment_root'))) {
        if (-not $Config.paths.Contains($pair[0])) { Put $pair[1] 'REQUIRES_USER_INPUT' $null 'PATH_NOT_SUPPLIED';continue }
        $local=Assert-WuaLocalPath $Config.paths[$pair[0]] -AllowMissing
        $exists=[IO.Directory]::Exists($local);$isRoot=([IO.Path]::GetPathRoot($local).TrimEnd('\') -ceq $local.TrimEnd('\'))
        $status='DETECTED';if ($isRoot -or ($pair[0] -eq 'deployment_root' -and ($exists -or [IO.File]::Exists($local)))) {$status='CONFLICT'}
        Put $pair[1] $status @{supplied=$true;local=$true;exists=$exists;reparse_free=$true;is_root=$isRoot} 'ROLE_REFERENCE_ONLY_NO_PRIVATE_PATH_EXPORT'
    }
    if ($Config.Contains('startup_mode')) {
        Put 'startup.mode' 'DETECTED' $Config.startup_mode 'DESIGN_NOT_REGISTERED'
        Put 'accounts.logon_rights' 'DETECTED' @{mode=$Config.startup_mode;interactive=$false;admin=$false} 'DESIGN_NOT_ASSIGNED'
    }
    Put 'startup.dependencies' 'DETECTED' @{deny_before_start=$true;activation_separate_gate=$true} 'DESIGN_NOT_REGISTERED'
    Put 'files.acl_contract' 'DETECTED' @{scope='owned_resources_only';workspace_wide=$false} 'DESIGN_NOT_APPLIED'
    Put 'ownership.baseline' 'DETECTED' @{owner_guid_valid=$true;path_collision_known=$facts.ContainsKey('files.deployment_root');port_snapshot_only=$true} 'DESIGN_NO_RESOURCES_CREATED'
    Put 'ledger.backend' 'UNSUPPORTED' $null 'PROVISIONING_BACKEND_NOT_IMPLEMENTED'
    Put 'broker.schema' 'REQUIRES_USER_INPUT' $null 'OFFLINE_VERSIONED_SCHEMA_REVIEW_REQUIRED'
    if ($Config.Contains('remote_endpoint')) { Put 'broker.remote_endpoint' 'DETECTED' @{specified=$true;address_kind='literal_ipv4';port_specified=$true} 'PRIVATE_OPERATOR_INPUT_NOT_ROUTE_PROOF' }
    Put 'broker.remote_identity' 'REQUIRES_USER_INPUT' $null 'AUTHENTICATED_SERVER_PROOF_REQUIRED'
    Put 'mcp.launcher_hold' 'REQUIRES_USER_INPUT' $null 'PRESERVE_EXISTING_HOLD_NO_LAUNCHER_EXECUTION'
    return New-WuaInventory $Config $facts 'local_readonly'
}
