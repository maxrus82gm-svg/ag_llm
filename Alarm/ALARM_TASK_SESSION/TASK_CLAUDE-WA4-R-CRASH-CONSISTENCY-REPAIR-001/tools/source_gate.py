"""Source/baseline gate for CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 (read-only over the repository).

Expected map = source-gate.json of CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 (104 files). Copies the exact
pre-repair bytes of the eight files of the write-scope into baseline/web_alarm/ (only when absent) and
writes source-gate.json here. Usage: source_gate.py [--final]
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
DESIGN = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001"
SCOPE = ["state_machine.py", "operation_store.py", "projection.py", "closeout.py", "recovery_coordinator.py",
         "manifest_store.py", "event_checkpoint_store.py", "server.py"]
sha = lambda data: hashlib.sha256(data).hexdigest()

expected = json.loads((DESIGN / "source-gate.json").read_bytes())["source_sha256_all"]
local = sorted([p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").glob("*.py")]
               + [p.name for p in REPO.glob("test_web_alarm*.py")])
current = {n: sha((REPO / n).read_bytes()) for n in local}
for n in expected:
    if n not in current and (REPO / n).is_file():
        current[n] = sha((REPO / n).read_bytes())
report = {
    "design_source_gate_sha256": sha((DESIGN / "source-gate.json").read_bytes()),
    "expected_files": len(expected),
    "missing": sorted(set(expected) - set(current)),
    "unexpected": sorted(set(current) - set(expected)),
    "drift": sorted(n for n in expected if n in current and current[n] != expected[n]),
    "scope_files": {f"web_alarm/{n}": expected[f"web_alarm/{n}"] for n in SCOPE},
    "source_sha256_all": current,
}
if "--final" not in sys.argv:
    copied = []
    for n in SCOPE:
        target = HERE / "baseline" / "web_alarm" / n
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / "web_alarm" / n, target)
            copied.append(n)
        assert sha(target.read_bytes()) == expected[f"web_alarm/{n}"], n
    report["baseline_copied_now"] = copied
    report["verdict"] = "PASS" if not (report["missing"] or report["unexpected"] or report["drift"]) else "ATTENTION"
    out = HERE / "source-gate.json"
else:
    report["verdict"] = "FINAL_MAP"
    out = HERE / "source-final.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in report.items() if k != "source_sha256_all"}, indent=1))
