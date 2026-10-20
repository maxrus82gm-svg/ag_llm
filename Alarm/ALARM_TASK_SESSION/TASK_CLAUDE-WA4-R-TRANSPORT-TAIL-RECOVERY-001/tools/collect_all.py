"""Gather label=base pairs from every runs/<batch>.attempts.json (in run order) and call collect_evidence.py.

A label that occurs in two batches gets the batch name appended. Usage: collect_all.py <python>
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ORDER = ["red", "green2", "green3", "mutants", "green4", "final", "flake"]
pairs, seen = [], {}
for batch in ORDER:
    for row in json.loads((HERE / "runs" / f"{batch}.attempts.json").read_text(encoding="utf-8-sig")):
        label = row["label"]
        if label in seen:
            label = f"{label}-{batch}"
        seen[label] = batch
        pairs.append(f"{label}={row['base']}")
code = subprocess.run([sys.executable, "-I", "-B", str(HERE / "tools" / "collect_evidence.py"), *pairs]).returncode
sys.exit(code)
