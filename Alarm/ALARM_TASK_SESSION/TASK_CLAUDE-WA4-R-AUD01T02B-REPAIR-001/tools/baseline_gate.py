"""Baseline gate for CLAUDE-WA4-R-AUD01T02B-REPAIR-001 (read-only over the repository).

Expected starting point = R-006 pins (Codex package checks.json) with exactly the three files changed by
CLAUDE-WA4-R-AUD010205-REPAIR-001 at its final SHA-256 and its one new test module.
Copies the exact pre-repair bytes of the two primary targets into baseline/ (only if baseline/ is empty)
and writes baseline-gate.json next to this tools/ folder.
Usage: baseline_gate.py
"""
import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
sha = lambda data: hashlib.sha256(data).hexdigest()

PREV_REPAIR = {
    "web_alarm/event_checkpoint_store.py": "7342b221e6663bee65bef116f57507b0de84b74269cb7541f4955b527eb91304",
    "web_alarm/operation_store.py": "acb1e4c9ccc6a9ee70684f852c48cf8ba815ea67548781f2e1e53e535468826a",
    "web_alarm/projection.py": "e4503ce955a41d8e9891bc429db4f145b32027a838334081688a4d662426f4e1",
}
PREV_TEST = ("test_web_alarm_aud010205_repair.py",
             "f0b1c492f38d711e135f571fff2cefa7781f87827b5a43781e0ac69ff4d543ba")
TARGETS = ["web_alarm/transport_event_store.py", "web_alarm/state_machine.py"]

pins = json.loads((PKG / "checks.json").read_bytes())["final_full_source_sha256"]
expected = dict(pins)
expected.update(PREV_REPAIR)
expected[PREV_TEST[0]] = PREV_TEST[1]

local = sorted([p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").glob("*.py")]
               + [p.name for p in REPO.glob("test_web_alarm*.py")])
current = {name: sha((REPO / name).read_bytes()) for name in local}
for name in expected:  # pinned files outside the two globs (e.g. the runner wa4a_acceptance.py)
    if name not in current and (REPO / name).is_file():
        current[name] = sha((REPO / name).read_bytes())
report = {
    "expected_files": len(expected),
    "local_files": len(local),
    "missing": sorted(set(expected) - set(current)),
    "unexpected": sorted(set(current) - set(expected)),
    "drift": sorted(n for n in expected if n in current and current[n] != expected[n]),
    "prev_repair_present": {n: current.get(n) == d for n, d in PREV_REPAIR.items()},
    "targets": {},
}
for name in TARGETS:
    data = (REPO / name).read_bytes()
    report["targets"][name] = {
        "sha256": sha(data), "bytes": len(data), "equals_r006_pin": sha(data) == pins.get(name),
        "eol": "CRLF" if b"\r\n" in data else "LF",
        "raw_line_separators": sum(data.count(ch.encode()) for ch in (chr(0x85), chr(0x2028), chr(0x2029))),
    }
base = HERE / "baseline"
copied = []
for name in TARGETS:
    target = base / name
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
        copied.append(name)
    report["targets"][name]["baseline_copy_sha256"] = sha(target.read_bytes())
report["baseline_copied_now"] = copied
manifest = json.loads((PKG / "manifest.json").read_bytes())
report["r006_package"] = {
    "manifest_sha256": sha((PKG / "manifest.json").read_bytes()),
    "exact": sum(1 for n, p in manifest["files"].items()
                 if (PKG / n).exists() and sha((PKG / n).read_bytes()) == p["sha256"]),
    "listed": len(manifest["files"]),
}
report["source_sha256_all"] = current
report["verdict"] = ("PASS" if not report["missing"] and not report["unexpected"] and not report["drift"]
                     and all(report["prev_repair_present"].values())
                     and all(t["baseline_copy_sha256"] == t["sha256"] for t in report["targets"].values())
                     else "ATTENTION")
(HERE / "baseline-gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8", newline="\n")
summary = {k: v for k, v in report.items() if k != "source_sha256_all"}
print(json.dumps(summary, ensure_ascii=False, indent=1))
