"""Build a disposable TEMP mirror of the repository code for Gate A (baseline) and Gate C (quality mutants).

Usage: build_mirror.py <variant> <dest>
  "baseline": the pre-task code - web_alarm/evidence_sanitizer.py removed (it did not exist); tests kept.
  "<mutant>": one exact, single-occurrence replacement in web_alarm/evidence_sanitizer.py (MUTANTS).
Copies only top-level *.py and web_alarm/*.py (read-only use of the repository); refuses a dest outside TEMP or
an existing dest. The repository root comes from this file's location. Prints one JSON line (relative names only).
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MODULE = "evidence_sanitizer.py"

MUTANTS = {
    # M1: a separator is exactly one character (the literal-replacement blind spot for \\ and \\\\)
    "M1-single-separator": ('_SEP = r"(?:/|\\\\(?!u[0-9a-fA-F]{4}))++"', '_SEP = r"(?:/|\\\\(?!u[0-9a-fA-F]{4}))"'),
    # M2: component names compared case-sensitively (lower-cased physical keys, \"users\" vs \"Users\")
    "M2-case-sensitive": ('.strip("\\\\/").lower()', '.strip("\\\\/")'),
    # M3: no fragment rule (message tails truncated inside the profile name)
    "M3-no-fragment": ("    if name in ELLIPSES or name in PROFILE_ROOTS:\n        return None\n",
                       "    if True:\n        return None\n"),
    # M4: the final publication gate never refuses
    "M4-gate-off": ("    left = Counter()\n    for view in views:", "    return Counter()\n    for view in views:"),
    # M5: the JSON structure comparison is skipped
    "M5-no-structure-check": ("_compare(old, _load_pairs(new), policy, issues)", "_load_pairs(new)"),
    # M6: the output directory may overlap the source package
    "M6-no-overlap-guard": ("    if _inside(out_r, pkg_r) or _inside(pkg_r, out_r):", "    if False:"),
    # M7: escape-level-blind component split (\\uXXXX of a nested profile name breaks the name apart)
    "M7-naive-split": ("    escape = _separator_width(tail) // 2", "    escape = 0"),
    # M8: JSON re-serialized as a whole instead of token-wise editing
    "M8-reserialize": ("        new_records = [line for line in new_text.split",
                       "        new_text = json.dumps(json.loads(new_text), ensure_ascii=False, indent=1) "
                       "if suffix == \".json\" else new_text\n        new_records = [line for line in new_text.split"),
    # M9: UNC root accepted at any separator level (two escaped newlines read as a UNC server and share)
    "M9-no-unc-level-check": ('        if not (first_sep.startswith("/") or len(m.group("lead")) == 2 * len(first_sep)):',
                              "        if False:"),
    # M10: a rejected candidate swallows its text (search resumes at its end)
    "M10-resume-at-end": ("            pos = m.start() + 1\n            continue", "            pos = m.end()\n            continue"),
    # M11: secret-like values are not redacted
    "M11-no-secret-redaction": ("def _redact_secrets(text: str, counts: Counter) -> str:\n",
                                "def _redact_secrets(text: str, counts: Counter) -> str:\n    return text\n"),
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
    target = dest / "web_alarm" / MODULE
    changed = {}
    if variant == "baseline":
        target.unlink()
        changed[MODULE] = "REMOVED"
    else:
        replacements = MUTANTS[variant]
        replacements = replacements if isinstance(replacements, list) else [replacements]
        text = target.read_text(encoding="utf-8")
        for old, new in replacements:
            if text.count(old) != 1:
                raise SystemExit(f"{variant}: pattern found {text.count(old)} times")
            text = text.replace(old, new)
        target.write_bytes(text.encode("utf-8"))
        changed[MODULE] = hashlib.sha256(target.read_bytes()).hexdigest()
    print(json.dumps({"variant": variant, "mirror": dest.name, "changed": changed}))


if __name__ == "__main__":
    main()
