"""Copy one finished run_gate.py attempt into a path-free evidence record (test ids, statuses, counters, and the
last assertion line of every non-PASS test with local paths removed).
Usage: record_gate.py <attempt base folder> <purpose> <out.json>
"""
import json
import re
import sys
from pathlib import Path

base, purpose, target = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
results = json.loads((base / "out" / "results.json").read_text(encoding="utf-8"))
PATH = re.compile(r"[A-Za-z]:\\[^\s'\"]*|/(?:tmp|home|Users)/[^\s'\"]*")


def last_line(test):
    text = test.get("reason") or test.get("error") or ""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return PATH.sub("<path>", lines[-1])[:300] if lines else ""


record = {
    "task": "CLAUDE-WUA-CHAT-LAUNCHER-001", "purpose": purpose,
    "runner": "wa4a_acceptance.py via run_gate.py (TEMP isolation)", "python": summary["python"][:7],
    "targets": summary["argv"][summary["argv"].index("--output") + 2:],
    "runner_exit": summary["exit"], "tests_run": summary["tests_run"], "failures": summary["failures"],
    "errors": summary["errors"], "skips": summary["skips"], "isolation_violations": summary["isolation_violations"],
    "tests": [{"test": t["test"], "status": t["status"], **({"detail": last_line(t)} if t["status"] != "PASS" else {})}
              for t in results["tests"]],
}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: record[k] for k in ("runner_exit", "tests_run", "failures", "errors", "skips", "isolation_violations")}))
