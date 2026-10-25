"""Launch the canonical guarded runner (wa4a_acceptance.py) for one attempt, with extra isolation.

Same isolation as the earlier per-TASK wrappers (LOCALAPPDATA/APPDATA and pycache redirected into a disposable
TEMP folder, -B, no PYTHON*/GIT_*/proxy variables), but the repository root is derived from this file's location
instead of being written into the source, and the console line is ASCII only. Everything this script writes lives
in TEMP; the published evidence is produced later by collect_runs.py through web_alarm.evidence_sanitizer.
Usage: run_gate.py <python> <attempt-label> <target> [<target> ...]
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(os.environ.get("CLAUDE_RUNNER_ROOT") or Path(__file__).resolve().parents[4])
TEMP = Path(tempfile.gettempdir()).resolve()
python, label, targets = sys.argv[1], sys.argv[2], sys.argv[3:]
base = Path(tempfile.mkdtemp(prefix=f"{os.environ.get('CLAUDE_RUN_PREFIX', 'claude-wua1')}-{label}-", dir=TEMP))
out = base / "out"
env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "GIT_", "HTTP_PROXY", "HTTPS_PROXY",
                                                                       "ALL_PROXY"))}
for key in ("LOCALAPPDATA", "APPDATA"):
    (base / key.lower()).mkdir()
    env[key] = str(base / key.lower())
env["PYTHONPYCACHEPREFIX"] = str(base / "pycache")
env["PYTHONDONTWRITEBYTECODE"] = "1"
env["PYTHONUTF8"] = "1"
if os.environ.get("CLAUDE_EXTRA_PATH"):
    env["PYTHONPATH"] = os.environ["CLAUDE_EXTRA_PATH"]
argv = [python, "-X", "utf8", "-B", str(REPO / "wa4a_acceptance.py"),
        "--task", os.environ.get("CLAUDE_TASK_LABEL", "CLAUDE-WUA-1-EVM-CONNECTIONS-001"), "--output", str(out),
        *targets]
started = time.time()
with (base / "stdout.txt").open("wb") as so, (base / "stderr.txt").open("wb") as se:
    code = subprocess.run(argv, cwd=REPO, env=env, stdout=so, stderr=se).returncode
summary = {"label": label, "argv": argv, "exit": code, "wall_seconds": round(time.time() - started, 3),
           "base": str(base), "runner_root": str(REPO)}
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
print(json.dumps({k: summary.get(k) for k in ("label", "exit", "tests_run", "failures", "errors", "skips",
                                              "isolation_violations", "base")}, ensure_ascii=True))
