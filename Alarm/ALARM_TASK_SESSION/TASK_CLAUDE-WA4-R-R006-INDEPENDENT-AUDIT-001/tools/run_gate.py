"""Launch the canonical guarded runner (wa4a_acceptance.py) for one attempt, with extra isolation.

Extra isolation on top of the runner guard (Git metadata / external sockets / non-Python children / writes
outside TEMP): LOCALAPPDATA/APPDATA/USERPROFILE-derived storage roots point into a disposable TEMP folder, so
default_storage_root() can never resolve to live Web Alarm state; PYTHONPYCACHEPREFIX points into TEMP so the
repository's existing __pycache__ is never read; -B / PYTHONDONTWRITEBYTECODE keep the tree byte-clean.
Usage: run_gate.py <python> <attempt-label> <target> [<target> ...]
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(os.environ.get("CLAUDE_RUNNER_ROOT") or r"M:\GitHub\ag_llm")  # attribution mirror only
TEMP = Path(tempfile.gettempdir()).resolve()
python, label, targets = sys.argv[1], sys.argv[2], sys.argv[3:]
base = Path(tempfile.mkdtemp(prefix=f"claude-wa4r006-{label}-", dir=TEMP))
out = base / "out"
env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "GIT_", "HTTP_PROXY", "HTTPS_PROXY",
                                                                       "ALL_PROXY"))}
for key in ("LOCALAPPDATA", "APPDATA"):
    (base / key.lower()).mkdir()
    env[key] = str(base / key.lower())
env["PYTHONPYCACHEPREFIX"] = str(base / "pycache")
env["PYTHONDONTWRITEBYTECODE"] = "1"
env["PYTHONUTF8"] = "1"
if os.environ.get("CLAUDE_EXTRA_PATH"):  # own probe module (TEMP); the runner still guards every child
    env["PYTHONPATH"] = os.environ["CLAUDE_EXTRA_PATH"]
argv = [python, "-X", "utf8", "-B", str(REPO / "wa4a_acceptance.py"),
        "--task", "CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001", "--output", str(out), *targets]
started = time.time()
with (base / "stdout.txt").open("wb") as so, (base / "stderr.txt").open("wb") as se:
    code = subprocess.run(argv, cwd=REPO, env=env, stdout=so, stderr=se).returncode
elapsed = round(time.time() - started, 3)
summary = {"label": label, "python": python, "argv": argv, "exit": code, "wall_seconds": elapsed, "base": str(base)}
results = out / "results.json"
if results.exists():
    r = json.loads(results.read_text(encoding="utf-8"))
    summary.update({k: r[k] for k in ("tests_run", "passed", "failures", "errors", "skips", "elapsed_seconds",
                                      "python", "successful")})
    summary["isolation_violations"] = len(r["isolation_violations"])
    summary["non_pass"] = [(t["test"], t["status"], (t.get("reason") or t.get("error") or "")[-300:])
                           for t in r["tests"] if t["status"] != "PASS"]
else:
    summary["results"] = "MISSING"
(base / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
