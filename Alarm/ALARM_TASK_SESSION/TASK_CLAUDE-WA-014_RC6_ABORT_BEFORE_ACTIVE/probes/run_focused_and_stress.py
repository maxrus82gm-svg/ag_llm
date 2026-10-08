"""Focused regression and stress repeats for WA-014 (each module in its own process).

Run from the repository root: python -B <this file> focused|stress
Writes ../focused_regression.txt or ../stress_repeats.txt (Markdown tables).
"""
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path.cwd()
SESSION = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA-014_RC6_ABORT_BEFORE_ACTIVE"

FOCUSED = [
    ("WA-014 (new)", "test_web_alarm_recovery_coordinator_wa014"),
    ("Repair #4B (B4 updated)", "test_web_alarm_recovery_coordinator_repair4b"),
    ("Repair #4A", "test_web_alarm_recovery_coordinator_repair4a"),
    ("Repair #4", "test_web_alarm_recovery_coordinator_repair4"),
    ("Repair #3", "test_web_alarm_recovery_coordinator_repair3"),
    ("State machine CAS (#2A)", "test_web_alarm_state_machine_cas"),
    ("Repair #2", "test_web_alarm_recovery_coordinator_repair2"),
    ("Repair #1", "test_web_alarm_recovery_coordinator_repair1"),
    ("RC-6", "test_web_alarm_recovery_coordinator"),
    ("RC-6 adversarial", "test_web_alarm_recovery_coordinator_adversarial"),
    ("RC-6 concurrency", "test_web_alarm_recovery_coordinator_concurrency"),
    ("RC-4", "test_web_alarm_rollback"),
    ("RC-4 concurrency", "test_web_alarm_rollback_concurrency"),
    ("RC-5 projection", "test_web_alarm_projection"),
    ("RC-5 projection concurrency", "test_web_alarm_projection_concurrency"),
    ("RC-2 Resolver", "test_web_alarm_resolver"),
    ("RC-2 Resolver concurrency", "test_web_alarm_resolver_concurrency"),
    ("RC-3 claims", "test_web_alarm_target_claims"),
    ("RC-3 claims concurrency", "test_web_alarm_target_claims_concurrency"),
    ("RC-1 contract", "test_web_alarm_operation_contract"),
    ("Operation store", "test_web_alarm_operation_store"),
    ("Operation store concurrency", "test_web_alarm_operation_store_concurrency"),
    ("State machine", "test_web_alarm_state_machine"),
    ("Task store", "test_web_alarm_task_store"),
    ("Manifest store", "test_web_alarm_manifest_store"),
    ("Recovery report acceptance", "test_web_alarm_recovery_report_acceptance"),
    ("Server", "test_web_alarm_server"),
    ("CLI", "test_web_alarm_cli"),
]
STRESS = [
    ("test_web_alarm_recovery_coordinator_wa014", 5),
    ("test_web_alarm_recovery_coordinator_repair4b", 2),
    ("test_web_alarm_rollback_concurrency", 3),
    ("test_web_alarm_recovery_coordinator_repair4a", 3),
    ("test_web_alarm_recovery_coordinator_repair4", 3),
    ("test_web_alarm_recovery_coordinator_repair3", 2),
    ("test_web_alarm_recovery_coordinator_repair2", 2),
    ("test_web_alarm_recovery_coordinator_concurrency", 3),
    ("test_web_alarm_state_machine_cas", 2),
    ("test_web_alarm_target_claims_concurrency", 2),
    ("test_web_alarm_projection_concurrency", 2),
]


def run(module):
    start = time.time()
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", module], cwd=REPO,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    ran = re.search(r"^Ran (\d+) test", proc.stderr, re.M)
    last = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "?"
    return (int(ran.group(1)) if ran else 0), last, proc.returncode, round(time.time() - start)


mode = sys.argv[1]
lines = []
if mode == "focused":
    lines += ["| Набор | Модуль | Тестов | Итог |", "| --- | --- | --- | --- |"]
    total = ok = 0
    for label, module in FOCUSED:
        n, last, code, _ = run(module)
        total += n
        ok += n if code == 0 else 0
        lines.append(f"| {label} | `{module}` | {n} | {last} (exit {code}) |")
        print(lines[-1], flush=True)
    lines.append(f"\nИтого: {len(FOCUSED)} модулей, {total} тестов; модулей с exit 0 — "
                 f"{sum(1 for l in lines if l.endswith('(exit 0) |'))}")
    (SESSION / "focused_regression.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
else:
    lines += ["| Модуль | Повтор | Тестов | Итог | сек |", "| --- | --- | --- | --- | --- |"]
    for module, times in STRESS:
        for i in range(1, times + 1):
            n, last, code, secs = run(module)
            lines.append(f"| `{module}` | {i}/{times} | {n} | {last} | {secs} |")
            print(lines[-1], flush=True)
    passed = sum(1 for l in lines[2:] if "| OK" in l)
    lines.append(f"\nИтого: {passed}/{len(lines) - 2} повторов OK")
    (SESSION / "stress_repeats.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(lines[-1])
