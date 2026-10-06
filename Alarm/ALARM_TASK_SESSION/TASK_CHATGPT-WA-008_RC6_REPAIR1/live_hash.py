import hashlib
from pathlib import Path
from web_alarm.workspace_registry import default_storage_root

root = default_storage_root()
if not root.is_dir():
    print(f"ROOT={root}")
    print("MISSING")
    raise SystemExit(2)

files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix())
dirs = sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: p.relative_to(root).as_posix())
tree = hashlib.sha256()
for path in files:
    rel = path.relative_to(root).as_posix()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    tree.update(rel.encode("utf-8"))
    tree.update(b"\0")
    tree.update(str(len(data)).encode("ascii"))
    tree.update(b"\0")
    tree.update(digest.encode("ascii"))
    tree.update(b"\n")
print(f"ROOT={root}")
print(f"FILES={len(files)}")
print(f"DIRS={len(dirs)}")
print(f"SHA256={tree.hexdigest()}")
