"""RED on the base: run the stage-1 tests against the stage-0 code, rebuilt in a TEMP mirror without Git.

The mirror copies top-level *.py / *.js and web_alarm/*.py, applies the inverse edits of reverse_check.py to the four
changed files (each must reproduce its stage-0 SHA-256) and removes the new web_alarm/ultra_chat.py. The new tests
must then fail: this shows they depend on the stage-1 code and not on the environment. Path-free JSON record.
Usage: red_on_base.py <python> <out.json>
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
source = (TOOLS / "reverse_check.py").read_text(encoding="utf-8")
namespace = {"__file__": str(TOOLS / "reverse_check.py")}
exec(source.split("\npreflight = json.loads")[0], namespace)
OPERATIONS, undo, PREFLIGHT = namespace["OPERATIONS"], namespace["undo"], namespace["PREFLIGHT"]
python, target = sys.argv[1], Path(sys.argv[2])
stage0 = json.loads(PREFLIGHT.read_text(encoding="utf-8"))["compared"]

dest = Path(tempfile.mkdtemp(prefix="claude-s1-base-"))
try:
    for path in list(REPO.glob("*.py")) + list(REPO.glob("*.js")):
        shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    (dest / "web_alarm" / "ultra_chat.py").unlink()
    rebuilt = {}
    for rel, operations in OPERATIONS.items():
        raw = (dest / rel).read_bytes()
        crlf = b"\r\n" in raw
        text, problems = undo(raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8"), operations)
        data = (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")
        rebuilt[rel] = hashlib.sha256(data).hexdigest() == stage0[rel]["stage0_sha256"] and not problems
        (dest / rel).write_bytes(data)
    if not all(rebuilt.values()):
        sys.exit("base not reproduced: " + json.dumps(rebuilt))
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s1", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S1-READONLY-UI-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    python_runs = {}
    for module in ("test_ultra_chat_read", "test_web_alarm_ultra_chat"):
        done = subprocess.run([python, str(GATE), python, "base-" + module[-10:], module], cwd=dest, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        summary = json.loads(done.stdout)
        python_runs[module] = {key: summary.get(key) for key in ("exit", "tests_run", "failures", "errors", "skips",
                                                                  "isolation_violations")}
        if summary.get("results") == "MISSING":  # the module could not even be imported: take the error from stderr
            lines = [line.strip() for line in (Path(summary["base"]) / "stderr.txt").read_text(
                encoding="utf-8", errors="replace").splitlines() if line.strip()]
            python_runs[module]["results"] = "MISSING (module import failed)"
            python_runs[module]["first_error"] = re.sub(r"[A-Za-z]:\\[^\s'\"]*", "<path>", lines[-1] if lines else "")[:200]
            continue
        python_runs[module]["first_error"] = re.sub(r"[A-Za-z]:\\[^\s'\"]*", "<path>", (summary.get("non_pass") or [["", "", ""]])[0][2].strip().splitlines()[-1] if summary.get("non_pass") else "")[:200]
    node_runs = {}
    for name in ("test_web_alarm_ultra_chat_ui.js", "test_web_alarm_evm_ui.js"):
        done = subprocess.run(["node", "--test", name], cwd=dest, capture_output=True, text=True, encoding="utf-8")
        node_runs[name] = {"exit": done.returncode,
                           "failed": re.findall(r"^not ok \d+ - (.+)$", done.stdout, re.M),
                           "passed": len(re.findall(r"^ok \d+ - ", done.stdout, re.M))}
finally:
    shutil.rmtree(dest, ignore_errors=True)
record = {"task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "purpose": "RED: stage-1 tests against the rebuilt stage-0 code",
          "base_rebuilt_from_inverse_edits": rebuilt, "python": python_runs, "node": node_runs}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"rebuilt": rebuilt, "python": {k: (v["exit"], v["errors"], v["failures"]) for k, v in python_runs.items()},
                  "node": {k: (v["exit"], len(v["failed"]), v["passed"]) for k, v in node_runs.items()}}, ensure_ascii=False))
