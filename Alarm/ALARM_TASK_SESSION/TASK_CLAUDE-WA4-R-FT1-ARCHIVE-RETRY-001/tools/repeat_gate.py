"""TEST-FLAKY bounded repeats: run one selector N times through run_gate.py in a given runner root.

Usage: repeat_gate.py <python> <batch-label> <runner-root|repo> <count> <target> [<target> ...]
Every repeat is a separate guarded runner process (fresh TEMP attempt). Per repeat the exit code, counts, isolation
lines and the masked shape of each isolation reason are recorded; nothing is dropped, the first failure included.
Writes <TEMP>/claude-ft1-<batch-label>.repeats.json. The repository is never written.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
TEMP = Path(tempfile.gettempdir()).resolve()
python, batch, root, count, targets = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5:]


def shape(reason):
    text = reason.replace("\\\\?\\", "<PREFIX>")
    for form in (str(TEMP), str(TEMP).lower()):
        text = text.replace(form, "<TEMP>")
    text = re.sub(r"(?i)[a-z]:\\\$extend\\\$deleted\\[0-9a-f]+", "<DRIVE>:\\$Extend\\$Deleted\\<ID>", text)
    text = re.sub(r"<TEMP>\\[^\\]+", "<TEMP>\\<FIXTURE>", text)
    return text if "<TEMP>" in text or "$Deleted" in text else "<OTHER-FORM>"


rows = []
for index in range(1, count + 1):
    env = dict(os.environ, CLAUDE_RUN_PREFIX=f"claude-ft1-{batch}")
    if root != "repo":
        env["CLAUDE_RUNNER_ROOT"] = root
    proc = subprocess.run([python, "-I", "-B", str(TOOLS / "run_gate.py"), python, f"r{index:02d}", *targets],
                          env=env, capture_output=True, cwd=str(TEMP))
    try:
        summary = json.loads(proc.stdout.decode("ascii", errors="replace").strip().splitlines()[-1])
    except (ValueError, IndexError):
        summary = {"raw_error": proc.stderr.decode(errors="replace")[-300:]}
    base = Path(summary.get("base", ""))
    shapes = []
    results = base / "out" / "results.json"
    if summary.get("base") and results.exists():
        for entry in json.loads(results.read_text(encoding="utf-8"))["isolation_violations"]:
            try:
                shapes.append(shape(entry["reason"]))
            except (KeyError, TypeError):
                shapes.append("<UNPARSED>")
    row = {"repeat": index, "exit": summary.get("exit"), "tests_run": summary.get("tests_run"),
           "failures": summary.get("failures"), "errors": summary.get("errors"),
           "isolation_violations": summary.get("isolation_violations"), "isolation_shapes": shapes,
           "attempt": base.name}
    rows.append(row)
    print(json.dumps({k: row[k] for k in ("repeat", "exit", "failures", "errors", "isolation_violations")}), flush=True)
(TEMP / f"claude-ft1-{batch}.repeats.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
