"""Compare two full-suite results.json files by test ID and status (read-only).
Usage: compare_full_runs.py <previous results.json> <current results.json> <out.json>"""
import hashlib
import json
import sys
from pathlib import Path

prev_raw, cur_raw = Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes()
prev = {t["test"]: t["status"] for t in json.loads(prev_raw)["tests"]}
cur = {t["test"]: t["status"] for t in json.loads(cur_raw)["tests"]}
report = {
    "previous": {"path": sys.argv[1], "sha256": hashlib.sha256(prev_raw).hexdigest(), "ids": len(prev)},
    "current": {"path": sys.argv[2], "sha256": hashlib.sha256(cur_raw).hexdigest(), "ids": len(cur)},
    "missing_in_current": sorted(set(prev) - set(cur)),
    "status_changed": {k: [prev[k], cur[k]] for k in sorted(set(prev) & set(cur)) if prev[k] != cur[k]},
    "added": sorted(set(cur) - set(prev)),
}
report["added_count"] = len(report["added"])
report["added_all_in_new_module"] = all(k.startswith("test_web_alarm_aud01t02b_repair.") for k in report["added"])
Path(sys.argv[3]).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 6 else f"{len(v)} items") for k, v in report.items()},
                 indent=1))
