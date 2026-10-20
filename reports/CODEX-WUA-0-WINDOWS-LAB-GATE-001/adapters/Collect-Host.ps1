# Bounded trusted local CIM/module/file metadata only. No VM query/activation or network.
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$out=[IO.Path]::GetFullPath($OutputPath)
if (-not $out.StartsWith(($taskRoot+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase) -or [IO.File]::Exists($out)) {throw 'OUTPUT_SCOPE'}
if (-not [Environment]::Is64BitProcess) {throw '64BIT_REQUIRED'}
Import-Module (Join-Path $PSHOME 'Modules/CimCmdlets/CimCmdlets.psd1') -ErrorAction Stop
$errorsFound=@()
function LocalQuery([string]$Class,[string]$Filter,[string[]]$Properties){
    try { if ($Filter) { @(Get-CimInstance -Namespace root/cimv2 -ClassName $Class -Filter $Filter -Property $Properties -OperationTimeoutSec 8 -ErrorAction Stop) } else { @(Get-CimInstance -Namespace root/cimv2 -ClassName $Class -Property $Properties -OperationTimeoutSec 8 -ErrorAction Stop) } }
    catch {$script:errorsFound+=@{query=$Class;status='BLOCKED';error_class=$_.Exception.GetType().Name};@()}
}
$os=@(LocalQuery 'Win32_OperatingSystem' '' @('Version','BuildNumber','OperatingSystemSKU'))
$system=@(LocalQuery 'Win32_ComputerSystem' '' @('HypervisorPresent'))
$cpu=@(LocalQuery 'Win32_Processor' '' @('AddressWidth','VirtualizationFirmwareEnabled','VMMonitorModeExtensions','SecondLevelAddressTranslationExtensions'))
$features=@(LocalQuery 'Win32_OptionalFeature' "Name LIKE 'Microsoft-Hyper-V%' OR Name='VirtualMachinePlatform' OR Name='HypervisorPlatform' OR Name='Containers-DisposableClientVM'" @('Name','InstallState'))
$services=@(LocalQuery 'Win32_Service' "Name='vmms' OR Name='vmcompute'" @('Name','State'))
$moduleRoot=Join-Path ([Environment]::GetFolderPath('System')) 'WindowsPowerShell/v1.0/Modules/Hyper-V'
$modulePresent=[IO.Directory]::Exists($moduleRoot)
$commands=@();$moduleVersions=@()
if ($modulePresent) {
    # Metadata only: not Import-Module, not Get-VM, no auto-loading by command name.
    $found=@(Get-Module -ListAvailable -Name (Join-Path $moduleRoot '*'))
    $moduleVersions=@($found | ForEach-Object {$_.Version.ToString()})
    $commands=@($found | ForEach-Object {$_.ExportedCommands.Keys} | Where-Object {$_ -in @('Get-VM','Get-VMNetworkAdapter','Get-VMIntegrationService','Get-VMHardDiskDrive','Get-VMDvdDrive','Get-VMComPort','Get-VMSnapshot','Get-VMHost','Get-VMAssignableDevice','Get-VMFibreChannelHba','Get-VMGpuPartitionAdapter')})
}
$toolchain=@{}
foreach($pair in @(@('framework_csc',(Join-Path $env:SystemRoot 'Microsoft.NET/Framework64/v4.0.30319/csc.exe')),@('hyperv_manager',(Join-Path ([Environment]::GetFolderPath('System')) 'virtmgmt.msc')),@('vmware','C:/Program Files (x86)/VMware/VMware Workstation/vmware.exe'),@('virtualbox','C:/Program Files/Oracle/VirtualBox/VirtualBox.exe'),@('qemu','C:/Program Files/qemu/qemu-system-x86_64.exe'))){$toolchain[$pair[0]]=[IO.File]::Exists($pair[1])}
$mediaRoot=Join-Path $taskRoot 'assets'
$media=@();if([IO.Directory]::Exists($mediaRoot)){$media=@(Get-ChildItem -LiteralPath $mediaRoot -File | Where-Object {$_.Extension -in @('.iso','.wim','.esd','.vhdx')})}
$record=@{schema=1;source='bounded_local_readonly';collected_utc=[DateTime]::UtcNow.ToString('o');runtime=$PSVersionTable.PSVersion.ToString();architecture=$env:PROCESSOR_ARCHITECTURE;
    os=@($os|ForEach-Object {@{version=$_.Version;build=$_.BuildNumber;sku=$_.OperatingSystemSKU}});
    hypervisor_present=@($system|ForEach-Object {$_.HypervisorPresent});cpu=@($cpu|ForEach-Object {@{address_width=$_.AddressWidth;firmware_virtualization=$_.VirtualizationFirmwareEnabled;vm_monitor_extensions=$_.VMMonitorModeExtensions;slat=$_.SecondLevelAddressTranslationExtensions}});
    optional_feature_codes=@($features|ForEach-Object {@{component=$_.Name;raw_state_code=$_.InstallState}});services=@($services|ForEach-Object {@{service=$_.Name;state=$_.State}});
    hyperv_module_present=$modulePresent;hyperv_module_versions=$moduleVersions;exported_readonly_commands=$commands;known_tool_locations=$toolchain;
    approved_vm_guid_supplied=$false;existing_vm_queries=0;lab_status='LAB_NOT_PROVISIONED';lab_existence_scope='No approved VM identity supplied; unrelated VMs not enumerated';trusted_media_candidates_in_task_assets=$media.Count;trusted_media_verified=$false;
    query_errors=$errorsFound;vm_adapter_status='NOT RUN';host_config_proof='PENDING';guest_proof='PENDING';native_execution='BLOCKED';mutations=0;
    limits='Bounded paths only; absence outside these paths not established. Feature codes/module presence are not readiness proof. No remote CIM session, network, private VM config or working V2Ray read.'}
$stream=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 12));$stream.Write($b,0,$b.Length)}finally{$stream.Dispose()}
Write-Output 'BOUNDED HOST READ-ONLY INVENTORY SAVED; VM QUERIES 0'
