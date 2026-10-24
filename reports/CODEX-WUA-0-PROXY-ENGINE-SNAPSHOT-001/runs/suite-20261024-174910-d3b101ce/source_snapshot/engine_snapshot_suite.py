"""Pure offline metadata and gate oracles; no engine, sockets or children."""
import copy,hashlib,importlib.util,io,json,os
from pathlib import Path
import struct,sys,time,types,unittest,uuid
sys.dont_write_bytecode=True
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1];sys.path.insert(0,str(PKG))
import common,broker,engine_snapshot as engine
OUT=None;ITEMS=[]

def guard(event,args):
    if event.startswith('socket.') or event in ['subprocess.Popen','os.system','os.posix_spawn']:
        raise PermissionError('PURE_OFFLINE_NO_NETWORK_OR_CHILD')
sys.addaudithook(guard)
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(p):return json.loads(p.read_bytes())
def pe_fixture(family='V2Ray',version='v5.0.0'):
    # Independent, inert byte fixture: known literal fields, no executable code.
    data=bytearray(5120);data[:2]=b'MZ';struct.pack_into('<I',data,60,128);data[128:132]=b'PE\0\0'
    struct.pack_into('<HHIIIHH',data,132,0x8664,1,123,0,0,240,2)
    struct.pack_into('<H',data,152,0x20b);struct.pack_into('<I',data,152+108,16)
    section=152+240;data[section:section+8]=b'.data\0\0\0';struct.pack_into('<II',data,section+16,4096,1024)
    module='github.com/v2fly/v2ray-core/v5' if family=='V2Ray' else 'github.com/sagernet/sing-box'
    payload=bytes.fromhex('3077af0c9274080241e1c107e6d618e6')+('path\t'+module+'/cmd/test\nmod\t'+module+'\t'+version+'\t\nbuild\tGOOS=windows\n').encode()+bytes.fromhex('f932433186182072008242104116d8f2')
    n=len(payload);length=bytes([n]) if n<128 else bytes([(n&127)|128,n>>7])
    block=b'\xff Go buildinf:\x08\x02'+bytes(16)+b'\x08go1.25.8'+length+payload
    data[1536:1536+len(block)]=block
    return bytes(data)
def snapshot(family='V2Ray',version='v5.0.0'):
    return {'schema':1,'kind':'STATIC_BINARY_SNAPSHOT','basename':'fixture.exe','path_label':'ENGINE_BINARY_01','path_sha256':'a'*64,**engine.inspect_bytes(pe_fixture(family,version)),'windows_version':{k:None for k in ['FileVersion','ProductVersion','CompanyName','OriginalFilename','ProductName']},'verified_release':None,'source_archive_sha256':None,'native_schema_sha256':None,'capabilities':{k:'UNKNOWN' for k in engine.CAPABILITIES},'owner_proof':'NOT_VERIFIED','engine_execution':False}
def contract():return load(PKG/'configs/broker.v1.synthetic.example.json')
def evaluate(s,c=None,selected='V2Ray',pin=None,source=None):
    c=contract() if c is None else c
    return engine.evaluate(s,common.digest(s) if pin is None else pin,c,common.digest(c),broker.source_pin() if source is None else source,selected)

class EngineTests(unittest.TestCase):
    def denied(self,s,reason,c=None,selected='V2Ray',pin=None,source=None):
        r=evaluate(s,c,selected,pin,source);self.assertEqual(r['snapshot_status'],'REJECTED');self.assertEqual(r['reason'],reason);self.assertFalse(r['can_apply'] or r['can_start_tunnel']);return r
    def test_known_literal_pe_go_fixture_and_corruption(self):
        r=engine.inspect_bytes(pe_fixture());self.assertEqual(r['go_build']['module_version_claim'],'v5.0.0');self.assertEqual(r['engine_family_claim'],'V2Ray');self.assertEqual(r['pe']['sections'],1)
        with self.assertRaisesRegex(common.Denied,'PE_DOS'):engine.inspect_bytes(b'NO'+pe_fixture()[2:])
    def test_truncated_pe_headers(self):
        self.assertEqual(engine.inspect_bytes(pe_fixture())['bytes'],5120)
        for n in [0,63,64,130,160,400]:
            with self.assertRaises(common.Denied):engine.inspect_bytes(pe_fixture()[:n])
    def test_wrong_architecture_and_section_bounds(self):
        self.assertEqual(engine.inspect_bytes(pe_fixture())['pe']['machine'],'AMD64')
        for at,value in [(132,0x14c),(134,0),(392+16,9000)]:
            d=bytearray(pe_fixture());struct.pack_into('<H' if at<392 else '<I',d,at,value)
            with self.assertRaises(common.Denied):engine.inspect_bytes(bytes(d))
    def test_certificate_metadata_is_not_trust(self):
        self.assertFalse(engine.inspect_bytes(pe_fixture())['authenticode']['embedded_certificate_table_present'])
        d=bytearray(pe_fixture());struct.pack_into('<II',d,152+112+32,5000,500)
        with self.assertRaisesRegex(common.Denied,'CERTIFICATE_BOUNDS'):engine.inspect_bytes(bytes(d))
    def test_go_inline_only_and_ambiguous_marker(self):
        self.assertEqual(engine.inspect_bytes(pe_fixture())['go_build']['format'],'INLINE_GO_BUILDINFO')
        d=bytearray(pe_fixture());d[1536+15]=0
        with self.assertRaisesRegex(common.Denied,'UNSUPPORTED_GO'):engine.inspect_bytes(bytes(d))
        d=bytearray(pe_fixture());d[2048:2048+14]=b'\xff Go buildinf:'
        with self.assertRaisesRegex(common.Denied,'AMBIGUOUS'):engine.inspect_bytes(bytes(d))
    def test_go_varint_limits(self):
        self.assertEqual(engine.go_string(b'\x03abc',0),(b'abc',4))
        for raw in [b'',b'\x80',b'\xff'*10,b'\x04abc',b'\x81\x80\x04']:
            with self.assertRaises(common.Denied):engine.go_string(raw,0)
    def test_go_module_sentinel_and_duplicate_module(self):
        self.assertEqual(engine.inspect_bytes(pe_fixture())['go_build']['dependency_count'],0)
        d=bytearray(pe_fixture());d[1536+32+9+2]^=1
        with self.assertRaisesRegex(common.Denied,'SENTINEL'):engine.inspect_bytes(bytes(d))
        d=pe_fixture().replace(b'build\tGOOS=windows',b'mod\tx\tv1.0.0\t  ')
        with self.assertRaises(common.Denied):engine.inspect_bytes(d)
    def test_no_buildinfo_never_invents_version(self):
        d=pe_fixture().replace(b'\xff Go buildinf:',b'_'*14);r=engine.inspect_bytes(d);self.assertIsNone(r['go_build']);self.assertEqual(r['engine_family_claim'],'UNKNOWN')
        s=snapshot();s.update(go_build=None,engine_family_claim='UNKNOWN');self.denied(s,'ENGINE_FAMILY_MISMATCH')
    def test_bound_metadata_still_never_activates(self):
        r=evaluate(snapshot());self.assertEqual(r['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY');self.assertEqual(r['release_provenance'],'BLOCKED');self.assertFalse(r['can_apply'] or r['can_start_tunnel'])
        self.denied(snapshot(),'INVENTORY_PIN_MISMATCH',pin='0'*64)
    def test_binary_or_release_metadata_swap_uses_controller_pin(self):
        original=snapshot();pin=common.digest(original);self.assertEqual(evaluate(original,pin=pin)['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        for loc,key,value in [(None,'sha256','0'*64),('go_build','module_version_claim','v99.99.99'),('go_build','module_path_claim','foreign/module')]:
            s=copy.deepcopy(original);(s if loc is None else s[loc])[key]=value;self.denied(s,'INVENTORY_PIN_MISMATCH',pin=pin)
    def test_source_schema_and_release_booleans_cannot_verify(self):
        self.assertEqual(evaluate(snapshot())['native_config_schema'],'BLOCKED')
        for key in ['verified_release','source_archive_sha256','native_schema_sha256']:
            s=snapshot();s[key]='1'*64;self.denied(s,'UNTRUSTED_PROVENANCE_CLAIM')
    def test_unknown_version_and_devel_are_rejected(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        for value in [None,'(devel)','latest','v1.0',True]:
            s=snapshot();s['go_build']['module_version_claim']=value;self.denied(s,'ENGINE_VERSION_UNKNOWN')
    def test_capability_true_or_supported_cannot_unlock(self):
        self.assertEqual(evaluate(snapshot())['strict_connect_compatibility'],'UNVERIFIED')
        for value in [True,'SUPPORTED',{'verified':True}]:
            s=snapshot();s['capabilities']['http_connect']=value;self.denied(s,'UNTRUSTED_CAPABILITY_CLAIM')
    def test_owner_sid_signature_and_run_claim_not_authority(self):
        self.assertEqual(evaluate(snapshot())['B_EGRESS_OWNER'],'NOT_VERIFIED')
        for key,val in [('owner_proof','S-1-5-21-101-202-303-1002'),('owner_proof',{'signature':'signed','verified':True}),('engine_execution',True)]:
            s=snapshot();s[key]=val;self.denied(s,'UNTRUSTED_OWNER_OR_EXECUTION_CLAIM')
    def test_signature_publisher_claim_not_trust(self):
        self.assertEqual(evaluate(snapshot())['release_provenance'],'BLOCKED')
        s=snapshot();s['authenticode']['publisher_trust']='VERIFIED';self.denied(s,'UNTRUSTED_SIGNATURE_CLAIM')
    def test_engine_selection_and_old_contract_conflict(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        self.denied(snapshot('sing-box','v1.13.4'),'ENGINE_FAMILY_MISMATCH')
        self.denied(snapshot('sing-box','v1.13.4'),'EXISTING_CONTRACT_ENGINE_MISMATCH',selected='sing-box')
        c=contract();c['engine']['family']='sing-box';self.denied(snapshot('sing-box','v1.13.4'),'BROKER_CONTRACT_REJECTED',c,'sing-box')
    def test_family_label_cannot_override_module(self):
        self.assertEqual(snapshot()['engine_family_claim'],'V2Ray')
        s=snapshot();s['engine_family_claim']='sing-box';self.denied(s,'ENGINE_FAMILY_CLAIM_INCONSISTENT',selected='sing-box')
    def test_wrong_binary_hash_bound_in_old_contract(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        c=contract();c['engine']['binary_sha256']='2'*64;self.denied(snapshot(),'ENGINE_BINARY_HASH_MISMATCH',c)
    def test_wrong_inbound_outbound_direct_default_and_proxy(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        for group,key,value in [('routing','direct',True),('routing','fallback',True),('routing','secondary_proxy',True),('routing','default','DIRECT')]:
            c=contract();c[group][key]=value;self.denied(snapshot(),'BROKER_CONTRACT_REJECTED',c)
        for key,value in [('client_proxy_host','0.0.0.0'),('egress_ip','remote.invalid'),('proxy_scheme','socks5')]:
            c=contract();c['integration']['route'][key]=value;self.denied(snapshot(),'BROKER_CONTRACT_REJECTED',c)
    def test_broker_schema_and_source_drift(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        self.denied(snapshot(),'BROKER_CONTRACT_REJECTED',source='0'*64)
        c=contract();c['schema']=2;self.denied(snapshot(),'BROKER_CONTRACT_REJECTED',c)
    def test_fake_all_approved_json_is_rejected(self):
        s=snapshot();self.assertFalse(evaluate(s)['can_apply']);s['all_approved']=True;self.denied(s,'SCHEMA')
        with self.assertRaisesRegex(common.Denied,'DUPLICATE_KEY'):common.parse(b'{"schema":1,"schema":1}')
    def test_snapshot_nested_shape_limits(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        for group,key,value,reason in [('pe','sections',True,'SNAPSHOT_PE'),('go_build','dependency_count',-1,'SNAPSHOT_GO_MODULE'),('windows_version','CompanyName','bad\nname','SNAPSHOT_WINDOWS_VERSION'),('go_build','build_settings_claims',{'password':'x'},'SNAPSHOT_GO_SETTINGS')]:
            s=snapshot();s[group][key]=value;self.denied(s,reason)
    def test_current_inventory_is_independently_pinned(self):
        s=load(engine.REPORT/'evidence/binary_snapshot.json');receipt=load(engine.REPORT/'evidence/inventory_receipt.json');self.assertEqual(common.digest(s),receipt['inventory_canonical_sha256']);self.assertTrue(receipt['historical_hash_matches']);self.assertEqual(s['go_build']['module_version_claim'],'v1.13.4')
        self.denied(s,'ENGINE_FAMILY_MISMATCH',pin=receipt['inventory_canonical_sha256']);self.denied(s,'EXISTING_CONTRACT_ENGINE_MISMATCH',selected='sing-box',pin=receipt['inventory_canonical_sha256'])
    def mutation(self,old,replacement,alter,expected):
        source=(PKG/'engine_snapshot.py').read_text();self.assertEqual(source.count(old),1);changed=source.replace(old,replacement);m=types.ModuleType('engine_metadata_mutant');m.__file__=str(PKG/'engine_snapshot.py');exec(compile(changed,m.__file__,'exec'),m.__dict__)
        s=snapshot();pin=common.digest(s);alter(s);c=contract()
        class Oracle(unittest.TestCase):
            def runTest(self):
                value=m.evaluate(s,pin if expected=='INVENTORY_PIN_MISMATCH' else common.digest(s),c,common.digest(c),broker.source_pin(),'V2Ray');self.assertEqual(value['reason'],expected)
        stream=io.StringIO();r=unittest.TextTestRunner(stream=stream).run(Oracle());self.assertEqual(len(r.failures),1);self.assertEqual(len(r.errors),0)
        root=OUT/('mutant-'+expected);root.mkdir();(root/'engine_snapshot_mutant.py').write_text(changed,encoding='utf-8');put(root/'result.json',{'expected_inner_FAIL':1,'inner_collected':r.testsRun,'inner_failures':len(r.failures),'inner_errors':len(r.errors),'oracle':expected,'output':stream.getvalue(),'scope':'synthetic metadata, no engine/OS proof'})
    def test_inventory_hash_guard_mutation_is_detected(self):
        self.assertEqual(evaluate(snapshot())['snapshot_status'],'STRUCTURALLY_CONSISTENT_ONLY')
        self.mutation("require(digest(snapshot)==expected_inventory_pin,'INVENTORY_PIN_MISMATCH')","require(True,'INVENTORY_PIN_MISMATCH')",lambda s:s.update(sha256='0'*64),'INVENTORY_PIN_MISMATCH')
    def test_capability_guard_mutation_is_detected(self):
        self.assertEqual(evaluate(snapshot())['strict_connect_compatibility'],'UNVERIFIED')
        self.mutation("require(snapshot['capabilities']=={k:'UNKNOWN' for k in CAPABILITIES},'UNTRUSTED_CAPABILITY_CLAIM')","require(True,'UNTRUSTED_CAPABILITY_CLAIM')",lambda s:s['capabilities'].update(http_connect='SUPPORTED'),'UNTRUSTED_CAPABILITY_CLAIM')

class Result(unittest.TextTestResult):
    def addSuccess(self,t):super().addSuccess(t);ITEMS.append({'id':t.id(),'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);ITEMS.append({'id':t.id(),'status':'FAIL','traceback':self._exc_info_to_string(e,t)})
    def addError(self,t,e):super().addError(t,e);ITEMS.append({'id':t.id(),'status':'ERROR','traceback':self._exc_info_to_string(e,t)})
def main():
    global OUT
    OUT=engine.REPORT/'runs'/('suite-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);OUT.mkdir()
    paths=[Path(__file__).resolve(),PKG/'engine_snapshot.py',PKG/'broker.py',PKG/'broker_fixture.py',PKG/'common.py',PKG/'security_contract.py',PKG/'route_simulation.py',PKG/'configs/broker.v1.schema.json',PKG/'configs/broker.v1.synthetic.example.json',PKG/'tests/broker_suite.py']
    pins={p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};snap=OUT/'source_snapshot';snap.mkdir()
    for p in paths:(snap/p.name).write_bytes(p.read_bytes())
    put(OUT/'source_pins.json',pins)
    spec=importlib.util.spec_from_file_location('legacy_broker_suite',PKG/'tests/broker_suite.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy);legacy.OUT=OUT/'legacy';legacy.OUT.mkdir()
    skip={'test_cli_always_exit20_and_output_scope','test_remote_schema_reference_is_refused_without_dial'}
    names=[n for n in unittest.defaultTestLoader.getTestCaseNames(legacy.ContractTests) if n not in skip]
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(EngineTests),unittest.TestSuite(legacy.ContractTests(n) for n in names)])
    stream=io.StringIO();r=unittest.TextTestRunner(verbosity=2,stream=stream,resultclass=Result).run(suite)
    unchanged=all(hashlib.sha256((REPO/p).read_bytes()).hexdigest()==v for p,v in pins.items())
    put(OUT/'result.json',{'task':engine.TASK,'collected':r.testsRun,'passed':sum(x['status']=='PASS' for x in ITEMS),'failed':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'new_metadata_tests':len(unittest.defaultTestLoader.getTestCaseNames(EngineTests)),'legacy_pure_contract_regression':len(names),'legacy_network_or_subprocess_tests_not_run':sorted(skip),'tests':ITEMS,'source_pins_current':unchanged,'engine_runs':0,'native_network_tests':0,'network_or_child_creation_permitted':False})
    (OUT/'runner.txt').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue());print('EVIDENCE '+str(OUT))
    return 0 if r.wasSuccessful() and unchanged else 1
if __name__=='__main__':sys.exit(main())
