"""Deliberate source weakenings, tested only on synthetic TEMP cards."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
label = sys.argv[1] if len(sys.argv) > 1 else 'mutants-final'
assert re.fullmatch(r'[a-z0-9-]{1,40}', label)
source = (ROOT / "tools/task_slot_rotate.py").read_text(encoding="utf-8")
cases = [
    ("archive_match", "if not parts or parts[0] != copy or len(parts[1]) != expected_amends:", "if False:",
     "AutomaticArchive.test_a04_previous_snapshot_conflict_is_never_overwritten"),
    ("snapshot_readback", "if bounded_bytes(p) != payload:", "if False:",
     "AutomaticArchive.test_a16_snapshot_readback_failure_keeps_card"),
    ("repeat_write", "if new != data:", "if True:", "AutomaticArchive.test_a07_repeat_is_successful_without_card_write"),
    ("assign_waiting", 'if check["block1"]["state"] != "WAITING":', "if False:",
     "TaskAssignment.test_s04_active_task_cannot_be_overwritten"),
    ("assign_expected_hash", 'if check["card_sha256"] != sha256(data) or args.expected_card_sha256 != sha256(data):', "if False:",
     "TaskAssignment.test_s06_stale_observation_cannot_assign_even_if_still_waiting"),
]
rows = []
for name, needle, replacement, selector in cases:
    assert needle in source
    folder = OUT / label / name
    folder.mkdir(parents=True, exist_ok=True)
    variant = folder / "task_slot_rotate.py"
    variant.write_text(source.replace(needle, replacement), encoding="utf-8")
    env = dict(os.environ, TASK_SLOT_ROTATE_UNDER_TEST=str(variant), PYTHONIOENCODING="utf-8")
    cmd = [sys.executable, "-B", "-m", "unittest", "tools.test_task_slot_rotate." + selector]
    run = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    log = run.stdout + run.stderr
    (folder / "result.txt").write_text(log, encoding="utf-8")
    caught = run.returncode == 1 and "FAILED (failures=1)" in log and "ERROR:" not in log
    rows.append({"mutant": name, "selector": selector, "exit_code": run.returncode, "caught": caught,
                 "source_sha256": hashlib.sha256(variant.read_bytes()).hexdigest()})
(OUT / (label + '.json')).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"executed": len(rows), "caught": sum(r["caught"] for r in rows)}))
raise SystemExit(0 if all(r["caught"] for r in rows) else 1)
