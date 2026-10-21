"""Write manifest.json for this TASK folder: every file (except the manifest) with bytes, SHA-256 and EOL, plus the
two new repository files and the card. Relative paths only; the repository root comes from this file's location.
Usage: make_manifest.py
"""
import hashlib
import json
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
TASK = "CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001"


def entry(path: Path) -> dict:
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    eol = "NONE" if not (crlf or lf) else "CRLF" if crlf and not lf else "LF" if lf and not crlf else "MIXED"
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


files = {p.relative_to(TASK_DIR).as_posix(): entry(p) for p in sorted(TASK_DIR.rglob("*"))
         if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
repo_files = {rel: entry(REPO / rel) | {"kind": "new", "lines": (REPO / rel).read_bytes().count(b"\n")}
              for rel in ("web_alarm/evidence_sanitizer.py", "test_web_alarm_evidence_sanitizer.py")}
manifest = {
    "task": TASK, "title": "Безопасная анонимизация диагностических отчётов Web Alarm Workspace",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION", "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": TASK_DIR.relative_to(REPO).as_posix(), "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_new": repo_files,
    "also_changed_outside_folder": {"Документация/000_Задачи Claude.md": entry(REPO / "Документация" / "000_Задачи Claude.md")
                                    | {"note": "BLOCK 1-3 rotation only, current EOL kept"}},
    "not_published_private": "logs/test-evidence/web_alarm/" + TASK + "/ (git-ignored: originals, sanitized copies, raw runs)",
    "files": files,
}
(TASK_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                        newline="\n")
print(json.dumps({"files": len(files), "repository_files_new": {k: v["sha256"] for k, v in repo_files.items()}}))
