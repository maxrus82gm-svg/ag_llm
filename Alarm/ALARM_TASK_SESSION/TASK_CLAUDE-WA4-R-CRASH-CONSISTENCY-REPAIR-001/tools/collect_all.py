"""Gather label=base pairs from every runs/<batch>.attempts.json (in run order) and call collect_evidence.py.

A label that occurs in two batches gets the batch name appended (green5 / green5b: the same test before and
after its oracle was narrowed). Usage: collect_all.py <python>
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ORDER = ["red", "green1", "green2", "green3", "full1", "adv1", "gate2", "mutants", "green4", "mutants2",
         "green5", "green5b", "final"]
pairs, seen = [], {}
for batch in ORDER:
    for row in json.loads((HERE / "runs" / f"{batch}.attempts.json").read_text(encoding="utf-8-sig")):
        label = row["label"]
        if label in seen:
            label = f"{label}-{batch}"
        seen[label] = batch
        pairs.append(f"{label}={row['base']}")
code = subprocess.run([sys.argv[1], "-I", "-B", str(HERE / "tools" / "collect_evidence.py"), *pairs]).returncode
sys.exit(code)
