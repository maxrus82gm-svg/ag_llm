"""Build a disposable TEMP mirror of the repository code for Gate A (RED on the original module) and Gate C mutants.

Usage: build_mirror.py <variant> <dest>
  "baseline": web_alarm/evidence_sanitizer.py replaced by the exact pre-repair bytes (SHA-256 checked below); the new
              tests stay, so the original fail-open behaviour is reproduced. The bytes are read from the file named by
              CLAUDE_BASELINE_MODULE: the module as published by CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001 (e.g. from
              GitHub at the coordinator's baseline commit). The copy is not kept in the published report folder:
              its illustrative path comments would fail this TASK's own publication gate.
  "<mutant>": one exact, single-occurrence replacement (or a list of them) in the repaired module (MUTANTS).
Copies only top-level *.py and web_alarm/*.py (read-only use of the repository); refuses a dest outside TEMP or an
existing dest. The repository root comes from this file's location. Prints one JSON line (relative names only).
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BASELINE_SHA256 = "1b4fb52e1e2736ac3c7ccd97c534a3acc1aba3ea5b2fe2481ea42f23e8cc4201"
MODULE = "evidence_sanitizer.py"

MUTANTS = {
    # R1: stage ignores manifest SHA-256 / size / entry problems (the original F-ES-01 behaviour in stage)
    "R1-stage-ignores-manifest": ("                check = (status, match)\n                for reason in reasons:\n"
                                  "                    r.refuse(reason)\n",
                                  "                check = (status, match)\n"),
    # R2: verify does not re-prove manifest integrity (trusts the mapping's safety claims)
    "R2-verify-trusts-manifest": ("        results[rel][2] = (status, match)\n        for reason in reasons:\n"
                                  "            results[rel][1].refuse(reason)\n",
                                  "        results[rel][2] = (status, match)\n"),
    # R3: an internally consistent bundle is safe even when completeness is not proven
    "R3-no-completeness-anchor": (' and not blocked and completeness != "NOT_PROVEN" else "REFUSED"}',
                                  ' and not blocked else "REFUSED"}'),
    # R4: the source inventory is not compared with the mapping (added / removed files go unnoticed)
    "R4-no-inventory-compare": ("            if set(source.ids) != ids or len(rows) != total:", "            if False:"),
    # R5: links / junctions inside the bundle are not reported
    "R5-links-ignored": ("    if links:\n        problems[\"link-in-bundle\"] += links", "    if False:\n        pass"),
    # R6: every mapped id is read, unvalidated, even if it is not a walked file inside originals/
    "R6-read-unvalidated-ids": [("    if _id_problem(rel):\n        return \"unsafe-id\"\n    valid = (",
                                 "    valid = ("),
                                ("    for rel in sorted(ids & originals):", "    for rel in sorted(ids):")],
    # R7: files_total / files_blocked / files_changed / verdict of the mapping are not recomputed
    "R7-totals-trusted": ("            mapping.get(\"verdict\")) != (total, blocked, changed, expected_verdict):",
                          "            mapping.get(\"verdict\")) != (mapping.get(\"files_total\"), "
                          "mapping.get(\"files_blocked\"), mapping.get(\"files_changed\"), mapping.get(\"verdict\")):"),
    # R8: duplicate JSON keys accepted (the last value silently wins)
    "R8-duplicate-keys-accepted": ("        if len(keys) != len(set(keys)):", "        if False:"),
    # R9: files present in the package but missing from the manifest are not refused
    "R9-unlisted-accepted": ("                check = (\"NOT_LISTED\", None)\n                r.refuse(\"not-listed-in-manifest\")\n",
                             "                check = (\"NOT_LISTED\", None)\n"),
    # R10: the candidate keeps the stale manifest (hashes of the originals)
    "R10-no-candidate-rehash": ("        if candidate is not None:\n            manifest_result.output = candidate\n",
                                "        if candidate is not None:\n            pass\n"),
    # R11: a repository anchor may be a profile/system folder name (e.g. "users")
    "R11-anchor-unchecked": ("or low in (\".\", \"..\") \\\n                or low in ANCHOR_FORBIDDEN:",
                             "or low in (\".\", \"..\"):"),
    # R13: a local name in a file id is published (only file contents are gated)
    "R13-file-name-unchecked": ("    if identity is not None and identity.search(rel):\n        result.refuse(\"identity-in-file-name\")\n",
                                ""),
    # R12: a deeply nested manifest crashes instead of being refused
    "R12-recursion-not-refused": ("    except (ValueError, RecursionError):\n        raise IntegrityRefusal(\"manifest.json is not valid",
                                  "    except ValueError:\n        raise IntegrityRefusal(\"manifest.json is not valid"),
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
    if variant == "baseline":
        data = Path(os.environ["CLAUDE_BASELINE_MODULE"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE_SHA256:
            raise SystemExit("CLAUDE_BASELINE_MODULE is not the pre-repair module")
        target.write_bytes(data)
    else:
        replacements = MUTANTS[variant]
        replacements = replacements if isinstance(replacements, list) else [replacements]
        text = target.read_text(encoding="utf-8")
        for old, new in replacements:
            if text.count(old) != 1:
                raise SystemExit(f"{variant}: pattern found {text.count(old)} times")
            text = text.replace(old, new)
        target.write_bytes(text.encode("utf-8"))
    print(json.dumps({"variant": variant, "mirror": dest.name,
                      "changed": {MODULE: hashlib.sha256(target.read_bytes()).hexdigest()}}))


if __name__ == "__main__":
    main()
