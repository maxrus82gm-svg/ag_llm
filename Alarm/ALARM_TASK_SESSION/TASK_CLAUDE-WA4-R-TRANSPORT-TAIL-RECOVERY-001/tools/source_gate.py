"""Source/baseline gate for CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 (read-only over the repository).

Expected map = source-final.json of CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001 (105 files: web_alarm/*.py,
test_web_alarm*.py, wa4a_acceptance.py), i.e. the published repair the coordinator's W1 CI ran (874/OK).
Copies the exact pre-task bytes of the files this TASK may touch into baseline/ (only when absent) and
writes source-gate.json; with --final writes source-final.json instead. EOL of every file is recorded.
Usage: source_gate.py [--final]
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
PREVIOUS = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001" / "source-final.json"
MAY_CHANGE = {"web_alarm/transport_event_store.py": "web_alarm", "web_alarm/store_lock.py": "web_alarm",
              "test_web_alarm_transport_event_store.py": "tests"}
sha = lambda data: hashlib.sha256(data).hexdigest()


def eol(data: bytes) -> str:
    return "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CRLF_PRESENT")


expected = json.loads(PREVIOUS.read_bytes())["source_sha256_all"]
local = sorted([p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").glob("*.py")]
               + [p.name for p in REPO.glob("test_web_alarm*.py")] + ["wa4a_acceptance.py"])
current = {n: sha((REPO / n).read_bytes()) for n in local}
report = {
    "previous_map": PREVIOUS.relative_to(REPO).as_posix(),
    "previous_map_sha256": sha(PREVIOUS.read_bytes()),
    "expected_files": len(expected),
    "missing": sorted(set(expected) - set(current)),
    "unexpected": sorted(set(current) - set(expected)),
    "drift": sorted(n for n in expected if n in current and current[n] != expected[n]),
    "eol": {n: eol((REPO / n).read_bytes()) for n in local},
    "source_sha256_all": current,
}
if "--final" not in sys.argv:
    copied = []
    for rel, kind in MAY_CHANGE.items():
        target = HERE / "baseline" / kind / Path(rel).name
        if not target.exists():
            shutil.copyfile(REPO / rel, target)
            copied.append(rel)
        assert sha(target.read_bytes()) == expected[rel], rel
    report["baseline_copies"] = {rel: expected[rel] for rel in MAY_CHANGE}
    report["baseline_copied_now"] = copied
    report["verdict"] = "PASS" if not (report["missing"] or report["unexpected"] or report["drift"]) else "ATTENTION"
    out = HERE / "source-gate.json"
else:
    report["verdict"] = "FINAL_MAP"
    out = HERE / "source-final.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in report.items() if k not in ("source_sha256_all", "eol")}, indent=1))
