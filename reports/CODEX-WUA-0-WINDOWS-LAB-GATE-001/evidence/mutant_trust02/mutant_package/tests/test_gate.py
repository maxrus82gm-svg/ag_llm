"""Independent synthetic facts. No production checker used to construct expected facts."""
from pathlib import Path
import base64,copy,datetime as dt,hashlib,io,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'));import lab_gate as gate
NOW=dt.datetime(2030,1,1,0,0,30,tzinfo=dt.timezone.utc)
OWNER='11111111-1111-4111-8111-111111111111';VM='22222222-2222-4222-8222-222222222222';RUN='33333333-3333-4333-8333-333333333333'
H=lambda c:c*64
HELPER=Path(sys.argv[1]);OUT=Path(sys.argv[2]);sys.argv=sys.argv[:1]
def iso(d):return d.isoformat().replace('+00:00','Z')
class Fixtures:
    def __init__(self):
        self.proc=subprocess.Popen([str(HELPER),'synthetic-session'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=gate.environment())
        self.pub=json.loads(self.proc.stdout.readline());self.calls=0
        self.trust={'schema':1,'test_only':True,'principals':{role:{'principal_id':str(__import__('uuid').UUID(int=n)),'key':key} for n,(role,key) in enumerate(self.pub.items(),1)},'crypto_helper_sha256':hashlib.sha256(HELPER.read_bytes()).hexdigest(),'observers':{'host':{'version':'1.0','sha256':H('c')},'guest':{'version':'1.0','sha256':H('d')}}}
        assets=[{'role':role,'sha256':H(c),'bytes':123,'origin_review':H('e')} for role,c in zip(['wfp_source','wfp_binary','observer_host','observer_guest','fixture','windows_media'],'abcdef')]
        assets[-1]['sha256']=H('2');disks=[{'id':'44444444-4444-4444-8444-444444444444','owner':OWNER,'sha256':H('7'),'bytes':1024,'parent':None,'local':True,'reparse':False,'shared_writable':False,'host_mounted':False}]
        self.request={'schema':1,'owner':OWNER,'vm_guid':VM,'boot_id':'55555555-5555-4555-8555-555555555555','guest_baseline_digest':H('8'),'run_id':RUN,'nonce':H('9'),'backend':'Hyper-V','backend_version':'10.0.19045','config_digest':H('1'),'media_digest':H('2'),'chain_digest':gate.digest(disks),'assets_digest':gate.digest(assets),'rollback_digest':H('4'),'valid_from':iso(NOW-dt.timedelta(seconds=30)),'valid_until':iso(NOW+dt.timedelta(seconds=60)),'endpoints':[{'address':'127.0.0.1','port':54321,'transport':'tcp'}],'assets':assets,'disks':disks,'approval':{'read_only_review':True,'provision':False,'native':False}}
        common={
        'I01':{'vm_guid':VM,'owner':OWNER,'boot_id':'55555555-5555-4555-8555-555555555555','guest_baseline_digest':H('8'),'vm_state':'Running','backend':'Hyper-V','backend_version':'10.0.19045','config_digest':H('1'),'run_id':RUN},
        'I02':{'census_complete':True,'nic_count':0,'legacy_nics':0,'nat_edges':0,'bridge_edges':0,'hostonly_edges':0,'forwarders':0,'passthrough':0},
        'I03':{'census_complete':True,'shared_folders':0,'clipboard':False,'enhanced_console':False,'powershell_direct':False,'guest_relay':False,'serial_pipes':0,'usb_relay':0,'gpu_relay':0,'host_disk_mounts':0,'console_mode':'basic'},
        'I04':{'census_complete':True,'chain_digest':gate.digest(disks),'media_digest':H('2'),'local_only':True,'owned_only':True,'no_reparse':True,'shared_writable':False,'concurrent_mount':False,'input_readonly':True,'output_bridge':False},
        'I05':{'census_complete':True,'nonloopback_adapters':0,'nonloopback_addresses':0,'gateways':0,'resolvers':0,'proxy_endpoints':0,'relays':0},
        'I06':{'assets_digest':gate.digest(assets),'origins_reviewed':True,'dependencies_offline':True,'startup_audited':True,'auto_install':False},
        'I07':{'schema_reviewed':True,'fresh_profile':True,'host_credentials_inherited':False,'real_tunnel_id':False,'secrets_present':False,'real_profiles':False,'original_launcher_changed':False},
        'I08':{'observer_hash':H('c'),'observer_version':'1.0','coverage_validated':True,'socket_attempts':True,'dns_attempts':True,'process_events':True,'children':True,'refused_attempts':True,'started_before_subject':True,'loss_count':0,'restarts':0,'zero_packets_only':False,'run_id':RUN,'heartbeat_age_ms':50,'monotonic_duration_ms':10000,'clock_correlation_error_ms':10,'trace_retained':True},
        'I09':{'endpoint_digest':gate.digest(self.request['endpoints']),'owned_receivers':True,'positive_receipts':True,'negative_controls_reviewed':True,'cleanup_known':True,'wildcard':False,'dns_used':False,'external_upstream':False},
        'I10':{'assets_digest':gate.digest(assets),'all_processes_in_guest':True,'unknown_children':0,'unapproved_helpers':0,'cloudflared':False,'inherited_secrets':False},
        'I11':{'before_digest':H('1'),'after_digest':H('1'),'watch_complete':True,'config_drift':0,'heartbeat_ok':True,'independent_power_control':True,'admissions_frozen_on_loss':True},
        'I12':{'rollback_digest':H('4'),'ledger_owner':OWNER,'clean_checkpoint_reviewed':True,'disk_chain_reviewed':True,'independent_stop_ready':True,'evidence_retention':True,'recovery_reviewed':True,'network_reset_required':False}}
        # Explicit independent role partition, not derived from gate.ROLES.
        self.host={i:copy.deepcopy(common[i]) for i in ['I01','I02','I03','I04','I06','I07','I08','I10','I11','I12']}
        self.guest={i:copy.deepcopy(common[i]) for i in ['I01','I03','I05','I06','I07','I08','I09','I10','I11']};self.guest['I08']['observer_hash']=H('d')
    def sign(self,role,body):
        self.calls+=1;assert self.calls<250
        self.proc.stdin.write(role+' '+gate.digest(body)+'\n');self.proc.stdin.flush();signature=self.proc.stdout.readline().strip();assert signature
        return {'body':body,'signature':signature}
    def bundle(self,modify=None):
        r=copy.deepcopy(self.request);h=copy.deepcopy(self.host);g=copy.deepcopy(self.guest)
        if modify:modify(r,h,g)
        host=self.sign('host',{'role':'host','request_hash':gate.digest(r),'observed_at':iso(NOW-dt.timedelta(seconds=1)),'facts':h})
        guest=self.sign('guest',{'role':'guest','request_hash':gate.digest(r),'observed_at':iso(NOW-dt.timedelta(seconds=1)),'facts':g})
        review=self.sign('review',{'role':'review','request_hash':gate.digest(r),'observed_at':iso(NOW),'host_hash':gate.digest(host['body']),'guest_hash':gate.digest(guest['body']),'decisions':{i:'CONFIRMED' for i in [f'I{n:02}' for n in range(1,13)]}})
        return {'request':r,'host':host,'guest':guest,'review':review}
    def close(self):self.proc.stdin.write('close\n');self.proc.stdin.flush();self.proc.communicate(timeout=8);assert self.proc.returncode==0
F=None
class GateTests(unittest.TestCase):
    def eval(self,b=None,t=None,**kw):return gate.evaluate(b or BASE,t or F.trust,gate.digest(t or F.trust),NOW,HELPER,kw.get('synthetic',True))
    def mutated(self,role,i,k,v):return F.bundle(lambda r,h,g:(h if role=='host' else g)[i].__setitem__(k,v))
    def expect_bad(self,role,i,k,v,decision='FAIL'):
        result=self.eval(self.mutated(role,i,k,v));self.assertEqual(result['decision'],decision);self.assertEqual(next(x for x in result['requirements'] if x['id']==i)['status'],decision)
    def test_positive_all_twelve_independent_proofs(self):
        r=self.eval();self.assertEqual(r['decision'],'PASS');self.assertEqual([x['id'] for x in r['requirements']],[f'I{n:02}' for n in range(1,13)]);self.assertFalse(r['native_execution_allowed']);self.assertEqual(r['scope'],'SYNTHETIC')
    def test_deterministic_same_snapshot(self):self.assertEqual(self.eval(),self.eval())
    def test_real_mode_rejects_synthetic_trust(self):self.assertEqual(self.eval(synthetic=False)['decision'],'BLOCKED')
    def test_no_lab_is_blocked_not_vacuous_pass(self):self.assertEqual(gate.evaluate({'request':None},None,None,NOW,HELPER)['decision'],'BLOCKED')
    def test_no_root_cannot_self_attest(self):self.assertEqual(gate.evaluate(BASE,None,None,NOW,HELPER)['decision'],'BLOCKED')
    def test_trust_pin_mismatch(self):self.assertEqual(gate.evaluate(BASE,F.trust,H('0'),NOW,HELPER,True)['decision'],'FAIL')
    def test_one_actor_or_reused_key_not_independent(self):
        for field in ['key','principal_id']:
            t=copy.deepcopy(F.trust);t['principals']['guest'][field]=t['principals']['host'][field];self.assertEqual(self.eval(t=t)['decision'],'FAIL')
    def test_missing_host_guest_review_observations(self):
        for role in ['host','guest','review']:
            b=copy.deepcopy(BASE);del b[role];self.assertEqual(self.eval(b)['decision'],'BLOCKED')
    def test_manifest_tamper_without_resigning(self):
        b=copy.deepcopy(BASE);b['host']['body']['facts']['I02']['nic_count']=1;self.assertEqual(self.eval(b)['decision'],'FAIL')
    def test_signature_copied_from_different_role(self):
        b=copy.deepcopy(BASE);b['guest']['signature']=b['host']['signature'];self.assertEqual(self.eval(b)['decision'],'FAIL')
    def test_even_disabled_NIC_fails(self):self.expect_bad('host','I02','nic_count',1)
    def test_legacy_nic_fails(self):self.expect_bad('host','I02','legacy_nics',1)
    def test_nat_bridge_hostonly_forwarding_fails(self):
        for k in ['nat_edges','bridge_edges','hostonly_edges','forwarders','passthrough']:self.expect_bad('host','I02',k,1)
    def test_shared_folder_clipboard_and_device_relays_fail(self):
        for k,v in [('shared_folders',1),('clipboard',True),('usb_relay',1),('gpu_relay',1),('serial_pipes',1)]:self.expect_bad('host','I03',k,v)
    def test_enhanced_console_powershell_direct_and_guest_relay_fail(self):
        for k in ['enhanced_console','powershell_direct','guest_relay']:self.expect_bad('host','I03',k,True)
    def test_incomplete_device_census_blocks(self):self.expect_bad('host','I02','census_complete',False,'BLOCKED')
    def test_vm_owner_config_identity_mismatch(self):
        for k,v in [('vm_guid',OWNER),('owner',VM),('config_digest',H('f'))]:self.expect_bad('host','I01',k,v)
    def test_boot_or_guest_baseline_mismatch_fails(self):
        self.expect_bad('guest','I01','boot_id',VM);self.expect_bad('guest','I01','guest_baseline_digest',H('f'))
    def test_guest_live_claim_with_host_off_state_fails(self):self.expect_bad('host','I01','vm_state','Off')
    def test_image_chain_mismatch_and_shared_disk_fail(self):
        for k,v in [('chain_digest',H('f')),('media_digest',H('f')),('shared_writable',True),('concurrent_mount',True),('local_only',False),('no_reparse',False)]:self.expect_bad('host','I04',k,v)
    def test_guest_network_dns_proxy_and_nonloopback_fail(self):
        for k in ['nonloopback_adapters','nonloopback_addresses','gateways','resolvers','proxy_endpoints','relays']:self.expect_bad('guest','I05',k,1)
    def test_assets_unknown_origin_blocks_and_digest_fails(self):self.expect_bad('host','I06','origins_reviewed',False,'BLOCKED');self.expect_bad('guest','I06','assets_digest',H('f'))
    def test_credentials_and_real_profile_flags_fail(self):
        for k in ['host_credentials_inherited','real_tunnel_id','secrets_present','real_profiles','original_launcher_changed']:self.expect_bad('guest','I07',k,True)
    def test_unknown_observer_blocks(self):self.expect_bad('host','I08','observer_hash',H('f'),'BLOCKED')
    def test_zero_packets_is_not_attempt_observer(self):self.expect_bad('guest','I08','zero_packets_only',True)
    def test_lost_events_restart_or_missing_attempts_fail(self):
        for k,v in [('loss_count',1),('restarts',1),('socket_attempts',False),('refused_attempts',False)]:self.expect_bad('guest','I08',k,v)
    def test_stale_heartbeat_and_clock_correlation_block(self):
        for k in ['heartbeat_age_ms','clock_correlation_error_ms']:self.expect_bad('host','I08',k,2000,'BLOCKED')
    def test_fixture_unknown_receiver_or_upstream_fail(self):
        for k,v in [('owned_receivers',False),('wildcard',True),('external_upstream',True),('positive_receipts',False)]:self.expect_bad('guest','I09',k,v)
    def test_unapproved_descendants_cloudflared_and_outside_guest_fail(self):
        for k,v in [('unknown_children',1),('cloudflared',True),('all_processes_in_guest',False)]:self.expect_bad('guest','I10',k,v)
    def test_config_changed_after_snapshot_fails(self):self.expect_bad('host','I11','after_digest',H('f'))
    def test_watch_missing_or_heartbeat_loss_not_pass(self):self.expect_bad('host','I11','watch_complete',False,'BLOCKED');self.expect_bad('guest','I11','heartbeat_ok',False)
    def test_rollback_unreviewed_or_wrong_owner(self):self.expect_bad('host','I12','recovery_reviewed',False,'BLOCKED');self.expect_bad('host','I12','ledger_owner',VM)
    def test_guest_selfreport_without_independent_review_blocks(self):
        b=copy.deepcopy(BASE);del b['review'];self.assertEqual(self.eval(b)['decision'],'BLOCKED')
    def test_signed_negative_fact_dominates_missing_review(self):
        b=self.mutated('host','I02','nic_count',1);del b['review'];r=self.eval(b);self.assertEqual(r['decision'],'FAIL');self.assertEqual(next(x for x in r['requirements'] if x['id']=='I02')['status'],'FAIL')
    def test_wrong_independent_snapshot_reference_fails(self):
        b=copy.deepcopy(BASE);b['review']['body']['host_hash']=H('f');b['review']=F.sign('review',b['review']['body']);self.assertEqual(self.eval(b)['decision'],'FAIL')
    def test_stale_request_and_future_decision_block(self):
        self.assertEqual(gate.evaluate(BASE,F.trust,gate.digest(F.trust),NOW+dt.timedelta(minutes=10),HELPER,True)['decision'],'BLOCKED')
    def test_missing_required_fact_blocks(self):
        b=F.bundle(lambda r,h,g:h['I02'].pop('nic_count'));self.assertEqual(self.eval(b)['decision'],'BLOCKED')
    def test_string_boolean_and_bool_count_not_coerced(self):self.expect_bad('host','I02','nic_count',False);self.expect_bad('guest','I03','clipboard','false')
    def test_unknown_fact_fields_rejected(self):
        b=F.bundle(lambda r,h,g:h['I02'].__setitem__('force_safe',True));self.assertEqual(self.eval(b)['decision'],'FAIL')
    def test_strict_duplicate_escaped_json_and_nonfinite(self):
        for s in ['{"a":1,"a":2}','{"a":1,"\\u0061":2}','{"v":NaN}']:
            with self.assertRaises(gate.Invalid):gate.parse(s.encode())
    def test_json_size_depth_and_types(self):
        for s in ['['*20+'0'+']'*20,'{"x":1.1}']:
            with self.assertRaises(gate.Invalid):gate.parse(s.encode())
    def test_dry_plan_deterministic_and_no_apply(self):
        p=gate.plan(OWNER,'C:\\SyntheticLab\\owned-new',H('2'),{});self.assertEqual(p,gate.plan(OWNER,'C:\\SyntheticLab\\owned-new',H('2'),{}));self.assertFalse(p['plan']['can_apply']);self.assertTrue(all(a['executable'] is False for a in p['plan']['actions']))
    def test_dry_plan_rejects_foreign_unsafe_root(self):
        for root in ['C:\\','C:\\Users\\other','\\\\server\\share','C:\\Lab\\..\\other','C:\\Lab\\x:stream']:
            with self.assertRaises(gate.Invalid):gate.plan(OWNER,root,H('2'),{})
    def test_all_permission_flags_do_not_activate(self):
        b=F.bundle(lambda r,h,g:r['approval'].update(provision=True,native=True));self.assertFalse(self.eval(b)['native_execution_allowed']);self.assertFalse(self.eval(b)['vm_changes_allowed'])
    def test_write_output_never_overwrites(self):
        p=OUT/'owned-result.json';gate.write_new(p,{'ok':True})
        with self.assertRaises(FileExistsError):gate.write_new(p,{'ok':False})
    def test_storage_chain_cycles_foreign_parent_owner_backend_rejected(self):
        for field,value in [('parent',VM),('owner',VM),('local',False),('reparse',True),('shared_writable',True),('host_mounted',True)]:
            b=copy.deepcopy(BASE);b['request']['disks'][0][field]=value;b['request']['chain_digest']=gate.digest(b['request']['disks']);r=self.eval(b);self.assertEqual(r['decision'],'FAIL');self.assertTrue(r['requirements'][0]['reason'].startswith('DISK_'))
    def test_media_and_observer_asset_crossbinding(self):
        for role in ['windows_media','observer_host']:
            b=copy.deepcopy(BASE);next(a for a in b['request']['assets'] if a['role']==role)['sha256']=H('9');b['request']['assets_digest']=gate.digest(b['request']['assets']);self.assertEqual(self.eval(b)['decision'],'FAIL');self.assertTrue('ASSET_BINDING' in self.eval(b)['requirements'][0]['reason'])
    def test_root_reserved_names_and_command_metacharacters_rejected(self):
        for root in ['C:\\Lab\\NUL','C:\\Lab\\unsafe.','C:\\Lab\\x;echo','C:\\Lab\\x$y']:
            with self.assertRaises(gate.Invalid):gate.plan(OWNER,root,H('2'),{})
    def test_cli_remote_paths_rejected_before_io(self):
        for path in ['\\\\host\\share\\x.json','https://example.invalid/x','C:/outside-owned-package.json']:
            with self.assertRaises(gate.Invalid):gate.cli_path(path)
    def test_cli_real_clock_override_rejected_without_output(self):
        target=OUT/'clock-override.json'
        p=subprocess.run([sys.executable,'-B',str(ROOT/'source/lab_gate.py'),'check','--bundle',str(OUT/'positive_bundle.json'),'--helper',str(HELPER),'--now',iso(NOW),'--output',str(target)],capture_output=True,timeout=8)
        self.assertEqual(p.returncode,20);self.assertFalse(target.exists())
    def test_cli_signed_positive_and_real_unprovisioned_exit_status(self):
        stage=ROOT/'evidence'/HELPER.parent.name/'cli';stage.mkdir(parents=True)
        copied=stage/'Signatures.exe';shutil.copyfile(HELPER,copied)
        gate.write_new(stage/'bundle.json',BASE);gate.write_new(stage/'trust.json',F.trust);gate.write_new(stage/'none.json',{'request':None})
        cmd=[sys.executable,'-B',str(ROOT/'source/lab_gate.py'),'check','--bundle',str(stage/'bundle.json'),'--trust',str(stage/'trust.json'),'--trust-sha256',gate.digest(F.trust),'--helper',str(copied),'--synthetic','--now',iso(NOW),'--output',str(stage/'positive.json')]
        p=subprocess.run(cmd,capture_output=True,timeout=8);self.assertEqual(p.returncode,0);self.assertEqual(gate.parse((stage/'positive.json').read_bytes())['decision'],'PASS')
        p=subprocess.run([sys.executable,'-B',str(ROOT/'source/lab_gate.py'),'check','--bundle',str(stage/'none.json'),'--helper',str(copied),'--output',str(stage/'real.json')],capture_output=True,timeout=8)
        self.assertEqual(p.returncode,20);self.assertEqual(gate.parse((stage/'real.json').read_bytes())['decision'],'BLOCKED')
class Result(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.rows=[]
    def addSuccess(self,t):super().addSuccess(t);self.rows.append({'name':t._testMethodName,'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);self.rows.append({'name':t._testMethodName,'status':'FAIL','code':'ASSERTION'})
    def addError(self,t,e):super().addError(t,e);self.rows.append({'name':t._testMethodName,'status':'ERROR','code':e[0].__name__})
if __name__=='__main__':
    F=Fixtures();BASE=F.bundle();OUT.mkdir(exist_ok=True)
    try:
        gate.write_new(OUT/'positive_bundle.json',BASE);gate.write_new(OUT/'synthetic_trust.json',F.trust)
        text=io.StringIO();runner=unittest.TextTestRunner(stream=text,verbosity=0,resultclass=Result)
        result=runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(GateTests));gate.write_new(OUT/'results.json',{'total':result.testsRun,'passed':len([x for x in result.rows if x['status']=='PASS']),'failed':len(result.failures),'errors':len(result.errors),'tests':result.rows,'synthetic':True,'actual_vm_queries':0,'network_probes':0})
        (OUT/'runner.txt').write_text(text.getvalue().replace(str(ROOT),'<TASK>').replace(ROOT.as_posix(),'<TASK>').replace(str(HELPER.parent),'<RUN>'),encoding='utf-8')
        print('SYNTHETIC',result.testsRun,'FAIL',len(result.failures),'ERROR',len(result.errors));sys.exit(0 if result.wasSuccessful() else 1)
    finally:F.close()
