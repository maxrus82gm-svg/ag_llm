"""Gate A / Gate C driver: build a TEMP mirror per variant and run the target module through run_gate.py.

Usage: run_mutants.py <python> <batch-label> <variant> [<variant> ...]   (variants: baseline, M1-..., see build_mirror)
Writes <TEMP>/claude-esrep-<batch-label>.attempts.json (label -> attempt base, exit, counts). Nothing is written
into the repository; collect_runs.py later publishes sanitized copies.
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
TARGET = "test_web_alarm_evidence_sanitizer"
python, batch, variants = sys.argv[1], sys.argv[2], sys.argv[3:]
rows = []
for variant in variants:
    mirror = Path(tempfile.mkdtemp(prefix=f"claude-esrep-mirror-{variant}-", dir=TEMP)) / "code"
    built = subprocess.run([python, "-I", "-B", str(TOOLS / "build_mirror.py"), variant, str(mirror)],
                           capture_output=True, text=True)
    if built.returncode:
        rows.append({"label": variant, "build_error": built.stderr[-300:]})
        continue
    env = dict(os.environ, CLAUDE_RUNNER_ROOT=str(mirror), CLAUDE_RUN_PREFIX=f"claude-esrep-{batch}")
    started = time.time()
    proc = subprocess.run([python, "-I", "-B", str(TOOLS / "run_gate.py"), python, variant, TARGET],
                          env=env, capture_output=True, cwd=str(TEMP))
    try:
        summary = json.loads(proc.stdout.decode("ascii", errors="replace").strip().splitlines()[-1])
    except (ValueError, IndexError):
        summary = {"raw_error": proc.stderr.decode(errors="replace")[-300:]}
    summary.update(label=variant, build=json.loads(built.stdout), wall=round(time.time() - started, 1))
    rows.append(summary)
    print(json.dumps({k: summary.get(k) for k in ("label", "exit", "tests_run", "failures", "errors",
                                                  "isolation_violations")}), flush=True)
(TEMP / f"claude-esrep-{batch}.attempts.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
