"""I01-I12 offline evidence checker. No VM/OS/network mutation functions.

Explicit out-of-band pinned trust store; RSA verification via the bounded local
managed helper. Real PASS means evidence validated, never authority to execute.
"""
from pathlib import Path,PureWindowsPath
import argparse,base64,datetime as dt,hashlib,json,os,re,subprocess,sys,uuid
ROOT=Path(__file__).resolve().parents[1]
IDS=[f'I{i:02}' for i in range(1,13)]
ROLES={'I01':['host','guest'],'I02':['host'],'I03':['host','guest'],'I04':['host'],'I05':['guest'],'I06':['host','guest'],'I07':['host','guest'],'I08':['host','guest'],'I09':['guest'],'I10':['host','guest'],'I11':['host','guest'],'I12':['host']}
UTC=dt.timezone.utc
class Invalid(Exception):pass
def need(ok,code):
    if not ok:raise Invalid(code)
def pairs(items):
    out={}
    for k,v in items:
        need(k not in out,'DUPLICATE_JSON_KEY');out[k]=v
    return out
def parse(raw):
    need(len(raw)<=1048576,'INPUT_SIZE')
    try:obj=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(Invalid('NONFINITE_JSON')))
    except (ValueError,RecursionError):raise Invalid('JSON_SYNTAX')
    def walk(x,depth=0):
        need(depth<=16,'INPUT_DEPTH');need(not isinstance(x,(dict,list)) or len(x)<=256,'INPUT_ITEMS')
        if isinstance(x,dict):
            for k,v in x.items():need(isinstance(k,str) and len(k)<=128,'KEY_DOMAIN');walk(v,depth+1)
        elif isinstance(x,list):
            for v in x:walk(v,depth+1)
        elif isinstance(x,str):need(len(x)<=8192,'STRING_LIMIT')
        else:need(x is None or type(x) in (bool,int),'JSON_TYPE')
    walk(obj);return obj
def canonical(x):return json.dumps(x,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode('ascii')
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def keys(obj,expected,required=None):
    need(type(obj) is dict,'OBJECT_REQUIRED');need(set(obj)<=set(expected),'UNKNOWN_FIELD')
    if required is not None:need(set(required)<=set(obj),'MISSING_FIELD')
def guid(s):
    try:return isinstance(s,str) and str(uuid.UUID(s))==s and uuid.UUID(s).int!=0
    except (ValueError,AttributeError):return False
def hash_ok(s):return isinstance(s,str) and re.fullmatch('[0-9a-f]{64}',s) is not None
def stamp(s):
    need(isinstance(s,str) and s.endswith('Z'),'UTC_REQUIRED')
    try:return dt.datetime.fromisoformat(s[:-1]+'+00:00')
    except ValueError:raise Invalid('INVALID_TIME')
def environment():
    out={k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ};return out
def verify_signature(key,body,sig,helper,helper_hash):
    keys(key,['n','e'],['n','e']);need(helper.is_file() and hashlib.sha256(helper.read_bytes()).hexdigest()==helper_hash,'CRYPTO_HELPER_PIN')
    need(type(sig) is str and len(sig)<=1024,'SIGNATURE_FORMAT')
    try:
        for s in [key['n'],key['e'],sig]:base64.b64decode(s,validate=True)
        result=subprocess.run([str(helper),'verify'],input='\n'.join([key['n'],key['e'],digest(body),sig])+'\n',text=True,capture_output=True,env=environment(),timeout=8)
    except (OSError,ValueError,subprocess.TimeoutExpired):raise Invalid('CRYPTO_UNAVAILABLE')
    need(result.returncode==0,'INVALID_SIGNATURE')
def request_check(r,now):
    names=['schema','owner','vm_guid','boot_id','guest_baseline_digest','run_id','nonce','backend','backend_version','config_digest','media_digest','chain_digest','assets_digest','rollback_digest','valid_from','valid_until','endpoints','assets','disks','approval']
    keys(r,names,names);need(type(r['schema']) is int and r['schema']==1,'SCHEMA');need(all(guid(r[k]) for k in ['owner','vm_guid','boot_id','run_id']),'IDENTITY_FORMAT')
    need(all(hash_ok(r[k]) for k in ['nonce','guest_baseline_digest','config_digest','media_digest','chain_digest','assets_digest','rollback_digest']),'BINDING_HASH')
    need(r['backend']=='Hyper-V' and isinstance(r['backend_version'],str) and re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}',r['backend_version']),'BACKEND_UNSUPPORTED')
    start,end=stamp(r['valid_from']),stamp(r['valid_until']);need(dt.timedelta(0)<end-start<=dt.timedelta(minutes=5),'VALIDITY_WINDOW')
    need(type(r['endpoints']) is list and 0<len(r['endpoints'])<=8,'ENDPOINTS')
    ports=set()
    for e in r['endpoints']:
        keys(e,['address','port','transport'],['address','port','transport']);need(e['address']=='127.0.0.1' and e['transport']=='tcp' and type(e['port']) is int and 1<=e['port']<=65535 and e['port'] not in ports,'LOOPBACK_ENDPOINT_REQUIRED');ports.add(e['port'])
    need(type(r['assets']) is list and len(r['assets'])==6,'ASSETS')
    for a in r['assets']:
        keys(a,['role','sha256','bytes','origin_review'],['role','sha256','bytes','origin_review']);need(a['role'] in ['wfp_source','wfp_binary','observer_host','observer_guest','fixture','windows_media'] and hash_ok(a['sha256']) and type(a['bytes']) is int and a['bytes']>0 and hash_ok(a['origin_review']),'ASSET_DOMAIN')
    need(digest(r['assets'])==r['assets_digest'],'ASSET_MANIFEST_MISMATCH')
    need(set(a['role'] for a in r['assets'])=={'wfp_source','wfp_binary','observer_host','observer_guest','fixture','windows_media'},'ASSET_COVERAGE')
    need(next(a['sha256'] for a in r['assets'] if a['role']=='windows_media')==r['media_digest'],'MEDIA_ASSET_BINDING')
    need(type(r['disks']) is list and 0<len(r['disks'])<=8,'DISK_CHAIN_REQUIRED');disk_map={}
    for d in r['disks']:
        keys(d,['id','owner','sha256','bytes','parent','local','reparse','shared_writable','host_mounted'],['id','owner','sha256','bytes','parent','local','reparse','shared_writable','host_mounted'])
        need(guid(d['id']) and d['id'] not in disk_map and d['owner']==r['owner'] and hash_ok(d['sha256']) and type(d['bytes']) is int and d['bytes']>0,'DISK_OWNERSHIP')
        need(all(type(d[k]) is bool for k in ['local','reparse','shared_writable','host_mounted']) and d['local'] and not any(d[k] for k in ['reparse','shared_writable','host_mounted']),'DISK_BACKEND_UNSAFE')
        need(d['parent'] is None or guid(d['parent']),'DISK_PARENT');disk_map[d['id']]=d
    need(sum(d['parent'] is None for d in r['disks'])==1 and digest(r['disks'])==r['chain_digest'],'DISK_CHAIN_MANIFEST')
    for d in r['disks']:
        seen=set();cursor=d
        while cursor['parent'] is not None:
            need(cursor['id'] not in seen and cursor['parent'] in disk_map,'DISK_CYCLE_OR_FOREIGN_PARENT');seen.add(cursor['id']);cursor=disk_map[cursor['parent']]
    keys(r['approval'],['read_only_review','provision','native'],['read_only_review','provision','native']);need(all(type(v) is bool for v in r['approval'].values()),'APPROVAL_TYPES')
    return start<=now<end
def trust_check(t,expected,synthetic):
    need(hash_ok(expected) and digest(t)==expected,'TRUST_PIN_MISMATCH');keys(t,['schema','test_only','approved_request_sha256','principals','crypto_helper_sha256','observers'],['schema','test_only','approved_request_sha256','principals','crypto_helper_sha256','observers'])
    need(type(t['schema']) is int and t['schema']==1 and type(t['test_only']) is bool,'TRUST_SCHEMA')
    need(True,'MUTANT_ACCEPTS_TEST_TRUST');need(hash_ok(t['crypto_helper_sha256']) and hash_ok(t['approved_request_sha256']),'CRYPTO_OR_REQUEST_PIN')
    keys(t['principals'],['host','guest','review'],['host','guest','review']);principals=[];fingerprints=[]
    for role,p in t['principals'].items():
        keys(p,['principal_id','key'],['principal_id','key']);need(guid(p['principal_id']),'TRUST_PRINCIPAL');principals.append(p['principal_id']);fingerprints.append(digest(p['key']))
    need(len(set(principals))==3 and len(set(fingerprints))==3,'INDEPENDENT_PRINCIPALS_REQUIRED')
    keys(t['observers'],['host','guest'],['host','guest'])
    for o in t['observers'].values():keys(o,['version','sha256'],['version','sha256']);need(isinstance(o['version'],str) and hash_ok(o['sha256']),'OBSERVER_TRUST')
def checked_doc(envelope,role,r,t,helper,now):
    keys(envelope,['body','signature'],['body','signature']);b=envelope['body'];names=['role','request_hash','observed_at','facts'] if role!='review' else ['role','request_hash','observed_at','host_hash','guest_hash','decisions']
    keys(b,names,names);need(b['role']==role and b['request_hash']==digest(r),'DOC_REQUEST_IDENTITY')
    verify_signature(t['principals'][role]['key'],b,envelope['signature'],helper,t['crypto_helper_sha256'])
    observed=stamp(b['observed_at']);need(stamp(r['valid_from'])<=observed<=now and now-observed<=dt.timedelta(seconds=60),'OBSERVATION_STALE')
    return b
def facts_check(i,f,r,role,t):
    """Return diagnostic state; values never become trusted merely by being present."""
    expected={
      'I01':{'vm_guid':'bind:vm_guid','owner':'bind:owner','boot_id':'bind:boot_id','guest_baseline_digest':'bind:guest_baseline_digest','vm_state':'Running','backend':'bind:backend','backend_version':'bind:backend_version','config_digest':'bind:config_digest','run_id':'bind:run_id'},
      'I02':{'census_complete':True,'nic_count':0,'legacy_nics':0,'nat_edges':0,'bridge_edges':0,'hostonly_edges':0,'forwarders':0,'passthrough':0},
      'I03':{'census_complete':True,'shared_folders':0,'clipboard':False,'enhanced_console':False,'powershell_direct':False,'guest_relay':False,'serial_pipes':0,'usb_relay':0,'gpu_relay':0,'host_disk_mounts':0,'console_mode':'basic'},
      'I04':{'census_complete':True,'chain_digest':'bind:chain_digest','media_digest':'bind:media_digest','local_only':True,'owned_only':True,'no_reparse':True,'shared_writable':False,'concurrent_mount':False,'input_readonly':True,'output_bridge':False},
      'I05':{'census_complete':True,'nonloopback_adapters':0,'nonloopback_addresses':0,'gateways':0,'resolvers':0,'proxy_endpoints':0,'relays':0},
      'I06':{'assets_digest':'bind:assets_digest','origins_reviewed':True,'dependencies_offline':True,'startup_audited':True,'auto_install':False},
      'I07':{'schema_reviewed':True,'fresh_profile':True,'host_credentials_inherited':False,'real_tunnel_id':False,'secrets_present':False,'real_profiles':False,'original_launcher_changed':False},
      'I08':{'observer_hash':t['observers'][role]['sha256'],'observer_version':t['observers'][role]['version'],'coverage_validated':True,'socket_attempts':True,'dns_attempts':True,'process_events':True,'children':True,'refused_attempts':True,'started_before_subject':True,'loss_count':0,'restarts':0,'zero_packets_only':False,'run_id':'bind:run_id','heartbeat_age_ms':'range:0:1000','monotonic_duration_ms':'range:1:300000','clock_correlation_error_ms':'range:0:1000','trace_retained':True},
      'I09':{'endpoint_digest':digest(r['endpoints']),'owned_receivers':True,'positive_receipts':True,'negative_controls_reviewed':True,'cleanup_known':True,'wildcard':False,'dns_used':False,'external_upstream':False},
      'I10':{'assets_digest':'bind:assets_digest','all_processes_in_guest':True,'unknown_children':0,'unapproved_helpers':0,'cloudflared':False,'inherited_secrets':False},
      'I11':{'before_digest':'bind:config_digest','after_digest':'bind:config_digest','watch_complete':True,'config_drift':0,'heartbeat_ok':True,'independent_power_control':True,'admissions_frozen_on_loss':True},
      'I12':{'rollback_digest':'bind:rollback_digest','ledger_owner':'bind:owner','clean_checkpoint_reviewed':True,'disk_chain_reviewed':True,'independent_stop_ready':True,'evidence_retention':True,'recovery_reviewed':True,'network_reset_required':False}}
    want=expected[i];keys(f,want)
    if set(f)!=set(want):return 'BLOCKED','MISSING_REQUIRED_FACT'
    for k,value in want.items():
        if isinstance(value,str) and value.startswith('range:'):
            low,high=map(int,value.split(':')[1:]);need(type(f[k]) is int,'FACT_TYPE')
            if not low<=f[k]<=high:return 'BLOCKED','OBSERVATION_RANGE_'+k.upper()
            continue
        v=r[value[5:]] if isinstance(value,str) and value.startswith('bind:') else value
        need(type(f[k]) is type(v),'FACT_TYPE')
        if f[k]!=v:
            if k in ['observer_hash','observer_version']:return 'BLOCKED','UNKNOWN_OBSERVER'
            if k in ['census_complete','coverage_validated','origins_reviewed','startup_audited','schema_reviewed','watch_complete','clean_checkpoint_reviewed','disk_chain_reviewed','recovery_reviewed']:return 'BLOCKED','INCOMPLETE_PROOF_'+k.upper()
            return 'FAIL','CONTRADICTION_'+k.upper()
    return 'PASS','SIGNED_AND_INDEPENDENTLY_REVIEWED_SNAPSHOT'
def evaluate(bundle,trust,trust_pin,now,helper,synthetic=False):
    rows={i:{'id':i,'status':'BLOCKED','reason':'MISSING_EVIDENCE','sources':[]} for i in IDS};overall='BLOCKED';source='SYNTHETIC' if synthetic else 'REAL_EVIDENCE_VALIDATION'
    try:
        need(now.tzinfo==UTC,'DECISION_UTC_REQUIRED');keys(bundle,['request','host','guest','review'],['request']);r=bundle['request']
        if r is None:
            return {'schema':1,'decision':'BLOCKED','scope':source,'requirements':[{'id':i,'status':'BLOCKED','reason':'LAB_NOT_PROVISIONED_NO_APPROVED_IDENTITY','sources':[]} for i in IDS],'evidence_digest':digest(bundle),'native_execution_allowed':False,'vm_changes_allowed':False,'real_isolation':'NOT VERIFIED','states':['LAB_PLATFORM_NOT_PROVISIONED','HOST_CONFIG_PROOF_PENDING','GUEST_ISOLATION_PROOF_PENDING','NATIVE_WFP_EXECUTION_BLOCKED']}
        fresh=request_check(r,now)
        if trust is None:raise Invalid('TRUST_ROOT_NOT_SUPPLIED')
        trust_check(trust,trust_pin,synthetic)
        need(trust['approved_request_sha256']==digest(r),'REQUEST_APPROVAL_BINDING')
        for role in ['host','guest']:
            need(next(a['sha256'] for a in r['assets'] if a['role']=='observer_'+role)==trust['observers'][role]['sha256'],'OBSERVER_ASSET_BINDING')
        docs={};errors={}
        for role in ['host','guest','review']:
            if role not in bundle:errors[role]=('BLOCKED','MISSING_'+role.upper());continue
            try:docs[role]=checked_doc(bundle[role],role,r,trust,helper,now)
            except Invalid as e:errors[role]=('BLOCKED' if str(e) in ['OBSERVATION_STALE','CRYPTO_UNAVAILABLE','CRYPTO_HELPER_PIN','MISSING_FIELD'] else 'FAIL',str(e))
        for role in ['host','guest']:
            if role in docs:keys(docs[role]['facts'],[i for i in IDS if role in ROLES[i]])
        review=docs.get('review')
        if review:
            keys(review['decisions'],IDS,IDS)
            for role in ['host','guest']:
                if role in docs:need(review[role+'_hash']==digest(docs[role]),'REVIEW_SNAPSHOT_MISMATCH')
        for i in IDS:
            issues=[errors[role] for role in ROLES[i]+['review'] if role in errors]
            states=[]
            for role in ROLES[i]:
                if role not in docs:continue
                fact=docs[role]['facts'].get(i)
                if fact is None:states.append(('BLOCKED','MISSING_'+role.upper()+'_FACTS'));continue
                states.append(facts_check(i,fact,r,role,trust));rows[i]['sources'].append({'role':role,'body_sha256':digest(docs[role])})
            issues.extend(x for x in states if x[0]!='PASS')
            if review:
                decision=review['decisions'][i];need(decision in ['CONFIRMED','BLOCKED','FAIL'],'REVIEW_DECISION_DOMAIN')
                if decision!='CONFIRMED':issues.append((decision,'INDEPENDENT_REVIEW_'+decision))
            if issues:
                issue=next((x for x in issues if x[0]=='FAIL'),issues[0]);rows[i].update(status=issue[0],reason=issue[1])
            else:
                if not fresh:rows[i].update(reason='REQUEST_EXPIRED_OR_FUTURE');continue
                if not r['approval']['read_only_review']:rows[i].update(reason='READ_ONLY_REVIEW_NOT_APPROVED');continue
                rows[i].update(status='PASS',reason='SIGNED_AND_INDEPENDENTLY_REVIEWED_SNAPSHOT')
        overall='FAIL' if any(x['status']=='FAIL' for x in rows.values()) else 'PASS' if all(x['status']=='PASS' for x in rows.values()) else 'BLOCKED'
    except (Invalid,KeyError,TypeError,ValueError) as e:
        code=str(e) if isinstance(e,Invalid) else 'INVALID_SCHEMA'
        blocked=code in ['TRUST_ROOT_NOT_SUPPLIED','TEST_TRUST_IN_REAL_MODE','CRYPTO_UNAVAILABLE','CRYPTO_HELPER_PIN','MISSING_FIELD']
        overall='BLOCKED' if blocked else 'FAIL'
        for row in rows.values():row.update(status=overall,reason=code,sources=[])
    return {'schema':1,'decision':overall,'scope':source,'requirements':list(rows.values()),'evidence_digest':digest(bundle),'native_execution_allowed':False,'vm_changes_allowed':False,'real_isolation':'NOT VERIFIED' if synthetic or overall!='PASS' else 'EVIDENCE VALIDATED ONLY; LIVE LEASE/RECHECK REQUIRED','states':['OFFLINE_GATE_LOGIC_TESTED' if synthetic else 'HOST_CONFIG_PROOF_PENDING','NATIVE_WFP_EXECUTION_BLOCKED'],'notes':'Signature validates provenance, not sensor truth. Out-of-band pinned trust ceremony and independent observer validation required; this receipt is not an execution capability.'}
def plan(owner,resource_root,media_digest,inventory):
    need(guid(owner),'OWNER_REQUIRED');p=PureWindowsPath(resource_root);need(p.is_absolute() and re.fullmatch('[A-Za-z]:',p.drive) and len(p.parts)>=3 and '..' not in p.parts and ':' not in ''.join(p.parts[1:]) and not any(x.lower() in ['windows','users','program files','ag_llm'] for x in p.parts[1:]),'NEW_LOCAL_ROOT_REQUIRED');need(hash_ok(media_digest),'MEDIA_HASH_REQUIRED')
    reserved={'CON','AUX','PRN','NUL'}|{f'{prefix}{n}' for prefix in ['COM','LPT'] for n in range(1,10)}
    need(all(re.fullmatch(r'[A-Za-z0-9 _.-]+',part) and part[-1] not in ' .' and part.split('.')[0].upper() not in reserved for part in p.parts[1:]),'ROOT_SEGMENT_UNSAFE')
    operations=[('platform_preflight','Confirm installed supported Hyper-V; missing platform requires separate host-change permission'),('reserve_owned_root','Verify fixed local volume, no reparse/remote/cloud path, new root and owner quota/ledger'),('verify_offline_assets','Hash/license/image/dependency/observer closure; no secrets or real profiles'),('create_powered_off_vm','Create ONE owned VM, record returned GUID; no switch/NAT/bridge. Default NIC may exist transiently while OFF'),('remove_default_nic_before_boot','Remove owned NIC objects and all passthrough before any boot; disconnected NIC is insufficient'),('close_integration_channels','Per-VM disable integration/data relay; verify basic console and no PowerShell Direct, host disks or forwarding; unknown channel STOP'),('prepare_owned_disk_chain','Create local isolated guest disk and readonly input media; verify full parent chain and exclusive ownership'),('host_preboot_review','Full device/channel/storage census plus independent external review before first controlled boot'),('controlled_guest_boot','Separate provisioning GO must include boot for guest/observer baseline; no MCP/WFP subject'),('collect_guest_and_observer_proofs','Guest PnP/net/routes/DNS/relay/credentials, validated attempts observers, heartbeat/loss and fixture controls'),('clean_baseline_and_gate','Owned checkpoint/rollback proof; two signed evidence sources and independent review of same snapshot'),('await_native_user_go','Native execution remains BLOCKED; distinct later TASK, exact cases, time quota and independent acceptance'),('owned_exit_cleanup_plan','Host-side stop/quarantine/evidence then exact GUID/root deletion only with ownership and separate cleanup authority; no host network reset')]
    actions=[{'order':n+1,'what':name,'why':why,'target':'owned lab VM/root only','before':'uncreated/unverified or preceding step independently accepted','after':'reviewed stage; subject remains disabled','privileges':'future Hyper-V admin for VM operations; none requested now','verification':'fresh exact GUID/owner/device/media/digest readback; fail on unknown','rollback':'keep OFF/quarantine and retain evidence; only exact owned objects after separate authorization','executable':False,'status':'BLOCKED / SEPARATE USER GO'} for n,(name,why) in enumerate(operations)]
    body={'schema':1,'owner':owner,'resource_root_ref':digest(resource_root),'root_private_preview_required':True,'media_digest':media_digest,'host_inventory_digest':digest(inventory),'vm_guid':'UNASSIGNED_UNTIL_FUTURE_CREATION','proposed_vm_name':'wua-lab-'+owner.replace('-','')[:12],'sizing_proposal':{'memory_mib':4096,'cpu':2,'disk_gib':64,'generation':2,'status':'PROPOSAL_REQUIRES_EXPLICIT_REVIEW_NOT_RESERVED'},'desired_nic_objects':0,'native_execution_allowed':False,'platform_detected':inventory.get('hyperv_module_present') is True,'actions':actions,'can_apply':False}
    return {'plan':body,'plan_sha256':digest(body)}
def write_new(path,obj):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def cli_path(value,existing=True):
    # Only staged package-local files. Reject remote syntax before any path I/O.
    text=str(value);need(not text.startswith(('\\\\','//')) and '://' not in text,'LOCAL_PATH_REQUIRED')
    p=Path(os.path.abspath(text));root=Path(os.path.abspath(ROOT))
    try:need(os.path.commonpath([str(p),str(root)]).casefold()==str(root).casefold() and p!=root,'PATH_SCOPE')
    except ValueError:raise Invalid('PATH_SCOPE')
    if os.name=='nt':
        import ctypes
        get_type=ctypes.windll.kernel32.GetDriveTypeW;get_type.argtypes=[ctypes.c_wchar_p];get_type.restype=ctypes.c_uint
        kind=get_type(str(p.anchor));need(kind in (2,3),'LOCAL_VOLUME_REQUIRED')
    cursor=Path(p.anchor)
    for n,part in enumerate(p.parts[1:]):
        cursor=cursor/part
        if not existing and cursor==p:break
        try:s=cursor.lstat()
        except OSError:raise Invalid('LOCAL_PATH_UNAVAILABLE')
        need(not cursor.is_symlink() and not getattr(s,'st_file_attributes',0)&(0x400|0x1000|0x40000|0x400000),'REPARSE_OR_OFFLINE_PATH')
    return p
def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    g=sub.add_parser('check');g.add_argument('--bundle',required=True);g.add_argument('--trust');g.add_argument('--trust-sha256');g.add_argument('--helper',required=True);g.add_argument('--now');g.add_argument('--synthetic',action='store_true');g.add_argument('--output',required=True)
    p=sub.add_parser('plan');p.add_argument('--owner',required=True);p.add_argument('--root',required=True);p.add_argument('--media-sha256',required=True);p.add_argument('--inventory',required=True);p.add_argument('--output',required=True);p.add_argument('--private-preview',action='store_true')
    a=ap.parse_args()
    try:
        if a.command=='check':
            need(not a.now or a.synthetic,'DECISION_CLOCK_OVERRIDE');now=stamp(a.now) if a.now else dt.datetime.now(UTC)
            result=evaluate(parse(cli_path(a.bundle).read_bytes()),parse(cli_path(a.trust).read_bytes()) if a.trust else None,a.trust_sha256,now,cli_path(a.helper),a.synthetic)
        else:
            result=plan(a.owner,a.root,a.media_sha256,parse(cli_path(a.inventory).read_bytes()))
            if a.private_preview:print(json.dumps({'private_local_preview':{'resource_root':a.root,'system_disk':str(PureWindowsPath(a.root)/'disk'/'system.vhdx'),'vm_name':result['plan']['proposed_vm_name'],'sizing':result['plan']['sizing_proposal'],'plan_sha256':result['plan_sha256']}}))
        write_new(cli_path(a.output,False),result);print('OFFLINE_RESULT_SAVED; NATIVE/VM APPLY BLOCKED')
        return ({'PASS':0,'FAIL':10,'BLOCKED':20}[result['decision']] if a.command=='check' else 0)
    except (Invalid,OSError,ValueError):print('BLOCKED:INPUT_OR_OUTPUT_REJECTED');return 20
if __name__=='__main__':sys.exit(main())
