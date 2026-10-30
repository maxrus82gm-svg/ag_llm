"""Prove the change inventory without Git: compare each file of the task scope with its baseline bytes (a private copy
taken before the first edit) and with the published EVM package #457 (CLAUDE-WUA-EVM-COMPACT-LAYOUT-001 manifest; the
local checkout holds CRLF), and list the changed line ranges. Only hashes, counts and line ranges are published.
Usage: change_inventory.py <baseline folder> <out.json>
"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
baseline, target = Path(sys.argv[1]), Path(sys.argv[2])
PINS = {k: v["sha256"] for k, v in json.loads((REPO / "reports/CLAUDE-WUA-EVM-COMPACT-LAYOUT-001/manifest.json")
                                                 .read_text(encoding="utf-8"))["changed_files"].items()}
FILES = ("web_alarm/ui.py", "test_web_alarm_evm_ui.js", "web_alarm/server.py", "web_alarm/model_cards.py", "test_web_alarm_model_cards.py")
sha = lambda data: hashlib.sha256(data).hexdigest()


def same_content(data: bytes, pin: str) -> bool:
    lf = data.replace(b"\r\n", b"\n")
    return pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


rows = {}
for rel in FILES:
    before, after = (baseline / rel).read_bytes(), (REPO / rel).read_bytes()
    old, new = before.decode("utf-8").splitlines(), after.decode("utf-8").splitlines()
    hunks = [{"baseline_lines": [g[0][1] + 1, g[-1][2]], "new_lines": [g[0][3] + 1, g[-1][4]]}
             for g in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_grouped_opcodes(0)]
    rows[rel] = {"baseline_sha256": sha(before), "baseline_is_published_457_content": same_content(before, PINS[rel]),
                 "new_sha256": sha(after), "changed": before != after, "baseline_lines": len(old), "new_lines": len(new),
                 "eol": "CRLF" if b"\r\n" in after else "LF", "eol_kept": (b"\r\n" in before) == (b"\r\n" in after),
                 "changed_regions": hunks}
record = {"task": "CLAUDE-WUA-EVM-INTERACTION-DND-001", "purpose": "change inventory against the published #457 content",
          "files": rows, "all_baselines_are_457": all(r["baseline_is_published_457_content"] for r in rows.values()),
          "changed": sorted(rel for rel, r in rows.items() if r["changed"]),
          "unchanged": sorted(rel for rel, r in rows.items() if not r["changed"])}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({rel: (r["changed"], r["baseline_is_published_457_content"], len(r["changed_regions"]), r["eol_kept"]) for rel, r in rows.items()}))
