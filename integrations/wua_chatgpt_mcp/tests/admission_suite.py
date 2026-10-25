"""Offline admission checks reusing pure ContractTests, never legacy Harness.

The old broker suite combines Windows loopback/process tests with pure tests;
this selector keeps those network tests uncollected rather than silently SKIP.
"""
from pathlib import Path
import copy,hashlib,importlib.util,io,json,sys,time,types,unittest,uuid
sys.dont_write_bytecode=True
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1]
sys.path.insert(0,str(PKG))
import broker,common,security_contract as security
TASK=REPO/'reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001'
RUN=None;RESULTS=[];BLOCKED_OPERATIONS=[]
def guard(event,args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):
        BLOCKED_OPERATIONS.append(event);raise PermissionError('OFFLINE_ADMISSION_ONLY')
sys.addaudithook(guard)
spec=importlib.util.spec_from_file_location('legacy_admission_contracts',PKG/'tests/broker_suite.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)

def candidate():
    p=legacy.contract()
    p['remote_identity']['credential_ref']='wua-secret-ref:11111111-1111-4111-8111-111111111111'
    p['admission']={
      'authentication':{'required':True,'mechanism':'BROKER_ONLY_PROTECTED_REFERENCE','users':[{'principal':'mcp-client','credential_ref':'wua-secret-ref:22222222-2222-4222-8222-222222222222'}]},
      'configuration':{'source_count':1,'format':'CANONICAL_JSON','protection':'BROKER_ONLY_PROTECTED_SOURCE','merge':False,'reload':False,'environment_override':False},
      'connect':{'methods':['CONNECT'],'targets':[{'address':'198.51.100.20','port':443}],
                 'allow_upgrade':False,'allow_plain_http':False,'allow_uot':False,'allow_background':False}}
    return p
def metadata():return {'method':'CONNECT','upgrade':False,'address':'198.51.100.20','port':443,'connect_accepted':True}
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

class AdmissionTests(unittest.TestCase):
    def call(self,p=None,*,raw=None,pin=None,source=None,event=None):
        self.assertTrue(callable(getattr(broker,'strict_preflight',None)),'STRICT_ADMISSION_API_MISSING')
        p=candidate() if p is None else p
        result=broker.strict_preflight(common.canonical(p) if raw is None else raw,
                                      common.digest(p) if pin is None else pin,
                                      broker.source_pin() if source is None else source,
                                      request_metadata=metadata() if event is None else event)
        self.assertIs(result['can_apply'],False);self.assertIs(result['can_start_tunnel'],False)
        self.assertEqual(result['install_uninstall'],'BLOCKED');self.assertEqual(result['strict_admission_status'],'STRICT_ADMISSION_BLOCKED')
        self.assertIs(result['real_egress_verified'],False)
        return result
    def rejected(self,p,code,**kw):
        r=self.call(p,**kw);self.assertEqual(r['reason'],code);self.assertFalse(r['policy_route_allowed']);return r
    def test_legacy_fixture_structural_valid_but_strict_blocked(self):
        p=legacy.contract();r=broker.preflight(p,common.digest(p),broker.source_pin())
        self.assertEqual(r['profile_status'],'BROKER_PROFILE_STRUCTURALLY_VALID')
        self.assertEqual(r.get('strict_admission_status'),'STRICT_ADMISSION_BLOCKED')
        self.rejected(p,'AUTH_USERS_REQUIRED')
    def test_complete_policy_cannot_promote_native_security(self):
        r=self.call();self.assertEqual(r['strict_policy_status'],'VALID');self.assertTrue(r['policy_route_allowed'])
        self.assertEqual(r['connect_handler_event'],'UNTRUSTED_ACCEPTED_CLAIM')
        self.assertEqual(r['reason'],'RUNTIME_SECURITY_UNVERIFIED')
        for code in ['UPSTREAM_SECRET_BOUNDARY_UNVERIFIED','CREDENTIAL_STORE_UNVERIFIED','CONFIG_SOURCE_PROTECTION_UNVERIFIED','B_EGRESS_OWNER_NOT_VERIFIED']:
            self.assertIn(code,r['strict_blockers'])
    def test_missing_and_empty_users(self):
        for change in ('missing','empty'):
            p=candidate()
            if change=='missing':del p['admission']['authentication']['users']
            else:p['admission']['authentication']['users']=[]
            self.rejected(p,'AUTH_USERS_REQUIRED')
    def test_auth_required_not_disabled_or_self_asserted(self):
        p=candidate();p['admission']['authentication']['required']=False;self.rejected(p,'AUTH_REQUIRED')
        p=candidate();p['admission']['authentication']['mechanism']='NONE';self.rejected(p,'AUTH_MECHANISM_REQUIRED')
    def test_credential_reference_missing_wrong_or_inline_secret(self):
        for value in (None,'','FUTURE_BROKER_ONLY_SECRET_STORE','password:synthetic'):
            p=candidate();p['admission']['authentication']['users'][0]['credential_ref']=value
            self.rejected(p,'CREDENTIAL_REFERENCE_INVALID')
        p=candidate();p['admission']['authentication']['users'][0]['password']='SYNTHETIC_PASSWORD_SENTINEL_007'
        r=self.rejected(p,'AUTH_USER_FIELDS');self.assertNotIn('SYNTHETIC_PASSWORD_SENTINEL_007',json.dumps(r))
    def test_upstream_reference_is_not_optional(self):
        for value in (None,'FUTURE_BROKER_ONLY_SECRET_STORE'):
            p=candidate();p['remote_identity']['credential_ref']=value;self.rejected(p,'UPSTREAM_CREDENTIAL_REFERENCE_REQUIRED')
        p=candidate();p['remote_identity']['credential_ref']=p['admission']['authentication']['users'][0]['credential_ref']
        self.rejected(p,'UPSTREAM_CREDENTIAL_REFERENCE_REQUIRED')
    def test_no_secrets_or_header_material_in_own_errors(self):
        sentinel='SYNTHETIC_CREDENTIAL_SENTINEL_007'
        for field in ('password','Proxy-Authorization','credential_material'):
            p=candidate();p['admission']['authentication'][field]=sentinel
            r=self.rejected(p,'AUTH_FIELDS');self.assertNotIn(sentinel,json.dumps(r));self.assertNotIn(field,json.dumps(r))
        self.assertTrue(callable(getattr(security,'validate_admission',None)),'ADMISSION_VALIDATOR_MISSING')
        original=security.validate_admission
        try:
            security.validate_admission=lambda *a,**k:(_ for _ in ()).throw(common.Denied(sentinel))
            r=self.call();self.assertEqual(r['reason'],'STRICT_INTERNAL_FAILURE');self.assertNotIn(sentinel,json.dumps(r))
        finally:security.validate_admission=original
    def test_connect_acceptance_does_not_prove_route_or_owner(self):
        p=candidate();event=metadata();event['address']='198.51.100.21'
        self.rejected(p,'CONNECT_DESTINATION_DENIED',event=event)
        r=self.call();self.assertTrue(r['policy_route_allowed']);self.assertFalse(r['real_egress_verified'])
    def test_plain_http_upgrade_and_unknown_method(self):
        for method in ('GET','POST','UPGRADE','connect','UNKNOWN'):
            event=metadata();event['method']=method;self.rejected(candidate(),'CONNECT_METHOD_DENIED',event=event)
        event=metadata();event['upgrade']=True;self.rejected(candidate(),'CONNECT_UPGRADE_DENIED',event=event)
    def test_metadata_is_not_a_go_parser_or_owner_attestation(self):
        event=metadata();event['downstream_verified']=True;self.rejected(candidate(),'CONNECT_METADATA_FIELDS',event=event)
        self.rejected(candidate(),'CONNECT_METADATA_FIELDS',event=b'CONNECT raw bytes')
    def test_exact_destination_and_port(self):
        for key,value,code in [('address','other.invalid','CONNECT_ADDRESS_INVALID'),('address','::1','CONNECT_ADDRESS_INVALID'),('address','198.51.100.21','CONNECT_DESTINATION_DENIED'),('port',0,'CONNECT_PORT_INVALID'),('port',65536,'CONNECT_PORT_INVALID'),('port',True,'CONNECT_PORT_INVALID'),('port',444,'CONNECT_DESTINATION_DENIED')]:
            event=metadata();event[key]=value;self.rejected(candidate(),code,event=event)
    def test_undeclared_connect_targets_and_uot_denied(self):
        for key in ('allow_upgrade','allow_plain_http','allow_uot','allow_background'):
            p=candidate();p['admission']['connect'][key]=True;self.rejected(p,'CONNECT_POLICY_DENIED')
        p=candidate();p['admission']['connect']['targets'][0]['address']='::1';self.rejected(p,'CONNECT_ADDRESS_INVALID')
    def test_direct_fallback_second_proxy_and_unknown_default(self):
        for key,code in [('direct','STRICT_DIRECT_DENIED'),('fallback','STRICT_FALLBACK_DENIED'),('secondary_proxy','STRICT_SECONDARY_PROXY_DENIED'),('load_balancer','STRICT_LOAD_BALANCER_DENIED')]:
            p=candidate();p['routing'][key]=True;self.rejected(p,code)
        p=candidate();p['routing']['default']='AUTO';self.rejected(p,'STRICT_DEFAULT_DENIED')
    def test_dns_udp_ipv6_health_telemetry_and_unknown_egress(self):
        for key in ('host_dns','udp','ipv6','health_dials','telemetry'):
            p=candidate();p['routing'][key]=True;self.rejected(p,'STRICT_EXTRA_EGRESS_DENIED')
        p=candidate();p['routing']['unreviewed_outbound']=True;self.rejected(p,'STRICT_UNDECLARED_ROUTE')
    def test_duplicate_keys_unknown_fields_null_and_noncanonical_json(self):
        p=candidate();raw=common.canonical(p)
        self.rejected(p,'DUPLICATE_KEY',raw=raw.replace(b'"schema":1',b'"schema":1,"schema":1',1))
        p=candidate();p['unexpected']='synthetic';self.rejected(p,'BROKER_SCHEMA')
        p=candidate();p['admission']=None;self.rejected(p,'BROKER_SCHEMA')
        p=candidate();self.rejected(p,'CONFIG_NOT_CANONICAL',raw=json.dumps(p,indent=2).encode())
        self.rejected(p,'JSON_SYNTAX',raw=common.canonical(p)+b'{}')
    def test_protected_single_source_required(self):
        for value in (0,2,None,True):
            p=candidate();p['admission']['configuration']['source_count']=value;self.rejected(p,'CONFIG_SINGLE_SOURCE_REQUIRED')
        p=candidate();p['admission']['configuration']['protection']='UNPROTECTED';self.rejected(p,'CONFIG_PROTECTION_REQUIRED')
    def test_merge_reload_environment_override_denied(self):
        for key,code in [('merge','CONFIG_MERGE_DENIED'),('reload','CONFIG_RELOAD_DENIED'),('environment_override','CONFIG_ENV_OVERRIDE_DENIED')]:
            p=candidate();p['admission']['configuration'][key]=True;self.rejected(p,code)
    def test_replacement_after_preflight_and_source_drift(self):
        p=candidate();pin=common.digest(p);self.call(p,pin=pin)
        p['generation']+=1;self.rejected(p,'CONFIG_PIN_MISMATCH',pin=pin)
        self.rejected(candidate(),'SOURCE_PIN_MISMATCH',source='0'*64)
    def test_data_cannot_enable_flags_or_authorize_evidence(self):
        for key in ('can_apply','can_start_tunnel','engine_verified','all_approved'):
            p=candidate();p[key]=True;self.rejected(p,'BROKER_SCHEMA')
        p=candidate();p['integration']['approval']={k:True for k in p['integration']['approval']};self.assertFalse(self.call(p)['untrusted_evidence_accepted'])
    def test_unknown_engine_owner_and_runtime_claims_remain_blocked(self):
        p=candidate();p['engine'].update(implementation='synthetic claim',version='9.9',source_sha256='1'*64,binary_sha256='2'*64,config_schema_sha256='3'*64)
        r=self.call(p);self.assertIn('ENGINE_VERSION_SOURCE_BLOCKED',r['gates']);self.assertIn('B_EGRESS_OWNER_NOT_VERIFIED',r['strict_blockers'])
    def test_local_schema_cannot_trigger_remote_fetch(self):
        original=broker.SCHEMA;path=RUN/'remote-ref.json';put(path,{'$ref':'https://unapproved.invalid/schema'})
        try:
            broker.SCHEMA=path;self.rejected(candidate(),'SCHEMA_EXTERNAL_REF')
        finally:broker.SCHEMA=original
    def test_auth_users_types_and_duplicate_references(self):
        for value in (None,{},'synthetic',False):
            p=candidate();p['admission']['authentication']['users']=value;self.rejected(p,'AUTH_USERS_REQUIRED')
        p=candidate();p['admission']['authentication']['users'].append(copy.deepcopy(p['admission']['authentication']['users'][0]));self.rejected(p,'AUTH_PRINCIPAL_INVALID')
        p=candidate();u=copy.deepcopy(p['admission']['authentication']['users'][0]);u['principal']='second';p['admission']['authentication']['users'].append(u);self.rejected(p,'CREDENTIAL_REFERENCE_INVALID')
    def test_missing_metadata_and_handler_rejection_remain_explicit(self):
        self.assertTrue(callable(getattr(broker,'strict_preflight',None)))
        p=candidate();r=broker.strict_preflight(common.canonical(p),common.digest(p),broker.source_pin())
        self.assertEqual(r['reason'],'CONNECT_METADATA_FIELDS');self.assertFalse(r['policy_route_allowed'] or r['real_egress_verified'])
        event=metadata();event['connect_accepted']=False;r=self.call(p,event=event)
        self.assertEqual(r['connect_handler_event'],'UNTRUSTED_NOT_ACCEPTED_CLAIM');self.assertFalse(r['can_apply'])
    def test_invalid_raw_types_and_parse_errors_are_fixed_codes(self):
        for value in (None,{},'SYNTHETIC_PASSWORD_SENTINEL_007',bytearray(b'{}')):
            self.rejected(candidate(),'STRICT_INPUT_TYPE',raw=value if value is not None else False)
        self.rejected(candidate(),'JSON_SYNTAX',raw=b'{"password":"SYNTHETIC_PASSWORD_SENTINEL_007"')
        self.rejected(candidate(),'JSON_TYPE',raw=b'{"number":NaN}')
    def test_logical_connect_target_is_distinct_from_physical_egress(self):
        p=candidate();self.assertNotEqual(p['integration']['route']['egress_ip'],metadata()['address']);self.call(p)
        event=metadata();event['address']=p['integration']['route']['egress_ip'];self.rejected(p,'CONNECT_DESTINATION_DENIED',event=event)
    def test_every_public_preflight_keeps_install_gate_blocked(self):
        p=legacy.contract();self.assertEqual(broker.validate(p,common.digest(p),broker.source_pin())['install_uninstall'],'BLOCKED')
        base=p['integration'];self.assertEqual(security.validate(base,common.digest(base))['install_uninstall'],'BLOCKED')
        self.assertEqual(security.preflight({},'bad')['install_uninstall'],'BLOCKED')

class MutationTests(unittest.TestCase):
    def killed(self,module,old,new,probe,label):
        path=PKG/(module.__name__+'.py');source=path.read_text(encoding='utf-8');self.assertEqual(source.count(old),1)
        mutated=source.replace(old,new);clone=types.ModuleType('admission_mutant_'+label);clone.__file__=str(path)
        exec(compile(mutated,str(path),'exec'),clone.__dict__)
        original=broker.security
        if module is security:broker.security=clone
        try:
            class Oracle(unittest.TestCase):
                def runTest(self):probe(self,clone if module is broker else broker)
            stream=io.StringIO();r=unittest.TextTestRunner(stream=stream).run(Oracle())
        finally:broker.security=original
        self.assertEqual((r.testsRun,len(r.failures),len(r.errors)),(1,1,0))
        put(RUN/('mutant-'+label+'.json'),{'label':label,'inner_collected':1,'inner_failures':1,'inner_errors':0,
            'oracle':'Expected FAIL after weakening a mandatory Python admission check','executed_python':True,'network_native_go':False,
            'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'mutant_sha256':hashlib.sha256(mutated.encode()).hexdigest(),
            'runner':stream.getvalue().replace(str(REPO),'<REPO>')})
    @staticmethod
    def reason_probe(p,code,raw=None,event=None,pin=None):
        def probe(t,m):
            r=m.strict_preflight(common.canonical(p) if raw is None else raw,common.digest(p) if pin is None else pin,broker.source_pin(),request_metadata=metadata() if event is None else event)
            t.assertEqual(r['reason'],code)
        return probe
    def test_mutant_auth_required_detected(self):
        p=candidate();p['admission']['authentication']['required']=False
        self.killed(security,"require(auth['required'] is True,'AUTH_REQUIRED')","require(True,'AUTH_REQUIRED')",self.reason_probe(p,'AUTH_REQUIRED'),'auth')
    def test_mutant_merge_detected(self):
        p=candidate();p['admission']['configuration']['merge']=True
        self.killed(security,"require(config['merge'] is False,'CONFIG_MERGE_DENIED')","require(True,'CONFIG_MERGE_DENIED')",self.reason_probe(p,'CONFIG_MERGE_DENIED'),'merge')
    def test_mutant_method_detected(self):
        event=metadata();event['method']='GET'
        self.killed(security,"require(request_metadata['method']=='CONNECT','CONNECT_METHOD_DENIED')","require(True,'CONNECT_METHOD_DENIED')",self.reason_probe(candidate(),'CONNECT_METHOD_DENIED',event=event),'method')
    def test_mutant_schema_route_guard_detected(self):
        p=candidate();p['routing']['direct']=True
        self.killed(broker,'error=next(Draft202012Validator(schema).iter_errors(contract),None)','error=None',self.reason_probe(p,'STRICT_DIRECT_DENIED'),'direct')
    def test_mutant_canonical_guard_detected(self):
        p=candidate()
        self.killed(broker,"require(raw==canonical(contract),'CONFIG_NOT_CANONICAL')","require(True,'CONFIG_NOT_CANONICAL')",self.reason_probe(p,'CONFIG_NOT_CANONICAL',raw=json.dumps(p,indent=2).encode()),'canonical')
    def test_mutant_controller_pin_detected(self):
        p=candidate();pin=common.digest(p);p['generation']+=1
        self.killed(broker,"require(digest(contract) == pin, 'CONFIG_PIN_MISMATCH')","require(True, 'CONFIG_PIN_MISMATCH')",self.reason_probe(p,'CONFIG_PIN_MISMATCH',pin=pin),'pin')
    def test_mutant_secret_error_echo_detected(self):
        original=security.validate_admission;sentinel='SYNTHETIC_ERROR_ECHO_MARKER_007'
        security.validate_admission=lambda *a,**k:(_ for _ in ()).throw(common.Denied(sentinel))
        def probe(t,m):
            p=candidate();r=m.strict_preflight(common.canonical(p),common.digest(p),broker.source_pin(),request_metadata=metadata())
            t.assertNotIn(sentinel,json.dumps(r))
        try:self.killed(broker,'return fallback','return str(exc)',probe,'error-echo')
        finally:security.validate_admission=original

class Result(unittest.TextTestResult):
    def addSuccess(self,t):super().addSuccess(t);RESULTS.append({'id':t.id(),'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);RESULTS.append({'id':t.id(),'status':'FAIL','traceback':self._exc_info_to_string(e,t).replace(str(REPO),'<REPO>')})
    def addError(self,t,e):super().addError(t,e);RESULTS.append({'id':t.id(),'status':'ERROR','traceback':self._exc_info_to_string(e,t).replace(str(REPO),'<REPO>')})

def main():
    global RUN
    RUN=TASK/'runs'/('admission-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);RUN.mkdir()
    legacy.OUT=RUN/'legacy';legacy.OUT.mkdir()
    exclude={'test_cli_always_exit20_and_output_scope','test_remote_schema_reference_is_refused_without_dial'}
    names=[n for n in unittest.defaultTestLoader.getTestCaseNames(legacy.ContractTests) if n not in exclude]
    suite=unittest.TestSuite([unittest.TestSuite(legacy.ContractTests(n) for n in names),unittest.defaultTestLoader.loadTestsFromTestCase(AdmissionTests),unittest.defaultTestLoader.loadTestsFromTestCase(MutationTests)])
    paths=[PKG/'broker.py',PKG/'security_contract.py',PKG/'common.py',PKG/'configs/broker.v1.schema.json',PKG/'tests/broker_suite.py',Path(__file__).resolve()]
    pins={p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};put(RUN/'source_pins.json',pins)
    stream=io.StringIO();r=unittest.TextTestRunner(verbosity=2,stream=stream,resultclass=Result).run(suite)
    unchanged=all(hashlib.sha256((REPO/n).read_bytes()).hexdigest()==v for n,v in pins.items())
    code=0 if r.wasSuccessful() and unchanged and not BLOCKED_OPERATIONS else 1
    put(RUN/'result.json',{'task':TASK.name,'collected':r.testsRun,'passed':sum(x['status']=='PASS' for x in RESULTS),'failed':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'exit_code':code,'tests':RESULTS,'legacy_pure':len(names),'admission_tests':len(unittest.defaultTestLoader.getTestCaseNames(AdmissionTests)),'mutant_tests':len(unittest.defaultTestLoader.getTestCaseNames(MutationTests)),'source_pins_unchanged':unchanged,'offline_guard_violations':BLOCKED_OPERATIONS,'network_or_subprocess_tests_not_collected':sorted(exclude),'native_security':'NOT VERIFIED','can_apply':False,'can_start_tunnel':False})
    (RUN/'runner.txt').write_text(stream.getvalue().replace(str(REPO),'<REPO>'),encoding='utf-8')
    print(json.dumps({'exit_code':code,'collected':r.testsRun,'passed':sum(x['status']=='PASS' for x in RESULTS),'failed':len(r.failures),'errors':len(r.errors),'evidence':RUN.relative_to(REPO).as_posix()}));return code
if __name__=='__main__':sys.exit(main())
