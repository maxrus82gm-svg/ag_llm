"""Compact evidence for CLAUDE-WA4-R-AUD01T02B-REPAIR-001 (read-only over TEMP attempt outputs).

Usage: collect_evidence.py <out evidence.json> <label>=<attempt base dir> [...]
Per attempt: argv/exit/wall, per-entry recount and per-method census (the runner's `passed` counter goes
negative with failing subtests), results.json SHA-256, isolation events, the source map compared with
the expected pre-repair map (R-006 pins + AUD-01/02/05 repair) and with the final repaired bytes, every
non-PASS with its tail, and the facts of this TASK's own test/probe modules.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
HERE = Path(__file__).resolve().parent.parent
PKG = REPO / "reports" / "CODEX-WA4-R-006-WINDOWS-F1F2F3-LOCAL-GATE"
pins = json.loads((PKG / "checks.json").read_bytes())["final_full_source_sha256"]
before = dict(json.loads((HERE / "baseline-gate.json").read_bytes())["source_sha256_all"])
OWN = ("test_web_alarm_aud01t02b_repair", "test_aud01t02b_rollback_compat", "test_aud02b_residual_window",
       "test_aud01t_transport_finding", "test_aud02b_microtask_finding")


def census(tests):
    methods = {}
    for t in tests:
        method = t["test"].split(" [", 1)[0].split(" (", 1)[0]
        methods.setdefault(method, set()).add(t["status"])
    verdict = Counter("PASS" if s <= {"PASS"} else "ERROR" if "ERROR" in s else "FAIL" if "FAIL" in s
                      else "SKIP" if s <= {"PASS", "SKIP"} else "+".join(sorted(s)) for s in methods.values())
    return len(methods), dict(verdict)


out = Path(sys.argv[1])
attempts = []
for arg in sys.argv[2:]:
    label, base = arg.split("=", 1)
    base = Path(base)
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    raw = (base / "out" / "results.json").read_bytes()
    res = json.loads(raw)
    methods, method_counts = census(res["tests"])
    source = res.get("source_sha256", {})
    current = {k: hashlib.sha256((REPO / k).read_bytes()).hexdigest() for k in source if (REPO / k).is_file()}
    row = {"label": label, "argv": summary["argv"], "exit": summary["exit"], "wall_seconds": summary["wall_seconds"],
           "runner_elapsed_seconds": res.get("elapsed_seconds"), "python": res.get("python"),
           "platform": res.get("platform"), "started_unix": res.get("started_unix"),
           "tests_run": res["tests_run"], "entry_recount": dict(Counter(t["status"] for t in res["tests"])),
           "methods": methods, "method_counts": method_counts,
           "runner_counts": {k: res.get(k) for k in ("passed", "failures", "errors", "skips")},
           "isolation_violations": res.get("isolation_violations", []),
           "results_json_sha256": hashlib.sha256(raw).hexdigest(), "results_json_bytes": len(raw),
           "source_map_files": len(source),
           "source_map_diff_vs_pre_repair": sorted(k for k in source if before.get(k, pins.get(k)) != source[k]),
           "source_map_diff_vs_current_bytes": sorted(k for k in source if current.get(k) != source[k]),
           "non_pass": [{"test": t["test"], "status": t["status"],
                         "detail": (t.get("reason") or t.get("error") or "")[-1200:]}
                        for t in res["tests"] if t["status"] != "PASS"],
           "temp_base": str(base)}
    own = {t["test"]: {"status": t["status"], "facts": t.get("facts", [])} for t in res["tests"]
           if t["test"].startswith(OWN)}
    if own:
        row["own_module_facts"] = own
    attempts.append(row)
out.write_text(json.dumps({"task": "CLAUDE-WA4-R-AUD01T02B-REPAIR-001", "attempts": attempts},
                          ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
for a in attempts:
    print(a["label"], "exit", a["exit"], "methods", a["methods"], a["method_counts"], "entries", a["entry_recount"],
          "iso", len(a["isolation_violations"]), "diff_pre", a["source_map_diff_vs_pre_repair"],
          "diff_now", a["source_map_diff_vs_current_bytes"], "sha", a["results_json_sha256"][:16],
          "elapsed", a["runner_elapsed_seconds"])
