"""Write manifest.json for this TASK folder plus the changed repository files and the read-only Ultra core files.

Every file of the folder (except the manifest) with bytes, SHA-256 and EOL; a CR byte in a folder file refuses the
manifest (exit 1: published copies are LF). Changed repository files carry the working-copy SHA-256 and the
LF-normalised SHA-256 (what a published blob has). Read-only Ultra core files are listed with their SHA-256 so a
verifier can confirm this TASK left them as they are on the published base. Relative paths only.
Usage: make_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
TASK = "CLAUDE-WUA-1-EVM-CONNECTIONS-001"
CHANGED = {"web_alarm/ui.py": "modified", "web_alarm/server.py": "modified", "web_alarm/ultra_connections.py": "new",
           "test_web_alarm_ultra_connections.py": "new", "test_web_alarm_evm_ui.js": "new"}
READ_ONLY = ("model_registry.py", "gigachat_transport.py", "ultra_ui.py", "server.py", "ui_state.py")
sha = lambda data: hashlib.sha256(data).hexdigest()


def entry(path: Path) -> dict:
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    eol = "NONE" if not (crlf or lf) else "CRLF" if crlf and not lf else "LF" if lf and not crlf else "MIXED"
    return {"bytes": len(data), "sha256": sha(data), "eol": eol}


files = {p.relative_to(TASK_DIR).as_posix(): entry(p) for p in sorted(TASK_DIR.rglob("*"))
         if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
with_cr = sorted(rel for rel in files if b"\r" in (TASK_DIR / rel).read_bytes())
if with_cr:
    print(json.dumps({"refused": "files with CR bytes (publish LF only)", "first": with_cr[:5]}))
    sys.exit(1)
baseline = json.loads((TASK_DIR / "source-baseline.json").read_text(encoding="utf-8"))["sha256"]
changed = {}
for rel, kind in CHANGED.items():
    data = (REPO / rel).read_bytes()
    changed[rel] = entry(REPO / rel) | {"kind": kind, "sha256_lf_normalized": sha(data.replace(b"\r\n", b"\n")),
                                        "sha256_before_task": baseline.get(rel)}
manifest = {
    "task": TASK, "title": "Web Alarm Ultra — первый веб-интерфейс подключений (вкладка EVM)",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION", "publication": "LOCAL ONLY / NOT SYNCED",
    "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_changed": changed,
    "read_only_ultra_core": {rel: entry(REPO / rel) for rel in READ_ONLY},
    "card_and_001": "not changed (coordinator owns closeout, DOC-TASK-CLOSEOUT-OWNER-01@1)",
    "not_published_private": "raw runner outputs stay in disposable TEMP; published copies only via "
                             "web_alarm.evidence_sanitizer (runs/runs-map.json)",
    "files": files,
}
(TASK_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                        newline="\n")
print(json.dumps({"files": len(files), "changed": {k: v["sha256"][:16] for k, v in changed.items()}}))
