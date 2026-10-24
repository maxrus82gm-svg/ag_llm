"""Existing pure validators only. No sing-box source or runtime is tested."""
from pathlib import Path
import hashlib,importlib.util,io,json,sys,time,unittest,uuid
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;REPO=OUT.parents[1];PKG=REPO/'integrations/wua_chatgpt_mcp'
def guard(event,args):
    if event.startswith('socket.') or event in ['subprocess.Popen','os.system','os.posix_spawn']:
        raise PermissionError('PURE_OFFLINE_NO_NETWORK_OR_CHILD')
sys.addaudithook(guard)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    run=OUT/'runs'/('pure-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);run.mkdir()
    paths=[PKG/n for n in ['common.py','broker.py','broker_fixture.py','security_contract.py','route_simulation.py','configs/broker.v1.schema.json','configs/broker.v1.synthetic.example.json','tests/broker_suite.py']]
    pins={p.relative_to(REPO).as_posix():sha(p) for p in paths};put(run/'source_pins.json',pins)
    spec=importlib.util.spec_from_file_location('existing_broker_contracts',PKG/'tests/broker_suite.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.OUT=run
    excluded={'test_cli_always_exit20_and_output_scope','test_remote_schema_reference_is_refused_without_dial'}
    names=[n for n in unittest.defaultTestLoader.getTestCaseNames(module.ContractTests) if n not in excluded]
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=module.Result).run(unittest.TestSuite(module.ContractTests(n) for n in names))
    unchanged=all(sha(REPO/p)==v for p,v in pins.items())
    facts={'task':OUT.name,'status':'BLOCKED / SOURCE_BUNDLE_REQUIRED','existing_pure_validator_regression':{'collected':result.testsRun,'passed':sum(x['status']=='PASS' for x in module.RESULTS),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'tests':module.RESULTS,'source_pins_current':unchanged},'source_specific_tests':{'collected':0,'status':'NOT RUN / SOURCE_BUNDLE_REQUIRED'},'source_route_mutations':{'executed':0,'status':'NOT RUN / SOURCE_BUNDLE_REQUIRED'},'native_engine_runs':0,'native_network_tests':0,'Git_GitHub_operations':0,'can_apply':False,'can_start_tunnel':False,'excluded_nonpure_selectors':sorted(excluded),'run':run.relative_to(OUT).as_posix()}
    put(run/'result.json',facts);put(OUT/'test_results.json',facts);(run/'runner.txt').write_text(stream.getvalue(),encoding='utf-8')
    print(json.dumps({'run':facts['run'],'regression':{k:facts['existing_pure_validator_regression'][k] for k in ['collected','passed','failed','errors','skipped']},'source_tests':0,'source_mutations':0,'source_pins_current':unchanged}))
    return 0 if result.wasSuccessful() and result.testsRun and unchanged else 1
if __name__=='__main__':sys.exit(main())
