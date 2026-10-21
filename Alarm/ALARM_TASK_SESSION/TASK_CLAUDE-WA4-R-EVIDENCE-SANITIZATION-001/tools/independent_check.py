"""Independent oracle over a staged set (does not import web_alarm.evidence_sanitizer).

1. Raw byte search in every sanitized file for this machine's identity: the absolute TEMP, home and repository roots
   (any occurrence) and the user / computer / profile-folder names (at an alphanumeric word boundary; occurrences
   inside another word are counted separately as false positives of a plain substring search), case-insensitive, in
   UTF-8, UTF-16-LE (both alignments), with 1, 2, 4 and 8 backslashes per separator, forward slashes and \\uXXXX
   escapes. Values are never printed.
2. Evidence value: for every JSON original/sanitized pair the non-string leaves, list lengths, key counts and every
   ``status`` / ``test`` / ``exit`` string must be identical; per-method status census of runner results.json too.
3. SHA-256 recomputed for every original and sanitized file against mapping.json.
Usage: independent_check.py <staging dir> [--originals]   Prints one JSON object (counts only).
  --originals runs the identity search on the preserved originals instead (the RED side of the same oracle).
"""
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

out = Path(sys.argv[1])
mapping = json.loads((out / "mapping.json").read_bytes())
repo = Path(__file__).resolve().parents[4]
roots = [str(Path(tempfile.gettempdir()).resolve()), str(Path.home()), str(repo)]
names = {v for v in (os.environ.get("USERNAME"), os.environ.get("COMPUTERNAME"), Path.home().name) if v}


def forms(value: str) -> set:
    parts = value.replace("/", "\\").split("\\")
    found = {value.lower()}
    for width in (1, 2, 4, 8):
        found.add(("\\" * width).join(parts).lower())
    found.add("/".join(parts).lower())
    found.add(json.dumps(value.lower())[1:-1])
    return found


needles = set()  # absolute roots: any occurrence is a leak
for value in roots:
    needles |= forms(value)
name_needles = {json.dumps(v.lower())[1:-1] for v in names} | {v.lower() for v in names}


def name_hits(view: str) -> tuple[int, int]:
    """(at a word boundary = leak, inside another word = false positive of a plain substring search)."""
    leak = inside = 0
    for needle in name_needles:
        start = view.find(needle)
        while start != -1:
            end = start + len(needle)
            before = view[start - 1] if start else " "
            after = view[end] if end < len(view) else " "
            if before.isalnum() or after.isalnum():
                inside += 1
            else:
                leak += 1
            start = view.find(needle, start + 1)
    return leak, inside


def views(data: bytes):
    yield data.decode("utf-8", "replace").lower()
    for shift in (0, 1):
        chunk = data[shift:]
        yield chunk[:len(chunk) // 2 * 2].decode("utf-16-le", "replace").lower()


def leaf_signature(node, sig: Counter, path: str = ""):
    if isinstance(node, dict):
        sig["dict:" + path + ":" + str(len(node))] += 1
        for key, value in node.items():
            child = path + "/" + (key if key in ("status", "test", "exit", "tests", "tests_run") else "*")
            leaf_signature(value, sig, child)
            if key in ("status", "test", "exit") and isinstance(value, str):
                sig["protected:" + key + "=" + value] += 1
    elif isinstance(node, list):
        sig["list:" + path + ":" + str(len(node))] += 1
        for value in node:
            leaf_signature(value, sig, path + "[]")
    elif not isinstance(node, str):
        sig["leaf:" + path + ":" + repr(node)] += 1


def census(doc) -> dict:
    methods = {}
    for t in doc.get("tests", []) if isinstance(doc, dict) else []:
        if isinstance(t, dict) and "test" in t:
            methods.setdefault(t["test"].split(" [", 1)[0], set()).add(t.get("status"))
    return {m: "+".join(sorted(map(str, s))) for m, s in sorted(methods.items())}


report = Counter()
mismatch = []
for row in mapping["files"]:
    original = (out / "originals" / row["id"]).read_bytes()
    report["sha_original_ok"] += hashlib.sha256(original).hexdigest() == row["source_sha256"]
    if not row["sanitized_id"]:
        report["blocked"] += 1
        continue
    sanitized = (out / row["sanitized_id"]).read_bytes()
    report["sha_sanitized_ok"] += hashlib.sha256(sanitized).hexdigest() == row["sanitized_sha256"]
    texts = list(views(original if "--originals" in sys.argv[2:] else sanitized))
    if any(needle in view for view in texts for needle in needles):
        report["absolute_root_left"] += 1
        mismatch.append(row["id"] + ": absolute TEMP/home/repository root left")
    leak, inside = max(name_hits(view) for view in texts)
    if leak:
        report["name_left_at_word_boundary"] += 1
        mismatch.append(row["id"] + ": local name left")
    if inside:
        report["name_inside_other_word_false_positive_files"] += 1
    if row["kind"] == "json":
        a, b = json.loads(original), json.loads(sanitized)
        sa, sb = Counter(), Counter()
        leaf_signature(a, sa)
        leaf_signature(b, sb)
        if sa != sb:
            mismatch.append(row["id"] + ": structure/leaf signature differs")
        report["json_pairs"] += 1
        if census(a):
            report["results_with_census"] += 1
            if census(a) != census(b) or a.get("tests_run") != b.get("tests_run") or \
                    len(a.get("isolation_violations", [])) != len(b.get("isolation_violations", [])):
                mismatch.append(row["id"] + ": census differs")
    report["files"] += 1
print(json.dumps({"root_needles": len(needles), "name_needles": len(name_needles), "files_checked": report["files"], "counts": dict(sorted(report.items())),
                  "mismatches": mismatch}, ensure_ascii=True, indent=1))
