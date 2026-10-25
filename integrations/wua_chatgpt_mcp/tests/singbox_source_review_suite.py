"""Source-only assertions/mutations + existing pure contract regression."""
from pathlib import Path
import copy,hashlib,importlib.util,io,json,stat,sys,time,unittest,uuid,zipfile
sys.dont_write_bytecode=True
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1];sys.path.insert(0,str(PKG))
import common,broker,singbox_source_review as review
OUT=REPO/'reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/amendment_01';RUN=None;RESULTS=[];FILES=None
ROOT=Path('M:/WUA_SOURCE_REVIEW/sing-box/v1.13.4/source/sing-box-1.13.4')
ARCHIVE=ROOT.parents[1]/'sing-box-v1.13.4-source.zip'
DEP_ROOT=None;DEP_FILES=None;DEP_PINS=None;DEP_ARCHIVE=None
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

class DependencyTests(unittest.TestCase):
    """Data-only controls for ZIP admission and pinned lexical source review.

    No test here executes HTTP, Go JSON, authentication or a native network path.
    """
    prefix='github.com/sagernet/sing@'+review.SING_VERSION+'/'
    vector_h1='h1:MuNncLzBwKXj+qJX+wy7GISWyzp/i1ll8JXcFa6G8k8='
    def archive(self,extra=None,compression=zipfile.ZIP_STORED,reverse=False):
        rows=[('go.mod',b'module github.com/sagernet/sing\n'),('hello.txt',b'hello\n')]
        if extra:rows+=extra
        if reverse:rows.reverse()
        path=RUN/('synthetic-'+uuid.uuid4().hex+'.zip')
        with zipfile.ZipFile(path,'w',compression=compression) as z:
            for name,body in rows:
                z.writestr(self.prefix+name if isinstance(name,str) else name,body)
        self.addCleanup(path.unlink)
        return path
    def mutated(self,path,old,new):
        files=dict(DEP_FILES);self.assertIn(old.encode(),files[path]);files[path]=files[path].replace(old.encode(),new.encode())
        pins={n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()}
        return files,pins
    def test_actual_module_h1_is_not_raw_zip_sha(self):
        result=review.module_zip_identity(DEP_ARCHIVE)
        self.assertEqual(result['h1'],review.SING_SUM);self.assertEqual(result['file_count'],322)
        self.assertEqual(result['raw_zip_sha256'],'dfb3b8c7cbc603602c6cf453161d319209e5610477e1118354dd449bd9409659')
        self.assertFalse(result['native_security_verified'])
    def test_wrong_expected_module_hash_rejected(self):
        with self.assertRaisesRegex(common.Denied,'MODULE_ZIP_H1_MISMATCH'):
            review.module_zip_identity(DEP_ARCHIVE,'h1:'+'A'*43+'=')
    def test_fixed_vector_archive_order_and_compression_independent(self):
        a=self.archive();b=self.archive(compression=zipfile.ZIP_DEFLATED,reverse=True)
        ra=review.module_zip_identity(a,self.vector_h1);rb=review.module_zip_identity(b,self.vector_h1)
        self.assertEqual(ra['h1'],rb['h1']);self.assertNotEqual(ra['raw_zip_sha256'],rb['raw_zip_sha256'])
    def test_member_body_corruption_rejects_h1(self):
        p=self.archive([('extra.txt',b'changed')])
        with self.assertRaisesRegex(common.Denied,'MODULE_ZIP_H1_MISMATCH'):review.module_zip_identity(p,self.vector_h1)
    def test_crc_damage_rejected_before_extract(self):
        p=self.archive();raw=p.read_bytes();self.assertEqual(raw.count(b'hello\n'),1);p.write_bytes(raw.replace(b'hello\n',b'jello\n'))
        with self.assertRaisesRegex(zipfile.BadZipFile,'CRC'):review.module_zip_identity(p,self.vector_h1)
    def test_traversal_and_windows_aliases_rejected(self):
        for path,code in [('../escape','MODULE_ZIP_PATH'),('a/../b','MODULE_ZIP_PATH'),('a//b','MODULE_ZIP_PATH'),('a:stream','MODULE_ZIP_PATH'),('CON.txt','MODULE_ZIP_WINDOWS_PATH'),('a.','MODULE_ZIP_WINDOWS_PATH'),('.git/config','MODULE_ZIP_WINDOWS_PATH')]:
            with self.subTest(path=path):
                with self.assertRaisesRegex(common.Denied,code):review.module_zip_identity(self.archive([(path,b'x')]),self.vector_h1)
        # ZipInfo/writestr normalize '\\' on Windows: inject exact raw names in
        # both local/central headers and prove the malformed-name trigger.
        for bad in (b'a\\b',b'a\x00b'):
            p=self.archive([('a_b',b'x')]);data=p.read_bytes();self.assertEqual(data.count(b'/a_b'),2)
            p.write_bytes(data.replace(b'/a_b',b'/'+bad))
            with zipfile.ZipFile(p) as z:self.assertTrue(any(bad.decode() in e.orig_filename for e in z.infolist()))
            with self.assertRaisesRegex(common.Denied,'MODULE_ZIP_PATH'):review.module_zip_identity(p,self.vector_h1)
    def test_wrong_module_prefix_rejected(self):
        info=zipfile.ZipInfo('github.com/other/module@v1.0.0/file.go')
        with self.assertRaisesRegex(common.Denied,'MODULE_ZIP_PREFIX'):review.module_zip_identity(self.archive([(info,b'x')]),self.vector_h1)
    def test_case_and_file_directory_collisions_rejected(self):
        for rows,code in [([('A.go',b'a'),('a.go',b'b')],'MODULE_ZIP_COLLISION'),([('hello.txt/child',b'x')],'MODULE_ZIP_FILE_DIRECTORY_COLLISION')]:
            with self.subTest(code=code):
                with self.assertRaisesRegex(common.Denied,code):review.module_zip_identity(self.archive(rows),self.vector_h1)
    def test_link_and_binary_member_rejected(self):
        link=zipfile.ZipInfo(self.prefix+'link');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        for row,code in [((link,b'go.mod'),'MODULE_ZIP_ENTRY_TYPE'),(('core.exe',b'not an executable run'),'MODULE_ZIP_EXECUTABLE')]:
            with self.subTest(code=code):
                with self.assertRaisesRegex(common.Denied,code):review.module_zip_identity(self.archive([row]),self.vector_h1)
    def test_module_declaration_checked(self):
        path=RUN/'wrong-module.zip'
        with zipfile.ZipFile(path,'w') as z:z.writestr(self.prefix+'go.mod',b'module github.com/other/module\n')
        self.addCleanup(path.unlink)
        with self.assertRaisesRegex(common.Denied,'MODULE_DECLARATION'):review.module_zip_identity(path,self.vector_h1)
    def test_expansion_limit_checked_before_read(self):
        p=self.archive([('large.txt',b'0'*(8*1024*1024+1))],compression=zipfile.ZIP_DEFLATED)
        with self.assertRaisesRegex(common.Denied,'MODULE_ZIP_EXPANSION'):review.module_zip_identity(p,self.vector_h1)
    def test_oversize_archive_input_read_is_bounded(self):
        p=RUN/'oversize-input.zip';p.write_bytes(b'x'*(32*1024*1024+1));self.addCleanup(p.unlink)
        with self.assertRaisesRegex(common.Denied,'MODULE_ZIP_SIZE'):review.module_zip_identity(p,self.vector_h1)
    def test_real_reviewed_loci_keep_activation_blocked(self):
        result=review.inspect_sing_dependency(DEP_FILES,DEP_PINS)
        self.assertGreater(len(result['locators']),40);self.assertFalse(result['complete_dependency_closure'])
        self.assertFalse(result['can_apply']);self.assertFalse(result['can_start_tunnel'])
    def test_dependency_source_pin_tampering_rejected(self):
        files=dict(DEP_FILES);files['common/auth/auth.go']+=b'\n// unreviewed change\n'
        with self.assertRaisesRegex(common.Denied,'SOURCE_FILE_DRIFT'):review.inspect_sing_dependency(files,DEP_PINS)
    def test_missing_dependency_file_rejected(self):
        files=dict(DEP_FILES);del files['protocol/http/handshake.go']
        with self.assertRaisesRegex(common.Denied,'SOURCE_FILE_MISSING'):review.inspect_sing_dependency(files,DEP_PINS)
    def test_omitted_auth_guard_rejected_independently_of_pin(self):
        f,p=self.mutated('protocol/http/handshake.go','if authenticator != nil {','if true {')
        with self.assertRaisesRegex(common.Denied,'SING_BRANCH_DRIFT:auth_guard'):review.inspect_sing_dependency(f,p)
    def test_auth_verification_after_dispatch_rejected(self):
        f=dict(DEP_FILES);path='protocol/http/handshake.go';text=f[path].decode()
        verify='authOk = authenticator.Verify(username, password)'
        call='handler.NewConnectionEx(ctx, requestConn, source, destination, onClose)'
        self.assertEqual(text.count(verify),1);text=text.replace(verify,'// deliberately relocated verification').replace(call,call+'\n'+verify)
        f[path]=text.encode();pins={n:hashlib.sha256(b).hexdigest() for n,b in f.items()}
        with self.assertRaisesRegex(common.Denied,'SING_AUTH_DISPATCH_ORDER_DRIFT'):review.inspect_sing_dependency(f,pins)
        put(RUN/'auth_order_mutation.json',{'oracle':'SING_AUTH_DISPATCH_ORDER_DRIFT','executed_go':False,'scope':'Lexical copied source, not runtime auth failure'})
    def test_parser_and_port_conversion_drift_rejected(self):
        for key in ['http_read','connect_target','port_cast','stdlib_link']:
            path,_,anchors=review.SING_LOCI[key];f,p=self.mutated(path,anchors[0],'deliberately_changed_source_anchor')
            with self.subTest(key=key):
                with self.assertRaisesRegex(common.Denied,'SING_BRANCH_DRIFT:'+key):review.inspect_sing_dependency(f,p)
    def test_json_unknown_and_merge_drift_rejected(self):
        for key in ['json_unknown','json_merge','json_duplicates','json_nested']:
            path,_,anchors=review.SING_LOCI[key];f,p=self.mutated(path,anchors[-1],'deliberately_changed_source_anchor')
            with self.subTest(key=key):
                with self.assertRaisesRegex(common.Denied,'SING_BRANCH_DRIFT:'+key):review.inspect_sing_dependency(f,p)
    def test_unsafe_source_defaults_are_findings_not_security_pass(self):
        findings=review.inspect_sing_dependency(DEP_FILES,DEP_PINS)['findings']
        for finding in ['EMPTY_USERS_DISABLE_AUTH','AUTH_ERRORS_CAN_DISCLOSE_CREDENTIALS','CONNECT_200_PRECEDES_ROUTE_CALLBACK','JSON_DUPLICATES_NOT_REJECTED_BY_SEEN_KEY_GUARD']:
            self.assertIn(finding,findings)
    def test_unknown_default_and_direct_intent_never_allowed(self):
        for value in ['DIRECT','AUTO','UNKNOWN']:
            c=contract();c['routing']['default']=value
            result=broker.preflight(c,common.digest(c),broker.source_pin())
            self.assertEqual(result['profile_status'],'BROKER_PROFILE_REJECTED');self.assertFalse(result['can_apply'])
class Result(unittest.TextTestResult):
    def addSuccess(self,t):super().addSuccess(t);RESULTS.append({'id':t.id(),'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);RESULTS.append({'id':t.id(),'status':'FAIL','traceback':self._exc_info_to_string(e,t)})
    def addError(self,t,e):super().addError(t,e);RESULTS.append({'id':t.id(),'status':'ERROR','traceback':self._exc_info_to_string(e,t)})
    def addSubTest(self,t,sub,e):
        super().addSubTest(t,sub,e)
        if e:RESULTS.append({'id':t.id(),'subtest':str(sub),'status':'FAIL' if issubclass(e[0],t.failureException) else 'ERROR','traceback':self._exc_info_to_string(e,t)})
def main(dependency=False):
    global RUN,FILES,OUT,DEP_ROOT,DEP_FILES,DEP_PINS,DEP_ARCHIVE
    if dependency:
        OUT=REPO/'reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/amendment_01'
        identity=json.loads((OUT/'evidence/module_integrity.json').read_bytes())
        if identity['status']!='MODULE ZIP H1 VERIFIED / SOURCE EXTRACTED':raise RuntimeError('VERIFIED_MODULE_RECEIPT_REQUIRED')
        DEP_ROOT=Path(identity['source_root']);DEP_ARCHIVE=DEP_ROOT.parent/'sing-module-source.zip'
        DEP_FILES={n:(DEP_ROOT/n).read_bytes() for n in {'go.mod',*(v[0] for v in review.SING_LOCI.values())}}
        approved={f['path']:f['sha256'] for f in identity['files']};DEP_PINS={n:approved[n] for n in DEP_FILES}
        review.check_pins(DEP_FILES,DEP_PINS)
    RUN=OUT/'runs'/('source-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);RUN.mkdir()
    names={'go.mod','go.sum',*(v[0] for v in review.LOCI.values())};FILES={n:(ROOT/n).read_bytes() for n in names}
    source_pins={n:hashlib.sha256(raw).hexdigest() for n,raw in FILES.items()};put(RUN/'upstream_source_pins.json',source_pins)
    paths=[PKG/'singbox_source_review.py',Path(__file__).resolve(),PKG/'broker.py',PKG/'security_contract.py',PKG/'common.py',PKG/'tests/broker_suite.py'];pins={p.relative_to(REPO).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};put(RUN/'local_source_pins.json',pins)
    spec=importlib.util.spec_from_file_location('legacy_contracts',PKG/'tests/broker_suite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.OUT=RUN/'legacy';m.OUT.mkdir()
    excluded={'test_cli_always_exit20_and_output_scope','test_remote_schema_reference_is_refused_without_dial'};legacy=[n for n in unittest.defaultTestLoader.getTestCaseNames(m.ContractTests) if n not in excluded]
    suites=[unittest.defaultTestLoader.loadTestsFromTestCase(SourceTests),unittest.TestSuite(m.ContractTests(n) for n in legacy)]
    if dependency:suites.append(unittest.defaultTestLoader.loadTestsFromTestCase(DependencyTests))
    stream=io.StringIO();r=unittest.TextTestRunner(verbosity=2,stream=stream,resultclass=Result).run(unittest.TestSuite(suites))
    unchanged=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==pin for n,pin in source_pins.items()) and all(hashlib.sha256((REPO/n).read_bytes()).hexdigest()==pin for n,pin in pins.items())
    if dependency:
        unchanged=unchanged and all(hashlib.sha256((DEP_ROOT/n).read_bytes()).hexdigest()==pin for n,pin in DEP_PINS.items())
        put(RUN/'dependency_review.json',review.inspect_sing_dependency(DEP_FILES,DEP_PINS))
        put(RUN/'dependency_source_pins.json',DEP_PINS)
    exit_code=0 if r.wasSuccessful() and unchanged else 1
    put(RUN/'result.json',{'task':'CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001' if dependency else 'CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001','amendment':1,'collected':r.testsRun,'passed':sum(x['status']=='PASS' for x in RESULTS),'failed':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'source_tests':11,'dependency_source_tests':len(unittest.defaultTestLoader.getTestCaseNames(DependencyTests)) if dependency else 0,'legacy_regression':len(legacy),'tests':RESULTS,'sources_unchanged':unchanged,'engine_runs':0,'Go_build_test_runs':0,'network_tests':0,'can_apply':False,'can_start_tunnel':False,'exit_code':exit_code});(RUN/'runner.txt').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue());print('EVIDENCE '+str(RUN));return exit_code
if __name__=='__main__':
    if sys.argv[1:] not in ([],['--dependency']):raise SystemExit('Only optional --dependency is supported')
    sys.exit(main(dependency=bool(sys.argv[1:])))
