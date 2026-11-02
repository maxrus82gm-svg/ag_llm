"""Path-free record of the two self-guarded standalone runners (test_rt002_final_audit_m1.py, test_rt002_s2_budget_policy.py),
which skip as whole modules under the shared runner and run only through their own main(): own TEMP sandbox,
LOCALAPPDATA/APPDATA/TEMP redirection, socket/process guards and a production-file hash check.
Each output file holds the runner's printed JSON summary at its end; sandbox and log paths are dropped.
Usage: record_standalone.py <out.json> <label>=<runner output file> ...
"""
import json
import sys
from pathlib import Path


def summary(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.rfind('{\n  "task"')
    value = json.loads(text[start:])
    counts = value["counts"]
    run, fail, err, skip = counts["run"], counts["failures"], counts["errors"], counts["skipped"]
    return {"runner_task": value["task"], "gate": value["gate"]["status"], "exit_code": value["gate"]["exit_code"],
            "run": run, "passed": run - fail - err - skip, "failures": fail, "errors": err, "skipped": skip,
            "isolation_violations": len(value["isolation_violations"]), "problems": value["problems"],
            "python": value.get("python"), "log_sha256": value.get("log_sha256")}


def main():
    target = Path(sys.argv[1])
    rows = {}
    for item in sys.argv[2:]:
        label, path = item.split("=", 1)
        rows[label] = summary(Path(path))
    record = {"task": "CLAUDE-WUA-CHAT-RUNSTORE-P9-001",
              "purpose": "self-guarded standalone Audit/Run regression runners, base and final bytes", "runs": rows}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: (v["gate"], v["run"], v["passed"]) for k, v in rows.items()}))


if __name__ == "__main__":
    main()
