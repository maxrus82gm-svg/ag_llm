"""Explicit H34 source reconciliation. Never a runtime/test acceptance bypass.

Updates only reviewed H33 HTTP and H34 server-gateway nodes/census, plus the exact
new S2 ingress hash. Unknown consumers, endpoint reads and factories still fail.
"""
import ast, hashlib, json, pprint, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import test_rt002_s1_routes as s1
p=ROOT/'test_rt002_s1_routes.py';source=p.read_text();tree=ast.parse(source)
pins=dict(s1.RECON_PINS);refs=dict(s1.RECON_REFERENCES);old={}
for name in ['ordinary_gigachat_transport.py','gigachat_admission.py']:
    old[name]=pins.get(name)
    t=ast.parse((ROOT/name).read_text());nodes=dict(s1._owners(t))
    nodes.update({n.name:n for n in t.body if isinstance(n,ast.ClassDef)})
    for n in t.body:
        if isinstance(n,ast.Assign):
            for target in n.targets:
                if isinstance(target,ast.Name):nodes[target.id]=n
    keys=list(pins[name]) if name in pins else [n.name for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]+['_OWNER','_ROUTES','_VERSION']
    pins[name]={k:s1._ast_hash(nodes[k]) for k in keys};refs[name]=s1._recon_reference_digest(t,name)
edits=[]
for n in tree.body:
    if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('RECON_PINS','RECON_REFERENCES'):
        name=n.targets[0].id;value=pins if name=='RECON_PINS' else refs
        edits.append((n.lineno-1,n.end_lineno,name+' = '+pprint.pformat(value,width=110,sort_dicts=False)+'\n'))
lines=source.splitlines(keepends=True)
for start,end,text in sorted(edits,reverse=True):lines[start:end]=[text]
p.write_text(''.join(lines),encoding='utf-8')
p=ROOT/'test_rt002_s2_budget_policy.py';source=p.read_text();tree=ast.parse(source)
n=next(n for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='OFFLINE_ADMISSION_GATES')
gates=ast.literal_eval(n.value)
gates['gigachat_admission']=hashlib.sha256(ast.dump(ast.parse((ROOT/'gigachat_admission.py').read_text()),include_attributes=False).encode()).hexdigest()
lines=source.splitlines(keepends=True);lines[n.lineno-1:n.end_lineno]=['OFFLINE_ADMISSION_GATES = '+pprint.pformat(gates,width=110,sort_dicts=False)+'\n']
p.write_text(''.join(lines),encoding='utf-8')
Path(__file__).with_name('evidence').joinpath('reconciled_pins.json').write_text(json.dumps(dict(reviewed_before=old,
    reviewed_after={k:pins[k] for k in old},references={k:refs[k] for k in old},s2_gates=gates),indent=2))
print('H34 exact pin/census reconciliation written; all production graph nodes remain scanned')
