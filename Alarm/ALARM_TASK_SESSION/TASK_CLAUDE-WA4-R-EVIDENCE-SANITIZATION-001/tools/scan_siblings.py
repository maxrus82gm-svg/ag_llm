"""Read-only scan of the other evidence packages with web_alarm.evidence_sanitizer (counts and classes only).

Scans every Alarm/ALARM_TASK_SESSION/TASK_* folder and reports/CLAUDE-* folder except this TASK's own, all files
(not just a manifest). Writes inventory/siblings-scan.json: package name -> files, classes, findings. Values are
never printed or stored. Nothing is written into the scanned packages.
Usage: scan_siblings.py
"""
import json
import sys
import time
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from web_alarm import evidence_sanitizer as es  # noqa: E402

POLICY = es.Policy(("ag_llm",))
IDENTITY = es.identity_pattern(es.local_identity_tokens())
packages = sorted([*(REPO / "Alarm" / "ALARM_TASK_SESSION").glob("TASK_*"), *(REPO / "reports").glob("CLAUDE-*")])
rows = {}
for pkg in packages:
    if not pkg.is_dir() or pkg.resolve() == TASK_DIR.resolve():
        continue
    started = time.time()
    try:
        report = es.scan(pkg, False, POLICY, IDENTITY)
        rows[pkg.parent.name + "/" + pkg.name] = {
            "files": report["files_scanned"], "classes": report["classes"], "findings": report["findings_total"],
            "files_with_local_name": sum(1 for f in report["files"] if f.get("identity_hits")),
            "seconds": round(time.time() - started, 1)}
    except Exception as exc:  # noqa: BLE001 - record and continue, never print paths
        rows[pkg.parent.name + "/" + pkg.name] = {"error": type(exc).__name__}
    print(pkg.name, rows[pkg.parent.name + "/" + pkg.name].get("classes"), flush=True)
leaking = {k: v for k, v in rows.items() if v.get("files_with_local_name")}
summary = {"packages_scanned": len(rows), "packages_with_local_name": len(leaking),
           "files_with_local_name": sum(v["files_with_local_name"] for v in leaking.values()),
           "packages_with_any_path_finding": sum(1 for v in rows.values()
                                                 if any(k.startswith(("CONFIRMED", "SUSPECT"))
                                                        for k in v.get("classes", {})))}
(TASK_DIR / "inventory").mkdir(exist_ok=True)
(TASK_DIR / "inventory" / "siblings-scan.json").write_text(
    json.dumps({"tool": "web_alarm.evidence_sanitizer", "policy": POLICY.as_dict(), "summary": summary,
                "packages": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(summary))
