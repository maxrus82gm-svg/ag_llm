"""Build a disposable TEMP mirror of the repository code for Gate A red and quality-mutant runs.

Usage: build_mirror.py <variant> <dest>
  "baseline": the pre-task code — web_alarm/transport_event_recovery.py removed (it did not exist), the
              possibly-touched files replaced by the exact bytes in baseline/; the new test module is kept.
  "<mutant>": one exact, single-occurrence replacement in web_alarm/transport_event_recovery.py (MUTANTS).
Copies only top-level *.py and web_alarm/*.py (read-only use of the repository); refuses a dest outside
TEMP or an existing dest. Prints a JSON line with the changed files and their SHA-256.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
TASK = Path(__file__).resolve().parent.parent
MODULE = "transport_event_recovery.py"

MUTANTS = {
    # M1: a corrupt middle line is treated as the start of the tail (tail-salvage on the middle)
    "M1-middle-salvage": ("            return {\"verdict\": CORRUPT_MIDDLE, \"line\": index, \"problem\": problem,",
                          "            bad_at = sum(len(c) + 1 for c in prefix.split(b\"\\n\")[:index - 1])\n"
                          "            return classify(data[:bad_at] + data[bad_at:].replace(b\"\\n\", b\" \")) or "
                          "{\"line\": index, \"problem\": problem,"),
    # M2: the archive is never verified by reading it back (both read-back checks removed)
    "M2-no-archive-verify": [("    if path.read_bytes() != data:\n        raise OSError",
                              "    if False:\n        raise OSError"),
                             ("            if _sha((attempt / name).read_bytes()) != facts[\"sha256\"]:",
                              "            if False:")],
    # M3: no transport writer lock around the decisive steps
    "M3-no-lock": ("        lock.acquire()\n    except (StoreLockTimeout, OSError) as exc:",
                   "        pass\n    except (StoreLockTimeout, OSError) as exc:"),
    # M4: the plan fingerprint is not re-checked under the lock
    "M4-no-fingerprint-recheck": ("    if plan[\"plan_fingerprint\"] != fingerprint:",
                                  "    if False:"),
    # M5: NUL bytes in the tail are accepted as a torn tail
    "M5-accept-nul-tail": ("    if b\"\\x00\" in tail:", "    if False:"),
    # M6: reparse points (junctions) are not refused
    "M6-follow-junctions": ("    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, \"st_file_attributes\", 0) & _REPARSE)",
                            "    return False"),
    # M7: the source is not re-checked right before the replacement
    "M7-no-source-recheck": ("    if current is None or current[1] != identity or current[0] != data:",
                             "    if current is None:"),
    # M8: the log is truncated in place instead of an atomic replacement of a checked temporary file
    "M8-truncate-in-place": ("        _replace(temp, events_path)\n",
                             "        _discard(temp)\n        with events_path.open(\"r+b\") as fh:\n            fh.truncate(len(prefix))\n"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    variant, dest = sys.argv[1], Path(sys.argv[2]).resolve()
    temp = Path(os.environ["TEMP"]).resolve()
    if temp not in dest.parents or dest.exists():
        raise SystemExit(f"refused: {dest} must be a new directory under TEMP")
    (dest / "web_alarm").mkdir(parents=True)
    for src in REPO.glob("*.py"):
        shutil.copyfile(src, dest / src.name)
    for src in (REPO / "web_alarm").glob("*.py"):
        shutil.copyfile(src, dest / "web_alarm" / src.name)
    changed = {}
    if variant == "baseline":
        (dest / "web_alarm" / MODULE).unlink()
        changed["web_alarm/" + MODULE] = "REMOVED"
        for src in sorted((TASK / "baseline" / "web_alarm").glob("*.py")):
            shutil.copyfile(src, dest / "web_alarm" / src.name)
            changed["web_alarm/" + src.name] = sha(dest / "web_alarm" / src.name)
        for src in sorted((TASK / "baseline" / "tests").glob("*.py")):
            shutil.copyfile(src, dest / src.name)
            changed[src.name] = sha(dest / src.name)
    else:
        pairs = MUTANTS[variant] if isinstance(MUTANTS[variant], list) else [MUTANTS[variant]]
        path = dest / "web_alarm" / MODULE
        text = path.read_bytes().decode("utf-8")
        for old, new in pairs:
            if text.count(old) != 1:
                raise SystemExit(f"refused: {variant} anchor occurs {text.count(old)} times")
            text = text.replace(old, new)
        path.write_bytes(text.encode("utf-8"))
        changed["web_alarm/" + MODULE] = sha(path)
    print(json.dumps({"variant": variant, "dest": str(dest), "changed": changed}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
