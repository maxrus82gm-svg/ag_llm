"""Direct (no guarded runner) unittest run of one module in a code root, with a chosen temp environment.

env "local": TMPDIR removed, TEMP/TMP as on this host; env "ci": TMPDIR = TEMP = TMP = this host's temp (the shape the
GitHub workflows set). Output: <TEMP>/claude-ft1ci-direct-<label>.json with exit code, per-test status lines and the
summary line of unittest (paths of the host replaced by <TEMP>/<ROOT>). Usage: direct_run.py <python> <label>
<code-root> <local|ci> <module>
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

python, label, root, mode, module = sys.argv[1:6]
temp = str(Path(tempfile.gettempdir()).resolve())
env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "GIT_"))}
env.pop("TMPDIR", None)
if mode == "ci":
    env.update(TMPDIR=temp, TEMP=temp, TMP=temp)
env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
proc = subprocess.run([python, "-B", "-X", "utf8", "-m", "unittest", "-v", module], cwd=root, env=env,
                      capture_output=True, timeout=900)
text = proc.stderr.decode("utf-8", errors="replace")
for form in (temp, root):
    text = re.sub(re.escape(form), "<TEMP>" if form == temp else "<ROOT>", text, flags=re.I)
lines = [x for x in text.splitlines() if re.search(r"\.\.\. (ok|FAIL|ERROR|skipped)", x) or x.startswith(("Ran ", "OK", "FAILED"))]
result = {"label": label, "mode": mode, "module": module, "exit": proc.returncode, "lines": lines,
          "failing_subtests": sorted(set(re.findall(r"^FAIL: \S+ \(\S+\) \[(\w+)\]", text, flags=re.M)))}
(Path(temp) / f"claude-ft1ci-direct-{label}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: result[k] for k in ("label", "mode", "exit", "failing_subtests")} | {"summary": lines[-2:]}))
