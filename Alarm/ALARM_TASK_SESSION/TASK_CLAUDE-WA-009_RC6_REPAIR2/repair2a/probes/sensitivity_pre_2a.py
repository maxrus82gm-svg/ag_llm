"""Run the Repair #2A CAS suite against the pre-#2A runtime (Repair #2 safety copies)."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
SAFE = HERE / "safety_copies"
OUT = HERE / "sensitivity_pre_2a.txt"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shutil.copytree(REPO / "web_alarm", root / "web_alarm", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("task_store.py", "state_machine.py", "manifest_store.py", "recovery_coordinator.py", "server.py"):
        shutil.copy2(SAFE / f"web_alarm__{name}", root / "web_alarm" / name)
    for test in ("test_web_alarm_state_machine_cas.py", "test_web_alarm_recovery_coordinator_repair2.py"):
        text = (REPO / test).read_text(encoding="utf-8")
        # the old runtime has no MicrotaskStatusConflict: give the module a stand-in name
        text = text.replace(
            "from web_alarm.task_store import MicrotaskStatusConflict, TaskStore",
            "from web_alarm.task_store import TaskStore\nclass MicrotaskStatusConflict(Exception):\n    pass",
        )
        (root / test).write_text(text, encoding="utf-8")
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", "test_web_alarm_state_machine_cas"],
                          cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [line for line in proc.stderr.splitlines() if re.search(r" \.\.\. (ok|FAIL|ERROR)$", line)]
text = "Repair #2A CAS suite against the PRE-#2A runtime:\n" + "\n".join(lines) + "\n" + proc.stderr.strip().splitlines()[-1] + "\n"
OUT.write_text(text, encoding="utf-8", newline="\n")
print(text)
