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

MUTANTS = {
    # Phase B (Archive Retry) - each removes one part of the retry proof
    "B1-tail-unchecked": (REC, [("                       and tail == original[cut:]\n"
                                 "                       and _sha(tail) == plan[\"tail\"][\"sha256\"] and len(tail) == "
                                 "plan[\"tail\"][\"bytes\"]\n", "")]),
    "B2-receipt-ignored": (REC, [("                       and _receipt_agrees(attempt, plan, files, current))",
                                  "                       and True)")]),
    "B3-any-outcome": (REC, [("    return (receipt[\"outcome\"] == FAILED and receipt[\"step\"] == \"REPLACE_FAILED\"\n"
                              "            and receipt[\"transport_log_changed\"] is False)", "    return True")]),
    "B4-receipt-required": (REC, [("    if not os.path.lexists(path):\n        return True",
                                   "    if not os.path.lexists(path):\n        return False")]),
    "B5-archive-unchecked": (REC, [("\n            and set(archive) == set(files)\n"
                                    "            and all(archive[name][\"sha256\"] == _sha(data) and archive[name][\"bytes\"] "
                                    "== len(data)\n                    for name, data in files.items())):", "):")]),
    "B6-replace-failure-rejected": (REC, [("receipt[\"step\"] == \"REPLACE_FAILED\"", "receipt[\"step\"] == \"NEVER\"")]),
    "B7-result-unchecked": (REC, [("        return receipt[\"result\"][\"sha256\"] == _sha(current) and "
                                   "receipt[\"result\"][\"bytes\"] == len(current)", "        return True")]),
    "B8-identity-unchecked": (REC, [("receipt[\"attempt_id\"] == attempt.name", "True"),
                                    ("receipt[\"plan_fingerprint\"] == plan[\"plan_fingerprint\"]", "True")]),
    "B9-source-prefix-unchecked": (REC, [("receipt[\"source_before\"] == plan[\"source\"]", "True"),
                                         ("receipt[\"prefix\"] == plan[\"prefix\"]", "True")]),
    # Phase A (F-T1 guard) - the fix removed, over-widened, or the old protection itself disabled
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
    "original-guard": (GUARD, "198d0b8f7822fa29f9f59a00f15b9087313e244a95bf6b1d2d4757fb1be4cffc"),
    "original-recovery": (REC, "dcdd258342fcd1832efe9970fb5703cc7a7b001429c9e61c45ea8e4d18747ad5"),
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
        data = (temp / "claude-ft1-base-mirror" / rel).read_bytes()
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
