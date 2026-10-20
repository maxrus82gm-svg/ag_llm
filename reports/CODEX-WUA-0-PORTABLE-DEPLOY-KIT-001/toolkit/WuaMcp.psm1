# Portable PowerShell 5.1+ core. No command execution from input. No mutating backend.
Set-StrictMode -Version Latest
$script:KitRoot = $PSScriptRoot
$script:BackendImplemented = $false # Compile-time capability, never read from JSON.

function Assert-WuaPathSyntax {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2).Contains(':') -or $Path -match '[\x00-\x1f*?]') { throw 'LOCAL_PATH_REQUIRED' }
    foreach ($part in $Path.Substring(3).Split([char[]]'\/',[StringSplitOptions]::RemoveEmptyEntries)) {
        if ($part -in @('.','..') -or $part -match '[. ]$' -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)') { throw 'AMBIGUOUS_PATH_BLOCKED' }
    }
}

function Assert-WuaLocalPath {
    param([string]$Path,[switch]$AllowMissing)
    Assert-WuaPathSyntax $Path
    $full=[IO.Path]::GetFullPath($Path)
    $drive=New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($full))
    if ($drive.DriveType -notin @([IO.DriveType]::Fixed,[IO.DriveType]::Removable)) { throw 'NETWORK_OR_UNKNOWN_DRIVE_BLOCKED' }
    $current=[IO.Path]::GetPathRoot($full)
    foreach ($part in $full.Substring($current.Length).Split([char[]]'\/',[StringSplitOptions]::RemoveEmptyEntries)) {
        if ($part -match '[. ]$' -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)') { throw 'AMBIGUOUS_PATH_BLOCKED' }
        $current=[IO.Path]::Combine($current,$part)
        try { $attributes=[int][IO.File]::GetAttributes($current) }
        catch [IO.FileNotFoundException] {if ($AllowMissing) {continue};throw 'LOCAL_PATH_MISSING'}
        catch [IO.DirectoryNotFoundException] {if ($AllowMissing) {continue};throw 'LOCAL_PATH_MISSING'}
        catch {throw 'PATH_METADATA_UNAVAILABLE'}
        if (($attributes -band (0x400 -bor 0x1000 -bor 0x40000 -bor 0x400000)) -ne 0) { throw 'REPARSE_OR_CLOUD_PATH_BLOCKED' }
    }
    return $full
}

function ConvertTo-WuaMap {
    param($Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [Collections.IDictionary]) {
        $map=@{};foreach ($key in $Value.Keys) { $map[[string]$key]=ConvertTo-WuaMap $Value[$key] };return $map
    }
    if ($Value -is [Management.Automation.PSCustomObject]) {
        $map=@{};foreach ($p in $Value.PSObject.Properties) { $map[$p.Name]=ConvertTo-WuaMap $p.Value };return $map
    }
    if ($Value -is [Collections.IList]) { $items=@();foreach ($item in $Value) { $items+= ,(ConvertTo-WuaMap $item) };return ,$items }
    return $Value
}

function Assert-WuaJsonGrammar {
    param([string]$Text)
    if ($Text.Length -gt 2097152) { throw 'JSON_TOO_LARGE' }
    $pattern='\G\s*("(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9A-Fa-f]{4}))*"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false|null|[{}\[\]:,])'
    $tokens=New-Object Collections.Generic.List[string];$offset=0
    while ($offset -lt $Text.Length) {
        if ([string]::IsNullOrWhiteSpace($Text.Substring($offset))) { break }
        $match=[regex]::Match($Text.Substring($offset),$pattern,[Text.RegularExpressions.RegexOptions]::None,[TimeSpan]::FromSeconds(2))
        if (-not $match.Success) { throw 'INVALID_JSON_TOKEN' }
        $tokens.Add($match.Groups[1].Value);$offset+=$match.Length
        if ($tokens.Count -gt 50000) { throw 'JSON_TOKEN_LIMIT' }
    }
    $state=@{i=0;tokens=$tokens}
    function Read-WuaJsonValue([int]$Depth) {
        if ($Depth -gt 20 -or $state.i -ge $state.tokens.Count) { throw 'JSON_DEPTH_OR_EOF' }
        $token=$state.tokens[$state.i];$state.i++
        if ($token -eq '{') {
            $names=New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
            if ($state.i -lt $state.tokens.Count -and $state.tokens[$state.i] -eq '}') { $state.i++;return }
            while ($true) {
                if ($state.i -ge $state.tokens.Count -or -not $state.tokens[$state.i].StartsWith('"')) { throw 'JSON_OBJECT_KEY_REQUIRED' }
                $key=ConvertFrom-WuaJsonText $state.tokens[$state.i];$state.i++
                if (-not $names.Add($key)) { throw 'DUPLICATE_JSON_KEY' }
                if ($state.i -ge $state.tokens.Count -or $state.tokens[$state.i] -ne ':') { throw 'JSON_COLON_REQUIRED' };$state.i++
                Read-WuaJsonValue ($Depth+1)
                if ($state.i -ge $state.tokens.Count) { throw 'JSON_OBJECT_EOF' }
                $end=$state.tokens[$state.i];$state.i++
                if ($end -eq '}') { return };if ($end -ne ',') { throw 'JSON_OBJECT_SEPARATOR' }
            }
        } elseif ($token -eq '[') {
            if ($state.i -lt $state.tokens.Count -and $state.tokens[$state.i] -eq ']') { $state.i++;return }
            while ($true) {
                Read-WuaJsonValue ($Depth+1)
                if ($state.i -ge $state.tokens.Count) { throw 'JSON_ARRAY_EOF' }
                $end=$state.tokens[$state.i];$state.i++
                if ($end -eq ']') { return };if ($end -ne ',') { throw 'JSON_ARRAY_SEPARATOR' }
            }
        } elseif ($token -in @('}',']',':',',')) { throw 'JSON_VALUE_REQUIRED' }
    }
    Read-WuaJsonValue 0
    if ($state.i -ne $tokens.Count) { throw 'JSON_TRAILING_DATA' }
}

function Read-WuaJson {
    param([string]$Path)
    $local=Assert-WuaLocalPath $Path
    $file=Get-Item -LiteralPath $local -Force -ErrorAction Stop
    if ($file.Length -gt 2097152) { throw 'JSON_TOO_LARGE' }
    $text=[IO.File]::ReadAllText($local,[Text.Encoding]::UTF8)
    Assert-WuaJsonGrammar $text
    return ConvertTo-WuaMap (ConvertFrom-WuaJsonText $text)
}

function ConvertFrom-WuaJsonText {
    param([string]$Text)
    $parameters=@{InputObject=$Text;ErrorAction='Stop'}
    if ((Get-Command Microsoft.PowerShell.Utility\ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { $parameters.DateKind='String' }
    return Microsoft.PowerShell.Utility\ConvertFrom-Json @parameters
}

function ConvertTo-WuaCanonicalJson {
    param($Value)
    if ($null -eq $Value) { return 'null' }
    if ($Value -is [bool]) { if ($Value) { return 'true' };return 'false' }
    if ($Value -is [string]) {
        $b=New-Object Text.StringBuilder;[void]$b.Append('"')
        foreach ($c in $Value.ToCharArray()) {
            $n=[int]$c
            if ($n -eq 34) { [void]$b.Append('\"') } elseif ($n -eq 92) { [void]$b.Append('\\') }
            elseif ($n -lt 32 -or $n -gt 126) { [void]$b.Append(('\u{0:x4}' -f $n)) } else { [void]$b.Append($c) }
        }
        [void]$b.Append('"');return $b.ToString()
    }
    if ($Value -is [byte] -or $Value -is [int16] -or $Value -is [int32] -or $Value -is [int64] -or $Value -is [uint16] -or $Value -is [uint32] -or $Value -is [uint64]) { return $Value.ToString([Globalization.CultureInfo]::InvariantCulture) }
    if ($Value -is [Collections.IDictionary]) {
        [string[]]$keys=@($Value.Keys);[Array]::Sort($keys,[StringComparer]::Ordinal)
        $parts=@();foreach ($key in $keys) { $parts+=((ConvertTo-WuaCanonicalJson $key)+':'+(ConvertTo-WuaCanonicalJson $Value[$key])) };return '{'+($parts -join ',')+'}'
    }
    if ($Value -is [Collections.IList]) { $parts=@();foreach ($item in $Value) { $parts+= ,(ConvertTo-WuaCanonicalJson $item) };return '['+($parts -join ',')+']' }
    throw 'UNSUPPORTED_CANONICAL_TYPE'
}

function Get-WuaHash {
    param($Value)
    $data=[Text.Encoding]::UTF8.GetBytes((ConvertTo-WuaCanonicalJson $Value));$sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($data))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
}

function Write-WuaJson {
    param([string]$Path,$Value)
    $local=Assert-WuaLocalPath $Path -AllowMissing
    $parent=[IO.Path]::GetDirectoryName($local)
    if (-not [IO.Directory]::Exists($parent)) { throw 'OUTPUT_PARENT_MISSING' }
    $bytes=[Text.Encoding]::UTF8.GetBytes((ConvertTo-WuaCanonicalJson $Value)+[Environment]::NewLine)
    $stream=New-Object IO.FileStream ($local,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($bytes,0,$bytes.Length);$stream.Flush() } finally { $stream.Dispose() }
}

function Get-WuaContract {
    return Read-WuaJson ([IO.Path]::Combine($script:KitRoot,'contracts','requirements_manifest.json'))
}

function Assert-WuaKeys {
    param($Map,[string[]]$Allowed,[string[]]$Required=@())
    if ($Map -isnot [Collections.IDictionary]) { throw 'OBJECT_REQUIRED' }
    foreach ($k in $Map.Keys) { if ($k -cnotin $Allowed) { throw 'UNKNOWN_OR_CASE_MISMATCHED_KEY' } }
    foreach ($k in $Required) { if (-not $Map.Contains($k)) { throw 'REQUIRED_KEY_MISSING' } }
}

function Test-WuaInteger { param($Value) return ($Value -is [byte] -or $Value -is [int16] -or $Value -is [int32] -or $Value -is [int64]) }

function Assert-WuaConfiguration {
    param($Config)
    Assert-WuaKeys $Config @('schema_version','owner_id','local_port','remote_endpoint','paths','startup_mode','account_prefix','broker_schema_ref','remote_identity_ref') @('schema_version','owner_id','paths')
    if (-not (Test-WuaInteger $Config.schema_version) -or $Config.schema_version -ne 1) { throw 'CONFIG_VERSION_UNSUPPORTED' }
    $id=[Guid]::Empty;if ($Config.owner_id -isnot [string] -or -not [Guid]::TryParseExact($Config.owner_id,'D',[ref]$id) -or $id -eq [Guid]::Empty) { throw 'OWNER_GUID_REQUIRED' }
    Assert-WuaKeys $Config.paths @('client_exe','broker_exe','stdio_exe','stdio_script','source_archive','resources_root','working_directory','deployment_root')
    foreach ($v in $Config.paths.Values) { if ($v -isnot [string]) { throw 'PATH_STRING_REQUIRED' };Assert-WuaPathSyntax $v }
    if ($Config.paths.Contains('deployment_root') -and $Config.paths.deployment_root -match '^[A-Za-z]:[\\/]$') { throw 'DEPLOYMENT_ROOT_CANNOT_BE_DRIVE_ROOT' }
    if ($Config.Contains('local_port') -and ((-not (Test-WuaInteger $Config.local_port)) -or $Config.local_port -lt 1024 -or $Config.local_port -gt 65535)) { throw 'INVALID_PORT' }
    if ($Config.Contains('startup_mode') -and $Config.startup_mode -cnotin @('task_batch','service_wrapper')) { throw 'STARTUP_MODE_UNSUPPORTED' }
    if ($Config.Contains('account_prefix') -and ($Config.account_prefix -isnot [string] -or $Config.account_prefix -cnotmatch '^[a-z][a-z0-9]{0,3}$')) { throw 'ACCOUNT_PREFIX_INVALID' }
    foreach ($k in @('broker_schema_ref','remote_identity_ref')) { if ($Config.Contains($k) -and ($Config[$k] -isnot [string] -or $Config[$k] -cnotmatch '^[A-Za-z0-9_.-]{1,80}$')) { throw 'REFERENCE_INVALID' } }
    if ($Config.Contains('remote_endpoint')) {
        $e=$Config.remote_endpoint;Assert-WuaKeys $e @('address','port','transport') @('address','port','transport')
        $ip=$null
        if ($e.address -isnot [string] -or -not [Net.IPAddress]::TryParse($e.address,[ref]$ip) -or $ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or $ip.ToString() -cne $e.address -or [Net.IPAddress]::IsLoopback($ip) -or $e.address -eq '0.0.0.0' -or $ip.GetAddressBytes()[0] -ge 224) { throw 'LITERAL_REMOTE_IPV4_REQUIRED' }
        if (-not (Test-WuaInteger $e.port) -or $e.port -lt 1 -or $e.port -gt 65535 -or $e.transport -cne 'tcp') { throw 'REMOTE_TRANSPORT_INVALID' }
    }
}

function Get-WuaCandidateNames {
    param($Config)
    Assert-WuaConfiguration $Config
    $prefix='wm';if ($Config.Contains('account_prefix')) { $prefix=$Config.account_prefix }
    $tag=$Config.owner_id.Replace('-','').Substring(0,10)
    return @{client=($prefix+'c-'+$tag);broker=($prefix+'b-'+$tag)}
}

function New-WuaField {
    param([string]$Id,[string]$Status,$Value,[string]$Detail='NONE')
    return @{id=$Id;status=$Status;value=$Value;detail=$Detail;evidence_scope='metadata_or_static_only'}
}

function Test-WuaPublicValue {
    param([string]$Id,$Value)
    if ($null -eq $Value) { return $true }
    switch ($Id) {
        {$_ -in @('os.version','powershell.version','mcp.version','broker.version')} { return ($Value -is [string] -and $Value -cmatch '^\d{1,5}(\.\d{1,6}){1,3}$') }
        'os.architecture' { return ($Value -is [string] -and $Value -cin @('AMD64','ARM64','x86')) }
        {$_ -in @('os.build','os.edition')} { return ((Test-WuaInteger $Value) -and $Value -ge 0 -and $Value -le 999999) }
        {$_ -in @('bfe.state','firewall.state','startup.scheduler')} { return ($Value -cin @('Running','Stopped','Paused','Unknown')) }
        'startup.mode' { return ($Value -cin @('task_batch','service_wrapper')) }
        'startup.execution_policy' { return ($Value -cin @('AllSigned','RemoteSigned','Restricted','Unrestricted','Undefined','Bypass')) }
        {$_ -in @('api.wfp_file','accounts.collision_free','endpoint.snapshot_free','security.admin_token')} { return ($Value -is [bool]) }
    }
    if ($Value -isnot [Collections.IDictionary]) { return $false }
    $shapes=@{
        'firewall.profiles'=@('profile_count','enabled_count','default_outbound_codes');'policy.management'=@('gpo_present','mdm_present');'security.products'=@('count','third_party_unresolved');
        'endpoint.local'=@('address','port','selection');'network.interfaces'=@('count','connected_count');'network.families'=@('v4_count','v6_count');'network.routes'=@('v4_count','v6_count');
        'network.proxy_context'=@('http_present','https_present','all_present','no_proxy_present','wininet_present','winhttp_known');
        'broker.schema'=@('reference_supplied');'broker.remote_endpoint'=@('specified','address_kind','port_specified');'broker.remote_identity'=@('reference_present');
        'mcp.resources'=@('supplied','local','exists','reparse_free','is_root');'mcp.working_directory'=@('supplied','local','exists','reparse_free','is_root');'files.deployment_root'=@('supplied','local','exists','reparse_free','is_root');
        'mcp.launcher_hold'=@('must_preserve','current_state_verified');'accounts.logon_rights'=@('mode','interactive','admin');
        'startup.dependencies'=@('deny_before_start','activation_separate_gate');'files.acl_contract'=@('scope','workspace_wide');
        'ownership.baseline'=@('owner_guid_valid','path_collision_known','port_snapshot_only');'ledger.backend'=@('implemented');'accounts.new_sid_binding'=@('future_resolution')
    }
    if ($Id -in @('mcp.binary','broker.binary','mcp.source_archive','mcp.stdio_exe','mcp.stdio_script')) { $allowed=@('sha256','bytes','format','version_metadata') }
    elseif ($shapes.ContainsKey($Id)) { $allowed=$shapes[$Id] } else { return $false }
    try { Assert-WuaKeys $Value $allowed $allowed } catch { return $false }
    foreach ($key in $Value.Keys) {
        $v=$Value[$key]
        switch ($key) {
            'sha256' { if ($v -isnot [string] -or $v -cnotmatch '^[0-9a-f]{64}$') { return $false } }
            'bytes' { if (-not (Test-WuaInteger $v) -or $v -lt 1) { return $false } }
            'format' { if ($v -cnotin @('PE_AMD64','PE_OTHER','TEXT','ARCHIVE')) { return $false } }
            'version_metadata' { if ($v -isnot [string] -or $v -cnotmatch '^(unavailable|\d{1,5}(\.\d{1,6}){1,3})$') { return $false } }
            'address' { if ($v -cne '127.0.0.1') { return $false } }
            'port' { if (-not (Test-WuaInteger $v) -or $v -lt 1024 -or $v -gt 65535) { return $false } }
            'selection' { if ($v -cnotin @('operator','snapshot_candidate')) { return $false } }
            'address_kind' { if ($v -cne 'literal_ipv4') { return $false } }
            'mode' { if ($v -cnotin @('task_batch','service_wrapper')) { return $false } }
            'scope' { if ($v -cne 'owned_resources_only') { return $false } }
            'default_outbound_codes' { if ($v -isnot [Collections.IList]) { return $false };foreach ($code in $v) { if (-not (Test-WuaInteger $code) -or $code -lt 0 -or $code -gt 65535) { return $false } } }
            {$_ -in @('profile_count','enabled_count','count','connected_count','v4_count','v6_count')} { if (-not (Test-WuaInteger $v) -or $v -lt 0 -or $v -gt 1000000) { return $false } }
            default { if ($v -isnot [bool]) { return $false } }
        }
    }
    if ($Id -eq 'accounts.logon_rights' -and ($Value.admin -or $Value.interactive)) {return $false}
    if ($Id -eq 'files.acl_contract' -and $Value.workspace_wide) {return $false}
    if ($Id -eq 'startup.dependencies' -and (-not $Value.deny_before_start -or -not $Value.activation_separate_gate)) {return $false}
    return $true
}

function New-WuaInventory {
    param($Config,$ProbeData,[string]$SourceKind='synthetic',[string]$CollectedUtc=([DateTime]::UtcNow.ToString('o')))
    Assert-WuaConfiguration $Config
    if ($SourceKind -cnotin @('synthetic','local_readonly')) { throw 'INVENTORY_SOURCE_INVALID' }
    $contract=Get-WuaContract;$fields=@()
    foreach ($spec in $contract.fields) {
        $id=$spec.id
        if ($spec.security_proof) { $fields+= ,(New-WuaField $id 'UNSUPPORTED' $null 'SECURITY_BACKEND_NOT_IMPLEMENTED');continue }
        if ($ProbeData.Contains($id)) {
            $given=$ProbeData[$id];Assert-WuaKeys $given @('id','status','value','detail','evidence_scope') @('id','status','value','detail')
            if ($given.id -cne $id -or $given.status -cnotin $spec.statuses) { throw 'FIELD_ID_OR_STATUS_INVALID' }
            if ($given.detail -isnot [string] -or $given.detail -cnotmatch '^[A-Z0-9_.:-]{1,80}$' -or -not (Test-WuaPublicValue $id $given.value)) { throw 'NONPUBLIC_OR_INVALID_VALUE' }
            $fields+= ,$given
        } else { $fields+= ,(New-WuaField $id 'REQUIRES_USER_INPUT' $null 'NOT_SUPPLIED') }
    }
    foreach ($key in $ProbeData.Keys) { if ($key -cnotin @($contract.fields | ForEach-Object {$_.id})) { throw 'UNKNOWN_DISCOVERY_FIELD' } }
    return @{schema_version=1;source_kind=$SourceKind;collected_utc=$CollectedUtc;collection_id=[Guid]::NewGuid().ToString('D');requirements_sha256=(Get-WuaHash $contract);config_sha256=(Get-WuaHash $Config);fields=$fields;privacy='public_aggregate_no_identifiers';security_backend='NOT_IMPLEMENTED'}
}

function Get-WuaCoverage {
    param($Inventory)
    $contract=Get-WuaContract;$issues=@();$seen=@{};$rows=@()
    Assert-WuaKeys $Inventory @('schema_version','source_kind','collected_utc','collection_id','requirements_sha256','config_sha256','fields','privacy','security_backend') @('schema_version','source_kind','collected_utc','collection_id','requirements_sha256','config_sha256','fields','privacy','security_backend')
    $collection=[Guid]::Empty;$time=[DateTime]::MinValue
    if (-not (Test-WuaInteger $Inventory.schema_version) -or $Inventory.schema_version -ne 1 -or $Inventory.requirements_sha256 -cne (Get-WuaHash $contract) -or $Inventory.source_kind -cnotin @('synthetic','local_readonly') -or $Inventory.privacy -cne 'public_aggregate_no_identifiers' -or $Inventory.security_backend -cne 'NOT_IMPLEMENTED') { $issues+='INVENTORY_CONTRACT_MISMATCH' }
    if ($Inventory.collection_id -isnot [string] -or -not [Guid]::TryParseExact($Inventory.collection_id,'D',[ref]$collection) -or $collection -eq [Guid]::Empty) {$issues+='INVALID_COLLECTION_ID'}
    if ($Inventory.collected_utc -isnot [string] -or -not [DateTime]::TryParseExact($Inventory.collected_utc,'o',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind,[ref]$time)) {$issues+='INVALID_COLLECTION_TIME'}
    if ($Inventory.config_sha256 -isnot [string] -or $Inventory.config_sha256 -cnotmatch '^[0-9a-f]{64}$') {$issues+='INVALID_CONFIG_DIGEST'}
    if ($Inventory.fields -isnot [Collections.IList]) { throw 'FIELDS_ARRAY_REQUIRED' }
    foreach ($field in $Inventory.fields) {
        Assert-WuaKeys $field @('id','status','value','detail','evidence_scope') @('id','status','value','detail')
        if ($field.id -isnot [string] -or $seen.ContainsKey($field.id)) { $issues+='DUPLICATE_OR_INVALID_FIELD';continue };$seen[$field.id]=$field
    }
    $represented=0;$verified=0
    foreach ($spec in $contract.fields) {
        if (-not $seen.ContainsKey($spec.id)) { $issues+=('MISSING_FIELD:'+ $spec.id);$rows+= ,@{id=$spec.id;status='MISSING';valid=$false;blocking=$true};continue }
        $represented++;$field=$seen[$spec.id];$valid=$true
        if ($field.status -cnotin $spec.statuses) { $issues+=('INVALID_STATUS:'+ $spec.id);$valid=$false }
        if (-not (Test-WuaPublicValue $spec.id $field.value)) { $issues+=('NONPUBLIC_OR_INVALID_VALUE:'+ $spec.id);$valid=$false }
        if ($field.status -in @('DETECTED','VERIFIED')) {
            $v=$field.value
            $ok=switch ($spec.type) {'string' {($v -is [string] -and $v.Length -gt 0 -and $v.Length -le 256)} 'integer' {(Test-WuaInteger $v)} 'boolean' {($v -is [bool])} 'object' {($v -is [Collections.IDictionary])} default {$false}}
            if (-not $ok) { $issues+=('INVALID_TYPE:'+ $spec.id);$valid=$false }
        }
        if ($spec.security_proof -and $field.status -in @('DETECTED','VERIFIED')) { $issues+=('FORGED_SECURITY_PROOF:'+ $spec.id);$valid=$false }
        if ($field.status -eq 'VERIFIED' -and $valid) { $verified++ }
        $met=$valid
        if ($spec.id -in @('api.wfp_file','accounts.collision_free','endpoint.snapshot_free','security.admin_token') -and $field.value -is [bool] -and -not $field.value) {$met=$false}
        if ($spec.id -in @('bfe.state','firewall.state','startup.scheduler') -and $field.value -cne 'Running') {$met=$false}
        $rows+= ,@{id=$spec.id;status=$field.status;valid=$valid;requirement_met=$met;blocking=($field.status -ne 'VERIFIED' -or -not $met)}
    }
    foreach ($id in $seen.Keys) { if ($id -cnotin @($contract.fields | ForEach-Object {$_.id})) { $issues+='EXTRA_FIELD' } }
    $blocking=@($rows | Where-Object {$_.blocking -or -not $_.valid})
    return @{required=$contract.fields.Count;represented=$represented;representation_percent=([int](100*$represented/$contract.fields.Count));verified_metadata=$verified;issues=$issues;blocking_count=$blocking.Count;rows=$rows;ready_for_apply=$false;reason='NO_IMPLEMENTED_SECURITY_BACKEND'}
}

function Get-WuaPolicyTemplate {
    return @{schema_version=1;model='T1_candidate_not_enforcement';rules=@(
        @{principal='client';family='v6';predicate='any';action='block'},
        @{principal='client';family='v4';predicate='not_tcp';action='block'},
        @{principal='client';family='v4';predicate='tcp_not_loopback_exact';action='block'},
        @{principal='client';family='v4';predicate='tcp_loopback_wrong_port';action='block'},
        @{principal='broker';family='v6';predicate='any';action='block'},
        @{principal='broker';family='v4';predicate='not_tcp';action='block'},
        @{principal='broker';family='v4';predicate='tcp_not_remote_exact';action='block'},
        @{principal='broker';family='v4';predicate='tcp_remote_wrong_port';action='block'}
    );sid_binding='resolve_new_local_accounts_only';loopback_guard='UNIMPLEMENTED';arbitration='NOT_VERIFIED';lifecycle='NOT_VERIFIED'}
}

function Get-WuaModelDecision {
    param([string]$Role,[string]$Family,[int]$Protocol,[string]$Address,[int]$Port,[int]$LocalPort,[string]$RemoteAddress,[int]$RemotePort)
    if ($Role -cnotin @('client','broker') -or $Family -cnotin @('v4','v6') -or $Protocol -lt 0 -or $Protocol -gt 255 -or $Port -lt 0 -or $Port -gt 65535 -or $LocalPort -lt 1024 -or $LocalPort -gt 65535) { return 'BLOCK' }
    if ($Family -eq 'v6' -or $Protocol -ne 6) { return 'BLOCK' }
    if ($Role -eq 'client' -and $Address -ceq '127.0.0.1' -and $Port -eq $LocalPort) { return 'CANDIDATE_EDGE' }
    if ($Role -eq 'broker' -and $Address -ceq $RemoteAddress -and $Port -eq $RemotePort -and $RemotePort -ge 1 -and $RemotePort -le 65535) { return 'CANDIDATE_EDGE' }
    return 'BLOCK'
}

function New-WuaDeploymentPlan {
    param($Inventory,$Config)
    Assert-WuaConfiguration $Config
    $coverage=Get-WuaCoverage $Inventory
    if ($coverage.issues.Count -gt 0) { throw 'INVALID_INVENTORY' }
    if ($Inventory.config_sha256 -cne (Get-WuaHash $Config)) { throw 'CONFIG_BINDING_MISMATCH' }
    $fieldMap=@{};foreach ($f in $Inventory.fields) { $fieldMap[$f.id]=$f }
    $compat='UNSUPPORTED'
    if ($fieldMap['os.build'].status -eq 'VERIFIED' -and $fieldMap['os.edition'].status -eq 'VERIFIED' -and $fieldMap['os.architecture'].value -ceq 'AMD64') {
        $build=$fieldMap['os.build'].value;$sku=$fieldMap['os.edition'].value
        $psOk=$fieldMap['powershell.version'].status -eq 'VERIFIED' -and ([Version]$fieldMap['powershell.version'].value) -ge [Version]'5.1'
        if ($psOk -and $sku -in @(4,48,49,121,122,125,126,161,162) -and ($build -eq 19045 -or $build -in @(22000,22621,22631,26100,26200))) { $compat='METADATA_PROFILE_ONLY' }
    }
    $portRef='unresolved'
    if ($fieldMap['endpoint.local'].status -in @('VERIFIED','DETECTED')) { $portRef=$fieldMap['endpoint.local'].value.port }
    $actionSpecs=@(
        @('reserve_owner_ledger','Reserve exclusive ownership before any mutation','owner:new_root','absent','owned empty ledger','administrator','exact local path and no prior objects','retain diagnostics only'),
        @('create_disabled_client','Create NEW local standard account; do not reuse foreign SID','role:client','absent','disabled new identity','administrator','read back local SID and disabled state','remove only after deny/quiescence'),
        @('create_disabled_broker','Separate broker identity from client and current user','role:broker','absent','disabled new identity','administrator','read back distinct new local SID','remove only after deny/quiescence'),
        @('bind_new_sids','Resolve actual freshly created account SIDs locally','roles:client,broker','symbolic','local SID bindings in protected ledger','administrator','distinct local SIDs, no imported SID','keep principals disabled'),
        @('set_logon_rights','Least rights; batch/service only, no interactive/elevation grant','roles:client,broker','captured before','least privilege','administrator','rights diff exact owner entries','restore exact prior owned assignments'),
        @('set_owned_acls','Separate immutable binaries and role private profiles/resources','path_refs:owned_resources','captured before','minimal role ACLs','administrator','DACL readback, no workspace-wide grant','restore exact before descriptor'),
        @('install_sid_policy','Install reviewed disjoint denies before enabling any identity','policy:owner_guid','absent','effective deny partition','administrator','independent SID/loopback/arbitration/lifecycle proof','KEEP deny until all SID work absent'),
        @('configure_private_broker','No DIRECT; authenticated approved remote endpoint','role:broker/config','absent','version-pinned config plus local secret refs','administrator','loaded graph and remote pin; no DNS bypass','remove only owned config after stop'),
        @('register_disabled_startup','Stage noninteractive least-privilege startup; no activation','startup:owner_guid','absent','disabled task/service definitions','administrator','principal SID and dependencies; no start','remove exact ledger task/service only'),
        @('verify_staged_install','Independently compare installed objects and protected ledger','ledger:owner_guid','staged','verified or BLOCKED','reviewed verifier','effective filters, ACL, identities; no mock proof','retain deny and disabled resources'),
        @('activation_separate_go','Native/live activation is a separate future authorization','activation:separate_gate','not started','NOT STARTED','separate USER GO','native containment/live/E2E gates','no activation in this toolkit version')
    )
    $actions=@();$n=0
    foreach ($a in $actionSpecs) {
        $n++;$actions+= ,@{order=$n;operation=$a[0];what=$a[0];why=$a[1];target=$a[2];before=$a[3];after=$a[4];required_privileges=$a[5];verification=$a[6];rollback=$a[7];executable=$false}
    }
    $payload=@{schema_version=1;toolkit_version='0.1.0-offline';owner_id=$Config.owner_id;inventory_sha256=(Get-WuaHash $Inventory);config_sha256=(Get-WuaHash $Config);requirements_sha256=$Inventory.requirements_sha256;
        compatibility=$compat;public_redacted=$true;path_values='operator private input referenced by role; never copied here';remote_values='private configuration reference; never copied here';
        local_endpoint=@{address='127.0.0.1';port=$portRef;race_protection='NOT_VERIFIED'};
        sid_bindings=@(@{role='client';value=$null;resolve='new_local_account_on_future_apply'},@{role='broker';value=$null;resolve='new_local_account_on_future_apply'});
        policy=(Get-WuaPolicyTemplate);actions=$actions;coverage=$coverage;deployment_state='BLOCKED';backend='NOT_IMPLEMENTED';dry_run=$true;approval_semantics='digest binds content, not authority or host identity';
        privileges_forbidden=@('SeDebugPrivilege','SeTcbPrivilege','SeImpersonatePrivilege','Administrators membership');activation_allowed=$false}
    return @{payload=$payload;approval_sha256=(Get-WuaHash $payload)}
}

function Test-WuaPlanBinding {
    param($Plan,$Inventory,$Config)
    try {
        Assert-WuaKeys $Plan @('payload','approval_sha256') @('payload','approval_sha256')
        if ($Plan.approval_sha256 -isnot [string] -or $Plan.approval_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Plan.approval_sha256 -cne (Get-WuaHash $Plan.payload)) { return $false }
        $expected=New-WuaDeploymentPlan $Inventory $Config
        return ($expected.approval_sha256 -ceq $Plan.approval_sha256 -and (ConvertTo-WuaCanonicalJson $expected.payload) -ceq (ConvertTo-WuaCanonicalJson $Plan.payload))
    } catch { return $false }
}

function Get-WuaApplyDecision {
    param($Plan,$Inventory,$Config,[string]$ApprovedHash='')
    if (-not (Test-WuaPlanBinding $Plan $Inventory $Config)) { return @{status='FAIL';reason='TAMPERED_OR_MISMATCHED_PLAN';mutations=0} }
    if ($ApprovedHash -and $ApprovedHash -cne $Plan.approval_sha256) { return @{status='FAIL';reason='APPROVAL_DIGEST_MISMATCH';mutations=0} }
    # No input boolean, proof file, Force or approval string can change this capability.
    if (-not $script:BackendImplemented) { return @{status='BLOCKED';reason='NO_REVIEWED_EXECUTABLE_SECURITY_BACKEND';mutations=0;dry_run=$true} }
    throw 'UNREACHABLE_BACKEND_STATE'
}

function Compare-WuaInventory {
    param($Left,$Right)
    $lc=Get-WuaCoverage $Left;$rc=Get-WuaCoverage $Right
    if ($lc.issues.Count -or $rc.issues.Count) { throw 'INVALID_COMPARISON_INPUT' }
    $r=@{};foreach ($f in $Right.fields) { $r[$f.id]=$f }
    $rows=@();foreach ($f in $Left.fields) { $g=$r[$f.id];$rows+= ,@{id=$f.id;left_status=$f.status;right_status=$g.status;metadata_equal=((Get-WuaHash $f) -ceq (Get-WuaHash $g))} }
    return @{scope='redacted metadata comparison only, not device/security equivalence';rows=$rows;changed=@($rows | Where-Object {-not $_.metadata_equal}).Count}
}

function Test-WuaInstallation {
    param($Plan,$Inventory,$Config,$FreshInventory=$null)
    $binding=Test-WuaPlanBinding $Plan $Inventory $Config
    $drift=$null;if ($null -ne $FreshInventory) { $drift=Compare-WuaInventory $Inventory $FreshInventory }
    $policyCheck=Test-WuaStaticPolicy $Plan.payload.policy
    return @{schema_version=1;static_plan_binding=$(if ($binding) {'PASS'} else {'FAIL'});static_policy=$policyCheck;drift=$drift;
        sid_creation='NOT RUN';effective_wfp='NOT VERIFIED';listener_guard='NOT VERIFIED';denied_endpoints='NOT RUN';children='NOT RUN';dns_delegation='NOT VERIFIED';broker_outbound='NOT VERIFIED';failure_recovery='NOT RUN';v2ray_route='NOT VERIFIED';ordinary_chat_e2e='NOT RUN';security_verdict='NOT VERIFIED'}
}

function Test-WuaStaticPolicy {
    # Independent invariant check; does not call the generator, hash matcher or model decision.
    param($Policy)
    $findings=@();$seen=@{}
    try {
        foreach ($rule in $Policy.rules) {
            Assert-WuaKeys $rule @('principal','family','predicate','action') @('principal','family','predicate','action')
            if ($rule.principal -cnotin @('client','broker') -or $rule.action -cne 'block') {$findings+='NON_DENY_OR_UNKNOWN_PRINCIPAL'}
            $key=$rule.principal+'|'+$rule.family+'|'+$rule.predicate
            if ($seen.ContainsKey($key)) {$findings+='DUPLICATE_PREDICATE'};$seen[$key]=$true
            if ($rule.family -eq 'v4' -and $rule.predicate -eq 'any') {$findings+='BLOCK_ALL_CONFLICTS_WITH_REQUIRED_EDGE'}
        }
        foreach ($role in @('client','broker')) {
            foreach ($suffix in @('v6|any','v4|not_tcp')) {if (-not $seen.ContainsKey($role+'|'+$suffix)) {$findings+='MISSING_FAMILY_OR_PROTOCOL_DENY'}}
        }
        foreach ($key in @('client|v4|tcp_not_loopback_exact','client|v4|tcp_loopback_wrong_port','broker|v4|tcp_not_remote_exact','broker|v4|tcp_remote_wrong_port')) {
            if (-not $seen.ContainsKey($key)) {$findings+='MISSING_ADDRESS_OR_PORT_DENY'}
        }
        if ($Policy.rules.Count -ne 8) {$findings+='UNEXPECTED_PREDICATE_COUNT'}
    } catch {$findings+='INVALID_POLICY_STRUCTURE'}
    return @{status=$(if ($findings.Count) {'FAIL'} else {'PASS'});findings=$findings;scope='symbolic static invariants only; not WFP comparator/layer/OS proof'}
}

function New-WuaRollbackPlan {
    param($Ledger)
    Assert-WuaKeys $Ledger @('schema_version','owner_id','plan_sha256','resources','process_state','flow_state') @('schema_version','owner_id','plan_sha256','resources','process_state','flow_state')
    $owner=[Guid]::Empty
    if (-not (Test-WuaInteger $Ledger.schema_version) -or $Ledger.schema_version -ne 1 -or -not [Guid]::TryParseExact([string]$Ledger.owner_id,'D',[ref]$owner) -or $owner -eq [Guid]::Empty -or $Ledger.plan_sha256 -cnotmatch '^[0-9a-f]{64}$' -or $Ledger.resources -isnot [Collections.IList]) { throw 'LEDGER_INVALID' }
    $ids=@{}
    foreach ($resource in $Ledger.resources) {
        Assert-WuaKeys $resource @('resource_id','owner_id','kind','created_by_kit','before_exists','target_ref') @('resource_id','owner_id','kind','created_by_kit','before_exists','target_ref')
        $id=[Guid]::Empty
        if (-not [Guid]::TryParseExact([string]$resource.resource_id,'D',[ref]$id) -or $id -eq [Guid]::Empty -or $ids.ContainsKey($resource.resource_id)) { throw 'RESOURCE_ID_INVALID_OR_DUPLICATE' };$ids[$resource.resource_id]=$true
        if ($resource.owner_id -cne $Ledger.owner_id -or $resource.created_by_kit -isnot [bool] -or -not $resource.created_by_kit -or $resource.before_exists -isnot [bool] -or $resource.before_exists) { throw 'FOREIGN_RESOURCE_BLOCKED' }
        if ($resource.kind -cnotin @('account','filter','task','service','owned_directory','owned_config','rights_assignment') -or $resource.target_ref -isnot [string] -or $resource.target_ref -cnotmatch '^(role|policy|startup|path_ref|config_ref):[a-z_]{1,40}$') { throw 'LEDGER_TARGET_BLOCKED' }
    }
    if ($Ledger.process_state -cnotin @('unknown','reported_zero','reported_live') -or $Ledger.flow_state -cnotin @('unknown','reported_zero','reported_live')) { throw 'LEDGER_STATE_INVALID' }
    return @{status='ROLLBACK BLOCKED';reason='NO_TRUSTED_QUIESCENCE_OR_EXECUTABLE_BACKEND';owner_id=$Ledger.owner_id;mutations=0;resource_count=$Ledger.resources.Count;
        order=@('freeze_admissions','disable_owned_startup_and_accounts','quiesce_owned_sids_and_delegated_work','independently_verify_zero_processes_flows_and_queued_work','remove_exact_owned_tasks_and_secret_refs','remove_owned_accounts','remove_owned_deny_filters_last','remove_exact_owned_files_after_path_checks');
        keep_deny=$true;reported_zero_is_not_authority=$true;repeated_call_has_no_side_effects=$true}
}

function Format-WuaPlan {
    param($Plan)
    $lines=@('# WUA deployment plan (PUBLIC REDACTED / NOT EXECUTABLE)','',('Approval SHA-256: '+$Plan.approval_sha256),'State: BLOCKED; backend NOT_IMPLEMENTED; activation NOT STARTED.',
        'Digest binds input content only, not authenticated approval or host identity.','Private paths/remote endpoint are referenced through operator input; use a local private review before any future Apply.','')
    foreach ($a in $Plan.payload.actions) { $lines+=@(('## '+$a.order+'. '+$a.what),('WHY: '+$a.why),('TARGET: '+$a.target),('BEFORE: '+$a.before),('AFTER: '+$a.after),('REQUIRED PRIVILEGES: '+$a.required_privileges),('VERIFICATION: '+$a.verification),('ROLLBACK: '+$a.rollback),'') }
    return $lines -join [Environment]::NewLine
}

function Get-WuaResumeDecision {
    param($Plan,$Ledger)
    try {
        [void](New-WuaRollbackPlan $Ledger)
        if ($Ledger.owner_id -cne $Plan.payload.owner_id -or $Ledger.plan_sha256 -cne $Plan.approval_sha256) {return @{status='FAIL';reason='FOREIGN_OWNER_OR_PLAN';create_duplicate=$false;mutations=0}}
        return @{status='BLOCKED';reason='MATCHING_LEDGER_STILL_REQUIRES_TRUSTED_READBACK';create_duplicate=$false;mutations=0}
    } catch {return @{status='FAIL';reason='INVALID_LEDGER';create_duplicate=$false;mutations=0}}
}
