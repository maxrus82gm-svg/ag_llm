"""Repeat the RC-5 'completion vs new operation' race round and print the text of any CloseoutError."""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, r"M:\GitHub\ag_llm")
import test_web_alarm_projection_concurrency as t  # noqa: E402

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
t.CHILD = t.CHILD.replace(
    'result = "FAILED:" + type(exc).__name__',
    'result = "FAILED:" + type(exc).__name__ + ":" + str(exc)[:300]',
)
case = t.ProjectionRaceTests("test_completion_never_admits_new_open_state")
outcomes = Counter()
for index in range(ROUNDS):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        storage = case.setup_task(root, verified=True)
        jobs = [("a", "complete"), ("b1", "begin"), ("b2", "begin"), ("c1", "microtask")]
        results = case.run_jobs(storage, root, jobs, jitter=bool(index % 2))
    by_name = {r["name"]: r["result"] for r in results}
    outcomes[by_name["a"].split(":")[0] + ":" + by_name["a"].split(":")[1] if by_name["a"].startswith("FAILED") else by_name["a"]] += 1
    if by_name["a"] not in ("COMPLETED", "REJECTED"):
        print(f"round {index}: a = {by_name['a']}")
        print("   others:", json.dumps({k: v for k, v in by_name.items() if k != "a"}))
print("outcomes:", dict(outcomes))
