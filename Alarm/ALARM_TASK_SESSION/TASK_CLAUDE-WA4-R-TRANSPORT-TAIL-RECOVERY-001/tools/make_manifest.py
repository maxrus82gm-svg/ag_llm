"""manifest.json + gate-e.json for CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 (read-only elsewhere).

Asserts the scope at build time: against the Gate A map exactly two new files and zero drift/missing; the
two new files equal source-final.json and diff-summary.json; the card differs only by the recorded rotation
(card-rotation.json) and keeps its CRLF line endings. Lists every task-folder file (manifest excluded) with
bytes, SHA-256 and line endings.
"""
import hashlib
import json
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
NEW = {"web_alarm/transport_event_recovery.py", "test_web_alarm_transport_event_recovery.py"}
CARD = REPO / "Документация" / "000_Задачи Claude.md"
sha = lambda data: hashlib.sha256(data).hexdigest()


def entry(path: Path) -> dict:
    data = path.read_bytes()
    eol = "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CRLF_PRESENT")
    return {"bytes": len(data), "sha256": sha(data), "eol": eol}


gate = json.loads((HERE / "source-gate.json").read_bytes())
final = json.loads((HERE / "source-final.json").read_bytes())
diff = json.loads((HERE / "diff" / "diff-summary.json").read_bytes())
rotation = json.loads((HERE / "card-rotation.json").read_bytes())
precheck = json.loads((HERE / "card_precheck.json").read_bytes())
assert gate["verdict"] == "PASS" and not (final["drift"] or final["missing"]), final
assert set(final["unexpected"]) == NEW, final["unexpected"]
changed = {}
for rel in sorted(NEW):
    now = entry(REPO / rel)
    assert now["sha256"] == final["source_sha256_all"][rel] == diff[rel]["sha256_after"], rel
    changed[rel] = dict(now, kind="new", added_lines=diff[rel]["added"])
unchanged_in_scope = {rel: row["sha256_after"] for rel, row in diff.items() if row["kind"] == "unchanged"}
for rel, digest in unchanged_in_scope.items():
    assert sha((REPO / rel).read_bytes()) == digest == gate["source_sha256_all"][rel], rel
card = CARD.read_bytes()
assert sha(card) == rotation["after_sha256"] and rotation["block1_now"] == "WAITING", "card differs from rotation"
assert card.count(b"\r\n") == card.count(b"\n"), "card line endings changed"
gate_e = {
    "task": "CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001",
    "baseline_map": {"source": gate["previous_map"], "sha256": gate["previous_map_sha256"], "files": gate["expected_files"],
                     "verdict": gate["verdict"]},
    "final_map": {"files": len(final["source_sha256_all"]), "new": sorted(final["unexpected"]), "drift": final["drift"],
                  "missing": final["missing"]},
    "repository_files_changed": changed,
    "in_scope_unchanged": unchanged_in_scope,
    "card": {"path": "Документация/000_Задачи Claude.md", "eol": "CRLF (converted outside this TASK before start)",
             "precheck": precheck["result"], "sha256_at_start": precheck["before_sha256"],
             "sha256_after_rotation": rotation["after_sha256"], "change": "BLOCK 1-3 rotation only"},
    "eol_note": "8 pre-existing test files contain CRLF (unchanged, same as the Gate A map); both new files are LF",
    "rollback": "delete web_alarm/transport_event_recovery.py and test_web_alarm_transport_event_recovery.py; "
                "nothing else in the repository changed; no data format changed",
}
(HERE / "gate-e.json").write_text(json.dumps(gate_e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
manifest = {
    "task": "CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001",
    "title": "Безопасное ручное восстановление повреждённого транспортного журнала после аварии (AUD-01T-R)",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "publication": "LOCAL ONLY / NOT SYNCED",
    "task_folder": "Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001",
    "self_hash": "EXCLUDED (reported in the chat handoff)",
    "repository_files_changed": changed,
    "also_changed_outside_folder": ["Документация/000_Задачи Claude.md (BLOCK 1-3 rotation only, CRLF kept)"],
    "files": {p.relative_to(HERE).as_posix(): entry(p) for p in sorted(HERE.rglob("*"))
              if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts},
}
(HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                    newline="\n")
print(len(manifest["files"]), "task files;", sorted(changed), "new; card = rotation")
