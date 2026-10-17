$ErrorActionPreference = 'Stop'
$outRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$tools = @('go','docker','podman','WindowsSandbox','hcsdiag','Get-VM','Get-Container')
$commands = foreach ($name in $tools) {
    $found = Get-Command $name -ErrorAction SilentlyContinue
    [pscustomobject]@{name=$name; present=($null -ne $found); path=if($found){$found.Source}else{$null}}
}
$features = @(Get-CimInstance Win32_OptionalFeature -Filter "Name='Containers' OR Name='Microsoft-Hyper-V' OR Name='VirtualMachinePlatform' OR Name='Containers-DisposableClientVM' OR Name='Microsoft-Windows-Subsystem-Linux'" | Select-Object Name,InstallState)
$wslExit = $null
if (Test-Path -LiteralPath 'C:\Windows\System32\wsl.exe') {
    $probe = Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList '--status' -WindowStyle Hidden -Wait -PassThru
    $wslExit = $probe.ExitCode
}
$processes = @(Get-CimInstance Win32_Process -Filter "Name='tunnel-client.exe' OR Name='cloudflared.exe'" | ForEach-Object {
    [pscustomobject]@{name=$_.Name;pid=$_.ProcessId}
})
$data = [ordered]@{
    timestamp_utc=[DateTime]::UtcNow.ToString('o')
    scope='Read-only presence/feature inventory. No VM/container/client started; wsl --status only.'
    os_version=[Environment]::OSVersion.Version.ToString()
    commands=@($commands)
    windows_sandbox_binary_present=(Test-Path -LiteralPath 'C:\Windows\System32\WindowsSandbox.exe')
    wsl_status_exit=$wslExit
    optional_features_numeric_state=$features
    existing_tunnel_processes=$processes
    isolation_proven=$false
    limitations=@('PATH and standard locations only; not exhaustive whole-machine inventory',
        'Inventory is not evidence of an enforced egress boundary',
        'No feature, network, firewall, permission, registry or proxy changes')
}
$target = Join-Path $outRoot 'environment_inventory.json'
[IO.File]::WriteAllText($target, ($data | ConvertTo-Json -Depth 8) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
$data | ConvertTo-Json -Depth 8
