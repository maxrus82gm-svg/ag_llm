"""Write manifest.json for this TASK folder: every file (except the manifest) with bytes, SHA-256 and EOL.

A file with any CR byte refuses the manifest (exit 1): the publication path converts CRLF to LF, so a CRLF file's
SHA-256 could never match its published blob. Relative paths only. Usage: make_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
TASK = "CLAUDE-WA4-R-TOCTOU-RACE-REVIEW-001"


def entry(path: Path) -> dict:
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    eol = "NONE" if not (crlf or lf) else "CRLF" if crlf and not lf else "LF" if lf and not crlf else "MIXED"
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


files = {p.relative_to(TASK_DIR).as_posix(): entry(p) for p in sorted(TASK_DIR.rglob("*"))
         if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
with_cr = sorted(rel for rel in files if b"\r" in (TASK_DIR / rel).read_bytes())
if with_cr:
    print(json.dumps({"refused": "files with CR bytes (publish LF only)", "first": with_cr[:5]}))
    sys.exit(1)
manifest = {
    "task": TASK, "status": "BLOCKED (TOCTOU analysis direction); NO PRODUCTION CHANGE",
    "publication": "LOCAL ONLY / NOT SYNCED", "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_changed": {}, "card_and_001": "not changed (coordinator owns closeout)",
    "tests": "NOT RUN", "files": files,
}
(TASK_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                        newline="\n")
print(json.dumps({"files": len(files)}))
