# Targeted observation only. No elevation, listeners, tracing or configuration writes.
$ErrorActionPreference = 'Stop'
$rows = [System.Collections.Generic.List[object]]::new()
function Record([string]$id, [scriptblock]$probe) {
    try {
        $value = & $probe
        $rows.Add([ordered]@{id=$id; classification='OBSERVED_READ_ONLY'; status='OBSERVED'; value=$value})
    } catch {
        # Never serialize raw exceptions, host paths, users, SIDs or provider dumps.
        $category = [string]$_.CategoryInfo.Category
        $rows.Add([ordered]@{id=$id; classification='BLOCKED'; status='QUERY_UNAVAILABLE'; error_category=$category})
    }
}
Record 'shell' { [ordered]@{version=$PSVersionTable.PSVersion.ToString(); edition=$PSVersionTable.PSEdition; process_64bit=[Environment]::Is64BitProcess; os_64bit=[Environment]::Is64BitOperatingSystem} }
Record 'os' {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem -Property Caption,Version,BuildNumber,OSArchitecture
    [ordered]@{caption=$os.Caption; version=$os.Version; build=$os.BuildNumber; architecture=$os.OSArchitecture}
}
Record 'current_token' {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        $principal = [Security.Principal.WindowsPrincipal]::new($identity)
        [ordered]@{administrator_role=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator); system=$identity.IsSystem; authenticated=$identity.IsAuthenticated}
    } finally { $identity.Dispose() }
}
foreach ($cmd in @('Get-LocalUser','Get-Acl','Get-NetFirewallProfile','Get-NetFirewallRule','Get-NetFirewallSecurityFilter','Get-Service')) {
    $name = $cmd
    Record ('command_'+$name) { [ordered]@{available=($null -ne (Get-Command -Name $name -ErrorAction SilentlyContinue))} }
}
foreach ($account in @('wua-client','wua-broker')) {
    Record ('account_'+$account) {
        if (-not (Get-Command Get-LocalUser -ErrorAction SilentlyContinue)) { throw [NotSupportedException]::new() }
        try {
            $item = Get-LocalUser -Name $account
            [ordered]@{exists=$true; enabled=$item.Enabled; local_sid_shape=([string]$item.SID -match '^S-1-5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+$')}
        } catch {
            if ([string]$_.CategoryInfo.Category -eq 'ObjectNotFound') { [ordered]@{exists=$false} } else { throw }
        }
    }
}
foreach ($service in @('BFE','MpsSvc')) {
    Record ('service_'+$service) { $item=Get-Service -Name $service; [ordered]@{state=[string]$item.Status} }
}
Record 'firewall_profiles' {
    # Exactly profile settings, never rule/security-filter enumeration.
    @(Get-NetFirewallProfile | ForEach-Object { [ordered]@{name=[string]$_.Name; enabled=[string]$_.Enabled; default_inbound=[string]$_.DefaultInboundAction; default_outbound=[string]$_.DefaultOutboundAction} })
}
[ordered]@{schema=1; task='CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001'; collected_utc=[DateTime]::UtcNow.ToString('o'); scope='LOCAL_TARGETED_READ_ONLY'; observations=@($rows.ToArray()); native_network_tests_run=0; system_mutations_requested=0} | ConvertTo-Json -Depth 8
