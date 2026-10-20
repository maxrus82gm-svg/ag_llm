# Future local read-only adapter. NOT executed in this TASK: no approved owned VM exists.
param([Parameter(Mandatory=$true)][Guid]$ApprovedVmGuid,[Parameter(Mandatory=$true)][Guid]$ApprovedOwner,
      [Parameter(Mandatory=$true)][string]$PermissionFile,[Parameter(Mandatory=$true)][string]$PermissionSha256,
      [Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$out=[IO.Path]::GetFullPath($OutputPath)
if (-not $out.StartsWith(($taskRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase) -or [IO.File]::Exists($out)) {throw 'OUTPUT_SCOPE'}
function DigestText([string]$text){$h=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($text)))).Replace('-','').ToLowerInvariant()}finally{$h.Dispose()}}
function Save($value){$s=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$b=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 12));$s.Write($b,0,$b.Length)}finally{$s.Dispose()}}
$module=Join-Path ([Environment]::GetFolderPath('System')) 'WindowsPowerShell/v1.0/Modules/Hyper-V/Hyper-V.psd1'
if (-not [IO.File]::Exists($module)) {Save @{status='NOT RUN';reason='HYPERV_MODULE_UNAVAILABLE';vm_queries=0;isolation_proof='BLOCKED';mutations=0};exit 20}
if ($ApprovedVmGuid -eq [Guid]::Empty -or $ApprovedOwner -eq [Guid]::Empty -or $PermissionSha256 -cnotmatch '^[0-9a-f]{64}$') {throw 'APPROVED_IDENTITY_REQUIRED'}
# Permission is a private, out-of-band user/verifier-authorized READ_ONLY record,
# never auto-generated/adopted from a name or VM Notes. Its digest is caller-pinned.
$permissionPath=[IO.Path]::GetFullPath($PermissionFile)
if ($permissionPath.StartsWith('\') -or $permissionPath -match '^[^:]+::|:[^\\/]+:' -or -not $permissionPath.StartsWith(($taskRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) {throw 'PERMISSION_LOCAL_SCOPE'}
$pathRoot=[IO.Path]::GetPathRoot($permissionPath)
if([IO.DriveInfo]::new($pathRoot).DriveType -notin @([IO.DriveType]::Fixed,[IO.DriveType]::Removable)){throw 'PERMISSION_VOLUME_UNSAFE'}
$cursor=$pathRoot
foreach($segment in $permissionPath.Substring($pathRoot.Length).Split([IO.Path]::DirectorySeparatorChar)){
    $cursor=Join-Path $cursor $segment
    if(([IO.File]::GetAttributes($cursor) -band ([IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Offline)) -ne 0){throw 'PERMISSION_PATH_UNSAFE'}
}
$item=Get-Item -LiteralPath $permissionPath
if ($item.Length -gt 16384 -or (Get-FileHash -LiteralPath $permissionPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $PermissionSha256) {throw 'PERMISSION_PIN'}
$permission=Get-Content -LiteralPath $permissionPath -Raw | ConvertFrom-Json
if (@($permission.PSObject.Properties.Name).Count -ne 6 -or $permission.operation -cne 'READ_ONLY_EXISTING_OWNED_VM' -or $permission.vm_guid -cne $ApprovedVmGuid.ToString('D') -or $permission.owner -cne $ApprovedOwner.ToString('D') -or $permission.ownership_ledger_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $permission.independent_review_sha256 -cnotmatch '^[0-9a-f]{64}$') {throw 'PERMISSION_SCOPE'}
$expiry=[DateTimeOffset]::Parse($permission.valid_until)
if($expiry.Offset -ne [TimeSpan]::Zero -or $expiry -le [DateTimeOffset]::UtcNow -or $expiry -gt [DateTimeOffset]::UtcNow.AddMinutes(5)){throw 'PERMISSION_EXPIRED'}
$vmms=@(Get-CimInstance -Namespace root/cimv2 -ClassName Win32_Service -Filter "Name='vmms'" -Property State -OperationTimeoutSec 8)
if($vmms.Count -ne 1 -or $vmms[0].State -cne 'Running'){Save @{status='NOT RUN';reason='EXISTING_VMMS_NOT_RUNNING';vm_queries=0;mutations=0};exit 20}
Import-Module -Name $module -ErrorAction Stop
$selectors=@('Get-VM','Get-VMNetworkAdapter','Get-VMIntegrationService','Get-VMHardDiskDrive','Get-VMDvdDrive','Get-VMComPort','Get-VMSnapshot','Get-VMAssignableDevice','Get-VMFibreChannelHba','Get-VMGpuPartitionAdapter')
$available=@{};foreach($name in $selectors){$available[$name]=($null -ne (Get-Command -Name $name -Module Hyper-V -ErrorAction SilentlyContinue))}
if(-not $available['Get-VM']){throw 'READONLY_SELECTOR_UNAVAILABLE'}
$vm=Hyper-V\Get-VM -Id $ApprovedVmGuid -ErrorAction Stop
if($vm.Id -ne $ApprovedVmGuid){throw 'VM_GUID_MISMATCH'}
function Core($v){@{id=$v.Id.ToString('D');state=$v.State.ToString();generation=$v.Generation;version=$v.Version.ToString();config_location_ref=(DigestText ([string]$v.ConfigurationLocation))}|ConvertTo-Json -Compress}
$before=DigestText (Core $vm);$counts=@{};$errorsFound=@()
foreach($name in $selectors|Where-Object {$_ -ne 'Get-VM'}){
    if(-not $available[$name]){$counts[$name]=$null;continue}
    try{
        # VM objects originate exclusively from the exact local -Id query above.
        $command=Get-Command -Name $name -Module Hyper-V
        if(-not $command.Parameters.ContainsKey('VM')){throw 'EXACT_OBJECT_PARAMETER_UNAVAILABLE'}
        $rows=@(& $command -VM $vm -ErrorAction Stop)
        $counts[$name]=@{count=$rows.Count}
        if($name -eq 'Get-VMIntegrationService'){$counts[$name].enabled_count=@($rows|Where-Object {$_.Enabled}).Count}
        if($name -eq 'Get-VMComPort'){$counts[$name].configured_pipe_count=@($rows|Where-Object {$_.Path}).Count}
        if($name -in @('Get-VMHardDiskDrive','Get-VMDvdDrive')){
            # No Get-VHD/mount/backing traversal: an untrusted parent may be remote.
            $counts[$name].attachment_path_refs=@($rows|ForEach-Object {DigestText ([string]$_.Path)})
        }
    }catch{$errorsFound+=@{selector=$name;status='BLOCKED';error_class=$_.Exception.GetType().Name}}
}
$afterVm=Hyper-V\Get-VM -Id $ApprovedVmGuid -ErrorAction Stop
$after=DigestText (Core $afterVm)
Save @{schema=1;status=$(if($before -cne $after){'FAIL'}else{'PARTIAL'});vm_ref=(DigestText $ApprovedVmGuid.ToString('D'));owner_ref=(DigestText $ApprovedOwner.ToString('D'));core_digest_before=$before;core_digest_after=$after;selector_counts=$counts;query_errors=$errorsFound;
    device_census_complete=$false;channel_census_complete=$false;disk_chain_verified=$false;console_session_proof='PENDING';powershell_direct_proof='PENDING';guest_observer_proof='PENDING';full_config_watch_proof='PENDING';isolation_proof='BLOCKED';mutations=0;
    limits='Census counts and a stable core digest are partial metadata only. Integration counts do not prove absence of all relay channels. Pinned permission is access scope, not a signed isolation attestation.'}
