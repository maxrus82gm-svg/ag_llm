"""Independent per-method census of a wa4a_acceptance results.json (the runner's own `passed`
counter goes negative with failing subtests, ASTRA finding). A method is PASS only if neither it nor
any of its subtests has a non-PASS entry. Usage: summarize_results.py <results.json> [<out.json>]
"""
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_bytes()
data = json.loads(raw)
methods: "OrderedDict[str, dict]" = OrderedDict()
for entry in data["tests"]:
    test_id = entry["test"]
    method = test_id.split(" [", 1)[0].split(" (", 1)[0]
    slot = methods.setdefault(method, {"entries": 0, "statuses": {}})
    slot["entries"] += 1
    slot["statuses"][entry["status"]] = slot["statuses"].get(entry["status"], 0) + 1
verdict = {}
for method, slot in methods.items():
    statuses = slot["statuses"]
    if set(statuses) <= {"PASS"}:
        verdict[method] = "PASS"
    elif "ERROR" in statuses:
        verdict[method] = "ERROR"
    elif "FAIL" in statuses:
        verdict[method] = "FAIL"
    elif "SKIP" in statuses and set(statuses) <= {"PASS", "SKIP"}:
        verdict[method] = "SKIP"
    else:
        verdict[method] = "+".join(sorted(statuses))
counts = {}
for value in verdict.values():
    counts[value] = counts.get(value, 0) + 1
summary = {
    "results_json": str(path),
    "results_sha256": hashlib.sha256(raw).hexdigest(),
    "runner_reported": {k: data.get(k) for k in ("tests_run", "passed", "failures", "errors", "skips", "successful")},
    "isolation_violations": len(data.get("isolation_violations", [])),
    "entries": len(data["tests"]),
    "methods": len(verdict),
    "method_counts": counts,
    "non_pass_methods": {m: v for m, v in verdict.items() if v != "PASS"},
}
text = json.dumps(summary, indent=1)
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(text + "\n", encoding="utf-8")
print(text)
