"""Byte-exact legacy regression in this TASK's disposable mirror.

Legacy runners have fixed report roots. A small source mirror keeps those paths
inside this TASK without modifying NPFS/common code or historical evidence.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
sys.dont_write_bytecode=True
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1]
OUT=REPO/'reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    root=OUT/'runs'/('regression-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);root.mkdir()
    stage=root/'mirror';dest=stage/'integrations/wua_chatgpt_mcp';(dest/'tests').mkdir(parents=True)
    names=['common.py','server.py','api_channel.py','api_fixture.py','security_contract.py','route_simulation.py','reference_connect.py','diagnostics.py','tests/mcp_smoke.py','tests/test_security_routes.py','tests/run_suite.py']
    copies=[(PKG/name,dest/name) for name in names]
    copies += [(p,stage/p.relative_to(REPO)) for p in (REPO/'web_alarm').rglob('*.py') if '__pycache__' not in p.parts]
    pins=[]
    for source,target in copies:
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());assert sha(source)==sha(target)
        pins.append({'original':source.relative_to(REPO).as_posix(),'snapshot':target.relative_to(REPO).as_posix(),'bytes':source.stat().st_size,'sha256':sha(source)})
    (root/'source_pins.json').write_text(json.dumps(pins,indent=2),encoding='utf-8')
    env={k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ}
    runs=[]
    for label in ['mcp01','security01']:
        p=subprocess.run([sys.executable,'-I','-X','utf8','-B',str(dest/'tests/run_suite.py'),label],capture_output=True,text=True,env=env,timeout=75)
        runs.append({'selector':label,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    expected=stage/'reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001/runs'
    summary={'task':'CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001','staged_files':len(pins),'runs':runs,'original_sources_unchanged':all(sha(REPO/x['original'])==x['sha256'] for x in pins)}
    for label in ['mcp01','security01']:
        p=expected/label/'run_meta.json'
        if p.exists():summary[label]=json.loads(p.read_text())['counts']
    (root/'result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(root),'runs':[{'selector':x['selector'],'exit':x['exit']} for x in runs],'mcp':summary.get('mcp01'),'security':summary.get('security01')}))
    return 0 if all(x['exit']==0 for x in runs) and summary['original_sources_unchanged'] else 1
if __name__=='__main__':sys.exit(main())
