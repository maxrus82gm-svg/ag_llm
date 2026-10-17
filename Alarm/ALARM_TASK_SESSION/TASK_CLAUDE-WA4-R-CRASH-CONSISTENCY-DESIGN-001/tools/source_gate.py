"""Source gate for CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001 (read-only over the repository).

Expected source map = pre-repair map of CLAUDE-WA4-R-AUD01T02B-REPAIR-001 (its baseline-gate.json) with
the six files that TASK changed/added at their final SHA-256 (its gate-e.json). Writes source-gate.json.
Usage: source_gate.py
"""
import hashlib
import json
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
PREV = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD01T02B-REPAIR-001"
sha = lambda data: hashlib.sha256(data).hexdigest()

expected = dict(json.loads((PREV / "baseline-gate.json").read_bytes())["source_sha256_all"])
for name, entry in json.loads((PREV / "gate-e.json").read_bytes())["files"].items():
    expected[name] = entry["after"]
local = sorted([p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").glob("*.py")]
               + [p.name for p in REPO.glob("test_web_alarm*.py")])
current = {n: sha((REPO / n).read_bytes()) for n in local}
for n in expected:
    if n not in current and (REPO / n).is_file():
        current[n] = sha((REPO / n).read_bytes())
report = {
    "expected_files": len(expected),
    "missing": sorted(set(expected) - set(current)),
    "unexpected": sorted(set(current) - set(expected)),
    "drift": sorted(n for n in expected if n in current and current[n] != expected[n]),
    "prev_gate_e_sha256": sha((PREV / "gate-e.json").read_bytes()),
    "prev_report_sha256": sha((PREV / "report.md").read_bytes()),
    "prev_manifest_sha256": sha((PREV / "manifest.json").read_bytes()),
    "source_sha256_all": current,
}
report["verdict"] = "PASS" if not (report["missing"] or report["unexpected"] or report["drift"]) else "ATTENTION"
(HERE / "source-gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                       newline="\n")
print(json.dumps({k: v for k, v in report.items() if k != "source_sha256_all"}, indent=1))
