"""Gate E diff: unified diffs baseline -> repaired for every file this TASK changed (read-only over the repo).

Writes diff/<name>.diff (LF) and diff/diff-summary.json (SHA before/after, added/removed lines).
Rollback = copy the baseline bytes back (baseline/web_alarm/*, baseline/tests/*); the new test module is
removed. No Git is used.
"""
import difflib
import hashlib
import json
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
PAIRS = [(HERE / "baseline" / "web_alarm" / p.name, REPO / "web_alarm" / p.name)
         for p in sorted((HERE / "baseline" / "web_alarm").glob("*.py"))]
PAIRS += [(HERE / "baseline" / "tests" / p.name, REPO / p.name) for p in sorted((HERE / "baseline" / "tests").glob("*.py"))]
PAIRS += [(None, REPO / "test_web_alarm_crash_consistency.py")]
sha = lambda data: hashlib.sha256(data).hexdigest()

out = HERE / "diff"
out.mkdir(exist_ok=True)
summary = {}
for before, after in PAIRS:
    old = before.read_bytes() if before else b""
    new = after.read_bytes()
    rel = after.relative_to(REPO).as_posix()
    row = {"sha256_before": sha(old) if before else None, "sha256_after": sha(new),
           "bytes_before": len(old) if before else None, "bytes_after": len(new), "changed": old != new}
    if old != new:
        lines = list(difflib.unified_diff(old.decode("utf-8").splitlines(keepends=True),
                                          new.decode("utf-8").splitlines(keepends=True),
                                          f"a/{rel}" if before else "/dev/null", f"b/{rel}", n=3))
        text = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
        (out / (after.name + ".diff")).write_bytes(text.encode("utf-8"))
        row["added"] = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        row["removed"] = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    summary[rel] = row
(out / "diff-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
for rel, row in summary.items():
    print(rel, "CHANGED" if row["changed"] else "same", row.get("added", 0), row.get("removed", 0))
