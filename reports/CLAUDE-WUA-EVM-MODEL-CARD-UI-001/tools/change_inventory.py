"""Prove the change inventory without Git: compare each changed file with its baseline bytes (a private copy taken
before the first edit, whose SHA-256 must equal the stage-1 manifest pin) and list the changed line ranges.
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
S1 = json.loads((REPO / "reports" / "CLAUDE-WUA-CHAT-S1-READONLY-UI-001" / "manifest.json").read_text(encoding="utf-8"))
FILES = {"web_alarm/server.py": "web_alarm/server.py", "web_alarm/ui.py": "web_alarm/ui.py",
         "test_web_alarm_evm_ui.js": "test_web_alarm_evm_ui.js",
         "test_web_alarm_ultra_connections.py": "test_web_alarm_ultra_connections.py"}  # last: EVM WUA-1 test, no stage-1 pin
sha = lambda data: hashlib.sha256(data).hexdigest()
rows = {}
for rel, copy in FILES.items():
    before, after = (baseline / copy).read_bytes(), (REPO / rel).read_bytes()
    pin = S1["changed_files"].get(rel, {}).get("sha256")
    old, new = before.decode("utf-8").splitlines(), after.decode("utf-8").splitlines()
    hunks = []
    for group in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_grouped_opcodes(0):
        a0, a1, b0, b1 = group[0][1], group[-1][2], group[0][3], group[-1][4]
        hunks.append({"baseline_lines": [a0 + 1, a1], "new_lines": [b0 + 1, b1]})
    rows[rel] = {"baseline_sha256": sha(before), "baseline_equals_stage1_pin": sha(before) == pin if pin else "no stage-1 pin",
                 "new_sha256": sha(after), "baseline_lines": len(old), "new_lines": len(new),
                 "eol_kept": (b"\r\n" in before) == (b"\r\n" in after), "changed_regions": hunks}
record = {"task": "CLAUDE-WUA-EVM-MODEL-CARD-UI-001", "purpose": "change inventory against the stage-1 pinned bytes",
          "files": rows, "all_baselines_equal_stage1_pins": all(r["baseline_equals_stage1_pin"] is True for r in rows.values()
                                                                if r["baseline_equals_stage1_pin"] != "no stage-1 pin")}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({rel: (r["baseline_equals_stage1_pin"], len(r["changed_regions"]), r["eol_kept"]) for rel, r in rows.items()}))
