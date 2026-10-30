"""Build manifest.json for CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001: the changed project files with their published #464 / #457
pins, proof that the other published EVM / Stage1 / launcher files are unchanged, every package file, and the
publication scan (web_alarm.evidence_sanitizer, must exit 0). Text files of the package must be LF without unsafe
separators. After the BLOCK 1 -> 1.1 rotation the card and the snapshot are listed too.
Usage: make_manifest.py
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[1]
TASK = PACKAGE.name
CARD = "Документация/000_Задачи Claude.md"
CHANGED = {
    "web_alarm/ui.py": "pinned EVM windows: a collection by connection_id in its own layer under the Ctrl preview; moved by the title, "
                       "closed only by «×», saved per window and restored once per page load; the preview promoted by a press",
    "test_web_alarm_evm_ui.js": "E1-E44: 30 of #464 kept or adjusted, E15/E21/E31/E32 rewritten, E38-E44 new for the windows",
    "web_alarm/model_cards.py": "the optional layout part of ultra/evm_view.json (own revision, whole pixels, one window per entry); "
                                "save_layout; an order save keeps the layout; a damaged layout is reported, set aside and never breaks the board",
    "web_alarm/server.py": "POST /ultra/model-cards/layout under the existing local-origin guard of /ultra/model-cards*",
    "test_web_alarm_model_cards.py": "m22-m25 for the layout (persistence, validation, two pages and concurrency, damage and absent entries), "
                                     "four HTTP cases in m16",
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


def main():
    launcher, s1, evm455, evm457, evm464 = (manifest("CLAUDE-WUA-CHAT-LAUNCHER-001"), manifest("CLAUDE-WUA-CHAT-S1-READONLY-UI-001"),
                                            manifest("CLAUDE-WUA-EVM-MODEL-CARD-UI-001"), manifest("CLAUDE-WUA-EVM-COMPACT-LAYOUT-001"),
                                            manifest("CLAUDE-WUA-EVM-INTERACTION-DND-001"))
    pins = {}  # the latest published content of every file these packages list (later packages win)
    pins.update({k: v["sha256"] for k, v in launcher["new_files"].items()})
    pins.update({k: v["sha256"] for k, v in s1["changed_files"].items()})
    for group in ("new_files", "changed_files", "other_changed_files"):
        pins.update({k: v["sha256"] for k, v in evm455[group].items()})
    pins.update({k: v["sha256"] for k, v in evm457["changed_files"].items()})
    pins.update({k: v["sha256"] for k, v in evm464["changed_files"].items()})
    changed = {rel: {"role": role, **facts(REPO / rel), "published_sha256": pins[rel]} for rel, role in CHANGED.items()}
    unchanged = {rel: same_content(REPO / rel, pin) for rel, pin in sorted(pins.items()) if rel not in CHANGED}
    snapshot = PACKAGE / "handoff_task.md"
    rotation = None
    if snapshot.is_file():
        rotation = {"card": CARD, "card_after_rotation": facts(REPO / CARD), "snapshot": facts(snapshot),
                    "protocol": "evidence/rotation.json"}
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
    if not all(unchanged.values()):
        problems.append("a published file outside this task changed: " + ", ".join(k for k, v in unchanged.items() if not v))
    if any(same_content(REPO / rel, row["published_sha256"]) for rel, row in changed.items()):
        problems.append("a file listed as changed still has its published content")
    if problems:
        sys.exit("manifest refused: " + "; ".join(problems))
    evidence = {}
    for path in sorted((PACKAGE / "evidence").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        evidence[path.name] = {key: value[key] for key in ("purpose", "runner_exit", "tests_run", "failures", "errors", "skips",
                                                            "isolation_violations", "killed", "mutants", "pass", "fail", "verdict",
                                                            "checks", "failed", "result")
                               if key in value}
    record = {
        "task": TASK, "executor": "Claude 008",
        "source": "BLOCK 1 of the Claude card (coordinator text pasted by the user, TASK ID line included); user GO in chat",
        "base": "published #464 (page) and #457 (server side) content (local checkout compared by content; Git not used)",
        "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
        "changed_files": changed,
        "published_files_unchanged": unchanged,
        "server_side_changed": "layout only: web_alarm/model_cards.py, web_alarm/server.py",
        "rotation": rotation,
        "evidence_summary": evidence,
        "evidence_sanitizer_scan_before_manifest": json.loads(scan.stdout)["classes"],
        "git_used": False, "network_used": "loopback demo only", "real_standard_storage_used": False,
        "real_tk_settings_read": False, "live_or_paid_api_used": False, "physical_windows_mouse": "NOT RUN",
        "files": rows,
    }
    (PACKAGE / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"package_files": len(rows), "scan": record["evidence_sanitizer_scan_before_manifest"],
                      "published_unchanged": all(unchanged.values()), "unchanged_files": len(unchanged), "rotation": bool(rotation)}))


if __name__ == "__main__":
    main()
