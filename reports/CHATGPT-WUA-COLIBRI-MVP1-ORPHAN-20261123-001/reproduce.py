"""Run from WUA tree. Read-only local producer Git object; isolated TEMP only."""
import argparse, hashlib, subprocess, tempfile, sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--repo",required=True,type=Path)
a=p.parse_args()
root=Path(__file__).resolve().parents[2]
rev="883d91d4ad2e47fc260bfd7b1e61d230f8fb99ea"
contract="2d9e7f6fb860fdd53747f4ba75350d15bab27877"
def git(*args):return subprocess.check_output(["git","-C",str(a.repo),*args])
with tempfile.TemporaryDirectory(prefix="wua-colibri-review-") as td:
 d=Path(td);count=0
 for raw in git("ls-tree","-r","--name-only","-z",rev,"--","Client_Ultra_LLM","Contracts/ClientBridge/v1").split(b"\0"):
  if not raw:continue
  f=raw.decode("utf-8")
  if not(f.startswith("Contracts/") or f.endswith((".py",".md",".json",".js",".html",".css",".txt"))):continue
  data=git("show",rev+":"+f);out=d/f;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
  blob=git("rev-parse",rev+":"+f).decode().strip()
  assert hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()==blob
  if f.startswith("Contracts/"):assert git("rev-parse",contract+":"+f).decode().strip()==blob
  count+=1
 print("EXACT PRODUCER BLOBS",count,flush=True)
 py=[sys.executable,"-B","-X","utf8"]
 subprocess.run(py+[str(Path(__file__).with_name("recovery.py")),"--producer-source",str(d)],cwd=root,check=True,timeout=240)
