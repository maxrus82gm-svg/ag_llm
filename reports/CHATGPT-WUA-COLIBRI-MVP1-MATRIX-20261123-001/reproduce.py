"""Rerun #665 exact 68/22/7 and matrix/negative checks; no live Manager access.

Usage: python -B reports/<TASK>/reproduce.py --colibri-repo <local_LLM>
       --local-vault <offline #664 evidence vault, optional>
Run in an isolated WUA checkout; all sensitive/raw outputs are temporary.
"""
from __future__ import annotations
import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
WUA=HERE.parents[1]
py=sys.executable
a=argparse.ArgumentParser()
a.add_argument("--colibri-repo",required=True,type=Path)
a.add_argument("--local-vault",type=Path)
args=a.parse_args()
source=WUA/"reports/CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001/reproduce.py"
with tempfile.TemporaryDirectory(prefix="wua665-evidence-") as name:
    log=Path(name)/"producer.txt"
    p=subprocess.run([py,"-B","-X","utf8",str(source),"--repo",str(args.colibri_repo)],
                     cwd=WUA,capture_output=True,encoding="utf8",errors="replace",timeout=240)
    text=p.stdout+p.stderr
    log.write_text(text,encoding="utf8")
    print("PRODUCER_INDEPENDENT",p.returncode,
          "SHA256",hashlib.sha256(text.encode("utf8")).hexdigest(),flush=True)
    if p.returncode:
        print(text[-3000:],file=sys.stderr)
        raise SystemExit(p.returncode)
    cmd=[py,"-B","-X","utf8",str(HERE/"matrix_audit.py"),
         "--wua-repo",str(WUA),"--colibri-repo",str(args.colibri_repo),
         "--producer-log",str(log)]
    if args.local_vault:
        cmd+=["--local-vault",str(args.local_vault)]
    subprocess.run(cmd,check=True,timeout=120,cwd=WUA)
    if args.local_vault:
        neg=[py,"-B","-X","utf8",str(HERE/"audit_negative.py"),
             str(args.colibri_repo),str(args.local_vault),str(log)]
        subprocess.run(neg,check=True,timeout=120,cwd=WUA)
    else:
        print("NEGATIVE_AUDIT_NOT_RUN: --local-vault omitted")
print("WUA665_REPRODUCE_OFFLINE_PASS",flush=True)
