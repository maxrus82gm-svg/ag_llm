"""Prove the change inventory without Git: compare each changed file with its baseline bytes (a private copy taken
before the first edit) and with the published EVM package of #455 (CLAUDE-WUA-EVM-MODEL-CARD-UI-001 manifest; the
local checkout may hold CRLF where the package recorded LF), and list the changed line ranges.
Only hashes, counts and line ranges are published, never the baseline copy or a path.
Usage: change_inventory.py <baseline folder> <out.json>
"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
baseline, target = Path(sys.argv[1]), Path(sys.argv[2])
EVM = json.loads((REPO / "reports" / "CLAUDE-WUA-EVM-MODEL-CARD-UI-001" / "manifest.json").read_text(encoding="utf-8"))
PINS = {**{k: v["sha256"] for k, v in EVM["new_files"].items()}, **{k: v["sha256"] for k, v in EVM["changed_files"].items()}}
FILES = ("web_alarm/ui.py", "web_alarm/server.py", "web_alarm/model_cards.py", "test_web_alarm_model_cards.py", "test_web_alarm_evm_ui.js")
sha = lambda data: hashlib.sha256(data).hexdigest()


def same_content(data: bytes, pin: str) -> bool:
    lf = data.replace(b"\r\n", b"\n")
    return pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


rows = {}
for rel in FILES:
    before, after = (baseline / rel).read_bytes(), (REPO / rel).read_bytes()
    old, new = before.decode("utf-8").splitlines(), after.decode("utf-8").splitlines()
    hunks = []
    for group in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_grouped_opcodes(0):
        hunks.append({"baseline_lines": [group[0][1] + 1, group[-1][2]], "new_lines": [group[0][3] + 1, group[-1][4]]})
    rows[rel] = {"baseline_sha256": sha(before), "baseline_is_published_455_content": same_content(before, PINS[rel]),
                 "new_sha256": sha(after), "baseline_lines": len(old), "new_lines": len(new),
                 "eol": "CRLF" if b"\r\n" in after else "LF", "eol_kept": (b"\r\n" in before) == (b"\r\n" in after),
                 "changed_regions": hunks}
record = {"task": "CLAUDE-WUA-EVM-COMPACT-LAYOUT-001", "purpose": "change inventory against the published #455 content",
          "files": rows, "all_baselines_are_455": all(r["baseline_is_published_455_content"] for r in rows.values())}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({rel: (r["baseline_is_published_455_content"], len(r["changed_regions"]), r["eol_kept"]) for rel, r in rows.items()}))
