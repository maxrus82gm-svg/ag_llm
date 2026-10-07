"""Sensitivity: run the Repair #3 tests against the baseline (commit 162) runtime.

Copies the repository's baseline web_alarm (safety copy) plus the test modules it
imports into a temp tree and runs test_web_alarm_recovery_coordinator_repair3
there. A regression test is sensitive when it fails on the pre-repair code.
The microtask_gate module does not exist at 162: an import-level failure would
hide per-test results, so the baseline tree gets a tiny shim that exposes the
pure functions the tests import (no gate is wired into any baseline code path).
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SESSION = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-010_RC6_REPAIR3"
SHIM = '''"""Sensitivity shim for the 162 runtime: pure helpers only, wired into nothing."""
from .models import MicrotaskStatus
from .projection import settlement_lifecycle_target


def effective_settlement_target(actions, microtask_status):
    return settlement_lifecycle_target(list(actions))  # 162: no VERIFIED absorption


def execution_refusal(*args, **kwargs):
    return None  # 162: no microtask-level gate


def verification_refusal(projection, microtask_id):
    return None  # 162: no VERIFIED admission gate
'''

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shutil.copytree(SESSION / "safety_copies" / "web_alarm", root / "web_alarm")
    (root / "web_alarm" / "microtask_gate.py").write_text(SHIM, encoding="utf-8")
    for name in ("test_web_alarm_recovery_coordinator_repair2.py", "test_web_alarm_recovery_coordinator_repair3.py"):
        shutil.copy2(REPO / name, root / name)
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", "test_web_alarm_recovery_coordinator_repair3"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    lines = [l for l in proc.stderr.splitlines() if re.search(r" \.\.\. (ok|FAIL|ERROR)$", l)]
    print("\n".join(lines))
    # authoritative per-test verdicts: the FAIL/ERROR headers of the unittest report
    broken = sorted({m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR): (test_\w+)", proc.stderr, re.M)})
    names = sorted(set(re.findall(r"def (test_\w+)", (root / "test_web_alarm_recovery_coordinator_repair3.py").read_text(encoding="utf-8"))))
    print("\nfailing on 162:", *broken, sep="\n  ")
    print("passing on 162:", *[n for n in names if n not in broken], sep="\n  ")
    print(f"\n{proc.stderr.strip().splitlines()[-1]}")
    print(f"TESTS {len(names)}; failing on 162: {len(broken)}; passing on 162: {len(names) - len(broken)}")
