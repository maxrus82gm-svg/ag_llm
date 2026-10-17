"""Print compact facts of selected tests from a results.json (read-only). Usage: show_facts.py <results.json> <substr>..."""
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for test in data["tests"]:
    if not any(s in test["test"] for s in sys.argv[2:]):
        continue
    print("=====", test["test"].split(".")[-1], test["status"])
    for fact in test.get("facts", []):
        for key, value in fact.items():
            if key.startswith("reopen_"):
                before = value["before"]
                print(" ", key, "BEFORE views:", json.dumps(before["views"], ensure_ascii=True)[:900])
                print(" ", key, "BEFORE raw:", json.dumps({k: before["raw"][k] for k in
                      ("microtasks", "operations", "plan_current", "checkpoint_status", "location", "payload_files")},
                      ensure_ascii=True)[:500])
                for f in value["followups"]:
                    print("   FOLLOW", f["step"], json.dumps(f["outcome"], ensure_ascii=True)[:500])
            elif key not in ("task", "test"):
                print(" ", key, json.dumps(value, ensure_ascii=True, default=str)[:700])
