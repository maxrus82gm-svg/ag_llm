"""Sensitivity: run the Repair #4B tests against the baseline (commit 165) runtime.

The baseline web_alarm (safety copy) only gets the two names the tests import
(EXECUTED_STATUSES, rollback_refusal returning "no refusal"), wired into
nothing, so per-test results stay visible instead of one import error.
Run from anywhere: python -B <this file>
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SESSION = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-013_RC6_REPAIR4B"
SHIM = '''

# --- sensitivity shim: the Repair #4B names the tests import, used by nothing at 165 ---
EXECUTED_STATUSES = frozenset({"ACTIVE", "DONE", "UNKNOWN_AFTER_DISCONNECT", "FAILED_VERIFICATION"})


def rollback_refusal(task_id, microtask_id, *, tasks, operations):
    return None
'''
MODULE = "test_web_alarm_recovery_coordinator_repair4b"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shutil.copytree(SESSION / "safety_copies" / "web_alarm", root / "web_alarm")
    with open(root / "web_alarm" / "microtask_gate.py", "a", encoding="utf-8", newline="\n") as fh:
        fh.write(SHIM)
    for name in ("test_web_alarm_recovery_coordinator_repair2.py", "test_web_alarm_recovery_coordinator_repair4.py",
                 "test_web_alarm_recovery_coordinator_repair4a.py", MODULE + ".py"):
        shutil.copy2(REPO / name, root / name)
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", MODULE],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    broken = sorted({m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR): (test_\w+)", proc.stderr, re.M)})
    names = sorted(set(re.findall(r"def (test_\w+)", (root / (MODULE + ".py")).read_text(encoding="utf-8"))))
    print("failing on 165:", *broken, sep="\n  ")
    print("passing on 165:", *[n for n in names if n not in broken], sep="\n  ")
    print(f"\n{proc.stderr.strip().splitlines()[-1]}")
    print(f"TESTS {len(names)}; failing on 165: {len(broken)}; passing on 165: {len(names) - len(broken)}")
