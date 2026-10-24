"""Source-only assertions/mutations + existing pure contract regression."""
from pathlib import Path
import copy,hashlib,importlib.util,io,json,sys,time,unittest,uuid
sys.dont_write_bytecode=True
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1];sys.path.insert(0,str(PKG))
import common,broker,singbox_source_review as review
OUT=REPO/'reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/amendment_01';RUN=None;RESULTS=[];FILES=None
ROOT=Path('M:/WUA_SOURCE_REVIEW/sing-box/v1.13.4/source/sing-box-1.13.4')
ARCHIVE=ROOT.parents[1]/'sing-box-v1.13.4-source.zip'
def guard(event,args):
    if event.startswith('socket.') or event in ['subprocess.Popen','os.system','os.posix_spawn']:raise PermissionError('OFFLINE_SOURCE_ONLY')
sys.addaudithook(guard)
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def contract():return json.loads((PKG/'configs/broker.v1.synthetic.example.json').read_bytes())
class SourceTests(unittest.TestCase):
    def test_archive_revision_and_hash_binding(self):
        self.assertTrue(review.archive_identity(ARCHIVE)['revision_comment_matches'])
        with self.assertRaisesRegex(common.Denied,'ARCHIVE_HASH_MISMATCH'):review.archive_identity(ARCHIVE,'0'*64)
        with self.assertRaisesRegex(common.Denied,'ARCHIVE_REVISION_MISMATCH'):review.archive_identity(ARCHIVE,expected_revision='0'*40)
    def test_required_source_files_not_just_tag(self):
        self.assertFalse(review.inspect(FILES)['can_apply'])
        for path in ['go.mod','go.sum','protocol/http/inbound.go','route/route.go']:
            f=dict(FILES);del f[path]
            with self.assertRaises(common.Denied):review.inspect(f)
    def test_go_mod_and_sum_revision_mismatch(self):
        self.assertIn('EMPTY_OUTBOUND_CREATES_DIRECT',review.inspect(FILES)['findings'])
        for path,needle in [('go.mod',review.SING_VERSION),('go.sum',review.SING_SUM)]:
            f=dict(FILES);f[path]=f[path].replace(needle.encode(),b'wrong')
            with self.assertRaises(common.Denied):review.inspect(f)
    def test_file_content_substitution_pin(self):
        pins={'go.mod':hashlib.sha256(FILES['go.mod']).hexdigest()};review.check_pins(FILES,pins)
        f=dict(FILES);f['go.mod']+=b'\n'
        with self.assertRaisesRegex(common.Denied,'SOURCE_FILE_DRIFT'):review.check_pins(f,pins)
    def test_unknown_native_schema_field_mutation(self):
        self.assertTrue(review.inspect(FILES)['locators'])
        f=dict(FILES);p='option/options.go';f[p]=f[p].replace(b'type _Options struct {',b'type _Options struct {\n Sneaky bool `json:"sneaky"`')
        with self.assertRaisesRegex(common.Denied,'OPTION_FIELD_SET_DRIFT'):review.inspect(f)
    def test_other_outbound_source_mutation(self):
        p='route/route.go';normal=b'selectedOutbound, loaded = r.outbound.Outbound(action.Outbound)';self.assertIn(normal,FILES[p]);f=dict(FILES);f[p]=f[p].replace(normal,b'selectedOutbound, loaded = r.outbound.Outbound("unapproved")')
        with self.assertRaisesRegex(common.Denied,'SOURCE_BRANCH_DRIFT:selected_outbound'):review.inspect(f)
        (RUN/'other_outbound_mutant.go').write_bytes(f[p]);put(RUN/'other_outbound_mutation.json',{'oracle':'REJECT / SOURCE_BRANCH_DRIFT:selected_outbound','executed_go':False,'original_sha256':hashlib.sha256(FILES[p]).hexdigest(),'mutant_sha256':hashlib.sha256(f[p]).hexdigest()})
    def test_default_direct_review_intent_mutation(self):
        # Native empty-default is already DIRECT. Mutate the existing strict
        # intent, not pretend that unexecuted Go defaults were safe or executed.
        self.assertIn('EMPTY_OUTBOUND_CREATES_DIRECT',review.inspect(FILES)['findings']);c=contract();self.assertEqual(broker.preflight(c,common.digest(c),broker.source_pin())['profile_status'],'BROKER_PROFILE_STRUCTURALLY_VALID')
        c['routing']['default']='DIRECT';r=broker.preflight(c,common.digest(c),broker.source_pin());self.assertEqual(r['profile_status'],'BROKER_PROFILE_REJECTED');self.assertFalse(r['can_apply'])
        put(RUN/'default_direct_mutation.json',{'oracle':'REJECT','scope':'existing broker review intent; not native Go runtime','default':'DIRECT','native_default_finding':'EMPTY_OUTBOUND_CREATES_DIRECT','result':r})
    def test_config_default_and_merge_drift(self):
        self.assertFalse(review.inspect(FILES)['can_start_tunnel'])
        for p,old,new in [('cmd/sing-box/cmd.go','configPaths = append(configPaths, "config.json")','configPaths = append(configPaths, "other.json")'),('cmd/sing-box/cmd_run.go','badjson.MergeJSON(','unknown.Merge(')]:
            f=dict(FILES);f[p]=f[p].replace(old.encode(),new.encode())
            with self.assertRaisesRegex(common.Denied,'SOURCE_BRANCH_DRIFT:config_'):review.inspect(f)
    def test_hidden_path_drift(self):
        self.assertIn('HTTP_TCP_INBOUND_CAN_DISPATCH_UOT',review.inspect(FILES)['findings'])
        for key in ['uot','remote_rules','ntp','tor_helper','ech_dns','reality_cover']:
            p,_,anchors=review.LOCI[key];f=dict(FILES);f[p]=f[p].replace(anchors[-1].encode(),b'changed_anchor')
            with self.assertRaisesRegex(common.Denied,'SOURCE_BRANCH_DRIFT:'+key):review.inspect(f)
    def test_missing_dependency_never_becomes_full_http_support(self):
        r=review.inspect(FILES);self.assertFalse(r['dependency_http_path_present']);self.assertTrue(r['http_connect_source'].startswith('UNVERIFIED'))
        f=dict(FILES);f['vendor/github.com/sagernet/sing/protocol/http/server.go']=b'// fake approved'
        self.assertTrue(review.inspect(f)['http_connect_source'].startswith('UNVERIFIED'));self.assertFalse(review.inspect(f)['can_apply'])
    def test_second_proxy_and_engine_family_remain_rejected(self):
        c=contract();self.assertFalse(broker.preflight(c,common.digest(c),broker.source_pin())['can_apply'])
        for path,key,value in [('routing','secondary_proxy',True),('engine','family','sing-box')]:
            c=contract();c[path][key]=value;self.assertEqual(broker.preflight(c,common.digest(c),broker.source_pin())['profile_status'],'BROKER_PROFILE_REJECTED')
class Result(unittest.TextTestResult):
    def addSuccess(self,t):super().addSuccess(t);RESULTS.append({'id':t.id(),'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);RESULTS.append({'id':t.id(),'status':'FAIL','traceback':self._exc_info_to_string(e,t)})
    def addError(self,t,e):super().addError(t,e);RESULTS.append({'id':t.id(),'status':'ERROR','traceback':self._exc_info_to_string(e,t)})
def main():
    global RUN,FILES
    RUN=OUT/'runs'/('source-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);RUN.mkdir()
    names={'go.mod','go.sum',*(v[0] for v in review.LOCI.values())};FILES={n:(ROOT/n).read_bytes() for n in names}
    source_pins={n:hashlib.sha256(raw).hexdigest() for n,raw in FILES.items()};put(RUN/'upstream_source_pins.json',source_pins)
    paths=[PKG/'singbox_source_review.py',Path(__file__).resolve(),PKG/'broker.py',PKG/'security_contract.py',PKG/'common.py',PKG/'tests/broker_suite.py'];pins={p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};put(RUN/'local_source_pins.json',pins)
    spec=importlib.util.spec_from_file_location('legacy_contracts',PKG/'tests/broker_suite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.OUT=RUN/'legacy';m.OUT.mkdir()
    excluded={'test_cli_always_exit20_and_output_scope','test_remote_schema_reference_is_refused_without_dial'};legacy=[n for n in unittest.defaultTestLoader.getTestCaseNames(m.ContractTests) if n not in excluded]
    stream=io.StringIO();r=unittest.TextTestRunner(verbosity=2,stream=stream,resultclass=Result).run(unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(SourceTests),unittest.TestSuite(m.ContractTests(n) for n in legacy)]))
    unchanged=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==pin for n,pin in source_pins.items()) and all(hashlib.sha256((REPO/n).read_bytes()).hexdigest()==pin for n,pin in pins.items())
    put(RUN/'result.json',{'task':'CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001','amendment':1,'collected':r.testsRun,'passed':sum(x['status']=='PASS' for x in RESULTS),'failed':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'source_tests':11,'legacy_regression':len(legacy),'tests':RESULTS,'sources_unchanged':unchanged,'engine_runs':0,'Go_build_test_runs':0,'network_tests':0,'can_apply':False,'can_start_tunnel':False});(RUN/'runner.txt').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue());print('EVIDENCE '+str(RUN));return 0 if r.wasSuccessful() and unchanged else 1
if __name__=='__main__':sys.exit(main())
