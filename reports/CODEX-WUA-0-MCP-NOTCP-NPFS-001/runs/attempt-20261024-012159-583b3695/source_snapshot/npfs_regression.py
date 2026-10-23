"""Rerun existing SDK and security selectors into the new TASK only."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
sys.dont_write_bytecode = True
PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
sys.path.insert(0, str(PKG))
import common

def main():
    root = REPO/'reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/runs'/('regression-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    root.mkdir()
    spec = importlib.util.spec_from_file_location('baseline_sdk',PKG/'tests/mcp_smoke.py')
    smoke = importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)
    mcp_root=root/'sdk';mcp_root.mkdir()
    result=asyncio.run(smoke.exercise(mcp_root))
    (root/'sdk_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    security_root=root/'security';security_root.mkdir()
    p=subprocess.run([sys.executable,'-I','-X','utf8','-B',str(PKG/'tests/test_security_routes.py'),str(security_root)],capture_output=True,text=True,env=common.clean_environment(),timeout=65)
    summary={'sdk':result['counts'],'security_exit':p.returncode,'security':json.loads((security_root/'result.json').read_text()),'stdout':p.stdout,'stderr':p.stderr}
    (root/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'evidence':str(root),'sdk':result['counts'],'security_exit':p.returncode,'security_count':summary['security']['total']}))
    return 0 if p.returncode==0 and result['counts']['failed']==0 and result['counts']['total']>0 else 1

if __name__=='__main__':
    sys.exit(main())
