"""manifest.json for CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001: every file of this report folder (manifest excluded)
with bytes/SHA-256/line endings, plus the input census comparison (inputs_read.json vs inputs_final.json):
only the own card may differ, and only by the recorded rotation. Read-only elsewhere."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CARD = "Документация/000_Задачи Claude.md"


def entry(path: Path) -> dict:
    data = path.read_bytes()
    eol = "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CR_PRESENT")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


before = json.loads((HERE / "inputs_read.json").read_bytes())["inputs"]
after = json.loads((HERE / "inputs_final.json").read_bytes())["inputs"]
rotation = json.loads((HERE / "card-rotation.json").read_bytes())
changed = sorted(k for k in before if before[k]["sha256"] != after[k]["sha256"])
assert changed == [CARD], changed
assert after[CARD]["sha256"] == rotation["after_sha256"], "card differs from the recorded rotation result"
manifest = {
    "task": "CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "kind": "architecture review, READ-ONLY (0 network, 0 client/VM/Sandbox runs, 0 system queries/changes, 0 Git)",
    "publication": "LOCAL ONLY / NOT SYNCED",
    "report_folder": "reports/CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001",
    "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_changed_outside_folder": {CARD: {"sha256_before": before[CARD]["sha256"],
                                                       "sha256_after": after[CARD]["sha256"],
                                                       "change": "BLOCK 1-3 rotation only (card-rotation.json, card_precheck.json)"}},
    "inputs_read": len(before),
    "inputs_unchanged": len(before) - len(changed),
    "files": {p.relative_to(HERE).as_posix(): entry(p) for p in sorted(HERE.rglob("*"))
              if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts},
}
(HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                    newline="\n")
print(len(manifest["files"]), "files;", manifest["inputs_unchanged"], "of", len(before), "inputs unchanged; card = rotation")
