"""Collect the compact evidence for CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001 (read-only over TEMP outputs).
Usage: collect_evidence.py <out evidence.json> <attempt base dir> [<attempt base dir> ...]
For every attempt: argv/exit/wall, counts recomputed from results.json, results.json SHA-256, isolation events,
source-map equality with the R-006 pins, every non-PASS with its tail, and (for the probe module) all facts."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

PKG = Path(r"M:\GitHub\ag_llm\reports\CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE")
pins = json.loads((PKG / "checks.json").read_bytes())["final_full_source_sha256"]
out = Path(sys.argv[1])
attempts = []
for base in map(Path, sys.argv[2:]):
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    raw = (base / "out" / "results.json").read_bytes()
    res = json.loads(raw)
    counts = Counter(t["status"] for t in res["tests"])
    row = {"label": summary["label"], "argv": summary["argv"], "exit": summary["exit"],
           "wall_seconds": summary["wall_seconds"], "runner_elapsed_seconds": res["elapsed_seconds"],
           "python": res["python"], "platform": res["platform"], "started_unix": res["started_unix"],
           "tests_run": res["tests_run"], "recount": dict(counts),
           "runner_counts": {k: res[k] for k in ("passed", "failures", "errors", "skips")},
           "unique_ids": len({t["test"] for t in res["tests"]}),
           "isolation_violations": res["isolation_violations"],
           "results_json_sha256": hashlib.sha256(raw).hexdigest(), "results_json_bytes": len(raw),
           "source_map_files": len(res["source_sha256"]),
           "source_map_diff_vs_R006_pins": sorted(k for k in set(res["source_sha256"]) | set(pins)
                                                  if res["source_sha256"].get(k) != pins.get(k)),
           "non_pass": [{"test": t["test"], "status": t["status"],
                         "detail": (t.get("reason") or t.get("error") or "")[-1200:]}
                        for t in res["tests"] if t["status"] != "PASS"],
           "temp_base": str(base)}
    addressed = ("test_claude_r006_independent", "test_web_alarm_aud010205_repair", "quality_controls_aud010205",
                 "test_aud01t_transport_finding", "test_aud02b_microtask_finding", "test_rollback_compatibility")
    if any(t["test"].startswith(addressed) for t in res["tests"]):
        row["probe_facts"] = {t["test"]: {"status": t["status"], "facts": t.get("facts", [])}
                              for t in res["tests"] if t["test"].startswith(addressed)}
    attempts.append(row)
out.write_text(json.dumps({"task": "CLAUDE-WA4-R-AUD010205-REPAIR-001", "attempts": attempts},
                          ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
for a in attempts:
    print(a["label"], "exit", a["exit"], a["recount"], "iso", len(a["isolation_violations"]),
          "srcdiff", a["source_map_diff_vs_R006_pins"][:4], "sha", a["results_json_sha256"][:16],
          "elapsed", a["runner_elapsed_seconds"])
