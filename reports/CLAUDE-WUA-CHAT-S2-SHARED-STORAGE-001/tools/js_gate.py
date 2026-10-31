"""Run the Web Alarm page tests (node --test, node:vm DOM adapter, no network) and record names and verdicts.
Usage: js_gate.py <out.json> <purpose> [test file ...]   (default: the EVM, Ultra Chat and operator page tests)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FILES = tuple(sys.argv[3:]) or ("test_web_alarm_evm_ui.js", "test_web_alarm_ultra_chat_ui.js", "test_web_alarm_operator_ui.js")
node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
rows = {}
for name in FILES:
    done = subprocess.run(["node", "--test", "--test-reporter=tap", name], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    tests = [{"test": m.group(3), "status": "PASS" if m.group(1) == "ok" else "FAIL"}
             for m in re.finditer(r"^(ok|not ok) (\d+) - (.+)$", done.stdout, re.M)]
    rows[name] = {"exit": done.returncode, "tests": len(tests), "pass": sum(t["status"] == "PASS" for t in tests),
                  "fail": sum(t["status"] == "FAIL" for t in tests), "results": tests}
record = {"task": "CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", "purpose": sys.argv[2], "node": node,
          "tests_run": sum(r["tests"] for r in rows.values()), "pass": sum(r["pass"] for r in rows.values()),
          "fail": sum(r["fail"] for r in rows.values()), "files": rows}
Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: record[k] for k in ("tests_run", "pass", "fail")}))
