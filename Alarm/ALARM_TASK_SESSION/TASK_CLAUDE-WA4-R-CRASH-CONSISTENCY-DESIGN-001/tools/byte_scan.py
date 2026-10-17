"""Byte scan of source files: raw U+0085/U+2028/U+2029, CR bytes, non-ASCII count, in-memory compile().

compile() runs in memory only (no .pyc). Usage: byte_scan.py <file> [<file> ...]; exit 1 on any finding.
"""
import hashlib
import json
import sys
from pathlib import Path

bad = False
report = []
for name in sys.argv[1:]:
    data = Path(name).read_bytes()
    raw = {f"U+{code:04X}": data.count(chr(code).encode("utf-8")) for code in (0x85, 0x2028, 0x2029)}
    entry = {"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "raw_separators": raw,
             "cr_bytes": data.count(b"\r"), "non_ascii_bytes": sum(1 for b in data if b > 127)}
    try:
        compile(data.decode("utf-8"), name, "exec")
        entry["compile"] = "OK"
    except SyntaxError as exc:
        entry["compile"] = f"SyntaxError: {exc}"
    if any(raw.values()) or entry["cr_bytes"] or entry["compile"] != "OK":
        bad = True
    report.append(entry)
print(json.dumps(report, indent=1))
sys.exit(1 if bad else 0)
