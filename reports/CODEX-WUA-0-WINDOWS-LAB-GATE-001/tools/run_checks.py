"""Bounded offline compiler/tests. New attempt output only; no install/VM/network."""
from pathlib import Path
import ast,datetime as dt,hashlib,json,os,re,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    name=sys.argv[1];assert re.fullmatch(r'(?:attempt|mutant_nic|mutant_trust)[0-9]{2}',name)
    out=ROOT/'evidence'/name;out.mkdir(parents=True);(out/'temp').mkdir()
    source={p.relative_to(ROOT).as_posix():sha(p) for folder in ['source','adapters','tests','tools'] for p in (ROOT/folder).glob('*') if p.is_file()}
    for folder in ['source','tests','tools']:
        for p in (ROOT/folder).glob('*.py'):ast.parse(p.read_bytes())
    env={k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ};env['TEMP']=env['TMP']=str(out/'temp')
    compiler=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe';base=compiler.parent;helper=out/'Signatures.exe'
    args=[str(compiler),'/nologo','/noconfig','/nostdlib+','/platform:x64','/langversion:5','/optimize+','/debug-','/warnaserror+','/target:exe','/out:'+str(helper)]+['/r:'+str(base/x) for x in ['mscorlib.dll','System.dll','System.Core.dll','System.Web.Extensions.dll']]+[str(ROOT/'source/Signatures.cs')]
    c=subprocess.run(args,cwd=out,env=env,capture_output=True,timeout=25)
    record={'source_pins':source,'compiler_sha256':sha(compiler),'compile_exit':c.returncode,'compile_diagnostic_codes':re.findall(r'\bCS[0-9]+',c.stdout.decode('utf-8',errors='replace')+c.stderr.decode('utf-8',errors='replace')),'python_syntax':'PASS','child_environment_keys':sorted(env),'steps':[]}
    if c.returncode!=0:
        (out/'run.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record));return 1
    test=ROOT/'tests/test_gate.py';expected=None
    if name.startswith('mutant'):
        clone=out/'mutant_package';(clone/'source').mkdir(parents=True);(clone/'tests').mkdir()
        original=(ROOT/'source/lab_gate.py').read_text(encoding='utf-8')
        if name.startswith('mutant_nic'):
            needle='if f[k]!=v:';replacement="if f[k]!=v and k!='nic_count':";expected=['test_even_disabled_NIC_fails','test_signed_negative_fact_dominates_missing_review']
        else:
            needle="need(synthetic or not t['test_only'],'TEST_TRUST_IN_REAL_MODE')";replacement="need(True,'MUTANT_ACCEPTS_TEST_TRUST')";expected=['test_real_mode_rejects_synthetic_trust']
        assert original.count(needle)==1
        (clone/'source/lab_gate.py').write_text(original.replace(needle,replacement),encoding='utf-8')
        shutil.copyfile(test,clone/'tests/test_gate.py');test=clone/'tests/test_gate.py'
    results=out/'tests';results.mkdir()
    started=time.monotonic();p=subprocess.run([sys.executable,'-B',str(test),str(helper),str(results)],cwd=out,env=env,capture_output=True,timeout=100)
    record['elapsed_seconds']=round(time.monotonic()-started,3);record['test_exit']=p.returncode
    record['stdout_sha256']=hashlib.sha256(p.stdout+p.stderr).hexdigest()
    if (results/'results.json').is_file():
        r=json.loads((results/'results.json').read_text(encoding='utf-8'));bad=[x['name'] for x in r['tests'] if x['status']!='PASS'];record['test_counts']={k:r[k] for k in ['total','passed','failed','errors']}
        record['expected_mutant_failure']=expected;record['mutant_killed']=expected is not None and bad==expected and p.returncode==1
    else:
        record['test_counts']='NOT PRODUCED';record['diagnostic_tail']=(p.stderr.decode('utf-8',errors='replace')[-1200:]).replace(str(ROOT),'<TASK>').replace(str(out),'<RUN>')
    record['sources_unchanged']=all(sha(ROOT/ref)==h for ref,h in source.items());record['helper_sha256']=sha(helper);record['vm_changes']=record['WFP_calls']=record['network_probes']=0
    (out/'run.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record))
    return 0 if record['sources_unchanged'] and ((expected and record.get('mutant_killed')) or (not expected and p.returncode==0)) else 1
if __name__=='__main__':sys.exit(main())
