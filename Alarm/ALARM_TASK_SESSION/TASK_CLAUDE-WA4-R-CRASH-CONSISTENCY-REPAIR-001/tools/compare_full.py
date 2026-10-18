"""Per-method comparison of two wa4a_acceptance results.json (read-only). A method is PASS only if every
entry of it (subtests included) is PASS. Usage: compare_full.py <previous results.json> <current results.json> [<out.json>]
"""
import json
import sys
from pathlib import Path


def census(path):
    data = json.loads(Path(path).read_bytes())
    methods = {}
    for entry in data["tests"]:
        method = entry["test"].split(" [", 1)[0].split(" (", 1)[0]
        methods.setdefault(method, set()).add(entry["status"])
    return data, {m: ("PASS" if s <= {"PASS"} else "+".join(sorted(s - {"PASS"}))) for m, s in methods.items()}


prev_data, prev = census(sys.argv[1])
cur_data, cur = census(sys.argv[2])
report = {
    "previous": {"tests_run": prev_data["tests_run"], "methods": len(prev)},
    "current": {"tests_run": cur_data["tests_run"], "methods": len(cur)},
    "removed": sorted(set(prev) - set(cur)),
    "added": {m: cur[m] for m in sorted(set(cur) - set(prev))},
    "status_changed": {m: f"{prev[m]} -> {cur[m]}" for m in sorted(set(prev) & set(cur)) if prev[m] != cur[m]},
    "current_non_pass": {m: s for m, s in sorted(cur.items()) if s != "PASS"},
    "previous_non_pass": {m: s for m, s in sorted(prev.items()) if s != "PASS"},
}
text = json.dumps(report, indent=1) + "\n"
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(text, encoding="utf-8", newline="\n")
print(text)
