"""Keep the red trial run of run_real_input.py (TEST-FLAKY-01) as found, without local paths, with the cause found.
Usage: red_runs.py <trial real_input_run.json> <out.json>
"""
import json
import re
import sys
from pathlib import Path

PATH = re.compile(r"[A-Za-z]:\\[^\s'\"]*|/(?:tmp|home|Users)/[^\s'\"]*")
trial = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
clean = lambda items: [PATH.sub("<path>", x)[:300] for x in items]
record = {
    "task": "CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "purpose": "the red trial run of the real-input check, kept as found",
    "trial": {name: {"exit": p["exit"], "checks": p["checks"], "failed": p["failed"], "failed_checks": clean(p["failed_checks"]),
                     "step_errors": clean(p["step_errors"])} for name, p in trial["phases"].items()},
    "cause": ("script defect, not a product defect: the regression step S17 of #464 pressed «⧉» at 390 px to get the quick view sheet; "
              "«⧉» now pins a window, which was saved and restored on every later load. In P01 that window covered card B, and the "
              "later P steps cascaded. Fixed in the script: S17 shows the sheet with Ctrl + hover; free() tells what covers a card. "
              "Run 2 and the final run: 198/198."),
}
Path(sys.argv[2]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: (v["checks"], v["failed"]) for k, v in record["trial"].items()}))
