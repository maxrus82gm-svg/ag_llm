"""Per-method census of one guarded runner attempt (results.json), ASCII console line, no error text echoed.

A method counts as FAIL if the method itself or any of its subTests failed; subTest ids in this runner look like
"<method> (params)". The last line of each failure (assertion message only) is kept to classify it.
Usage: census.py <attempt-base-dir> [--detail]
"""
import json
import sys
from pathlib import Path

base = Path(sys.argv[1])
r = json.loads((base / "out" / "results.json").read_text(encoding="utf-8"))
methods = {}
for t in r["tests"]:
    test = t["test"]
    method = test.split(" (")[0].split(" [")[0]
    entry = methods.setdefault(method, {"status": "PASS", "subtests_failed": []})
    if t["status"] in ("FAIL", "ERROR"):
        entry["status"] = t["status"] if entry["status"] != "ERROR" else "ERROR"
        last = [line for line in (t.get("error") or "").strip().splitlines() if line.strip()][-1:]
        entry["subtests_failed"].append({"id": test[len(method):].strip() or "<method>", "last": last[0][:160] if last else ""})
    elif t["status"] == "SKIP" and entry["status"] == "PASS":
        entry["status"] = "SKIP"
counts = {}
for entry in methods.values():
    counts[entry["status"]] = counts.get(entry["status"], 0) + 1
out = {"tests_run": r["tests_run"], "methods": len(methods), "by_status": counts,
       "isolation_violations": len(r["isolation_violations"]), "successful": r["successful"]}
if "--detail" in sys.argv:
    out["non_pass"] = {m: e for m, e in methods.items() if e["status"] != "PASS"}
print(ascii(json.dumps(out, ensure_ascii=False, indent=1)))
