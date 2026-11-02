"""Change inventory of CLAUDE-WUA-CHAT-RUNSTORE-P9-001 without Git.
- run_store.py and test_run_store_v2.py against the copies taken before the first edit (a private TEMP folder passed
  as an argument, never published): SHA-256 before/after, line endings, added/removed lines (difflib);
- every READ-ONLY file named by the task against the last published package that pins it (by content, LF/CRLF
  normalised), and audit_storage.py (no package pins it) against its pre-edit copy;
- the launcher (STANDARD, files as in the launcher package) and the card slot check.
Usage: change_inventory.py <pre-edit folder> <out.json>
"""
import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from web_alarm.launcher import load_launch  # noqa: E402

CHANGED = ("run_store.py", "test_run_store_v2.py")
CARD = "Документация/000_Задачи Claude.md"
sha = lambda data: hashlib.sha256(data).hexdigest()


def row(data: bytes) -> dict:
    lf = data.replace(b"\r\n", b"\n")
    return {"sha256": sha(data), "sha256_lf": sha(lf), "crlf_lines": data.count(b"\r\n"), "lines": lf.count(b"\n")}


def same(rel: str, pin: str) -> bool:
    data = (REPO / rel).read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    return pin in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}


def manifest(task: str) -> dict:
    return json.loads((REPO / "reports" / task / "manifest.json").read_text(encoding="utf-8"))


def main():
    base, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = {}
    for rel in CHANGED:
        before, after = (base / rel).read_bytes(), (REPO / rel).read_bytes()
        diff = list(difflib.unified_diff(before.decode("utf-8").splitlines(), after.decode("utf-8").splitlines(), lineterm="", n=0))
        files[rel] = {"before": row(before), "after": row(after), "changed": before != after,
                      "added": sum(1 for d in diff if d.startswith("+") and not d.startswith("+++")),
                      "removed": sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))}
    pins, source = {}, {}
    for task, groups in (("CLAUDE-WUA-CHAT-LAUNCHER-001", ("new_files",)), ("CLAUDE-WUA-CHAT-S1-READONLY-UI-001", ("changed_files",)),
                         ("CLAUDE-WUA-EVM-MODEL-CARD-UI-001", ("new_files", "changed_files", "other_changed_files")),
                         ("CLAUDE-WUA-EVM-COMPACT-LAYOUT-001", ("changed_files",)), ("CLAUDE-WUA-EVM-INTERACTION-DND-001", ("changed_files",)),
                         ("CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", ("changed_files",)),
                         ("CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", ("changed_files", "new_files")),
                         ("CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001", ("changed_files",)),
                         ("CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001", ("changed_files",))):
        for group in groups:
            for rel, value in (manifest(task).get(group) or {}).items():
                pins[rel], source[rel] = value["sha256"], task
    read_only = {}
    for rel in ("context_storage.py", "web_alarm/store_lock.py", "web_alarm/server.py", "web_alarm/ui.py", "ultra_ui.py",
                "web_alarm/model_cards.py", "web_alarm/ultra_chat.py", "Start_WebAlarm.bat", "web_alarm/launcher.py",
                "web_alarm/launch_config.json"):
        read_only[rel] = {"pinned_by": source.get(rel), "same_content": same(rel, pins[rel]) if rel in pins else None}
    audit_before = (base / "audit_storage.py").read_bytes()
    read_only["audit_storage.py"] = {"pinned_by": "pre-edit copy (no package pins it)",
                                     "same_content": audit_before == (REPO / "audit_storage.py").read_bytes()}
    # store_lock.py: no package pins it; its SHA-256 was recorded in the session before the first edit of this task
    read_only["web_alarm/store_lock.py"] = {
        "pinned_by": "SHA-256 recorded before the first edit (6ae82859...)",
        "same_content": sha((REPO / "web_alarm/store_lock.py").read_bytes())
        == "6ae82859cb51f89dfcaa2f09ab560cf816236615ed7ad24c8cb89abde72ba4c7"}
    unpinned = [rel for rel in ("server.py", "model_registry.py") if rel not in pins]
    copy_time = min(p.stat().st_mtime_ns for p in base.iterdir())  # the pre-edit copies keep the source times (cp -p not used: copy time)
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    check = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", "check", "--card", CARD], cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8")
    protocol = json.loads(check.stdout)
    record = {"task": "CLAUDE-WUA-CHAT-RUNSTORE-P9-001", "method": "byte comparison; no Git",
              "changed": files, "read_only_files": read_only,
              "read_only_all_unchanged": all(v["same_content"] for v in read_only.values()),
              "read_only_without_a_published_pin": {
                  rel: {"sha256_now": sha((REPO / rel).read_bytes()),
                        "last_modified_before_the_pre_edit_copy": (REPO / rel).stat().st_mtime_ns < copy_time}
                  for rel in unpinned},
              "launcher": {"config_active": config["active"], "load_launch_standard": load_launch().standard},
              "card_check": {"result": protocol["result"], "block1": protocol["block1"], "block1_1": protocol["block1_1"]}}
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: (v["added"], v["removed"]) for k, v in files.items()}))
    print(json.dumps({k: v["same_content"] for k, v in read_only.items()}))
    print(json.dumps({"unpinned": unpinned, "launcher": config["active"], "card": protocol["result"]}))


if __name__ == "__main__":
    main()
