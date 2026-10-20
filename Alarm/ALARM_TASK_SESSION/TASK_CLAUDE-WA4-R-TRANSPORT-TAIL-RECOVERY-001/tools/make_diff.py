"""Gate E diff for CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 (read-only over the repository, no Git).

Unified diffs baseline -> current for every possibly touched file (baseline/ copies) and the two new files
(against an empty file). Writes diff/<name>.diff (LF) and diff/diff-summary.json with SHA before/after,
added/removed lines and line endings. Rollback = delete the two new files (the baseline files are unchanged).
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
PAIRS += [(None, REPO / "web_alarm" / "transport_event_recovery.py"),
          (None, REPO / "test_web_alarm_transport_event_recovery.py")]
sha = lambda data: hashlib.sha256(data).hexdigest()


def eol(data: bytes) -> str:
    return "NONE" if b"\n" not in data else ("LF" if b"\r" not in data else "CRLF_PRESENT")


out = HERE / "diff"
out.mkdir(exist_ok=True)
summary = {}
for before, after in PAIRS:
    old = before.read_bytes() if before else b""
    new = after.read_bytes()
    rel = after.relative_to(REPO).as_posix()
    row = {"kind": "new" if before is None else ("modified" if old != new else "unchanged"),
           "sha256_before": sha(old) if before else None, "sha256_after": sha(new),
           "bytes_before": len(old) if before else None, "bytes_after": len(new), "eol_after": eol(new)}
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
    print(rel, row["kind"], row.get("added", 0), row.get("removed", 0), row["eol_after"])
