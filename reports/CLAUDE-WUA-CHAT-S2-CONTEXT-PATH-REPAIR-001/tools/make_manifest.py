"""Build manifest.json for CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001: the two changed files with the Stage2 content they
replaced, proof that every other published launcher / Stage1 / EVM / Stage2 file is unchanged, every package file,
and the publication scan (web_alarm.evidence_sanitizer, must exit 0). Package text files must be LF without unsafe
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
    "context_storage.py": "F-01 repair: the three message-context writers refuse a link at any existing level of "
                          "message_context/<message_id>/variants before reading or writing, and write only into folders "
                          "created or verified level by level right before the write (under the Workspace lock, checked); "
                          "variants by exclusive publication, state.json by a verified replace with read-back; restore never "
                          "overwrites a newer state and refuses a state.json that is not a regular file",
    "test_ultra_chat_storage.py": "MessageContextPathTests (12) and MessageContextLockTests (3): junctions at each level, "
                                  "links made after the first check, state.json kinds, damaged and newer state, ordinary "
                                  "folders and byte-identical old data, lock, two processes, crashes",
}
sha = lambda data: hashlib.sha256(data).hexdigest()


def facts(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha(data), "eol": "CRLF" if b"\r\n" in data else ("LF" if b"\n" in data else "none")}


def same_content(path: Path, pin: str) -> bool:
    data = path.read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    return pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


def manifest(task: str) -> dict:
    return json.loads((REPO / "reports" / task / "manifest.json").read_text(encoding="utf-8"))


def main():
    pins = {}  # the latest published content of every file these packages list (later packages win)
    pins.update({k: v["sha256"] for k, v in manifest("CLAUDE-WUA-CHAT-LAUNCHER-001")["new_files"].items()})
    pins.update({k: v["sha256"] for k, v in manifest("CLAUDE-WUA-CHAT-S1-READONLY-UI-001")["changed_files"].items()})
    evm455 = manifest("CLAUDE-WUA-EVM-MODEL-CARD-UI-001")
    for group in ("new_files", "changed_files", "other_changed_files"):
        pins.update({k: v["sha256"] for k, v in evm455[group].items()})
    for task in ("CLAUDE-WUA-EVM-COMPACT-LAYOUT-001", "CLAUDE-WUA-EVM-INTERACTION-DND-001", "CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001"):
        pins.update({k: v["sha256"] for k, v in manifest(task)["changed_files"].items()})
    s2 = manifest("CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001")
    for group in ("changed_files", "new_files"):
        pins.update({k: v["sha256"] for k, v in s2[group].items()})
    changed = {rel: {"role": role, **facts(REPO / rel), "replaced_sha256": pins[rel],
                     "replaced_source": "Stage2 package (published No.473, base No.474)"} for rel, role in CHANGED.items()}
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
    if any(same_content(REPO / rel, row["replaced_sha256"]) for rel, row in changed.items()):
        problems.append("a file listed as changed still has its old content")
    if problems:
        sys.exit("manifest refused: " + "; ".join(problems))
    evidence = {}
    for path in sorted((PACKAGE / "evidence").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        evidence[path.name] = {key: value[key] for key in ("purpose", "runner_exit", "tests_run", "failures", "errors", "skips",
                                                            "isolation_violations", "killed", "mutants", "cases",
                                                            "wrote_outside", "refused")
                               if key in value}
    record = {
        "task": TASK, "executor": "Claude 008",
        "source": "BLOCK 1 of the Claude card (user paste, TASK ID line included); FOLLOWUP-WUA-S2-CONTEXT-PATH-001 / F-01 of WEB18",
        "base": "main@254e48166407d3aabf6484c8627da86acf8b05df (No.474) as published content (Stage2 bytes of No.473; Git not used)",
        "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
        "changed_files": changed,
        "published_files_unchanged": unchanged,
        "rotation": rotation,
        "evidence_summary": evidence,
        "evidence_sanitizer_scan_before_manifest": json.loads(scan.stdout)["classes"],
        "git_used": False, "network_used": "none (loopback test servers of the regression only)", "real_workspaces_used": False,
        "live_or_paid_api_used": False, "launcher_switched": False,
        "files": rows,
    }
    (PACKAGE / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"package_files": len(rows), "scan": record["evidence_sanitizer_scan_before_manifest"],
                      "published_unchanged": all(unchanged.values()), "unchanged_files": len(unchanged), "rotation": bool(rotation)}))


if __name__ == "__main__":
    main()
