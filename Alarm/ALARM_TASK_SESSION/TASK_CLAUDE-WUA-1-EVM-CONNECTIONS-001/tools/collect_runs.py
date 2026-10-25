"""Publish this TASK's run evidence only through web_alarm.evidence_sanitizer, as LF copies.

For every attempt (label=<TEMP attempt base>): the raw out/results.json and summary.json are kept unchanged in a
private disposable TEMP folder; sanitized copies go to runs/<label>/ in the TASK folder only if the publication gate
passes (a refused file is not written at all). Published = LF(sanitize(raw)); the raw SHA-256 and EOL stay in
runs-map.json. Extra files: file:<name>=<TEMP file> (batch lists, repeat tables). Every call ADDS to
runs/runs-map.json and runs/census.json (an existing label is refused, so an earlier RED is never overwritten).
Usage: collect_runs.py <label>=<attempt base> ... [file:<name>=<path> ...]
"""
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from web_alarm import evidence_sanitizer as es  # noqa: E402

TASK = "CLAUDE-WUA-1-EVM-CONNECTIONS-001"
PRIVATE = Path(tempfile.gettempdir()).resolve() / ("claude-wua1-private-" + TASK) / "runs-raw"
POLICY = es.Policy(("ag_llm",))
IDENTITY = es.identity_pattern(es.local_identity_tokens())
MAP, CENSUS = TASK_DIR / "runs" / "runs-map.json", TASK_DIR / "runs" / "census.json"
sha = lambda data: hashlib.sha256(data).hexdigest()


def eol_of(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    return "NONE" if not (crlf or lf) else "CRLF" if crlf and not lf else "LF" if lf and not crlf else "MIXED"


def publish(rel: str, raw: bytes, rows: list) -> None:
    if any(row["id"] == rel for row in rows):
        raise SystemExit(f"already collected, refusing to overwrite: {rel}")
    private = PRIVATE / rel
    private.parent.mkdir(parents=True, exist_ok=True)
    private.write_bytes(raw)
    r = es.process_bytes(rel, raw, POLICY, IDENTITY)
    row = {"id": rel, "raw_sha256": sha(raw), "raw_bytes": len(raw), "raw_eol": eol_of(raw), "safety": r.safety,
           "reasons": r.reasons, "replacements": {k: v for k, v in sorted(r.counts.items()) if k in es.REPLACED_KINDS},
           "published_sha256": None}
    if r.output is not None:
        published = r.output.replace(b"\r\n", b"\n")
        again = es.process_bytes(rel, published, POLICY, IDENTITY)
        if again.safety != "PASS" or again.output != published or b"\r" in published:
            row.update(safety="BLOCKED", reasons=r.reasons + ["lf-normalized-copy-not-stable"])
        else:
            target = TASK_DIR / "runs" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(published)
            row["published_sha256"] = sha(target.read_bytes())
            row["published_eol"] = "LF"
    rows.append(row)


def census(results: dict) -> dict:
    methods = {}
    for t in results["tests"]:  # a subTest id is "<method> (params)" or "<method> [params]" in this runner
        methods.setdefault(t["test"].split(" (", 1)[0].split(" [", 1)[0], set()).add(t["status"])
    status = {m: ("PASS" if s <= {"PASS"} else "+".join(sorted(s))) for m, s in sorted(methods.items())}
    return {"tests_run": results["tests_run"], "methods": len(status), "method_counts": dict(Counter(status.values())),
            "non_pass_methods": {m: s for m, s in status.items() if s != "PASS"},
            "isolation_violations": len(results.get("isolation_violations", [])),
            "python": results.get("python"), "platform": results.get("platform"),
            "source_files": len(results.get("source_sha256", {})),
            "changed_files_sha256": {k: v for k, v in results.get("source_sha256", {}).items()
                                     if k in ("web_alarm/ui.py", "web_alarm/server.py",
                                              "web_alarm/ultra_connections.py",
                                              "test_web_alarm_ultra_connections.py")}}


rows = json.loads(MAP.read_text(encoding="utf-8"))["files"] if MAP.exists() else []
runs = json.loads(CENSUS.read_text(encoding="utf-8"))["runs"] if CENSUS.exists() else {}
added = []
for arg in sys.argv[1:]:
    if arg.startswith("file:"):
        name, path = arg[5:].split("=", 1)
        publish(name, Path(path).read_bytes(), rows)
        added.append(name)
        continue
    label, base = arg.split("=", 1)
    if label in runs:
        raise SystemExit(f"run label already collected: {label}")
    base = Path(base)
    results_raw = (base / "out" / "results.json").read_bytes()
    summary_raw = (base / "summary.json").read_bytes()
    publish(f"{label}/results.json", results_raw, rows)
    publish(f"{label}/summary.json", summary_raw, rows)
    runs[label] = census(json.loads(results_raw)) | {"exit": json.loads(summary_raw)["exit"]}
    added.append(label)
(TASK_DIR / "runs").mkdir(exist_ok=True)
MAP.write_text(json.dumps({"task": TASK, "files": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
               newline="\n")
CENSUS.write_text(json.dumps({"task": TASK, "runs": runs}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                  newline="\n")
blocked = [r["id"] for r in rows if r["safety"] != "PASS"]
print(json.dumps({"added": added, "files_total": len(rows), "blocked": blocked}, ensure_ascii=True))
