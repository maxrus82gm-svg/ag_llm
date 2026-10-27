"""Run the same unittest targets several times through run_gate.py (guarded runner, TEMP isolation) and keep a
path-free record per attempt: counters, statuses and the last line of every non-PASS result.
Usage: repeat_gate.py <python> <attempts> <out.json> <purpose> <target> [<target> ...]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
PATH = re.compile(r"[A-Za-z]:\\[^\s'\"]*")
python, attempts, target, purpose, modules = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], sys.argv[5:]
runs = []
for number in range(1, attempts + 1):
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s1", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S1-READONLY-UI-001")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, f"rep{number}", *modules], cwd=REPO, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    summary = json.loads(done.stdout)
    base = Path(summary["base"])
    results = json.loads((base / "out" / "results.json").read_text(encoding="utf-8"))
    facts = []
    stderr = (base / "stderr.txt").read_text(encoding="utf-8", errors="replace") if (base / "stderr.txt").exists() else ""
    for line in stderr.splitlines():
        if "S1-CONCURRENCY " in line:
            facts.append(json.loads(line.split("S1-CONCURRENCY ", 1)[1]))
    runs.append({"attempt": number, "runner_exit": summary["exit"], "tests_run": summary.get("tests_run"),
                 "failures": summary.get("failures"), "errors": summary.get("errors"), "skips": summary.get("skips"),
                 "isolation_violations": summary.get("isolation_violations"), "concurrency_facts": facts,
                 "non_pass": [{"test": t["test"], "status": t["status"],
                               "detail": PATH.sub("<path>", ((t.get("reason") or t.get("error") or "").strip().splitlines() or [""])[-1])[:240]}
                              for t in results["tests"] if t["status"] != "PASS"]})
    print(json.dumps({k: runs[-1][k] for k in ("attempt", "runner_exit", "tests_run", "failures", "errors", "skips",
                                               "isolation_violations")}), flush=True)
record = {"task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "purpose": purpose, "targets": modules,
          "runner": "wa4a_acceptance.py via run_gate.py (TEMP isolation)", "attempts": runs}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
