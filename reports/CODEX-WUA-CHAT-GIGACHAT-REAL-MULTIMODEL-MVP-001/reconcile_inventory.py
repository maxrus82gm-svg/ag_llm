"""Explicit author reconciliation after source review; never run by acceptance.

Independent verifier reviews both the source and resulting pins. Does not
replace the original eight-site policy contract imported by S2.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
path=ROOT/'rt002_multimodel_reconciliation.json'
if not path.exists():
    path.write_text('{"pins":{},"references":{}}',encoding='utf-8')
import test_rt002_s1_routes as s1
symbols={
    'gigachat_admission.py':['require_real_authority'],
    'gigachat_transport.py':['get_access_token'],
    'gigachat_runtime.py':['ProviderSession','RealGigaChatTransport','ModelContract','LiveApproval','MODELS_URL'],
    'ordinary_chat_bridge.py':['OrdinaryCoreAdapter','_UsageCapture'],
}
result=dict(task='CODEX-WUA-CHAT-GIGACHAT-REAL-MULTIMODEL-MVP-001',pins={},references={},policy_gates={})
for module,names in symbols.items():
    file=ROOT/module if (ROOT/module).exists() else ROOT/'web_alarm'/module
    tree=ast.parse(file.read_text(encoding='utf-8'))
    nodes=dict(s1._owners(tree))
    for node in tree.body:
        if isinstance(node,ast.ClassDef):nodes[node.name]=node
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name):nodes[target.id]=node
    result['pins'][module]={n:s1._ast_hash(nodes[n]) for n in names}
    result['references'][module]=s1._recon_reference_digest(tree,module)
for module in ('web_alarm.ordinary_provider','web_alarm.ordinary_chat_bridge','web_alarm.turn_service',
               'web_alarm.ultra_chat','gigachat_admission','gigachat_runtime'):
    source=ROOT.joinpath(*module.split('.')).with_suffix('.py').read_text(encoding='utf-8')
    result['policy_gates'][module]=s1._ast_hash(ast.parse(source))
path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
for module in symbols:
    file=ROOT/module if (ROOT/module).exists() else ROOT/'web_alarm'/module
    # Re-import constants updated only in this inspection process.
    s1.RECON_PINS.setdefault(module,{}).update(result['pins'][module])
    s1.RECON_REFERENCES[module]=result['references'][module]
    found=s1.analyze_module(module,file.read_text(encoding='utf-8'))
    print(json.dumps(dict(module=module,**found),ensure_ascii=False))
