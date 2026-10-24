"""Offline structural preflight only. No process, port or account activation."""
from pathlib import Path
import argparse,datetime as dt,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from security_contract import preflight
def main():
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--pin',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    path=Path(os.path.abspath(a.profile));require(path.is_relative_to(PACKAGE/'configs') or path.is_relative_to(REPORT/'runs'),'PROFILE_SCOPE')
    # Use the same local/reparse guard for TASK-staged inputs; package templates
    # are trusted source in this offline CLI, not imported privileged settings.
    if path.is_relative_to(REPORT/'runs'):owned_path(path)
    profile=parse(path.read_bytes());result=preflight(profile,a.pin)
    result['checked_utc']=dt.datetime.now(dt.timezone.utc).isoformat();result['kind']='OFFLINE_STRUCTURAL_PREFLIGHT'
    result['states']=['TWO_WINDOWS_IDENTITIES_NOT_PROVISIONED','OS_WFP_EGRESS_NOT_VERIFIED','V2RAY_LIVE_ROUTE_NOT_VERIFIED','SECURE_TUNNEL_NOT_ACTIVATED','ORDINARY_CHATGPT_E2E_NOT_VERIFIED']
    target=Path(os.path.abspath(a.output));require(target.is_relative_to(REPORT) and target!=REPORT,'OUTPUT_SCOPE')
    with target.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print('STRUCTURAL PREFLIGHT SAVED; ALL REAL ACTIVATION BLOCKED');return 20
if __name__=='__main__':
    try:sys.exit(main())
    except (Denied,OSError,ValueError):print('BLOCKED:INPUT_OR_OUTPUT');sys.exit(20)
