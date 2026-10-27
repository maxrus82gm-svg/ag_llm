"""Build manifest.json for CLAUDE-WUA-CHAT-LAUNCHER-001: the new project files, proof that the stage-1 files are
unchanged, every package file, and the publication scan (web_alarm.evidence_sanitizer, must exit 0).
Usage: make_manifest.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
NEW = {"Start_WebAlarm.bat": "the one permanent launcher (ASCII, CRLF)",
       "web_alarm/launcher.py": "launcher logic: standard launch, test profiles, marking, port guard",
       "web_alarm/launch_config.json": "launch selection, shipped with active=standard",
       "test_web_alarm_launcher.py": "16 tests, part of the Web Alarm 'all' discovery"}


def facts(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "eol": "CRLF" if b"\r\n" in data else ("LF" if b"\n" in data else "none")}


s1 = json.loads((REPO / "reports" / "CLAUDE-WUA-CHAT-S1-READONLY-UI-001" / "manifest.json").read_text(encoding="utf-8"))
s1_unchanged = {rel: facts(REPO / rel)["sha256"] == row["sha256"] for rel, row in s1["changed_files"].items()}
rows, problems = [], []
for path in sorted(p for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json"):
    data = path.read_bytes()
    rel = path.relative_to(PACKAGE).as_posix()
    if b"\r" in data:
        problems.append(f"CR in {rel}")
    if any(chr(code) in data.decode("utf-8") for code in (0x85, 0x2028, 0x2029)):
        problems.append(f"unsafe separator in {rel}")
    rows.append({"path": rel, **facts(path)})
scan = subprocess.run([sys.executable, "-B", "-m", "web_alarm.evidence_sanitizer", "--repo-anchor", "ag_llm", "scan",
                       str(PACKAGE)], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
if scan.returncode != 0:
    problems.append(f"evidence_sanitizer scan exit {scan.returncode}")
if not all(s1_unchanged.values()):
    problems.append("stage-1 files changed")
if problems:
    sys.exit("manifest refused: " + "; ".join(problems))
evidence = {}
for path in sorted((PACKAGE / "evidence").glob("*.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    evidence[path.name] = {key: value[key] for key in ("purpose", "runner_exit", "tests_run", "failures", "errors", "skips",
                                                        "isolation_violations", "killed", "mutants") if key in value}
manifest = {
    "task": "CLAUDE-WUA-CHAT-LAUNCHER-001", "executor": "Claude 008", "source": "chat task (BLOCK 1 holds stage 1)",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "new_files": {rel: {"role": role, **facts(REPO / rel)} for rel, role in NEW.items()},
    "existing_files_changed": [],
    "stage1_files_unchanged": s1_unchanged,
    "evidence_summary": evidence,
    "evidence_sanitizer_scan_before_manifest": json.loads(scan.stdout)["classes"],
    "git_used": "one accidental read-only `git status --porcelain` at package closeout, after all checks; output discarded, nothing changed (DOC-GIT-01 breach, disclosed in report.md)",
    "network_used": False, "real_standard_storage_used": False,
    "files": rows,
}
(PACKAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"package_files": len(rows), "scan": manifest["evidence_sanitizer_scan_before_manifest"],
                  "stage1_unchanged": all(s1_unchanged.values())}))
