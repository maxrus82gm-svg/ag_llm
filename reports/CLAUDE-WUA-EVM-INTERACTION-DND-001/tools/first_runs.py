"""Keep the red runs of real_input_check.js (TEST-FLAKY-01): the failed checks of each kept run, with the cause found.
Only step names, check names, values and counters are written (no paths).
Usage: first_runs.py <run1 real_input.json> <run3 real_input.json> <out.json>
"""
import json
import sys
from pathlib import Path

CAUSES = {
    "run1": ("first run, page before the drag-label and role-grid fixes (both found on its screenshots: the label hid the "
             "insertion line and left the window; role names broke inside words at 390 px); script step S17 scrolled the card under the 265 px "
             "sticky page header of a 390 px window, so both clicks hit the header (script defect; the header layout is "
             "pre-existing and out of scope). Fixed in the script: scroll below the header, check the card opened."),
    "run3": ("first run on the final page bytes: the open card became taller (roles in two columns), the S02 click on the 4th card "
             "fell below a 1000 px window and left a card open; the following steps measured that layout (cascade, script "
             "defect). Fixed in the script: scroll a card into view before a click; every step starts on a reloaded page."),
}


def failed(path: Path):
    record = json.loads(path.read_text(encoding="utf-8"))
    rows = [{"step": s["step"][:3], "check": c["check"], **({"value": c["value"]} if "value" in c else {})}
            for s in record["steps"] for c in s["checks"] if not c["ok"]]
    errors = [{"step": s["step"][:3], "error": s["error"]} for s in record["steps"] if s.get("error")]
    return {"checks": record["checks"], "failed": record["failed"], "failed_checks": rows, "step_errors": errors}


out = {"task": "CLAUDE-WUA-EVM-INTERACTION-DND-001", "purpose": "red runs of the real-input check kept as found (TEST-FLAKY-01)",
       "runs": {name: {**failed(Path(arg)), "cause": CAUSES[name]} for name, arg in (("run1", sys.argv[1]), ("run3", sys.argv[2]))},
       "run2": "125/125 on the page before the role-grid fix (not kept: superseded)",
       "final": "evidence/real_input.json (fresh demo, final page bytes)"}
Path(sys.argv[3]).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: (v["checks"], v["failed"]) for k, v in out["runs"].items()}))
