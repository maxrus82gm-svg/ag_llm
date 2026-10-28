"""Build manifest.json for CLAUDE-WUA-EVM-COMPACT-LAYOUT-001: the changed project files with their published #455
pins, proof that Stage1, launcher and the untouched EVM files are unchanged, every package file, and the publication
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
CHANGED = {
    "web_alarm/ui.py": "four-column EVM board, compact cards, one floating full card, order and favourites, "
                       "«Изменить описание», chat-model picker next to the Ultra Chat composer",
    "web_alarm/server.py": "POST /ultra/model-cards/view (under the existing local-origin guard of /ultra/model-cards*)",
    "web_alarm/model_cards.py": "ultra/evm_view.json: manual order per column and favourites (references only), view in the catalog",
    "test_web_alarm_model_cards.py": "m18-m21 board view tests, three HTTP cases in m16",
    "test_web_alarm_evm_ui.js": "rewritten for the board: E1-E30",
}
BINARY = {".png"}
sha = lambda data: hashlib.sha256(data).hexdigest()


def facts(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha(data),
            "eol": "binary" if path.suffix in BINARY else "CRLF" if b"\r\n" in data else ("LF" if b"\n" in data else "none")}


def same_content(path: Path, pin: str) -> bool:
    data = path.read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    return pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


def manifest(task: str) -> dict:
    return json.loads((REPO / "reports" / task / "manifest.json").read_text(encoding="utf-8"))


evm, s1, launcher = (manifest("CLAUDE-WUA-EVM-MODEL-CARD-UI-001"), manifest("CLAUDE-WUA-CHAT-S1-READONLY-UI-001"),
                     manifest("CLAUDE-WUA-CHAT-LAUNCHER-001"))
pins = {**{k: v["sha256"] for k, v in evm["new_files"].items()}, **{k: v["sha256"] for k, v in evm["changed_files"].items()},
        **{k: v["sha256"] for k, v in evm["other_changed_files"].items()}}
changed = {rel: {"role": role, **facts(REPO / rel), "published_455_sha256": pins[rel]} for rel, role in CHANGED.items()}
evm_unchanged = {rel: same_content(REPO / rel, pin) for rel, pin in pins.items() if rel not in CHANGED}
s1_unchanged = {rel: same_content(REPO / rel, row["sha256"]) for rel, row in s1["changed_files"].items()
                if rel not in CHANGED and rel not in pins}
launcher_unchanged = {rel: same_content(REPO / rel, row["sha256"]) for rel, row in launcher["new_files"].items()}
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
if not all({**evm_unchanged, **s1_unchanged, **launcher_unchanged}.values()):
    problems.append("a file outside this task changed")
if any(same_content(REPO / rel, row["published_455_sha256"]) for rel, row in changed.items()):
    problems.append("a file listed as changed still has the #455 content")
if problems:
    sys.exit("manifest refused: " + "; ".join(problems))
evidence = {}
for path in sorted((PACKAGE / "evidence").glob("*.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    evidence[path.name] = {key: value[key] for key in ("purpose", "runner_exit", "tests_run", "failures", "errors", "skips",
                                                        "isolation_violations", "killed", "mutants", "pass", "fail", "verdict")
                           if key in value}
record = {
    "task": "CLAUDE-WUA-EVM-COMPACT-LAYOUT-001", "executor": "Claude 008",
    "source": "BLOCK 1 of the Claude card (user assignment) + AMENDMENT (local sources after the user's sync, one package)",
    "base": "published main #455 content of the EVM package (local checkout compared by content; Git not used)",
    "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
    "changed_files": changed,
    "evm_files_unchanged": evm_unchanged,
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
                  "evm_unchanged": all(evm_unchanged.values()), "stage1_unchanged": all(s1_unchanged.values()),
                  "launcher_unchanged": all(launcher_unchanged.values())}))
