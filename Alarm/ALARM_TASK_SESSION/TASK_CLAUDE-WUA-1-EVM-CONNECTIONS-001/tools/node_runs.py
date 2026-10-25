"""Run the shipped-client JS tests with node and keep their TAP output (LF) in TEMP for publication.

Usage: node_runs.py <node> <label>  -> <TEMP>/claude-wua1-node-<label>-<file>.tap and a summary JSON line.
The repository is only read (node executes the page script in node:vm with a fake DOM; no network).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TEMP = Path(tempfile.gettempdir()).resolve()
node, label = sys.argv[1], sys.argv[2]
summary = {}
for name in ("test_web_alarm_evm_ui.js", "test_web_alarm_operator_ui.js"):
    proc = subprocess.run([node, "--test", name], cwd=str(REPO), capture_output=True, timeout=300)
    out = proc.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
    (TEMP / f"claude-wua1-node-{label}-{name}.tap").write_text(out, encoding="utf-8", newline="\n")
    counts = {k: int(v) for k, v in (line[2:].split(" ", 1) for line in out.splitlines()
                                     if line.startswith(("# tests ", "# pass ", "# fail ", "# skipped ")))}
    summary[name] = {"exit": proc.returncode, **counts}
print(json.dumps(summary))
