"""Capture exact raw child outputs and exit; never overwrite an earlier run."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("label")
parser.add_argument("--network", choices=("none", "loopback"), default="none")
parser.add_argument("args", nargs=argparse.REMAINDER)
options = parser.parse_args()
package = Path(__file__).resolve().parent
root = package.parent.parent
prefix = package / "evidence" / options.label
assert not prefix.with_suffix(".result.json").exists(), "Preserve previous evidence"
secret_keys = {"GIGACHAT_CREDENTIALS", "GIGACHAT_SCOPE", "GIGACHAT_ACCESS_TOKEN"}
# Do not even read the real credential values when constructing the child env.
env = {key: os.environ[key] for key in os.environ if key.upper() not in secret_keys}
env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
           PYTHONPATH=str(package / "guard") + os.pathsep + str(root),
           ORDINARY_GUARD_LOG=str(prefix.with_suffix(".guard.jsonl")),
           ORDINARY_GUARD_NETWORK=options.network, ORDINARY_GUARD_ROOT=str(root))
args = options.args[1:] if options.args[:1] == ["--"] else options.args
command = [sys.executable, "-B", "-X", "utf8", *args]
sources = [root / "ordinary_chat_service.py", root / "test_ordinary_chat_service.py",
           root / "web_alarm/ordinary_chat_bridge.py", root / "test_web_alarm_ordinary_core_bridge.py",
           root / "web_alarm/turn_service.py", root / "web_alarm/ordinary_chat_test_adapter.py",
           root / "test_web_alarm_ultra_chat_turn_s4b.py", root / "run_store.py", root / "context_storage.py",
           root / "web_alarm/ultra_chat.py", root / "web_alarm/server.py", root / "web_alarm/ui.py",
           root / "ultra_ui.py", root / "test_web_alarm_ultra_chat_s5.py",
           root / "test_web_alarm_ultra_chat_ui.js",
           package / "guard/sitecustomize.py", Path(__file__)]
source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sources if p.is_file()}
started = time.monotonic()
with prefix.with_suffix(".stdout.txt").open("wb") as out, prefix.with_suffix(".stderr.txt").open("wb") as err:
    completed = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=err)
result = dict(command=command, cwd=str(root), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              python=sys.version, windows=platform.platform(), network=options.network,
              exit_code=completed.returncode, elapsed_seconds=time.monotonic()-started,
              source_sha256=source_hashes)
prefix.with_suffix(".result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
print(prefix.with_suffix(".stderr.txt").read_text(encoding="utf-8", errors="replace")[-2500:])
print(prefix.with_suffix(".stdout.txt").read_text(encoding="utf-8", errors="replace")[-2500:])
sys.exit(completed.returncode)
