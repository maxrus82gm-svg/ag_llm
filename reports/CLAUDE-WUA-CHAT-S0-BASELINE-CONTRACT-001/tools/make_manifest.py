"""Build manifest.json of this task package: every file except the manifest itself, with bytes, SHA-256 and line endings.

Refuses to write when a file is not LF-only or contains U+0085/U+2028/U+2029, and when the publication scan of
web_alarm.evidence_sanitizer does not exit 0. The scan is run before the manifest exists; run it once more afterwards.
Usage: make_manifest.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
files = sorted(p for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json")
rows, problems = [], []
for path in files:
    data = path.read_bytes()
    text = data.decode("utf-8")
    if b"\r" in data:
        problems.append(f"CR in {path.relative_to(PACKAGE).as_posix()}")
    if any(chr(code) in text for code in (0x85, 0x2028, 0x2029)):
        problems.append(f"unsafe separator in {path.relative_to(PACKAGE).as_posix()}")
    rows.append({"path": path.relative_to(PACKAGE).as_posix(), "bytes": len(data),
                 "sha256": hashlib.sha256(data).hexdigest(), "eol": "LF" if b"\n" in data else "none"})
scan = subprocess.run([sys.executable, "-B", "-m", "web_alarm.evidence_sanitizer", "--repo-anchor", "ag_llm", "scan",
                       str(PACKAGE)], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
if scan.returncode != 0:
    problems.append(f"evidence_sanitizer scan exit {scan.returncode}")
if problems:
    sys.exit("manifest refused: " + "; ".join(problems))
report = json.loads(scan.stdout)
probes = json.loads((PACKAGE / "evidence" / "probe_runs.json").read_text(encoding="utf-8"))
regression = json.loads((PACKAGE / "evidence" / "regression_baseline.json").read_text(encoding="utf-8"))
baseline = json.loads((PACKAGE / "evidence" / "baseline.json").read_text(encoding="utf-8"))
gate_runs = json.loads((PACKAGE / "evidence" / "access_gate_runs.json").read_text(encoding="utf-8"))
mutants = json.loads((PACKAGE / "evidence" / "access_gate_mutants.json").read_text(encoding="utf-8"))
picker = json.loads((PACKAGE / "evidence" / "picker_server_baseline.json").read_text(encoding="utf-8"))
manifest = {
    "task": "CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001",
    "program": "No.37 stage 0",
    "executor": "Claude 008",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "revision": 2,
    "amendments": [{
        "id": "AMENDMENT-1",
        "source": "ChatGPT coordinator after independent review of revision 1, relayed by the user in chat",
        "finding": "history read token was taken from /ui/capabilities, which hands out a token only when the "
                   "folder picker is available (off by default in create_server)",
        "resolution": "own capability ultra_chat_read: GET /ui/ultra-chat/capability, own token in "
                      "X-WebAlarm-Ultra-Chat-Token, loopback only, independent of the folder picker; "
                      "same Host/Origin/Sec-Fetch-Site rules; one scope (GET /ultra/chat/* of the issuing process)",
        "updated": ["architecture-contract.md 7.1, 7.1.1, 9", "stage1-handoff.md 3, 4, 5, 6, 8",
                    "report.md 1, 4.1, 8, 9, 10, 12, 13, 15", "manifest.json"],
    }],
    "base_revision_block1": "main@d33056e6e8ff64bc2a17f85865185fd253590e53",
    "base_check": {"method": "Astra rev2 section 2.2 manifest vs local bytes (no Git)",
                   "rows": baseline["manifest_rows"], "matched": baseline["matched"],
                   "mismatched": baseline["mismatched"],
                   "missing_named_files": [k for k, v in baseline["additional_files"].items() if not v["exists"]]},
    "checks": {
        "probes": {"attempts": len(probes["attempts"]),
                   "tests_per_attempt": sorted({a["tests_run"] for a in probes["attempts"]}),
                   "non_pass": sum(1 for a in probes["attempts"] for t in a["tests"] if t["status"] != "PASS"),
                   "isolation_violations": sum(a["isolation_violations"] for a in probes["attempts"]),
                   "runner_exit_codes": sorted({a["runner_exit"] for a in probes["attempts"]})},
        "regression_baseline": {k: regression[k] for k in ("tests_run", "failures", "errors", "skips",
                                                            "isolation_violations", "runner_exit")},
        "amendment1_access_prototype": {
            "attempts": len(gate_runs["attempts"]),
            "tests_per_attempt": sorted({a["tests_run"] for a in gate_runs["attempts"]}),
            "non_pass": sum(1 for a in gate_runs["attempts"] for t in a["tests"] if t["status"] != "PASS"),
            "isolation_violations": sum(a["isolation_violations"] for a in gate_runs["attempts"]),
            "runner_exit_codes": sorted({a["runner_exit"] for a in gate_runs["attempts"]})},
        "amendment1_mutants": {"control": mutants["control"], "killed": mutants["killed"], "mutants": mutants["mutants"]},
        "amendment1_picker_server_baseline": {k: picker[k] for k in ("tests_run", "failures", "errors", "skips",
                                                                     "isolation_violations", "runner_exit")},
        "evidence_sanitizer_scan_before_manifest": {"exit": scan.returncode, "files_scanned": report["files_scanned"],
                                                    "classes": report["classes"]},
    },
    "not_run": ["full Web Alarm 'all' regression (no production or test change)", "browser visual check",
                "symlink scenarios (no privilege)", "POSIX behaviour", "Git / GitHub / real API (forbidden)"],
    "write_scope": "reports/CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001/ only",
    "git_used": False,
    "files": rows,
}
(PACKAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                       newline="\n")
print(json.dumps({"files": len(rows), "scan_exit": scan.returncode, "classes": report["classes"]}))
