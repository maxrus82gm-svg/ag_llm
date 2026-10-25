"""Small synthetic oracle/plan checks + reuse of accepted pure broker API.

No native tests are imported or collected; no network/child processes allowed.
"""
import copy, hashlib, importlib.util, io, json, os, sys, unittest
from pathlib import Path
from unittest.mock import patch

TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[1]
sys.path.insert(0,str(TASK))
import offline_oracles as oracle
import plan_data
BLOCKED=[]
def guard(event,args):
    if event.startswith(('socket.','winreg.')) or event in ('subprocess.Popen','os.system','os.posix_spawn'):
        BLOCKED.append(event); raise PermissionError('OFFLINE_ONLY')
    if event == 'open':
        name, mode, flags=args
        if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)):
            if not isinstance(name,(str,bytes,os.PathLike)) or not Path(name).resolve().is_relative_to(TASK):
                BLOCKED.append('WRITE_OUTSIDE_TASK');raise PermissionError('TASK_WRITE_SCOPE')
sys.addaudithook(guard)

RUN='a'*32
def observation(name):
    return {'source':oracle.SOURCES[name],'run':RUN,'fresh':True,'complete_window':True}
def example(kind='DENY'):
    p={'boundary':'SYNTHETIC_OFFLINE_ONLY','run':RUN,'kind':kind}
    for name in ['initiator','policy','receiver','lifecycle']: p[name]=observation(name)
    p['initiator'].update(initiated=True,token_observed=True,image_pinned=True,tuple_bound=True,nonce_correlated=True,observer_control_valid=True,role='C',socket_owner_observed=False,exact_upstream=False)
    p['policy'].update(effective_readback=True,competing_filters_reviewed=True,attributable_deny=True,deny_retained=True)
    p['receiver'].update(receipts=0,payload_nonce_match=False)
    p['lifecycle'].update(admissions_frozen=True,startup_disabled=True,processes=0,flows=0,queued_work=0,inherited_handles=0)
    if kind=='ALLOW':
        p['initiator'].update(role='B_ENGINE',socket_owner_observed=True,exact_upstream=True)
        p['policy']['attributable_deny']=False
        p['receiver'].update(receipts=1,payload_nonce_match=True)
    return p

class OracleTests(unittest.TestCase):
    def reject(self,sample,code):
        r=oracle.evaluate(sample);self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(r['reason'],code)
    def test_complete_denial(self): self.assertEqual(oracle.evaluate(example())['status'],'OFFLINE_CONSISTENT')
    def test_complete_b_owned_route(self): self.assertEqual(oracle.evaluate(example('ALLOW'))['status'],'OFFLINE_CONSISTENT')
    def test_complete_quiescence(self): self.assertEqual(oracle.evaluate(example('QUIESCENCE'))['status'],'OFFLINE_CONSISTENT')
    def test_timeout_only_never_proves_deny(self): self.reject({'boundary':'SYNTHETIC_OFFLINE_ONLY','run':RUN,'kind':'DENY','timeout':True},'INDEPENDENT_FRESH_OBSERVATIONS_REQUIRED')
    def test_missing_attempt_and_controls(self):
        for field in ['initiated','token_observed','image_pinned','tuple_bound','nonce_correlated','observer_control_valid']:
            p=example();p['initiator'][field]=False;self.reject(p,'ATTEMPT_OR_CONTROL_UNPROVED')
    def test_receiver_receipt_contradicts_denial(self):
        p=example();p['receiver']['receipts']=1;self.reject(p,'DENIAL_UNPROVED')
    def test_firewall_enabled_not_effective_deny(self):
        p=example();p['policy']={'enabled':True};self.reject(p,'INDEPENDENT_FRESH_OBSERVATIONS_REQUIRED')
    def test_unreviewed_competing_filter_and_missing_deny(self):
        for field in ['effective_readback','competing_filters_reviewed']:
            p=example();p['policy'][field]=False;self.reject(p,'EFFECTIVE_POLICY_UNPROVED')
        p=example();p['policy']['attributable_deny']=False;self.reject(p,'DENIAL_UNPROVED')
    def test_connect200_without_owner_or_payload_is_insufficient(self):
        for field in ['socket_owner_observed','exact_upstream']:
            p=example('ALLOW');p['initiator'][field]=False;self.reject(p,'B_ROUTE_UNPROVED')
        p=example('ALLOW');p['receiver']['payload_nonce_match']=False;self.reject(p,'B_ROUTE_UNPROVED')
    def test_wrapper_or_ui_owner_is_rejected(self):
        for role in ['B_WRAPPER','U','C']:
            p=example('ALLOW');p['initiator']['role']=role;self.reject(p,'B_ROUTE_UNPROVED')
    def test_stale_mixed_and_partial_windows_rejected(self):
        for part in ['initiator','policy','receiver']:
            for key,value in [('run','b'*32),('fresh',False),('complete_window',False),('source','CALLER')]:
                p=example();p[part][key]=value;self.reject(p,'INDEPENDENT_FRESH_OBSERVATIONS_REQUIRED')
    def test_invalid_counts_not_coerced(self):
        for value in [True,-1,'0',None]:
            p=example();p['receiver']['receipts']=value;self.reject(p,'RECEIVER_COUNT_INVALID')
    def test_quiescence_blocks_survivors_unknown_and_bool_counts(self):
        for key in ['processes','flows','queued_work','inherited_handles']:
            for value in [1,-1,None,False,'0']:
                p=example('QUIESCENCE');p['lifecycle'][key]=value;self.reject(p,'KEEP_DENY_QUIESCENCE_UNPROVED')
    def test_keep_deny_and_freeze_are_required(self):
        for part,key in [('policy','deny_retained'),('lifecycle','admissions_frozen'),('lifecycle','startup_disabled')]:
            p=example('QUIESCENCE');p[part][key]=False;self.reject(p,'KEEP_DENY_QUIESCENCE_UNPROVED')
    def test_quiescence_requires_effective_readback(self):
        p=example('QUIESCENCE');p['policy']['effective_readback']=False
        self.reject(p,'EFFECTIVE_POLICY_UNPROVED')
    def test_denial_role_is_bounded(self):
        for role in ['U','B_WRAPPER',[],None,True]:
            p=example();p['initiator']['role']=role
            self.reject(p,'ATTEMPT_OR_CONTROL_UNPROVED')
    def test_only_synthetic_boundary_supported(self):
        for value in [None,{},[],{'boundary':'NATIVE_VERIFIED'}]: self.reject(value,'SYNTHETIC_BOUNDARY_REQUIRED')
    def test_malformed_kind_returns_fixed_rejection(self):
        for kind in [[],{},None,1,True,'OTHER']:
            p=example();p['kind']=kind;self.reject(p,'SCENARIO_KIND_REQUIRED')
    def test_run_binding_format(self):
        for value in [None,True,[],RUN.upper(), 'a'*31,'g'*32]:
            p=example();p['run']=value;self.reject(p,'RUN_BINDING_REQUIRED')
    def test_input_cannot_promote_native_status(self):
        for kind in ['DENY','ALLOW','QUIESCENCE']:
            p=example(kind);p.update(native_verified=True,can_apply=True,can_start_tunnel=True)
            r=oracle.evaluate(p);self.assertFalse(r['native_verified']);self.assertFalse(r['can_apply']);self.assertFalse(r['can_start_tunnel'])

class PlanTests(unittest.TestCase):
    def test_exact_family_collection_and_evidence_dimensions(self):
        p=plan_data.plan();self.assertEqual([x['id'] for x in p['families']],[f'N{i:02}' for i in range(1,19)])
        for row in p['families']:
            self.assertEqual(row['execution'],'NOT RUN');self.assertEqual(row['classification'],'BLOCKED')
            for key in ['observation_source','expected','negative_control','false_pass_risk','preparation_rollback']: self.assertGreater(len(row[key]),40)
    def test_permission_gates_are_separate_and_activation_closed(self):
        p=plan_data.plan();self.assertEqual(p['permissions'],['READ_ONLY','LAB_SETUP','RULE_APPLY','NATIVE_EGRESS_TEST','TUNNEL_START'])
        self.assertEqual(p['engine_family'],'V2Ray');self.assertEqual(p['native_tests_run'],0)
        self.assertIs(p['can_apply'],False);self.assertIs(p['can_start_tunnel'],False)
        self.assertEqual(p['install_uninstall'],'BLOCKED');self.assertEqual(p['strict_admission_status'],'STRICT_ADMISSION_BLOCKED')
    def test_host_observations_are_actual_bounded_schema(self):
        p=json.loads((TASK/'evidence/host_observations.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(len(p['observations']),14);self.assertEqual(p['native_network_tests_run'],0)
        self.assertEqual({r['id'] for r in p['observations'] if r['id'].startswith('account_')},{'account_wua-client','account_wua-broker'})
        for row in p['observations']: self.assertIn(row['classification'],{'OBSERVED_READ_ONLY','BLOCKED'})
    def test_protected_inputs_unchanged(self):
        data=json.loads((TASK/'evidence/protected_inputs_before.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['files']),24)
        for row in data['files']:
            raw=(ROOT/row['path']).read_bytes();self.assertEqual(len(raw),row['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
    def test_reuses_existing_admission_without_unlocking(self):
        sys.path.insert(0,str(ROOT/'integrations/wua_chatgpt_mcp'))
        import broker, common
        p=json.loads((ROOT/'integrations/wua_chatgpt_mcp/configs/broker.v1.synthetic.example.json').read_text())
        p['remote_identity']['credential_ref']='wua-secret-ref:11111111-1111-4111-8111-111111111111'
        p['admission']={'authentication':{'required':True,'mechanism':'BROKER_ONLY_PROTECTED_REFERENCE','users':[{'principal':'mcp-client','credential_ref':'wua-secret-ref:22222222-2222-4222-8222-222222222222'}]},'configuration':{'source_count':1,'format':'CANONICAL_JSON','protection':'BROKER_ONLY_PROTECTED_SOURCE','merge':False,'reload':False,'environment_override':False},'connect':{'methods':['CONNECT'],'targets':[{'address':'198.51.100.20','port':443}],'allow_upgrade':False,'allow_plain_http':False,'allow_uot':False,'allow_background':False}}
        event={'method':'CONNECT','upgrade':False,'address':'198.51.100.20','port':443,'connect_accepted':True}
        positive=broker.strict_preflight(common.canonical(p),common.digest(p),broker.source_pin(),request_metadata=event)
        self.assertEqual(positive['strict_policy_status'],'VALID');self.assertEqual(positive['reason'],'RUNTIME_SECURITY_UNVERIFIED')
        self.assertIs(positive['can_apply'],False);self.assertIs(positive['can_start_tunnel'],False)
        self.assertEqual(positive['strict_admission_status'],'STRICT_ADMISSION_BLOCKED')
        p['admission']['authentication']['users']=[]
        negative=broker.strict_preflight(common.canonical(p),common.digest(p),broker.source_pin(),request_metadata=event)
        self.assertEqual(negative['reason'],'AUTH_USERS_REQUIRED');self.assertIs(negative['can_apply'],False)

class MutationTests(unittest.TestCase):
    def caught(self,bad,mutation):
        class Inner(unittest.TestCase):
            def runTest(self): self.assertEqual(oracle.evaluate(bad)['status'],'INCOMPLETE')
        result=unittest.TestResult()
        with mutation: Inner().run(result)
        self.assertEqual(result.testsRun,1);self.assertEqual(len(result.failures),1);self.assertEqual(len(result.errors),0)
    def test_mutant_provenance_check_removed_is_caught(self):
        bad=example();bad['policy']['source']='CALLER'
        self.caught(bad,patch.object(oracle,'bound',return_value=True))
    def test_mutant_wrapper_owner_allowed_is_caught(self):
        bad=example('ALLOW');bad['initiator']['role']='U'
        original=oracle.evaluate
        def mutated(p):
            p=copy.deepcopy(p);p['initiator']['role']='B_ENGINE';return original(p)
        self.caught(bad,patch.object(oracle,'evaluate',side_effect=mutated))
    def test_mutant_ledger_zero_overrides_live_work_is_caught(self):
        bad=example('QUIESCENCE');bad['lifecycle']['queued_work']=1
        original=oracle.evaluate
        def mutated(p):
            p=copy.deepcopy(p);p['lifecycle']['queued_work']=0;return original(p)
        self.caught(bad,patch.object(oracle,'evaluate',side_effect=mutated))

class Recording(unittest.TextTestResult):
    def startTest(self,test): super().startTest(test); self.current=test.id()
    def addSuccess(self,test): super().addSuccess(test); ROWS.append({'id':test.id(),'status':'PASS'})
    def addFailure(self,test,err): super().addFailure(test,err); ROWS.append({'id':test.id(),'status':'FAIL','exception_type':err[0].__name__})
    def addError(self,test,err): super().addError(test,err); ROWS.append({'id':test.id(),'status':'ERROR','exception_type':err[0].__name__})

if __name__=='__main__':
    name=sys.argv[1] if len(sys.argv)==2 else 'green'
    if name not in {'red','review_red','green'}: raise SystemExit('OUTPUT_NAME')
    ROWS=[]
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [OracleTests,PlanTests,MutationTests])
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=0,resultclass=Recording).run(suite)
    payload={'schema':1,'kind':'SYNTHETIC_OFFLINE_ONLY','count':r.testsRun,'pass':len([x for x in ROWS if x['status']=='PASS']),'fail':len(r.failures),'error':len(r.errors),'skip':len(r.skipped),'exit_code':0 if r.wasSuccessful() else 1,'blocked_operation_attempts':BLOCKED,'native_network_tests_run':0,'rows':ROWS}
    (TASK/f'evidence/{name}_tests.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='rows'}))
    raise SystemExit(payload['exit_code'])
