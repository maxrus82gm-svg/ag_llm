"""Repeat the RC-4 'rollback vs normal owner' race round and record unexpected RC-4 outcomes."""
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"M:\GitHub\ag_llm")
import test_web_alarm_rollback_concurrency as t  # noqa: E402

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
case = t.RollbackRaceTests("test_rollback_and_normal_owner_never_both_win")
statuses = Counter()
for index in range(ROUNDS):
    with tempfile.TemporaryDirectory() as tmp:
        results, record, final, events, _ = case.round(Path(tmp), jitter=bool(index % 2))
    statuses[record["status"]] += 1
    if record["status"] not in ("VERIFIED", "PRESERVED"):
        print(f"round {index}: {record['status']} last_attempt={record.get('last_attempt')}")
        for target in record["targets"]:
            print("   ", target["source_path"], target["status"], target.get("failure"))
        print("    results:", results, "| restored events:", events["ROLLBACK_TARGET_RESTORED"])
print("statuses:", dict(statuses))
