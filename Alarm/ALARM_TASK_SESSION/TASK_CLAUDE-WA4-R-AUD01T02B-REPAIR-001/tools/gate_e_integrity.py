"""Gate E for CLAUDE-WA4-R-AUD01T02B-REPAIR-001 (read-only over the repository; writes only its outputs here).

1. every source of the pre-repair map (baseline-gate.json: R-006 pins + AUD-01/02/05 repair) is unchanged,
   except exactly the three allowed files;
2. no new web_alarm/*.py or test_web_alarm*.py besides the new repair test;
3. baseline copies equal the pre-repair SHA-256; restoring them in a TEMP copy reproduces the pre-repair
   bytes exactly (rollback is exact);
4. the R-006 evidence package is unchanged (manifest 64/64);
5. a unified diff baseline -> current is written to source-changes.diff;
6. the changed and new files are LF-only and hold no raw U+0085/U+2028/U+2029.
Usage: gate_e_integrity.py <out.json>
"""
import difflib
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
ALLOWED_SOURCES = ["web_alarm/event_checkpoint_store.py", "web_alarm/state_machine.py",
                   "web_alarm/transport_event_store.py"]
ALLOWED_TESTS = ["test_web_alarm_recovery_coordinator_repair3.py", "test_web_alarm_state_machine_cas.py"]
ALLOWED = ALLOWED_SOURCES + ALLOWED_TESTS
BASELINE_COPY = {name: ("baseline/" + name if name.startswith("web_alarm/") else "baseline/tests/" + name)
                 for name in ALLOWED}
NEW_TEST = "test_web_alarm_aud01t02b_repair.py"
sha = lambda data: hashlib.sha256(data).hexdigest()
before = json.loads((HERE / "baseline-gate.json").read_bytes())["source_sha256_all"]
report = {"pre_repair_map_files": len(before)}

changed, unchanged, missing = [], 0, []
for name, digest in sorted(before.items()):
    path = REPO / name
    if not path.exists():
        missing.append(name)
    elif sha(path.read_bytes()) == digest:
        unchanged += 1
    else:
        changed.append(name)
report["unchanged"] = unchanged
report["changed"] = changed
report["missing"] = missing
report["changed_equals_allowed"] = sorted(changed) == sorted(ALLOWED)
local = sorted([p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").glob("*.py")]
               + [p.name for p in REPO.glob("test_web_alarm*.py")])
report["new_local_files"] = [p for p in local if p not in before]
report["new_is_only_the_repair_test"] = report["new_local_files"] == [NEW_TEST]

files = {}
for name in ALLOWED + [NEW_TEST]:
    data = (REPO / name).read_bytes()
    files[name] = {"before": before.get(name), "after": sha(data), "bytes": len(data),
                   "eol": "LF" if b"\r" not in data else "CR_PRESENT",
                   "raw_separators": sum(data.count(chr(c).encode("utf-8")) for c in (0x85, 0x2028, 0x2029))}
report["files"] = files
report["files_clean"] = all(f["eol"] == "LF" and f["raw_separators"] == 0 for f in files.values())

baseline_ok, restore_ok = {}, None
temp = Path(tempfile.mkdtemp(prefix="aud01t02b-restore-"))
try:
    for name in ALLOWED:
        data = (HERE / BASELINE_COPY[name]).read_bytes()
        baseline_ok[name] = sha(data) == before[name]
        target = temp / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)                    # current repaired bytes
        shutil.copyfile(HERE / BASELINE_COPY[name], target)     # rollback = copy the baseline back
    restore_ok = all(sha((temp / name).read_bytes()) == before[name] for name in ALLOWED)
finally:
    shutil.rmtree(temp)
report["baseline_copies_equal_pre_repair"] = baseline_ok
report["rollback_reproduces_pre_repair"] = restore_ok

manifest = json.loads((PKG / "manifest.json").read_bytes())
exact = sum(1 for n, p in manifest["files"].items()
            if (PKG / n).exists() and sha((PKG / n).read_bytes()) == p["sha256"] and (PKG / n).stat().st_size == p["bytes"])
report["r006_package"] = {"manifest_sha256": sha((PKG / "manifest.json").read_bytes()), "exact": exact,
                          "listed": len(manifest["files"])}

diff = []
for name in ALLOWED:
    old = (HERE / BASELINE_COPY[name]).read_text(encoding="utf-8").splitlines(keepends=True)
    new = (REPO / name).read_text(encoding="utf-8").splitlines(keepends=True)
    diff.extend(difflib.unified_diff(old, new, "a/" + name, "b/" + name, n=3))
(HERE / "source-changes.diff").write_text("".join(diff), encoding="utf-8", newline="\n")
report["diff_lines_added"] = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
report["diff_lines_removed"] = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
report["source_changes_diff_sha256"] = sha((HERE / "source-changes.diff").read_bytes())
report["verdict"] = ("PASS" if report["changed_equals_allowed"] and not missing and report["new_is_only_the_repair_test"]
                     and all(baseline_ok.values()) and restore_ok and report["files_clean"]
                     and exact == len(manifest["files"]) == 64 else "FAIL")
Path(sys.argv[1]).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: v for k, v in report.items() if k != "files"}, ensure_ascii=False, indent=1))
