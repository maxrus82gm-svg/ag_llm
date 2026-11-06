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
for e in items:
    path=(root/e["path"]).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        errors.append((e["path"],"missing or out of scope"))
        continue
    raw=path.read_bytes()
    if len(raw)!=e["size"] or hashlib.sha256(raw).hexdigest()!=e["sha256"]:
        errors.append((e["path"],len(raw),hashlib.sha256(raw).hexdigest(),e["size"],e["sha256"]))
print("H20_MANIFEST checked",len(items),"mismatch",len(errors))
for error in errors[:25]:print("MANIFEST_ERROR",error)
assert not errors,"Published H20 manifest or file size differs"
