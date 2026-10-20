"""Explicit local compiler invocations only, no restore/build server/network/SDK install.
All outputs and child TEMP/TMP confined to a new TASK-local attempt directory.
Python is authoring/test orchestration only. Runtime sources need .NET Framework.
"""
from pathlib import Path
import os,sys,subprocess,json,hashlib,re
OUT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    attempt=sys.argv[1];assert re.fullmatch(r'(?:attempt|mutant_port)[0-9]{2}',attempt)
    mutant=attempt.startswith('mutant_port')
    run=OUT/'evidence'/attempt;run.mkdir();(run/'temp').mkdir()
    csc=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    vcbase=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC')
    versions=sorted(p for p in vcbase.iterdir() if (p/'bin/Hostx64/x64/cl.exe').is_file());assert versions
    vc=versions[-1];cl=vc/'bin/Hostx64/x64/cl.exe'
    sdk=Path('C:/Program Files (x86)/Windows Kits/10/Include/10.0.19041.0')
    # Do not inherit CL/_CL_/CSC options, proxy/API credentials or unrelated settings.
    allowed=['SystemRoot','WINDIR','SYSTEMDRIVE','COMSPEC','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE','PROCESSOR_ARCHITEW6432']
    env={k:os.environ[k] for k in allowed if k in os.environ}
    env['PATH']=str(cl.parent)+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32')
    env['TEMP']=env['TMP']=str(run/'temp');env['VSCMD_SKIP_SENDTELEMETRY']='1'
    refs=csc.parent
    sources={p.relative_to(OUT).as_posix():sha(p) for folder in ['source','native','tests'] for p in (OUT/folder).glob('*') if p.is_file()}
    record={'mode':'local offline compilation and synthetic tests','sources':sources,'orchestrator_sha256':sha(Path(__file__)),'child_environment_keys':sorted(env),'tools':{'csc_sha256':sha(csc),'cl_sha256':sha(cl),'sdk':'10.0.19041.0','cl_version_directory':vc.name},'steps':[]}
    def call(label,args):
        try:r=subprocess.run([str(a) for a in args],cwd=run,env=env,capture_output=True,timeout=90)
        except subprocess.TimeoutExpired:
            record['steps'].append({'step':label,'status':'TIMEOUT'});return False
        raw=r.stdout+r.stderr
        # Safe diagnostics: codes + basename:line only, no raw private source/tool paths.
        text=raw.decode('utf-8',errors='replace')
        errors=re.findall(r'\b(?:error|warning|fatal error)\s+([A-Z]+[0-9]+)',text)
        if errors: (run/(label+'-diagnostics.txt')).write_text('\n'.join(errors)+'\n',encoding='ascii')
        record['steps'].append({'step':label,'exit_code':r.returncode,'diagnostic_codes':errors,'stdout_sha256':hashlib.sha256(raw).hexdigest(),'status':'PASS' if r.returncode==0 else 'FAIL'})
        return r.returncode==0
    def compile(label,target,files,references):
        args=[csc,'/nologo','/noconfig','/nostdlib+','/platform:x64','/langversion:5','/optimize+','/debug-','/warn:4','/warnaserror+','/target:'+target,'/out:'+str(run/label)]
        args+=['/r:'+str(p) for p in references];args += [OUT/f for f in files]
        return call(label,args)
    basic=[refs/'mscorlib.dll',refs/'System.dll',refs/'System.Core.dll']
    okay=compile('Wua.Wfp.Core.dll','library',['source/Core.cs'],basic)
    abi='source/Abi.cs'
    if mutant:
        original=(OUT/abi).read_text(encoding='utf-8');needle='Guard.Need(a.Value.Union.U16==b.Value.Union.U16,"U16_READBACK");'
        assert original.count(needle)==1
        variant=run/'Abi-mutant.cs';variant.write_text(original.replace(needle,'Guard.Need(true,"MUTANT_SKIPS_PORT_READBACK");'),encoding='utf-8')
        abi=variant.relative_to(OUT).as_posix()
        record['mutant']={'change':'omit native UINT16 port comparison','source':abi,'sha256':sha(variant),'expected_failed_test':'readback_rejects_wrong_port_even_same_owner_digest'}
    if okay:okay=compile('Wua.Wfp.Abi.dll','library',[abi,'source/SdkConstants.cs'],basic+[run/'Wua.Wfp.Core.dll'])
    if okay:okay=compile('Wua.Wfp.NativePreview.dll','library',['native/NativePreview.cs'],basic+[run/'Wua.Wfp.Core.dll',run/'Wua.Wfp.Abi.dll'])
    if okay:okay=compile('OfflineTests.exe','exe',['tests/OfflineTests.cs'],basic+[run/'Wua.Wfp.Core.dll',run/'Wua.Wfp.Abi.dll'])
    # C++ uses static_assert/offsetof only, /Zs compiles syntax with no executable/link/API.
    cpp=call('SDK-ABI-static-assert',[cl,'/nologo','/Zs','/std:c++14','/D_WIN64','/I'+str(vc/'include'),'/I'+str(sdk/'ucrt'),'/I'+str(sdk/'shared'),'/I'+str(sdk/'um'),OUT/'tests/abi_static.cpp'])
    if okay:
        okay=call('managed-selftest',[run/'OfflineTests.exe','selftest',run/'results.json'])
        if mutant and (run/'results.json').is_file():
            results=json.loads((run/'results.json').read_text(encoding='utf-8'))
            bad=[t['name'] for t in results['tests'] if t['status']=='FAIL']
            killed=bad==[record['mutant']['expected_failed_test']]
            record['mutant']['killed_by_expected_test']=killed
            record['steps'][-1]['expected_exit_code']=1
            record['steps'][-1]['status']='PASS_EXPECTED_MUTANT_KILLED' if killed and record['steps'][-1].get('exit_code')==1 else 'FAIL'
            okay=killed
        call('unknown-command-blocked',[run/'OfflineTests.exe','apply'])
        record['steps'][-1]['expected_exit_code']=20
        record['steps'][-1]['status']='PASS' if record['steps'][-1].get('exit_code')==20 else 'FAIL'
    record['source_pins_unchanged']=all(sha(OUT/p)==h for p,h in sources.items())
    record['compiled_outputs']=[{'ref':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in run.glob('*') if p.suffix in ('.exe','.dll')]
    record['native_preview_execution']='NOT LOADED; reflection-only metadata in synthetic tests'
    record['actual_WFP_API_calls']=0;record['network_probes']=0
    (run/'build.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'attempt':attempt,'steps':record['steps'],'source_pins_unchanged':record['source_pins_unchanged']}))
    return 0 if okay and cpp and record['source_pins_unchanged'] and all(s['status'].startswith('PASS') for s in record['steps']) else 1
if __name__=='__main__':sys.exit(main())
