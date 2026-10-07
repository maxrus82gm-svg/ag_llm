"""Run the new Repair #2 suite against the unrepaired runtime (git HEAD = commit 160/161 runtime)."""
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
OUT = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-009_RC6_REPAIR2" / "sensitivity_old_runtime.txt"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    archive = subprocess.run(["git", "archive", "HEAD", "web_alarm"], cwd=REPO, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root)
    test = (REPO / "test_web_alarm_recovery_coordinator_repair2.py").read_text(encoding="utf-8")
    # the old runtime has no shared lock-order helper: give the test module a stand-in
    test = test.replace(
        "from web_alarm.target_claim_store import (\n    TargetClaimStore,\n    physical_target_key,\n    target_hash,\n    target_lock_order,\n)",
        "from web_alarm.target_claim_store import TargetClaimStore, physical_target_key, target_hash\n"
        "def target_lock_order(keys):\n    return sorted(set(keys), key=target_hash)",
    )
    (root / "test_web_alarm_recovery_coordinator_repair2.py").write_text(test, encoding="utf-8")
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", "test_web_alarm_recovery_coordinator_repair2"],
                          cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
lines = [line for line in proc.stderr.splitlines() if re.search(r" \.\.\. (ok|FAIL|ERROR)$", line)]
summary = proc.stderr.strip().splitlines()[-1]
text = "Repair #2 suite against the UNREPAIRED runtime (git HEAD web_alarm):\n" + "\n".join(lines) + f"\n{summary}\n"
OUT.write_text(text, encoding="utf-8", newline="\n")
print(text)
