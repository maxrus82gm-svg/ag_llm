"""Sensitivity: run the Repair #4A tests against the baseline (commit 164) runtime.

The baseline web_alarm (safety copy) gets only the constant the tests import
(_ABORT_FROM_PRE_EXECUTION), wired into nothing, so per-test results stay
visible instead of one import error.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SESSION = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-012_RC6_REPAIR4A"
SHIM = '''

# --- sensitivity shim: the Repair #4A constant the tests import, used by nothing at 164 ---
_ABORT_FROM_PRE_EXECUTION = {
    MicrotaskStatus.PLANNED,
    MicrotaskStatus.BACKUP_VERIFIED,
    MicrotaskStatus.READY,
    MicrotaskStatus.BLOCKED_PREPARE,
}
'''

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shutil.copytree(SESSION / "safety_copies" / "web_alarm", root / "web_alarm")
    with open(root / "web_alarm" / "recovery_coordinator.py", "a", encoding="utf-8", newline="\n") as fh:
        fh.write(SHIM)
    for name in ("test_web_alarm_recovery_coordinator_repair2.py", "test_web_alarm_recovery_coordinator_repair4.py", "test_web_alarm_recovery_coordinator_repair4a.py"):
        shutil.copy2(REPO / name, root / name)
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", "test_web_alarm_recovery_coordinator_repair4a"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    broken = sorted({m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR): (test_\w+)", proc.stderr, re.M)})
    names = sorted(set(re.findall(r"def (test_\w+)", (root / "test_web_alarm_recovery_coordinator_repair4a.py").read_text(encoding="utf-8"))))
    print("failing on 164:", *broken, sep="\n  ")
    print("passing on 164:", *[n for n in names if n not in broken], sep="\n  ")
    print(f"\n{proc.stderr.strip().splitlines()[-1]}")
    print(f"TESTS {len(names)}; failing on 164: {len(broken)}; passing on 164: {len(names) - len(broken)}")
