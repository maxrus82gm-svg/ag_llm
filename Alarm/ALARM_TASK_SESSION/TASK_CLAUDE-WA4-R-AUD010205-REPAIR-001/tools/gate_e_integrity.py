"""Gate E (read-only over the repository; writes only its own outputs in this TASK folder and TEMP).

1. every R-006 pinned source either equals its pin or is one of the three allowed repair files;
2. no unpinned web_alarm/*.py or test_web_alarm*.py besides the new repair test;
3. baseline copies equal the pre-repair SHA-256; restoring them in a TEMP copy reproduces exactly the
   R-006 pinned bytes (rollback is exact);
4. the R-006 evidence package is unchanged (manifest 64/64);
5. a unified diff baseline -> current is written to source-changes.diff.
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
ALLOWED = ["web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py", "web_alarm/projection.py"]
NEW_TEST = "test_web_alarm_aud010205_repair.py"
sha = lambda data: hashlib.sha256(data).hexdigest()
pins = json.loads((PKG / "checks.json").read_bytes())["final_full_source_sha256"]
report = {}

changed, unchanged, missing = [], 0, []
for name, digest in sorted(pins.items()):
    path = REPO / name
    if not path.exists():
        missing.append(name)
    elif sha(path.read_bytes()) == digest:
        unchanged += 1
    else:
        changed.append(name)
report["pinned"] = len(pins)
report["pinned_unchanged"] = unchanged
report["pinned_changed"] = changed
report["pinned_missing"] = missing
report["changed_equals_allowed"] = sorted(changed) == sorted(ALLOWED)
local = sorted([p.relative_to(REPO).as_posix() for p in (REPO / "web_alarm").glob("*.py")]
               + [p.name for p in REPO.glob("test_web_alarm*.py")])
report["unpinned_local"] = [p for p in local if p not in pins]
report["unpinned_is_only_new_test"] = report["unpinned_local"] == [NEW_TEST]

files = {}
for name in ALLOWED + [NEW_TEST]:
    data = (REPO / name).read_bytes()
    files[name] = {"before": pins.get(name), "after": sha(data), "bytes": len(data),
                   "eol": "CRLF" if b"\r\n" in data else "LF"}
report["files"] = files

baseline_ok, restore_ok = {}, None
temp = Path(tempfile.mkdtemp(prefix="aud010205-restore-"))
try:
    for name in ALLOWED:
        data = (HERE / "baseline" / name).read_bytes()
        baseline_ok[name] = sha(data) == pins[name]
        target = temp / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)          # current repaired bytes
        shutil.copyfile(HERE / "baseline" / name, target)  # rollback = copy baseline back
    restore_ok = all(sha((temp / name).read_bytes()) == pins[name] for name in ALLOWED)
finally:
    shutil.rmtree(temp)
report["baseline_copies_equal_pins"] = baseline_ok
report["rollback_reproduces_pins"] = restore_ok

manifest = json.loads((PKG / "manifest.json").read_bytes())
exact = sum(1 for n, p in manifest["files"].items()
            if (PKG / n).exists() and sha((PKG / n).read_bytes()) == p["sha256"] and (PKG / n).stat().st_size == p["bytes"])
report["r006_package"] = {"manifest_sha256": sha((PKG / "manifest.json").read_bytes()), "exact": exact,
                          "listed": len(manifest["files"])}

diff = []
for name in ALLOWED:
    before = (HERE / "baseline" / name).read_text(encoding="utf-8").splitlines(keepends=True)
    after = (REPO / name).read_text(encoding="utf-8").splitlines(keepends=True)
    diff.extend(difflib.unified_diff(before, after, "a/" + name, "b/" + name, n=3))
(HERE / "source-changes.diff").write_text("".join(diff), encoding="utf-8", newline="\n")
report["diff_lines_added"] = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
report["diff_lines_removed"] = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
report["source_changes_diff_sha256"] = sha((HERE / "source-changes.diff").read_bytes())
report["verdict"] = ("PASS" if report["changed_equals_allowed"] and not missing and report["unpinned_is_only_new_test"]
                     and all(baseline_ok.values()) and restore_ok
                     and exact == len(manifest["files"]) == 64 else "FAIL")
Path(sys.argv[1]).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(report, ensure_ascii=False, indent=1))
