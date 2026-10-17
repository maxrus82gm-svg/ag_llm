"""Run a list of guarded-runner attempts sequentially through tools/run_gate.py (one attempt at a time).

Each attempt: label, optional CLAUDE_EXTRA_PATH, optional CLAUDE_RUNNER_ROOT, targets. Writes
runs/<batch>.attempts.json with label -> TEMP base directory, exit and wall time.
Usage: run_gate_batch.py <python> <batch-name> <spec.json>
spec.json: [{"label": ..., "targets": [...], "extra_path": null|str, "runner_root": null|str}, ...]
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
python, batch, spec = sys.argv[1], sys.argv[2], json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
results = []
for item in spec:
    env = dict(os.environ)
    env["CLAUDE_RUN_PREFIX"] = "claude-crashcc"
    env["CLAUDE_TASK_LABEL"] = "CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001"
    env.pop("CLAUDE_EXTRA_PATH", None)
    env.pop("CLAUDE_RUNNER_ROOT", None)
    if item.get("extra_path"):
        env["CLAUDE_EXTRA_PATH"] = item["extra_path"]
    if item.get("runner_root"):
        env["CLAUDE_RUNNER_ROOT"] = item["runner_root"]
    started = time.time()
    proc = subprocess.run([python, "-I", "-B", str(HERE / "tools" / "run_gate.py"), python, item["label"],
                           *item["targets"]], env=env, capture_output=True, cwd=os.environ.get("TEMP"))
    try:
        summary = json.loads(proc.stdout.decode("ascii", errors="replace"))
    except ValueError:
        summary = {"base": None, "raw": proc.stdout.decode(errors="replace")[-500:],
                   "stderr": proc.stderr.decode(errors="replace")[-500:]}
    row = {"label": item["label"], "base": summary.get("base"), "exit": summary.get("exit"),
           "tests_run": summary.get("tests_run"), "failures": summary.get("failures"),
           "errors": summary.get("errors"), "skips": summary.get("skips"),
           "isolation_violations": summary.get("isolation_violations"), "wall": round(time.time() - started, 1)}
    results.append(row)
    print(json.dumps(row), flush=True)
    (HERE / "runs" / f"{batch}.attempts.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
