"""Build manifest.json for CLAUDE-WUA-EVM-MODEL-CARD-UI-001: new and changed project files (changed ones with their
stage-1 pin), proof that the other stage-1 and launcher files are unchanged, every package file, and the publication
scan (web_alarm.evidence_sanitizer, must exit 0). Text files of the package must be LF without unsafe separators.
Usage: make_manifest.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
NEW = {"web_alarm/model_cards.py": "server side of the cards: role facts, card data, profiles, one API status, checks",
       "test_web_alarm_model_cards.py": "17 tests, part of the Web Alarm 'all' discovery"}
CHANGED = {"web_alarm/server.py": "routes /ultra/model-cards*, local-origin guard for them, WebAlarmApi wiring",
           "web_alarm/ui.py": "EVM model card component, settings and diagnostics windows, chat choice outside the cards, "
                              "disabled voice-input place in the chat composer",
           "test_web_alarm_evm_ui.js": "E2/E3/E4/E7 rewritten for the new cards, E10-E20 added"}
OTHER_CHANGED = {"test_web_alarm_ultra_connections.py": "one needle: the removed card text 'API не проверено' is now required "
                                                        "to be absent; the diagnostic window is required instead"}
BINARY = {".png"}


def facts(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "eol": "binary" if path.suffix in BINARY else "CRLF" if b"\r\n" in data else ("LF" if b"\n" in data else "none")}


def manifest(rel_report: str) -> dict:
    return json.loads((REPO / "reports" / rel_report / "manifest.json").read_text(encoding="utf-8"))


s1, launcher = manifest("CLAUDE-WUA-CHAT-S1-READONLY-UI-001"), manifest("CLAUDE-WUA-CHAT-LAUNCHER-001")
changed = {rel: {"role": role, **facts(REPO / rel), "stage1_pin_sha256": s1["changed_files"][rel]["sha256"]}
           for rel, role in CHANGED.items()}
s1_unchanged = {rel: facts(REPO / rel)["sha256"] == row["sha256"] for rel, row in s1["changed_files"].items() if rel not in CHANGED}
launcher_unchanged = {rel: facts(REPO / rel)["sha256"] == row["sha256"] for rel, row in launcher["new_files"].items()}
rows, problems = [], []
for path in sorted(p for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json"):
    data = path.read_bytes()
    rel = path.relative_to(PACKAGE).as_posix()
    if path.suffix not in BINARY:
        if b"\r" in data:
            problems.append(f"CR in {rel}")
        if any(chr(code) in data.decode("utf-8") for code in (0x85, 0x2028, 0x2029)):
            problems.append(f"unsafe separator in {rel}")
    rows.append({"path": rel, **facts(path)})
scan = subprocess.run([sys.executable, "-B", "-m", "web_alarm.evidence_sanitizer", "--repo-anchor", "ag_llm", "scan",
                       str(PACKAGE)], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
if scan.returncode != 0:
    problems.append(f"evidence_sanitizer scan exit {scan.returncode}")
if not all(s1_unchanged.values()) or not all(launcher_unchanged.values()):
    problems.append("a stage-1 or launcher file outside this task changed")
if any(row["sha256"] == row["stage1_pin_sha256"] for row in changed.values()):
    problems.append("a file listed as changed is still the stage-1 pin")
if problems:
    sys.exit("manifest refused: " + "; ".join(problems))
evidence = {}
for path in sorted((PACKAGE / "evidence").glob("*.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    evidence[path.name] = {key: value[key] for key in ("purpose", "runner_exit", "tests_run", "failures", "errors", "skips",
                                                        "isolation_violations", "killed", "mutants", "pass", "fail")
                           if key in value}
record = {
    "task": "CLAUDE-WUA-EVM-MODEL-CARD-UI-001", "executor": "Claude 008",
    "source": "user assignment pasted in chat; card BLOCK 1 still holds stage 1 (not changed)",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "new_files": {rel: {"role": role, **facts(REPO / rel)} for rel, role in NEW.items()},
    "changed_files": changed,
    "other_changed_files": {rel: {"role": role, **facts(REPO / rel)} for rel, role in OTHER_CHANGED.items()},
    "stage1_files_unchanged": s1_unchanged,
    "launcher_files_unchanged": launcher_unchanged,
    "evidence_summary": evidence,
    "evidence_sanitizer_scan_before_manifest": json.loads(scan.stdout)["classes"],
    "git_used": False, "network_used": False, "real_standard_storage_used": False, "real_tk_settings_read": False,
    "live_or_paid_api_used": False,
    "files": rows,
}
(PACKAGE / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"package_files": len(rows), "scan": record["evidence_sanitizer_scan_before_manifest"],
                  "stage1_unchanged": all(s1_unchanged.values()), "launcher_unchanged": all(launcher_unchanged.values())}))
