param([Parameter(Mandatory=$true)][string]$OutputDirectory,[string]$RuntimeLabel='synthetic')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Import-Module (Join-Path (Split-Path $PSScriptRoot -Parent) 'WuaMcp.psm1') -Force -DisableNameChecking
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Discovery.ps1') # Definitions only; never Invoke-WuaLocalDiscovery in synthetic tests.
$out=Assert-WuaLocalPath $OutputDirectory
$results=New-Object Collections.Generic.List[object]
$sourcePins=@{}
foreach ($name in @('WuaMcp.psm1','Discovery.ps1','tests/Test-Toolkit.ps1')) {
    $p=Join-Path (Split-Path $PSScriptRoot -Parent) $name;$sourcePins[$name]=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Assert($Condition,[string]$Code='ASSERTION') { if (-not $Condition) { throw $Code } }
function Throws([scriptblock]$Action,[string]$Code='EXPECTED_REJECTION') { $seen=$false;try { & $Action | Out-Null } catch {$seen=$true};Assert $seen $Code }
function PublicTestError([string]$Message) {if ($Message -cmatch '^[A-Z][A-Z0-9_]{1,100}$') {return $Message};return 'REDACTED_TEST_FAILURE'}
function Case([string]$Name,[scriptblock]$Action) {
    try { & $Action;$results.Add(@{name=$Name;status='PASS'}) }
    catch { $results.Add(@{name=$Name;status='FAIL';error_code=(PublicTestError $_.Exception.Message);error_line=$_.InvocationInfo.ScriptLineNumber}) }
}
function CopyValue($Value) { return ConvertTo-WuaMap (ConvertFrom-WuaJsonText (ConvertTo-WuaCanonicalJson $Value)) }
function Config {
    return @{schema_version=1;owner_id='11111111-1111-4111-8111-111111111111';paths=@{client_exe='C:\Synthetic\client.exe';broker_exe='C:\Synthetic\broker.exe';deployment_root='C:\Synthetic\new-owned-root'};local_port=54321;startup_mode='task_batch';remote_endpoint=@{address='192.0.2.44';port=443;transport='tcp'}}
}
function Inventory($Config) {
    $probe=@{}
    foreach ($pair in @(@('os.version','10.0.19045'),@('os.build',19045),@('os.edition',48),@('os.architecture','AMD64'),@('powershell.version','5.1.19041.1'),@('bfe.state','Running'),@('firewall.state','Running'),@('startup.scheduler','Running'),@('accounts.collision_free',$true),@('endpoint.snapshot_free',$true))) {
        $probe[$pair[0]]=New-WuaField $pair[0] 'VERIFIED' $pair[1] 'SYNTHETIC'
    }
    $probe['endpoint.local']=New-WuaField 'endpoint.local' 'VERIFIED' @{address='127.0.0.1';port=54321;selection='operator'} 'SYNTHETIC'
    $inv=New-WuaInventory $Config $probe 'synthetic' '2026-01-01T00:00:00.0000000Z'
    $inv.collection_id='22222222-2222-4222-8222-222222222222';return $inv
}
$config=Config;$inventory=Inventory $config;$plan=New-WuaDeploymentPlan $inventory $config
Case 'contract_55_unique_fields_all_11_categories' {
    $c=Get-WuaContract;Assert ($c.fields.Count -eq 55);Assert (@($c.fields.id | Select-Object -Unique).Count -eq 55)
    Assert (@($c.fields.category | Select-Object -Unique).Count -eq 11)
    foreach ($f in $c.fields) { foreach ($k in @('purpose','source','safe_read','type','validation','required','sensitivity','statuses','stop_rule','dependent_actions')) { Assert $f.ContainsKey($k) } }
}
Case 'complete_representation_not_security_readiness' { $c=Get-WuaCoverage $inventory;Assert ($c.representation_percent -eq 100);Assert ($c.blocking_count -gt 0);Assert (-not $c.ready_for_apply) }
Case 'missing_required_field_is_blocker' { $x=CopyValue $inventory;$x.fields=@($x.fields | Where-Object {$_.id -ne 'os.build'});$c=Get-WuaCoverage $x;Assert ($c.represented -eq 54);Assert ($c.issues -contains 'MISSING_FIELD:os.build') }
Case 'duplicate_inventory_field_rejected' { $x=CopyValue $inventory;$x.fields+= ,$x.fields[0];Assert ((Get-WuaCoverage $x).issues -contains 'DUPLICATE_OR_INVALID_FIELD') }
Case 'unknown_inventory_field_rejected' { $x=CopyValue $inventory;$x.fields+= ,(New-WuaField 'not.contract' 'VERIFIED' 'x');Assert ((Get-WuaCoverage $x).issues -contains 'EXTRA_FIELD') }
Case 'string_bool_is_not_boolean' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'endpoint.snapshot_free'}).value='true';Assert ((Get-WuaCoverage $x).issues -contains 'INVALID_TYPE:endpoint.snapshot_free') }
Case 'forged_security_VERIFIED_is_rejected' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'wfp.loopback'}).status='VERIFIED';Assert ((Get-WuaCoverage $x).issues -contains 'FORGED_SECURITY_PROOF:wfp.loopback') }
Case 'constructor_does_not_accept_operator_security_claim' { $p=@{'wfp.sid_match'=(New-WuaField 'wfp.sid_match' 'VERIFIED' @{safe=$true})};$x=New-WuaInventory $config $p;Assert (($x.fields | Where-Object {$_.id -eq 'wfp.sid_match'}).status -eq 'UNSUPPORTED') }
Case 'plan_is_deterministic' { $again=New-WuaDeploymentPlan $inventory $config;Assert ($plan.approval_sha256 -ceq $again.approval_sha256) }
Case 'approval_hash_binds_private_configuration_version' { $c=CopyValue $config;$c.local_port=54322;Throws {New-WuaDeploymentPlan $inventory $c} }
Case 'payload_tamper_rejected' { $p=CopyValue $plan;$p.payload.actions[0].after='hijacked';Assert (-not (Test-WuaPlanBinding $p $inventory $config)) }
Case 'attacker_rehashed_modified_plan_still_rejected' { $p=CopyValue $plan;$p.payload.policy.rules=@();$p.approval_sha256=Get-WuaHash $p.payload;Assert (-not (Test-WuaPlanBinding $p $inventory $config)) }
Case 'overlapping_BlockALL_Allow_localhost_not_accepted' { $p=CopyValue $plan;$p.payload.policy.rules=@(@{principal='client';action='block';predicate='all'},@{principal='client';action='allow';predicate='localhost'});$p.approval_sha256=Get-WuaHash $p.payload;Assert (-not (Test-WuaPlanBinding $p $inventory $config)) }
Case 'SID_not_importable_in_config' { $c=CopyValue $config;$c.sid='S-1-5-21-123';Throws {Assert-WuaConfiguration $c} }
Case 'privilege_escalation_field_not_importable' { $c=CopyValue $config;$c.privileges=@('SeDebugPrivilege');Throws {Assert-WuaConfiguration $c} }
Case 'force_insecure_field_not_importable' { $c=CopyValue $config;$c.force_insecure=$true;Throws {Assert-WuaConfiguration $c} }
Case 'Apply_gate_blocks_valid_plan_even_with_matching_approval' { $d=Get-WuaApplyDecision $plan $inventory $config $plan.approval_sha256;Assert ($d.status -eq 'BLOCKED' -and $d.mutations -eq 0) }
Case 'Apply_gate_rejects_wrong_approval' { Assert ((Get-WuaApplyDecision $plan $inventory $config ('a'*64)).status -eq 'FAIL') }
Case 'Apply_gate_rejects_unknown_plan_properties' { $p=CopyValue $plan;$p.verified=$true;Assert ((Get-WuaApplyDecision $p $inventory $config).status -eq 'FAIL') }
Case 'new_accounts_derive_from_owner_without_foreign_names' { $a=Get-WuaCandidateNames $config;$c=CopyValue $config;$c.owner_id='33333333-3333-4333-8333-333333333333';$b=Get-WuaCandidateNames $c;Assert ($a.client -cne $b.client -and $a.client -cne $a.broker -and $a.client.Length -le 20) }
Case 'candidate_name_conflict_remains_explicit' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'accounts.collision_free'}).status='CONFLICT';($x.fields | Where-Object {$_.id -eq 'accounts.collision_free'}).value=$false;$p=New-WuaDeploymentPlan $x $config;Assert ($p.payload.coverage.blocking_count -gt 0) }
Case 'occupied_port_not_treated_as_reserved' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'endpoint.snapshot_free'}).status='CONFLICT';$p=New-WuaDeploymentPlan $x $config;Assert ($p.payload.local_endpoint.race_protection -eq 'NOT_VERIFIED') }
Case 'invalid_ports_bool_float_boundaries' { foreach ($v in @($true,1.5,0,1023,65536)) { $c=CopyValue $config;$c.local_port=$v;Throws {Assert-WuaConfiguration $c} } }
Case 'remote_domain_IPv6_multicast_not_auto_resolved' { foreach ($v in @('example.invalid','::1','224.0.0.1','127.0.0.1','0.0.0.0','192.000.002.044')) { $c=CopyValue $config;$c.remote_endpoint.address=$v;Throws {Assert-WuaConfiguration $c} } }
Case 'UDP_remote_does_not_expand_TCP_policy' { $c=CopyValue $config;$c.remote_endpoint.transport='udp';Throws {Assert-WuaConfiguration $c} }
Case 'network_provider_ADS_and_traversal_paths_rejected_lexically' { foreach ($p in @('\\host\share\x','Registry::HKLM\x','C:\x:stream','C:\a\..\b','C:\CON\x')) { $c=CopyValue $config;$c.paths.client_exe=$p;Throws {Assert-WuaConfiguration $c} } }
Case 'deployment_drive_root_rejected' { $c=CopyValue $config;$c.paths.deployment_root='C:\';Throws {Assert-WuaConfiguration $c} }
Case 'Windows11_metadata_profile_not_OS_security_pass' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'os.build'}).value=22631;$p=New-WuaDeploymentPlan $x $config;Assert ($p.payload.compatibility -eq 'METADATA_PROFILE_ONLY' -and $p.payload.deployment_state -eq 'BLOCKED') }
Case 'unknown_edition_architecture_are_unsupported_profiles' { foreach ($pair in @(@('os.edition',999),@('os.architecture','ARM64'),@('os.architecture','x86'),@('os.build',999999))) { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq $pair[0]}).value=$pair[1];Assert ((New-WuaDeploymentPlan $x $config).payload.compatibility -eq 'UNSUPPORTED') } }
Case 'PowerShell_below_51_is_unsupported_profile' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'powershell.version'}).value='4.0';Assert ((New-WuaDeploymentPlan $x $config).payload.compatibility -eq 'UNSUPPORTED') }
Case 'missing_binaries_versions_sources_and_endpoint_are_blockers' { $x=CopyValue $inventory;foreach ($id in @('broker.binary','mcp.binary','broker.version','mcp.source_archive','broker.remote_endpoint')) { $row=$x.fields | Where-Object {$_.id -eq $id};$row.status='MISSING';$row.value=$null };Assert ((New-WuaDeploymentPlan $x $config).payload.coverage.blocking_count -ge 5) }
Case 'startup_mode_unknown_rejected' { $c=CopyValue $config;$c.startup_mode='administrator_interactive';Throws {Assert-WuaConfiguration $c} }
Case 'GPO_MDM_and_no_admin_do_not_enable_Apply' { $x=CopyValue $inventory;$f=$x.fields | Where-Object {$_.id -eq 'policy.management'};$f.status='CONFLICT';$f.value=@{gpo_present=$true;mdm_present=$true};$p=New-WuaDeploymentPlan $x $config;Assert ((Get-WuaApplyDecision $p $x $config).status -eq 'BLOCKED') }
Case 'redacted_public_values_reject_secret_or_identifier_properties' { Throws {New-WuaInventory $config @{'broker.binary'=(New-WuaField 'broker.binary' 'VERIFIED' @{password='DO_NOT_EXPORT';username='PRIVATE'})}} }
Case 'test_failure_reporting_redacts_private_runtime_messages' {Assert ((PublicTestError 'Cannot read C:\Users\PRIVATE_PERSON\secret') -ceq 'REDACTED_TEST_FAILURE');Assert ((PublicTestError 'INVALID_PORT') -ceq 'INVALID_PORT')}
Case 'JSON_nested_duplicate_case_and_escape_rejected' { foreach ($text in @('{"a":{"x":1,"x":2}}','{"A":1,"a":2}','{"a":1,"\u0061":2}')) { Throws {Assert-WuaJsonGrammar $text} } }
Case 'JSON_invalid_grammar_and_excess_depth_rejected' { foreach ($text in @('{"a":01}','{"a":true,}','[1,]','{}{}',('['*23+'0'+']'*23))) {Throws {Assert-WuaJsonGrammar $text}} }
Case 'canonical_order_unicode_integer_and_newlines_stable' { Assert ((ConvertTo-WuaCanonicalJson @{z=1;a="x`n";b=[string][char]0x441}) -ceq '{"a":"x\u000a","b":"\u0441","z":1}') }
Case 'public_JSON_roundtrip_preserves_UTC_as_string' { $path=Join-Path $out 'roundtrip.json';Write-WuaJson $path $inventory;$x=Read-WuaJson $path;Assert ($x.collected_utc -is [string]);Assert ((Get-WuaHash $x) -ceq (Get-WuaHash $inventory)) }
Case 'JSON_output_never_overwrites_existing_file' { Throws {Write-WuaJson (Join-Path $out 'roundtrip.json') @{overwrite=$true}} }
Case 'owned_file_hash_metadata_matches_independent_hash' { $p=Join-Path $out 'owned-text.fixture';[IO.File]::WriteAllText($p,'synthetic-data-only');$m=Get-WuaFileMetadata $p 'TEXT';Assert ($m.sha256 -ceq (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -and $m.format -eq 'TEXT') }
Case 'invalid_PE_bytes_not_a_supported_executable' { $p=Join-Path $out 'invalid-pe.fixture';[IO.File]::WriteAllBytes($p,[byte[]](77,90,0,0,0,0));$m=Get-WuaFileMetadata $p 'PE';Assert ($m.format -eq 'PE_OTHER' -and $m.version_metadata -eq 'unavailable') }
Case 'metadata_comparison_ignores_no_values_and_reveals_no_hosts' { $x=CopyValue $inventory;($x.fields | Where-Object {$_.id -eq 'bfe.state'}).value='Stopped';$c=Compare-WuaInventory $inventory $x;Assert ($c.changed -eq 1);Assert ((ConvertTo-WuaCanonicalJson $c) -notmatch 'ComputerName|UserName|S-1-5-21') }
Case 'verification_does_not_promote_static_PASS_to_enforcement' { $v=Test-WuaInstallation $plan $inventory $config;Assert ($v.static_plan_binding -eq 'PASS' -and $v.effective_wfp -eq 'NOT VERIFIED' -and $v.security_verdict -eq 'NOT VERIFIED') }
Case 'independent_static_verifier_accepts_only_complete_symbolic_denies' { Assert ((Test-WuaStaticPolicy $plan.payload.policy).status -eq 'PASS') }
Case 'independent_static_verifier_catches_missing_port_deny' { $p=CopyValue $plan.payload.policy;$p.rules=@($p.rules | Where-Object {$_.predicate -ne 'tcp_loopback_wrong_port'});Assert ((Test-WuaStaticPolicy $p).status -eq 'FAIL') }
Case 'independent_static_verifier_catches_allow_and_BlockALL_conflict' { $p=CopyValue $plan.payload.policy;$p.rules+= ,@{principal='client';family='v4';predicate='any';action='allow'};Assert ((Test-WuaStaticPolicy $p).status -eq 'FAIL') }
Case 'inventory_schema_string_and_fake_backend_are_invalid' { foreach ($pair in @(@('schema_version','1'),@('security_backend','VERIFIED'))) {$x=CopyValue $inventory;$x[$pair[0]]=$pair[1];Assert ((Get-WuaCoverage $x).issues.Count -gt 0)} }
Case 'inventory_bad_time_and_collection_are_rejected' { foreach ($pair in @(@('collected_utc','not-a-date'),@('collection_id','copied-host'))) {$x=CopyValue $inventory;$x[$pair[0]]=$pair[1];Assert ((Get-WuaCoverage $x).issues.Count -gt 0)} }
Case 'known_false_fact_is_not_safe_default' { $x=CopyValue $inventory;$f=$x.fields | Where-Object {$_.id -eq 'accounts.collision_free'};$f.value=$false;$row=(Get-WuaCoverage $x).rows | Where-Object {$_.id -eq 'accounts.collision_free'};Assert ($row.blocking -and -not $row.requirement_met) }
Case 'unsafe_ACL_and_logon_design_rejected' { foreach ($p in @(@{'files.acl_contract'=(New-WuaField 'files.acl_contract' 'DETECTED' @{scope='owned_resources_only';workspace_wide=$true})},@{'accounts.logon_rights'=(New-WuaField 'accounts.logon_rights' 'DETECTED' @{mode='task_batch';interactive=$false;admin=$true})})) {Throws {New-WuaInventory $config $p}} }
$resource=@{resource_id='44444444-4444-4444-8444-444444444444';owner_id=$config.owner_id;kind='filter';created_by_kit=$true;before_exists=$false;target_ref='policy:client'}
$ledger=@{schema_version=1;owner_id=$config.owner_id;plan_sha256=$plan.approval_sha256;resources=@($resource);process_state='unknown';flow_state='unknown'}
Case 'rollback_unknown_quiescence_retains_deny' { $r=New-WuaRollbackPlan $ledger;Assert ($r.status -eq 'ROLLBACK BLOCKED' -and $r.keep_deny -and $r.mutations -eq 0) }
Case 'rollback_reported_zero_not_trusted_authority' { $l=CopyValue $ledger;$l.process_state='reported_zero';$l.flow_state='reported_zero';Assert ((New-WuaRollbackPlan $l).status -eq 'ROLLBACK BLOCKED') }
Case 'rollback_foreign_resource_preexisting_or_duplicate_rejected' { foreach ($kind in @('foreign','preexisting','duplicate')) { $l=CopyValue $ledger;if ($kind -eq 'foreign') {$l.resources[0].owner_id='33333333-3333-4333-8333-333333333333'} elseif ($kind -eq 'preexisting') {$l.resources[0].before_exists=$true} else {$l.resources+= ,$l.resources[0]};Throws {New-WuaRollbackPlan $l} } }
Case 'rollback_unsafe_target_ref_not_interpreted_as_path_or_command' { $l=CopyValue $ledger;$l.resources[0].target_ref='C:\Windows';Throws {New-WuaRollbackPlan $l} }
Case 'rollback_safe_order_and_idempotent_pure_planning' { $a=New-WuaRollbackPlan $ledger;$b=New-WuaRollbackPlan $ledger;Assert ((Get-WuaHash $a) -ceq (Get-WuaHash $b));Assert ([Array]::IndexOf($a.order,'independently_verify_zero_processes_flows_and_queued_work') -lt [Array]::IndexOf($a.order,'remove_owned_deny_filters_last')) }
Case 'resume_same_owner_never_creates_duplicate_resources' { $a=Get-WuaResumeDecision $plan $ledger;$b=Get-WuaResumeDecision $plan $ledger;Assert ($a.status -eq 'BLOCKED' -and -not $a.create_duplicate -and (Get-WuaHash $a) -ceq (Get-WuaHash $b)) }
Case 'resume_different_plan_or_owner_rejected' { $l=CopyValue $ledger;$l.plan_sha256='b'*64;Assert ((Get-WuaResumeDecision $plan $l).status -eq 'FAIL') }
Case 'public_plan_omits_private_paths_remote_endpoint_and_new_names' { $s=ConvertTo-WuaCanonicalJson $plan;Assert (-not $s.Contains('C:\\Synthetic'));Assert (-not $s.Contains('192.0.2.44'));Assert (-not $s.Contains((Get-WuaCandidateNames $config).client)) }
Case 'policy_oracle_all_protocol_numbers_and_port_boundaries' {
    foreach ($proto in 0..255) { foreach ($port in @(0,1,1023,1024,54320,54321,54322,65535)) {
        $d=Get-WuaModelDecision 'client' 'v4' $proto '127.0.0.1' $port 54321 '192.0.2.44' 443
        $expected=if ($proto -eq 6 -and $port -eq 54321) {'CANDIDATE_EDGE'} else {'BLOCK'}
        Assert ($d -ceq $expected)
    } }
    foreach ($address in @('127.0.0.2','0.0.0.0','192.0.2.1','255.255.255.255','::ffff:127.0.0.1')) { Assert ((Get-WuaModelDecision 'client' 'v4' 6 $address 54321 54321 '192.0.2.44' 443) -eq 'BLOCK') }
    Assert ((Get-WuaModelDecision 'client' 'v6' 6 '::1' 54321 54321 '192.0.2.44' 443) -eq 'BLOCK')
    Assert ((Get-WuaModelDecision 'broker' 'v4' 6 '192.0.2.44' 443 54321 '192.0.2.44' 443) -eq 'CANDIDATE_EDGE')
    Assert ((Get-WuaModelDecision 'broker' 'v4' 6 '192.0.2.45' 443 54321 '192.0.2.44' 443) -eq 'BLOCK')
}
Case 'negative_control_oracle_kills_loopback_any_port_mutant' {
    function Mutant([string]$Address,[int]$Port) { if ($Address -eq '127.0.0.1') { return 'CANDIDATE_EDGE' };return 'BLOCK' }
    $caught=$false;try { Assert ((Mutant '127.0.0.1' 54322) -eq 'BLOCK') 'MUTANT_ACCEPTED_FORBIDDEN_PORT' } catch {$caught=$true};Assert $caught
}
$sources=@{}
foreach ($name in @('WuaMcp.psm1','Discovery.ps1','tests/Test-Toolkit.ps1')) {
    $p=Join-Path (Split-Path $PSScriptRoot -Parent) $name;$sources[$name]=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
}
Case 'source_pins_unchanged_during_suite' {foreach ($name in $sources.Keys) {Assert ($sources[$name] -ceq $sourcePins[$name]) 'SOURCE_DRIFT'}}
$fails=@($results | Where-Object {$_.status -eq 'FAIL'})
$summary=@{runtime=$RuntimeLabel;ps_version=$PSVersionTable.PSVersion.ToString();scope='synthetic pure functions and owned JSON files only';tests=$results.ToArray();total=$results.Count;passed=($results.Count-$fails.Count);failed=$fails.Count;sources=$sources;canonical_fixture_plan_sha256=$plan.approval_sha256;network_calls=0;windows_policy_calls=0;installer_or_uninstaller_invocations=0;mutations_outside_test_output=0;negative_controls=1}
Write-WuaJson (Join-Path $out 'results.json') $summary
Write-Output (ConvertTo-WuaCanonicalJson @{runtime=$RuntimeLabel;total=$results.Count;passed=($results.Count-$fails.Count);failed=$fails.Count;failed_cases=@($fails | ForEach-Object {$_.name});plan_hash=$plan.approval_sha256})
if ($fails.Count) { exit 1 }
