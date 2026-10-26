"""Run one unittest module from this tools folder several times through run_gate.py and keep a path-free record
(test ids, statuses, counters). Usage: run_gate_attempts.py <python> <module> <attempts> <out.json>
"""
import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
python, module, attempts, target = sys.argv[1], sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
runs = []
for number in range(1, attempts + 1):
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s0", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001",
               CLAUDE_EXTRA_PATH=str(TOOLS))
    done = subprocess.run([python, str(GATE), python, f"attempt{number}", module], cwd=REPO, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    summary = json.loads(done.stdout)
    results = json.loads((Path(summary["base"]) / "out" / "results.json").read_text(encoding="utf-8"))
    runs.append({"attempt": number, "runner_exit": summary["exit"], "tests_run": summary.get("tests_run"),
                 "failures": summary.get("failures"), "errors": summary.get("errors"), "skips": summary.get("skips"),
                 "isolation_violations": summary.get("isolation_violations"),
                 "tests": [{"test": t["test"].removeprefix(module + "."), "status": t["status"]} for t in results["tests"]]})
    print(json.dumps({k: runs[-1][k] for k in ("attempt", "runner_exit", "tests_run", "failures", "errors",
                                               "isolation_violations")}))
record = {"task": "CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001", "module": f"tools/{module}.py",
          "runner": "wa4a_acceptance.py via run_gate.py (TEMP isolation)", "attempts": runs}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
