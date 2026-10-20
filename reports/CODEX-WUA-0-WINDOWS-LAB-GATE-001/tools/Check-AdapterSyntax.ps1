# Parse source only in Windows PowerShell 5.1. Never invoke either adapter.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$rows=@();$bad=@()
$allow=@('Split-Path','Join-Path','Import-Module','LocalQuery','Get-CimInstance','Get-Module','ForEach-Object','Where-Object','Get-ChildItem','ConvertTo-Json','Write-Output','Save','Get-Item','Get-FileHash','Get-Content','ConvertFrom-Json','Get-Command','Hyper-V\Get-VM','DigestText','Core')
foreach($name in @('Collect-Host.ps1','Read-HyperVApproved.ps1')){
    $path=Join-Path $root ('adapters/'+$name);$tokens=$null;$errorsFound=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errorsFound)
    $commands=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true)|ForEach-Object {$_.GetCommandName()}|Where-Object {$_}|Sort-Object -Unique)
    $unknown=@($commands|Where-Object {$_ -notin $allow});$bad+=@($errorsFound);$bad+=@($unknown)
    $dynamic=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst] -and $null -eq $n.GetCommandName()},$true)).Count
    $rows+=@{source=('adapters/'+$name);sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();parse_errors=@($errorsFound).Count;unknown_named_commands=$unknown;named_commands=$commands;dynamic_invocations=$dynamic}
}
$record=@{runtime=$PSVersionTable.PSVersion.ToString();files=$rows;parse_only=$true;adapters_invoked=0;scope='Static named-command allowlist plus manual review of fixed Hyper-V selector whitelist and .NET file APIs; not a runtime or OS isolation proof';status=$(if($bad.Count -eq 0){'PASS'}else{'FAIL'})}
$out=Join-Path $root 'evidence/ps51_syntax.json'
$s=[IO.File]::Open($out,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$b=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 12));$s.Write($b,0,$b.Length)}finally{$s.Dispose()}
Write-Output $record.status
if($bad.Count -ne 0){exit 1}
