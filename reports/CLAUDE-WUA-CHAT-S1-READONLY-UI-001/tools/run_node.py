"""Run the Web Alarm page tests with node --test and keep a path-free record (test names, ok / not ok, counts).
Usage: run_node.py <out.json> <test.js> [<test.js> ...]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
target, files = Path(sys.argv[1]), sys.argv[2:]
version = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
runs = []
for name in files:
    done = subprocess.run(["node", "--test", name], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    tests = [{"test": m.group(2), "status": "PASS" if m.group(1) == "ok" else "FAIL"}
             for m in re.finditer(r"^(ok|not ok) \d+ - (.+)$", done.stdout, re.M)]
    counts = {key: int(m.group(1)) for key in ("tests", "pass", "fail", "skipped", "cancelled")
              for m in [re.search(rf"^# {key} (\d+)$", done.stdout, re.M)] if m}
    runs.append({"file": name, "exit": done.returncode, **counts, "results": tests})
    print(json.dumps({"file": name, "exit": done.returncode, **counts}))
record = {"task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "runner": "node --test (node:vm DOM adapter, no network)",
          "node": version, "runs": runs}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
