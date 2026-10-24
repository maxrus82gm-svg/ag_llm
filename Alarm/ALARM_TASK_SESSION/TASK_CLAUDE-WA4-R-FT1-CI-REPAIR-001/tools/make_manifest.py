"""Write manifest.json for this TASK folder: every file (except the manifest) with bytes, SHA-256 and EOL, plus the
changed repository files (working-copy SHA-256 and LF-normalised SHA-256, which is what a published blob has) and the
card / archive pointers. Relative paths only; the repository root comes from this file's location.

LF policy: a file in this folder with any CR byte refuses the manifest (exit 1): the publication path converts CRLF
to LF, so a CRLF file's SHA-256 could never match its published blob.
Usage: make_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
TASK = "CLAUDE-WA4-R-FT1-CI-REPAIR-001"
CHANGED = {"test_web_alarm_runner_guard.py": "modified"}
UNCHANGED_PROTECTED = ("wa4a_acceptance.py", "web_alarm/transport_event_recovery.py",
                       "test_web_alarm_transport_event_recovery.py")
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
    print(json.dumps({"refused": "files with CR bytes (publish LF only)", "count": len(with_cr), "first": with_cr[:5]}))
    sys.exit(1)
baseline = json.loads((TASK_DIR / "source-baseline.json").read_text(encoding="utf-8"))["sha256"]
repo_files = {}
for rel, kind in CHANGED.items():
    data = (REPO / rel).read_bytes()
    repo_files[rel] = entry(REPO / rel) | {"kind": kind, "sha256_lf_normalized": sha(data.replace(b"\r\n", b"\n")),
                                           "sha256_before_task": baseline.get(rel)}
manifest = {
    "task": TASK,
    "title": "Устранение девяти ошибок независимой Windows-проверки защитного механизма Web Alarm",
    "repository_files_unchanged_checked": {rel: {"sha256": sha((REPO / rel).read_bytes()),
                                                 "sha256_before_task": baseline.get(rel),
                                                 "unchanged": sha((REPO / rel).read_bytes()) == baseline.get(rel)}
                                           for rel in UNCHANGED_PROTECTED},
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION", "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": TASK_DIR.relative_to(REPO).as_posix(), "self_hash": "EXCLUDED (reported in the chat handoff)",
    "eol_policy": "all files in this folder LF (a CR byte refuses the manifest); wa4a_acceptance.py is CRLF in the "
                  "working copy as before the TASK - compare its published blob with sha256_lf_normalized",
    "repository_files_changed": repo_files,
    "also_changed_outside_folder": {
        "Документация/000_Задачи Claude.md": "BLOCKS 1-3 rotated by tools/rotate_task.py (receipt rotation.json); "
                                             "BLOCK 4 byte-identical before/after",
        "Документация/001_История выполненных задач Claude.md": "one appended record; offset, length and SHA-256 in "
                                                              "rotation.json"},
    "not_published_private": "raw runner outputs stay in disposable TEMP; published copies only via "
                             "web_alarm.evidence_sanitizer (runs/runs-map.json: raw SHA -> published SHA)",
    "files": files,
}
(TASK_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                        newline="\n")
print(json.dumps({"files": len(files), "repository_files_changed": {k: v["sha256"][:16] for k, v in repo_files.items()}}))
