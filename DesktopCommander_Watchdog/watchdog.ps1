param(
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Config = Get-Content -LiteralPath (Join-Path $Root 'config.json') -Raw | ConvertFrom-Json
$LogDir = Join-Path $Root 'logs'
$LogPath = Join-Path $LogDir 'watchdog.log'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Get-RemoteProcess {
    $nodes = Get-CimInstance Win32_Process -Filter "Name='node.exe'"
    $match = $nodes | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match '@wonderwhy-er[\\/]desktop-commander[\\/].*dist[\\/]index\.js' -and
        $_.CommandLine -match ' remote( |$)'
    } | Sort-Object ProcessId | Select-Object -First 1
    return $match
}

function Get-RemoteState {
    $proc = Get-RemoteProcess
    if (-not $proc) {
        return [pscustomobject]@{ Status='OFFLINE'; Pid=$null; Connections=0; Reason='remote process not found' }
    }
    $tcp = @(Get-NetTCPConnection -OwningProcess $proc.ProcessId -State Established -ErrorAction SilentlyContinue |
        Where-Object { $_.RemotePort -eq 443 })
    if ($tcp.Count -gt 0) {
        return [pscustomobject]@{ Status='ONLINE'; Pid=$proc.ProcessId; Connections=$tcp.Count; Reason='TLS channel established' }
    }
    return [pscustomobject]@{ Status='OFFLINE'; Pid=$proc.ProcessId; Connections=0; Reason='no established TLS channel' }
}

$lastStatus = ''
Write-Host 'Desktop Commander Watchdog V1 - monitor only'
Write-Host "Expected device: $($Config.expectedDeviceName)"
Write-Host "Poll interval: $($Config.pollSeconds)s"
Write-Host 'No restart / no Enter actions are enabled yet.'
Write-Host ''

do {
    try {
        $state = Get-RemoteState
        $now = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        $line = "[$now] $($state.Status) pid=$($state.Pid) tls=$($state.Connections) - $($state.Reason)"
        Write-Host $line
        if ($state.Status -ne $lastStatus) {
            Add-Content -LiteralPath $LogPath -Value $line
            $lastStatus = $state.Status
        }
    }
    catch {
        $now = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        $line = "[$now] UNKNOWN - $($_.Exception.Message)"
        Write-Host $line
        if ('UNKNOWN' -ne $lastStatus) {
            Add-Content -LiteralPath $LogPath -Value $line
            $lastStatus = 'UNKNOWN'
        }
    }
    if (-not $Once) { Start-Sleep -Seconds ([int]$Config.pollSeconds) }
} while (-not $Once)
