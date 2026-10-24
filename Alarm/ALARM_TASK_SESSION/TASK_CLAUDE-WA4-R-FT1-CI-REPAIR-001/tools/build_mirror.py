"""Build a disposable TEMP mirror of the repository code with one variant applied.

Usage: build_mirror.py <variant> <dest>
  "final":    the working tree as it is (control);
  "<mutant>": exact single-occurrence replacements in one file of the working tree (MUTANTS below).
Copies only top-level *.py and web_alarm/*.py; refuses a dest outside TEMP or an existing dest. The repository
root comes from this file's location. Prints one JSON line with relative names only.
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
REC = "web_alarm/transport_event_recovery.py"
GUARD = "wa4a_acceptance.py"

TEST = "test_web_alarm_runner_guard.py"

MUTANTS = {
    # FT1-CI-REPAIR - the child's root chosen wrongly (C1, C2) or the guard's root widened (C3)
    "C1-tmpdir-not-overridden": (TEST, [("PYTHONDONTWRITEBYTECODE=\"1\", TMPDIR=str(self.inner),\n                   TMP=",
                                         "PYTHONDONTWRITEBYTECODE=\"1\",\n                   TMP=")]),
    "C2-tmpdir-and-root-oracle-removed": (TEST, [
        ("PYTHONDONTWRITEBYTECODE=\"1\", TMPDIR=str(self.inner),\n                   TMP=",
         "PYTHONDONTWRITEBYTECODE=\"1\",\n                   TMP="),
        ("        self.assertEqual(os.path.normcase(root[\"guard\"]), inner, \"the child's guard does not protect its own "
         "temp\")\n        self.assertEqual(os.path.normcase(root[\"gettempdir\"]), inner, \"the child's tempfile root is "
         "not its own temp\")\n", "")]),
    "C3-guard-root-widened": (GUARD, [("_audit_temp = _canon(tempfile.gettempdir())",
                                       "_audit_temp = _canon(os.path.dirname(tempfile.gettempdir()))")]),
    # FT1 guard (previous TASK) - the fix removed, over-widened, or the old protection itself disabled
    "A1-no-prefix-strip": (GUARD, [(r'''    if os.name == "nt" and s.startswith("\\\\?\\") and not os.path.normpath(raw).startswith("\\\\?\\"):
        p = Path("\\\\" + s[8:] if s.startswith("\\\\?\\UNC\\") else s[4:])
''', "")]),
    "A2-explicit-prefix-stripped-too": (GUARD, [(r''' and not os.path.normpath(raw).startswith("\\\\?\\"):''', ":")]),
    "A3-no-deleted-retry": (GUARD, [("    for _ in range(50):", "    for _ in range(0):")]),
    "A4-deleted-trusted-by-spelling": (GUARD, [(
        '        if [s.lower() for s in p.parts[1:3]] != ["$extend", "$deleted"]: break',
        '        if [s.lower() for s in p.parts[1:3]] == ["$extend", "$deleted"]: '
        'p = Path(os.path.abspath(os.fsdecode(value)))\n        break')]),
    "A5-write-check-disabled": (GUARD, [("    if write and not p.is_relative_to(_audit_temp): _violation(",
                                         "    if False: _violation(")]),
    "A6-git-check-removed": (GUARD, [('    if ".git" in {s.lower() for s in p.parts}: _violation("filesystem", '
                                      '"Git metadata access")', "    pass")]),
}

ORIGINAL = {  # pre-task bytes, as recorded in source-baseline.json
    "original-test": (TEST, "66039cef0af39db4347f4ebf68b706803fe5ce194e8e1a85fd6f0897f44b8c97"),
}


def main():
    variant, dest = sys.argv[1], Path(sys.argv[2]).resolve()
    temp = Path(tempfile.gettempdir()).resolve()
    if temp not in dest.parents or dest.exists():
        raise SystemExit("dest must be a new directory inside TEMP")
    (dest / "web_alarm").mkdir(parents=True)
    for path in REPO.glob("*.py"):
        shutil.copy2(path, dest / path.name)
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    changed = {}
    if variant in ORIGINAL:  # final tree, one file back to its pre-task bytes (RED of the final tests)
        rel, expected = ORIGINAL[variant]
        data = (temp / "claude-ft1ci-base-mirror" / rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit(f"{variant}: base mirror file is not the recorded pre-task revision")
        (dest / rel).write_bytes(data)
        changed[rel] = expected
    elif variant != "final":
        rel, replacements = MUTANTS[variant]
        target = dest / rel
        text = target.read_text(encoding="utf-8")
        for old, new in replacements:
            if text.count(old) != 1:
                raise SystemExit(f"{variant}: pattern found {text.count(old)} times")
            text = text.replace(old, new)
        target.write_bytes(text.encode("utf-8"))
        changed[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
    print(json.dumps({"variant": variant, "mirror": dest.name, "changed": changed}))


if __name__ == "__main__":
    main()
