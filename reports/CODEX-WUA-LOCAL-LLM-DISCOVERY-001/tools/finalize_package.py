"""Verify evidence and unchanged project inputs, then hash this report-only package."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001'
def sha(b):return hashlib.sha256(b).hexdigest()
def load(n):return json.loads((WORK/n).read_text(encoding='utf-8-sig'))
def dump(n,obj):(WORK/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def verify():
    checks=[]
    def check(n,ok,d=None):checks.append({'name':n,'pass':bool(ok),'detail':d})
    required=['report.md','host-inventory.md','provider-api-matrix.md','ultra-source-map.md','multi-provider-contract.md','blueprint-integration.md','test-plan.md','next-task-proposal.md','server-side-checklist.md']
    check('all required review documents nonempty',all((WORK/n).is_file() and (WORK/n).stat().st_size>500 for n in required))
    base=load('evidence/source_baseline.json')['files']
    drift=[x['path'] for x in base if not (ROOT/x['path']).is_file() or sha((ROOT/x['path']).read_bytes())!=x['sha256']]
    check('all 248 recorded project inputs unchanged',not drift,{'count':len(base),'drift':drift})
    rules=load('evidence/rule_scope.json')['definitions']
    check('direct rules and requires extracted',all(v['status']=='EXTRACTED' for v in rules.values()),{'rules':len(rules)})
    calls=load('evidence/http_inventory.json')
    allowed={'http://127.0.0.1:11434/api/version','http://127.0.0.1:11434/api/tags','http://127.0.0.1:11434/api/ps','http://127.0.0.1:11434/v1/models','http://127.0.0.1:8000/health','http://127.0.0.1:8000/v1/models','http://127.0.0.1:8000/openapi.json','http://192.168.0.77:8000/health','http://192.168.0.77:8000/v1/models','http://192.168.0.77:8000/openapi.json'}
    check('exact ten allowlisted explicit HTTP probes',len(calls)==10 and {c['url'] for c in calls}==allowed)
    check('GET-only, no proxy/redirect/auth, bounded timeout and response',all(c['method']=='GET' and c['proxy'] is False and c['redirects'] is False and c['auth_sent'] is False and c['timeout_seconds']==2 and not c.get('truncated',False) for c in calls))
    native=[c for c in calls if ':11434/' in c['url']]
    check('four local inventory methods returned 200',all(c.get('status')==200 for c in native) and len(native)==4)
    tags=next(c['data'] for c in native if c['url'].endswith('/api/tags'))
    ps=next(c['data'] for c in native if c['url'].endswith('/api/ps'))
    check('installed versus loaded distinction evidenced',len(tags['models'])==1 and tags['models'][0]['name']=='deepseek-r1:8b' and ps['models']==[])
    check('version evidence pinned',next(c['data'] for c in native if c['url'].endswith('/api/version'))['version']=='0.40.13')
    check('remote host failures preserved, not converted to empty catalog',all(c.get('error_type')=='URLError' and 'status' not in c and 'data' not in c for c in calls if '192.168.0.77' in c['url']))
    check('local 8000 disconnect preserved',all(c.get('error_type')=='RemoteDisconnected' and 'status' not in c for c in calls if '127.0.0.1:8000' in c['url']))
    host=load('evidence/host_inventory.json')
    check('diagnostic host distinct from target',any(x['IPAddress']=='192.168.0.9' for x in host['ipv4']) and not any(x['IPAddress']=='192.168.0.77' for x in host['ipv4']))
    check('Ollama loopback listener evidenced',any(x['LocalAddress']=='127.0.0.1' and x['LocalPort']==11434 for x in host['listeners']))
    check('8000 observed process not relabeled Colibri',any(x['Pid']==5156 and x['Name']=='Manager.exe' for x in host['processes']))
    unknown_secrets=[];new_graph=[]
    for p in WORK.rglob('*'):
        if not p.is_file() or p.name=='manifest.json' or p.suffix not in ['.md','.txt','.json','.py','.ps1']:continue
        t=p.read_text(encoding='utf-8-sig')
        if re.search(r'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',t):unknown_secrets.append(p.name)
        if p.suffix=='.md' and re.search(r'!?\[\[[^\]]+\]\]',t):new_graph.append(p.name)
    check('publication JWT-pattern scan',not unknown_secrets,{'findings':unknown_secrets,'limit':'No heuristic scanner proves absence of every possible secret; collectors use whitelisted fields and no secret reads.'})
    check('authored Markdown has no Wiki edges',not new_graph,new_graph)
    check('draft engineering proposal is unassigned',all(x in (WORK/'next-task-proposal.md').read_text(encoding='utf-8') for x in ['DRAFT PROPOSAL','NOT ASSIGNED','USER GO REQUIRED']))
    out={'task':'CODEX-WUA-LOCAL-LLM-DISCOVERY-001','classification':'AUTHOR PACKAGE/EVIDENCE CHECKS, NOT ADAPTER E2E OR INDEPENDENT VERDICT','passed':sum(c['pass'] for c in checks),'failed':sum(not c['pass'] for c in checks),'checks':checks}
    dump('evidence/package_checks.json',out)
    print(json.dumps({'passed':out['passed'],'failed':out['failed'],'failures':[c for c in checks if not c['pass']]},ensure_ascii=False))
    assert out['failed']==0

def manifest():
    receipt=WORK/'handoff_receipt.json'
    if receipt.exists():
        sent=load('handoff_receipt.json')['payload'];raw=(ROOT/sent['path']).read_bytes()
        assert sha(raw)==sent['sha256'] and len(raw)==sent['bytes'] and len(raw.decode('utf-8'))==sent['chars'], 'Transmitted packet changed'
    paths=sorted(p for p in WORK.rglob('*') if p.is_file() and p!=WORK/'manifest.json' and '__pycache__' not in p.parts)
    entries=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths]
    dump('manifest.json',{'task':'CODEX-WUA-LOCAL-LLM-DISCOVERY-001','status':'RESULT READY / PARTIAL DIAGNOSTICS / AWAITING INDEPENDENT VERIFICATION','path_base':'M:/GitHub/ag_llm','self_excluded':True,'entries':entries})
    for e in entries:
        raw=(ROOT/e['path']).read_bytes();assert len(raw)==e['bytes'] and sha(raw)==e['sha256']
    print(json.dumps({'manifest_entries_verified':len(entries),'source_baseline_ref':'evidence/source_baseline.json; production inputs listed but not copied into manifest'}))

if __name__=='__main__':
    verify()
    if len(sys.argv)<2 or sys.argv[1]=='finalize':manifest()
