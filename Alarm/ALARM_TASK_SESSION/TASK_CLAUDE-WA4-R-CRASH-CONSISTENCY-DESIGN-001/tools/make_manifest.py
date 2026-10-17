"""manifest.json for CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001: every file of this TASK folder (manifest
excluded) with bytes, SHA-256 and line endings, plus the statement that no repository source changed
(source-gate verdict). Read-only elsewhere."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def entry(path: Path) -> dict:
    data = path.read_bytes()
    eol = "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CR_PRESENT")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


gate = json.loads((HERE / "source-gate.json").read_bytes())
manifest = {
    "task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION - DESIGN PROPOSAL",
    "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001",
    "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_changed": [],
    "repository_source_gate": {"verdict": gate["verdict"], "files": gate["expected_files"],
                               "drift": gate["drift"], "missing": gate["missing"], "unexpected": gate["unexpected"]},
    "also_changed_outside_folder": ["Документация/000_Задачи Claude.md (card rotation only)"],
    "files": {p.relative_to(HERE).as_posix(): entry(p) for p in sorted(HERE.rglob("*"))
              if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts},
}
(HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                    newline="\n")
print(len(manifest["files"]), "task files; source gate", gate["verdict"])
