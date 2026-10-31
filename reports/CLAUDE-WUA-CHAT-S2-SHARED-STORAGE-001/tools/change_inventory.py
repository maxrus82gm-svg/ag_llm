"""Change inventory of CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001 without Git: every file of the write scope is compared
with the copy taken before the first edit (a private TEMP folder, passed as an argument and never published).
Published: per file the SHA-256 before/after (as on disk, and LF-normalised), the line ending, added/removed line
counts (difflib), and whether the file is new. Also checks that no file outside the write scope was changed among
the top-level and web_alarm sources, by comparing them with the pre-start record (evidence/prestart.json) where pinned.
Usage: change_inventory.py <baseline-folder> <out.json>
"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHANGED = ("context_storage.py", "ultra_ui.py", "web_alarm/ultra_chat.py", "web_alarm/server.py", "web_alarm/ui.py",
           "test_web_alarm_ultra_chat_ui.js")
NEW = ("test_ultra_chat_storage.py", "test_web_alarm_ultra_chat_storage.py")
UNCHANGED_IN_SCOPE = ("web_alarm/store_lock.py", "test_chat_create_atomicity.py", "test_ultra_chat_read.py",
                      "test_web_alarm_ultra_chat.py")
sha = lambda data: hashlib.sha256(data).hexdigest()


def row(data: bytes) -> dict:
    lf = data.replace(b"\r\n", b"\n")
    return {"sha256": sha(data), "sha256_lf": sha(lf), "eol": "CRLF" if b"\r\n" in data else "LF", "lines": lf.count(b"\n")}


def main():
    base, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = {}
    for rel in CHANGED + UNCHANGED_IN_SCOPE:
        before = (base / rel).read_bytes()
        after = (REPO / rel).read_bytes()
        diff = list(difflib.unified_diff(before.replace(b"\r\n", b"\n").decode("utf-8").splitlines(),
                                         after.replace(b"\r\n", b"\n").decode("utf-8").splitlines(), lineterm="", n=0))
        files[rel] = {"before": row(before), "after": row(after),
                      "added": sum(1 for d in diff if d.startswith("+") and not d.startswith("+++")),
                      "removed": sum(1 for d in diff if d.startswith("-") and not d.startswith("---")),
                      "changed": sha(before) != sha(after), "eol_kept": row(before)["eol"] == row(after)["eol"]}
    for rel in NEW:
        data = (REPO / rel).read_bytes()
        files[rel] = {"new": True, "after": row(data), "added": row(data)["lines"], "removed": 0, "changed": True}
    prestart = json.loads((REPO / "reports/CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001/evidence/prestart.json").read_text(encoding="utf-8"))
    launcher = {rel: sha((REPO / rel).read_bytes()) == prestart["files"][rel]["sha256"]
                for rel in ("Start_WebAlarm.bat", "web_alarm/launcher.py", "web_alarm/launch_config.json")}
    record = {
        "task": "CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", "method": "byte comparison with the pre-edit copies; no Git",
        "files": files,
        "changed_in_scope": sorted(k for k, v in files.items() if v["changed"] and not v.get("new")),
        "new_files": list(NEW),
        "unchanged_in_scope": sorted(k for k in UNCHANGED_IN_SCOPE if not files[k]["changed"]),
        "launcher_files_identical_to_prestart": launcher,
        "store_lock_changed": files["web_alarm/store_lock.py"]["changed"],
    }
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: (v["added"], v["removed"]) for k, v in files.items()}, ensure_ascii=False))
    print(json.dumps({"unchanged": record["unchanged_in_scope"], "launcher": launcher}))


if __name__ == "__main__":
    main()
