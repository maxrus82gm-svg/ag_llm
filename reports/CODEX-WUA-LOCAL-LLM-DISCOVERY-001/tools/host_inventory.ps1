$ErrorActionPreference = 'Stop'
$diagRoot = Split-Path -Parent $PSScriptRoot
$diagNow = [DateTime]::UtcNow.ToString('o')
function Clean-PathValue([string]$Value) {
    if (-not $Value) { return $null }
    return $Value.Replace($env:USERPROFILE, '%USERPROFILE%')
}
$diagOs = Get-CimInstance Win32_OperatingSystem
$diagCpu = @(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,LoadPercentage)
$diagGpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,Status)
$diagDisks = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,Size,FreeSpace)
$diagIps = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '169.254.*' } | Select-Object IPAddress,InterfaceAlias,PrefixLength)
$diagListen = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in @(8000,11434) } | Select-Object LocalAddress,LocalPort,OwningProcess)
$diagPids = @($diagListen | Select-Object -ExpandProperty OwningProcess)
$diagProcs = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'ollama|colibri|^coli\.|llama' -or $_.ProcessId -in $diagPids } | ForEach-Object {
    $diagVersion = $null
    if ($_.ExecutablePath -and (Test-Path -LiteralPath $_.ExecutablePath)) {
        $diagVersion = (Get-Item -LiteralPath $_.ExecutablePath).VersionInfo.FileVersion
    }
    $diagVerb = $null
    if ($_.Name -match '^ollama' -and $_.CommandLine -match '(?i)\b(serve|pull|runner|run|list|ps)\b') { $diagVerb = $Matches[1] }
    [pscustomobject]@{Pid=$_.ProcessId; ParentPid=$_.ParentProcessId; Name=$_.Name; Executable=(Clean-PathValue $_.ExecutablePath); FileVersion=$diagVersion; OllamaVerbOnly=$diagVerb; ExecutableUnavailable=(-not $_.ExecutablePath)}
})
$diagServices = @(Get-CimInstance Win32_Service | Where-Object { $_.Name -match 'ollama|colibri' -or $_.ProcessId -in $diagPids } | Select-Object Name,State,StartMode,ProcessId)
$diagCommands = @(foreach ($diagName in @('ollama','coli','colibri','llama-server','nvidia-smi')) {
    $diagCmd = Get-Command $diagName -ErrorAction SilentlyContinue
    if ($diagCmd) { [pscustomobject]@{Name=$diagName; Path=(Clean-PathValue $diagCmd.Source)} }
})
$diagEnv = @{}
foreach ($diagName in @('OLLAMA_HOST','OLLAMA_MODELS','OLLAMA_NUM_PARALLEL','OLLAMA_MAX_LOADED_MODELS','OLLAMA_KEEP_ALIVE','OLLAMA_CONTEXT_LENGTH')) {
    $diagValue = [Environment]::GetEnvironmentVariable($diagName, 'Process')
    $diagEnv[$diagName] = (Clean-PathValue $diagValue)
}
$diagInstall = @(foreach ($diagReg in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
    Get-ItemProperty -Path $diagReg -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'Ollama|Colibri' } | Select-Object DisplayName,DisplayVersion,Publisher
})
$diagModels = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { Join-Path $env:USERPROFILE '.ollama\models' }
$diagManifests = @()
$diagPartial = @()
if (Test-Path -LiteralPath (Join-Path $diagModels 'manifests')) {
    $diagManifests = @(Get-ChildItem -LiteralPath (Join-Path $diagModels 'manifests') -File -Recurse | Select-Object -First 100 | ForEach-Object { [pscustomobject]@{RelativePath=$_.FullName.Substring($diagModels.Length+1); Bytes=$_.Length; UpdatedUtc=$_.LastWriteTimeUtc.ToString('o')} })
}
if (Test-Path -LiteralPath (Join-Path $diagModels 'blobs')) {
    $diagPartial = @(Get-ChildItem -LiteralPath (Join-Path $diagModels 'blobs') -File -Filter '*partial*' | Select-Object -First 100 | ForEach-Object { [pscustomobject]@{Name=$_.Name; Bytes=$_.Length; UpdatedUtc=$_.LastWriteTimeUtc.ToString('o')} })
}
$diagNvidia = $null
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $diagNvidia = (& nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu,driver_version --format=csv,noheader,nounits 2>&1 | Out-String).Trim()
}
$diagResult = [ordered]@{time_utc=$diagNow; host_scope='DIAGNOSTIC HOST ONLY; remote 192.168.0.77 resources not inspected'; os=@{Caption=$diagOs.Caption; Version=$diagOs.Version; Build=$diagOs.BuildNumber; Architecture=$diagOs.OSArchitecture; TotalMemoryKiB=$diagOs.TotalVisibleMemorySize; FreeMemoryKiB=$diagOs.FreePhysicalMemory}; ipv4=$diagIps; cpu=$diagCpu; gpu=$diagGpu; nvidia_gpu_query=$diagNvidia; fixed_logical_disks=$diagDisks; listeners=$diagListen; processes=$diagProcs; matching_services=$diagServices; commands=$diagCommands; selected_nonsecret_process_environment=$diagEnv; installed_app_metadata=$diagInstall; default_or_configured_model_path=(Clean-PathValue $diagModels); local_model_manifest_metadata=$diagManifests; local_partial_blob_metadata=$diagPartial; limits=@('No process command lines or general environment dump saved','No secret values read','Null executable is unavailable, not proof of no executable','Win32 AdapterRAM can be inaccurate for >4GB; nvidia-smi preferred','No remote administrative access','Service enumeration does not cover containers, WSL, other users or every startup mechanism')}
[IO.Directory]::CreateDirectory((Join-Path $diagRoot 'evidence')) | Out-Null
[IO.File]::WriteAllText((Join-Path $diagRoot 'evidence/host_inventory.json'), ($diagResult | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
Write-Output ($diagResult | ConvertTo-Json -Depth 8)
