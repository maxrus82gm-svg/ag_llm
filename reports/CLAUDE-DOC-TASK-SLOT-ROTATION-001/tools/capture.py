"""Run tools/task_slot_rotate.py with the given arguments and save its JSON protocol as evidence.
Usage: capture.py <evidence-name> <script arguments...>
The evidence file keeps the command (relative paths only), the exit code and the protocol, LF line endings.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]


def main():
    name, args = sys.argv[1], sys.argv[2:]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", *args], cwd=REPO, env=env,
                          capture_output=True)
    protocol = json.loads(done.stdout.decode("utf-8"))
    record = {"command": "python -B tools/task_slot_rotate.py " + " ".join(f'"{a}"' if " " in a else a for a in args),
              "exit": done.returncode, "protocol": protocol}
    out = PACKAGE / "evidence" / f"{name}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"exit": done.returncode, "result": protocol.get("result"),
                      "problems": protocol.get("problems", [])}, ensure_ascii=False))
    sys.exit(done.returncode)


if __name__ == "__main__":
    main()
