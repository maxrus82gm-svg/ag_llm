"""Per-method comparison of two full-suite results.json files, plus the run's source map against the current tree.

Usage: compare_full.py <previous results.json> <new results.json> <out.json>
Prints/writes counts and method names only (no messages, no paths).
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def methods(path: Path) -> dict:
    doc = json.loads(path.read_bytes())
    found = {}
    for t in doc["tests"]:  # subTest ids: "<method> (params)" in this runner, "<method> [params]" elsewhere
        found.setdefault(t["test"].split(" (", 1)[0].split(" [", 1)[0], set()).add(t["status"])
    return {m: ("PASS" if s <= {"PASS"} else "+".join(sorted(s))) for m, s in found.items()}, doc


old, _ = methods(Path(sys.argv[1]))
new, doc = methods(Path(sys.argv[2]))
source = doc.get("source_sha256", {})
drift = sorted(rel for rel, digest in source.items()
               if not (REPO / rel).is_file() or hashlib.sha256((REPO / rel).read_bytes()).hexdigest() != digest)
report = {
    "previous_methods": len(old), "new_methods": len(new),
    "added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
    "status_changed": {m: [old[m], new[m]] for m in sorted(set(old) & set(new)) if old[m] != new[m]},
    "new_non_pass": {m: s for m, s in sorted(new.items()) if s != "PASS"},
    "tests_run": doc["tests_run"], "isolation_violations": len(doc.get("isolation_violations", [])),
    "source_map_files": len(source), "source_drift_vs_current_tree": drift,
}
Path(sys.argv[3]).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 6 else f"{len(v)} items") for k, v in report.items()},
                 ensure_ascii=True))
