"""Run probe_s0_storage under the guarded Web Alarm runner several times and keep a path-free evidence record.

Every attempt goes through run_gate.py (LOCALAPPDATA/APPDATA and pycache in TEMP, runner guard on writes outside TEMP,
external sockets and Git metadata). The facts file of each attempt lives in its own TEMP folder. Only test ids,
statuses, counters and the observed facts are published; local paths and tracebacks are not.
Usage: run_probes.py <python> <attempts> <out.json>
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
python, attempts, target = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
runs = []
for number in range(1, attempts + 1):
    facts_dir = Path(tempfile.mkdtemp(prefix="claude-s0-facts-"))
    facts_path = facts_dir / "facts.jsonl"
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s0", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001",
               CLAUDE_EXTRA_PATH=str(TOOLS), S0_FACTS_PATH=str(facts_path))
    done = subprocess.run([python, str(GATE), python, f"attempt{number}", "probe_s0_storage"], cwd=REPO, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    summary = json.loads(done.stdout)
    results = json.loads((Path(summary["base"]) / "out" / "results.json").read_text(encoding="utf-8"))
    facts = [json.loads(line) for line in facts_path.read_text(encoding="utf-8").splitlines()] if facts_path.exists() else []
    runs.append({
        "attempt": number, "runner_exit": summary["exit"], "tests_run": summary.get("tests_run"),
        "failures": summary.get("failures"), "errors": summary.get("errors"), "skips": summary.get("skips"),
        "isolation_violations": summary.get("isolation_violations"), "python": summary.get("python", "")[:7],
        "tests": [{"test": t["test"].removeprefix("probe_s0_storage."), "status": t["status"]} for t in results["tests"]],
        "facts": [{"test": f[0]["test"].removeprefix("probe_s0_storage."), "observed": f[1:]} for f in facts],
    })
    print(json.dumps({"attempt": number, "exit": summary["exit"], "failures": summary.get("failures"),
                      "errors": summary.get("errors"), "isolation_violations": summary.get("isolation_violations")}))
record = {"task": "CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001", "module": "tools/probe_s0_storage.py",
          "runner": "wa4a_acceptance.py via run_gate.py (TEMP isolation)", "attempts": runs}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
