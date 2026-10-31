"""Build manifest.json for CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001: the changed and new project files with the content they
replaced (the last published package pin, or the pre-start hash where no package pins a file), proof that the other
published launcher / Stage1 / EVM files are unchanged, every package file, and the publication scan
(web_alarm.evidence_sanitizer, must exit 0). Package text files must be LF without unsafe separators. After the
BLOCK 1 -> 1.1 rotation the card and the snapshot are listed too.
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
    "context_storage.py": "shared writer contract: Workspace writer lock (.ultra/locks/writer.lock, per-thread reentrant, visible timeout), "
                          "identity read again under the lock, ownership/version/link checks for every writer, exclusive "
                          "publication with read-back, replace retry, commit_raw_message (local RAW idempotency), "
                          "create_chat_record (idempotent by chat_id), rename with the seen title, no new identity next to an "
                          "orphaned history; message-context writers under the same lock",
    "ultra_ui.py": "Tk Chat writers only: create with the registered identity, rename with the title shown in the dialog",
    "web_alarm/ultra_chat.py": "separate write capability (ultra_chat_write) and the create/rename routes over the shared writer",
    "web_alarm/server.py": "POST create/rename and GET /ui/ultra-chat/write-capability under the local-origin gate; "
                           "--disable-ultra-chat-write; small bodies read before any refusal",
    "web_alarm/ui.py": "Ultra Chat area only: «+ Новый диалог», «✎ Переименовать», name form; write token asked on demand",
    "test_web_alarm_ultra_chat_ui.js": "U8 composer note updated; U13-U19 new (create, rename, retries, refusals, tokens)",
}
NEW = {
    "test_ultra_chat_storage.py": "shared writer: format, RAW idempotency, chats, lock, two processes, crashes, links, portability",
    "test_web_alarm_ultra_chat_storage.py": "HTTP write path over the real server: capability, tokens, refusals, ownership, restart, concurrency",
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
    prestart = json.loads((PACKAGE / "evidence" / "prestart.json").read_text(encoding="utf-8"))["files"]
    changed = {}
    for rel, role in CHANGED.items():
        before = pins.get(rel) or prestart[rel]["sha256"]
        changed[rel] = {"role": role, **facts(REPO / rel), "replaced_sha256": before,
                        "replaced_source": "published package pin" if rel in pins else "pre-start record (no package pins it)"}
    new = {rel: {"role": role, **facts(REPO / rel)} for rel, role in NEW.items()}
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
                                                            "isolation_violations", "killed", "mutants", "pass", "fail",
                                                            "passed", "result")
                               if key in value}
    record = {
        "task": TASK, "executor": "Claude 008",
        "source": "BLOCK 1 of the Claude card (user paste, TASK ID line included); user GO in chat",
        "base": "main@cd25b8d6ef71dc3a266adfb6945d30aa3cc8f66d as published content (local checkout compared by content; Git not used)",
        "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
        "changed_files": changed,
        "new_files": new,
        "published_files_unchanged": unchanged,
        "write_scope_files_not_changed": ["web_alarm/store_lock.py", "test_chat_create_atomicity.py", "test_ultra_chat_read.py",
                                          "test_web_alarm_ultra_chat.py"],
        "rotation": rotation,
        "evidence_summary": evidence,
        "evidence_sanitizer_scan_before_manifest": json.loads(scan.stdout)["classes"],
        "git_used": False, "network_used": "loopback test and demo servers only", "real_workspaces_used": False,
        "real_tk_settings_read": False, "live_or_paid_api_used": False, "launcher_switched": False,
        "files": rows,
    }
    (PACKAGE / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"package_files": len(rows), "scan": record["evidence_sanitizer_scan_before_manifest"],
                      "published_unchanged": all(unchanged.values()), "unchanged_files": len(unchanged), "rotation": bool(rotation)}))


if __name__ == "__main__":
    main()
