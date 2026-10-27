"""Build manifest.json: the changed project files (with their stage-0 base hash) and every file of this package.

Refuses when a package file is not LF-only, holds U+0085/U+2028/U+2029, or the publication scan of
web_alarm.evidence_sanitizer does not exit 0. Run the scan once more after the manifest exists.
Usage: make_manifest.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
CHANGED = {"context_storage.py": "production, additive read functions only",
           "web_alarm/ultra_chat.py": "production, new read-only adapter",
           "web_alarm/server.py": "production, routes, shared origin check, switch",
           "web_alarm/ui.py": "production, Ultra Chat screen and three sections",
           "test_ultra_chat_read.py": "test, new", "test_web_alarm_ultra_chat.py": "test, new",
           "test_web_alarm_ultra_chat_ui.js": "test, new", "test_web_alarm_evm_ui.js": "test, E1/E8 only"}


def facts(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "eol": "CRLF" if b"\r\n" in data else ("LF" if b"\n" in data else "none")}


preflight = json.loads((PACKAGE / "evidence" / "preflight_base.json").read_text(encoding="utf-8"))["compared"]
changed = {rel: {"role": role, **facts(REPO / rel),
                 "stage0_sha256": preflight[rel]["stage0_sha256"] if rel in preflight else None}
           for rel, role in CHANGED.items()}
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
if problems:
    sys.exit("manifest refused: " + "; ".join(problems))
evidence = {}
for path in sorted((PACKAGE / "evidence").glob("*.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    keep = {key: value[key] for key in ("purpose", "runner_exit", "tests_run", "failures", "errors", "skips",
                                         "isolation_violations", "killed", "mutants", "all_complete", "drift_since_stage0")
            if key in value}
    evidence[path.name] = keep
manifest = {
    "task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "program": "No.37 stage 1", "executor": "Claude 008",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "open": ["independent Windows/visual acceptance of stage 1", "independent EVM Windows/visual gate (unchanged, OPEN)"],
    "base": {"published": "main@734cbfc9d5c5800cf610241c19693ddad9f77cd6 (stage 0, WEB_14 PASS)",
             "method": "stage-0 baseline hashes vs local bytes, and inverse of the described edits (no Git)"},
    "changed_files": changed,
    "evidence_summary": evidence,
    "evidence_sanitizer_scan_before_manifest": json.loads(scan.stdout)["classes"],
    "git_used": False, "network_used": False, "real_workspaces_used": False,
    "files": rows,
}
(PACKAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                       newline="\n")
print(json.dumps({"package_files": len(rows), "changed": len(changed), "scan": manifest["evidence_sanitizer_scan_before_manifest"]}))
