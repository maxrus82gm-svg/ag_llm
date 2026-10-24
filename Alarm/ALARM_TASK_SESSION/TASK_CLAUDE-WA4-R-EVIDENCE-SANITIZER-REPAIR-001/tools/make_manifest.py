"""Write manifest.json for this TASK folder: every file (except the manifest) with bytes, SHA-256 and EOL, plus the
two changed repository files and the card / archive pointers. Relative paths only; the repository root comes from
this file's location.

LF policy: a file with CR bytes is refused (exit 1, no manifest written). The publication path converts CRLF to LF,
so a CRLF file's SHA-256 could never be matched against its published blob - the defect found in the finalization
of 2026-10-24 (201 CRLF run outputs). The card is a living document (the user puts the next BLOCK 1 in, the verifier
writes BLOCK 4): its hash is recorded as of this TASK's last rotation, not as a value to compare with a later card.
Usage: make_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
TASK = "CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001"


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
    print(json.dumps({"refused": "files with CR bytes (publish LF only)", "count": len(with_cr), "first": with_cr[:5]}))
    sys.exit(1)
repo_files = {rel: entry(REPO / rel) | {"kind": "modified", "lines": (REPO / rel).read_bytes().count(b"\n")}
              for rel in ("web_alarm/evidence_sanitizer.py", "test_web_alarm_evidence_sanitizer.py")}
card = entry(REPO / "Документация" / "000_Задачи Claude.md")
manifest = {
    "task": TASK, "title": "Исправление fail-open ошибок механизма безопасной публикации диагностических отчётов",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION", "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": TASK_DIR.relative_to(REPO).as_posix(), "self_hash": "EXCLUDED (reported in the chat handoff)",
    "eol_policy": "all files LF (checked: a CR byte refuses the manifest)",
    "repository_files_changed": repo_files,
    "also_changed_outside_folder": {
        "Документация/000_Задачи Claude.md": {"sha256_at_last_rotation": card["sha256"], "bytes": card["bytes"],
                                             "eol": card["eol"],
                                             "note": "living document (user BLOCK 1, verifier BLOCK 4): compare with "
                                                     "the rotation receipts, not with a later card; this TASK "
                                                     "changed only its BLOCK 1-3 lines, BLOCK 4 untouched"},
        "Документация/001_История выполненных задач Claude.md":
            "append-only records; offsets, lengths and SHA-256 in card-rotation.json, amendment-rotation.json, "
            "finalize-rotation.json"},
    "not_published_private": "raw run outputs and real-package staging stayed in disposable TEMP (not published)",
    "files": files,
}
(TASK_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                        newline="\n")
print(json.dumps({"files": len(files), "repository_files_changed": {k: v["sha256"] for k, v in repo_files.items()}}))
