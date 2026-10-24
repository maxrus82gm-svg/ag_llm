"""Build a TEMP mirror per variant and run one target through run_gate.py inside it.

Usage: run_mutants.py <python> <batch-label> <target> <variant> [<variant> ...]   (variants: final, see build_mirror)
Writes <TEMP>/claude-ft1-<batch-label>.attempts.json (label -> attempt base, exit, counts). Nothing is written into
the repository; collect_runs.py later publishes sanitized copies.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
TEMP = Path(tempfile.gettempdir()).resolve()
python, batch, target, variants = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
rows = []
for variant in variants:
    mirror = Path(tempfile.mkdtemp(prefix=f"claude-ft1-mirror-{variant}-", dir=TEMP)) / "code"
    built = subprocess.run([python, "-I", "-B", str(TOOLS / "build_mirror.py"), variant, str(mirror)],
                           capture_output=True, text=True)
    if built.returncode:
        rows.append({"label": variant, "build_error": built.stderr[-300:]})
        print(json.dumps({"label": variant, "build_error": built.stderr[-200:]}), flush=True)
        continue
    env = dict(os.environ, CLAUDE_RUNNER_ROOT=str(mirror), CLAUDE_RUN_PREFIX=f"claude-ft1-{batch}")
    started = time.time()
    proc = subprocess.run([python, "-I", "-B", str(TOOLS / "run_gate.py"), python, variant, target],
                          env=env, capture_output=True, cwd=str(TEMP))
    try:
        summary = json.loads(proc.stdout.decode("ascii", errors="replace").strip().splitlines()[-1])
    except (ValueError, IndexError):
        summary = {"raw_error": proc.stderr.decode(errors="replace")[-300:]}
    summary.update(label=variant, build=json.loads(built.stdout), wall=round(time.time() - started, 1))
    rows.append(summary)
    print(json.dumps({k: summary.get(k) for k in ("label", "exit", "tests_run", "failures", "errors",
                                                  "isolation_violations", "wall")}), flush=True)
(TEMP / f"claude-ft1-{batch}.attempts.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
