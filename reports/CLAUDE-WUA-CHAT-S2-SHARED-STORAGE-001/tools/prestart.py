"""Pre-start record of CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001, taken before the first edit:
- the slot check of the Claude card (tools/task_slot_rotate.py check);
- the launcher mode (launch_config.json, load_launch(): STANDARD, nothing switched) and Start_WebAlarm.bat content;
- the files of the write scope compared with the last published package that changed them (#467 for server/ui, the
  Stage1 package for context_storage / ultra_chat / the Stage1 tests), allowing the CRLF of the user's sync (no Git);
  files no package pins (ultra_ui.py, test_chat_create_atomicity.py, store_lock.py) are recorded by hash only.
Usage: prestart.py <out.json>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from web_alarm.launcher import load_launch  # noqa: E402

CARD = "Документация/000_Задачи Claude.md"
SCOPE = ("context_storage.py", "ultra_ui.py", "web_alarm/ultra_chat.py", "web_alarm/server.py", "web_alarm/ui.py",
         "web_alarm/store_lock.py", "test_chat_create_atomicity.py", "test_ultra_chat_read.py", "test_web_alarm_ultra_chat.py",
         "test_web_alarm_ultra_chat_ui.js")
sha = lambda data: hashlib.sha256(data).hexdigest()


def manifest(task: str) -> dict:
    return json.loads((REPO / "reports" / task / "manifest.json").read_text(encoding="utf-8"))


def main():
    check = subprocess.run([sys.executable, "-B", "tools/task_slot_rotate.py", "check", "--card", CARD], cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8")
    protocol = json.loads(check.stdout)
    config = json.loads((REPO / "web_alarm/launch_config.json").read_text(encoding="utf-8"))
    launch = load_launch()
    pins = {}
    for task, key in (("CLAUDE-WUA-CHAT-LAUNCHER-001", "new_files"), ("CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "changed_files"),
                      ("CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001", "changed_files")):
        for rel, row in manifest(task)[key].items():
            pins[rel] = (task, row["sha256"])
    scope = {}
    for rel in SCOPE + ("Start_WebAlarm.bat", "web_alarm/launcher.py", "web_alarm/launch_config.json"):
        data = (REPO / rel).read_bytes()
        lf = data.replace(b"\r\n", b"\n")
        row = {"sha256": sha(data), "eol": "CRLF" if b"\r\n" in data else "LF"}
        if rel in pins:
            row.update(pinned_by=pins[rel][0], same_content_as_pin=pins[rel][1] in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))})
        scope[rel] = row
    record = {
        "task": "CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001", "purpose": "pre-start state before the first edit",
        "card_check": {"exit": check.returncode, "result": protocol["result"], "card_sha256": protocol["card_sha256"],
                       "eol": protocol["eol"], "block1": protocol["block1"], "block1_1": protocol["block1_1"]},
        "card_check_first": "INVALID (WAITING_LINE_LEFT_IN_TASK, line 46) before the user's fix; reported, not fixed by the executor",
        "launcher": {"config_active": config["active"], "load_launch": {"name": launch.name, "standard": launch.standard,
                                                                         "port": launch.port, "storage": launch.storage}},
        "files": scope,
        "no_conflicting_changes": all(r.get("same_content_as_pin", True) for r in scope.values()),
        "direction_b_active_files": "none (No.40, section B)", "published_467_closed": "PASS / USER ACCEPTED (card BLOCKS 2/4, No.40)",
        "git_used": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"check": protocol["result"], "launcher": config["active"], "no_conflicting_changes": record["no_conflicting_changes"],
                      "unpinned": [k for k, v in scope.items() if "pinned_by" not in v]}))


if __name__ == "__main__":
    main()
