"""Sensitivity: run the Repair #4 tests against the baseline (commit 163) runtime.

The baseline web_alarm (safety copy) gets only the pure policy table the tests
import (SETTLEMENT_ADMITS / settlement_admits), wired into nothing, so per-test
results stay visible instead of one import error.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SESSION = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-011_RC6_REPAIR4"
SHIM = '''

# --- sensitivity shim: the pure Repair #4 policy table, used by nothing at 163 ---
SETTLEMENT_ADMITS = {
    "ADOPT": frozenset({"ABORT"}),
    "ABORT": frozenset(),
    "ROLLBACK": frozenset({"ABORT", "RETRY"}),
}


def settlement_admits(settlement_action, action):
    return action in SETTLEMENT_ADMITS.get(settlement_action, frozenset())
'''

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shutil.copytree(SESSION / "safety_copies" / "web_alarm", root / "web_alarm")
    with open(root / "web_alarm" / "resolver_service.py", "a", encoding="utf-8", newline="\n") as fh:
        fh.write(SHIM)
    for name in ("test_web_alarm_recovery_coordinator_repair2.py", "test_web_alarm_recovery_coordinator_repair4.py"):
        shutil.copy2(REPO / name, root / name)
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", "test_web_alarm_recovery_coordinator_repair4"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    broken = sorted({m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR): (test_\w+)", proc.stderr, re.M)})
    names = sorted(set(re.findall(r"def (test_\w+)", (root / "test_web_alarm_recovery_coordinator_repair4.py").read_text(encoding="utf-8"))))
    print("failing on 163:", *broken, sep="\n  ")
    print("passing on 163:", *[n for n in names if n not in broken], sep="\n  ")
    print(f"\n{proc.stderr.strip().splitlines()[-1]}")
    print(f"TESTS {len(names)}; failing on 163: {len(broken)}; passing on 163: {len(names) - len(broken)}")
