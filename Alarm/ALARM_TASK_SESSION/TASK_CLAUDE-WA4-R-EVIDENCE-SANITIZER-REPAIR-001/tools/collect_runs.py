"""Publish this TASK's own run evidence through web_alarm.evidence_sanitizer (the new tool eats its own dog food).

For every attempt (label=<TEMP attempt base>): the raw out/results.json and summary.json are copied unchanged into
a private disposable TEMP folder (logs/ is outside this TASK's write scope); sanitized copies go to
runs/<label>/ in the TASK folder only if the publication gate passes (a refused file is not written at all).
Extra files: <name>=<TEMP file> (e.g. a mutant batch attempts list). Writes runs/runs-map.json (raw -> published
SHA-256, replacements, gate) and runs/census.json (per-method status counts taken from the raw results).
Usage: collect_runs.py <label>=<attempt base> ... [file:<name>=<path> ...]
"""
import hashlib
import json
import shutil
import tempfile
import sys
from collections import Counter
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from web_alarm import evidence_sanitizer as es  # noqa: E402

TASK = "CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001"
PRIVATE = Path(tempfile.gettempdir()).resolve() / ("claude-esrep-private-" + TASK) / "runs-raw"
POLICY = es.Policy(("ag_llm",))
IDENTITY = es.identity_pattern(es.local_identity_tokens())
sha = lambda data: hashlib.sha256(data).hexdigest()


def publish(rel: str, raw: bytes, rows: list) -> None:
    private = PRIVATE / rel
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_bytes(raw)
    r = es.process_bytes(rel, raw, POLICY, IDENTITY)
    row = {"id": rel, "raw_sha256": sha(raw), "raw_bytes": len(raw), "safety": r.safety, "reasons": r.reasons,
           "replacements": {k: v for k, v in sorted(r.counts.items()) if k in es.REPLACED_KINDS},
           "published_sha256": None}
    if r.output is not None:
        target = TASK_DIR / "runs" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(r.output)
        row["published_sha256"] = sha(target.read_bytes())
    rows.append(row)


def census(results: dict) -> dict:
    methods = {}
    for t in results["tests"]:  # a subTest id is "<method> (params)" in this runner, "<method> [params]" elsewhere
        methods.setdefault(t["test"].split(" (", 1)[0].split(" [", 1)[0], set()).add(t["status"])
    status = {m: ("PASS" if s <= {"PASS"} else "+".join(sorted(s))) for m, s in sorted(methods.items())}
    return {"tests_run": results["tests_run"], "methods": len(status), "method_counts": dict(Counter(status.values())),
            "non_pass_methods": {m: s for m, s in status.items() if s != "PASS"},
            "isolation_violations": len(results.get("isolation_violations", [])),
            "python": results.get("python"), "platform": results.get("platform"),
            "source_files": len(results.get("source_sha256", {})),
            "new_module_sha256": {k: v for k, v in results.get("source_sha256", {}).items()
                                  if "evidence_sanitizer" in k}}


rows, runs = [], {}
for arg in sys.argv[1:]:
    if arg.startswith("file:"):
        name, path = arg[5:].split("=", 1)
        publish(name, Path(path).read_bytes(), rows)
        continue
    label, base = arg.split("=", 1)
    base = Path(base)
    results_raw = (base / "out" / "results.json").read_bytes()
    summary_raw = (base / "summary.json").read_bytes()
    publish(f"{label}/results.json", results_raw, rows)
    publish(f"{label}/summary.json", summary_raw, rows)
    runs[label] = census(json.loads(results_raw)) | {"exit": json.loads(summary_raw)["exit"]}
(TASK_DIR / "runs").mkdir(exist_ok=True)
(TASK_DIR / "runs" / "runs-map.json").write_text(json.dumps({"task": TASK, "files": rows}, ensure_ascii=False,
                                                            indent=1) + "\n", encoding="utf-8", newline="\n")
(TASK_DIR / "runs" / "census.json").write_text(json.dumps({"task": TASK, "runs": runs}, ensure_ascii=False,
                                                          indent=1) + "\n", encoding="utf-8", newline="\n")
blocked = [r["id"] for r in rows if r["safety"] != "PASS"]
print(json.dumps({"published": len(rows) - len(blocked), "blocked": blocked,
                  "runs": {k: {x: v[x] for x in ("tests_run", "method_counts", "isolation_violations", "exit")}
                           for k, v in runs.items()}}, ensure_ascii=True))
