"""Final source pins and bounded handoff/privacy review, not a whole-host attestation."""
from pathlib import Path
import hashlib,json,re,sys
OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(ref):return json.loads((OUT/ref).read_text(encoding='utf-8-sig'))
def save(ref,obj):
    with (OUT/ref).open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def source(final_release=False):
    attempt='attempt05' if final_release else 'attempt04';mutant_ref='mutant_port04' if final_release else 'mutant_port03';count=62 if final_release else 61
    final=load('evidence/'+attempt+'/build.json');results=load('evidence/'+attempt+'/results.json')
    assert results['total']==results['passed']==count and results['failed']==0
    assert all(sha(OUT/p)==h for p,h in final['sources'].items())
    assert all(s['status']=='PASS' for s in final['steps'])
    mutant=load('evidence/'+mutant_ref+'/results.json');build=load('evidence/'+mutant_ref+'/build.json')
    assert mutant['total']==count and mutant['failed']==1 and build['mutant']['killed_by_expected_test']
    for p in ['source/Core.cs','source/Abi.cs','source/SdkConstants.cs']:
        text=(OUT/p).read_text(encoding='utf-8');assert 'DllImport(' not in text and 'Process.Start' not in text and 'System.Net' not in text
    native=(OUT/'native/NativePreview.cs').read_text(encoding='utf-8')
    assert native.count('[DllImport(')==15 and 'internal sealed class LabSourceSession' in native
    prior=ROOT/'reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/toolkit/WuaMcp.psm1'
    assert '$script:BackendImplemented=$false' in prior.read_text(encoding='utf-8').replace(' ','')
    cpp=(OUT/'tests/abi_static.cpp').read_text();assertions=cpp.count('static_assert(')
    save('checks_final.json' if final_release else 'checks.json',{
        'task_id':OUT.name,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION',
        'final_managed_suite':{'passed':count,'failed':0,'total':count,'source':'evidence/'+attempt+'/','source_pins_current':True,'oracle_points_in_one_case':73728,'policy_mutants_killed':7},
        'compiled_readback_mutant':{'tests':count,'pass':count-1,'expected_FAIL':1,'killed':True,'source':'evidence/'+mutant_ref+'/','meaning':'Port-check omission detected, not unresolved product failure'},
        'build':{'managed_outputs':4,'compiler_errors':0,'warnings':0,'x64':True,'language':'C#5','target':'.NET Framework 4.5+ on Windows x64','SDK_versions_read':3,'SDK_headers_hashed':9,'native_prototypes':15,'Cxx_compile_only_static_asserts':assertions},
        'previous_toolkit_gate':load('evidence/previous_toolkit_guard.json'),
        'boundary':{'native_preview_exports':0,'native_preview_executable_entrypoints':0,'current_runtime_references_to_native_preview':0,'runtime_PInvoke_declarations':0,'preview_PInvoke_declarations':15,'CanApply':False,'old_toolkit_changed':False,'native_preview_loading':'reflection-only metadata, no execution load or WFP imports resolved'},
        'limitations':['Pointers in Readback are trusted owned/OS memory, not arbitrary user input','Headers/ABI/managed tests do not prove ALE condition support, arbitration, boot, loopback, DNS or WFP enforcement','Provenance/ledger/hash is not authenticated local SID/host ownership','Native stage/readback preview compiled but never called; native rollback deletion is BLOCKED','No Windows/network operational probes or host-wide no-traffic attestation'],
        'NATIVE_WFP_ENFORCEMENT':'NOT RUN / NOT VERIFIED','REAL_HOST_SECURITY':'NOT VERIFIED','V2RAY_REMOTE_ROUTE':'NOT VERIFIED','ORDINARY_CHAT_MCP_E2E':'NOT VERIFIED','HOSTED_TUNNEL':'NOT STARTED',
        'native_WFP_calls':0,'account_acl_rights_firewall_changes':0,'network_probes':0,'Git_GitHub_operations':0,
        'independent_verifier':'WEB_11 / PENDING','publication':'LOCAL ONLY / NOT VERIFIED'
    })
    print(json.dumps({'current_sources':len(final['sources']),'suite':str(count)+'/'+str(count),'compiled_mutant':str(count-1)+' PASS / 1 EXPECTED FAIL','Cxx_static_asserts':assertions}))
def privacy():
    issues=[];binary=[];text_count=0
    for p in OUT.rglob('*'):
        if not p.is_file():continue
        ref=p.relative_to(OUT).as_posix();b=p.read_bytes()
        if p.suffix in ('.exe','.dll'):
            binary.append({'ref':ref,'sha256':sha(p),'debug':'debug- build; no source PDB generated'});continue
        try:t=b.decode('utf-8-sig')
        except UnicodeDecodeError:issues.append({'ref':ref,'code':'NON_UTF8_UNREVIEWED'});continue
        text_count+=1
        for code,pattern in [('USER_PATH',r'(?i)[a-z]:[\\/]+Users[\\/]+(?!PRIVATE_PERSON\b)[^\\/\s]+'),('MACHINE',r'\bDESKTOP-[A-Z0-9]{5,}\b'),('TOKEN',r'\bsk-[A-Za-z0-9_-]{24,}|\bBearer\s+[A-Za-z0-9._-]{20,}')]:
            if re.search(pattern,t):issues.append({'ref':ref,'code':code})
        # Complete SIDs are permitted only in the clearly synthetic test source or mutant source.
        if re.search(r'\bS-1-5-21-\d+-\d+-\d+-\d+\b',t) and ref!='tests/OfflineTests.cs':issues.append({'ref':ref,'code':'SID_REVIEW_REQUIRED'})
    assert not issues,json.dumps(issues)
    save('privacy_review.json',{'text_files_reviewed':text_count,'binary_files':binary,'findings':[],'scope':'Bounded token/user/machine patterns, synthetic SID provenance, manual address/config review; no universal secret-detector claim','raw_historic_card_copied':False,'secret_configs_read':False,'source_and_evidence_only_real_identifiers':'none identified','compiled_artifacts':'not production/installable; NativePreview remains inactive, no exported public types'})
    print(json.dumps({'text_files':text_count,'compiled_binaries':len(binary),'findings':0}))
if __name__=='__main__':{'source':source,'source-final':lambda:source(True),'privacy':privacy}[sys.argv[1]]()
