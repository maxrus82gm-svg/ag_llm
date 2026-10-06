"""Read-only RC-6 check of live WEB-02 storage: recover must stop before any step on completed TASKs."""
import hashlib
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, r"M:\GitHub\ag_llm")
ROOT = Path(os.environ["LOCALAPPDATA"]) / "WebAlarmWorkspace"


def tree():
    outer = hashlib.sha256()
    items = sorted(ROOT.rglob("*"))
    for path in items:
        rel = path.relative_to(ROOT).as_posix()
        outer.update(rel.encode() + b"\0" + (hashlib.sha256(path.read_bytes()).hexdigest().encode()
                                             if path.is_file() else b"<dir>") + b"\n")
    return sum(1 for p in items if p.is_file()), sum(1 for p in items if p.is_dir()), outer.hexdigest()


before = tree()
from web_alarm.recovery_coordinator import RecoveryCoordinator  # noqa: E402


def forbidden(self, task_id, projection, action):
    raise AssertionError(f"live storage: coordinator tried to perform {action}")


with mock.patch.object(RecoveryCoordinator, "_perform", forbidden):
    for task_id in ("WA-3.6", "WA-3.7"):
        result = RecoveryCoordinator(ROOT).recover(task_id)
        print(task_id, "->", result["state"], "| steps", result["performed_steps"], "| recovery", result["recovery_state"])
after = tree()
print("before", before)
print("after ", after)
print("UNCHANGED" if before == after else "CHANGED!")
