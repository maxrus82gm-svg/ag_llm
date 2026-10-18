"""manifest.json for CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001: every changed repository file (SHA before/after,
bytes, line endings, diff counts from diff/diff-summary.json, re-hashed now) and every file of this TASK folder
(manifest excluded), plus the final source-map verdict (only the intended files drift). Read-only elsewhere."""
import hashlib
import json
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
INTENDED = {
    "web_alarm/state_machine.py", "web_alarm/operation_store.py", "web_alarm/projection.py",
    "web_alarm/recovery_coordinator.py", "web_alarm/event_checkpoint_store.py", "web_alarm/server.py",
    "test_web_alarm_aud01t02b_repair.py", "test_web_alarm_recovery_coordinator_adversarial.py",
}
NEW = {"test_web_alarm_crash_consistency.py"}


def entry(path: Path) -> dict:
    data = path.read_bytes()
    eol = "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CR_PRESENT")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": eol}


final = json.loads((HERE / "source-final.json").read_bytes())
diff = json.loads((HERE / "diff" / "diff-summary.json").read_bytes())
changed = {}
for rel, row in diff.items():
    if not row["changed"]:
        continue
    now = entry(REPO / rel)
    assert now["sha256"] == row["sha256_after"], f"{rel} changed after the diff was made"
    assert now["sha256"] == final["source_sha256_all"][rel], f"{rel} differs from source-final.json"
    changed[rel] = dict(now, sha256_before=row["sha256_before"], added=row["added"], removed=row["removed"],
                        kind="new" if row["sha256_before"] is None else "modified")
assert set(final["drift"]) == INTENDED and set(final["unexpected"]) == NEW and not final["missing"], final
manifest = {
    "task": "CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001",
    "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_changed": changed,
    "repository_files_unchanged_in_scope": sorted(rel for rel, row in diff.items() if not row["changed"]),
    "final_source_map": {"files": len(final["source_sha256_all"]), "drift_vs_design_map": final["drift"],
                         "unexpected": final["unexpected"], "missing": final["missing"],
                         "only_intended_files_changed": True},
    "rollback": "copy baseline/web_alarm/* and baseline/tests/* back over the repository files; delete "
                "test_web_alarm_crash_consistency.py (no data migration: new events are ignored by the old code)",
    "also_changed_outside_folder": ["Документация/000_Задачи Claude.md (card rotation only)"],
    "files": {p.relative_to(HERE).as_posix(): entry(p) for p in sorted(HERE.rglob("*"))
              if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts},
}
(HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                    newline="\n")
print(len(changed), "repository files;", len(manifest["files"]), "task files")
