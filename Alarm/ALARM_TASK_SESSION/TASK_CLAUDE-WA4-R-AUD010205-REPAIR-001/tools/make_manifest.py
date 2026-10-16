"""manifest.json for CLAUDE-WA4-R-AUD010205-REPAIR-001: every file of this TASK folder (manifest excluded)
plus the changed/new repository files with bytes, SHA-256 and line endings. Read-only elsewhere."""
import hashlib
import json
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
REPO_FILES = ["web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py", "web_alarm/projection.py",
              "test_web_alarm_aud010205_repair.py"]


def entry(path: Path) -> dict:
    data = path.read_bytes()
    eol = "NONE" if b"\n" not in data else ("CRLF" if data.count(b"\r\n") == data.count(b"\n") else
                                            ("LF" if b"\r\n" not in data else "MIXED"))
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


manifest = {
    "task": "CLAUDE-WA4-R-AUD010205-REPAIR-001",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001",
    "self_hash": "EXCLUDED (reported in the chat handoff)",
    "files": {p.relative_to(HERE).as_posix(): entry(p) for p in sorted(HERE.rglob("*"))
              if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts},
    "repository_files": {name: entry(REPO / name) for name in REPO_FILES},
}
(HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                    newline="\n")
print(len(manifest["files"]), "task files;", len(manifest["repository_files"]), "repository files")
