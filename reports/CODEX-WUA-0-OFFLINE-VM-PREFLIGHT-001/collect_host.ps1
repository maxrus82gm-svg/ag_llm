$ErrorActionPreference = 'Stop'
$outPath = Join-Path $PSScriptRoot 'host_inventory.json'
if (Test-Path -LiteralPath $outPath) { throw 'Refuse to overwrite first inventory' }
$errorsFound = [System.Collections.Generic.List[object]]::new()
function Read-SafeQuery($label, $query) {
    try { & $query } catch { $errorsFound.Add([ordered]@{source=$label;exception=$_.Exception.GetType().FullName;hresult=$_.Exception.HResult}); @() }
}
$os = Read-SafeQuery 'Win32_OperatingSystem' { Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture }
$system = Read-SafeQuery 'Win32_ComputerSystem' { Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,HypervisorPresent,TotalPhysicalMemory }
$cpu = Read-SafeQuery 'Win32_Processor' { Get-CimInstance Win32_Processor | Select-Object Name,AddressWidth,VirtualizationFirmwareEnabled,VMMonitorModeExtensions,SecondLevelAddressTranslationExtensions }
$features = Read-SafeQuery 'Win32_OptionalFeature' { Get-CimInstance Win32_OptionalFeature | Where-Object {$_.Name -match 'Hyper-V|Hypervisor|VirtualMachinePlatform|Subsystem-Linux|DisposableClientVM|Containers'} | Select-Object Name,InstallState }
$stateSchema = Read-SafeQuery 'Win32_OptionalFeature.InstallState qualifiers' {
    $prop=(Get-CimClass Win32_OptionalFeature).CimClassProperties['InstallState']
    @($prop.Qualifiers | Where-Object {$_.Name -in @('ValueMap','Values')} | ForEach-Object { [ordered]@{name=$_.Name;value=$_.Value} })
}
$products = @()
foreach ($registryRoot in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')) {
    if (Test-Path -LiteralPath $registryRoot) {
        $products += @(Read-SafeQuery 'filtered installed virtualization products' {
            Get-ItemProperty -Path ($registryRoot+'\*') -ErrorAction Stop | Where-Object {$_.DisplayName -match 'VirtualBox|VMware|QEMU|Hyper-V|Parallels|Docker Desktop'} | Select-Object DisplayName,DisplayVersion,InstallLocation,Publisher
        })
    }
}
$services = Read-SafeQuery 'filtered virtualization services' { Get-CimInstance Win32_Service | Where-Object {$_.Name -match '^(vmms|vmcompute|VBox.*|VMAuthdService|VMnet.*|VMUSBArbService)$'} | Select-Object Name,State,StartMode }
$drivers = Read-SafeQuery 'filtered virtualization drivers' { Get-CimInstance Win32_SystemDriver | Where-Object {$_.Name -match '^(VBox.*|vmx86|vmnet.*|vmmemctl|vmmouse|vmhgfs)$'} | Select-Object Name,State,StartMode }
$modules = Read-SafeQuery 'Hyper-V module metadata' { Get-Module -ListAvailable -Name Hyper-V | Select-Object Name,Version,Path }
$paths = @(
 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe',
 'C:\Program Files\VMware\VMware Workstation\vmware.exe',
 'C:\Program Files (x86)\VMware\VMware Workstation\vmware.exe',
 'C:\Program Files\qemu\qemu-system-x86_64.exe',
 'C:\Windows\System32\WindowsSandbox.exe',
 'C:\Windows\System32\vmms.exe',
 'C:\Windows\System32\vmcompute.exe'
)
$binaries = foreach ($p in $paths) {
    $exists=Test-Path -LiteralPath $p -PathType Leaf
    $version=if ($exists) {(Get-Item -LiteralPath $p).VersionInfo.FileVersion} else {$null}
    [ordered]@{path=$p;exists=$exists;file_version=$version;executed=$false}
}
$result=[ordered]@{
 task_id='CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001';collected_utc=[DateTime]::UtcNow.ToString('o')
 os=@($os);system=@($system);cpu=@($cpu);features=@($features);install_state_schema=@($stateSchema)
 installed_virtualization_products=@($products);services=@($services);drivers=@($drivers);hyperv_modules=@($modules)
 known_binary_paths=@($binaries);query_errors=@($errorsFound);mutations=0;product_commands_executed=0
 limitation='Read-only bounded metadata; no VM enumeration through a hypervisor daemon, no elevation, no network probes.'
}
$result | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $outPath -Encoding utf8NoBOM
$result | ConvertTo-Json -Depth 9
