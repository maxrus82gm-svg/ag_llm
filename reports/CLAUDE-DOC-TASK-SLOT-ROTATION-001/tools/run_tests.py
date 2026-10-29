"""Run tools/test_task_slot_rotate.py in a fresh process and save the per-test result as evidence (no local paths).
Usage: run_tests.py <evidence-name> [--purpose TEXT]
Env TASK_SLOT_ROTATE_UNDER_TEST (optional) selects another copy of the script (mutants).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
TESTS = "tools/test_task_slot_rotate.py"
LINE = re.compile(r"^(test_\w+) \([\w.]+\)(?: \.\.\. | \n)?.*?\.\.\. (ok|FAIL|ERROR|skipped.*)$")


def run(env_extra=None):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", **(env_extra or {})}
    done = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", TESTS], cwd=REPO, env=env,
                          capture_output=True, timeout=600)
    text = done.stderr.decode("utf-8", errors="replace")
    per_test = {}
    for line in text.splitlines():
        match = LINE.match(line)
        if match:
            status = match.group(2)
            per_test[match.group(1)] = "SKIP" if status.startswith("skipped") else {"ok": "PASS"}.get(status, status)
    ran = re.search(r"^Ran (\d+) tests?", text, re.M)
    return {"exit": done.returncode, "tests_run": int(ran.group(1)) if ran else 0, "per_test": per_test,
            "pass": sum(v == "PASS" for v in per_test.values()), "fail": sum(v == "FAIL" for v in per_test.values()),
            "errors": sum(v == "ERROR" for v in per_test.values()), "skips": sum(v == "SKIP" for v in per_test.values()),
            "parsed_all": len(per_test) == (int(ran.group(1)) if ran else -1)}


def main():
    name = sys.argv[1]
    purpose = sys.argv[sys.argv.index("--purpose") + 1] if "--purpose" in sys.argv else ""
    result = run()
    record = {"purpose": purpose, "command": f"python -B -m unittest -v {TESTS}",
              "python": sys.version.split()[0],
              "script_sha256": hashlib.sha256((REPO / "tools/task_slot_rotate.py").read_bytes()).hexdigest(),
              "tests_sha256": hashlib.sha256((REPO / TESTS).read_bytes()).hexdigest(), **result}
    out = PACKAGE / "evidence" / f"{name}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: record[k] for k in ("exit", "tests_run", "pass", "fail", "errors", "skips", "parsed_all")}))


if __name__ == "__main__":
    main()
