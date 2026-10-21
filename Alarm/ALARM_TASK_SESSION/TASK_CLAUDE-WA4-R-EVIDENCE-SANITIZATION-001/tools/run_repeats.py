"""TEST-FLAKY-01 bounded repeats: run one target N times through run_gate.py on the current tree and on a baseline
mirror (this TASK's module removed), one attempt at a time.
Usage: run_repeats.py <python> <batch-label> <target> <n>
Writes <TEMP>/claude-evsan-<batch-label>.attempts.json; nothing is written into the repository.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
TEMP = Path(tempfile.gettempdir()).resolve()
python, batch, target, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
mirror = Path(tempfile.mkdtemp(prefix=f"claude-evsan-mirror-{batch}-", dir=TEMP)) / "code"
subprocess.run([python, "-I", "-B", str(TOOLS / "build_mirror.py"), "baseline", str(mirror)], check=True,
               capture_output=True)
rows = []
for tree, root in (("current", None), ("baseline", str(mirror))):
    for i in range(1, n + 1):
        env = dict(os.environ, CLAUDE_RUN_PREFIX=f"claude-evsan-{batch}")
        env.pop("CLAUDE_RUNNER_ROOT", None)
        if root:
            env["CLAUDE_RUNNER_ROOT"] = root
        proc = subprocess.run([python, "-I", "-B", str(TOOLS / "run_gate.py"), python, f"{tree}-{i:02d}", target],
                              env=env, capture_output=True, cwd=str(TEMP))
        row = json.loads(proc.stdout.decode("ascii", errors="replace").strip().splitlines()[-1])
        row["tree"] = tree
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ("label", "exit", "tests_run", "failures", "errors",
                                                  "isolation_violations")}), flush=True)
(TEMP / f"claude-evsan-{batch}.attempts.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
for tree in ("current", "baseline"):
    sub = [r for r in rows if r["tree"] == tree]
    print(tree, "red attempts:", sum(1 for r in sub if r["exit"]), "of", len(sub))
