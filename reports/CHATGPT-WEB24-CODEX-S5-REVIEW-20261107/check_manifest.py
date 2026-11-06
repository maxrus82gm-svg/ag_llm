"""Verify every published H20 manifest SHA/byte size without line-ending repair."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
manifest=root/"reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/manifest.json"
data=json.loads(manifest.read_text(encoding="utf-8"))
items=data["files"]
assert len(items)==83,(len(items),"expected 83 author entries")
errors=[]
modes={}
for e in items:
    path=(root/e["path"]).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        errors.append((e["path"],"missing or out of scope"))
        continue
    raw=path.read_bytes()
    lf=raw.replace(b"\\r\\n",b"\\n")
    crlf=lf.replace(b"\\n",b"\\r\\n")
    candidates=[("raw",raw),("checkout-LF",lf),("checkout-CRLF",crlf)]
    match=next((mode for mode,data in candidates
                if len(data)==e["size"] and hashlib.sha256(data).hexdigest()==e["sha256"]),None)
    if match is None:
        errors.append((e["path"],len(raw),hashlib.sha256(raw).hexdigest(),e["size"],e["sha256"]))
    else:
        modes[match]=modes.get(match,0)+1
print("H20_MANIFEST checked",len(items),"mismatch",len(errors),"line_modes",modes)
for error in errors[:25]:print("MANIFEST_ERROR",error)
assert not errors,"Published H20 manifest or file size differs"
