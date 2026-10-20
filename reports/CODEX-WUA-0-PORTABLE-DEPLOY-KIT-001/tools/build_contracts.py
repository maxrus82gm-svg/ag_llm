"""Authoring helper, not a runtime dependency of the portable PowerShell toolkit."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'toolkit/contracts'
OUT.mkdir(parents=True,exist_ok=True)
groups={
 'A': [('os.version','string','os','local CIM version'),('os.build','integer','os','local CIM build'),('os.edition','integer','os','local CIM SKU'),('os.architecture','string','arch','process/OS architecture metadata'),('powershell.version','string','ps','local runtime'),('api.wfp_file','boolean','api','system library presence, no load')],
 'B': [('bfe.state','string','services','local ServiceController'),('firewall.state','string','services','local ServiceController'),('firewall.profiles','object','firewall','local cached MSFT_NetFirewallProfile'),('policy.management','object','policy','local policy-key presence only'),('security.products','object','security','local SecurityCenter2 counts'),('security.admin_token','boolean','permissions','current token administrator membership boolean, no SID export'),('security.effective_policy','object','proof','effective WFP graph requires reviewed backend')],
 'C': [('accounts.collision_free','boolean','accounts','only generated technical candidate names'),('accounts.new_sid_binding','object','future','resolve NEW local SIDs at provisioning'),('accounts.logon_rights','object','operator','future least-privilege logon contract')],
 'D': [('endpoint.local','object','ports','operator port or deterministic unused candidate'),('endpoint.snapshot_free','boolean','ports','local TCP/UDP metadata, no bind'),('endpoint.receiver_guard','object','proof','bind/recipient enforcement must be proved')],
 'E': [('network.interfaces','object','network','local adapter counts, no names or hardware identifiers'),('network.families','object','network','local address family counts'),('network.routes','object','network','local route counts, no addresses'),('network.proxy_context','object','proxy','presence flags only, no values'),('network.dns_delegation','object','proof','DNS/service causal egress proof')],
 'F': [('broker.binary','object','broker','explicit local file metadata/hash only'),('broker.version','string','broker','file version metadata, not execution'),('broker.schema','object','operator','version-pinned offline schema review'),('broker.route_graph','object','proof','loaded config/overrides/DNS closure proof'),('broker.remote_endpoint','object','operator','operator supplies literal endpoint privately'),('broker.remote_identity','object','operator','server authentication reference, not secret')],
 'G': [('mcp.binary','object','client','explicit local file metadata/hash only'),('mcp.version','string','client','file version metadata, not execution'),('mcp.source_archive','object','source','exact provided archive size/hash'),('mcp.stdio_exe','object','stdio_exe','explicit interpreter metadata'),('mcp.stdio_script','object','stdio_script','explicit script hash, no execution'),('mcp.working_directory','object','cwd','explicit local working directory role reference'),('mcp.resources','object','resources','local read-only resource root reference'),('mcp.launcher_hold','object','operator','existing hold must remain, no launcher execution')],
 'H': [('startup.scheduler','string','services','local Schedule status'),('startup.execution_policy','string','permissions','effective script policy read-only; never bypass automatically'),('startup.mode','string','operator','batch/task or reviewed service wrapper'),('startup.dependencies','object','operator','deny before principals/workers'),('startup.child_identity','object','proof','primary token/children/delegation proof')],
 'I': [('files.deployment_root','object','root','local root, no reparse/network path'),('files.acl_contract','object','operator','role-based exact ACL, no workspace-wide grant'),('files.acl_effective','object','proof','actual per-new-SID access checks require trusted local backend')],
 'J': [('ownership.baseline','object','operator','owner GUID and new-resource/no-reuse contract'),('ledger.backend','object','future','trusted owner ledger after provisioning'),('rollback.quiescence','object','proof','independent absence of SID work/flows/delegation')],
 'K': [('wfp.sid_match','object','proof','actual ALE identity semantics'),('wfp.loopback','object','proof','exact endpoint, aliases and alternate ports'),('wfp.arbitration','object','proof','installed graph/third-party precedence'),('wfp.lifecycle','object','proof','boot/BFE/profile/established flows'),('verification.observer','object','proof','independent attempts observer with loss counters'),('host.binding','object','proof','trusted local device binding, not public inventory hash')]
}
fields=[]
for category,items in groups.items():
 for key,kind,probe,source in items:
  fields.append({'id':key,'category':category,'purpose':source,'source':source,'safe_read':'local metadata only; no network/remoting/elevation; proof/future never synthesized',
    'type':kind,'validation':{'strict_type':True,'max_string_length':256,'no_unknown_safe_default':True},'required':True,
    'sensitivity':'public_aggregate_or_role_reference','statuses':['DETECTED','VERIFIED','MISSING','UNSUPPORTED','CONFLICT','REQUIRES_USER_INPUT'],
    'probe':probe,'stop_rule':'block all dependent mutations unless required evidence is valid and complete',
    'dependent_actions':['plan','install','verify','rollback'],'security_proof':probe=='proof'})
manifest={'schema_version':1,'contract_id':'wua.discovery.v1','coverage_definition':'100% required entries represented with explicit status; not 100% security verification',
          'categories':list(groups),'fields':fields}
(OUT/'requirements_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(OUT/'discovery_contract.json').write_text(json.dumps({'schema_version':1,'requirements':'requirements_manifest.json','expected_fields':len(fields),
 'statuses':['DETECTED','VERIFIED','MISSING','UNSUPPORTED','CONFLICT','REQUIRES_USER_INPUT'],
 'unavailable_detail':['REQUIRES_ELEVATION','BLOCKED','NOT_IMPLEMENTED','NOT_SUPPLIED'],
 'privacy':'No host/user/SID/address/credential/raw-command output. Public data uses aggregates and symbolic refs.',
 'compatibility':'PowerShell 5.1 and 7 parser/runtime tests; metadata profiles are not OS security certification.',
 'apply':'No executable security backend in v1. Apply cannot be enabled by input attestations.'},indent=2)+'\n',encoding='utf-8')
print('REQUIRED_FIELDS',len(fields))
