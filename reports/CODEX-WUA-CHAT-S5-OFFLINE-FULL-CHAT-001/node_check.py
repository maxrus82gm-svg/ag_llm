"""Record the Node VM suites. Their fetch functions are fixture-only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

package = Path(__file__).resolve().parent
root = package.parent.parent
files = ["test_web_alarm_ultra_chat_ui.js", "test_web_alarm_operator_ui.js", "test_web_alarm_evm_ui.js"]
command = ["node", "--test", *files]
env = {key: os.environ[key] for key in os.environ
       if not key.upper().startswith("GIGACHAT_") and key.upper() != "NODE_OPTIONS"}
version = subprocess.check_output(["node", "--version"], env=env).decode().strip()
start = time.monotonic()
result = subprocess.run(command, cwd=root, env=env, capture_output=True)
prefix = package / "evidence/js_final"
for suffix, content in ((".stdout.txt", result.stdout), (".stderr.txt", result.stderr)):
    with prefix.with_suffix(suffix).open("xb") as handle:
        handle.write(content)
metadata = dict(command=command, cwd=str(root), node=version, exit_code=result.returncode,
                elapsed_seconds=time.monotonic() - start,
                source_sha256={name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                               for name in [*files, "web_alarm/ui.py"]})
with prefix.with_suffix(".result.json").open("x", encoding="utf-8") as handle:
    json.dump(metadata, handle, indent=2)
print(result.stdout.decode("utf-8", errors="replace")[-650:])
raise SystemExit(result.returncode)
