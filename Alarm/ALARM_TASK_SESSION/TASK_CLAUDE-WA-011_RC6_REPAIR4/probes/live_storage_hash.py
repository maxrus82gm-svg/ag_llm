"""Read-only fingerprint of the live storage (%LOCALAPPDATA%\\WebAlarmWorkspace).

Usage: python -B live_storage_hash.py <label>
Prints file/dir counts and one SHA-256 over (relative path, content SHA-256)
pairs. Opens files for reading only; never writes into the storage.
"""
import hashlib
import os
import sys
from pathlib import Path

root = Path(os.environ["LOCALAPPDATA"]) / "WebAlarmWorkspace"
files, dirs = [], 0
for path in sorted(root.rglob("*")):
    if path.is_dir():
        dirs += 1
    elif path.is_file():
        files.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
combined = hashlib.sha256("\n".join(f"{name} {digest}" for name, digest in files).encode("utf-8")).hexdigest()
print(f"{sys.argv[1] if len(sys.argv) > 1 else 'snapshot'}: files={len(files)} dirs={dirs} sha256={combined}")
